from __future__ import annotations

import copy
import gzip
import json
from datetime import datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import stock_radar_reading as stock
from decision_kernel.runtime.sector_radar_state import parse_sector_radar_market_state, serialize_sector_radar_market_state
from decision_kernel.runtime.sector_radar_events import create_sector_radar_candidate_event_ledger
from test_sector_radar_audit import SyntheticProvider, FRIDAY, ms, prohibit_network
from test_economic_company_context import ROOT, reading
from test_economic_market_context import NOW
from test_livestock_company_evidence import MANIFEST, copy_inputs


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def synthetic_references(state, codes, *, kind=None):
    """Explicit independent TEST fixtures, never a provider field or origin proof."""
    windows, latest = {}, {}
    for code in codes:
        rows=[]
        for i,day in enumerate(state.sessions[-61:]):
            close=Decimal(100-i) if kind=='falling' else Decimal(10)+Decimal('0.5')*i
            previous=close+1 if kind=='falling' else close-Decimal('0.5')
            rows.append({'thscode':code,'market_session':day.isoformat(),
                'captured_at':datetime.combine(day,datetime.min.time(),tzinfo=stock.SHANGHAI_TZ).replace(hour=15,minute=30).isoformat(),
                'last_price':str(close),'prev_price':str(previous),
                'volume':'0' if kind=='zero_volume' and i==60 else '100',
                'turnover':'0' if kind=='zero_turnover' and i==60 else str(10000+i*10)})
        windows[code]=rows
        latest[code]={**copy.deepcopy(rows[-1]),'captured_at':NOW.isoformat()}
    return {'provenance':stock.SYNTHETIC_REFERENCES,'windows':windows,'latest_quotes':latest}


@lru_cache(maxsize=1)
def _prepared_upstream():
    """Build the frozen shared inputs once; never cache the mutable plan.

    MarketState and the empty EventLedger are frozen dataclass graphs containing
    immutable tuples.  The association is copied for every caller below because
    several negative tests intentionally mutate it.  `stock.prepare_stock_reading`
    must stay outside this cache: issuer-isolation tests monkeypatch that callable
    and need every helper invocation to exercise the current wrapper.
    """
    raw = gzip.decompress((ROOT/'radar_inputs/sector-radar-state-bootstrap-2026-09-04.json.gz').read_bytes()).decode()
    state = parse_sector_radar_market_state(raw)
    ledger = create_sector_radar_candidate_event_ledger(created_at=NOW, source='SYNTHETIC_STOCK_READING_TEST')
    links = json.loads((ROOT/'radar_inputs/economic-market-links-v0.json').read_text())
    association = reading(state=state, ledger=ledger, links=links)
    return state, ledger, association


def prepared():
    state, ledger, frozen_association = _prepared_upstream()
    association = copy.deepcopy(frozen_association)
    plan = stock.prepare_stock_reading(ROOT, state, ledger, association, observed_at=NOW)
    base = SyntheticProvider(SimpleNamespace(market_state=state), session=FRIDAY)
    calls = []
    codes = [r['thscode'] for r in plan['issuers']]

    def response(path, params):
        calls.append((path, params))
        if path == stock.HITHINK_CALENDAR_PATH:
            # Explicit synthetic future sessions, not a real exchange-calendar proof.
            sessions = (*state.sessions, FRIDAY+timedelta(days=3), FRIDAY+timedelta(days=4))
            return {'code':0,'data':{'item':[{'date':d.strftime('%Y%m%d')} for d in sessions]}}
        if path == stock.indices.HITHINK_INDEX_CATALOG_PATH:
            return {'code':0,'data':{'timestamp':int(NOW.timestamp()*1000),'item':[
                {'thscode':r.thscode,'name':r.name} for r in state.series if r.thscode!=state.benchmark_thscode]}}
        if path == stock.members.HITHINK_SECTOR_CONSTITUENTS_PATH:
            return {'code':0,'data':{'timestamp':int(NOW.timestamp()*1000),'item':[
                {'thscode':c,'ticker':c[:6],'name':'Synthetic stock '+c} for c in codes]+[
                {'thscode':'600999.SH','ticker':'600999','name':'Unreviewed member'}]}}
        if path == stock.STOCK_HISTORY:
            return {'code':0,'data':{'thscode':params['thscode'],'interval':'1d','adjust':'none',
                'timestamp':ms(FRIDAY,0,0),'item':[
                    {'date_ms':ms(day,0,0),'close_price':str(Decimal(10)+Decimal('0.5')*i),
                     'volume':'100','turnover':str(10000+i*10)} for i,day in enumerate(state.sessions[-61:])]}}
        return base(path, params)
    return state, ledger, association, plan, response, calls


def observe(change=None, *, reference_kind=None):
    state, ledger, association, plan, response, calls = prepared()
    def altered(path, params):
        result = response(path,params)
        return change(path, params, result) if change else result
    refs=synthetic_references(state,[r['thscode'] for r in plan['issuers']],kind=reference_kind)
    result = stock.observe_stock_reading(plan,state,request_json=altered,observed_at=NOW,reference_inputs=refs)
    return result, plan, calls


