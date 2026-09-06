from __future__ import annotations
import copy
import hashlib
import json
import shutil
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from decision_kernel.evidence import EvidenceArtifact
from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import economic_company_context as company
from test_economic_company_context import reading, cli_case, bytes_under, ROOT, SOURCE
from test_sector_radar_audit import prohibit_network

MANIFEST = 'radar_inputs/economic-company-links-livestock-v1.json'
EVIDENCE = 'radar_inputs/company-evidence/002714-muyuan-h1-2026-09-06.json'
RAW_HASH = '06f3f6284318122399c6cf1156f5a142c9b9abd8157c669ccd37bdb298002c53'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    prohibit_network(monkeypatch)


def build(root=ROOT, **kwargs):
    return company.build_company_links(root, reading(**kwargs), manifest_path=MANIFEST)


def copy_inputs(tmp_path):
    root = tmp_path / 'source'
    for path in (MANIFEST, EVIDENCE, SOURCE):
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, root / path)
    return root, json.loads((root / MANIFEST).read_text()), json.loads((root / EVIDENCE).read_text())


def save(root, spec, source):
    raw = (json.dumps(source, ensure_ascii=False, indent=2) + '\n').encode()
    (root / EVIDENCE).write_bytes(raw)
    spec['nodes'][0]['companies'][0]['source_blob_sha1'] = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    (root / MANIFEST).write_text(json.dumps(spec, ensure_ascii=False))


def test_selected_original_has_no_manufactured_research_snapshot():
    source = json.loads((ROOT / EVIDENCE).read_text())
    assert 'research_snapshot' not in source
    assert source['company_identity'] == {'ticker':'002714','exchange':'SZSE','company_name':'牧原股份'}
    assert source['semantics'] == 'COMPANY_EVIDENCE_ONLY_NOT_RESEARCH_OR_JUDGMENT'
    assert len(source['evidence_artifacts']) == 3
    for record in source['evidence_artifacts']:
        evidence = EvidenceArtifact.model_validate(record)
        assert evidence.retention_mode.value == 'EXTRACTED_VALUES'
        assert evidence.replayability_level.value == 'PARTIAL' and evidence.raw_storage_ref is None
        assert record['source_locator'].endswith('/2026-08-21/1225485220.PDF')
        fields = record['extracted_structured_values']
        assert fields['original_pdf_sha256'] == RAW_HASH
        assert fields['original_capture_run_id'] == '33999968354'
        assert evidence.available_at == evidence.retrieved_at
        assert evidence.retrieved_at < datetime.fromisoformat(source['recorded_at'])
        assert record['content_hash'] == canonical_hash({'source_url':record['source_locator'],
            'raw_pdf_sha256':RAW_HASH,'location':record['source_location'],'retained_fields':fields})


def test_financial_bridge_retains_negative_elimination_not_normalized_exposure():
    report = build(); c = report['projection']['nodes'][0]['companies'][0]
    values = {r['field']:r['value'] for r in c['basis'][0]['values']}
    assert len(values) == 12
    assert values['consolidated_revenue_cny'] == '59410306384.59'
    assert values['interbusiness_revenue_elimination_cny'] == '-21040419426.46'
    assert sum(Decimal(values[k]) for k in ('farming_revenue_cny','slaughter_meat_revenue_cny',
        'trade_revenue_cny','other_revenue_cny','interbusiness_revenue_elimination_cny')) == Decimal(values['consolidated_revenue_cny'])
    assert Decimal(values['reported_farming_revenue_percent']) + Decimal(values['reported_slaughter_revenue_percent']) > 100
    assert values['farming_gross_margin_percent'] == '-4.51'
    assert values['slaughter_gross_margin_percent'] == '4.24'
    assert values['consolidated_operating_cash_flow_cny'] == '-2223668382.68'
    assert values['consolidated_long_lived_asset_cash_purchase_cny'] == '6520966515.39'
    assert c['exposure_size'] is c['elasticity'] is c['benefit_direction'] is None
    assert c['basis'][0]['source_use']['assertion_scope'] == 'REALIZED_OUTCOME'
    assert c['basis'][0]['original_page_verified_this_run'] is False  # render != fresh PDF examination


def test_approximate_month_and_annual_target_remain_attributed_text():
    c = build()['projection']['nodes'][0]['companies'][0]
    ops = c['basis'][1]
    values = {r['field']:r for r in ops['values']}
    assert ops['source_use']['source_role'] == 'PRIMARY_STATEMENT'
    assert ops['source_use']['assertion_scope'] == 'ATTRIBUTED_STATEMENT'
    assert values['commercial_pigs_sold_10k']['value'] == '3861.5'
    assert '集团' in values['commercial_pigs_sold_10k']['scope_note']
    assert values['pigs_slaughtered_10k']['value'] == '1723.4'
    for key in ('june_full_cost_statement','annual_cost_target_statement'):
        assert values[key]['kind'] == 'TEXT'
    assert '约11.7' in values['june_full_cost_statement']['value']
    assert '2026年6月' in values['june_full_cost_statement']['value']
    assert '11.5' in values['annual_cost_target_statement']['value']
    assert '不是已经实现' in values['annual_cost_target_statement']['value']
    capacity = next(m for m in c['mechanisms'] if m['channel'] == 'CAPACITY')
    assert capacity['basis_keys'] == [] and capacity['status'] == 'EVIDENCE_GAP'


