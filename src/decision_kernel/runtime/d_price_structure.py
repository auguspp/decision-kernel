"""CZSC's public geometry over saved index bars, not another detection engine.

Native floats remain explicitly separate from source Decimal strings. Replay
visibility and actual publication observations have different clocks. No source
transport, pickle, trader, probability or permanent state service is used here.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
from importlib.metadata import version as installed_version
import json
import math
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from decision_kernel.identity import canonical_hash, canonical_json
from . import current_state as model
from .d_market_expression import close_structure, _number

VERSION = 'd-saved-czsc-structure-v1'
PARAMETERS = {'max_bi_num': 50, 'min_bi_len': 6}
ALGORITHM = {'package': 'czsc', 'version': '1.0.1',
             'source_commit': '90372af035f01ed9f05070eadddd265b91c84d24'}
MAX_BYTES = 512 * 1024
MAX_BARS = 512  # Worker safety, not a minimum history or another purpose's gate.
ZONE = ZoneInfo('Asia/Shanghai')
FIELDS = {'open': 'open', 'close': 'close', 'high': 'high', 'low': 'low',
          'source_volume': 'vol', 'source_turnover': 'amount'}


def encode(value):
    return (canonical_json(value) + '\n').encode()


def f64(value):
    value = float(value)
    model.check(math.isfinite(value), 'structure nonfinite native value')
    return {'repr': repr(value), 'hex': value.hex()}


def bi_summary(bi):
    geometry = {'symbol': bi.symbol, 'direction': bi.direction.name,
                'sdt': bi.sdt.isoformat(), 'edt': bi.edt.isoformat(),
                'a': f64(bi.fx_a.fx), 'b': f64(bi.fx_b.fx),
                'high': f64(bi.high), 'low': f64(bi.low)}
    return {'key': canonical_hash(geometry), **geometry}


def fx_summary(fx):
    geometry = {'symbol': fx.symbol, 'mark': fx.mark.name, 'dt': fx.dt.isoformat(),
                'fx': f64(fx.fx), 'high': f64(fx.high), 'low': f64(fx.low)}
    return {'key': canonical_hash(geometry), **geometry}


def zs_summary(zs):
    return {'key': canonical_hash({'sdt': zs.sdt.isoformat(), 'sdir': zs.sdir.name}),
            'sdt': zs.sdt.isoformat(), 'edt': zs.edt.isoformat(),
            'sdir': zs.sdir.name, 'edir': zs.edir.name,
            **{k: f64(getattr(zs, k)) for k in ('zg', 'zd', 'gg', 'dd', 'zz')},
            'is_valid': bool(zs.is_valid()), 'stroke_count': len(zs.bis),
            'stroke_keys': [bi_summary(b)['key'] for b in zs.bis]}


def snapshot(engine):
    """Plain public geometry only; no mutable native objects survive this call."""
    ubi = engine.ubi
    unfinished = None if ubi is None else {
        'direction': ubi['direction'].name, 'high': f64(ubi['high']),
        'low': f64(ubi['low']), 'fx_a': fx_summary(ubi['fx_a']),
        'high_bar_session': ubi['high_bar'].dt.date().isoformat(),
        'low_bar_session': ubi['low_bar'].dt.date().isoformat()}
    return {'bi_list': [bi_summary(b) for b in engine.bi_list],
            'finished_keys': [bi_summary(b)['key'] for b in engine.finished_bis],
            'fx_list': [fx_summary(f) for f in engine.fx_list],
            'zs_list': [zs_summary(z) for z in engine.zs_list], 'ubi': unfinished,
            'last_bi_extend': engine.last_bi_extend}


def validate_input(source):
    model.check(source['subject_type'] == 'BENCHMARK_INDEX_NOT_STOCK_COHORT'
                and source['interval'] == '1d' and source['source_adjust'] is None
                and source['requested_adjust'] == 'OMITTED'
                and source['geometry'] == 'PROVIDER_INDEX_OHLC_NO_EXTRA_ADJUSTMENT',
                'structure input purpose or basis')
    from decision_kernel.adapters.hithink_index import normalize_hithink_index_thscode
    model.check(normalize_hithink_index_thscode(source['subject']) == source['subject'],
                'structure index identity')
    model.clock(source['source_captured_at'])
    bars = source['bars']
    model.check(isinstance(bars, list) and 1 <= len(bars) <= MAX_BARS, 'structure bar safety bound')
    sessions = [date.fromisoformat(b['session']) for b in bars]
    model.check(sessions == sorted(set(sessions)), 'structure session order')
    for bar in bars:
        values = {k: _number(bar[k]) for k in FIELDS}
        model.check(all(type(bar[k]) is str for k in FIELDS), 'structure source strings')
        model.check(0 < values['low'] <= min(values['open'], values['close'])
                    <= max(values['open'], values['close']) <= values['high'], 'structure OHLC geometry')
        model.check(values['source_volume'] >= 0 and values['source_turnover'] >= 0,
                    'structure nonnegative volume amount')
        ms = bar['source_date_ms']
        model.check(type(ms) is int and
                    datetime.fromtimestamp(ms / 1000, ZONE).date().isoformat() == bar['session'],
                    'structure source date binding')
    return bars


def make_bar(source, bar, index):
    from czsc import RawBar, Freq
    return RawBar(symbol=source['subject'], dt=datetime.fromisoformat(bar['session']),
                  freq=Freq.D, id=index,
                  **{native: float(_number(bar[key])) for key, native in FIELDS.items()})


def project(source, *, computed_at=None):
    """One forward pass. Final structure does not back-label earlier prefixes."""
    import czsc
    from czsc import CZSC
    model.check(czsc.__version__ == installed_version('czsc') == ALGORITHM['version'],
                'structure exact algorithm version')
    bars = validate_input(source)
    computed_at = computed_at or datetime.now(timezone.utc).isoformat()
    model.check(model.clock(source['source_captured_at']) <= model.clock(computed_at),
                'structure observation precedes source')
    engine, previous = None, None
    states, events, binding, lives = [], [], [], {}
    for index, bar in enumerate(bars):
        raw = make_bar(source, bar, index)
        bound = {'session': bar['session'], 'native_id': index, 'fields': {}}
        for field, native in FIELDS.items():
            actual = f64(getattr(raw, native))
            model.check(actual == f64(float(_number(bar[field]))), 'structure native input changed')
            bound['fields'][native] = {'source_decimal': bar[field], **actual}
        binding.append(bound)
        if engine is None:
            engine = CZSC([raw], **PARAMETERS)
        else:
            engine.update(raw)
        model.check(engine.max_bi_num == PARAMETERS['max_bi_num']
                    and engine.min_bi_len == PARAMETERS['min_bi_len'], 'structure parameters changed')
        current = snapshot(engine)
        obs = {'prefix_count': index + 1, 'replay_session': bar['session']}
        active = {b['key']: b for b in current['bi_list']}
        finished = set(current['finished_keys'])
        old = {} if previous is None else {b['key']: b for b in previous['bi_list']}
        old_finished = set() if previous is None else set(previous['finished_keys'])
        for key in active:
            if key not in lives:
                lives[key] = {'geometry': active[key], 'first_visible': obs,
                              'first_finished': None, 'withdrawals': []}
            if key not in old:
                events.append({**obs, 'kind': 'BI_VISIBLE', 'key': key})
            if key in finished and key not in old_finished:
                if lives[key]['first_finished'] is None:
                    lives[key]['first_finished'] = obs
                events.append({**obs, 'kind': 'ENTERED_FINISHED_BIS', 'key': key})
        for key in sorted(old.keys() - active.keys()):
            is_tail = key == previous['bi_list'][-1]['key']
            pruning = (len(old) == PARAMETERS['max_bi_num'] and
                       key == previous['bi_list'][0]['key'] and not is_tail)
            kind = 'CAPACITY_EVICTION' if pruning else 'TAIL_WITHDRAWN' if is_tail else 'REMOVED_OTHER'
            event = {**obs, 'kind': kind, 'key': key, 'previously_finished': key in old_finished}
            events.append(event)
            lives[key]['withdrawals'].append(event)
        for key in sorted(old_finished - finished):
            events.append({**obs, 'kind': 'LEFT_FINISHED_BIS', 'key': key})
        states.append({**obs, 'input_prefix_hash': canonical_hash(bars[:index + 1]),
                       'native_prefix_hash': canonical_hash(binding),
                       'state_hash': canonical_hash(current), 'bi_count': len(active),
                       'finished_count': len(finished),
                       'valid_centre_count': sum(z['is_valid'] for z in current['zs_list'])})
        previous = current
    metadata = {k: deepcopy(v) for k, v in source.items() if k != 'bars'}
    report = {'version': VERSION, 'algorithm': dict(ALGORITHM), 'parameters': dict(PARAMETERS),
              'subject': source['subject'], 'market_session': bars[-1]['session'],
              'computed_at': computed_at, 'source': metadata,
              'bar_count': len(bars), 'window_start': bars[0]['session'],
              'input_hash': canonical_hash(bars),
              'input_members': [{'session': b['session'], 'hash': canonical_hash(b)} for b in bars],
              'native_input_hash': canonical_hash(binding), 'native_binding': binding,
              'state': current, 'prefix_checks': states, 'replay_events': events,
              'stroke_lifecycles': list(lives.values()),
              'baseline': close_structure([b['session'] for b in bars], [b['close'] for b in bars], (5, 20, 60)),
              'semantics': 'SAVED_INDEX_STRUCTURE_NOT_COMPANY_EVIDENCE_OR_ODDS',
              'replay_clock': 'AFTER_PREFIX_ONLY_NOT_HISTORICAL_PUBLIC_KNOWLEDGE',
              'finished_semantics': 'NATIVE_CURRENT_MEMBERSHIP_REVOCABLE_NOT_PERMANENT_CONFIRMATION',
              'historical_public_availability': source['historical_public_availability'],
              'new_source_requests': 0, 'odds_recomputed': False, 'automatic_research_routing': False,
              **model.AUTHORITY}
    report['report_hash'] = canonical_hash(report)
    model.check(len(encode(report)) <= MAX_BYTES, 'structure report byte bound')
    return report


def compare(previous, current):
    """Changes in observed files; changed history/warm-up is not a new signal."""
    if previous is None:
        return {'status': 'FIRST_RECORDED_READING', 'added': [], 'removed': []}
    same_method = all(previous[k] == current[k] for k in ('version', 'algorithm', 'parameters', 'subject'))
    if not same_method:
        return {'status': 'METHOD_OR_SUBJECT_CHANGED_NOT_COMPARABLE', 'added': [], 'removed': []}
    old = previous['input_members']; new = current['input_members']
    if old == new:
        return {'status': 'UNCHANGED_INPUT_NOT_NEW_MARKET_EVENT', 'added': [], 'removed': []}
    old_map = {b['session']: b['hash'] for b in old}; new_map = {b['session']: b['hash'] for b in new}
    revised = sorted(k for k in old_map.keys() & new_map.keys() if old_map[k] != new_map[k])
    if revised:
        return {'status': 'SOURCE_HISTORY_REVISED_NOT_PURE_FORWARD_CHANGE', 'revised_sessions': revised,
                'added': [], 'removed': []}
    if current['market_session'] <= previous['market_session']:
        return {'status': 'NON_ADVANCING_WINDOW_NOT_NEW_MARKET_EVENT', 'added': [], 'removed': []}
    if new[:len(old)] != old:
        return {'status': 'LOOKBACK_CHANGED_NOT_PURE_FORWARD_CHANGE', 'added': [], 'removed': []}
    old_bis = {b['key'] for b in previous['state']['bi_list']}
    new_bis = {b['key'] for b in current['state']['bi_list']}
    return {'status': 'APPENDED_MARKET_SESSIONS', 'from_session': previous['market_session'],
            'to_session': current['market_session'], 'added': sorted(new_bis - old_bis),
            'removed': sorted(old_bis - new_bis),
            'centres_changed': previous['state']['zs_list'] != current['state']['zs_list']}


def observed_strokes(current, previous):
    """Actual saved-reading observations, NEVER copied from retrospective FX dates."""
    compatible = previous and all(previous[k] == current[k] for k in ('algorithm', 'parameters', 'subject'))
    old = {r['key']: r for r in previous.get('observed_strokes', [])} if compatible else {}
    finished = set(current['state']['finished_keys']); rows = []
    for bi in current['state']['bi_list']:
        row = deepcopy(old.get(bi['key'], {'key': bi['key'], 'first_observed_at': current['computed_at'],
                                         'first_observed_finished_at': None}))
        if bi['key'] in finished and row['first_observed_finished_at'] is None:
            row['first_observed_finished_at'] = current['computed_at']
        row['currently_finished'] = bi['key'] in finished
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Block standard Python networking before importing the optional engine.
    # This is not an OS sandbox or a claim about arbitrary native libraries.
    def no_network(event, _args):
        if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto'}:
            raise RuntimeError('structure worker does not use network')
    sys.addaudithook(no_network)
    # Worker handles only local JSON. No credentials are passed by the reader.
    raw = args.input.read_bytes()
    model.check(0 < len(raw) <= MAX_BYTES, 'structure worker input size')
    report = project(json.loads(raw))
    with args.output.open('xb') as out:
        out.write(encode(report))
    print(json.dumps({'status': 'STRUCTURE_COMPUTED', 'version': report['algorithm']['version'],
                      'bars': report['bar_count'], 'report_hash': report['report_hash']}))


if __name__ == '__main__':
    main()
