#!/usr/bin/env python3
"""Continue frozen Sector source coverage via plain-HTTP THS v4.

Starts from 298 exact identities retained in run 34592526507 plus accepted
884293.TI v4 raw. Only the remaining 22 identities may be requested. One
request per identity, no retry. Source-completion only; no candidate or
production/Research/Odds/Action authority.
"""
from __future__ import annotations

import argparse, hashlib, json, shutil, sys, time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import requests
from akshare.stock_feature import stock_board_industry_ths as ak

PRIOR_RUN=34592526507
PRIOR_ARTIFACT=10196213877
PRIOR_DIGEST="997d11a4973c5fa04dbc51de2080fe4fb6670c6503b3ad1ca1998b77788113c0"
PROBE_RUN=34592767428
PROBE_ARTIFACT=10196301442
PROBE_DIGEST="8b4f4cc43d6abcd8f48b2df0f553c22a41a2a726e635668e46c5fb7fea5823d7"
PROBE_RAW_SHA256="5005478468b7ad8b50c4d29ba990d8f536cc779ac5df093101d501f8696737e1"
PROBE_CODE="884293.TI"
TARGETS=(date(2026,9,7),date(2026,9,8),date(2026,9,9),date(2026,9,10))
EXPECTED_TOTAL=321; EXPECTED_RETAINED=110; EXPECTED_PUBLIC=211
EXPECTED_START_EXACT=299; EXPECTED_START_PUBLIC=189; EXPECTED_NEW=22
SPACING=1.0; TIMEOUT=12.0; MAX_BODY=4*1024*1024
AUTHORITY={"hithink_new_requests":0,"production_state_writes":0,"events_created":0,"restore_authority":"NONE","research_authority":"NONE","human_attention_authority":"NONE","investment_authority":"NONE"}

class CaptureError(RuntimeError): pass

def require(v,m):
    if not v: raise CaptureError(m)

def dec(v,f):
    try: x=Decimal(str(v))
    except (InvalidOperation,TypeError,ValueError) as exc: raise CaptureError(f"{f} not numeric") from exc
    require(x.is_finite(),f"{f} not finite"); return x

def load_json(p:Path):
    require(p.is_file() and not p.is_symlink(),f"missing input {p}"); return json.loads(p.read_text(encoding="utf-8"))

def save_json(p:Path,v): p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")

def cookie():
    js=ak.py_mini_racer.MiniRacer(); js.eval(ak._get_file_content_ths("ths.js")); v=js.call("v")
    require(isinstance(v,str) and v,"THS cookie failed"); return v

def retained_codes(source:Path):
    report=load_json(source/"capture"/"report.json"); out=set()
    for row in report.get("requests",[]):
        if str(row.get("path","")).endswith("/prices/historical") and row.get("response_file"):
            code=str(row.get("params",{}).get("thscode","")).upper()
            if code: out.add(code)
    require(len(out)==EXPECTED_RETAINED,f"retained count {len(out)}"); return out

def state_input(source:Path):
    state=load_json(source/"input"/"market-state.json"); sessions=[date.fromisoformat(x) for x in state["sessions"]]
    allcodes=tuple(str(r["thscode"]) for r in state["series"]); require(len(allcodes)==EXPECTED_TOTAL and len(set(allcodes))==EXPECTED_TOTAL,"state identity count changed")
    rows={str(r["thscode"]):r for r in state["series"]}; return sessions,allcodes,rows

def old_points(sessions,row):
    return {d:(dec(c,f"{row['thscode']}.{d}.state_close"),dec(t,f"{row['thscode']}.{d}.state_turnover")) for d,c,t in zip(sessions,row["closes"],row["turnovers"],strict=True)}

def parse_v4(body:bytes,code:str):
    require(len(body)<=MAX_BODY,f"v4 body too large {code}")
    prefix=f"quotebridge_v4_line_bk_{code[:6]}_01_2026(".encode(); require(body.startswith(prefix),f"wrapper identity mismatch {code}")
    text=body.decode(); start=text.find("{"); require(start>=0,f"object missing {code}")
    try: payload=ak.demjson.decode(text[start:-1])
    except Exception as exc: raise CaptureError(f"v4 parse failed {code}") from exc
    series=payload.get("data") if isinstance(payload,dict) else None; require(isinstance(series,str),f"data missing {code}")
    out={}
    for rec in series.split(";"):
        cols=rec.split(","); require(len(cols) in (11,12),f"row width {code}")
        raw=cols[0]; require(len(raw)==8 and raw.isdigit(),f"date invalid {code}")
        d=date(int(raw[:4]),int(raw[4:6]),int(raw[6:8]))
        if d in TARGETS:
            require(d not in out,f"duplicate date {code}"); out[d]=(dec(cols[4],f"{code}.{d}.close"),dec(cols[5],f"{code}.{d}.volume"),dec(cols[6],f"{code}.{d}.turnover"))
    require(set(out)==set(TARGETS),f"target dates missing {code}"); return out

