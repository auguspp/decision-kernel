"""Display units, readable clocks and small-screen table preservation."""
from copy import deepcopy

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import concept_observation_map as view
from tests.test_concept_radar import Fixture, no_network, AT


def test_excess_uses_percentage_points_and_daily_uses_percent():
    value = view.build(Fixture().run())
    html = view.render(value)
    assert html.count('超额（百分点）') == 3 * len(value['projection']['groups'])
    assert '当日涨跌另用百分比' in html
    assert '%' in html
    assert '（北京时间）' in html and AT.strftime('%Y-%m-%d %H:') in html
    assert 'False' not in html and 'True' not in html


def test_left_censoring_is_explained_without_claiming_a_true_trend_start():
    value = view.build(Fixture().run())
    row = next(r for r in value['projection']['universe'] if r['path'])
    row['path']['positive_20d_excess_persistence_left_censored'] = True
    value['projection_hash'] = canonical_hash(value['projection'])
    html = view.render(value)
    assert '实际连续时长可能更长' in html
    assert '经济趋势起点' in html


def test_table_scroll_not_wrapped_security_codes_and_original_states_unchanged():
    value = view.build(Fixture().run()); before = deepcopy(value)
    html = view.render(value)
    assert 'min-width:760px' in html and 'white-space:nowrap' in html
    assert '.scroll{overflow:auto}' in html
    assert 'DEFERRED_NOT_ACQUIRED' not in html and '尚未取得' in html
    assert value == before


def test_mutating_returned_policy_does_not_change_the_module_contract():
    expected = deepcopy(view.POLICY)
    value = view.build(Fixture().run())
    try:
        value['projection']['policy']['page_size'] = 100
        assert view.POLICY == expected
    finally:
        # This also isolates an actual failure against the pre-fix implementation.
        view.POLICY.clear()
        view.POLICY.update(expected)
