"""Historical delivery identity regressions; synthetic dates, no network/dispatch."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from test_radar_delivery_reconciliation import module


def history():
    return {'unresolved_deliveries': [
        {'lane': 'sector', 'target': '2026-10-05',
         'first_seen': '2026-10-05T19:05:00+08:00', 'run_id': '100'},
        {'lane': 'stock', 'target': '101',
         'first_seen': '2026-10-05T19:05:00+08:00', 'run_id': '100'}]}


def success(market='2026-10-08', checked='2026-10-08T18:13:00+08:00'):
    return {'status': 'UP_TO_DATE', 'checked_at': '2026-10-08T19:05:00+08:00',
            'code_sha': 'a' * 40, 'reconciliation_run_id': '200',
            'market_session': market, 'sector_checked_at': checked,
            'stock_parent': '202', 'open_gap': False, 'action': None}


@pytest.mark.parametrize('market,checked', [
    ('2026-10-08', '2026-10-08T18:13:00+08:00'),
    ('2026-10-06', '2026-10-07T18:13:00+08:00'),
    ('2026-09-30', '2026-10-08T18:13:00+08:00'),
])
def test_other_day_success_preserves_original_delivery_identity(market, checked):
    previous, current = history(), success(market, checked)
    before = deepcopy((previous, current))
    out = module().retain_unresolved(previous, current)
    assert out['unresolved_deliveries'] == previous['unresolved_deliveries']
    assert out['open_gap'] and out['action'] is None
    assert (previous, current) == before
    repeated = module().retain_unresolved(out, current)
    assert repeated == out  # No duplicate or reset first-seen clock.


@pytest.mark.parametrize('market,checked,cleared', [
    ('2026-10-05', '2026-10-08T18:13:00+08:00', True),
    ('2026-09-30', '2026-10-05T07:30:00Z', True),
    ('2026-09-30', '2026-10-05T07:29:59Z', False),
    ('2026-10-05', None, False),
    (None, '2026-10-08T18:13:00+08:00', False),
])
def test_exact_market_date_or_same_local_day_after_cutoff_only(market, checked, cleared):
    out = module().retain_unresolved(history(), success(market, checked))
    remaining = {(x['lane'], x['target']) for x in out['unresolved_deliveries']}
    assert (('sector', '2026-10-05') not in remaining) is cleared
    assert ('stock', '101') in remaining
    assert out['open_gap']  # The independent Stock gap is not resolved.


def test_exact_stock_recovery_cannot_clear_older_sector_gap():
    out = module().retain_unresolved(history(), dict(success(), stock_parent='101'))
    assert out['unresolved_deliveries'] == history()['unresolved_deliveries'][:1]
    assert out['open_gap']


def test_existing_issue_writer_keeps_issue_open_and_preserves_history(monkeypatch):
    mod = module()
    previous = history()
    calls = []
    def command(args, **kwargs):
        calls.append((args, kwargs))
        if len(calls) == 1:
            assert args[-1] == 'repos/auguspp/decision-kernel/issues/581'
            body = '<!-- radar-continuity-status-v1 -->' + json.dumps(previous) + '<!-- /radar-continuity-status-v1 -->'
            return SimpleNamespace(stdout=json.dumps({'body': body}))
        assert '--method' in args and 'PATCH' in args and '/dispatches' not in ' '.join(args)
        payload = json.loads(kwargs['input'])
        assert payload['state'] == 'open'
        marker = payload['body'].split('<!-- radar-continuity-status-v1 -->')[1].split('<!-- /radar-continuity-status-v1 -->')[0]
        saved = json.loads(marker)
        assert saved['unresolved_deliveries'] == previous['unresolved_deliveries']
        assert saved['checked_at'] == success()['checked_at']
        return SimpleNamespace(stdout='')
    monkeypatch.setattr(mod.subprocess, 'run', command)
    out = mod.report_issue(success())
    assert len(calls) == 2 and out['open_gap']
