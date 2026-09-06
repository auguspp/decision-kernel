"""Bounded immutable snapshots of existing scan/execution bundles, not signal state.

Registration and restoration reuse the original replayers. No discovery, HTTP,
registry mutation, completion inference, or implicit empty-history fallback.
"""
from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from decision_kernel.identity import canonical_hash
from . import radar_feed_consumer as consumer
from . import radar_feed_intake as feed
from . import theme_plan_execution as execution
from . import theme_radar_probe as probe

VERSION = 'native-feed-retained-consumer-history-v0'
SEMANTICS = 'REGISTERED_SCAN_AND_EXECUTION_BYTES_NOT_SOURCE_DELIVERY_OR_SIGNAL_STATE'
SCOPE = 'EXPLICIT_BRANCH_HISTORY_NOT_GLOBAL_LATEST_OR_EXACTLY_ONCE_TRANSPORT'
KINDS = ('scans', 'executions')
MAX_FILES = 8192  # The existing 32 MiB TOTAL bundle budget still applies.
FIELDS = {'version', 'semantics', 'scope', 'created_at', 'recorded_at', 'parent_history_hash',
          'source_anchor', 'scans', 'executions', 'files', 'source_delivery_acknowledged',
          'remote_publication_verified', 'history_hash', *probe.AUTHORITY}


def _inventory(root):
    return consumer._inventory(root, maximum_files=MAX_FILES)


def _write(path, value):
    with path.open('xb') as stream:
        stream.write(feed.data(value))


def _new_output(output, inputs):
    probe._safe_path(output)
    if output.exists():
        raise ValueError('history output already exists; never overwrite')
    for source in inputs:
        probe._safe_path(source)
        left, right = output.resolve(), source.resolve()
        if left.is_relative_to(right) or right.is_relative_to(left):
            raise ValueError('history output must be disjoint from all inputs')


def _anchor(source, at):
    captured, registry, _ = consumer._load_feed(source, at)
    # These are references to immutable versions and FIRST clocks, not new facts.
    rows = {v['version_hash']: {
        'first_identity': canonical_hash({k: val for k, val in v.items() if k != 'appearances'}),
        'appearances': sorted(canonical_hash(a) for a in v['appearances']),
    } for v in registry['versions']}
    return {'provenance': captured['provenance'], 'policy_hash': registry['policy_hash'],
            'initialized_at': registry['initialized_at'], 'recorded_at': registry['recorded_at'],
            'capture_hash': captured['capture_hash'], 'registry_hash': registry['registry_hash'],
            'versions': rows}


def _extends(old, new):
    if (any(old[k] != new[k] for k in ('provenance', 'policy_hash', 'initialized_at'))
            or probe._clock(old['recorded_at']) > probe._clock(new['recorded_at'])):
        raise ValueError('source baseline, provenance, policy or chronology differs')
    for key, original in old['versions'].items():
        candidate = new['versions'].get(key)
        if (candidate is None or candidate['first_identity'] != original['first_identity']
                or not set(original['appearances']) <= set(candidate['appearances'])):
            raise ValueError('source history lost a version, first clock or appearance')


def _header(value):
    probe._keys(value, FIELDS)
    if (value['version'] != VERSION or value['semantics'] != SEMANTICS or value['scope'] != SCOPE
            or value['history_hash'] != canonical_hash({k: v for k, v in value.items() if k != 'history_hash'})
            or any(value[k] != v for k, v in probe.AUTHORITY.items())
            or value['source_delivery_acknowledged'] is not False
            or value['remote_publication_verified'] is not False
            or probe._clock(value['created_at']) > probe._clock(value['recorded_at'])):
        raise ValueError('history identity, time or authority differs')
    for kind in KINDS:
        if not isinstance(value[kind], dict) or len(value[kind]) > consumer.MAX_RECEIPTS:
            raise ValueError('history capacity reached; explicit archival required')
    return value


def _object(path, kind, *, at):
    if kind == 'scans':
        checked = consumer.verify_scan(path, as_of=at)
        receipt = checked['receipt']
        identity = receipt['receipt_hash']
        result = {'receipt_hash': identity,
                  'plan_hash': canonical_hash(checked['result']['acquisition_plan']) if checked['result']['acquisition_plan'] else None}
        inventory = consumer._inventory(path)
    else:
        checked = execution.verify_execution(path, as_of=at)
        identity = checked['execution_hash']
        result = {'receipt_hash': checked['scan_receipt_hash'], 'plan_hash': checked['plan_hash'],
                  'market_stage_succeeded': checked['market_stage_succeeded']}
        inventory = consumer._inventory(path, maximum_files=64)
    return identity, {**result, 'tree_hash': canonical_hash(inventory)}, inventory


