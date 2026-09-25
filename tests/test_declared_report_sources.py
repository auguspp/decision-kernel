"""Source-only round trips: real PDF parser/Retainer, synthetic HTTP/Git boundaries."""
from copy import deepcopy
import json
from pathlib import Path
import socket

import pytest
import requests

from decision_kernel.runtime import declared_report_sources as s
from test_woton_report_custody import API, Retainer, synthetic_pdf, CODE

ROOT = Path(__file__).parents[1]
AT = '2026-09-22T16:00:00Z'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs): raise AssertionError('offline regression')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)


def setup(monkeypatch):
    plan = json.loads((ROOT / s.REQUEST).read_bytes())
    plan['reports'] = [plan['reports'][1]]
    plan['reports'][0]['cninfo_locator'] = 'https://static.cninfo.com.cn/finalpage/2026-08-26/1234567890.PDF'
    # Reuse the generic native-Git simulator; no retired Woton writer state.
    monkeypatch.setattr(s.once, 'now', lambda: AT)
    api = API(request_path=s.REQUEST, scope=plan, permission=plan['permission'],
              prefix=s.ROOT + plan['batch_id'] + '/')
    api.comment['body'] = (ROOT / 'tests/fixtures/declared_report_sources_permission.txt').read_text()
    raw = synthetic_pdf(pages=2, title='600362 2026 ABCDE')
    return plan, api, raw


def execute(tmp_path, api, fetch, **kw):
    return s.run(api=api, code=CODE, output=tmp_path/'out', clock=lambda: AT,
                 fetch=fetch, retainer_factory=Retainer, **kw)


def html(plan, href=None):
    row = plan['reports'][0]
    link = href or f'https://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESH_STOCK/2026/2026-8/2026-08-26/{row["sina_id"]}.PDF'
    return f'<html><meta charset="utf-8"><h1>600362 江西铜业：2026年半年度报告</h1><p>公告日2026-08-26</p><a href="{link}">下载公告</a></html>'.encode()


def test_large_public_pdf_is_retained_before_parsing_without_research_and_not_reacquired(tmp_path, monkeypatch):
    plan, api, raw = setup(monkeypatch)
    calls = []
    def fetch(url, limit):
        calls.append(url)
        assert api.prefix + 'prepare.json' in api.versions[api.head]
        return 200, raw
    result = execute(tmp_path, api, fetch)
    assert result['status'] == 'DECLARED_REPORTS_RETAINED_NOT_RESEARCH', result
    assert len(calls) == 1 and result['model_calls'] == result['research_executions'] == 0
    assert len(raw) > 1024 * 1024
    selected = result['reports'][0]['routes'][0]
    assert selected['page_count'] == 2 and selected['provenance'] == 'CNINFO_ISSUER_REPORT'
    assert api.versions[api.head][selected['pdf_source']['path']] == raw
    assert api.versions[api.head]['old-research/failure.json'] == b'ORIGINAL_FAILURE'
    saved = deepcopy(api.versions)
    def forbid(*args): raise AssertionError('duplicate acquisition')
    again = s.run(api=api, code=CODE, output=tmp_path/'again', clock=lambda: AT,
                  fetch=forbid, retainer_factory=Retainer)
    assert again['status'] == 'EXISTING_SOURCE_ATTEMPT_NOT_REACQUIRED' and api.versions == saved
    assert not any('/candidates/' in name or '/daily-stock-questions-v0/' in name for name in api.writes)


def test_mirror_uses_actual_matching_page_link_and_keeps_original_http_failure(tmp_path, monkeypatch):
    plan, api, raw = setup(monkeypatch)
    calls = []
    def fetch(url, limit):
        calls.append(url)
        if 'static.cninfo.com.cn' in url: return 403, b'forbidden'
        if 'vip.stock' in url: return 200, html(plan)
        return 200, raw
    result = execute(tmp_path, api, fetch)
    assert result['status'] == 'DECLARED_REPORTS_RETAINED_NOT_RESEARCH', result
    record = result['reports'][0]
    assert record['selected_source'] == 'sina' and len(calls) == 3
    assert record['routes'][0]['status'] == 'SOURCE_UNAVAILABLE'
    assert result['requests'][0]['http_status'] == 403
    assert record['routes'][1]['provenance'] == 'ISSUER_REPORT_VIA_SINA_NOT_CNINFO_BYTE_EQUIVALENCE'
    assert (tmp_path/'out/2026H1-cninfo-source.pdf').read_bytes() == b'forbidden'


