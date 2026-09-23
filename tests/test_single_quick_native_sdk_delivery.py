"""Actual installed SDK at the original native host; no network or live issuer data."""
import json
import socket

import pytest

from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import stock_daily_question as daily
from decision_kernel.runtime import reviewed_full_input as full
from decision_kernel.runtime import reviewed_question_reading as reader
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import single_quick_contract as single
from test_single_quick_host_delivery import setup_single
from test_reviewed_full_input import seal_full
from test_reviewed_question_reading import collector, report
from test_single_quick_execution import assessment
from test_single_quick_full_wire import sse


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs): raise AssertionError('Native SDK tests cannot use live network')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)


@pytest.mark.parametrize('route', ['STOP', 'WAIT_FOR_TRIGGER', 'FULL_CANDIDATE', 'INVALID'])
def test_native_complete_industry_input_through_sdk_retainer_publisher_reader(tmp_path, monkeypatch, route):
    # Mandatory pinned SDK in complete CI: no skip or production fallback.
    import openai
    import httpx2 as httpx
    c = setup_single(tmp_path, monkeypatch, lane='industry')
    c.case.context['source_limitations'] += ' Synthetic full body retained, not truncated.' * 14000
    seal_full(c.case)
    _, p, d, context, _ = host._question_inputs(api=c.api, code=c.args['code'],
        request=daily.base_request(c.request), clock=c.args['clock'], allow_full=True)
    p, _, _ = daily.bind(c.api, c.request, c.q, p, context, c.args['clock'])
    _, bound = full.load_context(c.request['context_source'],
        lambda s: c.api.file(s['path'], s['ref']), ticker=p.ticker, allowed=True)
    c.request['approved_egress_hash'] = host.single_egress_hash(p, d, context, bound=bound, daily=True)
    c.api.files[c.args['code']][daily.REQUEST] = once.raw(c.request)
    seen, texts = [], []
    def transport(request):
        body = json.loads(request.content);seen.append(body)
        prompt = json.loads(body['input'][0]['content'])
        assert str(request.url) == once.DEEPSEEK_BASE_URL+'/responses'
        assert len(request.content) > 512*1024
        assert prompt['public_context'] == context
        assert prompt['stage'] == 'QUICK' and prompt['method_version'] == single.METHOD_VERSION
        assert not {'pre_research', 'pre_research_hash'} & set(prompt)
        assert body['model'] == once.DEEPSEEK_MODEL and body['reasoning'] == {'effort':'none'}
        assert body['tools'] == [] and body['store'] is False and body['max_output_tokens'] == 6000
        text = '{"route":' if route == 'INVALID' else assessment(prompt, route).model_dump_json()
        texts.append(text)
        return httpx.Response(200, headers={'content-type':'text/event-stream'}, content=sse(text))
    def client(**kwargs):
        # Preserve preview's own rejecting transport; only the real send is mocked.
        kwargs.setdefault('transport', httpx.MockTransport(transport))
        return httpx.Client(**kwargs)
    monkeypatch.setattr(openai, 'DefaultHttpxClient', client)
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'synthetic-not-real')
    result = host.run_question(**{**c.args, 'call': None})
    assert result['status'] == ('EXECUTION_GAP' if route == 'INVALID' else 'VALIDATED_QUICK_RESULT'), result
    assert len(seen) == 1 and not result['mutation_uncertain']
    saved = c.api.files[c.api.heads[intake.WORK_REF]]
    assert saved[c.prefix+'quick-model-output.txt'].decode() == texts[0]
    usage = json.loads(saved[c.prefix+'model-usage.json'])
    assert len(usage) == 1 and usage[0]['usage']['total_tokens'] == 12
    assert usage[0]['pre_send']['request_sha256'] == result['full_input']['single_quick_request_sha256']
    assert full.unpack(saved[c.prefix+'source.json'], ticker=p.ticker) == once.raw(context)
    assert not any(path.startswith(c.prefix) and path.endswith(('pre.json', 'funnel.json')) for path in saved)
    col, baseline = collector(c.args, tmp_path, stock=False)
    item = report(col, reader.attach(col, baseline))['question_work']['items'][0]
    assert item['status'] == ('VALIDATED_EXECUTION_GAP' if route == 'INVALID' else 'VALIDATED_QUICK_RESULT'), item
    assert item['pre_state'] == 'NOT_APPLICABLE'
    assert (c.prefix+'full-commission.json' in saved) == (route == 'FULL_CANDIDATE')
    assert 'synthetic-not-real' not in '\n'.join(v.decode() for path,v in saved.items() if path.startswith(c.prefix))
