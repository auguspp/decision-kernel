from __future__ import annotations

import copy
import hashlib
import json
from datetime import timedelta
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import theme_radar_probe as probe
from decision_kernel.runtime.hithink_dump_trial import DumpTrialError
from decision_kernel.runtime.sector_radar_state import serialize_sector_radar_market_state
from test_sector_radar_audit import prohibit_network
from test_theme_capture_trial import code, environment
from test_theme_radar_probe import fixture, PLANNED, THEMES, choices
from test_theme_source_discovery import source

SOURCE_PATH = 'radar_inputs/company-evidence/synthetic.json'


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def prepared(tmp_path, text=None):
    mod = code(); state, captures = fixture()
    row = source(text or 'Discuss ' + ' and '.join(t['name'] for t in THEMES))
    doc = {'semantics': 'COMPANY_EVIDENCE_ONLY_NOT_RESEARCH_OR_JUDGMENT',
           'recorded_at': row['recorded_at'],
           'company_identity': {'ticker': '000001', 'exchange': 'SZSE', 'company_name': 'Synthetic'},
           'evidence_artifacts': [row['evidence']]}
    documents = {SOURCE_PATH: mod['data'](doc)}
    selection = {'schema_version': 2, 'purpose': 'Synthetic declared text scope, not real news.',
                 'industries': choices(state), 'source_files': [
                     {'path': SOURCE_PATH, 'blob_sha': blob(documents[SOURCE_PATH]),
                      'records': [{'evidence_id': row['evidence']['id'], 'text_fields': row['text_fields']}]}]}
    bodies = [captures['concept_catalog'], captures['industry_catalog'], *captures['captures'].values()]
    lookup = {(r['path'], canonical_json(r['params'])): r['response'] for r in bodies}
    calls, pauses = [], []
    output = tmp_path / 'capture'
    clock = iter(PLANNED + timedelta(seconds=i) for i in range(100))

    def transport(path, params):
        if len(calls) >= 2:
            scan = json.loads((output / 'source-discovery.json').read_text())
            plan = json.loads((output / 'plan.json').read_text())
            assert (output / 'sources/01.json').read_bytes() == documents[SOURCE_PATH]
            assert scan['acquisition_plan'] == plan
            assert all(scan['projection_hash'] in t['reason'] for t in plan['themes'])
            assert any(r['path'] == path and r['params'] == params for r in plan['requests'])
        calls.append((path, params))
        if path == probe.SNAPSHOT:
            body = copy.deepcopy(captures['captures']['snapshot']['response'])
            requested = params['thscodes'].split(',')
            body['data']['item'] = [r for r in body['data']['item'] if r['thscode'] in requested]
            body['data']['total'] = len(requested)
        else:
            body = lookup[(path, canonical_json(params))]
        return (json.dumps(body, ensure_ascii=False) + '\n').encode()

    def run(override=None):
        return mod['capture_trial'](state, selection, output, context=environment(),
            api_key='not-a-real-secret', source_documents=documents,
            transport=override or transport, now=lambda: next(clock), pause=pauses.append)
    return mod, state, captures, doc, documents, selection, output, calls, pauses, run


def replace_document(mod, doc, documents, selection):
    documents[SOURCE_PATH] = mod['data'](doc)
    selection['source_files'][0]['blob_sha'] = blob(documents[SOURCE_PATH])


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    prohibit_network(monkeypatch)


def test_sources_then_complete_catalog_scan_then_frozen_plan_then_existing_probe(tmp_path):
    mod, state, captures, _, documents, selection, output, calls, pauses, run = prepared(tmp_path)
    before = serialize_sector_radar_market_state(state), canonical_json(selection), documents[SOURCE_PATH]
    result = run()
    assert result['status'] == mod['COMPLETE'], result['failure']
    assert result['requests_attempted'] == len(calls) == 9 and pauses == [20] * 8
    assert mod['verify_capture'](output)['status'] == 'ORIGINAL_SOURCES_SCAN_PLAN_AND_PAGE_REBUILT'
    assert before == (serialize_sector_radar_market_state(state), canonical_json(selection), documents[SOURCE_PATH])
    assert (output / 'sources/01.json').read_bytes() == documents[SOURCE_PATH]
    scan = json.loads((output / 'source-discovery.json').read_text())
    assert scan['requests_executed'] == 0 and len(scan['projection']['leads']) == 2
    result_probe = json.loads((output / 'theme-probe.json').read_text())
    original = probe.build_theme_probe(state, captures, as_of=(PLANNED + timedelta(minutes=8)).isoformat(),
                                       generated_at=(PLANNED + timedelta(minutes=8)).isoformat())
    for a, b in zip(result_probe['projection']['themes'], original['projection']['themes']):
        assert a['path'] == b['path'] and a['current_membership'] == b['current_membership']
    assert result['market_state_writes'] == result['events_created'] == 0
    assert result['investment_authority'] == result['research_authority'] == 'NONE'


