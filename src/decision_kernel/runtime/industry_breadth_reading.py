"""Reuse original saved artifacts; keep historical breadth separate from native attempts."""
from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from urllib.parse import quote

from ..identity import canonical_hash
from . import current_state as m, current_state_delivery as delivery
from . import industry_breadth as source
from . import external_radar_observations as original
from .institutional_radar_reading import _reserve, ERRORS
from .radar_company_reading import retained_bytes

DETAIL = 'details/radar/industry-breadth.md'
REPORT = 'details/radar/industry-breadth.json'
QUERY = 'actions/workflows/radar-industry-breadth.yml/runs?branch=main&per_page=20'


def history(collector, baseline):
    ref = baseline['research'].get('external_radar', {}).get('details', {}).get('json')
    if ref is None:
        return {'status': 'HISTORICAL_SOURCE_NOT_LOADED', 'snapshot': None}
    old = original._decode(retained_bytes(collector.files, ref))
    m.check(old['projection_hash'] == canonical_hash(old['projection']), 'Historical source report differs')
    section = old['projection']['sections']['industry']
    m.check(section['status'] == 'SAVED_SAMPLE_REBUILT', 'Historical source not verified')
    archive = section['archive']
    files, verified = collector.archive_cache[archive['artifact_id']]
    m.check(verified == archive, 'Historical source archive association differs')
    retained_bytes(collector.files, archive)  # Verify the copy retained by the original Collector.
    records = original._decode(files['requests.json'])
    m.check(isinstance(records, list) and len(records) <= 32, 'Historical receipt budget')
    candidates = [r for r in records if r.get('path') == source.ENDPOINT and r.get('params') == {}]
    m.check(len(candidates) == 1, 'Historical breadth source ambiguous')
    receipt = candidates[0]
    snapshot = source.normalize(files[m.safe_path(receipt['response_file'])], receipt, cutoff=collector.now())
    return {'status': 'HISTORICAL_BREADTH_NOT_TODAY', 'archive': archive, 'snapshot': snapshot}


def _run(run, cutoff):
    m.check(run.get('repository', {}).get('full_name') == m.REPOSITORY
        and run.get('head_repository', {}).get('full_name') == m.REPOSITORY
        and run.get('path') == source.WORKFLOW and run.get('head_branch') == 'main'
        and run.get('event') in {'workflow_run', 'workflow_dispatch'}
        and type(run.get('run_attempt')) is int and run['run_attempt'] == 1
        and type(run.get('id')) is int and run['id'] > 0
        and isinstance(run.get('head_sha'), str) and m.SHA.fullmatch(run['head_sha']),
        'Native breadth run identity differs')
    m.check(m.clock(run['created_at']) <= m.clock(run['updated_at']) <= m.clock(cutoff),
            'Native breadth run clocks differ')


def native(collector):
    _reserve(collector, calls=4, files=2)
    data = collector.api.get(QUERY); runs = data['workflow_runs']
    m.check(isinstance(runs, list) and len(runs) <= 20 and type(data['total_count']) is int
        and data['total_count'] >= len(runs) and (runs or data['total_count'] == 0)
        and len({r['id'] for r in runs}) == len(runs), 'Native breadth query incomplete')
    if not runs:
        return {'status': 'NOT_RUN_NOT_NO_INDUSTRY_CHANGE', 'snapshot': None}
    selected = max(runs, key=lambda r: (m.clock(r['created_at']), r['id']))
    _run(selected, collector.now())
    run = collector.api.get('actions/runs/' + str(selected['id'])); _run(run, collector.now())
    m.check(all(run[k] == selected[k] for k in ('id', 'head_sha', 'event', 'created_at', 'run_attempt')),
            'Native breadth selected identity changed')
    state = {'latest_attempt': m.concise_run(run), 'snapshot': None}
    if run['status'] != 'completed' or run['conclusion'] != 'success':
        return {**state, 'status': 'LATEST_ATTEMPT_NOT_SUCCESSFUL_NO_OLDER_FALLBACK'}
    artifact = m.select_artifact(collector.artifacts(run), 'industry-breadth-' + str(run['id']) + '-1')
    files, archive = collector.archive(artifact, run)
    result = source.replay(files, run, cutoff=collector.now())
    age = m.clock(collector.now()) - m.clock(result['capture']['receipt']['received_at'])
    return {**state, **result, 'archive': archive,
            'capture_age_status': 'OLDER_THAN_36H' if age > timedelta(hours=36) else 'RECENT_CAPTURE',
            'capture_age_is_not_source_freshness_or_close_finality': True}


