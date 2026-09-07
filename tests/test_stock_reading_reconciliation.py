"""Counterexamples migrated from local B; reference fixtures are not live evidence."""
import copy
from datetime import timedelta
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import stock_radar_reading as stock
from test_stock_radar_reading import prepared, synthetic_references, observe, NOW
from test_stock_radar_capture import setup
from test_sector_radar_audit import prohibit_network


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def test_missing_supplied_reference_cannot_be_certified_as_independent_reference():
    state,_,_,plan,_,_=prepared()
    code=plan['issuers'][0]['thscode']
    with pytest.raises(stock.StockReadingInputError) as exc:
        stock._qualify_references(code,state.sessions[-61:],{},None,NOW)
    assert exc.value.category=='DATA_INSUFFICIENT'
    assert exc.value.reason_code=='QUALIFIED_DAILY_REFERENCE_HISTORY_UNAVAILABLE'


def test_undocumented_prev_price_does_not_replace_required_current_quote():
    from test_hithink_stock_reading_integration import contract_provider
    state,plan,response,_=contract_provider(missing_quote=True)
    def changed(path,params):
        body=response(path,params)
        if path==stock.STOCK_HISTORY:
            for row in body['data']['item']:row['prev_price']='1'
        return body
    p=stock.observe_stock_reading(plan,state,request_json=changed,observed_at=NOW)['projection']
    assert p['status']=='NO_USABLE_STOCK_DATA' and not p['surfaced_stocks']
    assert p['coverage']['unavailable_issuers']==len(plan['issuers'])
    assert all(r['input_failure']['reason_code']=='REQUIRED_INPUT_OR_FIELD_MISSING'
               and r['stock_path'] is None for r in p['all_stock_observations'])


@pytest.mark.parametrize('kind',['missing_window','short_window','missing_latest','identity','day','order','reference_break',
    'close','volume','turnover','nontrading','future','unfinished','reversed','latest_mismatch','latest_identity',
    'latest_day','latest_future','latest_early','nan','float','bool','null','extra_identity'])
def test_b_reference_boundaries_remain_fail_closed(kind):
    state,_,_,plan,response,_=prepared()
    codes=[r['thscode'] for r in plan['issuers']]
    refs=synthetic_references(state,codes);code=codes[0]
    rows=refs['windows'][code];r=rows[20];q=refs['latest_quotes'][code]
    if kind=='missing_window':del refs['windows'][code]
    elif kind=='short_window':rows.pop(20)
    elif kind=='missing_latest':del refs['latest_quotes'][code]
    elif kind=='identity':r['thscode']='000001.SZ'
    elif kind=='day':r['market_session']=rows[19]['market_session']
    elif kind=='order':rows[19],rows[20]=rows[20],rows[19]
    elif kind=='reference_break':r['prev_price']='1'
    elif kind in {'close','volume','turnover'}:r[{'close':'last_price','volume':'volume','turnover':'turnover'}[kind]]='1'
    elif kind=='nontrading':r['turnover']='0'
    elif kind=='future':r['captured_at']=(NOW+timedelta(seconds=1)).isoformat()
    elif kind=='unfinished':r['captured_at']=r['market_session']+'T14:00:00+08:00'
    elif kind=='reversed':r['captured_at']=rows[19]['captured_at']
    elif kind=='latest_mismatch':q['turnover']='1'
    elif kind=='latest_identity':q['thscode']='000001.SZ'
    elif kind=='latest_day':q['market_session']=rows[-2]['market_session']
    elif kind=='latest_future':q['captured_at']=(NOW+timedelta(seconds=1)).isoformat()
    elif kind=='latest_early':q['captured_at']=rows[-2]['captured_at']
    elif kind=='nan':r['prev_price']='NaN'
    elif kind=='float':r['prev_price']=19.5
    elif kind=='bool':r['prev_price']=True
    elif kind=='null':r['prev_price']=None
    else:refs['windows']['000001.SZ']=copy.deepcopy(rows)
    with pytest.raises(ValueError):
        stock.observe_stock_reading(plan,state,request_json=response,observed_at=NOW,reference_inputs=refs)


def test_reference_and_source_origin_cannot_be_relabelled_live_before_requests(tmp_path):
    mod,_,out,calls,_,run=setup(tmp_path)
    with pytest.raises(ValueError,match='synthetic'):
        run(provenance=mod['PUBLIC'],credential='dummy-secret')
    assert not calls and not out.exists()


