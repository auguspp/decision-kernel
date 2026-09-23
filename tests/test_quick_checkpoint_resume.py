"""Frozen real checkpoint + original executor; no live providers or source HTTP."""
from copy import deepcopy
import json
from pathlib import Path
import socket

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import reviewed_full_input as full
from decision_kernel.runtime.external_research_execution import ExternalResearchInputPacket
from test_saved_research_once import quick

FIXTURE = Path(__file__).parent / 'fixtures/industry_quick_contract_20260923'
WORK = '4b9988f20aa41810c6818d101e2bdb37cf139bde'
CODE = 'a' * 40
NOW = '2026-09-23T07:00:00+00:00'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('checkpoint tests cannot access networking')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)


def prepared():
    parent_raw = (FIXTURE / 'input.json').read_bytes()
    candidate_raw = (FIXTURE / 'candidate.json').read_bytes()
    parent = ExternalResearchInputPacket.model_validate_json(parent_raw)
    prior = once.ExternalResearchCandidate.model_validate_json(candidate_raw)
    specs = [once.source_ref(parent.candidate_output_prefix + name, WORK, body, purpose)
        for name, body, purpose in [('input.json', parent_raw, 'QUICK_RESUME_PARENT_INPUT'),
                                  ('candidate.json', candidate_raw, 'QUICK_RESUME_PARENT_CANDIDATE')]]
    cp = once.QuickCheckpoint(parent_raw, candidate_raw, *(once.raw(s) for s in specs))
    value = parent.model_dump(mode='json')
    child = ExternalResearchInputPacket.model_validate({**value,
        'execution_id': parent.execution_id + '-technical-continuation-v1',
        'code_commit': CODE, 'candidate_output_prefix': parent.candidate_output_prefix + 'technical-continuation-v1/',
        'source_refs': value['source_refs'] + specs,
        'budget': {**value['budget'], 'max_technical_retries': 1}})
    spec = next(s.model_dump(mode='json') for s in parent.source_refs if s.purpose == 'MODEL_CONTEXT')
    # Exact existing stored source blob, not newly acquired or a clipped fixture.
    raw = (FIXTURE / 'source.json').read_bytes()
    context, bound = full.load_context(spec, lambda _: raw, ticker=parent.ticker, allowed=True)
    return cp, child, prior.discovery, context, bound


def test_real_checkpoint_preserves_original_pre_cutoff_and_complete_context():
    cp, packet, discovery, context, bound = prepared()
    pre = cp.restore(packet, discovery)
    assert canonical_hash(pre) == 'cbe003b6122f6897da19f5fc47d2bb82b14d906eec38276d5aeab485c2ed772e'
    assert pre.as_of == packet.research_cutoff == discovery.as_of
    assert [d['page_count'] for d in context['issuer_documents']] == [262, 216]
    bound.check_packet(packet, context)
    assert cp.record()['source_freshness'] == 'ORIGINAL_CUTOFF_NOT_RECHECKED_AS_CURRENT'


@pytest.mark.parametrize('route', ['WAIT_FOR_TRIGGER', 'STOP', 'DEEPEN'])
def test_only_quick_is_called_and_original_pre_is_read_not_regenerated(tmp_path, route):
    cp, packet, discovery, context, bound = prepared()
    seen = []
    original_pre = once.raw(cp.restore(packet, discovery))
    def call(stage, prompt, model, out, usage):
        seen.append(stage)
        assert stage == 'quick' and model is once.QuickResearchResult
        assert once.raw(prompt['pre_research']) == original_pre
        assert prompt['pre_research_hash'] == cp.record()['pre_research_hash']
        assert prompt['public_context'] == context
        assert prompt['continuation_scope']['pre_model_calls'] == 0
        value = quick(prompt).model_dump(mode='json')
        value.update(route=route, route_reason='SYNTHETIC route, not issuer correction.')
        if route == 'DEEPEN':
            claim = {'statement': 'SYNTHETIC observed limitation', 'kind': 'FACT',
                     'evidence_artifact_ids': prompt['evidence_ids']}
            value.update(supporting_claims=[claim], contradictory_claims=[claim],
                         variant_perception='SYNTHETIC testable hypothesis')
        return model.model_validate(value)
    candidate, checked, usage = once.research(packet, discovery, context, tmp_path,
        call=call, clock=lambda: NOW, bound_context=bound, quick_checkpoint=cp)
    assert checked.status.value == 'VALIDATED_FUNNEL_RESULT'
    assert seen == ['quick'] and usage == []  # Synthetic callback, no fabricated provider receipt.
    assert once.raw(candidate.pre_research) == original_pre
    assert candidate.quick_research.route.value == route
    assert candidate.receipt.technical_retries_used == 1
    assert all(not e.target.endswith(':PRE') for e in candidate.receipt.tool_events)
    assert (tmp_path / 'pre.json').read_bytes() == original_pre
    assert json.loads((tmp_path / 'pre-reuse.json').read_bytes()) == cp.record()
    assert not (tmp_path / 'pre-model-input.json').exists()
    assert not (tmp_path / 'pre-model-output.txt').exists()