def test_original_gates_and_business_sources_produce_actual_stock_cards_not_sector_cards():
    result,plan,calls = observe()
    p=result['projection']
    assert '002714.SZ' in [r['thscode'] for r in plan['issuers']]
    assert any(r['thscode']=='002714.SZ' for r in p['surfaced_stocks'])
    assert p['reviewed_issuers']==len(plan['issuers'])
    assert len(p['surfaced_stocks'])<=3 and p['active_directions_without_stock_business_scope']
    assert '600999.SH' in [r['thscode'] for r in p['unreviewed_current_members']]
    assert p['market_state_writes']==p['events_created']==0 and p['recommendation'] is None
    assert p['scope']=='CURATED_LINKS_ONLY_NOT_A_BLIND_ALL_STOCK_SCREEN'
    assert p['reference_input_provenance']=='SYNTHETIC_TEST_ONLY'
    assert p['live_stock_qualification']=='NOT_ESTABLISHED'
    assert not p['business_benefit_established']
    assert all(r['stock_path']['history_session_count']==61 for r in p['surfaced_stocks'])
    assert len(calls)<=plan['maximum_request_count']<=26
    m=next(r for r in p['surfaced_stocks'] if r['thscode']=='002714.SZ')
    assert Decimal(m['market_comparison']['20']['stock_return'])==Decimal(40)/Decimal(30)-1
    assert len(m['sector_comparisons'])==2
    assert m['current_origins'][0]['company']['basis'][0]['evidence']['replayability_level']=='PARTIAL'


def test_source_and_sector_objects_are_not_modified():
    state,ledger,a,plan,response,_=prepared()
    refs=synthetic_references(state,[r['thscode'] for r in plan['issuers']])
    before=serialize_sector_radar_market_state(state),canonical_json(a),canonical_json(plan),canonical_json(refs)
    stock.observe_stock_reading(plan,state,request_json=response,observed_at=NOW,reference_inputs=refs)
    assert before==(serialize_sector_radar_market_state(state),canonical_json(a),canonical_json(plan),canonical_json(refs))
    assert ledger.events==()


@pytest.mark.parametrize('bad',['missing_first','missing_middle','missing_latest','duplicate','nan','adjusted','identity','future','off_calendar','extra_early'])
def test_invalid_individual_history_never_becomes_quiet_or_a_selected_stock(bad):
    def change(path,params,result):
        if path!=stock.STOCK_HISTORY:return result
        d=result['data'];rows=d['item']
        if bad=='missing_first':rows.pop(0)
        elif bad=='missing_middle':rows.pop(25)
        elif bad=='missing_latest':rows.pop()
        elif bad=='duplicate':rows.append(copy.deepcopy(rows[0]))
        elif bad=='nan':rows[-1]['close_price']='NaN'
        elif bad=='adjusted':d['adjust']='qfq'
        elif bad=='identity':d['thscode']='000001.SZ'
        elif bad=='future':rows[-1]['date_ms']=ms(FRIDAY+timedelta(days=3),0,0)
        elif bad=='off_calendar':rows[0]['date_ms']=ms(FRIDAY+timedelta(days=1),0,0)
        else:
            row=copy.deepcopy(rows[0]);row['date_ms']-=1000*86400;rows.insert(0,row)
        return result
    with pytest.raises(ValueError):observe(change)


@pytest.mark.parametrize('kind',['catalog','calendar','snapshot_last','snapshot_previous','old_members','future_members','fake_member','duplicate_member'])
def test_current_context_and_membership_integrity(kind):
    def change(path,params,result):
        if kind=='catalog' and path==stock.indices.HITHINK_INDEX_CATALOG_PATH:result['data']['item'][0]['name']='renamed'
        if kind=='calendar' and path==stock.HITHINK_CALENDAR_PATH:result['data']['item'].pop(50)
        if kind.startswith('snapshot') and path==stock.indices.HITHINK_INDEX_SNAPSHOT_PATH:
            row=next(r for r in result['data']['item'] if r['thscode']!='000300.SH')
            row['last_price' if kind=='snapshot_last' else 'prev_price']='1'
        if path==stock.members.HITHINK_SECTOR_CONSTITUENTS_PATH:
            if kind=='old_members':result['data']['timestamp']-=86400000
            elif kind=='future_members':result['data']['timestamp']+=1
            elif kind=='fake_member':result['data']['item'][0]['thscode']='ABCDEF.XY'
            elif kind=='duplicate_member':result['data']['item'].append(copy.deepcopy(result['data']['item'][0]))
        return result
    with pytest.raises((ValueError,RuntimeError)):observe(change)


