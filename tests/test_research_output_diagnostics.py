"""Native validation diagnostics only: no repaired output or provider request."""
from copy import deepcopy
import json
from pathlib import Path
import socket

import pytest
from pydantic import ValidationError
from pydantic_core import PydanticCustomError

from decision_kernel.runtime import saved_research_once as once
from test_saved_research_raw_retention import mock_stream, prompt_for, bad_text
from test_saved_research_once import pre, quick

REVIEW = Path('docs/readings/000920-continuation-review-2026-09-21')


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*a, **kw):
        raise AssertionError('diagnostics regression must not access networking')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


def test_real_invalid_response_remains_invalid_with_exact_three_locations():
    raw = (REVIEW / 'pre-model-output.txt').read_bytes()
    assert once.sha(raw) == '81723ae6148f3df114948b2618a9c3512f26df0e22068093be2ea2676bbda4b0'
    with pytest.raises(ValidationError) as caught:
        once.PreResearchResult.model_validate(once.identity._json(raw))
    report = once._application_validation_diagnostic(caught.value, once.PreResearchResult)
    assert report['error_count'] == 3 and report['omitted_error_count'] == 0
    assert report['errors'] == [{'type': 'enum', 'loc': ['material_claims', i, 'kind']}
                                for i in (15, 16, 17)]
    assert report['status'] == 'REJECTED_BY_ORIGINAL_MODEL'
    assert (REVIEW / 'pre-model-output.txt').read_bytes() == raw
    assert json.loads((REVIEW / 'validation.json').read_bytes())['funnel_result'] is None


@pytest.mark.parametrize('model,field', [(once.PreResearchResult, 'material_claims'),
                                        (once.QuickResearchResult, 'supporting_claims')])
def test_secret_values_messages_context_urls_and_extra_keys_are_not_reported(model, field):
    value = (pre(prompt_for('pre')) if model is once.PreResearchResult else quick(prompt_for('quick'))).model_dump(mode='json')
    value[field][0]['kind'] = 'PRIVATE_VALUE_DO_NOT_LOG'
    value['PRIVATE_FIELD_DO_NOT_LOG'] = 'PRIVATE_SECRET'
    unchanged = deepcopy(value)
    with pytest.raises(ValidationError) as caught:
        model.model_validate(value)
    report = once._application_validation_diagnostic(caught.value, model)
    expected = [{'type': 'enum', 'loc': [field, 0, 'kind']}]
    if model is once.PreResearchResult:
        # Original Pydantic also reports the required claim tuple as empty.
        expected.append({'type': 'too_short', 'loc': [field]})
    expected.append({'type': 'extra_forbidden', 'loc': ['REDACTED']})
    assert report['error_count'] == len(expected) and report['errors'] == expected
    text = json.dumps(report)
    assert all(x not in text for x in ('PRIVATE', 'https://', '"input"', '"msg"', '"ctx"', '"url"'))
    assert value == unchanged


def test_many_errors_have_explicit_count_not_silent_truncation():
    value = pre(prompt_for('pre')).model_dump(mode='json')
    value.update({f'PRIVATE_FIELD_{i}': 'PRIVATE_VALUE' for i in range(75)})
    with pytest.raises(ValidationError) as caught:
        once.PreResearchResult.model_validate(value)
    report = once._application_validation_diagnostic(caught.value, once.PreResearchResult)
    assert report['error_count'] == 75 and len(report['errors']) == 20
    assert report['omitted_error_count'] == 55 and len(json.dumps(report)) < 2048
    assert 'PRIVATE' not in json.dumps(report)


@pytest.mark.parametrize('loc,expected', [
    (('material_claims', 2, 'kind'), ['material_claims', 2, 'kind']),
    (('PRIVATE_KEY', -1, 'PRIVATE_VALUE'), ['REDACTED', 'REDACTED', 'REDACTED']),
    (('material_claims', 1000001, 'kind'), ['material_claims', 'REDACTED', 'kind']),
    (('a', 'b', 'c', 'd', 'e', 'f'), ['REDACTED'] * 4 + ['TRUNCATED']),
    ((), []),
])
def test_native_error_location_redaction_and_depth_bound(loc, expected):
    error = ValidationError.from_exception_data('PRIVATE_TITLE', [{
        'type': 'value_error', 'loc': loc, 'input': 'PRIVATE_INPUT',
        'ctx': {'error': ValueError('PRIVATE_CONTEXT_AND_MESSAGE')}}])
    report = once._application_validation_diagnostic(error, once.PreResearchResult)
    assert report['errors'] == [{'type': 'value_error', 'loc': expected}]
    assert 'PRIVATE' not in json.dumps(report)


