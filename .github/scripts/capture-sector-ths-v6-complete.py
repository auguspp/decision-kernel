#!/usr/bin/env python3
"""Complete the frozen 2026-09-10 Sector recovery candidate using retained sources.

Source composition:
- 110 retained successful HiThink histories from the failed bounded recovery;
- 40 already-validated THS v4 public raw files from the later partial capture;
- one validated THS v6 raw file for 884075 from the two-code probe;
- only the remaining 170 identities are fetched from THS v6 last1800.

Candidate only. No production write, signal creation, Research or investment authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests
from akshare.stock_feature import stock_board_industry_ths as ak_ths

from decision_kernel.adapters.hithink import latest_completed_a_share_session, normalize_hithink_calendar
from decision_kernel.adapters.hithink_index import normalize_hithink_completed_index_history, normalize_hithink_industry_catalog
from decision_kernel.identity import canonical_json
from decision_kernel.runtime.sector_radar import SectorPricePoint, SectorPriceSeries
from decision_kernel.runtime.sector_radar_audit import _atomic_bytes, _sha
from decision_kernel.runtime.sector_radar_persistence import load_sector_radar_persistent_bundle
from decision_kernel.runtime.sector_radar_state import (
    SectorRadarStateSourceLineage,
    create_sector_radar_market_state,
    serialize_sector_radar_market_state,
)

REPO = "auguspp/decision-kernel"
SOURCE_WORKFLOW = ".github/workflows/sector-radar-shadow.yml"
AKSHARE_COMMIT = "8e95744b79ae22326308ccd2b4e62650c5b53c55"

HITHINK_SOURCE_RUN = 34566950303
HITHINK_SOURCE_ARTIFACT = 10187281705
HITHINK_SOURCE_DIGEST = "aedf5fc5507fa33c00f316be72c14b50962486961ba7199e097d2628205dc60b"
V4_SOURCE_RUN = 34574796927
V4_SOURCE_ARTIFACT = 10189239372
V4_SOURCE_DIGEST = "98aa1c075bf4f76d3876fe3793d95a3a8cc0702929ce1894fc2d029636133351"
V6_PROBE_RUN = 34575354939
V6_PROBE_ARTIFACT = 10189399695
V6_PROBE_DIGEST = "841580273c7d038d25deca9dc234a7fae8a13984c0e4ec02b1cce36415e6a43b"
EXPECTED_PARENT_RUN = 34364727989
EXPECTED_PARENT_ARTIFACT = 10109790767

TARGET = date(2026, 9, 10)
EXPECTED_RETAINED_HITHINK = 110
EXPECTED_V4_VALID = 40
EXPECTED_V6_PROBE_VALID = 1
EXPECTED_V6_NEW = 170
EXPECTED_PUBLIC_TOTAL = 211
V6_PROBE_CODE = "884075.TI"

SPACING_SECONDS = 1.0
TIMEOUT_SECONDS = 12.0
RETRY_DELAY_SECONDS = 5.0
TRANSIENT = frozenset({502, 503, 504})
MAX_SECOND_ATTEMPTS = 25
MAX_BODY = 4 * 1024 * 1024
SHANGHAI = ZoneInfo("Asia/Shanghai")
CODE_RE = re.compile(r"^(?:881|884)\d{3}\.TI$")

AUTHORITY = {
    "restore_authority": "NONE",
    "production_state_writes": 0,
    "events_created": 0,
    "research_authority": "NONE",
    "human_attention_authority": "NONE",
    "investment_authority": "NONE",
}

class CaptureError(RuntimeError):
    pass

def require(value: bool, message: str) -> None:
    if not value:
        raise CaptureError(message)

def dec(value: Any, field: str) -> Decimal:
    try:
        out = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CaptureError(f"{field} is not numeric") from exc
    require(out.is_finite(), f"{field} is not finite")
    return out

def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_bytes(path, (canonical_json(value) + "\n").encode())

def load_json(path: Path) -> Any:
    require(path.is_file() and not path.is_symlink(), f"missing input {path}")
    require(path.stat().st_size <= 16 * 1024 * 1024, f"input too large {path}")
    return json.loads(path.read_text())

def source_report(source: Path) -> dict[str, Any]:
    report = load_json(source / "capture" / "report.json")
    require(report.get("status") == "FAILED_CLOSED", "HiThink source status changed")
    require(report.get("restore_authority") is False, "HiThink source has restore authority")
    require(report.get("production_state_writes") == 0, "HiThink source wrote production state")
    require(report.get("events_created") == 0, "HiThink source created events")
    parent = report.get("binding", {}).get("request", {}).get("parent", {})
    require(parent.get("run_id") == EXPECTED_PARENT_RUN, "parent run changed")
    require(parent.get("artifact_id") == EXPECTED_PARENT_ARTIFACT, "parent artifact changed")
    return report

def retained_inputs(source: Path, report: dict[str, Any]):
    calendar = catalog = None
    histories: dict[str, Path] = {}
    for row in report.get("requests", []):
        require(isinstance(row, dict), "malformed retained request")
        rf = row.get("response_file")
        if not isinstance(rf, str):
            continue
        p = source / "capture" / rf
        require(p.is_file() and not p.is_symlink(), "retained response missing")
        path = str(row.get("path", ""))
        params = row.get("params", {})
        if path.endswith("/calendar/trading-days"):
            require(calendar is None, "duplicate calendar")
            calendar = load_json(p)
        elif path.endswith("/catalog/ths-index-list"):
            require(catalog is None, "duplicate catalog")
            catalog = load_json(p)
        elif path.endswith("/prices/historical"):
            code = str(params.get("thscode", "")).upper()
            require(code and code not in histories, "duplicate retained history")
            histories[code] = p
    require(calendar is not None and catalog is not None, "calendar/catalog missing")
    require(len(histories) == EXPECTED_RETAINED_HITHINK, "retained history count changed")
    return calendar, catalog, histories

def parse_day(raw: str, code: str) -> date:
    raw = raw.strip()
    require(len(raw) == 8 and raw.isdigit(), f"date invalid {code}")
    return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))

def parse_v4(body: bytes, code: str, needed: tuple[date, ...]):
    require(len(body) <= MAX_BODY, f"v4 body too large {code}")
    text = body.decode("utf-8")
    start = text.find("{")
    require(start >= 0, f"v4 object missing {code}")
    try:
        payload = ak_ths.demjson.decode(text[start:-1])
    except Exception as exc:
        raise CaptureError(f"v4 parse failed {code}") from exc
    series = payload.get("data") if isinstance(payload, dict) else None
    require(isinstance(series, str), f"v4 data missing {code}")
    wanted = set(needed)
    points = {}
    for rec in series.split(";"):
        cols = rec.split(",")
        require(len(cols) in (11, 12), f"v4 row width {code}")
        d = parse_day(cols[0], code)
        if d not in wanted:
            continue
        require(d not in points, f"v4 duplicate date {code}")
        points[d] = (dec(cols[4], f"{code}.{d}.close"), dec(cols[5], f"{code}.{d}.volume"), dec(cols[6], f"{code}.{d}.turnover"))
    require(set(points) == wanted, f"v4 needed dates missing {code}")
    return points

def parse_v6(body: bytes, code: str, needed: tuple[date, ...]):
    require(len(body) <= MAX_BODY, f"v6 body too large {code}")
    text = body.decode("utf-8")
    start = text.find("{")
    require(start >= 0, f"v6 object missing {code}")
    try:
        payload = json.loads(text[start:-1])
    except json.JSONDecodeError as exc:
        raise CaptureError(f"v6 parse failed {code}") from exc
    series = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(series, str) and isinstance(payload, dict):
        node = payload.get("48_" + code[:6])
        if isinstance(node, dict):
            series = node.get("data")
    require(isinstance(series, str), f"v6 data missing {code}")
    wanted = set(needed)
    points = {}
    for rec in series.split(";"):
        cols = rec.split(",")
        require(len(cols) >= 7, f"v6 row width {code}")
        d = parse_day(cols[0], code)
        if d not in wanted:
            continue
        require(d not in points, f"v6 duplicate date {code}")
        points[d] = (dec(cols[4], f"{code}.{d}.close"), dec(cols[5], f"{code}.{d}.volume"), dec(cols[6], f"{code}.{d}.turnover"))
    require(set(points) == wanted, f"v6 needed dates missing {code}")
    return points

def cookie() -> str:
    js = ak_ths.py_mini_racer.MiniRacer()
    js.eval(ak_ths._get_file_content_ths("ths.js"))
    value = js.call("v")
    require(isinstance(value, str) and value, "THS cookie failed")
    return value

def v6_get(code: str, value: str, attempts: Path, attempt: int):
    require(CODE_RE.fullmatch(code) is not None, f"v6 identity rejected {code}")
    url = f"https://d.10jqka.com.cn/v6/line/48_{code[:6]}/01/last1800.js"
    headers = {"User-Agent":"Mozilla/5.0", "Referer":"http://q.10jqka.com.cn", "Host":"d.10jqka.com.cn", "Cookie":"v=" + value}
    started = datetime.now(tz=SHANGHAI)
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS, allow_redirects=False)
    except requests.RequestException as exc:
        raise CaptureError(f"v6 request failed {code}: {type(exc).__name__}") from exc
    finished = datetime.now(tz=SHANGHAI)
    body = response.content
    require(len(body) <= MAX_BODY, f"v6 response too large {code}")
    attempts.mkdir(parents=True, exist_ok=True)
    name = f"{code[:6]}-attempt{attempt}.js"
    _atomic_bytes(attempts / name, body)
    return body, {
        "code":code, "attempt":attempt, "url":url, "http_status":response.status_code,
        "started_at":started.isoformat(), "finished_at":finished.isoformat(),
        "bytes":len(body), "sha256":hashlib.sha256(body).hexdigest(),
        "attempt_raw_file":f"attempts/{name}",
    }
def valid_v4_raw(prior: Path) -> dict[str, Path]:
    receipt = load_json(prior / "receipt.json")
    require(receipt.get("status") == "FAILED_CLOSED", "v4 source receipt status changed")
    codes = set()
    for row in receipt.get("public_reused_raw", []):
        codes.add(str(row.get("code", "")).upper())
    for code in receipt.get("public_new_success_codes", []):
        codes.add(str(code).upper())
    require(len(codes) == EXPECTED_V4_VALID, f"v4 valid count changed {len(codes)}")
    out = {}
    for code in sorted(codes):
        require(CODE_RE.fullmatch(code) is not None, f"v4 identity invalid {code}")
        p = prior / "raw" / f"{code[:6]}-2026.js"
        require(p.is_file() and not p.is_symlink(), f"v4 valid raw missing {code}")
        out[code] = p
    return out

def v6_probe_raw(probe: Path) -> Path:
    result = load_json(probe / "result.json")
    require(result.get("status") == "EXACT_OVERLAP_AND_KNOWN_SOURCE_MATCH", "v6 probe not accepted")
    p = probe / "raw" / "884075.js"
    require(p.is_file() and not p.is_symlink(), "v6 probe raw missing")
    return p

def compose(source: Path, root: Path, capture_mode: bool, prior_v4: Path | None = None, probe_v6: Path | None = None, cv: str | None = None):
    report = source_report(source)
    calendar_env, catalog_env, retained = retained_inputs(source, report)
    bundle = load_sector_radar_persistent_bundle(
        source / "input", expected_repository=REPO, expected_workflow=SOURCE_WORKFLOW,
        expected_parent_hint_mapping_hash=report["binding"]["request"]["parent"]["parent_hint_mapping_hash"],
    )
    state = bundle.market_state
    sessions = normalize_hithink_calendar(calendar_env)
    observed_at = datetime.fromisoformat(report["observed_at"])
    target = latest_completed_a_share_session(sessions, observed_at=observed_at)
    require(target == TARGET, f"target changed {target}")
    require(state.sessions[-1] == date(2026,9,9), "frozen state end changed")
    overlap = state.sessions[-3:]
    needed = (*overlap, target)
    catalog = normalize_hithink_industry_catalog(catalog_env)
    require(catalog.catalog_hash == state.catalog_hash, "catalog hash changed")
    all_codes = tuple(x.thscode for x in state.series)
    public_codes = tuple(c for c in all_codes if c not in retained)
    require(len(public_codes) == EXPECTED_PUBLIC_TOTAL, "public code count changed")

    if capture_mode:
        require(prior_v4 is not None and probe_v6 is not None and cv is not None, "capture sources missing")
        v4 = valid_v4_raw(prior_v4)
        p75 = v6_probe_raw(probe_v6)
        require(V6_PROBE_CODE in public_codes and V6_PROBE_CODE not in v4, "v6 probe identity composition changed")
    else:
        v4 = {c: root / "raw-v4" / f"{c[:6]}-2026.js" for c in public_codes if (root / "raw-v4" / f"{c[:6]}-2026.js").is_file()}
        p75 = root / "raw-v6" / "884075.js"
        require(p75.is_file(), "captured 884075 v6 raw missing")
    require(len(v4) == EXPECTED_V4_VALID, "captured v4 count changed")

    reused_v6 = {V6_PROBE_CODE}
    remaining = tuple(c for c in public_codes if c not in v4 and c not in reused_v6)
    require(len(remaining) == EXPECTED_V6_NEW, f"v6 new count changed {len(remaining)}")

    receipt = {
        "schema_version":1, "status":"RECORDING" if capture_mode else "VERIFYING",
        "semantics":"FROZEN_20260910_SECTOR_RECOVERY_MIXED_RETAINED_HITHINK_THS_V4_THS_V6_CANDIDATE_ONLY",
        "sources": {
            "hithink":{"run_id":HITHINK_SOURCE_RUN,"artifact_id":HITHINK_SOURCE_ARTIFACT,"digest":HITHINK_SOURCE_DIGEST,"history_count":EXPECTED_RETAINED_HITHINK},
            "ths_v4":{"run_id":V4_SOURCE_RUN,"artifact_id":V4_SOURCE_ARTIFACT,"digest":V4_SOURCE_DIGEST,"valid_count":EXPECTED_V4_VALID},
            "ths_v6_probe":{"run_id":V6_PROBE_RUN,"artifact_id":V6_PROBE_ARTIFACT,"digest":V6_PROBE_DIGEST,"code":V6_PROBE_CODE},
        },
        "target_session":TARGET.isoformat(), "overlap_sessions":[x.isoformat() for x in overlap],
        "v6_new_identity_count":0, "v6_http_attempts":[], "v6_second_attempt_count":0,
        "overlap_checks":[], "candidate_state_hash":None, "candidate_state_sha256":None,
        "event_ledger_sha256":_sha((source/"input/candidate-events.json").read_bytes()),
        "hithink_new_requests":0, **AUTHORITY, "error":None,
    }
    raw_v4 = root / "raw-v4"; raw_v6 = root / "raw-v6"; attempts = root / "attempts"
    if capture_mode:
        raw_v4.mkdir(parents=True); raw_v6.mkdir(parents=True)
        for code,p in v4.items():
            _atomic_bytes(raw_v4 / f"{code[:6]}-2026.js", p.read_bytes())
        _atomic_bytes(raw_v6 / "884075.js", p75.read_bytes())

    old_by = {x.thscode:x for x in state.series}
    completed = {}
    for code in all_codes:
        old = old_by[code]
        old_points = {d:(c,t) for d,c,t in zip(state.sessions,old.closes,old.turnovers,strict=True)}
        if code in retained:
            env = load_json(retained[code])
            hist = normalize_hithink_completed_index_history(env, thscode=code, sessions=sessions, observed_at=observed_at)
            require(hist.response_session == hist.expected_latest_session == TARGET, f"retained target mismatch {code}")
            by = {p.as_of.date():(p.close,p.volume,p.turnover) for p in hist.points}
            require(all(d in by for d in needed), f"retained dates missing {code}")
            kind = "RETAINED_HITHINK"
        elif code in v4:
            p = (raw_v4 / f"{code[:6]}-2026.js") if not capture_mode else (raw_v4 / f"{code[:6]}-2026.js")
            by = parse_v4(p.read_bytes(), code, needed)
            kind = "PUBLIC_THS_V4"
        else:
            canonical = raw_v6 / f"{code[:6]}.js"
            if code == V6_PROBE_CODE:
                by = parse_v6((raw_v6 / "884075.js").read_bytes(), code, needed)
                kind = "PUBLIC_THS_V6_PROBE_REUSED"
            else:
                if capture_mode:
                    success = False
                    for attempt in (1,2):
                        if attempt == 2:
                            require(receipt["v6_second_attempt_count"] < MAX_SECOND_ATTEMPTS, "v6 second-attempt budget exhausted")
                            receipt["v6_second_attempt_count"] += 1
                            save_json(root / "receipt.partial.json", receipt)
                            time.sleep(RETRY_DELAY_SECONDS)
                        body,meta = v6_get(code,cv,attempts,attempt)
                        receipt["v6_http_attempts"].append(meta); save_json(root/"receipt.partial.json",receipt)
                        if meta["http_status"] == 200:
                            _atomic_bytes(canonical,body); success=True; break
                        if meta["http_status"] not in TRANSIENT or attempt == 2:
                            raise CaptureError(f"v6 HTTP {meta['http_status']} {code} attempt={attempt}")
                    require(success,f"v6 identity failed {code}")
                    receipt["v6_new_identity_count"] += 1; save_json(root/"receipt.partial.json",receipt)
                    if receipt["v6_new_identity_count"] < EXPECTED_V6_NEW: time.sleep(SPACING_SECONDS)
                require(canonical.is_file(), f"v6 canonical raw missing {code}")
                by = parse_v6(canonical.read_bytes(),code,needed)
                kind = "PUBLIC_THS_V6"
        for d in overlap:
            close,_,turn = by[d]; ec,et = old_points[d]
            exact = close == ec and turn == et
            receipt["overlap_checks"].append({"code":code,"source_kind":kind,"session":d.isoformat(),"close_exact":close==ec,"turnover_exact":turn==et,"exact":exact})
            require(exact,f"overlap mismatch {code} {d}")
        close,_,turn = by[TARGET]; completed[code]=(close,turn)
    require(len(completed)==len(all_codes),"candidate coverage incomplete")
    if capture_mode:
        require(receipt["v6_new_identity_count"] == EXPECTED_V6_NEW,"v6 new identity count incomplete")
        require(receipt["v6_second_attempt_count"] <= MAX_SECOND_ATTEMPTS,"v6 retry cap exceeded")

    series=[]
    for old in state.series:
        pts=tuple(SectorPricePoint(d,c,t) for d,c,t in zip(state.sessions,old.closes,old.turnovers,strict=True))
        c,t=completed[old.thscode]; pts += (SectorPricePoint(TARGET,c,t),)
        series.append(SectorPriceSeries(old.thscode,old.name,pts))
    parent=report["binding"]["request"]["parent"]
    lineage=(*state.source_lineage, SectorRadarStateSourceLineage("RECOVERY_PARENT_STATE",parent["run_id"],parent["artifact_id"],parent["artifact_digest"],bundle.manifest.last_result_hash))
    candidate=create_sector_radar_market_state(
        catalog=catalog, benchmark=series[0], broad_series=series[1:1+len(state.broad_identities)],
        granular_series=series[1+len(state.broad_identities):], created_at=observed_at,
        source="RECOVERY_CANDIDATE_RETAINED_HITHINK_THS_V4_V6_NOT_RESTORE_AUTHORITY", source_lineage=lineage,
    )
    cb=serialize_sector_radar_market_state(candidate).encode(); eb=(source/"input/candidate-events.json").read_bytes()
    receipt.update(status="RECOVERY_CANDIDATE_REVIEW_REQUIRED", candidate_state_hash=candidate.state_hash,
                   candidate_state_sha256=hashlib.sha256(cb).hexdigest(), v6_new_identity_count=(receipt["v6_new_identity_count"] if capture_mode else EXPECTED_V6_NEW))
    return cb,eb,receipt

def capture(source:Path, prior_v4:Path, probe_v6:Path, out:Path):
    out.mkdir(parents=True,exist_ok=False)
    try:
        cb,eb,r=compose(source,out,True,prior_v4,probe_v6,cookie())
        _atomic_bytes(out/"candidate-state.json",cb); _atomic_bytes(out/"candidate-events.json",eb); save_json(out/"receipt.json",r)
        print(f"status={r['status']} v6_new={r['v6_new_identity_count']} attempts={len(r['v6_http_attempts'])} candidate={r['candidate_state_hash']}")
        return 0
    except Exception as exc:
        p=out/"receipt.partial.json"
        r=load_json(p) if p.is_file() else {"schema_version":1,"status":"FAILED_CLOSED","v6_http_attempts":[],"v6_new_identity_count":0,"v6_second_attempt_count":0,**AUTHORITY}
        r["status"]="FAILED_CLOSED"; r["error"]={"type":type(exc).__name__,"message":" ".join(str(exc).split())[:1000]}; save_json(out/"receipt.json",r)
        print(f"FAILED_CLOSED: {type(exc).__name__}: {exc}",file=sys.stderr); return 2

def verify(source:Path, cap:Path, out:Path):
    out.mkdir(parents=True,exist_ok=False)
    try:
        saved=load_json(cap/"receipt.json"); require(saved.get("status")=="RECOVERY_CANDIDATE_REVIEW_REQUIRED","capture not complete")
        cb,eb,r=compose(source,cap,False)
        require(cb==(cap/"candidate-state.json").read_bytes(),"candidate bytes differ")
        require(eb==(cap/"candidate-events.json").read_bytes(),"event bytes differ")
        require(r["candidate_state_hash"]==saved["candidate_state_hash"],"candidate hash differs")
        result={"schema_version":1,"status":"OFFLINE_REBUILD_EXACT_MATCH","candidate_state_hash":r["candidate_state_hash"],"candidate_state_sha256":r["candidate_state_sha256"],"event_ledger_sha256":r["event_ledger_sha256"],"network_calls":0,**AUTHORITY}
        save_json(out/"verification.json",result); print(result["status"],result["candidate_state_hash"]); return 0
    except Exception as exc:
        save_json(out/"verification.json",{"schema_version":1,"status":"FAILED_CLOSED","network_calls":0,"error":{"type":type(exc).__name__,"message":" ".join(str(exc).split())[:1000]},**AUTHORITY}); return 2

def main():
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest="cmd",required=True)
    c=s.add_parser("capture"); c.add_argument("--source",type=Path,required=True); c.add_argument("--prior-v4",type=Path,required=True); c.add_argument("--probe-v6",type=Path,required=True); c.add_argument("--output",type=Path,required=True)
    v=s.add_parser("verify"); v.add_argument("--source",type=Path,required=True); v.add_argument("--capture",type=Path,required=True); v.add_argument("--output",type=Path,required=True)
    a=p.parse_args(); return capture(a.source,a.prior_v4,a.probe_v6,a.output) if a.cmd=="capture" else verify(a.source,a.capture,a.output)
if __name__=="__main__": raise SystemExit(main())
