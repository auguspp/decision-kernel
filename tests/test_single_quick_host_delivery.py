"""Original host/retainer/reader/Brief with synthetic Git and model boundaries."""
from copy import deepcopy
import json
import socket
from types import SimpleNamespace

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import single_quick_contract as single
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import stock_daily_question as daily
from decision_kernel.runtime import reviewed_question_reading as reader
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import external_research_identity as identity
from decision_kernel.runtime import attention_inbox as brief
from decision_kernel.runtime import full_research_commission as full
from test_saved_research_raw_retention import format_converter
from test_single_quick_execution import assessment
from test_stock_question_host import setup_question
from test_reviewed_question_reading import collector, report


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("host delivery tests must not acquire sources or call a real model")
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)


def setup_single(tmp_path, monkeypatch, route='FULL_CANDIDATE', lane=None, invalid=False):
    format_converter(monkeypatch)
    case = None
    if lane:
        if lane == 'industry':
            from test_industry_daily_question import setup_industry
            case = setup_industry(tmp_path, monkeypatch)
        else:
            from test_stock_daily_question import setup_daily
            case = setup_daily(tmp_path, monkeypatch)
        args, api, request, q, context, calls, writes, prefix = (
            case.args, case.api, case.request, case.q, case.context, case.calls, case.writes, case.prefix)
    else:
        args, api, request, q, context, pf, calls, writes, prefix = setup_question(tmp_path, monkeypatch)
    permission = {**deepcopy(api.comment), 'id': 2, 'body': 'SYNTHETIC approval of exactly this new single Quick, no real authority.'}
    get = api.get
    def load(path):
        return deepcopy(permission) if path == 'issues/comments/2' else get(path)
    api.get = load
    request.update(research_method=single.METHOD_VERSION, method_permission={
        'comment_id': 2, 'body_sha256': once.sha(permission['body'].encode()), 'created_at': permission['created_at']})
    request['approved_egress_hash'] = '0' * 64
    base = daily.base_request(request) if lane else request
    _, packet, discovery, ctx, checks = host._question_inputs(api=api, code=args['code'], request=base, clock=args['clock'], allow_full=bool(lane))
    if lane:
        packet, _, _ = daily.bind(api, request, q, packet, ctx, args['clock'])
    request['approved_egress_hash'] = host.single_egress_hash(packet, discovery, ctx, daily=bool(lane),
        source_preflight=checks["preflight_raw"])
    path = daily.REQUEST if lane else host.QUESTION_REQUEST
    api.files[args['code']][path] = once.raw(request)
    def call(stage, prompt, model, output, usage):
        calls.append(stage)
        assert stage == 'quick' and model is single.QuickAssessment
        assert not {'pre_research', 'pre_research_hash'} & set(prompt)
        assert prompt['public_context'] == context
        value = assessment(prompt, route).model_dump(mode='json')
        value['explanation'] = 'SYNTHETIC 为什么值得看：资金批准并非实际支出，现金问题需要核对。'
        if invalid: del value['route_reason']
        raw = once.raw(value)
        (output / 'quick-model-output.txt').write_bytes(raw)
        usage.append({'stage': 'quick', 'status': 'FAILED' if invalid else 'completed',
                      'output_text_retained': True, 'output_sha256': once.sha(raw),
                      'response_received': True, 'usage': {'total_tokens': 2}})
        return model.model_validate(value)
    args['call'] = call
    return SimpleNamespace(args=args, api=api, request=request, q=q, calls=calls, writes=writes,
                           prefix=prefix, permission=permission, request_path=path, case=case, context=context)


