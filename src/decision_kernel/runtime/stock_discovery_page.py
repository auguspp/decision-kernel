"""Explicit discovery page -> the existing Stock plan, never a second executor.

The original pool/page is retained as a plan. Only a capture's actual outcomes
are dispositions; earlier/later pages are never inferred to have run.
"""
from __future__ import annotations

from copy import deepcopy
from html import escape
import json
import re

from decision_kernel.identity import canonical_hash
from . import radar_stock_candidates as pool_source
from . import stock_radar_reading as stock

ROUTING = 'EXPLICIT_ALL_GROUP_DISCOVERY_PAGE_VIA_EXISTING_STOCK_EXECUTOR'
SCOPE = 'ONE_BOUND_PAGE_OF_RETAINED_SECTOR_LEADERS_NOT_FULL_POOL_OR_ALL_A_SHARES'
CAPTURE_VERSION = 'stock-reading-discovery-page-capture-v8'


def parse_selection(value):
    """Empty input leaves the historical route byte-for-byte unchanged."""
    if value == '':
        return None
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}:(?:0|[1-9][0-9]{0,5})', value):
        raise ValueError('discovery page requires exact pool_hash:offset')
    digest, offset = value.split(':')
    return {'pool_hash': digest, 'offset': int(offset)}


def selection_page(result, selection):
    if (not isinstance(selection, dict) or set(selection) != {'pool_hash', 'offset'}
            or type(selection['offset']) is not int or not isinstance(selection['pool_hash'], str)
            or parse_selection(f"{selection['pool_hash']}:{selection['offset']}") != selection):
        raise ValueError('invalid exact discovery page selection')
    return pool_source.plan_stock_discovery_batch(result, **selection)


def prepare(state, ledger, association, result, *, linked, reviewed, context,
            observed_at, company_manifest, selection):
    """Called after the original market/state/association qualification."""
    page = selection_page(result, selection)
    pool = pool_source.build_stock_discovery_pool(result)
    rows = {r['thscode']: r for r in pool['candidates']}
    saved = {r['observation']['thscode']: (u['family'], r)
             for u in context['universes'] for r in u['rows']}
    groups = {g['group_key']: g for g in result['composition']['all_groups']}
    directions, issuers, order = {}, [], []
    for code in page['selected_codes']:
        candidate = rows[code]
        origins = []
        for raw in candidate['origins']:
            sector = raw['sector_thscode']
            family, direction = saved[sector]
            if (family != raw['family'] or direction['observation']['name'] != raw['sector_name']):
                raise ValueError('discovery direction differs from exact saved state')
            directions[sector] = direction
            group = groups[raw['group_key']]
            primary = group['primary_candidate']
            business = reviewed.get((code, sector))
            origins.append({
                'origin_kind': 'SECTOR_BREADTH_MARKET_EXPRESSION_CANDIDATE',
                'node_id': raw['group_key'], 'node_label': primary['name'] + ' ' + primary['thscode'],
                'sector_codes': [sector],
                'direction_sources': [{'thscode': sector, 'name': raw['sector_name'], 'family': family,
                    'source_kind': 'QUALIFIED_GROUP_PRIMARY' if raw['is_primary'] else 'QUALIFIED_GROUP_DRIVER',
                    'recorded_event_ids': direction['recorded_event_ids_latest_session']}],
                'company': business,
                'business_linkage_status': 'REVIEWED_BUSINESS_LINK_PRESENT' if business else 'UNKNOWN',
                'node_relation_note': 'CURRENT_MEMBERSHIP_AND_PRICE_ROUTING_ONLY_NOT_BENEFICIARY_PROOF',
                'review_question': 'Which public business evidence supports or contradicts this observed link?',
                'economic_coverage': None, 'breadth_leader': deepcopy(raw['retained_leader']),
                'discovery_origin': deepcopy(raw),
            })
            if raw['group_key'] not in order:
                order.append(raw['group_key'])
        issuers.append({'thscode': code, 'company_name': candidate['company_name'], 'origins': origins,
            'candidate_source': 'ALL_QUALIFIED_GROUP_RETAINED_LEADER_EXPLICIT_PAGE',
            'business_linkage_status': ('REVIEWED_BUSINESS_LINK_PRESENT' if any(o['company'] for o in origins)
                                        else 'UNKNOWN'), 'business_benefit_status': 'NOT_ESTABLISHED'})
    linked_codes = {s for i in issuers for o in i['origins'] if o['company'] for s in o['sector_codes']}
    body = {
        'version': stock.DISCOVERY_PAGE_VERSION, 'semantics': stock.MARKET_EXPRESSION_SEMANTICS,
        'policy': stock.DISCOVERY_PAGE_POLICY, 'observed_at': observed_at,
        'market_session': state.sessions[-1], 'market_state_hash': state.state_hash,
        'event_ledger_hash': ledger.ledger_hash, 'association_hash': association['projection_hash'],
        'company_links_hash': linked['projection_hash'], 'company_manifest': company_manifest,
        'directions': {c: directions[c] for c in sorted(directions)}, 'issuers': issuers, 'node_order': order,
        'evidence_scope_issuers': [{'thscode': i['thscode'], 'company_name': i['company_name']}
                                  for i in issuers if i['business_linkage_status'] == 'REVIEWED_BUSINESS_LINK_PRESENT'],
        'all_active_direction_count': sum(r['currently_gate_active'] for _, r in saved.values()),
        'active_directions_without_stock_business_scope': sorted(set(directions) - linked_codes),
        'recorded_sector_events_latest_session': context['recorded_events_latest_session'],
        'reviewed_company_coverage': SCOPE, 'reading_scope': SCOPE,
        'sector_result_hash': result['result_hash'], 'candidate_source_group_count': len(groups),
        'candidate_routing': {'semantics': ROUTING, 'page_plan': page, 'pool_coverage': pool['coverage'],
            'candidate_codes': page['selected_codes'], 'candidate_count': len(issuers),
            'business_evidence_is_candidate_gate': False},
        'maximum_request_count': page['maximum_request_count'],
        'stock_gate_is_unvalidated_shadow_policy': True, **stock.LIMITS,
    }
    body['plan_hash'] = canonical_hash(body)
    check_plan(body)
    return stock._plain(body)


