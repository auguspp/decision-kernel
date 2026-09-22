"""Regression for archive-only re-entry guidance; no acquisition or model calls."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import research_reentry_reading as r
from test_research_reentry_reading import NOW, CODE, add_watch, one, package, record


@pytest.mark.parametrize('watch_status', [None, 'PRICE_UNAVAILABLE_NOT_QUIET',
                                         'NEEDS_REVIEW_NOW', 'ACTIVE_ODDS_WATCH'])
@pytest.mark.parametrize('has_observation', [False, True])
def test_archive_body_recovery_precedes_observation_or_watch_guidance(watch_status, has_observation):
    row = {'assets': [], 'archives': [{'status': 'REGISTERED_LOCATOR_NOT_BODY_RECOVERED'}],
           'saved_observations': [{'kind': 'SAVED_RADAR_ORIGINS'}] if has_observation else [],
           'saved_watch': {'status': watch_status} if watch_status else None}
    before = deepcopy(row)
    assert r._next_step(row) == 'RECOVER_REGISTERED_ARCHIVE'
    assert row == before


@pytest.mark.parametrize('has_gap', [False, True])
def test_existing_method_review_and_source_gap_keep_their_priority(has_gap):
    row = {'assets': [{'use': 'METHOD_SUPPLEMENT', 'source_check': {'gaps': ['missing'] if has_gap else []}}],
           'archives': [{'status': 'REGISTERED_LOCATOR_NOT_BODY_RECOVERED'}],
           'saved_observations': [{'kind': 'SAVED_RADAR_ORIGINS'}],
           'saved_watch': {'status': 'NEEDS_REVIEW_NOW'}}
    expected = 'RECOVER_MISSING_RETAINED_BYTES' if has_gap else 'RECONCILE_EXISTING_METHOD_REVIEW'
    assert r._next_step(row) == expected


def test_real_registered_archive_and_synthetic_saved_observation_keep_both_visible():
    fixture = Path(__file__).parent / 'fixtures/reviewed_question_real/reading.json'
    old = json.loads(fixture.read_text())
    archives = [a for a in old['research']['on_demand_archives'] if a.get('case') == '300638.SZ']
    assert archives, 'The existing real archive fixture must remain available'
    files = {}
    projection = {'companies': [{'thscode': '300638.SZ', 'origins': [
        {'kind': 'SYNTHETIC_TEST', 'market_session': '2026-09-21'}]}],
        'generated_at': NOW, **m.AUTHORITY}
    radar = {'projection': projection, 'projection_hash': canonical_hash(projection)}
    path = 'details/radar/company-reading.json'; raw = m.json_bytes(radar); files[path] = raw
    baseline = package(on_demand_archives=archives, radar_discovery={
        'projection_hash': radar['projection_hash'], 'details': {'company_reading': r._meta(path, raw)}})
    before = deepcopy(baseline)
    report = r.build(baseline, files); row = one(report); page = r.render(report)
    assert not row['assets'] and row['archives'] and row['saved_observations']
    assert row['next_step'] == 'RECOVER_REGISTERED_ARCHIVE'
    assert '先按明确定位恢复旧研究正文' in page
    assert '原保存观察' in page and '只有定位，本页没有恢复正文' in page
    assert row['semantic_comparison'] == 'NOT_PERFORMED_BY_READING'
    assert report['projection']['new_attention_events'] == report['projection']['new_research_executions'] == 0
    assert baseline == before and r.build(baseline, files) == report


def test_available_research_keeps_existing_watch_review_route():
    files = {}; item = record(files); baseline = package([item]); add_watch(baseline, files)
    row = one(r.build(baseline, files))
    assert row['next_step'] == 'REVIEW_SAVED_PRICE_CONDITION_AND_RESEARCH_PREREQUISITES'
    assert row['saved_watch']['qualification'] == 'SAVED_TYPED_WATCH_NOT_REQUALIFIED_CURRENT_MARKET'


@pytest.mark.parametrize('unknowns', [['first unknown', '<script>x</script>[x](javascript:evil)'],
                                     'legacy scalar unknown', []])
def test_saved_unknowns_render_without_python_list_repr_or_acceptance_claim(unknowns):
    files = {}; item = record(files)
    saved = {'thscode': CODE, 'execution_id': 'synthetic-render-test',
             'question': 'original question', 'known_unknowns': unknowns,
             'terminal_reason': 'unchanged model reason', 'sources': {}, **m.AUTHORITY}
    path = 'details/research/reviewed-questions.json'
    raw = m.json_bytes({'question_work': {'items': [saved]}}); files[path] = raw
    baseline = package([item], reviewed_question_work={'structured': r._meta(path, raw)})
    report = r.build(baseline, files); before = deepcopy(report); page = r.render(report)
    assert '原模型停止理由（历史输出，不代表复核认可）' in page
    assert 'unchanged model reason' in page
    assert report == before and files[path] == raw
    assert '<script>' not in page and '[x](javascript:' not in page
    if isinstance(unknowns, list) and unknowns:
        assert '    - first unknown' in page and '&#91;&#x27;' not in page
    elif isinstance(unknowns, str):
        assert 'legacy scalar unknown' in page
    else:
        assert '原关键未知' not in page
