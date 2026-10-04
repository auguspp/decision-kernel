"""Publish optional CZSC context through the existing saved-reading Collector.

Existing source capture, archive validation, Git history, budgets and publisher
own their original responsibilities. The native computation runs in a bounded,
credential-free child; its failure cannot discard usable prices or Research.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, time
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import sys
from zipfile import BadZipFile
from tempfile import TemporaryDirectory

from decision_kernel.identity import canonical_hash
from decision_kernel.adapters.hithink import normalize_hithink_calendar
from decision_kernel.adapters.hithink_index import normalize_hithink_completed_index_history
from . import current_state as model
from . import d_price_structure as structure

KEY = 'd_price_structure'
PATH = 'details/stock/price-structure.json'
INPUT_PATH = 'details/stock/price-structure-input.json'
ERRORS = (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, ArithmeticError, BadZipFile)
HISTORY_PATH = '/api/a-share-index/prices/historical'
CALENDAR_PATH = '/api/a-share/calendar/trading-days'


def normalize_archive(files, archive, checked_at):
    """Reuse the original history/calendar adapters, then add OHLC geometry."""
    audit = json.loads(files['input-audit/manifest.json'])
    model.check(audit['audit_hash'] == canonical_hash({k: v for k, v in audit.items() if k != 'audit_hash'})
                and audit['provenance'] == 'LIVE_HITHINK', 'structure source audit identity')
    for name, descriptor in audit['files'].items():
        body = files['input-audit/' + model.safe_path(name)]
        model.check(len(body) == descriptor['bytes'] and model.sha256(body) == descriptor['sha256'],
                    'structure inventory bytes')
    if 'result.json' in files:
        result = json.loads(files['result.json'])
        model.check(result['result_hash'] == canonical_hash({k: v for k, v in result.items() if k != 'result_hash'}),
                    'structure result identity')
        subject = result['benchmark_thscode']
    else:
        # A later Sector failure need not invalidate an earlier complete history.
        state = json.loads(files['input-audit/inputs/market-state.json'])
        subject = state['benchmark']['thscode']
    def response(path, subject=None):
        rows = [r for r in audit['requests'] if r['path'] == path and
                (subject is None or r['params'].get('thscode') == subject)]
        model.check(len(rows) == 1 and rows[0]['error_type'] is None, 'structure source request unavailable')
        request = rows[0]
        model.check(model.clock(request['captured_at']) <= model.clock(checked_at), 'structure future capture')
        name = model.safe_path(request['response_file'])
        model.check(name in audit['files'], 'structure response absent from manifest')
        raw = files['input-audit/' + name]
        body = json.loads(raw, parse_float=Decimal)
        for obj in (body, body['data']):
            model.check(all(obj.get(k) in (None, False, '') for k in ('has_more', 'truncated', 'next', 'next_page')),
                        'structure truncated response')
        return request, raw, body
    calendar_request, calendar_raw, calendar = response(CALENDAR_PATH)
    request, history_raw, history = response(HISTORY_PATH, subject)
    model.check(set(request['params']) == {'thscode', 'interval', 'start', 'end'} and
                request['params']['interval'] == '1d', 'structure history request scope')
    sessions = normalize_hithink_calendar(calendar)
    qualified = normalize_hithink_completed_index_history(history, thscode=subject, sessions=sessions,
                                                         observed_at=model.clock(request['captured_at']))
    model.check(qualified.response_session == qualified.expected_latest_session, 'structure source endpoint stale')
    bars = []
    for row in history['data']['item']:
        ms = row['date_ms']
        model.check(type(ms) is int and int(request['params']['start']) <= ms <= int(request['params']['end']),
                    'structure request date bounds')
        dt = datetime.fromtimestamp(ms / 1000, structure.ZONE)
        model.check(dt.time() == time(0), 'structure date is not a daily label')
        fields = {k: str(structure._number(row[v])) for k, v in {
            'open': 'open_price', 'close': 'close_price', 'high': 'high_price', 'low': 'low_price',
            'source_volume': 'volume', 'source_turnover': 'turnover'}.items()}
        bars.append({'session': dt.date().isoformat(), 'source_date_ms': ms, **fields})
    days = [b['session'] for b in bars]
    model.check(days == [d.isoformat() for d in sessions if days[0] <= d.isoformat() <= days[-1]],
                'structure internal calendar gap or order')
    model.check([Decimal(b['close']) for b in bars] == [p.close for p in qualified.points],
                'structure original adapter close mismatch')
    source = {'subject': subject, 'subject_type': 'BENCHMARK_INDEX_NOT_STOCK_COHORT', 'interval': '1d',
              'source_adjust': None, 'requested_adjust': 'OMITTED',
              'geometry': 'PROVIDER_INDEX_OHLC_NO_EXTRA_ADJUSTMENT',
              'source_captured_at': request['captured_at'], 'historical_public_availability': 'NOT_ESTABLISHED',
              'archive': deepcopy(archive), 'response_file': 'input-audit/' + request['response_file'],
              'response_sha256': model.sha256(history_raw), 'response_git_blob': model.blob_sha(history_raw),
              'calendar_response_sha256': model.sha256(calendar_raw), 'audit_hash': audit['audit_hash'], 'bars': bars}
    structure.validate_input(source)
    return source


def run_native(source):
    """Standard subprocess isolation; no token/env copying, source I/O or pickle."""
    with TemporaryDirectory() as directory:
        root = Path(directory); inp = root / 'input.json'; out = root / 'output.json'
        inp.write_bytes(structure.encode(source))
        env = {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'HOME': directory, 'PYTHONNOUSERSITE': '1',
               'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
               # Support the same trusted checkout in editable and test installs.
               'PYTHONPATH': str(Path(__file__).resolve().parents[2])}
        try:
            result = subprocess.run([sys.executable, '-m', 'decision_kernel.runtime.d_price_structure',
                                     '--input', str(inp), '--output', str(out)],
                                    env=env, cwd=directory, capture_output=True, timeout=45)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('structure worker timeout') from exc
        model.check(result.returncode == 0, 'structure worker failed')
        model.check(out.is_file() and 0 < out.stat().st_size <= structure.MAX_BYTES, 'structure worker output bound')
        report = json.loads(out.read_bytes())
    model.check(report['report_hash'] == canonical_hash({k: v for k, v in report.items() if k != 'report_hash'})
                and report['algorithm'] == structure.ALGORITHM and report['parameters'] == structure.PARAMETERS
                and report['subject'] == source['subject'] and report['input_hash'] == canonical_hash(source['bars']),
                'structure worker identity')
    return report


def _bound(raw, descriptor):
    model.check(len(raw) == descriptor['bytes'] and model.sha256(raw) == descriptor['sha256']
                and model.blob_sha(raw) == descriptor['git_blob'], 'structure retained file identity')


def _reserve(collector, **kwargs):
    from .institutional_radar_reading import _reserve as existing_reserve
    return existing_reserve(collector, **kwargs)


def _previous(collector):
    previous = collector.previous or {}
    descriptor = previous.get('research', {}).get(KEY)
    if not descriptor or 'read_path' not in descriptor:
        return None
    model.check(descriptor['read_path'] == PATH and model.SHA.fullmatch(collector.previous_commit or ''),
                'structure previous locator')
    _reserve(collector, calls=1, files=2)
    raw = collector.api.file(PATH, collector.previous_commit)
    _bound(raw, descriptor)
    payload = json.loads(raw)
    model.check(payload['report_hash'] == canonical_hash({k: v for k, v in payload.items() if k != 'report_hash'}),
                'structure previous report identity')
    return payload


def render(report):
    tail = report['state']['bi_list'][-1:] if report else []
    lines = ['\n\n## D：基准指数价格结构（保存输入、非交易信号）\n',
             f"市场日：{report['market_session']}；{report['subject']}；{report['bar_count']}根；CZSC 1.0.1／50／6。",
             f"来源采集：{report['source']['source_captured_at']}；本次计算：{report['computed_at']}。",
             f"本次输入状态：{report['reading_status']}；与上一读取：{report['observed_delta']['status']}。",
             f"{len(report['state']['bi_list'])}笔，{len(report['state']['finished_keys'])}笔在当次finished_bis；"
             f"{sum(z['is_valid'] for z in report['state']['zs_list'])}个native有效中枢。finished_bis可撤回。"]
    if tail:
        bi = tail[0]
        lines.append(f"末笔几何：{bi['sdt'][:10]}→{bi['edt'][:10]}，{bi['direction']}，"
                     f"{bi['a']['repr']}→{bi['b']['repr']}；几何日期不是首次获知或永久确认日期。")
    life = {row['geometry']['key']: row for row in report['stroke_lifecycles']}
    seen = {row['key']: row for row in report['observed_strokes']}
    finished = set(report['state']['finished_keys'])
    lines += ['\n| 几何起止 | 方向／端点 | 首见回放前缀日 | 当次finished | 实际首次观察UTC |',
              '|---|---|---|---|---|']
    for bi in report['state']['bi_list']:
        row = life[bi['key']]
        lines.append(f"| {bi['sdt'][:10]}→{bi['edt'][:10]} | {bi['direction']}／"
                     f"{bi['a']['repr']}→{bi['b']['repr']} | {row['first_visible']['replay_session']} | "
                     f"{'是（仍可撤回）' if bi['key'] in finished else '否'} | "
                     f"{seen[bi['key']]['first_observed_at']} |")
    if report['state']['zs_list']:
        lines += ['\n| 中枢几何起止 | 核心zd–zg | 极值dd–gg | native valid |', '|---|---|---|---|']
        for z in report['state']['zs_list']:
            lines.append(f"| {z['sdt'][:10]}→{z['edt'][:10]} | {z['zd']['repr']}–{z['zg']['repr']} | "
                         f"{z['dd']['repr']}–{z['gg']['repr']} | {z['is_valid']} |")
    lines += ['历史前缀回放时间与本次实际观察时间分别保留；滚动窗口变化不包装为新信号。',
              f'完整结构、撤回、原收盘基线和数值绑定见 [{PATH}]({PATH})；'
              f'来源日线见 [{INPUT_PATH}]({INPUT_PATH})。原行情失败与公司Research保持独立。\n']
    return '\n'.join(lines)


def attach(collector, baseline, *, retained_limit):
    """Optional addition, committed only after ALL existing capacity checks pass."""
    from .independent_stock_reading import _cached
    model.validate_read_package(baseline)
    model.check(collector.code_commit == baseline['code_commit'], 'structure reader code identity')
    before = dict(collector.files)
    previous, prior_gap = None, None
    try:
        previous = _previous(collector)
    except ERRORS as exc:
        prior_gap = type(exc).__name__
    report, source = None, None
    phase = 'SOURCE_ARCHIVE'
    lane = baseline['lanes'].get('sector', {})
    attempt = lane.get('latest_attempt') or {}
    last = lane.get('last_qualified_result') or {}
    failed = (attempt.get('operation') or {}).get('source') if attempt.get('conclusion') == 'failure' else None
    reference = failed or last.get('archive')
    try:
        _reserve(collector, files=2)
        files = _cached(collector, reference, baseline['checks']['finished_at'])
        phase = 'SOURCE_GEOMETRY'
        source = normalize_archive(files, reference, baseline['checks']['finished_at'])
        phase = 'NATIVE_COMPUTATION'
        same = previous and previous.get('version') == structure.VERSION and previous.get('algorithm') == structure.ALGORITHM
        same = same and previous.get('parameters') == structure.PARAMETERS and previous.get('subject') == source['subject']
        same = same and previous.get('input_hash') == canonical_hash(source['bars'])
        same = same and all(previous.get('source', {}).get(k) == source[k]
                            for k in ('audit_hash', 'source_captured_at', 'response_sha256'))
        report = deepcopy(previous) if same else run_native(source)
        report['source'] = {k: deepcopy(v) for k, v in source.items() if k != 'bars'}
        report['reading_status'] = 'SAME_INPUT_REUSED' if same else 'SAVED_SOURCE_COMPUTED'
        report['observed_delta'] = structure.compare(previous, report)
        report['observed_strokes'] = structure.observed_strokes(report, previous)
        report['previous_reading_commit'] = collector.previous_commit if previous else None
        report['previous_reading_gap'] = prior_gap
        report['source_selection'] = 'FAILED_SECTOR_AVAILABLE_INPUT' if failed else 'LAST_QUALIFIED_SECTOR_INPUT'
        report['latest_sector_attempt'] = deepcopy(attempt)
        report['source_lane_gaps'] = deepcopy(lane.get('gaps', []))
        report['checked_at'] = baseline['checks']['finished_at']
        report['code_commit'] = collector.code_commit
        input_raw = structure.encode(source)
        report['normalized_input_file'] = {'read_path': INPUT_PATH, 'bytes': len(input_raw),
            'sha256': model.sha256(input_raw), 'git_blob': model.blob_sha(input_raw),
            'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}
        report['report_hash'] = canonical_hash({k: v for k, v in report.items() if k != 'report_hash'})
        phase = 'PUBLICATION_CAPACITY'
        raw = structure.encode(report); note = render(report).encode()
        model.check(len(raw) <= structure.MAX_BYTES and len(input_raw) <= structure.MAX_BYTES,
                    'structure saved detail byte bound')
        descriptor = {'read_path': PATH, 'bytes': len(raw), 'sha256': model.sha256(raw),
                      'git_blob': model.blob_sha(raw), 'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}
        payload = deepcopy(baseline); payload['research'][KEY] = descriptor
        payload['reading_hash'] = canonical_hash({k: v for k, v in payload.items() if k != 'reading_hash'})
        entry = model.read_package_bytes(payload)
        total = sum(len(v) for k, v in collector.files.items() if k != 'current-state.json')
        model.check(total + len(raw) + len(input_raw) + len(entry) + len(note) <= retained_limit,
                    'structure total publication bound')
        _reserve(collector, files=2)
        collector.retain(PATH, raw); collector.retain(INPUT_PATH, input_raw)
        collector.files['current-state.json'] = entry
        collector.files['README.md'] += note
        model.validate_read_package(payload)
        return payload
    except ERRORS as exc:
        collector.files = before
        # Existing prices/Research remain usable. No older success is substituted
        # for this failure; previous Git versions remain independently readable.
        payload = deepcopy(baseline)
        payload['research'][KEY] = {'status': 'STRUCTURE_UNAVAILABLE_OTHER_INPUTS_PRESERVED',
                                    'phase': phase, 'error_type': type(exc).__name__,
                                    'previous_reading_gap': prior_gap, 'new_source_requests': 0}
        payload['reading_hash'] = canonical_hash({k: v for k, v in payload.items() if k != 'reading_hash'})
        if previous:
            payload['research'][KEY]['previous_saved_reading'] = {
                'commit': collector.previous_commit, 'file': collector.previous['research'][KEY],
                'market_session': previous['market_session'], 'meaning': 'PREVIOUS_READING_NOT_CURRENT_SUCCESS'}
            payload['reading_hash'] = canonical_hash({k: v for k, v in payload.items() if k != 'reading_hash'})
        try:
            entry = model.read_package_bytes(payload)
        except ValueError:
            print('D_STRUCTURE_UNAVAILABLE: existing root capacity preserved')
            return baseline
        note = b'\n\nD price structure unavailable; existing prices and Research preserved.\n'
        total = sum(len(v) for k, v in before.items() if k != 'current-state.json')
        if total + len(entry) + len(note) > retained_limit:
            return baseline
        collector.files['current-state.json'] = entry
        collector.files['README.md'] += note
        return payload
