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
from . import smart_money_sources as s, smart_money_capture as capture, smart_money_view as view\nfrom . import smart_money_relay as relay_supplement
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
        relay_value=None
        if refs.get('relay'):
            _reserve(c,calls=1,files=0)
            relay_value=json.loads(read_bound(c,refs['relay'],prior_commit))
        return {'history':hist,'overview':overview,'state':state,'origins':origins,
                'relay':relay_value},'EXACT_PREVIOUS_'+prior_commit
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
    return read_run(c,selected,follow_control=True)


def reconcile_pending_attempt(c, run):
    """One native attempt read for pending metadata; no polling or source calls.

    The run-level response may precede the completed attempt response. Never
    promote success from a notification, collection row, or another attempt.
    Identity conflicts or a failed read remain an explicit reading gap.
    """
    if run['status'] == 'completed':
        return run, []
    m.check(type(run['run_attempt']) is int and run['run_attempt'] == 1,
            'smart-money pending attempt identity')
    _reserve(c, calls=1, files=0)
    endpoint = f"actions/runs/{run['id']}/attempts/1"
    attempt = c.api.get(endpoint)
    fields = ('id', 'head_sha', 'head_branch', 'path', 'event', 'run_attempt', 'created_at')
    m.check(all(attempt.get(k) == run.get(k) for k in fields),
            'smart-money attempt metadata identity differs')
    for field in ('repository', 'head_repository'):
        m.check(attempt.get(field, {}).get('full_name') == run.get(field, {}).get('full_name'),
                'smart-money attempt repository differs')
    m.check(m.clock(run['created_at']) <= m.clock(run['updated_at'])
            <= m.clock(attempt['updated_at']) <= m.clock(c.now()),
            'smart-money attempt metadata clocks differ')
    m.check(attempt['status'] in {'queued', 'in_progress', 'waiting', 'requested',
                                'pending', 'completed'}, 'smart-money attempt status unknown')
    diagnostic = {'run_id': run['id'], 'attempt': 1, 'endpoint': endpoint,
                  'run_status': run['status'], 'run_updated_at': run['updated_at'],
                  'attempt_status': attempt['status'], 'attempt_updated_at': attempt['updated_at'],
                  'checked_at': c.now(), 'reads': 1,
                  'meaning': 'SAME_IDENTITY_ATTEMPT_READ_NOT_STATUS_INFERENCE_OR_RETRY'}
    return attempt, [diagnostic]


def read_relay(c, artifacts, run, identity):
    matches=[a for a in artifacts if a['name']==f"smart-money-relay-{run['id']}-1"]
    if not matches:
        return None
    m.check(len(matches)==1,'smart-money relay artifact duplicate')
    files,archive=c.archive(matches[0],run)
    result=relay_supplement.replay(files,identity=identity,cutoff=c.now())
    m.check(result['identity']==identity and result['relay_host'].startswith('https://pcd.mobcvb.cn/'),
            'smart-money relay identity')
    return {'result':result,'archive':archive}


