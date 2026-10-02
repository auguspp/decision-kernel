"""Offline source-only contracts. Synthetic pages are not real source acceptance."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json

import pytest
import requests

from decision_kernel.runtime import broker_report_discovery as d

NOW = '2026-10-02T06:30:00+00:00'
S = d.scope('industry', '2026-09-01', '2026-09-30', 4)
ROW = {'infoCode': 'AP202609301234567890', 'title': 'PCB / AI服务器行业研究',
       'orgSName': '测试券商', 'orgCode': '123', 'industryCode': '456',
       'industryName': '电子', 'publishDate': '2026-09-30 00:00:00.000', 'emRatingName': '中性'}


def body(rows=None, page=1, total=None, **extra):
    rows = [deepcopy(ROW)] if rows is None else rows
    total = len(rows) if total is None else total
    return d.encoded({'data': rows, 'hits': total, 'TotalPage': (total + 49) // 50,
                      'pageNo': page, **extra})


def run(tmp_path, fetch=None, selected=S):
    calls = []
    def transport(req, scope):
        calls.append(deepcopy(req))
        return fetch(req) if fetch else (200, body())
    root = tmp_path / 'capture'
    result = d.capture(root, selected, transport=transport, clock_fn=lambda: NOW, sleep=lambda _: None)
    assert result == d.replay(root, result['capture_hash'])
    return root, result, calls


def reseal(meta):
    meta['capture_hash'] = d.canonical_hash({k: v for k, v in meta.items() if k != 'capture_hash'})
    return meta


@pytest.mark.parametrize('kind,route,qtype', [('industry','list','1'), ('strategy','jg','2'),
                                            ('macro','jg','3'), ('morning','jg','4')])
def test_type_mapping_and_bounded_plan(kind, route, qtype):
    selected = d.scope(kind, S['begin'], S['end'], 2)
    req = d.spec(selected, 2)
    assert req['url'] == 'https://reportapi.eastmoney.com/report/' + route
    assert req['params']['qType'] == qtype and req['params']['pageNo'] == '2'
    assert req['params']['pageSize'] == '50'
    assert 'code' not in req['params'] and 'list2' not in req['url']


@pytest.mark.parametrize('change', [{'kind':'stock'}, {'pages':0}, {'pages':5}, {'pages':True},
    {'begin':'2026-01-01'}, {'begin':'2026-09-31'}, {'begin':'20260901'}, {'end':'2026-08-01'},
    {'industry_code':'../secret'}, {'industry_code':'456','kind':'macro'}])
def test_bad_scope(change):
    with pytest.raises((ValueError, TypeError)):
        d.scope(**{**S, **change})


def test_real_capture_replay_code_with_synthetic_page_and_readonly_search(tmp_path):
    root, result, calls = run(tmp_path)
    assert len(calls) == 1 and result['unique_reports'] == 1
    assert result['coverage'] == 'PROVIDER_PAGES_READ_NOT_CORPUS_COMPLETENESS'
    assert result['window_completeness'] == 'NOT_ESTABLISHED'
    assert all(result[k] == v for k, v in d.AUTHORITY.items())
    item = result['records'][0]
    assert item['publication_date'] == '2026-09-30' and item['acquired_at'] == NOW
    assert item['historical_available_at'] == 'NOT_ESTABLISHED'
    assert item['detail_status'] == 'UNFETCHED_LOCATOR'
    assert item['source_rows'][0]['sha256'] == sha256((root/'page-1.body').read_bytes()).hexdigest()
    before = deepcopy(result)
    for word in ('pcb', '测试券商', '电子'):
        assert d.search(result, word)['filter']['matched_versions'] == 1
    assert d.search(result, '无匹配')['records'] == [] and result == before


def test_actual_two_page_path(tmp_path):
    rows = [{**ROW, 'infoCode': f'AP{i:018d}'} for i in range(51)]
    def fetch(req):
        p = int(req['params']['pageNo'])
        return 200, body(rows[(p-1)*50:p*50], p, 51)
    _, result, calls = run(tmp_path, fetch)
    assert len(calls) == 2 and result['unique_reports'] == 51 and result['provider_pages'] == 2


def test_page_budget_does_not_assert_all_reports(tmp_path):
    _, result, calls = run(tmp_path, lambda _: (200, body([ROW]*50, total=100)), {**S,'pages':1})
    assert len(calls) == 1 and result['coverage'] == 'PAGE_BUDGET_REACHED'
    assert result['provider_total'] == 100 and result['duplicate_or_variant_rows'] == 49
    assert result['window_completeness'] == 'NOT_ESTABLISHED'


def test_duplicates_and_same_id_variants_have_all_raw_locations(tmp_path):
    _, result, _ = run(tmp_path, lambda _: (200, body([ROW, ROW, {**ROW, 'title':'修订标题'}])))
    assert result['returned_rows'] == 3 and result['unique_reports'] == 1 and result['versions'] == 2
    assert sorted(len(r['source_rows']) for r in result['records']) == [1, 2]


@pytest.mark.parametrize('status', [301, 302, 401, 403, 429, 500, 502])
def test_http_failure_is_retained_and_stops_no_retry(tmp_path, status):
    root, result, calls = run(tmp_path, lambda _: (status, b'refused'))
    assert len(calls) == 1 and result['records'] == [] and result['provider_total'] is None
    assert (root/'page-1.body').read_bytes() == b'refused'


@pytest.mark.parametrize('raw', [b'', b'{"data":[],"data":[]}', b'callback({"data":[]})',
    d.encoded({'data': [], 'total': 1}), body([], code=1), body([], code=False), body([], code='0'),
    body([], success=False), body([], pageNo=2), body([], TotalPage=7), b'{"data":NaN}'])
def test_unqualified_response_is_not_empty_success(tmp_path, raw):
    root, result, calls = run(tmp_path, lambda _: (200, raw))
    assert len(calls) == 1 and result['coverage'] == 'RETAINED_PAGE_UNQUALIFIED'
    assert result['failure_detail'] and result['provider_total'] is None
    assert (root/'page-1.body').read_bytes() == raw


def test_legitimate_empty_is_only_provider_empty_not_no_reports(tmp_path):
    _, result, _ = run(tmp_path, lambda _: (200, body([])))
    assert result['provider_total'] == 0 and result['records'] == []
    assert result['window_completeness'] == 'NOT_ESTABLISHED'


@pytest.mark.parametrize('change', [{'publishDate':'2026-08-31'}, {'publishDate':'2026-10-01'},
    {'publishDate':'2026-09-30T00:00:00Z'}, {'infoCode':None}, {'infoCode':'../bad'},
    {'title':None}, {'orgSName':'bad\nname'}])
def test_bad_row_retains_entire_page_and_does_not_partially_admit_it(tmp_path, change):
    _, result, calls = run(tmp_path, lambda _: (200, body([ROW, {**ROW, **change}])))
    assert len(calls) == 1 and result['records'] == []
    assert result['coverage'] == 'RETAINED_PAGE_UNQUALIFIED'


def test_industry_filter_mismatch_is_not_silently_ignored(tmp_path):
    _, result, _ = run(tmp_path, selected={**S,'industry_code':'777'})
    assert result['failure_detail'] == 'INDUSTRY_FILTER_MISMATCH'


def test_type_conflict_and_encoded_locator_are_not_laundered(tmp_path):
    row = {**ROW, 'infoCode':None, 'encodeUrl':'a+b/c==&x=1', 'column':'002001002123'}
    selected = {**S,'kind':'macro'}
    _, result, _ = run(tmp_path, lambda _: (200, body([row])), selected)
    item = result['records'][0]
    assert item['type_status'] == 'COLUMN_CONFLICT'
    assert 'encodeUrl=a%2Bb%2Fc%3D%3D%26x%3D1' in item['detail_url']
    assert d.search(result, 'PCB')['records'] == []


@pytest.mark.parametrize('kind,column', [('strategy','002001002123'), ('macro','002001001123'), ('morning','002003001123')])
def test_matching_column_is_still_only_discovery(tmp_path, kind, column):
    _, result, _ = run(tmp_path, lambda _: (200, body([{**ROW,'column':column}])), {**S,'kind':kind})
    assert result['records'][0]['type_status'] == 'COLUMN_MATCH'
    assert result['pdf_requests'] == 0


def test_denominator_drift_retains_first_page_but_stops(tmp_path):
    def fetch(req):
        p = int(req['params']['pageNo'])
        return 200, body([ROW]*50 if p==1 else [ROW]*2, p, 51 if p==1 else 52)
    _, result, calls = run(tmp_path, fetch)
    assert len(calls) == 2 and result['returned_rows'] == 50
    assert result['failure_detail'] == 'PAGE_DENOMINATOR_DRIFT'


def test_transport_exception_and_contract_failure_do_not_retry(tmp_path):
    def fail(_): raise requests.Timeout('untrusted error text')
    _, result, calls = run(tmp_path, fail)
    assert len(calls) == 1 and result['coverage'] == 'TRANSPORT_ERROR'
    _, result, calls = run(tmp_path/'second', lambda _: (200, b'x'*(d.MAX_BODY+1)))
    assert len(calls) == 1 and result['coverage'] == 'TRANSPORT_CONTRACT'


@pytest.mark.parametrize('mutation', ['body','catalog','summary','extra','hash','clock','request','authority'])
def test_replay_tampering(tmp_path, mutation):
    root, result, _ = run(tmp_path)
    expected = result['capture_hash']
    targets = {'body':'page-1.body','catalog':'catalog.json','summary':'summary.md','extra':'extra'}
    if mutation in targets:
        (root/targets[mutation]).write_bytes(b'changed')
    elif mutation == 'hash': expected = '0'*64
    else:
        meta = d.decode((root/'capture.json').read_bytes())
        if mutation == 'clock': meta['records'][0]['received_at'] = '2026-01-01T00:00:00Z'
        if mutation == 'request': meta['records'][0]['request']['params']['qType'] = '3'
        if mutation == 'authority': meta['authority']['investment_authority'] = 'YES'
        reseal(meta); expected = meta['capture_hash']
        (root/'capture.json').write_bytes(d.encoded(meta))
    with pytest.raises((ValueError, KeyError)):
        d.replay(root, expected)


def test_resealed_request_after_stop_is_rejected(tmp_path):
    root, result, _ = run(tmp_path, lambda _: (403, b'no'))
    meta = d.decode((root/'capture.json').read_bytes())
    extra = {**deepcopy(meta['records'][0]), 'request': d.spec(S, 2)}
    meta['records'].append(extra)
    with pytest.raises(ValueError, match='REQUEST_AFTER_STOP'):
        d.project(reseal(meta), {'page-1.body':b'no'})


def test_interrupted_capture_checkpoint_is_not_final(tmp_path):
    calls = []
    def fetch(req, selected):
        calls.append(req)
        if len(calls) == 2: raise KeyboardInterrupt()
        return 200, body([ROW]*50, total=51)
    root = tmp_path/'partial'
    with pytest.raises(KeyboardInterrupt):
        d.capture(root, S, transport=fetch, clock_fn=lambda:NOW, sleep=lambda _:None)
    meta = d.decode((root/'capture.json').read_bytes())
    assert meta['final'] is False
    result = d.replay(root, meta['capture_hash'])
    assert result['coverage'] == 'INTERRUPTED_OR_IN_PROGRESS' and result['returned_rows'] == 50


def test_create_only_symlinks_future_and_custody_write_failure(tmp_path, monkeypatch):
    root, _, _ = run(tmp_path)
    with pytest.raises(ValueError, match='OUTPUT_CREATE_ONLY'):
        d.capture(root, S, clock_fn=lambda:NOW)
    link = tmp_path/'link'; link.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError): d.replay(link, '0'*64)
    with pytest.raises(ValueError, match='FUTURE_WINDOW'):
        d.capture(tmp_path/'future', {**S,'end':'2026-10-03'}, clock_fn=lambda:NOW)
    assert not (tmp_path/'future').exists()
    original = Path.open
    def fail(self, *args, **kwargs):
        if self.name == 'page-1.body': raise PermissionError('disk failure')
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', fail)
    calls = []
    with pytest.raises(PermissionError):
        d.capture(tmp_path/'broken', S, transport=lambda *a:(calls.append(1) or (200,body())), clock_fn=lambda:NOW)
    assert len(calls) == 1


def test_fixed_transport_no_auth_redirect_proxy_or_unbounded_body():
    req = d.spec(S, 1); raw = body(); seen = []
    class Response:
        status_code = 200
        headers = {'Content-Length':str(len(raw))}
        url = requests.Request('GET',req['url'],params=req['params']).prepare().url
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def iter_content(self,size): yield raw
    class Session:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def get(self,url,**kwargs):
            assert self.trust_env is False and kwargs['allow_redirects'] is False
            assert kwargs['stream'] is True and kwargs['timeout'] == (10,20)
            assert not any(k.lower() in ('authorization','cookie','x-api-key') for k in kwargs['headers'])
            seen.append(url)
            return Response()
    assert d.request_raw(req,S,session_factory=Session) == (200,raw)
    with pytest.raises(ValueError,match='REQUEST_SPEC'):
        d.request_raw({**req,'url':'https://evil.invalid/'},S,session_factory=Session)
    Response.headers = {'Content-Length':str(d.MAX_BODY+1)}
    with pytest.raises(ValueError,match='BODY_SIZE'):
        d.request_raw(req,S,session_factory=Session)
    assert len(seen) == 2


def test_cli_plan_needs_no_network_and_summary_escapes_markdown(tmp_path, capsys):
    assert d.main(['plan','--kind','macro','--begin','2026-09-01','--end','2026-09-30']) == 0
    assert d.decode(capsys.readouterr().out.encode())['requests'][0]['params']['qType'] == '3'
    _, result, _ = run(tmp_path,lambda _:(200,body([{**ROW,'title':'[click](javascript:bad) <script>x</script>'}])))
    summary = d.render(result)
    assert '<script>' not in summary and '[click](javascript:bad)' not in summary
    with pytest.raises(SystemExit): d.main(['capture','--kind','industry'])


def test_source_numeric_and_string_versions_stay_distinct(tmp_path):
    rows = [{**ROW, 'provider_value': 1.25}, {**ROW, 'provider_value': '1.25'}]
    raw = json.dumps({'data':rows, 'hits':2, 'TotalPage':1, 'pageNo':1}).encode()
    _, result, _ = run(tmp_path, lambda _:(200,raw))
    assert result['unique_reports'] == 1 and result['versions'] == 2
    assert d.row_version(ROW) == d.row_version(dict(reversed(list(ROW.items()))))
