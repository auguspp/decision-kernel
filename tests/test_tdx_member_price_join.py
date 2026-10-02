"""Offline cohort joins: synthetic coverage controls, no source acquisition."""
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
import socket

import pytest

from decision_kernel.runtime import tdx_member_price_join as m

BOARD = '880550.TDX'
A, B = '600001.SH', '000002.SZ'
# Deliberately synthetic daily sessions: these are not an exchange calendar.
DAYS = [(date(2098, 1, 1) + timedelta(days=i)).isoformat() for i in range(61)]


def price(code=A):
    return {'status': 'RECHECKED_RETAINED_RAW_PATH', 'reason': None,
            'windows': {str(n): {'base_session': DAYS[-n-1], 'end_session': DAYS[-1],
                'status': 'RAW_COMPARABLE', 'return': '0.1', 'reported_action_dates': []} for n in m.WINDOWS}}


def snapshots(complete=False):
    return {d: {BOARD: [A, B]} for d in (DAYS if complete else DAYS[-2:])}


def test_left_join_keeps_complete_denominator_and_does_not_rank(monkeypatch):
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: pytest.fail('network'))
    result = m.join(snapshots(), DAYS, {A, B}, {A: price()})[0]
    assert result['terminal_members'] == 2
    for w in result['windows']:
        assert len(w['rows']) == 2
        assert w['price_counts'] == {'QUOTE_ONLY_NO_RETAINED_PATH': 1, 'RAW_COMPARABLE': 1}
        assert len(w['available_member_observation_dates']) == 2
        assert len(w['missing_member_observation_dates']) == w['sessions'] - 1
        assert not w['all_terminal_members_price_comparable']
        assert not w['date_labeled_member_and_price_complete']
        assert 'rank' not in w and 'role' not in w


def test_complete_dates_and_prices_are_separate_positive_controls():
    only_prices = m.join(snapshots(), DAYS, {A, B}, {A: price(), B: price()})[0]
    only_dates = m.join(snapshots(True), DAYS, {A, B}, {A: price()})[0]
    complete = m.join(snapshots(True), DAYS, {A, B}, {A: price(), B: price()})[0]
    assert all(w['all_terminal_members_price_comparable'] for w in only_prices['windows'])
    assert not any(w['date_labeled_member_and_price_complete'] for w in only_prices['windows'])
    assert not any(w['date_labeled_member_and_price_complete'] for w in only_dates['windows'])
    assert all(w['date_labeled_member_and_price_complete'] for w in complete['windows'])


def test_reported_action_does_not_erase_other_windows_or_promote_peer():
    a = price(); a['windows']['60'].update(status='RAW_WINDOW_UNAVAILABLE', return_=None)
    del a['windows']['60']['return_']; a['windows']['60']['return'] = None
    a['windows']['60']['reported_action_dates'] = [DAYS[10]]
    result = m.join(snapshots(True), DAYS, {A, B}, {A: a, B: price()})[0]['windows']
    assert [w['date_labeled_member_and_price_complete'] for w in result] == [True, True, False]
    assert result[2]['rows'][0]['raw_return'] is not None  # lexical B precedes A
    assert result[2]['rows'][1]['reported_action_dates'] == [DAYS[10]]


def test_observed_nonmember_is_not_an_effective_entry_date():
    s = snapshots(True); s[DAYS[-2]][BOARD] = [B]
    result = m.join(s, DAYS, {A, B}, {A: price(), B: price()})[0]
    for w in result['windows']:
        assert not w['missing_member_observation_dates']
        a = next(r for r in w['rows'] if r['code'] == A)
        assert a['observed_nonmember_dates'] == [DAYS[-2]]
        assert not w['date_labeled_member_and_price_complete']
        assert 'effective_entry_date' not in a


def test_removed_member_is_explicit_outside_terminal_estimand():
    s = snapshots(); s[DAYS[-2]][BOARD].append('300003.SZ')
    result = m.join(s, DAYS, {A, B}, {})[0]
    assert result['observed_nonterminal_members'] == ['300003.SZ']
    assert result['terminal_members'] == 2


