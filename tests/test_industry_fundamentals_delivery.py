"""Industrial delivery regressions: no-op publication is not new source evidence."""
from copy import deepcopy
import pytest
from decision_kernel.runtime import industry_fundamentals as source
from decision_kernel.runtime import industry_fundamentals_reading as reader


def observation(value='50.6',period='2026-08'):
    return {'coverage':{'available_families':1},'series':[
        source.series('nbs-pmi','制造业/新订单','指数点','MONTHLY_DIFFUSION_INDEX',
                      [{'period':period,'value':value}])]}


def test_same_capture_republication_preserves_increment():
    current={'capture_hash':'a'*64,'observation':observation()}
    first=reader.select_display(current)
    assert first['comparison']['changes'][0]['kind']=='BASELINE_FIRST_SEEN'
    again=reader.select_display(deepcopy(current),first)
    assert again['comparison']==first['comparison']
    assert again['comparison_status']=='SAME_CAPTURE_INCREMENT_PRESERVED'


def test_new_capture_revises_unchanged_or_new_statistical_period():
    first=reader.select_display({'capture_hash':'a'*64,'observation':observation()})
    unchanged=reader.select_display({'capture_hash':'b'*64,'observation':observation()},first)
    assert unchanged['comparison']['unchanged_count']==1
    changed=reader.select_display({'capture_hash':'b'*64,'observation':observation('51')},first)
    assert changed['comparison']['changes'][0]['kind']=='SAME_PERIOD_REVISION'
    next_=reader.select_display({'capture_hash':'b'*64,'observation':observation('51','2026-09')},first)
    assert next_['comparison']['changes'][0]['kind']=='NEW_STATISTICAL_PERIOD'


@pytest.mark.parametrize('unavailable',[None,{'coverage':{'available_families':0},'series':[]}])
def test_unavailable_batch_keeps_prior_explicitly(unavailable):
    first=reader.select_display({'capture_hash':'a'*64,'observation':observation()})
    later=reader.select_display({'capture_hash':'b'*64,'observation':unavailable},first)
    assert later['observation']==first['observation'] and later['observation_is_prior']
    assert later['last_capture_hash']=='a'*64
    assert later['comparison']==first['comparison']


def test_independent_job_can_survive_failed_commodity_sibling(monkeypatch):
    run={'id':99,'path':source.WORKFLOW,'head_branch':'main','head_sha':'a'*40,
         'repository':{'full_name':'auguspp/decision-kernel'},
         'head_repository':{'full_name':'auguspp/decision-kernel'},
         'run_attempt':1,'status':'completed','conclusion':'failure',
         'event':'workflow_dispatch','created_at':'2026-09-25T10:00:00Z','updated_at':'2026-09-25T10:01:00Z'}
    job={'id':101,'run_id':99,'head_sha':'a'*40,'run_attempt':1,'name':'industrial-fundamentals',
         'status':'completed','conclusion':'success'}
    class API:
        def get(self,path):
            if path==reader.QUERY:return {'total_count':1,'workflow_runs':[run]}
            if path=='actions/runs/99':return run
            if path=='actions/runs/99/attempts/1/jobs?per_page=100':return {'total_count':1,'jobs':[job]}
            raise AssertionError(path)
    class Collector:
        api=API()
        now=lambda self:'2026-09-25T11:00:00Z'
        artifacts=lambda self,run:[{'name':'industry-fundamentals-99-1','expired':False}]
        archive=lambda self,artifact,run:({'capture.json':b'{"identity":{"trigger_run_id":null}}'}, {'artifact_id':77})
    monkeypatch.setattr(reader,'_reserve',lambda *a,**k:None)
    calls=[]
    def replay(files,identity,cutoff):
        calls.append(identity)
        return {'status':'PARTIAL','coverage':{'available_families':1}}, {'capture_hash':'c'*64}
    monkeypatch.setattr(source,'replay',replay)
    result=reader.native(Collector())
    assert result['status']=='PARTIAL' and result['job']['workflow_conclusion']=='failure'
    assert len(calls)==1 and result['source_calls']==0
    job['head_sha']='b'*40
    with pytest.raises(ValueError,match='job identity'):reader.native(Collector())
