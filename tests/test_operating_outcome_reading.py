"""Native root/reserve integration with synthetic Git I/O, no live sources."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import operating_outcome_reading as r
from decision_kernel.runtime import operating_outcomes as o

ROOT=Path(__file__).resolve().parents[1]
AT='2026-10-06T05:45:00+00:00'
LIMIT=20*1024*1024


def fixture(indices=(0,), at=AT):
    config=json.loads((ROOT/r.CONFIG).read_bytes())
    config['cases']=[config['cases'][i] for i in indices]
    raw=(json.dumps(config,ensure_ascii=False)+'\n').encode()
    # Use the real navigation input; deriving links from config hid #779's omission.
    nav=(ROOT/'docs/live-decision-book.md').read_bytes()
    def descriptor(path,raw,ref):
        return dict(path=path,ref=ref,read_path='sources/test/'+model.blob_sha(raw)+'/'+path.rsplit('/',1)[-1],
            bytes=len(raw),sha256=model.sha256(raw),git_blob=model.blob_sha(raw),
            read_ref_rule='USE_THE_SAME_PINNED_READING_COMMIT')
    nav_ref=descriptor('docs/live-decision-book.md',nav,'a'*40)
    base=model.assemble(code_commit='a'*40,checked_at=at,check_started_at=at,
        research={'handoffs':{'active':[]},'records':[{'id':'decision-book','use':'NAVIGATION_ONLY','source':nav_ref},
                                                  {'id':'keep-human-record'}]},
        lanes={'stock':{'gaps':['original source failure']}},capabilities=[],refresh_identity={})
    c=SimpleNamespace(code_commit='a'*40,now=lambda:at,sources={},api=SimpleNamespace(calls=0,max_calls=180),
        files={'current-state.json':model.read_package_bytes(base),'README.md':b'Original reading\n',nav_ref['read_path']:nav})
    values={r.CONFIG:raw,**{v['path']:(ROOT/v['path']).read_bytes() for e in config['cases'] for v in e['sources'].values()}}
    c.reads=[]
    def source(spec):
        c.reads.append((spec['path'],spec.get('ref')));c.api.calls+=1
        raw=values[spec['path']];d=descriptor(spec['path'],raw,spec.get('ref',c.code_commit))
        assert spec.get('git_blob',d['git_blob'])==d['git_blob']
        c.files[d['read_path']]=raw;c.sources[spec['path'],spec.get('ref',c.code_commit)]=(raw,d)
        return raw,d
    c.source=source
    return c,base,values


def test_real_retained_case_reaches_normal_root_without_price_or_case_changes():
    c,base,_=fixture();original=deepcopy(base)
    result=r.attach(c,base,retained_limit=LIMIT)
    model.validate_read_package(result)
    report=o.loads(c.files[r.PATH]);item=report['items'][0]
    assert report['compared_events']==1 and report['selected_events']==1
    assert item['comparable_metrics']==4 and item['brier_score'] is None
    assert result['lanes']==base['lanes'] and result['research']['records']==base['research']['records']
    assert base==original and c.sources=={} and len(c.reads)==4
    assert report['report_hash']==canonical_hash({k:v for k,v in report.items() if k!='report_hash'})
    assert 'D2：已保存经营结果对账' in c.files['README.md'].decode()
    for ref in item['retained_files'].values():
        assert model.sha256(c.files[ref['read_path']])==ref['sha256']


def test_missing_source_is_a_visible_gap_not_old_success_or_zero_error():
    c,base,values=fixture();before=dict(c.files)
    del values[next(k for k in values if k.endswith('source-notes.json'))]
    result=r.attach(c,base,retained_limit=LIMIT)
    item=o.loads(c.files[r.PATH])['items'][0]
    assert item['status']=='RETAINED_OUTCOME_UNAVAILABLE_NOT_ECONOMIC_FAILURE'
    assert item['difference'] is None and item['phase']=='SELECTED_RETAINED_SOURCES'
    assert result['lanes']==base['lanes'] and c.sources=={}
    assert all(c.files[k]==v for k,v in before.items() if k not in ('current-state.json','README.md'))


def test_wrong_navigation_cannot_fetch_an_unregistered_review():
    c,base,_=fixture();desc=base['research']['records'][0]['source']
    c.files[desc['read_path']]=b'wrong navigation'
    result=r.attach(c,base,retained_limit=LIMIT)
    assert o.loads(c.files[r.PATH])['items'][0]['phase']=='NAVIGATION'
    assert len(c.reads)==1 and result['lanes']==base['lanes']


def test_exhausted_original_api_budget_does_not_read_or_modify_baseline():
    c,base,_=fixture();c.api.calls=180;before=dict(c.files)
    assert r.attach(c,base,retained_limit=LIMIT)==base
    assert c.files==before and c.reads==[] and c.api.calls==180


def test_no_capacity_rolls_back_only_new_attachment_and_keeps_reading():
    c,base,_=fixture();before=dict(c.files)
    assert r.attach(c,base,retained_limit=1)==base
    assert c.files==before and c.sources=={}


def test_optional_cache_does_not_expand_or_overwrite_original_source_registry():
    c,base,_=fixture();c.sources={('old/'+str(i),'b'*40):(b'old',{}) for i in range(60)}
    old=dict(c.sources);result=r.attach(c,base,retained_limit=LIMIT)
    assert result['research'][r.KEY]['read_path']==r.PATH and c.sources==old


def test_repeated_reading_preserves_original_review_clock_not_new_event():
    c,base,_=fixture();r.attach(c,base,retained_limit=LIMIT);first=o.loads(c.files[r.PATH])
    c2,base2,_=fixture();c2.now=lambda:'2026-10-06T06:00:00Z'
    r.attach(c2,base2,retained_limit=LIMIT);second=o.loads(c2.files[r.PATH])
    assert first['items'][0]['retained_review_at']==second['items'][0]['retained_review_at']
    assert first['items'][0]['rows']==second['items'][0]['rows']
    assert first['new_attention_events']==second['new_attention_events']==0


def test_normal_entry_calls_outcomes_separately_from_current_price_flag():
    import ast
    code=ast.parse((ROOT/'src/decision_kernel/runtime/current_state_delivery_with_odds_watch.py').read_text())
    collect=next(n for n in ast.walk(code) if isinstance(n,ast.FunctionDef) and n.name=='collect')
    branches=[n for n in collect.body if isinstance(n,ast.If) and 'attach_outcomes' in ast.unparse(n)]
    assert len(branches)==1 and 'include_reviewed_questions' in ast.unparse(branches[0].test)
    assert 'INCLUDE_CURRENT_STOCK_INPUTS' not in ast.unparse(branches[0].test)
