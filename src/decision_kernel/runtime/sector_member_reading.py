"""Bounded, manual sector-member history reading; not a selector or Research runner.

Reuse saved Sector ZIP validation, the existing HiThink raw-history/action
qualification and return calculation. No second provider, corporate-action
adjustment, role scoring, production state update or automatic research.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from decision_kernel.identity import canonical_hash, canonical_json
from . import current_state as saved
from . import hithink_stock_reading as own
from .sector_radar import _average, _return_over
from .sector_radar_audit import _check_safe_json
from .sector_radar_state import parse_sector_radar_market_state
from .stock_radar_reading import _stock_path

VERSION = 'sector-two-member-history-reading-v0'
REQUEST = 'radar_inputs/sector-member-reading-v0.json'
WINDOWS = (5, 20, 60)
NONE = {'human_attention_authority': 'NONE', 'research_authority': 'NONE',
        'investment_authority': 'NONE'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    # Validate/serialize before creating a file; failed payloads leave no empty success artifact.
    raw = (canonical_json(value) + '\n').encode('utf-8')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def require_request(request):
    saved.check(request['version'] == VERSION and request['max_requests'] == 4,
                'unexpected request version or budget')
    saved.check(request['windows'] == list(WINDOWS), 'common windows must remain 5/20/60')
    members = request['members']
    saved.check(len(members) == 2 and len({m['thscode'] for m in members}) == 2,
                'this approved slice requires exactly two distinct members')
    saved.check(request['price_convention'] == 'RAW_WITH_REPORTED_ACTION_WINDOW_EXCLUSIONS',
                'no implicit adjustment convention')
    saved.check(request['automatic_research'] is False, 'no research execution permission')


def load_source(request, raw, artifact, run):
    """Derive two historical quote projections from the exact original Sector run.

    Projection is explicit: it is NOT a new single-stock quote endpoint response.
    Its receipt time remains the original all-market response's receipt time.
    """
    require_request(request)
    source = request['source']
    saved.check((run['id'], artifact['id'], artifact['digest'], run['head_sha']) ==
                (source['run_id'], source['artifact_id'], source['digest'], source['head_sha']),
                'source differs from the reviewed request')
    saved.run_identity(run, 'sector', success=True)
    files = saved.unpack_archive(raw, artifact, run)
    bundle = {name: files['input-audit/expected/state/' + name] for name in
              ('market-state.json', 'candidate-events.json', 'manifest.json')}
    saved.validate_sector(run, files, bundle)
    state = parse_sector_radar_market_state(bundle['market-state.json'].decode('utf-8'))
    result = json.loads(files['result.json'])
    saved.check(state.sessions[-1].isoformat() == request['market_session'] == result['market_session'],
                'historical session differs')
    matches = [r for r in result['breadth_observations'] if r['sector_thscode'] == request['sector']]
    saved.check(len(matches) == 1, 'exact same-session breadth required')
    breadth = matches[0]
    saved.check(breadth['constituent_set_hash'] == request['constituent_set_hash'] and
                breadth['member_count'] == breadth['priced_member_count'] == 2 and
                breadth['missing_or_unpriced_member_count'] == 0, 'member coverage differs')
    members = {r['thscode']: r['name'] for r in request['members']}
    saved.check({r['thscode']: r['name'] for r in breadth['leaders']} == members,
                'requested members differ from saved complete two-member group')
    audit = json.loads(files['input-audit/manifest.json'])
    saved.inventory(files, audit['files'], 'input-audit/')
    quotes = {}
    for record in audit['requests']:
        if record['path'] != own.SNAPSHOT or record.get('error_type') is not None:
            continue
        name = 'input-audit/' + saved.safe_path(record['response_file'])
        # Match own.request_json: preserve stored decimal lexemes as strings.
        # The original response bytes/hash stay unchanged; never round binary floats.
        response = json.loads(files[name], parse_float=str)
        saved.check(response['code'] == 0, 'saved snapshot failed')
        for row in response['data']['item']:
            code = row.get('thscode')
            if code not in members:
                continue
            saved.check(code not in quotes, 'duplicate saved stock snapshot')
            projected = {'code': 0, 'data': {'timestamp': response['data']['timestamp'], 'item': [row]}}
            quotes[code] = {'quote': projected, 'received_at': record['captured_at'],
                            'source_path': name, 'source_sha256': saved.sha256(files[name]),
                            'semantics': 'DERIVED_SINGLE_ROW_FROM_SAVED_ALL_MARKET_RESPONSE'}
    saved.check(set(quotes) == set(members), 'saved terminal quotes incomplete')
    return state, quotes


def _drawdown(values):
    peak, worst = values[0], values[0] * 0
    for value in values:
        peak = max(peak, value)
        worst = min(worst, value / peak - 1)
    return worst


def compare(request, state, quotes, responses, receipts):
    """All members or no complete comparison; null unsafe windows, never rank them."""
    require_request(request)
    sessions = state.sessions[-61:]
    saved.check(sessions[-1].isoformat() == request['market_session'], 'state cutoff differs')
    series = {s.thscode: s for s in state.series}
    sector = series[request['sector']].closes[-61:]
    benchmark = series[request['benchmark']].closes[-61:]
    rows = []
    for member in request['members']:
        code = member['thscode']
        quote = quotes[code]
        history, actions = responses[code]['history'], responses[code]['actions']
        hist_time = saved.clock(receipts[code]['history'])
        own.check_history_receipt(history, code=code, received_at=hist_time)
        at = saved.clock(receipts[code]['actions'])
        saved.check(hist_time <= at, 'request clock reversed')
        quote_time = saved.clock(quote['received_at'])
        path = _stock_path(state, code, history, at=at, quote=quote['quote'], actions=actions,
                           quote_received_at=quote_time)
        bars, _ = own.qualify(history, quote['quote'], actions, code=code, sessions=state.sessions,
                             params=own.history_params(code, state.sessions), observed_at=at,
                             quote_received_at=quote_time)
        closes = tuple(bars[d]['close_price'] for d in sessions)
        amounts = tuple(bars[d]['turnover'] for d in sessions)
        windows = {}
        for n in WINDOWS:
            ret = path['returns'][str(n)]
            sr = _return_over(sector, end_index=60, sessions=n)
            br = _return_over(benchmark, end_index=60, sessions=n)
            relative = tuple(closes[i] / closes[-n-1] - sector[i] / sector[-n-1]
                             for i in range(61-n, 61)) if ret is not None else ()
            windows[str(n)] = {
                'base_session': sessions[-n-1], 'end_session': sessions[-1],
                'stock_return': ret, 'sector_return': sr, 'benchmark_return': br,
                'excess_vs_sector': None if ret is None else ret-sr,
                'excess_vs_benchmark': None if ret is None else ret-br,
                'close_to_close_max_drawdown': None if ret is None else _drawdown(closes[-n-1:]),
                'positive_cumulative_excess_days_vs_sector': None if ret is None else sum(v > 0 for v in relative),
                'average_turnover_cny': _average(amounts[-n:]),
                'price_comparison_status': 'RAW_COMPARABLE' if ret is not None else 'REPORTED_ACTION_WINDOW_UNAVAILABLE',
            }
        rows.append({**member, 'windows': windows, 'turnover_pulse_5_vs_prior_20': path['turnover_pulse_5_vs_prior_20'],
                     'price_checks': path['input_checks'], 'quote_provenance': quote,
                     'role': 'UNDETERMINED_NOT_INFERRED_FROM_RETURN_RANK'})
    for n in WINDOWS:
        key = str(n)
        all_comparable = all(r['windows'][key]['stock_return'] is not None for r in rows)
        total = sum(r['windows'][key]['average_turnover_cny'] for r in rows)
        for row in rows:
            w = row['windows'][key]
            w['member_return_rank'] = (1 + sum(r['windows'][key]['stock_return'] > w['stock_return'] for r in rows)
                                       if all_comparable else None)
            w['member_count'] = len(rows)
            w['turnover_share_of_complete_group'] = w['average_turnover_cny'] / total
    result = {'version': VERSION, 'status': 'COMPLETE_BOUNDED_RAW_READING', 'request_hash': canonical_hash(request),
              'market_session': request['market_session'], 'sector': request['sector'], 'benchmark': request['benchmark'],
              'rows': rows, 'source': request['source'], **NONE,
              'limits': ['Historical acquisition is now, not a PIT-observed historical execution or backtest.',
                         'Unadjusted prices only. Reported actions exclude affected windows; no total-return or exhaustive-action proof.',
                         'Cumulative-excess day counts use the SAME fixed base within each window, not a rolling beat-rate.',
                         'Two-member turnover share is not market-wide capacity or index contribution; float market cap is unavailable.',
                         'Return ranks are not causal leadership, investment ranking or research priority; roles remain unassigned.']}
    result['reading_hash'] = canonical_hash(result)
    return result


def render(result):
    rows = ['# 板块内成员历史比较 · ' + result['market_session'],
            '**保存观察的历史对照，不是今日行情、复权收益、投资排序或角色认证。**',
            '每个区间使用同一开始与截止收盘；超额为涨幅之差（百分点）。',
            '| 成员 | 区间 | 自身涨幅 | 相对行业 | 相对沪深300 | 组内名次 | 组内成交额占比 | 收盘最大回撤 |',
            '|---|---|---:|---:|---:|---:|---:|---:|']
    pct = lambda x: '未取得可比口径' if x is None else f'{x*100:+.2f}%'
    for member in result['rows']:
        for n in WINDOWS:
            w = member['windows'][str(n)]
            rank = '未定' if w['member_return_rank'] is None else f"{w['member_return_rank']}/{w['member_count']}"
            rows.append('| ' + ' | '.join((member['name']+' '+member['thscode'], str(n)+'交易日',
                pct(w['stock_return']), pct(w['excess_vs_sector']).replace('%','pp'),
                pct(w['excess_vs_benchmark']).replace('%','pp'), rank,
                pct(w['turnover_share_of_complete_group']), pct(w['close_to_close_max_drawdown']))) + ' |')
    rows += ['', '## 怎样使用', '先看不同窗口的领先是否一致，再看相对路径与成交承载；不把涨幅第一直接叫弹性龙头或中军。',
             '如跨公司行为的区间不能直接比较，明确保留缺口，不填值、不把另一家自动推为胜者。',
             '本切片只提供比较依据；没有自动挑公司、Research、Deep、Odds 或账户操作。',
             '完整基期、输入资格、来源与限制见 reading.json；两家公司不能强行凑三种角色。',
             'reading_hash: '+result['reading_hash']]
    return '\n\n'.join(rows[:3])+'\n\n'+'\n'.join(rows[3:])+'\n'


def capture(root, request, state, quotes, *, transport, now=lambda: datetime.now(timezone.utc), pause=time.sleep):
    """Exactly four planned calls, stop on error, preserve safe partial results."""
    root = Path(root)
    root.mkdir(exist_ok=False)
    write(root/'request.json', request)
    events, responses, receipts = [], {}, {}
    try:
        require_request(request)
        for member in request['members']:
            code = member['thscode']
            responses[code], receipts[code] = {}, {}
            for label, endpoint, params in (('history', own.HISTORY, own.history_params(code, state.sessions)),
                                            ('actions', own.ACTIONS, own.action_params(code, state.sessions))):
                if events:
                    pause(20)
                event = {'sequence': len(events)+1, 'thscode': code, 'label': label,
                         'endpoint': endpoint, 'params': params, 'started_at': now().isoformat(), 'status': 'REQUESTED'}
                events.append(event)
                write(root/f"events/{event['sequence']:02d}-request.json", event)
                value = transport(endpoint, params)
                received = now()
                # Unsafe responses are never retained; the caller checks actual key too.
                _check_safe_json(value, None)
                write(root/f'responses/{code}-{label}.json', value)
                event.update(received_at=received.isoformat(), status='RECEIVED_SAFE_JSON')
                responses[code][label], receipts[code][label] = value, received.isoformat()
                if label == 'history':
                    own.check_history_receipt(value, code=code, received_at=received)
                else:
                    own.qualify(responses[code]['history'], quotes[code]['quote'], value, code=code,
                                sessions=state.sessions, params=own.history_params(code,state.sessions),
                                observed_at=received, quote_received_at=saved.clock(quotes[code]['received_at']))
                event['status'] = 'QUALIFIED'
                write(root/f"events/{event['sequence']:02d}-response.json", event)
        result = compare(request, state, quotes, responses, receipts)
        write(root/'reading.json', result)
        (root/'summary.md').write_text(render(result), encoding='utf-8')
        return result
    except Exception as exc:
        failure = {'version': VERSION, 'status': 'INCOMPLETE_MEMBER_COMPARISON',
                   'error_type': type(exc).__name__, 'reason_code': getattr(exc, 'reason_code', None),
                   'request_hash': canonical_hash(request), 'events': events, 'automatic_retry': False,
                   'meaning': 'No complete group/role/Research outcome; safe partial responses remain.', **NONE}
        write(root/'failure.json', failure)
        (root/'summary.md').write_text('# 成员比较未完成\n\n不是零匹配、不是角色未参与；未推定任何公司为leader。\n'
                                      '具体有限错误与已保存请求见failure.json；不自动重试。\n', encoding='utf-8')
        raise
    finally:
        write(root/'receipts.json', receipts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'capture', 'verify'))
    parser.add_argument('--root', required=True, type=Path)
    args = parser.parse_args()
    root = args.root
    request, run, artifact = read(root/'request.json'), read(root/'source-run.json'), read(root/'source-artifact.json')
    state, quotes = load_source(request, (root/'source.zip').read_bytes(), artifact, run)
    if args.mode == 'prepare':
        write(root/'derived-quotes.json', quotes)
        write(root/'source-check.json', {'status':'SOURCE_BOUND', 'request_hash':canonical_hash(request), **NONE})
    elif args.mode == 'capture':
        key = os.environ.get('HITHINK_FINANCE_API_KEY', '')
        if not key:
            raise ValueError('configured market credential required')
        def transport(endpoint, params):
            value = own.request_json(endpoint, params, api_key=key)
            _check_safe_json(value, key)
            return value
        capture(root/'capture', request, state, quotes, transport=transport)
    else:
        cap = root/'capture'
        responses = {m['thscode']: {label: read(cap/f"responses/{m['thscode']}-{label}.json")
                                  for label in ('history', 'actions')} for m in request['members']}
        result = compare(request, state, quotes, responses, read(cap/'receipts.json'))
        saved.check(canonical_hash(read(cap/'reading.json')) == canonical_hash(result), 'offline readback differs')
        write(root/'verification.json', {'status':'MATCHED', 'reading_hash':result['reading_hash'], 'network_calls':0, **NONE})


if __name__ == '__main__':
    main()
