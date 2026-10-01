"""Native News windows in the original read package; never acquire or route Research."""
from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from urllib.parse import quote

from ..identity import canonical_hash
from . import current_state as m
from . import current_state_delivery as delivery
from . import news_daily as source
from . import external_radar_observations as original
from .institutional_radar_reading import _reserve, ERRORS
from .radar_company_reading import retained_bytes

DETAIL = 'details/radar/news-daily.md'
REPORT = 'details/radar/news-daily.json'
MAX_AGE = timedelta(hours=36)


def _run(run, cutoff):
    m.check(run.get('repository', {}).get('full_name') == m.REPOSITORY
            and run.get('head_repository', {}).get('full_name') == m.REPOSITORY
            and run.get('path') == source.WORKFLOW and run.get('head_branch') == 'main'
            and run.get('event') in {'workflow_run', 'workflow_dispatch', 'schedule'}
            and type(run.get('run_attempt')) is int and run['run_attempt'] == 1
            and type(run.get('id')) is int and run['id'] > 0
            and m.SHA.fullmatch(run.get('head_sha', '')) is not None,
            'Native news run identity differs')
    m.check(m.clock(run['created_at']) <= m.clock(run['updated_at']) <= m.clock(cutoff),
            'Native news run chronology differs')


def read(collector, baseline):
    _reserve(collector, calls=4, files=4)
    result = collector.api.get('actions/workflows/radar-newsnow-daily.yml/runs?branch=main&per_page=20')
    runs = result['workflow_runs']
    m.check(isinstance(runs, list) and len(runs) <= 20 and type(result['total_count']) is int
            and result['total_count'] >= len(runs) and (runs or result['total_count'] == 0)
            and len({r['id'] for r in runs}) == len(runs), 'Native news run query incomplete')
    if not runs:
        return {'status': 'NOT_RUN', 'meaning': 'NOT_NO_NEWS'}, None
    latest = max(runs, key=lambda r: (m.clock(r['created_at']), r['id']))
    _run(latest, collector.now())
    latest_failed = latest['status'] != 'completed' or latest['conclusion'] != 'success'
    selected = latest
    if latest_failed:
        successes = [r for r in runs if r['status'] == 'completed' and r['conclusion'] == 'success']
        if not successes:
            return {'status': 'LATEST_ATTEMPT_NOT_SUCCESSFUL',
                    'latest_attempt': m.concise_run(latest),
                    'meaning': 'NO_QUALIFIED_ROLLING_CAPTURE_IN_BOUNDED_RUN_WINDOW_NOT_QUIET'}, None
        selected = max(successes, key=lambda r: (m.clock(r['created_at']), r['id']))
        _run(selected, collector.now())
    run = collector.api.get('actions/runs/' + str(selected['id']))
    _run(run, collector.now())
    m.check(all(run[k] == selected[k] for k in ('id', 'head_sha', 'created_at', 'event', 'run_attempt')),
            'Native news selected identity changed')
    m.check(run['status'] == 'completed' and run['conclusion'] == 'success',
            'Native news selected prior capture is not qualified success')
    state = {'status': 'LATEST_ATTEMPT_NOT_SUCCESSFUL_PRIOR_CAPTURE_RETAINED' if latest_failed
                       else 'QUALIFIED_LATEST_CAPTURE',
             'latest_attempt': m.concise_run(latest),
             'selected_capture': m.concise_run(run),
             'meaning': 'LATEST_FAILURE_VISIBLE_WITH_BOUNDED_PRIOR_ROLLING_CAPTURE' if latest_failed
                        else 'LATEST_QUALIFIED_CAPTURE_SELECTED'}
    artifact = m.select_artifact(collector.artifacts(run), 'newsnow-daily-' + str(run['id']) + '-1')
    files, archive = collector.archive(artifact, run)
    captured = original._decode(files['observations.json'])
    finish = captured['projection']['captured_through']
    rebuilt = source.rebuild(files, cutoff=finish, run=run)
    m.check(captured == rebuilt, 'Native news saved projection differs from raw inputs')
    if source.HISTORY_FILE in files:
        history = source.validate_history(source.news._decode(files[source.HISTORY_FILE]))
        hp = history['projection']
        m.check(hp['generated_at'] == finish and hp['captures']
                and hp['captures'][-1]['run_id'] == run['id']
                and hp['captures'][-1]['code_commit'] == run['head_sha'],
                'Native news rolling history does not end at selected capture')
    else:
        history = source.rolling_history(rebuilt)
    company = None
    context_status = 'NO_SAVED_COMPANY_CONTEXT_NOT_NO_RELATED_COMPANY'
    ref = baseline['research'].get('radar_discovery', {}).get('details', {}).get('company_reading')
    if ref:
        try:
            from .radar_company_reading import render as check_company
            company = original._decode(retained_bytes(collector.files, ref))
            check_company(company)
            m.check(m.clock(company['projection']['generated_at']) <= m.clock(collector.now()),
                    'Native news company context is future')
            context_status = 'SAME_READING_NAME_MATCH_ONLY'
        except ERRORS:
            company = None
            context_status = 'COMPANY_READING_UNAVAILABLE_OR_REJECTED'
    associated = source.rebuild(files, cutoff=collector.now(), run=run, company_reading=company)
    stale = m.clock(collector.now()) - m.clock(finish) > MAX_AGE
    capture_status = 'STALE_CAPTURE_NOT_TODAY_NEWS' if stale else rebuilt['projection']['status']
    latest_failed = state['latest_attempt']['id'] != state['selected_capture']['id']
    state.update(status=('STALE_PRIOR_CAPTURE_AFTER_LATEST_FAILURE' if stale and latest_failed
                         else 'LATEST_ATTEMPT_NOT_SUCCESSFUL_PRIOR_CAPTURE_RETAINED' if latest_failed
                         else capture_status),
                 capture_status=capture_status, captured_through=finish, archive=archive,
                 capture_hash=rebuilt['projection']['capture_hash'],
                 rolling_history_status=history['projection']['status'],
                 rolling_window_start=history['projection']['window_start'],
                 rolling_observation_count=history['projection']['coverage']['observation_count'],
                 rolling_dropped_observation_count=history['projection']['coverage']['dropped_observation_count'],
                 company_context_status=context_status, freshness_is_not_publication_proof=True,
                 meaning=('LATEST_FAILURE_VISIBLE_WITH_PRIOR_ROLLING_CAPTURE_NOT_COMPLETE_NEWS'
                          if latest_failed else 'SAVED_WINDOWS_AND_ROLLING_INDEX_NOT_COMPLETE_DAILY_NEWS_OR_RESEARCH'))
    report = {'state': state, 'capture': associated, 'history': history,
              'company_source': ref if company is not None else None,
              'association_as_of': collector.now(), 'base_reading_hash': baseline['reading_hash'],
              'semantic_review': 'NOT_PERFORMED', **source.AUTHORITY}
    return state, {'projection': report, 'projection_hash': canonical_hash(report)}


