"""Synthetic returned-text failures, not reconstructed CATL output or live calls."""
from copy import deepcopy
import json
import os
import sys
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import saved_research_once as w
from decision_kernel.research_funnel import PreResearchResult, QuickResearchResult
from test_saved_research_once import fixture, pre, quick


def format_converter(monkeypatch):
    """Real pinned SDK converter in CI; a labelled local-only schema transport seam."""
    try:
        from openai.lib._parsing._responses import type_to_text_format_param
    except ImportError:
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            pytest.fail('declared pinned SDK converter unavailable in CI')
        def type_to_text_format_param(model):
            return {'type': 'json_schema', 'strict': True, 'name': model.__name__,
                    'schema': model.model_json_schema()}
        monkeypatch.setitem(sys.modules, 'openai.lib._parsing._responses', SimpleNamespace(
            type_to_text_format_param=type_to_text_format_param))
    return type_to_text_format_param


def mock_stream(monkeypatch, response_text, *, fail=False, status='completed'):
    converter = format_converter(monkeypatch)
    seen = []
    class Client:
        def __init__(self, **kw):
            assert kw['max_retries'] == 0 and kw['timeout'] == 180
            assert kw['base_url'] == w.BASE_URL
            assert kw['http_client']['follow_redirects'] is False
            self.responses = self
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def stream(self, **kw):
            seen.append(kw)
            assert kw['tools'] == [] and kw['store'] is False
            assert kw['max_output_tokens'] == 6000
            value = json.loads(kw['input'][0]['content'])
            text = response_text(value)
            class Stream:
                def __enter__(self): return self
                def __exit__(self, *_): pass
                def get_final_response(self):
                    if fail:
                        raise RuntimeError('SECRET_TRANSPORT_EXCEPTION_NOT_FOR_RECEIPT')
                    # Same fixture models the old eager parse and the explicit-format path.
                    if 'text_format' in kw:
                        kw['text_format'].model_validate_json(text)
                    return SimpleNamespace(output_text=text, status=status, id='synthetic-response',
                        usage=SimpleNamespace(model_dump=lambda **_: {'total_tokens': 2}),
                        output=[SimpleNamespace(type='reasoning', content='PRIVATE_REASONING_NOT_RETAINED')])
            return Stream()
    monkeypatch.setitem(sys.modules, 'openai', SimpleNamespace(
        OpenAI=Client, DefaultHttpxClient=lambda **kw: kw))
    monkeypatch.setenv('SUB2API_API_KEY', 'synthetic-only')
    return seen, converter


def prompt_for(stage):
    packet, discovery, _ = fixture()
    prompt = {'binding': {'discovery_id': discovery.discovery_id, 'as_of': discovery.as_of.isoformat()},
              'evidence_ids': [str(packet.seed_evidence_artifacts[0].id)]}
    if stage == 'quick': prompt['pre_research_hash'] = w.canonical_hash(pre(prompt, 'CONTINUE_TO_QUICK'))
    return prompt


def bad_text(prompt, stage, defect):
    value = (pre(prompt) if stage == 'pre' else quick(prompt)).model_dump(mode='json')
    if defect == 'json': return '{"route":'
    if defect == 'missing': del value['route_reason']
    elif defect == 'route': value['route'] = 'BUY'
    elif defect == 'extra': value['position_size'] = 1
    elif defect == 'fact':
        field = 'material_claims' if stage == 'pre' else 'supporting_claims'
        value[field][0]['evidence_artifact_ids'] = []
    return json.dumps(value, ensure_ascii=False)


@pytest.mark.parametrize('stage,model', [('pre', PreResearchResult), ('quick', QuickResearchResult)])
@pytest.mark.parametrize('defect', ['json', 'missing', 'route', 'extra', 'fact'])
def test_rejected_application_output_is_retained_before_original_validation(tmp_path, monkeypatch, stage, model, defect):
    prompt = prompt_for(stage); text = bad_text(prompt, stage, defect)
    seen, converter = mock_stream(monkeypatch, lambda _: text)
    usage = []
    with pytest.raises(ValueError): w.model_call(stage, prompt, model, tmp_path, usage)
    assert (tmp_path / (stage+'-model-output.txt')).read_text() == text
    assert usage[0]['usage'] == {'total_tokens': 2}
    assert usage[0]['output_sha256'] == w.sha(text.encode())
    assert usage[0]['response_received'] and usage[0]['output_text_retained']
    assert usage[0]['provider_status'] == 'completed' and usage[0]['phase'] == 'APPLICATION_VALIDATION'
    assert usage[0]['status'] == 'FAILED' and len(seen) == 1
    assert 'text_format' not in seen[0]
    assert seen[0]['text']['format'] == converter(w.admitted_output_type(model, prompt['evidence_ids']))
    assert 'PRIVATE_REASONING_NOT_RETAINED' not in '\n'.join(p.read_text() for p in tmp_path.iterdir())


