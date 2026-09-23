"""Pinned real SDK over its mock HTTP transport; never a live provider call."""
import json
from pathlib import Path
import socket

import pytest

from decision_kernel.runtime import saved_research_once as once
from test_saved_research_once import pre, quick
from test_saved_research_raw_retention import prompt_for
from test_research_route_contract import historical_wire_without_descriptions

REVIEW = Path('docs/readings/000920-continuation-review-2026-09-21')


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*a, **kw):
        raise AssertionError('only the pinned SDK mock HTTP transport is permitted')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)


def options(provider):
    if provider == 'DEEPSEEK_OFFICIAL':
        return dict(base_url=once.DEEPSEEK_BASE_URL, model=once.DEEPSEEK_MODEL,
                    api_key_env='DEEPSEEK_API_KEY', provider=provider,
                    extra_parameters={'reasoning': {'effort': 'none'}})
    return dict(base_url=once.BASE_URL, model=once.MODEL,
                api_key_env='SUB2API_API_KEY', provider='SUB2API')


def mock_http(monkeypatch, text, provider, *, http_error=False):
    # Deliberately no importorskip or fallback. Full CI installs the pinned SDK.
    import openai as sdk
    import httpx2 as httpx
    part = {'type': 'output_text', 'text': text, 'annotations': []}
    item = {'id': 'msg_fixture', 'type': 'message', 'role': 'assistant',
            'status': 'completed', 'content': [part]}
    final = {'id': 'resp_offline', 'object': 'response', 'created_at': 1789972830,
             'status': 'completed', 'model': options(provider)['model'], 'output': [item],
             'parallel_tool_calls': False, 'tool_choice': 'auto', 'tools': [],
             'error': None, 'incomplete_details': None,
             'usage': {'input_tokens': 1, 'input_tokens_details': {'cached_tokens': 0},
                       'output_tokens': 1, 'output_tokens_details': {'reasoning_tokens': 0},
                       'total_tokens': 2}}
    # Reuse the native SSE event shape already exercised by raw-retention tests.
    events = [
        {'type': 'response.created', 'response': {**final, 'status': 'in_progress', 'output': []}},
        {'type': 'response.output_item.added', 'output_index': 0,
         'item': {**item, 'status': 'in_progress', 'content': []}},
        {'type': 'response.content_part.added', 'output_index': 0, 'content_index': 0,
         'item_id': 'msg_fixture', 'part': {**part, 'text': ''}},
        {'type': 'response.output_text.delta', 'output_index': 0, 'content_index': 0,
         'item_id': 'msg_fixture', 'delta': text},
        {'type': 'response.output_text.done', 'output_index': 0, 'content_index': 0,
         'item_id': 'msg_fixture', 'text': text},
        {'type': 'response.content_part.done', 'output_index': 0, 'content_index': 0,
         'item_id': 'msg_fixture', 'part': part},
        {'type': 'response.output_item.done', 'output_index': 0, 'item': item},
        {'type': 'response.completed', 'response': final}]
    data = ''.join('data: ' + json.dumps({**e, 'sequence_number': i}) + '\n\n'
                   for i, e in enumerate(events)).encode()
    seen = []
    def transport(request):
        body = json.loads(request.content)
        assert str(request.url) == options(provider)['base_url'] + '/responses'
        seen.append(body)
        if http_error:
            return httpx.Response(400, json={'error': {'type': 'invalid_request_error',
                'code': 'invalid_json_schema', 'message': 'PRIVATE_PROVIDER_MESSAGE'}},
                headers={'x-request-id': 'offline_request'})
        return httpx.Response(200, headers={'content-type': 'text/event-stream'}, content=data)
    monkeypatch.setattr(sdk, 'DefaultHttpxClient', lambda **kw: httpx.Client(
        transport=httpx.MockTransport(transport), **kw))
    monkeypatch.setenv(options(provider)['api_key_env'], 'SYNTHETIC_KEY_NEVER_RETAIN')
    return seen


def check_wire(provider, prompt, model, usage, seen, root):
    assert len(seen) == len(usage) == 1
    body, schema, original_format, original_parameters = once.model_request(
        prompt, model, max_prompt_bytes=524288,
        model=options(provider)['model'], extra_parameters=options(provider).get('extra_parameters'))
    expected_format = original_format if provider == 'SUB2API' else {
        k: v for k, v in original_format.items() if k != 'strict'}
    expected_parameters = {**original_parameters, 'text': {'format': expected_format}, 'stream': True}
    assert seen[0] == expected_parameters  # Actual SDK HTTP JSON, not a mocked request builder.
    saved = (root / usage[0]['output_format_file']).read_bytes()
    assert json.loads(saved) == seen[0]['text']['format'] == expected_format
    assert once.sha(saved) == usage[0]['output_format_sha256']
    assert usage[0]['output_model_schema_sha256'] == once.sha(once.raw(schema))
    assert usage[0]['input_sha256'] == once.sha(body.encode())
    assert usage[0]['system_sha256'] == once.sha(once.SYSTEM.encode())
    assert seen[0]['tools'] == [] and seen[0]['store'] is False
    assert seen[0]['max_output_tokens'] == 6000
    assert 'SYNTHETIC_KEY' not in saved.decode() + json.dumps(usage)
    definitions = expected_format['schema']['$defs']
    assert definitions['ResearchClaimKind']['enum'] == ['FACT', 'INFERENCE', 'ASSUMPTION', 'MARKET_CONTEXT']
    assert definitions['ResearchClaim']['properties']['evidence_artifact_ids']['items']['enum'] == prompt['evidence_ids']
    assert ('strict' in expected_format) == (provider == 'SUB2API')