def verify_history(root: Path, *, as_of: str | None = None, expected_hash: str | None = None,
                   source: Path | None = None) -> dict:
    """Rebuild every stored object; parent inclusion is relative to the supplied branch.

    Parent metadata does not authenticate an omitted predecessor. Remote selection
    must independently bind the exact artifact/hash; this is not latest discovery.
    """
    inventory = _inventory(root)
    value = _header(consumer._json(root/'history.json'))
    if expected_hash is not None and value['history_hash'] != expected_hash:
        raise ValueError('history differs from the explicitly pinned identity')
    at = value['recorded_at']
    if as_of is not None and probe._clock(at) > probe._clock(as_of):
        raise ValueError('history was registered after the requested cutoff')
    if value['files'] != {k: v for k, v in inventory.items() if k != 'history.json'}:
        raise ValueError('history file inventory differs')
    names = {'history.json', 'feed-capture', *KINDS}
    if value['parent_history_hash'] is not None:
        names.add('parent.json')
        parent = _header(consumer._json(root/'parent.json'))
        if (parent['history_hash'] != value['parent_history_hash'] or parent['created_at'] != value['created_at']
                or probe._clock(parent['recorded_at']) >= probe._clock(at)):
            raise ValueError('history predecessor identity or registration time differs')
        _extends(parent['source_anchor'], value['source_anchor'])
        for kind in KINDS:
            if any(value[kind].get(key) != row for key, row in parent[kind].items()):
                raise ValueError('history predecessor objects were removed or rewritten')
    if {p.name for p in root.iterdir()} != names:
        raise ValueError('history root inventory differs')
    anchor = _anchor(root/'feed-capture', at)
    if value['source_anchor'] != anchor:
        raise ValueError('source anchor does not rebuild from retained original RSS')
    for kind in KINDS:
        paths = list((root/kind).iterdir())
        if {p.name for p in paths} != set(value[kind]):
            raise ValueError('registered object inventory differs')
        for path in paths:
            identity, descriptor, _ = _object(path, kind, at=at)
            if path.name != identity or descriptor != value[kind].get(identity):
                raise ValueError('registered object identity or replay differs')
            if kind == 'scans':
                _extends(_anchor(path/'feed-capture', at), anchor)
            else:
                linked = value['scans'].get(descriptor['receipt_hash'])
                if (linked is None or linked['plan_hash'] != descriptor['plan_hash']
                        or linked['tree_hash'] != canonical_hash(consumer._inventory(path/'source-scan'))):
                    raise ValueError('execution does not reference the exact registered scan')
    if source is not None:
        _extends(anchor, _anchor(source, as_of or at))
    return value


