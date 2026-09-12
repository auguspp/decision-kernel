"""Synthetic Human intent fixtures; these are NOT actual Human permission records."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import pytest
from decision_kernel.runtime import disclosure_continuation as cont
from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import incremental_disclosure as work
from decision_kernel.runtime import saved_disclosure_host as host
from decision_kernel.runtime import saved_disclosure_preparation as prep
from decision_kernel.runtime import saved_research_once as once
from test_incremental_disclosure import external_pair
from test_saved_disclosure_preparation import CODE, READING, WORK, AT, packet_pdf, setup
from test_saved_disclosure_host import setup_host
from test_saved_research_once import pre

OLD='d'*40
PERMISSION='e'*40


def configure(api, child_raw, *, kind='CANDIDATE', old_packet=None):
    old_raw=old_packet if old_packet is not None else packet_pdf('Prior public source body.')[0]
    old_key=work._packet(old_raw).assessment_input_hash
    prefix=work.request_path(old_key).removesuffix('packet.json')
    input_raw,result_raw=external_pair(old_raw,complete=True)
    prior_question=read.json.loads(input_raw)['research_question']
    if kind=='PRE_EXECUTION_FAILURE':
        result_raw=once.raw({'schema_version':1,'record_kind':'PRE_EXECUTION_FAILURE_NOT_VALIDATOR_RESULT',
            'research_execution':'NOT_EXECUTED','funnel_status':'NOT_REACHED','formal_research_budget_used':0,
            'assessment_input_hash':old_key,'packet_blob':read.blob_sha(old_raw),
            'packet_sha256':read.sha256(old_raw),'status':'SOURCE_PREFLIGHT_INCOMPLETE',**read.AUTHORITY})
    name='candidate.json' if kind=='CANDIDATE' else 'failure.json'
    api.snapshots[OLD]={prefix+'packet.json':old_raw,prefix+name:result_raw}
    if kind=='CANDIDATE':api.snapshots[OLD][prefix+'input.json']=input_raw
    api.snapshots[api.work].update(api.snapshots[OLD])
    prior={'kind':kind,
        'packet':once.source_ref(prefix+'packet.json',OLD,old_raw,'PREVIOUS_PACKET'),
        'input':once.source_ref(prefix+'input.json',OLD,input_raw,'PREVIOUS_INPUT') if kind=='CANDIDATE' else None,
        'result':once.source_ref(prefix+name,OLD,result_raw,'PREVIOUS_RESULT')}
    role='candidate' if kind=='CANDIDATE' else 'failure'
    exposure=read.assemble(code_commit=CODE,checked_at=AT,check_started_at=AT,lanes={},
        research={'handoffs':{'active':[]},'candidate_work':{'status':'READ_OK','items':[
            {'sources':{role:prior['result']}}]}},capabilities=[],refresh_identity={})
    api.snapshots[READING]={'current-state.json':read.json_bytes(exposure)}
    verbatim='SYNTHETIC HUMAN CONTINUE — never a real response'
    body='Synthetic canonical Issue response: ' + verbatim
    permission={'response_kind':'EXPLICIT_RESEARCH_CONTINUE','verbatim':verbatim,
                'ticker':'600036','issue_number':297,'comment_id':101,'record_body':body,'body_sha256':read.sha256(body.encode())}
    comment={'id':101,'issue_url':'https://api.github.com/repos/'+read.REPOSITORY+'/issues/297',
             'body':body,'created_at':AT,'updated_at':AT,'user':{'login':'synthetic-not-authority'}}
    original_call=api._call
    def call(method,endpoint):
        if endpoint=='issues/comments/101':return SimpleNamespace(json=lambda:deepcopy(comment))
        return original_call(method,endpoint)
    api._call=call
    api.permission_comment=comment
    req={'schema_version':1,'mode':cont.MODE,'enabled':True,'predecessor':prior,
        'permission':permission,
        'exposed_reading':once.source_ref('current-state.json',READING,read.json_bytes(exposure),'EXPOSURE'),
        'new_assessment_input_hash':work._packet(child_raw).assessment_input_hash,
        'prior_question':prior_question,'follow_up_question':'Synthetic focused continuation of the prior question',
        'new_evidence_reason':'Synthetic new primary body addresses the prior missing distinction'}
    for ref in (CODE,OLD,READING):
        api.commits[ref]={'sha':ref,'committer':{'date':AT}}
    def store():
        raw=once.raw(req);api.snapshots[CODE][cont.REQUEST_PATH]=raw
        return once.source_ref(cont.REQUEST_PATH,CODE,raw,cont.REQUEST_PURPOSE)
    return req,permission,store,old_raw


@pytest.mark.parametrize('kind',['CANDIDATE','PRE_EXECUTION_FAILURE'])
def test_original_predecessor_and_new_body_bound_without_exposing_human_text(tmp_path,monkeypatch,kind):
    args,api,clock,child,_=setup(tmp_path,monkeypatch,text='New public source body.')
    req,permission,store,old=configure(api,child,kind=kind)
    result=cont.check(api=api,code_commit=CODE,request_source=store(),new_packet_raw=child,checked_at=clock())
    assert result['question']==req['follow_up_question']
    assert permission['verbatim'] not in once.raw(result['public_context']).decode()
    assert result['permission_receipt']['comment_id']==101
    assert cont.REQUEST_PURPOSE in [s['purpose'] for s in result['source_refs']]
    assert result['public_context']['new_body_hashes']==[work._packet(child).evidence[0].pdf_sha256]
    assert api.writes==[]


@pytest.mark.parametrize('defect',['disabled','wrong-target','wrong-main','wrong-path','engineering-reply',
    'wrong-company','wrong-seen-result','wrong-exposure','old-problem','no-reason','future-commit','bad-predecessor-hash'])
def test_invalid_permission_or_identity_cannot_authorize_work(tmp_path,monkeypatch,defect):
    args,api,clock,child,_=setup(tmp_path,monkeypatch,text='New body')
    req,permission,store,_=configure(api,child)
    if defect=='disabled':req['enabled']=False
    elif defect=='wrong-target':req['new_assessment_input_hash']='f'*64
    elif defect=='engineering-reply':permission['response_kind']='ENGINEERING_CONTINUE'
    elif defect=='wrong-company':permission['ticker']='603986'
    elif defect=='wrong-seen-result':req['predecessor']['result']['ref']='f'*40
    elif defect=='wrong-exposure':req['exposed_reading']['sha256']='f'*64
    elif defect=='old-problem':req['prior_question']='Another question'
    elif defect=='no-reason':req['new_evidence_reason']=''
    elif defect=='future-commit':api.commits[READING]['committer']['date']='2027-01-01T00:00:00Z'
    elif defect=='bad-predecessor-hash':req['predecessor']['result']['sha256']='f'*64
    spec=store()
    if defect=='wrong-main':spec['ref']=OLD
    if defect=='wrong-path':spec['path']='from-source.json'
    before=deepcopy(api.snapshots)
    with pytest.raises((ValueError,KeyError)):
        cont.check(api=api,code_commit=CODE,request_source=spec,new_packet_raw=child,checked_at=clock())
    assert api.snapshots==before and api.writes==[]


def test_same_body_new_packet_context_is_not_new_discriminating_evidence(tmp_path,monkeypatch):
    args,api,clock,_,_=setup(tmp_path,monkeypatch,text='Prior public source body.')
    child,_=packet_pdf('Prior public source body.',thesis='Changed context does not change primary Evidence')
    req,_,store,old=configure(api,child)
    assert work._packet(child).assessment_input_hash!=work._packet(old).assessment_input_hash
    assert work._packet(child).evidence[0].pdf_sha256==work._packet(old).evidence[0].pdf_sha256
    with pytest.raises(ValueError,match='no new discriminating'):
        cont.check(api=api,code_commit=CODE,request_source=store(),new_packet_raw=child,checked_at=clock())


def test_prep_and_executor_reuse_genuine_intent_binding_no_second_loop(tmp_path,monkeypatch):
    child,pdf=packet_pdf('New body discriminates the prior unknown.')
    args,api,calls=setup_host(tmp_path,monkeypatch,[(child,pdf)])
    req,permission,store,old=configure(api,child)
    before=deepcopy(api.snapshots[OLD]);source=store();seen=[]
    def model(stage,prompt,*_):
        seen.append(prompt)
        assert permission['verbatim'] not in once.raw(prompt).decode()
        assert prompt['question']==req['follow_up_question']
        return pre(prompt)
    monkeypatch.setattr(once,'model_call',model)
    result=host.consume(**dict(args,continuation_request_source=source))
    assert result['status']=='EXPLICIT_CONTINUATION_CANDIDATE_RETAINED',result
    assert len(seen)==1 and api.snapshots[OLD]==before
    key=work._packet(child).assessment_input_hash
    frozen=read.json.loads(api.file(work.request_path(key).replace('packet.json','input.json'),api.work))
    assert frozen['prompt_version']=='saved-disclosure-continuation-v1'
    assert frozen['research_question']==req['follow_up_question']
    old_count=len(api.writes)
    repeat=host.consume(**dict(args,output=tmp_path/'repeat',continuation_request_source=source))
    assert repeat['status']=='BATCH_INCOMPLETE' and len(seen)==1 and len(api.writes)==old_count


def test_ordinary_host_does_not_use_configured_permission_without_explicit_mode(tmp_path,monkeypatch):
    child,pdf=packet_pdf('A new normal saved question')
    args,api,calls=setup_host(tmp_path,monkeypatch,[(child,pdf)])
    req,_,store,_=configure(api,child);store()
    underlying=api._call
    def checked(method,endpoint):
        assert not endpoint.startswith('issues/comments/'), 'ordinary mode read Human permission'
        return underlying(method,endpoint)
    monkeypatch.setattr(api,'_call',checked)
    seen=[]
    def model(stage,prompt,*_):
        seen.append(prompt['question']);return pre(prompt)
    monkeypatch.setattr(once,'model_call',model)
    result=host.consume(**args)
    assert result['status']=='NO_UNRESERVED_PACKET_IN_SAVED_SCAN',result
    assert seen==[prep.QUESTION] and req['follow_up_question'] not in seen


@pytest.mark.parametrize('damage',['body-edited','wrong-issue','future-comment','before-exposure','no-quote'])
def test_actual_issue_record_is_checked_not_just_a_saved_permission_label(tmp_path,monkeypatch,damage):
    args,api,clock,child,_=setup(tmp_path,monkeypatch,text='New discriminating body')
    req,permission,store,_=configure(api,child)
    spec=store()
    if damage=='body-edited':api.permission_comment['body']+=' changed after review'
    elif damage=='wrong-issue':api.permission_comment['issue_url']=api.permission_comment['issue_url'].replace('/297','/999')
    elif damage=='future-comment':api.permission_comment['updated_at']='2027-01-01T00:00:00Z'
    elif damage=='before-exposure':api.permission_comment['created_at']='2026-09-01T00:00:00Z'
    elif damage=='no-quote':
        api.permission_comment['body']='Different actual body'
        req['permission']['body_sha256']=read.sha256(api.permission_comment['body'].encode());spec=store()
    with pytest.raises(ValueError):
        cont.check(api=api,code_commit=CODE,request_source=spec,new_packet_raw=child,checked_at=clock())
    assert api.writes==[]


def test_git_author_username_cannot_turn_engineering_approval_into_permission(tmp_path,monkeypatch):
    args,api,clock,child,_=setup(tmp_path,monkeypatch,text='New discriminating body')
    req,_,store,_=configure(api,child)
    api.permission_comment['user']['login']='auguspp'
    req['permission']['response_kind']='ENGINEERING_CONTINUE'
    with pytest.raises(ValueError,match='not research continuation'):
        cont.check(api=api,code_commit=CODE,request_source=store(),new_packet_raw=child,checked_at=clock())


def test_same_required_pdf_can_be_newly_readable_after_an_explicit_source_failure(tmp_path,monkeypatch):
    from decision_kernel.adapters.pdf_text import PagedPdfText, PdfPageText, PdfTextStatus, extract_pdf_text
    from decision_kernel.runtime.disclosure_assessment import _page_text_sha256
    def old_extraction(payload):
        parsed=extract_pdf_text(payload); pages=tuple(PdfPageText(page_number=p.page_number,text='') for p in parsed.pages)
        return PagedPdfText(pdf_sha256=parsed.pdf_sha256,text_sha256=_page_text_sha256(pages),
            page_count=len(pages),extracted_char_count=0,status=PdfTextStatus.NO_TEXT,pages=pages)
    body='Previously unavailable representation of the required original body'
    old,_=packet_pdf(body,extractor=old_extraction)
    args,api,clock,child,_=setup(tmp_path,monkeypatch,text=body)
    req,_,store,_=configure(api,child,kind='PRE_EXECUTION_FAILURE',old_packet=old)
    assert work._packet(old).evidence[0].pdf_sha256==work._packet(child).evidence[0].pdf_sha256
    result=cont.check(api=api,code_commit=CODE,request_source=store(),new_packet_raw=child,checked_at=clock())
    assert len(result['public_context']['new_body_hashes'])==1
    assert api.writes==[]