def render(report):
    from .reviewed_question_reading import _text
    p = report['projection']; m.check(report['projection_hash'] == canonical_hash(p), 'News reading hash differs')
    value = p['capture']['projection']; state = p['state']; history = p['history']['projection']
    lines = ['# 日常新闻输入：保存窗口与待核对线索', '',
             '原采集截止：' + _text(value['captured_through']) + '；状态：' + _text(state['status']),
             '滚动索引起点：' + _text(history['window_start']) + '；保留条目：'
             + _text(history['coverage']['observation_count']) + '；历史状态：' + _text(history['status']),
             '这里只保存来源窗口和按抓取首次出现时间去重的滚动索引；不是完整新闻覆盖、已核实经济事件、已审阅研究问题或投资建议。',
             'first_seen_at 是本系统首次抓到该 version_id 的时间，不是发布时刻；缓存/服务时间也不是原文发布时间。', '',
             '| 来源 | 本批处置 | 窗口条数 |', '|---|---|---|']
    lines += ['| ' + _text(o['source_id']) + ' | ' + _text(o['status']) + ' | ' + _text(o.get('observations_in_window') if o.get('observations_in_window') is not None else 'UNKNOWN') + ' |' for o in value['source_outcomes']]
    lines += ['', '## 滚动18小时新闻索引（按首次抓到时间倒序）', '',
              '用于晨报/晚报做内容增量筛选；相同 version_id 重复抓取不会变成新新闻。']
    if history['coverage']['dropped_observation_count']:
        lines.append('滚动索引因既有字节/条目上限丢弃较老条目：'
                     + _text(history['coverage']['dropped_observation_count']) + '；不能据此声称窗口完整。')
    for entry in sorted(history['observations'],
                        key=lambda x: (m.clock(x['first_seen_at']),
                                       x['observation']['source_id'],
                                       x['observation']['version_id']), reverse=True):
        row = entry['observation']
        lines.append('- ' + _text(entry['first_seen_at']) + ' · [' + _text(row['title']) + ']('
                     + quote(row['url'], safe='/:?=&%#') + ') · ' + _text(row['source_id'])
                     + ' · last_seen ' + _text(entry['last_seen_at']))
    if not history['observations']:
        lines.append('滚动索引当前无可用条目；这不是“没有新闻”的证明。')
    context = value['news']
    if context:
        n = context['projection']; by_id = {r['version_id']: r for r in n['observations']}
        lines += ['', '## 公司名称命中：先解释经济联系，再决定是否形成问题', '',
                  '名称匹配不认证证券或业务受益；未命中不代表没有相关公司。']
        for company in n['companies']:
            lines.append('\n### ' + _text(' / '.join(company['source_names']) + ' ' + company['thscode']))
            for match in company['matches']:
                row = by_id[match['observation_id']]
                lines.append('- ' + _text(row['title']) + '（' + _text(row['source_id']) + '）')
            lines.append('旧研究定位保留在同版本公司阅读；经济联系和具体问题仍待审阅，不自动启动Pre。')
        lines += ['', '## 原窗口标题（不是新增事件清单）', '']
        for row in n['observations']:
            lines.append('- [' + _text(row['title']) + '](' + quote(row['url'], safe='/:?=&%#')
                         + ') · ' + _text(row['source_id']))
    else:
        lines += ['', '本批未取得可归一化窗口；不能据此宣布没有新闻。']
    archive = state['archive']
    m.check(archive['read_ref_rule'] == 'USE_THE_SAME_PINNED_READING_COMMIT', 'News archive not pinned')
    lines += ['', '[本批原始ZIP](../../' + quote(m.safe_path(archive['read_path']), safe='/') + ')',
              '[结构化窗口与版本](news-daily.json)', '']
    return '\n'.join(lines)


