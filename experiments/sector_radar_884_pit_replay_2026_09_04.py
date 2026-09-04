from __future__ import annotations

import hashlib, json, os, shutil, statistics, time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from decision_kernel.adapters.hithink import SHANGHAI_TZ, latest_completed_a_share_session, normalize_hithink_calendar
from decision_kernel.adapters.hithink_index import normalize_hithink_completed_index_history, normalize_hithink_industry_catalog
from decision_kernel.runtime.hithink_http import HITHINK_API_KEY_ENV, HITHINK_CALENDAR_PATH, _request_hithink_json
from decision_kernel.runtime.hithink_index_http import HITHINK_INDEX_CATALOG_PATH, HITHINK_INDEX_HISTORY_PATH
from decision_kernel.runtime.sector_radar import (
    SECTOR_RADAR_FORMULA_VERSION, SECTOR_RADAR_HUMAN_ATTENTION_AUTHORITY,
    SECTOR_RADAR_INVESTMENT_AUTHORITY, SECTOR_RADAR_SEMANTICS,
    SectorPricePoint, SectorPriceSeries, calculate_sector_radar_snapshot,
)

TARGET=date(2026,9,4); BENCHMARK=("000300.SH","沪深300")
CATALOG_HASH="367d64660f5ef1f715ae0ef1d832a180d075ec7d6fc0a915797cbfafbd33f360"
SOURCE_RUN=33869436890; SOURCE_ARTIFACT=9936117543
SOURCE_SHA="58de421f48f5d8d5ddafd1a702e1f676367f450da145948e932b186d6cd78816"
SOURCE=Path("broad-source"); SOURCE_PROGRESS=SOURCE/"sector-radar-pit-replay-progress.jsonl"; SOURCE_INPUTS=SOURCE/"sector-radar-pit-replay-inputs"
OUT=Path("sector-radar-884-pit-replay.json"); SUMMARY=Path("sector-radar-884-pit-replay-summary.md")
PROGRESS=Path("sector-radar-884-pit-replay-progress.jsonl"); ERROR=Path("sector-radar-884-pit-replay-error.json"); CHECKPOINTS=Path("sector-radar-884-pit-replay-inputs")
PACE=float(os.environ.get("SECTOR_RADAR_884_HISTORY_PACE_SECONDS","15")); MAX_ATTEMPTS=3
PRESSURE={
 "农业 / 种植":(("881101.TI",),("884002.TI","884003.TI","884004.TI")),
 "养殖 / 猪肉 / 鸡肉":(("881102.TI",),("884275.TI","884276.TI","884277.TI")),
 "水产":(("881102.TI",),("884005.TI","884006.TI","884279.TI")),
 "造船 / 航海装备":(("881166.TI",),("884183.TI",)),
}
RULES={
 "TOP_QUARTILE_RUN_3":"20d excess > 0 + 20d rating >= 75 + top-quartile run == 3",
 "TOP_DECILE_RUN_3":"20d excess > 0 + 20d rating >= 90 + top-decile run == 3",
 "TOP_DECILE_RUN_3_TURNOVER":"TOP_DECILE_RUN_3 + turnover pulse >= 1.2x",
}

def j(v:Any)->Any:
 if is_dataclass(v): return j(asdict(v))
 if isinstance(v,Mapping): return {str(k):j(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)): return [j(x) for x in v]
 if isinstance(v,Decimal): return format(v,"f")
 if isinstance(v,(date,datetime)): return v.isoformat()
 return v

