#!/usr/bin/env python3
"""Bounded existing-GitHub preflight. Never modifies business state or dispatches."""
from __future__ import annotations
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
from zoneinfo import ZoneInfo


def get(path,params=None):
    args=['gh','api','--method','GET','repos/auguspp/decision-kernel/'+path]
    for k,v in (params or {}).items():args += ['-f',k+'='+str(v)]
    p=subprocess.run(args,capture_output=True,text=True,timeout=45)
    if p.returncode:raise RuntimeError('GITHUB_PREFLIGHT_UNAVAILABLE')
    return json.loads(p.stdout)


def choose(previous,today,today_count,event):
    if today_count>3:return 'SKIP_DAILY_ATTEMPT_BOUND'
    if not previous or previous.get('target_date')!=today:return 'RUN_INITIAL_OR_DAILY'
    gaps=previous.get('unresolved',[])
    if not gaps:
        return 'RUN_RELEASE_CONFIRMATION' if previous.get('late_confirmation_complete') is False else 'SKIP_ALREADY_DELIVERED'
    transient={'TRANSPORT_TIMEOUT','TRANSPORT_CONNECTION','HTTP_502','HTTP_503','HTTP_504',
               'SOURCE_BUSY','RESOURCE_BUDGET','PAGE_OR_TIME_BUDGET','NOT_ATTEMPTED','CALENDAR_UNAVAILABLE'}
    if any(g.get('failure') in transient for g in gaps):return 'RUN_BOUNDED_RECOVERY'
    # Changed contracts, authentication, quota, identity or unknown errors are
    # not retried just because another maintenance clock arrived.
    return 'SKIP_NONTRANSIENT_GAPS'


def pending_publication(runs,current_id,accepted_source_id,artifacts):
    """Reconcile an earlier unconsumed capture before spending on another one.

    Metadata-only skip attempts do not hide an earlier raw capture. Return an
    exact run locator, not permission to rerun it or silently choose old success.
    """
    if len({r['id'] for r in runs})!=len(runs):raise ValueError('DUPLICATE_SOURCE_RUN')
    own=[r for r in runs if r['id']==current_id]
    if len(own)!=1:raise ValueError('CURRENT_RUN_NOT_DISCOVERED')
    older=sorted((r for r in runs if r['created_at']<own[0]['created_at']),
                 key=lambda r:(r['created_at'],r['id']),reverse=True)
    for r in older:
        if r['id']==accepted_source_id:return None
        if r['status']!='completed':return r['id']
        inventory=artifacts(r['id'])
        values=inventory['artifacts']
        if type(inventory['total_count']) is not int or inventory['total_count']!=len(values):
            raise ValueError('PRIOR_ARTIFACT_SCOPE_INCOMPLETE')
        name=f"smart-money-{r['id']}-1"
        found=[a for a in values if a['name']==name]
        if len(found)>1:raise ValueError('DUPLICATE_PRIOR_CAPTURE')
        if found:return r['id']
    if len(runs)>=30 and accepted_source_id is not None:
        raise ValueError('UNRECONCILED_SOURCE_HISTORY_RANGE')
    return None