def test_custom_error_code_is_not_a_secret_channel():
    error = ValidationError.from_exception_data('PRIVATE_TITLE', [{
        'type': PydanticCustomError('PRIVATE_ERROR_CODE', 'PRIVATE_MESSAGE'),
        'loc': (), 'input': 'PRIVATE_INPUT'}])
    report = once._application_validation_diagnostic(error, once.PreResearchResult)
    assert report['errors'] == [{'type': 'OTHER_VALIDATION_ERROR', 'loc': []}]
    assert 'PRIVATE' not in json.dumps(report)


@pytest.mark.parametrize('error', [RuntimeError('private'), ValueError('private'), TypeError('private')])
def test_non_application_exceptions_are_not_misclassified(error):
    assert once._application_validation_diagnostic(error, once.PreResearchResult) == {}


@pytest.mark.parametrize('stage,model', [('pre', once.PreResearchResult), ('quick', once.QuickResearchResult)])
def test_original_adapter_retains_format_and_rejection_without_retry(tmp_path, monkeypatch, stage, model):
    prompt = prompt_for(stage)
    text = bad_text(prompt, stage, 'route')
    seen, converter = mock_stream(monkeypatch, lambda _: text)
    usage = []
    with pytest.raises(ValidationError):
        once.model_call(stage, prompt, model, tmp_path, usage)
    report = usage[0]
    saved = (tmp_path / report['output_format_file']).read_bytes()
    assert json.loads(saved) == seen[0]['text']['format'] == converter(once.admitted_output_type(model, prompt['evidence_ids']))
    assert once.sha(saved) == report['output_format_sha256']
    assert (tmp_path / (stage + '-model-output.txt')).read_text() == text
    assert report['application_validation']['errors'] == [{'type': 'enum', 'loc': ['route']}]
    assert report['status'] == 'FAILED' and report['provider_status'] == 'completed'
    assert report['phase'] == 'APPLICATION_VALIDATION' and len(seen) == 1


@pytest.mark.parametrize('stage,model', [('pre', once.PreResearchResult), ('quick', once.QuickResearchResult)])
def test_valid_output_is_not_diagnosed_as_failure(tmp_path, monkeypatch, stage, model):
    prompt = prompt_for(stage)
    expected = pre(prompt) if stage == 'pre' else quick(prompt)
    seen, _ = mock_stream(monkeypatch, lambda _: expected.model_dump_json())
    usage = []
    assert once.model_call(stage, prompt, model, tmp_path, usage) == expected
    assert 'application_validation' not in usage[0] and usage[0]['phase'] == 'COMPLETE'
    assert len(seen) == 1 and (tmp_path / usage[0]['output_format_file']).is_file()


@pytest.mark.parametrize('stage,model', [('pre', once.PreResearchResult), ('quick', once.QuickResearchResult)])
def test_existing_format_file_stops_before_provider_without_overwrite(tmp_path, monkeypatch, stage, model):
    prompt = prompt_for(stage); target = tmp_path / (stage + '-output-format.json')
    target.write_bytes(b'PREEXISTING')
    seen, _ = mock_stream(monkeypatch, lambda p: pre(p).model_dump_json())
    usage = []
    with pytest.raises(FileExistsError):
        once.model_call(stage, prompt, model, tmp_path, usage)
    assert seen == [] and target.read_bytes() == b'PREEXISTING'
    assert usage[0]['phase'] == 'REQUEST_RETENTION' and usage[0]['status'] == 'FAILED'
    assert not usage[0]['response_received'] and 'output_format_file' not in usage[0]
    assert 'application_validation' not in usage[0]


def test_diagnostic_failure_does_not_replace_original_validation_error(tmp_path, monkeypatch):
    prompt = prompt_for('pre'); text = bad_text(prompt, 'pre', 'route')
    seen, _ = mock_stream(monkeypatch, lambda _: text)
    def broken(*a): raise RuntimeError('PRIVATE_DIAGNOSTIC_FAILURE')
    monkeypatch.setattr(once, '_application_validation_diagnostic', broken)
    usage = []
    with pytest.raises(ValidationError) as caught:
        once.model_call('pre', prompt, once.PreResearchResult, tmp_path, usage)
    assert caught.value.errors()[0]['type'] == 'enum' and len(seen) == 1
    assert usage[0]['application_validation'] == {'status': 'DIAGNOSTIC_UNAVAILABLE'}
    assert 'PRIVATE' not in json.dumps(usage)


def test_transport_failure_has_no_application_validation_claim(tmp_path, monkeypatch):
    prompt = prompt_for('pre')
    seen, _ = mock_stream(monkeypatch, lambda p: pre(p).model_dump_json(), fail=True)
    usage = []
    with pytest.raises(RuntimeError):
        once.model_call('pre', prompt, once.PreResearchResult, tmp_path, usage)
    assert len(seen) == 1 and usage[0]['phase'] == 'RESPONSE'
    assert 'application_validation' not in usage[0] and not usage[0]['output_text_retained']
    assert (tmp_path / usage[0]['output_format_file']).exists()
