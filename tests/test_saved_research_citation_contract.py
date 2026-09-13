"""Synthetic transport regression for 34703004892; not a new Research sample."""
from copy import deepcopy
from types import SimpleNamespace
import json
import sys

import pytest

from decision_kernel.research_funnel import PreResearchResult, QuickResearchResult
from decision_kernel.runtime import saved_research_once as w
from test_saved_research_once import fixture, pre, quick

FOREIGN = 'd761d18c-37dd-58ff-ba02-3826e25bd988'


def mock_sdk(monkeypatch, make_text):
    from test_saved_research_raw_retention import format_converter
    format_converter(monkeypatch)
    requests = []
    class Stream:
        def __init__(self, request): self.request = request
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def get_final_response(self):
            text = make_text(self.request)
            # Explicit wire schema does not ask the SDK to parse the application
            # model. Original model and transition checks run after retention.
            assert 'text_format' not in self.request
            assert self.request['text']['format']['strict'] is True
            return SimpleNamespace(output_text=text, status='completed', id='synthetic',
                                   usage=None, output=[SimpleNamespace(type='message')])
    class Client:
        def __init__(self, **kwargs):
            assert kwargs['max_retries'] == 0 and kwargs['timeout'] == 180
            self.responses = self
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def stream(self, **kwargs):
            requests.append(kwargs)
            assert kwargs['tools'] == [] and not kwargs['store']
            return Stream(kwargs)
    monkeypatch.setitem(sys.modules, 'openai', SimpleNamespace(
        OpenAI=Client, DefaultHttpxClient=lambda **kw: kw))
    monkeypatch.setenv('SUB2API_API_KEY', 'synthetic-key')
    return requests


def prompt():
    packet, discovery, _ = fixture()
    return {'binding': {'discovery_id': discovery.discovery_id, 'as_of': discovery.as_of.isoformat()},
            'evidence_ids': [str(packet.seed_evidence_artifacts[0].id)],
            'public_context': {'evidence_artifact': {'id': FOREIGN}, 'pages': ['Synthetic body']}}


@pytest.mark.parametrize('stage,model,make', [('pre', PreResearchResult, pre), ('quick', QuickResearchResult, quick)])
def test_request_schema_only_adds_admitted_ids_and_keeps_original_models(tmp_path, monkeypatch, stage, model, make):
    value = prompt()
    if stage == 'quick': value['pre_research_hash'] = w.canonical_hash(pre(value))
    before = deepcopy(value); original = model.model_json_schema()
    seen = mock_sdk(monkeypatch, lambda request: make(value).model_dump_json())
    usage = []
    result = w.model_call(stage, value, model, tmp_path, usage)
    request_type = w.admitted_output_type(model, value['evidence_ids'])
    from openai.lib._parsing._responses import type_to_text_format_param
    assert seen[0]['text']['format'] == type_to_text_format_param(request_type)
    schema = request_type.model_json_schema()
    items = schema['$defs']['ResearchClaim']['properties']['evidence_artifact_ids']['items']
    assert items.pop('enum', None) == value['evidence_ids']
    schema['title'] = original['title']
    assert schema == original and model.model_json_schema() == original
    assert type(result) is model and result == make(value)
    assert value == before and (tmp_path / (stage+'-model-input.json')).read_bytes() == w.raw(before)
    assert FOREIGN in seen[0]['input'][0]['content']  # Do not delete source metadata.
    assert 'top-level evidence_ids' in seen[0]['instructions']
    assert usage[0]['reference_contract'] == 'ADMITTED_EVIDENCE_IDS_V1'
    assert usage[0]['output_model_schema_sha256'] == w.sha(w.raw(request_type.model_json_schema()))


def test_per_call_reference_set_does_not_leak_or_mutate_original_schema(tmp_path, monkeypatch):
    value = prompt(); original = PreResearchResult.model_json_schema()
    seen = mock_sdk(monkeypatch, lambda r: pre(json.loads(r['input'][0]['content'])).model_dump_json())
    for n, ids in enumerate([value['evidence_ids'], [FOREIGN, value['evidence_ids'][0]]]):
        directory=tmp_path/str(n); directory.mkdir()
        w.model_call('pre', dict(value, evidence_ids=ids), PreResearchResult, directory, [])
    for request, expected in zip(seen, [value['evidence_ids'], [FOREIGN, value['evidence_ids'][0]]]):
        item=request['text']['format']['schema']['$defs']['ResearchClaim']['properties']['evidence_artifact_ids']['items']
        assert item['enum'] == expected
    assert PreResearchResult.model_json_schema() == original


