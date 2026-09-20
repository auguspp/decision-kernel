"""GitHub-only reading of two explicitly pinned historical Radar samples.

Reuse native archive safety/retention and the original pure adapters. Never run
artifact code, select latest, refresh a publisher, qualify an issuer, or route Pre.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from html import escape
import json
from urllib.parse import quote

from decision_kernel.identity import canonical_hash
from . import current_state as model
from . import current_state_delivery as delivery
from . import external_radar_observations as observations
from . import institutional_radar_reading as radar
from .radar_company_reading import retained_bytes

CONFIG = 'decision_inputs/external-radar-reading-v1.json'
FORMAT = 'saved-external-radar-reading-v1'
PREFIX = 'details/radar/external/'
AUTHORITY = {**model.AUTHORITY, 'automatic_admission': False,
             'market_requests': 0, 'model_calls': 0, 'research_executions': 0}
SOURCE_FIELDS = {'run_id', 'workflow', 'head_branch', 'head_sha', 'artifact_id',
                 'artifact_name', 'bytes', 'sha256'}


def decode(raw):
    model.check(isinstance(raw, bytes) and len(raw) <= 4 * 1024 * 1024, 'External reading JSON budget')
    return json.loads(raw, object_pairs_hook=observations._unique)


def validate_config(value):
    model.check(isinstance(value, dict) and set(value) == {'format', 'enabled', 'news', 'industry', 'window'}
                and value['format'] == FORMAT and type(value['enabled']) is bool, 'External reading config shape')
    model.check(set(value['window']) == {'price_start', 'recent_start', 'period_end'}, 'External reading window shape')
    first, recent, end = [observations._day(value['window'][k]) for k in ('price_start', 'recent_start', 'period_end')]
    model.check(first <= recent <= end, 'External reading window order')
    for kind in ('news', 'industry'):
        spec = value[kind]
        model.check(isinstance(spec, dict) and set(spec) == SOURCE_FIELDS, 'External reading source shape')
        model.check(all(type(spec[k]) is int and spec[k] > 0 for k in ('run_id', 'artifact_id', 'bytes'))
                    and spec['bytes'] <= model.MAX_ARCHIVE, 'External reading source limits')
        model.check(model.SHA.fullmatch(spec['head_sha']) is not None
                    and len(spec['sha256']) == 64 and all(c in '0123456789abcdef' for c in spec['sha256']),
                    'External reading source digest')
        model.check(all(isinstance(spec[k], str) and 0 < len(spec[k]) <= 200
                        for k in ('workflow', 'head_branch', 'artifact_name'))
                    and spec['workflow'].startswith('.github/workflows/'), 'External reading source identity')
    return value


def _load(collector, spec, cutoff):
    run = collector.api.get('actions/runs/' + str(spec['run_id']))
    model.check(run.get('repository', {}).get('full_name') == model.REPOSITORY
                and run.get('head_repository', {}).get('full_name') == model.REPOSITORY
                and run.get('id') == spec['run_id'] and run.get('path') == spec['workflow']
                and run.get('head_branch') == spec['head_branch'] and run.get('head_sha') == spec['head_sha']
                and run.get('event') == 'push' and type(run.get('run_attempt')) is int and run['run_attempt'] == 1
                and run.get('status') == 'completed' and run.get('conclusion') == 'success',
                'External saved sample run differs')
    model.check(model.clock(run['created_at']) <= model.clock(run['updated_at']) <= model.clock(cutoff),
                'External saved sample run clock differs')
    artifact = model.select_artifact(collector.artifacts(run), spec['artifact_name'])
    model.check(artifact.get('id') == spec['artifact_id'] and artifact.get('size_in_bytes') == spec['bytes']
                and artifact.get('digest') == 'sha256:' + spec['sha256'], 'External saved sample artifact differs')
    files, reference = collector.archive(artifact, run)  # Original digest/ZIP/path/CRC checks.
    model.check(len(files) <= 64 and sum(map(len, files.values())) <= 8 * 1024 * 1024,
                'External saved sample expanded budget')
    return files, reference


def _records(raw):
    rows = decode(raw)
    model.check(isinstance(rows, list) and 0 < len(rows) <= 32
                and all(isinstance(r, dict) and isinstance(r.get('label'), str) for r in rows),
                'External source receipt inventory')
    model.check(len({r['label'] for r in rows}) == len(rows), 'External duplicate receipt label')
    return {r['label']: r for r in rows}


def rebuild_news(files, *, cutoff, company_reading=None):
    records = _records(files['attempts.json'])
    pairs, excluded = [], []
    for label, receipt in records.items():
        if label in observations.NEWS_DOMAINS:
            name = 'raw/newsnow-' + label + '.json'
            pairs.append((files[name], receipt))
        else:
            model.check(label in {'rsshub-yicai', 'rsshub-stcn-yw'}, 'Unexpected saved news profile')
            name = 'raw/' + label + '.xml'
            observations._bound(files[name], receipt, cutoff)
            excluded.append({'source_id': label, 'http_status': receipt.get('http_status'),
                             'status': 'NOT_CONSUMED_BY_NEWSNOW_PROFILE',
                             'capture_status': receipt.get('status')})
    result = observations.news_context(pairs, cutoff=cutoff, company_reading=company_reading)
    return {'result': result, 'excluded_profiles': excluded,
            'receipt_sha256': model.sha256(files['attempts.json']),
            'captured_from': min(r['requested_at'] for r in records.values()),
            'captured_through': max(r['received_at'] for r in records.values())}


def rebuild_industry(files, *, cutoff, window):
    records = _records(files['requests.json'])
    pairs = {}
    for label, receipt in records.items():
        name = model.safe_path(receipt['response_file'])
        body = files[name]
        observations._bound(body, receipt, cutoff, hithink=True)
        pairs[label] = (body, receipt)
    results = []
    for code in observations.CONTINUOUS:
        captures = {'identity': pairs['basis-main-continuous-latest'],
                    **{k: pairs[code + '-' + k] for k in ('prices', 'basis', 'warehouse')}}
        positions = [p for p in pairs.values() if p[1]['path'] == '/api/futures/positions/variety-daily']
        model.check(len(positions) <= 1, 'Ambiguous saved position request')
        if positions:
            captures['positions'] = positions[0]
        results.append(observations.industry(code, captures, cutoff=cutoff, **window))
    return {'results': results, 'receipt_sha256': model.sha256(files['requests.json']),
            'captured_from': min(r['requested_at'] for r in records.values()),
            'captured_through': max(r['received_at'] for r in records.values())}


def _gap(exc):
    return {'status': 'UNAVAILABLE_OR_REJECTED', 'error_type': type(exc).__name__,
            'reason': 'SAVED_SOURCE_OR_REPLAY_GAP_NOT_ZERO_OR_QUIET'}


def attach(collector, baseline):
    model.validate_read_package(baseline)
    config = validate_config(decode(delivery.git_file(collector.root, collector.code_commit, CONFIG)))
    if not config['enabled']:
        return baseline
    cutoff = collector.now()
    before = dict(collector.files), dict(collector.archive_cache)
    sections, company, company_ref = {}, None, None
    company_status = 'NO_READABLE_COMPANY_CONTEXT_NOT_NO_RELATED_COMPANY'
    try:
        radar._reserve(collector, calls=6, files=7)
        source = baseline['research'].get('radar_discovery', {}).get('details', {}).get('company_reading')
        if source:
            try:
                company = decode(retained_bytes(collector.files, source))
                from .radar_company_reading import render as check_company
                check_company(company)
                company_ref, company_status = source, 'SAME_READING_SAVED_CONTEXT'
            except radar.ERRORS:
                company, company_status = None, 'COMPANY_CONTEXT_UNAVAILABLE_OR_REJECTED'
        for kind in ('news', 'industry'):
            saved = dict(collector.files), dict(collector.archive_cache)
            try:
                files, archive = _load(collector, config[kind], cutoff)
                section = (rebuild_news(files, cutoff=cutoff, company_reading=company) if kind == 'news'
                           else rebuild_industry(files, cutoff=cutoff, window=config['window']))
                sections[kind] = {'status': 'SAVED_SAMPLE_REBUILT', 'archive': archive, **section}
            except radar.ERRORS as exc:
                collector.files, collector.archive_cache = saved
                sections[kind] = _gap(exc)
        payload = {'version': FORMAT, 'semantics': 'DATED_SAVED_OBSERVATIONS_NOT_DAILY_RADAR_OR_NEW_SIGNAL',
                   'generated_at': cutoff, 'base_reading_hash': baseline['reading_hash'],
                   'company_context_status': company_status, 'company_source': company_ref,
                   'config_hash': canonical_hash(config), 'sections': sections, **AUTHORITY}
        report = {'projection': payload, 'projection_hash': canonical_hash(payload)}
        rendered = render(report).encode()
        refs = {'json': collector.retain(PREFIX + 'observations.json', model.json_bytes(report)),
                'html': collector.retain(PREFIX + 'index.html', rendered),
                'config': collector.retain(PREFIX + 'source-config.json', model.json_bytes(config))}
        success = sum(s['status'] == 'SAVED_SAMPLE_REBUILT' for s in sections.values())
        reading = {'status': 'READ_OK_WITH_DECLARED_GAPS' if success == 2 else
                   'PARTIAL_SAVED_READING' if success else 'UNAVAILABLE_OR_REJECTED',
                   'details': refs, 'projection_hash': report['projection_hash'],
                   'meaning': 'SAVED_SAMPLE_NOT_DAILY_FEED; REPLAY_TIME_IS_NOT_PUBLICATION_TIME', **AUTHORITY}
    except radar.ERRORS as exc:
        collector.files, collector.archive_cache = before
        reading = {**_gap(exc), **AUTHORITY}
    return _finish(collector, baseline, reading)


def _finish(collector, baseline, reading):
    research = deepcopy(baseline['research'])
    research['external_radar'] = reading
    payload = model.assemble(code_commit=collector.code_commit, checked_at=collector.now(),
        check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
        capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
    # Preserve all existing company/concept/archive navigation after the native summary.
    old = model.render_summary(baseline).encode()
    root = collector.files['README.md']
    model.check(root.startswith(old), 'External reading must preserve existing summary and navigation')
    if 'details' in reading:
        note = '\n## 保存的新闻与行业观察\n\n[查看带日期的观察、公司名称命中及来源缺口](' + PREFIX + 'index.html)\n'
        note += '\n这是明确保存的历史样本，不是今日重采、每日信号或待执行研究；重读不新增事件。\n'
    else:
        note = '\n保存新闻/行业观察读取有缺口；不代表没有新闻或行业变化。原有Radar及Research状态保留。\n'
    data = {'current-state.json': model.json_bytes(payload),
            'README.md': model.render_summary(payload).encode() + root[len(old):] + note.encode()}
    model.check(sum(len(v) for k, v in collector.files.items() if k not in data)
                + sum(map(len, data.values())) <= delivery.MAX_RETAINED_OUTPUT, 'External reading final byte budget')
    radar._reserve(collector, replacements=data)
    collector.files.update(data)
    return payload


def render(report):
    p = report['projection']
    model.check(report['projection_hash'] == canonical_hash(p) and p['version'] == FORMAT
                and all(p.get(k) == v for k, v in AUTHORITY.items()), 'External reading projection differs')
    e = lambda value: escape(str(value), quote=True)
    def archive_link(ref):
        model.check(ref['read_ref_rule'] == 'USE_THE_SAME_PINNED_READING_COMMIT', 'Foreign external reading source')
        return '../../../' + quote(model.safe_path(ref['read_path']), safe='/')
    def percent(value):
        return 'UNKNOWN' if value is None else format(Decimal(value) * 100, '+.2f') + '%'
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'">',
        '<title>保存的新闻与行业观察</title><style>body{font:16px/1.7 system-ui;max-width:1100px;margin:auto;padding:20px}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid;padding:8px;text-align:left}p,td,a,pre{overflow-wrap:anywhere}pre{white-space:pre-wrap}section{margin:24px 0}.scroll{overflow:auto}</style>',
        '<h1>保存的新闻与行业观察</h1><p><b>历史样本 · 非每日采集 · 非新信号 · 非投资建议</b></p>',
        '<p>重建时间：' + e(p['generated_at']) + '。重建不改变原始取得时间，不表示今天重新发现或确认。</p>',
        '<p><a href="../index.html">原公司发现与研究上下文</a> / <a href="observations.json">完整结构化结果</a> / <a href="source-config.json">精确来源配置</a></p>']
    for kind, label in (('news', '新闻窗口'), ('industry', '行业变量窗口')):
        section = p['sections'][kind]
        parts.append('<section><h2>' + label + '</h2>')
        if section['status'] != 'SAVED_SAMPLE_REBUILT':
            parts.append('<p>来源读取或重建有缺口，不解释为零或没有变化。' + e(section['status']) + '</p></section>')
            continue
        parts.append('<p>原取得区间：' + e(section['captured_from']) + ' 至 ' + e(section['captured_through'])
                     + '；<a href="' + archive_link(section['archive']) + '">同读取包原始ZIP</a>。</p>')
        if kind == 'news':
            n = section['result']['projection']
            parts.append('<p>' + str(len(n['observations'])) + '条保存标题，' + str(len(n['possible_event_groups']))
                + '个精确同标题待核对组；不是已核实经济事件。发布时间仅为来源声明，缓存时间不冒充发布时间。</p>')
            parts.append('<p>公司上下文：' + e(p['company_context_status']) + '。名称命中不是业务受益或Pre资格。</p>')
            by_id = {r['version_id']: r for r in n['observations']}
            for company in n['companies']:
                parts.append('<h3>' + e(' / '.join(company['source_names'])) + ' · ' + e(company['thscode']) + '</h3>')
                for match in company['matches']:
                    row = by_id[match['observation_id']]
                    parts.append('<p>' + e(row['title']) + '（' + e(row['source_id']) + '）</p>')
                parts.append('<p>问题尚未形成；业务联系未建立。研究上下文：' + e(company['research']['status']) + '。</p>')
            parts.append('<details><summary>全部保存标题与原时间声明</summary>')
            for row in n['observations']:
                parts.append('<p><a rel="noreferrer noopener" href="' + e(row['url']) + '">' + e(row['title'])
                    + '</a> · ' + e(row['source_id']) + '<br>' + e(json.dumps(row['publication_claims'], ensure_ascii=False)) + '</p>')
            parts.append('</details><details><summary>未消费的补充来源及原状态</summary><pre>'
                         + e(json.dumps(section['excluded_profiles'], ensure_ascii=False)) + '</pre></details>')
        else:
            parts.append('<p>供应商主连，不是固定到期合约；收益按保存观察间隔计算。仓单单位、换月构成、历史PIT和公司实质性未建立。</p><div class="scroll"><table><tr><th>品种 / 截止</th><th>5观察期</th><th>20观察期</th><th>基差率变化：百分点</th><th>仓单变化：未知单位</th><th>字段缺口</th></tr>')
            for report_row in section['results']:
                row = report_row['projection']
                values = (row['name'] + ' / ' + row['period_end'], percent(row['returns_over_observations']['5']),
                          percent(row['returns_over_observations']['20']), row['basis_reported_delta_percentage_points'],
                          row['warehouse_delta_raw_unit'], len(row['field_gaps']))
                parts.append('<tr>' + ''.join('<td>' + e('UNKNOWN' if x is None else x) + '</td>' for x in values) + '</tr>')
            parts.append('</table></div><p>局部勾稽差异保留UNKNOWN；不能据此自动判定行业拐点或受益公司。完整原值、计算值与差异见结构化结果。</p>')
        parts.append('</section>')
    parts.append('<p>AI Investment Authority = NONE。未执行Pre/Quick/Deep/Odds/Action。</p></html>')
    return ''.join(parts)