def check_plan(plan):
    routing = plan['candidate_routing']
    page = routing['page_plan']
    codes = [i['thscode'] for i in plan['issuers']]
    directions = sorted({s for i in plan['issuers'] for o in i['origins'] for s in o['sector_codes']})
    partition = page['prior_page_codes'] + page['selected_codes'] + page['deferred_codes']
    if (routing['semantics'] != ROUTING or not stock._hash_ok(page, 'plan_hash')
            or page['version'] != 'stock-discovery-batch-plan-v1'
            or len(partition) != len(set(partition))
            or len(page['prior_page_codes']) != page['offset']
            or routing['candidate_codes'] != codes or codes != page['selected_codes']
            or routing['candidate_count'] != len(codes)
            or directions != sorted(plan['directions']) or directions != page['direction_codes']
            or plan['maximum_request_count'] != page['maximum_request_count']
            or str(plan['market_session']) != page['market_session']):
        raise ValueError('discovery page plan identity or partition differs')


def dispositions(result, selection, outcomes, *, projection_hash=None):
    page = selection_page(result, selection)
    pool = pool_source.build_stock_discovery_pool(result)
    by_code = {r['thscode']: r for r in outcomes}
    if (len(by_code) != len(outcomes) or (outcomes and list(by_code) != page['selected_codes'])
            or (projection_hash is not None and not re.fullmatch('[0-9a-f]{64}', projection_hash))):
        raise ValueError('discovery outcomes differ from the selected page')
    rows = []
    for candidate in pool['candidates']:
        code = candidate['thscode']
        if code in by_code:
            value = by_code[code]
            if value['company_name'] != candidate['company_name']:
                raise ValueError('discovery outcome company identity differs')
            status = value['status']
        elif code in page['prior_page_codes']:
            status = 'PRIOR_PAGE_EXECUTION_NOT_ASSERTED'
        elif code in page['deferred_codes']:
            status = 'DEFERRED_NOT_EXECUTED_BY_THIS_CAPTURE'
        else:
            status = 'SELECTED_NOT_COMPLETED_NO_SELECTION_CLAIM'
        rows.append({'thscode': code, 'company_name': candidate['company_name'], 'status': status})
    body = {'version': 'stock-discovery-page-dispositions-v1', 'pool_hash': pool['pool_hash'],
            'page_plan_hash': page['plan_hash'], 'market_session': pool['market_session'],
            'projection_hash': projection_hash, 'rows': rows,
            'total_pool_count': len(rows), 'selected_count': len(page['selected_codes']),
            'prior_count': len(page['prior_page_codes']), 'deferred_count': len(page['deferred_codes']),
            'meaning': 'ONE_CAPTURE_DISPOSITIONS_NOT_CROSS_RUN_PROGRESS_OR_RESEARCH',
            'automatic_next_page': False, **stock.LIMITS}
    body['dispositions_hash'] = canonical_hash(body)
    return stock._plain(body)


