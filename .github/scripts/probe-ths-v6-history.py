#!/usr/bin/env python3
"""Probe THS v6 last1800 board history for one known and one stubborn identity.

No HiThink calls, no production writes, no retries.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from akshare.stock_feature import stock_board_industry_ths as ak_ths

SOURCE = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
RAW = OUT / "raw"
RAW.mkdir()
SH = ZoneInfo("Asia/Shanghai")
CODES = ("884002.TI", "884075.TI")
KNOWN = "884002.TI"
STUBBORN = "884075.TI"
TARGETS = (date(2026,9,7), date(2026,9,8), date(2026,9,9), date(2026,9,10))
CODE_RE = re.compile(r"^884\d{3}\.TI$")

class E(RuntimeError): pass

def req(c,m):
    if not c: raise E(m)

def dec(v,f):
    try: x=Decimal(str(v))
    except (InvalidOperation,TypeError,ValueError) as e: raise E(f+" not numeric") from e
    req(x.is_finite(),f+" not finite")
    return x

def msday(v):
    return datetime.fromtimestamp(int(v)/1000,tz=SH).date()

def cookie():
    js=ak_ths.py_mini_racer.MiniRacer(); js.eval(ak_ths._get_file_content_ths("ths.js")); v=js.call("v")
    req(isinstance(v,str) and v,"cookie failed"); return v

def old_state():
    p=SOURCE/"input"/"market-state.json"; req(p.is_file(),"state missing")
    return json.loads(p.read_text())

def retained_known():
    r=json.loads((SOURCE/"capture"/"report.json").read_text())
    for x in r["requests"]:
        if x.get("params",{}).get("thscode")==KNOWN and x.get("response_file"):
            return json.loads((SOURCE/"capture"/x["response_file"]).read_text())
    raise E("known retained history missing")

def state_points(st,code):
    sessions=[date.fromisoformat(x) for x in st["sessions"]]
    row=next((x for x in st["series"] if x["thscode"]==code),None); req(row is not None,"state identity missing "+code)
    return {d:(dec(c,"state close"),dec(t,"state turnover")) for d,c,t in zip(sessions,row["closes"],row["turnovers"],strict=True)}

def known_points(env):
    data=env["data"]; req(data["thscode"]==KNOWN,"known identity mismatch")
    out={}
    for r in data["item"]:
        d=msday(r["date_ms"])
        if d in TARGETS:
            out[d]=(dec(r["close_price"],"known close"),dec(r["volume"],"known volume"),dec(r["turnover"],"known turnover"))
    return out

def parse_v6(body,code):
    text=body.decode("utf-8"); s=text.find("{"); req(s>=0,"v6 object missing")
    payload=json.loads(text[s:-1])
    # Mature AData contract places the semicolon K-line series at root data.
    series=payload.get("data")
    if not isinstance(series,str):
        # Some THS wrappers may nest under 48_<code>; accept only an unambiguous data string.
        node=payload.get("48_"+code[:6])
        if isinstance(node,dict): series=node.get("data")
    req(isinstance(series,str),"v6 data series missing")
    out={}
    for rec in series.split(";"):
        cols=rec.split(",")
        req(len(cols)>=7,"v6 row too short")
        raw=cols[0].strip(); req(len(raw)==8 and raw.isdigit(),"v6 date invalid")
        d=date(int(raw[:4]),int(raw[4:6]),int(raw[6:8]))
        if d not in TARGETS: continue
        req(d not in out,"v6 duplicate date")
        out[d]=(dec(cols[4],f"{code} close"),dec(cols[5],f"{code} volume"),dec(cols[6],f"{code} turnover"))
    return out

def fetch(code,v):
    req(CODE_RE.fullmatch(code),"code invalid")
    url=f"https://d.10jqka.com.cn/v6/line/48_{code[:6]}/01/last1800.js"
    h={"User-Agent":"Mozilla/5.0","Referer":"http://q.10jqka.com.cn","Host":"d.10jqka.com.cn","Cookie":"v="+v}
    r=requests.get(url,headers=h,timeout=12,allow_redirects=False)
    b=r.content; (RAW/f"{code[:6]}.js").write_bytes(b)
    meta={"code":code,"url":url,"http_status":r.status_code,"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
    req(r.status_code==200,f"HTTP {r.status_code} {code}")
    return parse_v6(b,code),meta

def main():
    result={"status":"FAILED_CLOSED","requests":[],"checks":[],"network_calls":0,"hithink_calls":0,"production_state_writes":0,"restore_authority":"NONE","error":None}
    try:
        st=old_state(); kp=known_points(retained_known()); ck=cookie()
        for code in CODES:
            pts,meta=fetch(code,ck); result["requests"].append(meta); result["network_calls"]+=1
            req(all(d in pts for d in TARGETS),f"target dates missing {code}")
            old=state_points(st,code)
            for d in TARGETS[:3]:
                close,_,turn=pts[d]; ec,et=old[d]
                ok=(close==ec and turn==et)
                result["checks"].append({"code":code,"date":d.isoformat(),"scope":"OLD_STATE_OVERLAP","close_exact":close==ec,"turnover_exact":turn==et,"exact":ok})
                req(ok,f"old-state mismatch {code} {d}")
            if code==KNOWN:
                for d in (date(2026,9,9),date(2026,9,10)):
                    close,vol,turn=pts[d]; ec,ev,et=kp[d]
                    ok=(close==ec and vol==ev and turn==et)
                    result["checks"].append({"code":code,"date":d.isoformat(),"scope":"RETAINED_HITHINK","close_exact":close==ec,"volume_exact":vol==ev,"turnover_exact":turn==et,"exact":ok})
                    req(ok,f"HiThink mismatch {code} {d}")
            if code==STUBBORN:
                close,vol,turn=pts[date(2026,9,10)]
                result["stubborn_target"]={"code":code,"date":"2026-09-10","close":str(close),"volume":str(vol),"turnover":str(turn)}
        result["status"]="EXACT_OVERLAP_AND_KNOWN_SOURCE_MATCH"
        rc=0
    except Exception as e:
        result["error"]={"type":type(e).__name__,"message":" ".join(str(e).split())[:800]}; rc=2
    (OUT/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    print(result["status"], result.get("error")); return rc

if __name__=="__main__": raise SystemExit(main())
