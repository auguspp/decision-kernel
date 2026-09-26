"""Original ZIP reading, immutable blobs, and history failure isolation."""
from copy import deepcopy
import base64
import io
import json
from pathlib import Path
import zipfile

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import smart_money_reading as r
from decision_kernel.runtime import smart_money_sources as s
from decision_kernel.runtime import smart_money_documents as docs
from test_smart_money import captured, NOW, IDENT, example, offline
from test_radar_company_reading import collector, baseline, API


def setup(tmp_path):
    obs,files=captured(tmp_path)
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
        for name,raw in files.items():z.writestr(name,raw)
    raw=stream.getvalue();api=API(archive=raw);col=collector(api,tmp_path);col.now=lambda:NOW
    b,_,_=baseline(col)
    col.previous=None;col.previous_commit=None
    run={'id':IDENT['run_id'],'head_sha':IDENT['code_commit'],'head_branch':'main','path':s.WORKFLOW,
        'repository':{'full_name':m.REPOSITORY},'head_repository':{'full_name':m.REPOSITORY},
        'event':'workflow_dispatch','run_attempt':1,'status':'completed','conclusion':'success',
        'created_at':'2026-09-26T01:19:00+00:00','updated_at':NOW}
    job={'id':44,'name':'capture-smart-money','run_id':run['id'],'head_sha':run['head_sha'],'run_attempt':1,
         'status':'completed','conclusion':'success','steps':[]}
    art={'id':99,'name':f"smart-money-{run['id']}-1",'expired':False,'size_in_bytes':len(raw),
         'digest':'sha256:'+m.sha256(raw),'workflow_run':{'id':run['id'],'head_sha':run['head_sha']}}
    api.responses={r.QUERY:{'total_count':1,'workflow_runs':[run]},f"actions/runs/{run['id']}":run,
        f"actions/runs/{run['id']}/attempts/1/jobs?per_page=100":{'total_count':1,'jobs':[job]},
        f"actions/runs/{run['id']}/artifacts?per_page=100":{'total_count':1,'artifacts':[art]}}
    return col,b,run,job,art


def preserve_as_previous(col,result):
    col.previous=result;col.previous_commit='b'*40
    refs=result['research']['smart_money']['details']
    for raw in col.files.values():
        sha=m.blob_sha(raw)
        col.api.responses['git/blobs/'+sha]={'sha':sha,'encoding':'base64','content':base64.b64encode(raw).decode()}
    col.files={k:v for k,v in col.files.items() if not k.startswith('details/radar/smart-money')}
    return refs


def test_real_zip_rebuild_and_company_actor_reading(tmp_path):
    col,b,run,job,art=setup(tmp_path)
    before=deepcopy(b);result=r.attach(col,b)
    m.validate_read_package(result)
    sm=result['research']['smart_money']
    assert sm['status']=='READY' and sm['pending_delivery_count']==0
    assert result['lanes']==before['lanes'] and b==before
    assert sm['family_coverage']['hot_money']['companies']==1
    assert 'browse.html' in sm['details']['browser']['read_path']
    assert b'full' not in col.files[sm['details']['state']['read_path']]


def test_repeat_publisher_preserves_original_increment(tmp_path):
    col,b,*_=setup(tmp_path);result=r.attach(col,b);refs=preserve_as_previous(col,result)
    old=json.loads(base64.b64decode(col.api.responses['git/blobs/'+refs['overview']['git_blob']]['content']))
    again=r.attach(col,result)
    new=json.loads(col.files[again['research']['smart_money']['details']['overview']['read_path']])
    assert new['increment_counts']==old['increment_counts']
    assert new['first_baseline'] is True


def test_new_failed_source_keeps_actual_prior_data_and_cutoff(tmp_path):
    col,b,run,*_=setup(tmp_path);result=r.attach(col,b);preserve_as_previous(col,result)
    run['id']+=1;run['status']='in_progress';run['conclusion']=None
    col.api.responses[f"actions/runs/{run['id']}"]=run
    result=r.attach(col,result);sm=result['research']['smart_money']
    assert sm['status']=='AWAITING_CURRENT_CAPTURE' and sm['uses_prior_observation']
    assert sm['family_coverage']['holdings']['saved_records']==2
    assert '旧日期'.encode() in col.files[sm['details']['markdown']['read_path']]


def test_missing_previous_blob_preserves_recovery_locator_not_empty_baseline(tmp_path):
    col,b,*_=setup(tmp_path);result=r.attach(col,b);refs=preserve_as_previous(col,result)
    del col.api.responses['git/blobs/'+refs['history']['git_blob']]
    result=r.attach(col,result);sm=result['research']['smart_money']
    assert sm['status']=='HISTORY_RECOVERY_GAP'
    assert sm['prior_retained_entry']['commit']=='b'*40
    assert sm['prior_retained_entry']['entry']['details']==refs
    assert result['lanes']==b['lanes']


@pytest.mark.parametrize('damage',['foreign','rerun','job_head','job_attempt','artifact_digest','wrong_event'])
def test_changed_run_or_archive_cannot_be_read_as_current_source(tmp_path,damage):
    col,b,run,job,art=setup(tmp_path)
    if damage=='foreign':run['head_repository']['full_name']='other/repo'
    elif damage=='rerun':run['run_attempt']=2
    elif damage=='job_head':job['head_sha']='c'*40
    elif damage=='job_attempt':job['run_attempt']=2
    elif damage=='artifact_digest':art['digest']='sha256:'+'0'*64
    else:run['event']='push'
    result=r.attach(col,b)
    assert result['research']['smart_money']['status'].startswith('CURRENT_READING_REJECTED')
    assert result['lanes']==b['lanes']


def test_partial_checkpoint_not_promoted_to_complete_run(tmp_path):
    col,b,run,job,art=setup(tmp_path);job['conclusion']='failure';run['conclusion']='failure'
    result=r.attach(col,b);sm=result['research']['smart_money']
    assert sm['status']=='PARTIAL_FAILED_EXECUTION' and sm['pending_delivery_count']==1
    assert sm['family_coverage']['activity']['saved_records']==1


def test_reported_revision_requires_explicit_metric_unit_broker_and_years(monkeypatch):
    import pypdf
    class Page:
        def extract_text(self):return '测试证券 600000 预计2026-2028年归母净利润为283/297/316亿（前值为352/368/-亿）'
    class Reader:
        is_encrypted=False
        pages=[Page()]
        def __init__(self,*a,**kw):pass
    monkeypatch.setattr(pypdf,'PdfReader',Reader)
    req=s.spec('forecasts','disclosures','2026-06-28','2026-09-26')
    report=s.normalize(example('forecasts'),req,0,1,{'currentYear':2026})[0]
    out=docs.reported_revisions(b'%PDF-test-synthetic',report)
    assert [x['target_year'] for x in out['revisions']]==[2026,2027]
    assert out['revisions'][0]['old_original_report']=='NOT_INDEPENDENTLY_RECOVERED'
    report['actor_name']='另一券商'
    assert not docs.reported_revisions(b'%PDF-test-synthetic',report)['revisions']