def test_denial_is_a_source_lead_not_business_benefit(tmp_path):
    mod, _, _, _, _, _, output, calls, _, run = prepared(tmp_path, f'We deny exposure to {THEMES[0]["name"]}.')
    assert run()['status'] == mod['COMPLETE']
    scan = json.loads((output / 'source-discovery.json').read_text())
    assert len(scan['projection']['leads']) == 1 and len(calls) == 7
    assert 'deny exposure' in scan['projection']['leads'][0]['mentions'][0]['context']
    assert scan['projection']['sentiment'] == 'NOT_INFERRED'
    assert mod['verify_capture'](output)['capture_status'] == mod['COMPLETE']


def test_no_literal_match_is_a_scoped_scan_not_a_theme_capture(tmp_path):
    mod, _, _, _, _, _, output, calls, pauses, run = prepared(tmp_path, 'No catalog labels here.')
    result = run()
    assert result['status'] == mod['NO_LEADS'] and len(calls) == 2 and pauses == [20]
    assert (output / 'source-discovery.html').is_file()
    assert not any((output / p).exists() for p in ('plan.json', 'index.html', 'theme-probe.json'))
    assert mod['verify_capture'](output)['status'] == 'ORIGINAL_SOURCES_CATALOGS_SCAN_REBUILT_NO_DETAIL_REQUESTS'


@pytest.mark.parametrize('reason', ['budget', 'ambiguous', 'no_text'])
def test_all_leads_retained_but_no_partial_plan(tmp_path, reason):
    mod, _, captures, doc, documents, selection, output, calls, _, run = prepared(tmp_path)
    if reason == 'budget':
        for i in (3, 4):
            label = f'Synthetic theme {i}'
            captures['concept_catalog']['response']['data']['item'].append({'thscode':f'88600{i}.TI', 'name':label})
            doc['evidence_artifacts'][0]['permitted_excerpt'] += ' and ' + label
        replace_document(mod, doc, documents, selection)
    elif reason == 'ambiguous':
        captures['concept_catalog']['response']['data']['item'].append({'thscode':'886099.TI','name':THEMES[0]['name']})
    else:
        selection['source_files'][0]['records'][0]['text_fields'] = []
    result = run()
    assert result['status'] == mod['FAILED'] and len(calls) == 2
    assert (output / 'source-discovery.html').exists() and not (output / 'plan.json').exists()
    scan = json.loads((output / 'source-discovery.json').read_text())
    if reason == 'budget':
        assert len(scan['projection']['leads']) == 4 and 'ACQUISITION_BUDGET_EXCEEDED' in scan['acquisition_blockers']
    assert mod['verify_capture'](output)['status'] == 'SOURCE_SCAN_REBUILT_CAPTURE_STILL_INCOMPLETE'


@pytest.mark.parametrize('reason', ['blob', 'record_id', 'field', 'future', 'duplicate_id', 'missing_file'])
def test_invalid_originals_stop_before_any_provider_request(tmp_path, reason):
    mod, _, _, doc, documents, selection, output, calls, _, run = prepared(tmp_path)
    if reason == 'blob': documents[SOURCE_PATH] += b'\n'
    elif reason == 'record_id': selection['source_files'][0]['records'][0]['evidence_id'] = 'absent'
    elif reason == 'field': selection['source_files'][0]['records'][0]['text_fields'] = [['source_identifier']]
    elif reason == 'future':
        doc['recorded_at'] = (PLANNED + timedelta(days=1)).isoformat()
        replace_document(mod, doc, documents, selection)
    elif reason == 'duplicate_id':
        doc['evidence_artifacts'].append(copy.deepcopy(doc['evidence_artifacts'][0]))
        replace_document(mod, doc, documents, selection)
    else: documents.clear()
    assert run()['status'] == mod['FAILED'] and calls == []
    assert not (output / 'plan.json').exists()
    assert mod['verify_capture'](output)['status'] == 'RETAINED_BYTES_ONLY_INCOMPLETE_CAPTURE'


