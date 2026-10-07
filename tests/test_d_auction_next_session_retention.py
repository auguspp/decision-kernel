"""Synthetic same-date source regressions; no live prices, dispatch or outcomes."""
from copy import deepcopy

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import d_auction_next_session as n
from decision_kernel.runtime import stock_market_inputs as prices

AT = '2026-10-09T09:00:00+00:00'
CHECK = '2026-10-09T10:00:00+00:00'
LATER = '2026-10-10T10:00:00+00:00'
DAY = '2026-10-09'
CALENDAR = {DAY: True}


def seed():
    members = [{'symbol': '600001.SH', 'group': 'MATCHED'},
               {'symbol': '600002.SH', 'group': 'STATIC_EXCLUDED'}]
    return {'id': 'a'*64, 'market_session': '2026-10-08', 'members': members,
            'members_hash': canonical_hash(members), 'target_session': None,
            'calendar_prefix': [], 'auction_timeliness': 'SYNTHETIC_ONLY',
            'auction_origin': {'sha256': 'b'*64, 'read_path': 'auction.zip'}}


def source(rows, tag='c'):
    return {'source': prices.SOURCE, 'provenance': 'LIVE_TUSHARE_RELAY',
            'tables': {('daily', '20261009'): rows},
            'coverage': {'daily:20261009': {'returned_rows': len(rows)}},
            'received_through': AT,
            'archive': {'sha256': tag*64, 'read_path': tag+'-daily.zip'}}


def observe(previous, rows, *, tag='c', at=CHECK):
    return n.project(previous, CALENDAR, DAY, [source(rows, tag)], checked_at=at)


@pytest.mark.parametrize('row,field,status', [
    (None, 'open', 'QUOTE_NOT_RETAINED'),
    ({'close': '19'}, 'open', 'FIELD_NOT_RETURNED'),
    ({'open': '19'}, 'close', 'FIELD_NOT_RETURNED'),
    ({'open': None, 'close': '19'}, 'open', 'FIELD_NOT_RETURNED'),
    ({'open': 'NaN', 'close': '19'}, 'open', 'QUOTE_VALUE_INVALID'),
    ({'open': '19', 'close': '-1'}, 'close', 'QUOTE_VALUE_INVALID'),
])
def test_present_table_gap_retains_whole_previous_result(row, field, status):
    old = observe(seed(), {'600001.SH': {'open': '11', 'close': '10'}})
    before = deepcopy(old)
    candidate = {} if row is None else {'600001.SH': row}
    out = observe(old, candidate, tag='d', at=LATER)
    for key in ('rows', 'groups', 'quote_source', 'quote_received_through',
                'quote_row_coverage', 'result_hash', 'result_first_recorded_at',
                'status', 'price_basis', 'acquisition_timing', 'members_hash'):
        assert out[key] == old[key]
    assert old == before
    assert out['current_quote_gap'] == 'CURRENT_DATED_FIELDS_UNAVAILABLE_PRIOR_RESULT_RETAINED'
    assert out['observation'] == 'PREVIOUS_DATED_OBSERVATIONS_RETAINED'
    attempt = out['current_quote_attempt']
    assert attempt['source'] == source(candidate, 'd')['archive']
    assert attempt['received_through'] == AT
    assert {'symbol': '600001.SH', 'field': field, 'status': status} in attempt['unavailable_previously_observed_fields']


def test_gaining_another_security_does_not_splice_rows_or_erase_excluded_member():
    old = observe(seed(), {'600001.SH': {'open': '11', 'close': '10'}})
    swapped = observe(old, {'600002.SH': {'open': '21', 'close': '20'}}, tag='d', at=LATER)
    assert swapped['rows'] == old['rows'] and swapped['rows'][1][2:4] == [None, None]
    assert swapped['groups']['STATIC_EXCLUDED']['denominator'] == 1
    both = observe(old, {'600001.SH': {'open': '12', 'close': '13'},
                         '600002.SH': {'open': '21', 'close': '20'}}, tag='e', at=LATER)
    out = observe(both, {'600001.SH': {'open': '14', 'close': '15'}}, tag='f', at=LATER)
    assert out['rows'] == both['rows']
    assert {x['symbol'] for x in out['current_quote_attempt']['unavailable_previously_observed_fields']} == {'600002.SH'}


