"""Public market/positioning context on the original reader; no new authority."""
from __future__ import annotations
from copy import deepcopy
from datetime import timedelta

from ..identity import canonical_hash
from . import current_state as m, current_state_delivery as delivery
from . import easy_stock_context as c, easy_stock_capture as source
from .industry_breadth_reading import QUERY, _run
from .institutional_radar_reading import _reserve, ERRORS
from .reviewed_question_reading import _text

PREFIX = 'details/radar/easy-stock-context'
JOB = 'public-context'
GUARD = 'Require exact independent main CI before source access'
CAPTURE = 'Capture bounded public context'
UPLOAD = 'Upload public context original attempts'


def native(collector):
    _reserve(collector, calls=5, files=4)
    listing = collector.api.get(QUERY); runs = listing['workflow_runs']
    m.check(isinstance(runs, list) and len(runs) <= 20 and type(listing['total_count']) is int
        and listing['total_count'] >= len(runs) and (runs or listing['total_count'] == 0)
        and len({r['id'] for r in runs}) == len(runs), 'Public context run query incomplete')
    if not runs:
        return {'status': 'NOT_RUN_NOT_NO_ACTIVITY', 'result': None}
    selected = max(runs, key=lambda r: (m.clock(r['created_at']), r['id']))
    _run(selected, collector.now())
    run = collector.api.get('actions/runs/' + str(selected['id'])); _run(run, collector.now())
    m.check(all(run[k] == selected[k] for k in ('id', 'head_sha', 'event', 'created_at', 'run_attempt')),
            'Public context selected run changed')
    state = {'latest_attempt': m.concise_run(run), 'result': None,
             'whole_workflow_conclusion': run['conclusion']}
    if run['status'] != 'completed':
        return {**state, 'status': 'LATEST_ATTEMPT_INCOMPLETE_NO_OLDER_FALLBACK'}
    data = collector.api.get(f"actions/runs/{run['id']}/attempts/1/jobs?per_page=100")
    jobs = data['jobs']
    m.check(isinstance(jobs, list) and type(data['total_count']) is int and len(jobs) <= 100
        and data['total_count'] == len(jobs) and len({j['id'] for j in jobs}) == len(jobs),
        'Public context job enumeration incomplete')
    matches = [j for j in jobs if j.get('name') == JOB]
    m.check(len(matches) <= 1, 'Public context job ambiguous')
    if not matches:
        return {**state, 'status': 'PUBLIC_JOB_NOT_PRESENT_IN_SELECTED_RUN'}
    job = matches[0]
    m.check(job['run_id'] == run['id'] and job['head_sha'] == run['head_sha'], 'Public job identity differs')
    state['job_id'] = job['id']
    if job['status'] != 'completed' or job['conclusion'] != 'success':
        return {**state, 'status': 'PUBLIC_JOB_NOT_SUCCESSFUL_NO_OLDER_FALLBACK'}
    m.check(m.clock(run['created_at']) <= m.clock(job['started_at']) <= m.clock(job['completed_at'])
            <= m.clock(run['updated_at']), 'Public job clocks differ')
    for name in (GUARD, CAPTURE, UPLOAD):
        steps = [s for s in job.get('steps', []) if s.get('name') == name]
        m.check(len(steps) == 1 and steps[0]['status'] == 'completed' and steps[0]['conclusion'] == 'success',
                'Public context required step not successful')
    artifact = m.select_artifact(collector.artifacts(run), source.ARTIFACT_PREFIX + str(run['id']) + '-1')
    files, archive = collector.archive(artifact, run)
    result = source.replay(files, run, cutoff=collector.now())
    m.check(m.clock(job['started_at']) <= m.clock(result['started_at'])
            <= m.clock(result['finished_at']) <= m.clock(job['completed_at']), 'Public capture outside job')
    proof = collector.retain(PREFIX + '-job.json', m.json_bytes(data))
    good = sum(s['result'] is not None for s in result['sections'])
    return {**state, 'status': 'READ_OK_DECLARED_CONTEXT_ONLY' if good == 8 else 'READ_OK_WITH_SOURCE_GAPS',
        'result': result, 'archive': archive, 'job_proof': proof, 'normalized_source_count': good,
        'capture_age': 'OLDER_THAN_36H' if m.clock(collector.now()) - m.clock(result['finished_at']) > timedelta(hours=36)
                       else 'RECENT_CAPTURE_NOT_SOURCE_FRESHNESS',
        'whole_workflow_failure_preserved': run['conclusion'] != 'success'}


