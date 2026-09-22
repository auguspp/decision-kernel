"""One provider breadth snapshot, not a three-symbol universe or industry truth.

Reuse the existing HTTP, exact-byte and canonical-JSON owners. The historical
sample and native capture retain distinct representations and original clocks.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import os
from pathlib import Path
import re

from ..identity import canonical_hash
from . import current_state as m
from . import external_radar_observations as original
from .hithink_dump_trial import _session, _check_response
from .hithink_http import HITHINK_BASE_URL, HITHINK_API_KEY_ENV
from .sector_radar_audit import _check_safe_json

VERSION = 'industry-breadth-snapshot-v1'
WORKFLOW = '.github/workflows/radar-industry-breadth.yml'
ENDPOINT = '/api/futures/basis/main-continuous-latest'
MAX_BODY, MAX_ROWS = 4 * 1024 * 1024, 2048
AUTHORITY = {**m.AUTHORITY, 'automatic_admission': False, 'model_calls': 0,
             'research_executions': 0, 'new_attention_events': 0, 'odds_recomputed': False}
ERRORS = (ValueError, TypeError, KeyError, OSError, RuntimeError, OverflowError)


def now():
    return datetime.now(timezone.utc).isoformat()


def normalize(raw, receipt, *, cutoff):
    bound = original._bound(raw, receipt, cutoff, hithink=True)
    m.check(receipt.get('path') == ENDPOINT and receipt.get('params') == {}
            and (receipt.get('representation'), receipt.get('status')) in {
                ('DECODED_JSON_TOOL_RETURN_NOT_WIRE_BYTES', 'CAPTURED_DECODED_RESPONSE'),
                ('RETAINED_HTTP_BODY', 'CAPTURED_HTTP_RESPONSE')}, 'Breadth source identity differs')
    obj = original._decode(raw)
    m.check(isinstance(obj, dict) and type(obj.get('code')) is int and obj['code'] == 0
            and isinstance(obj.get('data'), dict), 'Breadth provider rejected')
    data = obj['data']
    m.check(original._ms(data['timestamp']) <= m.clock(receipt['received_at']),
            'Breadth provider clock is future')
    rows = data.get('item')
    m.check(isinstance(rows, list) and len(rows) <= MAX_ROWS, 'Breadth row budget')
    observations, invalid, groups = [], [], {}
    for index, row in enumerate(rows):
        code = row.get('thscode') if isinstance(row, dict) else None
        if not isinstance(code, str) or re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', code) is None:
            invalid.append({'source_row': index, 'status': 'SERIES_IDENTITY_UNAVAILABLE', 'raw': row})
            continue
        # Every spot quotation remains separate; no guessed preferred/default row.
        identity = {k: row.get(k) for k in ('thscode', 'ticker', 'spot_indicator_id', 'reference_site')}
        spot = row.get('spot_publish_date')
        try:
            day = original._day(spot)
            age = (m.clock(receipt['received_at']).astimezone(original.SHANGHAI).date() - day).days
            date_status = 'FUTURE_SOURCE_DATE' if age < 0 else 'DATED_SOURCE_CLAIM'
        except (ValueError, TypeError):
            age, date_status = None, 'SOURCE_DATE_UNKNOWN'
        fields = ('spot_price', 'converted_spot_price', 'close_price', 'settle_price',
                  'close_basis', 'settle_basis', 'close_basis_rate', 'settle_basis_rate')
        bad_fields = []
        for field in fields:
            try:
                original._number(row.get(field))
            except (ValueError, TypeError):
                bad_fields.append(field)
        record = {'source_row': index, 'identity': identity,
                  'observation_id': canonical_hash(identity), 'version_id': canonical_hash(row),
                  'raw': row, 'source_date_status': date_status, 'spot_age_days_at_capture': age,
                  'missing_fields': [k for k in fields if row.get(k) is None],
                  'invalid_numeric_fields': bad_fields,
                  'lane': 'FINANCIAL_MARKET_CONTEXT' if code.endswith('.CFE') else 'INDUSTRY_CANDIDATE_CONTEXT',
                  'qualification': 'CONTEXT_ONLY', 'question_status': 'NOT_FORMED'}
        observations.append(record)
        groups.setdefault(code, []).append(record)
    series = [{'thscode': code, 'source_rows': [r['source_row'] for r in members],
               'default_rows': [r['source_row'] for r in members if r['raw'].get('default_value') == 'Y'],
               'spot_selection': 'NOT_SELECTED_ALL_SOURCE_ALTERNATIVES_RETAINED',
               'lane': members[0]['lane']} for code, members in sorted(groups.items())]
    counts = Counter(r['version_id'] for r in observations)
    return original._seal({'version': VERSION, 'source': {**bound, 'path': ENDPOINT, 'params': {},
                    'representation': receipt['representation'], 'provider_timestamp': data['timestamp']},
                'status': 'EMPTY_SOURCE_SNAPSHOT_NOT_NO_INDUSTRY_CHANGE' if not rows else
                          'BREADTH_CONTEXT_WITH_ROW_GAPS' if invalid else 'BREADTH_CONTEXT_RETAINED',
                'observations': observations, 'invalid_rows': invalid, 'series': series,
                'coverage': {'source_rows': len(rows), 'identified_rows': len(observations),
                    'unidentified_rows': len(invalid), 'distinct_series': len(series),
                    'financial_series': sum(s['lane'] == 'FINANCIAL_MARKET_CONTEXT' for s in series),
                    'duplicate_content_rows': sum(n - 1 for n in counts.values()),
                    'all_industries_covered': False, 'provider_universe_complete': 'NOT_ESTABLISHED'},
                'semantics': 'SOURCE_BREADTH_NOT_INDEPENDENT_INDUSTRY_SIGNALS',
                'units_and_ratio_scale': 'RAW_PROVIDER_FIELDS_NOT_UNIFORMLY_ESTABLISHED',
                'completed_session_finality': 'NOT_ESTABLISHED', 'historical_pit': 'NOT_ESTABLISHED',
                'continuous_roll_composition': 'UNKNOWN', 'economic_exposure': 'NOT_ESTABLISHED',
                'noncommodity_coverage': 'NOT_ESTABLISHED_BY_THIS_FUTURES_SNAPSHOT', **AUTHORITY})


def request_raw(credential):
    # Same mature HTTP policy as institutional capture; only this fixed URL.
    with _session() as session:
        with session.get(HITHINK_BASE_URL + ENDPOINT, params={},
                headers={'X-api-key': credential, 'Accept': 'application/json', 'Accept-Encoding': 'identity'},
                timeout=(10, 20), stream=True, allow_redirects=False) as response:
            length = _check_response(response)
            m.check(length is None or length <= MAX_BODY, 'Breadth body limit')
            m.check(response.url == HITHINK_BASE_URL + ENDPOINT, 'Breadth destination differs')
            chunks, count = [], 0
            for chunk in response.iter_content(chunk_size=65536):
                count += len(chunk)
                m.check(count <= MAX_BODY, 'Breadth body limit')
                chunks.append(chunk)
            m.check(length is None or count == length, 'Breadth body length differs')
    return b''.join(chunks)


def workflow_identity(value):
    m.check(isinstance(value, dict) and set(value) == {
        'repository', 'workflow', 'ref', 'event', 'code_commit', 'run_id', 'attempt', 'trigger_run_id'},
        'Breadth workflow shape')
    m.check(value['repository'] == m.REPOSITORY and value['workflow'] == WORKFLOW
            and value['ref'] == 'refs/heads/main' and value['event'] in {'workflow_run', 'workflow_dispatch'}
            and isinstance(value['code_commit'], str) and m.SHA.fullmatch(value['code_commit'])
            and type(value['run_id']) is int and value['run_id'] > 0
            and type(value['attempt']) is int and value['attempt'] == 1, 'Breadth workflow differs')
    trigger = value['trigger_run_id']
    m.check((value['event'] == 'workflow_dispatch' and trigger is None)
            or (value['event'] == 'workflow_run' and type(trigger) is int and trigger > 0),
            'Breadth trigger differs')
    return value


def capture(output, identity, *, credential, request=request_raw, clock=now):
    workflow_identity(identity)
    output = Path(output)
    m.check(not output.exists() and not output.is_symlink()
            and not any(p.is_symlink() for p in output.parents), 'Breadth output must be create-only')
    output.mkdir(parents=True, exist_ok=False)
    request_record = {'path': ENDPOINT, 'params': {}, 'requested_at': clock()}
    with (output / 'request.json').open('xb') as out:
        out.write(m.json_bytes(request_record))
    receipt = {**request_record, 'received_at': None, 'representation': 'RETAINED_HTTP_BODY',
               'status': 'SOURCE_UNAVAILABLE', 'response_bytes': None, 'response_sha256': None}
    result = {'version': VERSION, 'workflow': identity, 'receipt': receipt,
              'attempted_requests': 0, 'error_type': None, 'http_status': None, **AUTHORITY}
    try:
        m.check(isinstance(credential, str) and bool(credential) and credential.isascii()
                and all(32 < ord(c) < 127 for c in credential), 'Breadth credential unavailable')
        result['attempted_requests'] = 1
        raw = request(credential)
        receipt['received_at'] = clock()
        m.check(isinstance(raw, bytes) and 0 < len(raw) <= MAX_BODY, 'Breadth body limit')
        m.check(credential.encode() not in raw, 'Breadth credential reflection')
        _check_safe_json(original._decode(raw), credential)
        receipt.update(status='CAPTURED_HTTP_RESPONSE', response_bytes=len(raw), response_sha256=m.sha256(raw))
        with (output / 'basis.json').open('xb') as out:
            out.write(raw)
        result['http_status'] = 200
    except ERRORS as exc:
        receipt['received_at'] = clock()
        result['error_type'] = type(exc).__name__
        http = getattr(exc, 'http_status', None)
        result['http_status'] = http if type(http) is int and 100 <= http <= 599 else None
    result['finished_at'] = clock()
    m.check(m.clock(receipt['requested_at']) <= m.clock(receipt['received_at'])
            <= m.clock(result['finished_at']), 'Breadth capture clock differs')
    result['capture_hash'] = canonical_hash(result)
    with (output / 'capture.json').open('xb') as out:
        out.write(m.json_bytes(result))
    return result


def replay(files, run, *, cutoff):
    m.check(set(files) in ({'request.json', 'capture.json'}, {'request.json', 'capture.json', 'basis.json'})
            and all(isinstance(v, bytes) for v in files.values())
            and sum(map(len, files.values())) <= MAX_BODY + 16384, 'Breadth inventory differs')
    value = original._decode(files['capture.json'])
    m.check(value['version'] == VERSION and value['capture_hash'] == canonical_hash({
        k: v for k, v in value.items() if k != 'capture_hash'})
        and all(value.get(k) == v for k, v in AUTHORITY.items()), 'Breadth capture differs')
    identity = workflow_identity(value['workflow']); receipt = value['receipt']
    m.check(identity['run_id'] == run['id'] and identity['code_commit'] == run['head_sha']
            and identity['event'] == run['event'] and identity['attempt'] == run['run_attempt'],
            'Breadth native run binding differs')
    req = original._decode(files['request.json'])
    m.check(req == {k: receipt[k] for k in ('path', 'params', 'requested_at')}
            and req['path'] == ENDPOINT and req['params'] == {}, 'Breadth request differs')
    m.check(m.clock(run['created_at']) <= m.clock(receipt['requested_at'])
            <= m.clock(receipt['received_at']) <= m.clock(value['finished_at'])
            <= m.clock(run['updated_at']) <= m.clock(cutoff), 'Breadth native clocks differ')
    m.check(type(value['attempted_requests']) is int and value['attempted_requests'] in {0, 1},
            'Breadth request budget differs')
    if 'basis.json' not in files:
        m.check(receipt['status'] == 'SOURCE_UNAVAILABLE' and receipt['response_bytes'] is None
                and receipt['response_sha256'] is None and isinstance(value['error_type'], str),
                'Breadth absence is not empty success')
        return {'status': 'SOURCE_UNAVAILABLE', 'capture': value, 'snapshot': None}
    m.check(value['attempted_requests'] == 1 and value['http_status'] == 200
            and value['error_type'] is None and receipt['representation'] == 'RETAINED_HTTP_BODY',
            'Breadth successful response differs')
    return {'status': 'SAVED_NATIVE_SNAPSHOT', 'capture': value,
            'snapshot': normalize(files['basis.json'], receipt, cutoff=cutoff)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv); env = os.environ
    identity = {'repository': env['GITHUB_REPOSITORY'], 'workflow': WORKFLOW,
        'ref': env['GITHUB_REF'], 'event': env['GITHUB_EVENT_NAME'], 'code_commit': env['GITHUB_SHA'],
        'run_id': int(env['GITHUB_RUN_ID']), 'attempt': int(env['GITHUB_RUN_ATTEMPT']),
        'trigger_run_id': int(env['TRIGGER_RUN_ID']) if env.get('TRIGGER_RUN_ID') else None}
    result = capture(args.output, identity, credential=env.get(HITHINK_API_KEY_ENV, ''))
    print('INDUSTRY_BREADTH_SOURCE_STATUS=' + result['receipt']['status'])
    return 0  # A finite source attempt may contain an explicit unavailable result.


if __name__ == '__main__':
    raise SystemExit(main())
