"""Synthetic arithmetic/qualification tests, never actual two-company market proof."""
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import sector_member_reading as m
from decision_kernel.runtime import hithink_stock_reading as own


@pytest.fixture
def case():
    dates = []
    day = date(2026,9,9)
    while len(dates)<61:
        if day.weekday()<5: dates.append(day)  # SYNTHETIC calendar, not exchange qualification.
        day -= timedelta(days=1)
    dates = tuple(reversed(dates))
    members = [{'thscode':'600598.SH','name':'北大荒'}, {'thscode':'601952.SH','name':'苏垦农发'}]
    request = {'version':m.VERSION, 'market_session':'2026-09-09', 'windows':[5,20,60],
               'members':members, 'sector':'884002.TI','benchmark':'000300.SH', 'source':{},
               'max_requests':4, 'price_convention':'RAW_WITH_REPORTED_ACTION_WINDOW_EXCLUSIONS', 'automatic_research':False}
    state = SimpleNamespace(sessions=dates, series=[SimpleNamespace(thscode=c,
                closes=tuple(Decimal(100)+Decimal(i)/Decimal(10) for i in range(61)))
                for c in ('884002.TI','000300.SH')])
    stamp = lambda d: int(datetime.combine(d,time(),own.TZ).timestamp()*1000)
    responses, receipts, quotes = {}, {}, {}
    for j,member in enumerate(members):
        c = member['thscode']
        bars = []
        for i,d in enumerate(dates):
            price = Decimal(10)+Decimal(i)*(Decimal('0.02') if j==0 else Decimal('0.01'))
            bars.append({'date_ms':stamp(d), **{k:str(price) for k in ('open_price','high_price','low_price','close_price')},
                         'volume':'100', 'turnover':str(1000*(j+1))})
        q = {k:bars[-1][k] for k in ('open_price','high_price','low_price','volume','turnover')}
        q.update(thscode=c,ticker=c[:6],last_price=bars[-1]['close_price'],prev_price=bars[-2]['close_price'])
        quotes[c] = {'quote':{'code':0,'data':{'timestamp':None,'item':[q]}}, 'received_at':'2026-09-09T14:45:00+00:00'}
        responses[c] = {'history':{'code':0,'data':{'timestamp':stamp(dates[-1]),'item':bars}},
                         'actions':{'code':0,'data':{'thscode':c,'ticker':c[:6],'item':[]}}}
        receipts[c] = {'history':'2026-09-10T06:00:00+00:00','actions':'2026-09-10T06:01:00+00:00'}
    return request, state, quotes, responses, receipts


def test_common_window_comparison_and_no_role_guess(case):
    result = m.compare(*case)
    a,b = result['rows']
    for n in m.WINDOWS:
        w = a['windows'][str(n)]
        assert w['member_return_rank']==1
        assert b['windows'][str(n)]['member_return_rank']==2
        assert w['excess_vs_sector']==w['stock_return']-w['sector_return']
        assert w['base_session']==case[1].sessions[-n-1]
        assert w['close_to_close_max_drawdown']==0
        assert w['positive_cumulative_excess_days_vs_sector']==n
        assert w['turnover_share_of_complete_group']==Decimal(1)/3
    assert all(r['role'].startswith('UNDETERMINED') for r in result['rows'])
    assert result['investment_authority']=='NONE'
    assert '600598.SH' in m.render(result) and '601952.SH' in m.render(result)
    assert result['reading_hash']==canonical_hash({k:v for k,v in result.items() if k!='reading_hash'})


def test_cash_action_excludes_long_window_for_both_ranks(case):
    c = '600598.SH'; d=case[1].sessions[10]
    case[3][c]['actions']['data']['item']=[{'ticker':c[:6],'ex_date_ms':int(datetime.combine(d,time(),own.TZ).timestamp()*1000),
                                         'dividend_per_share':'0.5','per_share_bonus':'0'}]
    r=m.compare(*case)
    assert r['rows'][0]['windows']['60']['stock_return'] is None
    assert all(row['windows']['60']['member_return_rank'] is None for row in r['rows'])
    assert r['rows'][0]['windows']['20']['member_return_rank']==1


@pytest.mark.parametrize('mutation', ('bad_cutoff','budget','research','duplicate','future_history','bad_quote','bad_receipt','missing_bar','missing_action'))
def test_fail_closed_not_pick_remaining_member(case,mutation):
    q,s,quotes,r,receipts = deepcopy(case)
    c='600598.SH'
    if mutation=='bad_cutoff': q['market_session']='2026-09-08'
    elif mutation=='budget': q['max_requests']=5
    elif mutation=='research': q['automatic_research']=True
    elif mutation=='duplicate': q['members'][1]=q['members'][0]
    elif mutation=='future_history': r[c]['history']['data']['timestamp']=int(datetime(2026,9,11,tzinfo=timezone.utc).timestamp()*1000)
    elif mutation=='bad_quote': quotes[c]['quote']['data']['item'][0]['last_price']='11.7'
    elif mutation=='bad_receipt': receipts[c]['actions']='2026-09-10T05:00:00Z'
    elif mutation=='missing_bar': r[c]['history']['data']['item'].pop()
    elif mutation=='missing_action': del r[c]['actions']
    with pytest.raises((ValueError,KeyError)): m.compare(q,s,quotes,r,receipts)


def test_drawdown_is_negative_close_based():
    assert m._drawdown(tuple(map(Decimal,('100','120','90','110'))))==Decimal('-.25')


def test_ties_are_not_broken_by_ticker(case):
    q,s,quotes,r,receipts=deepcopy(case)
    a,b=[x['thscode'] for x in q['members']]
    r[b]['history']=deepcopy(r[a]['history'])
    quotes[b]['quote']['data']['item'][0].update({k:v for k,v in quotes[a]['quote']['data']['item'][0].items()
                                                if k not in ('thscode','ticker')})
    result=m.compare(q,s,quotes,r,receipts)
    assert all(row['windows']['20']['member_return_rank']==1 for row in result['rows'])


def test_capture_stops_once_and_keeps_failure(tmp_path,case):
    q,s,quotes,_,_=case
    calls=[]
    def fail(endpoint,params):
        calls.append((endpoint,params));raise RuntimeError('not echoed provider content')
    root=tmp_path/'capture'
    with pytest.raises(RuntimeError): m.capture(root,q,s,quotes,transport=fail,pause=lambda _:None)
    assert len(calls)==1 and (root/'failure.json').exists()
    assert not (root/'reading.json').exists()
    assert 'not echoed provider' not in (root/'failure.json').read_text()


def test_capture_exact_four_no_quote_or_new_calendar(tmp_path,case):
    q,s,quotes,r,_=case; calls=[];pauses=[]
    def transport(endpoint,params):
        calls.append((endpoint,params))
        return r[params['thscode']]['history' if endpoint==own.HISTORY else 'actions']
    root=tmp_path/'capture'
    result=m.capture(root,q,s,quotes,transport=transport,pause=pauses.append,
                     now=lambda:datetime(2026,9,10,7,tzinfo=timezone.utc))
    assert len(calls)==4 and pauses==[20,20,20]
    assert {p for p,_ in calls}=={own.HISTORY,own.ACTIONS}
    assert all(params.get('thscode') in {'600598.SH','601952.SH'} for _,params in calls)
    assert result['status']=='COMPLETE_BOUNDED_RAW_READING'
    assert (root/'summary.md').exists()
