"""Read-side association tests: real retained document plus explicit synthetic inputs."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import research_reentry_reading as r

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-09-22T05:00:00+00:00'
CODE = '600598.SH'


def package(records=None, **extra):
    research = {'records': records or [], 'gaps': [], 'handoffs': {'active': [], 'background': []},
                'stock_business_work': {'status': 'READ_OK', 'items': []}, **extra}
    return m.assemble(code_commit='a'*40, checked_at=NOW, check_started_at=NOW,
                      lanes={}, research=research, capabilities=[], refresh_identity={})


def record(files, code=CODE, *, rid='test-asset', use='RETAINED_RESEARCH_DOCUMENT', raw=b'research'):
    path = 'sources/git/' + m.blob_sha(raw) + '/research.md'
    files[path] = raw
    return {'id': rid, 'case': code, 'use': use, 'source': r._meta(path, raw),
            'purpose_note': 'SYNTHETIC_TEST_REFERENCE_NOT_REAL_RESEARCH'}


def one(report):
    return report['projection']['companies'][0]


def test_real_retained_human_record_is_read_without_transferring_acceptance():
    path = ROOT / 'docs/decisions/600598-beidahuang-human-odds-acceptance-2026-09-16.md'
    raw = path.read_bytes()
    assert b'600598' in raw
    files = {}
    item = record(files, use='HUMAN_DECISION_CHECKPOINT', raw=raw)
    baseline = package([item]); before = deepcopy(baseline)
    result = r.build(baseline, files)
    assert one(result)['assets'][0]['source_check']['status'] == 'RETAINED_BYTES_VERIFIED'
    assert one(result)['human_acceptance'] == 'REFER_TO_EXACT_ORIGINAL_RECORD_NOT_TRANSFERRED'
    assert result['projection']['new_research_executions'] == 0
    assert baseline == before


@pytest.mark.parametrize('mutation', ['missing', 'bytes', 'sha256', 'git_blob', 'path', 'rule'])
def test_invalid_source_keeps_the_asset_and_exposes_gap(mutation):
    files = {}; item = record(files); source = item['source']
    if mutation == 'missing':
        files.clear()
    elif mutation == 'path':
        source['read_path'] = '../outside'
    elif mutation == 'rule':
        source['read_ref_rule'] = 'USE_LATEST'
    else:
        source[mutation] = 999 if mutation == 'bytes' else '0'*len(source[mutation])
    result = r.build(package([item]), files)
    assert len(result['projection']['companies']) == 1
    assert one(result)['next_step'] == 'RECOVER_MISSING_RETAINED_BYTES'
    assert one(result)['assets'][0]['source_check']['gaps']


def test_method_supplement_requires_reconciliation_not_silent_supersession():
    files = {}; original = record(files)
    review = record(files, rid='review', use='METHOD_SUPPLEMENT', raw=b'challenge')
    result = r.build(package([original, review]), files)
    assert len(one(result)['assets']) == 2
    assert one(result)['next_step'] == 'RECONCILE_EXISTING_METHOD_REVIEW'
    assert one(result)['semantic_comparison'] == 'NOT_PERFORMED_BY_READING'


def test_no_observation_never_claims_no_change_and_repeat_is_deterministic():
    files = {}; item = record(files); baseline = package([item])
    left, right = r.build(baseline, files), r.build(baseline, files)
    assert left == right
    assert one(left)['next_step'].endswith('NOT_NO_CHANGE')
    assert left['projection']['new_attention_events'] == 0
    assert left['projection']['coverage']['all_theses_checked'] is False


def test_unstarted_empty_stock_placeholder_is_not_existing_research():
    baseline = package(stock_business_work={'status': 'READ_OK', 'items': [
        {'thscode': CODE, 'status': 'NOT_STARTED', 'sources': {}}]})
    assert r.build(baseline, {})['projection']['companies'] == []


def test_duplicate_record_id_fails_closed():
    files = {}; item = record(files)
    with pytest.raises(ValueError, match='ambiguous'):
        r.build(package([item, deepcopy(item)]), files)


@pytest.mark.parametrize('field', list(m.AUTHORITY))
def test_root_authority_cannot_expand(field):
    baseline = package(); baseline[field] = 'GRANTED'
    baseline['reading_hash'] = canonical_hash({k:v for k,v in baseline.items() if k != 'reading_hash'})
    with pytest.raises(ValueError, match='authority'):
        r.build(baseline, {})


def add_watch(baseline, files, price='9.00'):
    from decision_kernel.runtime.odds_watch import build_watch
    config = json.loads((ROOT/'decision_inputs/odds-watch-v0.json').read_text())
    registry = json.loads((ROOT/'current_state/registry.json').read_text())
    when = datetime.fromisoformat(NOW)
    market = SimpleNamespace(market_price=price, market_timestamp=when, currency='CNY',
                             market_data_source='SYNTHETIC_TEST', price_convention='RAW')
    report = build_watch(config=config, registry=registry, observed_at=when,
                         fetch_market=lambda **_: market)
    path = 'details/inbox/1/odds-watch/watch.json'; raw = m.json_bytes(report); files[path] = raw
    baseline['lanes']['inbox'] = {'last_qualified_result': {
        'details': {'odds-watch/watch.json': r._meta(path, raw)},
        'odds_watch': {'status': 'TYPED_ODDS_WATCH_READ_OK', 'report': report}}}
    baseline['reading_hash'] = canonical_hash({k:v for k,v in baseline.items() if k != 'reading_hash'})
    return report, path


def test_original_watch_builder_is_reused_but_not_numerical_odds_authority():
    files = {}; item = record(files); baseline = package([item]); add_watch(baseline, files)
    result = r.build(baseline, files); row = one(result)
    assert row['saved_watch']['status'] == 'NEEDS_REVIEW_NOW'
    assert row['next_step'] == 'REVIEW_SAVED_PRICE_CONDITION_AND_RESEARCH_PREREQUISITES'
    assert row['numerical_odds_eligibility'] == 'REQUALIFY_FROZEN_RESEARCH_AND_MARKET_AT_ORIGINAL_ENTRY'
    assert result['projection']['odds_recomputed'] is False
    assert len(result['projection']['companies']) == 1  # Other Watch-only stocks not added.


def test_quiet_price_watch_does_not_prove_thesis_unchanged():
    files = {}; item = record(files); baseline = package([item]); add_watch(baseline, files, '10000')
    row = one(r.build(baseline, files))
    assert row['next_step'] == 'WAITING_SAVED_PRICE_BOUNDARY_NOT_THESIS_NO_CHANGE'


def test_bad_watch_bytes_do_not_hide_research_or_produce_a_trigger():
    files = {}; item = record(files); baseline = package([item]); _, path = add_watch(baseline, files)
    files[path] = b'{}'
    result = r.build(baseline, files)
    assert one(result)['saved_watch'] is None
    assert one(result)['assets'][0]['source_check']['status'] == 'RETAINED_BYTES_VERIFIED'
    assert any(g['kind'] == 'odds_watch' for g in result['projection']['read_gaps'])


def test_question_batch_rejection_rolls_back_partial_new_assets():
    files = {}; item = record(files)
    valid = {'thscode': CODE, 'execution_id': 'synthetic', 'sources': {}, **m.AUTHORITY}
    bad = {**valid, 'thscode': '000001.SZ', 'research_authority': 'GRANTED'}
    raw = m.json_bytes({'question_work': {'items': [valid, bad]}})
    path = 'details/research/reviewed-questions.json'; files[path] = raw
    baseline = package([item], reviewed_question_work={'structured': r._meta(path, raw)})
    result = r.build(baseline, files)
    assert len(one(result)['assets']) == 1
    assert len(result['projection']['companies']) == 1
    assert any(g['kind'] == 'reviewed_question_work' for g in result['projection']['read_gaps'])


def test_markup_is_escaped_and_tampered_report_rejected():
    files = {}; item = record(files, rid='<script>alert(1)</script>[x](javascript:evil)')
    report = r.build(package([item]), files)
    page = r.render(report)
    assert '<script>' not in page and '[x](javascript:' not in page
    report['projection']['companies'][0]['next_step'] = 'BUY'
    with pytest.raises(ValueError, match='hash'):
        r.render(report)


def test_attach_preserves_original_reading_and_makes_no_remote_calls(monkeypatch):
    from decision_kernel.runtime import institutional_radar_reading as existing
    files = {}; item = record(files); baseline = package([item])
    files.update({'current-state.json': m.read_package_bytes(baseline), 'README.md': b'original\n'})
    collector = SimpleNamespace(files=files, code_commit='a'*40, now=lambda:NOW,
                                api=SimpleNamespace(calls=0, max_calls=4096))
    # Exercise original reserve function, never a stand-in that blindly passes.
    original = deepcopy(baseline)
    result = r.attach(collector, baseline)
    assert baseline == original
    assert result['lanes'] == original['lanes'] and result['pending'] == original['pending']
    assert collector.api.calls == 0
    assert collector.files['README.md'].startswith(b'original\n')
    assert r.REPORT in collector.files and r.DETAIL in collector.files
    m.validate_read_package(result)


def test_publication_budget_failure_is_atomic(monkeypatch):
    from decision_kernel.runtime import institutional_radar_reading as existing
    baseline = package(); files = {'current-state.json':m.read_package_bytes(baseline), 'README.md':b'old'}
    collector = SimpleNamespace(files=files, code_commit='a'*40, now=lambda:NOW)
    def reject(*args, **kwargs):
        raise ValueError('publication reserve')
    monkeypatch.setattr(existing, '_reserve', reject)
    before = deepcopy(files)
    with pytest.raises(ValueError, match='publication reserve'):
        r.attach(collector, baseline)
    assert collector.files == before


def test_original_collector_calls_the_reentry_attachment(monkeypatch):
    from decision_kernel.runtime import current_state_delivery_with_odds_watch as c
    baseline = package(); seen=[]
    monkeypatch.setattr(c.base.Collector, 'collect', lambda self, refresh: deepcopy(baseline))
    from decision_kernel.runtime import reviewed_question_reading as q, stock_batch_disposition as b
    monkeypatch.setattr(q, 'attach', lambda self, payload:payload)
    monkeypatch.setattr(b, 'attach', lambda self, payload:payload)
    monkeypatch.setattr(r, 'attach', lambda self, payload:seen.append(payload) or payload)
    collector = object.__new__(c.Collector)
    collector.include_reviewed_questions = True
    assert collector.collect({}) == baseline and len(seen) == 1


def test_real_saved_reading_keeps_on_demand_locators_without_claiming_body_recovery():
    fixture = ROOT/'tests/fixtures/reviewed_question_real/reading.json'
    baseline = json.loads(fixture.read_text())
    assert baseline['research']['on_demand_archives']
    result = r.build(baseline, {})
    archives = [a for row in result['projection']['companies'] for a in row['archives']]
    assert archives and all(a['status'] == 'REGISTERED_LOCATOR_NOT_BODY_RECOVERED' for a in archives)
    assert result['projection']['coverage']['unavailable_assets'] > 0
    assert result['projection']['new_research_executions'] == 0


def test_radar_failure_rolls_back_all_associations_but_keeps_independent_assets():
    files={}; first=record(files); second=record(files, '300183.SZ', rid='second', raw=b'other')
    origins=[{'kind':'SYNTHETIC_TEST', 'market_session':'2026-09-21'}]
    projection={'companies':[{'thscode':CODE, 'origins':origins},
                {'thscode':'300183.SZ', 'origins':origins*(r.MAX_OBSERVATIONS+1)}],
                'generated_at':NOW, **m.AUTHORITY}
    report={'projection':projection, 'projection_hash':canonical_hash(projection)}
    path='details/radar/company-reading.json'; raw=m.json_bytes(report); files[path]=raw
    baseline=package([first,second], radar_discovery={'projection_hash':report['projection_hash'],
                         'details':{'company_reading':r._meta(path,raw)}})
    result=r.build(baseline,files)
    assert all(not row['saved_observations'] for row in result['projection']['companies'])
    assert len(result['projection']['companies']) == 2
    assert any(g['kind']=='radar_discovery' for g in result['projection']['read_gaps'])


def test_nested_markdown_links_resolve_to_the_original_pinned_package_paths():
    import posixpath
    from urllib.parse import unquote
    files={}; item=record(files)
    link=r._detail_link(item['source'])
    assert link.startswith('../../sources/git/')
    assert posixpath.normpath(posixpath.join(posixpath.dirname(r.DETAIL), unquote(link))) == item['source']['read_path']
    assert '(' + link + ')' in r.render(r.build(package([item]), files))
    with pytest.raises(ValueError, match='pinned'):
        r._detail_link({**item['source'], 'read_path':'other/file.md'})


def test_original_question_and_watch_prerequisite_are_visible_not_only_ids():
    files={}; item=record(files)
    question={'thscode':CODE, 'execution_id':'test-question', 'question':'原现金转换问题',
              'known_unknowns':['原尚未解决的现金桥'], 'terminal_reason':'原有界停止理由',
              'sources':{}, **m.AUTHORITY}
    path='details/research/reviewed-questions.json'
    raw=m.json_bytes({'question_work':{'items':[question]}}); files[path]=raw
    baseline=package([item], reviewed_question_work={'structured':r._meta(path,raw)})
    add_watch(baseline,files)
    report=r.build(baseline,files); page=r.render(report)
    assert '原现金转换问题' in page and '原有界停止理由' in page
    assert '原尚未解决的现金桥' in page
    assert '原业务前提' in page and '原价格条件记录' in page
    assert report['projection']['new_attention_events'] == 0
