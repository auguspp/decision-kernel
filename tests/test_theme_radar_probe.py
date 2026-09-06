from __future__ import annotations

import copy
import gzip
import json
from datetime import datetime, time, timedelta
from decimal import Decimal, localcontext
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import theme_radar_probe as probe
from decision_kernel.runtime.hithink_http import HithinkRuntimeError
from decision_kernel.runtime.sector_radar import (
    SectorPricePoint, SectorPriceSeries, calculate_sector_radar_snapshot,
)
from decision_kernel.runtime.sector_radar_state import parse_sector_radar_market_state, serialize_sector_radar_market_state
from test_sector_radar_audit import resolution, prohibit_network, TZ, FRIDAY

ROOT = Path(__file__).resolve().parents[1]
PLANNED = datetime.combine(FRIDAY, time(17, 2), tzinfo=TZ)
AS_OF = PLANNED + timedelta(minutes=8)
THEMES = [{'thscode': f'88600{i}.TI', 'name': f'Synthetic theme {i}', 'reason': 'Explicit fixture, not a real selection'} for i in (1, 2)]
A, B, C, D = '000001.SZ', '600001.SH', '920001.BJ', '300001.SZ'


def ms(value):
    return int(value.timestamp() * 1000)


def envelope(rows, at=PLANNED, **fields):
    return {'code': 0, 'data': {'timestamp': ms(at), 'item': rows, **fields}}


def capture(path, params, response, at=PLANNED):
    return {'path': path, 'params': params, 'requested_at': at.isoformat(),
            'received_at': (at + timedelta(seconds=1)).isoformat(), 'response': response}


def choices(state):
    return [{'thscode': code, 'name': name, 'reason': 'Selected coverage only'} for code, name in state.broad_identities[:2]]


def catalogs(state):
    before = PLANNED - timedelta(minutes=1)
    industries = [{'thscode': code, 'name': name} for code, name in state.broad_identities + state.granular_identities]
    concepts = [{'thscode': t['thscode'], 'name': t['name']} for t in THEMES]
    return (capture(probe.CATALOG, {'tag': 'cn_concept'}, envelope(concepts, before), before),
            capture(probe.CATALOG, {'tag': 'industry'}, envelope(industries, before), before))


def history(state, code, rate):
    return envelope([{'date_ms': ms(datetime.combine(day, time(), tzinfo=TZ)),
                      'close_price': str(Decimal(100) + rate*i), 'volume': str(1000+i), 'turnover': str(2000+i)}
                     for i, day in enumerate(state.sessions)], thscode=code, interval='1d', adjust=None)


def snapshot_row(code, current, previous, volume, turnover):
    current, previous = Decimal(current), Decimal(previous)
    return {'thscode': code, 'ticker': code[:6], 'last_price': str(current), 'prev_price': str(previous),
        'price_change': str(current-previous), 'price_change_ratio_pct': str((current/previous-1)*100),
        'open_price': str(current), 'high_price': str(max(current,previous)+1), 'low_price': str(min(current,previous)-1),
        'volume': str(volume), 'turnover': str(turnover)}


def fixture():
    restored = resolution(); state = restored.market_state
    concept, industry = catalogs(state)
    plan = probe.make_theme_plan(state, concept, industry, themes=copy.deepcopy(THEMES), industries=choices(state), planned_at=PLANNED.isoformat())
    histories = {t['thscode']: history(state, t['thscode'], rate) for t, rate in zip(THEMES, [Decimal('.6'), Decimal('-.05')])}
    benchmark = next(s for s in state.series if s.family == 'BENCHMARK')
    snaps = [snapshot_row(benchmark.thscode, benchmark.closes[-1], benchmark.closes[-2], 1000, benchmark.turnovers[-1])]
    for code, body in histories.items():
        now, prior = body['data']['item'][-2:][::-1]
        snaps.append(snapshot_row(code, now['close_price'], prior['close_price'], now['volume'], now['turnover']))
    by_members = {THEMES[0]['thscode']: [A,B,C], THEMES[1]['thscode']: [B,C,D],
                  state.broad_identities[0][0]: [A,B], state.broad_identities[1][0]: [C]}
    captures = {}
    for request in plan['requests']:
        key = request['id']
        if key == 'snapshot': body = envelope(snaps, total=len(snaps))
        elif key.startswith('history:'): body = histories[key.split(':')[1]]
        else:
            body = envelope([{'thscode': c, 'ticker': c[:6], 'name': 'Synthetic '+c} for c in by_members[key.split(':')[1]]])
        captures[key] = capture(request['path'], request['params'], body)
    return state, {'schema_version': 1, 'provenance': probe.SYNTHETIC, 'plan': plan,
                   'concept_catalog': concept, 'industry_catalog': industry, 'captures': captures}