@pytest.mark.parametrize('kind',['not_member','st','n_prefix','zero_volume','zero_turnover','falling'])
def test_explicit_stock_exclusions_are_not_beneficiary_inference(kind):
    def change(path,params,result):
        if path==stock.members.HITHINK_SECTOR_CONSTITUENTS_PATH:
            if kind=='not_member':result['data']['item']=[result['data']['item'][-1]]
            if kind in {'st','n_prefix'}:
                for r in result['data']['item']:r['name']='*ST测试' if kind=='st' else 'N测试'
        if path==stock.STOCK_HISTORY:
            if kind.startswith('zero'):result['data']['item'][-1]['volume' if kind=='zero_volume' else 'turnover']='0'
            elif kind=='falling':
                for i,r in enumerate(result['data']['item']):r['close_price']=str(100-i)
        return result
    if kind in {'zero_volume','zero_turnover'}:
        with pytest.raises(stock.StockReadingInputError,match='NONTRADING') as exc:
            observe(change,reference_kind=kind)
        assert exc.value.category=='DATA_INSUFFICIENT'
        return
    result,_,calls=observe(change,reference_kind=kind)
    p=result['projection']
    assert not p['surfaced_stocks'] and p['status']=='NO_MATCH_WITHIN_REVIEWED_COMPANY_SCOPE'
    assert all(r['excluded_reasons'] for r in p['all_stock_observations'])
    if kind in {'not_member','st','n_prefix'}:assert not any(path==stock.STOCK_HISTORY for path,_ in calls)


def test_forged_sector_prices_with_rehashed_association_fail():
    state,ledger,a,_,_,_=prepared()
    a['projection']['panels'][0]['markets'][0]['saved_market']['currently_gate_active']=False
    a['projection_hash']=canonical_hash(a['projection'])
    with pytest.raises(ValueError,match='reproduce'):
        stock.prepare_stock_reading(ROOT,state,ledger,a,observed_at=NOW)


def test_late_or_changed_original_business_mapping_is_not_accepted(tmp_path):
    state,ledger,a,_,_,_=prepared()
    root,spec,source=copy_inputs(tmp_path)
    p=root/'radar_inputs/company-evidence/002714-muyuan-h1-2026-09-06.json'
    p.write_bytes(p.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='source bytes'):
        stock.prepare_stock_reading(root,state,ledger,a,observed_at=NOW)


def test_request_caps_do_not_pick_first_three_before_enrichment(monkeypatch):
    state,ledger,a,_,_,_=prepared()
    monkeypatch.setattr(stock,'MAX_MEMBERSHIPS',1)
    with pytest.raises(ValueError,match='budget'):
        stock.prepare_stock_reading(ROOT,state,ledger,a,observed_at=NOW)


def test_expired_plan_and_future_cutoff_fail_before_requests():
    state,_,_,plan,response,calls=prepared()
    with pytest.raises(ValueError,match='lifetime'):
        stock.observe_stock_reading(plan,state,request_json=response,observed_at=NOW+timedelta(minutes=31))
    assert calls==[]


def test_round_robin_dedup_and_full_eligible_inventory_not_a_composite_score():
    def row(code,score,nodes):
        return {'thscode':code,'eligible_for_shadow_reading':True,'eligible_nodes':nodes,
                'market_comparison':{'20':{'excess_return':str(score)},'5':{'excess_return':'0.1'}}}
    rows=[row('000001.SZ',4,['a','b']),row('000002.SZ',3,['a']),row('000003.SZ',2,['b']),row('000004.SZ',1,['c'])]
    picked=stock._select(rows,['a','b','c'])
    assert [r['thscode'] for r in picked]==['000001.SZ','000003.SZ','000004.SZ']
    assert stock._select(list(reversed(rows)),['a','b','c'])==picked
    assert len(rows)==4 and stock._select([],['a'])==[]


def test_stock_first_page_exposes_business_limits_price_windows_and_full_scope():
    result,_,_=observe()
    soup=BeautifulSoup(stock.render_stock_reading(result),'html.parser')
    assert soup.find('h1').get_text().startswith('股票观察')
    assert len(soup.find_all('article'))==len(result['projection']['surfaced_stocks'])
    text=soup.get_text()
    for word in ('牧原股份','5日','20日','60日','PARTIAL','不是全 A 股盲选','未复权','公司依据','不倒灌历史',
                 '为什么值得进一步看','风险／缺口','下一步核查','仍强势阅读，非新事件','SYNTHETIC_TEST_ONLY'):
        assert word in text
    assert soup.find('script') is soup.find('iframe') is None
    # Keep the synthetic selected row and its full-scope counterpart consistent
    # so this remains an escaping test rather than an identity-forgery test.
    selected=result['projection']['surfaced_stocks'][0]
    for row in result['projection']['all_stock_observations']:
        if row['thscode']==selected['thscode']:
            row['company_name']='<script>alert(1)</script>'
    selected['company_name']='<script>alert(1)</script>'
    result['projection_hash']=canonical_hash(result['projection'])
    escaped=BeautifulSoup(stock.render_stock_reading(result),'html.parser')
    assert escaped.find('script') is None
    assert '<script>alert(1)</script>' in escaped.get_text()
