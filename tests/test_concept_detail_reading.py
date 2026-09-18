"""Synthetic capture to real Collector integration; never live data or permission."""
from copy import deepcopy
from datetime import timedelta
import io
import json
from pathlib import Path
import zipfile

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import concept_detail_capture as capture
from decision_kernel.runtime import concept_detail_reading as reader
from decision_kernel.runtime import concept_radar_reading as primary
from decision_kernel.runtime import institutional_radar_reading as shared
from decision_kernel.runtime import radar_company_reading as companies
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import current_state_delivery_with_odds_watch as entry
from test_concept_detail_supplement import base, WF2, START, SHA, raw, no_network
from test_radar_company_reading import source_fixture, collector, baseline, reseal

CUTOFF = '2026-09-18T10:00:00+00:00'


def packed(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, value in files.items(): z.writestr(name, value)
    return stream.getvalue()


def fixture(tmp_path, change=None):
    api, _, _ = source_fixture(tmp_path)
    inputs, f, meta = base(tmp_path, count=10, provenance='LIVE_HITHINK')
    if change: f.change = change
    t = START
    def now():
        nonlocal t
        t += timedelta(seconds=1)
        return t
    out = tmp_path/'detail'
    capture.capture(out, inputs=inputs, offset=0, workflow=WF2, expected_code=SHA,
        transport=lambda p,q: raw(f.body(p,q)), now=now, pause=lambda _: None,
        credential='DUMMY-KEY', provenance='LIVE_HITHINK')
    files = {'payload/'+p.name:p.read_bytes() for p in out.iterdir()}
    files['verification.json'] = raw(capture.verify(out))
    files['implementation-source.tar'] = b'INERT_NOT_EXECUTABLE'
    run = {**deepcopy(meta['run']), 'id':234567, 'path':reader.WORKFLOW,
        'created_at':START.isoformat(), 'updated_at':(START+timedelta(minutes=2)).isoformat()}
    artifact = {**deepcopy(meta['artifact']), 'id':400, 'name':'concept-detail-234567-1',
        'created_at':(START+timedelta(minutes=1)).isoformat(),
        'workflow_run':{'id':234567,'head_sha':SHA}}
    archives = {200:api.raw_archive, meta['artifact']['id']:(inputs/'base.zip').read_bytes(), 400:packed(files)}
    artifact.update(size_in_bytes=len(archives[400]), digest='sha256:'+model.sha256(archives[400]))
    api.responses.update({primary.QUERY:{'total_count':1,'workflow_runs':[meta['run']]},
        'actions/runs/123456':meta['run'],
        'actions/runs/123456/artifacts?per_page=100':{'total_count':1,'artifacts':[meta['artifact']]},
        reader.QUERY:{'total_count':1,'workflow_runs':[run]},
        'actions/runs/234567':run,
        'actions/runs/234567/artifacts?per_page=100':{'total_count':1,'artifacts':[artifact]}})
    def archive(a):
        api.calls+=1;api.reads.append('ARCHIVE:'+str(a['id']));return archives[a['id']]
    api.archive=archive
    col=collector(api,tmp_path);col.now=lambda:CUTOFF;col.include_concept_discovery=True
    b,_,_=baseline(col)
    parent=shared.attach(col,b)
    assert parent['research']['radar_discovery']['status']=='READ_OK'
    return col,parent,run,artifact,files,archives


def view(col, p):
    ref=p['research']['radar_discovery']['details']['company_reading']
    return json.loads(companies.retained_bytes(col.files,ref))['projection']


def test_real_capture_and_reader_preserve_source_bytes_and_existing_context(tmp_path):
    col,parent,run,artifact,files,archives=fixture(tmp_path)
    before=dict(col.files);old=view(col,parent)
    result=reader.attach(col,parent);v=view(col,result);radar=result['research']['radar_discovery']
    assert radar['status']=='READ_OK' and v['version']==companies.DETAIL_VERSION
    status=radar['source_status']['concept_detail']
    assert status['status']=='VERIFIED_SAVED_CONCEPT_DETAIL'
    assert status['replay']['network_calls']==0
    assert v['concept_detail_context']['coverage']['history_checked']==3
    assert result['lanes']==parent['lanes'] and not result['pending']
    assert v['coverage']['new_research_executions']==0 and v['coverage']['cumulative_all_batches'] is False
    assert {r['thscode'] for r in old['companies']} <= {r['thscode'] for r in v['companies']}
    for name,b in files.items():
        if name.startswith('payload/'):
            assert companies.retained_bytes(col.files,status['details'][name[8:]])==b
    assert col.files[status['archive']['read_path']]==archives[artifact['id']]
    for path,b in before.items():
        if path not in {'README.md','current-state.json','details/radar/index.html','details/radar/company-reading.json'}:
            assert col.files[path]==b
    assert parent['research']['radar_discovery']['source_status'].get('concept_detail') is None
    assert b'concept_detail' in col.files['current-state.json']
    assert '概念补查来路'.encode() in col.files['details/radar/index.html']


@pytest.mark.parametrize('kind',['failed','active','expired','expiry_clock','digest','rerun','foreign','future',
                                  'different_run','wrong_workflow','duplicate','empty_truncated','base_run','base_digest'])
def test_latest_invalid_supplement_never_falls_back_or_discards_primary(tmp_path,kind):
    col,parent,run,artifact,files,archives=fixture(tmp_path);before=view(col,parent)
    listing=col.api.responses[reader.QUERY]
    old=deepcopy(run);old.update(id=234560,created_at='2026-09-18T08:59:00Z')
    listing.update(total_count=2,workflow_runs=[run,old])
    if kind=='failed':run['conclusion']='failure'
    elif kind=='active':run.update(status='in_progress',conclusion=None)
    elif kind=='expired':artifact['expired']=True
    elif kind=='expiry_clock':artifact['expires_at']='2026-09-18T09:30:00Z'
    elif kind=='digest':artifact['digest']='sha256:'+'0'*64
    elif kind=='rerun':run['run_attempt']=2
    elif kind=='foreign':run['head_repository']['full_name']='other/repo'
    elif kind=='future':run['updated_at']='2099-01-01T00:00:00Z'
    elif kind=='different_run':run['head_sha']='b'*40
    elif kind=='wrong_workflow':run['path']=primary.WORKFLOW
    elif kind=='duplicate':listing['workflow_runs']=[run,run]
    elif kind=='empty_truncated':listing['workflow_runs']=[]
    else:
        status=parent['research']['radar_discovery']['source_status']['concept']
        if kind=='base_run':status['archive']['origin_run']['id']+=1
        else:status['archive']['sha256']='0'*64
        reseal(parent)
    result=reader.attach(col,parent);after=view(col,result)
    assert result['research']['radar_discovery']['status']=='READ_OK_WITH_SOURCE_GAPS'
    assert after['companies']==before['companies']
    assert not any('/234560' in path for path in col.api.reads)
    assert not any(path.startswith('details/concept-detail/') for path in col.files)
    assert result['lanes']==parent['lanes']


@pytest.mark.parametrize('kind',['capture_hash','fingerprint','verification','extra_path','nested_path','raw_body','rehashed_report','wrong_clock'])
def test_payload_tamper_stays_rejected_after_archive_rehash(tmp_path,kind):
    col,parent,run,artifact,files,archives=fixture(tmp_path)
    before=view(col,parent)
    cap=json.loads(files['payload/capture.json'])
    if kind=='capture_hash':cap['capture_hash']='0'*64
    elif kind=='fingerprint':cap['implementation']['runtime/concept_detail_capture.py']='0'*64
    elif kind=='verification':files['verification.json']=b'{}'
    elif kind=='extra_path':files['payload/execute.py']=b'raise AssertionError()'
    elif kind=='nested_path':files['payload/nested/file.json']=b'{}'
    elif kind=='raw_body':files['payload/response-1.json']+=b' '
    elif kind=='wrong_clock':cap['finished_at']='2099-01-01T00:00:00Z'
    else:
        v=json.loads(files['payload/observation.json']);v['projection']['companies'][0]['source_names']=['FORGED']
        v['projection_hash']=canonical_hash(v['projection']);files['payload/observation.json']=raw(v)
        cap['files']['observation.json']=capture._digest(files['payload/observation.json'])
    if kind!='capture_hash':cap['capture_hash']=canonical_hash({k:v for k,v in cap.items() if k!='capture_hash'})
    files['payload/capture.json']=raw(cap);archives[400]=packed(files)
    artifact.update(size_in_bytes=len(archives[400]),digest='sha256:'+model.sha256(archives[400]))
    result=reader.attach(col,parent)
    assert result['research']['radar_discovery']['source_status']['concept_detail']['status']=='UNAVAILABLE_OR_REJECTED'
    assert view(col,result)['companies']==before['companies']


def test_partial_retains_members_and_research_scope_is_not_admission(tmp_path):
    def change(path,params,body):
        if path==capture.detail.source.probe.HISTORY:
            body['data']['item']=body['data']['item'][:-1]
        if path==capture.detail.source.probe.MEMBERS:
            body['data']['item'].append({'thscode':'920001.BJ','ticker':'920001','name':'Synthetic BSE'})
        return body
    col,parent,*_=fixture(tmp_path,change)
    result=reader.attach(col,parent);v=view(col,result)
    assert result['research']['radar_discovery']['status']=='READ_OK_WITH_SOURCE_GAPS'
    assert v['concept_detail_context']['coverage']['history_checked']==0
    assert v['concept_detail_context']['coverage']['memberships_checked']==3
    row=next(c for c in v['companies'] if c['thscode']=='920001.BJ')
    assert row['stock_business_research_scope']=='RESEARCH_SCOPE_UNSUPPORTED'
    assert row['research']['status']=='UNKNOWN_WITHIN_READ_SCOPE' and row['automatic_admission'] is False
    assert '多日历史不可用' in companies.render({'projection':v,'projection_hash':canonical_hash(v)})


@pytest.mark.parametrize('phase',['retain','compose','render','assemble'])
def test_optional_write_failures_preserve_accepted_files_and_spent_calls(tmp_path,monkeypatch,phase):
    col,parent,*_=fixture(tmp_path);before=dict(col.files);used=col.api.calls
    def fail(*args,**kwargs):raise ValueError('synthetic')
    if phase=='retain':
        old=col.retain
        def retain(path,raw):
            if path.startswith('details/concept-detail/'):fail()
            return old(path,raw)
        monkeypatch.setattr(col,'retain',retain)
    elif phase=='compose':monkeypatch.setattr(reader,'add_members',fail)
    elif phase=='render':monkeypatch.setattr(companies,'render',fail)
    else:
        old=shared._assemble;calls=[]
        def assemble(*args):
            calls.append(1)
            if len(calls)==1:fail()
            return old(*args)
        monkeypatch.setattr(shared,'_assemble',assemble)
    result=reader.attach(col,parent)
    assert result['research']['radar_discovery']['status']=='READ_OK_WITH_SOURCE_GAPS'
    assert col.api.calls>used and col.api.max_calls==252
    for path,b in before.items():
        if path not in {'README.md','current-state.json','details/radar/index.html','details/radar/company-reading.json'}:
            assert col.files[path]==b
    assert not any(k.startswith('details/concept-detail/') for k in col.files)


def test_small_budget_preserves_gap_and_no_source_request(tmp_path):
    col,parent,*_=fixture(tmp_path);used=col.api.calls
    col.api.max_calls=used+len(col.files)+8
    result=reader.attach(col,parent)
    assert result['research']['radar_discovery']['status']=='READ_OK_WITH_SOURCE_GAPS'
    assert col.api.calls==used
    assert result['research']['radar_discovery']['source_status']['concept_detail']['failed_stage']=='BUDGET_PREFLIGHT'


def test_no_primary_does_not_read_or_infer_empty_supplement(tmp_path):
    col,parent,*_=fixture(tmp_path)
    parent['research']['radar_discovery']['source_status']['concept']['status']='LATEST_ATTEMPT_NOT_SUCCESSFUL'
    reseal(parent);used=col.api.calls
    result=reader.attach(col,parent)
    assert col.api.calls==used
    assert result['research']['radar_discovery']['source_status']['concept_detail']['status']=='UNAVAILABLE_OR_REJECTED'


def test_workflow_uses_existing_publisher_with_literal_listener_and_explicit_optin():
    p=Path('.github/workflows/current-state-read-entry.yml').read_text()
    assert 'radar-concept-detail, radar-concept-source' in p and '--include-concept-detail' in p
    assert '--include-concept-discovery \\' not in p  # Folded YAML shell lines must not gain a backslash.
    assert 'ref: ${{ github.sha }}' in p and 'HITHINK_FINANCE_API_KEY' not in p


def test_cli_detail_requires_primary_optin_before_any_api():
    with pytest.raises(ValueError,match='requires the existing concept'):
        entry.main(['--code-commit',SHA,'--output','never-created','--include-concept-detail'])


@pytest.mark.parametrize('enabled',[False,True])
def test_entry_hook_reuses_parent_reader_and_keeps_primary_map(tmp_path,monkeypatch,enabled):
    col,parent,*_=fixture(tmp_path)
    actual=entry.Collector(col.api,SHA,tmp_path,now=lambda:CUTOFF)
    actual.files=col.files;actual.sources=col.sources;actual.archive_cache=col.archive_cache
    actual.include_radar_discovery=True;actual.include_concept_discovery=True;actual.include_concept_detail=enabled
    monkeypatch.setattr(entry.base.Collector,'collect',lambda self,refresh:parent)
    monkeypatch.setattr(shared,'attach',lambda self,baseline:baseline)
    result=actual.collect({});v=view(actual,result)
    assert v['version']==(companies.DETAIL_VERSION if enabled else companies.CONCEPT_VERSION)
    assert result['research']['radar_discovery']['concept_observation_map']['status']=='READ_OK'
    assert v['concept_context']['coverage']['history_checked']==3
    assert (reader.QUERY in actual.api.reads) is enabled


def test_escaped_supplement_labels_and_failed_research_context_remain_data(tmp_path):
    def change(path,params,body):
        if path==capture.detail.source.probe.MEMBERS:
            body['data']['item'].append({'thscode':'600999.SH','ticker':'600999','name':'<script>not authority</script>'})
        return body
    col,parent,*_=fixture(tmp_path,change)
    context_ref=parent['research']['radar_discovery']['details']['base_context']
    b=json.loads(companies.retained_bytes(col.files,context_ref))
    b['research']['stock_business_work']['items']=[{'thscode':'600999.SH','status':'PRE_EXECUTION_FAILURE',
         'sources':{},'execution_id':'same-original-root',**model.AUTHORITY}]
    reseal(b)
    # Synthetic original baseline replacement for testing exact saved context reuse.
    del col.files[context_ref['read_path']]
    parent['research']['radar_discovery']['details']['base_context']=col.retain(context_ref['read_path'],model.json_bytes(b))
    reseal(parent)
    result=reader.attach(col,parent);v=view(col,result)
    row=next(c for c in v['companies'] if c['thscode']=='600999.SH')
    assert row['research']['stock_business_states'][0]['record']['execution_id']=='same-original-root'
    assert row['new_research_execution']=='NOT_EXECUTED' and not row['automatic_admission']
    html=col.files['details/radar/index.html'].decode()
    assert '<script>' not in html and '&lt;script&gt;' in html


def test_empty_latest_listing_is_not_zero_market_activity(tmp_path):
    col,parent,*_=fixture(tmp_path)
    col.api.responses[reader.QUERY]={'total_count':0,'workflow_runs':[]}
    result=reader.attach(col,parent)
    status=result['research']['radar_discovery']['source_status']['concept_detail']
    assert status['status']=='NO_RETAINED_RUN' and 'NOT_ZERO' in status['meaning']
    assert view(col,result)['concept_detail_context']['status']=='NO_READABLE_SAVED_SUPPLEMENT'