@pytest.mark.parametrize('route', ['STOP', 'WAIT_FOR_TRIGGER', 'FULL_CANDIDATE'])
@pytest.mark.parametrize('lane', [None, 'stock', 'industry'])
def test_native_host_retains_one_quick_and_same_reader_delivers_explanation(tmp_path, monkeypatch, route, lane):
    c = setup_single(tmp_path, monkeypatch, route, lane)
    result = host.run_question(**c.args)
    assert result['status'] == 'VALIDATED_QUICK_RESULT', result
    assert c.calls == ['quick'] and not result['mutation_uncertain']
    saved = c.api.files[c.api.heads[intake.WORK_REF]]
    assert not any(p.startswith(c.prefix) and p.endswith(('pre.json', 'funnel.json')) for p in saved)
    assert json.loads(saved[c.prefix+'candidate.json'])['schema_version'] == 2
    assert saved[c.prefix+'quick-model-output.txt'] == (c.args['output']/'quick-model-output.txt').read_bytes()
    assert json.loads(saved[c.prefix+'model-usage.json'])[0]['usage']['total_tokens'] == 2
    packet_raw, candidate_raw = saved[c.prefix+'input.json'], saved[c.prefix+'candidate.json']
    packet, _, _ = single.read_saved_result(packet_raw, candidate_raw)
    identity.read_bound_execution(packet_raw, candidate_raw, identity.input_key(packet))
    if route == 'FULL_CANDIDATE':
        proposal = full.FullResearchCommission.model_validate_json(saved[c.prefix+'full-commission.json'])
        full.verify(proposal, load=lambda ref: c.api.file(ref['path'], ref['ref']))
        assert proposal.execution_authority == 'NONE' and proposal.execution_budget is None
    else: assert c.prefix+'full-commission.json' not in saved
    wrapped = brief.parse_research_attention_handoff(saved[c.prefix+'research-attention.json'].decode())
    assert wrapped.research_funnel is None
    if route == 'FULL_CANDIDATE':
        md = brief._render_research_markdown(packet.ticker, (wrapped,), None)
        rendered = brief._render_research_html(packet.ticker, (wrapped,), None)
        assert '为什么值得看' in md and '资金批准' in rendered
    before_writes = len(c.writes)
    col, baseline = collector(c.args, tmp_path, stock=False)
    result = reader.attach(col, baseline)
    rows = report(col, result)['question_work']['items']
    assert rows[0]['status'] == 'VALIDATED_QUICK_RESULT', rows
    assert rows[0]['pre_state'] == 'NOT_APPLICABLE' and not rows[0]['pre_present'] and rows[0]['quick_present']
    assert '资金批准' in col.files['README.md'].decode()
    assert '该方法不设 Pre' in col.files[reader.DETAIL].decode()
    assert len(c.writes) == before_writes and c.calls == ['quick']
    if lane:
        marker = json.loads(saved[daily.PREFIX+'slots/01/prepare.json'])
        assert marker['policy'] == daily.POLICY
    repeated = host.run_question(**{**c.args, 'output': tmp_path/'repeat'})
    assert repeated['status'] == 'EXISTING_QUESTION_REUSED_NO_EXECUTION', repeated
    assert c.calls == ['quick'] and len(c.writes) == before_writes


@pytest.mark.parametrize('damage', ['old-permission', 'permission-bytes', 'old-egress', 'method', 'source'])
def test_new_method_cannot_inherit_old_approval_or_changed_source(tmp_path, monkeypatch, damage):
    c = setup_single(tmp_path, monkeypatch)
    if damage == 'old-permission': c.request['method_permission'] = c.request['permission']
    elif damage == 'permission-bytes': c.permission['body'] += ' revoked'
    elif damage == 'old-egress': c.request['approved_egress_hash'] = 'f' * 64
    elif damage == 'method': c.request['research_method'] = 'unapproved'
    else:
        spec = c.request['context_source'];c.api.files[spec['ref']][spec['path']] += b'changed'
    c.api.files[c.args['code']][c.request_path] = once.raw(c.request)
    result = host.run_question(**c.args)
    assert result['status'] == 'NOT_EXECUTED', result
    assert c.calls == [] and c.writes == []


def test_invalid_first_output_is_remotely_preserved_not_retried_or_business_wait(tmp_path, monkeypatch):
    c = setup_single(tmp_path, monkeypatch, invalid=True)
    result = host.run_question(**c.args)
    assert result['status'] == 'EXECUTION_GAP', result
    saved = c.api.files[c.api.heads[intake.WORK_REF]]
    assert 'route_reason' not in json.loads(saved[c.prefix+'quick-model-output.txt'])
    assert c.prefix+'research-attention.json' not in saved
    col, baseline = collector(c.args, tmp_path, stock=False)
    row = report(col, reader.attach(col, baseline))['question_work']['items'][0]
    assert row['status'] == 'VALIDATED_EXECUTION_GAP' and row['terminal_state'] is None
    assert row['pre_state'] == 'NOT_APPLICABLE' and c.calls == ['quick']


@pytest.mark.parametrize('artifact', ['research-attention.json', 'full-commission.json', 'quick-model-output.txt'])
def test_saved_output_tampering_stays_visible_as_read_gap(tmp_path, monkeypatch, artifact):
    c = setup_single(tmp_path, monkeypatch)
    assert host.run_question(**c.args)['status'] == 'VALIDATED_QUICK_RESULT'
    c.api.files[c.api.heads[intake.WORK_REF]][c.prefix+artifact] += b'changed'
    col, baseline = collector(c.args, tmp_path, stock=False)
    row = report(col, reader.attach(col, baseline))['question_work']['items'][0]
    assert row['status'] == 'UNAVAILABLE_OR_REJECTED' and c.calls == ['quick']


