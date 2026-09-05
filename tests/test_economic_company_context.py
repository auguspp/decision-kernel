from __future__ import annotations

import copy
import hashlib
import json
import shutil
from datetime import timedelta
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import economic_company_context as company
from decision_kernel.runtime import economic_market_context as market
from decision_kernel.runtime.economic_node_study import qualify_release_excerpt
from test_economic_market_context import build as build_market, links_for, NOW
from test_sector_radar_audit import execute, PRODUCED, prohibit_network

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'research_cases/600233-yto-deep-research-v2.json'
SEED = 'radar_inputs/economic-node-study-2026-09-05.json'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    prohibit_network(monkeypatch)
    from decision_kernel.runtime import economic_release_discovery, economic_source_capture
    monkeypatch.setattr(economic_release_discovery, 'fetch_discovery_page', lambda *a, **k: pytest.fail('no discovery call'))
    monkeypatch.setattr(economic_source_capture, 'fetch_public_page', lambda *a, **k: pytest.fail('no source call'))


def reading(*, empty=False, **kwargs):
    sources = json.loads((ROOT / SEED).read_text())
    return build_market([] if empty else [qualify_release_excerpt(s) for s in sources], **kwargs)


def copied(tmp_path):
    root = tmp_path / 'source'
    for path in (SOURCE, company.DEFAULT_MANIFEST):
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, root / path)
    return root, json.loads((root / company.DEFAULT_MANIFEST).read_text()), json.loads((root / SOURCE).read_text())


def save(root, spec, source=None):
    if source is not None:
        raw = (json.dumps(source, ensure_ascii=False, indent=2) + '\n').encode()
        (root / SOURCE).write_bytes(raw)
        spec['nodes'][1]['companies'][0]['source_blob_sha1'] = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    (root / company.DEFAULT_MANIFEST).write_text(json.dumps(spec, ensure_ascii=False) + '\n')


