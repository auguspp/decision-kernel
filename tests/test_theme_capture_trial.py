from __future__ import annotations

import json
import runpy
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import theme_radar_probe as probe
from decision_kernel.runtime.hithink_dump_trial import DumpTrialError
from decision_kernel.runtime.sector_radar_state import serialize_sector_radar_market_state
from test_theme_radar_probe import fixture, PLANNED, THEMES, choices
from test_sector_radar_audit import prohibit_network

SCRIPT = Path('.github/scripts/capture-theme-probe.py').resolve()
WORKFLOW = Path('.github/workflows/hithink-stock-dump-trial.yml')


def code():
    return runpy.run_path(str(SCRIPT), run_name='test_theme_capture')


@pytest.fixture(autouse=True)
def blocked_network(monkeypatch):
    prohibit_network(monkeypatch)


def prepared(tmp_path, mutate=None):
    mod = code(); state, inputs = fixture()
    if mutate:
        mutate(inputs)
    selected = {'schema_version': 1, 'purpose': 'Synthetic acceptance only',
        'themes': [{k: t[k] for k in ('name', 'reason')} for t in THEMES], 'industries': choices(state)}
    bodies = [inputs['concept_catalog'], inputs['industry_catalog'], *inputs['captures'].values()]
    lookup = {(r['path'], canonical_json(r['params'])): r['response'] for r in bodies}
    clock = iter(PLANNED + timedelta(seconds=i) for i in range(100))
    calls, pauses = [], []
    output = tmp_path / 'capture'

    def transport(path, params):
        if len(calls) >= 2:
            assert (output / 'plan.json').is_file(), 'plan must precede detail request'
        calls.append((path, params))
        return (json.dumps(lookup[(path, canonical_json(params))], ensure_ascii=False) + '\n').encode()

    def run(**overrides):
        return mod['capture_trial'](state, selected, output, context={'test': 'synthetic'},
            api_key='synthetic-secret-must-not-be-retained', transport=overrides.get('transport', transport),
            now=lambda: next(clock), pause=pauses.append)
    return mod, state, selected, inputs, output, calls, pauses, run


def test_full_raw_capture_reuses_probe_and_rebuilds_without_network(tmp_path):
    mod, state, _, inputs, output, calls, pauses, run = prepared(tmp_path)
    before = serialize_sector_radar_market_state(state)
    report = run()
    assert report['status'] == mod['COMPLETE'], report['failure']
    assert report['provenance'] == probe.SYNTHETIC
    assert len(calls) == report['requests_attempted'] == 9
    assert pauses == [20] * 8
    assert before == serialize_sector_radar_market_state(state)
    assert report['events_created'] == report['market_state_writes'] == 0
    result = mod['verify_capture'](output)
    assert result['status'] == 'ORIGINAL_RESPONSES_PLAN_AND_PAGE_REBUILT'
    assert result['network_calls'] == 0
    for entry in report['requests']:
        raw = (output / entry['response_file']).read_bytes()
        assert raw.endswith(b'\n')
        assert entry['http_status'] == 200 and entry['error_type'] is None
    page = (output / 'index.html').read_text()
    assert 'NOT RESEARCH' in page and 'Synthetic theme 1' in page


def test_decimal_lexemes_and_duplicate_or_nonfinite_json():
    mod = code()
    assert mod['decode'](b'{"x": 123456789.123456789}')['x'] == Decimal('123456789.123456789')
    for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'[]'):
        with pytest.raises(ValueError):
            mod['decode'](raw)


@pytest.mark.parametrize('change', ['missing', 'ambiguous', 'industry_drift'])
def test_catalog_selection_never_guesses_or_queries_prices(tmp_path, change):
    def mutate(x):
        if change == 'missing':
            x['concept_catalog']['response']['data']['item'][0]['name'] = 'Different label'
        elif change == 'ambiguous':
            x['concept_catalog']['response']['data']['item'].append({'thscode':'886099.TI', 'name':THEMES[0]['name']})
        else:
            x['industry_catalog']['response']['data']['item'][0]['name'] = 'Renamed industry'
    mod, _, _, _, output, calls, _, run = prepared(tmp_path, mutate)
    report = run()
    assert report['status'] == mod['FAILED'] and len(calls) == 2
    assert not (output / 'plan.json').exists() and not (output / 'index.html').exists()
    assert mod['verify_capture'](output)['status'] == 'RETAINED_BYTES_ONLY_INCOMPLETE_CAPTURE'


@pytest.mark.parametrize('status', [401, 403, 429, 500])
def test_http_failures_stop_once_and_never_record_credentials(tmp_path, status):
    mod, _, _, _, output, _, pauses, run = prepared(tmp_path)
    attempts = []
    def rejected(path, params):
        attempts.append(path)
        raise DumpTrialError('HTTP_REJECTED', http_status=status)
    report = run(transport=rejected)
    assert report['status'] == mod['FAILED'] and len(attempts) == 1 and pauses == []
    assert report['requests'][0]['http_status'] == status
    assert report['requests'][0]['response_file'] is None
    assert not (output / 'index.html').exists()
    assert mod['verify_capture'](output)['capture_status'] == mod['FAILED']
    assert all(b'synthetic-secret-must-not-be-retained' not in p.read_bytes() for p in output.rglob('*') if p.is_file())


