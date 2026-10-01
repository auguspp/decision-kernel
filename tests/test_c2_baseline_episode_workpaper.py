"""Small semantic controls for the active C2 workpaper; no source downloads."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'docs/readings/c2-baseline-episodes-2026-10-01/episode-calculation.py'
spec = importlib.util.spec_from_file_location('c2_episode_workpaper', PATH)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
DAYS = ['2026-06-12', '2026-06-15', '2026-06-16', '2026-06-17']


def rows(flags=(False, True, True, False), entries=(False, False, True, False), code='881001.TI'):
    return [{'family': 'BROAD_881', 'thscode': code, 'name': code, 'signal_session': day,
             'baseline_selected': flag, 'radar_selected': entry,
             'signal_features': {'positive_20d_excess_persistence_sessions': 1,
                                'horizon_5_rating': 80, 'horizon_20_rating': 90},
             'outcomes': {str(h): {'status': 'PENDING_HORIZON', 'metrics': None, 'target_session': None}
                          for h in (5, 20, 60)}}
            for day, flag, entry in zip(DAYS, flags, entries)]


def episodes(value):
    return c.episodes(c.signal_projection(value), DAYS, {'BROAD_881': 1})


def test_runs_not_daily_rows_and_trading_session_wait():
    e = episodes(rows())[0]
    assert e['onset'] == DAYS[1] and e['last_selected_session'] == DAYS[2]
    assert e['selected_sessions'] == 2 and e['wait_to_new_entry_sessions'] == 1
    assert not e['left_censored'] and not e['right_censored']
    v = rows((True, True, True, False), (False, True, False, False))
    assert episodes(v)[0]['wait_to_new_entry_sessions'] == 1  # Friday to Monday, not three.


def test_first_window_state_is_left_censored_not_fresh():
    v = rows((True, True, False, True), (False, False, False, True))
    assert episodes(v)[0]['left_censored']
    assert c.onset_keys(c.signal_projection(v), DAYS, {'BROAD_881': 1}) == {('BROAD_881', '881001.TI', DAYS[3])}


def test_end_of_window_is_censored_not_no_future_entry():
    v = rows((False, False, True, True), (False,) * 4)
    s, _ = c.summarize(v, DAYS, {'BROAD_881': 1})
    assert s['BROAD_881']['fresh_onset_timing']['RIGHT_CENSORED_NO_ENTRY'] == 1
    assert s['BROAD_881']['fresh_onset_timing']['CLOSED_RUN_NO_NEW_ENTRY'] == 0


def test_next_episode_entry_does_not_backfill_first_episode():
    v = rows((False, True, False, True), (False, False, False, True))
    es = episodes(v)
    assert es[0]['wait_to_new_entry_sessions'] is None
    assert es[1]['wait_to_new_entry_sessions'] == 0


def test_other_identity_entry_is_never_used():
    v = rows(entries=(False,) * 4) + rows(code='881002.TI')
    es = c.episodes(c.signal_projection(v), DAYS, {'BROAD_881': 2})
    assert es[0]['first_new_entry_in_same_run'] is None
    assert es[1]['first_new_entry_in_same_run'] == DAYS[2]


def test_outcomes_are_not_onset_inputs():
    v = rows(); changed = deepcopy(v)
    for row in changed:
        row['outcomes'] = object()  # Cannot accidentally inspect the results.
    assert c.signal_projection(v) == c.signal_projection(changed)
    assert episodes(v) == episodes(changed)


def test_observed_onsets_are_prefix_stable():
    v = rows((False, True, False, True), (False,) * 4)
    full = c.onset_keys(c.signal_projection(v), DAYS, {'BROAD_881': 1})
    for end in range(1, len(DAYS) + 1):
        prefix = c.onset_keys(c.signal_projection(v[:end]), DAYS[:end], {'BROAD_881': 1})
        assert prefix == {key for key in full if key[2] <= DAYS[end - 1]}


@pytest.mark.parametrize('change,match', [('duplicate', 'duplicate'), ('missing', 'missing signal session'),
                                         ('flag', 'signal flag type'), ('family', 'family universe')])
def test_incomplete_or_ambiguous_grid_is_not_silently_accepted(change, match):
    v = rows(); sizes = {'BROAD_881': 1}
    if change == 'duplicate': v.append(deepcopy(v[1]))
    if change == 'missing': v.pop(2)
    if change == 'flag': v[1]['baseline_selected'] = 'false'
    if change == 'family': sizes['BROAD_881'] = 2
    with pytest.raises(ValueError, match=match):
        c.episodes(c.signal_projection(v), DAYS, sizes)


def test_pending_remains_none_and_zero_is_not_negative():
    v = rows(); s, _ = c.summarize(v, DAYS, {'BROAD_881': 1})
    o = s['BROAD_881']['outcomes']['fresh_onsets']['20']
    assert o['pending'] == 1 and o['evaluated'] == 0 and o['mean_excess'] is None
    assert s['BROAD_881']['outcomes']['under_five_persistence']['20']['selected'] == 1
    assert s['BROAD_881']['outcomes']['at_least_five_persistence']['20']['selected'] == 0
    v[1]['outcomes']['5'] = {'status': 'EVALUATED', 'target_session': '2026-06-22', 'metrics': {'excess_return': '0'}}
    s, _ = c.summarize(v, DAYS, {'BROAD_881': 1})
    o = s['BROAD_881']['outcomes']['fresh_onsets']['5']
    assert (o['positive'], o['zero'], o['negative']) == (0, 1, 0)


def test_pending_cannot_smuggle_a_zero_result():
    v = rows(); v[1]['outcomes']['5']['metrics'] = {'excess_return': '0'}
    with pytest.raises(ValueError, match='pending is not zero'):
        c.summarize(v, DAYS, {'BROAD_881': 1})


def test_nonfinite_outcome_fails():
    with pytest.raises(ValueError, match='nonfinite'):
        c.decimal_summary(['NaN'])


def test_unknown_rank_not_zero_and_future_60d_return_not_signal_role():
    v = rows(); v[1]['signal_features']['horizon_5_rating'] = None
    s, _ = c.summarize(v, DAYS, {'BROAD_881': 1})
    assert s['BROAD_881']['onset_5d_vs_20d_rank_order']['UNKNOWN'] == 1
    v[1]['outcomes']['60'] = {'status': 'EVALUATED', 'target_session': '2026-09-14', 'metrics': {'excess_return': '1000'}}
    new, _ = c.summarize(v, DAYS, {'BROAD_881': 1})
    assert new['BROAD_881']['onset_5d_vs_20d_rank_order'] == s['BROAD_881']['onset_5d_vs_20d_rank_order']


def test_empty_numeric_cohort_has_no_invented_mean():
    assert c.decimal_summary([]) == {'count': 0, 'mean': None, 'median': None}
