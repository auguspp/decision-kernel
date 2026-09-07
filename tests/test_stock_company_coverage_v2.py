"""Real retained company inputs, synthetic market responses; no live stock claim.

The fixture calendar deliberately treats Sept 7 as closed to reuse the frozen
Sept 4 state after the NEW evidence acquisition. It is not an exchange calendar
or permission to use stale state in production. No evidence clock is backdated.
"""
import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from decision_kernel.evidence import EvidenceArtifact
from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import stock_radar_reading as stock
from decision_kernel.runtime import hithink_stock_reading as own
from test_hithink_stock_reading_integration import contract_provider
from test_sector_radar_audit import prohibit_network
from test_stock_radar_capture import setup, stock_environment
from test_stock_radar_reading import ROOT, NOW
from test_stock_issuer_isolation import rehash_capture

V2 = 'radar_inputs/economic-company-links-livestock-v2.json'
AT = datetime(2026, 9, 7, 13, tzinfo=timezone.utc)
NEW = {'300498.SZ', '603477.SH', '605296.SH'}
PLANNED = {'002714.SZ', *NEW}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def specification():
    return json.loads((ROOT/V2).read_bytes())


def copy_inputs(tmp_path, at=AT):
    mod, state, out, _, _, _ = setup(tmp_path)
    helper = mod['sibling']('build-sector-radar-reading.py')
    files, directories = helper['_source_files'](ROOT, state, as_of=at, company_manifest=V2)
    root = tmp_path/'input-copy'
    for directory in directories:
        (root/directory).mkdir(parents=True, exist_ok=True)
    for name, raw in files.items():
        p = root/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
    return mod, state, out, root


def run_expanded(tmp_path, failed='002714.SZ'):
    mod, state, out, root = copy_inputs(tmp_path)
    bundle, _, plan = mod['load_inputs'](root, AT, company_manifest=V2)
    _, _, base, _ = contract_provider()
    codes = {r['thscode']:r['company_name'] for r in plan['issuers']}
    calls, pauses = [], []
    raw_failure = {'code':3002, 'data':None, 'message':f'No adjustment events for thscode={failed}',
                   'request_id':'SYNTHETIC_COMPANY_SCOPE_TEST'}
    def request(path, params):
        calls.append((path, dict(params)))
        value = base(path, params)
        if path == stock.HITHINK_CALENDAR_PATH:
            # Explicit test closure, not a weekday heuristic or actual market claim.
            days = (*bundle.market_state.sessions, AT.date()+timedelta(days=1))
            value = {'code':0, 'data':{'item':[{'date':d.strftime('%Y%m%d')} for d in days]}}
        if path == stock.indices.HITHINK_INDEX_CATALOG_PATH:
            value['data']['timestamp'] = int(AT.timestamp()*1000)
        if path == stock.members.HITHINK_SECTOR_CONSTITUENTS_PATH:
            value['data'] = {'timestamp':int(AT.timestamp()*1000), 'item':[
                {'thscode':c, 'ticker':c[:6], 'name':n} for c,n in sorted(codes.items())]}
        if path == own.HISTORY:
            value['data']['timestamp'] = int(AT.timestamp()*1000)
        if path == own.ACTIONS and params['thscode'] == failed:
            value = copy.deepcopy(raw_failure)
        return value
    ticks = iter(AT+timedelta(seconds=i*21) for i in range(100))
    before = mod['inventory'](state)
    result = mod['capture'](ROOT, state, out, observed_at=AT, transport=request,
        workflow={'test':'synthetic-market-real-company-inputs'}, now=lambda:next(ticks),
        pause=pauses.append, company_manifest=V2)
    assert mod['inventory'](state) == before
    return mod, out, result, plan, calls, pauses, raw_failure


