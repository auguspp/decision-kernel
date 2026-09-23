"""Native one-Quick host, source-status egress, retention and read delivery."""
from copy import deepcopy
import json
import socket

import pytest

from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import stock_daily_question as daily
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import reviewed_question_reading as reader
from test_single_quick_host_delivery import setup_single
from test_reviewed_question_reading import collector, report


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*a, **kw): raise AssertionError('Synthetic host test must not call a real endpoint')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)


def inputs(c, lane):
    q, packet, d, ctx, checks = host._question_inputs(api=c.api, code=c.args['code'],
        request=daily.base_request(c.request) if lane else c.request,
        clock=c.args['clock'], allow_full=bool(lane))
    if lane: packet, _, _ = daily.bind(c.api, c.request, q, packet, ctx, c.args['clock'])
    return packet, d, ctx, checks


@pytest.mark.parametrize('lane', [None, 'stock', 'industry'])
@pytest.mark.parametrize('route', ['STOP', 'WAIT_FOR_TRIGGER', 'FULL_CANDIDATE'])
def test_native_projection_is_same_in_prompt_launch_final_receipt_and_readable_result(tmp_path, monkeypatch, lane, route):
    c = setup_single(tmp_path, monkeypatch, lane=lane, route=route)
    p, d, context, checks = inputs(c, lane)
    expected = host.admission.prompt_source_checks(p, checks['preflight_raw'])
    before = once.raw(context); seen = []; original_call = c.args['call']
    def call(stage, prompt, model, output, usage):
        seen.append(deepcopy(prompt)); assert prompt['host_source_checks'] == expected
        assert prompt['public_context'] == context and prompt['evidence_ids'] == [str(e.id) for e in p.seed_evidence_artifacts]
        assert prompt['known_unknowns'] == p.known_unknowns
        return original_call(stage, prompt, model, output, usage)
    result = host.run_question(**{**c.args, 'call': call})
    assert result['status'] == 'VALIDATED_QUICK_RESULT' and c.calls == ['quick']
    assert len(seen) == 1 and result['source_check_context'] == expected
    saved = c.api.files[c.api.heads[intake.WORK_REF]]
    assert json.loads(saved[c.prefix+'launch.json'])['source_check_context'] == expected
    assert json.loads(saved[c.prefix+'host-receipt.json'])['source_check_context'] == expected
    assert saved[c.prefix+'source.json'] == before
    col, baseline = collector(c.args, tmp_path, stock=False)
    row = report(col, reader.attach(col, baseline))['question_work']['items'][0]
    assert row['status'] == 'VALIDATED_QUICK_RESULT' and row['pre_state'] == 'NOT_APPLICABLE'
    assert '资金批准' in col.files['README.md'].decode()
    assert c.calls == ['quick']  # Neither projecting nor reading spends another model call.


@pytest.mark.parametrize('lane', [None, 'stock', 'industry'])
def test_old_egress_does_not_authorize_new_metadata(tmp_path, monkeypatch, lane):
    c = setup_single(tmp_path, monkeypatch, lane=lane)
    p, d, ctx, checks = inputs(c, lane)
    old_hash = host.single_egress_hash(p, d, ctx, daily=bool(lane))
    assert old_hash != c.request['approved_egress_hash']
    c.request['approved_egress_hash'] = old_hash
    c.api.files[c.args['code']][c.request_path] = once.raw(c.request)
    result = host.run_question(**c.args)
    assert result['status'] == 'NOT_EXECUTED' and c.calls == [] and c.writes == []


@pytest.mark.parametrize('damage', ['remove', 'status', 'window', 'reference'])
def test_metadata_tampering_is_rejected_before_model_call(tmp_path, monkeypatch, damage):
    c = setup_single(tmp_path, monkeypatch)
    original_research = once.research
    def research(*args, call, **kwargs):
        def alter(stage, prompt, model, out, usage):
            prompt = deepcopy(prompt)
            if damage == 'remove': del prompt['host_source_checks']
            elif damage == 'status': prompt['host_source_checks']['status'] = 'ASSUMED'
            elif damage == 'window': prompt['host_source_checks']['recorded_window']['valid_until'] = '2999-01-01T00:00:00Z'
            else: prompt['host_source_checks']['preflight_source']['sha256'] = '0'*64
            return call(stage, prompt, model, out, usage)
        return original_research(*args, call=alter, **kwargs)
    monkeypatch.setattr(once, 'research', research)
    result = host.run_question(**c.args)
    assert result['status'] == 'EXECUTION_GAP' and c.calls == []
    saved = c.api.files[c.api.heads[intake.WORK_REF]]
    assert json.loads(saved[c.prefix+'candidate.json'])['assessment'] is None
    assert c.prefix+'research-attention.json' not in saved


def test_legacy_prompt_is_byte_identical_and_metadata_does_not_silently_migrate_it(tmp_path, monkeypatch):
    c = setup_single(tmp_path, monkeypatch); p, d, ctx, checks = inputs(c, None)
    old = p.model_copy(update={'method_version': 'research-funnel-v1', 'prompt_version':'reviewed-question-stock-v0'})
    assert once.raw(once.initial_prompt(old, d, ctx)) == once.raw(once.pre_prompt(old, d, ctx))
    with pytest.raises(ValueError, match='SOURCE_CHECK_CONTEXT_REQUIRES_SINGLE_QUICK'):
        once.initial_prompt(old, d, ctx, source_preflight=checks['preflight_raw'])
