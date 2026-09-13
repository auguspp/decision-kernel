"""Synthetic Human/visual records; real original gates, PDFium and saved executor.

No live provider/source access, genuine Human consent or Research acceptance is
claimed by these fixtures. Reuse existing fake Git and original stage fixtures.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest
import pypdfium2

from decision_kernel.runtime import disclosure_continuation as continuation
from decision_kernel.runtime import disclosure_source_reading as pages
from decision_kernel.runtime import incremental_disclosure as work
from decision_kernel.runtime import saved_disclosure_preparation as prep
from decision_kernel.runtime import saved_disclosure_host as host
from decision_kernel.runtime import prepared_disclosure_research as executor
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import external_research_identity as identity
from decision_kernel.runtime.current_state_delivery import GitHubReadError
from test_saved_disclosure_preparation import setup, CODE, WORK, READING, AT
from test_saved_research_once import pre, quick


def fixture(tmp_path, monkeypatch, *, text='', code='603986'):
    args, api, clock, raw, pdf = setup(tmp_path, monkeypatch, text=text, code=code)
    key = work._packet(raw).assessment_input_hash
    packet = identity._json(raw); evidence = packet['evidence'][0]
    failure = {'schema_version': 1, 'record_kind': 'PRE_EXECUTION_FAILURE_NOT_VALIDATOR_RESULT',
        'assessment_input_hash': key, 'case_id': code, 'packet_blob': read.blob_sha(raw),
        'packet_sha256': read.sha256(raw), 'status': 'SOURCE_OR_INPUT_PREPARATION_INCOMPLETE',
        'research_execution': 'NOT_EXECUTED', 'funnel_status': 'NOT_REACHED', 'formal_research_budget_used': 0,
        'error_code': 'required page text unavailable' if not text else 'required text contains encoding damage',
        'started_at': '2026-09-12T12:00:00Z', 'finished_at': '2026-09-12T12:01:00Z',
        'automatic_retry': False, **read.AUTHORITY}
    root = work.request_path(key).removesuffix('packet.json')
    api.snapshots[WORK][root+'failure.json'] = once.raw(failure)
    old_failure = once.source_ref(root+'failure.json', WORK, once.raw(failure), 'prior')
    old_packet = once.source_ref(root+'packet.json', WORK, raw, work.PACKET_PURPOSE)
    exposure = read.assemble(code_commit=CODE, checked_at=AT, check_started_at=AT, lanes={},
        research={'handoffs': {'active': []}, 'candidate_work': {'items': [
            {'sources': {'failure': old_failure, 'packet': old_packet}}]}}, capabilities=[], refresh_identity={})
    api.snapshots[READING]['current-state.json'] = read.json_bytes(exposure)
    exposed = once.source_ref('current-state.json', READING, read.json_bytes(exposure), 'exposure')
    exposed.pop('sha256')  # Existing _checked_source validates an exact Git blob, normalizes actual bytes.
    comment = {'id': 7, 'issue_url': f'https://api.github.com/repos/{read.REPOSITORY}/issues/297',
               'body': 'Synthetic permission ONLY for this source-reading test. 好，继续',
               'created_at': '2026-09-12T13:01:00Z', 'updated_at': '2026-09-12T13:01:00Z'}
    api.comment = comment
    request = {'schema_version': 2, 'mode': continuation.READING_MODE, 'enabled': True,
        'source_run_id': args['run']['id'], 'exposed_reading': exposed,
        'permission': {'issue_number': 297, 'comment_id': 7, 'record_body': comment['body'],
            'body_sha256': read.sha256(comment['body'].encode()), 'verbatim': '好，继续',
            'response_kind': 'EXPLICIT_RESEARCH_CONTINUE', 'tickers': [code]},
        'items': [{'ticker': code, 'assessment_input_hash': key,
            'predecessor': {'kind': 'PRE_EXECUTION_FAILURE', 'packet': old_packet, 'input': None, 'result': old_failure},
            'prior_question': prep.QUESTION, 'follow_up_question': prep.QUESTION,
            'new_evidence_reason': 'Synthetic source newly readable, not a new independent source.',
            'required_reading_pdf_sha256s': [evidence['pdf_sha256']]}]}
    api.snapshots[CODE][continuation.REQUEST_PATH] = once.raw(request)
    api.commits.update({CODE: {'sha': CODE, 'committer': {'date': '2026-09-12T13:02:00Z'}},
        WORK: {'sha': WORK, 'committer': {'date': '2026-09-12T12:02:00Z'}},
        READING: {'sha': READING, 'committer': {'date': '2026-09-12T13:00:30Z'}}})
    clock.wait(180)
    with pypdfium2.PdfDocument(pdf) as doc:
        page = doc[0]
        try: rendered, _ = pages.render_page(page)
        finally: page.close()
    note = {'schema_version': 1, 'pdf_sha256': evidence['pdf_sha256'], 'page_number': 1,
        'engine': pages.engine_identity(), 'render': rendered, 'review_kind': 'AI_VISUAL_READING',
        'scope': 'WHOLE_PAGE_WITH_EXPLICIT_UNKNOWNS', 'reviewed_at': '2026-09-12T12:59:00Z',
        'text': 'Synthetic test reading only; no actual issuer or signature.',
        'unknowns': ['Synthetic fixture, not semantic acceptance.']}
    note_path = pages.review_path(evidence['pdf_sha256'], 1)
    api.snapshots[CODE][note_path] = once.raw(note)
    call, file = api._call, api.file
    def checked_call(method, endpoint):
        if endpoint == 'issues/comments/7':
            assert method == 'GET'
            return SimpleNamespace(json=lambda: deepcopy(api.comment))
        if endpoint == 'git/ref/heads/' + read.READ_REF:
            return SimpleNamespace(json=lambda: {'object': {'type': 'commit', 'sha': READING}})
        return call(method, endpoint)
    def checked_file(path, ref):
        try: return file(path, ref)
        except KeyError: raise GitHubReadError('GitHub HTTP 404') from None
    monkeypatch.setattr(api, '_call', checked_call)
    monkeypatch.setattr(api, 'file', checked_file)
    spec = once.source_ref(continuation.REQUEST_PATH, CODE, once.raw(request), continuation.REQUEST_PURPOSE)
    args['continuation_request_source'] = spec
    return args, api, clock, raw, request, spec, note_path


def check(args, clock, raw, spec):
    return continuation.check(api=args['api'], code_commit=CODE, request_source=spec,
                              new_packet_raw=raw, checked_at=clock())


def update_request(api, args, request):
    raw = once.raw(request); api.snapshots[CODE][continuation.REQUEST_PATH] = raw
    spec = once.source_ref(continuation.REQUEST_PATH, CODE, raw, continuation.REQUEST_PURPOSE)
    args['continuation_request_source'] = spec
    return spec


def prepared_call(args, api, clock, tmp_path, monkeypatch, *, use_quick=False, fail=False):
    prepared = prep.prepare_reserved(**args)
    assert prepared['status'] == 'INPUT_PREPARED_NOT_EXECUTED', prepared
    calls = []
    def call(stage, prompt, model, out, usage):
        calls.append(stage)
        if fail: raise RuntimeError('synthetic provider failed')
        return pre(prompt, 'CONTINUE_TO_QUICK' if use_quick else 'WAIT_FOR_TRIGGER') if stage == 'pre' else quick(prompt)
    monkeypatch.setattr(once, 'model_call', call)
    result = host.execute_prepared(api=api, prepared=prepared, code_commit=CODE,
                                  output=tmp_path/'executed', clock=clock)
    return prepared, result, calls


@pytest.mark.parametrize('use_quick', [False, True])
def test_real_original_gates_and_executor_preserve_parent_and_block_repeat(tmp_path, monkeypatch, use_quick):
    args, api, clock, raw, request, spec, _ = fixture(tmp_path, monkeypatch)
    parent = deepcopy(api.snapshots[WORK])
    checked = check(args, clock, raw, spec)
    assert checked['public_context']['new_body_hashes'] == []
    assert all('sha256' in s for s in checked['source_refs'])
    prepared, result, calls = prepared_call(args, api, clock, tmp_path, monkeypatch, use_quick=use_quick)
    assert result['status'] == 'VALIDATED_FUNNEL_RESULT', result
    assert calls == (['pre', 'quick'] if use_quick else ['pre'])
    assert all(api.snapshots[api.work][p] == b for p, b in parent.items())
    assert all(p.startswith(checked['execution_prefix']) for p in api.writes)
    assert not any(p.endswith('/packet.json') for p in api.writes)
    input_raw = api.file(prepared['input_source']['path'], prepared['input_source']['ref'])
    packet = executor.ExternalResearchInputPacket.model_validate(identity._json(input_raw))
    cs = executor._one(packet, 'MODEL_CONTEXT')
    context = identity._json(api.file(cs['path'], cs['ref']))
    assert context['disclosure_packet'] == identity._json(raw)
    assert context['continuation_context']['new_body_hashes'] == []
    assert len(context['continuation_context']['new_reading_hashes']) == 1
    assert '新工作项' not in identity._json(api.file(executor._one(packet, prep.DISCOVERY_PURPOSE)['path'],
                                              executor._one(packet, prep.DISCOVERY_PURPOSE)['ref']))['why_now']
    writes = list(api.writes)
    repeat = prep.prepare_reserved(**dict(args, output=tmp_path/'repeat'))
    assert repeat['status'] == 'ALREADY_ATTEMPTED_NO_PREPARATION' and api.writes == writes
    replay = host.execute_prepared(api=api, prepared=prepared, code_commit=CODE, output=tmp_path/'repeat-execute', clock=clock)
    assert replay['status'] == 'ALREADY_LAUNCHED_NO_EXECUTION' and api.writes == writes
    assert calls == (['pre', 'quick'] if use_quick else ['pre'])
    plan = work.plan_one(archive_raw=args['scan_raw'], artifact=args['scan_artifact'], run=args['run'],
        work_files=api.snapshots[api.work], work_commit=api.work, selected_at=clock())
    assert plan['selected'] is None and plan['reserved_count'] == 1


@pytest.mark.parametrize('damage', ['permission-body', 'permission-time', 'wrong-ticker', 'no-intent',
    'same-request-duplicate', 'new-key', 'wrong-body', 'changed-question', 'future-exposure',
    'wrong-failure', 'no-gap', 'foreign-request', 'disabled', 'exposure-other-result'])
def test_invalid_continuation_rejected_before_any_write(tmp_path, monkeypatch, damage):
    args, api, clock, raw, request, spec, _ = fixture(tmp_path, monkeypatch)
    entry = request['items'][0]
    if damage == 'permission-body': api.comment['body'] += ' revoked'
    elif damage == 'permission-time': api.comment['created_at'] = '2027-01-01T00:00:00Z'
    elif damage == 'wrong-ticker': request['permission']['tickers'] = ['300750']
    elif damage == 'no-intent': request['permission']['response_kind'] = 'ENGINEERING_CONTINUE'
    elif damage == 'same-request-duplicate': request['items'].append(deepcopy(entry))
    elif damage == 'new-key': entry['assessment_input_hash'] = 'f'*64
    elif damage == 'wrong-body': entry['required_reading_pdf_sha256s'] = ['f'*64]
    elif damage == 'changed-question': entry['follow_up_question'] = 'Buy now'
    elif damage == 'future-exposure': api.commits[READING]['committer']['date'] = '2026-09-12T13:01:01Z'
    elif damage == 'wrong-failure': entry['predecessor']['result']['git_blob'] = 'f'*40
    elif damage == 'no-gap':
        entry['predecessor']['result']['path'] = entry['predecessor']['packet']['path']
    elif damage == 'disabled': request['enabled'] = False
    elif damage == 'exposure-other-result': request['exposed_reading']['git_blob'] = 'f'*40
    spec = update_request(api, args, request)
    if damage == 'foreign-request': spec['ref'] = WORK
    with pytest.raises((ValueError, KeyError)):
        check(args, clock, raw, spec)
    prepared = prep.prepare_reserved(**dict(args, continuation_request_source=spec))
    assert prepared['status'] == 'NOT_EXECUTED' and not prepared['formal_research_started'] and api.writes == []


@pytest.mark.parametrize('gap', ['missing-note', 'changed-pixels'])
def test_missing_readable_material_retains_child_failure_not_parent_mutation(tmp_path, monkeypatch, gap):
    args, api, clock, raw, request, spec, note_path = fixture(tmp_path, monkeypatch)
    old = deepcopy(api.snapshots[WORK])
    if gap == 'missing-note': del api.snapshots[CODE][note_path]
    else:
        note = identity._json(api.snapshots[CODE][note_path]); note['render']['pixels_sha256'] = 'f'*64
        api.snapshots[CODE][note_path] = once.raw(note)
    checked = check(args, clock, raw, spec)
    prepared = prep.prepare_reserved(**args)
    assert prepared['status'] == 'NOT_EXECUTED' and not prepared['formal_research_started']
    assert api.writes == [checked['execution_prefix']+'failure.json']
    assert all(api.snapshots[api.work][p] == b for p, b in old.items())
    repeat = prep.prepare_reserved(**dict(args, output=tmp_path/'repeat'))
    assert repeat['status'] == 'ALREADY_ATTEMPTED_NO_PREPARATION'


def test_permission_rechecked_after_launch_before_model(tmp_path, monkeypatch):
    args, api, clock, raw, request, spec, _ = fixture(tmp_path, monkeypatch)
    prepared = prep.prepare_reserved(**args)
    assert prepared['status'] == 'INPUT_PREPARED_NOT_EXECUTED', prepared
    native = once.Retainer.native
    def revoke(self, method, endpoint, body):
        value = native(self, method, endpoint, body)
        if endpoint.endswith('/launch.json'): api.comment['body'] += ' revoked'
        return value
    monkeypatch.setattr(once.Retainer, 'native', revoke)
    monkeypatch.setattr(once, 'model_call', lambda *a: pytest.fail('no spend after revoked permission'))
    result = host.execute_prepared(api=api, prepared=prepared, code_commit=CODE, output=tmp_path/'execute', clock=clock)
    assert result['status'] == 'NOT_EXECUTED' and not result['formal_research_started']
    assert any(p.endswith('/launch.json') for p in api.writes)


def test_provider_failure_stays_gap_and_has_no_retry(tmp_path, monkeypatch):
    args, api, clock, _, _, _, _ = fixture(tmp_path, monkeypatch)
    prepared, result, calls = prepared_call(args, api, clock, tmp_path, monkeypatch, fail=True)
    assert result['status'] == 'EXECUTION_GAP' and calls == ['pre']
    assert prep.prepare_reserved(**dict(args, output=tmp_path/'repeat'))['status'] == 'ALREADY_ATTEMPTED_NO_PREPARATION'


def test_without_explicit_continuation_parent_remains_blocked(tmp_path, monkeypatch):
    args, api, _, _, _, _, _ = fixture(tmp_path, monkeypatch)
    args.pop('continuation_request_source')
    prepared = prep.prepare_reserved(**args)
    assert prepared['status'] == 'ALREADY_ATTEMPTED_NO_PREPARATION' and api.writes == []


@pytest.mark.parametrize('suffix', ['continuations/0/input.json','continuations/007/input.json',
    'continuations/7/packet.json','continuations/x/input.json','other/7/input.json','continuations/7/a/b.json'])
def test_invalid_child_paths_cannot_reset_or_forge_a_packet(suffix):
    with pytest.raises(ValueError): work.split_work_path(work.WORK_PREFIX+'a'*64+'/'+suffix)


def test_stable_execution_identity_ignores_clock_wording_and_code(tmp_path, monkeypatch):
    args, api, clock, raw, request, spec, _ = fixture(tmp_path, monkeypatch)
    before = check(args, clock, raw, spec)
    request['items'][0]['new_evidence_reason'] += ' added explanation'
    spec = update_request(api, args, request); clock.wait(5)
    after = check(args, clock, raw, spec)
    assert before['execution_id'] == after['execution_id'] and before['execution_prefix'] == after['execution_prefix']


def test_same_source_mode_does_not_weaken_original_new_packet_continuation(tmp_path, monkeypatch):
    args, api, clock, raw, request, spec, _ = fixture(tmp_path, monkeypatch)
    entry = request['items'][0]
    request = {'schema_version': 1, 'enabled': True, 'mode': continuation.MODE,
        'permission': {**{k:v for k,v in request['permission'].items() if k!='tickers'}, 'ticker': entry['ticker']},
        'exposed_reading': request['exposed_reading'], 'new_assessment_input_hash': entry['assessment_input_hash'],
        **{k:entry[k] for k in ('predecessor','prior_question','follow_up_question','new_evidence_reason')}}
    spec = update_request(api, args, request)
    with pytest.raises(ValueError, match='not reset'): check(args, clock, raw, spec)


def host_arguments(args, api, clock, tmp_path, monkeypatch):
    get = api.get
    def get_source(endpoint):
        if endpoint == 'actions/runs/' + str(args['run']['id']): return args['run']
        if endpoint == f"actions/runs/{args['run']['id']}/artifacts?per_page=100":
            return {'total_count': 2, 'artifacts': [args['scan_artifact'], args['body_artifact']]}
        return get(endpoint)
    monkeypatch.setattr(api, 'get', get_source)
    monkeypatch.setattr(api, 'archive', lambda a: args['scan_raw'] if a['id']==100 else args['body_raw'], raising=False)
    return dict(api=api, source_run_id=args['run']['id'], code_commit=CODE, output=tmp_path/'host',
        clock=clock, prepare=lambda **kw: prep.prepare_reserved(**kw, wait=clock.wait),
        continuation_request_source=args['continuation_request_source'])


def test_existing_host_opt_in_uses_original_prepare_execute_then_repeat_is_zero_spend(tmp_path, monkeypatch):
    args, api, clock, raw, _, _, _ = fixture(tmp_path, monkeypatch)
    host_args = host_arguments(args, api, clock, tmp_path, monkeypatch)
    calls=[]
    def call(stage, prompt, *_): calls.append(stage); return pre(prompt)
    monkeypatch.setattr(once, 'model_call', call)
    result = host.consume(**host_args)
    assert result['status'] == 'EXPLICIT_READING_CONTINUATIONS_PROCESSED', result
    assert result['items'][0]['research_status']=='VALIDATED_FUNNEL_RESULT' and calls==['pre']
    writes = list(api.writes)
    repeated = host.consume(**dict(host_args, output=tmp_path/'host-repeat'))
    assert repeated['status']=='CONTINUATIONS_ALREADY_ATTEMPTED_NO_EXECUTION'
    assert repeated['items'][0]['research_status']=='NOT_EXECUTED' and calls==['pre'] and api.writes==writes


def test_existing_host_default_does_not_consume_enabled_request(tmp_path, monkeypatch):
    args, api, clock, raw, _, _, _ = fixture(tmp_path, monkeypatch)
    kwargs = host_arguments(args, api, clock, tmp_path, monkeypatch)
    kwargs.pop('continuation_request_source')
    monkeypatch.setattr(once, 'model_call', lambda *a: pytest.fail('default cannot retry parent'))
    result=host.consume(**kwargs)
    assert result['status']=='NO_UNRESERVED_PACKET_IN_SAVED_SCAN' and result['items']==[] and api.writes==[]


def test_corrupt_shared_source_never_reserves_a_continuation(tmp_path, monkeypatch):
    args, api, clock, _, _, _, _ = fixture(tmp_path, monkeypatch)
    args['body_raw'] += b'corrupt'
    kwargs = host_arguments(args, api, clock, tmp_path, monkeypatch)
    result=host.consume(**kwargs)
    assert result['status']=='BATCH_INCOMPLETE' and api.writes==[]


def test_host_wont_switch_scans_for_a_green_result(tmp_path, monkeypatch):
    args, api, clock, _, request, _, _ = fixture(tmp_path, monkeypatch)
    request['source_run_id'] += 1
    update_request(api,args,request)
    result=host.consume(**host_arguments(args,api,clock,tmp_path,monkeypatch))
    assert result['status']=='BATCH_INCOMPLETE' and api.writes==[]


@pytest.mark.parametrize('existing', ['source.json','failure.json','launch.json','input.json','candidate.json','receipt.json'])
def test_any_child_preparation_or_result_blocks_new_preparation(tmp_path,monkeypatch,existing):
    args,api,clock,raw,_,spec,_=fixture(tmp_path,monkeypatch)
    prefix=check(args,clock,raw,spec)['execution_prefix']
    api.snapshots[WORK][prefix+existing]=b'{}'
    result=prep.prepare_reserved(**args)
    assert result['status']=='ALREADY_ATTEMPTED_NO_PREPARATION' and api.writes==[]


def test_changed_reading_after_preparation_cannot_be_egressed(tmp_path,monkeypatch):
    args,api,clock,raw,_,_,_=fixture(tmp_path,monkeypatch)
    prepared=prep.prepare_reserved(**args)
    assert prepared['status']=='INPUT_PREPARED_NOT_EXECUTED'
    packet=executor.ExternalResearchInputPacket.model_validate(identity._json(api.file(
        prepared['input_source']['path'],prepared['input_source']['ref'])))
    context_ref=executor._one(packet,'MODEL_CONTEXT')
    api.snapshots[context_ref['ref']][context_ref['path']]+=b'changed'
    monkeypatch.setattr(once,'model_call',lambda *a:pytest.fail('no call for changed bytes'))
    with pytest.raises(ValueError):
        host.execute_prepared(api=api,prepared=prepared,code_commit=CODE,output=tmp_path/'execute',clock=clock)
    assert not any(p.endswith('/launch.json') for p in api.writes)


def test_two_authorized_parents_share_one_permission_but_never_share_an_execution(tmp_path,monkeypatch):
    from io import BytesIO
    from zipfile import ZipFile
    from test_saved_disclosure_preparation import archive
    from test_incremental_disclosure import scan
    first=fixture(tmp_path/'first',monkeypatch,code='603986')
    second=fixture(tmp_path/'second',monkeypatch,code='300750')
    args,api,clock,raw,request,_,_=first
    other_args,other_api,_,other_raw,other_request,_,_=second
    api.snapshots[WORK].update(other_api.snapshots[WORK])
    request['items']+=other_request['items'];request['permission']['tickers'].append('300750')
    exposure=read.assemble(code_commit=CODE,checked_at=AT,check_started_at=AT,lanes={},
        research={'handoffs':{'active':[]},'candidate_work':{'items':[
            {'sources':{'failure':i['predecessor']['result']}} for i in request['items']]}},
        capabilities=[],refresh_identity={})
    exposure_raw=read.json_bytes(exposure);api.snapshots[READING]['current-state.json']=exposure_raw
    request['exposed_reading']=once.source_ref('current-state.json',READING,exposure_raw,'exposure')
    update_request(api,args,request)
    args['scan_raw'],args['scan_artifact'],args['run']=scan([raw,other_raw])
    body_files={};rows=[]
    for source in (args,other_args):
        with ZipFile(BytesIO(source['body_raw'])) as z:
            body_files.update({n:z.read(n) for n in z.namelist()})
            rows.extend(identity._json(line) for line in z.read(prep.BODY_ROOT+'manifest.jsonl').splitlines())
    for idx,row in enumerate(rows,1):row['sequence']=idx
    manifest=b''.join(once.raw(row).replace(b'\n',b'')+b'\n' for row in rows)
    summary=identity._json(body_files[prep.BODY_ROOT+'capture-summary.json'])
    summary.update(manifest_sha256=read.sha256(manifest),returned_pdf_reads=len(rows),
                   unique_pdf_objects=len({row['pdf_sha256'] for row in rows}))
    body_files[prep.BODY_ROOT+'manifest.jsonl']=manifest
    body_files[prep.BODY_ROOT+'capture-summary.json']=once.raw(summary)
    args['body_raw'],args['body_artifact']=archive(body_files,args['run'])
    monkeypatch.setattr(once,'now',clock)
    monkeypatch.setattr(once.Retainer,'native',lambda self,*a:api.native(*a))
    calls=[]
    def call(stage,prompt,*_):calls.append(prompt['discovery_observation']['ticker']);return pre(prompt)
    monkeypatch.setattr(once,'model_call',call)
    result=host.consume(**host_arguments(args,api,clock,tmp_path,monkeypatch))
    assert result['status']=='EXPLICIT_READING_CONTINUATIONS_PROCESSED',result
    assert calls==['603986','300750'] and len(result['items'])==2
    launches=[p for p in api.writes if p.endswith('/launch.json')]
    assert len(launches)==2 and all('/continuations/7/' in p for p in launches)
    assert all(api.snapshots[api.work][p]==b for p,b in api.snapshots[WORK].items())


def test_time_only_new_packet_is_not_same_source_recovery(tmp_path,monkeypatch):
    from dataclasses import replace
    from decision_kernel.runtime.disclosure_assessment import serialize_disclosure_assessment_packet
    args,api,clock,raw,_,spec,_=fixture(tmp_path,monkeypatch)
    model=work._packet(raw)
    stamp=read.clock(clock())
    changed=serialize_disclosure_assessment_packet(replace(model,prepared_at=stamp,
        evidence=tuple(replace(e,evidence_artifact=e.evidence_artifact.model_copy(update={'retrieved_at':stamp}))
                       for e in model.evidence))).encode()
    assert work._packet(changed).assessment_input_hash==model.assessment_input_hash
    with pytest.raises(ValueError,match='not reset'):check(args,clock,changed,spec)


@pytest.mark.parametrize('record',['source.json','launch.json','candidate.json'])
def test_another_permission_id_cannot_recover_same_parent_again_without_a_new_predecessor(tmp_path,monkeypatch,record):
    args,api,_,raw,_,_,_=fixture(tmp_path,monkeypatch)
    key=work._packet(raw).assessment_input_hash
    api.snapshots[WORK][work.continuation_prefix(key,8)+record]=b'{}'
    result=prep.prepare_reserved(**args)
    assert result['status']=='NOT_EXECUTED' and api.writes==[]


def test_other_permission_history_arriving_after_input_preparation_blocks_launch(tmp_path,monkeypatch):
    args,api,clock,raw,_,_,_=fixture(tmp_path,monkeypatch)
    prepared=prep.prepare_reserved(**args)
    assert prepared['status']=='INPUT_PREPARED_NOT_EXECUTED'
    key=work._packet(raw).assessment_input_hash
    api.snapshots[api.work][work.continuation_prefix(key,8)+'launch.json']=b'{}'
    monkeypatch.setattr(once,'model_call',lambda *a:pytest.fail('competing parent history cannot spend'))
    result=host.execute_prepared(api=api,prepared=prepared,code_commit=CODE,output=tmp_path/'execute',clock=clock)
    assert result['status']=='NOT_EXECUTED' and not any(p.endswith('/launch.json') for p in api.writes)
