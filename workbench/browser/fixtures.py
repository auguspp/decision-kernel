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
    files['current-state.json'] = raw(payload)
    return files