def run(state, inputs, as_of=AS_OF, generated_at=AS_OF):
    return probe.build_theme_probe(state, inputs, as_of=as_of.isoformat(), generated_at=generated_at.isoformat())


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    prohibit_network(monkeypatch)


def test_actual_existing_math_and_overlap_reused_without_small_subset_ranks():
    state, inputs = fixture(); before = canonical_json(inputs), serialize_sector_radar_market_state(state)
    report = run(state, inputs); p = report['projection']
    assert p['global_theme_ranking'] == 'NOT_COMPUTED' and p['independent_forecast_count'] is None
    assert p['unique_selected_theme_members'] == 4 and p['summed_theme_member_count'] == 6
    assert p['theme_overlaps'][0]['intersection_members'] == [B,C]
    assert Decimal(p['theme_overlaps'][0]['jaccard']) == Decimal('.5')
    for field, value in probe.AUTHORITY.items(): assert p[field] == value
    first, second = p['themes']
    assert first['industry_probe_status'] == 'OBSERVED_ACROSS_PROBED_INDUSTRIES'
    assert first['unassigned_in_probed_industries'] == []
    assert second['unassigned_in_probed_industries'] == [D]
    assert first['current_price_breadth'] == 'NOT_ACQUIRED'
    benchmark = next(s for s in state.series if s.family == 'BENCHMARK')
    def series(code, name, closes, turnovers):
        return SectorPriceSeries(code, name, tuple(SectorPricePoint(d,c,t) for d,c,t in zip(state.sessions,closes,turnovers)))
    theta = []
    for t in THEMES:
        rows = inputs['captures']['history:'+t['thscode']]['response']['data']['item']
        theta.append(series(t['thscode'], t['name'], [Decimal(r['close_price']) for r in rows], [Decimal(r['turnover']) for r in rows]))
    original = calculate_sector_radar_snapshot(sectors=theta,
        benchmark=series(benchmark.thscode, benchmark.name, benchmark.closes, benchmark.turnovers), as_of_session=FRIDAY)
    expected = {o.thscode:o for o in original.observations}
    for t in p['themes']:
        path, base = t['path'], expected[t['selection']['thscode']]
        assert path['rating'] is path['cross_sectional_rank'] is path['first_system_discovery_at'] is None
        for h in path['horizons']:
            old = getattr(base, 'horizon_'+str(h['sessions']))
            assert Decimal(h['index_return']) == old.sector_return
            assert Decimal(h['excess_return']) == old.excess_return
        assert Decimal(path['excess_acceleration_5_sessions_20d']) == base.excess_acceleration_5_sessions_20d
        assert path['positive_20d_excess_persistence_sessions'] == base.positive_20d_excess_persistence_sessions
    assert first['path']['positive_20d_excess_persistence_left_censored'] is True
    assert before == (canonical_json(inputs), serialize_sector_radar_market_state(state))


