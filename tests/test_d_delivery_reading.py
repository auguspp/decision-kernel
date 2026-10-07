"""Joint consumer uses native root/reserve; producer values here are synthetic."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import d_delivery_reading as joint

AT = '2026-10-06T08:00:00Z'
CODE = 'a' * 40
LIMIT = 4 * 1024 * 1024


def seal(value, field='report_hash'):
    value[field] = canonical_hash({k: v for k, v in value.items() if k != field})
    return value


def fixture():
    values = {
        'horizons': {'cases': [{'id': 'case-a', 'symbol': '603986.SH',
            'frozen_at': '2026-10-04T01:03:53Z', 'long_research_deadline': '2027-09-02',
            'analyst_review_by': '2026-11-30', 'opportunity_established': None,
            'opportunity_probability': None, 'economic_result': 'NOT_ADJUDICATED',
            'retained_interpretation': {'intermediate': 'synthetic hypothesis', 'invalidation': 'synthetic counterevidence'},
            'historical_price_context': {'market_session': '2026-09-30', 'meaning': 'BACKWARD_ONLY'},
            'checkpoints': [{'period': 5, 'status': 'WAITING_FOR_COMPLETED_SESSION',
                            'anchor_session': None, 'target_session': None, 'change': None}]}],
            'economic_continuations': [{'case_id': 'case-a', 'excerpts': ['support', 'counterevidence', 'unknown']}],
            'latest_price_status': 'AVAILABLE_WITH_GAPS'},
        'outcomes': {'items': [{'event_id': 'MU:FQ4_2026', 'subject': 'MU',
            'status': 'RETAINED_REVIEW_COMPARED', 'comparator_role': 'COMPANY_GUIDANCE_NOT_CONSENSUS_OR_AI_FORECAST',
            'rows': [{'label': '经营费用', 'comparison': {'status': 'COMPARABLE_RETAINED_VALUES',
                      'difference': '918', 'unit': 'USD_million'}}],
            'excerpts': ['expense pressure', 'not AI forecast'], 'source_acquisition_limits': {'raw_obtained': False}}],
            'selected_events': 1, 'compared_events': 1, 'independent_forecast_sample_count': None,
            'ai_forecast_score': None, 'pooled_score': None, 'method_effectiveness': None},
        'structure': {'subject': '000300.SH', 'reading_status': 'SAME_INPUT_REUSED',
            'algorithm': {'package': 'czsc', 'version': '1.0.1'},
            'source': {'subject_type': 'BENCHMARK_INDEX_NOT_STOCK_COHORT'},
            'observed_delta': {'status': 'UNCHANGED_INPUT_NOT_NEW_MARKET_EVENT'}},
        'auction': {'cohorts': [{'id': 'cohort-a', 'market_session': '2026-09-30',
            'status': 'WAITING_FOR_NEXT_COMPLETED_SESSION', 'target_session': None,
            'auction_timeliness': 'HISTORICAL_OR_LATE_NOT_PREOPEN_DISCOVERY',
            'groups': {'MATCHED': {'denominator': 0}, 'NOT_MATCHED': {'denominator': 12}}}],
            'archived_cohorts': [{'id': 'old-cohort', 'status': 'SOURCE_GAP'}],
            'cross_session_return': 'NOT_COMPUTED_RAW_DATED_OBSERVATIONS_ONLY'},
    }
    research = {'handoffs': {'active': []}, 'records': [{'id': 'original-human'}]}
    files = {'README.md': b'Original reading\n'}
    for kind, key, path, version, _ in joint.COMPONENTS:
        value = seal({**values[kind], 'version': version, 'code_commit': CODE,
                      'checked_at': AT, **model.AUTHORITY})
        raw = (canonical_json(value) + '\n').encode(); files[path] = raw
        research[key] = descriptor(path, raw)
    base = model.assemble(code_commit=CODE, checked_at=AT, check_started_at=AT,
        lanes={'stock': {'gaps': ['original price failure']}}, research=research,
        capabilities=[], refresh_identity={})
    files['current-state.json'] = model.read_package_bytes(base)
    c = SimpleNamespace(code_commit=CODE, files=files, now=lambda: AT,
        api=SimpleNamespace(calls=0, max_calls=180), sources={('keep', CODE): (b'keep', {})})
    return c, base


def descriptor(path, raw):
    return {'read_path': path, 'bytes': len(raw), 'sha256': model.sha256(raw),
            'git_blob': model.blob_sha(raw), 'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}


def replace_report(c, base, kind, change):
    spec = next(s for s in joint.COMPONENTS if s[0] == kind)
    value = json.loads(c.files[spec[2]]); change(value); seal(value)
    raw = (canonical_json(value) + '\n').encode(); c.files[spec[2]] = raw
    base['research'][spec[1]] = descriptor(spec[2], raw); seal(base, 'reading_hash')


def test_joint_reading_preserves_semantics_counterevidence_and_distinct_subjects():
    c, base = fixture(); old = deepcopy(base); files = dict(c.files); sources = dict(c.sources)
    result = joint.attach(c, base, retained_limit=LIMIT); model.validate_read_package(result)
    report = json.loads(c.files[joint.PATH]); model.sealed(report, 'report_hash')
    items = {i['kind']: i for i in report['components']}
    assert all(i['status'] == 'VERIFIED_SAME_READING_COMPONENT' for i in items.values())
    case = items['horizons']['data']['cases'][0]
    assert case['opportunity_established'] is None and case['checkpoints'][0]['change'] is None
    assert case['historical_price_context']['market_session'] == '2026-09-30'
    assert items['horizons']['data']['economic_continuations'][0]['excerpts'] == ['support', 'counterevidence', 'unknown']
    assert items['outcomes']['data']['items'][0]['subject'] == 'MU' and case['symbol'] == '603986.SH'
    assert items['outcomes']['data']['independent_forecast_sample_count'] is None
    assert items['outcomes']['data']['items'][0]['source_acquisition_limits']['raw_obtained'] is False
    assert items['auction']['data']['cohorts'][0]['groups']['MATCHED']['denominator'] == 0
    assert items['auction']['data']['archived_cohorts'][0]['status'] == 'SOURCE_GAP'
    assert report['cross_subject_outcome_join'] == 'NOT_PERFORMED' and report['pooled_score'] is None
    assert c.api.calls == 0 and c.sources == sources and base == old and result['lanes'] == base['lanes']
    assert all(c.files[p] == raw for p, raw in files.items() if p not in ('README.md', 'current-state.json'))
    assert '经营费用' in c.files['README.md'].decode() and '918 USD' in c.files['README.md'].decode()
    assert joint.attach(c, result, retained_limit=LIMIT) is result
    assert c.files['README.md'].count('## D：经济假设'.encode()) == 1


@pytest.mark.parametrize('change', ['raw', 'version', 'code', 'authority', 'future', 'shape', 'sealed'])
def test_one_broken_component_does_not_suppress_other_components(change):
    c, base = fixture(); path = joint.COMPONENTS[0][2]
    if change == 'raw':
        c.files[path] += b' '
    elif change == 'sealed':
        value = json.loads(c.files[path]); value['report_hash'] = '0' * 64
        raw = json.dumps(value).encode(); c.files[path] = raw
        base['research'][joint.COMPONENTS[0][1]] = descriptor(path, raw); seal(base, 'reading_hash')
    else:
        def modify(value):
            if change == 'version': value['version'] = 'unknown'
            if change == 'code': value['code_commit'] = 'b' * 40
            if change == 'authority': value['investment_authority'] = 'YES'
            if change == 'future': value['checked_at'] = '2026-10-07T08:00:00Z'
            if change == 'shape': value['cases'] = [{'id': 'broken'}]
        replace_report(c, base, 'horizons', modify)
    result = joint.attach(c, base, retained_limit=LIMIT)
    assert result is not base
    items = json.loads(c.files[joint.PATH])['components']
    assert items[0]['status'] == 'COMPONENT_READ_GAP'
    assert all(i['status'] == 'VERIFIED_SAME_READING_COMPONENT' for i in items[1:])
    assert c.api.calls == 0


@pytest.mark.parametrize('mode', ['missing_key', 'missing_file', 'inline_gap', 'wrong_path'])
def test_absence_and_source_gap_are_distinct_without_history_fallback(mode):
    c, base = fixture(); _, key, path, _, _ = joint.COMPONENTS[2]
    if mode == 'missing_key': del base['research'][key]
    if mode == 'missing_file': del c.files[path]
    if mode == 'inline_gap': base['research'][key] = {'status': 'STRUCTURE_UNAVAILABLE_OTHER_INPUTS_PRESERVED',
        'previous_saved_reading': {'commit': 'b' * 40, 'path': path}}
    if mode == 'wrong_path': base['research'][key]['read_path'] = 'sources/untrusted.md'
    seal(base, 'reading_hash'); result = joint.attach(c, base, retained_limit=LIMIT)
    item = json.loads(c.files[joint.PATH])['components'][2]
    assert item['status'] == {'missing_key': 'NOT_PRESENT_IN_THIS_READING',
        'inline_gap': 'PRODUCER_REPORTED_GAP'}.get(mode, 'COMPONENT_READ_GAP')
    assert item['source'] is None and result['lanes'] == base['lanes'] and c.api.calls == 0


@pytest.mark.parametrize('mode', ['api', 'bytes', 'clock', 'no_d'])
def test_no_capacity_or_no_d_input_keeps_original_entry(mode):
    c, base = fixture(); limit = LIMIT
    if mode == 'api': c.api.calls = 180
    if mode == 'bytes': limit = 1
    if mode == 'clock': c.now = lambda: '2026-10-05T00:00:00Z'
    if mode == 'no_d':
        for spec in joint.COMPONENTS: del base['research'][spec[1]]
        seal(base, 'reading_hash')
    before = dict(c.files); calls = c.api.calls
    assert joint.attach(c, base, retained_limit=limit) is base
    assert c.files == before and c.api.calls == calls


def test_duplicate_json_and_nonfinite_source_are_rejected_locally():
    for extra in ('"version":"duplicate"', '"bad":NaN'):
        c, base = fixture(); spec = joint.COMPONENTS[0]; raw = c.files[spec[2]]
        raw = b'{' + extra.encode() + b',' + raw[1:]
        c.files[spec[2]] = raw; base['research'][spec[1]] = descriptor(spec[2], raw); seal(base, 'reading_hash')
        joint.attach(c, base, retained_limit=LIMIT)
        assert json.loads(c.files[joint.PATH])['components'][0]['status'] == 'COMPONENT_READ_GAP'


def test_untrusted_text_is_not_rendered_as_html_image_or_markdown_link():
    text = joint._text('<script>x</script>![click](https://invalid.test)\n| *do it*')
    assert '<script>' not in text and '![' not in text and '\\[' in text and '\\|' in text


def test_reading_clock_does_not_rebase_original_horizon_or_count_new_event():
    c, base = fixture(); first = joint.build(base, c.files, checked_at=AT)
    later = joint.build(base, c.files, checked_at='2026-10-07T08:00:00Z')
    assert first['components'] == later['components'] and first['new_attention_events'] == later['new_attention_events'] == 0


def test_normal_entry_hook_is_after_existing_d_producers():
    import ast
    root = Path(__file__).resolve().parents[1]
    code = ast.parse((root / 'src/decision_kernel/runtime/current_state_delivery_with_odds_watch.py').read_text())
    collect = next(n for n in ast.walk(code) if isinstance(n, ast.FunctionDef) and n.name == 'collect')
    statements = [ast.unparse(n) for n in collect.body]
    joint_pos = next(i for i, s in enumerate(statements) if 'attach_joint' in s)
    assert all(next(i for i, s in enumerate(statements) if name in s) < joint_pos
               for name in ('attach_horizons', 'attach_auction_next', 'attach_structure', 'attach_outcomes'))
    assert 'return payload' in statements[-1]


def test_later_joint_clock_cannot_accept_source_after_input_root_cutoff():
    c, base = fixture()
    replace_report(c, base, 'horizons', lambda value: value.update(checked_at='2026-10-06T08:30:00Z'))
    report = joint.build(base, c.files, checked_at='2026-10-06T09:00:00Z')
    assert report['components'][0]['status'] == 'COMPONENT_READ_GAP'
    assert report['components'][1]['status'] == 'VERIFIED_SAME_READING_COMPONENT'