def test_bad_market_data_keeps_raw_but_never_creates_a_success_page(tmp_path):
    def mutate(x):
        x['captures']['history:886001.TI']['response']['data']['item'][-1]['close_price'] = 'NaN'
    mod, _, _, _, output, calls, _, run = prepared(tmp_path, mutate)
    report = run()
    assert report['status'] == mod['FAILED'] and len(calls) == 9
    assert (output / 'supplied-input.json').exists()
    assert not (output / 'index.html').exists()
    assert mod['verify_capture'](output)['status'] == 'RETAINED_BYTES_ONLY_INCOMPLETE_CAPTURE'


def test_credential_echo_is_not_retained_even_in_failure(tmp_path):
    mod, _, _, _, output, _, _, run = prepared(tmp_path)
    report = run(transport=lambda *a: b'{"message":"synthetic-secret-must-not-be-retained"}')
    assert report['status'] == mod['FAILED']
    assert all(b'synthetic-secret-must-not-be-retained' not in p.read_bytes() for p in output.rglob('*') if p.is_file())


@pytest.mark.parametrize('target', ['index.html', 'market-state.json', 'responses/01.json', 'capture.json', 'extra.json'])
def test_saved_byte_drift_and_extra_files_fail_verification(tmp_path, target):
    mod, _, _, _, output, _, _, run = prepared(tmp_path)
    assert run()['status'] == mod['COMPLETE']
    path = output / target
    path.write_bytes((path.read_bytes() if path.exists() else b'') + b'\n')
    if target == 'capture.json':
        # Whitespace in the outer receipt is not semantic tampering; change its actual status.
        value = json.loads(path.read_text()); value['status'] = 'OTHER'
        path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        mod['verify_capture'](output)


def test_rehashed_derived_page_is_not_a_substitute_for_raw_reconstruction(tmp_path):
    mod, _, _, _, output, _, _, run = prepared(tmp_path)
    assert run()['status'] == mod['COMPLETE']
    p = output / 'index.html'; p.write_text('fabricated page')
    receipt = json.loads((output / 'capture.json').read_text())
    receipt['files']['index.html'] = mod['digest'](p.read_bytes())
    receipt['capture_hash'] = canonical_hash({k:v for k,v in receipt.items() if k!='capture_hash'})
    (output / 'capture.json').write_text(canonical_json(receipt))
    with pytest.raises(ValueError, match='offline theme'):
        mod['verify_capture'](output)


def test_existing_output_not_overwritten(tmp_path):
    _, _, _, _, output, _, _, run = prepared(tmp_path)
    output.mkdir(); (output / 'sentinel').write_text('keep')
    with pytest.raises(FileExistsError):
        run()
    assert (output / 'sentinel').read_text() == 'keep'


def environment():
    return {'GITHUB_REPOSITORY':'auguspp/decision-kernel', 'GITHUB_WORKFLOW':'hithink-stock-dump-trial',
        'GITHUB_REF':'refs/heads/main','GITHUB_EVENT_NAME':'push','GITHUB_RUN_ATTEMPT':'1',
        'GITHUB_RUN_ID':'123','GITHUB_SHA':'a'*40}


@pytest.mark.parametrize('field,value', [('GITHUB_REF','refs/heads/test'),('GITHUB_RUN_ATTEMPT','2'),
    ('GITHUB_EVENT_NAME','schedule'),('GITHUB_REPOSITORY','other/repo'),('GITHUB_SHA','main')])
def test_execution_requires_exact_reviewed_workflow(field, value):
    env = environment(); env[field] = value
    with pytest.raises(ValueError): code()['workflow_identity'](env)


def test_actual_fixed_sample_and_workflow_do_not_enable_production_or_redownload_dump():
    mod = code(); mod['validate_selection'](json.loads(Path('radar_inputs/theme-probe-sample-v0.json').read_text()))
    text = WORKFLOW.read_text()
    assert "if: github.event_name == 'workflow_dispatch' && inputs.trial-purpose == 'stock-dump'" in text
    assert "options: [stock-dump, theme-probe]" in text
    assert "default: stock-dump" in text
    theme = text.split('  theme-probe:\n',1)[1]
    assert "pip install -e '.[dump-study,discovery]'" in theme
    assert 'capture-theme-probe.py capture' in theme and 'capture-theme-probe.py verify' in theme
    assert 'if: always()' in theme and 'retention-days: 90' in theme
    assert theme.count('${{ secrets.HITHINK_FINANCE_API_KEY }}') == 1
    for word in ('schedule:', 'actions/cache', 'sector_radar_producer', 'decision-state/', 'continue-on-error'):
        assert word not in text
