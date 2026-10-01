"""Bounded C2 workpaper over exact retained #375 data, never a detector/runtime.

Explicit invocation only. The selected baseline and Radar flags are not changed.
Future outcomes are attached after onset selection; all cohort results are
post-hoc diagnostics, not research usefulness, executable returns or acceptance.
"""
from collections import Counter, defaultdict
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
from statistics import median
import sys
import zipfile

from decision_kernel.identity import canonical_hash, canonical_json

ZIP_SHA = '4a357ef5973439c3bf17e5842a17e879e3ebe5452070e7aea8d2cf2baaaf3fb1'
STUDY_HASH = 'bbe1500b75db1b73254fac2d074ba96a9de65e5ef9b69603eacc7bbf4afd62a6'
FILES = {'study.json': (31759771, 'c59fde0ad9268e3c49ebc62e98b64601266fac15333a64c0becb45371737417e'),
         'execution.json': (738, 'aa29c3c8e07ca2292011605264d2f6322ef034705deea00a7788615b133d9441'),
         'summary.md': (1595, '05e1192fbba85bd8cb2b333c0db1912ba215bafd3e651ffcfd089d6b77b1f684')}
FAMILIES = {'BROAD_881': 90, 'GRANULAR_884': 230}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def load_source(path):
    """Reuse the predecessor's exact native ZIP/inner bytes/receipt bindings."""
    raw = Path(path).read_bytes()
    require(len(raw) == 4042845 and hashlib.sha256(raw).hexdigest() == ZIP_SHA, 'original ZIP identity')
    with zipfile.ZipFile(Path(path)) as z:
        require(len(z.namelist()) == len(FILES) and set(z.namelist()) == set(FILES), 'original inventory')
        require(z.testzip() is None, 'original CRC')
        blobs = {name: z.read(name) for name in FILES}
    for name, (size, digest) in FILES.items():
        require(len(blobs[name]) == size and hashlib.sha256(blobs[name]).hexdigest() == digest, 'original inner bytes')
    wrapper, receipt = json.loads(blobs['study.json']), json.loads(blobs['execution.json'])
    study = wrapper['study']
    require(canonical_hash(study) == wrapper['study_hash'] == STUDY_HASH, 'original study hash')
    require(canonical_hash({k: v for k, v in receipt.items() if k != 'receipt_hash'}) == receipt['receipt_hash'], 'receipt hash')
    require(receipt['study_hash'] == STUDY_HASH and receipt['workflow_run_id'] == 35070558913
            and receipt['workflow_run_attempt'] == 1, 'original execution')
    require(study['source_state_hash'] == receipt['expected_state_hash']
            and study['source_state_session'] == receipt['expected_market_session'], 'original source state')
    require(receipt['provider_requests'] == receipt['market_state_writes'] == 0, 'original effects')
    for key in ('research_authority', 'investment_authority', 'human_attention_authority'):
        require(receipt[key] == study[key] == 'NONE', 'authority')
    require(study['signal_transition_authority'] == 'NONE' and study['horizons'] == [5, 20, 60], 'study scope')
    require(study['row_count'] == len(study['rows']) == 21120 and study['signal_session_count'] == 66, 'original denominator')
    return wrapper, receipt


def signal_projection(rows):
    """Only stored at-signal fields; no outcome/target-session access here."""
    return [{k: row[k] for k in ('family', 'thscode', 'name', 'signal_session',
                                 'baseline_selected', 'radar_selected', 'signal_features')} for row in rows]


def episodes(signal_rows, sessions, family_sizes):
    """Baseline runs. Left-edge true is context, never an observed fresh onset."""
    require(sessions == sorted(set(sessions)) and len(sessions) > 0, 'session order')
    groups = defaultdict(list)
    keys = set()
    for row in signal_rows:
        key = row['family'], row['thscode'], row['signal_session']
        require(key not in keys and row['family'] in family_sizes, 'duplicate/foreign signal identity')
        require(type(row['baseline_selected']) is bool and type(row['radar_selected']) is bool, 'signal flag type')
        keys.add(key); groups[key[:2]].append(row)
    require(Counter(family for family, _ in groups) == Counter(family_sizes), 'family universe')
    result = []
    for (family, code), group in sorted(groups.items()):
        group.sort(key=lambda row: row['signal_session'])
        require([row['signal_session'] for row in group] == sessions, 'missing signal session')
        require(len({row['name'] for row in group}) == 1, 'name changed within frozen identity')
        start = None
        for i in range(len(group) + 1):
            selected = i < len(group) and group[i]['baseline_selected']
            if selected and start is None:
                start = i
            if start is not None and not selected:
                entry = next((j for j in range(start, i) if group[j]['radar_selected']), None)
                result.append({'family': family, 'thscode': code, 'name': group[start]['name'],
                    'onset': sessions[start], 'last_selected_session': sessions[i - 1],
                    'selected_sessions': i - start, 'left_censored': start == 0,
                    'right_censored': i == len(group),
                    'first_new_entry_in_same_run': sessions[entry] if entry is not None else None,
                    'wait_to_new_entry_sessions': entry - start if entry is not None else None,
                    'signal_features': group[start]['signal_features']})
                start = None
    return result


