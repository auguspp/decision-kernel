"""Use-specific price reading over the original capture/replay; no live sources."""
from copy import deepcopy
from decimal import Context, localcontext, ROUND_DOWN
import json

import pytest

from decision_kernel.runtime import independent_stock_reading as reading
from decision_kernel.runtime import tushare_c2_price_check as price
from test_tushare_c2_price_check import (
    sample, gap_original, run_capture, gap_attempt, saved_consumer_fixture, identity,
)


def interpret(root):
    proof = price.verify(root, expected_identity=identity())
    files = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    before = deepcopy(files)
    result = reading._interval_performance(files, price.raw_json(files['report.json']), proof)
    assert files == before
    return result


@pytest.mark.parametrize('index', [1, 2])
def test_interior_price_or_factor_gap_does_not_erase_interval(tmp_path, sample, index):
    def change(i, obj):
        if i == index: obj['data']['items'].pop(10)
    root, _, old, _ = run_capture(tmp_path, sample, change=change)
    assert old['qualified_windows'] == {'5': 2, '20': 1, '60': 1}
    result = interpret(root)
    assert result['qualified_windows'] == {'5': 2, '20': 2, '60': 2}
    assert result['legacy_full_window_qualified'] == old['qualified_windows']
    assert result['observations'][0]['windows']['20']['price_change'] == '1'
    assert json.loads((root/'report.json').read_bytes()) == old


@pytest.mark.parametrize('damage', ['zero-volume', 'missing-base', 'bad-factor', 'end-mismatch'])
def test_only_needed_values_gate_the_interval(tmp_path, sample, damage):
    def change(i, obj):
        if damage == 'zero-volume' and i == 1:
            obj['data']['items'][0][obj['data']['fields'].index('vol')] = '0'
        if damage == 'missing-base' and i == 2: obj['data']['items'].pop()
        if damage == 'bad-factor' and i == 2: obj['data']['items'][0][-1] = 'NaN'
        if damage == 'end-mismatch' and i == 1:
            obj['data']['items'][0][obj['data']['fields'].index('close')] = '21'
    root, _, old, _ = run_capture(tmp_path, sample, change=change)
    result = interpret(root)
    want = {'5': 2, '20': 2, '60': 2} if damage == 'zero-volume' else (
        {'5': 2, '20': 2, '60': 1} if damage == 'missing-base' else {'5': 1, '20': 1, '60': 1})
    assert result['qualified_windows'] == want
    assert result['legacy_full_window_qualified'] == old['qualified_windows']
    assert result['cohort_denominator'] == 2 and result['new_source_requests'] == 0
    assert result['pit_knowledge'] == 'NOT_ESTABLISHED' and result['role_inference'] == 'NOT_GRANTED'


@pytest.mark.parametrize('repair', [False, True])
def test_existing_saved_consumer_exposes_intervals_and_retains_failure(tmp_path, gap_original, repair):
    gap = gap_attempt(tmp_path, gap_original, fail=None if repair else 1)
    reader, collector, observation, _, fetched = saved_consumer_fixture(tmp_path, gap_original, gap=gap)
    before = deepcopy(observation)
    out = reader.saved_tushare_comparison(collector, observation, '2026-10-03T05:00:00Z')
    result = out['interval_performance']
    assert result['qualified_windows'] == {'5': 16, '20': 16, '60': 16 if repair else 0}
    assert out['qualified_windows'] == {'5': 16, '20': 16 if repair else 0, '60': 16 if repair else 0}
    assert result['source_report_sha256'] == out['verification']['report_sha256']
    assert result['source_stop'] == out['source_stop'] == (None if repair else 'AUTH_OR_ENTITLEMENT')
    assert before == observation and fetched == [1234]
    text = reading.render_intervals(result)
    assert all(code in text for code in gap_original[1]['symbols'])
    assert '| 证券 | 5日 | 20日 | 60日 |' in text and '原完整逐日检查' in text
    assert '不可比' in text and '不是总回报' in text


def test_intervals_keep_original_numeric_checks_and_fixed_decimal_context(tmp_path, sample):
    def change(i, obj):
        if i == 1: obj['data']['items'][-1][obj['data']['fields'].index('close')] = '13'
    root, _, _, _ = run_capture(tmp_path, sample, change=change)
    proof = price.verify(root)
    files = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    original = price.raw_json(files['report.json'])
    expected = reading._interval_performance(files, original, proof)
    expected_text = reading.render_intervals(expected)
    with localcontext(Context(prec=7, rounding=ROUND_DOWN)):
        assert reading._interval_performance(files, original, proof) == expected
        assert reading.render_intervals(expected) == expected_text
    assert expected['observations'][0]['windows']['60']['price_change'] == '0.538461538461538461538461538'