def validate_saved(request, capture, report, files):
    """Bind this new reader version to retained original selection and Sector bytes.

    The publisher does not claim a fresh price replay. Original capture.verify
    separately rebuilds the full plan and price results from recorded requests.
    """
    selection = json.loads(files['reading/inputs/discovery-page.json'])
    result = json.loads(files['reading/inputs/sector-result.json'])
    page = selection_page(result, selection)
    plan = json.loads(files['reading/plan.json'])
    p = report['projection']
    check_plan(plan)
    if (request.get('discovery_page') != selection or capture['version'] != CAPTURE_VERSION
            or plan['version'] != stock.DISCOVERY_PAGE_VERSION or not stock._hash_ok(plan, 'plan_hash')
            or plan['plan_hash'] != p['plan_hash'] or plan['plan_hash'] != capture['plan_hash']
            or plan['candidate_routing']['page_plan'] != page
            or plan['candidate_routing'] != p['candidate_routing']):
        raise ValueError('saved discovery page binding differs')
    pool = pool_source.build_stock_discovery_pool(result)
    if plan['candidate_routing']['pool_coverage'] != pool['coverage']:
        raise ValueError('saved discovery pool coverage differs')
    originals = {r['thscode']: r for r in pool['candidates']}
    if len(plan['issuers']) != len(p['all_stock_observations']):
        raise ValueError('saved discovery issuer coverage differs')
    for issuer, observed in zip(plan['issuers'], p['all_stock_observations'], strict=True):
        original = originals[issuer['thscode']]
        if (issuer['company_name'] != original['company_name']
                or [o['discovery_origin'] for o in issuer['origins']] != original['origins']
                or any(observed[k] != v for k, v in issuer.items())
                or any(o['sector_codes'] != [o['discovery_origin']['sector_thscode']]
                       for o in issuer['origins'])):
            raise ValueError('saved discovery original company or direction differs')
    outcomes = [{'thscode': r['thscode'], 'company_name': r['company_name'], 'status': r['status']}
                for r in p['all_stock_observations']]
    expected = dispositions(result, selection, outcomes, projection_hash=report['projection_hash'])
    if (capture['planned_issuer_outcomes'] != outcomes
            or json.loads(files['reading/discovery-dispositions.json']) != expected):
        raise ValueError('saved discovery dispositions differ')


def reading_notice(projection):
    page = projection['candidate_routing']['page_plan']
    e = lambda v: escape(str(v), quote=True)
    return (f'<section><h2>完整发现池与本批检查分开</h2><p>本批 {len(page["selected_codes"])} 家；'
            f'此前页 {len(page["prior_page_codes"])} 家的执行状态未由本次断言；'
            f'后续 {len(page["deferred_codes"])} 家本次未执行。不是全池检查完成。</p>'
            '<p>来源包含首页之外及细分驱动；当前方向不再满足既有强势条件时，不凭历史进入记录通过价格资格。'
            '完整逐公司处置见 discovery-dispositions.json。分页不是自动续跑许可，也不是Research。</p>'
            '<details><summary>未由本批执行的证券</summary><pre>'
            + e(stock.canonical_json({'prior_not_asserted': page['prior_page_codes'],
                                     'deferred_not_executed': page['deferred_codes']}))
            + '</pre></details></section>')