def test_v2_keeps_both_existing_company_definitions_and_adds_three_primary_bases():
    old = json.loads((ROOT/stock.COMPANY_MANIFEST).read_bytes())
    new = specification()
    assert new['nodes'][0]['companies'][0] == old['nodes'][0]['companies'][0]
    assert new['nodes'][1] == old['nodes'][1]
    added = new['nodes'][0]['companies'][1:]
    assert {r['ticker'] for r in added} == {'300498','603477','605296'}
    for company in added:
        raw = (ROOT/company['source_path']).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == company['source_blob_sha1']
        source = json.loads(raw)
        assert source['semantics'] == 'COMPANY_EVIDENCE_ONLY_NOT_RESEARCH_OR_JUDGMENT'
        evidence = EvidenceArtifact.model_validate(source['evidence_artifacts'][0])
        assert evidence.report_period_end.isoformat() == '2025-12-31'
        assert evidence.retention_mode.value == 'EXTRACTED_VALUES'
        assert evidence.replayability_level.value == 'PARTIAL'
        assert evidence.raw_storage_ref is None
        record = source['evidence_artifacts'][0]
        assert evidence.content_hash == canonical_hash({k:record[k] for k in (
            'source_locator','source_location','extracted_structured_values')})
        assert datetime.fromisoformat(source['recorded_at']) <= datetime.fromisoformat(new['prepared_at']) <= AT
        assert evidence.retrieved_at.date().isoformat() == '2026-09-07'
        assert not evidence.is_available_at(NOW)
        assert all(f['kind'] == 'TEXT' for b in company['basis'] for f in b['fields'])
        assert company['basis'][0]['source_use']['assertion_scope'] == 'ATTRIBUTED_STATEMENT'
    count = sum(len(n['companies']) for n in new['nodes'])
    assert count == 5
    assert 4+stock.MAX_MEMBERSHIPS+3*count == 25 < stock.MAX_REQUESTS


def test_expanded_plan_uses_four_real_company_identities_not_a_top_three(tmp_path):
    mod, _, _, root = copy_inputs(tmp_path)
    _, _, plan = mod['load_inputs'](root, AT, company_manifest=V2)
    assert {r['thscode'] for r in plan['issuers']} == PLANNED
    assert set(plan['directions']) == {'881102.TI','884275.TI'}
    assert plan['maximum_request_count'] == 18
    assert plan['company_manifest'] == V2
    assert {r['thscode'] for r in plan['evidence_scope_issuers']} == PLANNED|{'600233.SH'}
    assert all(r['origins'][0]['company']['basis'] for r in plan['issuers'])
    assert plan['investment_authority'] == plan['research_authority'] == 'NONE'


@pytest.mark.parametrize('failed',['002714.SZ','300498.SZ'])
def test_expanded_capture_isolates_one_and_rebuilds_the_other_three(tmp_path, failed):
    mod, out, report, plan, calls, pauses, raw_failure = run_expanded(tmp_path, failed)
    assert report['status'] == mod['PARTIAL'], report
    assert report['company_manifest'] == V2
    assert report['coverage']['planned_issuers'] == 4
    assert report['coverage']['qualified_issuers'] == 3
    assert report['coverage']['unavailable_issuers'] == 1
    assert len(calls) == plan['maximum_request_count'] == 18
    assert pauses == [20]*17
    p = mod['read'](out/'stock-reading.json')['projection']
    assert {r['thscode'] for r in p['surfaced_stocks']} == PLANNED-{failed}
    assert p['status'] == 'PARTIAL_STOCKS_FOR_SHADOW_READING'
    entry = next(r for r in report['requests'] if r['path'] == own.ACTIONS and r['params']['thscode'] == failed)
    assert mod['read'](out/entry['response_file']) == raw_failure
    for company in specification()['nodes'][0]['companies'][1:]:
        assert (out/'inputs'/company['source_path']).read_bytes() == (ROOT/company['source_path']).read_bytes()
    assert (out/'inputs'/V2).read_bytes() == (ROOT/V2).read_bytes()
    assert not (out/'inputs'/stock.COMPANY_MANIFEST).exists()
    rebuilt = mod['verify'](out)
    assert rebuilt['status'] == 'STOCK_BATCH_WITH_DATA_GAPS_REBUILT'
    assert rebuilt['stock_count'] == 3 and rebuilt['requests_replayed'] == 18
    assert rebuilt['network_calls'] == 0 and rebuilt['coverage'] == report['coverage']
    html = (out/'index.html').read_text()
    assert '合成验收样本' in html and '数据不可用 1' in html
    assert '2025' in html and all(name in html for name in ('温氏股份','巨星农牧','神农集团'))