@pytest.mark.parametrize('provider', ['DEEPSEEK_OFFICIAL', 'SUB2API'])
def test_real_invalid_output_over_original_sdk_wire_keeps_exact_constraints(tmp_path, monkeypatch, provider):
    from pydantic import ValidationError
    packet = json.loads((REVIEW / 'input.json').read_bytes())
    prompt = {'evidence_ids': [e['id'] for e in packet['seed_evidence_artifacts']],
              'binding': {'discovery_id': packet['execution_id'], 'as_of': packet['research_cutoff']}}
    text = (REVIEW / 'pre-model-output.txt').read_text()
    seen = mock_http(monkeypatch, text, provider)
    usage = []
    with pytest.raises(ValidationError):
        once.model_call('pre', prompt, once.PreResearchResult, tmp_path, usage,
                        max_prompt_bytes=524288, **options(provider))
    check_wire(provider, prompt, once.PreResearchResult, usage, seen, tmp_path)
    if provider == 'DEEPSEEK_OFFICIAL':
        historical = json.loads((REVIEW / 'host-receipt.json').read_bytes())['provider_usage'][0]
        # New descriptions legitimately change format hashes; reconstruct the old
        # wire with the same SDK rather than rewriting the historical receipt.
        with historical_wire_without_descriptions(monkeypatch):
            _, old_schema, old_format, _ = once.model_request(
                prompt, once.PreResearchResult, max_prompt_bytes=524288,
                model=once.DEEPSEEK_MODEL, extra_parameters={'reasoning': {'effort': 'none'}})
        old_format = {k: v for k, v in old_format.items() if k != 'strict'}
        assert once.sha(once.raw(old_format)) == historical['output_format_sha256']
        assert once.sha(once.raw(old_schema)) == historical['output_model_schema_sha256']
        assert usage[0]['output_format_sha256'] != historical['output_format_sha256']
        assert usage[0]['output_model_schema_sha256'] != historical['output_model_schema_sha256']
        assert usage[0]['system_sha256'] == historical['system_sha256']
    assert usage[0]['application_validation']['errors'] == [
        {'type': 'enum', 'loc': ['material_claims', i, 'kind']} for i in (15, 16, 17)]
    assert usage[0]['phase'] == 'APPLICATION_VALIDATION' and usage[0]['status'] == 'FAILED'
    assert (tmp_path / 'pre-model-output.txt').read_text() == text
    assert not (tmp_path / 'pre.json').exists() and not list(tmp_path.glob('quick*'))


@pytest.mark.parametrize('provider', ['DEEPSEEK_OFFICIAL', 'SUB2API'])
@pytest.mark.parametrize('stage,model', [('pre', once.PreResearchResult), ('quick', once.QuickResearchResult)])
def test_valid_original_stage_and_wire_are_unchanged(tmp_path, monkeypatch, provider, stage, model):
    prompt = prompt_for(stage)
    result = pre(prompt) if stage == 'pre' else quick(prompt)
    seen = mock_http(monkeypatch, result.model_dump_json(), provider)
    usage = []
    assert once.model_call(stage, prompt, model, tmp_path, usage,
                            max_prompt_bytes=524288, **options(provider)) == result
    check_wire(provider, prompt, model, usage, seen, tmp_path)
    assert usage[0]['phase'] == 'COMPLETE' and 'application_validation' not in usage[0]


def test_http_error_is_not_misreported_as_application_rejection_or_retried(tmp_path, monkeypatch):
    import openai as sdk
    provider = 'DEEPSEEK_OFFICIAL'; prompt = prompt_for('pre')
    seen = mock_http(monkeypatch, '', provider, http_error=True)
    usage = []
    with pytest.raises(sdk.BadRequestError):
        once.model_call('pre', prompt, once.PreResearchResult, tmp_path, usage,
                        max_prompt_bytes=524288, **options(provider))
    check_wire(provider, prompt, once.PreResearchResult, usage, seen, tmp_path)
    assert usage[0]['phase'] == 'RESPONSE' and usage[0]['http_status'] == 400
    assert usage[0]['provider_error_code'] == 'invalid_json_schema'
    assert not usage[0]['response_received'] and 'application_validation' not in usage[0]
    assert 'PRIVATE_PROVIDER_MESSAGE' not in json.dumps(usage)
    assert not (tmp_path / 'pre-model-output.txt').exists()
