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
from . import smart_money_relay as relay_supplement
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
        # Optional supplement bytes are read only after the primary package is
        # safely assembled. A missing supplement must not erase primary history.
        relay_reference=({'commit':prior_commit,'reference':refs['relay']} if refs.get('relay')
                         else item.get('relay_prior_retained_entry'))
        return {'history':hist,'overview':overview,'state':state,'origins':origins,
                'relay_reference':relay_reference},'EXACT_PREVIOUS_'+prior_commit
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
    _reserve(c,calls=8,files=3)
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
    # Keep this internal context out of serialized primary observations. The
    # optional archive is not allowed to spend the primary publication budget.
    status['_relay_context']={'jobs':jobs['jobs'],'artifacts':artifacts,
                              'run':run,'identity':identity}
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
        reuse=(control or {}).get('decision')=='SKIP_RELAY_ONLY_REUSE_CAPTURE'
        if follow_control and reuse:
            declared=control.get('relay_source') or {}
            pending=declared.get('run_id')
            m.check(type(pending)is int and pending>0 and pending!=run['id'],
                    'smart-money relay reuse source locator')
            bound=c.api.get('actions/runs/'+str(pending))
            m.check(bound['id']==pending and bound['head_sha']==declared.get('head_sha') and
                    m.clock(bound['created_at'])<m.clock(run['created_at']),
                    'smart-money relay reuse chronology')
            recovered=read_run(c,bound,follow_control=False)
            obs=recovered.get('observation')
            m.check(obs is not None and obs['capture_hash']==declared.get('capture_hash'),
                    'smart-money relay reuse capture binding')
            source_archive=recovered['archive']
            m.check(source_archive['artifact_id']==declared.get('artifact_id') and
                    source_archive['sha256']==declared.get('digest','').removeprefix('sha256:') and
                    source_archive['bytes']==declared.get('bytes'), 'smart-money relay reuse archive binding')
            context=status['_relay_context']
            context.update(market_session=max(obs['trading_sessions'],default=None),
                           primary_capture=relay_supplement.source_binding(obs), requires_reuse_binding=True)
            recovered.update(source_run=recovered.get('source_run',recovered.get('latest_attempt')),
                latest_attempt=m.concise_run(run), control=control, control_archive=status.get('control_archive'),
                _relay_context=context, reading_relation='EXACT_REUSED_PRIMARY_CALENDAR_NOT_NEW_MARKET_CAPTURE',
                run_metadata_reads=metadata_reads+recovered.get('run_metadata_reads',[]))
            return recovered
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
    status['_relay_context']['market_session']=max(observation['trading_sessions'],default=None)
    status['_relay_context']['primary_capture']=relay_supplement.source_binding(observation)
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
    # Never carry an old derived READY summary after its optional bytes fail.
    overview.pop('relay_supplement',None)
    overview.pop('relay_reading',None)
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
    text=view.render(overview,hist,failure=current['status'] if obs is None and current['status']!='NO_NEW_CAPTURE_REQUIRED' else None)
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
    context=current.get('_relay_context') or {}
    optional_pending=bool((old or {}).get('relay_reference') or
        any(j.get('name')=='capture-tushare-relay' for j in context.get('jobs',[])) or
        any(a.get('name','').startswith('smart-money-relay-') for a in context.get('artifacts',[])))
    research=deepcopy(baseline['research'])
    research['smart_money']={'status':current['status'],'details':refs,'source_cutoff':overview['cutoff'],
        'target_date':overview['target_date'],'latest_attempt':current.get('latest_attempt'),
        'browser_status':browser_status,
        'relay_status':'OPTIONAL_RELAY_NOT_CHECKED' if optional_pending else 'NOT_PRESENT_LEGACY_OR_NOT_RUN',
        'relay_retained_status':None,
        'relay_prior_retained_entry':deepcopy((old or {}).get('relay_reference')),
        'capture_hash':hist['capture_hash'],'uses_prior_observation':obs is None,
        'pending_delivery_count':len(state['unresolved']),'reading_freshness':reading_freshness,
        'capture_age_hours':f"{age:.2f}",
        'family_coverage':{f:{k:v[k] for k in ('status','saved_records','companies','latest_period')} for f,v in overview['families'].items()},
        'meaning':'PUBLIC_BEHAVIOR_NOT_SMARTNESS_OR_BUY_SELL_SIGNAL',**s.AUTHORITY}
    primary=assemble(c,baseline,research,{},'\n[聪明钱：游资、北向、具名持股与资本行为](details/radar/smart-money.md)；独立观察与缺口，不是综合荐股分。\n')
    return attach_relay(c,primary,current,old)