def validate_prior(prior:Path):
    r=load_json(prior/"receipt.json")
    require(r.get("status")=="FAILED_CLOSED","prior status changed")
    require(r.get("semantics")=="FROZEN_SECTOR_RECOVERY_THS_V6_SOURCE_COMPLETION_ONLY","prior semantics changed")
    require(r.get("starting_exact_coverage")==293 and r.get("new_identity_count")==5,"prior progress changed")
    require(r.get("network_calls")==6 and r.get("retry_count")==0,"prior request policy changed")
    for k,e in AUTHORITY.items(): require(r.get(k)==e,f"prior authority changed {k}")
    err=r.get("error") or {}; require(PROBE_CODE in str(err.get("message","")),"prior blocker changed")
    checks=r.get("overlap_checks"); require(isinstance(checks,list) and len(checks)==15 and all(x.get("exact") is True for x in checks),"prior new overlaps changed")
    rv4,rv6,rv2=prior/"raw-v4",prior/"raw-v6",prior/"raw-v2"; require(rv4.is_dir() and rv6.is_dir() and rv2.is_dir(),"prior raw dirs missing")
    v4={p.name[:6]+".TI" for p in rv4.glob("*.js")}; v6={p.name[:6]+".TI" for p in rv6.glob("*.js")}; v2={p.name[:6]+".TI" for p in rv2.glob("*.js")}
    require((len(v4),len(v6),len(v2))==(97,76,15),"prior raw counts changed"); require(v4.isdisjoint(v6) and v4.isdisjoint(v2) and v6.isdisjoint(v2),"prior source overlap")
    require(len(v4|v6|v2)==188,"prior public coverage changed"); require(PROBE_CODE not in (v4|v6|v2),"884293 unexpectedly canonical")
    return v4,v6,v2

def validate_probe(probe:Path):
    r=load_json(probe/"result.json"); require(r.get("status")=="EXACT_OVERLAP_HTTP_V4_AVAILABLE" and r.get("code")==PROBE_CODE,"884293 probe not accepted")
    require(r.get("transport")=="THS_V4_HTTP" and r.get("http_status")==200,"884293 probe transport changed"); require(r.get("network_calls")==1 and r.get("retry_count")==0,"884293 probe request policy changed")
    checks=r.get("checks"); require(isinstance(checks,list) and len(checks)==3 and all(x.get("exact") is True for x in checks),"884293 probe overlap changed")
    raw=probe/"884293.js"; require(raw.is_file(),"884293 raw missing"); b=raw.read_bytes(); require(hashlib.sha256(b).hexdigest()==PROBE_RAW_SHA256,"884293 raw hash changed"); return b

def seed(prior:Path,probe:Path,out:Path):
    v4,v6,v2=validate_prior(prior); rv4,rv6,rv2=out/"raw-v4",out/"raw-v6",out/"raw-v2"; rv4.mkdir();rv6.mkdir();rv2.mkdir()
    for p in sorted((prior/"raw-v4").glob("*.js")): shutil.copyfile(p,rv4/p.name)
    for p in sorted((prior/"raw-v6").glob("*.js")): shutil.copyfile(p,rv6/p.name)
    for p in sorted((prior/"raw-v2").glob("*.js")): shutil.copyfile(p,rv2/p.name)
    (rv4/"884293-2026.js").write_bytes(validate_probe(probe)); v4.add(PROBE_CODE); require(len(v4|v6|v2)==EXPECTED_START_PUBLIC,"starting public coverage changed"); return v4,v6,v2

