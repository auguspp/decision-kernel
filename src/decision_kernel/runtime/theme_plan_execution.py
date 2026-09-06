"""Execute/rebuild one exact source-scan plan with the existing market probe.

Transport is supplied by the workflow adapter (the existing Requests collector).
A rebuilt raw capture proves this stage, not remote publication or Human delivery.
"""
from __future__ import annotations

import json
import re
import shutil
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from decision_kernel.identity import canonical_hash
from . import radar_feed_consumer as consumer
from . import radar_feed_intake as feed
from . import theme_radar_probe as probe
from .sector_radar_audit import _check_safe_json

VERSION = 'source-scan-exact-market-plan-execution-v1'
LIVE = 'PUBLIC_HTTP_CAPTURE_CLAIM_NOT_REMOTE_PUBLICATION'
COMPLETE = 'COMPLETE_EXACT_PLAN_CAPTURE'
FAILED = 'INCOMPLETE_EXACT_PLAN_CAPTURE'


def _decode(raw, credential=None):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= probe.MAX_INPUT_BYTES:
        raise ValueError('bounded original market response bytes required')
    value = json.loads(raw.decode('utf-8'), parse_float=Decimal, object_pairs_hook=probe._unique_object)
    if not isinstance(value, dict):
        raise ValueError('market response must be an object')
    _check_safe_json(value, credential)  # Inspect decoded keys/values before saving original bytes.
    feed.data(value)  # Reject nonfinite values before they reach market adapters.
    return value


def _execution_clock(state, plan, at):
    current = probe._clock(at)
    probe._window(state, current)
    # Same exact-plan lifetime already enforced by build_theme_probe; reject
    # before transport rather than waiting until the final market calculation.
    planned = probe._clock(plan['planned_at'])
    if current < planned or current - planned > timedelta(minutes=30):
        raise ValueError('exact plan is outside the existing 30-minute capture window')
    return current


def _identity(root, *, at):
    scan = consumer.verify_scan(root, as_of=at)
    plan = scan['result']['acquisition_plan']
    if plan is None:
        raise ValueError('no market plan from this source scan')
    state = probe.parse_sector_radar_market_state(probe._read(root / 'market-state.json').decode())
    _execution_clock(state, plan, at)  # Neither market-day nor plan-age limits are refreshed.
    return scan, plan, state, consumer._json(root / 'context.json')


def _workflow(context):
    if (context.get('GITHUB_REPOSITORY') != 'auguspp/decision-kernel'
            or context.get('GITHUB_REF') != 'refs/heads/main'
            or context.get('GITHUB_WORKFLOW') != 'hithink-stock-dump-trial'
            or context.get('GITHUB_EVENT_NAME') not in {'push', 'workflow_dispatch'}
            or context.get('GITHUB_RUN_ATTEMPT') != '1'
            or not re.fullmatch('[0-9a-f]{40}', context.get('GITHUB_SHA', ''))
            or not re.fullmatch('[1-9][0-9]{0,19}', context.get('GITHUB_RUN_ID', ''))):
        raise ValueError('canonical fresh workflow identity required for public capture claim')