def current_relay(c, context):
    """Read one same-run supplement, without relaxing its source contracts."""
    run,identity=context['run'],context['identity']
    jobs=[j for j in context['jobs'] if j['name']=='capture-tushare-relay']
    artifacts=[a for a in context['artifacts'] if a['name']==f"smart-money-relay-{run['id']}-1"]
    m.check(len(jobs)<=1 and len(artifacts)<=1,'smart-money relay duplicate')
    if not jobs:
        m.check(not artifacts,'smart-money relay artifact without job')
        return None,'NOT_PRESENT_LEGACY_OR_NOT_RUN'
    job=jobs[0]
    m.check(job.get('head_sha')==run['head_sha'] and job.get('run_id')==run['id']
            and job.get('run_attempt')==1,'smart-money relay job identity')
    conclusion=job.get('conclusion')
    state=({'success':'JOB_SUCCEEDED_ARTIFACT_MISSING','skipped':'NOT_RUN_WITHOUT_PRIMARY_CAPTURE'}
           .get(conclusion,'JOB_'+str(conclusion or job.get('status')).upper()))
    if not artifacts:
        return None,state
    m.check(job.get('status')=='completed' and conclusion in {'success','failure','cancelled','timed_out'},
            'smart-money relay artifact job state')
    m.check(context.get('market_session') is not None,'smart-money relay primary calendar missing')
    _reserve(c,calls=1,files=2)
    saved=read_relay(c,artifacts,run,identity)
    result=saved['result']
    manifest=s.decode(c.archive_cache[artifacts[0]['id']][0]['capture.json'])
    m.check(m.clock(run['created_at'])<=m.clock(manifest['started_at'])
            <=m.clock(manifest['finished_at'])<=m.clock(run['updated_at']),
            'smart-money relay run clock binding')
    m.check(result['market_session']==context['market_session'],'smart-money relay calendar differs')
    if context.get('requires_reuse_binding'):
        m.check(result.get('plan_revision')==2,'smart-money relay reuse needs explicit source binding')
    if result.get('plan_revision')==2:
        m.check(result.get('source_capture')==context.get('primary_capture'),
                'smart-money relay source capture differs')
    if conclusion!='success':
        result=deepcopy(result)
        result['status']='PARTIAL_FAILED_EXECUTION'
        result['unresolved'].append({'api':'execution','status':'CAPTURE_JOB_'+conclusion.upper()})
    result.update(archive=saved['archive'],reading_relation='CURRENT_SOURCE_RUN')
    return result,result['status']


def prior_relay(c, locator):
    _reserve(c,calls=1,files=1)
    result=json.loads(read_bound(c,locator['reference'],locator['commit']))
    m.check(result['version']==relay_supplement.VERSION
            and result['relay_host']==relay_supplement.relay.PRO,'smart-money prior relay source')
    capture.validate_identity(result['identity'])
    m.check(all(result.get(k)==v for k,v in relay_supplement.AUTHORITY.items()),
            'smart-money prior relay authority')
    m.check(m.clock(result['cutoff'])<=m.clock(c.now()),'smart-money prior relay future')
    # Verify the existing consumer shape, not economic truth or source coverage.
    relay_supplement.render(result)
    result['reading_relation']='PRIOR_RETAINED_NO_CURRENT_SUPPLEMENT'
    return result