def attach(collector, baseline):
    m.validate_read_package(baseline)
    before = dict(collector.files), dict(collector.archive_cache)
    research = deepcopy(baseline['research'])
    try:
        state, report = read(collector, baseline)
        reading = {**state, **source.AUTHORITY}
        if report is not None:
            reading['details'] = {
                'json': collector.retain(REPORT, m.json_bytes(report)),
                'markdown': collector.retain(DETAIL, render(report).encode())}
        research['daily_news'] = reading
    except ERRORS as exc:
        collector.files, collector.archive_cache = before
        research['daily_news'] = {'status': 'UNAVAILABLE_OR_REJECTED', 'error_type': type(exc).__name__,
                                 'meaning': 'NEWS_READ_GAP_NOT_NO_NEWS', **source.AUTHORITY}
    payload = m.assemble(code_commit=collector.code_commit, checked_at=collector.now(),
        check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
        capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
    note = ('\n[日常新闻：原采集日期、保存窗口与待核对线索](' + DETAIL + ')；不是新Research或自动提醒。\n'
            if 'details' in research['daily_news'] else '\n日常新闻输入尚无可读批次或读取受阻；不代表没有新闻。\n')
    replacements = {'current-state.json': m.read_package_bytes(payload),
                    'README.md': collector.files['README.md'] + note.encode()}
    m.check(sum(len(v) for k, v in collector.files.items() if k not in replacements)
            + sum(map(len, replacements.values())) <= delivery.MAX_RETAINED_OUTPUT, 'News publication byte budget')
    _reserve(collector, replacements=replacements)
    collector.files.update(replacements)
    return payload