def test_new_company_inputs_cannot_be_backdated_into_old_capture(tmp_path):
    mod, state, out, _, _, _ = setup(tmp_path)
    calls = []
    report = mod['capture'](ROOT, state, out, observed_at=NOW,
        transport=lambda *args:calls.append(args), workflow={'test':'past-cutoff'},
        now=lambda:NOW, pause=lambda _:None, company_manifest=V2)
    assert report['status'] == mod['FAILED'] and not report['requests'] and not calls
    assert report['plan_hash'] is None and not (out/'stock-reading.json').exists()
    assert not (out/'inputs'/stock.COMPANY_MANIFEST).exists()


@pytest.mark.parametrize('kind',['missing','changed'])
def test_new_evidence_failure_does_not_fall_back_to_old_scope(tmp_path, kind):
    mod, _, _, root = copy_inputs(tmp_path)
    (root/stock.COMPANY_MANIFEST).write_bytes((ROOT/stock.COMPANY_MANIFEST).read_bytes())
    if kind == 'missing':
        (root/V2).unlink()
    else:
        p = root/specification()['nodes'][0]['companies'][1]['source_path']
        p.write_bytes(p.read_bytes()+b'\n')
    with pytest.raises((ValueError, OSError)):
        mod['load_inputs'](root, AT, company_manifest=V2)


def test_rehashed_capture_cannot_relabel_v2_as_historical_v1(tmp_path):
    mod, out, report, _, _, _, _ = run_expanded(tmp_path)
    (out/'inputs'/stock.COMPANY_MANIFEST).write_bytes((ROOT/stock.COMPANY_MANIFEST).read_bytes())
    report['company_manifest'] = stock.COMPANY_MANIFEST
    rehash_capture(mod, out, report)
    with pytest.raises(ValueError, match='reconstruct'):
        mod['verify'](out)


@pytest.mark.parametrize('value',['latest','../../arbitrary.json',None,{}])
def test_unknown_company_manifest_is_rejected(tmp_path, value):
    mod, _, _, _, _, _ = setup(tmp_path)
    with pytest.raises(ValueError, match='exact reviewed'):
        mod['company_scope'](value)


def test_normal_live_cli_explicitly_uses_v2_without_new_user_input(tmp_path, monkeypatch):
    mod, _, _, _, _, _ = setup(tmp_path)
    env = stock_environment()
    for key,value in env.items():
        monkeypatch.setenv(key, str(value))
    monkeypatch.setenv('GITHUB_WORKSPACE', str(ROOT))
    monkeypatch.setenv('HITHINK_FINANCE_API_KEY','SYNTHETIC-CLI-CREDENTIAL')
    monkeypatch.delenv('GITHUB_STEP_SUMMARY', raising=False)
    root = tmp_path/'cli'; root.mkdir()
    request = mod['intent'](env, AT.isoformat())
    mod['write'](root/'request.json', request)
    scope = mod['main'].__globals__
    seen = []
    def captured(*args, **kwargs):
        seen.append(kwargs)
        assert kwargs['company_manifest'] == V2 == mod['LIVE_COMPANIES']
        assert kwargs['provenance'] == mod['PUBLIC']
        return {'status':mod['COMPLETE']}
    monkeypatch.setitem(scope, 'capture', captured)
    monkeypatch.setitem(scope, 'bound_state', lambda *args:None)
    assert mod['main'](['capture','--root',str(root)]) == 0
    assert len(seen) == 1  # No provider call: only CLI routing is under test here.