def test_failure_before_response_does_not_claim_raw_or_usage(tmp_path, monkeypatch):
    p, d, context = fixture()
    seen, _ = mock_stream(monkeypatch, lambda v: pre(v).model_dump_json(), fail=True)
    candidate, result, usage = w.research(p, d, context, tmp_path)
    assert result.status.value == 'EXECUTION_GAP' and candidate.pre_research is None
    assert len(seen) == 1 and len(usage) == 1
    assert not (tmp_path/'pre-model-output.txt').exists()
    assert 'Raw output retained' not in candidate.model_dump_json()
    assert usage[0]['response_received'] is False and usage[0]['output_text_retained'] is False
    assert 'usage' not in usage[0] and 'output_sha256' not in usage[0]
    assert 'SECRET_TRANSPORT_EXCEPTION' not in candidate.model_dump_json()+json.dumps(usage)


def test_valid_pre_bad_quick_stays_gap_without_retry_or_repaired_output(tmp_path, monkeypatch):
    p, d, context = fixture(); rejected = []
    def output(value):
        if value['stage'] == 'PRE': return pre(value, 'CONTINUE_TO_QUICK').model_dump_json()
        text = bad_text(value, 'quick', 'missing'); rejected.append(text); return text
    seen, _ = mock_stream(monkeypatch, output)
    candidate, result, usage = w.research(p, d, context, tmp_path)
    assert len(seen) == len(usage) == 2 and result.status.value == 'EXECUTION_GAP'
    assert result.funnel_result is None and candidate.pre_research.route.value == 'CONTINUE_TO_QUICK'
    assert candidate.quick_research is None and candidate.receipt.technical_retries_used == 0
    assert (tmp_path/'quick-model-output.txt').read_text() == rejected[0]
    assert usage[1]['output_text_retained'] and usage[1]['status'] == 'FAILED'


@pytest.mark.parametrize('stage,model', [('pre', PreResearchResult), ('quick', QuickResearchResult)])
@pytest.mark.parametrize('defect', ['json', 'missing'])
def test_pinned_sdk_retains_rejected_text_and_usage_with_mock_http_only(tmp_path, monkeypatch, stage, model, defect):
    sdk = pytest.importorskip('openai')
    import httpx2 as httpx
    from openai.lib._parsing._responses import type_to_text_format_param
    prompt = prompt_for(stage); text = bad_text(prompt, stage, defect)
    part = {'type': 'output_text', 'text': text, 'annotations': []}
    item = {'id': 'msg_fixture', 'type': 'message', 'role': 'assistant', 'status': 'completed', 'content': [part]}
    final = {'id': 'resp_fixture', 'object': 'response', 'created_at': 1789056000, 'status': 'completed',
        'model': w.MODEL, 'output': [item], 'parallel_tool_calls': False, 'tool_choice': 'auto',
        'tools': [], 'error': None, 'incomplete_details': None,
        'usage': {'input_tokens': 1, 'input_tokens_details': {'cached_tokens': 0}, 'output_tokens': 1,
                  'output_tokens_details': {'reasoning_tokens': 0}, 'total_tokens': 2}}
    # Reuse the existing test_saved_research_once SSE fixture shape; no live server.
    events = [
        {'type': 'response.created', 'response': {**final, 'status': 'in_progress', 'output': []}},
        {'type': 'response.output_item.added', 'output_index': 0, 'item': {**item, 'status': 'in_progress', 'content': []}},
        {'type': 'response.content_part.added', 'output_index': 0, 'content_index': 0, 'item_id': 'msg_fixture', 'part': {**part, 'text': ''}},
        {'type': 'response.output_text.delta', 'output_index': 0, 'content_index': 0, 'item_id': 'msg_fixture', 'delta': text},
        {'type': 'response.output_text.done', 'output_index': 0, 'content_index': 0, 'item_id': 'msg_fixture', 'text': text},
        {'type': 'response.content_part.done', 'output_index': 0, 'content_index': 0, 'item_id': 'msg_fixture', 'part': part},
        {'type': 'response.output_item.done', 'output_index': 0, 'item': item},
        {'type': 'response.completed', 'response': final}]
    data = ''.join('data: '+json.dumps({**e, 'sequence_number': i})+'\n\n' for i, e in enumerate(events)).encode()
    seen = []
    expected = type_to_text_format_param(w.admitted_output_type(model, prompt['evidence_ids']))
    def transport(request):
        body = json.loads(request.content); seen.append(body)
        assert str(request.url) == w.BASE_URL+'/responses'
        assert body['text']['format'] == expected and body['text']['format']['strict'] is True
        assert body['stream'] is True and body['tools'] == [] and body['store'] is False
        assert body['max_output_tokens'] == 6000 and body['model'] == w.MODEL
        return httpx.Response(200, headers={'content-type': 'text/event-stream'}, content=data)
    monkeypatch.setattr(sdk, 'DefaultHttpxClient', lambda **kw: httpx.Client(transport=httpx.MockTransport(transport), **kw))
    monkeypatch.setenv('SUB2API_API_KEY', 'synthetic-only')
    usage = []
    with pytest.raises(ValueError): w.model_call(stage, prompt, model, tmp_path, usage)
    assert len(seen) == 1 and (tmp_path/(stage+'-model-output.txt')).read_text() == text
    assert usage[0]['response_received'] and usage[0]['output_text_retained']
    assert usage[0]['usage']['total_tokens'] == 2 and usage[0]['response_id'] == 'resp_fixture'
    assert usage[0]['phase'] == 'APPLICATION_VALIDATION' and usage[0]['status'] == 'FAILED'


