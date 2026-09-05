from __future__ import annotations

import copy
import gzip
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import economic_market_context as view
from decision_kernel.runtime.economic_node_study import qualify_release_excerpt
from decision_kernel.runtime.sector_radar_context import build_sector_radar_context
from decision_kernel.runtime.sector_radar_events import (
    create_sector_radar_candidate_event_ledger, serialize_sector_radar_candidate_event_ledger,
)
from decision_kernel.runtime.sector_radar_state import parse_sector_radar_market_state, serialize_sector_radar_market_state
from test_sector_radar_audit import execute, prohibit_network, resolution, PRODUCED

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    prohibit_network(monkeypatch)


@pytest.fixture
def sources():
    return json.loads((ROOT / 'radar_inputs/economic-node-study-2026-09-05.json').read_text())


@pytest.fixture
def observations(sources):
    return [qualify_release_excerpt(row) for row in sources]


def links_for(state):
    links = json.loads((ROOT / view.DEFAULT_LINKS).read_text())
    links['catalog_hash'] = state.catalog_hash
    rows = {r.thscode: r for r in state.series}
    for link, codes in zip(links['links'], [('881101.TI', '884001.TI'), ('881102.TI',)], strict=True):
        link['targets'] = [{'thscode': c, 'name': rows[c].name, 'family': rows[c].family} for c in codes]
    return links


def build(observations, *, state=None, ledger=None, links=None, as_of=NOW, generated_at=NOW):
    restored = resolution()
    state, ledger = state or restored.market_state, ledger or restored.event_ledger
    return view.build_economic_market_context(market_state=state, event_ledger=ledger,
        observations=observations, links=links or links_for(state), as_of=as_of, generated_at=generated_at)


def test_frozen_official_excerpts_join_real_bootstrap_without_new_signals(observations):
    state = parse_sector_radar_market_state(gzip.decompress((ROOT / 'radar_inputs/sector-radar-state-bootstrap-2026-09-04.json.gz').read_bytes()).decode())
    ledger = create_sector_radar_candidate_event_ledger(created_at=NOW, source='READ_ONLY_TEST_LEDGER_NOT_LIVE')
    links = json.loads((ROOT / view.DEFAULT_LINKS).read_text())
    before = serialize_sector_radar_market_state(state), serialize_sector_radar_candidate_event_ledger(ledger), canonical_json(observations)
    report = build(observations, state=state, ledger=ledger, links=links)
    p = report['projection']
    assert p['market_session'] == '2026-09-04'
    assert p['new_events_created'] == 0 and p['company_exposure_established'] is False
    assert report['projection_hash'] == canonical_hash(p)
    assert all(p[k] == 'NONE' for k in view.AUTHORITY)
    livestock, express = p['panels']
    assert [r['identity']['family'] for r in livestock['markets']] == ['BROAD_881', 'GRANULAR_884']
    assert express['markets'][0]['identity']['thscode'] == '881152.TI'
    assert '物流不等于快递' in express['relation_note']
    assert livestock['economics']['directions'] == {'live_hog_price': 'UP', 'corn_price': 'UNCHANGED', 'fattening_pig_feed_price': 'UNCHANGED'}
    assert express['economics']['directions']['revenue_per_parcel_mix_proxy'] == 'DOWN'
    for panel in p['panels']:
        assert panel['economics']['coverage'] == 'TWO_PERIOD_DESCRIPTIVE_COMPARISON'
        assert panel['economics']['fundamental_confirmation'] == 'NOT_ESTABLISHED'
        assert all(t['provided_capture_after_market_close'] for t in panel['economics']['timing'])
        assert not any(t['period_extends_beyond_market_session'] for t in panel['economics']['timing'])
    assert before == (serialize_sector_radar_market_state(state), serialize_sector_radar_candidate_event_ledger(ledger), canonical_json(observations))


def test_exact_existing_market_rows_and_family_ranks_are_reused(observations):
    restored = resolution()
    p = build(observations)['projection']
    context = build_sector_radar_context(market_state=restored.market_state, event_ledger=restored.event_ledger, generated_at=NOW)
    expected = {(u['family'], r['observation']['thscode']): r for u in context['universes'] for r in u['rows']}
    for panel in p['panels']:
        for item in panel['markets']:
            assert item['saved_market'] == expected[(item['identity']['family'], item['identity']['thscode'])]


def test_actual_synthetic_candidate_entries_are_not_recreated_or_erased(tmp_path, observations):
    outcome, _, _ = execute(tmp_path, jump=True)
    b = outcome.persistent_bundle
    report = build(observations, state=b.market_state, ledger=b.event_ledger, as_of=PRODUCED, generated_at=PRODUCED)
    ids = [event for panel in report['projection']['panels'] for row in panel['markets'] for event in row['saved_market']['recorded_event_ids_latest_session']]
    assert set(ids) == {e.event_id for e in b.event_ledger.events}
    assert len(b.event_ledger.events) == 2 and report['projection']['new_events_created'] == 0