def render(report):
    from .reviewed_question_reading import _text
    p = report['projection']
    m.check(report['projection_hash'] == canonical_hash(p), 'Breadth reading hash differs')
    lines = ['# 行业观察面：全返回范围，而非三个样本', '',
        'LC／CU／RB仍是历史详细样本，不是发现白名单。以下不是行业拐点、受益公司或已审阅研究问题。',
        '保留全部现货报价与默认标记；不同主连、现货口径和金融指数不合并。',
        '价格单位、基差符号及比例尺度未统一认证；原比率不加百分号、不排名、不据此推定受益。',
        '半导体价格／库存、汽车销量等非商品指标仍未由此快照覆盖；集运期货也不等于现货运价。', '']
    for key, label in (('native', '日常原生批次'), ('historical', '独立历史样本（不是日常失败的替代）')):
        section = p['sections'][key]
        lines += ['## ' + label, '', '状态：' + _text(section['status']), '']
        if section.get('snapshot') is None:
            lines += ['没有可用快照不代表没有行业变化。', '']; continue
        value = section['snapshot']['projection']; coverage = value['coverage']
        lines += ['原取得时间：' + _text(value['source']['received_at']),
            '返回 ' + str(coverage['source_rows']) + ' 行；可识别 ' + str(coverage['distinct_series'])
            + ' 个主连，其中金融市场序列 ' + str(coverage['financial_series']) + ' 个。',
            '无法识别行数：' + str(coverage['unidentified_rows']) + '；完整行业分母未建立。', '',
            '| 品种 / 原代码 | 现货口径 / 默认标记 | 现货日期 | 现货原值 | 期货收盘原值 | 基差原值 | 比率原值 |',
            '|---|---|---|---|---|---|---|']
        for record in value['observations']:
            row = record['raw']
            values = [str(row.get('variety_name')) + ' / ' + row['thscode'],
                str(row.get('spot_indicator_id')) + ' / ' + str(row.get('default_value')),
                str(row.get('spot_publish_date')) + ' / ' + record['source_date_status'],
                row.get('converted_spot_price'), row.get('close_price'),
                row.get('close_basis'), row.get('close_basis_rate')]
            lines.append('| ' + ' | '.join(_text(v if v is not None else 'UNKNOWN') for v in values) + ' |')
        archive = section['archive']
        m.check(archive['read_ref_rule'] == 'USE_THE_SAME_PINNED_READING_COMMIT', 'Breadth archive not pinned')
        lines += ['', '[本节原始ZIP](../../' + quote(m.safe_path(archive['read_path']), safe='/') + ')', '']
    lines += ['[全部原字段、行级缺口及来源身份](industry-breadth.json)', '',
              '后续只对有经济意义的变化补充解释与原件；覆盖增加不自动增加Research或Human提醒。', '']
    return '\n'.join(lines)


def attach(collector, baseline):
    m.validate_read_package(baseline)
    sections = {}
    for kind, operation in (('historical', lambda: history(collector, baseline)), ('native', lambda: native(collector))):
        before = dict(collector.files), dict(collector.archive_cache)
        try:
            sections[kind] = operation()
        except ERRORS as exc:
            collector.files, collector.archive_cache = before
            sections[kind] = {'status': 'UNAVAILABLE_OR_REJECTED_NOT_QUIET',
                              'error_type': type(exc).__name__, 'snapshot': None}
    value = {'version': source.VERSION, 'sections': sections, 'generated_at': collector.now(),
             'base_reading_hash': baseline['reading_hash'], 'economic_review': 'NOT_PERFORMED', **source.AUTHORITY}
    report = {'projection': value, 'projection_hash': canonical_hash(value)}
    _reserve(collector, files=2)
    refs = {'json': collector.retain(REPORT, m.json_bytes(report)),
            'markdown': collector.retain(DETAIL, render(report).encode())}
    research = deepcopy(baseline['research'])
    research['industry_breadth'] = {'native_status': sections['native']['status'],
        'historical_status': sections['historical']['status'], 'details': refs,
        'meaning': 'BROAD_SOURCE_CONTEXT_NOT_INDUSTRY_SIGNALS_OR_RESEARCH', **source.AUTHORITY}
    payload = m.assemble(code_commit=collector.code_commit, checked_at=collector.now(),
        check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
        capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
    old = m.render_summary(baseline).encode(); root = collector.files['README.md']
    m.check(root.startswith(old), 'Breadth reading preserves original summary')
    replacements = {'current-state.json': m.read_package_bytes(payload),
        'README.md': m.render_summary(payload).encode() + root[len(old):]
            + ('\n[行业广泛观察：日常批次与独立历史范围](' + DETAIL + ')；不是新增研究或受益判断。\n').encode()}
    m.check(sum(len(v) for k, v in collector.files.items() if k not in replacements)
            + sum(map(len, replacements.values())) <= delivery.MAX_RETAINED_OUTPUT, 'Breadth final byte budget')
    _reserve(collector, replacements=replacements)
    collector.files.update(replacements)
    return payload