def test_real_bootstrap_supports_exact_max_budget_without_any_real_theme_claim():
    state = parse_sector_radar_market_state(gzip.decompress((ROOT/'radar_inputs/sector-radar-state-bootstrap-2026-09-04.json.gz').read_bytes()).decode())
    # Bootstrap was retained on Saturday: build a LATER synthetic catalogue receipt,
    # not backdated acquisition and not a genuine HiThink catalogue or theme sample.
    at = datetime(2026,9,6,10,tzinfo=TZ)
    concept, industry = catalogs(state)
    for r in (concept, industry):
        r['requested_at'] = (at-timedelta(seconds=2)).isoformat(); r['received_at'] = (at-timedelta(seconds=1)).isoformat()
        r['response']['data']['timestamp'] = ms(at-timedelta(seconds=3))
    third = {'thscode':'886003.TI','name':'Synthetic theme 3','reason':'budget case'}
    concept['response']['data']['item'].append({k:third[k] for k in ('thscode','name')})
    industries = [{'thscode':c,'name':n,'reason':'fixture'} for c,n in state.broad_identities[:6]]
    p = probe.make_theme_plan(state,concept,industry,themes=THEMES+[third],industries=industries,planned_at=at.isoformat())
    assert p['planned_request_count_including_catalogs'] == p['maximum_request_count'] == 15
    assert p['requests_executed_by_planner'] == 0
    assert all(r['path'] != '/api/a-share/prices/snapshot' for r in p['requests'])


@pytest.mark.parametrize('change', ['too_many_themes','too_many_industries','duplicate','rename','foreign','wrong_tag','drift','industry_as_concept','granular'])
def test_plan_rejects_budget_and_catalog_identity_changes(change):
    state, inputs = fixture(); a,b=inputs['concept_catalog'],inputs['industry_catalog']
    ts, ins = copy.deepcopy(THEMES), choices(state)
    if change=='too_many_themes': ts *= 2
    elif change=='too_many_industries': ins *= 4
    elif change=='duplicate': ts[1]=ts[0]
    elif change=='rename': ts[0]['name']='not that concept'
    elif change=='foreign': ts[0]['thscode']='886999.TI'
    elif change=='wrong_tag': a['params']['tag']='industry'
    elif change=='drift': b['response']['data']['item'][0]['name']='drift'
    elif change=='industry_as_concept': a['response']['data']['item'].append(b['response']['data']['item'][0])
    else:
        c,n=state.granular_identities[0]; ins=[{'thscode':c,'name':n,'reason':'not a broad industry'}]
    with pytest.raises(ValueError): probe.make_theme_plan(state,a,b,themes=ts,industries=ins,planned_at=PLANNED.isoformat())


@pytest.mark.parametrize('change',['latest','middle','initial','nan','future','adjusted','wrong_code','duplicate'])
def test_bad_theme_history_cannot_be_dropped_or_filled(change):
    state,x=fixture(); data=x['captures']['history:886001.TI']['response']['data']; rows=data['item']
    if change=='latest': rows.pop(); data['timestamp']=rows[-1]['date_ms']
    elif change=='middle': rows.pop(20)
    elif change=='initial': rows.pop(0)
    elif change=='nan': rows[-1]['close_price']='NaN'
    elif change=='future': rows[-1]['date_ms']+=3*86400000
    elif change=='adjusted': data['adjust']='qfq'
    elif change=='wrong_code': data['thscode']='886002.TI'
    else: rows.append(rows[-1])
    with pytest.raises(ValueError): run(state,x)


@pytest.mark.parametrize('change',['benchmark','last','prev','volume','turnover','missing_capture','extra_capture','wrong_request','rehash_plan','future_ready','stale_members'])
def test_snapshots_and_saved_inputs_are_exact_not_plausible(change):
    state,x=fixture(); rows=x['captures']['snapshot']['response']['data']['item']
    if change=='benchmark': rows[0]['last_price']=str(Decimal(rows[0]['last_price'])+Decimal('.01'))
    elif change in {'last','prev','volume','turnover'}:
        f={'last':'last_price','prev':'prev_price','volume':'volume','turnover':'turnover'}[change]
        rows[1][f]=str(Decimal(rows[1][f])+Decimal('.01'))
    elif change=='missing_capture': x['captures'].pop('history:886001.TI')
    elif change=='extra_capture': x['captures']['unplanned']=copy.deepcopy(x['captures']['snapshot'])
    elif change=='wrong_request': x['captures']['members:886001.TI']['params']['thscode']='886002.TI'
    elif change=='rehash_plan':
        x['plan']['maximum_request_count']=99
        x['plan']['plan_hash']=canonical_hash({k:v for k,v in x['plan'].items() if k!='plan_hash'})
    elif change=='future_ready': x['captures']['snapshot']['response']['data']['timestamp']=ms(AS_OF+timedelta(seconds=1))
    else: x['captures']['members:886001.TI']['response']['data']['timestamp']=ms(PLANNED-timedelta(days=1))
    with pytest.raises(ValueError): run(state,x)


