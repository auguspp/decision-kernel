"""One bounded same-session detail batch over a replayed concept catalogue.

Reuse original history/member qualification and path maths. Never mutate the
primary source or manufacture a full-catalogue multiday result from one batch.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, time, timedelta
from decimal import Context, localcontext
from itertools import combinations

from decision_kernel.identity import canonical_hash
from . import concept_radar as source

VERSION = 'concept-detail-supplement-v1'
MAX_DETAILS = source.MAX_DETAILS
MAX_REQUESTS = 2 * MAX_DETAILS
AUTHORITY = {**source.AUTHORITY, 'automatic_dispatch': False, 'model_calls': 0,
             'research_priority_established': False}
POLICY = {'version': VERSION, 'order': 'EXACT_UNEXAMINED_CODE_NOT_DAILY_RETURN',
          'maximum_details': MAX_DETAILS, 'maximum_requests': MAX_REQUESTS,
          'base': 'ORIGINAL_CAPTURE_REPLAY_AND_SAME_COMPLETED_SESSION_REQUIRED',
          'retry_count': 0, 'next_batch': 'NOT_AUTOMATIC',
          'acceptance': 'ORIGINAL_SNAPSHOT_HISTORY_AND_CURRENT_MEMBERSHIP_RULES'}
require = source.require


def plan(report: dict, *, offset: int) -> dict:
    """Derive identities; neither caller-supplied stocks nor a price threshold."""
    source.render(report)  # Identity guard only; caller must replay the raw base.
    p = report['projection']
    codes = [r['thscode'] for r in p['concepts']]
    require(len(codes) == len(set(codes)) == p['catalog_count'] == p['snapshot_count'],
            'DETAIL_CATALOG_SCOPE_DIFFERS')
    attempted = set(p['detail_selected_codes'])
    require(attempted == {d['thscode'] for d in p['details']} and attempted <= set(codes),
            'DETAIL_BASE_SCOPE_DIFFERS')
    missing = sorted(set(codes) - attempted)
    require(type(offset) is int and 0 <= offset < len(missing)
            and offset % MAX_DETAILS == 0, 'DETAIL_OFFSET_REJECTED')
    selected = missing[offset:offset + MAX_DETAILS]
    value = {'version': VERSION, 'policy': deepcopy(POLICY),
        'base_projection_hash': report['projection_hash'],
        'base_catalog_hash': p['concept_catalog_hash'], 'market_session': p['market_session'],
        'offset': offset, 'selected_codes': selected, 'base_attempted_codes': sorted(attempted),
        'base_unexamined_codes': missing,
        'outside_this_batch': sorted(set(missing) - set(selected)),
        'next_offset': offset + len(selected) if offset + len(selected) < len(missing) else None,
        'outside_batch_meaning': 'NOT_EXECUTED_BY_THIS_BATCH; EARLIER_OFFSETS_NOT_ASSUMED_DONE',
        **AUTHORITY}
    return {'plan': value, 'plan_hash': canonical_hash(value)}


def _base_context(base_files, report):
    """Use only original, already replayed bytes; not embedded reconstructed bars."""
    p = report['projection']; refs = p['requests']
    def body(i):
        return source.decode(base_files[f'response-{i+1}.json'])
    calendar = source.normalize_hithink_calendar(body(0))
    day = source.session_date(p['market_session'])
    sessions = tuple(d for d in calendar if d <= day)[-source.SECTOR_RADAR_MAX_WINDOW_SESSIONS:]
    snapshots = {}
    for i, r in enumerate(refs):
        if r['path'] == source.probe.SNAPSHOT:
            batch = source.normalize_hithink_index_snapshot(body(i),
                requested_thscodes=r['params']['thscodes'].split(','))
            snapshots.update({s.thscode: s for s in batch.points})
    indexes = [i for i, r in enumerate(refs) if r['path'] == source.probe.HISTORY
               and r['params']['thscode'] == source.BENCHMARK]
    require(len(indexes) == 1, 'DETAIL_BASE_BENCHMARK_DIFFERS')
    i = indexes[0]
    benchmark = source._history(body(i), source.BENCHMARK, sessions,
        source._clock(refs[i]['received_at']), snapshots[source.BENCHMARK], compare_activity=False)
    members = {}
    for d in p['details']:
        if d['current_membership'] is not None:
            members[d['thscode']] = source.normalize_hithink_sector_membership(
                body(d['membership_request_index']), sector_thscode=d['thscode'], sector_name=d['name'])
    return sessions, snapshots, benchmark, members


def observe(request, *, base_files: dict, report: dict, selection: dict, started_at) -> dict:
    """Execute exactly the source-derived request plan; callback also serves replay."""
    require(selection == plan(report, offset=selection['plan']['offset']), 'DETAIL_PLAN_REBUILD_DIFFERS')
    with localcontext(Context(prec=28)):
        return _observe(request, base_files, report, selection, source._clock(started_at))


def _observe(request, base_files, report, selection, started):
    p = report['projection']; day = source.session_date(p['market_session'])
    local = started.astimezone(source.SHANGHAI_TZ)
    require(local.date() == day and local.time() >= time(15, 30)
            and source._clock(p['as_of']) <= started, 'DETAIL_SAME_SESSION_REQUIRED')
    sessions, snapshots, benchmark, old_members = _base_context(base_files, report)
    names = {r['thscode']: r['name'] for r in p['concepts']}
    refs, details, new_members = [], [], {}
    last = started

    def get(path, params):
        nonlocal last
        require(len(refs) < MAX_REQUESTS, 'DETAIL_REQUEST_BUDGET_REACHED')
        source._check_request(path, params)
        raw, requested, received = request(path, dict(params))
        requested, received = source._clock(requested), source._clock(received)
        require(last <= requested <= received <= started + timedelta(minutes=30)
            and received.astimezone(source.SHANGHAI_TZ).date() == day, 'DETAIL_RESPONSE_CLOCK_REJECTED')
        body = source.decode(raw)
        refs.append({'path': path, 'params': params, 'requested_at': requested, 'received_at': received,
                     'body_bytes': len(raw), 'body_sha256': source.hashlib.sha256(raw).hexdigest()})
        last = received
        require(type(body.get('code')) is int, 'DETAIL_BUSINESS_ENVELOPE_REJECTED')
        if body['code'] in {3001, 3002, 3004}:
            raise source._DetailUnavailable('DETAIL_PROVIDER_DATA_UNAVAILABLE')
        require(body['code'] == 0, 'DETAIL_PROVIDER_BUSINESS_REJECTED')
        source.probe._record({'path': path, 'params': params, 'requested_at': requested.isoformat(),
            'received_at': received.isoformat(), 'response': body}, path, params,
            lower=started, upper=received,
            ready_after=datetime.combine(day, time(15), tzinfo=source.SHANGHAI_TZ)
                if path == source.probe.MEMBERS else None)
        return body

    for code in selection['plan']['selected_codes']:
        row = {'thscode': code, 'name': names[code], 'path': None, 'current_membership': None,
               'history_status': 'NOT_ACQUIRED', 'membership_status': 'NOT_ACQUIRED', 'gaps': []}
        for kind, path, params in (
            ('history', source.probe.HISTORY, source._history_params(code, sessions)),
            ('membership', source.probe.MEMBERS, {'thscode': code})):
            try:
                body = get(path, params)
            except source._DetailUnavailable:
                row[kind + '_status'] = 'SOURCE_UNAVAILABLE'
                row['gaps'].append(kind.upper() + '_PROVIDER_DATA_UNAVAILABLE')
            else:
                try:
                    if kind == 'history':
                        series = source._history(body, code, sessions, last, snapshots[code])
                        row['path'] = source.probe._path_observation(code, series.points,
                            tuple(q.close for q in benchmark.points), sessions)
                        row['history_status'] = 'EXACT_WINDOW_CHECKED'
                    else:
                        member = source.normalize_hithink_sector_membership(body,
                            sector_thscode=code, sector_name=names[code])
                        new_members[code] = member
                        row['current_membership'] = asdict(member)
                        row['membership_status'] = 'CURRENT_MEMBERS_CHECKED_NOT_ECONOMIC_EXPOSURE'
                except (ValueError, TypeError, KeyError, RuntimeError, OverflowError, OSError):
                    row[kind + '_status'] = 'DATA_QUALIFICATION_REJECTED'
                    row['gaps'].append(kind.upper() + '_REJECTED_NOT_NO_TREND_OR_MEMBERS')
            row[kind + '_request_index'] = len(refs) - 1
        details.append(row)
    combined = {**old_members, **new_members}
    old_codes = {m.thscode for s in old_members.values() for m in s.members}
    companies = {}
    for code, membership in new_members.items():
        for member in membership.members:
            c = companies.setdefault(member.thscode, {'thscode': member.thscode, 'source_names': [],
                'origins': [], 'business_linkage': 'NOT_ESTABLISHED', 'pre_quick_execution': 'NOT_EXECUTED'})
            if member.name not in c['source_names']: c['source_names'].append(member.name)
            c['origins'].append({'concept_thscode': code, 'concept_name': names[code],
                'market_session': day, 'membership_hash': membership.constituent_set_hash,
                'membership_captured_at': membership.captured_at})
    overlaps = [asdict(source.calculate_current_membership_overlap(left=combined[a], right=combined[b]))
                for a, b in combinations(sorted(combined), 2) if a in new_members or b in new_members]
    value = {'version': VERSION, 'policy': deepcopy(POLICY), 'base_projection_hash': report['projection_hash'],
        'plan_hash': selection['plan_hash'], 'market_session': day,
        'started_at': started, 'as_of': last, 'base_observed_at': p['as_of'], 'requests': refs,
        'details': details, 'companies': [companies[c] for c in sorted(companies)], 'overlaps': overlaps,
        'coverage': {'batch_attempted': len(details), 'history_checked': sum(d['path'] is not None for d in details),
            'memberships_checked': len(new_members), 'detail_gaps': sum(bool(d['gaps']) for d in details),
            'new_member_union': len(companies), 'members_outside_original_details': len(set(companies) - old_codes),
            'original_member_union': len(old_codes), 'unselected_by_this_batch': len(selection['plan']['outside_this_batch']),
            'full_multiday_radar': False, 'member_breadth': 'NOT_ACQUIRED',
            'history_membership': 'NOT_ESTABLISHED', 'atomic_snapshot': False}, **AUTHORITY}
    return source._plain({'projection': value, 'projection_hash': canonical_hash(value)})
