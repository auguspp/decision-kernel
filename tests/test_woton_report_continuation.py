"""One-shot composition; synthetic Git/model, original admission/retainer/Funnel.

The real PDF test exercises the retained original parser. Synthetic custody
returns in host tests stand in for that already independently tested boundary;
these tests never constitute a real company Research or provider invocation.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import socket

import pytest

from decision_kernel.runtime import woton_report_continuation as w
from decision_kernel.runtime import woton_report_custody as c
from decision_kernel.runtime import stock_question_continuation as deepseek
from test_saved_research_once import pre, quick
import test_stock_research_host as stock_fx


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*a, **k): raise AssertionError('No live networking in continuation tests')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


class FrozenDate(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 21, 6, 0, 0, tzinfo=timezone.utc).astimezone(tz)


def setup(tmp_path, monkeypatch, route='WAIT_FOR_TRIGGER', failure=None):
    monkeypatch.setattr(stock_fx, 'datetime', FrozenDate)
    args, api, _, captures, writes = stock_fx.setup_host(tmp_path, monkeypatch)
    code = args['code']; old = 'b' * 40
    request = json.loads(Path(w.REQUEST).read_text())
    request['permission'] = args['request']['permission']
    request['reading_commit'] = args['reading_commit']
    parent_path = request['parent_failure']['path'].rsplit('/', 1)[0] + '/'
    selection = {'execution_id': w.PARENT, 'thscode': '000920.SZ'}
    original_failure = {'execution_id': w.PARENT, 'thscode': '000920.SZ',
        'formal_research_started': False, 'research_execution': 'NOT_EXECUTED',
        'error_type': 'CninfoPdfHttpError', 'status': 'SOURCE_OR_INPUT_PREPARATION_INCOMPLETE'}
    def store(key, path, body):
        spec = w.once.source_ref(path, old, body, request[key]['purpose'])
        api.files[old][path] = body; request[key] = spec
    store('parent_selection', parent_path + 'prepare.json', w.once.raw(selection))
    store('parent_failure', parent_path + 'failure.json', w.once.raw(original_failure))
    r3 = Path('docs/readings/000920-profit-bridge-progress-2026-09-21')
    for key, name in [('predecessor_progress', 'progress.json'),
                      ('predecessor_workpaper', 'workpaper.md'), ('predecessor_parent', 'predecessor.json')]:
        store(key, str(r3 / name), (r3 / name).read_bytes())
    store('source_manifest', c.PREFIX + 'source.json', b'{"synthetic_custody":true}')
    raw = w.once.raw(request)
    api.files[code][w.REQUEST] = raw
    monkeypatch.setattr(w, 'REQUEST_SHA256', w.once.sha(raw))
    api.heads[w.intake.WORK_REF] = old
    recovered = []
    parsed = {'pdf_sha256': c.PDF_SHA, 'page_count': 133,
        'pages': [{'page_number': i, 'text': 'Synthetic complete report page ' + str(i)} for i in range(1, 134)]}
    def recover(git, spec):
        assert git is api and spec == request['source_manifest']
        w.checked_source(api, spec); recovered.append(spec)
        return b'Synthetic source bytes', deepcopy(parsed), {'received_at': '2026-09-21T01:27:16Z'}
    monkeypatch.setattr(c, 'recover', recover)
    calls = []; prompts = []
    def call(stage, prompt, model, output, usage):
        calls.append(stage); prompts.append(deepcopy(prompt))
        if failure == stage: raise RuntimeError('PRIVATE_PROVIDER_ERROR_DO_NOT_ECHO')
        if failure == 'revoke_after_pre': api.comment['body'] = 'REVOKED'
        return pre(prompt, route) if stage == 'pre' else quick(prompt)
    run_args = dict(api=api, code=code, output=tmp_path/'out', clock=args['clock'], call=call)
    return run_args, api, request, calls, prompts, recovered, writes, parsed, captures


def test_real_scope_permission_and_separate_fixed_child():
    raw = Path(w.REQUEST).read_bytes(); req = json.loads(raw)
    assert w.once.sha(raw) == w.REQUEST_SHA256
    permission = Path('tests/fixtures/woton_report_continuation_permission.txt').read_bytes()
    assert w.once.sha(permission) == req['permission']['body_sha256']
    assert req['parent_execution_id'] == w.PARENT and req['relation'] == 'CONTINUE_ANALYSIS'
    assert req['limits']['max_pre_calls'] == req['limits']['max_quick_calls'] == 1
    assert not w.PREFIX.startswith(w.intake.PREFIX)
    assert w.PARENT in w.EXECUTION and req['question']
    # The Woton one-shot never supplies authority to the later daily request.
    # Daily activation has its own original permission; do not freeze its old
    # disabled deployment state as a permanent Woton contract.
    daily_request = json.loads(Path('research_runs/stock-daily-question-request.json').read_text())
    assert daily_request['permission'] != req['permission']
    assert daily_request['mode'] != req['mode']
    assert all(not spec['path'].startswith(w.PREFIX) for spec in daily_request.values()
               if isinstance(spec, dict) and 'path' in spec)


@pytest.mark.parametrize('route,stages', [('WAIT_FOR_TRIGGER',['pre']), ('STOP',['pre']),
                                        ('CONTINUE_TO_QUICK',['pre','quick'])])
def test_native_admission_funnel_child_history_and_duplicate(tmp_path, monkeypatch, route, stages):
    args, api, req, calls, prompts, recovered, writes, _, captures = setup(tmp_path, monkeypatch, route)
    before = deepcopy(api.files[api.heads[w.intake.WORK_REF]])
    result = w.run(**args)
    assert result['status'] == 'VALIDATED_FUNNEL_RESULT', result
    assert calls == stages == result['model_stage_attempts']
    assert result['parent_execution_id'] == w.PARENT and not result['new_distinct_question']
    assert len(recovered) == 1 and captures == []
    assert result['source_requests'] == result['market_requests'] == 0
    after = api.files[api.heads[w.intake.WORK_REF]]
    assert all(after[p] == raw for p, raw in before.items())
    assert all(endpoint.startswith('contents/' + w.PREFIX) for _, endpoint, _ in writes)
    assert len([p for p in after if p.startswith(w.PREFIX)]) <= 16
    assert json.loads((args['output']/'admission.json').read_bytes())['research_execution_allowed']
    packet = json.loads((args['output']/'input.json').read_bytes())
    assert packet['seed_evidence_artifacts'][0]['published_at'] is not None
    assert prompts[0]['public_context']['issuer_documents'][0]['published_at'] is None
    assert req['permission']['body_sha256'] not in w.once.raw(prompts).decode()
    paper = before[req['predecessor_workpaper']['path']]
    assert paper not in w.once.raw(prompts)
    n = len(writes)
    repeat = w.run(**{**args, 'output': tmp_path/'again'})
    assert repeat['status'] == w.REUSED and calls == stages and len(writes) == n
    assert len(recovered) == 1


@pytest.mark.parametrize('failure,stages', [('pre',['pre']),('quick',['pre','quick']),
                                           ('revoke_after_pre',['pre'])])
def test_model_failure_or_revocation_is_not_wait_and_never_retried(tmp_path,monkeypatch,failure,stages):
    args, api, _, calls, _, _, writes, _, _ = setup(tmp_path,monkeypatch,'CONTINUE_TO_QUICK',failure)
    result = w.run(**args)
    assert result['status'] == 'EXECUTION_GAP', result
    assert calls == stages and not (args['output']/'funnel.json').exists()
    assert 'PRIVATE_PROVIDER_ERROR' not in json.dumps(result)
    n=len(writes); w.run(**{**args,'output':tmp_path/'repeat'})
    assert calls == stages and len(writes)==n


@pytest.mark.parametrize('key', w.HISTORY_KEYS)
def test_tampered_original_or_progress_rejected_before_reservation(tmp_path,monkeypatch,key):
    args,api,req,calls,_,recovered,writes,_,_=setup(tmp_path,monkeypatch)
    s=req[key];api.files[s['ref']][s['path']]+=b' '
    result=w.run(**args)
    assert result['status']=='NOT_EXECUTED'
    assert calls==recovered==writes==[]


@pytest.mark.parametrize('name',sorted(w.once.OUTPUT_NAMES))
def test_any_partial_child_consumes_this_exact_intent(tmp_path,monkeypatch,name):
    args,api,_,calls,_,recovered,writes,_,_=setup(tmp_path,monkeypatch)
    api.files[api.heads[w.intake.WORK_REF]][w.PREFIX+name]=b'partial'
    result=w.run(**args)
    assert result['status']==w.REUSED and calls==recovered==writes==[]


@pytest.mark.parametrize('damage',['scope','permission','expiry','parent-launch','tree-truncated','page-missing','context-oversize'])
def test_scope_and_material_failures_do_not_call_model(tmp_path,monkeypatch,damage):
    args,api,req,calls,_,_,writes,parsed,_=setup(tmp_path,monkeypatch)
    if damage=='scope': api.files[args['code']][w.REQUEST]+=b' '
    elif damage=='permission': api.comment['body']='CHANGED'
    elif damage=='expiry': args['clock']=lambda:'2026-09-23T00:00:00Z'
    elif damage=='parent-launch':
        p=req['parent_failure']['path'].replace('failure.json','launch.json')
        api.files[api.heads[w.intake.WORK_REF]][p]=b'{}'
    elif damage=='tree-truncated':
        get=api.get
        def truncated(p):
            value=get(p)
            if p.startswith('git/trees/'): value['truncated']=True
            return value
        monkeypatch.setattr(api,'get',truncated)
    elif damage=='page-missing': parsed['pages'].pop()
    elif damage=='context-oversize': parsed['pages'][0]['text']='x'*(w.MAX_CONTEXT+1)
    result=w.run(**args)
    assert result['status']=='NOT_EXECUTED' and not calls and not writes


def test_real_pdf_whole_context_and_unknown_publication():
    parsed=c.parse_original(Path('tests/fixtures/woton_original/source.pdf').read_bytes())
    context=w.public_context(parsed,{'received_at':'2026-09-21T01:27:16Z'})
    assert context['issuer_documents'][0]['pages']==parsed['pages']
    assert len(parsed['pages'])==133 and len(w.once.raw(context))<=w.MAX_CONTEXT
    assert context['issuer_documents'][0]['published_at'] is None
    assert context['issuer_documents'][0]['pdf_sha256']==c.PDF_SHA


def test_actual_provider_adapter_parameters_and_no_fallback(tmp_path,monkeypatch):
    args,_,_,_,_,_,_,_,_=setup(tmp_path,monkeypatch)
    captured=[]
    def model_call(stage,prompt,output_type,out,usage,**options):
        captured.append((stage,options));return pre(prompt)
    monkeypatch.setattr(w.once,'model_call',model_call)
    result=w.run(**{**args,'call':None})
    assert result['status']=='VALIDATED_FUNNEL_RESULT',result
    assert captured==[('pre',dict(max_prompt_bytes=524288,base_url=w.once.DEEPSEEK_BASE_URL,
        model='deepseek-flash',api_key_env='DEEPSEEK_API_KEY',provider='DEEPSEEK_OFFICIAL',
        extra_parameters={'reasoning':{'effort':'none'}}))]


def env():
    return {'GITHUB_SHA':'a'*40,'EXPECTED_CODE_SHA':'a'*40,'GITHUB_REPOSITORY':w.once.REPO,
        'GITHUB_REF':'refs/heads/main','GITHUB_WORKFLOW':'stock-business-research',
        'GITHUB_EVENT_NAME':'issues','GITHUB_RUN_ATTEMPT':'1','GITHUB_RUN_ID':'123',
        'REPORT_EVENT_ACTION':'labeled','REPORT_ISSUE_NUMBER':'297','REPORT_LABEL':w.LABEL,
        'REPORT_SENDER':'auguspp','REPORT_IS_PULL_REQUEST':'false'}


@pytest.mark.parametrize('key',list(env()))
def test_wrong_event_cannot_trigger_runtime(key):
    e=env();e[key]='wrong'
    with pytest.raises(ValueError):w.check_environment(e,'a'*40)


def test_same_workflow_isolated_exact_label_and_original_jobs_unchanged():
    text=Path('.github/workflows/stock-business-research.yml').read_text()
    original_tail=text.split('\n  deepseek-compatibility:\n',1)[1]
    assert w.once.blob(original_tail.encode()) == '4f62ac1c1c5979ac80c226659932994f4ee53c65'
    step=text.split('      - name: One approved Woton same-question report continuation\n',1)[1].split('      - name:',1)[0]
    assert "github.event.label.name == 'woton-h1-analysis-ready'" in step
    assert 'group: stock-business-first-v0' in text and 'cancel-in-progress: false' in text
    assert 'secrets.DEEPSEEK_API_KEY' in step and 'SUB2API' not in step and 'HITHINK' not in step
    assert 'decision_kernel.runtime.woton_report_continuation' in step
    assert '--output run-output' in step and 'timeout-minutes: 20' in step
    assert '  continue-woton-report:' not in text
    legacy=text.split('      - name: Original Stock validation, business sources, admission and Pre with necessary Quick\n',1)[1].split('        env:',1)[0]
    assert "github.event_name == 'workflow_dispatch'" in legacy


@pytest.mark.parametrize('name', ['prepare.json','input.json','launch.json','candidate.json','host-receipt.json'])
def test_uncertain_native_write_stops_without_overwriting_or_retry(tmp_path,monkeypatch,name):
    args,api,_,calls,_,_,writes,_,_=setup(tmp_path,monkeypatch)
    original=w.once.Retainer.native
    def lost(self,method,endpoint,body):
        result=original(self,method,endpoint,body)
        if endpoint.endswith('/'+name):
            self.uncertain=True
            raise RuntimeError('SYNTHETIC_LOST_WRITE_RESPONSE')
        return result
    monkeypatch.setattr(w.once.Retainer,'native',lost)
    result=w.run(**args)
    assert result['mutation_uncertain'] is True
    assert calls == ([] if name in {'prepare.json','input.json','launch.json'} else ['pre'])
    assert writes[-1][1].endswith('/'+name)
    count=len(writes); attempted=list(calls)
    repeated=w.run(**{**args,'output':tmp_path/'repeat'})
    assert repeated['status']==w.REUSED
    assert len(writes)==count and calls==attempted