@pytest.mark.parametrize('change',['duplicate','fake_identity','ticker','empty'])
def test_member_quality_does_not_silently_shrink_denominator(change):
    state,x=fixture(); rows=x['captures']['members:886001.TI']['response']['data']['item']
    if change=='duplicate': rows.append(rows[0])
    elif change=='fake_identity': rows[0]['thscode']='ABCDEF.XY';rows[0]['ticker']='ABCDEF'
    elif change=='ticker': rows[0]['ticker']='000002'
    else: rows.clear()
    reason = {'duplicate': 'duplicate constituent', 'fake_identity': 'qualified A-share',
              'ticker': 'ticker disagrees', 'empty': 'membership is empty'}[change]
    with pytest.raises(HithinkRuntimeError, match=reason): run(state,x)


def test_ambiguous_and_identical_memberships_are_visible_without_forced_assignment():
    state,x=fixture()
    industry=state.broad_identities[0][0]
    x['captures']['members:'+industry]['response']['data']['item'].append({'thscode':C,'ticker':C[:6],'name':'Synthetic '+C})
    x['captures']['members:886002.TI']['response']['data']['item']=copy.deepcopy(x['captures']['members:886001.TI']['response']['data']['item'])
    p=run(state,x)['projection']
    assert p['themes'][0]['industry_probe_status']=='AMBIGUOUS_CURRENT_MEMBERSHIP'
    assert p['themes'][0]['ambiguous_industry_members']=={C:[i['thscode'] for i in x['plan']['industries']]}
    assert p['theme_overlaps'][0]['left_contains_right'] is p['theme_overlaps'][0]['right_contains_left'] is True
    assert p['unique_selected_theme_members']==3 and len(p['themes'])==2


def test_no_industry_probe_preserves_all_unknowns_and_single_theme_has_no_rank():
    state,x=fixture(); x['plan']=probe.make_theme_plan(state,x['concept_catalog'],x['industry_catalog'],themes=THEMES[:1],industries=[],planned_at=PLANNED.isoformat())
    x['captures']={r['id']:x['captures'][r['id']] for r in x['plan']['requests']}
    x['captures']['snapshot']['params']=x['plan']['requests'][0]['params']
    data=x['captures']['snapshot']['response']['data']; data['item']=data['item'][:2];data['total']=2
    p=run(state,x)['projection'];t=p['themes'][0]
    assert t['industry_probe_status']=='NO_INDUSTRIES_PROBED'
    assert len(t['unassigned_in_probed_industries'])==t['denominator']==3
    assert t['path']['cross_sectional_rank'] is None and p['theme_overlaps']==[]


@pytest.mark.parametrize('change',['pre_plan','after_cutoff','catalog_late','naive','long_window','weekday_gap','before_close'])
def test_time_boundaries_fail_instead_of_relabelling_market_date(change):
    state,x=fixture(); asof=AS_OF
    if change=='pre_plan': x['captures']['snapshot']['requested_at']=(PLANNED-timedelta(microseconds=1)).isoformat()
    elif change=='after_cutoff': x['captures']['snapshot']['received_at']=(AS_OF+timedelta(microseconds=1)).isoformat()
    elif change=='catalog_late': x['concept_catalog']['received_at']=(PLANNED+timedelta(microseconds=1)).isoformat()
    elif change=='naive': x['captures']['snapshot']['requested_at']='2026-09-04T17:02:00'
    elif change=='long_window': asof=PLANNED+timedelta(minutes=30,microseconds=1)
    elif change=='weekday_gap': asof=AS_OF+timedelta(days=3)
    else: asof=AS_OF.replace(hour=14)
    with pytest.raises(ValueError): run(state,x,as_of=asof,generated_at=asof)


