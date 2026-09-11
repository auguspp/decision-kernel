#!/usr/bin/env python3
"""Finish the frozen 2026-09-10 Sector candidate with THS v6→v4 bounded fallback.

All prior successful raw is reused. Only remaining exact identities access the public
THS CDN. No HiThink calls, no production state writes, no signals.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import requests

B = runpy.run_path('.github/scripts/capture-sector-ths-v6-complete.py')
CaptureError = B['CaptureError']; require=B['require']; save_json=B['save_json']; load_json=B['load_json']
source_report=B['source_report']; retained_inputs=B['retained_inputs']; parse_v4=B['parse_v4']; parse_v6=B['parse_v6']; cookie=B['cookie']
REPO=B['REPO']; SOURCE_WORKFLOW=B['SOURCE_WORKFLOW']; TARGET=B['TARGET']; CODE_RE=B['CODE_RE']; MAX_BODY=B['MAX_BODY']; SHANGHAI=B['SHANGHAI']
AUTHORITY=B['AUTHORITY']; TRANSIENT=B['TRANSIENT']

from decision_kernel.adapters.hithink import latest_completed_a_share_session, normalize_hithink_calendar
from decision_kernel.adapters.hithink_index import normalize_hithink_completed_index_history, normalize_hithink_industry_catalog
from decision_kernel.runtime.sector_radar import SectorPricePoint, SectorPriceSeries
from decision_kernel.runtime.sector_radar_audit import _atomic_bytes, _sha
from decision_kernel.runtime.sector_radar_persistence import load_sector_radar_persistent_bundle
from decision_kernel.runtime.sector_radar_state import SectorRadarStateSourceLineage, create_sector_radar_market_state, serialize_sector_radar_market_state

PRIOR_COMBINED_RUN=34575644848
PRIOR_COMBINED_ARTIFACT=10189565008
PRIOR_COMBINED_DIGEST='bcc95e6d875197ad992c2b57186f2642f4a8aee1e4d52bc5a6844e1a3b630e33'
V4_PROBE_RUN=34576022176
V4_PROBE_ARTIFACT=10189654420
V4_PROBE_DIGEST='f2b2e42418a92acc3a596d7e06b04d21429ee8cd4e24774b67362fc8fd326b0a'
EXPECTED_HITHINK=110; EXPECTED_V4_PRIOR=40; EXPECTED_V6_PRIOR=27; EXPECTED_V4_PROBE=1; EXPECTED_NEW=143
SPACING=1.25; TIMEOUT=12.0; RETRY_DELAY=5.0
MAX_V6_SECOND=40; MAX_FALLBACK_IDENTITIES=30; MAX_V4_SECOND=20


def scan_prior(prior:Path, probe:Path, out:Path, capture:bool):
    rv4=out/'raw-v4'; rv6=out/'raw-v6'
    if capture:
        rv4.mkdir(parents=True); rv6.mkdir(parents=True)
        s4=prior/'raw-v4'; s6=prior/'raw-v6'; require(s4.is_dir() and s6.is_dir(),'prior raw dirs missing')
        v4=list(sorted(s4.glob('*.js'))); v6=list(sorted(s6.glob('*.js')))
        require(len(v4)==EXPECTED_V4_PRIOR,f'prior v4 count {len(v4)}'); require(len(v6)==EXPECTED_V6_PRIOR,f'prior v6 count {len(v6)}')
        for p in v4: _atomic_bytes(rv4/p.name,p.read_bytes())
        for p in v6: _atomic_bytes(rv6/p.name,p.read_bytes())
        pr=load_json(probe/'result.json'); require(pr.get('status')=='EXACT_OVERLAP_V4_AVAILABLE','884118 v4 probe not accepted')
        pp=probe/'884118.js'; require(pp.is_file(),'884118 v4 probe raw missing'); _atomic_bytes(rv4/'884118-2026.js',pp.read_bytes())
    v4codes={p.name[:6]+'.TI' for p in rv4.glob('*.js')}; v6codes={p.name[:6]+'.TI' for p in rv6.glob('*.js')}
    require(len(v4codes)==EXPECTED_V4_PRIOR+EXPECTED_V4_PROBE,f'captured v4 count {len(v4codes)}')
    require(len(v6codes)==EXPECTED_V6_PRIOR,f'captured v6 count {len(v6codes)}')
    require(v4codes.isdisjoint(v6codes),'prior v4/v6 identities overlap')
    return v4codes,v6codes


def public_get(code:str, mode:str, cv:str, attempts:Path, attempt:int):
    require(mode in {'v6','v4'},'mode invalid'); require(CODE_RE.fullmatch(code) is not None,f'identity invalid {code}')
    if mode=='v6': url=f'https://d.10jqka.com.cn/v6/line/48_{code[:6]}/01/last1800.js'
    else: url=f'https://d.10jqka.com.cn/v4/line/bk_{code[:6]}/01/2026.js'
    headers={'User-Agent':'Mozilla/5.0','Referer':'http://q.10jqka.com.cn','Host':'d.10jqka.com.cn','Cookie':'v='+cv}
    started=datetime.now(tz=SHANGHAI)
    try: r=requests.get(url,headers=headers,timeout=TIMEOUT,allow_redirects=False)
    except requests.RequestException as exc: raise CaptureError(f'{mode} request failed {code}: {type(exc).__name__}') from exc
    finished=datetime.now(tz=SHANGHAI); body=r.content; require(len(body)<=MAX_BODY,f'{mode} response too large {code}')
    attempts.mkdir(parents=True,exist_ok=True); name=f'{code[:6]}-{mode}-attempt{attempt}.js'; _atomic_bytes(attempts/name,body)
    return body,{'code':code,'mode':mode,'attempt':attempt,'url':url,'http_status':r.status_code,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'started_at':started.isoformat(),'finished_at':finished.isoformat(),'attempt_raw_file':f'attempts/{name}'}


def acquire(code:str, cv:str, out:Path, receipt:dict[str,Any]):
    attempts=out/'attempts'
    # v6: at most two attempts for transient HTTP only
    for n in (1,2):
        if n==2:
            require(receipt['v6_second_attempts']<MAX_V6_SECOND,'v6 second-attempt cap exhausted'); receipt['v6_second_attempts']+=1; save_json(out/'receipt.partial.json',receipt); time.sleep(RETRY_DELAY)
        body,m=public_get(code,'v6',cv,attempts,n); receipt['http_attempts'].append(m); save_json(out/'receipt.partial.json',receipt)
        if m['http_status']==200:
            _atomic_bytes(out/'raw-v6'/f'{code[:6]}.js',body); return 'v6'
        if m['http_status'] not in TRANSIENT: raise CaptureError(f"v6 HTTP {m['http_status']} {code}")
        if n==1: continue
    # v4 fallback only after two transient v6 responses
    require(receipt['fallback_identities']<MAX_FALLBACK_IDENTITIES,'fallback identity cap exhausted'); receipt['fallback_identities']+=1; save_json(out/'receipt.partial.json',receipt)
    for n in (1,2):
        if n==2:
            require(receipt['v4_second_attempts']<MAX_V4_SECOND,'v4 second-attempt cap exhausted'); receipt['v4_second_attempts']+=1; save_json(out/'receipt.partial.json',receipt); time.sleep(RETRY_DELAY)
        body,m=public_get(code,'v4',cv,attempts,n); receipt['http_attempts'].append(m); save_json(out/'receipt.partial.json',receipt)
        if m['http_status']==200:
            _atomic_bytes(out/'raw-v4'/f'{code[:6]}-2026.js',body); return 'v4'
        if m['http_status'] not in TRANSIENT or n==2: raise CaptureError(f"v4 HTTP {m['http_status']} {code} attempt={n}")
    raise CaptureError(f'no source succeeded {code}')


def compose(source:Path,out:Path,capture:bool,prior:Path|None=None,probe:Path|None=None,cv:str|None=None):
    report=source_report(source); cal_env,cat_env,retained=retained_inputs(source,report)
    bundle=load_sector_radar_persistent_bundle(source/'input',expected_repository=REPO,expected_workflow=SOURCE_WORKFLOW,expected_parent_hint_mapping_hash=report['binding']['request']['parent']['parent_hint_mapping_hash'])
    state=bundle.market_state; sessions=normalize_hithink_calendar(cal_env); observed=datetime.fromisoformat(report['observed_at']); target=latest_completed_a_share_session(sessions,observed_at=observed)
    require(target==TARGET,'target changed'); require(state.sessions[-1]==date(2026,9,9),'state end changed'); overlap=state.sessions[-3:]; needed=(*overlap,target)
    catalog=normalize_hithink_industry_catalog(cat_env); require(catalog.catalog_hash==state.catalog_hash,'catalog changed')
    allcodes=tuple(x.thscode for x in state.series); public=tuple(c for c in allcodes if c not in retained); require(len(retained)==EXPECTED_HITHINK and len(public)==211,'identity counts changed')
    if capture: require(prior is not None and probe is not None and cv is not None,'capture inputs missing')
    v4,v6=scan_prior(prior if prior else Path('.'),probe if probe else Path('.'),out,capture)
    require((v4|v6).issubset(set(public)),'prior public identity not in missing set')
    remaining=tuple(c for c in public if c not in v4 and c not in v6); require(len(remaining)==EXPECTED_NEW,f'remaining count {len(remaining)}')
    receipt={'schema_version':1,'status':'RECORDING' if capture else 'VERIFYING','semantics':'FROZEN_SECTOR_RECOVERY_THS_DUAL_BOUNDED_FALLBACK_CANDIDATE_ONLY','prior_combined':{'run_id':PRIOR_COMBINED_RUN,'artifact_id':PRIOR_COMBINED_ARTIFACT,'digest':PRIOR_COMBINED_DIGEST},'v4_probe':{'run_id':V4_PROBE_RUN,'artifact_id':V4_PROBE_ARTIFACT,'digest':V4_PROBE_DIGEST},'target_session':TARGET.isoformat(),'preexisting_v4_count':len(v4),'preexisting_v6_count':len(v6),'new_identity_count':0,'v6_second_attempts':0,'fallback_identities':0,'v4_second_attempts':0,'http_attempts':[],'overlap_checks':[],'event_ledger_sha256':_sha((source/'input/candidate-events.json').read_bytes()),'candidate_state_hash':None,'candidate_state_sha256':None,'hithink_new_requests':0,**AUTHORITY,'error':None}
    oldby={x.thscode:x for x in state.series}; done={}
    for code in allcodes:
        old=oldby[code]; oldpts={d:(c,t) for d,c,t in zip(state.sessions,old.closes,old.turnovers,strict=True)}
        if code in retained:
            env=load_json(retained[code]); h=normalize_hithink_completed_index_history(env,thscode=code,sessions=sessions,observed_at=observed); require(h.response_session==h.expected_latest_session==TARGET,f'retained target {code}'); by={p.as_of.date():(p.close,p.volume,p.turnover) for p in h.points}; kind='RETAINED_HITHINK'
        else:
            if capture and code in remaining:
                mode=acquire(code,cv,out,receipt); receipt['new_identity_count']+=1; save_json(out/'receipt.partial.json',receipt); time.sleep(SPACING)
                if mode=='v4': v4.add(code)
                else: v6.add(code)
            p4=out/'raw-v4'/f'{code[:6]}-2026.js'; p6=out/'raw-v6'/f'{code[:6]}.js'
            require(p4.is_file() ^ p6.is_file(),f'canonical public source ambiguous/missing {code}')
            if p4.is_file(): by=parse_v4(p4.read_bytes(),code,needed); kind='PUBLIC_THS_V4'
            else: by=parse_v6(p6.read_bytes(),code,needed); kind='PUBLIC_THS_V6'
        require(all(d in by for d in needed),f'needed dates missing {code}')
        for d in overlap:
            cl,_,tu=by[d]; ec,et=oldpts[d]; exact=cl==ec and tu==et; receipt['overlap_checks'].append({'code':code,'source_kind':kind,'session':d.isoformat(),'close_exact':cl==ec,'turnover_exact':tu==et,'exact':exact}); require(exact,f'overlap mismatch {code} {d}')
        cl,_,tu=by[TARGET]; done[code]=(cl,tu)
    require(len(done)==len(allcodes),'coverage incomplete')
    if capture: require(receipt['new_identity_count']==EXPECTED_NEW,'new count incomplete')
    series=[]
    for old in state.series:
        pts=tuple(SectorPricePoint(d,c,t) for d,c,t in zip(state.sessions,old.closes,old.turnovers,strict=True)); c,t=done[old.thscode]; pts+=(SectorPricePoint(TARGET,c,t),); series.append(SectorPriceSeries(old.thscode,old.name,pts))
    parent=report['binding']['request']['parent']; lineage=(*state.source_lineage,SectorRadarStateSourceLineage('RECOVERY_PARENT_STATE',parent['run_id'],parent['artifact_id'],parent['artifact_digest'],bundle.manifest.last_result_hash))
    candidate=create_sector_radar_market_state(catalog=catalog,benchmark=series[0],broad_series=series[1:1+len(state.broad_identities)],granular_series=series[1+len(state.broad_identities):],created_at=observed,source='RECOVERY_CANDIDATE_RETAINED_HITHINK_THS_DUAL_NOT_RESTORE_AUTHORITY',source_lineage=lineage)
    cb=serialize_sector_radar_market_state(candidate).encode(); eb=(source/'input/candidate-events.json').read_bytes(); receipt.update(status='RECOVERY_CANDIDATE_REVIEW_REQUIRED',candidate_state_hash=candidate.state_hash,candidate_state_sha256=hashlib.sha256(cb).hexdigest(),final_v4_count=sum(1 for c in public if (out/'raw-v4'/f'{c[:6]}-2026.js').is_file()),final_v6_count=sum(1 for c in public if (out/'raw-v6'/f'{c[:6]}.js').is_file()))
    return cb,eb,receipt

def capture(source,prior,probe,out):
    out.mkdir(parents=True,exist_ok=False)
    try:
        cb,eb,r=compose(source,out,True,prior,probe,cookie()); _atomic_bytes(out/'candidate-state.json',cb); _atomic_bytes(out/'candidate-events.json',eb); save_json(out/'receipt.json',r); print(f"status={r['status']} new={r['new_identity_count']} v4={r['final_v4_count']} v6={r['final_v6_count']} candidate={r['candidate_state_hash']}"); return 0
    except Exception as exc:
        p=out/'receipt.partial.json'; r=load_json(p) if p.is_file() else {'schema_version':1,'status':'FAILED_CLOSED','http_attempts':[],**AUTHORITY}; r['status']='FAILED_CLOSED'; r['error']={'type':type(exc).__name__,'message':' '.join(str(exc).split())[:1000]}; save_json(out/'receipt.json',r); print(f'FAILED_CLOSED: {type(exc).__name__}: {exc}',file=sys.stderr); return 2

def verify(source,cap,out):
    out.mkdir(parents=True,exist_ok=False)
    try:
        saved=load_json(cap/'receipt.json'); require(saved.get('status')=='RECOVERY_CANDIDATE_REVIEW_REQUIRED','capture incomplete'); cb,eb,r=compose(source,cap,False); require(cb==(cap/'candidate-state.json').read_bytes(),'candidate bytes differ'); require(eb==(cap/'candidate-events.json').read_bytes(),'event bytes differ'); require(r['candidate_state_hash']==saved['candidate_state_hash'],'state hash differs'); result={'schema_version':1,'status':'OFFLINE_REBUILD_EXACT_MATCH','candidate_state_hash':r['candidate_state_hash'],'candidate_state_sha256':r['candidate_state_sha256'],'event_ledger_sha256':r['event_ledger_sha256'],'network_calls':0,**AUTHORITY}; save_json(out/'verification.json',result); print(result['status'],result['candidate_state_hash']); return 0
    except Exception as exc: save_json(out/'verification.json',{'schema_version':1,'status':'FAILED_CLOSED','network_calls':0,'error':{'type':type(exc).__name__,'message':' '.join(str(exc).split())[:1000]},**AUTHORITY}); return 2

def main():
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest='cmd',required=True); c=s.add_parser('capture'); c.add_argument('--source',type=Path,required=True); c.add_argument('--prior',type=Path,required=True); c.add_argument('--probe',type=Path,required=True); c.add_argument('--output',type=Path,required=True); v=s.add_parser('verify'); v.add_argument('--source',type=Path,required=True); v.add_argument('--capture',type=Path,required=True); v.add_argument('--output',type=Path,required=True); a=p.parse_args(); return capture(a.source,a.prior,a.probe,a.output) if a.cmd=='capture' else verify(a.source,a.capture,a.output)
if __name__=='__main__': raise SystemExit(main())