def main():
    from decision_kernel.runtime import current_state as m
    from decision_kernel.runtime import smart_money_sources as s, smart_money_capture as capture
    env=os.environ;ident=capture.identity(env);clock=datetime.now(timezone.utc);today=clock.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()
    root=Path(env['RUNNER_TEMP'])/'smart-money-control';root.mkdir(exist_ok=False)
    expected=env.get('EXPECTED_CODE') or env['GITHUB_SHA']
    if expected!=env['GITHUB_SHA']:raise ValueError('EXPECTED_MAIN_CHANGED')
    ci=get('actions/workflows/ci.yml/runs',{'head_sha':expected,'event':'push','per_page':10})['workflow_runs']
    matches=[r for r in ci if r['head_sha']==expected and r['head_branch']=='main' and r['path']=='.github/workflows/ci.yml']
    if not matches:raise ValueError('MAIN_CI_MISSING')
    latest=max(matches,key=lambda r:(r['created_at'],r['id']))
    if not(latest['run_attempt']==1 and latest['status']=='completed' and latest['conclusion']=='success'):raise ValueError('MAIN_CI_NOT_PASSED')
    refs=get('git/matching-refs/heads/read-model/current-state');refs=[r for r in refs if r['ref']=='refs/heads/read-model/current-state']
    previous=None;reading=None;read_status='NO_PREVIOUS_READING'
    if refs:
        if len(refs)!=1:raise ValueError('AMBIGUOUS_READING_REF')
        reading=refs[0]['object']['sha']
        package=get('contents/current-state.json',{'ref':reading})
        raw=base64.b64decode(package['content']);m.check(m.blob_sha(raw)==package['sha'],'prior root blob differs')
        value=json.loads(raw);m.validate_read_package(value)
        sm=value['research'].get('smart_money',{})
        if sm.get('prior_retained_entry'):
            sm=sm['prior_retained_entry']['entry']
        ref=sm.get('details',{}).get('state')
        if ref:
            data=get('git/blobs/'+ref['git_blob']);raw=base64.b64decode(data['content'])
            m.check(len(raw)==ref['bytes'] and m.blob_sha(raw)==ref['git_blob'] and m.sha256(raw)==ref['sha256'],'prior state bytes differ')
            previous=json.loads(raw);m.check(previous['version']==s.VERSION,'prior state contract differs')
            (Path(env['RUNNER_TEMP'])/'smart-money-previous-state.json').write_bytes(raw)
            read_status='EXACT_PRIOR_STATE_READ'
        else:read_status='NO_SMART_MONEY_STATE_IN_READING'
    page=get('actions/workflows/radar-smart-money.yml/runs',{'branch':'main','per_page':30})
    runs=page['workflow_runs']
    if not isinstance(runs,list) or page['total_count']<len(runs):raise ValueError('RUN_QUERY_INCOMPLETE')
    today_runs=[r for r in runs if datetime.fromisoformat(r['created_at'].replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()==today]
    if len(runs)==30 and len(today_runs)==30:raise ValueError('DAILY_RUN_SCOPE_INCOMPLETE')
    decision=choose(previous,today,len(today_runs),env['GITHUB_EVENT_NAME'])
    repair=env.get('REPAIR_PENDING','false')=='true'
    if repair:
        if env['GITHUB_EVENT_NAME']!='workflow_dispatch' or not env.get('EXPECTED_CODE') or not previous:
            raise ValueError('EXPLICIT_REPAIR_REQUIRES_PINNED_MAIN_AND_PRIOR_STATE')
        if len(today_runs)<=3 and previous.get('unresolved'):decision='RUN_EXPLICIT_PENDING_REPAIR'
    pending_source=None
    if decision.startswith('RUN_'):
        pending_source=pending_publication(runs,ident['run_id'],(previous or {}).get('last_source_run_id'),
            lambda rid:get(f'actions/runs/{rid}/artifacts',{'per_page':100}))
        if pending_source is not None:decision='SKIP_AWAITING_PRIOR_CAPTURE_READING'
    blockers=[];activity_status='NOT_CHECKED_NO_CAPTURE'
    if decision.startswith('RUN_'):
        activity=runpy.run_path('.github/scripts/check-sector-scheduled-activity.py')
        peers=activity['PEERS']|frozenset('.github/workflows/'+n+'.yml' for n in
             ('sector-radar-shadow','radar-industry-breadth','radar-institutional-source'))
        try:
            blockers=activity['check_activity'](activity['request_reader'](env['GH_TOKEN']),peers=peers)
            activity_status='SOURCE_BUSY' if blockers else 'NO_VISIBLE_PEER'
        except (RuntimeError,ValueError,KeyError):
            activity_status='ACTIVITY_CHECK_UNAVAILABLE'
    skip_ht=activity_status in {'SOURCE_BUSY','ACTIVITY_CHECK_UNAVAILABLE'}
    control={'version':s.VERSION,'run_id':ident['run_id'],'code_commit':expected,'event':ident['event'],
             'checked_at':clock.isoformat(),'target_date':today,'decision':decision,'today_invocations':len(today_runs),
             'prior_reading':reading,'prior_read_status':read_status,'hithink_activity':activity_status,
             'pending_source_run_id':pending_source,'blockers':blockers,'skip_hithink':skip_ht,'pending_delivery_count':len((previous or {}).get('unresolved',[])),
             'investment_authority':'NONE'}
    (root/'control.json').write_text(json.dumps(control,ensure_ascii=False,indent=2))
    with open(env['GITHUB_OUTPUT'],'a') as f:
        print('run_capture='+str(decision.startswith('RUN_')).lower(),file=f)
        print('skip_hithink='+str(skip_ht).lower(),file=f)
        print('repair_pending='+str(repair or decision=='RUN_BOUNDED_RECOVERY').lower(),file=f)
    print(json.dumps(control,ensure_ascii=False))


if __name__=='__main__':main()
