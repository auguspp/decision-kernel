"""Saved outcome joins and publisher seam; synthetic, all source/network I/O denied."""
from copy import deepcopy
from decimal import Decimal
import json
import socket
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import d_auction_follow_through as outcome
from decision_kernel.runtime import d_auction_probe as probe
from decision_kernel.runtime import stock_market_inputs as prices
from test_d_auction_probe import capture, pool_row, TARGET, offline

AT = '2026-10-08T10:00:00+00:00'
BOUND = 128 * 1024 * 1024


def daily(rows):
    # A typed source-reader projection fixture; no assertion of actual trading.
    return {'version': prices.VERSION, 'source': prices.SOURCE, 'provenance': 'SYNTHETIC_TEST_ONLY',
        'market_session': TARGET, 'end_date': TARGET.replace('-', ''),
        'columns': prices.COLUMNS, 'cohort_denominator': len(rows),
        'rows': [[code, close, None, None, None, 3, 3, 3] for code, close in rows],
        'qualified_windows': {'5': 0, '20': 0, '60': 0},
        'observed_at': AT, 'received_through': AT, 'source_row_coverage': {'daily:'+TARGET.replace('-', ''): {
            'status': 'SOURCE_ROWS_READ', 'possibly_truncated': False, 'duplicate_symbols': []}}}


def mixed(tmp_path):
    pool = [pool_row('600001.SH'), pool_row('600002.SH'), pool_row('600003.SH'),
            pool_row('600004.SH'), pool_row('600005.SH', turnover='1'), pool_row(None)]
    rows = [[code, TARGET.replace('-', ''), price, '10'] for code, price in (
        ('600001.SH', '10.5'), ('600002.SH', '10.5'), ('600003.SH', '10.1'))]
    a, _, _ = capture(tmp_path, prior_rows=pool, auction_rows=rows)
    d = daily([('600001.SH', '11'), ('600002.SH', '10'), ('600003.SH', '10.1'),
               ('600004.SH', '10'), ('600005.SH', '10')])
    return a, d


def test_complete_cohort_positive_negative_zero_unmatched_and_unresolved(tmp_path):
    a, d = mixed(tmp_path); before = deepcopy((a, d))
    report = outcome.project(a, d)
    assert report['cohort_denominator'] == 6 and report['comparable'] == 3
    assert report['close_available'] == 5
    assert report['groups']['MATCHED']['denominator'] == 2
    assert report['groups']['MATCHED']['above_auction'] == report['groups']['MATCHED']['below_auction'] == 1
    assert report['groups']['NOT_MATCHED']['equal_to_auction'] == 1
    assert report['groups']['AUCTION_UNRESOLVED']['denominator'] == 1
    assert report['groups']['STATIC_EXCLUDED']['denominator'] == 1
    assert report['groups']['STATIC_UNRESOLVED']['denominator'] == 1
    assert report['rows'][-1][0] is None  # Null identities never join to each other.
    assert (a, d) == before
    assert all(row[:len(probe.ROW_COLUMNS)] == original for row, original in zip(report['rows'], a['rows']))
    assert report['new_source_requests'] == 0 and report['investment_authority'] == 'NONE'
    assert '零匹配不记为零收益' in outcome.render(report)


@pytest.mark.parametrize('bad', [None, True, False, 'NaN', 'Infinity', '-1', '0', {}, []])
def test_bad_close_is_local_and_no_factor_or_minute_prerequisite(tmp_path, bad):
    a, d = mixed(tmp_path); d['rows'][0][1] = bad
    report = outcome.project(a, d)
    assert report['cohort_denominator'] == 6 and report['comparable'] == 2
    assert report['rows'][0][-1] == 'CLOSE_VALUE_UNAVAILABLE_OR_CONFLICT'
    assert report['groups']['MATCHED']['denominator'] == 2
    assert all(v == 0 for v in d['qualified_windows'].values())


