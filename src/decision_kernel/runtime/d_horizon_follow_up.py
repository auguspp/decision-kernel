"""Read a declared horizon case using existing saved-price math and Git history.

No signal classifier, forecast, backtest engine, source request or trade is made.
The old case owns its hypothesis and clocks; this module only follows its dates.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, time, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from decision_kernel.identity import canonical_hash
from . import current_state as model
from . import stock_market_inputs as prices

CONFIG = 'decision_inputs/d-horizon-follow-up.json'
KEY = 'd_horizon_follow_up'
PATH = 'details/stock/horizon-follow-up.json'
VERSION = 'd-retained-horizon-follow-up-v1'
ERRORS = (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, ArithmeticError)


def read_price_parts(files, expected_report):
    """Original full replay, then the original table/key parsers; no alternate feed."""
    with TemporaryDirectory() as directory:
        root = Path(directory)
        for name, raw in files.items():
            path = root / model.safe_path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        report = prices.verify(root)
    model.check(report == expected_report and report['provenance'] == 'LIVE_TUSHARE_RELAY',
                'horizon original price replay differs')
    receipt = prices.loads(files['receipt.json'])
    first = receipt['calls'][0]
    raw = files[first['attempts'][-1]['response_file']]
    rows, partial = prices.table(raw, 'trade_cal', ('exchange', 'cal_date', 'is_open'))
    model.check(not partial, 'horizon calendar truncated')
    calendar = {prices.day(r['cal_date']).isoformat(): str(r['is_open']) == '1' for r in rows}
    tables, coverage = {}, deepcopy(report['source_row_coverage'])
    for call in receipt['calls'][1:]:
        if call['status'] != 'SUCCESS':
            continue
        item = {k: call[k] for k in ('api', 'params')}
        name = call['api'] + ':' + call['params']['trade_date']
        if coverage.get(name, {}).get('status') != 'SOURCE_ROWS_READ':
            continue
        values, _ = prices.keyed(files[call['attempts'][-1]['response_file']], item)
        tables[call['api'], call['params']['trade_date']] = values
    return calendar, tables, coverage


def calendar_prefix(case, market_session, values, previous=None):
    """Count explicit completed SSE sessions, never weekdays or first good prices."""
    frozen = model.clock(case['frozen_at']).astimezone(prices.ZONE)
    first = frozen.date() + timedelta(days=int(frozen.time() >= time(15)))
    end = date.fromisoformat(market_session)
    retained = (previous or {}).get('calendar_prefix', [])
    known = {r['session']: r['is_open'] for r in retained}
    model.check(all(type(v) is bool for v in values.values()), 'horizon calendar values')
    model.check(all(known[k] == values[k] for k in known.keys() & values.keys()),
                'horizon calendar revised; original anchor cannot silently move')
    known.update(values)
    if retained:
        end = max(end, date.fromisoformat(retained[-1]['session']))
    prefix, opened, gap = [], [], None
    day = first
    while day <= end and len(opened) <= max(case['checkpoints']):
        model.check(len(prefix) < 512, 'horizon calendar safety bound')
        label = day.isoformat()
        if label not in known:
            gap = label
            break
        prefix.append({'session': label, 'is_open': known[label]})
        if known[label]:
            opened.append(label)
        day += timedelta(days=1)
    return prefix, opened, gap


def exact_interval(symbol, anchor, target, period, tables, coverage):
    """Delegate all factor arithmetic to the already delivered interval consumer."""
    a, b = anchor.replace('-', ''), target.replace('-', '')
    context = {'market_session': target, 'end_date': b,
               'bases': {str(n): a if n == period else None for n in prices.WINDOWS}}
    selected = {key: {symbol: rows[symbol]} if symbol in rows else {} for key, rows in tables.items()}
    result = prices.evaluate(context, selected, coverage)
    row = next((r for r in result['rows'] if r[0] == symbol), None)
    i = prices.WINDOWS.index(period)
    status = prices.STATUS[str(row[5 + i])] if row else 'PRICE_ENDPOINT_UNAVAILABLE'
    endpoints = {}
    for label, d in (('start', a), ('end', b)):
        endpoints[label] = {'session': prices.day(d).isoformat(), **{
            field: str(tables[api, d][symbol][field]) if symbol in tables.get((api, d), {}) else None
            for api, field in (('daily', 'close'), ('adj_factor', 'adj_factor'))}}
    return {'status': status, 'change': row[2 + i] if row else None, 'endpoints': endpoints,
            'basis': result['comparison_basis'], 'formula': result['formula'],
            'source_row_coverage': {k: v for k, v in coverage.items() if k.split(':')[-1] in (a, b)}}


def project(case, daily, calendar, tables, coverage, *, checked_at, source, previous=None, previous_reading_commit=None,
            calendar_market_session=None):
    """Case-owned deadlines are displayed, not turned into automatic judgments."""
    frozen = model.clock(case['frozen_at'])
    model.check(model.clock(daily['observed_at']) <= model.clock(daily['received_through'])
                <= model.clock(checked_at), 'horizon price clock')
    model.check(frozen <= model.clock(checked_at), 'horizon freeze is in the future')
    model.check(prices.CODE.fullmatch(case['symbol']) and case['symbol'].endswith('.SH'),
                'this case calendar is SSE, not a universal market calendar')
    model.check(case['checkpoints'] and len(set(case['checkpoints'])) == len(case['checkpoints'])
                and all(type(n) is int and n in prices.WINDOWS for n in case['checkpoints']),
                'use existing interval periods explicitly declared by the case')
    identity = canonical_hash(case)
    model.check(previous is None or previous['contract_hash'] == identity,
                'horizon contract changed; do not reset the same case in place')
    prefix, opened, gap = calendar_prefix(case, calendar_market_session or daily['market_session'], calendar, previous)
    anchor = opened[0] if opened else None
    model.check(not previous or previous.get('anchor_session') in (None, anchor),
                'horizon source cannot move or forget the original anchor')
    past = {row['period']: row for row in (previous or {}).get('checkpoints', [])}
    results = []
    for n in case['checkpoints']:
        target = opened[n] if len(opened) > n else None
        current = {'period': n, 'anchor_session': anchor, 'target_session': target,
                   'status': 'CALENDAR_GAP' if gap else 'WAITING_FOR_COMPLETED_SESSION',
                   'change': None, 'source': deepcopy(source), 'received_through': daily['received_through']}
        if target:
            current.update(exact_interval(case['symbol'], anchor, target, n, tables, coverage))
        old = past.get(n, {})
        if old.get('target_session'):
            model.check(target == old['target_session'], 'horizon target identity changed')
        if current['status'] == 'COMPARABLE':
            unchanged = old.get('status') == 'COMPARABLE' and all(
                current[k] == old[k] for k in ('target_session', 'endpoints', 'change'))
            current['first_recorded_at'] = old['first_recorded_at'] if unchanged else checked_at
            current['observation'] = ('UNCHANGED_ENDPOINT_RESULT' if unchanged else
                'REVISED_ENDPOINT_RESULT' if old.get('status') == 'COMPARABLE' else 'FIRST_RECORDED_ENDPOINT_RESULT')
            target_close = model.clock(target + 'T15:00:00+08:00')
            current['acquisition_timing'] = ('SAME_SESSION_AFTER_CLOSE' if
                model.clock(daily['received_through']).astimezone(prices.ZONE).date().isoformat() == target
                else 'LATER_ACQUISITION_NOT_HISTORICAL_KNOWLEDGE')
            model.check(target_close <= model.clock(daily['received_through']), 'horizon future endpoint')
        elif old.get('status') == 'COMPARABLE':
            model.check(model.SHA.fullmatch(previous_reading_commit or ''), 'horizon previous result locator')
            origin = old['source'].get('retained_reading_commit', previous_reading_commit)
            original_hash = old['source'].get('archive_sha256', old['source'].get('sha256'))
            current = {**deepcopy(old), 'current_source_status': current['status'],
                'source': {'retained_reading_commit': origin, 'report_path': PATH,
                           'archive_sha256': original_hash, 'meaning': 'EXPLICIT_PRIOR_READING_NOT_SAME_R_ARCHIVE'},
                'observation': 'RETAINED_PREVIOUS_ENDPOINT_RESULT_NOT_CURRENT_SOURCE_SUCCESS'}
        results.append(current)
    quote = next((dict(zip(daily['columns'], row, strict=True)) for row in daily['rows']
                  if row[0] == case['symbol']), None)
    return {'id': case['id'], 'record_id': case['record_id'], 'symbol': case['symbol'],
            'contract_hash': identity, 'frozen_at': case['frozen_at'], 'anchor_session': anchor,
            'calendar_prefix': prefix, 'calendar_gap': gap, 'checkpoints': results,
            'retained_interpretation': deepcopy(case['interpretation']),
            'long_research_deadline': case['long_research_deadline'],
            'analyst_review_by': case['analyst_review_by'],
            'review_clock': 'DATE_REACHED_NOT_ECONOMIC_VERIFICATION' if
                model.clock(checked_at).astimezone(prices.ZONE).date() >= date.fromisoformat(case['analyst_review_by'])
                else 'REVIEW_DATE_NOT_REACHED',
            'historical_price_context': {'market_session': daily['market_session'], 'row': quote,
                'source': deepcopy(source), 'received_through': daily['received_through'],
                'meaning': 'BACKWARD_LOOKING_CONTEXT_NOT_THE_FROZEN_FORWARD_WINDOW'},
            'economic_result': 'NOT_AUTOMATICALLY_ADJUDICATED',
            'execution_result': 'NOT_EVALUATED_NO_EXECUTION_INPUT',
            'benchmark_comparison': 'NOT_ATTACHED_DOES_NOT_BLOCK_SECURITY_INTERVAL',
            'path_metrics': 'NOT_COMPUTED_NO_CONTINUOUS_PATH',
            'opportunity_probability': None, 'opportunity_established': None}


def render(report):
    lines = ['\n\n## D：已冻结案例的多期限跟进（不是交易信号）\n',
             f"读取截止：{report['checked_at']}；最新价格尝试：{report['latest_price_status']}。"]
    for row, body_ref in zip(report['cases'], report['case_bodies'], strict=True):
        lines += [f"\n### {row['symbol']} / {row['id']}",
            f"原冻结：{row['frozen_at']}；S0：{row['anchor_session'] or '尚未由已完成交易日日历建立'}。",
            f"长期Research期限：{row['long_research_deadline']}（不缩短、不重算原长期模型）。",
            '中期：' + row['retained_interpretation']['intermediate'],
            '反证／停止：' + row['retained_interpretation']['invalidation'],
            f"原分析者有限裁定日：{row['analyst_review_by']}；{row['review_clock']}（日期到达不等于兑现）。",
            '| 原事前窗口 | 准确起止 | 区间变化 | 本次状态 |', '|---|---|---:|---|']
        for item in row['checkpoints']:
            value = '未可比' if item['change'] is None else f"{Decimal(item['change']):+.2%}"
            lines.append(f"| S0之后{item['period']}交易日 | {item['anchor_session'] or '未建立'} → "
                         f"{item['target_session'] or '未建立'} | {value} | {item.get('observation', item['status'])} |")
        lines.append(f"[原案例正文（只读所声明README）]({body_ref['read_path']})。")
        context = row['historical_price_context']
        quote = context['row']
        if quote:
            backward = '／'.join('未可比' if quote['change_' + str(n)] is None else
                                f"{Decimal(quote['change_' + str(n)]):+.2%}" for n in prices.WINDOWS)
            lines.append('原5／20／60交易日向后价格变化：' + backward + '（不等于事前窗口收益）。')
        lines += [f"已有价格背景：{context['market_session']}，收盘{quote['raw_close'] if quote else '未取得'}；"
                  '它不是上述向前窗口的收益。',
                  '缺S0不顺延；缺因子不填1；前缀交易日按来源日历计数；晚到结果保留实际取得时间。']
    lines += [f'[完整期限、准确端点／缺口、原案例正文和来源定位]({PATH})。',
              '经营兑现、市场表达和真实执行分别评价；未产生机会成立、概率、持仓或自动唤醒结论。\n']
    return '\n'.join(lines)


def _bound(raw, descriptor):
    model.check(len(raw) == descriptor['bytes'] and model.sha256(raw) == descriptor['sha256']
                and model.blob_sha(raw) == descriptor['git_blob'], 'horizon retained bytes differ')


def _previous(collector):
    descriptor = (collector.previous or {}).get('research', {}).get(KEY)
    if not descriptor or 'read_path' not in descriptor:
        return None
    model.check(descriptor['read_path'] == PATH and model.SHA.fullmatch(collector.previous_commit or ''),
                'horizon previous reading identity')
    raw = collector.api.file(PATH, collector.previous_commit)
    _bound(raw, descriptor)
    value = prices.loads(raw)
    model.check(value['version'] == VERSION and value['report_hash'] ==
                canonical_hash({k: v for k, v in value.items() if k != 'report_hash'}), 'horizon previous report')
    return value


def _continuation_lines(rows):
    lines = ['\n\n## D：原期限下的后继经济解释\n',
             '以下仅引用已登记研究接续；不是本轮新研究、原冻结时已知事实或新的Human接受。']
    for row in rows:
        lines.append('\n### ' + str(row.get('case_id') or '接续读取'))
        if row['status'] != 'RETAINED_CONTINUATION_READ_OK':
            lines.append('后继解释读取缺口；原冻结案例、期限、价格与历史结果仍保留。')
            continue
        lines.append(f"该研究自报截止：{row['research_cutoff']}；本次读取：{row['read_at']}。")
        for excerpt in row['excerpts']:
            lines.append('\n'.join('> ' + line for line in excerpt.splitlines()))
            lines.append('')
        lines.append(f"[本次选定接续原文]({row['source']['read_path']})；只读取该README，不代表完整档案或原公司来源已复核。")
    return '\n'.join(lines) + '\n'


def _publish_continuations(collector, baseline, report, rows, *, retained_limit):
    """Replace only this publication's derived files, never the frozen cases."""
    from .institutional_radar_reading import _reserve
    checked = collector.now()
    model.check(model.clock(checked) >= model.clock(baseline['checks']['finished_at']),
                'continuation publication clock reversed')
    updated = {**report, 'checked_at': checked, 'economic_continuations': rows}
    updated['report_hash'] = canonical_hash({k: v for k, v in updated.items() if k != 'report_hash'})
    raw = prices.dumps(updated)
    model.check(len(raw) <= prices.MAX_REPORT, 'continuation detail capacity')
    research = deepcopy(baseline['research'])
    research[KEY] = {'read_path': PATH, 'bytes': len(raw), 'sha256': model.sha256(raw),
        'git_blob': model.blob_sha(raw), 'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}
    payload = model.assemble(code_commit=baseline['code_commit'], checked_at=checked,
        check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
        capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
    updates = {PATH: raw, 'current-state.json': model.read_package_bytes(payload),
               'README.md': collector.files['README.md'] + _continuation_lines(rows).encode()}
    model.check(sum(map(len, {**collector.files, **updates}.values())) <= retained_limit,
                'continuation total capacity')
    _reserve(collector, replacements=updates)
    collector.files.update(updates)
    return payload


def _attach_continuations(collector, baseline, report, items, registry, *, retained_limit):
    """Optional exact-source excerpts; a local failure cannot erase the core reading.

    This is not a second research store or an economic classifier. Selection is
    explicit in the existing config, outside the immutable cases/contract hashes.
    """
    if items == []:
        return baseline
    from .institutional_radar_reading import _reserve
    before, sources = dict(collector.files), dict(collector.sources)
    phase = 'CONTINUATION_DECLARATION'
    try:
        model.check(isinstance(items, list) and 0 < len(items) <= 8,
                    'continuation selection must be a bounded list')
        model.check(all(isinstance(item, dict) and isinstance(item.get('case_id'), str) for item in items)
                    and len({item['case_id'] for item in items}) == len(items),
                    'select one exact continuation per case, not an inferred latest version')
        cases = {case['id']: case for case in report['cases']}
        rows = []
        for item in items:
            saved_files, saved_sources = dict(collector.files), dict(collector.sources)
            phase = 'CONTINUATION_IDENTITY'
            row = {'case_id': item['case_id'], 'record_id': item.get('record_id'),
                   'meaning': 'RETAINED_INTERPRETATION_NOT_ORIGINAL_KNOWLEDGE_OR_ACCEPTANCE'}
            try:
                case = cases[item['case_id']]
                record = registry[item['record_id']]
                model.check(record['case'] == case['symbol']
                            and record['use'] == 'RETAINED_RESEARCH_DOCUMENT'
                            and record['archive']['format'] == 'RETAINED_FILES'
                            and record['id'] != case['record_id'], 'continuation research identity differs')
                source = record['source']
                model.check(model.SHA.fullmatch(source['ref']) and model.SHA.fullmatch(source['git_blob']),
                            'continuation source must pin commit and blob')
                excerpts = item['excerpts']
                model.check(isinstance(excerpts, list) and 0 < len(excerpts) <= 8
                            and all(isinstance(t, str) and 0 < len(t.strip()) <= 4096 for t in excerpts),
                            'continuation excerpts must be bounded nonempty text')
                phase = 'CONTINUATION_CLOCK'
                read_at = collector.now()
                model.check(model.clock(case['frozen_at']) <= model.clock(item['research_cutoff'])
                            <= model.clock(read_at), 'continuation cutoff outside reading window')
                phase = 'CONTINUATION_SOURCE'
                _reserve(collector, calls=1, files=3)
                raw, body_ref = collector.source({k: source[k] for k in ('path', 'ref', 'git_blob')})
                _bound(raw, source)
                _bound(raw, body_ref)
                model.check(model.sha256(raw) == item['document_sha256'], 'continuation selected bytes differ')
                text = raw.decode('utf-8')
                predecessor = registry[case['record_id']]['source']
                predecessor_link = f"/blob/{predecessor['ref']}/{predecessor['path']}"
                model.check(all(value in text for value in [predecessor_link, case['frozen_at'],
                            case['long_research_deadline'], case['analyst_review_by'],
                            item['research_cutoff'], *excerpts]), 'continuation excerpt or predecessor not in source')
                finished = collector.now()
                model.check(model.clock(finished) >= model.clock(read_at), 'continuation read clock reversed')
                row.update(status='RETAINED_CONTINUATION_READ_OK', source=body_ref,
                    research_cutoff=item['research_cutoff'], read_at=finished, excerpts=deepcopy(excerpts),
                    original_contract_hash=case['contract_hash'], **model.AUTHORITY)
            except ERRORS as exc:
                collector.files, collector.sources = saved_files, saved_sources
                row.update(status='CONTINUATION_UNAVAILABLE_CORE_PRESERVED',
                           phase=phase, error_type=type(exc).__name__)
            rows.append(row)
        phase = 'CONTINUATION_PUBLICATION'
        return _publish_continuations(collector, baseline, report, rows, retained_limit=retained_limit)
    except ERRORS as exc:
        collector.files, collector.sources = before, sources
        gap = [{'status': 'CONTINUATION_UNAVAILABLE_CORE_PRESERVED',
                'phase': phase, 'error_type': type(exc).__name__}]
        try:
            return _publish_continuations(collector, baseline, report, gap, retained_limit=retained_limit)
        except ERRORS:
            # No room even for the gap: keep the already verified core untouched.
            collector.files, collector.sources = before, sources
            return baseline


def attach(collector, baseline, *, retained_limit):
    """Small file boundary in the existing publisher; rollback only this addition."""
    from .institutional_radar_reading import _reserve
    from .research_archive_index import read_entries
    from .independent_stock_reading import _cached, KEY as STOCK_KEY
    from .d_auction_follow_through import _read
    before, sources = dict(collector.files), dict(collector.sources)
    phase, prior = 'DECLARATION', None
    try:
        model.validate_read_package(baseline)
        model.check(collector.code_commit == baseline['code_commit'], 'horizon code identity')
        _reserve(collector, files=2)
        raw, config_ref = collector.source({'path': CONFIG})
        config = prices.loads(raw)
        model.check(config['version'] == VERSION and 0 < len(config['cases']) <= 8, 'horizon declaration')
        model.check(len({c['id'] for c in config['cases']}) == len(config['cases']), 'horizon duplicate case')
        _reserve(collector, calls=len(config['cases']) + 1, files=len(config['cases']) + 2)
        registry = {r['id']: r for r in read_entries(baseline['research'], collector.files.__getitem__)}
        phase = 'PREVIOUS_READING'
        prior_gap = None
        try:
            prior = _previous(collector)
            model.check(prior is None or model.clock(prior['checked_at']) <= model.clock(collector.now()),
                        'horizon previous check is in the future')
        except ERRORS as exc:
            prior, prior_gap = None, type(exc).__name__
        prior_rows = {r['id']: r for r in (prior or {}).get('cases', [])}
        phase = 'EXISTING_PRICE_INPUT'
        ref = baseline['research'][STOCK_KEY]
        raw = collector.files[ref['read_path']]; _bound(raw, ref)
        daily_state = prices.loads(raw)['daily_market_inputs']
        available = [s for s in (daily_state, daily_state.get('last_qualified_result') or {})
                     if s.get('file') and s.get('market_session')]
        model.check(available, 'horizon no saved calendar or prices')
        selected = next((s for s in available if s.get('cohort_denominator', 0) > 0), available[0])
        cutoff = collector.now()
        daily = _read(collector, selected, cutoff)
        archive = selected['source_archive']
        files = _cached(collector, archive, cutoff)
        calendar, tables, coverage = read_price_parts(files, daily)
        calendar_report, calendar_source = daily, archive
        # A complete calendar still anchors S0 when that day's prices failed.
        # Never splice prices or factors across these archives.
        if available[0] is not selected:
            calendar_report = _read(collector, available[0], cutoff)
            calendar_source = available[0]['source_archive']
            calendar, _, _ = read_price_parts(_cached(collector, calendar_source, cutoff), calendar_report)
        phase = 'CASE_BODY'
        cases, body_refs = [], []
        for case in config['cases']:
            record = registry[case['record_id']]
            model.check(record['case'] == case['symbol'] and record['use'] == 'RETAINED_RESEARCH_DOCUMENT'
                        and record['archive']['format'] == 'RETAINED_FILES', 'horizon case use differs')
            document = record['source']
            raw, body_ref = collector.source({k: document[k] for k in ('path', 'ref', 'git_blob')})
            _bound(raw, document)
            model.check(model.sha256(raw) == case['document_sha256'] and
                        all(text in raw.decode('utf-8') for text in [*case['source_assertions'], case['frozen_at'],
                            case['long_research_deadline'], case['analyst_review_by'],
                            *case['interpretation'].values()]), 'horizon declaration not in body')
            body_refs.append(body_ref)
            cases.append(project(case, daily, calendar, tables, coverage, checked_at=collector.now(),
                                 source=archive, previous=prior_rows.get(case['id']),
                                 previous_reading_commit=collector.previous_commit,
                                 calendar_market_session=calendar_report['market_session']))
        checked = collector.now()
        model.check(model.clock(checked) >= model.clock(baseline['checks']['finished_at']), 'horizon clock reversed')
        report = {'version': VERSION, 'code_commit': collector.code_commit, 'checked_at': checked,
            'config': config_ref, 'case_bodies': body_refs, 'body_scope': 'DECLARED_README_NOT_FULL_ARCHIVE_RECOVERY',
            'price_file': selected['file'], 'calendar_source': calendar_source,
            'calendar_market_session': calendar_report['market_session'], 'latest_price_status': daily_state['status'],
            'using_prior_price_source': selected is not daily_state, 'cases': cases,
            'previous_reading_commit': collector.previous_commit if prior else None,
            'previous_reading_gap': prior_gap,
            'new_source_requests': 0, 'automatic_research_routing': False, **model.AUTHORITY}
        report['report_hash'] = canonical_hash(report)
        phase = 'PUBLICATION_CAPACITY'
        raw, note = prices.dumps(report), render(report).encode()
        model.check(len(raw) <= prices.MAX_REPORT, 'horizon detail capacity')
        descriptor = {'read_path': PATH, 'bytes': len(raw), 'sha256': model.sha256(raw),
            'git_blob': model.blob_sha(raw), 'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}
        research = deepcopy(baseline['research']); research[KEY] = descriptor
        payload = model.assemble(code_commit=baseline['code_commit'], checked_at=checked,
            check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
            capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
        entry = model.read_package_bytes(payload)
        model.check(sum(len(v) for k,v in collector.files.items() if k != 'current-state.json')
                    + len(raw) + len(note) + len(entry) <= retained_limit, 'horizon total capacity')
        _reserve(collector, files=2)
        collector.retain(PATH, raw)
        collector.files['current-state.json'] = entry
        collector.files['README.md'] += note
        return _attach_continuations(collector, payload, report, config.get('continuations', []),
                                     registry, retained_limit=retained_limit)
    except ERRORS as exc:
        collector.files, collector.sources = before, sources
        # A bad new attachment cannot discard the earlier completed reading.
        reading = {'status': 'HORIZON_FOLLOW_UP_UNAVAILABLE_OTHER_INPUTS_PRESERVED',
            'phase': phase, 'error_type': type(exc).__name__, 'new_source_requests': 0,
            'previous_reading_commit': collector.previous_commit if prior else None}
        try:
            checked = collector.now()
            model.check(model.clock(checked) >= model.clock(baseline['checks']['finished_at']), 'horizon failure clock')
            research = deepcopy(baseline['research']); research[KEY] = reading
            payload = model.assemble(code_commit=baseline['code_commit'], checked_at=checked,
                check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
                capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
            entry = model.read_package_bytes(payload)
            note = b'\nD horizon follow-up unavailable; existing prices, research and decisions preserved.\n'
            model.check(sum(len(v) for k,v in before.items() if k != 'current-state.json')
                        + len(entry) + len(note) <= retained_limit, 'horizon failure capacity')
            collector.files['current-state.json'] = entry
            collector.files['README.md'] += note
            return payload
        except ValueError:
            return baseline