def test_failure_unchecked_and_missing_snapshot_remain_distinct():
    failed = {'status': 'RETAINED_INPUT_GAP', 'reason': 'PROVIDER_BUSINESS_REQUEST_FAILED', 'windows': {}}
    r = m.join(snapshots(), DAYS, {A}, {A: failed})[0]['windows'][0]
    assert r['price_counts'] == {'NOT_IN_PRICE_INPUT': 1, 'RETAINED_INPUT_GAP': 1}
    assert all(x['raw_return'] is None for x in r['rows'])
    assert next(x for x in r['rows'] if x['code'] == A)['price_gap'] == failed['reason']


@pytest.mark.parametrize('change', ['date', 'security', 'duplicate', 'future', 'missing_terminal', 'calendar'])
def test_identity_date_and_denominator_errors_rejected(change):
    s, days = snapshots(), list(DAYS)
    if change == 'date': s['not-a-date'] = s.pop(DAYS[-2])
    elif change == 'security': s[DAYS[-1]][BOARD][0] = '600001'
    elif change == 'duplicate': s[DAYS[-1]][BOARD].append(A)
    elif change == 'future': s['2099-01-01'] = {BOARD: [A]}
    elif change == 'missing_terminal': s.pop(DAYS[-1])
    else: days[-2] = days[-1]
    with pytest.raises((ValueError, TypeError)): m.join(s, days, {A, B}, {})


@pytest.mark.parametrize('change', ['end', 'base', 'unknown', 'missing', 'nan', 'false_raw', 'negative_one'])
def test_price_windows_cannot_be_relabelled_or_filled(change):
    p = price(); w = p['windows']['5']
    if change == 'end': w['end_session'] = DAYS[-2]
    elif change == 'base': w['base_session'] = DAYS[-5]
    elif change == 'unknown': w['status'] = 'ACCEPTED'
    elif change == 'missing': p['windows'].pop('60')
    elif change == 'nan': w['return'] = 'NaN'
    elif change == 'false_raw': w['return'] = None
    else: w['return'] = '-1'
    with pytest.raises(ValueError): m.join(snapshots(), DAYS, {A, B}, {A: p})


def test_failed_input_cannot_supply_prices():
    p = price(); p.update(status='RETAINED_INPUT_GAP', reason='unknown')
    with pytest.raises(ValueError): m.join(snapshots(), DAYS, {A, B}, {A: p})


def test_missing_board_on_observed_day_is_not_known_empty_board():
    s = snapshots(); s[DAYS[-2]] = {}
    r = m.join(s, DAYS, {A, B}, {})[0]['windows'][0]
    assert r['available_member_observation_dates'] == [DAYS[-1]]
    assert not any(x['observed_nonmember_dates'] for x in r['rows'])


def test_known_empty_board_is_not_a_missing_observation():
    s = snapshots(); s[DAYS[-2]][BOARD] = []
    r = m.join(s, DAYS, {A, B}, {})[0]['windows'][0]
    assert r['available_member_observation_dates'] == DAYS[-2:]
    assert all(x['observed_nonmember_dates'] == [DAYS[-2]] for x in r['rows'])


def test_source_run_requires_same_manual_first_success():
    r = {'id': 123, 'head_sha': 'a'*40, 'path': 'expected', 'head_branch': 'main',
         'event': 'workflow_dispatch', 'run_attempt': 1, 'status': 'completed', 'conclusion': 'success'}
    m._run(r, 'expected')
    for key, bad in [('run_attempt', 2), ('event', 'pull_request'), ('head_branch', 'feature'),
                     ('path', 'other'), ('conclusion', 'failure')]:
        with pytest.raises(ValueError): m._run({**r, key: bad}, 'expected')


def test_original_create_only_writer_refuses_replacement(tmp_path):
    output = tmp_path/'join'
    m._publish_report_files(output, {'join.json': b'{}\n', 'join.md': b'SYNTHETIC\n'})
    with pytest.raises(FileExistsError):
        m._publish_report_files(output, {'join.json': b'{}\n', 'join.md': b'changed\n'})
    assert (output/'join.md').read_bytes() == b'SYNTHETIC\n'


def test_inputs_not_mutated_by_join():
    s, p = snapshots(), {A: price()}; before = deepcopy((s, p))
    m.join(s, DAYS, {A, B}, p)
    assert (s, p) == before
