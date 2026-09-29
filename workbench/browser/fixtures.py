"""TEST_ONLY inputs for the actual Workbench; no production fetch or saved state.

Shapes follow app.test.mjs continuityFixture and global-markets.test.mjs.
Only input bytes/descriptors are made here. All reading, digest and UI behavior
is exercised by the unmodified browser modules, not reimplemented in Python.
"""
import hashlib
import json

REPO = 'auguspp/decision-kernel'
R1, R2, M = 'a' * 40, 'b' * 40, 'c' * 40  # Synthetic identities, not Git commits.
NOW = '2026-09-27T08:30:00Z'
AUTHORITY = {key: 'NONE' for key in ('signal_transition_authority',
    'human_attention_authority', 'research_authority', 'investment_authority')}
CATALOGUE = 'details/research/asset-reentry.json'
MARKETS = 'details/markets/global-market.json'


def raw(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode()


def descriptor(path, data):
    return {'read_path': path, 'path': path, 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}


def market_fixture():
    authority = {**AUTHORITY, 'automatic_admission': False, 'odds_recomputed': False}
    run = {'id': 901, 'path': '.github/workflows/radar-global-market.yml',
           'event': 'workflow_dispatch', 'head_branch': 'main', 'head_sha': M,
           'run_attempt': 1, 'status': 'completed', 'conclusion': 'success'}
    outcomes = [{'id': symbol, 'status': 'ROWS_NORMALIZED', 'observations': [{
        'symbol': symbol, 'source_date': '2026-09-25', 'previous_observed_date': '2026-09-21',
        'value': '101', 'previous_value': '100', 'unit': 'INDEX_POINTS',
        'observed_interval_change_pct': '1.000000',
        'change_scope': 'TWO_RETURNED_DATES_NOT_ASSERTED_CONSECUTIVE_SESSIONS'}]}
        for symbol in ('SPX', 'IXIC', 'HSI', 'HKTECH', 'N225', 'GDAXI')]
    report = {'version': 'global-market-context-v1', 'family': 'indices', 'authority': authority,
        'source': 'TUSHARE_RELAY_THIRD_PARTY_NOT_OFFICIAL_TUSHARE', 'source_calls_during_replay': 0,
        'capture_hash': 'd' * 64, 'identity': {'repository': REPO, 'workflow': run['path'],
            'ref': 'refs/heads/main', 'event': 'workflow_dispatch', 'attempt': 1, 'run_id': 901, 'code_commit': M},
        'captured_from': '2026-09-27T08:00:00Z', 'captured_through': '2026-09-27T08:01:00Z',
        'outcomes': outcomes, 'available_values': 6, 'status': 'AVAILABLE'}
    # An explicit source gap alongside a valid family, not a forged zero quote.
    families = {name: {'latest_attempt': None, 'latest_read_status': 'TEST_ONLY_SOURCE_GAP', 'snapshot': None}
                for name in ('indices', 'shibor', 'treasury', 'fx', 'commodities', 'crypto')}
    families['indices'] = {'latest_attempt': run, 'latest_read_status': 'CAPTURE_READ',
        'snapshot': {'run': run, 'report': report,
            'archive': {'sha256': 'd' * 64, 'read_path': 'sources/artifacts/' + 'd' * 64 + '.zip'}}}
    return {'projection': {'version': 'global-market-reading-v2', 'checked_at': NOW,
        'authority': authority, 'source_calls': 0, 'complete_global_coverage': False,
        'families': families, 'query': {'unattributed_run_ids': []}, 'prior_read_gaps': []},
        'projection_hash': 'e' * 64}


def calendar_fixture(files, ref):
    """TEST_ONLY normalized view shapes; not a new reviewed or admitted source.

    The apparent REVIEWED_WEB_EXCERPT is a display-contract input only, like the
    existing synthetic main/run identities. Backend synthetic rejection has its
    own no-network tests. All source bytes remain intercepted fixture data.
    """
    source = ("# October 2026\n"
        "Friday, October 2, 2026 08:30 AM Employment Situation for September 2026\n"
        "Wednesday, October 14, 2026 08:30 AM Consumer Price Index for September 2026\n"
        "Thursday, October 15, 2026 08:30 AM Producer Price Index for September 2026\n"
        "NOTE: All times on calendar are Eastern Time.\n"
        "TEST_ONLY <script>window.fixtureInjected=true</script>\n").encode()
    digest = hashlib.sha256(source).hexdigest()
    events = []
    for line, (code, series, title, day) in enumerate([
        ('employment', 'Employment Situation', '美国就业报告', '02'),
        ('cpi', 'Consumer Price Index', '美国消费者价格指数', '14'),
        ('ppi', 'Producer Price Index', '美国生产者价格指数', '15')], 2):
        events.append({'event_id': f'BLS:{code}:2026-09', 'title': title, 'source_series': series,
            'reporting_period': '2026-09', 'date_status': 'SCHEDULED', 'scheduled_date': f'2026-10-{day}',
            'source_timezone': 'America/New_York', 'time_precision': 'MINUTE',
            'scheduled_at': f'2026-10-{day}T08:30:00-04:00', 'local_scheduled_at': f'2026-10-{day}T20:30:00+08:00',
            'source_line': line, 'source_sha256': digest, 'actual_release_at': 'UNKNOWN',
            'release_observed': 'NOT_CHECKED', 'release_material_obtained': 'NOT_CHECKED',
            'analysis': 'NOT_RUN', 'human_response': 'NOT_RECORDED'})
    c = {'version': 'bls-research-calendar-v1', 'as_of': NOW, 'status': 'SCHEDULED_EVENTS_IN_WINDOW',
        'coverage': 'THREE_BLS_SERIES_IN_REVIEWED_EXCERPT_NOT_COMPLETE_CALENDAR',
        'company_events': 'NOT_IMPLEMENTED_NO_FOLLOW_OR_HOLDING_INFERENCE',
        'window': {'start':'2026-09-28', 'end':'2026-10-25' if ref == R1 else '2026-10-10',
                   'basis':'SOURCE_DATE', 'timezone':'America/New_York'},
        'local_timezone':'Asia/Singapore', 'parsed_rows':3, 'excluded_outside_window':0 if ref == R1 else 2,
        'events':events if ref == R1 else events[:1],
        'source':{'url':'https://www.bls.gov/schedule/2026/10_sched_list.htm', 'reviewed_at':NOW,
            'observation_kind':'REVIEWED_WEB_EXCERPT', 'custody':'EXCERPT_BYTES_ONLY_NOT_ORIGINAL_HTTP_BODY',
            'retrieved_at':'UNKNOWN', 'published_at':'UNKNOWN', 'path':'source.txt', 'bytes':len(source), 'sha256':digest},
        'authority':{key:'NONE' for key in ('research','human_attention','investment','execution')}}
    c['calendar_hash'] = hashlib.sha256(json.dumps(c, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    originals = {'source.txt':source, 'calendar.json':raw(c),
                 'calendar.md':'# TEST_ONLY 日历原件\n\n不是已发布或已接受。\n'.encode(),
                 'request.json':raw({'meaning':'TEST_ONLY display fixture, not a production request'})}
    refs = {}
    for name, content in originals.items():
        blob = descriptor(name, content)['git_blob']
        path = f'sources/git/{blob}/{name}'
        files[path] = content
        refs[name] = descriptor(path, content)
    return {**AUTHORITY, 'version':'research-calendar-reading-v1', 'status':'SAVED_REVIEWED_CALENDAR',
            'meaning':'SAVED_APPOINTMENTS_NOT_RELEASE_OR_RESEARCH', 'calendar_hash':c['calendar_hash'],
            'as_of':NOW, 'checked_at':NOW, 'source_commit':M, 'coverage':c['coverage'],
            'window':c['window'], 'event_count':len(c['events']), 'files':refs}



def concept_fixture(files, ref):
    """TEST_ONLY three concepts with overlapping source members and separate Stock states."""
    auth = {k: 'NONE' for k in ('research_authority', 'odds_authority', 'action_authority', 'investment_authority')}
    taxonomy = 'TDX_CATEGORY_CONCEPT_SOURCE_NATIVE_NOT_EASTMONEY_BK_OR_HITHINK_TI'
    names = ['TEST_ONLY 概念甲', 'TEST_ONLY 概念乙', 'TEST_ONLY 概念丙']
    rows = [{'code': str(i + 1) * 6, 'name': name, 'full_code': 'sh'+str(i+1)*6, 'market_session': '2026-09-25',
        'periods': {k: {'change_percent': '-1.25'} for k in ('today', '5d', '10d')}} for i, name in enumerate(names)]
    observation = {'projection': {**auth, 'version': 'tdx-concept-snapshot-v1', 'taxonomy': taxonomy,
        'kind': 'MARKET_EXPRESSION', 'qualification': 'CONTEXT_ONLY', 'market_session': '2026-09-25',
        'catalog_count': 3, 'observations': rows}, 'projection_hash': '1' * 64}
    groups = [['600000.SH', '600001.SH', '600002.SH', '600003.SH'] if ref == R1 else ['600000.SH'],
              ['600000.SH', '600001.SH'], ['600003.SH']]
    labels = ['TEST_ONLY 成员甲 <script>window.fixtureInjected=true</script>', 'TEST_ONLY 成员乙', 'TEST_ONLY 成员丙', 'TEST_ONLY 成员丁']
    used = {t for group in groups for t in group}
    securities = {f'60000{i}.SH': {'name': name, 'in_source_catalog': True} for i, name in enumerate(labels) if f'60000{i}.SH' in used}
    members = {'projection': {**auth, 'version': 'tdx-concept-membership-v1', 'taxonomy': taxonomy,
        'market_session': '2026-09-25', 'source_prepared_date': '2026-09-25', 'source_observed_at': NOW,
        'observation_hash': observation['projection_hash'], 'capture_hash': '2' * 64, 'parser_version': '3.2.2',
        'membership_time_basis': 'SAVED_SOURCE_PREPARATION_NOT_HISTORICAL_EFFECTIVE_MEMBERSHIP',
        'historical_membership': 'NOT_ESTABLISHED', 'member_ranking': 'NOT_COMPUTED',
        'business_benefit': 'NOT_ESTABLISHED', 'source_calls': 0, 'catalog_count': 3,
        'relation_count': sum(map(len, groups)), 'securities': securities,
        'concepts': [{'code': row['code'], 'name': row['name'], 'members': group} for row, group in zip(rows, groups)]},
        'projection_hash': ('3' if ref == R1 else '4') * 64}
    op, mp = 'details/radar/tdx-concept/observation.json', 'details/radar/tdx-concept/membership.json'
    files[op], files[mp] = raw(observation), raw(members)
    return {'status': 'VERIFIED_SAVED_TDX_CONCEPT_SOURCE', 'result': {
        'projection_hash': observation['projection_hash'], 'market_session': '2026-09-25', 'catalog_count': 3},
        'details': {'observation': descriptor(op, files[op])}, 'membership': {
            'status': 'VERIFIED_SAVED_MEMBERSHIP', 'projection_hash': members['projection_hash'],
            'catalog_count': 3, 'relation_count': sum(map(len, groups)), 'file': descriptor(mp, files[mp])}}



def concept_trend_fixture(files, saved, ref):
    """TEST_ONLY presentation shapes, not a real history capture or phase computation."""
    source = json.loads(files[saved['details']['observation']['read_path']])['projection']
    coverage = {'horizons': {'5': 3, '20': 2, '60': 2}, 'phase_rows': 2, 'unavailable_rows': 0}
    phases = ['STRENGTHENING' if ref == R1 else 'MATURE_OR_DIVERGING', 'WEAKENING_OR_EXIT', 'UNKNOWN']
    rows = []
    for i, c in enumerate(source['observations']):
        row = {k: c[k] for k in ('code','name','full_code')}
        row.update(phase=phases[i], phase_reason='TEST_ONLY_SAVED_OBSERVATION', gap=None,
            history_points=126 if i<2 else 15, history_start='2026-04-01' if i<2 else '2026-09-07',
            history_end='2026-09-25', previous_session='2026-09-24',
            previous_20d_excess='0.01' if i<2 else None,
            excess_acceleration_5_sessions_20d='0.01' if i==0 and ref==R1 else '-0.01' if i<2 else None,
            positive_20d_excess_persistence_sessions=106 if i==0 else 0 if i==1 else None,
            positive_20d_excess_run_started='2026-04-29' if i==0 else None,
            positive_20d_excess_persistence_left_censored=True if i==0 else False if i==1 else None,
            horizons={str(n): {'index_return':'0.03' if i==0 else '-0.01', 'benchmark_return':'0.01',
                               'excess_return':'0.02' if i==0 else '-0.02'} if i<2 or n==5 else None for n in (5,20,60)})
        rows.append(row)
    p = {k: source[k] for k in ('taxonomy','kind','qualification','market_session',
                               'research_authority','odds_authority','action_authority','investment_authority')}
    p.update(version='tdx-concept-trend-v1',observation_hash=saved['result']['projection_hash'],
        base_capture_hash='2'*64, source_hash='5'*64, source_observed_at=NOW, catalog_count=3,
        benchmark={'full_code':'sh000300','source':'SAME_TDX_HOST','history_start':'2026-04-01',
                   'history_end':'2026-09-25','history_points':126},
        return_unit='FRACTION_NOT_PERCENT', source_calls_during_replay=0,
        policy={'phase_basis':'DESCRIPTIVE_20D_EXCESS_NOT_INVESTMENT_SIGNAL',
                'session_basis':'RETURNED_BENCHMARK_SESSIONS_NOT_EXCHANGE_CALENDAR',
                'custody':'EXTRACTED_SDK_TIME_AND_INTEGER_CLOSE_NOT_RAW_WIRE'},
        historical_universe='CURRENT_CATALOG_NOT_HISTORICAL_MEMBERSHIP',
        trend_age='POSITIVE_20D_EXCESS_RUN_WITH_LEFT_CENSOR_NOT_THEME_LIFETIME',
        coverage=coverage,observations=rows)
    report={'projection':p, 'projection_hash':('6' if ref==R1 else '7')*64}
    path='details/radar/tdx-concept/trend/trend.json';files[path]=raw(report)
    saved['trend']={'status':'VERIFIED_SAVED_LONG_HISTORY','projection_hash':report['projection_hash'],
                    'catalog_count':3,'coverage':coverage,'details':{'trend.json':descriptor(path,files[path])}}

def fixture(ref=R1):
    """Fresh, small bytes per scenario. Synthetic reading_hash is shape-only."""
    files = {'sources/correction.md': '# TEST_ONLY 更正\n\n## 限制\n\n只适用于原版本；未知仍是 UNKNOWN。\n'.encode(),
             'sources/response.md': '# TEST_ONLY 历史回应\n\n仅针对原版本，不是新接受。\n'.encode(),
             'sources/request.json': raw({'meaning': 'TEST_ONLY synthetic request, not Human authority'})}
    companies = []
    for index in range(12):
        path = f'sources/paper-{index}.md'
        files[path] = (f'# TEST_ONLY 研究 {index}\n\n## 结论\n\n合成正文 {index}；固定版本 {ref}。'
                       '\n\n## 限制\n\n未建立接受或投资权限；<script>window.fixtureInjected=true</script> 只是文字。\n').encode()
        assets = [{'id': f'paper-{index}', 'use': 'RETAINED_RESEARCH_DOCUMENT',
                   'purpose_note': 'TEST_ONLY 合成原研究，不是真实公司结论。', 'source': descriptor(path, files[path])}]
        if index == 0:
            assets += [{'id': 'correction', 'use': 'METHOD_SUPPLEMENT',
                        'source': descriptor('sources/correction.md', files['sources/correction.md'])},
                       {'id': 'old-response', 'use': 'HUMAN_DECISION_CHECKPOINT',
                        'source': descriptor('sources/response.md', files['sources/response.md'])}]
        companies.append({'thscode': f'600{index:03d}.SH', 'saved_watch': {'company_name': f'合成公司{index:02d}'},
            'archives': [], 'assets': assets, 'human_acceptance': 'NOT_ESTABLISHED'})
    files[CATALOGUE] = raw({'projection': {'automatic_admission': False, 'companies': companies}})
    market = market_fixture()
    files[MARKETS] = raw(market)
    source = descriptor('sources/request.json', files['sources/request.json'])
    item = {'request_id': '2' * 64, 'security_id': '600000.SH', 'ticker': '600000',
        'as_of': NOW, 'terminal_state': 'DEEPEN_REQUIRED', 'reason': 'TEST_ONLY 新版本请求，未接受。',
        'source': source, 'resolution': None}
    old = {**item, 'request_id': '1' * 64, 'reason': 'TEST_ONLY 历史版本请求',
           'resolution': descriptor('sources/response.md', files['sources/response.md'])}
    payload = {'schema_version': 1, 'entry_ref': 'read-model/current-state', 'code_commit': M,
        'semantics': 'READ_ONLY_SAVED_RESULTS_AND_EXPLICIT_REQUESTS_NOT_RESTORE_AUTHORITY',
        'reading_hash': 'f' * 64, **AUTHORITY, 'checks': {}, 'pending': [item],
        'lanes': {'stock': {'health': 'LATEST_ATTEMPT_SUCCEEDED', 'last_qualified_result': {
            'market_session': '2026-09-25', 'dispositions': [{'thscode': '600000.SH',
                'company_name': 'TEST_ONLY 个股保留', 'status': 'CONTRACT_CHECKED_RAW_READING'}]}}},
        'research': {'handoffs': {'active': [item], 'resolved_history': [old], 'background': [], 'gaps': [],
            'registration_scope': 'EXPLICIT_INPUTS_ONLY_NOT_ALL_RESEARCH_OR_ALL_MARKET'},
            'asset_reentry': {'structured': descriptor(CATALOGUE, files[CATALOGUE])},
            'global_market': {'version': 'global-market-reading-v2', 'checked_at': NOW,
                'projection_hash': market['projection_hash'], 'details': {'json': descriptor(MARKETS, files[MARKETS])}}}}
    payload['research']['calendar'] = calendar_fixture(files, ref)
    payload['research']['tdx_concept_context'] = concept_fixture(files, ref)
    concept_trend_fixture(files, payload['research']['tdx_concept_context'], ref)
    payload['lanes']['stock']['last_qualified_result']['dispositions'] += [
        {'thscode': '600001.SH', 'company_name': 'TEST_ONLY 条件不满足', 'status': 'CONDITIONS_NOT_MET'},
        {'thscode': '600002.SH', 'company_name': 'TEST_ONLY 数据不可用', 'status': 'DATA_QUALIFICATION_FAILED'}]
    files['current-state.json'] = raw(payload)
    return files