def onset_keys(signal_rows, sessions, family_sizes):
    return {(e['family'], e['thscode'], e['onset']) for e in episodes(signal_rows, sessions, family_sizes)
            if not e['left_censored']}


def decimal_summary(values):
    if not values:
        return {'count': 0, 'mean': None, 'median': None}
    with localcontext() as context:
        context.prec = 50
        values = [Decimal(str(value)) for value in values]
        require(all(v.is_finite() for v in values), 'nonfinite value')
        return {'count': len(values), 'mean': format(sum(values) / len(values), 'f'),
                'median': format(median(values), 'f')}


def outcome_summary(selected, by_key, horizon):
    values, pending = [], 0
    for e in selected:
        row = by_key[(e['family'], e['thscode'], e['onset'])]
        value = row['outcomes'][str(horizon)]
        if value['status'] == 'PENDING_HORIZON':
            require(value['metrics'] is None and value['target_session'] is None, 'pending is not zero')
            pending += 1
        else:
            require(value['status'] == 'EVALUATED' and value['target_session'] > e['onset'], 'outcome clock/status')
            values.append(Decimal(value['metrics']['excess_return']))
    summary = decimal_summary(values)
    return {'selected': len(selected), 'evaluated': len(values), 'pending': pending,
            'positive': sum(v > 0 for v in values), 'zero': sum(v == 0 for v in values),
            'negative': sum(v < 0 for v in values), 'mean_excess': summary['mean'], 'median_excess': summary['median']}


def summarize(rows, sessions, family_sizes):
    selected = episodes(signal_projection(rows), sessions, family_sizes)
    by_key = {(r['family'], r['thscode'], r['signal_session']): r for r in rows}
    result = {}
    for family in family_sizes:
        all_runs = [e for e in selected if e['family'] == family]
        fresh = [e for e in all_runs if not e['left_censored']]
        # Existing frozen production minimum is described, never modified or executed.
        for e in fresh:
            persistence = e['signal_features'].get('positive_20d_excess_persistence_sessions')
            require(type(persistence) is int and persistence >= 0, 'persistence unknown or invalid')
        early = [e for e in fresh if e['signal_features']['positive_20d_excess_persistence_sessions'] < 5]
        established = [e for e in fresh if e['signal_features']['positive_20d_excess_persistence_sessions'] >= 5]
        waits = [e['wait_to_new_entry_sessions'] for e in fresh if e['wait_to_new_entry_sessions'] is not None
                 and e['wait_to_new_entry_sessions'] > 0]
        timing = Counter('SAME_SESSION_ENTRY' if e['wait_to_new_entry_sessions'] == 0 else
            'LATER_ENTRY_IN_SAME_RUN' if e['wait_to_new_entry_sessions'] is not None else
            'RIGHT_CENSORED_NO_ENTRY' if e['right_censored'] else 'CLOSED_RUN_NO_NEW_ENTRY' for e in fresh)
        rank_order = Counter()
        for e in fresh:
            a = e['signal_features'].get('horizon_5_rating')
            b = e['signal_features'].get('horizon_20_rating')
            require(a is None or type(a) is int and 0 <= a <= 100, '5d rating')
            require(b is None or type(b) is int and 0 <= b <= 100, '20d rating')
            rank_order['UNKNOWN' if a is None or b is None else 'FIVE_GT_TWENTY' if a > b else
                       'FIVE_LT_TWENTY' if a < b else 'EQUAL'] += 1
        active_rows = sum(r['baseline_selected'] for r in rows if r['family'] == family)
        result[family] = {'identities': family_sizes[family], 'sector_sessions': family_sizes[family] * len(sessions),
            'baseline_selected_rows': active_rows, 'radar_new_entry_rows': sum(r['radar_selected'] for r in rows if r['family'] == family),
            'observed_baseline_runs': len(all_runs), 'left_censored_runs': len(all_runs) - len(fresh),
            'fresh_onsets': len(fresh), 'fresh_distinct_identities': len({e['thscode'] for e in fresh}),
            'fresh_right_censored_runs': sum(e['right_censored'] for e in fresh),
            'within_run_repeated_rows': active_rows - len(all_runs),
            'fresh_onset_timing': {k: timing[k] for k in ('SAME_SESSION_ENTRY', 'LATER_ENTRY_IN_SAME_RUN',
                                                        'CLOSED_RUN_NO_NEW_ENTRY', 'RIGHT_CENSORED_NO_ENTRY')},
            'matched_later_entry_wait_sessions': decimal_summary(waits),
            'onset_5d_vs_20d_rank_order': {k: rank_order[k] for k in ('FIVE_GT_TWENTY', 'FIVE_LT_TWENTY', 'EQUAL', 'UNKNOWN')},
            'fresh_under_five_persistence': len(early),
            'outcomes': {name: {str(h): outcome_summary(cohort, by_key, h) for h in (5, 20, 60)}
                         for name, cohort in [('fresh_onsets', fresh), ('under_five_persistence', early),
                                              ('at_least_five_persistence', established)]}}
        require(sum(timing.values()) == len(fresh) and sum(rank_order.values()) == len(fresh), 'cohort partition')
    return result, selected