def test_zero_matches_is_not_a_zero_strategy_return(tmp_path):
    a, _, _ = capture(tmp_path, auction_rows=[['600001.SH', TARGET.replace('-', ''), '10.1', '10']])
    report = outcome.project(a, daily([('600001.SH', '9')]))
    assert report['groups']['MATCHED']['denominator'] == 0
    assert report['groups']['MATCHED']['median_change'] is None
    assert report['groups']['NOT_MATCHED']['below_auction'] == 1
    assert 'portfolio_return' not in report and 'win_rate' not in report


def test_missing_price_and_rounding_do_not_delete_or_invent_equal_prices(tmp_path):
    a, d = mixed(tmp_path)
    d['rows'] = d['rows'][:-1]; d['cohort_denominator'] -= 1
    d['rows'][2][1] = '10.100000000001'
    report = outcome.project(a, d)
    assert report['rows'][4][-1] == 'CLOSE_IDENTITY_NOT_RETURNED'
    assert report['groups']['NOT_MATCHED']['above_auction'] == 1
    assert report['groups']['NOT_MATCHED']['equal_to_auction'] == 0
    assert report['rows'][2][-2] == '0.000000000000'  # Display rounding is not equality.


@pytest.mark.parametrize('damage', ['other_date', 'other_source', 'provenance', 'duplicate_price',
    'wrong_price_count', 'wrong_cohort_count', 'duplicate_cohort', 'wrong_match_count'])
def test_identity_conflicts_rejected_not_silently_joined(tmp_path, damage):
    a, d = mixed(tmp_path)
    if damage == 'other_date': d['market_session'] = '2026-10-09'
    elif damage == 'other_source': d['source'] = 'ANOTHER_PROVIDER'
    elif damage == 'provenance': d['provenance'] = 'LIVE_TUSHARE_RELAY'
    elif damage == 'duplicate_price': d['rows'].append(d['rows'][0]); d['cohort_denominator'] += 1
    elif damage == 'wrong_price_count': d['cohort_denominator'] += 1
    elif damage == 'wrong_cohort_count': a['cohort_denominator'] += 1
    elif damage == 'duplicate_cohort': a['rows'][1][0] = a['rows'][0][0]
    elif damage == 'wrong_match_count': a['matched'] += 1
    with pytest.raises(ValueError): outcome.project(a, d)


def test_no_same_session_close_retains_all_rows(tmp_path):
    a, _ = mixed(tmp_path)
    report = outcome.project(a, None)
    assert report['cohort_denominator'] == 6 and report['comparable'] == 0
    assert report['groups']['MATCHED']['denominator'] == 2
    assert report['groups']['MATCHED']['median_change'] is None
    assert all(row[-1] == 'SAME_SESSION_CLOSE_NOT_RETAINED' for row in report['rows'])


