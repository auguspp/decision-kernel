"""Exact saved-v8 compatibility, never source replay or live acceptance."""
import copy
import json

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import stock_market_expression as market
from decision_kernel.runtime import stock_radar_reading as stock

# Frozen complete policy from ce22fa79, not built from the current producer.
OLD_POLICY = json.loads('''{"activity":"POSITIVE_LATEST_VOLUME_AND_TURNOVER_NOT_EXECUTION_ELIGIBILITY","business_evidence":"ANNOTATION_ONLY_NOT_CANDIDATE_GATE","corporate_actions":"SUCCESSFUL_QUERY_REQUIRED_NO_REPORTED_EVENT_CROSSING_5D_OR_20D","direction":"EXISTING_CURRENT_SECTOR_GATE_NOT_NEW_EVENT_REQUIRED","issuer_failure_scope":"ISOLATE_KNOWN_STOCK_DATA_FAILURES_NOT_SHARED_OR_TRANSPORT_FAILURES","issuer_universe":"BOUNDED_SURFACED_SECTOR_BREADTH_LEADERS_NOT_ALL_A_SHARES","live_reference_source":"HITHINK_EXISTING_GITHUB_SECRET_NO_SECOND_PROVIDER_REQUIRED","max_cards":3,"max_issuers":16,"max_memberships":6,"membership":"EXACT_CURRENT_MEMBER_REQUIRED_NOT_HISTORICAL_EXPOSURE","name_guard":"ST_DELISTING_AND_N_C_PREFIX_LABELS_ONLY_NOT_FULL_REGULATORY_STATUS","no_composite_score":true,"partial_result":"USABLE_SUBSET_ONLY_WITH_FULL_PLAN_DENOMINATOR_AND_EXPLICIT_GAPS","premarket_index_carry":"STOCK_ONLY_RECEIPT_BOUND_STRICTLY_BEFORE_0915_OPENING_AUCTION","presentation":"SURFACED_GROUP_ROUND_ROBIN_CANDIDATES_THEN_EXISTING_STOCK_GATE","reference_requirement":"HITHINK_LAST_26_MARKET_SESSION_BARS_REQUIRED_OLDER_GAPS_EXPLICIT_EXACT_PRICES_BOUNDED_VOLUME_TURNOVER_ACTIONS_BY_WINDOW","session_freshness":"FETCHED_CALENDAR_LATEST_COMPLETED_NOT_WEEKDAY_HEURISTIC","sixty_day":"CONTEXT_ONLY_NOT_A_GATE_NULL_IF_ACTION_OR_NONCRITICAL_HISTORY_GAP","source_contract":"hithink-own-61-bars-history-actions-through-session-v4","stock_gate":"POSITIVE_5D_RAW_AND_5D_MARKET_EXCESS_AND_20D_MARKET_EXCESS_AND_ONE_20D_SECTOR_EXCESS","turnover_reconciliation":{"absolute_tolerance_cny":"0.01","calculation_source":"DATED_HISTORY_UNCHANGED","hard_cap_cny":"100","relative_tolerance":"0.0000001","supplier_precision_rule_established":false,"version":"stock-snapshot-turnover-cny-v1"},"version":"stock-market-expression-window-qualified-v8","volume_reconciliation":{"absolute_tolerance_shares":"2","calculation_source":"DATED_HISTORY_UNCHANGED","hard_cap_shares":"10","relative_tolerance":"0.00000001","supplier_precision_rule_established":false,"version":"stock-snapshot-volume-shares-v1"}}''')


def sealed(value, field):
    value[field] = canonical_hash({k: v for k, v in value.items() if k != field})
    return value