@pytest.mark.parametrize('count,expected', [(0, 'NO_OBSERVATIONS'), (1, 'ONE_PERIOD_ONLY')])
def test_missing_evidence_remains_a_visible_node_not_negative_economics(observations, count, expected):
    panels = build(observations[:count])['projection']['panels']
    assert len(panels) == 2
    assert panels[0]['economics']['coverage'] == expected
    assert panels[1]['economics']['coverage'] == 'NO_OBSERVATIONS'
    assert all(p['economics']['comparison'] is None for p in panels)
    assert all(p['economics']['fundamental_confirmation'] == 'NOT_ESTABLISHED' for p in panels)


def test_duplicate_inputs_do_not_add_periods_or_change_report(observations):
    assert build(observations) == build(observations + observations)
    assert build(observations) == build(list(reversed(observations)))


def test_identical_recapture_is_not_a_revision_or_new_period(sources):
    recaptured = copy.deepcopy(sources[0]); recaptured['captured_at'] = '2026-09-05T05:00:00+00:00'
    records = [qualify_release_excerpt(s) for s in [sources[0], recaptured]]
    economics = build(records)['projection']['panels'][0]['economics']
    assert len(economics['observations']) == 2 and economics['supplied_distinct_periods'] == 1
    assert economics['coverage'] == 'ONE_PERIOD_ONLY' and economics['comparison'] is None


def test_conflicting_latest_vintage_is_not_silently_selected(sources, observations):
    amended = copy.deepcopy(sources[1]); amended['excerpt'] = amended['excerpt'].replace('11.55', '12.55')
    amended['captured_at'] = '2026-09-05T05:00:00+00:00'
    economics = build(observations + [qualify_release_excerpt(amended)])['projection']['panels'][0]['economics']
    assert economics['coverage'] == 'VERSION_REVIEW_REQUIRED'
    assert economics['comparison'] is None and economics['directions'] == {}
    assert len(economics['observations']) == 3


@pytest.mark.parametrize('node', ['weekly', 'monthly'])
def test_missing_intermediate_period_not_mislabeled_as_period_over_period(sources, node):
    if node == 'weekly':
        first = copy.deepcopy(sources[0]); first['excerpt'] = first['excerpt'].replace('采集日为8月20日', '采集日为8月13日')
        records = [qualify_release_excerpt(first), qualify_release_excerpt(sources[1])]
        index = 0
    else:
        first = copy.deepcopy(sources[2]); first['title'] = first['title'].replace('上半年', '1-5月')
        first['excerpt'] = first['excerpt'].replace(sources[2]['title'], first['title']).replace('6月份', '5月份')
        records = [qualify_release_excerpt(first), qualify_release_excerpt(sources[3])]
        index = 1
    economics = build(records)['projection']['panels'][index]['economics']
    assert economics['coverage'] == 'NONADJACENT_PERIODS' and economics['comparison'] is None


def test_capture_order_inversion_visible_not_reordered(sources):
    before, after = copy.deepcopy(sources[0]), sources[1]
    before['captured_at'] = '2026-09-05T05:00:00+00:00'
    economics = build([qualify_release_excerpt(before), qualify_release_excerpt(after)])['projection']['panels'][0]['economics']
    assert economics['coverage'] == 'CAPTURE_ORDER_REVIEW_REQUIRED'


@pytest.mark.parametrize('fault', ['naive', 'future-generation', 'future-evidence', 'future-mapping'])
def test_clock_boundaries_are_checked_not_only_publication_dates(observations, fault):
    links = links_for(resolution().market_state)
    records = copy.deepcopy(observations)
    kwargs = {}
    if fault == 'naive': kwargs['as_of'] = NOW.replace(tzinfo=None)
    elif fault == 'future-generation': kwargs['generated_at'] = NOW - timedelta(seconds=1)
    elif fault == 'future-mapping': links['reviewed_at'] = (NOW + timedelta(seconds=1)).isoformat()
    else:
        source = records[0]['source_record']; source['captured_at'] = (NOW + timedelta(seconds=1)).isoformat()
        records[0] = qualify_release_excerpt(source)
    with pytest.raises(ValueError): build(records, links=links, **kwargs)


@pytest.mark.parametrize('fault', ['catalog', 'name', 'family', 'duplicate', 'extra-authority'])
def test_mapping_drift_not_silently_remapped(observations, fault):
    links = links_for(resolution().market_state)
    if fault == 'catalog': links['catalog_hash'] = 'a' * 64
    elif fault == 'name': links['links'][0]['targets'][0]['name'] += ' changed'
    elif fault == 'family': links['links'][0]['targets'][0]['family'] = 'GRANULAR_884'
    elif fault == 'duplicate': links['links'][0]['targets'] *= 2
    else: links['research_authority'] = 'APPROVE'
    with pytest.raises(ValueError): build(observations, links=links)