def capture_plan(scan_root: Path, output: Path, *, transport, context=None,
                 public_http=False, credential='', now=lambda: datetime.now(timezone.utc), pause=time.sleep):
    """No retry/fallback; the wrapper reuses its existing bounded HTTP transport."""
    started = now().isoformat()
    scan, plan, state, context_inputs = _identity(scan_root, at=started)
    if type(public_http) is not bool:
        raise ValueError('explicit transport provenance required')
    if public_http:
        _workflow(context or {})
        if scan['receipt']['provenance'] != 'PUBLIC_HTTP_CAPTURE' or not credential:
            raise ValueError('synthetic scan or missing credential cannot enter a live capture')
    elif scan['receipt']['provenance'] != probe.SYNTHETIC:
        raise ValueError('synthetic execution cannot acknowledge a public source scan')
    for path in (scan_root, output):
        probe._safe_path(path)
    if output.exists() or output.resolve().is_relative_to(scan_root.resolve()):
        raise ValueError('new execution output must be outside source-scan inputs')
    output.mkdir(parents=True)
    saved, requests, captures = {}, [], {}
    report = {'version': VERSION, 'status': FAILED, 'provenance': LIVE if public_http else probe.SYNTHETIC,
              'workflow': context or {}, 'scan_receipt_hash': scan['receipt']['receipt_hash'],
              'plan_hash': canonical_hash(plan), 'started_at': started, 'finished_at': None,
              'as_of': None, 'failure': None, 'requests': requests, 'files': saved,
              'catalog_requests_executed': 0, 'catalogs_reused_from_scan': True,
              'source_delivery_acknowledged': False, 'publication_verified': False, **probe.AUTHORITY}

    def save(name, raw):
        if credential and credential.encode() in raw:
            raise ValueError('credential echo cannot be retained')
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if (name in saved or len(raw) > probe.MAX_INPUT_BYTES
                or sum(v['bytes'] for v in saved.values()) + len(raw) > consumer.MAX_BUNDLE_BYTES):
            raise ValueError('execution byte budget exceeded')
        path.write_bytes(raw); saved[name] = feed.digest(raw)

    try:
        original = consumer._inventory(scan_root)
        for name in original:
            save('source-scan/' + name, probe._read(scan_root / name))
        if consumer._inventory(output / 'source-scan') != original:
            raise ValueError('source scan changed during capture preparation')
        copied, copied_plan, _, _ = _identity(output / 'source-scan', at=started)
        if copied['receipt'] != scan['receipt'] or copied_plan != plan:
            raise ValueError('copied source scan identity differs')
        save('plan.json', feed.data(plan))  # Written before the FIRST detail request.
        last_response = probe._clock(started)
        for i, slot in enumerate(plan['requests'], 1):
            pause(20)  # Also pace the first detail after the previously supplied catalogs.
            requested = now().isoformat()
            request_clock = _execution_clock(state, plan, requested)
            if request_clock < last_response:
                raise ValueError('request clock precedes the previous execution boundary')
            entry = {**slot, 'requested_at': requested, 'received_at': None,
                     'response_file': None, 'http_status': None, 'error_type': None}
            requests.append(entry)
            try:
                raw = transport(slot['path'], slot['params'])
                entry['received_at'] = now().isoformat()
                received_clock = _execution_clock(state, plan, entry['received_at'])
                if received_clock < request_clock:
                    raise ValueError('response clock precedes the request')
                body = _decode(raw, credential)
                name = f'responses/{i:02d}.json'; save(name, raw)
                entry.update(response_file=name, http_status=200)
                captures[slot['id']] = {k: entry[k] for k in ('path', 'params', 'requested_at', 'received_at')}
                captures[slot['id']]['response'] = body
                last_response = received_clock
            except (ValueError, OSError, RuntimeError) as exc:
                entry['received_at'] = entry['received_at'] or now().isoformat()
                entry['error_type'] = type(exc).__name__
                status = getattr(exc, 'http_status', None)
                if type(status) is int:
                    entry['http_status'] = status
                raise
        report['as_of'] = now().isoformat()
        inputs = {'schema_version': 1, 'provenance': probe.SUPPLIED if public_http else probe.SYNTHETIC,
                  'plan': plan, 'captures': captures,
                  **{k: context_inputs[k] for k in ('concept_catalog', 'industry_catalog')}}
        save('supplied-input.json', feed.data(inputs))
        result = probe.build_theme_probe(state, inputs, as_of=report['as_of'], generated_at=now().isoformat())
        save('theme-probe.json', feed.data(result)); save('index.html', probe.render_theme_probe(result).encode())
        report['status'] = COMPLETE
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as exc:
        report['failure'] = {'type': type(exc).__name__}  # No secret-bearing exception text.
        for name in ('theme-probe.json', 'index.html'):
            (output / name).unlink(missing_ok=True); saved.pop(name, None)
    report['finished_at'] = now().isoformat()
    report = feed._sealed(report, 'execution_hash')
    (output / 'execution.json').write_bytes(feed.data(report))
    return report