def sample(*, legacy=True):
    """Synthetic two-issuer saved reading; not a live acquisition fixture."""
    good = {'thscode': '600001.SH', 'company_name': 'Synthetic raw issuer',
            'status': 'CONTRACT_CHECKED_RAW_READING', 'input_failure': None,
            'eligible_for_shadow_reading': True, 'excluded_reasons': [],
            'business_benefit_status': 'NOT_ESTABLISHED', 'market_expression_status': 'OBSERVED',
            'current_origins': [],
            'market_comparison': {'5': {'excess_return': '0.1'}, '20': {'excess_return': '0.2'}},
            'stock_path': {'last_close': '10', 'corporate_action_adjustment': 'NOT_PERFORMED',
                           'price_convention': 'RAW_UNADJUSTED_PRICE_PATH_NOT_TOTAL_RETURN',
                           'input_checks': {'action_window_checks': {}}}}
    gap = {'thscode': '600002.SH', 'company_name': 'Synthetic unavailable issuer',
           'status': 'REQUEST_FAILED', 'input_failure': {'provider_business_code': 3002},
           'eligible_for_shadow_reading': False, 'stock_path': None, 'excluded_reasons': [],
           'business_benefit_status': 'NOT_ESTABLISHED'}
    policy = copy.deepcopy(OLD_POLICY if legacy else stock.MARKET_EXPRESSION_POLICY)
    p = {'version': policy['version'], 'policy': policy, **stock.LIMITS,
         'semantics': stock.MARKET_EXPRESSION_SEMANTICS,
         'market_session': '2026-09-30', 'observed_at': '2026-09-30T10:30:00Z',
         'market_state_hash': 'a' * 64, 'event_ledger_hash': 'b' * 64,
         'sector_result_hash': 'c' * 64, 'scope': 'SYNTHETIC_READING_TEST',
         'reference_input_provenance': stock.HITHINK_RAW,
         'live_stock_qualification': 'SYNTHETIC_ENVELOPES_NOT_LIVE_ACCEPTANCE',
         'current_member_union_count': 2, 'unreviewed_current_members': [],
         'all_stock_observations': [good, gap], 'surfaced_stocks': [good],
         'candidate_source_group_count': 1, 'candidate_routing': {},
         'omitted_eligible_stock_codes': [], 'status': 'PARTIAL_STOCKS_FOR_SHADOW_READING'}
    p['coverage'] = stock._coverage(p['all_stock_observations'])
    p['selection_scope_complete'] = False
    return {'projection': p, 'projection_hash': canonical_hash(p)}


def saved(report):
    """Same native bindings as validate_stock; every byte is synthetic."""
    raw = lambda value: (canonical_json(value) + '\n').encode()
    p = report['projection']
    sha = 'd' * 40
    run = {'id': 10, 'path': read.WORKFLOWS['stock'], 'head_sha': sha,
           'head_branch': 'main', 'repository': {'full_name': read.REPOSITORY},
           'head_repository': {'full_name': read.REPOSITORY}, 'status': 'completed',
           'conclusion': 'success', 'event': 'workflow_dispatch', 'run_attempt': 1}
    workflow = {'GITHUB_RUN_ID': '10', 'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_SHA': sha,
                'GITHUB_REPOSITORY': read.REPOSITORY, 'GITHUB_REF': 'refs/heads/main',
                'GITHUB_EVENT_NAME': 'workflow_dispatch'}
    request = {'workflow': workflow, 'market_run_id': 9}
    state, ledger = b'synthetic market state', b'synthetic ledger'
    manifest = sealed({'market_session': p['market_session'],
        'market_state_hash': p['market_state_hash'], 'event_ledger_hash': p['event_ledger_hash'],
        'source_run_id': 9, 'source_commit_sha': sha,
        'market_state_file_sha256': read.sha256(state),
        'event_ledger_file_sha256': read.sha256(ledger)}, 'manifest_hash')
    binding = {'request_hash': canonical_hash(request), 'run_id': 9,
               'commit': sha, 'artifact_id': 90}
    sector = raw({'result_hash': p['sector_result_hash'],
                  'output_market_state_hash': p['market_state_hash'],
                  'event_ledger_update': {'event_ledger_hash': p['event_ledger_hash']}})
    files = {'request.json': raw(request), 'market-binding.json': raw(binding),
             'market-context-binding.json': raw({**binding, 'state_artifact_id': 90}),
             'market-context/result.json': sector,
             'reading/inputs/sector-result.json': sector, 'reading/stock-reading.json': raw(report)}
    for name, data in [('manifest.json', raw(manifest)), ('market-state.json', state),
                       ('candidate-events.json', ledger)]:
        files['market/' + name] = files['reading/inputs/state/' + name] = data
    inventory = {name.removeprefix('reading/'): {'bytes': len(data), 'sha256': read.sha256(data)}
                 for name, data in files.items() if name.startswith('reading/')}
    capture = sealed({'status': 'COMPLETED_BATCH_WITH_STOCK_DATA_GAPS',
        'workflow': workflow, 'provenance': 'LIVE_HITHINK', 'files': inventory,
        'projection_hash': report['projection_hash'], 'coverage': p['coverage']}, 'capture_hash')
    files['reading/capture.json'] = raw(capture)
    files['verification.json'] = raw({'status': 'STOCK_BATCH_WITH_DATA_GAPS_REBUILT',
        'network_calls': 0, 'capture_hash': capture['capture_hash'],
        'projection_hash': report['projection_hash'], 'coverage': p['coverage']})
    return run, files