@pytest.mark.parametrize('damage', ['cutoff', 'question', 'source', 'budget', 'parent-id', 'prefix', 'discovery'])
def test_changed_checkpoint_binding_stops_before_any_executor_action(tmp_path, damage):
    cp, packet, discovery, context, bound = prepared()
    value = packet.model_dump(mode='json')
    if damage == 'cutoff': value['research_cutoff'] = NOW
    elif damage == 'question': value['research_question'] += ' changed'
    elif damage == 'source': value['source_refs'].pop()
    elif damage == 'budget': value['budget']['max_technical_retries'] = 2
    elif damage == 'parent-id': value['execution_id'] += '-again'
    elif damage == 'prefix': value['candidate_output_prefix'] += 'again/'
    else:
        discovery = discovery.model_copy(update={'why_now': 'changed'})
    packet = ExternalResearchInputPacket.model_validate(value)
    calls = []
    with pytest.raises(ValueError):
        once.research(packet, discovery, context, tmp_path, quick_checkpoint=cp,
                      call=lambda *a: calls.append(a), clock=lambda: NOW, bound_context=bound)
    assert calls == [] and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('damage', ['candidate-bytes', 'input-bytes', 'source-purpose', 'source-ref', 'source-path', 'checkpoint-type'])
def test_exact_source_proof_and_typed_checkpoint_cannot_be_bypassed(tmp_path, damage):
    cp, packet, discovery, context, bound = prepared()
    values = dict(input_raw=cp.input_raw, candidate_raw=cp.candidate_raw,
                  input_source_raw=cp.input_source_raw, candidate_source_raw=cp.candidate_source_raw)
    if damage == 'candidate-bytes': values['candidate_raw'] += b' '
    elif damage == 'input-bytes': values['input_raw'] += b' '
    else:
        spec = json.loads(values['candidate_source_raw'])
        if damage == 'source-purpose': spec['purpose'] = 'MODEL_CONTEXT'
        elif damage == 'source-ref': spec['ref'] = 'b' * 40
        elif damage == 'source-path': spec['path'] += '-renamed'
        values['candidate_source_raw'] = once.raw(spec)
    changed = values if damage == 'checkpoint-type' else once.QuickCheckpoint(**values)
    calls = []
    with pytest.raises(ValueError):
        once.research(packet, discovery, context, tmp_path, quick_checkpoint=changed,
                      call=lambda *a: calls.append(a), clock=lambda: NOW, bound_context=bound)
    assert calls == [] and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('failure', ['real-rejected-output', 'wrong-pre-hash', 'wrong-cutoff', 'unknown-evidence', 'timeout'])
def test_failed_quick_keeps_valid_pre_without_an_automatic_retry(tmp_path, failure):
    cp, packet, discovery, context, bound = prepared()
    calls = []
    def call(stage, prompt, model, out, usage):
        calls.append(stage)
        if failure == 'timeout': raise TimeoutError('SYNTHETIC timeout')
        if failure == 'real-rejected-output':
            raw = (FIXTURE / 'quick-model-output.txt').read_bytes()
            (out / 'quick-model-output.txt').write_bytes(raw)
            return model.model_validate_json(raw)
        value = quick(prompt).model_dump(mode='json')
        if failure == 'wrong-pre-hash': value['pre_research_hash'] = '0' * 64
        elif failure == 'wrong-cutoff': value['as_of'] = NOW
        else:
            value['supporting_claims'] = [{'statement': 'SYNTHETIC unknown reference', 'kind': 'FACT',
                'evidence_artifact_ids': ['00000000-0000-0000-0000-000000000001']}]
        return model.model_validate(value)
    candidate, checked, usage = once.research(packet, discovery, context, tmp_path,
        call=call, clock=lambda: NOW, bound_context=bound, quick_checkpoint=cp)
    assert calls == ['quick'] and checked.status.value == 'EXECUTION_GAP'
    assert candidate.quick_research is None and candidate.pre_research == cp.restore(packet, discovery)
    assert candidate.receipt.technical_retries_used == 1 and checked.funnel_result is None
    assert json.loads((tmp_path / 'candidate-before-validation.json').read_bytes())['quick_research'] is None


@pytest.mark.parametrize('name', ['source.json', 'admission.json', 'host-receipt.json', 'launch.json',
                                 'receipt.json', 'validation.json', 'prepare.json', 'question.json',
                                 'preflight.json', 'original-request.json'])
def test_added_checkpoint_fixtures_are_exact_retained_bytes(name):
    proof = json.loads((FIXTURE / 'resume-provenance.json').read_bytes())
    body = (FIXTURE / name).read_bytes()
    assert len(body) == proof[name]['bytes']
    assert once.sha(body) == proof[name]['sha256']
    assert once.blob(body) == proof[name]['git_blob']