def test_missing_current_quote_produces_rebuildable_isolated_data_gap_page(tmp_path):
    from test_hithink_stock_reading_integration import contract_provider
    mod,_,out,_,_,run=setup(tmp_path)
    _,_,provider,calls=contract_provider(missing_quote=True)
    r=run(reference_inputs=None,transport=provider,provenance=mod['PUBLIC'],credential='dummy-secret')
    assert r['status']==mod['PARTIAL'] and r['failure_category'] is None
    p=mod['read'](out/'stock-reading.json')['projection']
    assert p['status']=='NO_USABLE_STOCK_DATA' and not p['surfaced_stocks']
    assert all(row['input_failure']['reason_code']=='REQUIRED_INPUT_OR_FIELD_MISSING'
               for row in p['all_stock_observations'])
    assert any(path==stock.STOCK_HISTORY for path,_ in calls)
    assert not (out/'synthetic-reference-inputs.json').exists()
    soup=BeautifulSoup((out/'index.html').read_text(),'html.parser')
    assert not soup.find_all('article') and '数据不可用' in soup.get_text()
    assert '不是完整检查后的零匹配' in soup.get_text()
    v=mod['verify'](out)
    assert v['coverage']==r['coverage'] and not v['coverage']['scope_complete']
    assert v['network_calls']==0 and v['stock_count']==0
    assert v['status']=='STOCK_BATCH_WITH_DATA_GAPS_REBUILT'


def test_http_success_with_business_failure_is_request_failure(tmp_path):
    mod,_,out,_,_,run=setup(tmp_path)
    r=run(transport=lambda *a:{'code':1003,'data':{}})
    assert r['failure_category']=='REQUEST_FAILED'
    assert r['reason_code']=='PROVIDER_BUSINESS_REQUEST_FAILED'
    assert r['requests'][0]['response_file']=='responses/01.json'
    assert mod['verify'](out)['reason_code']==r['reason_code']


def test_isolated_page_cannot_be_rehashed_into_success_or_renamed_plan(tmp_path):
    from test_hithink_stock_reading_integration import contract_provider
    mod,_,out,_,_,run=setup(tmp_path)
    _,_,provider,_=contract_provider(missing_quote=True)
    assert run(reference_inputs=None,transport=provider)['status']==mod['PARTIAL']
    r=mod['read'](out/'capture.json')
    r['planned_issuer_outcomes'][0]['company_name']='invented company'
    r['files']={k:v for k,v in mod['inventory'](out).items() if k!='capture.json'}
    r['capture_hash']=canonical_hash({k:v for k,v in r.items() if k!='capture_hash'})
    (out/'capture.json').write_bytes(mod['data'](r))
    with pytest.raises(ValueError,match='reconstruct'):mod['verify'](out)


def test_empty_business_scope_is_not_a_completed_no_match(monkeypatch):
    state,ledger,association,_,_,_=prepared()
    original=stock.company.build_company_links
    def unlinked(*args,**kwargs):
        report=copy.deepcopy(original(*args,**kwargs))
        for node in report['projection']['nodes']:node['companies']=[]
        report['projection_hash']=canonical_hash(report['projection'])
        return report
    monkeypatch.setattr(stock.company,'build_company_links',unlinked)
    from test_stock_radar_reading import ROOT
    plan=stock.prepare_stock_reading(ROOT,state,ledger,association,observed_at=NOW)
    calls=[]
    result=stock.observe_stock_reading(plan,state,request_json=lambda *args:calls.append(args),observed_at=NOW)
    p=result['projection']
    assert p['status']=='BUSINESS_COVERAGE_INSUFFICIENT' and not p['surfaced_stocks'] and not calls
    assert not p['fresh_context_revalidated']


def test_source_event_status_is_not_a_third_wake():
    report,plan,_=observe()
    p=report['projection']
    assert p['source_event_status']=='NO_NEW_RECORDED_SECTOR_EVENT_NOT_NO_STOCK_OPPORTUNITY'
    assert p['surfaced_stocks'] and not p['new_stock_event_created']
    for row in p['surfaced_stocks']:
        for origin in row['current_origins']:
            for source in origin['direction_sources']:
                assert source['source_kind']=='CURRENT_STRONG_PATH_NOT_A_NEW_EVENT'
                assert source['recorded_event_ids']==[]
    assert set(r['thscode'] for r in plan['evidence_scope_issuers'])=={'002714.SZ','600233.SH'}


def test_rehashed_duplicate_cards_are_not_rendered():
    report,_,_=observe()
    report['projection']['surfaced_stocks']*=2
    report['projection_hash']=canonical_hash(report['projection'])
    with pytest.raises(ValueError):stock.render_stock_reading(report)


def test_stock_workflow_secret_is_scoped_to_one_capture_step_only():
    text=Path('.github/workflows/hithink-stock-dump-trial.yml').read_text()
    job=text.split('  stock-reading:\n',1)[1].split('  theme-probe:\n',1)[0]
    capture=job.split('- name: Build stock-first observations',1)[1].split('- name: Rebuild stock selection',1)[0]
    assert capture.count('${{ secrets.HITHINK_FINANCE_API_KEY }}')==1
    assert job.count('${{ secrets.HITHINK_FINANCE_API_KEY }}')==1
    assert 'secrets.' not in text.split('jobs:\n',1)[0]
    assert "if: github.event_name == 'workflow_dispatch' && inputs.trial-purpose == 'stock-reading'" in job
    assert "HITHINK_FINANCE_API_KEY: ''" in job.split('- name: Rebuild stock selection',1)[1]
    assert 'persist-credentials: false' in job and 'contents: read' in job and 'actions: read' in job
    for word in ('schedule:', 'contents: write', 'continue-on-error', 'actions/cache', 'sector_radar_producer'):
        assert word not in job