def test_completed_text_write_failure_is_not_reported_as_retained(tmp_path, monkeypatch):
    prompt = prompt_for('pre'); target = tmp_path/'pre-model-output.txt'
    target.write_text('PREEXISTING_DO_NOT_REPLACE')
    seen, _ = mock_stream(monkeypatch, lambda v: pre(v).model_dump_json())
    usage = []
    with pytest.raises(FileExistsError): w.model_call('pre', prompt, PreResearchResult, tmp_path, usage)
    assert target.read_text() == 'PREEXISTING_DO_NOT_REPLACE' and len(seen) == 1
    assert usage[0]['response_received'] and usage[0]['output_text_retained'] is False
    assert usage[0]['phase'] == 'OUTPUT_RETENTION' and 'output_sha256' not in usage[0]
    assert usage[0]['usage'] == {'total_tokens': 2}  # Returned usage is not lost to a local write failure.


def test_incomplete_provider_response_is_retained_but_not_accepted(tmp_path, monkeypatch):
    prompt = prompt_for('pre'); text = pre(prompt).model_dump_json()
    seen, _ = mock_stream(monkeypatch, lambda _: text, status='incomplete')
    usage = []
    with pytest.raises(ValueError, match='did not complete'):
        w.model_call('pre', prompt, PreResearchResult, tmp_path, usage)
    assert len(seen) == 1 and (tmp_path/'pre-model-output.txt').read_text() == text
    assert usage[0]['output_text_retained'] and usage[0]['phase'] == 'OUTPUT_CHECKS'
    assert usage[0]['provider_status'] == 'incomplete' and usage[0]['status'] == 'FAILED'


def test_full_converted_format_is_included_in_pre_provider_byte_check(tmp_path, monkeypatch):
    prompt = prompt_for('pre'); seen, converter = mock_stream(monkeypatch, lambda v: pre(v).model_dump_json())
    model = w.admitted_output_type(PreResearchResult, prompt['evidence_ids'])
    size = len(w.SYSTEM.encode())+len(w.raw(prompt))+len(w.raw(converter(model)))
    monkeypatch.setattr(w, 'MAX_PROMPT_BYTES', size-1)
    with pytest.raises(ValueError, match='byte budget'):
        w.model_call('pre', prompt, PreResearchResult, tmp_path, [])
    assert seen == [] and list(tmp_path.iterdir()) == []
    monkeypatch.setattr(w, 'MAX_PROMPT_BYTES', size)
    assert w.model_call('pre', prompt, PreResearchResult, tmp_path, []).route.value == 'WAIT_FOR_TRIGGER'
    assert len(seen) == 1