def test_generation_time_is_presentation_only_and_zero_prior_turnover_is_unknown():
    state,x=fixture(); rows=x['captures']['history:886001.TI']['response']['data']['item']
    for row in rows[-25:-5]: row['turnover']='0'
    a=run(state,x); b=run(state,x,generated_at=AS_OF+timedelta(days=30))
    assert a['projection_hash']==b['projection_hash']
    assert a['projection']['themes'][0]['path']['turnover_pulse_5_vs_prior_20'] is None
    with localcontext() as ctx:
        ctx.prec=9
        assert run(state,x)['projection_hash']==a['projection_hash']


def test_html_is_read_only_escaped_and_does_not_claim_global_theme_discovery():
    state,x=fixture();x['plan']['themes'][0]['reason']='<script>alert(1)</script>'
    x['plan']=probe.make_theme_plan(state,x['concept_catalog'],x['industry_catalog'],themes=x['plan']['themes'],industries=x['plan']['industries'],planned_at=PLANNED.isoformat())
    soup=BeautifulSoup(probe.render_theme_probe(run(state,x)),'html.parser')
    assert soup.find('script') is soup.find('iframe') is soup.find('img') is None
    text=soup.get_text()
    assert '<script>alert(1)</script>' in text and probe.SYNTHETIC in text
    assert '不是全市场扫描或排名' in text and '当前涨跌宽度未采集' in text


def inventory(root):
    return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}


def cli_case(tmp_path):
    state,x=fixture(); source=tmp_path/'source';source.mkdir()
    (source/'state.json').write_text(serialize_sector_radar_market_state(state))
    (source/'input.json').write_text(canonical_json(x))
    output=tmp_path/'report'
    args=['--state',str(source/'state.json'),'--input',str(source/'input.json'),'--as-of',AS_OF.isoformat(),'--output',str(output)]
    return args,source,output


def test_full_cli_preserves_exact_inputs_and_rebuilds_with_no_market_or_ledger_writes(tmp_path):
    args,source,out=cli_case(tmp_path);before=inventory(source)
    assert probe.main(args)==0
    assert set(inventory(out))=={'index.html','theme-probe.json','supplied-input.json','saved-market-state.json','files.json'}
    assert (out/'supplied-input.json').read_bytes()==before['input.json']
    assert (out/'saved-market-state.json').read_bytes()==before['state.json']
    report=json.loads((out/'theme-probe.json').read_text())
    state=parse_sector_radar_market_state((out/'saved-market-state.json').read_text())
    rebuilt=probe.build_theme_probe(state,json.loads((out/'supplied-input.json').read_text()),as_of=AS_OF.isoformat(),generated_at=report['generated_at'])
    assert rebuilt==report and (out/'index.html').read_text()==probe.render_theme_probe(rebuilt)
    assert inventory(source)==before
    saved=inventory(out)
    assert probe.main(args)==2 and inventory(out)==saved


@pytest.mark.parametrize('failure',['duplicate_json','symlink','oversize','rename'])
def test_cli_rejects_unsafe_input_and_cleans_interrupted_output(tmp_path,monkeypatch,failure):
    args,source,out=cli_case(tmp_path)
    if failure=='duplicate_json': (source/'input.json').write_text('{"schema_version":1,"schema_version":1}')
    elif failure=='symlink':
        p=source/'input.json';p.rename(source/'old.json');p.symlink_to(source/'old.json')
    elif failure=='oversize': (source/'input.json').write_bytes(b' '* (probe.MAX_INPUT_BYTES+1))
    else:
        old=Path.rename
        def stop(self,dst):
            if Path(dst)==out: raise OSError('test interruption')
            return old(self,dst)
        monkeypatch.setattr(Path,'rename',stop)
    assert probe.main(args)==2 and not out.exists()
    assert not list(tmp_path.glob('.theme-probe-*'))


def test_cli_handles_existing_membership_runtime_rejection_without_an_output(tmp_path):
    args, source, out = cli_case(tmp_path)
    path = source / 'input.json'
    payload = json.loads(path.read_text())
    payload['captures']['members:886001.TI']['response']['data']['item'] = []
    path.write_text(canonical_json(payload))
    before = inventory(source)
    assert probe.main(args) == 2
    assert not out.exists() and inventory(source) == before