def test_rehashed_economic_value_tampering_still_fails(observations):
    forged = copy.deepcopy(observations)
    forged[0]['metrics'][0]['value'] = '999'
    forged[0]['observation_hash'] = canonical_hash({k: v for k, v in forged[0].items() if k != 'observation_hash'})
    with pytest.raises(ValueError, match='source-derived'): build(forged)


def test_synthetic_and_public_economic_observations_cannot_mix(observations):
    mixed = copy.deepcopy(observations)
    source = mixed[0]['source_record']; source['capture_method'] = 'SYNTHETIC_TEST_ONLY'
    mixed[0] = qualify_release_excerpt(source)
    with pytest.raises(ValueError, match='mix'): build(mixed)


def test_later_generation_and_caller_decimal_context_do_not_change_projection(observations):
    first = build(observations)
    later = build(observations, generated_at=NOW + timedelta(days=800))
    assert first['projection'] == later['projection'] and first['projection_hash'] == later['projection_hash']
    with localcontext() as arithmetic:
        arithmetic.prec = 4
        assert first == build(observations)


def test_html_keeps_time_provenance_and_questions_not_authority(observations):
    report = build(observations)
    page = BeautifulSoup(view.render_economic_market_context(report), 'html.parser')
    assert not page.select('script,iframe,form,input,button,img,link,canvas')
    assert len(page.select('section')) == 2
    assert '资料期' in page.get_text() and '实际采集' in page.get_text()
    assert '不等于市场尚未反应' in page.get_text() or '产业确认未建立' in page.get_text()
    assert '不代表市场此前不知道' in page.get_text()
    assert '经营改善已确认' in page.get_text()  # Explicitly negated by coverage label.
    assert '不代表经营改善已确认' in page.get_text()
    links = links_for(resolution().market_state); links['links'][0]['label'] = '<script>alert(1)</script>'
    assert '<script>alert' not in view.render_economic_market_context(build(observations, links=links))
    report['projection']['investment_authority'] = 'EXECUTE'
    report['projection_hash'] = canonical_hash(report['projection'])
    with pytest.raises(ValueError): view.render_economic_market_context(report)


def test_cli_runs_real_saved_bundle_path_and_keeps_inputs_unchanged(tmp_path, observations):
    _, _, audit = execute(tmp_path / 'producer', jump=True)
    bundle, hints = audit / 'expected/state', audit / 'inputs/parent-hints.json'
    state = parse_sector_radar_market_state((bundle / 'market-state.json').read_text())
    inputs = tmp_path / 'economic-inputs'; inputs.mkdir()
    manifest = inputs / 'links.json'; manifest.write_text(json.dumps(links_for(state), ensure_ascii=False))
    paths = []
    for i, row in enumerate(observations):
        path = inputs / f'{i}.json'; path.write_text(canonical_json(row)); paths.append(path)
    before = {str(p): p.read_bytes() for root in [bundle, inputs] for p in root.rglob('*') if p.is_file()}
    # Explicit frozen boundary; generation uses an injected real datetime subclass, no fake prices.
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None): return PRODUCED + timedelta(hours=1)
    # Use a context-managed monkeypatch to avoid altering existing adapter clocks.
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(view, 'datetime', Clock)
        args = ['--bundle', str(bundle), '--parent-hints', str(hints), '--links', str(manifest), '--as-of', PRODUCED.isoformat()]
        for path in paths: args += ['--observation', str(path)]
        output = tmp_path / 'review'
        assert view.main([*args, '--output', str(output)]) == 0
        assert set(p.name for p in output.iterdir()) == {'index.html', 'association.json'}
        assert view.main([*args, '--output', str(output)]) == 2
        assert view.main([*args, '--output', str(inputs / 'nested')]) == 2
        assert before == {str(p): p.read_bytes() for root in [bundle, inputs] for p in root.rglob('*') if p.is_file()}
        original = Path.write_text
        def fail(path, *a, **k):
            if path.name == 'association.json': raise OSError('simulated interrupted view write')
            return original(path, *a, **k)
        monkeypatch.setattr(Path, 'write_text', fail)
        broken = tmp_path / 'broken'
        assert view.main([*args, '--output', str(broken)]) == 2
        assert not broken.exists() and output.exists()


def test_bounded_reader_rejects_duplicate_keys_symlinks_and_oversize(tmp_path):
    path = tmp_path / 'input.json'; path.write_text('{"a":1,"a":2}')
    with pytest.raises(ValueError, match='duplicate'): view._read_json(path)
    link = tmp_path / 'link.json'; link.symlink_to(path)
    with pytest.raises(ValueError, match='symlink'): view._read_json(link)
    path.write_bytes(b' ' * (view.MAX_INPUT_BYTES + 1))
    with pytest.raises(ValueError, match='budget'): view._read_json(path)