@pytest.mark.parametrize('legacy', [False, True])
def test_saved_market_reading_preserves_exact_subset_and_input_bytes(legacy):
    report = sample(legacy=legacy)
    run, files = saved(report)
    before = copy.deepcopy((report, files))
    result = read.validate_stock(run, files)
    assert result['coverage']['qualified_issuers'] == 1
    assert result['coverage']['unavailable_issuers'] == 1
    assert result['dispositions'][1]['input_failure']['provider_business_code'] == 3002
    assert result['projection_hash'] == report['projection_hash']
    assert (report, files) == before
    html = market.render_market_expression_reading(report)
    assert ('历史v8原始价格读取' in html) is legacy


@pytest.mark.parametrize('change', ['policy', 'version', 'authority', 'coverage', 'hash'])
def test_resealed_legacy_policy_or_authority_changes_are_not_compatibility(change):
    report = sample()
    p = report['projection']
    if change == 'policy': p['policy']['max_cards'] = 4
    elif change == 'version': p['version'] = stock.MARKET_EXPRESSION_VERSION
    elif change == 'authority': p['investment_authority'] = 'GRANTED'
    elif change == 'coverage': p['coverage']['unavailable_issuers'] = 0
    report['projection_hash'] = canonical_hash(p) if change != 'hash' else '0' * 64
    with pytest.raises(ValueError, match='identity or authority'):
        market.render_market_expression_reading(report)


@pytest.mark.parametrize('change', ['convention', 'adjustment', 'fallback', 'window'])
def test_legacy_raw_reading_cannot_gain_adjusted_price_qualification(change):
    report = sample()
    path = report['projection']['all_stock_observations'][0]['stock_path']
    if change == 'convention': path['price_convention'] = 'REPORTED_ACTION_REFERENCE_ADJUSTED_NOT_TOTAL_RETURN'
    elif change == 'adjustment': path['corporate_action_adjustment'] = 'PERFORMED'
    elif change == 'fallback': path['input_checks']['adjusted_history_fallback'] = {}
    else: path['input_checks']['action_window_checks'] = {'20': {'comparison_basis': 'REPORTED_ACTION_REFERENCE_ADJUSTED'}}
    report['projection_hash'] = canonical_hash(report['projection'])
    with pytest.raises(ValueError, match='legacy raw'):
        market.render_market_expression_reading(report)


def test_legacy_reader_does_not_enable_legacy_producer_plans():
    assert canonical_hash(OLD_POLICY) == market.LEGACY_RAW_POLICY_HASH
    assert stock._plan_contract({'version': OLD_POLICY['version'], 'policy': OLD_POLICY}) is None
    current = {'version': stock.MARKET_EXPRESSION_VERSION, 'policy': stock.MARKET_EXPRESSION_POLICY}
    assert stock._plan_contract(current) is not None
    report = sample(legacy=False)
    report['projection']['policy'] = copy.deepcopy(OLD_POLICY)
    report['projection_hash'] = canonical_hash(report['projection'])
    with pytest.raises(ValueError, match='identity or authority'):
        market.render_market_expression_reading(report)


@pytest.mark.parametrize('change', ['sector-copy', 'context', 'inventory', 'run', 'discovery'])
def test_legacy_reading_keeps_original_source_and_context_checks(change):
    run, files = saved(sample())
    if change == 'sector-copy': files['market-context/result.json'] = b'changed'
    elif change == 'context':
        value = json.loads(files['market-context-binding.json'])
        value['state_artifact_id'] = 91
        files['market-context-binding.json'] = json.dumps(value).encode()
    elif change == 'inventory': files['reading/stock-reading.json'] += b' '
    elif change == 'run': run['head_sha'] = 'e' * 40
    else: files['reading/inputs/discovery-page.json'] = b'{}'
    with pytest.raises(ValueError):
        read.validate_stock(run, files)
