"""Same-source long history: synthetic closed sessions; no live source calls."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import socket
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import tdx_concept_trend as trend, tdx_concept_snapshot as old
from test_tdx_concept_snapshot import DAY, WF, SHA, source, write_source_files


def sample():
    # Synthetic sessions deliberately use weekdays only; not an exchange calendar.
    dates = []
    day = DAY
    while len(dates) < trend.COUNT:
        if day.weekday() < 5:
            dates.append(day)
        day -= timedelta(days=1)
    dates.reverse()
    clocks = [d.isoformat() + 'T15:00:00+08:00' for d in dates]
    prices = {'sh880001': [10000000 + i**3 for i in range(trend.COUNT)],
              'sh880002': [200000 - 100*i for i in range(trend.COUNT)],
              trend.BENCHMARK: [100000] * trend.COUNT}
    base = source()
    for r in base['boards']:
        r['bars'] = [{'time': t, 'close': str(Decimal(v)/1000)}
                     for t, v in list(zip(clocks, prices[r['full_code']]))[-15:]]
        r['snapshot'] = {'last_price': r['bars'][-1]['close'], 'pre_close_price': r['bars'][-2]['close']}
    data = dict(version=trend.VERSION, policy=deepcopy(trend.POLICY), package_version='3.2.2',
                wheel_sha256='1'*64, chosen_host=base['chosen_host'], requested_market_session=DAY.isoformat(),
                observed_started_at='2026-09-25T04:00:03Z', observed_finished_at='2026-09-25T04:00:04Z',
                source_batch_calls=1, requested_series=3, series={})
    for code, values in prices.items():
        data['series'][code] = dict(full_code=code, market_id=1, period_name='day', adjust_mode='none',
                                   start=0, request_count=trend.COUNT, bars=list(map(list, zip(clocks, values))))
    return base, data


def bundle(tmp_path):
    base, data = sample()
    root = tmp_path / 'snapshot'
    def take(out, _):
        write_source_files(out)
        return base
    ticks = iter([datetime(2026, 9, 25, 4, 0, i, tzinfo=timezone.utc) for i in (0, 1)])
    receipt = old.capture(root, market_session=DAY, workflow=WF, expected_code=SHA,
                          source_fn=take, now=lambda: next(ticks))
    return root, data, old.replay(root), receipt, json.loads((root/'source.json').read_bytes())


def capture_bundle(tmp_path, damage=None):
    root, data, observation, receipt, base = bundle(tmp_path)
    if damage:
        damage(data)
    output = tmp_path / 'trend'
    ticks = iter([datetime(2026, 9, 25, 4, 0, i, tzinfo=timezone.utc) for i in (2, 5, 6)])
    result = trend.capture(root, output, source_fn=lambda *_: data, now=lambda: next(ticks))
    return root, output, result, observation, receipt, base


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def reject(*a, **k):
        raise AssertionError('no live capture in tests')
    monkeypatch.setattr(socket, 'create_connection', reject)
    monkeypatch.setattr(socket.socket, 'connect', reject)


def test_full_catalog_reuses_arithmetic_and_retains_weak_direction_and_censored_run(tmp_path):
    _, data, obs, receipt, base = bundle(tmp_path)
    before = deepcopy((data, obs, receipt, base))
    p = trend.build(data, obs, receipt, base)['projection']
    strong, weak = p['observations']
    assert p['catalog_count'] == 2 and p['coverage']['horizons'] == {'5': 2, '20': 2, '60': 2}
    assert strong['phase'] == 'STRENGTHENING' and weak['phase'] == 'WEAKENING_OR_EXIT'
    assert strong['positive_20d_excess_persistence_sessions'] == 106
    assert strong['positive_20d_excess_persistence_left_censored'] is True
    values = data['series']['sh880001']['bars']
    assert Decimal(strong['horizons']['60']['index_return']) == Decimal(values[-1][1])/Decimal(values[-61][1])-1
    assert weak['positive_20d_excess_persistence_sessions'] == 0
    assert p['return_unit'] == 'FRACTION_NOT_PERCENT' and p['source_calls_during_replay'] == 0
    assert before == (data, obs, receipt, base)
    assert '弱化或退出' in trend.render({'projection': p})


@pytest.mark.parametrize('e5,e20,previous,acc,expected', [
    ('1','1','0','1','EMERGING'), ('1','1','1','1','STRENGTHENING'),
    ('1','1','1','0','PERSISTENT'), ('-1','1','1','1','MATURE_OR_DIVERGING'),
    ('1','1','1','-1','MATURE_OR_DIVERGING'), ('-1','0','1','-1','WEAKENING_OR_EXIT'),
    ('1','-1','-1','-1','WEAKENING_OR_EXIT'), ('1','0','0','0','NOT_POSITIVE')])
def test_phase_is_explicit_price_observation_not_opaque_score(e5,e20,previous,acc,expected):
    hs = {str(n): {'excess_return': Decimal(v)} for n,v in ((5,e5),(20,e20),(60,'1'))}
    assert trend._phase(hs, Decimal(previous), Decimal(acc))[0] == expected
    hs['60'] = None
    assert trend._phase(hs, Decimal(previous), Decimal(acc))[0] == 'UNKNOWN'


def test_short_history_stays_in_full_catalog_and_cannot_become_long_phase(tmp_path):
    _, data, obs, receipt, base = bundle(tmp_path)
    data['series']['sh880002']['bars'] = data['series']['sh880002']['bars'][-15:]
    p = trend.build(data, obs, receipt, base)['projection']
    row = p['observations'][1]
    assert p['catalog_count'] == 2 and p['coverage']['horizons'] == {'5': 2, '20': 1, '60': 1}
    assert row['phase'] == 'UNKNOWN' and row['gap'] is None
    assert row['horizons']['5'] is not None and row['horizons']['20'] is None


@pytest.mark.parametrize('damage', ['duplicate','close','zero','bool','stale','gap','future','timezone'])
def test_bad_concept_history_is_local_gap_not_negative_condition(tmp_path, damage):
    _, data, obs, receipt, base = bundle(tmp_path)
    bars = data['series']['sh880002']['bars']
    if damage == 'duplicate': bars[5][0] = bars[4][0]
    if damage == 'close': bars[-7][1] += 1
    if damage == 'zero': bars[5][1] = 0
    if damage == 'bool': bars[5][1] = True
    if damage == 'stale': bars.pop()
    if damage == 'gap': bars.pop(5)
    if damage == 'future': bars[-1][0] = '2026-09-25T15:00:00+08:00'
    if damage == 'timezone': bars[5][0] = bars[5][0][:-6]
    p = trend.build(data, obs, receipt, base)['projection']
    assert p['observations'][0]['phase'] == 'STRENGTHENING'
    assert p['observations'][1]['phase'] == 'UNKNOWN' and p['observations'][1]['gap']
    assert all(v is None for v in p['observations'][1]['horizons'].values())
    assert p['coverage']['horizons'] == {'5': 1,'20': 1,'60': 1}


@pytest.mark.parametrize('damage', ['benchmark','extra','missing','identity','adjust','clock','version','count','bool'])
def test_source_or_benchmark_failure_rejects_only_optional_projection(tmp_path, damage):
    root, data, obs, receipt, base = bundle(tmp_path)
    if damage == 'benchmark': data['series'][trend.BENCHMARK]['bars'] = []
    if damage == 'extra': data['series']['sh888888'] = deepcopy(data['series']['sh880002'])
    if damage == 'missing': del data['series']['sh880002']
    if damage == 'identity': data['series']['sh880002']['full_code'] = 'sz880002'
    if damage == 'adjust': data['series'][trend.BENCHMARK]['adjust_mode'] = 'qfq'
    if damage == 'clock': data['observed_started_at'] = '2026-09-25T03:59:00Z'
    if damage == 'version': data['package_version'] = 'different'
    if damage == 'count': data['series'][trend.BENCHMARK]['request_count'] = 127
    if damage == 'bool': data['source_batch_calls'] = True
    with pytest.raises(ValueError): trend.build(data, obs, receipt, base)
    assert old.replay(root) == obs


def test_capture_is_create_only_replay_is_byte_exact_and_old_files_unchanged(tmp_path):
    root, out, cap, obs, receipt, base = capture_bundle(tmp_path)
    assert cap['status'] == 'CAPTURED_LONG_HISTORY'
    assert trend.replay(out, obs, receipt, base) == json.loads((out/'trend.json').read_bytes())
    assert old.replay(root) == obs
    with pytest.raises(ValueError, match='CREATE_ONLY'):
        trend.capture(root, out)
    (out/'summary.md').write_bytes((out/'summary.md').read_bytes() + b' ')
    with pytest.raises(ValueError): trend.replay(out, obs, receipt, base)
    assert old.replay(root) == obs


def test_failed_history_is_retained_not_promoted_and_base_survives(tmp_path):
    root, out, cap, obs, receipt, base = capture_bundle(tmp_path, lambda d: d['series'][trend.BENCHMARK].update(bars=[]))
    assert cap['status'] == 'INCOMPLETE_LONG_HISTORY' and cap['reason_code'] == 'TREND_BENCHMARK_UNAVAILABLE'
    assert trend.replay(out, obs, receipt, base)['status'] == 'INCOMPLETE_LONG_HISTORY'
    assert not (out/'trend.json').exists() and (out/'source.json').exists()
    assert old.replay(root) == obs


def test_replay_rejects_wrong_parent_clock_and_forged_derived_bytes(tmp_path):
    _, out, cap, obs, receipt, base = capture_bundle(tmp_path)
    with pytest.raises(ValueError): trend.replay(out, obs, {**receipt,'capture_hash':'f'*64}, base)
    raw = json.loads((out/'trend.json').read_bytes()); raw['projection']['observations'][0]['phase'] = 'UNKNOWN'
    changed = trend.encoded(raw); (out/'trend.json').write_bytes(changed)
    cap['files']['trend.json'] = trend.identity(changed)
    cap['capture_hash'] = canonical_hash({k:v for k,v in cap.items() if k != 'capture_hash'})
    (out/'capture.json').write_bytes(trend.encoded(cap))
    with pytest.raises(ValueError, match='DERIVED_DIFFERS'): trend.replay(out, obs, receipt, base)


def test_size_limit_is_not_relaxed_for_long_history(tmp_path, monkeypatch):
    _, data, obs, receipt, base = bundle(tmp_path)
    monkeypatch.setattr(trend, 'MAX_READING_BYTES', 10)
    with pytest.raises(ValueError, match='BYTE_LIMIT'): trend.build(data, obs, receipt, base)


def test_compact_installed_sdk_models_preserves_exact_integer_close():
    from eltdx.models.kline import KlineBar, KlineSeries
    bar = KlineBar(time=datetime(2026,9,24,15,tzinfo=timezone(timedelta(hours=8))),
        open=1.001,close=1.001,high=1.001,low=1.001,
        open_price_milli=1001,close_price_milli=1001,high_price_milli=1001,low_price_milli=1001,
        last_close_price_milli=1000,volume_raw=1,amount_raw=1,volume_wire_value=1.,
        volume_lots=1.,amount=1.,open_delta_raw=0,close_delta_raw=0,high_delta_raw=0,low_delta_raw=0)
    series = KlineSeries(exchange='sh',market_id=1,code='000300',period_raw=9,period_param_raw=9,
        period_name='day',start=0,request_count=126,adjust_mode_raw=0,adjust_mode='none',
        anchor_date_raw=0,anchor_date=None,bars=(bar,))
    compact = trend._compact(series, trend.BENCHMARK)
    assert compact['bars'][0][1] == 1001
    assert trend._values(compact, DAY)[1] == [Decimal('1.001')]


def test_same_workflow_adds_only_bounded_history_and_preserves_source_limits():
    text = (Path(__file__).resolve().parents[1]/'.github/workflows/tdx-concept-snapshot.yml').read_text()
    assert 'tdx_concept_snapshot capture' in text and 'tdx_concept_snapshot replay' in text
    assert 'tdx_concept_trend capture' in text and 'tdx_concept_trend replay' in text
    assert 'timeout-minutes: 8' in text and 'include-hidden-files: true' in text
    assert 'schedule:' not in text and 'continue-on-error:' not in text
    assert trend.PARAMS == dict(period='day', start=0, count=126, adjust=None, kind='index',
                               all_pages=False, batch_size=old.HISTORY_BATCH)
    assert old.HISTORY_COUNT == 15 and old.MAX_TOTAL_BYTES == 16*1024*1024