@pytest.mark.parametrize('target', ['sources/01.json', 'source-input.json', 'source-discovery.json', 'source-discovery.html', 'plan.json'])
def test_rehashed_sidecars_cannot_replace_original_source_reconstruction(tmp_path, target):
    mod, _, _, _, _, _, output, _, _, run = prepared(tmp_path)
    assert run()['status'] == mod['COMPLETE']
    path = output / target
    if target.endswith('.html'):
        path.write_text('fabricated page')
    elif target == 'source-discovery.json':
        value = json.loads(path.read_text()); value['projection']['sentiment'] = 'POSITIVE'
        path.write_text(canonical_json(value))
    else:
        path.write_bytes(path.read_bytes() + b'\n')
    receipt = json.loads((output / 'capture.json').read_text())
    receipt['files'][target] = mod['digest'](path.read_bytes())
    receipt['capture_hash'] = canonical_hash({k:v for k,v in receipt.items() if k!='capture_hash'})
    (output / 'capture.json').write_bytes(mod['data'](receipt))
    with pytest.raises(ValueError): mod['verify_capture'](output)


def test_http_refusal_after_plan_never_retries_or_publishes_market_page(tmp_path):
    mod, _, captures, _, _, _, output, _, pauses, run = prepared(tmp_path)
    attempts = []
    def transport(path, params):
        attempts.append((path, params))
        if len(attempts) <= 2:
            name = 'concept_catalog' if params['tag'] == 'cn_concept' else 'industry_catalog'
            return json.dumps(captures[name]['response']).encode()
        assert (output / 'source-discovery.json').exists() and (output / 'plan.json').exists()
        raise DumpTrialError('HTTP_REJECTED', http_status=429)
    result = run(transport)
    assert result['status'] == mod['FAILED'] and len(attempts) == 3 and pauses == [20,20]
    assert result['requests'][-1]['http_status'] == 429 and not (output / 'index.html').exists()
    assert mod['verify_capture'](output)['status'] == 'SOURCE_SCAN_REBUILT_CAPTURE_STILL_INCOMPLETE'


def test_actual_sample_reads_existing_exact_fields_without_new_evidence_or_named_themes():
    mod = code()
    selection = json.loads(Path('radar_inputs/theme-source-sample-v0.json').read_text())
    documents = {item['path']: Path(item['path']).read_bytes() for item in selection['source_files']}
    rows = mod['selected_sources'](selection, documents, cutoff='2026-09-06T03:00:00+00:00')
    assert len(rows) == 2 and sum(len(r['text_fields']) for r in rows) == 5
    assert 'themes' not in selection and selection['schema_version'] == 2
    assert all(r['evidence']['retention_mode'] == 'EXTRACTED_VALUES' and r['evidence']['replayability_level'] == 'PARTIAL' for r in rows)
    assert all(r['recorded_at'] == '2026-09-06T00:03:48.879155+00:00' for r in rows)
    for r in rows:
        for field in r['text_fields']:
            assert isinstance(r['evidence'][field[0]][field[1]], str)


def test_workflow_keeps_fixed_name_and_dump_manual_and_current_source_push_bounded():
    text = Path('.github/workflows/hithink-stock-dump-trial.yml').read_text()
    assert 'options: [stock-dump, theme-probe, theme-source, native-feed-acceptance]' in text
    assert 'default: stock-dump' in text
    assert 'selection=radar_inputs/theme-source-sample-v0.json' in text
    assert '[ "$GITHUB_EVENT_NAME" = workflow_dispatch ] && [ "$TRIAL_PURPOSE" = theme-probe ]' in text
    assert "and Path('theme-probe-trial/capture/index.html').is_file()" in text
    assert 'source-discovery.html' in text
    for forbidden in ('schedule:', 'actions/cache', 'sector_radar_producer', 'continue-on-error', 'contents: write'):
        assert forbidden not in text
