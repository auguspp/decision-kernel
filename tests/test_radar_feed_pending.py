from datetime import timedelta

from decision_kernel.runtime import radar_feed_intake as intake
from test_radar_feed_intake import AT, advance, item, offline


def test_seen_does_not_acknowledge_delivery_or_hide_blocked_pending_on_next_window():
    initial, _ = advance([])
    first, delta = advance([item(published='2026-09-04')], initial, AT + timedelta(minutes=1))
    assert intake.source_rows(first, delta)['status'] == 'SOURCE_EXPORT_BLOCKED'
    second, delta2 = advance([item(published='2026-09-04')], first, AT + timedelta(minutes=2))
    assert delta2['status'] == 'NO_NEW_FEED_VERSIONS'
    export = intake.source_rows(second, delta2)
    assert export['status'] == 'SOURCE_EXPORT_BLOCKED' and export['pending_versions'] == 1
    assert not export['delivery_acknowledged']


def test_ready_pending_reoffers_original_evidence_ids_not_new_retrieval_times():
    initial, _ = advance([])
    first, d1 = advance([item()], initial, AT + timedelta(minutes=1))
    second, d2 = advance([], first, AT + timedelta(minutes=2))
    e1, e2 = intake.source_rows(first, d1), intake.source_rows(second, d2)
    assert e1['sources'] == e2['sources'] and e2['pending_versions'] == 1
    assert d2['changes'] == [] and not e2['delivery_acknowledged']