def test_first_partial_is_useful_and_complete_revision_updates_without_old_gap():
    old = observe(seed(), {'600001.SH': {'close': '10'}})
    assert old['rows'][0][2:4] == [None, '10'] and not old.get('current_quote_gap')
    kept = observe(old, {'600001.SH': {'open': '19'}}, tag='d', at=LATER)
    assert kept['rows'][0][2:4] == [None, '10']  # No cell-level fill-forward.
    new = observe(kept, {'600001.SH': {'open': '20', 'close': '21'}}, tag='e', at=LATER)
    assert new['rows'][0][2:4] == ['20', '21']
    assert new['quote_source']['sha256'] == 'e'*64
    assert new['result_first_recorded_at'] == LATER
    assert new['current_quote_gap'] is None and 'current_quote_attempt' not in new
    assert new['observation'] == 'DATED_OBSERVATIONS_UPDATED'


def test_later_absent_table_keeps_original_clock_and_clears_stale_attempt():
    old = observe(seed(), {'600001.SH': {'open': '11', 'close': '10'}})
    partial = observe(old, {}, tag='d', at=LATER)
    out = n.project(partial, CALENDAR, DAY, [], checked_at=LATER)
    assert out['rows'] == old['rows'] and out['result_first_recorded_at'] == CHECK
    assert out['current_quote_attempt'] is None
    assert out['current_quote_gap'] == 'TARGET_QUOTE_NOT_IN_CURRENT_SAVED_SOURCES'


@pytest.mark.parametrize('damage', ['foreign', 'future', 'prior-row-identity'])
def test_invalid_source_or_previous_identity_is_not_hidden_by_retention(damage):
    old = observe(seed(), {'600001.SH': {'open': '11', 'close': '10'}})
    candidate = source({}, 'd')
    if damage == 'foreign': candidate['source'] = 'FOREIGN'
    elif damage == 'future': candidate['received_through'] = '2099-01-01T00:00:00Z'
    else: old['rows'][0][0] = '600003.SH'
    with pytest.raises(ValueError):
        n.project(old, CALENDAR, DAY, [candidate], checked_at=LATER)


def test_previous_location_and_summary_distinguish_retained_from_new():
    old = observe(seed(), {'600001.SH': {'open': '11', 'close': '10'}})
    location = {'reading_commit': 'f'*40, 'file': {'read_path': n.PATH}}
    cohorts, archived = n.retain_cohorts({'cohorts': [old]}, None, location)
    out = observe(cohorts[0], {}, tag='d', at=LATER)
    assert not archived and out['quote_source']['reading_commit'] == 'f'*40
    assert 'read_path' not in out['quote_source']
    assert out['current_quote_attempt']['source']['read_path'] == 'd-daily.zip'
    text = n.render({'checked_at': LATER, 'latest_price_status': 'SYNTHETIC_GAP', 'cohorts': [out]})
    assert '保留整份旧观察' in text and '不是本次重新取得' in text and '未跨包拼接' in text


def test_original_collector_preserves_prior_source_with_injected_parsed_field_gap(tmp_path, monkeypatch):
    # Original full saved-archive/parser fixture; only the final parsed quote gap
    # is injected. This is not a new source acquisition or real future session.
    from test_d_auction_next_session import fixture_collector, R, LIMIT
    collector, baseline = fixture_collector(tmp_path, monkeypatch)
    first = n.attach(collector, baseline, retained_limit=LIMIT)
    raw = collector.files[n.PATH]; old = prices.loads(raw)['cohorts'][0]
    collector.files.pop(n.PATH)
    collector.previous, collector.previous_commit = first, R
    def read_prior(path, ref):
        assert (path, ref) == (n.PATH, R)
        return raw
    collector.api.file = read_prior
    original = n.read_price_parts
    def missing_field(files, report):
        calendar, tables, coverage = original(files, report)
        tables = deepcopy(tables)
        for (api, day), rows in tables.items():
            if api == 'daily':
                for row in rows.values(): row.pop('open', None)
        return calendar, tables, coverage
    monkeypatch.setattr(n, 'read_price_parts', missing_field)
    out = n.attach(collector, baseline, retained_limit=LIMIT)
    assert 'read_path' in out['research'][n.KEY]
    actual = prices.loads(collector.files[n.PATH])
    kept = actual['cohorts'][0]
    assert kept['rows'] == old['rows']
    assert kept['quote_source']['reading_commit'] == R
    assert kept['current_quote_attempt']['source']['read_path'] == 'sources/daily.zip'
    assert actual['new_source_requests'] == 0 and actual['investment_authority'] == 'NONE'
    assert '保留整份旧观察'.encode() in collector.files['README.md']