def h(v:Any)->str:
 return hashlib.sha256(json.dumps(j(v),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def sha(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def loc(path:str,params:Mapping[str,str])->str:
 q=urlencode(sorted(params.items())); return f"https://fuyao.aicubes.cn{path}"+(f"?{q}" if q else "")
def log(v:Mapping[str,Any])->None:
 with PROGRESS.open("a",encoding="utf-8") as f: f.write(json.dumps(j(v),ensure_ascii=False,sort_keys=True)+"\n")

def request(key:str,path:str,params:Mapping[str,str]):
 attempts=[]
 for n in range(1,MAX_ATTEMPTS+1):
  started=datetime.now(timezone.utc)
  try: env=_request_hithink_json(api_key=key,path=path,params=params,timeout_seconds=30.0)
  except ConnectionError as exc:
   ended=datetime.now(timezone.utc); row={"attempt":n,"status":"TRANSIENT_CONNECTION_FAILURE","started":started,"ended":ended,"error_type":type(exc).__name__,"error":str(exc)}; attempts.append(row); log({"stage":"transport_retry","path":path,"params":dict(params),**row})
   if n==MAX_ATTEMPTS: raise
   time.sleep(2**(n-1)); continue
  ended=datetime.now(timezone.utc)
  return env,{"path":path,"params":dict(sorted(params.items())),"source_locator":loc(path,params),"request_started_at":started,"response_completed_at":ended,"duration_seconds":(ended-started).total_seconds(),"request_id":env.get("request_id"),"business_code":env.get("code"),"envelope_sha256":h(env),"transport_attempt_count":n,"transport_retry_count":n-1,"transport_attempts":attempts+[dict(attempt=n,status="SUCCESS",started=started,ended=ended)],"retry_scope":"TRANSIENT_CONNECTION_FAILURE_ONLY"}
 raise RuntimeError("unreachable")

def source_meta():
 rows=[json.loads(x) for x in SOURCE_PROGRESS.read_text().splitlines() if x.strip()]; cats=[x for x in rows if x.get("stage")=="catalog"]; hist=[x for x in rows if x.get("stage")=="history"]
 if len(cats)!=1 or cats[0].get("catalog_hash")!=CATALOG_HASH or len(hist)!=101: raise ValueError("source artifact lineage mismatch")
 by={x["thscode"].upper():x for x in hist}
 if len(by)!=101: raise ValueError("source history metadata duplicated")
 return by

def read_series(path:Path,code:str,name:str,expected_sha:str|None=None):
 if expected_sha and sha(path)!=expected_sha: raise ValueError(f"checkpoint hash mismatch {code}")
 p=json.loads(path.read_text());
 if p.get("thscode")!=code or p.get("response_session")!=p.get("expected_latest_session") or p.get("response_session")!=TARGET.isoformat(): raise ValueError(f"checkpoint PIT mismatch {code}")
 if p.get("checkpoint_semantics")!="QUALIFIED_HISTORY_INPUT_ONLY" or p.get("human_attention_authority")!="NONE" or p.get("investment_authority")!="NONE": raise ValueError(f"checkpoint authority mismatch {code}")
 pts=tuple(SectorPricePoint(session=datetime.fromisoformat(x["as_of"]).date(),close=Decimal(x["close"]),turnover=Decimal(x["turnover"])) for x in p["points"])
 if tuple(x.session for x in pts)!=tuple(sorted({x.session for x in pts})): raise ValueError(f"checkpoint sessions invalid {code}")
 return SectorPriceSeries(code,name,pts)

def load_source(meta):
 bench=read_series(SOURCE_INPUTS/"000300_SH.json",BENCHMARK[0],BENCHMARK[1],meta[BENCHMARK[0]]["checkpoint_sha256"]); broad=[]; seeds={}
 for code,m in meta.items():
  if m.get("family") not in {"BROAD_881","GRANULAR_884"}: continue
  s=read_series(SOURCE_INPUTS/f"{code.replace('.','_')}.json",code,m["name"],m["checkpoint_sha256"])
  if m["family"]=="BROAD_881": broad.append(s)
  else: seeds[code]=s
 broad=tuple(sorted(broad,key=lambda x:x.thscode)); seeds={k:v for k,v in seeds.items()}
 if len(broad)!=90 or len(seeds)!=10: raise ValueError("source family counts changed")
 sessions=tuple(x.session for x in bench.points)
 if len(sessions)!=164 or sessions[-1]!=TARGET or any(tuple(x.session for x in s.points)!=sessions for s in (*broad,*seeds.values())): raise ValueError("source session alignment changed")
 return bench,broad,seeds

def write_checkpoint(code,history,meta):
 CHECKPOINTS.mkdir(exist_ok=True); path=CHECKPOINTS/f"{code.replace('.','_')}.json"; body={"schema_version":1,"thscode":code,"request":meta,"response_session":history.response_session,"expected_latest_session":history.expected_latest_session,"points":history.points,"checkpoint_semantics":"QUALIFIED_HISTORY_INPUT_ONLY","human_attention_authority":"NONE","investment_authority":"NONE"}; text=json.dumps(j(body),ensure_ascii=False,indent=2,sort_keys=True)+"\n"; tmp=path.with_name("."+path.name+".tmp"); tmp.write_text(text); tmp.replace(path); return path,hashlib.sha256(text.encode()).hexdigest()
def copy_seed(code,meta):
 src=SOURCE_INPUTS/f"{code.replace('.','_')}.json"; expected=meta[code]["checkpoint_sha256"]
 if sha(src)!=expected: raise ValueError(f"seed hash mismatch {code}")
 CHECKPOINTS.mkdir(exist_ok=True); dst=CHECKPOINTS/src.name; shutil.copyfile(src,dst)
 return dst,expected

def replay(bench,sectors):
 sessions=tuple(x.session for x in bench.points)
 if any(tuple(x.session for x in s.points)!=sessions for s in sectors): raise ValueError("replay inputs are not aligned")
 by_date={}; decile={}; runs={s.thscode:0 for s in sectors}
 for d in sessions[60:]:
  snap=calculate_sector_radar_snapshot(sectors=sectors,benchmark=bench,as_of_session=d)
  if snap.exclusions or len(snap.observations)!=len(sectors): raise ValueError(f"coverage failure {d}")
  if (snap.radar_semantics,snap.human_attention_authority,snap.investment_authority)!=(SECTOR_RADAR_SEMANTICS,SECTOR_RADAR_HUMAN_ATTENTION_AUTHORITY,SECTOR_RADAR_INVESTMENT_AUTHORITY): raise ValueError("authority changed")
  rows={x.thscode:x for x in snap.observations}
  for c,x in rows.items(): runs[c]=runs[c]+1 if x.horizon_20.excess_return>0 and x.horizon_20.cross_sectional_rating>=90 else 0
  by_date[d]=rows; decile[d]=dict(runs)
 return tuple(by_date),by_date,decile

def row(obs,run): return {**asdict(obs),"top_decile_20d_persistence_sessions":run}
def first(rows,pred): return next((x for x in rows if pred(x)),None)
def marks(rows):
 return {"first_positive":first(rows,lambda x:x["horizon_20"]["excess_return"]>0),"first_top_quartile":first(rows,lambda x:x["horizon_20"]["excess_return"]>0 and x["horizon_20"]["cross_sectional_rating"]>=75),"first_top_quartile_run_3":first(rows,lambda x:x["horizon_20"]["excess_return"]>0 and x["top_quartile_20d_persistence_sessions"]==3),"first_top_decile":first(rows,lambda x:x["horizon_20"]["excess_return"]>0 and x["horizon_20"]["cross_sectional_rating"]>=90),"first_top_decile_run_3":first(rows,lambda x:x["top_decile_20d_persistence_sessions"]==3),"latest":rows[-1]}
def traces(dates,rep,runs,codes):
 out={}
 for c in codes:
  rows=tuple(row(rep[d][c],runs[d][c]) for d in dates); out[c]={"name":rep[dates[-1]][c].name,"milestones":marks(rows),"trace":rows}
 return out

def forward(series,bench,d,n):
 dates=tuple(x.session for x in bench.points); i=dates.index(d)
 if i+n>=len(dates): return None
 end=dates[i+n]; sc={x.session:x.close for x in series.points}; bc={x.session:x.close for x in bench.points}; sr=sc[end]/sc[d]-1; br=bc[end]/bc[d]-1
 return {"end":end,"sector_return":sr,"benchmark_return":br,"excess_return":sr-br}
def stats(values):
 return {"count":len(values),"mean":sum(values,Decimal())/len(values),"median":Decimal(str(statistics.median(values))),"positive_share":Decimal(sum(x>0 for x in values))/len(values)} if values else {"count":0}
def eligible(x,run,rule):
 if rule=="TOP_QUARTILE_RUN_3": return x.horizon_20.excess_return>0 and x.horizon_20.cross_sectional_rating>=75 and x.top_quartile_20d_persistence_sessions==3
 if rule=="TOP_DECILE_RUN_3": return x.horizon_20.excess_return>0 and run==3
 if rule=="TOP_DECILE_RUN_3_TURNOVER": return x.horizon_20.excess_return>0 and run==3 and x.turnover_pulse_5_vs_prior_20 is not None and x.turnover_pulse_5_vs_prior_20>=Decimal("1.2")
 raise ValueError(rule)
def evaluate(rule,dates,rep,runs,series,bench):
 daily=[]; events=[]
 for d in dates:
  candidates=[x for c,x in rep[d].items() if eligible(x,runs[d][c],rule)]; candidates.sort(key=lambda x:(x.horizon_20.cross_sectional_rank,-x.rank_change_5_sessions_20d,x.thscode)); daily.append({"date":d,"eligible":len(candidates),"selected":[x.thscode for x in candidates[:3]],"omitted":[x.thscode for x in candidates[3:]]})
  for pos,x in enumerate(candidates,1): events.append({"date":d,"position":pos if pos<=3 else None,"observation":x,"forward_5":forward(series[x.thscode],bench,d,5),"forward_20":forward(series[x.thscode],bench,d,20)})
 f5=[x["forward_5"]["excess_return"] for x in events if x["forward_5"]]; f20=[x["forward_20"]["excess_return"] for x in events if x["forward_20"]]
 return {"rule":RULES[rule],"status":"RETROSPECTIVE_ONLY_NOT_AUTHORIZED","days":len(dates),"quiet_days":sum(x["eligible"]==0 for x in daily),"active_days":sum(x["eligible"]>0 for x in daily),"events":len(events),"selected":sum(x["position"] is not None for x in events),"truncated_days":sum(x["eligible"]>3 for x in daily),"max_same_day":max(x["eligible"] for x in daily),"forward_5":stats(f5),"forward_20":stats(f20),"daily":daily}
def pct(v): return "NA" if v is None else f"{Decimal(str(v))*100:+.2f}%"
def render(result):
 lines=["# Sector Discovery Radar — separate 884 cross-sectional replay","",f"- Target session: `{result['target_session']}`",f"- Broad comparison: `{result['integrity']['broad_count']}` exact 881 identities",f"- Granular challenger: `{result['integrity']['granular_count']}` exact 884 identities",f"- Replay dates: `{result['replay']['days']}`",f"- New history calls: `{result['acquisition']['new_history_calls']}`; reused exact granular checkpoints: `{result['acquisition']['reused_granular_histories']}`",f"- Human attention authority: `NONE`",f"- Investment authority: `NONE`","","## Pressure cases","","| Case / lane | Identity | Top-quartile run 3 | Top-decile run 3 | Latest 20d excess | Rating |","| --- | --- | --- | --- | ---: | ---: |"]
 for case,m in result["pressure_cases"].items():
  for lane in ("broad","granular"):
   for code,t in m[lane].items():
    x=t["milestones"]; q=x["first_top_quartile_run_3"]; d=x["first_top_decile_run_3"]; latest=x["latest"]; lines.append(f"| {case} / {lane} | `{code} {t['name']}` | {q['as_of_session'] if q else 'not observed'} | {d['as_of_session'] if d else 'not observed'} | {pct(latest['horizon_20']['excess_return'])} | {latest['horizon_20']['cross_sectional_rating']} |")
 lines += ["","## Noise / compression comparison","","| Universe / rule | Events | Quiet days | Truncated days | Max same day | T+5 median | T+20 median |","| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
 for name,x in result["challengers"].items(): lines.append(f"| {name} | {x['events']} | {x['quiet_days']} | {x['truncated_days']} | {x['max_same_day']} | {pct(x['forward_5'].get('median'))} | {pct(x['forward_20'].get('median'))} |")
 lines += ["","Separate 884 ranks are descriptive challenger evidence. They are not mixed with the 881 percentile universe.","","```text","PHASE C 884 CHALLENGER = ANALYSIS_REQUIRED","CURRENT BREADTH = NOT YET RUN","PHASE D SHADOW PRODUCER = NOT AUTHORIZED","HUMAN ATTENTION AUTHORITY = NONE","INVESTMENT AUTHORITY = NONE","```",""]
 return "\n".join(lines)

def main():
 if PACE<0: raise ValueError("pace must be non-negative")
 key=os.environ.get(HITHINK_API_KEY_ENV)
 if not key: raise ValueError(f"{HITHINK_API_KEY_ENV} is required")
 captured=datetime.now(timezone.utc); meta=source_meta(); bench,broad,seeds=load_source(meta)
 cal_env,cal_meta=request(key,HITHINK_CALENDAR_PATH,{}); calendar=normalize_hithink_calendar(cal_env); latest=latest_completed_a_share_session(calendar,observed_at=captured)
 if latest!=TARGET: raise ValueError(f"target {TARGET} != latest {latest}")
 log({"stage":"calendar","latest":latest,**cal_meta})
 cat_env,cat_meta=request(key,HITHINK_INDEX_CATALOG_PATH,{"tag":"industry"}); catalog=normalize_hithink_industry_catalog(cat_env)
 if catalog.catalog_hash!=CATALOG_HASH or len(catalog.broad_industries)!=90 or len(catalog.granular_industries)!=230: raise ValueError("catalog identity changed")
 log({"stage":"catalog","catalog_hash":catalog.catalog_hash,"broad":90,"granular":230,**cat_meta})
 start=datetime.combine(date(2026,1,1),datetime.min.time(),tzinfo=SHANGHAI_TZ); end=datetime.combine(TARGET+timedelta(days=1),datetime.min.time(),tzinfo=SHANGHAI_TZ); common={"interval":"1d","start":str(int(start.timestamp()*1000)),"end":str(int(end.timestamp()*1000))}
 granular={}; records=[]; new_calls=0; reused=0; last=None
 for i,item in enumerate(catalog.granular_industries,1):
  code=item.thscode
  if code in seeds:
   path,ck=copy_seed(code,meta); s=read_series(path,code,item.name,ck); rec={"stage":"history","index":i,"total":230,"thscode":code,"name":item.name,"acquisition":"REUSED_RUN_33869436890","checkpoint_path":str(path),"checkpoint_sha256":ck,"points":len(s.points)}; reused+=1
  else:
   if last is not None and PACE:
    elapsed=time.monotonic()-last
    if elapsed<PACE: time.sleep(PACE-elapsed)
   env,req=request(key,HITHINK_INDEX_HISTORY_PATH,{"thscode":code,**common}); last=time.monotonic(); history=normalize_hithink_completed_index_history(env,thscode=code,sessions=calendar,observed_at=captured)
   if history.response_session!=TARGET: raise ValueError(f"stale history {code}")
   path,ck=write_checkpoint(code,history,req); s=read_series(path,code,item.name,ck); rec={"stage":"history","index":i,"total":230,"thscode":code,"name":item.name,"acquisition":"NEW_PROVIDER_HISTORY","checkpoint_path":str(path),"checkpoint_sha256":ck,"points":len(s.points),**req}; new_calls+=1
  granular[code]=s; records.append(rec); log(rec); print(f"HISTORY {i}/230 {code} {item.name} {rec['acquisition']}",flush=True)
 granular_tuple=tuple(granular[c] for c in sorted(granular)); bd,br,bt=replay(bench,broad); gd,gr,gt=replay(bench,granular_tuple)
 if bd!=gd: raise ValueError("replay dates differ")
 pressure={}
 for label,(bc,gc) in PRESSURE.items(): pressure[label]={"broad":traces(bd,br,bt,bc),"granular":traces(gd,gr,gt,gc),"mapping_warning":"881166 军工装备 remains contextual parent only" if label=="造船 / 航海装备" else None}
 bmap={x.thscode:x for x in broad}; gmap={x.thscode:x for x in granular_tuple}
 challengers={"881 comparable":evaluate("TOP_QUARTILE_RUN_3",bd,br,bt,bmap,bench),"884 comparable":evaluate("TOP_QUARTILE_RUN_3",gd,gr,gt,gmap,bench),"884 top-decile":evaluate("TOP_DECILE_RUN_3",gd,gr,gt,gmap,bench),"884 top-decile + turnover":evaluate("TOP_DECILE_RUN_3_TURNOVER",gd,gr,gt,gmap,bench)}
 current=tuple(row(x,gt[TARGET][x.thscode]) for x in sorted(gr[TARGET].values(),key=lambda x:(x.horizon_20.cross_sectional_rank,x.thscode)))
 result={"schema_version":1,"captured_at":captured,"target_session":TARGET,"source":"HiThink Financial-API index daily market data","source_artifact":{"run_id":SOURCE_RUN,"artifact_id":SOURCE_ARTIFACT,"artifact_sha256":SOURCE_SHA},"formula_version":SECTOR_RADAR_FORMULA_VERSION,"integrity":{"catalog_hash":catalog.catalog_hash,"broad_count":90,"granular_count":230,"session_count":len(bench.points),"history_start":bench.points[0].session,"history_end":bench.points[-1].session,"all_histories_aligned":True,"checkpoint_count":len(tuple(CHECKPOINTS.glob('*.json'))),"checkpoint_set_hash":h({p.name:sha(p) for p in sorted(CHECKPOINTS.glob('*.json'))})},"acquisition":{"calendar":cal_meta,"catalog":cat_meta,"new_history_calls":new_calls,"reused_granular_histories":reused,"pace_seconds":PACE,"max_transport_attempts":MAX_ATTEMPTS,"retry_scope":"TRANSIENT_CONNECTION_FAILURE_ONLY","records":records},"replay":{"start":gd[0],"end":gd[-1],"days":len(gd)},"pressure_cases":pressure,"challengers":challengers,"current_granular_cross_section":current,"decision":{"phase_c_884_challenger":"ANALYSIS_REQUIRED","current_breadth":"NOT_YET_RUN","phase_d_shadow_producer":"NOT_AUTHORIZED"},"radar_semantics":SECTOR_RADAR_SEMANTICS,"human_attention_authority":SECTOR_RADAR_HUMAN_ATTENTION_AUTHORITY,"investment_authority":SECTOR_RADAR_INVESTMENT_AUTHORITY,"explicit_non_authorities":["NO_PRODUCTION_DETECTOR","NO_RESEARCH_ROUTE","NO_ATTENTION_INBOX_INSERTION","NO_RECOMMENDATION","NO_ACTION"]}
 result["result_hash"]=h(result); OUT.write_text(json.dumps(j(result),ensure_ascii=False,indent=2,sort_keys=True)+"\n"); SUMMARY.write_text(render(json.loads(OUT.read_text()))); print(f"RESULT={OUT}\nSUMMARY={SUMMARY}\nGRANULAR_UNIVERSE=230\nREPLAY_DAYS={len(gd)}\nHUMAN_ATTENTION_AUTHORITY=NONE\nINVESTMENT_AUTHORITY=NONE")

if __name__=="__main__":
 try: main()
 except Exception as exc:
  ERROR.write_text(json.dumps({"captured_at":datetime.now(timezone.utc).isoformat(),"error_type":type(exc).__name__,"error":str(exc),"progress_path":str(PROGRESS),"checkpoint_count":len(tuple(CHECKPOINTS.glob('*.json'))) if CHECKPOINTS.is_dir() else 0,"human_attention_authority":"NONE","investment_authority":"NONE"},ensure_ascii=False,indent=2)+"\n"); raise