def bytes_under(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_retained_real_company_fields_join_existing_radar_without_a_new_signal():
    association = reading(); before = copy.deepcopy(association)
    source_before = (ROOT / SOURCE).read_bytes()
    report = company.build_company_links(ROOT, association)
    p = report['projection']
    assert association == before and (ROOT / SOURCE).read_bytes() == source_before
    assert p['association_hash'] == association['projection_hash']
    assert p['membership_inferred'] is p['company_benefit_established'] is False
    assert p['market_event_writes'] == 0
    assert all(p[k] == v for k, v in company.LIMITS.items())
    livestock, express = p['nodes']
    assert livestock['company_coverage'] == 'NO_COMPANY_EVIDENCE_SUPPLIED'
    assert livestock['companies'] == []
    c = express['companies'][0]
    assert (c['ticker'], c['exchange'], c['company_name']) == ('600233', 'SSE', '圆通速递')
    assert c['exposure_size'] is c['elasticity'] is c['benefit_direction'] is None
    assert c['temporal_alignment'] == 'NOT_ESTABLISHED'
    h1, ir = c['basis']
    values = {f['field']: f['value'] for f in h1['values']}
    assert values['unit_rev'] == '2.17' and values['unit_cost'] == '1.90'
    assert values['volume_yi'] == '162.78'
    assert h1['evidence']['retention_mode'] == 'EXTRACTED_VALUES'
    assert h1['evidence']['replayability_level'] == 'PARTIAL'
    assert h1['original_page_verified_this_run'] is False
    assert h1['evidence']['source_location'] == '2026 H1 full filing'
    assert ir['source_use']['assertion_scope'] == 'ATTRIBUTED_STATEMENT'
    capacity = next(m for m in c['mechanisms'] if m['channel'] == 'CAPACITY')
    assert capacity['basis_keys'] == [] and capacity['status'] == 'EVIDENCE_GAP'
    assert report['projection_hash'] == canonical_hash(p)


def test_no_economic_observation_is_not_deterioration_or_company_confirmation():
    report = company.build_company_links(ROOT, reading(empty=True))
    assert all(n['economic_coverage'] == 'NO_OBSERVATIONS' for n in report['projection']['nodes'])
    assert report['projection']['nodes'][1]['companies']
    assert report['projection']['company_benefit_established'] is False


def test_generation_time_does_not_create_a_company_event_or_new_link_identity():
    a = company.build_company_links(ROOT, reading(generated_at=NOW))
    b = company.build_company_links(ROOT, reading(generated_at=NOW + timedelta(days=1)))
    assert a == b


def test_changed_source_bytes_fail_even_when_parsed_values_are_identical(tmp_path):
    root, _, _ = copied(tmp_path)
    with (root / SOURCE).open('ab') as f: f.write(b'\n')
    with pytest.raises(ValueError, match='source bytes changed'):
        company.build_company_links(root, reading())


@pytest.mark.parametrize('mode', ['mapping', 'retrieval', 'availability'])
def test_late_mapping_or_late_evidence_cannot_enter_earlier_reading(tmp_path, mode):
    root, spec, source = copied(tmp_path)
    if mode == 'mapping':
        spec['prepared_at'] = (NOW + timedelta(microseconds=1)).isoformat()
    elif mode == 'retrieval':
        source['evidence_artifacts'][0]['retrieved_at'] = NOW.isoformat()
    else:
        source['evidence_artifacts'][0]['available_at'] = (NOW + timedelta(seconds=1)).isoformat()
        source['evidence_artifacts'][0]['retrieved_at'] = (NOW + timedelta(seconds=2)).isoformat()
    save(root, spec, source)
    with pytest.raises(ValueError): company.build_company_links(root, reading())


@pytest.mark.parametrize('mode', ['issuer', 'evidence_id', 'identifier', 'field', 'duplicate_field', 'node', 'duplicate_company'])
def test_exact_company_evidence_and_node_identity_not_keyword_inference(tmp_path, mode):
    root, spec, source = copied(tmp_path); c = spec['nodes'][1]['companies'][0]
    if mode == 'issuer': c['company_name'] = 'Another issuer'
    elif mode == 'evidence_id': c['basis'][0]['evidence_artifact_id'] = 'missing'
    elif mode == 'identifier': c['basis'][0]['source_identifier'] = 'Another filing'
    elif mode == 'field': c['basis'][0]['fields'][0]['field'] = 'invented_future_profit'
    elif mode == 'duplicate_field': c['basis'][0]['fields'].append(c['basis'][0]['fields'][0])
    elif mode == 'node': spec['nodes'][1]['node_id'] = 'not.in.projection'
    else: spec['nodes'][1]['companies'].append(copy.deepcopy(c))
    save(root, spec)
    with pytest.raises(ValueError): company.build_company_links(root, reading())


@pytest.mark.parametrize('mode', ['sell_side', 'management_as_realized', 'metadata', 'missing_extraction', 'unsafe_url'])
def test_source_role_and_retention_remain_strict_even_with_a_new_valid_blob_hash(tmp_path, mode):
    root, spec, source = copied(tmp_path); c = spec['nodes'][1]['companies'][0]
    e = source['evidence_artifacts'][0]
    if mode == 'sell_side': e['source_type'] = 'SELL_SIDE_RESEARCH'
    elif mode == 'management_as_realized': c['basis'][1]['source_use']['source_role'] = 'PRIMARY_REALIZED'
    elif mode == 'metadata':
        e.update(retention_mode='METADATA_ONLY', replayability_level='REFERENCE_ONLY', extracted_structured_values=None)
    elif mode == 'missing_extraction': e['extracted_structured_values'] = {}; e['permitted_excerpt'] = 'title only'
    else: e['source_locator'] = 'javascript:alert(1)'
    save(root, spec, source)
    with pytest.raises(ValueError): company.build_company_links(root, reading())


@pytest.mark.parametrize('mode', ['confirmed', 'gap_with_support', 'missing_ref', 'new_score'])
def test_inputs_do_not_automatically_establish_transmission_or_opportunity(tmp_path, mode):
    root, spec, _ = copied(tmp_path); c = spec['nodes'][1]['companies'][0]
    if mode == 'confirmed': c['mechanisms'][0]['status'] = 'CONFIRMED_BENEFICIARY'
    elif mode == 'gap_with_support': c['mechanisms'][2]['status'] = 'HYPOTHESIS_WITH_RETAINED_INPUTS'
    elif mode == 'missing_ref': c['mechanisms'][0]['basis_keys'] = ['not_retained']
    else: c['opportunity_score'] = 100
    save(root, spec)
    with pytest.raises(ValueError): company.build_company_links(root, reading())


def test_reference_paths_cannot_escape_source_root(tmp_path):
    root, spec, _ = copied(tmp_path)
    spec['nodes'][1]['companies'][0]['source_path'] = 'research_cases/../outside.json'
    save(root, spec)
    with pytest.raises(ValueError): company.build_company_links(root, reading())
    alias = tmp_path / 'alias'; alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError): company.build_company_links(alias, reading())


