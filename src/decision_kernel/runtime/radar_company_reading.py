"""Company-first composition of saved Radar sources and existing research records.

No source acquisition, price qualification, research admission/execution or score.
The caller supplies validated source products and exact same-reading references.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Context, Decimal, localcontext
from html import escape
from urllib.parse import quote

from decision_kernel.adapters.hithink import to_hithink_thscode
from decision_kernel.identity import canonical_hash, canonical_json
from . import current_state as model
from . import institutional_radar as institutional
from .radar_stock_candidates import build_stock_discovery_pool

VERSION = 'radar-company-reading-v1'
CONCEPT_VERSION = 'radar-company-reading-with-concepts-v2'
AUTHORITY = {**model.AUTHORITY, 'automatic_research_routing': False,
             'odds_recomputed': False, 'new_market_requests': 0, 'model_calls': 0}


def retained_bytes(files, reference):
    """Resolve an exact same-package reference, never a mutable remote URL."""
    model.check(isinstance(reference, dict)
                and reference.get('read_ref_rule') == 'USE_THE_SAME_PINNED_READING_COMMIT',
                'Radar source must remain in the same reading')
    raw = files[model.safe_path(reference['read_path'])]
    model.check(len(raw) == reference['bytes'] and model.sha256(raw) == reference['sha256']
                and model.blob_sha(raw) == reference['git_blob'], 'Radar retained source differs')
    return raw


def _code(code):
    model.check(isinstance(code, str) and len(code) == 9, 'Radar security identity missing')
    exchange = {'SH': 'SSE', 'SZ': 'SZSE', 'BJ': 'BSE'}.get(code[-2:])
    model.check(exchange is not None
                and to_hithink_thscode(ticker=code[:6], exchange=exchange) == code,
                'Radar security identity differs')
    return code


def _research_context(code, research):
    # Do not infer exchange from a free-text case name or a six-digit ticker.
    references = [deepcopy(r) for r in research.get('records', []) if r.get('case') == code]
    work = research.get('stock_business_work', {})
    matched = [deepcopy(r) for r in work.get('items', []) if r.get('thscode') == code]
    model.check(len(matched) <= 1, 'Duplicate Stock business root for a security')
    if work.get('status') != 'READ_OK':
        model.check(not matched, 'Unavailable Research work cannot supply company results')
    states = []
    if matched:
        item = matched[0]
        states = [{'role': 'ROOT', 'record': item}]
        for key in ('source_recovery', 'source_successor', 'source_successor_continuation'):
            if key in item:
                states.append({'role': key, 'record': deepcopy(item[key])})
        for state in states:
            r = state['record']
            model.check(r.get('thscode') == code and all(r.get(k) == v for k, v in model.AUTHORITY.items()),
                        'Research state security or authority differs')
    return {'status': 'SAVED_CONTEXT_PRESENT' if references or states else 'UNKNOWN_WITHIN_READ_SCOPE',
            'references': references, 'stock_business_states': states,
            'stock_business_read_status': work.get('status', 'NOT_CONFIGURED'),
            'scope': 'EXPLICIT_PURPOSE_REFERENCES_AND_STOCK_BUSINESS_ROOTS_NOT_ALL_RESEARCH',
            'meaning': 'NO_RECORD_IS_NOT_NEVER_RESEARCHED; SAVED_STATE_IS_NOT_HUMAN_ACCEPTANCE'}


def _questions(row):
    questions = []
    for origin in row['origins']:
        if origin['kind'] == 'SECTOR_LEADER':
            questions.append('来源方向“' + origin['sector_name'] + '”中，该公司为何值得核查？'
                             '先核对业务联系、收入利润暴露及反证；当日突出不等于多日领先或业务受益。')
        elif origin['kind'] == 'CONCEPT_CURRENT_MEMBER':
            questions.append('概念“' + origin['concept_name'] + '”中的当前成员身份是否有真实业务依据？'
                             '先区分上市属性、市场标签与经济暴露；多个重叠概念不是独立受益证据。')
        else:
            observations = origin['observations']
            nets = [Decimal(v['institution_net_cny']) for v in observations
                    if v['institution_net_cny'] is not None]
            if any(v > 0 for v in nets) and any(v < 0 for v in nets):
                questions.append('单日和三日席位净额方向不同：先核对各区间披露与事件时间；不相加、不倒算前两日。')
            if any(v['institution_net_cny'] is None for v in observations):
                questions.append('机构净额未提供：先补来源字段口径，不能把缺失解释为零交易。')
            questions.append('该区间机构席位活动是否伴随可核实的经营、公告或预期变化？净额方向本身不能解释机构动机。')
    if len({v['kind'] for v in row['origins']}) > 1:
        questions.append(('多种' if any(v['kind'] == 'CONCEPT_CURRENT_MEMBER' for v in row['origins']) else '两种')
                         + '发现来路落在同一公司：分别核对日期和业务事实，不把来源重叠当成独立投资确认。')
    if any(s['record'].get('status') == 'PRE_EXECUTION_FAILURE'
           for s in row['research']['stock_business_states']):
        questions.append('已有来源准备失败记录：先按原执行身份处理接续，不重置旧问题、重复启动首次基线或把失败写成WAIT。')
    return list(dict.fromkeys(questions))


def build(baseline, *, sector_result, sector_source, institution_report, institution_source,
          source_status, generated_at, concept_report=None, concept_source=None, include_concept=False):
    model.validate_read_package(baseline)
    cutoff = model.clock(generated_at)
    model.check(cutoff >= model.clock(baseline['generated_at']), 'Radar reading clock reversed')
    model.check(type(include_concept) is bool and (include_concept or (concept_report is None and concept_source is None)),
                'Concept reading must be explicitly enabled')
    companies = {}
    def company(code, name):
        _code(code)
        model.check(isinstance(name, str) and bool(name.strip()), 'Radar source name missing')
        row = companies.setdefault(code, {'thscode': code, 'source_names': [], 'origins': []})
        if name not in row['source_names']:
            row['source_names'].append(name)
        return row
    sector_codes, institution_codes = set(), set()
    if sector_result is not None:
        model.check(sector_source is not None, 'Sector origin reference required')
        pool = build_stock_discovery_pool(sector_result)
        model.check(model.clock(pool['source_produced_at']) <= cutoff, 'Future Sector source')
        for item in pool['candidates']:
            row = company(item['thscode'], item['company_name']); sector_codes.add(item['thscode'])
            for origin in item['origins']:
                row['origins'].append({'kind': 'SECTOR_LEADER', 'market_session': pool['market_session'],
                    'source_observed_at': pool['source_produced_at'], 'source': deepcopy(sector_source),
                    'source_result_hash': pool['source_result_hash'], **deepcopy(origin)})
    if institution_report is not None:
        institutional.render(institution_report)  # Existing pure identity/authority check.
        p = institution_report['projection']
        model.check(institution_source is not None and model.clock(p['generated_at']) <= cutoff,
                    'Institutional origin missing or future')
        for item in p['companies']:
            row = company(item['thscode'], item['company_name']); institution_codes.add(item['thscode'])
            row['origins'].append({'kind': 'INSTITUTIONAL_WINDOWS', 'market_session': p['market_session'],
                'source_observed_at': p['origin']['requests'][-1]['received_at'],
                'source': deepcopy(institution_source), 'projection_hash': institution_report['projection_hash'],
                'observations': deepcopy(item['observations']), 'publication_time': 'UNKNOWN',
                'window_aggregation': p['window_aggregation'], 'source_labels': p['source_labels']})
    concept_codes = set()
    concept_context = {'status': 'NO_READABLE_SAVED_SOURCE'}
    if concept_report is not None:
        from . import concept_radar as concept
        concept.render(concept_report)  # Caller already replayed original raw payload.
        cp = concept_report['projection']
        model.check(concept_source is not None and model.clock(cp['as_of']) <= cutoff,
                    'Concept source missing or future')
        detail_by_code = {d['thscode']: d for d in cp['details']}
        model.check(len(detail_by_code) == len(cp['details']), 'Duplicate concept detail')
        for item in cp['companies']:
            model.check(item['thscode'] not in concept_codes and item['source_names'], 'Duplicate or unnamed concept company')
            concept_codes.add(item['thscode'])
            for name in item['source_names']:
                row = company(item['thscode'], name)
            for origin in item['origins']:
                detail = detail_by_code[origin['concept_thscode']]
                index = origin['membership_request_index']
                model.check(type(index) is int and 0 <= index < len(cp['requests']), 'Concept request reference invalid')
                request = cp['requests'][index]
                membership = detail['current_membership']
                model.check(origin['kind'] == 'CONCEPT_CURRENT_MEMBER' and membership is not None
                    and request['path'] == concept.probe.MEMBERS and request['params'] == {'thscode': detail['thscode']}
                    and origin['membership_hash'] == membership['constituent_set_hash']
                    and any(m['thscode'] == item['thscode'] for m in membership['members'])
                    and origin['market_session'] == cp['market_session']
                    and model.clock(request['received_at']) <= model.clock(cp['as_of']), 'Concept member origin differs')
                row['origins'].append({**deepcopy(origin), 'source': deepcopy(concept_source),
                    'source_observed_at': request['received_at'], 'membership_captured_at': membership['captured_at'],
                    'projection_hash': concept_report['projection_hash'], 'business_linkage': 'NOT_ESTABLISHED',
                    'historical_membership': 'NOT_ESTABLISHED', 'publication_time': 'UNKNOWN'})
        concept_context = {'status': 'SAVED_SOURCE_AVAILABLE', 'source': deepcopy(concept_source),
            'market_session': cp['market_session'], 'source_observed_at': cp['as_of'],
            'catalog_count': cp['catalog_count'], 'snapshot_count': cp['snapshot_count'],
            'detail_selection_policy': deepcopy(cp['policy']), 'coverage': deepcopy(cp['coverage']),
            'overlaps': deepcopy(cp['overlaps']),
            'details': [{k: deepcopy(d[k]) for k in ('thscode', 'name', 'history_status', 'membership_status', 'path', 'gaps')}
                        for d in cp['details']], 'meaning': 'CURRENT_MEMBERS_NOT_ECONOMIC_EXPOSURE_OR_INDEPENDENT_CONFIRMATIONS'}
    stock_lane = baseline['lanes'].get('stock', {})
    stock = stock_lane.get('last_qualified_result') or {}
    dispositions = stock.get('dispositions', [])
    model.check(len({v['thscode'] for v in dispositions}) == len(dispositions), 'Duplicate saved Stock disposition')
    for row in companies.values():
        price = [deepcopy(v) for v in dispositions if v['thscode'] == row['thscode']]
        row['stock'] = {'status': 'SAVED_DISPOSITION' if price else 'NOT_PRESENT_IN_SAVED_STOCK_SCOPE',
            'market_session': stock.get('market_session'), 'lane_health': stock_lane.get('health', 'UNKNOWN'),
            'dispositions': price, 'source': deepcopy(stock.get('details', {}).get('reading/stock-reading.json')),
            'meaning': 'HISTORICAL_SAVED_DISPOSITION_NOT_A_NEW_CHECK; ABSENCE_IS_NOT_REJECTION'}
        row['research'] = _research_context(row['thscode'], baseline['research'])
        if include_concept:
            from .stock_research_intake import supported
            row['stock_business_research_scope'] = ('SUPPORTED_IDENTITY_ONLY_NOT_ADMITTED' if supported(row['thscode'])
                                                     else 'RESEARCH_SCOPE_UNSUPPORTED')
        row['name_status'] = 'ONE_SOURCE_NAME' if len(row['source_names']) == 1 else 'SOURCE_NAMES_DIFFER_NOT_RESOLVED'
        row['questions'] = _questions(row)
        row['question_status'] = 'OBSERVATION_QUESTIONS_NOT_PRE_OR_QUICK_RESULTS'
        row['new_research_execution'] = 'NOT_EXECUTED'
        row['automatic_admission'] = False
    payload = {'version': CONCEPT_VERSION if include_concept else VERSION, 'base_reading_hash': baseline['reading_hash'],
        'generated_at': generated_at, 'source_status': deepcopy(source_status),
        'coverage': {'distinct_companies': len(companies), 'sector_companies': len(sector_codes),
            'institutional_companies': len(institution_codes), 'overlap_companies': len(sector_codes & institution_codes),
            'institution_only_companies': len(institution_codes - sector_codes),
            'with_saved_stock_disposition': sum(bool(r['stock']['dispositions']) for r in companies.values()),
            'with_saved_research_context': sum(r['research']['status'] == 'SAVED_CONTEXT_PRESENT' for r in companies.values()),
            'concept_radar': False, 'all_members': False, 'ongoing_without_event': False,
            'complete_research_history': False, 'new_research_executions': 0},
        'research_read_gaps': deepcopy(baseline['research'].get('gaps', [])),
        'research_work_read_status': baseline['research'].get('candidate_work', {}).get('status', 'NOT_CONFIGURED'),
        'stock_business_read_status': baseline['research'].get('stock_business_work', {}).get('status', 'NOT_CONFIGURED'),
        'companies': list(companies.values()),
        'ordering': 'SECTOR_RETAINED_ORDER_THEN_INSTITUTION_SOURCE_ORDER_NOT_PRIORITY_OR_SCORE',
        'date_policy': 'EACH_ORIGIN_DATE_AND_ACTUAL_CLOCK_PRESERVED_NOT_ATOMIC_OR_FIRST_VINTAGE_PIT',
        **AUTHORITY}
    if include_concept:
        existing_codes = sector_codes | institution_codes
        payload['concept_context'] = concept_context
        payload['coverage'].update(concept_radar=concept_report is not None,
            concept_companies=len(concept_codes), concept_only_companies=len(concept_codes - existing_codes),
            concept_overlap_existing_companies=len(concept_codes & existing_codes),
            multi_source_companies=sum(len({o['kind'] for o in r['origins']}) > 1 for r in companies.values()),
            unsupported_stock_business_research_companies=sum(r['stock_business_research_scope'] == 'RESEARCH_SCOPE_UNSUPPORTED'
                                                             for r in companies.values()),
            full_concept_trend_radar=False)
        payload['ordering'] = 'SECTOR_THEN_INSTITUTION_THEN_CONCEPT_RETAINED_ORDER_NOT_PRIORITY_OR_SCORE'
    return {'projection': payload, 'projection_hash': canonical_hash(payload)}


def render(report):
    p = report['projection']
    model.check(report['projection_hash'] == canonical_hash(p) and p['version'] in {VERSION, CONCEPT_VERSION}
                and all(p.get(k) == v for k, v in AUTHORITY.items()), 'Radar company reading identity differs')
    with_concepts = p['version'] == CONCEPT_VERSION
    e = lambda v: escape(str(v), quote=True)
    def link(label, ref):
        if not ref:
            return e(label) + '（无已绑定入口）'
        model.check(ref.get('read_ref_rule') == 'USE_THE_SAME_PINNED_READING_COMMIT', 'Foreign reading link')
        path = model.safe_path(ref['read_path'])
        return '<a href="../../' + quote(path, safe='/') + '">' + e(label) + '</a>'
    def money(v):
        with localcontext(Context(prec=64)):
            return '未提供' if v is None else f'{Decimal(v)/10000:+,.2f}万元'
    c = p['coverage']
    for key in ('distinct_companies', 'sector_companies', 'institutional_companies', 'overlap_companies',
                'with_saved_stock_disposition', 'with_saved_research_context'):
        model.check(type(c[key]) is int and c[key] >= 0, 'Radar display count invalid')
    for row in p['companies']:
        _code(row['thscode'])
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'">',
        '<title>公司发现与研究上下文 · Radar</title>',
        '<style>body{font:16px/1.7 system-ui;max-width:1100px;margin:auto;padding:20px}article{border-top:1px solid #aaa;padding:18px 0}p,pre,a{overflow-wrap:anywhere}pre{white-space:pre-wrap}summary{cursor:pointer}h2{font-size:21px}nav{display:flex;gap:12px;flex-wrap:wrap}small{font-size:13px}@media(max-width:600px){body{padding:12px}}</style>',
        '<h1>公司发现与研究上下文</h1>',
        (f'<p><b>{c["distinct_companies"]} 家保存线索</b>：行业 {c["sector_companies"]} 家，机构 {c["institutional_companies"]} 家，概念 {c["concept_companies"]} 家；按证券去重，不是同日信号合并。</p>'
         if with_concepts else f'<p><b>{c["distinct_companies"]} 家保存线索</b>：行业 {c["sector_companies"]} 家，机构 {c["institutional_companies"]} 家，重叠 {c["overlap_companies"]} 家。</p>'),
        '<p>不是推荐榜。每条来路保留自己的交易日和取得时间；重叠不是双重确认。'
        '以下问题尚未执行Pre/Quick，不代表自动准入或买卖判断。</p>',
        f'<p>有保存价格处置 {c["with_saved_stock_disposition"]} 家；有匹配的保存研究上下文 {c["with_saved_research_context"]} 家。'
        '没有匹配记录不等于从未研究；旧结果不冒充今天的新检查。</p>',
        f'<p>Research work读取：{e(p["research_work_read_status"])}；Stock业务读取：{e(p["stock_business_read_status"])}。</p>',
        '<details><summary>来源状态与未覆盖范围</summary><pre>' + e(canonical_json(p['source_status'])) + '</pre>'
        '<p>尚未覆盖完整概念、全部成员、无新事件持续方向及其他聪明钱维度；缺口不解释为无变化。</p></details>',
        '<nav>' + ''.join(f'<a href="#s-{r["thscode"]}">{e(" / ".join(r["source_names"]))} {r["thscode"]}</a>' for r in p['companies']) + '</nav>']
    if with_concepts:
        navigation_html = parts.pop()
        context = p['concept_context']
        parts.append('<section><h2>概念覆盖与实际重叠</h2>')
        if context['status'] == 'SAVED_SOURCE_AVAILABLE':
            cc = context['coverage']
            parts.append(f'<p>概念保存日 {e(context["market_session"])}；取得截止 {e(context["source_observed_at"])}。'
                f'目录内快照 {context["snapshot_count"]}；已核历史 {cc["history_checked"]}；已核成员 {cc["memberships_checked"]}；'
                f'未取详情 {cc["detail_deferred"]}；详情缺口 {cc["detail_gaps"]}。不是完整连续趋势雷达。</p>')
            source_page = p['source_status'].get('concept', {}).get('details', {}).get('index.html')
            parts.append('<p>' + link('全部概念快照与原详情', source_page) + ' / ' + link('原概念结构化结果', context['source']) + '</p>')
            for overlap in context['overlaps']:
                names = e(overlap['left_sector_name']) + ' / ' + e(overlap['right_sector_name'])
                relation = ('；当前成员完全包含或相同，不是两个独立公司集合。'
                            if overlap['left_contains_right'] or overlap['right_contains_left'] else '。')
                parts.append(f'<p>{names}：成员 {overlap["left_member_count"]} / {overlap["right_member_count"]}；'
                             f'共同 {overlap["intersection_count"]}，并集 {overlap["union_count"]}{relation}</p>')
            parts.append('<details><summary>已取得成员的实际重叠（不是多重确认）</summary><pre>'
                         + e(canonical_json(context['overlaps'])) + '</pre></details>')
        else:
            parts.append('<p>概念来源本次不可读；不是没有变化。其他来源照常保留。</p>')
        parts.append(f'<p>概念独有公司 {c["concept_only_companies"]}；与行业/机构旧池重叠 {c["concept_overlap_existing_companies"]}。'
                     f'全部来路中现有Stock业务Research范围不支持 {c["unsupported_stock_business_research_companies"]} 家；'
                     '支持身份也不代表获准研究。概念归属不是业务受益。</p></section>')
        parts.append(navigation_html)
    for row in p['companies']:
        parts += [f'<article id="s-{row["thscode"]}"><h2>{e(" / ".join(row["source_names"]))} {row["thscode"]}</h2>']
        for origin in row['origins']:
            prefix = f'交易日 {e(origin["market_session"])}；原取得/生成时间 {e(origin["source_observed_at"])}。'
            if origin['kind'] == 'SECTOR_LEADER':
                parts.append('<p><b>行业来路：</b>' + e(origin['sector_name']) + ' ' + e(origin['sector_thscode'])
                             + '；' + prefix + ' ' + link('原行业结果', origin['source']) + '</p>')
            elif origin['kind'] == 'CONCEPT_CURRENT_MEMBER':
                parts.append('<p><b>概念来路：</b>' + e(origin['concept_name']) + ' ' + e(origin['concept_thscode'])
                             + '；' + prefix + ' ' + link('原概念成员结果', origin['source'])
                             + '。当前成员，业务联系未建立；多个标签不独立计票。</p>')
            else:
                values = '；'.join(f'{v["range_days"]}日机构席位净额 {money(v["institution_net_cny"])}' for v in origin['observations'])
                parts.append('<p><b>机构来路：</b>' + e(values) + '；' + prefix + ' '
                             + link('原机构结果', origin['source']) + '。各区间不相加。</p>')
        price = row['stock']
        parts.append('<p><b>价格检查：</b>' + e(price['status']) + '；原保存日 ' + e(price['market_session'])
                     + '；读取健康 ' + e(price['lane_health']) + '。</p>')
        if price['dispositions']:
            parts.append('<p>' + e(canonical_json(price['dispositions'])) + ' ' + link('保存价格结果', price['source']) + '</p>')
        if with_concepts:
            parts.append('<p><b>现有Stock业务Research范围：</b>' + e(row['stock_business_research_scope']) + '。</p>')
        research = row['research']
        parts.append('<p><b>研究上下文：</b>' + e(research['status']) + '。这次新Pre/Quick：未执行。</p>')
        for ref in research['references']:
            parts.append('<p>' + link(ref['id'], ref['source']) + ' — ' + e(ref['use']) + '；' + e(ref['purpose_note']) + '</p>')
        for state in research['stock_business_states']:
            r = state['record']; refs = r.get('sources', {})
            parts.append('<p>' + e(state['role'] + ' / ' + r['status']) + ' '
                         + link('原执行记录', refs.get('candidate') or refs.get('failure') or refs.get('selection')) + '</p>')
        parts += ['<details><summary>待核问题与完整来路（不是已完成研究）</summary>',
                  ''.join('<p>' + e(q) + '</p>' for q in row['questions']),
                  '<pre>' + e(canonical_json(row)) + '</pre></details></article>']
    parts.append('<footer>Radar发现，Research解释，Human决定。投资权限NONE；未产生新的研究、Odds或Action。</footer></html>')
    return '\n'.join(parts) + '\n'


def navigation(value):
    """Small saved Markdown entry; all company rows stay in the detail product."""
    lines = ['## 多来源公司发现与研究上下文', '',
             '读取状态：' + escape(str(value['status']), quote=True) + '。']
    if value['status'] in {'READ_OK', 'READ_OK_WITH_SOURCE_GAPS'}:
        c = value['coverage']
        lines += [f"保存公司线索 {c['distinct_companies']} 家：行业 {c['sector_companies']}，"
                  f"机构 {c['institutional_companies']}，重叠 {c['overlap_companies']}；不是推荐数量或已完成研究数量。"]
        if 'concept_companies' in c:
            lines[-1] = (f"保存公司线索 {c['distinct_companies']} 家：行业 {c['sector_companies']}，"
                         f"机构 {c['institutional_companies']}，概念 {c['concept_companies']}；证券去重，不是同日信号或已完成研究数量。")
        for key, label in [('index', '打开全部公司、各自来路与保存研究状态'),
                           ('company_reading', '读取结构化公司结果')]:
            ref = value['details'][key]
            model.check(ref['read_ref_rule'] == 'USE_THE_SAME_PINNED_READING_COMMIT', 'Foreign Radar navigation')
            lines.append('[' + label + '](' + quote(model.safe_path(ref['read_path']), safe='/') + ')')
        lines.append('各来源日期和实际取得时间分开；无匹配研究记录不等于从未研究。'
                     '本层没有执行新的Pre/Quick、Odds或Action；完整概念与其他聪明钱维度仍未覆盖。')
    else:
        lines.append('公司发现读取有缺口；不把不可读解释为零对象，原始各lane状态保留。')
    return '\n'.join(lines) + '\n'
