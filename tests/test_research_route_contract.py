"""Real rejected output replay; schema guidance is not a new validator or a live run."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from decision_kernel.identity import canonical_hash
from decision_kernel.research_funnel import (
    PreResearchResult, QuickResearchResult, ResearchClaim,
    validate_pre_research_transition,
)
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_question_continuation as deepseek
from decision_kernel.runtime.external_research_execution import (
    ExternalResearchInputPacket, ExternalResearchCandidate,
    validate_external_research_candidate,
)

FIXTURE = Path(__file__).parent / 'fixtures/industry_quick_contract_20260923'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('route contract regressions must not use live networking')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)


def saved(name):
    return json.loads((FIXTURE / name).read_bytes())


def without_descriptions(value):
    if isinstance(value, dict):
        return {k: without_descriptions(v) for k, v in value.items() if k != 'description'}
    if isinstance(value, list):
        return [without_descriptions(v) for v in value]
    return value


@contextmanager
def historical_wire_without_descriptions(monkeypatch):
    """Test-only reconstruction of the exact old wire, never a production fallback.

    Both the legacy host's direct schemas and the SDK's request-local subclass
    must use the same historical descriptions. Keep classes, validators and the
    original SDK builder intact; restore current metadata after this scope.
    """
    with monkeypatch.context() as patch:
        for model in (PreResearchResult, QuickResearchResult):
            original = model.model_json_schema.__func__
            def historical(cls, *args, _original=original, **kwargs):
                return without_descriptions(_original(cls, *args, **kwargs))
            patch.setattr(model, 'model_json_schema', classmethod(historical))
        yield


def prompt_for(stage):
    candidate, packet = saved('candidate.json'), saved('input.json')
    prompt = {
        'stage': stage.upper(),
        'binding': {'discovery_id': candidate['discovery']['discovery_id'],
                    'as_of': packet['research_cutoff']},
        'evidence_ids': [e['id'] for e in packet['seed_evidence_artifacts']],
        'public_context': {'scope': 'SYNTHETIC request-build test, not an issuer body'},
    }
    if stage == 'quick':
        pre = PreResearchResult.model_validate(candidate['pre_research'])
        prompt.update(pre_research=pre.model_dump(mode='json'),
                      pre_research_hash=canonical_hash(pre))
    return prompt


def synthetic_deepen():
    # Counterfactual validator exercise only. Never save as a repaired issuer result.
    value = deepcopy(saved('quick-model-output.txt'))
    for group in ('supporting_claims', 'contradictory_claims'):
        value[group] = [deepcopy(next(c for c in value[group] if c['kind'] == 'FACT'))]
    value['variant_perception'] = 'SYNTHETIC testable differentiated hypothesis, not issuer research.'
    value['route_reason'] = 'SYNTHETIC available-now discrimination, not a production route correction.'
    return value


@pytest.mark.parametrize('name', ['quick-model-output.txt', 'pre-output-format.json',
                                 'quick-output-format.json', 'candidate.json', 'input.json'])
def test_original_failure_fixtures_are_exact_bytes(name):
    manifest = saved('provenance.json')
    assert manifest['run_id'] == 35819538967 and manifest['artifact_id'] == 10732853090
    raw = (FIXTURE / name).read_bytes()
    spec = manifest['files'][name]
    assert len(raw) == spec['bytes']
    assert hashlib.sha256(raw).hexdigest() == spec['sha256']
    assert once.blob(raw) == spec['git_blob']


def test_real_quick_still_rejected_without_relabelling_or_silent_route_repair():
    raw = (FIXTURE / 'quick-model-output.txt').read_bytes()
    assert once.sha(raw) == '3fee82af3c0167cc2afc44795f4e72a5b4ac76416d6abc410029a468c86e4c99'
    value = json.loads(raw)
    assert value['route'] == 'DEEPEN'
    assert [(group, i) for group in ('supporting_claims', 'contradictory_claims')
            for i, claim in enumerate(value[group]) if claim['kind'] == 'INFERENCE'] == [
                ('supporting_claims', 10), ('contradictory_claims', 5)]
    original = deepcopy(value)
    with pytest.raises(ValidationError, match='DEEPEN evidence groups require evidenced FACT or MARKET_CONTEXT'):
        QuickResearchResult.model_validate(value)
    assert value == original and (FIXTURE / 'quick-model-output.txt').read_bytes() == raw


def test_saved_pre_and_partial_candidate_revalidate_with_identical_hashes():
    candidate = ExternalResearchCandidate.model_validate(saved('candidate.json'))
    packet = ExternalResearchInputPacket.model_validate(saved('input.json'))
    pre = candidate.pre_research
    assert pre is not None and pre.route.value == 'CONTINUE_TO_QUICK'
    assert canonical_hash(pre) == 'cbe003b6122f6897da19f5fc47d2bb82b14d906eec38276d5aeab485c2ed772e'
    validate_pre_research_transition(candidate.discovery, pre, packet.seed_evidence_artifacts)
    assert candidate.quick_research is None
    result = validate_external_research_candidate(packet=packet, candidate=candidate)
    assert result.status.value == 'EXECUTION_GAP'
    assert result.gap_reason == 'ValidationError' and result.funnel_result is None
    assert result.candidate_hash == 'fb7890f96979320d492f235caa215e3d1e0ef955cb21addf53d7debb7e2540da'
    assert result.input_hash == 'e4c1ad0da89182b2f4cceb129f5928247c94dd9690f2d58fcaf178402f19ad42'


@pytest.mark.parametrize('stage,model', [('pre', PreResearchResult), ('quick', QuickResearchResult)])
def test_actual_sdk_and_deepseek_wire_change_only_descriptions(stage, model):
    prompt = prompt_for(stage)
    original = deepcopy(prompt)
    body, schema, output_format, parameters = deepseek._deepseek_request(prompt, model)
    old = saved(stage + '-output-format.json')
    assert without_descriptions(output_format) == old
    assert output_format != old
    assert json.loads(body) == prompt == original
    assert parameters['text']['format'] == output_format
    assert parameters['instructions'] == once.SYSTEM
    assert parameters['tools'] == [] and parameters['store'] is False
    assert parameters['max_output_tokens'] == 6000
    _, sdk_schema, sdk_format, sdk_parameters = once.model_request(
        prompt, model, max_prompt_bytes=512 * 1024)
    assert sdk_schema == schema
    assert sdk_format == {**output_format, 'strict': True}
    assert sdk_parameters['text']['format'] == sdk_format
    props = output_format['schema']['properties']
    assert props['route']['$ref'].endswith('ResearchRoute')
    assert 'description' in props['route_reason']
    claims = output_format['schema']['$defs']['ResearchClaim']['properties']
    assert claims['evidence_artifact_ids']['items']['enum'] == prompt['evidence_ids']
    assert 'Never relabel INFERENCE' in claims['statement']['description']
    # Defaults, nullable fields and machine constraints remain those of the old SDK wire.
    assert 'if' not in output_format['schema'] and 'then' not in output_format['schema']


def test_quick_wire_explains_conditionals_unknowns_and_future_trigger_without_new_gate():
    _, _, wire, _ = deepseek._deepseek_request(prompt_for('quick'), QuickResearchResult)
    props = wire['schema']['properties']
    for name in ('supporting_claims', 'contradictory_claims'):
        description = props[name]['description']
        assert all(text in description for text in ('DEEPEN', 'nonempty', 'EVERY',
                   'FACT', 'MARKET_CONTEXT', 'evidence_artifact_ids', 'WAIT_FOR_TRIGGER', 'STOP'))
    assert 'Do not discard counterevidence' in props['contradictory_claims']['description']
    assert 'Do not invent market consensus' in props['variant_perception']['description']
    assert 'future trigger' in props['next_discriminating_evidence']['description']
    assert 'not all subsequent announcements' in props['evidence_authority_assessment']['description']
    assert 'not permission for automatic Deep' in props['route_reason']['description']


@pytest.mark.parametrize('route', ['WAIT_FOR_TRIGGER', 'STOP'])
def test_nondeepen_routes_still_allow_honestly_labelled_inference(route):
    value = deepcopy(saved('quick-model-output.txt'))
    value.update(route=route, variant_perception=None,
                 route_reason='SYNTHETIC route-boundary exercise, not a revised issuer conclusion.')
    parsed = QuickResearchResult.model_validate(value)
    assert parsed.supporting_claims[10].kind.value == 'INFERENCE'
    assert parsed.contradictory_claims[5].kind.value == 'INFERENCE'
    assert parsed.route.value == route


@pytest.mark.parametrize('group', ['supporting_claims', 'contradictory_claims'])
@pytest.mark.parametrize('damage', ['empty', 'inference', 'assumption', 'unreferenced'])
def test_original_deepen_evidence_conditions_still_reject(group, damage):
    value = synthetic_deepen()
    if damage == 'empty':
        value[group] = []
    elif damage == 'unreferenced':
        value[group][0]['evidence_artifact_ids'] = []
    else:
        value[group][0]['kind'] = damage.upper()
    with pytest.raises(ValidationError):
        QuickResearchResult.model_validate(value)


@pytest.mark.parametrize('variant', [None, '', '   '])
def test_original_deepen_missing_variant_condition_still_rejects(variant):
    value = synthetic_deepen()
    value['variant_perception'] = variant
    with pytest.raises(ValidationError, match='plausible variant perception'):
        QuickResearchResult.model_validate(value)


def test_valid_synthetic_deepen_and_claim_defaults_are_unchanged():
    parsed = QuickResearchResult.model_validate(synthetic_deepen())
    assert parsed.route.value == 'DEEPEN' and parsed.schema_version == 1
    claim = ResearchClaim(statement='SYNTHETIC inference', kind='INFERENCE')
    assert claim.evidence_artifact_ids == ()
    assert claim.model_dump(mode='json') == {'statement': 'SYNTHETIC inference',
                                           'kind': 'INFERENCE', 'evidence_artifact_ids': []}


def test_real_rejected_text_is_retained_before_application_validation(tmp_path, monkeypatch):
    import openai
    text = (FIXTURE / 'quick-model-output.txt').read_text()
    response = SimpleNamespace(output_text=text, status='completed', id='synthetic-replay',
                               output=[SimpleNamespace(type='message')], usage=None)
    requests = []
    class Client:
        def __init__(self, **options):
            assert options['max_retries'] == 0
            self.http_client = options['http_client']
            self.responses = self
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.http_client.close()
        @contextmanager
        def stream(self, **parameters):
            requests.append(parameters)
            yield SimpleNamespace(get_final_response=lambda: response)
    monkeypatch.setattr(openai, 'OpenAI', Client)
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'SYNTHETIC_NO_NETWORK_CREDENTIAL')
    usage = []
    with pytest.raises(ValidationError):
        once.model_call('quick', prompt_for('quick'), QuickResearchResult, tmp_path, usage,
                       max_prompt_bytes=512 * 1024, base_url=once.DEEPSEEK_BASE_URL,
                       model=once.DEEPSEEK_MODEL, api_key_env='DEEPSEEK_API_KEY',
                       provider='DEEPSEEK_OFFICIAL', extra_parameters={'reasoning': deepseek.REASONING})
    assert len(requests) == len(usage) == 1
    assert (tmp_path / 'quick-model-output.txt').read_bytes() == (FIXTURE / 'quick-model-output.txt').read_bytes()
    assert usage[0]['provider_status'] == 'completed' and usage[0]['status'] == 'FAILED'
    assert usage[0]['output_text_retained'] is True
    assert usage[0]['application_validation']['status'] == 'REJECTED_BY_ORIGINAL_MODEL'
    assert 'SYNTHETIC_NO_NETWORK_CREDENTIAL' not in json.dumps(usage)
    assert saved('candidate.json')['quick_research'] is None


@pytest.mark.parametrize('mode', ['question', 'continuation'])
def test_current_host_rejects_frozen_egress_approval_after_wire_guidance_changes(
        tmp_path, monkeypatch, mode):
    from test_stock_question_host import setup_question
    from test_stock_question_continuation import setup_continuation
    from decision_kernel.runtime import stock_question_host as host
    setup = setup_question if mode == 'question' else setup_continuation
    execute = host.run_question if mode == 'question' else deepseek.run_continuation
    with historical_wire_without_descriptions(monkeypatch):
        fixture = setup(tmp_path, monkeypatch)
    args, api = fixture[:2]
    before = deepcopy(api.files)
    calls, writes = fixture[6:8]
    # Continuation setup retains its failed parent; only NEW activity is forbidden.
    prior_calls, prior_writes = list(calls), list(writes)
    result = execute(**args)
    assert result['status'] == 'NOT_EXECUTED', result
    assert result['error_code'] in {
        'QUESTION_PUBLIC_EGRESS_NOT_APPROVED',
        'QUESTION_CONTINUATION_PUBLIC_EGRESS_NOT_APPROVED',
    }, result
    assert not result['formal_research_started']
    assert calls == prior_calls and writes == prior_writes and api.files == before
