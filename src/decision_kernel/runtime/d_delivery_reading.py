"""One same-reading D consumer; no source I/O, new score or state owner.

Project already sealed producer results without joining foreign/company results,
reinterpreting maturity, or following a historical locator as a current result.
"""
from __future__ import annotations

from copy import deepcopy
from html import escape

from decision_kernel.identity import canonical_hash, canonical_json
from . import current_state as model

KEY = 'd_joint_reading'
PATH = 'details/research/d-joint-reading.json'
VERSION = 'd-joint-reading-v1'
MAX_BYTES = 512 * 1024
# Fixed projections of existing consumers, not another configurable registry.
COMPONENTS = (
    ('horizons', 'd_horizon_follow_up', 'details/stock/horizon-follow-up.json',
     'd-retained-horizon-follow-up-v1', '经济假设与独立期限'),
    ('outcomes', 'd_operating_outcomes', 'details/research/operating-outcomes.json',
     'reviewed-operating-outcomes-v1', '经营指引与实际结果'),
    ('structure', 'd_price_structure', 'details/stock/price-structure.json',
     'd-saved-czsc-structure-v1', '指数价格结构'),
    ('auction', 'd_auction_next_session', 'details/stock/auction-next-session.json',
     'd-auction-next-session-observation-v1', '竞价分组与后续观察'),
)
ERRORS = (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError,
          RuntimeError, ArithmeticError, ImportError)


def _select(value, keys):
    """Copy only fields that actually exist; absence is not a manufactured null."""
    return {key: deepcopy(value[key]) for key in keys if key in value}


def _projection(kind, report):
    if kind == 'horizons':
        model.check(isinstance(report['cases'], list), 'joint horizon cases')
        for case in report['cases']:
            for key in ('symbol', 'frozen_at', 'long_research_deadline', 'analyst_review_by'):
                model.check(isinstance(case[key], str) or
                            key == 'long_research_deadline' and case[key] is None, 'joint horizon field')
            model.check(isinstance(case.get('retained_interpretation', {}), dict), 'joint interpretation')
            model.check(isinstance(case.get('checkpoints', []), list), 'joint checkpoints')
            for checkpoint in case.get('checkpoints', []):
                model.check(type(checkpoint['period']) is int and isinstance(checkpoint['status'], str),
                            'joint checkpoint shape')
        return _select(report, ('cases', 'economic_continuations', 'case_bodies',
            'calendar_market_session', 'latest_price_status', 'calendar_source',
            'price_file', 'using_prior_price_source', 'previous_reading_gap'))
    if kind == 'outcomes':
        model.check(isinstance(report['items'], list), 'joint outcome events')
        for event in report['items']:
            model.check(isinstance(event['status'], str) and isinstance(event.get('rows', []), list),
                        'joint outcome event shape')
            for row in event.get('rows', []):
                model.check(isinstance(row['label'], str) and isinstance(row['comparison']['status'], str),
                            'joint outcome row shape')
        return _select(report, ('items', 'selected_events', 'compared_events',
            'source_or_comparison_gap_events', 'independent_forecast_sample_count',
            'pooled_score', 'ai_forecast_score', 'method_effectiveness', 'automatic_method_change'))
    if kind == 'structure':
        return _select(report, ('algorithm', 'parameters', 'subject', 'market_session',
            'computed_at', 'reading_status', 'observed_delta', 'source',
            'source_lane_gaps', 'previous_reading_gap', 'source_selection'))
    out = _select(report, ('latest_auction_status', 'latest_price_status',
        'calendar_market_session', 'cross_session_return', 'previous_reading_gap'))
    # Keep ALL current/archived cohort dispositions, but do not duplicate price rows.
    for key in ('cohorts', 'archived_cohorts'):
        rows = report[key]
        model.check(isinstance(rows, list), 'joint auction cohorts')
        out[key] = [_select(row, ('id', 'profile', 'market_session', 'target_session',
            'status', 'groups', 'auction_timeliness', 'auction_observed_at',
            'auction_received_through', 'auction_origin', 'acquisition_timing',
            'price_basis', 'current_quote_gap', 'calendar_gap', 'observation')) for row in rows]
    return out