def test_past_years_multiple_ingredients_range_is_not_a_corn_weight():
    c = build()['projection']['nodes'][0]['companies'][0]
    risk = c['basis'][2]
    assert risk['source_use']['assertion_scope'] == 'ATTRIBUTED_STATEMENT'
    assert all(r['kind'] == 'TEXT' for r in risk['values'])
    text = risk['values'][0]['value']
    assert all(word in text for word in ('过去几年','小麦','玉米','豆粕','55%-65%'))
    assert '不是2026H1精确占比' in text and '不是玉米单项占比' in text
    assert 'PDF/printed p.25' in risk['evidence']['source_location']
    assert 'p.26' in risk['evidence']['source_location']
    assert c['current_business_freshness'] == 'NOT_REVALIDATED'
    assert c['temporal_alignment'] == 'NOT_ESTABLISHED'


def test_old_manifest_default_and_yto_source_semantics_remain_unchanged():
    old = company.build_company_links(ROOT, reading())
    new = build()
    assert old['projection']['nodes'][0]['companies'] == []
    before = old['projection']['nodes'][1]['companies'][0]
    after = new['projection']['nodes'][1]['companies'][0]
    for key in ('basis','mechanisms','source_blob_sha1','source_sha256','business_scope','exposure_size_note'):
        assert before[key] == after[key]
    for report in (old, new):
        assert all(report['projection'][k] == v for k,v in company.LIMITS.items())
        assert report['projection']['automatic_research_routing'] is False


@pytest.mark.parametrize('mode', ['extra-snapshot','semantics','future-record','pre-acquisition-record','naive-record','issuer','proxy','missing-evidence'])
def test_evidence_only_rejects_rehashed_invalid_container_and_clocks(tmp_path, mode):
    root, spec, source = copy_inputs(tmp_path)
    if mode == 'extra-snapshot': source['research_snapshot'] = source['company_identity']
    elif mode == 'semantics': source['semantics'] = 'CONFIRMED_BENEFICIARY'
    elif mode == 'future-record': source['recorded_at'] = (datetime.fromisoformat(spec['prepared_at'])+timedelta(seconds=1)).isoformat()
    elif mode == 'pre-acquisition-record': source['recorded_at'] = '2026-09-05T23:56:00+00:00'
    elif mode == 'naive-record': source['recorded_at'] = '2026-09-06T00:04:00'
    elif mode == 'issuer': source['company_identity']['company_name'] = '另一家公司'
    elif mode == 'proxy': source['company_identity']['ticker'] = '02714'
    else: source['evidence_artifacts'] = source['evidence_artifacts'][1:]
    save(root, spec, source)
    with pytest.raises(ValueError): build(root)


def test_mapping_and_source_drift_cannot_enter_an_earlier_cutoff(tmp_path):
    root, spec, source = copy_inputs(tmp_path)
    early = datetime.fromisoformat(spec['prepared_at']) - timedelta(microseconds=1)
    with pytest.raises(ValueError, match='prepared after'): build(root, as_of=early)
    with (root / EVIDENCE).open('ab') as stream: stream.write(b'\n')
    with pytest.raises(ValueError, match='source bytes changed'): build(root)


def test_html_exposes_page_scope_and_no_confirmed_benefit():
    page = company.render_company_links(build())
    soup = BeautifulSoup(page,'html.parser')
    assert soup.find('script') is soup.find('iframe') is None
    text = soup.get_text()
    assert all(word in text for word in ('牧原股份','PDF/printed pp.19-20','第25页','前瞻目标','内部销售抵消','PARTIAL','公司摘录记录时间'))
    assert '原文 PDF 第6页' in text
    assert soup.find('a',href='https://static.cninfo.com.cn/finalpage/2026-08-21/1225485220.PDF')
    assert '不是受益股名单' in text and '未重验公司原文或页码' in text


def test_full_existing_radar_cli_adds_case_without_changing_market_events(tmp_path, monkeypatch):
    args, target, audit, outcome, inputs = cli_case(tmp_path, monkeypatch)
    args += ['--company-links', MANIFEST]
    originals = bytes_under(audit), bytes_under(inputs), (ROOT/EVIDENCE).read_bytes(), (ROOT/SOURCE).read_bytes()
    assert company.main(args) == 0
    association = json.loads((target/'association.json').read_text())
    result = json.loads((target/'company-links.json').read_text())
    assert result['projection']['association_hash'] == association['projection_hash']
    assert [len(n['companies']) for n in result['projection']['nodes']] == [1,1]
    ids = {i for p in association['projection']['panels'] for m in p['markets'] for i in m['saved_market']['recorded_event_ids_latest_session']}
    assert ids == {e.event_id for e in outcome.persistent_bundle.event_ledger.events} and len(ids)==2
    assert all(p['economics']['fundamental_confirmation']=='NOT_ESTABLISHED' for p in association['projection']['panels'])
    assert originals == (bytes_under(audit),bytes_under(inputs),(ROOT/EVIDENCE).read_bytes(),(ROOT/SOURCE).read_bytes())
    saved=bytes_under(target)
    assert company.main(args)==2 and bytes_under(target)==saved
