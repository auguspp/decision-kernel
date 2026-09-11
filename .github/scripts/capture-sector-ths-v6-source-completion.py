#!/usr/bin/env python3
"""Finish frozen Sector source coverage using retained bytes plus THS v6.

Starts from 292 exact identities retained in run 34591191296 and one accepted
884287.TI v6 probe. Only the remaining 28 identities may access THS v6.
One request per identity, no retry. This establishes source coverage only; it
creates no candidate state and has no production/Research/Odds/Action authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import requests
from akshare.stock_feature import stock_board_industry_ths as ak_ths

PRIOR_RUN = 34591191296
PRIOR_ARTIFACT = 10195718219
PRIOR_DIGEST = "81b9d3ca0861c47a10fad5bcba44a6e4d4de38c1be8bd6d907f74c88996a9522"
PROBE_RUN = 34592027908
PROBE_ARTIFACT = 10196014989
PROBE_DIGEST = "8d7459dc28878c0189d3a98388802d2587e0517d20ae9864f068d93763bfe160"
PROBE_RAW_SHA256 = "84f0df84d5a0a9e910e9e37f756396d3cbfff2e2713ff50b6d02691c6ab8aa2e"
PROBE_CODE = "884287.TI"
TARGETS = (date(2026, 9, 7), date(2026, 9, 8), date(2026, 9, 9), date(2026, 9, 10))
EXPECTED_TOTAL = 321
EXPECTED_RETAINED = 110
EXPECTED_PUBLIC = 211
EXPECTED_PRIOR_EXACT = 292
EXPECTED_PRIOR_PUBLIC = 182
EXPECTED_START_EXACT = 293
EXPECTED_START_PUBLIC = 183
EXPECTED_NEW = 28
EXPECTED_PRIOR_CHECKS = 876
SPACING_SECONDS = 1.0
TIMEOUT_SECONDS = 12.0
MAX_BODY = 4 * 1024 * 1024

AUTHORITY = {
    "hithink_new_requests": 0,
    "production_state_writes": 0,
    "events_created": 0,
    "restore_authority": "NONE",
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
        raise CaptureError(f"{field} not numeric") from exc
    require(out.is_finite(), f"{field} not finite")
    return out


def load_json(path: Path) -> Any:
    require(path.is_file() and not path.is_symlink(), f"missing input {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def copy_raw(src: Path, dst: Path) -> None:
    require(src.is_file() and not src.is_symlink(), f"missing raw {src}")
    shutil.copyfile(src, dst)


def cookie() -> str:
    js = ak_ths.py_mini_racer.MiniRacer()
    js.eval(ak_ths._get_file_content_ths("ths.js"))
    value = js.call("v")
    require(isinstance(value, str) and value, "THS cookie failed")
    return value


def parse_v6(body: bytes, code: str) -> dict[date, tuple[Decimal, Decimal, Decimal]]:
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
    out = {}
    for record in series.split(";"):
        cols = record.split(",")
        require(len(cols) >= 7, f"v6 row too short {code}")
        raw = cols[0].strip()
        require(len(raw) == 8 and raw.isdigit(), f"v6 date invalid {code}")
        d = date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
        if d not in TARGETS:
            continue
        require(d not in out, f"v6 duplicate date {code}")
        out[d] = (
            dec(cols[4], f"{code}.{d}.close"),
            dec(cols[5], f"{code}.{d}.volume"),
            dec(cols[6], f"{code}.{d}.turnover"),
        )
    require(set(out) == set(TARGETS), f"v6 target dates missing {code}")
    return out


def state_input(source: Path):
    state = load_json(source / "input" / "market-state.json")
    sessions = [date.fromisoformat(x) for x in state["sessions"]]
    require(TARGETS[0] in sessions and TARGETS[1] in sessions and TARGETS[2] in sessions, "overlap sessions missing")
    allcodes = tuple(str(row["thscode"]) for row in state["series"])
    require(len(allcodes) == EXPECTED_TOTAL and len(set(allcodes)) == EXPECTED_TOTAL, "state identity count changed")
    rows = {str(row["thscode"]): row for row in state["series"]}
    return sessions, allcodes, rows


def old_points(sessions: list[date], row: dict[str, Any]) -> dict[date, tuple[Decimal, Decimal]]:
    return {
        d: (dec(c, f"{row['thscode']}.{d}.state_close"), dec(t, f"{row['thscode']}.{d}.state_turnover"))
        for d, c, t in zip(sessions, row["closes"], row["turnovers"], strict=True)
    }


def validate_prior(prior: Path):
    receipt = load_json(prior / "receipt.json")
    require(receipt.get("status") == "FAILED_CLOSED", "prior status changed")
    require(receipt.get("semantics") == "FROZEN_SECTOR_RECOVERY_THS_HTTP_V4_FINAL_CONTINUATION_CANDIDATE_ONLY", "prior semantics changed")
    require(receipt.get("starting_exact_coverage") == 279, "prior start coverage changed")
    require(receipt.get("new_identity_count") == 13, "prior admitted count changed")
    require(receipt.get("network_calls") == 14, "prior request count changed")
    require(receipt.get("retry_count") == 0, "prior retry count changed")
    for key, expected in AUTHORITY.items():
        require(receipt.get(key) == expected, f"prior authority changed: {key}")
    error = receipt.get("error") or {}
    require(PROBE_CODE in str(error.get("message", "")), "prior blocker changed")
    checks = receipt.get("overlap_checks")
    require(isinstance(checks, list) and len(checks) == EXPECTED_PRIOR_CHECKS, "prior overlap count changed")
    require(all(isinstance(x, dict) and x.get("exact") is True for x in checks), "prior overlap not exact")
    exact_codes = {str(x.get("code")) for x in checks}
    require(len(exact_codes) == EXPECTED_PRIOR_EXACT, "prior exact identity count changed")
    retained_codes = {str(x.get("code")) for x in checks if x.get("source_kind") == "RETAINED_HITHINK"}
    require(len(retained_codes) == EXPECTED_RETAINED, "prior retained identity count changed")
    public_codes = exact_codes - retained_codes
    require(len(public_codes) == EXPECTED_PRIOR_PUBLIC, "prior public identity count changed")

    rv4, rv6, rv2 = prior / "raw-v4", prior / "raw-v6", prior / "raw-v2"
    require(rv4.is_dir() and rv6.is_dir() and rv2.is_dir(), "prior raw dirs missing")
    v4 = {p.name[:6] + ".TI" for p in rv4.glob("*.js")}
    v6 = {p.name[:6] + ".TI" for p in rv6.glob("*.js")}
    v2 = {p.name[:6] + ".TI" for p in rv2.glob("*.js")}
    require((len(v4), len(v6), len(v2)) == (97, 70, 15), "prior canonical raw counts changed")
    require(v4.isdisjoint(v6) and v4.isdisjoint(v2) and v6.isdisjoint(v2), "prior canonical sources overlap")
    require(v4 | v6 | v2 == public_codes, "prior canonical identity set changed")
    require(PROBE_CODE not in public_codes, "884287 unexpectedly present in prior exact set")
    return retained_codes, v4, v6, v2


def validate_probe(probe: Path) -> bytes:
    result = load_json(probe / "result.json")
    require(result.get("status") == "EXACT_OVERLAP_V6_AVAILABLE", "884287 v6 probe not accepted")
    require(result.get("code") == PROBE_CODE, "884287 probe identity changed")
    require(result.get("network_calls") == 1 and result.get("retries") == 0, "884287 probe request policy changed")
    require(result.get("hithink_calls") == 0, "884287 probe made HiThink call")
    require(result.get("production_state_writes") == 0 and result.get("events_created") == 0, "884287 probe wrote state/event")
    request = result.get("request") or {}
    require(request.get("http_status") == 200, "884287 probe HTTP status changed")
    checks = result.get("checks")
    require(isinstance(checks, list) and len(checks) == 3 and all(x.get("exact") is True for x in checks), "884287 probe overlap changed")
    raw = probe / "raw" / "884287.js"
    require(raw.is_file(), "884287 probe raw missing")
    body = raw.read_bytes()
    require(hashlib.sha256(body).hexdigest() == PROBE_RAW_SHA256, "884287 probe raw hash changed")
    return body


def seed(prior: Path, probe: Path, out: Path):
    retained, v4, v6, v2 = validate_prior(prior)
    rv4, rv6, rv2 = out / "raw-v4", out / "raw-v6", out / "raw-v2"
    rv4.mkdir(); rv6.mkdir(); rv2.mkdir()
    for p in sorted((prior / "raw-v4").glob("*.js")): copy_raw(p, rv4 / p.name)
    for p in sorted((prior / "raw-v6").glob("*.js")): copy_raw(p, rv6 / p.name)
    for p in sorted((prior / "raw-v2").glob("*.js")): copy_raw(p, rv2 / p.name)
    body = validate_probe(probe)
    (rv6 / "884287.js").write_bytes(body)
    v6.add(PROBE_CODE)
    require(len(v4 | v6 | v2) == EXPECTED_START_PUBLIC, "starting public coverage changed")
    return retained, v4, v6, v2


def fetch_v6(code: str, value: str, out: Path):
    url = f"https://d.10jqka.com.cn/v6/line/48_{code[:6]}/01/last1800.js"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "http://q.10jqka.com.cn", "Host": "d.10jqka.com.cn", "Cookie": "v=" + value}
    started = datetime.now().astimezone()
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS, allow_redirects=False)
        body, status, request_error = response.content, response.status_code, None
    except requests.RequestException as exc:
        body, status, request_error = b"", None, type(exc).__name__
    finished = datetime.now().astimezone()
    require(len(body) <= MAX_BODY, f"v6 response too large {code}")
    attempts = out / "attempts"; attempts.mkdir(exist_ok=True)
    name = f"{code[:6]}-v6-attempt1.js"; (attempts / name).write_bytes(body)
    return body, {
        "code": code, "transport": "THS_V6_HTTPS", "attempt": 1, "retry": False,
        "url": url, "http_status": status, "request_error": request_error,
        "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
        "started_at": started.isoformat(), "finished_at": finished.isoformat(),
        "attempt_raw_file": f"attempts/{name}",
    }


def capture(source: Path, prior: Path, probe: Path, out: Path) -> int:
    out.mkdir(parents=True, exist_ok=False)
    receipt = {
        "schema_version": 1,
        "status": "RECORDING",
        "semantics": "FROZEN_SECTOR_RECOVERY_THS_V6_SOURCE_COMPLETION_ONLY",
        "prior_v4_continuation": {"run_id": PRIOR_RUN, "artifact_id": PRIOR_ARTIFACT, "digest": PRIOR_DIGEST},
        "v6_884287_probe": {"run_id": PROBE_RUN, "artifact_id": PROBE_ARTIFACT, "digest": PROBE_DIGEST, "raw_sha256": PROBE_RAW_SHA256},
        "starting_exact_coverage": EXPECTED_START_EXACT,
        "starting_public_exact_coverage": EXPECTED_START_PUBLIC,
        "requested_identity_count": EXPECTED_NEW,
        "new_identity_count": 0,
        "network_calls": 0,
        "retry_count": 0,
        "http_attempts": [],
        "overlap_checks": [],
        **AUTHORITY,
        "error": None,
    }
    try:
        sessions, allcodes, rows = state_input(source)
        retained, v4, v6, v2 = seed(prior, probe, out)
        public = tuple(code for code in allcodes if code not in retained)
        require(len(public) == EXPECTED_PUBLIC, "public identity count changed")
        canonical = v4 | v6 | v2
        require(canonical.issubset(set(public)), "canonical public set invalid")
        remaining = tuple(code for code in public if code not in canonical)
        require(len(remaining) == EXPECTED_NEW, f"remaining count {len(remaining)}")
        value = cookie()
        for code in remaining:
            body, meta = fetch_v6(code, value, out)
            receipt["http_attempts"].append(meta); receipt["network_calls"] += 1
            save_json(out / "receipt.partial.json", receipt)
            require(meta["request_error"] is None, f"v6 request failed {code}")
            require(meta["http_status"] == 200, f"v6 HTTP {meta['http_status']} {code}")
            points = parse_v6(body, code)
            old = old_points(sessions, rows[code])
            for d in TARGETS[:3]:
                close, _volume, turnover = points[d]; exp_close, exp_turnover = old[d]
                exact = close == exp_close and turnover == exp_turnover
                receipt["overlap_checks"].append({
                    "code": code, "source_kind": "PUBLIC_THS_V6_NEW", "session": d.isoformat(),
                    "close_exact": close == exp_close, "turnover_exact": turnover == exp_turnover, "exact": exact,
                })
                require(exact, f"overlap mismatch {code} {d}")
            (out / "raw-v6" / f"{code[:6]}.js").write_bytes(body)
            v6.add(code); receipt["new_identity_count"] += 1
            save_json(out / "receipt.partial.json", receipt)
            time.sleep(SPACING_SECONDS)

        require(receipt["network_calls"] == EXPECTED_NEW and receipt["new_identity_count"] == EXPECTED_NEW, "completion counts incomplete")
        require(len(v4 | v6 | v2) == EXPECTED_PUBLIC, "public source coverage incomplete")
        receipt.update(
            status="SOURCE_COVERAGE_EXACT_COMPLETE",
            final_exact_coverage=EXPECTED_TOTAL,
            final_public_exact_coverage=EXPECTED_PUBLIC,
            final_v4_count=len(v4), final_v6_count=len(v6), final_v2_count=len(v2),
        )
        save_json(out / "receipt.json", receipt)
        print(f"{receipt['status']} exact={receipt['final_exact_coverage']} v4={len(v4)} v6={len(v6)} v2={len(v2)}")
        return 0
    except Exception as exc:
        receipt["status"] = "FAILED_CLOSED"
        receipt["error"] = {"type": type(exc).__name__, "message": " ".join(str(exc).split())[:1000]}
        save_json(out / "receipt.json", receipt)
        print(f"FAILED_CLOSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return capture(args.source, args.prior, args.probe, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