def render(section):
    lines = ['# 行业市场表达与期指持仓上下文', '', '状态：' + _text(section['status']), '',
        '资金流不是公司 Evidence；期指会员排名不是市场方向或买卖指令。',
        '腾讯/东方财富分类独立；f24不作为20日，缺失字段不填零；抓取时间不是交易/发布时间。',
        '榜单第一页不是全市场；中信(代客)缺失侧为UNKNOWN，四品种手数不合为风险敞口。', '']
    if section.get('whole_workflow_conclusion') is not None:
        lines += ['原工作流结论：' + _text(section['whole_workflow_conclusion']) + '；本节单独核对public-context任务。', '']
    result = section.get('result')
    if result is None:
        return '\n'.join(lines + ['尚无可用的本批公共上下文，不推断无变化。', ''])
    lines += ['本批目标日期：' + _text(result['target_date']) + '（检查目标，不是已认证的最新完成交易日）。', '']
    for item in result['sections']:
        lines += ['## ' + item['source_id'], '', '状态：' + _text(item['status']), '']
        if item['result'] is None:
            lines += ['来源未取得或合同未通过；原尝试保留，不用旧成功替代。', '']; continue
        p = item['result']['projection']
        if p['kind'] == 'POSITIONING_CONTEXT':
            lines += ['| 合约 | 多头前20 | 空头前20 | 净多变化 | 净空变化 | 中信净多变化 |',
                      '|---|---|---|---|---|---|']
            for row in p['contracts']:
                values = [row['contract'], row['long_position'], row['short_position'], row['net_long_change'],
                          row['net_short_change'], row['citic']['net_long_change']]
                lines.append('| ' + ' | '.join(_text(v if v is not None else 'UNKNOWN') for v in values) + ' |')
            lines += ['', '仅对文件实际披露合约；缺合约目录不声明全合约穷尽。', '']
        else:
            rows = p['observations']
            lines += ['原响应行数：' + str(len(rows)) + '；这里展示前10行，全部原字段和缺口见JSON。', '',
                      '| 原代码/名称 | 1日 | 5日 | 20日 | 主力净流入原值 |', '|---|---|---|---|---|---|']
            for row in rows[:10]:
                vals = row['values']
                values = [str(row['identity']['source_code']) + '/' + str(row['name']),
                          *[vals.get(k) for k in ('change_percent', 'five_day_change_percent',
                                                 'twenty_day_change_percent', 'main_net_inflow')]]
                lines.append('| ' + ' | '.join(_text(v if v is not None else 'UNKNOWN') for v in values) + ' |')
            lines += ['']
    return '\n'.join(lines + ['[全部原字段、可用性、原件和任务身份](easy-stock-context.json)', '',
                              '未执行经济问题审阅、Pre/Quick、Odds重算或Human提醒。', ''])


def attach(collector, baseline):
    m.validate_read_package(baseline)
    before = dict(collector.files), dict(collector.archive_cache)
    try:
        section = native(collector)
    except ERRORS as exc:
        collector.files, collector.archive_cache = before
        section = {'status': 'UNAVAILABLE_OR_REJECTED_NOT_QUIET', 'error_type': type(exc).__name__, 'result': None}
    report = c.seal({'version': c.VERSION, 'generated_at': collector.now(),
        'base_reading_hash': baseline['reading_hash'], 'section': section, **c.AUTHORITY})
    _reserve(collector, files=2)
    refs = {'json': collector.retain(PREFIX + '.json', m.json_bytes(report)),
            'markdown': collector.retain(PREFIX + '.md', render(section).encode())}
    research = deepcopy(baseline['research'])
    research['easy_stock_context'] = {'status': section['status'], 'details': refs,
        'meaning': 'MARKET_EXPRESSION_AND_POSITIONING_NOT_COMPANY_EVIDENCE', **c.AUTHORITY}
    payload = m.assemble(code_commit=collector.code_commit, checked_at=collector.now(),
        check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
        capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
    old = m.render_summary(baseline).encode(); root = collector.files['README.md']
    m.check(root.startswith(old), 'Public context original navigation differs')
    replacements = {'current-state.json': m.read_package_bytes(payload),
        'README.md': m.render_summary(payload).encode() + root[len(old):]
            + ('\n[行业市场表达与期指持仓上下文](' + PREFIX + '.md)；不是研究结论或买卖指令。\n').encode()}
    m.check(sum(len(v) for k, v in collector.files.items() if k not in replacements)
        + sum(map(len, replacements.values())) <= delivery.MAX_RETAINED_OUTPUT, 'Public context retained byte budget')
    _reserve(collector, replacements=replacements)
    collector.files.update(replacements)
    return payload
