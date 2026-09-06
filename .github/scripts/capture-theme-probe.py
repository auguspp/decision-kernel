"""One bounded real-source trial around the existing offline theme probe.

Requests handles transport; existing adapters/plan/math own interpretation.
This script never calls the production producer or restores/writes its ledger.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import time
from datetime import datetime, timezone
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.adapters.hithink_index import normalize_hithink_industry_catalog
from decision_kernel.runtime import theme_radar_probe as probe
from decision_kernel.runtime.hithink_dump_trial import _session, _check_response, DumpTrialError
from decision_kernel.runtime.hithink_http import HITHINK_BASE_URL
from decision_kernel.runtime.sector_radar_audit import _check_request, _check_safe_json
from decision_kernel.runtime.sector_radar_persistence import load_sector_radar_committed_bootstrap
from decision_kernel.runtime.sector_radar_state import parse_sector_radar_market_state, serialize_sector_radar_market_state

LIVE = 'LIVE_HITHINK_BOUNDED_THEME_CAPTURE'
COMPLETE = 'COMPLETE_BOUNDED_THEME_CAPTURE'
FAILED = 'INCOMPLETE_THEME_CAPTURE'
LIMIT = 8 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
CATALOGS = [('concept_catalog', {'tag': 'cn_concept'}), ('industry_catalog', {'tag': 'industry'})]


def data(value):
    return (canonical_json(value) + '\n').encode('utf-8')


def decode(raw):
    value = json.loads(raw.decode('utf-8'), parse_float=Decimal, object_pairs_hook=probe._unique_object)
    _check_safe_json(value)
    canonical_json(value)  # Also refuse NaN, infinity and malformed number values.
    if not isinstance(value, dict):
        raise ValueError('provider JSON must be an object')
    return value


def digest(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def workflow_identity(env):
    if (env.get('GITHUB_REPOSITORY') != 'auguspp/decision-kernel'
            or env.get('GITHUB_REF') != 'refs/heads/main'
            or env.get('GITHUB_WORKFLOW') != 'hithink-stock-dump-trial'
            or env.get('GITHUB_EVENT_NAME') not in {'push', 'workflow_dispatch'}
            or env.get('GITHUB_RUN_ATTEMPT') != '1'
            or not re.fullmatch('[0-9a-f]{40}', env.get('GITHUB_SHA', ''))
            or not re.fullmatch('[1-9][0-9]{0,19}', env.get('GITHUB_RUN_ID', ''))):
        raise ValueError('requires reviewed main, canonical trial workflow and a fresh attempt')
    return {key: env[key] for key in ('GITHUB_REPOSITORY', 'GITHUB_WORKFLOW', 'GITHUB_REF',
            'GITHUB_EVENT_NAME', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_SHA')}


def validate_selection(selection):
    probe._keys(selection, {'schema_version', 'purpose', 'themes', 'industries'})
    if type(selection['schema_version']) is not int or selection['schema_version'] != 1:
        raise ValueError('unsupported sample selection')
    if not isinstance(selection['purpose'], str) or not selection['purpose'].strip():
        raise ValueError('sample purpose must be explicit')
    for key, maximum, minimum in (('themes', 3, 1), ('industries', 6, 0)):
        rows = selection[key]
        if not isinstance(rows, list) or not minimum <= len(rows) <= maximum:
            raise ValueError('sample budget exceeded; no truncation')
        seen = set()
        for row in rows:
            probe._keys(row, {'name', 'reason'} if key == 'themes' else {'thscode', 'name', 'reason'})
            if any(not isinstance(row[k], str) or not 1 <= len(row[k].strip()) <= 1600 for k in row):
                raise ValueError('sample names, identities and reasons must be explicit')
            if row['name'] in seen:
                raise ValueError('duplicate sample name')
            seen.add(row['name'])


def selected_plan(state, records, selection, planned_at):
    validate_selection(selection)
    catalog = normalize_hithink_industry_catalog(records['concept_catalog']['response'])
    themes = []
    for criterion in selection['themes']:
        matches = [i for i in catalog.identities if i.name == criterion['name']]
        if len(matches) != 1:
            raise ValueError('sample name must resolve uniquely in the captured catalog; no aliases or substitute')
        themes.append({'thscode': matches[0].thscode, **criterion})
    return probe.make_theme_plan(state, records['concept_catalog'], records['industry_catalog'],
        themes=themes, industries=selection['industries'], planned_at=planned_at)


def request_raw(path, params, *, api_key):
    """Thin raw-byte retention around the existing Requests session/status policy."""
    _check_request(path, params)
    with _session() as session:
        with session.get(HITHINK_BASE_URL + path, params=params,
                headers={'X-api-key': api_key, 'Accept': 'application/json', 'Accept-Encoding': 'identity'},
                timeout=(10, 20), stream=True, allow_redirects=False) as response:
            length = _check_response(response)
            if length is not None and length > LIMIT:
                raise ValueError('provider body exceeds byte budget')
            chunks, size = [], 0
            for chunk in response.iter_content(chunk_size=65536):
                size += len(chunk)
                if size > LIMIT:
                    raise ValueError('provider body exceeds byte budget')
                chunks.append(chunk)
            if length is not None and length != size:
                raise ValueError('provider body length mismatch')
            return b''.join(chunks)


def capture_trial(state, selection, output, *, context, api_key, transport=None,
                  now=lambda: datetime.now(timezone.utc), pause=time.sleep):
    validate_selection(selection)
    state_raw = serialize_sector_radar_market_state(state).encode('utf-8')
    state = parse_sector_radar_market_state(state_raw.decode())
    started = now(); probe._window(state, started)
    if not api_key:
        raise ValueError('provider credential is not configured')
    probe._safe_path(output)
    output.mkdir(parents=True, exist_ok=False)
    provenance = LIVE if transport is None else probe.SYNTHETIC
    transport = transport or (lambda path, params: request_raw(path, params, api_key=api_key))
    saved, requests, records = {}, [], {}
    report = {'schema_version': 1, 'semantics': 'ISOLATED_CAPTURE_NOT_PRODUCER_RESTORE_OR_SIGNAL',
        'provenance': provenance, 'workflow': context, 'started_at': started.isoformat(),
        'market_state_hash': state.state_hash, 'market_session': state.sessions[-1].isoformat(),
        'selection_hash': canonical_hash(selection), 'planned_at': None, 'as_of': None,
        'status': FAILED, 'failure': None, 'requests': requests, 'files': saved,
        'maximum_request_count': 15, 'pacing_seconds': 20, 'retention_days': 90,
        'runtime': {'python': platform.python_version(), 'requests': version('requests')}, **probe.AUTHORITY}

    def save(name, raw):
        if name in saved or len(raw) > LIMIT or sum(i['bytes'] for i in saved.values()) + len(raw) > MAX_TOTAL:
            raise ValueError('duplicate file or capture byte budget exceeded')
        if api_key.encode() in raw:
            raise ValueError('credential echo cannot enter retained evidence')
        path = output / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw); saved[name] = digest(raw)

    def acquire(key, path, params):
        if len(requests) >= 15:
            raise ValueError('request count exceeds frozen budget')
        if requests:
            pause(20)
        entry = {'id': key, 'path': path, 'params': dict(params), 'requested_at': now().isoformat(),
                 'received_at': None, 'response_file': None, 'http_status': None, 'error_type': None}
        requests.append(entry)
        try:
            raw = transport(path, params)
            entry['received_at'] = now().isoformat()
            entry['http_status'] = 200
            if not isinstance(raw, bytes) or len(raw) > LIMIT:
                raise ValueError('transport must return bounded original bytes')
            body = decode(raw); _check_safe_json(body, api_key)
            name = f'responses/{len(requests):02d}.json'
            save(name, raw)
            entry.update(response_file=name, http_status=200)
            records[key] = {k: entry[k] for k in ('path', 'params', 'requested_at', 'received_at')}
            records[key]['response'] = body
        except (OSError, ValueError, RuntimeError) as exc:
            entry['received_at'] = entry['received_at'] or now().isoformat()
            entry['error_type'] = type(exc).__name__
            if isinstance(exc, DumpTrialError):
                entry['http_status'] = exc.http_status
            raise

    try:
        save('market-state.json', state_raw); save('selection.json', data(selection))
        for key, params in CATALOGS:
            acquire(key, probe.CATALOG, params)
        planned = now().isoformat(); report['planned_at'] = planned
        plan = selected_plan(state, records, selection, planned)
        save('plan.json', data(plan))  # Plan exists BEFORE the first quote/history/member request.
        for item in plan['requests']:
            acquire(item['id'], item['path'], item['params'])
        cutoff = now().isoformat(); report['as_of'] = cutoff
        inputs = {'schema_version': 1, 'provenance': probe.SUPPLIED if provenance == LIVE else probe.SYNTHETIC,
            'plan': plan, 'concept_catalog': records['concept_catalog'], 'industry_catalog': records['industry_catalog'],
            'captures': {item['id']: records[item['id']] for item in plan['requests']}}
        save('supplied-input.json', data(inputs))
        result = probe.build_theme_probe(state, inputs, as_of=cutoff, generated_at=now().isoformat())
        save('theme-probe.json', data(result)); save('index.html', probe.render_theme_probe(result).encode())
        report['status'] = COMPLETE
    except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
        message = ' '.join(str(exc).replace(api_key, '[REDACTED]').split())[:500]
        report['failure'] = {'type': type(exc).__name__, 'message': message}
    report['finished_at'] = now().isoformat()
    report['requests_attempted'] = len(requests)
    report['capture_hash'] = canonical_hash(report)
    (output / 'capture.json').write_bytes(data(report))
    return report


def verify_capture(root):
    """No network. Byte integrity for failures; full original-response rebuild for success."""
    probe._safe_path(root)
    report = decode(probe._read(root / 'capture.json'))
    if canonical_hash({k: v for k, v in report.items() if k != 'capture_hash'}) != report['capture_hash']:
        raise ValueError('capture manifest hash mismatch')
    if any(report[k] != v for k, v in probe.AUTHORITY.items()) or report['provenance'] not in {LIVE, probe.SYNTHETIC}:
        raise ValueError('invalid capture provenance or authority')
    expected = {'capture.json', *report['files']}
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if not p.is_dir()}
    if actual != expected:
        raise ValueError('capture file inventory differs')
    for name, expected_hash in report['files'].items():
        if not re.fullmatch(r'(?:responses/[0-9]{2}\.json|market-state\.json|selection\.json|plan\.json|supplied-input\.json|theme-probe\.json|index\.html)', name):
            raise ValueError('unsafe capture path')
        if digest(probe._read(root / name)) != expected_hash:
            raise ValueError('captured byte identity differs')
    state = parse_sector_radar_market_state(probe._read(root / 'market-state.json').decode())
    selection = decode(probe._read(root / 'selection.json')); validate_selection(selection)
    if state.state_hash != report['market_state_hash'] or canonical_hash(selection) != report['selection_hash']:
        raise ValueError('state or selection identity differs')
    entries = report['requests']; records = {}
    if len(entries) != report['requests_attempted'] or not 0 <= len(entries) <= 15:
        raise ValueError('invalid captured request count')
    for i, entry in enumerate(entries):
        if entry['response_file'] is not None:
            if entry['response_file'] != f'responses/{i+1:02d}.json' or entry['id'] in records:
                raise ValueError('response identity differs')
            records[entry['id']] = {k: entry[k] for k in ('path', 'params', 'requested_at', 'received_at')}
            records[entry['id']]['response'] = decode(probe._read(root / entry['response_file']))
    verified = 'RETAINED_BYTES_ONLY_INCOMPLETE_CAPTURE'
    if report['status'] == COMPLETE:
        plan = selected_plan(state, records, selection, report['planned_at'])
        if data(plan) != probe._read(root / 'plan.json'):
            raise ValueError('frozen plan differs from captured catalogs and selection')
        slots = [{'id': k, 'path': probe.CATALOG, 'params': v} for k, v in CATALOGS] + plan['requests']
        if len(slots) != len(entries) or any(any(a[k] != b[k] for k in ('id', 'path', 'params')) for a, b in zip(slots, entries)):
            raise ValueError('executed requests differ from plan')
        inputs = {'schema_version': 1, 'provenance': probe.SUPPLIED if report['provenance'] == LIVE else probe.SYNTHETIC,
            'plan': plan, 'concept_catalog': records['concept_catalog'], 'industry_catalog': records['industry_catalog'],
            'captures': {item['id']: records[item['id']] for item in plan['requests']}}
        if data(inputs) != probe._read(root / 'supplied-input.json'):
            raise ValueError('normalized inputs differ from original response bytes')
        original = decode(probe._read(root / 'theme-probe.json'))
        rebuilt = probe.build_theme_probe(state, inputs, as_of=report['as_of'], generated_at=original['generated_at'])
        if data(rebuilt) != probe._read(root / 'theme-probe.json') or probe.render_theme_probe(rebuilt).encode() != probe._read(root / 'index.html'):
            raise ValueError('offline theme projection differs')
        verified = 'ORIGINAL_RESPONSES_PLAN_AND_PAGE_REBUILT'
    elif report['status'] != FAILED:
        raise ValueError('unknown capture result')
    return {'status': verified, 'capture_status': report['status'], 'capture_hash': report['capture_hash'],
            'network_calls': 0, **probe.AUTHORITY}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Bounded real theme trial, not a Sector producer.')
    parser.add_argument('mode', choices=['capture', 'verify'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--selection', type=Path, default=Path('radar_inputs/theme-probe-sample-v0.json'))
    args = parser.parse_args(argv)
    try:
        if args.mode == 'verify':
            if os.environ.get('HITHINK_FINANCE_API_KEY'):
                raise ValueError('offline verification must not receive a market credential')
            print(canonical_json(verify_capture(args.output)))
            return 0
        context = workflow_identity(os.environ)
        now = datetime.now(timezone.utc)
        base = Path('radar_inputs/sector-radar-state-bootstrap-2026-09-04')
        # Read a frozen comparison state, not the producer's restore selection or event history.
        state = load_sector_radar_committed_bootstrap(bootstrap_path=base.with_suffix('.json.gz'),
            bootstrap_manifest_path=base.with_suffix('.manifest.json'), ledger_created_at=now).market_state
        raw_selection = probe._read(args.selection)
        if args.output.resolve().is_relative_to(args.selection.resolve().parent):
            raise ValueError('capture output must be outside selection inputs')
        report = capture_trial(state, decode(raw_selection), args.output, context=context,
                               api_key=os.environ.get('HITHINK_FINANCE_API_KEY', ''))
        print(canonical_json({'status': report['status'], 'requests_attempted': report['requests_attempted'],
                             'failure': report['failure'], **probe.AUTHORITY}))
        return 0 if report['status'] == COMPLETE else 2
    except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
        print('Theme capture unavailable:', type(exc).__name__)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