def register_history(source: Path, output: Path, *, as_of: str, previous: Path | None = None,
                     initialize: bool = False, previous_hash: str | None = None, scans=(), executions=()) -> dict:
    """Create one new snapshot; explicit initial history OR verified predecessor.

    The raw source registry never changes. A failed-but-replayable execution can
    be recorded; a malformed attempt or blocked scan cannot become a completion.
    """
    if type(initialize) is not bool or (previous is None) != initialize:
        raise ValueError('explicit initialization OR exact previous history required')
    if previous is not None and (not isinstance(previous_hash, str) or not previous_hash):
        raise ValueError('explicit predecessor hash required')
    if initialize and previous_hash is not None:
        raise ValueError('initial history cannot claim a predecessor hash')
    additions = {'scans': tuple(scans), 'executions': tuple(executions)}
    if any(len(paths) > consumer.MAX_RECEIPTS for paths in additions.values()):
        raise ValueError('history registration input count exceeded')
    inputs = [source, *additions['scans'], *additions['executions'], *([previous] if previous is not None else [])]
    _new_output(output, inputs)
    at = probe._clock(as_of).isoformat()
    original = {path: _inventory(path) for path in inputs}
    parent = verify_history(previous, as_of=at, expected_hash=previous_hash, source=source) if previous is not None else None
    if parent is not None and probe._clock(parent['recorded_at']) >= probe._clock(at):
        raise ValueError('successor registration must follow its predecessor')
    value = {'version': VERSION, 'semantics': SEMANTICS, 'scope': SCOPE,
             'created_at': parent['created_at'] if parent else at, 'recorded_at': at,
             'parent_history_hash': parent['history_hash'] if parent else None,
             'source_anchor': _anchor(source, at), 'scans': {}, 'executions': {},
             'source_delivery_acknowledged': False, 'remote_publication_verified': False, **probe.AUTHORITY}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.native-history-', dir=output.parent) as tmp:
        stage = Path(tmp)/'history'; stage.mkdir()
        shutil.copytree(source, stage/'feed-capture')
        if parent is not None:
            _write(stage/'parent.json', parent)
        for kind in KINDS:
            (stage/kind).mkdir()
            candidates = list((previous/kind).iterdir()) if previous is not None else []
            for path in [*candidates, *additions[kind]]:
                identity, descriptor, files = _object(path, kind, at=at)
                if identity in value[kind]:
                    if value[kind][identity] != descriptor or consumer._inventory(stage/kind/identity, maximum_files=64) != files:
                        raise ValueError('same history identity has different original bytes')
                    continue
                if len(value[kind]) >= consumer.MAX_RECEIPTS:
                    raise ValueError('history capacity reached; never prune')
                shutil.copytree(path, stage/kind/identity)
                value[kind][identity] = descriptor
        value['files'] = _inventory(stage)
        value = feed._sealed(value, 'history_hash')
        _write(stage/'history.json', value)
        verify_history(stage, as_of=at)
        if any(_inventory(path) != expected for path, expected in original.items()):
            raise ValueError('history input changed during registration')
        _new_output(output, inputs)
        stage.rename(output)
    return value


def restore_history(root: Path, source: Path, output: Path, *, as_of: str, expected_hash: str) -> dict:
    """Materialize the ORIGINAL consumer directories; never create an empty fallback."""
    if not isinstance(expected_hash, str) or not expected_hash:
        raise ValueError('explicit history hash required for restoration')
    _new_output(output, [root, source])
    value = verify_history(root, as_of=as_of, expected_hash=expected_hash, source=source)
    original, source_files = _inventory(root), _inventory(source)
    result = {'status': 'EXACT_CONSUMER_HISTORY_RESTORED', 'history_hash': value['history_hash'],
              'as_of': probe._clock(as_of).isoformat(), 'scan_count': len(value['scans']),
              'execution_count': len(value['executions']), 'scope': SCOPE, 'network_calls': 0,
              'source_delivery_acknowledged': False, 'remote_publication_verified': False, **probe.AUTHORITY}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.restore-native-history-', dir=output.parent) as tmp:
        stage = Path(tmp)/'restored'; stage.mkdir()
        for kind in KINDS:
            shutil.copytree(root/kind, stage/kind)
            if _inventory(stage/kind) != _inventory(root/kind):
                raise ValueError('restored history bytes differ')
        _write(stage/'restoration.json', result)
        if _inventory(root) != original or _inventory(source) != source_files:
            raise ValueError('history/source input changed during restoration')
        _new_output(output, [root, source]); stage.rename(output)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['register', 'verify', 'restore'])
    parser.add_argument('--history', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--expected-hash')
    parser.add_argument('--initialize', action='store_true')
    parser.add_argument('--scan', type=Path, action='append', default=[])
    parser.add_argument('--execution', type=Path, action='append', default=[])
    args = parser.parse_args(argv)
    try:
        if args.mode == 'register':
            if args.source is None or args.output is None:
                raise ValueError('source and new output required')
            value = register_history(args.source, args.output, as_of=args.as_of, previous=args.history,
                                     initialize=args.initialize, previous_hash=args.expected_hash, scans=args.scan, executions=args.execution)
        elif args.mode == 'verify':
            if args.history is None:
                raise ValueError('complete history required')
            value = verify_history(args.history, as_of=args.as_of, expected_hash=args.expected_hash, source=args.source)
        else:
            if any(x is None for x in (args.history, args.source, args.output, args.expected_hash)):
                raise ValueError('complete pinned history, source and new output required')
            value = restore_history(args.history, args.source, args.output, as_of=args.as_of, expected_hash=args.expected_hash)
        print(feed.data({'status': 'HISTORY_OPERATION_COMPLETE', 'history_hash': value['history_hash'],
                         'network_calls': 0, **probe.AUTHORITY}).decode())
        return 0
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as exc:
        print(feed.data({'status': 'HISTORY_UNAVAILABLE', 'error_type': type(exc).__name__, 'network_calls': 0}).decode())
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