def component(research, files, spec, *, code_commit, checked_at):
    kind, key, path, version, label = spec
    result = {'kind': kind, 'label': label, 'producer_key': key,
              'status': 'NOT_PRESENT_IN_THIS_READING', 'source': None}
    if key not in research:
        return result
    descriptor = research[key]
    try:
        model.check(isinstance(descriptor, dict), 'joint source descriptor')
        # A producer can publish an inline gap instead of a file. Preserve it;
        # do not dereference its previous_saved_reading or substitute old success.
        if 'read_path' not in descriptor:
            model.check(isinstance(descriptor.get('status'), str), 'joint inline gap shape')
            return {**result, 'status': 'PRODUCER_REPORTED_GAP',
                    'producer_gap': deepcopy(descriptor)}
        model.check(descriptor['read_path'] == path and
                    descriptor['read_ref_rule'] == 'USE_THE_SAME_PINNED_READING_COMMIT',
                    'joint source location')
        raw = files[path]
        model.check(type(descriptor.get('bytes')) is int and len(raw) == descriptor['bytes']
                    and model.sha256(raw) == descriptor['sha256']
                    and model.blob_sha(raw) == descriptor['git_blob'], 'joint source integrity')
        from .operating_outcomes import loads
        report = loads(raw)  # Existing strict size, duplicate-key and nonfinite checks.
        model.sealed(report, 'report_hash')
        model.check(report['version'] == version and report['code_commit'] == code_commit,
                    'joint source version or code')
        model.check(all(report.get(k) == v for k, v in model.AUTHORITY.items()), 'joint source authority')
        model.check(model.clock(report['checked_at']) <= model.clock(checked_at), 'joint future reading')
        return {**result, 'status': 'VERIFIED_SAME_READING_COMPONENT',
                'meaning': 'CUSTODY_AND_PROJECTION_NOT_ECONOMIC_OR_D_ACCEPTANCE',
                'source': deepcopy(descriptor), 'source_report_hash': report['report_hash'],
                'source_checked_at': report['checked_at'], 'data': _projection(kind, report)}
    except ERRORS as exc:
        # No provider text/error body or unaudited locator is emitted as a link.
        return {**result, 'status': 'COMPONENT_READ_GAP', 'error_type': type(exc).__name__}


def build(baseline, files, *, checked_at):
    model.validate_read_package(baseline)
    model.check(model.clock(checked_at) >= model.clock(baseline['checks']['finished_at']), 'joint reading clock')
    items = [component(baseline['research'], files, s,
        code_commit=baseline['code_commit'], checked_at=baseline['checks']['finished_at']) for s in COMPONENTS]
    report = {'version': VERSION, 'code_commit': baseline['code_commit'], 'checked_at': checked_at,
        'input_reading_hash': baseline['reading_hash'], 'components': items,
        'meaning': 'JOINT_RESEARCH_CONTEXT_NOT_OPPORTUNITY_ADJUDICATION',
        'scope': 'FOUR_EXISTING_D_CONSUMERS_NOT_ALL_D_REQUIREMENTS',
        'cross_subject_outcome_join': 'NOT_PERFORMED', 'pooled_score': None,
        'new_source_requests': 0, 'new_model_calls': 0, 'new_attention_events': 0,
        'human_acceptance_inferred': False, **model.AUTHORITY}
    report['report_hash'] = canonical_hash(report)
    return report


def _text(value):
    if value is None:
        return '未建立/未提供'
    text = escape(str(value)).replace('\\', '\\\\')
    for char in ('`', '*', '_', '[', ']', '|', '#'):
        text = text.replace(char, '\\' + char)
    return text.replace('\r', ' ').replace('\n', ' ')