def read_run(c,selected,*,follow_control=False):
    _reserve(c,calls=6,files=2)
    run=c.api.get('actions/runs/'+str(selected['id']))
    m.check(all(run[k]==selected[k] for k in ('id','head_sha','event','run_attempt')),'smart-money run changed')
    run, metadata_reads = reconcile_pending_attempt(c, run)
    identity={'repository':run.get('repository',{}).get('full_name'),'workflow':run['path'],
              'ref':'refs/heads/'+str(run['head_branch']),'event':run['event'],'code_commit':run['head_sha'],
              'run_id':run['id'],'attempt':run['run_attempt']}
    capture.validate_identity(identity)
    m.check(run.get('head_repository',{}).get('full_name')==m.REPOSITORY,'smart-money foreign source')
    m.check(m.clock(run['created_at'])<=m.clock(run['updated_at'])<=m.clock(c.now()),'smart-money run clock')
    status={'latest_attempt':m.concise_run(run),'observation':None,
            'run_metadata_reads':metadata_reads}
    if run['status']!='completed':return {**status,'status':'AWAITING_CURRENT_CAPTURE'}
    jobs=c.api.get(f"actions/runs/{run['id']}/attempts/1/jobs?per_page=100")
    m.check(jobs['total_count']==len(jobs['jobs']),'smart-money incomplete jobs')
    matches=[j for j in jobs['jobs'] if j['name']=='capture-smart-money']
    m.check(len(matches)==1,'smart-money capture job identity')
    job=matches[0]
    m.check(job.get('head_sha')==run['head_sha'] and job.get('run_id')==run['id'] and job.get('run_attempt')==1,
            'smart-money job identity')
    artifacts=c.artifacts(run)
    relay_info=read_relay(c,artifacts,run,identity)
    status['relay']=relay_info
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
        pending=(control or {}).get('pending_source_run_id')
        if follow_control and control and control['decision']=='SKIP_AWAITING_PRIOR_CAPTURE_READING' and pending:
            m.check(type(pending)is int and pending>0 and pending!=run['id'],'smart-money invalid prior capture locator')
            bound=c.api.get('actions/runs/'+str(pending))
            m.check(bound['id']==pending and m.clock(bound['created_at'])<m.clock(run['created_at']),
                    'smart-money prior capture chronology')
            recovered=read_run(c,bound,follow_control=False)
            recovered['source_run']=recovered.get('source_run',recovered.get('latest_attempt'))
            recovered['latest_attempt']=m.concise_run(run)
            recovered['control']=control
            recovered['run_metadata_reads']=metadata_reads+recovered.get('run_metadata_reads',[])
            recovered['reading_relation']='EXACT_UNCONSUMED_CAPTURE_BOUND_BY_CONTROL_NOT_SILENT_SUCCESS_FALLBACK'
            return recovered
        return {**status,'status':('NO_NEW_CAPTURE_REQUIRED' if control and control['decision']=='SKIP_ALREADY_DELIVERED'
                                  else 'CAPTURE_NOT_SAVED_NOT_QUIET')}
    m.check(len(captures)==1,'smart-money capture duplicate')
    files,archive=c.archive(captures[0],run)
    manifest=s.decode(files['capture.json'])
    observation=capture.replay(files,identity,cutoff=c.now())
    m.check(m.clock(run['created_at'])<=m.clock(manifest['started_at'])<=m.clock(manifest['finished_at'])
            <=m.clock(run['updated_at']),'smart-money capture clock binding')
    # A checkpoint from a failed job may yield useful partial facts but cannot
    # erase missing deliveries or be promoted into complete source qualification.
    if job['conclusion']!='success':
        observation['status']='PARTIAL_FAILED_EXECUTION'
        observation['unresolved'].append({'family':'execution','partition':str(run['id']),'failure':'CAPTURE_JOB_FAILED'})
    return {**status,'status':observation['status'],'observation':observation,'archive':archive,
            'capture_hash':manifest['capture_hash'],'job_id':job['id'],'job_conclusion':job['conclusion']}