def build(wrapper, receipt):
    study = wrapper['study']; rows = study['rows']
    sessions = sorted({row['signal_session'] for row in rows})
    summary, selected = summarize(rows, sessions, FAMILIES)
    require(sessions[0] == study['first_signal_session'] and sessions[-1] == study['last_signal_session'], 'source window')
    result = {'version': 'c2-baseline-episode-workpaper-v1', 'source_study_hash': STUDY_HASH,
        'source_generated_at': wrapper['generated_at'], 'source_execution_receipt_hash': receipt['receipt_hash'],
        'source_artifact': {'run_id': 35070558913, 'attempt': 1, 'id': 10435911881, 'zip_sha256': ZIP_SHA,
                            'expires_at': '2026-12-15T07:50:09Z', 'permanent_git_original': 'NOT_ESTABLISHED'},
        'window': {'first': sessions[0], 'last': sessions[-1], 'sessions': len(sessions), 'rows': len(rows)},
        'selection': 'EXISTING_BASELINE_FALSE_TO_TRUE_WITHIN_OBSERVED_WINDOW_NO_OUTCOME_INPUT',
        'timing': 'NEXT_NEW_ENTRY_INSIDE_SAME_CONTIGUOUS_BASELINE_RUN_NOT_FIRST_DISCOVERY_OR_ACTIVE_STATE',
        'interpretation': 'POST_HOC_FROZEN_COHORT_DIAGNOSTIC_NOT_PIT_UNIVERSE_EDGE_OR_INVESTMENT_BACKTEST',
        'attention': 'ROW_VERSUS_RUN_COUNTS_ONLY_NOT_MEASURED_HUMAN_EXPOSURE_OR_NOTIFICATION_COST',
        'rank_limit': 'ONLY_STORED_5D_20D_RATINGS_NO_60D_SIGNAL_RANK_OR_HISTORICAL_STOCK_MEMBERS',
        'outcome_limit': 'SOURCE_CLOSE_EXCESS_SIGN_PROXY_PENDING_NOT_ZERO_OVERLAPPING_WINDOWS_NOT_INDEPENDENT',
        'summary': summary, 'signal_changes': False, 'source_requests': 0, 'model_calls': 0,
        'investment_authority': 'NONE', 'full_c_acceptance': 'NOT_ESTABLISHED'}
    result['report_hash'] = canonical_hash(result)
    return result


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    require(len(args) == 2, 'usage: episode-calculation.py ORIGINAL_ZIP ABSENT_OUTPUT_DIRECTORY')
    wrapper, receipt = load_source(args[0]); report = build(wrapper, receipt)
    raw = (canonical_json(report) + '\n').encode()
    require(len(raw) <= 512 * 1024, 'bounded derived report')
    out = Path(args[1]); out.mkdir(parents=False, exist_ok=False)
    with (out / 'episode-summary.json').open('xb') as stream:
        stream.write(raw)
    print(report['report_hash'])


if __name__ == '__main__':
    main()
