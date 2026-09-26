"""Read-only attachment to the existing publisher; exact source archives retained.

Large plain-JSON snapshots are gzip chunks read by immutable Git blob SHA. A
new source failure retains old observations with their own dates and locators.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import json

from ..identity import canonical_hash
from . import current_state as m, current_state_delivery as delivery
from . import smart_money_sources as s, smart_money_capture as capture, smart_money_view as view
from .institutional_radar_reading import _reserve, ERRORS

PREFIX='details/radar/smart-money/'
QUERY='actions/workflows/radar-smart-money.yml/runs?branch=main&per_page=20'


def read_bound(c,ref,commit):
    m.check(m.SHA.fullmatch(commit) is not None,'smart-money previous commit required')
    m.safe_path(ref['read_path'])
    value=c.api.get('git/blobs/'+ref['git_blob'])
    m.check(value['sha']==ref['git_blob'] and value['encoding']=='base64','smart-money blob identity')
    data=base64.b64decode(value['content'])
    m.check(len(data)==ref['bytes'] and m.sha256(data)==ref['sha256'] and m.blob_sha(data)==ref['git_blob'],
            'smart-money previous bytes differ')
    return data


def previous(c):
    item=(c.previous or {}).get('research',{}).get('smart_money',{})
    prior_commit=c.previous_commit
    if item.get('prior_retained_entry'):
        prior_commit=item['prior_retained_entry']['commit'];item=item['prior_retained_entry']['entry']
    if not item.get('details'):return None,'NO_PREVIOUS_CAPTURE'
    try:
        refs=item['details'];_reserve(c,calls=4,files=0)
        meta=json.loads(read_bound(c,refs['history'],prior_commit))
        overview=json.loads(read_bound(c,refs['overview'],prior_commit))
        state=json.loads(read_bound(c,refs['state'],prior_commit))
        _reserve(c,calls=len(meta['chunks']),files=0)
        blobs={r['name']:read_bound(c,r['reference'],prior_commit) for r in meta['chunks']}
        hist=view.decode_chunks(meta,blobs)
        origins=overview['origins']
        for origin in origins.values():
            if origin.get('reading_commit') is None:origin['reading_commit']=prior_commit
        return {'history':hist,'overview':overview,'state':state,'origins':origins},'EXACT_PREVIOUS_'+prior_commit
    except ERRORS as exc:
        return None,'PREVIOUS_UNAVAILABLE_'+type(exc).__name__


def native(c):
    _reserve(c,calls=6,files=2)
    page=c.api.get(QUERY);runs=page['workflow_runs']
    m.check(isinstance(runs,list) and page['total_count']>=len(runs) and (runs or page['total_count']==0),
            'smart-money run query incomplete')
    m.check(len({r['id'] for r in runs})==len(runs),'smart-money duplicate runs')
    if not runs:return {'status':'NOT_RUN','observation':None}
    selected=max(runs,key=lambda r:(m.clock(r['created_at']),r['id']))
    run=c.api.get('actions/runs/'+str(selected['id']))
    m.check(all(run[k]==selected[k] for k in ('id','head_sha','event','run_attempt')),'smart-money run changed')
    identity={'repository':run.get('repository',{}).get('full_name'),'workflow':run['path'],
              'ref':'refs/heads/'+str(run['head_branch']),'event':run['event'],'code_commit':run['head_sha'],
              'run_id':run['id'],'attempt':run['run_attempt']}
    capture.validate_identity(identity)
    m.check(run.get('head_repository',{}).get('full_name')==m.REPOSITORY,'smart-money foreign source')
    m.check(m.clock(run['created_at'])<=m.clock(run['updated_at'])<=m.clock(c.now()),'smart-money run clock')
    status={'latest_attempt':m.concise_run(run),'observation':None}
    if run['status']!='completed':return {**status,'status':'AWAITING_CURRENT_CAPTURE'}
    jobs=c.api.get(f"actions/runs/{run['id']}/attempts/1/jobs?per_page=100")
    m.check(jobs['total_count']==len(jobs['jobs']),'smart-money incomplete jobs')
    matches=[j for j in jobs['jobs'] if j['name']=='capture-smart-money']
    m.check(len(matches)==1,'smart-money capture job identity')
    job=matches[0]
    m.check(job.get('head_sha')==run['head_sha'] and job.get('run_id')==run['id'] and job.get('run_attempt')==1,
            'smart-money job identity')
    artifacts=c.artifacts(run)
    controls=[a for a in artifacts if a['name']==f"smart-money-control-{run['id']}-1"]
    control=None
    if controls:
        m.check(len(controls)==1,'smart-money control duplicate')
        files,origin=c.archive(controls[0],run);m.check(set(files)=={'control.json'},'smart-money control files')
        control=json.loads(files['control.json'])
        m.check(control['run_id']==run['id'] and control['code_commit']==run['head_sha'], 'smart-money control identity')
        status['control']=control;status['control_archive']=origin
    captures=[a for a in artifacts if a['name']==f"smart-money-{run['id']}-1"]
    if not captures:
        return {**status,'status':('NO_NEW_CAPTURE_REQUIRED' if control and control['decision']=='SKIP_ALREADY_DELIVERED'
                                  else 'CAPTURE_NOT_SAVED_NOT_QUIET')}
    m.check(len(captures)==1,'smart-money capture duplicate')
    files,archive=c.archive(captures[0],run)
    manifest=s.decode(files['capture.json'])
    observation=capture.replay(files,identity,cutoff=c.now())
    m.check(m.clock(run['created_at'])<=m.clock(manifest['started_at'])<=m.clock(manifest['finished_at'])
            <=m.clock(run['updated_at']),'smart-money capture clock binding')
    if job['conclusion']!='success':
        observation['status']='PARTIAL_FAILED_EXECUTION'
        observation['unresolved'].append({'family':'execution','partition':str(run['id']),'failure':'CAPTURE_JOB_FAILED'})
    return {**status,'status':observation['status'],'observation':observation,'archive':archive,
            'capture_hash':manifest['capture_hash'],'job_id':job['id'],'job_conclusion':job['conclusion']}


def _attach(c,baseline):
    old,prior_status=previous(c)
    before=dict(c.files),dict(c.archive_cache),dict(c.sources)
    try:current=native(c)
    except ERRORS as exc:
        c.files,c.archive_cache,c.sources=before
        current={'status':'CURRENT_READING_REJECTED_'+type(exc).__name__,'observation':None}
    if old is None and prior_status.startswith('PREVIOUS_UNAVAILABLE_'):
        old_entry=(c.previous or {}).get('research',{}).get('smart_money',{})
        locator=old_entry.get('prior_retained_entry') or {'commit':c.previous_commit,'entry':old_entry}
        research=deepcopy(baseline['research'])
        research['smart_money']={'status':'HISTORY_RECOVERY_GAP','previous_status':prior_status,
            'latest_attempt':current.get('latest_attempt'),'prior_retained_entry':locator,
            'current_capture_retained':current.get('archive'),
            'meaning':'EXACT_OLD_HISTORY_LOCATOR_PRESERVED; NO_FALSE_EMPTY_REBASE',**s.AUTHORITY}
        return assemble(c,baseline,research,{},'\n聪明钱历史读取暂不可用，原件定位仍保留；不把缺口重置成新基线或无活动。\n')
    obs=current.get('observation');origins=deepcopy((old or {}).get('origins',{}))
    if obs:
        hist=view.history(obs,(old or {}).get('history'))
        overview=view.summarize(obs,hist);state=view.state(obs,(old or {}).get('state'))
        origins[obs['capture_hash']]={'reading_commit':None,'archive':current['archive'],
            'run':current['latest_attempt'],'capture_hash':obs['capture_hash'],'cutoff':obs['cutoff']}
    elif old:
        hist=old['history'];overview=deepcopy(old['overview']);state=old['state']
    else:
        research=deepcopy(baseline['research'])
        research['smart_money']={'status':current['status'],'previous_status':prior_status,
            'meaning':'NO_READABLE_SMART_MONEY_OBSERVATION_NOT_ZERO_ACTIVITY',**s.AUTHORITY}
        return assemble(c,baseline,research,{},'\n聪明钱观察尚不可读；不是没有资本行为。\n')
    chunks,meta=view.encode_chunks(hist)
    _reserve(c,files=len(chunks)+5)
    refs={}
    for ref in meta['chunks']:
        ref['reference']=c.retain(PREFIX+ref['name'],chunks[ref['name']])
    age=(m.clock(c.now())-m.clock(overview['cutoff'])).total_seconds()/3600
    reading_freshness='CHECK_AGE_EXCEEDS_36H_RECHECK_SCHEDULE' if age>36 else 'RECENT_CAPTURE_NOT_EACH_SOURCE_FRESHNESS'
    overview.update(reading_freshness=reading_freshness,capture_age_hours=f"{age:.2f}",
        origins=origins,current_reading={'status':current['status'],
        'latest_attempt':current.get('latest_attempt'),'control':current.get('control'),
        'uses_prior_observation':obs is None,'previous_status':prior_status})
    refs['overview']=c.retain(PREFIX+'overview.json',m.json_bytes(overview))
    refs['history']=c.retain(PREFIX+'history.json',m.json_bytes(meta))
    refs['state']=c.retain(PREFIX+'state.json',m.json_bytes(state))
    text=view.render(overview,hist,failure=current['status'] if obs is None and current['status']!='NO_NEW_CAPTURE_REQUIRED' else None)
    refs['markdown']=c.retain('details/radar/smart-money.md',text.encode())
    refs['browser']=c.retain(PREFIX+'browse.html',view.browser(overview,chunks,meta,origins).encode())
    research=deepcopy(baseline['research'])
    research['smart_money']={'status':current['status'],'details':refs,'source_cutoff':overview['cutoff'],
        'target_date':overview['target_date'],'latest_attempt':current.get('latest_attempt'),
        'capture_hash':hist['capture_hash'],'uses_prior_observation':obs is None,
        'pending_delivery_count':len(state['unresolved']),'reading_freshness':reading_freshness,
        'capture_age_hours':f"{age:.2f}",
        'family_coverage':{f:{k:v[k] for k in ('status','saved_records','companies','latest_period')} for f,v in overview['families'].items()},
        'meaning':'PUBLIC_BEHAVIOR_NOT_SMARTNESS_OR_BUY_SELL_SIGNAL',**s.AUTHORITY}
    return assemble(c,baseline,research,{},'\n[聪明钱：游资、北向、具名持股与资本行为](details/radar/smart-money.md)；独立观察与缺口，不是综合荐股分。\n')


def attach(c,baseline):
    """A large/failed optional view must not suppress Sector, Watch or Research."""
    m.validate_read_package(baseline)
    before=dict(c.files),dict(c.archive_cache),dict(c.sources)
    try:
        return _attach(c,baseline)
    except ERRORS as exc:
        c.files,c.archive_cache,c.sources=before
        old_entry=(c.previous or {}).get('research',{}).get('smart_money',{})
        locator=old_entry.get('prior_retained_entry') or (
            {'commit':c.previous_commit,'entry':old_entry} if old_entry.get('details') else None)
        research=deepcopy(baseline['research'])
        research['smart_money']={'status':'OPTIONAL_PUBLICATION_GAP','error_type':type(exc).__name__,
            'prior_retained_entry':locator,'meaning':'OTHER_LANES_PRESERVED; NO_EMPTY_HISTORY_REBASE',**s.AUTHORITY}
        return assemble(c,baseline,research,{},'\n聪明钱本次交付有缺口，其他阅读保留；旧历史定位未删除，不代表无资本活动。\n')


def assemble(c,baseline,research,files,note):
    # Existing optional readers append Markdown while advancing canonical JSON.
    # The README prefix therefore legitimately has an earlier check timestamp.
    # Bind to the exact in-memory JSON, not a newly rendered Markdown prefix.
    m.check(json.loads(c.files['current-state.json']) == baseline,
            'smart-money canonical composition binding')
    payload=m.assemble(code_commit=c.code_commit,checked_at=c.now(),check_started_at=baseline['checks']['started_at'],
        lanes=baseline['lanes'],research=research,capabilities=baseline['capability_gaps'],refresh_identity=baseline['refresh'])
    replacements={**files,'current-state.json':m.read_package_bytes(payload),
                  'README.md':c.files['README.md']+note.encode()}
    m.check(sum(len(v) for k,v in c.files.items() if k not in replacements)+sum(map(len,replacements.values()))
            <=delivery.MAX_RETAINED_OUTPUT,'smart-money retained byte bound')
    _reserve(c,replacements=replacements);c.files.update(replacements)
    return payload
