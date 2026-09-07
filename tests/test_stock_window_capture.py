"""Production selector/recorder/replayer on explicitly synthetic market envelopes."""
from decimal import Decimal

import pytest
from bs4 import BeautifulSoup

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import stock_radar_reading as stock
from decision_kernel.runtime import hithink_stock_reading as own
from test_stock_issuer_isolation import expanded_provider, rehash_capture
from test_stock_radar_capture import setup
from test_sector_radar_audit import prohibit_network


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def scenario(tmp_path,monkeypatch,*,event_index=20):
    state,plan,provider,calls = expanded_provider(monkeypatch,3)
    mod,_,out,_,pauses,run = setup(tmp_path)
    bad = plan['issuers'][0]['thscode']
    from datetime import datetime, time
    ex_ms = int(datetime.combine(state.sessions[-61:][event_index],time(),stock.SHANGHAI_TZ).timestamp()*1000)
    def request(path,params):
        body = provider(path,params)
        if path == own.SNAPSHOT:
            row = body['data']['item'][0]
            row['turnover'] = str(Decimal(row['turnover'])-Decimal('0.005'))
        if path == own.ACTIONS:
            code = params['thscode']
            if code == bad:
                return {'code':3002,'data':None,'message':'No adjustment events for thscode='+bad}
            body['data']['item'] = [{'ticker':code[:6],'ex_date_ms':ex_ms,
                                    'dividend_per_share':'0.2','per_share_bonus':0}]
        return body
    report = run(reference_inputs=None,transport=request)
    return mod,out,report,calls,pauses


@pytest.mark.parametrize('event_index', [20,40])
def test_old_events_and_amount_tolerance_produce_exact_partial_capture_replay(tmp_path,monkeypatch,event_index):
    mod,out,report,calls,pauses = scenario(tmp_path,monkeypatch,event_index=event_index)
    assert report['status'] == mod['PARTIAL'] and report['coverage']['qualified_issuers'] == 2
    assert report['coverage']['unavailable_issuers'] == 1
    original = mod['read'](out/'stock-reading.json')
    p = original['projection']
    assert p['status'] == 'PARTIAL_STOCKS_FOR_SHADOW_READING'
    assert len(p['surfaced_stocks']) == 2
    for row in p['surfaced_stocks']:
        path = row['stock_path']
        assert path['returns']['60'] is None
        assert row['market_comparison']['60']['excess_return'] is None
        assert all(c['horizons']['60']['stock_excess_return'] is None for c in row['sector_comparisons'])
        assert (path['twenty_day_return_five_sessions_ago'] is None) is (event_index == 40)
        assert path['input_checks']['reported_corporate_actions']
        assert path['input_checks']['turnover_reconciliation']['absolute_difference_cny'] == '0.005'
        assert path['input_checks']['turnover_reconciliation']['status'] == 'WITHIN_EXPLICIT_TOLERANCE'
        assert path['corporate_action_adjustment'] == 'NOT_PERFORMED'
    replay = mod['verify'](out)
    assert replay['status'] == 'STOCK_BATCH_WITH_DATA_GAPS_REBUILT'
    assert replay['requests_replayed'] == len(calls) and replay['network_calls'] == 0
    assert replay['coverage'] == report['coverage'] and replay['stock_count'] == 2
    assert pauses == [20]*(len(calls)-1)
    text = BeautifulSoup((out/'index.html').read_text(),'html.parser').get_text()
    assert '不可比（跨公司行为）' in text and '允许上限' in text and '每股现金 0.2' in text
    assert '不是全计划排名或完整零匹配' in text
    assert p['price_path_is_not_total_return'] is True
    assert p['research_authority'] == p['investment_authority'] == p['human_attention_authority'] == 'NONE'


@pytest.mark.parametrize('tamper', ['amount_outside_bound','action_inside_selection','invent_60_return'])
def test_rehashed_new_policy_tampering_is_rejected_by_recomputation(tmp_path,monkeypatch,tamper):
    mod,out,r,_,_ = scenario(tmp_path,monkeypatch)
    if tamper == 'invent_60_return':
        p = mod['read'](out/'stock-reading.json')
        p['projection']['surfaced_stocks'][0]['stock_path']['returns']['60'] = '0.5'
        p['projection_hash'] = canonical_hash(p['projection'])
        (out/'stock-reading.json').write_bytes(mod['data'](p))
        r['projection_hash'] = p['projection_hash']
    else:
        # The first stock is unavailable; modify a later stock which originally passed.
        path = own.SNAPSHOT if tamper == 'amount_outside_bound' else own.ACTIONS
        entry = [e for e in r['requests'] if e['path'] == path][1]
        file = out/entry['response_file']; body = mod['read'](file)
        if tamper == 'amount_outside_bound':
            body['data']['item'][0]['turnover'] = '1'
        else:
            h = next(e for e in r['requests'] if e['path'] == own.HISTORY
                     and e['params']['thscode'] == entry['params']['thscode'])
            body['data']['item'][0]['ex_date_ms'] = mod['read'](out/h['response_file'])['data']['item'][50]['date_ms']
        file.write_bytes(mod['data'](body))
    rehash_capture(mod,out,r)
    with pytest.raises(ValueError): mod['verify'](out)
