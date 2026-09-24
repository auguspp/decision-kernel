"""Synthetic official-transport composition and declared full-body source scope."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import json
from types import SimpleNamespace

import pytest

from decision_kernel.adapters.cninfo import CninfoAnnouncement
from decision_kernel.runtime import cninfo_http as cninfo
from decision_kernel.runtime import stock_research_sources as sources
from decision_kernel.runtime import saved_research_once as once
from test_pdf_text import _pdf_with_text_pages

NOW='2026-09-13T04:00:00+00:00'


def row(identifier,title,stamp='2026-08-29T00:00:00+08:00'):
    return CninfoAnnouncement(identifier,'600184','synthetic-org',title,'定期报告',
        datetime.fromisoformat(stamp) if stamp else None,'https://static.cninfo.com.cn/'+identifier+'.PDF')


def batch(*rows):
    return cninfo.CninfoDisclosureBatch('600184','synthetic-org',date(2025,8,9),date(2026,9,13),tuple(rows))


def test_latest_period_not_republication_date_and_all_subsequent_disclosures():
    half=row('half','2026年半年度报告')
    old_correction=row('old','2025年年度报告（更正后）','2026-09-12T00:00:00+08:00')
    risk=row('risk','诉讼及风险事项','2026-09-11T00:00:00+08:00')
    report,selected=sources.choose(batch(half,old_correction,risk),checked_at=NOW)
    assert report==half
    assert {r.announcement_id for r in selected}=={'half','old','risk'}


def test_summaries_not_full_reports_and_newest_version_selected():
    a=row('a','2026年半年度报告')
    b=row('b','2026年半年度报告（修订版）','2026-08-30T00:00:00+08:00')
    summary=row('summary','2026年半年度报告摘要','2026-08-31T00:00:00+08:00')
    selected,items=sources.choose(batch(a,b,summary),checked_at=NOW)
    assert selected==b and items==[a,b,summary]


@pytest.mark.parametrize('rows',[
    [],[row('s','2026年半年度报告摘要')],
    [row('a','2026年半年度报告'),row('b','2026年半年度报告（更新）')],
    [row('a','2026年半年度报告',None)],
    [row('a','2026年半年度报告','2026-09-14T00:00:00+08:00')],
    [row('a','2026年年度报告')],
    [row('a','2026年半年度报告')]+[row(str(n),'风险公告') for n in range(32)]
])
def test_incomplete_ambiguous_future_and_overcapacity_sources_are_gaps(rows):
    with pytest.raises(ValueError): sources.choose(batch(*rows),checked_at=NOW)


def setup_capture(tmp_path,monkeypatch,*,problem=None):
    rows=[{'announcementId':'report','announcementTitle':'2026年半年度报告','announcementTypeName':'定期报告',
        'announcementTime':1787932800000,'adjunctUrl':'finalpage/2026-08-29/report.PDF',
        'secCode':'600184','orgId':'synthetic-org'},
        {'announcementId':'risk','announcementTitle':'风险公告','announcementTypeName':'其他',
        'announcementTime':1787932800000,'adjunctUrl':'finalpage/2026-08-29/risk.PDF',
        'secCode':'600184','orgId':'synthetic-org'}]
    calls=[]
    def query(**kw):
        calls.append(kw)
        if problem=='transport':raise cninfo.CninfoRuntimeError('SYNTHETIC_PRIVATE_ERROR')
        if kw['url']==cninfo.CNINFO_STOCK_MAP_URL:
            assert kw['method']=='POST'
            assert kw['form']=={'keyWord':'600184','maxNum':'10'}
            return [{'code':'600184','orgId':'synthetic-org'}]
        assert kw['url']==cninfo.CNINFO_ANNOUNCEMENT_QUERY_URL and kw['method']=='POST'
        if problem=='foreign':rows[0]['secCode']='300183'
        return {'totalAnnouncement':len(rows),'announcements':rows}
    monkeypatch.setattr(cninfo,'_request_json',query)
    pdf=_pdf_with_text_pages('Synthetic 600184 report')
    def fetch_pdf(**kw):
        calls.append(kw)
        return pdf if problem!='invalid_pdf' else b'not a PDF'
    def extract(data,**kwargs):
        if problem=='invalid_pdf':
            return sources.extract_pdf_text(data,**kwargs)
        text='证券代码：600184 半年度报告；收入、利润、现金流与风险的合成文字。'
        if problem=='wrong_header':text='证券代码：300183 半年度报告'
        if problem=='oversize':text+='x'*(sources.CONTEXT_BYTES+1)
        return SimpleNamespace(pdf_sha256=once.sha(data),text_sha256=once.sha(text.encode()),
            page_count=1,pages=[SimpleNamespace(page_number=1,text=text)])
    args={'ticker':'600184','observation':{'market_session':'2026-09-11'},'api':None,
          'code_commit':'a'*40,'output':tmp_path/'sources','clock':lambda:NOW,
          'fetch_pdf':fetch_pdf,'extract':extract}
    return args,calls,pdf


def test_original_cninfo_identity_and_every_selected_body_no_model(tmp_path,monkeypatch):
    args,calls,pdf=setup_capture(tmp_path,monkeypatch)
    value,reads,journal=sources.capture(**args)
    assert [r['identity'] for r in reads]==['600184:report','600184:risk']
    assert value['issuer_inventory']['org_id']=='synthetic-org'
    assert len(value['issuer_documents'])==2 and all(len(d['pages'])==1 for d in value['issuer_documents'])
    assert (args['output']/(once.sha(pdf)+'.pdf')).read_bytes()==pdf
    assert len(journal['decoded_query_events'])==2
    assert all(e['representation']=='DECODED_TOOL_RETURN_NOT_WIRE_BYTES' for e in journal['decoded_query_events'])
    assert 'no clipping' not in value['issuer_documents'][0]['pages'][0]['text']
    assert (args['output']/'source-journal.json').exists()


@pytest.mark.parametrize('problem',['transport','foreign','invalid_pdf','wrong_header','oversize'])
def test_no_title_only_or_truncated_success_on_failed_sources(tmp_path,monkeypatch,problem):
    args,calls,pdf=setup_capture(tmp_path,monkeypatch,problem=problem)
    with pytest.raises((ValueError, RuntimeError)):sources.capture(**args)
    journal=(args['output']/'source-journal.json').read_text()
    assert 'SYNTHETIC_PRIVATE_ERROR' not in journal
    assert 'scope' in json.loads(journal)


def test_same_pdf_alternate_representation_receives_original_locator(tmp_path,monkeypatch):
    from decision_kernel.runtime import disclosure_source_reading as page_reading
    args,calls,pdf=setup_capture(tmp_path,monkeypatch)
    def damaged(data,**kw):
        return SimpleNamespace(pdf_sha256=once.sha(data),text_sha256='e'*64,page_count=1,
                               pages=[SimpleNamespace(page_number=1,text='damaged\x01')])
    args['extract']=damaged
    def represent(data,evidence,**kw):
        assert data==pdf and evidence['source_locator'].endswith('report.PDF')
        assert evidence['pages'][0]['text']=='damaged\x01'
        raise once.TrialError('required page visual review unavailable')
    monkeypatch.setattr(page_reading,'represent',represent)
    with pytest.raises(ValueError,match='visual review'):sources.capture(**args)
    assert (args['output']/(once.sha(pdf)+'-extraction.json')).exists()


def test_finite_prompt_bound_defaults_remain_shared():
    import inspect
    assert inspect.signature(once.model_call).parameters['max_prompt_bytes'].default is None
    assert once.MAX_PROMPT_BYTES==128*1024


def test_report_revision_does_not_erase_intervening_risk():
    original=row('original','2026年半年度报告')
    risk=row('risk','重大诉讼及风险公告','2026-09-11T00:00:00+08:00')
    revision=row('revision','2026年半年度报告（修订版）','2026-09-12T00:00:00+08:00')
    latest, selected=sources.choose(batch(original,risk,revision),checked_at=NOW)
    assert latest==revision
    assert [r.announcement_id for r in selected]==['original','risk','revision']
