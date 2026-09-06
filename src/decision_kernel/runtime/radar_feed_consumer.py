"""Verified receipts for the existing source scanner, not market-delivery acks.

The feed registry and its strict complete-export guard are left unchanged.
A receipt proves exactly which qualified descriptions the existing scanner read.
It does not prove article acceptance, Human review, or execution of a market plan.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import tempfile
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from decision_kernel.identity import canonical_hash, canonical_json
from . import radar_feed_intake as feed
from . import theme_radar_probe as probe
from . import theme_source_discovery as discovery

VERSION = 'native-feed-source-scan-receipt-v0'
SEMANTICS = 'COMPLETED_LITERAL_SOURCE_SCAN_NOT_MARKET_EXECUTION_OR_FACT_ACCEPTANCE'
MAX_RECEIPTS = 64
MAX_BUNDLE_BYTES = 32 * 1024 * 1024
CONTEXT_FIELDS = {'concept_catalog', 'industry_catalog', 'industries'}
COMPLETED = {'SOURCE_LEADS_PLANNED', 'NO_LITERAL_CATALOG_MENTIONS'}
CORE_FILES = {'context.json', 'market-state.json', 'selection.json', 'source-discovery.json',
              'index.html', 'scan-receipt.json', 'handoff.json', 'files.json'}
SOURCE_SCOPE = 'Qualified post-baseline NBS RSS descriptions selected by verified source-scan receipts; not full articles.'


def _json(path: Path):
    return feed.decode(probe._read(path))


def _inventory(root: Path) -> dict:
    probe._safe_path(root)
    if not root.is_dir():
        raise ValueError('complete saved directory required')
    files, total = {}, 0
    for path in sorted(root.rglob('*')):
        probe._safe_path(path)
        if path.is_dir():
            continue
        raw = probe._read(path)
        total += len(raw)
        if total > MAX_BUNDLE_BYTES or len(files) >= 32:
            raise ValueError('source-scan bundle budget exceeded')
        files[path.relative_to(root).as_posix()] = feed.digest(raw)
    return files


def _load_feed(root: Path, as_of: str):
    checked = feed.verify_capture(root)
    if checked['capture_status'] != 'COMPLETE_FEED_INTAKE':
        raise ValueError('incomplete source acquisition cannot be consumed')
    receipt, registry, delta = (_json(root / name) for name in ('capture.json', 'registry.json', 'delta.json'))
    if probe._clock(receipt['finished_at']) > probe._clock(as_of):
        raise ValueError('source capture finished after the consumer cutoff')
    provenance = receipt['provenance']
    if provenance not in {'PUBLIC_HTTP_CAPTURE', probe.SYNTHETIC}:
        raise ValueError('unsupported source capture provenance')
    exports = feed.source_rows(registry, delta)
    return receipt, registry, exports


def _context(state, context: dict, provenance: str, as_of: str, generated_at: str):
    probe._keys(context, CONTEXT_FIELDS)
    inputs = {'schema_version': 1, 'provenance': probe.SYNTHETIC if provenance == probe.SYNTHETIC else probe.SUPPLIED,
              'source_scope': SOURCE_SCOPE, **copy.deepcopy(context), 'sources': []}
    # Validate the supplied market/catalog context through the existing consumer.
    # Its empty-source blocker is intentional here; no plan or request is created.
    result = discovery.discover_theme_sources(state, inputs, as_of=as_of, generated_at=generated_at)
    scope = {'consumer_version': VERSION, 'matcher_version': discovery.VERSION,
             'concept_catalog_hash': result['projection']['concept_catalog_hash'],
             'industry_catalog_hash': state.catalog_hash,
             'industries': sorted(context['industries'], key=lambda x: x['thscode']),
             'source_policy_hash': feed.POLICY_HASH}
    return inputs, scope


def _source_key(row: dict) -> str:
    # Includes exact content, retention semantics and FIRST receipt/record clocks.
    # A later feed occurrence does not change this key; a different version does.
    return canonical_hash(row)


def _evaluate(source: Path, state, context: dict, selection: dict):
    probe._keys(selection, {'source_keys', 'as_of', 'generated_at'})
    captured, registry, exports = _load_feed(source, selection['as_of'])
    inputs, scope = _context(state, context, captured['provenance'], selection['as_of'], selection['generated_at'])
    keys = selection['source_keys']
    if (exports['status'] != 'READY_RETAINED_DESCRIPTIONS' or not isinstance(keys, list)
            or not keys or keys != sorted(set(keys))):
        raise ValueError('qualified nonempty exact source selection required')
    by_key = {_source_key(row): row for row in exports['sources']}
    if not set(keys) <= set(by_key):
        raise ValueError('selected source is absent or not a qualified post-baseline version')
    inputs['sources'] = [by_key[key] for key in keys]
    result = discovery.discover_theme_sources(state, inputs, as_of=selection['as_of'], generated_at=selection['generated_at'])
    receipt = None
    if result['status'] in COMPLETED and not result['acquisition_blockers']:
        body = {'schema_version': 1, 'semantics': SEMANTICS, 'consumer_scope': scope,
                'consumer_scope_hash': canonical_hash(scope), 'provenance': captured['provenance'],
                'feed_initialized_at': registry['initialized_at'], 'feed_capture_hash': captured['capture_hash'],
                'feed_registry_hash': registry['registry_hash'], 'recorded_at': selection['generated_at'],
                'source_keys': keys, 'source_versions': sorted(row['evidence']['content_hash'] for row in inputs['sources']),
                'result_hash': result['result_hash'], 'scan_status': result['status'],
                'acquisition_status': 'PLAN_NOT_EXECUTED' if result['acquisition_plan'] else 'NO_PLAN_FROM_THIS_SCAN',
                'source_delivery_acknowledged': False, 'article_accepted': False,
                'human_review_recorded': False, **probe.AUTHORITY}
        receipt = feed._sealed(body, 'receipt_hash')
    return result, receipt


def verify_scan(root: Path, *, as_of: str | None = None) -> dict:
    """Rebuild the selected-source proof, not merely its declared hashes.

    Older scan receipts are external evidence. This proof concerns only its listed
    sources; it does not certify that the caller supplied every historical receipt.
    """
    inventory = _inventory(root)
    if set(p.name for p in root.iterdir()) != CORE_FILES | {'feed-capture'}:
        raise ValueError('completed source-scan inventory differs')
    manifest = _json(root / 'files.json')
    if manifest != {name: value for name, value in inventory.items() if name != 'files.json'}:
        raise ValueError('source-scan file bytes differ')
    state = probe.parse_sector_radar_market_state(probe._read(root / 'market-state.json').decode('utf-8'))
    selection, context = _json(root / 'selection.json'), _json(root / 'context.json')
    result, receipt = _evaluate(root / 'feed-capture', state, context, selection)
    if receipt is None:
        raise ValueError('blocked or prepared-only source scan is not acknowledged')
    expected = {'source-discovery.json': feed.data(result), 'scan-receipt.json': feed.data(receipt),
                'index.html': discovery.render_source_discovery(result).encode('utf-8')}
    if any(probe._read(root / name) != raw for name, raw in expected.items()):
        raise ValueError('source scan does not rebuild from original feed and market inputs')
    handoff = _json(root / 'handoff.json')
    if (canonical_hash({k:v for k,v in handoff.items() if k != 'handoff_hash'}) != handoff.get('handoff_hash')
            or handoff.get('new_scan_receipt') != receipt['receipt_hash']
            or handoff.get('status') != 'SOURCE_SCAN_COMPLETED'
            or handoff.get('consumer_scope_hash') != receipt['consumer_scope_hash']
            or handoff.get('source_capture_hash') != receipt['feed_capture_hash']
            or handoff.get('selected_source_records') != len(receipt['source_keys'])
            or handoff.get('source_delivery_acknowledged') is not False
            or handoff.get('network_calls') != 0
            or any(handoff.get(k) != v for k,v in probe.AUTHORITY.items())):
        raise ValueError('handoff does not identify the completed source scan')
    if as_of is not None and probe._clock(receipt['recorded_at']) > probe._clock(as_of):
        raise ValueError('consumer receipt is later than the requested cutoff')
    return {'receipt': receipt, 'result': result, 'verification': 'ORIGINAL_FEED_AND_SOURCE_SCAN_REBUILT',
            'network_calls': 0}


def _prior(root: Path, registry: dict, captured: dict, exports: dict, scope: dict, as_of: str):
    probe._safe_path(root)
    if not root.is_dir():
        raise ValueError('explicit receipt directory missing; no empty-store fallback')
    paths = sorted(root.iterdir())
    if sum(p.name != '.gitkeep' for p in paths) > MAX_RECEIPTS:
        raise ValueError('receipt capacity reached; explicit archive review required')
    prior, seen, done, outstanding = [], set(), set(), []
    all_versions = {v['version_hash'] for v in registry['versions']}
    qualified = {_source_key(row) for row in exports.get('sources', [])}
    for path in paths:
        probe._safe_path(path)
        if path.name == '.gitkeep' and path.is_file() and path.read_bytes() == b'':
            continue
        if not path.is_dir():
            raise ValueError('only complete scan bundles may be registered, not loose receipts')
        verified = verify_scan(path, as_of=as_of)
        receipt = verified['receipt']
        if (receipt['provenance'] != captured['provenance']
                or receipt['feed_initialized_at'] != registry['initialized_at']
                or not set(receipt['source_versions']) <= all_versions):
            raise ValueError('receipt belongs to another source observation chain')
        identity = receipt['receipt_hash']
        if identity in seen:
            continue
        seen.add(identity)
        applicable = receipt['consumer_scope'] == scope
        prior.append({'receipt_hash': identity, 'scope_matches': applicable})
        if applicable:
            if exports['status'] == 'READY_RETAINED_DESCRIPTIONS' and not set(receipt['source_keys']) <= qualified:
                raise ValueError('receipt source identity or first observation clocks differ')
            done.update(receipt['source_keys'])
        if receipt['acquisition_status'] == 'PLAN_NOT_EXECUTED':
            outstanding.append({'receipt_hash': identity, 'scope_matches': applicable,
                                'plan': verified['result']['acquisition_plan'],
                                'status': 'HISTORICAL_PLAN_NOT_ACKNOWLEDGED_AS_EXECUTED'})
    return sorted(prior, key=lambda r: r['receipt_hash']), done, outstanding


def scan(source: Path, state, context: dict, receipts: Path, output: Path, *, as_of: str, generated_at: str) -> dict:
    """Single-writer immutable output. Register completed bundles explicitly.

    Full upstream date/text/32-source guard runs BEFORE receipt suppression. This
    deliberately does not extend intake capacity or turn seen versions into acks.
    """
    for path in (source, receipts, output):
        probe._safe_path(path)
    if output.exists() or any(output.resolve().is_relative_to(p.resolve()) for p in (source, receipts)):
        raise ValueError('new output must be outside source and registered receipt directories')
    captured, registry, exports = _load_feed(source, as_of)
    inputs, scope = _context(state, context, captured['provenance'], as_of, generated_at)
    prior, done, outstanding = _prior(receipts, registry, captured, exports, scope, as_of)
    keys = sorted({_source_key(row) for row in exports.get('sources', [])} - done)
    selection = {'source_keys': keys, 'as_of': as_of, 'generated_at': generated_at}
    result = receipt = None
    if exports['status'] == 'SOURCE_EXPORT_BLOCKED':
        status = 'SOURCE_EXPORT_BLOCKED'
    elif not keys:
        status = 'BASELINE_NOT_FORWARDED' if exports['status'] == 'BASELINE_NOT_FORWARDED' else 'NO_PENDING_SOURCE_SCAN'
    else:
        result, receipt = _evaluate(source, state, context, selection)
        status = 'SOURCE_SCAN_COMPLETED' if receipt else 'SOURCE_SCAN_BLOCKED'
    handoff = {'schema_version': 1, 'semantics': SEMANTICS, 'status': status,
               'source_capture_hash': captured['capture_hash'], 'registry_hash': registry['registry_hash'],
               'consumer_scope_hash': canonical_hash(scope), 'as_of': as_of, 'generated_at': generated_at,
               'upstream_export_status': exports['status'], 'upstream_pending_versions': exports.get('pending_versions', 0),
               'already_scanned_source_records': len(done), 'selected_source_records': len(keys),
               'prior_scan_receipts': prior, 'unexecuted_prior_plans': outstanding,
               'gaps': exports.get('gaps', []), 'new_scan_receipt': receipt['receipt_hash'] if receipt else None,
               'source_delivery_acknowledged': False, 'network_calls': 0, **probe.AUTHORITY}
    handoff = feed._sealed(handoff, 'handoff_hash')
    original = _inventory(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.feed-consumer-', dir=output.parent) as tmp:
        stage = Path(tmp) / 'bundle'
        stage.mkdir()
        shutil.copytree(source, stage / 'feed-capture')
        if _inventory(stage / 'feed-capture') != original:
            raise ValueError('source changed while copying')
        contents = {'context.json': feed.data(context), 'market-state.json': probe.serialize_sector_radar_market_state(state).encode('utf-8'),
                    'selection.json': feed.data(selection), 'handoff.json': feed.data(handoff)}
        if result is not None:
            contents['source-discovery.json'] = feed.data(result)
            contents['index.html'] = discovery.render_source_discovery(result).encode('utf-8')
        else:
            contents['index.html'] = ('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'"><title>来源扫描交接</title>'
                '<h1>来源扫描交接</h1><p>没有新增可执行市场请求。扫描完成不等于行情计划已执行。</p>'
                '<p>历史未执行计划及来源缺口保留在下方；旧计划不能当作当前计划重新执行。</p>'
                '<pre style="white-space:pre-wrap;overflow-wrap:anywhere">' + escape(canonical_json(handoff)) + '</pre></html>').encode('utf-8')
        if receipt:
            contents['scan-receipt.json'] = feed.data(receipt)
        for name, raw in contents.items():
            (stage / name).write_bytes(raw)
        (stage / 'files.json').write_bytes(feed.data(_inventory(stage)))
        if receipt:
            verify_scan(stage)
        if output.exists():
            raise ValueError('output appeared during publication')
        stage.rename(output)
    return handoff


def main(argv=None):
    parser = argparse.ArgumentParser(description='Receipt-scoped native feed source scan; zero network or authority changes.')
    parser.add_argument('mode', choices=['scan', 'verify'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--feed-capture', type=Path)
    parser.add_argument('--market-state', type=Path)
    parser.add_argument('--context', type=Path)
    parser.add_argument('--receipts-dir', type=Path)
    parser.add_argument('--as-of')
    args = parser.parse_args(argv)
    try:
        if args.mode == 'verify':
            verified = verify_scan(args.output, as_of=args.as_of)
            print(canonical_json({'status': verified['verification'], 'receipt_hash': verified['receipt']['receipt_hash'], 'network_calls': 0}))
            return 0
        if any(x is None for x in (args.feed_capture, args.market_state, args.context, args.receipts_dir, args.as_of)):
            raise ValueError('all explicit feed, context, receipt and cutoff inputs required')
        state = probe.parse_sector_radar_market_state(probe._read(args.market_state).decode('utf-8'))
        result = scan(args.feed_capture, state, _json(args.context), args.receipts_dir, args.output,
                      as_of=args.as_of, generated_at=datetime.now(timezone.utc).isoformat())
        print(canonical_json(result))
        return 2 if result['status'] in {'SOURCE_EXPORT_BLOCKED', 'SOURCE_SCAN_BLOCKED'} else 0
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as exc:
        print(canonical_json({'status': 'SOURCE_CONSUMER_UNAVAILABLE', 'error_type': type(exc).__name__, 'network_calls': 0}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