@pytest.mark.parametrize('bad_ids', [None, [], ['not-a-uuid'], [FOREIGN, FOREIGN], [FOREIGN.upper()], [1]])
def test_invalid_admitted_reference_input_stops_before_provider_and_writes(tmp_path, monkeypatch, bad_ids):
    value = prompt(); value['evidence_ids'] = bad_ids
    seen = mock_sdk(monkeypatch, lambda _: pre(prompt()).model_dump_json())
    with pytest.raises((ValueError, TypeError), match='admitted Evidence'):
        w.model_call('pre', value, PreResearchResult, tmp_path, [])
    assert not seen and list(tmp_path.iterdir()) == []


def test_enlarged_request_schema_still_obeys_original_byte_budget(tmp_path, monkeypatch):
    value=prompt(); original_schema=PreResearchResult.model_json_schema()
    original_size=len(w.SYSTEM.encode())+len(w.raw(value))+len(w.raw(original_schema))
    monkeypatch.setattr(w, 'MAX_PROMPT_BYTES', original_size)
    seen=mock_sdk(monkeypatch, lambda _: pre(value).model_dump_json())
    with pytest.raises(ValueError, match='model input byte budget'):
        w.model_call('pre', value, PreResearchResult, tmp_path, [])
    assert not seen and list(tmp_path.iterdir()) == []


def test_ignored_provider_constraint_retains_raw_then_original_gate_rejects(tmp_path, monkeypatch):
    packet, discovery, context=fixture()
    context['nested_original_evidence_id']=FOREIGN
    spec=packet.source_refs[0].model_copy(update={'sha256':w.sha(w.raw(context)), 'git_blob':w.blob(w.raw(context))})
    packet=packet.model_copy(update={'source_refs':(spec,)})
    texts=[]
    def response(request):
        value=json.loads(request['input'][0]['content'])
        raw=pre(value).model_dump(mode='json')
        raw['material_claims'][0]['evidence_artifact_ids']=[FOREIGN]
        text=json.dumps(raw); texts.append(text); return text
    seen=mock_sdk(monkeypatch,response)
    candidate, result, usage=w.research(packet,discovery,context,tmp_path)
    assert len(seen)==1 and len(usage)==1
    assert result.status.value=='EXECUTION_GAP' and candidate.pre_research is None
    assert candidate.receipt.stop_or_failure_reason=='DomainValidationError'
    assert (tmp_path/'pre-model-output.txt').read_text()==texts[0]
    assert FOREIGN in texts[0] and usage[0]['output_sha256']==w.sha(texts[0].encode())
    assert not (tmp_path/'quick-model-input.json').exists()


@pytest.mark.parametrize('route', ['WAIT_FOR_TRIGGER', 'STOP'])
def test_correct_reference_preserves_original_terminal_route(tmp_path, monkeypatch, route):
    packet, discovery, context=fixture()
    seen=mock_sdk(monkeypatch, lambda r: pre(json.loads(r['input'][0]['content']),route).model_dump_json())
    candidate,result,_=w.research(packet,discovery,context,tmp_path)
    assert result.status.value=='VALIDATED_FUNNEL_RESULT' and len(seen)==1
    assert candidate.pre_research.route.value==route


def test_original_fact_and_extra_field_validators_not_weakened(monkeypatch, tmp_path):
    value=prompt()
    seen=mock_sdk(monkeypatch, lambda _: pre(value).model_dump_json())
    w.model_call('pre',value,PreResearchResult,tmp_path,[])
    model=w.admitted_output_type(PreResearchResult, value['evidence_ids'])
    assert seen[0]['text']['format']['strict'] is True
    no_source=pre(value).model_dump(mode='json')
    no_source['material_claims'][0]['evidence_artifact_ids']=[]
    with pytest.raises(ValueError): model.model_validate(no_source)
    with pytest.raises(ValueError): model.model_validate({**pre(value).model_dump(mode='json'), 'buy':True})
