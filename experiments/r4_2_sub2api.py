"""One Human-approved, two-sample evaluation. No production selector or scheduler.

Reuses the original request builder, official SDK, full-byte guard, validators,
and create-only Git primitives. Saved source text is never execution authority.
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import subprocess
import zipfile

from decision_kernel.identity import canonical_hash
from decision_kernel.research_funnel import validate_funnel_transition
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import reviewed_full_input as full
from decision_kernel.runtime import stock_full_input as codec
from decision_kernel.runtime import single_quick_contract as single
from decision_kernel.runtime.current_state_delivery import GitHubAPI

M = 'f956ea490ede8f31fe82fae4a1dc7f43c94d1a6d'
EXPERIMENT = 'r4-2-sub2api-20260923-v1'
AUTHORITY = 'https://github.com/auguspp/decision-kernel/issues/526#issuecomment-5796637317'
WORK_REF = 'research-eval/' + EXPERIMENT
PREFIX = 'research_runs/evaluations/' + EXPERIMENT + '/'
S0_POLICY = ('LIMITED S0 EXPERIMENT ONLY, not a production method. Keep the ordinary single-Quick '
    'outcome responsibilities. FULL_CANDIDATE additionally requires a nonblank plausible differentiated '
    'hypothesis with its basis in route_reason, and both supporting and contradictory claims classified '
    'FACT or MARKET_CONTEXT with admitted evidence IDs. Do not relabel inference or invent contrary '
    'facts to satisfy this rule. Explain which evidence serves each side in counterevidence_review. '
    'STOP and WAIT retain their ordinary meanings; missing current required sources remains a host gap. '
    'This text replaces only the S1 statement that variant and contrary fact are not mandatory.')
SAMPLES = (
    dict(ticker='600362', run_id=35819538967, artifact_id=10732853090,
         archive_sha256='d1a6f74e9dd38802a262bf2d741e763ed57ec07e25a4777a272e60f78c520164',
         input_sha256='2626a4237beb14f674ae0e304466558ad5011730054ef9318410e57efbe0c5db',
         context_sha256='babf9b709345311f18d8f73872058b3e5140822e76a96c2bcbb0d381288a3014',
         candidate_hash='fb7890f96979320d492f235caa215e3d1e0ef955cb21addf53d7debb7e2540da',
         pages=[262, 216]),
    dict(ticker='603507', run_id=35620959045, artifact_id=10649281888,
         archive_sha256='a88c3948a2983605ba34841c23556e07cef52b316ba67d477e81cd38e3806745',
         input_sha256='99a80f2aba8f740b02f3110ca6ac84961664517983cbe7802a59cac4ae043d02',
         context_sha256='8f87b903b2912cbd558d84442e80fff0f4cc1aaefea26eb306cdb2bfff7b1ebe',
         candidate_hash='75d72a7996390daec61ec652f502c833195a8ef5232e31d79b1d173df8e6ae92',
         pages=[215]),
)


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(value if isinstance(value, bytes) else once.raw(value))


def load_sample(api, spec, out):
    artifact = api.get('actions/artifacts/' + str(spec['artifact_id']))
    once.require(artifact['workflow_run']['id'] == spec['run_id'] and not artifact['expired']
                 and artifact['digest'] == 'sha256:' + spec['archive_sha256'], 'EVAL_ARCHIVE_IDENTITY')
    archive = api.archive(artifact)
    once.require(once.sha(archive) == spec['archive_sha256'], 'EVAL_ARCHIVE_BYTES')
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        once.require(z.testzip() is None and len(z.namelist()) == len(set(z.namelist())), 'EVAL_ARCHIVE_MEMBERS')
        packet, candidate, checked = single.read_saved_result(z.read('input.json'), z.read('candidate.json'))
        once.require(once.sha(z.read('input.json')) == spec['input_sha256']
                     and canonical_hash(candidate) == spec['candidate_hash'], 'EVAL_OLD_RESULT_IDENTITY')
        original = once.identity._json(z.read('pre-model-input.json'))
        context = original['public_context']
        plain = once.raw(context)
        once.require(once.sha(plain) == spec['context_sha256']
                     and context == once.identity._json(z.read('quick-model-input.json'))['public_context'],
                     'EVAL_COMPLETE_CONTEXT')
        source = next(s.model_dump(mode='json') for s in packet.source_refs if s.purpose == 'MODEL_CONTEXT')
        stored = once.identity._checked_source(source, lambda s: api.file(s['path'], s['ref']))
        once.require(stored == z.read('source.json'), 'EVAL_RETAINED_SOURCE_DIFFERENT')
        decoded = full.unpack(stored, ticker=spec['ticker']) if 'policy' in once.identity._json(stored) else stored
        once.require(decoded == plain, 'EVAL_LOSSLESS_SOURCE')
        full._context(plain, spec['ticker'])
        once.require([d['page_count'] for d in context['issuer_documents']] == spec['pages'], 'EVAL_PAGE_SCOPE')
        discovery = candidate.discovery
        once.require(once.pre_prompt(packet, discovery, context) == original, 'EVAL_ORIGINAL_PROMPT_DIFFERENT')
        put(out / 'original-input.json', z.read('input.json'))
        put(out / 'original-source.json', stored)
        put(out / 'source-identity.json', {**spec, 'source': source,
            'original_cutoff': packet.research_cutoff.isoformat(),
            'original_execution_id': packet.execution_id,
            'historical_validation_status': checked.status.value,
            'meaning': 'IMMUTABLE_REPLAY_NOT_CURRENT_SOURCE_ADMISSION'})
        return packet, discovery, context


def parameters(prompt, output_type, arm):
    once.require(arm in {'O', 'S0', 'S1'} and
                 ((arm == 'O') == (output_type in {once.PreResearchResult, once.QuickResearchResult})),
                 'EVAL_ARM_MODEL')
    _, _, _, params = once.model_request(prompt, output_type,
        max_prompt_bytes=codec.REQUEST_BYTES, model=once.MODEL)
    if arm == 'S0':
        params = deepcopy(params)
        params['text']['format']['schema']['properties']['route']['description'] = S0_POLICY
    return params


def request_guard(prompt, params):
    plain = once.raw(prompt['public_context'])
    ticker = prompt['discovery_observation']['ticker']
    full._context(plain, ticker)
    once.require(params['model'] == once.MODEL and params['instructions'] == once.SYSTEM
                 and params['tools'] == [] and params['store'] is False
                 and params['max_output_tokens'] == once.MAX_OUTPUT_TOKENS
                 and 'reasoning' not in params, 'EVAL_PROVIDER_PARAMETERS')
    encoded = once.raw({**params, 'stream': True})
    once.require(len(encoded) <= codec.REQUEST_BYTES, 'EVAL_REQUEST_SIZE_NO_CLIPPING')
    return codec.FinalRequestCheck(plain, ticker, once.BASE_URL + '/responses', encoded,
                                  policy='R4_2_EXACT_SAVED_INPUT_SUB2API')


def preview(prompt, params):
    """Construct through the REAL SDK; no transport or real credential is possible."""
    from openai import OpenAI, DefaultHttpxClient
    receipt = {}
    check = request_guard(prompt, params).hook(receipt)
    class Prepared(BaseException): pass
    def hook(request):
        check(request)
        raise Prepared()
    class DenyTransport:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def close(self): pass
        def handle_request(self, request): raise AssertionError('EVAL_PREVIEW_TRANSPORT_FORBIDDEN')
    with OpenAI(api_key='not-a-real-credential', base_url=once.BASE_URL, max_retries=0,
                http_client=DefaultHttpxClient(transport=DenyTransport(), trust_env=False,
                    follow_redirects=False, event_hooks={'request': [hook]})) as client:
        try:
            with client.responses.stream(**params) as stream: stream.get_final_response()
        except Prepared: pass
        else: raise once.TrialError('EVAL_PREVIEW_MISSING')
    once.require(bool(receipt), 'EVAL_PREVIEW_MISSING')
    return receipt


def send_one(prompt, output_type, arm, out):
    """Finite evaluation adapter, using the same SDK and original raw-first policy."""
    from openai import OpenAI, DefaultHttpxClient
    params = parameters(prompt, output_type, arm)
    prepared = preview(prompt, params)
    put(out / 'prompt.json', once.raw(prompt))
    put(out / 'output-format.json', params['text']['format'])
    put(out / 'sdk-preview.json', prepared)
    record = dict(arm=arm, stage=prompt['stage'], started_at=once.now(), provider='SUB2API',
        requested_model=once.MODEL, provider_base_url=once.BASE_URL, monetary_cap=None,
        max_output_tokens=once.MAX_OUTPUT_TOKENS, reasoning='PROVIDER_DEFAULT_NOT_FROZEN',
        automatic_retries=0, fallback=False, response_received=False, physical_sends=0,
        prompt_sha256=once.sha(once.raw(prompt)), format_sha256=once.sha(once.raw(params['text']['format'])),
        system_sha256=once.sha(once.SYSTEM.encode()), phase='PRE_SEND', pre_send={})
    check = request_guard(prompt, params).hook(record['pre_send'])
    def hook(request):
        check(request)
        once.require(record['pre_send']['request_sha256'] == prepared['request_sha256'], 'EVAL_PREVIEW_BYTES_CHANGED')
        record['physical_sends'] += 1
        record['phase'] = 'RESPONSE'
    result = None
    try:
        once.require(bool(os.environ.get('SUB2API_API_KEY')), 'SUB2API_CONNECTION_MISSING')
        with OpenAI(api_key=os.environ['SUB2API_API_KEY'], base_url=once.BASE_URL, max_retries=0,
            timeout=180, http_client=DefaultHttpxClient(trust_env=False, follow_redirects=False,
                event_hooks={'request': [hook]})) as client:
            with client.responses.stream(**params) as stream: response = stream.get_final_response()
        record.update(response_received=True, phase='OUTPUT_RETENTION', response_id=response.id,
            returned_model=response.model, provider_status=response.status,
            usage=response.usage.model_dump(mode='json') if response.usage else None)
        # Never save reasoning items, credentials, headers or full provider error bodies.
        text = response.output_text
        put(out / 'model-output.txt', text.encode())
        record.update(output_sha256=once.sha(text.encode()), output_text_retained=True, phase='APPLICATION_VALIDATION')
        once.require(response.status == 'completed', 'EVAL_MODEL_INCOMPLETE')
        once.require(all(i.type in {'message', 'reasoning'} for i in response.output), 'EVAL_UNEXPECTED_TOOL_OUTPUT')
        result = output_type.model_validate(once.identity._json(text.encode()))
        claims = result.claims if output_type is single.QuickAssessment else ()
        allowed = set(prompt['evidence_ids'])
        once.require(all(str(e) in allowed for c in claims for e in c.evidence_artifact_ids), 'EVAL_UNADMITTED_CLAIM')
        record.update(status='STRUCTURE_VALID_NOT_QUALITY_ACCEPTANCE', phase='COMPLETE')
        put(out / 'parsed.json', result)
    except Exception as exc:
        record.update(status='FAILED', error_type=type(exc).__name__, **once._provider_error_diagnostic(exc))
        if record['phase'] == 'APPLICATION_VALIDATION':
            record['validation'] = once._application_validation_diagnostic(exc, output_type)
        # Transport uncertainty is not a permit to start another arm or retry.
        record['stop_batch'] = not record['response_received'] or record['phase'] != 'APPLICATION_VALIDATION'
    finally:
        record['finished_at'] = once.now()
        put(out / 'usage.json', record)
    return result, record


def run_arms(packet, discovery, context, out, *, send=send_one):
    rows = []
    base = once.pre_prompt(packet, discovery, context)
    pre, row = send(base, once.PreResearchResult, 'O', out / 'O' / 'pre'); rows.append(row)
    if row.get('stop_batch'): return rows, True
    if pre is not None:
        try:
            once.validate_pre_research_transition(discovery, pre, packet.seed_evidence_artifacts)
        except Exception as exc:
            put(out / 'O' / 'transition.json', {'status':'REJECTED', 'error_type':type(exc).__name__})
            pre = None
    if pre is not None and pre.route.value == 'CONTINUE_TO_QUICK':
        q = {**base, 'stage':'QUICK', 'pre_research':pre.model_dump(mode='json'), 'pre_research_hash':canonical_hash(pre)}
        quick, row = send(q, once.QuickResearchResult, 'O', out / 'O' / 'quick'); rows.append(row)
        if row.get('stop_batch'): return rows, True
        if quick is not None:
            try:
                validate_funnel_transition(discovery, pre, quick, packet.seed_evidence_artifacts)
                transition = {'status':'VALIDATED_LEGACY_TRANSITION_NOT_QUALITY_ACCEPTANCE'}
            except Exception as exc: transition = {'status':'REJECTED', 'error_type':type(exc).__name__}
            put(out / 'O' / 'transition.json', transition)
    else:
        put(out / 'O' / 'quick-not-run.json', {'reason':'PRE_NOT_VALID_OR_DID_NOT_REQUEST_QUICK'})
    sp = packet.model_copy(update={'method_version':single.METHOD_VERSION,'prompt_version':single.PROMPT_VERSION})
    prompt = once.initial_prompt(sp, discovery, context)
    for arm in ('S0','S1'):
        _, row = send(prompt, single.QuickAssessment, arm, out / arm); rows.append(row)
        if row.get('stop_batch'): return rows, True
    once.require(len(rows) <= 4, 'EVAL_SAMPLE_CALL_BOUND')
    return rows, False


def retain_results(ret, api, out, launch):
    """Native Git objects through the existing uncertain-write stop primitive."""
    rows = []
    files = sorted(p for p in out.rglob('*') if p.is_file())
    once.require(len(files) <= 128 and sum(p.stat().st_size for p in files) <= 32*1024*1024, 'EVAL_ARCHIVE_SCOPE')
    for path in files:
        once.require(not path.is_symlink(), 'EVAL_ARCHIVE_SYMLINK')
        relative = path.relative_to(out).as_posix()
        body = path.read_bytes()
        item = ret.native('POST','git/blobs',{'encoding':'base64','content':base64.b64encode(body).decode()})
        once.require(item['sha'] == once.blob(body), 'EVAL_BLOB_WRITE_MISMATCH')
        rows.append({'path':PREFIX+relative,'mode':'100644','type':'blob','sha':item['sha']})
    parent = launch['ref']
    tree = ret.native('POST','git/trees',{'base_tree':api.get('git/commits/'+parent)['tree']['sha'],'tree':rows})['sha']
    commit = ret.native('POST','git/commits',{'message':'Retain bounded R4-2 Sub2API evaluation, not production Research',
                                           'tree':tree,'parents':[parent]})['sha']
    fresh = GitHubAPI(os.environ['GH_TOKEN'])
    once.require(fresh.get('git/ref/heads/'+WORK_REF)['object']['sha'] == parent, 'EVAL_CONCURRENT_RESULT_WRITE')
    ret.native('PATCH','git/refs/heads/'+WORK_REF,{'sha':commit,'force':False})
    for row, path in zip(rows,files,strict=True):
        blob = fresh.get('git/blobs/'+row['sha'])
        once.require(base64.b64decode(blob['content']) == path.read_bytes(), 'EVAL_RESULT_READBACK')
    return {'commit':commit,'files':len(files),'tree':tree,'readback':'EXACT_BYTES',
            'meaning':'EVALUATION_ONLY_NOT_PRODUCTION_OR_HUMAN_ACCEPTANCE'}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--execute',action='store_true')
    args = parser.parse_args()
    once.require(args.execute and os.environ.get('R4_2_APPROVAL') == '5796637317'
                 and os.environ.get('GITHUB_RUN_ATTEMPT') == '1', 'EVAL_EXPLICIT_AUTHORITY')
    code = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    once.require(code == os.environ.get('EVAL_CODE_SHA'), 'EVAL_CODE_IDENTITY')
    api = GitHubAPI(os.environ['GH_TOKEN'],max_calls=512)
    out = Path(PREFIX); out.mkdir(parents=True,exist_ok=False)
    scope = dict(experiment=EXPERIMENT,authority=AUTHORITY,human_words='你用 sub2api 吧，预算不设限',
        code_commit=code,runtime_base=M,samples=SAMPLES,max_model_calls=8,monetary_cap=None,
        provider='SUB2API',model=once.MODEL,provider_base_url=once.BASE_URL,
        investment_authority='NONE',production_activation=False,automatic_retry=False,
        paid_evaluator_calls=0,new_financial_source_fetches=0,hosted_calls=0)
    put(out/'scope.json',scope)
    # Validate BOTH complete samples before any model call or consumption marker.
    samples = [(s,load_sample(api,s,out/s['ticker']/'original')) for s in SAMPLES]
    ret = once.Retainer(api,{'id':EXPERIMENT,'work_ref':WORK_REF,'prefix':PREFIX,
                            'continuation':{'kind':'ISOLATED_EVALUATION','authority':AUTHORITY}},code,out)
    launch = ret.begin()  # Original create-only launch, shared by all arms.
    records=[]; stop=False
    try:
        for spec,(packet,discovery,context) in samples:
            rows,stop = run_arms(packet,discovery,context,out/spec['ticker'])
            records.extend({**r,'ticker':spec['ticker']} for r in rows)
            if stop: break
    except Exception as exc:
        stop=True
        put(out/'failure.json',{'error_type':type(exc).__name__,'automatic_retry':False})
    summary={**scope,'records':records,'model_requests_started':sum(r.get('physical_sends',0) for r in records),
             'stopped_early':stop,'status':'EXECUTION_RECORDS_NOT_QUALITY_ACCEPTANCE',
             'billing':'ACCOUNT_BILL_NOT_RETRIEVED_NO_MONETARY_LIMIT', 'finished_at':once.now()}
    once.require(len(records)<=8 and summary['model_requests_started']<=8,'EVAL_TOTAL_CALL_BOUND')
    put(out/'receipt.json',summary)
    # Saving results is not another model attempt, even following a transport gap.
    publication=retain_results(ret,api,out,launch)
    put(out/'publication.json',publication)  # Artifact copy; remote commit cannot include its own hash.
    print('EVAL_RESULT_COMMIT='+publication['commit'])
    print('EVAL_MODEL_REQUESTS='+str(summary['model_requests_started']))
    return 1 if stop else 0


if __name__ == '__main__': raise SystemExit(main())