@pytest.mark.parametrize('marker', ['prepare.json', 'failure.json', 'candidate.json'])
def test_old_method_attempt_markers_block_new_method_without_spending(tmp_path, monkeypatch, marker):
    c = setup_single(tmp_path, monkeypatch)
    old = b'SYNTHETIC old failed attempt; retained, not validated as a success.'
    c.api.heads[intake.WORK_REF] = c.args['code']
    c.api.files[c.api.heads[intake.WORK_REF]][c.prefix+marker] = old
    result = host.run_question(**c.args)
    assert result['status'] == 'EXISTING_QUESTION_REUSED_NO_EXECUTION'
    assert not c.calls and not c.writes
    assert c.api.files[c.api.heads[intake.WORK_REF]][c.prefix+marker] == old


def test_new_result_does_not_create_an_old_method_retry_opportunity(tmp_path, monkeypatch):
    c = setup_single(tmp_path, monkeypatch)
    assert host.run_question(**c.args)['status'] == 'VALIDATED_QUICK_RESULT'
    request = c.request
    del request['research_method']; del request['method_permission']
    _, p, d, ctx, _ = host._question_inputs(api=c.api, code=c.args['code'], request=request, clock=c.args['clock'])
    request['approved_egress_hash'] = host.question_egress_hash(p, d, ctx)
    c.api.files[c.args['code']][c.request_path] = once.raw(request)
    before = len(c.writes)
    result = host.run_question(**{**c.args, 'output': tmp_path/'old-method-again'})
    assert result['status'] == 'EXISTING_QUESTION_REUSED_NO_EXECUTION'
    assert c.calls == ['quick'] and len(c.writes) == before


def test_uncertain_raw_write_stops_retention_and_repeat_without_research_retry(tmp_path, monkeypatch):
    c = setup_single(tmp_path, monkeypatch)
    native = once.Retainer.native
    lost = []
    def uncertain(self, method, endpoint, body):
        if endpoint.endswith('/quick-model-output.txt'):
            lost.append(endpoint)
            self.uncertain = True
            raise RuntimeError('UNKNOWN native mutation outcome, no retry')
        return native(self, method, endpoint, body)
    monkeypatch.setattr(once.Retainer, 'native', uncertain)
    result = host.run_question(**c.args)
    assert result['status'] == 'RETENTION_INCOMPLETE' and result['mutation_uncertain']
    assert c.calls == ['quick'] and len(lost) == 1
    col, baseline = collector(c.args, tmp_path, stock=False)
    item = report(col, reader.attach(col, baseline))['question_work']['items'][0]
    assert item['status'] == 'UNAVAILABLE_OR_REJECTED'  # valid local result != delivered result
    before = len(c.writes)
    again = host.run_question(**{**c.args, 'output': tmp_path/'no-retry'})
    assert again['status'] == 'EXISTING_QUESTION_REUSED_NO_EXECUTION'
    assert c.calls == ['quick'] and len(lost) == 1 and len(c.writes) == before


@pytest.mark.parametrize('file', ['host-receipt.json', 'model-usage.json', 'quick-model-output.txt'])
def test_new_delivery_requires_actual_receipt_and_first_raw_output(tmp_path, monkeypatch, file):
    c = setup_single(tmp_path, monkeypatch)
    assert host.run_question(**c.args)['status'] == 'VALIDATED_QUICK_RESULT'
    del c.api.files[c.api.heads[intake.WORK_REF]][c.prefix+file]
    col, baseline = collector(c.args, tmp_path, stock=False)
    item = report(col, reader.attach(col, baseline))['question_work']['items'][0]
    assert item['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert c.calls == ['quick']


def test_actual_normal_collector_chain_keeps_new_result_after_other_reading_layers(tmp_path, monkeypatch):
    from decision_kernel.runtime import current_state_delivery as base
    from decision_kernel.runtime import current_state_delivery_with_odds_watch as normal
    from decision_kernel.runtime import research_reentry_reading as reentry
    c = setup_single(tmp_path, monkeypatch, lane='industry')
    assert host.run_question(**c.args)['status'] == 'VALIDATED_QUICK_RESULT'
    original, baseline = collector(c.args, tmp_path, stock=False)
    published = normal.Collector(original.api, original.code_commit, original.root, now=original.now)
    published.files, published.sources = original.files, original.sources
    published.include_reviewed_questions = True
    # Only upstream saved products are synthetic. The production composition and
    # all question/disposition/re-entry attachment functions execute normally.
    monkeypatch.setattr(base.Collector, 'collect', lambda self, refresh: baseline)
    result = published.collect({})
    row = report(published, result)['question_work']['items'][0]
    assert row['status'] == 'VALIDATED_QUICK_RESULT'
    assert '资金批准' in published.files['README.md'].decode()
    assert '该方法不设 Pre' in published.files[reader.DETAIL].decode()
    assert reentry.REPORT in published.files
    assert c.calls == ['quick'] and result['pending'] == []
