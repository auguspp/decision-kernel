"""Real retained company controls; mutations and check clocks are synthetic tests."""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path

import pytest

from decision_kernel.runtime import operating_outcomes as o
from decision_kernel.runtime import operating_outcome_reading as r
from test_operating_outcome_reading import fixture, LIMIT

ROOT = Path(__file__).resolve().parents[1]
AT = '2026-10-07T12:00:00Z'  # Synthetic test clock, not an observed publication.


def retained(subject='688337.SH'):
    config = json.loads((ROOT / r.CONFIG).read_bytes())
    entry = next(e for e in config['cases'] if e['subject'] == subject)
    return entry, {k: (ROOT / s['path']).read_bytes() for k, s in entry['sources'].items()}


def changed(entry, files, key, edit):
    entry, files = deepcopy(entry), dict(files)
    payload = o.loads(files[key]); edit(payload)
    raw = (json.dumps(payload, ensure_ascii=False, indent=2) + '\n').encode()
    files[key] = raw
    entry['sources'][key].update(bytes=len(raw), sha256=o.model.sha256(raw), git_blob=o.model.blob_sha(raw))
    return entry, files


def pair():
    entry, files = retained()
    row = o.review(entry, files, checked_at=AT)['rows'][0]
    return row['forecast'], row['actual']


def test_rigol_has_three_within_range_results_not_new_positive_surprises():
    entry, files = retained(); original = deepcopy(entry)
    report = o.review(entry, files, checked_at=AT)
    assert report['comparable_metrics'] == report['metric_count'] == 3
    assert [Decimal(row['comparison']['difference']) for row in report['rows']] == [
        Decimal('-2.54835510'), Decimal('-1.45536592'), Decimal('-0.92133068')]
    assert all(row['comparison']['range_position'] == 'WITHIN' for row in report['rows'])
    assert report['forecast_kind'] == 'POST_PERIOD_END_PREANNOUNCEMENT'
    assert report['company_guidance_events'] == 1 and report['independent_sample_count'] is None
    assert all(report[k] is None for k in ('ai_forecast_error', 'brier_score', 'win_rate', 'method_effectiveness'))
    assert all(row['forecast']['published_at'] is None and row['actual']['published_at'] is None
               for row in report['rows'])
    assert entry == original


def test_yto_keeps_missing_actual_metric_without_zero_or_partial_success_promotion():
    e, files = retained('600233.SH'); report = o.review(e, files, checked_at=AT)
    assert report['status'] == 'RETAINED_REVIEW_COMPARED'
    assert report['metric_count'] == report['comparable_metrics'] == 2
    assert report['event_id'] == '600233.SH:2026H1' and report['company_guidance_events'] == 1
    assert report['rows'][1]['actual']['value'] == '3122.5831'
    assert Decimal(report['rows'][1]['comparison']['difference']) == Decimal('-67.4169')
    assert all(row['comparison']['range_position'] == 'WITHIN' for row in report['rows'])
    assert report['publication_timing_qualification'] == 'NOT_ESTABLISHED_BY_DOCUMENT_DATES'
    assert report['ai_forecast_error'] is report['brier_score'] is None
    # The actual historical null stays on disk; a new observation does not backfill it.
    legacy = ROOT / 'docs/readings/d2-yto-preannouncement-2026-10-07/inputs.json'
    assert o.model.blob_sha(legacy.read_bytes()) == '7f536ad0cc6cad3e9bdbeead3f901391df02f12f'
    assert o.loads(legacy.read_bytes())['actual']['parent_net_profit_ex_nonrecurring'] is None
    # Explicit synthetic missing-value control still exercises the unchanged reader.
    e, files = changed(e, files, 'inputs',
                       lambda p: p['actual'].update(parent_net_profit_ex_nonrecurring=None))
    report = o.review(e, files, checked_at=AT)
    assert report['status'] == 'RETAINED_REVIEW_WITH_COMPARISON_GAPS'
    assert report['metric_count'] == 2 and report['comparable_metrics'] == 1
    first, missing = report['rows']
    assert Decimal(first['comparison']['difference']) == Decimal('-74.96011656')
    assert first['comparison']['range_position'] == 'WITHIN'
    assert missing['comparison']['status'] == 'VALUE_NOT_RETAINED'
    assert missing['actual']['value'] is None and missing['comparison']['difference'] is None
    text = o.render({'items': [report]})
    assert '未可比' in text and '期后预告不是期内前瞻预测' in text
    assert '不借归母填充' in text and '不是市场共识' in text


