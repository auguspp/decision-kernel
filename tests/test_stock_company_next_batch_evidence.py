"""Two prepared business sources, not production coverage or a market acceptance.

Use the existing EvidenceArtifact / company mapper. No live inputs, provider
request, selector change, captured-input rewrite or second research schema.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from decision_kernel.evidence import EvidenceArtifact
from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import economic_company_context as company
from decision_kernel.runtime import stock_radar_reading as stock
from test_sector_radar_audit import prohibit_network

ROOT = Path(__file__).resolve().parents[1]
V2 = 'radar_inputs/economic-company-links-livestock-v2.json'
CASES = (
    ('000048', '京基智农', 'kingkey', 'KINGKEY:000048:2026-H1:business'),
    ('000735', '罗牛山', 'luoniushan', 'LUONIUSHAN:000735:2026-H1:business'),
)
OLD_ACCEPTED_RUN_STARTED = datetime(2026, 9, 7, 22, 49, 27, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def source(case):
    ticker, _, slug, _ = case
    path = ROOT / f'radar_inputs/company-evidence/{ticker}-{slug}-business-2026-09-08.json'
    return json.loads(path.read_bytes())


def basis(record):
    return {
        'key': 'business',
        'evidence_artifact_id': record['id'],
        'source_identifier': record['source_identifier'],
        'source_use': {
            'source_role': 'PRIMARY_STATEMENT',
            'assertion_scope': 'ATTRIBUTED_STATEMENT',
            'role_basis': '公司披露的有限转述；副本不构成源站认证或已实现净受益。',
        },
        'fields': [
            {'field': key, 'label': key, 'unit': '公司叙述', 'kind': 'TEXT',
             'scope_note': '只限已注明报告期与位置，不是市场输入或投资判断。'}
            for key in record['extracted_structured_values']
        ],
    }


@pytest.mark.parametrize('case', CASES)
def test_prepared_evidence_uses_existing_contract_and_exact_issuer(case):
    value = source(case)
    ticker, name, _, identifier = case
    assert set(value) == {'semantics', 'recorded_at', 'company_identity', 'evidence_artifacts'}
    assert value['semantics'] == 'COMPANY_EVIDENCE_ONLY_NOT_RESEARCH_OR_JUDGMENT'
    assert value['company_identity'] == {'ticker': ticker, 'exchange': 'SZSE', 'company_name': name}
    assert len(value['evidence_artifacts']) == 1
    evidence = EvidenceArtifact.model_validate(value['evidence_artifacts'][0])
    assert evidence.source_identifier == identifier
    assert evidence.report_period_end.isoformat() == '2026-06-30'
    assert evidence.retention_mode.value == 'EXTRACTED_VALUES'
    assert evidence.replayability_level.value == 'PARTIAL'
    assert evidence.raw_storage_ref is None
    assert evidence.permitted_excerpt is None
    assert evidence.published_at < evidence.available_at == evidence.retrieved_at
    assert evidence.retrieved_at == datetime.fromisoformat(value['recorded_at'])
    assert evidence.retrieved_at > OLD_ACCEPTED_RUN_STARTED
    assert all(isinstance(v, str) and v.strip() for v in evidence.extracted_structured_values.values())


@pytest.mark.parametrize('case', CASES)
def test_retained_hash_binds_locator_location_and_fields_not_original_pdf(case):
    record = source(case)['evidence_artifacts'][0]
    payload = {key: record[key] for key in (
        'source_locator', 'source_location', 'extracted_structured_values')}
    assert record['content_hash'] == canonical_hash(payload)
    assert record['idempotency_key'] == record['source_identifier'] + ':' + record['content_hash']
    assert record['source_locator'].startswith('https://file.finance.sina.com.cn/')
    changed = {**payload, 'source_location': payload['source_location'] + ' changed'}
    assert canonical_hash(changed) != record['content_hash']


@pytest.mark.parametrize('case', CASES)
def test_existing_business_mapper_accepts_prepared_fields_without_freshness_claim(case):
    value = source(case)
    record = value['evidence_artifacts'][0]
    at = datetime.fromisoformat(value['recorded_at'])
    result = company._basis(basis(record), {record['id']: record}, prepared=at, as_of=at)
    assert result['evidence'] == record
    assert result['original_page_verified_this_run'] is False
    assert result['source_use']['source_role'] == 'PRIMARY_STATEMENT'
    assert result['source_use']['assertion_scope'] == 'ATTRIBUTED_STATEMENT'
    assert all(field['kind'] == 'TEXT' for field in result['values'])


@pytest.mark.parametrize('case', CASES)
def test_publication_day_does_not_allow_new_acquisition_in_old_capture(case):
    value = source(case)
    record = value['evidence_artifacts'][0]
    at = datetime.fromisoformat(value['recorded_at'])
    evidence = EvidenceArtifact.model_validate(record)
    assert not evidence.is_available_at(OLD_ACCEPTED_RUN_STARTED)
    with pytest.raises(ValueError, match='cutoff'):
        company._basis(basis(record), {record['id']: record},
                       prepared=at, as_of=OLD_ACCEPTED_RUN_STARTED)


def test_original_v2_scope_is_not_silently_expanded_by_prepared_files():
    spec = json.loads((ROOT / V2).read_bytes())
    companies = [c for node in spec['nodes'] for c in node['companies']]
    assert {c['ticker'] for c in companies} == {'002714', '300498', '603477', '605296', '600233'}
    assert not {case[0] for case in CASES} & {c['ticker'] for c in companies}


def test_proposed_scope_budget_preserves_existing_companies_and_all_linked_directions():
    # Static planning arithmetic, NOT an actual capture or market qualification.
    spec = json.loads((ROOT / V2).read_bytes())
    links = json.loads((ROOT / 'radar_inputs/economic-market-links-v0.json').read_bytes())
    covered = {node['node_id'] for node in spec['nodes'] if node['companies']}
    directions = {target['thscode'] for node in links['links'] if node['node_id'] in covered
                  for target in node['targets']}
    issuers = {(c['ticker'], c['exchange']) for node in spec['nodes'] for c in node['companies']}
    assert len(directions) == 3 and len(issuers) == 5
    # Same reservation as prepare_stock_reading: 4 shared + directions + 3 per issuer.
    one_addition = 4 + len(directions) + 3 * (len(issuers) + 1)
    two_additions = 4 + len(directions) + 3 * (len(issuers) + 2)
    assert one_addition == 25 <= stock.MAX_REQUESTS == 26
    assert two_additions == 28 > stock.MAX_REQUESTS