def attach_relay(c, primary, current, old):
    """Transactional optional reading after a fully valid primary package.

    Only the exact current archive and explicit prior locator may be read. On
    rejection restore optional retained files, never API counters or old facts.
    """
    before=dict(c.files),dict(c.archive_cache),dict(c.sources)
    locator=deepcopy((old or {}).get('relay_reference'))
    value=None
    current_status='NOT_PRESENT_LEGACY_OR_NOT_RUN'
    previous_status='NOT_NEEDED_NO_PRIOR_SUPPLEMENT'
    diagnostic={}
    context=current.get('_relay_context')
    if context is not None:
        try:
            value,current_status=current_relay(c,context)
            if value is not None:
                relay_supplement.render(value)
        except ERRORS as exc:
            c.files,c.archive_cache,c.sources=map(dict,before)
            value=None
            current_status='CURRENT_RELAY_READING_GAP'
            diagnostic['current_error_type']=type(exc).__name__
    elif current.get('status') not in {'NOT_RUN','NO_NEW_CAPTURE_REQUIRED'}:
        current_status='NOT_READ_WITHOUT_QUALIFIED_CURRENT_CONTEXT'
    if value is None and locator is not None:
        try:
            value=prior_relay(c,locator)
            previous_status='EXACT_PREVIOUS_SUPPLEMENT'
        except ERRORS as exc:
            c.files,c.archive_cache,c.sources=map(dict,before)
            previous_status='PREVIOUS_RELAY_READING_GAP'
            diagnostic['previous_error_type']=type(exc).__name__
    elif value is not None:
        previous_status='NOT_READ_CURRENT_SUPPLEMENT_AVAILABLE'
    if value is None and not diagnostic and locator is None and current_status=='NOT_PRESENT_LEGACY_OR_NOT_RUN':
        return primary
    try:
        research=deepcopy(primary['research']);sm=research['smart_money']
        display_status=current_status
        if current_status=='NOT_PRESENT_LEGACY_OR_NOT_RUN' and locator is not None:
            display_status=('PRIOR_RETAINED_NO_CURRENT_SUPPLEMENT' if value is not None
                            else 'PREVIOUS_RELAY_READING_GAP')
        sm.update(relay_status=display_status,relay_previous_status=previous_status,
                  relay_current_run_id=context['run']['id'] if context is not None else None,
                  relay_retained_status=value['status'] if value is not None else None,
                  relay_prior_retained_entry=locator if value is None else None,
                  relay_reading_diagnostics=diagnostic)
        refs=sm['details']
        overview=json.loads(c.files[refs['overview']['read_path']])
        note='\n## Tushare Relay 补充读取\n\n当前读取：'+current_status+'；历史补充：'+previous_status+'。主资料独立保留。\n'
        if value is not None:
            value['current_run_status']=current_status
            refs['relay']=c.retain(PREFIX+'relay.json',m.json_bytes(value))
            overview['relay_supplement']={
                'status':value['status'],'current_run_status':current_status,
                'market_session':value.get('market_session'),'cutoff':value['cutoff'],
                'relay_host':value['relay_host'],'reading_relation':value['reading_relation'],
                'family_coverage':{api:{'status':item['status'],'row_count':item['row_count']}
                                   for api,item in value['families'].items()},
                'meaning':'SECONDARY_RELAY_SUPPLEMENT_NOT_PRIMARY_OR_OFFICIAL_TUSHARE'}
            note+='\n'+relay_supplement.render(value)
        overview['relay_reading']={'current_status':current_status,'previous_status':previous_status,
                                   'diagnostics':diagnostic}
        # These two files were built locally in this call, not yet published.
        # Replace only their exact primary bytes within this rollback boundary.
        for key,raw in (('overview',m.json_bytes(overview)),
                        ('markdown',c.files[refs['markdown']['read_path']]+note.encode())):
            ref=refs[key]
            m.check(m.blob_sha(c.files[ref['read_path']])==ref['git_blob'],'smart-money local primary bytes')
            del c.files[ref['read_path']]
            refs[key]=c.retain(ref['read_path'],raw)
        return assemble(c,primary,research,{},'')
    except ERRORS as exc:
        c.files,c.archive_cache,c.sources=map(dict,before)
        # The primary was already assembled and validated. Optional formatting,
        # budget or retention failure cannot turn it into an unavailable lane.
        research=deepcopy(primary['research'])
        research['smart_money'].update(relay_status='OPTIONAL_RELAY_PUBLICATION_GAP',
            relay_retained_status=None,relay_prior_retained_entry=locator,
            relay_reading_diagnostics={**diagnostic,'publication_error_type':type(exc).__name__})
        try:
            return assemble(c,primary,research,{},'')
        except ERRORS:
            c.files,c.archive_cache,c.sources=map(dict,before)
            # Even diagnostics must fit the original budget. The already-valid
            # primary still explicitly marks this supplement as NOT_CHECKED and
            # retains its prior locator; do not spend its reserve again.
            return primary


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