def fetch_v4(code,value,out):
    url=f"http://d.10jqka.com.cn/v4/line/bk_{code[:6]}/01/2026.js"; headers={"User-Agent":"Mozilla/5.0","Referer":"http://q.10jqka.com.cn","Host":"d.10jqka.com.cn","Cookie":"v="+value}
    started=datetime.now().astimezone()
    try: resp=requests.get(url,headers=headers,timeout=TIMEOUT,allow_redirects=False); body,status,err=resp.content,resp.status_code,None
    except requests.RequestException as exc: body,status,err=b"",None,type(exc).__name__
    finished=datetime.now().astimezone(); require(len(body)<=MAX_BODY,f"v4 response too large {code}")
    attempts=out/"attempts"; attempts.mkdir(exist_ok=True); name=f"{code[:6]}-v4-attempt1.js"; (attempts/name).write_bytes(body)
    return body,{"code":code,"transport":"THS_V4_HTTP","attempt":1,"retry":False,"url":url,"http_status":status,"request_error":err,"bytes":len(body),"sha256":hashlib.sha256(body).hexdigest(),"started_at":started.isoformat(),"finished_at":finished.isoformat(),"attempt_raw_file":f"attempts/{name}"}

def capture(source,prior,probe,out):
    out.mkdir(parents=True,exist_ok=False); receipt={"schema_version":1,"status":"RECORDING","semantics":"FROZEN_SECTOR_RECOVERY_THS_V4_SOURCE_COMPLETION_ONLY","prior_v6_continuation":{"run_id":PRIOR_RUN,"artifact_id":PRIOR_ARTIFACT,"digest":PRIOR_DIGEST},"v4_884293_probe":{"run_id":PROBE_RUN,"artifact_id":PROBE_ARTIFACT,"digest":PROBE_DIGEST,"raw_sha256":PROBE_RAW_SHA256},"starting_exact_coverage":EXPECTED_START_EXACT,"starting_public_exact_coverage":EXPECTED_START_PUBLIC,"requested_identity_count":EXPECTED_NEW,"new_identity_count":0,"network_calls":0,"retry_count":0,"http_attempts":[],"overlap_checks":[],**AUTHORITY,"error":None}
    try:
        sessions,allcodes,rows=state_input(source); retained=retained_codes(source); v4,v6,v2=seed(prior,probe,out); public=tuple(c for c in allcodes if c not in retained); require(len(public)==EXPECTED_PUBLIC,"public count changed")
        remaining=tuple(c for c in public if c not in (v4|v6|v2)); require(len(remaining)==EXPECTED_NEW,f"remaining count {len(remaining)}"); value=cookie()
        for code in remaining:
            body,meta=fetch_v4(code,value,out); receipt["http_attempts"].append(meta); receipt["network_calls"]+=1; save_json(out/"receipt.partial.json",receipt)
            require(meta["request_error"] is None,f"v4 request failed {code}"); require(meta["http_status"]==200,f"v4 HTTP {meta['http_status']} {code}"); pts=parse_v4(body,code); old=old_points(sessions,rows[code])
            for d in TARGETS[:3]:
                close,_vol,turn=pts[d]; ec,et=old[d]; exact=close==ec and turn==et; receipt["overlap_checks"].append({"code":code,"source_kind":"PUBLIC_THS_V4_NEW","session":d.isoformat(),"close_exact":close==ec,"turnover_exact":turn==et,"exact":exact}); require(exact,f"overlap mismatch {code} {d}")
            (out/"raw-v4"/f"{code[:6]}-2026.js").write_bytes(body); v4.add(code); receipt["new_identity_count"]+=1; save_json(out/"receipt.partial.json",receipt); time.sleep(SPACING)
        require(receipt["network_calls"]==EXPECTED_NEW and receipt["new_identity_count"]==EXPECTED_NEW,"completion counts incomplete"); require(len(v4|v6|v2)==EXPECTED_PUBLIC,"public coverage incomplete")
        receipt.update(status="SOURCE_COVERAGE_EXACT_COMPLETE",final_exact_coverage=EXPECTED_TOTAL,final_public_exact_coverage=EXPECTED_PUBLIC,final_v4_count=len(v4),final_v6_count=len(v6),final_v2_count=len(v2)); save_json(out/"receipt.json",receipt); print(receipt["status"],receipt["final_exact_coverage"]); return 0
    except Exception as exc:
        receipt["status"]="FAILED_CLOSED"; receipt["error"]={"type":type(exc).__name__,"message":" ".join(str(exc).split())[:1000]}; save_json(out/"receipt.json",receipt); print(f"FAILED_CLOSED: {type(exc).__name__}: {exc}",file=sys.stderr); return 2

def main():
    p=argparse.ArgumentParser(); p.add_argument("--source",type=Path,required=True); p.add_argument("--prior",type=Path,required=True); p.add_argument("--probe",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args(); return capture(a.source,a.prior,a.probe,a.output)
if __name__=="__main__": raise SystemExit(main())