@pytest.mark.parametrize('side,key,value', [
    ('forecast', 'document_date', '2026-06-30'),
    ('forecast', 'document_date', '2026-08-26'),
    ('actual', 'document_date', '2026-07-05'),
    ('actual', 'document_date', '20260826'),
    ('actual', 'period_end', '2026-07-31'),
    ('forecast', 'published_at', '2026-07-06T00:00:00+08:00'),
    ('actual', 'clock_basis', 'PUBLISHED_AT'),
    ('actual', 'clock_timezone', 'UTC'),
    ('actual', 'retained_review_at', '2026-08-25T00:00:00Z'),
])
def test_document_clocks_cannot_be_exact_publication_or_out_of_order(side, key, value):
    f, a = pair(); (f if side == 'forecast' else a)[key] = value
    with pytest.raises(ValueError):
        o.compare_pair(f, a, checked_at=AT)


def test_document_date_boundary_uses_declared_timezone_but_still_waits_for_actual_retention():
    f, a = pair()
    before = o.compare_pair(f, a, checked_at='2026-08-25T15:59:59Z')
    same_local_date = o.compare_pair(f, a, checked_at='2026-08-25T16:00:00Z')
    assert before['status'] == 'RESULT_NOT_YET_MATURE_OR_PUBLISHED'
    assert same_local_date['status'] == 'REVIEW_NOT_YET_RETAINED_AT_CUTOFF'
    assert before['difference'] is same_local_date['difference'] is None


@pytest.mark.parametrize('field,value', [('subject', '600233.SH'), ('metric', 'parent_net_profit'),
                                        ('unit', 'CNY'), ('basis', 'HK_ADJUSTED'), ('period', '2026FY')])
def test_pair_identity_remains_metric_period_unit_and_subject_specific(field, value):
    f, a = pair(); a[field] = value
    out = o.compare_pair(f, a, checked_at=AT)
    assert out['status'] == 'INCOMPARABLE_BASIS' and out['difference'] is None


@pytest.mark.parametrize('field,value', [('value', 'NaN'), ('value', True), ('value', '1e6'), ('half_width', '-1')])
def test_new_layout_reuses_strict_decimal_number_contract(field, value):
    f, a = pair(); f[field] = value
    with pytest.raises(ValueError): o.compare_pair(f, a, checked_at=AT)


@pytest.mark.parametrize('key,value', [('revenue_mid', '480'), ('revenue_half_width', '10')])
def test_midpoint_and_range_must_reconcile_instead_of_inventing_an_expectation(key, value):
    e, files = retained(); e, files = changed(e, files, 'inputs', lambda p: p['guide'].update({key: value}))
    with pytest.raises(ValueError, match='midpoint'):
        o.review(e, files, checked_at=AT)


@pytest.mark.parametrize('edit', [
    lambda p: p.update(amount_unit='CNY_billion'),
    lambda p: p['actual'].update(subject='600233.SH'),
    lambda p: p['guide'].update(period_end='2026-06-29'),
    lambda p: p['actual'].update(document_date='2026-08-25'),
    lambda p: p['qualification'].update(new_human_decision=True),
    lambda p: p.update(metric_ids=['revenue', 'revenue']),
    lambda p: p.update(metric_ids=['arbitrary_formula']),
])
def test_selected_source_bindings_are_not_relaxed_for_preannouncements(edit):
    e, files = retained(); e, files = changed(e, files, 'inputs', edit)
    with pytest.raises(ValueError): o.review(e, files, checked_at=AT)


