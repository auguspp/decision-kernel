"""Offline, all-market-origin observations; no Sector or Research admission.

REUSE + THIN_ADAPTER: sealed inventory, complete-page parser, benchmark/calendar
qualification, own-stock qualification and legacy price-path arithmetic. Caller
pins come from independently retained source receipts, never from this report.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from decimal import Context, Decimal, localcontext
from pathlib import Path
import re

from decision_kernel.adapters.hithink import normalize_hithink_calendar
from decision_kernel.adapters.hithink_index import qualify_hithink_index_snapshot
from decision_kernel.identity import canonical_hash, canonical_json
from . import hithink_index_http as indices
from . import hithink_sector_breadth_http as quotes
from . import hithink_stock_reading as own
from . import sector_radar_audit as audit
from . import stock_radar_reading as stock
from .hithink_http import HITHINK_CALENDAR_PATH
from .research_commit_only import _json, _publish_report_files, _safe_path

VERSION = 'independent-stock-retained-observations-v1'
ORIGIN = 'INDEPENDENT_ALL_MARKET_SNAPSHOT'
RULE = 'ABS_SIGNED_LAST_OVER_PREVIOUS_MINUS_ONE_DESCENDING_THEN_CODE'
LIMITS = {**stock.LIMITS, 'network_calls': 0, 'new_source_requests': 0,
          'production_admission': False, 'surprise_qualification': 'NOT_ESTABLISHED'}
_CODE = re.compile(r'\d{6}\.(SH|SZ|BJ)\Z')


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _read(path):
    _safe_path(path)
    _require(path.is_file() and path.stat().st_size <= audit.MAX_FILE_BYTES,
             'bounded regular source file required')
    raw = path.read_bytes()
    _require(len(raw) <= audit.MAX_FILE_BYTES, 'source file grew beyond bound')
    return raw


def _load(path):
    return _json(_read(path))


def _load_bound(root, name, files):
    """Parse exactly the bytes checked against the already pinned inventory.

    The earlier whole-tree check cannot bind a later filesystem read. Do not
    validate here and then reopen the path: qualification must use this buffer.
    """
    raw = _read(root / name)
    descriptor = files[name]
    _require(len(raw) == descriptor['bytes'] and audit._sha(raw) == descriptor['sha256'],
             'consumed source bytes differ from pinned inventory: ' + name)
    return _json(raw)


def _pin(value, field, expected):
    _require(audit._hash_string(expected) and value.get(field) == expected
             and canonical_hash({k: v for k, v in value.items() if k != field}) == expected,
             'independently supplied source pin differs: ' + field)


def _descriptor(root, record, manifest):
    name = record['response_file']
    return {'file': name, **manifest['files'][name], 'path': record['path'],
            'params': record['params'], 'captured_at': record['captured_at']}


def _source_context(root, manifest, *, closed_dates=(), closure_evidence=()):
    """Replay the original calendar/index requests, without Sector state/gates."""
    records = manifest['requests']
    started = audit._clock(_load_bound(root, 'inputs/context.json', manifest['files'])['observed_at'])
    _require(bool(manifest['run_clocks']), 'source completion clock missing')
    finished = audit._clock(manifest['run_clocks'][-1])
    clocks = [audit._clock(r['captured_at']) for r in records]
    _require(clocks == sorted(clocks) and all(started <= t <= finished for t in clocks),
             'source request clocks reversed or outside recorded capture')

    def one(path):
        matches = [r for r in records if r['path'] == path]
        _require(len(matches) == 1 and matches[0]['error_type'] is None,
                 'exact recorded context request unavailable: ' + path)
        return matches[0]

    calendar_record = one(HITHINK_CALENDAR_PATH)
    snapshot_record = one(indices.HITHINK_INDEX_SNAPSHOT_PATH)
    history_record = one(indices.HITHINK_INDEX_HISTORY_PATH)
    _require(records.index(calendar_record) < records.index(snapshot_record)
             < records.index(history_record), 'context requests reordered')
    calendar_raw = _load_bound(root, calendar_record['response_file'], manifest['files'])
    stock._current_calendar_source_date(calendar_raw,
        received_at=audit._clock(calendar_record['captured_at']))
    calendar = normalize_hithink_calendar(calendar_raw)

    def replay(record):
        def request(path, params):
            _require((path, dict(params)) == (record['path'], record['params']),
                     'unrecorded context request; no network fallback')
            return _load_bound(root, record['response_file'], manifest['files'])
        return request

    snapshot_at = audit._clock(snapshot_record['captured_at'])
    history_at = audit._clock(history_record['captured_at'])
    snapshot = indices.fetch_hithink_index_snapshot_batch(
        thscodes=tuple(snapshot_record['params']['thscodes'].split(',')),
        api_key='OFFLINE_REPLAY', request_json=replay(snapshot_record))
    _require(datetime.fromtimestamp(snapshot.provider_timestamp_ms / 1000,
             tz=stock.SHANGHAI_TZ) <= snapshot_at, 'index ready time follows its receipt')
    benchmark = indices.fetch_hithink_completed_index_history(
        thscode='000300.SH', observed_at=history_at, api_key='OFFLINE_REPLAY',
        request_json=replay(history_record), trading_sessions=calendar)
    qualified = qualify_hithink_index_snapshot(snapshot, benchmark_history=benchmark,
        trading_sessions=calendar, observed_at=history_at)
    reference = quotes.HithinkStockSnapshotReference(calendar, qualified, started,
        closed_dates=closed_dates, closure_evidence=closure_evidence)
    reference.validate()
    sessions = tuple(day for day in calendar if day <= reference.market_session)[-61:]
    _require(len(sessions) == 61, '61 dated calendar sessions required, not 61 own-stock bars')
    return reference, sessions, {
        'comparison_session': reference.market_session.isoformat(),
        'sessions': [d.isoformat() for d in sessions],
        'reference': reference.evidence(),
        'requests': [_descriptor(root, r, manifest)
                     for r in (calendar_record, snapshot_record, history_record)],
        'started_at': started.isoformat(), 'finished_at': finished.isoformat(),
    }


def _snapshot(root, manifest, reference):
    records = [r for r in manifest['requests'] if r['path'] == own.SNAPSHOT]
    _require(bool(records), 'complete all-market pages not supplied; not an empty scan')
    _require(all(r['error_type'] is None for r in records), 'all-market request failed')
    position, last_record = 0, None
    pages, locations = [], {}

    def request(path, params):
        nonlocal position, last_record
        _require(position < len(records), 'missing all-market page; no network fallback')
        record = records[position]
        _require((path, dict(params)) == (record['path'], record['params']),
                 'unrecorded all-market request or wrong offset')
        envelope = _load_bound(root, record['response_file'], manifest['files'])
        audit._check_safe_json(envelope)
        for row_position, row in enumerate(envelope.get('data', {}).get('item', [])):
            if isinstance(row, dict):
                locations[str(row.get('thscode', '')).strip().upper()] = [position, row_position]
        pages.append(_descriptor(root, record, manifest))
        position += 1
        last_record = record
        return envelope

    batch = quotes.fetch_hithink_all_market_snapshot(market_session=reference.market_session,
        api_key='OFFLINE_REPLAY', request_json=request, reference_context=reference,
        received_at=lambda: audit._clock(last_record['captured_at']))
    _require(position == len(records), 'extra unconsumed all-market requests')
    return batch, pages, locations


def _capture(root, expected, sessions, provenance, reference):
    """Read retained data only; never execute scripts found in a source archive."""
    report = _load(root / 'capture.json')
    _pin(report, 'capture_hash', expected)
    _require(report['version'] in {'stock-reading-capture-replay-v7',
                                  'stock-reading-discovery-page-capture-v8'}
             and report['provenance'] == provenance
             and report['response_semantics'] == 'DECODED_PROVIDER_JSON_NOT_ORIGINAL_HTTP_BYTES'
             and report['reference_input_hash'] is None
             and all(report.get(k) == v for k, v in stock.LIMITS.items()),
             'stock capture contract differs')
    files, total = {}, 0
    _safe_path(root)
    for path in sorted(root.rglob('*')):
        _safe_path(path)
        if path.is_file() and path != root / 'capture.json':
            raw = _read(path)
            total += len(raw)
            files[path.relative_to(root).as_posix()] = {'bytes': len(raw), 'sha256': audit._sha(raw)}
    _require(len(files) <= 2048 and total <= audit.MAX_AUDIT_BYTES and files == report['files'],
             'stock capture file inventory differs')
    # Read only the original dated context from this state copy, not any Sector
    # membership, trigger, leader, company-link, Research or old result payload.
    saved_sessions = _load_bound(root, 'inputs/state/market-state.json', report['files'])['sessions'][-61:]
    _require(saved_sessions == [d.isoformat() for d in sessions], 'stock capture session context differs')
    started, finished = (audit._clock(report[k]) for k in ('observed_at', 'finished_at'))
    _require(started <= finished <= started + timedelta(minutes=30), 'stock capture lifetime differs')
    reference.validate_received_at(started)
    reference.validate_received_at(finished)
    planned = {r['thscode'] for r in report['planned_issuer_outcomes']}
    _require(len(planned) == len(report['planned_issuer_outcomes']) <= stock.MAX_ISSUERS,
             'stock capture original plan denominator differs')
    traces, referenced, last = {}, set(), started
    _require(isinstance(report['requests'], list) and len(report['requests']) <= stock.MAX_REQUESTS,
             'stock capture request budget differs')
    for index, record in enumerate(report['requests'], 1):
        requested, received = (audit._clock(record[k]) for k in ('requested_at', 'received_at'))
        _require(last <= requested <= received <= finished, 'stock request clocks reversed or future')
        last = received
        name = f'responses/{index:02d}.json'
        _require(record['error_type'] is None and type(record['http_status']) is int
                 and record['http_status'] == 200 and record['response_file'] == name and name in files,
                 'recorded stock response missing; no fallback')
        referenced.add(name)
        path, params = record['path'], record['params']
        individual = path in {own.HISTORY, own.ACTIONS} or (path == own.SNAPSHOT and 'thscodes' in params)
        if not individual:
            audit._check_request(path, params)
            continue
        code = params.get('thscode', params.get('thscodes'))
        _require(isinstance(code, str) and _CODE.fullmatch(code) and code in planned,
                 'unplanned stock request identity')
        expected_params = {own.HISTORY: own.history_params(code, sessions),
                           own.SNAPSHOT: {'thscodes': code}, own.ACTIONS: own.action_params(code, sessions)}
        _require(params == expected_params[path], 'stock request/session identity differs')
        trace = traces.setdefault(code, [])
        _require(len(trace) < 3 and path == (own.HISTORY, own.SNAPSHOT, own.ACTIONS)[len(trace)],
                 'stock trace request order differs')
        trace.append(record)
    _require(referenced == {name for name in files if name.startswith('responses/')},
             'unreferenced stock response')
    return report, traces


def _trace(root, report, records, code, sessions):
    result = {'thscode': code, 'status': 'UNKNOWN', 'reason_code': 'HISTORY_NOT_SUPPLIED',
              'stock_path': None, 'input_failure': None, 'sources': []}
    if not records:
        return result
    envelopes = []
    phase = 'HISTORY'
    try:
        for phase, record in zip(('HISTORY', 'QUOTE', 'CORPORATE_ACTIONS'), records):
            result['sources'].append({**record, **report['files'][record['response_file']]})
            envelope = _load_bound(root, record['response_file'], report['files'])
            audit._check_safe_json(envelope)
            _require(type(envelope.get('code')) is int, 'invalid retained provider envelope')
            if envelope['code'] != 0:
                raise own.StockReadingInputError('REQUEST_FAILED', 'PROVIDER_BUSINESS_REQUEST_FAILED',
                    thscode=code, provider_code=envelope['code'])
            if phase == 'HISTORY':
                own.check_history_receipt(envelope, code=code, received_at=audit._clock(record['received_at']))
            elif phase == 'QUOTE':
                own.check_quote_receipt(envelope, code=code, received_at=audit._clock(record['received_at']))
            envelopes.append(envelope)
        if len(envelopes) != 3:
            result['reason_code'] = 'RECORDED_TRACE_INCOMPLETE'
            return result
        phase = 'INPUT_QUALIFICATION'
        result['stock_path'] = stock.stock_path_for_sessions(sessions, code, envelopes[0],
            at=audit._clock(records[-1]['received_at']), quote=envelopes[1], actions=envelopes[2],
            quote_received_at=audit._clock(records[1]['received_at']))
        result.update(status='CONTRACT_CHECKED_RAW_READING', reason_code=None)
    except own.StockReadingInputError as exc:
        # Same issuer-local isolation boundary as the old reader. Shared clocks,
        # credentials/rate limits and unknown business errors never become gaps.
        if not stock._isolatable_stock_error(exc, code):
            raise
        result.update(status=exc.category, reason_code=exc.reason_code, input_failure={
            'phase': phase, 'category': exc.category, 'reason_code': exc.reason_code,
            'provider_business_code': exc.provider_code,
            'selection_claim': 'NONE_DATA_UNAVAILABLE_NOT_CONDITIONS_NOT_MET'})
    return stock._plain(result)


def _sample(batch, locations, sample_size, source_hash, *, source_key="source_audit_hash"):
    """Pure frozen sample; no history availability, Sector or company input."""
    with localcontext(Context(prec=28)):
        priced = [p for p in batch.points if p.last_price is not None and p.prev_price is not None]
        changes = {p.thscode: p.last_price / p.prev_price - 1 for p in priced}
        selected = sorted(changes, key=lambda code: (-abs(changes[code]), code))[:sample_size]
        selected_set = set(selected)
        rows = [[p.thscode, *locations[p.thscode], p.last_price, p.prev_price,
                 None if p.thscode not in changes else p.last_price - p.prev_price,
                 'S' if p.thscode in selected_set else ('D' if p.thscode in changes else 'U')]
                for p in batch.points]
        frozen = stock._plain({'origin': ORIGIN, source_key: source_hash,
            'rule': RULE, 'sample_size': sample_size, 'complete_denominator': batch.returned_unique_rows,
            'selected': [{'thscode': code, 'signed_quote_change': changes[code]} for code in selected]})
        frozen['selection_hash'] = canonical_hash(frozen)
    return priced, selected, rows, frozen


def build(audit_root: Path, *, expected_audit_hash: str, sample_size: int = 16,
          stock_root: Path | None = None, expected_capture_hash: str | None = None) -> dict:
    """Return a full derived denominator plus independently frozen bounded sample."""
    _require(type(sample_size) is int and 1 <= sample_size <= stock.MAX_ISSUERS,
             'sample size must be between 1 and 16')
    _require((stock_root is None) == (expected_capture_hash is None), 'stock root and external pin must be paired')
    audit_root = Path(audit_root)
    _safe_path(audit_root)
    manifest = audit.validate_sector_radar_input_audit_integrity(audit_root)
    _pin(manifest, 'audit_hash', expected_audit_hash)
    reference, sessions, context = _source_context(audit_root, manifest)
    batch, pages, locations = _snapshot(audit_root, manifest, reference)
    priced, selected, rows, frozen = _sample(batch, locations, sample_size, expected_audit_hash)
    with localcontext(Context(prec=28)):
        # Freeze before inspecting any available-history list or old result.
        capture, traces = (None, {}) if stock_root is None else _capture(
            Path(stock_root), expected_capture_hash, sessions, manifest['provenance'], reference)
        results = {code: _trace(Path(stock_root) if stock_root else None, capture,
                              traces.get(code), code, sessions) for code in sorted(set(selected) | set(traces))}
    return _report(manifest, expected_audit_hash, expected_capture_hash, context, batch,
                   pages, priced, selected, rows, frozen, traces, results)


def _report(manifest, expected_audit_hash, expected_capture_hash, context, batch,
            pages, priced, selected, rows, frozen, traces, results):
    """Shared deterministic assembly; capture callers supply truthful source mode."""
    table = stock._plain(rows)
    report = {'version': VERSION, 'origin': ORIGIN, 'status': 'OFFLINE_OBSERVATIONS_WITH_EXPLICIT_GAPS',
        'semantics': 'UNVALIDATED_REPLAY_SAMPLE_NOT_SURPRISE_RANKING_OR_PRODUCTION_GATE',
        'source_provenance': manifest['provenance'], 'source_audit_hash': expected_audit_hash,
        'source_capture_hash': expected_capture_hash, 'source_implementation': manifest['implementation'],
        'consumer_implementation': {**audit._implementation(),
            'runtime/hithink_stock_reading.py': audit._sha(Path(own.__file__).read_bytes()),
            'runtime/independent_stock_observations.py': audit._sha(Path(__file__).read_bytes())},
        'source_validation': 'SEALED_INVENTORY_INTEGRITY_PLUS_REUSED_INPUT_QUALIFICATION_NOT_OLD_PRODUCER_REPLAY',
        'response_semantics': 'DECODED_PROVIDER_JSON_NOT_ORIGINAL_HTTP_BYTES',
        'source_custody': 'EXTERNAL_RETAINED_INPUTS_REQUIRED_HASHES_CANNOT_RECOVER_MISSING_BYTES',
        'context': context, 'pages': pages,
        'inventory': {'columns': ['thscode', 'page_index', 'row_position', 'last_price', 'prev_price',
                                  'signed_change_numerator', 'disposition'],
            'rows': table, 'rows_hash': canonical_hash(table),
            'dispositions': {'S': 'INDEPENDENT_SAMPLE', 'D': 'DEFERRED_BY_SAMPLE_BOUND', 'U': 'UNPRICED'},
            'signed_quote_change': '(last_price-prev_price)/prev_price; denominator=prev_price; null stays UNKNOWN',
            'row_identity': 'JOIN_PAGES_BY_PAGE_INDEX_THEN_ZERO_BASED_ORIGINAL_ITEM_POSITION',
            'company_names': 'UNKNOWN_NOT_SUPPLIED_BY_OFFICIAL_SNAPSHOT',
            'name_risk_classification': 'UNKNOWN_NOT_INFERRED_FROM_CODE',
            'per_security_market_session': 'NOT_PROVEN_BY_PAGE_TIMESTAMP'},
        'coverage': {'declared_total': batch.declared_total, 'unique_identities': batch.returned_unique_rows,
            'complete_pages': batch.page_count, 'usable_quote_ratios': len(priced),
            'unpriced': batch.returned_unique_rows-len(priced), 'independently_selected': len(selected),
            'deferred_priced': len(priced)-len(selected),
            'selected_with_supplied_history': sum(code in traces for code in selected),
            'selected_qualified': sum(results[code]['status'] == 'CONTRACT_CHECKED_RAW_READING' for code in selected)},
        'selection': frozen, 'selected_observations': [results[code] for code in selected],
        'replay_controls': {'origin': 'ORIGINAL_SECTOR_SELECTED_TRACES_NOT_INDEPENDENT_DISCOVERIES',
            'rows': [results[code] for code in sorted(traces)]},
        'quiet_sector_live_acquisition': 'NOT_PROVEN_BY_RETAINED_ACTIVE_DAY_ARCHIVE', **LIMITS}
    report['report_hash'] = canonical_hash(report)
    return stock._plain(report)


def verify(report, audit_root, **kwargs):
    _require(report == build(audit_root, **kwargs), 'independent observations do not rebuild from pinned inputs')
    return {'status': 'REBUILT_FROM_PINNED_RETAINED_INPUTS', 'report_hash': report['report_hash'],
            'network_calls': 0}


def render(report):
    c = report['coverage']
    return (f"Independent stock observations: {c['unique_identities']} identities / {c['complete_pages']} complete pages\n"
        f"Quote ratios: {c['usable_quote_ratios']}; unpriced: {c['unpriced']}; bounded sample: {c['independently_selected']}\n"
        f"Selected histories supplied: {c['selected_with_supplied_history']}; qualified: {c['selected_qualified']}\n"
        'This is an unvalidated signed quote-change replay sample, not Surprise or investment ranking.\n'
        'Every source identity remains in the derived inventory. Missing histories remain UNKNOWN.\n'
        'Replay controls were originally Sector-selected and are not independent discoveries.\n'
        'Provider clocks indicate readiness, not individual trading dates. Company names are UNKNOWN.\n'
        'The source pages and original archive remain external; this lossy report is not original-byte custody.\n'
        'Quiet-day live acquisition, discovery value and natural consumption remain unproved.\n'
        'No network, production admission, Research or investment authority.\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-root', type=Path, required=True)
    parser.add_argument('--audit-hash', required=True)
    parser.add_argument('--stock-root', type=Path)
    parser.add_argument('--capture-hash')
    parser.add_argument('--sample-size', type=int, default=16)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path)
    mode.add_argument('--verify', type=Path)
    args = parser.parse_args(argv)
    kwargs = {'expected_audit_hash': args.audit_hash, 'sample_size': args.sample_size,
              'stock_root': args.stock_root, 'expected_capture_hash': args.capture_hash}
    if args.verify:
        _safe_path(args.verify)
        _require(args.verify.is_dir() and {p.name for p in args.verify.iterdir()}
                 == {'observations.json', 'README.txt'}, 'report pair inventory differs')
        report = _load(args.verify / 'observations.json')
        verify(report, args.audit_root, **kwargs)
        _require(_read(args.verify / 'README.txt') == render(report).encode(), 'report rendering differs')
    else:
        _require(not any(args.output.resolve().is_relative_to(p.resolve())
                         for p in (args.audit_root, args.stock_root) if p is not None),
                 'output must be outside source trees')
        report = build(args.audit_root, **kwargs)
        _publish_report_files(args.output, {'observations.json': (canonical_json(report)+'\n').encode(),
                                           'README.txt': render(report).encode()})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