def verify_execution(root: Path, *, as_of: str | None = None):
    """Rebuild exact plan and result from raw responses; no trust in a loose ack."""
    inventory = consumer._inventory(root, maximum_files=64)
    report = consumer._json(root / 'execution.json')
    if (report['version'] != VERSION
            or canonical_hash({k:v for k,v in report.items() if k != 'execution_hash'}) != report['execution_hash']
            or report['files'] != {k:v for k,v in inventory.items() if k != 'execution.json'}
            or any(report.get(k) != v for k,v in probe.AUTHORITY.items())
            or report.get('source_delivery_acknowledged') is not False
            or report.get('publication_verified') is not False
            or report.get('catalog_requests_executed') != 0 or report.get('catalogs_reused_from_scan') is not True):
        raise ValueError('execution identity, inventory or authority differs')
    allowed = {'execution.json', 'source-scan', 'plan.json', 'responses', 'supplied-input.json', 'theme-probe.json', 'index.html'}
    if not {p.name for p in root.iterdir()} <= allowed:
        raise ValueError('unknown execution files')
    scan, plan, state, context = _identity(root / 'source-scan', at=report['started_at'])
    if (report['scan_receipt_hash'] != scan['receipt']['receipt_hash']
            or report['plan_hash'] != canonical_hash(plan) or probe._read(root / 'plan.json') != feed.data(plan)):
        raise ValueError('execution does not belong to the exact source-scan plan')
    if report['provenance'] == LIVE:
        _workflow(report['workflow'])
        if scan['receipt']['provenance'] != 'PUBLIC_HTTP_CAPTURE':
            raise ValueError('synthetic source cannot become public execution')
    elif report['provenance'] != probe.SYNTHETIC or scan['receipt']['provenance'] != probe.SYNTHETIC:
        raise ValueError('unknown or mixed source/execution provenance')
    finished = probe._clock(report['finished_at'])
    last = probe._clock(report['started_at'])
    if last > finished or (as_of is not None and finished > probe._clock(as_of)):
        raise ValueError('execution is later than cutoff or clocks reverse')
    entries, captures = report['requests'], {}
    if not isinstance(entries, list) or len(entries) > len(plan['requests']):
        raise ValueError('execution request budget differs')
    response_paths = set()
    for i, (slot, entry) in enumerate(zip(plan['requests'], entries), 1):
        if any(entry[k] != slot[k] for k in ('id', 'path', 'params')):
            raise ValueError('request sequence differs from exact plan')
        start, end = probe._clock(entry['requested_at']), probe._clock(entry['received_at'])
        if not last <= start <= end <= finished:
            raise ValueError('request clocks outside execution boundary')
        last = end
        if entry['response_file'] is not None:
            name = f'responses/{i:02d}.json'
            if entry['response_file'] != name or entry['http_status'] != 200 or entry['error_type'] is not None:
                raise ValueError('saved response identity differs')
            response_paths.add(name)
            captures[slot['id']] = {k:entry[k] for k in ('path', 'params', 'requested_at', 'received_at')}
            captures[slot['id']]['response'] = _decode(probe._read(root / name))
    if {k for k in inventory if k.startswith('responses/')} != response_paths:
        raise ValueError('extra or missing response files')
    succeeded = report['status'] == COMPLETE
    if succeeded:
        if (report['failure'] is not None or len(captures) != len(plan['requests'])
                or any(e['error_type'] is not None for e in entries)
                or not last <= probe._clock(report['as_of']) <= finished):
            raise ValueError('incomplete or failed acquisition cannot be confirmed')
        probe._window(state, finished)
        inputs = {'schema_version': 1, 'provenance': probe.SUPPLIED if report['provenance'] == LIVE else probe.SYNTHETIC,
                  'plan': plan, 'captures': captures,
                  **{k:context[k] for k in ('concept_catalog', 'industry_catalog')}}
        original = _decode(probe._read(root / 'theme-probe.json'))
        if probe._clock(original['generated_at']) > finished:
            raise ValueError('result generation follows execution finish')
        rebuilt = probe.build_theme_probe(state, inputs, as_of=report['as_of'], generated_at=original['generated_at'])
        expected = {'supplied-input.json': feed.data(inputs), 'theme-probe.json': feed.data(rebuilt),
                    'index.html': probe.render_theme_probe(rebuilt).encode()}
        if any(probe._read(root / name) != raw for name, raw in expected.items()):
            raise ValueError('market result does not rebuild from original responses')
    elif report['status'] != FAILED or report['failure'] is None or {'theme-probe.json', 'index.html'} & inventory.keys():
        raise ValueError('invalid incomplete execution status')
    return {'status': 'EXACT_SOURCE_PLAN_AND_MARKET_REBUILT' if succeeded else 'INCOMPLETE_ATTEMPT_NOT_ACKNOWLEDGED',
            'execution_hash': report['execution_hash'], 'scan_receipt_hash': scan['receipt']['receipt_hash'],
            'plan_hash': canonical_hash(plan), 'market_stage_succeeded': succeeded,
            'finished_at': report['finished_at'], 'source_delivery_acknowledged': False,
            'publication_verified': False, 'network_calls': 0, **probe.AUTHORITY}