def restore_deferred_documents(c,old,obs):
    """Migrate only already-retained forecast originals, never fetch new PDFs."""
    if not old or old['history'].get('forecast_documents'):
        return
    if any(p['family']=='forecasts' for p in obs['partitions']):
        return
    rows=[r for r in old['history']['records'] if r['family']=='forecasts']
    if not rows:return
    try:
        keys={r['origin'] for r in rows}
        eligible=[(k,v) for k,v in old['origins'].items() if k in keys]
        m.check(bool(eligible),'forecast origin absent')
        key,origin=max(eligible,key=lambda kv:m.clock(kv[1]['cutoff']))
        # Exact recorded prior origin, not a search for a conveniently green run.
        saved=read_run(c,origin['run'],follow_control=False)
        prior=saved.get('observation')
        m.check(prior is not None and prior['capture_hash']==key
                and m.clock(prior['cutoff'])<=m.clock(obs['cutoff']),
                'forecast origin binding differs')
        documents=deepcopy(prior.get('forecast_documents',[]))
        for doc in documents:
            doc.update(origin_capture_hash=key,origin_cutoff=prior['cutoff'])
        old['history']['forecast_documents']=documents
        old['history']['forecast_document_recovery']='EXACT_RETAINED_ORIGIN_REPLAY_NOT_NEW_PDF_ACQUISITION'
    except ERRORS as exc:
        old['history']['forecast_document_recovery']='RETAINED_DOCUMENT_CONTEXT_GAP_'+type(exc).__name__


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
        restore_deferred_documents(c,old,obs)
        hist=view.history(obs,(old or {}).get('history'))
        overview=view.summarize(obs,hist);state=view.state(obs,(old or {}).get('state'))
        origins[obs['capture_hash']]={'reading_commit':None,'archive':current['archive'],
            'run':current.get('source_run',current['latest_attempt']),'capture_hash':obs['capture_hash'],'cutoff':obs['cutoff']}
    elif old:
        hist=old['history'];overview=deepcopy(old['overview']);state=old['state']
    else:
        research=deepcopy(baseline['research'])
        research['smart_money']={'status':current['status'],'previous_status':prior_status,
            'meaning':'NO_READABLE_SMART_MONEY_OBSERVATION_NOT_ZERO_ACTIVITY',**s.AUTHORITY}
        return assemble(c,baseline,research,{},'\n聪明钱观察尚不可读；不是没有资本行为。\n')
    relay_info=current.get('relay')
    relay_value=(deepcopy(relay_info['result']) if relay_info
                 else deepcopy((old or {}).get('relay')))
    if relay_value is not None:
        if relay_info:
            relay_value['archive']=relay_info['archive']
            relay_value['reading_relation']='CURRENT_SOURCE_RUN'
        else:
            relay_value['reading_relation']='PRIOR_RETAINED_NO_CURRENT_SUPPLEMENT'
        overview['relay_supplement']={
            'status':relay_value['status'],'market_session':relay_value.get('market_session'),
            'cutoff':relay_value['cutoff'],'relay_host':relay_value['relay_host'],
            'family_coverage':{api:{'status':item['status'],'row_count':item['row_count']}
                               for api,item in relay_value.get('families',{}).items()},
            'reading_relation':relay_value['reading_relation'],
            'meaning':'SECONDARY_RELAY_SUPPLEMENT_NOT_PRIMARY_OR_OFFICIAL_TUSHARE'}
    chunks,meta=view.encode_chunks(hist)
    _reserve(c,files=len(chunks)+6)
    refs={}
    for ref in meta['chunks']:
        ref['reference']=c.retain(PREFIX+ref['name'],chunks[ref['name']])
    age=(m.clock(c.now())-m.clock(overview['cutoff'])).total_seconds()/3600
    reading_freshness='CHECK_AGE_EXCEEDS_36H_RECHECK_SCHEDULE' if age>36 else 'RECENT_CAPTURE_NOT_EACH_SOURCE_FRESHNESS'
    overview.update(reading_freshness=reading_freshness,capture_age_hours=f"{age:.2f}",
        origins=origins,current_reading={'status':current['status'],
        'latest_attempt':current.get('latest_attempt'),'control':current.get('control'),
        'run_metadata_reads':current.get('run_metadata_reads',[]),
        'uses_prior_observation':obs is None,'previous_status':prior_status})
    refs['overview']=c.retain(PREFIX+'overview.json',m.json_bytes(overview))
    refs['history']=c.retain(PREFIX+'history.json',m.json_bytes(meta))
    refs['state']=c.retain(PREFIX+'state.json',m.json_bytes(state))
    if relay_value is not None:
        refs['relay']=c.retain(PREFIX+'relay.json',m.json_bytes(relay_value))
    text=view.render(overview,hist,failure=current['status'] if obs is None and current['status']!='NO_NEW_CAPTURE_REQUIRED' else None)
    if relay_value is not None:
        text += '\n' + relay_supplement.render(relay_value)
    refs['markdown']=c.retain('details/radar/smart-money.md',text.encode())
    browser_status = 'DISPLAY_PROJECTION_COMPLETE'
    try:
        browser_bytes = view.browser(overview,chunks,meta,origins).encode()
    except s.SourceError as exc:
        if str(exc) != 'BROWSER_OUTPUT_BOUND':
            raise
        # A display size limit must not roll back qualified observations/state.
        # Keep the original cap, all canonical chunks, and an honest navigation.
        browser_status = 'DISPLAY_SIZE_LIMIT_CANONICAL_DATA_RETAINED'
        browser_bytes = ("<!doctype html><html lang='zh-CN'><meta charset='utf-8'>"
                         "<title>聪明钱完整资料已保留</title><h1>完整资料已保存</h1>"
                         "<p>本次离线检索页超过显示大小限制，不代表采集失败或没有行为。"
                         "全部记录、原始身份和来源仍可在以下同版入口读取。</p>"
                         "<p><a href='../smart-money.md'>摘要与限制</a> · "
                         "<a href='overview.json'>结构化概览</a> · "
                         "<a href='history.json'>全部历史分块</a></p></html>").encode()
    refs['browser']=c.retain(PREFIX+'browse.html',browser_bytes)
    research=deepcopy(baseline['research'])
    research['smart_money']={'status':current['status'],'details':refs,'source_cutoff':overview['cutoff'],
        'target_date':overview['target_date'],'latest_attempt':current.get('latest_attempt'),
        'browser_status':browser_status,
        'relay_status':relay_value['status'] if relay_value is not None else 'NOT_PRESENT_LEGACY_OR_NOT_RUN',
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