def test_html_preserves_scope_and_escapes_notes_without_remote_assets(tmp_path):
    root, spec, _ = copied(tmp_path)
    spec['nodes'][1]['companies'][0]['mechanisms'][0]['hypothesis'] = '<script>not an instruction</script>'
    save(root, spec)
    page = company.render_company_links(company.build_company_links(root, reading()))
    soup = BeautifulSoup(page, 'html.parser')
    assert soup.find('script') is soup.find('iframe') is soup.find('img') is None
    assert '<script>not an instruction</script>' in soup.get_text()
    assert '未重验公司原文或页码' in soup.get_text()
    assert 'ATTRIBUTED_STATEMENT' in soup.get_text()
    assert soup.find('a', href='company-links.json') is not None
    assert 'https://money.finance.sina.com.cn/' in page


def test_source_budget_and_duplicate_manifest_keys_are_rejected(tmp_path):
    root, spec, _ = copied(tmp_path)
    (root / company.DEFAULT_MANIFEST).write_text('{"schema_version":1,"schema_version":1}')
    with pytest.raises(ValueError, match='duplicate'): company.build_company_links(root, reading())
    save(root, spec)
    (root / SOURCE).write_bytes(b'x' * (256 * 1024 + 1))
    with pytest.raises(ValueError, match='bounded'): company.build_company_links(root, reading())


def cli_case(tmp_path, monkeypatch):
    outcome, _, audit = execute(tmp_path / 'market', jump=True)
    inputs = tmp_path / 'inputs'; inputs.mkdir()
    seed = inputs / 'seed.json'; shutil.copyfile(ROOT / SEED, seed)
    reviews = inputs / 'reviews'; reviews.mkdir()
    links = inputs / 'links.json'; links.write_text(canonical_json(links_for(outcome.persistent_bundle.market_state)))
    class Clock(market.datetime):
        @classmethod
        def now(cls, tz=None): return PRODUCED + timedelta(days=1)
    monkeypatch.setattr(market, 'datetime', Clock)
    target = tmp_path / 'reading'
    args = ['--seed', str(seed), '--reviews-dir', str(reviews), '--bundle', str(audit / 'expected/state'),
        '--parent-hints', str(audit / 'inputs/parent-hints.json'), '--links', str(links),
        '--source-root', str(ROOT), '--as-of', PRODUCED.isoformat(), '--output', str(target)]
    return args, target, audit, outcome, inputs


def test_full_shared_input_cli_preserves_real_computed_synthetic_candidates(tmp_path, monkeypatch):
    args, target, audit, outcome, inputs = cli_case(tmp_path, monkeypatch)
    prior = bytes_under(audit), bytes_under(inputs), (ROOT / SOURCE).read_bytes()
    assert company.main(args) == 0
    base = json.loads((target / 'association.json').read_text())
    links = json.loads((target / 'company-links.json').read_text())
    assert links['projection']['association_hash'] == base['projection_hash']
    assert base['projection']['new_events_created'] == 0
    ids = {i for p in base['projection']['panels'] for m in p['markets'] for i in m['saved_market']['recorded_event_ids_latest_session']}
    assert ids == {e.event_id for e in outcome.persistent_bundle.event_ledger.events}
    assert len(ids) == 2
    assert {p.name for p in target.iterdir()} == {'index.html', 'association.json', 'company-links.json', 'input-set.json'}
    soup = BeautifulSoup((target / 'index.html').read_text(), 'html.parser')
    assert len(soup.select('#company-evidence')) == 1
    assert soup.find('script') is None
    assert prior == (bytes_under(audit), bytes_under(inputs), (ROOT / SOURCE).read_bytes())
    saved = bytes_under(target)
    assert company.main(args) == 2 and bytes_under(target) == saved


def test_interrupted_company_publication_leaves_no_partial_output(tmp_path, monkeypatch):
    args, target, audit, _, inputs = cli_case(tmp_path, monkeypatch)
    before = bytes_under(audit), bytes_under(inputs)
    old = Path.rename
    def fail(self, dst):
        if Path(dst) == target: raise OSError('synthetic publication failure')
        return old(self, dst)
    monkeypatch.setattr(Path, 'rename', fail)
    assert company.main(args) == 2
    assert not target.exists() and not list(tmp_path.glob('.company-reading-*'))
    assert before == (bytes_under(audit), bytes_under(inputs))