def bound_collector(a, d):
    """Native-shaped verified-reader seam fixture, not a real source capture."""
    collector = SimpleNamespace(files={'README.md': b'ORIGINAL', 'daily-failure.json': b'ORIGINAL_FAILURE'},
                                code_commit='a'*40, api=SimpleNamespace(calls=0, max_calls=180))
    def denied(*args, **kwargs): raise AssertionError('outcome must not make API/source requests')
    collector.api.get = denied
    def retain(path, raw):
        if path in collector.files: assert collector.files[path] == raw
        collector.files[path] = raw
        return {'read_path': path, 'bytes': len(raw), 'sha256': model.sha256(raw),
                'git_blob': model.blob_sha(raw), 'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}
    collector.retain = retain
    descriptions = []
    for label, report in (('auction', a), ('daily', d)):
        report = deepcopy(report); report['provenance'] = 'LIVE_TUSHARE_RELAY'
        descriptions.append({'file': retain(label+'.json', prices.dumps(report)),
            'source_archive': {'meaning': 'SYNTHETIC_DESCRIPTOR_TEST_ONLY', 'artifact_id': len(descriptions)+1},
            'market_session': report['market_session'], 'status': report.get('status', 'TEST_ONLY'),
            'cohort_denominator': report['cohort_denominator'], 'qualified_windows': {'5':0,'20':0,'60':0},
            'publication_verification': 'REBUILT_FROM_RETAINED_RESPONSE_BYTES' if label == 'auction'
                                        else 'REBUILT_FROM_EXACT_RETAINED_RESPONSE_BYTES'})
    return collector, {'checks': {'finished_at': AT}}, *descriptions


def test_reader_uses_dated_close_with_zero_qualified_longer_windows(tmp_path):
    a, d = mixed(tmp_path); c, b, ad, dd = bound_collector(a, d)
    before = deepcopy((c.files, ad, dd)); result = outcome.read_saved(c, b, dd, ad, retained_limit=BOUND)
    assert result['status'] == 'SAVED_SAME_SESSION_OUTCOMES' and result['comparable'] == 3
    assert c.api.calls == 0 and all(c.files[k] == v for k, v in before[0].items())
    assert (ad, dd) == before[1:]
    report = json.loads(c.files[outcome.PATH])
    assert report['auction_file'] == ad['file'] and report['close_file'] == dd['file']
    assert report['auction_observed_at'] == a['observed_at']


def test_reader_keeps_latest_failure_and_separate_earlier_same_session_input(tmp_path):
    a, d = mixed(tmp_path); c, b, ad, dd = bound_collector(a, d)
    daily_result = {'status': 'LATEST_FAILURE', 'last_qualified_result': dd}
    result = outcome.read_saved(c, b, daily_result, ad, retained_limit=BOUND)
    assert result['comparable'] == 3
    report = json.loads(c.files[outcome.PATH])
    assert report['using_prior_daily'] and report['latest_daily_attempt_status'] == 'LATEST_FAILURE'
    assert daily_result['status'] == 'LATEST_FAILURE'


def test_reader_never_substitutes_next_day_or_queries_history(tmp_path):
    a, d = mixed(tmp_path); c, b, ad, dd = bound_collector(a, d)
    dd['market_session'] = '2026-10-09'
    result = outcome.read_saved(c, b, dd, ad, retained_limit=BOUND)
    assert result['status'] == 'SAME_SESSION_CLOSE_NOT_RETAINED' and result['comparable'] == 0
    report = json.loads(c.files[outcome.PATH])
    assert report['cohort_denominator'] == 6 and report['close_file'] is None and c.api.calls == 0


@pytest.mark.parametrize('damage', ['bytes', 'sha', 'blob', 'ref_rule', 'verification', 'future_clock', 'capacity', 'calls'])
def test_optional_failure_does_not_mutate_original_or_fallback_after_corruption(tmp_path, damage):
    a, d = mixed(tmp_path); c, b, ad, dd = bound_collector(a, d)
    dd['last_qualified_result'] = deepcopy(dd)
    if damage == 'bytes': dd['file']['bytes'] += 1
    elif damage == 'sha': dd['file']['sha256'] = '0'*64
    elif damage == 'blob': dd['file']['git_blob'] = '0'*40
    elif damage == 'ref_rule': dd['file']['read_ref_rule'] = 'READ_LATEST'
    elif damage == 'verification': dd['publication_verification'] = 'NOT_VERIFIED'
    elif damage == 'future_clock': b['checks']['finished_at'] = '2026-10-08T08:00:00Z'
    elif damage == 'calls': c.api.max_calls = 1
    before = deepcopy(c.files)
    result = outcome.read_saved(c, b, dd, ad, retained_limit=1 if damage == 'capacity' else BOUND)
    assert result['status'] == 'AUCTION_FOLLOW_THROUGH_READING_GAP'
    assert c.files == before and c.api.calls == 0 and 'file' not in result


def test_large_complete_cohort_is_not_trimmed_to_display_limit(tmp_path):
    pool = [pool_row(f'{600000+i:06}.SH') for i in range(2500)]
    values = [[r[1], TARGET.replace('-', ''), '10.5', '10'] for r in pool]
    a, _, _ = capture(tmp_path, prior_rows=pool, auction_rows=values)
    d = daily([(r[1], '9.000000000000') for r in pool])
    report = outcome.project(a, d)
    assert len(report['rows']) == report['cohort_denominator'] == 2500
    assert len(prices.dumps(report)) <= probe.MAX_REPORT
    assert report['groups']['MATCHED']['below_auction'] == a['matched']
