"""Manual K3 independent Stock capture using the admitted HiThink owner.

REUSE + THIN_ADAPTER. No Sector inputs/state, retries, successor, or admission to
legacy Stock/Research. The original retained-audit build remains a separate API.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from decimal import Context, localcontext
import os
from pathlib import Path
import re
import time

from decision_kernel.adapters.hithink import normalize_hithink_calendar
from decision_kernel.identity import canonical_hash, canonical_json
from . import independent_stock_observations as independent
from . import hithink_stock_reading as own
from . import stock_radar_reading as stock
from . import sector_radar_audit as audit
from .research_commit_only import _safe_path

PURPOSE = 'stock-independent-observations'
VERSION = 'hithink-independent-stock-capture-v1'
COMPLETE = 'COMPLETED_INDEPENDENT_OBSERVATIONS_WITH_EXPLICIT_GAPS'
FAILED = 'INCOMPLETE_INDEPENDENT_CAPTURE_NO_SCAN_CLAIM'
SAMPLE_SIZE, PAGE_SIZE, MAX_REQUESTS = 3, 500, stock.MAX_REQUESTS
PUBLIC, SYNTHETIC = 'LIVE_HITHINK', 'SYNTHETIC_TEST_ONLY'
# Reviewed official notice facts, not a URL-shaped automatic holiday exception.
# The body was read 2026-10-01; the page displays 2026-09-17, despite its URL date.
CLOSURE_EVIDENCE = {
    'source_url': 'https://www.sse.com.cn/disclosure/announcement/general/c/c_20260915_10832273.shtml',
    'issuer': 'Shanghai Stock Exchange', 'notice_number': '上证公告〔2026〕22号',
    'published_date': '2026-09-17', 'reviewed_at': '2026-10-01T02:35:15+00:00',
    'evidence_kind': 'REVIEWED_NOTICE_FACTS_NOT_ORIGINAL_HTML_CUSTODY',
    'notice_facts': {'closure_start': '2026-10-01', 'closure_end': '2026-10-07',
                     'resumption_date': '2026-10-08'},
    'bounded_application': {'capture_date': '2026-10-01', 'comparison_session': '2026-09-30',
                            'closed_dates': ['2026-10-01']},
    'semantics': 'EXPLICIT_CLOSURE_CAPTURE_NOT_NATURALLY_QUIET_ACTIVE_DAY',
}


class CaptureFailure(ValueError):
    """Static safe diagnostic, never copied provider text or credentials."""


def _require(ok, reason):
    if not ok:
        raise CaptureFailure(reason)


def _bytes(value):
    return (canonical_json(value) + '\n').encode()


def _implementation():
    return {**audit._implementation(), **{
        'runtime/' + Path(module.__file__).name: audit._sha(Path(module.__file__).read_bytes())
        for module in (own, independent)},
        'runtime/hithink_independent_capture.py': audit._sha(Path(__file__).read_bytes())}


def intent(env):
    keys = ('GITHUB_REPOSITORY', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_SHA',
            'GITHUB_REF', 'GITHUB_EVENT_NAME', 'GITHUB_WORKFLOW_REF', 'GITHUB_JOB')
    value = {key: env.get(key) for key in keys}
    _require(value['GITHUB_REPOSITORY'] == 'auguspp/decision-kernel'
        and value['GITHUB_EVENT_NAME'] == 'workflow_dispatch'
        and value['GITHUB_REF'] == 'refs/heads/main' and value['GITHUB_RUN_ATTEMPT'] == '1'
        and isinstance(value['GITHUB_RUN_ID'], str) and re.fullmatch(r'[1-9][0-9]*', value['GITHUB_RUN_ID'])
        and isinstance(value['GITHUB_SHA'], str) and re.fullmatch(r'[0-9a-f]{40}', value['GITHUB_SHA'])
        and value['GITHUB_WORKFLOW_REF'] == 'auguspp/decision-kernel/.github/workflows/hithink-stock-dump-trial.yml@refs/heads/main'
        and value['GITHUB_JOB'] == PURPOSE and env.get('TRIAL_PURPOSE') == PURPOSE,
        'EXACT_MAIN_MANUAL_FIRST_ATTEMPT_IDENTITY_REQUIRED')
    _require(not env.get('STOCK_MARKET_RUN_ID') and not env.get('STOCK_DISCOVERY_PAGE')
             and not env.get('RECOVERY_KEY'), 'INDEPENDENT_CAPTURE_REJECTS_SECTOR_PAGE_OR_RECOVERY_INPUT')
    return {**value, 'trial_purpose': PURPOSE}


def _closures(closure_date, observed_at):
    _require(closure_date in (None, '2026-10-01'), 'UNREVIEWED_CLOSURE_DATE')
    if closure_date is None:
        return (), ()
    _require(observed_at.astimezone(stock.SHANGHAI_TZ).date() == date(2026, 10, 1),
             'CLOSURE_EVIDENCE_OUTSIDE_EXACT_CAPTURE_DATE')
    return (date(2026, 10, 1),), (CLOSURE_EVIDENCE['source_url'],)


def _input_pin(source, records):
    names = {'inputs/context.json'} | {r['response_file'] for r in records}
    if 'inputs/closure-evidence.json' in source['files']:
        names.add('inputs/closure-evidence.json')
    return canonical_hash({'workflow': source['workflow'], 'requests': records,
        'files': {name: source['files'][name] for name in sorted(names)}})


def _run(root, source, request, received, freeze):
    """Same ordered acquisition/replay; all parsing and price arithmetic reused."""
    calendar = normalize_hithink_calendar(request(independent.HITHINK_CALENDAR_PATH, {}))
    independent.indices.fetch_hithink_index_snapshot_batch(thscodes=('000300.SH',),
        api_key='EXPLICIT_TRANSPORT', request_json=request)
    independent.indices.fetch_hithink_completed_index_history(thscode='000300.SH',
        observed_at=received(), api_key='EXPLICIT_TRANSPORT', request_json=request,
        trading_sessions=calendar)
    closures, evidence = _closures(source['closure_date'], audit._clock(source['observed_at']))
    context_source = {**source, 'requests': source['requests'][:3], 'run_clocks': [received().isoformat()]}
    reference, sessions, context = independent._source_context(root, context_source,
        closed_dates=closures, closure_evidence=evidence)
    if closures:
        _require(reference.market_session == date(2026, 9, 30), 'CLOSURE_COMPARISON_SESSION_DIFFERS')
    snapshot_record = source['requests'][1]
    snapshot_body = independent._load_bound(root, snapshot_record['response_file'], source['files'])
    reference.validate_ready_time(snapshot_body['data']['timestamp'],
        received_at=audit._clock(snapshot_record['received_at']))
    locations, pages = {}, []

    def page_request(path, params):
        envelope = request(path, params)
        data = envelope.get('data')
        total = data.get('total') if isinstance(data, dict) else None
        # Reserve all K3 traces as soon as the first page declares a denominator.
        # A failure consumes an attempt; no retry, truncation, or smaller K fallback.
        if not pages:
            _require(type(total) is int and total > 0, 'EXACT_POSITIVE_FULL_MARKET_TOTAL_REQUIRED')
            _require(3 + (total + PAGE_SIZE - 1) // PAGE_SIZE + 3 * SAMPLE_SIZE <= MAX_REQUESTS,
                     'FULL_MARKET_AND_FROZEN_K3_EXCEED_EXISTING_26_REQUEST_BUDGET')
        record = source['requests'][3 + len(pages)]
        for index, row in enumerate(data.get('item', []) if isinstance(data, dict) else []):
            if isinstance(row, dict):
                locations[str(row.get('thscode', '')).strip().upper()] = [len(pages), index]
        pages.append(independent._descriptor(root, record, source))
        return envelope

    batch = independent.quotes.fetch_hithink_all_market_snapshot(market_session=reference.market_session,
        api_key='EXPLICIT_TRANSPORT', request_json=page_request, page_size=PAGE_SIZE,
        reference_context=reference, received_at=received)
    priced, selected, rows, selection = independent._sample(batch, locations, SAMPLE_SIZE,
        _input_pin(source, source['requests'][:3 + batch.page_count]), source_key='source_input_hash')
    _require(len(selected) == SAMPLE_SIZE, 'FULL_K3_PRICED_SAMPLE_UNAVAILABLE_NO_SMALLER_K_FALLBACK')
    freeze(selection)
    traces, results = {}, {}
    for code in selected:
        traces[code] = []
        for path, params in ((own.HISTORY, own.history_params(code, sessions)),
                             (own.SNAPSHOT, {'thscodes': code}),
                             (own.ACTIONS, own.action_params(code, sessions))):
            request(path, params)
            reference.validate_received_at(received())
            # The recorder/replayer returns the index of the last consumed request.
            records = source['requests']
            trace_index = 3 + batch.page_count + sum(len(items) for items in traces.values())
            traces[code].append(records[trace_index])
            with localcontext(Context(prec=28)):
                results[code] = independent._trace(root, source, traces[code], code, sessions)
            if results[code]['status'] not in {'UNKNOWN', 'CONTRACT_CHECKED_RAW_READING'}:
                break  # Only the old explicitly isolatable issuer failures reach here.
    return context, batch, pages, priced, selected, rows, selection, traces, results


def _assemble(source, parts):
    context, batch, pages, priced, selected, rows, selection, traces, results = parts
    report = independent._report(source, None, source['capture_hash'], context, batch,
        pages, priced, selected, rows, selection, {}, results)
    report.pop('source_audit_hash')
    report.pop('network_calls')
    report.pop('new_source_requests')
    report.update(version='independent-stock-captured-observations-v1', status=COMPLETE,
        semantics='UNVALIDATED_INDEPENDENT_SAMPLE_NOT_SURPRISE_RANKING_OR_PRODUCTION_GATE',
        source_validation='EXACT_MANUAL_CAPTURE_INVENTORY_AND_ORDERED_OFFLINE_REPLAY',
        source_custody='CAPTURE_ARTIFACT_REQUIRED_NOT_PERMANENT_GIT_CUSTODY',
        source_request_attempts=len(source['requests']), report_generation_network_calls=0,
        request_ceiling=MAX_REQUESTS, sample_size=SAMPLE_SIZE,
        coverage={**report['coverage'], 'selected_with_supplied_history': len(traces)},
        replay_controls={'origin': 'NONE_NO_SECTOR_SELECTED_CONTROL_INPUT', 'rows': []},
        quiet_sector_live_acquisition='NOT_ESTABLISHED_NO_SECTOR_QUIETNESS_OBSERVATION')
    report['report_hash'] = canonical_hash({k: v for k, v in report.items() if k != 'report_hash'})
    return report


def render(report):
    c = report['coverage']
    return (f"Independent observations: {c['unique_identities']} identities / {c['complete_pages']} complete pages\n"
        f"Frozen K3: {c['independently_selected']}; qualified: {c['selected_qualified']}; source attempts: {report['source_request_attempts']}/26\n"
        'Absolute signed-move sampling is unvalidated; this is not Surprise or investment priority.\n'
        'Selection preceded own-history acquisition. Missing/failed inputs remain explicit.\n'
        'Source clocks are actual receipt/readiness clocks, not per-security trading-date proof.\n'
        'No Sector state, membership, association, production admission, Research or investment authority.\n'
        'A holiday capture is not naturally quiet active-day evidence. Discovery value and later use remain unproved.\n')


def capture(output, *, observed_at, transport, workflow, provenance=SYNTHETIC,
            credential='', closure_date=None, now=lambda: datetime.now(timezone.utc), pause=time.sleep):
    output = Path(output)
    _safe_path(output)
    _require(not output.exists(), 'CREATE_ONLY_OUTPUT_REQUIRED')
    _require(provenance in {PUBLIC, SYNTHETIC} and (provenance != PUBLIC or credential),
             'EXPLICIT_LIVE_CREDENTIAL_OR_SYNTHETIC_PROVENANCE_REQUIRED')
    audit._check_safe_json(workflow, credential or None)
    if provenance == PUBLIC:
        _require(workflow == intent({**workflow, 'TRIAL_PURPOSE': workflow.get('trial_purpose')}),
                 'WORKFLOW_IDENTITY_FIELDS_DIFFER')
    at = audit._clock(observed_at.isoformat())
    _closures(closure_date, at)
    output.mkdir(parents=True)
    source = {'version': VERSION, 'purpose': PURPOSE, 'status': FAILED,
        'observed_at': at.isoformat(), 'finished_at': None, 'workflow': workflow,
        'provenance': provenance, 'closure_date': closure_date,
        'response_semantics': 'DECODED_PROVIDER_JSON_NOT_ORIGINAL_HTTP_BYTES',
        'request_ceiling': MAX_REQUESTS, 'sample_size': SAMPLE_SIZE, 'page_size': PAGE_SIZE,
        'implementation': _implementation(), 'requests': [], 'files': {}, 'selection_hash': None,
        'failure_reason': None, 'remote_upload_verified': False, **stock.LIMITS}
    last, total_bytes = at, 0

    def save(name, raw):
        nonlocal total_bytes
        _require(len(raw) <= audit.MAX_FILE_BYTES and total_bytes + len(raw) <= audit.MAX_AUDIT_BYTES,
                 'CAPTURE_BYTE_BUDGET_EXCEEDED')
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
        source['files'][name] = {'bytes': len(raw), 'sha256': audit._sha(raw)}
        total_bytes += len(raw)

    save('inputs/context.json', _bytes({'observed_at': at.isoformat()}))
    if closure_date:
        save('inputs/closure-evidence.json', _bytes(CLOSURE_EVIDENCE))

    def clock():
        nonlocal last
        value = now()
        _require(isinstance(value, datetime) and value.tzinfo is not None
            and last <= value <= at + timedelta(minutes=30)
            and value.astimezone(stock.SHANGHAI_TZ).date() == at.astimezone(stock.SHANGHAI_TZ).date(),
            'CAPTURE_CLOCK_REVERSED_EXPIRED_OR_CROSSED_DATE')
        last = value
        return value.isoformat()

    def request(path, params):
        _require(len(source['requests']) < MAX_REQUESTS, 'EXISTING_26_REQUEST_BUDGET_EXHAUSTED')
        if source['requests']:
            pause(20)
        requested = clock()
        record = {'path': path, 'params': dict(params), 'requested_at': requested,
            'received_at': None, 'captured_at': None, 'response_file': None,
            'http_status': None, 'error_type': None}
        source['requests'].append(record)  # Count before transport, including failed attempts.
        try:
            try:
                value = transport(path, params)
            except (ValueError, RuntimeError, OSError, TypeError) as exc:
                cause = exc.__cause__ or exc
                status = getattr(cause, 'http_status', getattr(cause, 'code', None))
                if type(status) is int and 100 <= status <= 599:
                    record['http_status'] = status
                record['received_at'] = record['captured_at'] = clock()
                raise CaptureFailure('TRANSPORT_REQUEST_FAILED_NO_RETRY') from None
            record['received_at'] = record['captured_at'] = clock()
            try:
                audit._check_safe_json(value, credential or None)
                raw = _bytes(value)
                _require(isinstance(value, dict), 'PROVIDER_OBJECT_REQUIRED')
            except (ValueError, RuntimeError, TypeError):
                raise CaptureFailure('UNSAFE_OR_INVALID_RESPONSE_NOT_RETAINED') from None
            name = f"responses/{len(source['requests']):02d}.json"
            save(name, raw)
            record.update(response_file=name, http_status=200)
            return value
        except (ValueError, RuntimeError, OSError, TypeError) as exc:
            record['error_type'] = type(exc).__name__
            raise

    def freeze(selection):
        save('selection.json', _bytes(selection))
        source['selection_hash'] = selection['selection_hash']

    parts = None
    try:
        parts = _run(output, source, request, lambda: last, freeze)
        source['status'] = COMPLETE
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        source['failure_reason'] = str(exc) if isinstance(exc, CaptureFailure) else 'INPUT_QUALIFICATION_FAILED'
    try:
        source['finished_at'] = clock()
    except CaptureFailure:
        source.update(status=FAILED, finished_at=last.isoformat(),
                      failure_reason='CAPTURE_CLOCK_REVERSED_EXPIRED_OR_CROSSED_DATE')
    source['capture_hash'] = canonical_hash(source)
    with (output / 'capture.json').open('xb') as stream:
        stream.write(_bytes(source))
    if source['status'] == COMPLETE:
        report = _assemble(source, parts)
        with (output / 'observations.json').open('xb') as stream:
            stream.write(_bytes(report))
        with (output / 'README.txt').open('xb') as stream:
            stream.write(render(report).encode())
    return source


def verify(root, *, expected_capture_hash):
    root = Path(root)
    source = independent._load(root / 'capture.json')
    independent._pin(source, 'capture_hash', expected_capture_hash)
    _require(source['version'] == VERSION and source['purpose'] == PURPOSE
        and source['implementation'] == _implementation()
        and source['response_semantics'] == 'DECODED_PROVIDER_JSON_NOT_ORIGINAL_HTTP_BYTES'
        and source['request_ceiling'] == MAX_REQUESTS and source['sample_size'] == SAMPLE_SIZE
        and source['page_size'] == PAGE_SIZE
        and all(source.get(k) == v for k, v in stock.LIMITS.items()), 'CAPTURE_CONTRACT_DIFFERS')
    _require(source['provenance'] in {PUBLIC, SYNTHETIC}, 'CAPTURE_PROVENANCE_DIFFERS')
    audit._check_safe_json(source['workflow'])
    if source['provenance'] == PUBLIC:
        _require(source['workflow'] == intent({**source['workflow'],
            'TRIAL_PURPOSE': source['workflow'].get('trial_purpose')}), 'WORKFLOW_IDENTITY_FIELDS_DIFFER')
    records, files = source['requests'], source['files']
    _require(isinstance(records, list) and len(records) <= MAX_REQUESTS
        and isinstance(files, dict) and len(files) <= MAX_REQUESTS + 3, 'CAPTURE_INVENTORY_BOUND')
    actual = {}
    for path in sorted(root.rglob('*')):
        _safe_path(path)
        if path.is_file():
            raw = independent._read(path)
            actual[path.relative_to(root).as_posix()] = {'bytes': len(raw), 'sha256': audit._sha(raw)}
    outputs = {'capture.json', 'observations.json', 'README.txt'} if source['status'] == COMPLETE else {'capture.json'}
    _require(set(actual) == set(files) | outputs and all(actual[name] == row for name, row in files.items())
        and sum(row['bytes'] for row in actual.values()) <= audit.MAX_AUDIT_BYTES,
        'CAPTURE_INVENTORY_DIFFERS')
    started, finished = (audit._clock(source[k]) for k in ('observed_at', 'finished_at'))
    _require(started <= finished <= started + timedelta(minutes=30), 'CAPTURE_LIFETIME_DIFFERS')
    _require(independent._load_bound(root, 'inputs/context.json', files) == {'observed_at': source['observed_at']},
             'CONTEXT_CLOCK_DIFFERS')
    _closures(source['closure_date'], started)
    if source['closure_date']:
        _require(independent._load_bound(root, 'inputs/closure-evidence.json', files) == CLOSURE_EVIDENCE,
                 'REVIEWED_CLOSURE_EVIDENCE_DIFFERS')
    response_names, last = set(), started
    for index, record in enumerate(records, 1):
        requested = audit._clock(record['requested_at'])
        _require(last <= requested <= finished, 'REQUEST_CLOCK_DIFFERS')
        if record['received_at'] is not None:
            last = audit._clock(record['received_at'])
            _require(requested <= last <= finished and record['captured_at'] == record['received_at'],
                     'RECEIPT_CLOCK_DIFFERS')
        if record['response_file'] is not None:
            _require(record['response_file'] == f'responses/{index:02d}.json'
                and record['error_type'] is None and type(record['http_status']) is int
                and record['http_status'] == 200, 'RESPONSE_IDENTITY_DIFFERS')
            response_names.add(record['response_file'])
        else:
            _require(record['error_type'] is not None, 'MISSING_RESPONSE_WITHOUT_FAILURE')
    _require(response_names == {name for name in files if name.startswith('responses/')},
             'UNREFERENCED_RESPONSE')
    if source['status'] != COMPLETE:
        _require(source['status'] == FAILED and source['failure_reason'], 'FAILURE_CONTRACT_DIFFERS')
        return {'status': 'RETAINED_FAILED_ATTEMPT_NO_SUCCESS_OR_REMOTE_CAUSE_REPROOF',
                'capture_hash': expected_capture_hash, 'request_attempts': len(records), 'network_calls': 0}
    position, receipt = 0, started

    def request(path, params):
        nonlocal position, receipt
        _require(position < len(records), 'UNRECORDED_REQUEST_NO_NETWORK_FALLBACK')
        record = records[position]
        position += 1
        _require(record['path'] == path and record['params'] == params and record['error_type'] is None,
                 'REPLAY_REQUEST_IDENTITY_DIFFERS')
        receipt = audit._clock(record['received_at'])
        return independent._load_bound(root, record['response_file'], files)

    def freeze(selection):
        _require(independent._load_bound(root, 'selection.json', files) == selection
            and source['selection_hash'] == selection['selection_hash'], 'FROZEN_SELECTION_DIFFERS')

    parts = _run(root, source, request, lambda: receipt, freeze)
    _require(position == len(records), 'UNCONSUMED_REQUESTS')
    report = _assemble(source, parts)
    _require(independent._read(root / 'observations.json') == _bytes(report)
        and independent._read(root / 'README.txt') == render(report).encode(), 'DERIVED_OBSERVATIONS_DIFFER')
    return {'status': 'INDEPENDENT_OBSERVATIONS_REBUILT_FROM_EXACT_CAPTURE',
        'capture_hash': expected_capture_hash, 'report_hash': report['report_hash'],
        'request_attempts': position, 'network_calls': 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('capture', 'verify'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--capture-hash')
    parser.add_argument('--closure-date', choices=('2026-10-01',))
    args = parser.parse_args(argv)
    if args.mode == 'verify':
        _require(bool(args.capture_hash), 'EXPLICIT_CAPTURE_HASH_REQUIRED')
        print(canonical_json(verify(args.root, expected_capture_hash=args.capture_hash)))
        return 0
    workflow = intent(os.environ)
    credential = os.environ.get('HITHINK_FINANCE_API_KEY', '')
    source = capture(args.root, observed_at=datetime.now(timezone.utc),
        transport=lambda p, q: own.request_json(p, q, api_key=credential),
        workflow=workflow, provenance=PUBLIC, credential=credential, closure_date=args.closure_date)
    print(canonical_json({'capture_hash': source['capture_hash'], 'status': source['status'],
                          'request_attempts': len(source['requests'])}))
    return 0 if source['status'] == COMPLETE else 1


if __name__ == '__main__':
    raise SystemExit(main())