def test_reuses_original_discovery_callable_for_unknown_official_locator(tmp_path, monkeypatch):
    plan, api, raw = setup(monkeypatch)
    api.scope['reports'][0]['cninfo_locator'] = None
    calls = []
    def discover(**kw):
        calls.append(kw)
        return {'status': 'OFFICIAL_REPORT_LOCATED_NOT_ACQUIRED', 'official_report': {
            'stock_code': '600362', 'source_locator': 'https://static.cninfo.com.cn/finalpage/2026-08-26/1234567890.PDF'}}
    result = execute(tmp_path, api, lambda url, limit: (200, raw), discover=discover)
    assert result['status'] == 'DECLARED_REPORTS_RETAINED_NOT_RESEARCH', result
    assert len(calls) == 1 and calls[0]['period'] == '2026H1' and calls[0]['ticker'] == '600362'


@pytest.mark.parametrize('fault', ['permission', 'unsafe_batch', 'foreign_url', 'duplicate_period', 'expired',
                                    'prepare_lost', 'pdf_lost', 'wrong_issuer', 'wrong_period', 'half_year_not_annual', 'parse_failure'])
def test_failures_do_not_spend_model_or_reset_history(tmp_path, monkeypatch, fault):
    plan, api, raw = setup(monkeypatch)
    calls = []
    if fault == 'permission': api.comment['body'] += ' revoked'
    elif fault == 'unsafe_batch': api.scope['batch_id'] = '../unsafe'
    elif fault == 'foreign_url': api.scope['reports'][0]['cninfo_locator'] = 'https://evil.invalid/report.pdf'
    elif fault == 'duplicate_period': api.scope['reports'] *= 2
    elif fault == 'expired': api.scope['execute_before'] = AT
    elif fault in {'prepare_lost', 'pdf_lost'}:
        api.fail_name = 'prepare.json' if fault == 'prepare_lost' else '2026H1-cninfo-source.pdf'
        api.fail_after_write = True
    elif fault == 'wrong_issuer': raw = synthetic_pdf(pages=2, title='000920 2026 ABCDE')
    elif fault == 'wrong_period': raw = synthetic_pdf(pages=2, title='600362 2025 ABCDE')
    elif fault == 'half_year_not_annual':
        api.scope['reports'][0].update(period='2025FY', announcement_date='2026-08-26')
        raw = synthetic_pdf(pages=2, title='600362 2025 ABCDE')
    elif fault == 'parse_failure': raw = b'%PDF-1.7 broken'
    def fetch(url, limit):
        calls.append(url)
        return (200, raw) if 'static.cninfo' in url else (503, b'unavailable')
    result = execute(tmp_path, api, fetch)
    assert result['status'] in {'SOURCE_GAPS', 'SOURCE_PREPARATION_INCOMPLETE'}, result
    assert api.versions[api.head]['old-research/failure.json'] == b'ORIGINAL_FAILURE'
    if fault in {'permission', 'unsafe_batch', 'foreign_url', 'duplicate_period', 'expired'}:
        assert not calls and not api.writes
    if fault in {'prepare_lost', 'pdf_lost'}:
        assert result['mutation_uncertain'] and len(calls) == (0 if fault == 'prepare_lost' else 1)
        if fault == 'pdf_lost':
            assert result['requests'][0]['sha256'] == s.once.sha(raw)
            assert result['reports'][0]['routes'][0]['pdf_sha256'] == s.once.sha(raw)
    if fault in {'wrong_issuer', 'wrong_period', 'parse_failure'}:
        assert api.versions[api.head][api.prefix + '2026H1-cninfo-source.pdf'] == raw
    assert not any('/candidates/' in name for name in api.writes)


@pytest.mark.parametrize('href', ['https://evil.invalid/12535637.PDF', 'javascript:alert(1)',
    'https://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESH_STOCK/2026/2026-8/2026-08-26/OTHER.PDF',
    'https://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESH_STOCK/2026/2026-8/2026-08-26/12535637.PDF?redirect=1'])
def test_page_cannot_redirect_or_invent_another_document(monkeypatch, href):
    plan, _, _ = setup(monkeypatch)
    with pytest.raises(ValueError): s.sina_locator(html(plan, href), plan['reports'][0], plan['subject'], plan['issuer_name'])


def test_partial_transport_body_survives_and_no_retry(tmp_path, monkeypatch):
    plan, api, _ = setup(monkeypatch)
    calls = []
    def fetch(url, limit):
        calls.append(url)
        if 'static.cninfo' in url: raise s.SourceFetchError(b'%PDF partial', 200)
        return 503, b'unavailable'
    result = execute(tmp_path, api, fetch)
    assert result['status'] == 'SOURCE_GAPS' and len(calls) == 2
    assert (tmp_path/'out/2026H1-cninfo-source.pdf.partial').read_bytes() == b'%PDF partial'
    assert result['requests'][0]['status'] == 'PARTIAL_HTTP_BODY_NOT_COMPLETE'