def test_source_custody_and_retained_event_cannot_be_relabelled():
    e, files = retained(); e['event_id'] += '-duplicate'
    with pytest.raises(ValueError): o.review(e, files, checked_at=AT)
    e, files = retained(); files['notes'] += b' '
    with pytest.raises(ValueError, match='bytes differ'): o.review(e, files, checked_at=AT)
    e, files = retained(); e['sources']['notes']['ref'] = 'b' * 40
    with pytest.raises(ValueError, match='splice'): o.review(e, files, checked_at=AT)


def test_exact_clock_legacy_cannot_silently_be_reinterpreted_as_document_dates():
    f, a = pair(); f.pop('clock_basis'); a.pop('clock_basis')
    f['published_at'] = '2026-07-06T00:00:00+08:00'; a['published_at'] = '2026-08-26T00:00:00+08:00'
    with pytest.raises(ValueError, match='explicit layout'): o.compare_pair(f, a, checked_at=AT)
    f.pop('document_date'); a.pop('document_date')
    with pytest.raises(ValueError, match='temporal'): o.compare_pair(f, a, checked_at=AT)


def test_repeated_reading_and_decimal_context_do_not_rebase_the_review():
    e, files = retained(); first = o.review(e, files, checked_at=AT)
    with localcontext() as ctx:
        ctx.prec = 4
        assert first == o.review(e, files, checked_at=AT)
    later = o.review(e, files, checked_at='2026-10-08T12:00:00Z')
    assert first['rows'] == later['rows'] and first['retained_review_at'] == later['retained_review_at']
    assert first['new_source_requests'] == later['model_calls'] == 0


def test_new_cases_use_existing_reader_and_local_gaps_do_not_remove_other_events():
    c, base, values = fixture(indices=(1, 2), at=AT)
    before = deepcopy(base); result = r.attach(c, base, retained_limit=LIMIT)
    report = o.loads(c.files[r.PATH])
    assert report['selected_events'] == 2 and report['compared_events'] == 2
    assert report['source_or_comparison_gap_events'] == 0
    assert report['items'][1]['rows'][1]['comparison']['status'] == 'COMPARABLE_RETAINED_VALUES'
    assert base == before and result['lanes'] == base['lanes'] and c.sources == {}
    assert len(c.reads) == 7 and report['ai_forecast_score'] is None
    for item in report['items']:
        for ref in item['retained_files'].values():
            assert o.model.sha256(c.files[ref['read_path']]) == ref['sha256']
    c, base, values = fixture(indices=(1, 2), at=AT)
    yto_input = next(v for p, v in values.items() if 'd2-yto-' in p and p.endswith('inputs.json'))
    del values[next(p for p in values if 'd2-yto-' in p and p.endswith('source-notes.json'))]
    r.attach(c, base, retained_limit=LIMIT); report = o.loads(c.files[r.PATH])
    assert report['items'][0]['status'] == 'RETAINED_REVIEW_COMPARED'
    assert report['items'][1]['status'] == 'RETAINED_OUTCOME_UNAVAILABLE_NOT_ECONOMIC_FAILURE'
    assert not any(o.model.blob_sha(yto_input) in p for p in c.files) and c.sources == {}


def test_production_selection_preserves_mu_and_delivers_all_three_event_dispositions():
    c, base, _ = fixture(indices=(0, 1, 2), at=AT)
    r.attach(c, base, retained_limit=LIMIT); report = o.loads(c.files[r.PATH])
    assert report['selected_events'] == 3 and report['compared_events'] == 3
    assert report['source_or_comparison_gap_events'] == 0
    assert [i['comparable_metrics'] for i in report['items']] == [4, 3, 2]
    assert sum(i['metric_count'] for i in report['items']) == 9
    assert [Decimal(row['comparison']['difference']) for row in report['items'][0]['rows']] == [
        Decimal('4229'), Decimal('1'), Decimal('918'), Decimal('2.42')]
    assert 'clock_basis' not in report['items'][0]
    assert report['independent_forecast_sample_count'] is None and report['pooled_score'] is None