def render(report):
    lines = ['\n## D：经济假设、期限与结果联合阅读\n',
        '这是同一读取包的联合视图，不是综合机会分、完整D验收或新研究。'
        '公司/指数/竞价分组各守原身份；公司指引结果不自动归因给其他公司的机会。\n',
        '| 用途 | 本次读取处置 | 原完整结果 |', '|---|---|---|']
    for item in report['components']:
        link = f"[同版本正文]({item['source']['read_path']})" if item['source'] else '未提供可用正文'
        lines.append(f"| {item['label']} | {_text(item['status'])} | {link} |")
    for item in report['components']:
        if item['status'] == 'PRODUCER_REPORTED_GAP':
            lines += ['', f"{item['label']}原处置：{_text(item['producer_gap']['status'])}。历史定位不当本次成功。"]
    for item in report['components']:
        if item['status'] != 'VERIFIED_SAME_READING_COMPONENT':
            continue
        data = item['data']
        if item['kind'] == 'horizons':
            for case in data.get('cases', []):
                lines += ['', f"**{_text(case['symbol'])}：原假设与独立期限**",
                    f"原冻结：{_text(case['frozen_at'])}；长期研究截止："
                    f"{_text(case['long_research_deadline']) if case['long_research_deadline'] is not None else '本声明未单设（不覆盖原长期研究）'}；"
                    f"分析者复核日：{_text(case['analyst_review_by'])}。",
                    f"原解释：{_text(case.get('retained_interpretation', {}).get('intermediate'))}",
                    f"原失效条件：{_text(case.get('retained_interpretation', {}).get('invalidation'))}"]
                for checkpoint in case.get('checkpoints', []):
                    lines.append(f"观察窗口 {_text(checkpoint['period'])} 个交易日：{_text(checkpoint['status'])}；"
                        f"起点 {_text(checkpoint.get('anchor_session'))}；终点 {_text(checkpoint.get('target_session'))}。")
                lines.append(f"机会是否成立：{_text(case.get('opportunity_established'))}；"
                    f"经济结果：{_text(case.get('economic_result'))}。旧区间行情不是冻结后的结果，复核日也不是交易退出指令。")
        elif item['kind'] == 'outcomes':
            for event in data.get('items', []):
                lines += ['', f"**{_text(event.get('event_id'))}：{_text(event['status'])}**",
                    f"比较归属：{_text(event.get('comparator_role'))}；不是AI预测胜率。"]
                for row in event.get('rows', []):
                    comparison = row['comparison']
                    lines.append(f"{_text(row['label'])}：{_text(comparison['status'])}；"
                        f"实际减原指引 {_text(comparison.get('difference'))} {_text(comparison.get('unit'))}。")
                lines.append('同一事件的多个指标不当独立样本；完整反证、来源限制和原审阅时点见同版本正文。')
        elif item['kind'] == 'auction':
            for cohort in data.get('cohorts', []):
                lines += ['', f"竞价原市场日 {_text(cohort.get('market_session'))}：{_text(cohort.get('status'))}；"
                    f"取得及时性 {_text(cohort.get('auction_timeliness'))}。历史/延迟材料不证明盘前发现，后续价格不是成交收益。"]
                if cohort.get('observation') == 'PREVIOUS_DATED_OBSERVATIONS_RETAINED':
                    lines.append(f"本次报价缺口 {_text(cohort.get('current_quote_gap'))}；"
                        '保留整份旧观察，不是本次重新取得，也未跨包拼接。具体缺项和来源见同版本正文。')
        else:
            lines += ['', f"指数 {_text(data.get('subject'))}：{_text(data.get('reading_status'))}。"
                '形态是原方法的价格表示，不是公司经营证据或已成立机会。']
    lines += ['', '尚未取得的窗口、来源失败、方法有效性与自然使用分别保留；'
        '读取本页不启动研究、采集、通知、Watch或交易。', '']
    return '\n'.join(lines)


def attach(collector, baseline, *, retained_limit):
    if KEY in baseline.get('research', {}):
        return baseline  # A second consumption does not append another joint section.
    if not any(spec[1] in baseline.get('research', {}) for spec in COMPONENTS):
        return baseline  # No new mandatory hook for consumers without any D input.
    before = dict(collector.files)
    try:
        model.check(collector.code_commit == baseline['code_commit'], 'joint code identity')
        report = build(baseline, collector.files, checked_at=collector.now())
        raw = (canonical_json(report) + '\n').encode()
        model.check(len(raw) <= MAX_BYTES, 'joint detail capacity')
        descriptor = {'read_path': PATH, 'bytes': len(raw), 'sha256': model.sha256(raw),
            'git_blob': model.blob_sha(raw), 'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}
        research = deepcopy(baseline['research']); research[KEY] = descriptor
        payload = model.assemble(code_commit=baseline['code_commit'], checked_at=report['checked_at'],
            check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
            capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
        updates = {PATH: raw, 'current-state.json': model.read_package_bytes(payload),
            'README.md': collector.files['README.md'] + render(report).encode() +
                         f'\n[D联合结构化阅读与原字段]({PATH})。\n'.encode()}
        model.check(sum(map(len, {**collector.files, **updates}.values())) <= retained_limit, 'joint total capacity')
        from .institutional_radar_reading import _reserve
        _reserve(collector, replacements=updates)
        collector.files.update(updates)
        return payload
    except ERRORS:
        collector.files = before
        return baseline  # Source producer results/gaps remain, never manufacture PASS.