def test_request_and_source_job_do_not_activate_old_research_or_add_secrets():
    plan = json.loads((ROOT / s.REQUEST).read_bytes())
    body = (ROOT / 'tests/fixtures/declared_report_sources_permission.txt').read_bytes()
    assert s.once.sha(body) == plan['permission']['body_sha256']
    assert s.check_request(plan, lambda: AT) == plan
    workflow = (ROOT / '.github/workflows/stock-business-research.yml').read_text()
    before, rest = workflow.split('\n  prepare-declared-report-sources:', 1)
    job, after = rest.split('\n  deepseek-compatibility:', 1)
    old_jobs = before + '\n  deepseek-compatibility:' + after
    # Protect isolation semantics, not an obsolete byte hash of unrelated jobs.
    assert s.LABEL not in old_jobs and 'declared-report-output/' not in old_jobs
    assert 'retain-public-report-source' not in workflow and 'retain-report-source' not in workflow
    assert 'secrets.' not in job
    assert "types: [labeled]" in old_jobs and 'schedule:' not in workflow
    assert "group: stock-business-first-v0" in old_jobs
    assert 'declared-report-output/' in job and "[documents,feeds]" in job
    assert 'research-api' not in job and "github.event.issue.number == 297" in job


@pytest.mark.parametrize('scheme', ['http:', ''])
def test_real_page_link_may_be_protocol_relative_or_same_host_https_upgraded(monkeypatch, scheme):
    plan, _, _ = setup(monkeypatch)
    link = scheme + '//file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESH_STOCK/2026/2026-8/2026-08-26/12535637.PDF'
    actual = s.sina_locator(html(plan, link), plan['reports'][0], plan['subject'], plan['issuer_name'])
    assert actual == ('https:' + link.split(':', 1)[1] if scheme else 'https:' + link)


@pytest.mark.parametrize('partial', [False, True])
def test_original_requests_boundary_is_credential_free_bounded_and_non_retrying(monkeypatch, partial):
    calls = []
    url = 'https://static.cninfo.com.cn/finalpage/2026-08-26/1234567890.PDF'
    class Response:
        status_code = 200
        headers = {'Content-Length': '3'}
        def __init__(self): self.url = url
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, size):
            yield b'abc'
            if partial: raise requests.exceptions.ReadTimeout('synthetic')
    class Session:
        trust_env = True
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, target, **kw):
            calls.append((target, kw))
            assert self.trust_env is False and target == url
            assert kw == {'timeout': (15, 60), 'stream': True, 'allow_redirects': False,
                          'headers': {'Accept-Encoding': 'identity'}}
            return Response()
    monkeypatch.setattr(s.requests, 'Session', Session)
    if partial:
        with pytest.raises(s.SourceFetchError) as caught: s.public_get(url, 100)
        assert caught.value.body == b'abc' and caught.value.status == 200
    else:
        assert s.public_get(url, 100) == (200, b'abc')
    assert len(calls) == 1


@pytest.mark.parametrize('field', ['GITHUB_REPOSITORY', 'GITHUB_REF', 'GITHUB_SHA', 'GITHUB_WORKFLOW',
    'GITHUB_RUN_ATTEMPT', 'GITHUB_RUN_ID', 'GITHUB_EVENT_NAME', 'SOURCE_ACTION', 'SOURCE_ISSUE',
    'SOURCE_LABEL', 'SOURCE_SENDER', 'SOURCE_IS_PR'])
def test_native_source_identity_rejected_before_any_git_or_public_io(tmp_path, monkeypatch, field):
    env = {'GITHUB_REPOSITORY': s.once.REPO, 'GITHUB_REF': 'refs/heads/main', 'GITHUB_SHA': CODE,
        'GITHUB_WORKFLOW': 'stock-business-research', 'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_RUN_ID': '42',
        'GITHUB_EVENT_NAME': 'issues', 'SOURCE_ACTION': 'labeled', 'SOURCE_ISSUE': '297',
        'SOURCE_LABEL': s.LABEL, 'SOURCE_SENDER': 'auguspp', 'SOURCE_IS_PR': 'false'}
    for key, value in env.items(): monkeypatch.setenv(key, value)
    monkeypatch.setenv(field, 'wrong')
    def forbid(*args, **kw): raise AssertionError('rejected event reached Git')
    monkeypatch.setattr(s, 'GitHubAPI', forbid)
    with pytest.raises(ValueError): s.main(['--code-commit', CODE, '--output', str(tmp_path/'out')])
    assert not (tmp_path/'out').exists()
