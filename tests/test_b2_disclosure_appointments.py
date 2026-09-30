"""Standard source path: synthetic new selections plus offline retained raw replay.

No test contacts CNINFO, adds production stocks, or certifies live appointments.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import runpy

import pytest
import requests
import yaml
from decision_kernel.runtime import tushare_relay as relay

ROOT = Path(__file__).resolve().parents[1]
b2 = runpy.run_path(str(ROOT / '.github/scripts/b2-disclosure-appointments.py'))
NOW = '2099-01-01T00:00:00+00:00'
IDENTITY = {'GITHUB_SHA': 'a' * 40, 'GITHUB_RUN_ID': '123456789', 'GITHUB_RUN_ATTEMPT': '1',
            'test_only': 'SYNTHETIC_NOT_A_GITHUB_RUN'}
PERIOD = '2099-12-31'
CODES = ['600001.SH', '688001.SH', '300001.SZ', '920001.BJ']


def registry(codes=CODES):
    return {'schema_version': 1,
        'semantics': 'EXPLICIT_READ_PURPOSES_AND_RESOLUTION_REFERENCES_NOT_CANONICAL_STATE',
        'references': [{'id': 'selected-' + str(i), 'case': code, 'use': 'RETAINED_RESEARCH_DOCUMENT',
                        'source': {'path': 'docs/readings/synthetic.md'}} for i, code in enumerate(codes)]}


def envelope(rows):
    count = len(rows) if rows is not None else 0
    return json.dumps({'prbookinfos': rows, 'totalRows': count, 'totalPages': 1 if count else 0,
                       'hasNextPage': False, 'hasPreviousPage': False}, ensure_ascii=False).encode()


def row(code, period=PERIOD):
    return {'seccode': code, 'secname': 'SYNTHETIC_NOT_A_REAL_COMPANY',
            'f001d_0102': period, 'f002d_0102': '2100-02-01', 'f003d_0102': '',
            'f004d_0102': None, 'f005d_0102': '', 'f006d_0102': '', 'latest_time': None}


def client(factory=None, *, http=200, complete=True, error=None):
    calls = []
    def request(params, *, clock):
        calls.append(deepcopy(params))
        raw = factory(params) if factory else envelope([row(params['stockCode'], params['sectionTime'])])
        return {'http_status': http, 'headers': {}, 'raw': raw,
                'body_complete': complete, 'error_type': error,
                'requested_at': clock(), 'received_at': clock()}
    return request, calls


def run(tmp_path, request, *, reg=None, ids=None, period=PERIOD):
    reg = registry() if reg is None else reg
    ids = [r['id'] for r in reg['references']] if ids is None else ids
    return b2['capture'](tmp_path / 'out', IDENTITY, reference_ids=ids, period=period,
        registry_raw=json.dumps(reg).encode(), request=request, clock=lambda: NOW)


def test_new_selected_securities_and_another_period_need_no_runtime_change(tmp_path):
    request, calls = client()
    original = registry()
    result = run(tmp_path, request, reg=original)
    assert [p['stockCode'] for p in calls] == [c[:6] for c in CODES]
    assert [p['market'] for p in calls] == ['sh', 'shkcp', 'sz', 'bj']
    assert all(p['sectionTime'] == PERIOD and p['pagesize'] == '100' and p['pagenum'] == '1' for p in calls)
    assert result['status'] == 'CAPTURED_REQUIRES_SOURCE_REVIEW'
    assert result['official_appointment_qualified'] is False
    assert original == registry()
    plan = json.loads((tmp_path/'out/plan.json').read_bytes())
    assert plan['scope_source']['selected_reference_ids'] == ['selected-0', 'selected-1', 'selected-2', 'selected-3']
    assert plan['scope_source']['ref'] == IDENTITY['GITHUB_SHA']
    assert all(p['relationship'] == 'NOT_INFERRED_FROM_SOURCE_SELECTION' for p in plan['requests'])
    for item in result['outcomes']:
        d = tmp_path/'out'/item['code']
        receipt = json.loads((d/'receipt.json').read_bytes())
        raw = (d/'response.body').read_bytes()
        assert receipt['response']['sha256'] == sha256(raw).hexdigest()
        assert receipt['date_qualification'] == 'NOT_PERFORMED'
    text = (tmp_path/'out/summary.md').read_text()
    assert PERIOD in text and all(code in text for code in CODES)
    assert '首次预约' in text and '不是持仓' in text and '原件待复核' in text
    with pytest.raises(FileExistsError):
        run(tmp_path, request)
    assert len(calls) == len(CODES)


def test_only_explicit_selected_reference_is_requested_and_archive_locator_is_retained(tmp_path):
    reg = registry(); reg['references'][1]['archive_source'] = reg['references'][1].pop('source')
    request, calls = client()
    run(tmp_path, request, reg=reg, ids=['selected-1'])
    assert [p['stockCode'] for p in calls] == ['688001']
    plan = json.loads((tmp_path/'out/plan.json').read_bytes())
    assert plan['requests'][0]['selection'] == reg['references'][1]


def test_invalid_inputs_stop_before_any_source_or_output(tmp_path):
    cases = []
    for period in ('2099-01-01', '2099-02-30', '20991231', 'latest', '2099-12-31;echo bad'):
        cases.append((registry(), ['selected-0'], period))
    for ids in ([], ['not-registered'], ['selected-0']*2, ['selected-0;echo bad'], ['x']*7):
        cases.append((registry(), ids, PERIOD))
    duplicate = registry(); duplicate['references'].append(deepcopy(duplicate['references'][0]))
    cases.append((duplicate, ['selected-0'], PERIOD))
    duplicate_stock = registry(['600001.SH', '600001.SH'])
    cases.append((duplicate_stock, ['selected-0', 'selected-1'], PERIOD))
    for code in ('navigation', '600001', '../../unsafe', 'AAPL.US'):
        cases.append((registry([code]), ['selected-0'], PERIOD))
    for reg, ids, period in cases:
        request, calls = client()
        with pytest.raises(ValueError): run(tmp_path, request, reg=reg, ids=ids, period=period)
        assert calls == [] and not (tmp_path/'out').exists()


def test_middle_empty_null_and_missing_fields_do_not_stop_independent_objects(tmp_path):
    def raw(params):
        code = params['stockCode']
        if code == '688001': return envelope(None)
        if code == '300001':
            value = row(code); del value['f003d_0102']
            return envelope([value])
        if code == '920001': return envelope([])
        return envelope([row(code)])
    request, calls = client(raw)
    result = run(tmp_path, request)
    assert len(calls) == 4 and result['status'] == 'CAPTURED_WITH_GAPS'
    assert [o['status'] for o in result['outcomes']] == [
        'CAPTURED_REQUIRES_SOURCE_REVIEW', 'NULL_RESPONSE_NOT_NO_APPOINTMENT',
        'CAPTURED_WITH_FIELD_GAPS', 'EMPTY_RESPONSE_NOT_NO_APPOINTMENT']
    missing = result['outcomes'][2]['inspection']['rows'][0]
    assert 'f003d_0102' in missing['missing_fields'] and 'change_1' not in missing['date_fields']
    assert b2['readable_summary'](result) == (tmp_path/'out/summary.md').read_bytes()


def test_source_keys_and_revision_slots_are_preserved_without_sort_fill_or_keep_last():
    a = row('600001'); a.update(f003d_0102='2100-02-10', f004d_0102='2100-02-05')
    rows = [dict(reversed(list(a.items()))), dict(a)]
    mapped = b2['inspect_body'](envelope(rows), '600001.SH', PERIOD)
    assert mapped['row_count'] == 2 and mapped['revision_history_complete'] is False
    fields = mapped['rows'][0]['date_fields']
    assert fields == {'first_appointment': '2100-02-01', 'change_1': '2100-02-10',
                      'change_2': '2100-02-05', 'change_3': '', 'actual_disclosure': ''}
    assert 'current_appointment' not in fields
    assert mapped['rows'][1]['source_row_index'] == 1
    for bad_value in ('2100-02-30', 20991231, False, {'untrusted': '<script>'}):
        bad = dict(a, f003d_0102=bad_value)
        result = b2['inspect_body'](envelope([bad]), '600001.SH', PERIOD)
        assert result['status'] == 'CAPTURED_WITH_FIELD_GAPS'
        assert result['rows'][0]['date_fields']['change_1'] == bad_value
        assert result['rows'][0]['invalid_fields'] == ['f003d_0102']


def test_existing_raw_capture_is_replayed_offline_without_rewriting_its_failure():
    base = ROOT/'docs/readings/2026-09-30-b2-cninfo-36648293469'
    original = (base/'capture.json').read_bytes()
    prior = json.loads(original)
    assert prior['status'] == 'STOPPED_WITH_GAPS'
    for code, first in [('600276.SH','2026-10-28'), ('688277.SH','2026-10-29'), ('603986.SH','2026-10-30')]:
        raw = (base/code/'response.body').read_bytes()
        receipt = json.loads((base/code/'receipt.json').read_bytes())
        assert sha256(raw).hexdigest() == receipt['response']['sha256']
        result = b2['inspect_body'](raw, code, '2026-09-30')
        assert result['rows'][0]['date_fields']['first_appointment'] == first
        assert result['rows'][0]['date_fields']['actual_disclosure'] == ''
        assert receipt['date_qualification'] == 'NOT_PERFORMED'
    raw = (base/'002674.SZ/response.body').read_bytes()
    assert b2['inspect_body'](raw, '002674.SZ', '2026-09-30')['status'] == 'NULL_RESPONSE_NOT_NO_APPOINTMENT'
    assert (base/'capture.json').read_bytes() == original


@pytest.mark.parametrize('http', [302, 401, 403, 429, 503])
def test_non_success_retains_raw_and_stops_no_retry_or_fallback(tmp_path, http):
    request, calls = client(lambda _: b'{"error":"synthetic"}', http=http)
    result = run(tmp_path, request)
    assert len(calls) == 1 and result['status'] == 'STOPPED_WITH_GAPS'
    assert all(o['status'] == 'NOT_QUERIED_AFTER_STOP' and o['receipt'] is None for o in result['outcomes'][1:])
    assert (tmp_path/'out/600001.SH/response.body').read_bytes() == b'{"error":"synthetic"}'


def test_unknown_envelope_coverage_identity_or_business_error_stops_with_raw(tmp_path):
    originals = [b'{"prbookinfos":null}', b'{"prbookinfos":[],"prbookinfos":[]}', envelope([42]),
                 envelope([row('000000')]), envelope([row('600001', '2099-06-30')])]
    good = json.loads(envelope([row('600001')]))
    for change in ({'error':'denied'}, {'success':False}, {'hasNextPage':True},
                   {'totalRows':2}, {'totalRows':True}, {'totalPages':2}):
        originals.append(json.dumps({**good, **change}).encode())
    for index, raw in enumerate(originals):
        d = tmp_path/str(index); d.mkdir()
        request, calls = client(lambda _, raw=raw: raw)
        result = run(d, request)
        assert len(calls) == 1 and result['status'] == 'STOPPED_WITH_GAPS'
        assert result['outcomes'][0]['status'] == 'RESPONSE_GAP_RAW_RETAINED'
        assert (d/'out/600001.SH/response.body').read_bytes() == raw


def test_partial_stream_and_exception_keep_gap_without_leaking_error_text(tmp_path):
    request, calls = client(lambda _: b'{"partial":', complete=False, error='ChunkedEncodingError')
    result = run(tmp_path, request)
    assert len(calls) == 1 and result['status'] == 'STOPPED_WITH_GAPS'
    assert (tmp_path/'out/600001.SH/response.body').read_bytes() == b'{"partial":'
    d = tmp_path/'exception'; d.mkdir()
    def fail(*args, **kwargs): raise RuntimeError('sensitive-url-not-to-be-serialized')
    result = run(d, fail)
    assert result['status'] == 'STOPPED_WITH_GAPS'
    assert all(b'sensitive-url' not in p.read_bytes() for p in d.rglob('*') if p.is_file())


def test_transport_has_no_credentials_retry_redirect_or_cross_object_session():
    calls = []
    class Response:
        status_code = 503
        headers = {'Content-Type': 'application/json'}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, chunk_size): yield b'{"error":"synthetic"}'
    class Session:
        trust_env = True
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            assert self.trust_env is False and url == b2['URL']
            assert kwargs['allow_redirects'] is False and kwargs['stream'] is True
            assert kwargs['timeout'] == (5, 15)
            assert kwargs['headers'] == {'Accept':'application/json','Accept-Encoding':'identity'}
            assert 'auth' not in kwargs and 'cookies' not in kwargs
            calls.append(kwargs)
            return Response()
    result = b2['public_request']({'stockCode':'600001'}, clock=lambda:NOW, session_factory=Session)
    assert len(calls) == 1 and result['http_status'] == 503 and result['body_complete'] is True
    with requests.Session() as original: assert original.get_adapter('https://').max_retries.total == 0


def test_stream_failure_preserves_prefix_without_exception_text():
    class Response:
        status_code = 200
        headers = {}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, chunk_size):
            yield b'{"prefix":'
            raise requests.ConnectionError('not-for-serialization')
    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return Response()
    result = b2['public_request']({}, clock=lambda:NOW, session_factory=Session)
    assert result['raw'] == b'{"prefix":' and result['body_complete'] is False
    assert result['error_type'] == 'ConnectionError' and 'not-for-serialization' not in str(result)


def test_reflected_credential_cannot_be_archived(tmp_path, monkeypatch):
    monkeypatch.setenv(relay.SECRET_ENV,'synthetic-sensitive-value')
    with pytest.raises(ValueError, match='B2_CREDENTIAL_REFLECTION'):
        b2['save'](tmp_path/'receipt.json', b'synthetic-sensitive-value')
    assert not (tmp_path/'receipt.json').exists()


def test_workflow_requires_selection_and_period_keeps_gates_and_uses_env_not_shell_interpolation():
    source = (ROOT/'.github/workflows/b2-disclosure-appointments.yml').read_text()
    w = yaml.load(source, Loader=yaml.BaseLoader)
    assert set(w['on']) == {'workflow_dispatch'}
    inputs = w['on']['workflow_dispatch']['inputs']
    assert set(inputs) == {'code-sha','reference-ids','report-period','source-kind','start-date','end-date'}
    assert all(inputs[k]['required'] == 'true' and 'default' not in inputs[k] for k in ('code-sha','reference-ids'))
    assert inputs['source-kind']['default'] == 'appointments'
    assert inputs['source-kind']['options'] == ['appointments','announcements']
    assert all(inputs[k]['required'] == 'false' for k in ('report-period','start-date','end-date'))
    capture = next(s for s in w['jobs']['capture']['steps'] if s.get('id') == 'capture')
    assert capture['env'] == {'B2_REFERENCE_IDS':'${{ inputs.reference-ids }}', 'B2_REPORT_PERIOD':'${{ inputs.report-period }}',
        'B2_SOURCE_KIND':'${{ inputs.source-kind }}', 'B2_START_DATE':'${{ inputs.start-date }}', 'B2_END_DATE':'${{ inputs.end-date }}'}
    assert '${{' not in capture['run'] and '--reference-ids "$B2_REFERENCE_IDS"' in capture['run']
    for flag, variable in [('report-period','B2_REPORT_PERIOD'),('source-kind','B2_SOURCE_KIND'),
                           ('start-date','B2_START_DATE'),('end-date','B2_END_DATE')]:
        assert f'--{flag} "${variable}"' in capture['run']
    assert 'contents: write' not in source and 'actions: write' not in source
    assert "github.run_attempt == 1" in source and "github.actor == 'auguspp'" in source
    assert 'persist-credentials: false' in source and 'cancel-in-progress: false' in source
    assert 'head_sha=$EXPECTED_CODE' in source and "r['conclusion'] == 'success'" in source
    assert 'secrets.' not in source and 'TUSHARE_PROXY_API_KEY' not in source
    assert 'continue-on-error' not in source and 'current-state-read-entry' not in source
    assert not {'COMPANIES', 'PERIOD', 'SCOPE'} & b2.keys()


def test_per_security_reading_and_unbound_reference_preserve_original_batch(tmp_path):
    request, calls = client()
    result = run(tmp_path, request)
    output = tmp_path / 'out'
    before = deepcopy(result)
    proposal = json.loads((output/'registration-proposal.json').read_bytes())
    assert proposal['status'] == 'PROPOSED_NOT_SAVED_REGISTERED_OR_PUBLISHED'
    assert proposal['directory'] == 'docs/readings/b2-appointments-123456789-1'
    assert [r['case'] for r in proposal['references']] == CODES
    assert len({r['id'] for r in proposal['references']}) == 4
    for item, record in zip(result['outcomes'], proposal['references']):
        target = output / item['code']
        assert {p.name for p in target.iterdir()} == {'plan.json','summary.md','receipt.json','response.body'}
        assert (target/'plan.json').read_bytes() == (output/'plan.json').read_bytes()
        summary = (target/'summary.md').read_bytes()
        assert 'receipt.json' in summary.decode() and item['code'] + '/receipt.json' not in summary.decode()
        assert all(code not in summary.decode() for code in CODES if code != item['code'])
        assert record['use'] == 'NAVIGATION_ONLY' and record['archive'] == {'format':'RETAINED_FILES'}
        assert record['read_policy'] == 'ON_DEMAND_ARCHIVE' and 'source' not in record
        assert record['archive_source']['bytes'] == len(summary)
        assert record['archive_source']['sha256'] == sha256(summary).hexdigest()
        assert record['archive_source']['ref'] is None  # Never default to the capture commit or moving main.
        assert record['archive_source']['path'] == proposal['directory'] + '/' + item['code'] + '/summary.md'
        from hashlib import sha1
        assert record['archive_source']['git_blob'] == sha1(f'blob {len(summary)}\0'.encode()+summary).hexdigest()
        assert item['reference_id'] in record['purpose_note'] and '不是研究' in record['purpose_note']
    assert before == result and len(calls) == 4
    assert not (output/'registry.json').exists()


def test_source_failure_keeps_unqueried_readable_without_fabricating_a_response(tmp_path):
    request, calls = client(http=403)
    result = run(tmp_path, request)
    assert result['status'] == 'STOPPED_WITH_GAPS' and len(calls) == 1
    output = tmp_path/'out'
    proposal = json.loads((output/'registration-proposal.json').read_bytes())
    assert len(proposal['references']) == 4
    for item in result['outcomes'][1:]:
        target = output/item['code']
        assert {p.name for p in target.iterdir()} == {'plan.json','summary.md'}
        text = (target/'summary.md').read_text()
        assert 'NOT_QUERIED_AFTER_STOP' in text and '不是空表或没有预约' in text
        assert (target/'plan.json').read_bytes() == (output/'plan.json').read_bytes()
    assert json.loads((output/'capture.json').read_bytes())['status'] == 'STOPPED_WITH_GAPS'


def test_retention_run_identity_is_validated_before_source_or_output(tmp_path):
    for run_id, attempt in [(None, '1'), ('../outside','1'), ('0','1'), ('1','2'), (1,'1')]:
        request, calls = client()
        with pytest.raises(ValueError, match='B2_RETENTION_IDENTITY'):
            b2['capture'](tmp_path/'out', {**IDENTITY,'GITHUB_RUN_ID':run_id,'GITHUB_RUN_ATTEMPT':attempt},
                reference_ids=['selected-0'], period=PERIOD,
                registry_raw=json.dumps(registry()).encode(), request=request, clock=lambda:NOW)
        assert calls == [] and not (tmp_path/'out').exists()


@pytest.mark.parametrize('source_kind', ['appointments', 'announcements'])
@pytest.mark.parametrize('http', [200, 403])
def test_standard_capture_uses_original_archive_reader_for_each_security(tmp_path, monkeypatch, http, source_kind):
    # Native API transport fixture only; the real archive reader and validators run unchanged.
    import socket
    def no_network(*args, **kwargs): raise AssertionError('no live source in standard archive test')
    monkeypatch.setattr(socket.socket, 'connect', no_network)
    from decision_kernel.runtime import research_archive as archive
    fixture = runpy.run_path(str(ROOT/'tests/test_research_archive.py'))
    request, calls = client(lambda p: envelope(None) if p['stockCode']=='688001' else
                            envelope([row(p['stockCode'],p['sectionTime'])]), http=http)
    if source_kind == 'appointments':
        result = run(tmp_path, request)
    else:
        request, calls = announcement_client(http=http, null_code='688001')
        result = run_announcements(tmp_path, request)
    output = tmp_path/'out'
    proposal = json.loads((output/'registration-proposal.json').read_bytes())
    for index, record in enumerate(proposal['references']):
        files = {p.name:p.read_bytes() for p in (output/record['case']).iterdir()}
        api = fixture['API'](files=files, entry='summary.md')
        from decision_kernel.runtime import research_archive_index as archive_index
        # The original index rejects the actual unbound proposal before any Git read.
        with pytest.raises(ValueError): archive_index.project(record)
        api.record = deepcopy(record)
        api.record['archive_source']['ref'] = fixture['A']  # Simulated custody only.
        api.registry['references'] = [api.record]
        index_fixture = runpy.run_path(str(ROOT/'tests/test_research_archive_index.py'))
        index_fixture['reindex'](api)
        prefix = str(Path(api.record['archive_source']['path']).parent)
        for tree_entry in api.tree['tree']:
            tree_entry['path'] = prefix + '/' + Path(tree_entry['path']).name
        # An unbound shown locator cannot bypass the same-R registry/reader check.
        api.reading['research']['on_demand_archives'][0]['source']['ref'] = None
        api.reseal()
        with pytest.raises(ValueError):
            archive.recover_archive(api, reading_commit=fixture['R'],
                record_id=record['id'], output=tmp_path/f'unbound-{index}')
        assert not any(call[0] == 'get' for call in api.calls)
        index_fixture['reindex'](api)
        receipt = archive.recover_archive(api, reading_commit=fixture['R'],
            record_id=record['id'], output=tmp_path/f'recovered-{index}')
        assert receipt['source_materialization'] == 'RECOVERED_ON_DEMAND_AFTER_REGISTERED_ONLY'
        assert api.reading['research']['records'] == []
        assert receipt['case'] == record['case'] and receipt['original_use'] == 'NAVIGATION_ONLY'
        assert receipt['qualification'] == 'RETAINED_FILES_NOT_REVALIDATED_RESEARCH'
        assert receipt['continuation_status'] == 'NOT_EXECUTED' and receipt['remote_write'] is False
        assert {p.name:p.read_bytes() for p in (tmp_path/f'recovered-{index}'/'bundle').iterdir()} == files
        assert receipt['source_commit'] == fixture['A'] and receipt['reading_commit'] == fixture['R']
    assert len(calls) == (1 if http == 403 else 4 if source_kind == 'appointments' else 8)
    assert result['status'] == ('STOPPED_WITH_GAPS' if http == 403 else 'CAPTURED_WITH_GAPS')


def test_source_archive_keeps_navigation_use_and_rejects_typed_progress(tmp_path):
    from decision_kernel.runtime import research_archive_index as archive_index
    request, calls = client()
    run(tmp_path, request, ids=['selected-0'])
    record = json.loads((tmp_path/'out/registration-proposal.json').read_bytes())['references'][0]
    record['archive_source']['ref'] = 'b' * 40  # Synthetic retained commit, no Git effect.
    entry = archive_index.project(record)
    assert entry['use'] == 'NAVIGATION_ONLY' and entry['body_materialized_in_reading'] is False
    assert 'read_path' not in entry['source'] and len(calls) == 1
    record['archive'] = {'format':'RESEARCH_PROGRESS', 'expected_sha256':'c' * 64, 'question_id':'synthetic'}
    with pytest.raises(ValueError, match='source navigation cannot become typed research'):
        archive_index.project(record)


# Source-only directory scenarios. Dates/tickers are synthetic, never a live source.
PUBLICATION_MS = 4070847600000  # 2098-12-31 15:00 Asia/Shanghai.


def announcement_client(*, http=200, total=1, null_code=None, damage=None):
    calls = []
    def request(form, *, kind, clock):
        calls.append((kind, deepcopy(form)))
        if kind == 'organization':
            value = [{'code':form['keyWord'], 'orgId':'org-'+form['keyWord']}]
        else:
            code, org = form['stock'].split(',')
            count = 0 if code == null_code else total
            number, size = int(form['pageNum']), int(form['pageSize'])
            begin = (number-1)*size
            rows = [{'announcementId':str(i), 'secCode':code, 'orgId':org,
                     'announcementTitle':'SYNTHETIC dividend / meeting, not an event date',
                     'announcementTime':PUBLICATION_MS, 'announcementTypeName':'SYNTHETIC',
                     'adjunctUrl':f'finalpage/2098-12-31/{i}.PDF'}
                    for i in range(begin+1,min(begin+size,count)+1)]
            value = {'totalAnnouncement':count,'announcements':None if code==null_code else rows,
                     'hasMore':begin+len(rows)<count}
            if damage: damage(value, number)
        raw = json.dumps(value, ensure_ascii=False).encode()
        return {'http_status':http,'raw':raw,'headers':{},'body_complete':True,'error_type':None,
                'requested_at':clock(),'received_at':clock()}
    return request, calls


def run_announcements(tmp_path, request, *, ids=None, start='2098-12-31', end='2098-12-31'):
    return b2['capture_announcements'](tmp_path/'out', IDENTITY,
        reference_ids=ids or ['selected-'+str(i) for i in range(4)], start_date=start, end_date=end,
        registry_raw=json.dumps(registry()).encode(), request=request, clock=lambda:NOW)


def test_announcement_directory_uses_original_identity_and_batch_parser_with_raw_pages(tmp_path, monkeypatch):
    from decision_kernel.runtime import cninfo_http as cninfo
    original = cninfo.fetch_cninfo_disclosures
    invocations = []
    def tracked(**kwargs):
        invocations.append(kwargs['stock_code']); return original(**kwargs)
    monkeypatch.setattr(cninfo, 'fetch_cninfo_disclosures', tracked)
    monkeypatch.setattr(cninfo, 'fetch_cninfo_pdf_bytes', lambda **_: pytest.fail('directory must not download PDFs'))
    request, calls = announcement_client(total=35)
    result = run_announcements(tmp_path, request, ids=['selected-0'])
    assert result['status'] == 'CAPTURED_REQUIRES_SOURCE_REVIEW' and len(calls) == 3
    assert invocations == ['600001'] and result['pdf_requests'] == 0 and result['research_executed'] is False
    item = result['outcomes'][0]
    assert len(item['announcements']) == 35 and item['announcements'][0]['announcement_id'] == '1'
    assert item['announcements'][0]['source_locator'] == 'https://static.cninfo.com.cn/finalpage/2098-12-31/1.PDF'
    target=tmp_path/'out/600001.SH'
    assert {p.name for p in target.iterdir()} == {'plan.json','summary.md','receipt.json',
        'query-1.body','query-1.json','query-2.body','query-2.json','query-3.body','query-3.json'}
    for ordinal, record in enumerate(item['requests'],1):
        raw=(target/f'query-{ordinal}.body').read_bytes()
        assert record['response']['sha256'] == sha256(raw).hexdigest()
        assert json.loads((target/f'query-{ordinal}.json').read_bytes()) == record
        assert record['endpoint'].startswith('https://www.cninfo.com.cn/')
    assert [f['pageNum'] for k,f in calls if k=='announcements'] == ['1','2']
    assert all(f['column']=='szse' and f['category']=='' for k,f in calls if k=='announcements')
    assert (target/'plan.json').read_bytes() == (tmp_path/'out/plan.json').read_bytes()
    assert '原件链接不是PDF已下载' in (target/'summary.md').read_text()
    proposal=json.loads((tmp_path/'out/registration-proposal.json').read_bytes())
    assert proposal['directory']=='docs/readings/b2-announcements-123456789-1'
    record=proposal['references'][0]
    assert record['archive_source']['ref'] is None and record['use']=='NAVIGATION_ONLY'
    assert record['read_policy']=='ON_DEMAND_ARCHIVE' and 'source' not in record
    assert len(list(target.iterdir()))<=16
    with pytest.raises(FileExistsError): run_announcements(tmp_path,request,ids=['selected-0'])
    assert len(calls)==3


def test_announcement_page_budget_preserves_partial_raw_and_does_not_infer_zero(tmp_path):
    request,calls=announcement_client(total=95)
    result=run_announcements(tmp_path,request,ids=['selected-0'])
    assert len(calls)==4 and [f['pageNum'] for k,f in calls if k=='announcements']==['1','2','3']
    item=result['outcomes'][0]
    assert item['status']=='DIRECTORY_PAGE_LIMIT_RAW_RETAINED' and item['announcements'] is None
    assert result['status']=='CAPTURED_WITH_GAPS'
    assert len(json.loads((tmp_path/'out/600001.SH/query-4.body').read_bytes())['announcements'])==30
    assert '公告数量未知，不记零' in (tmp_path/'out/600001.SH/summary.md').read_text()


def test_announcement_null_and_empty_remain_distinct_raw_bounded_directory_results(tmp_path):
    request,calls=announcement_client(total=0,null_code='688001')
    result=run_announcements(tmp_path,request,ids=['selected-0','selected-1'])
    assert len(calls)==4 and all(o['status']=='EMPTY_DIRECTORY_NOT_NO_EVENTS' for o in result['outcomes'])
    assert json.loads((tmp_path/'out/600001.SH/query-2.body').read_bytes())['announcements']==[]
    assert json.loads((tmp_path/'out/688001.SH/query-2.body').read_bytes())['announcements'] is None
    assert [o['page_shapes'][0]['table_kind'] for o in result['outcomes']]==['LIST','NULL']


@pytest.mark.parametrize('http',[302,403,429,503])
def test_announcement_failure_stops_other_objects_without_fake_queries_or_secret_text(tmp_path,http):
    request,calls=announcement_client(http=http)
    result=run_announcements(tmp_path,request)
    assert result['status']=='STOPPED_WITH_GAPS' and len(calls)==1
    for item in result['outcomes'][1:]:
        target=tmp_path/'out'/item['code']
        assert item['announcements'] is None and item['receipt'] is None
        assert {p.name for p in target.iterdir()}=={'plan.json','summary.md'}
    assert (tmp_path/'out/600001.SH/query-1.body').exists()


def test_announcement_original_parser_rejects_duplicate_ids_changed_totals_and_foreign_identity(tmp_path):
    def duplicate(value,number):
        if number==2: value['announcements'][0]['announcementId']='1'
    def total_drift(value,number):
        if number==2: value['totalAnnouncement']+=1
    mutations=[duplicate,total_drift,
        lambda v,n:v['announcements'][0].pop('secCode'),
        lambda v,n:v['announcements'][0].update(secCode='600002'),
        lambda v,n:v.update(success=False),
        lambda v,n:v.update(hasMore=not v['hasMore']),
        lambda v,n:v['announcements'][0].update(announcementTime=1)]
    for i,mutate in enumerate(mutations):
        folder=tmp_path/str(i);folder.mkdir()
        request,calls=announcement_client(total=35,damage=mutate)
        result=run_announcements(folder,request,ids=['selected-0','selected-1'])
        assert result['status']=='STOPPED_WITH_GAPS'
        assert result['outcomes'][0]['announcements'] is None
        assert result['outcomes'][1]['status']=='NOT_QUERIED_AFTER_STOP'
        assert (folder/'out/600001.SH/query-2.body').exists()
        assert not (folder/'out/688001.SH/query-1.body').exists()


def test_announcement_missing_publication_clock_is_unknown_not_midnight(tmp_path):
    request,calls=announcement_client(damage=lambda v,n:v['announcements'][0].update(announcementTime=None))
    result=run_announcements(tmp_path,request,ids=['selected-0'])
    assert len(calls)==2 and result['status']=='CAPTURED_WITH_GAPS'
    assert result['outcomes'][0]['announcements'][0]['source_announcement_time'] is None


def test_announcement_invalid_window_fails_before_http_or_output(tmp_path):
    for start,end in [('2099-01-02','2099-01-02'),('bad','2098-12-31'),('2098-12-31','2098-12-30'),
                      ('2096-01-01','2098-12-31')]:
        request,calls=announcement_client()
        with pytest.raises(ValueError,match='B2_PUBLICATION_WINDOW'):
            run_announcements(tmp_path,request,start=start,end=end)
        assert calls==[] and not (tmp_path/'out').exists()


def test_announcement_transport_is_fixed_https_form_without_cookies_credentials_or_redirects():
    calls=[]
    class Response:
        status_code=200;headers={}
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def iter_content(self,chunk_size):yield b'[]'
    class Session:
        trust_env=True
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,**kwargs):
            assert self.trust_env is False and kwargs['allow_redirects'] is False
            assert 'data' in kwargs and 'params' not in kwargs
            assert not {'Authorization','Cookie','X-API-Key'} & set(kwargs['headers'])
            calls.append(url);return Response()
    for kind in ('organization','announcements'):
        b2['public_request']({},kind=kind,clock=lambda:NOW,session_factory=Session)
    assert calls==list(b2['ANNOUNCEMENT_URLS'].values())
    with pytest.raises(ValueError,match='B2_SOURCE_KIND'):
        b2['public_request']({},kind='https://untrusted.invalid',session_factory=Session)
    assert len(calls)==2


def test_cli_source_modes_require_their_own_inputs_before_execution(tmp_path,monkeypatch):
    import sys
    base=['b2','--output',str(tmp_path/'out'),'--reference-ids','selected-0']
    for suffix in [[],['--source-kind','announcements'],['--report-period',PERIOD,'--start-date','2098-12-31'],
                   ['--source-kind','announcements','--start-date','2098-12-31','--end-date','2098-12-31','--report-period',PERIOD]]:
        monkeypatch.setattr(sys,'argv',base+suffix)
        with pytest.raises(SystemExit) as error:b2['main']()
        assert error.value.code==2 and not (tmp_path/'out').exists()
