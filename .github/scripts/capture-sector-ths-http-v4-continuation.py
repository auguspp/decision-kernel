#!/usr/bin/env python3
"""Continue the frozen 2026-09-10 Sector candidate via THS plain-HTTP v4.

Reuse:
- 110 retained HiThink histories from the failed bounded recovery (no new HiThink);
- 112 public THS identities already exact-overlap-qualified in run 34576290791;
- 884189.TI exact-overlap-qualified over the mature plain-HTTP v4 route in run 34588879476.

Only the remaining 98 exact identities access the public THS CDN. Each identity gets
one request, no retry. Candidate only: no production/current-state/event/Research/Odds/
Action authority.
"""
from __future__ import annotations

import argparse
import hashlib
import runpy
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import requests

D = runpy.run_path(".github/scripts/capture-sector-ths-dual-complete.py")
CaptureError = D["CaptureError"]
require = D["require"]
save_json = D["save_json"]
load_json = D["load_json"]
source_report = D["source_report"]
retained_inputs = D["retained_inputs"]
parse_v4 = D["parse_v4"]
parse_v6 = D["parse_v6"]
cookie = D["cookie"]
REPO = D["REPO"]
SOURCE_WORKFLOW = D["SOURCE_WORKFLOW"]
TARGET = D["TARGET"]
CODE_RE = D["CODE_RE"]
MAX_BODY = D["MAX_BODY"]
SHANGHAI = D["SHANGHAI"]
AUTHORITY = D["AUTHORITY"]

from decision_kernel.adapters.hithink import latest_completed_a_share_session, normalize_hithink_calendar
from decision_kernel.adapters.hithink_index import (
    normalize_hithink_completed_index_history,
    normalize_hithink_industry_catalog,
)
from decision_kernel.runtime.sector_radar import SectorPricePoint, SectorPriceSeries
from decision_kernel.runtime.sector_radar_audit import _atomic_bytes, _sha
from decision_kernel.runtime.sector_radar_persistence import load_sector_radar_persistent_bundle
from decision_kernel.runtime.sector_radar_state import (
    SectorRadarStateSourceLineage,
    create_sector_radar_market_state,
    serialize_sector_radar_market_state,
)

PRIOR_DUAL_RUN = 34576290791
PRIOR_DUAL_ARTIFACT = 10189873815
PRIOR_DUAL_DIGEST = "50d318ad7cae65471d51e75896eed1b9b6551b24b572f2286cb32bfc50e8171f"
HTTP_V4_PROBE_RUN = 34588879476
HTTP_V4_PROBE_ARTIFACT = 10194766390
HTTP_V4_PROBE_DIGEST = "59b36691d666b48917b13ff0ae853988267292ae6a3b9b5e5abf6863fea3b8aa"
HTTP_V4_PROBE_RAW_SHA256 = "5cafe210b8ebd3f5a30546aa01d62329f49e1594f8d13820c9d85182b08c2d73"

EXPECTED_HITHINK = 110
EXPECTED_PUBLIC_TOTAL = 211
EXPECTED_PRIOR_PUBLIC = 112
EXPECTED_STARTING_PUBLIC = 113
EXPECTED_STARTING_TOTAL = 223
EXPECTED_NEW = 98
EXPECTED_PRIOR_OVERLAP_CHECKS = 666
SPACING_SECONDS = 1.25
TIMEOUT_SECONDS = 12.0
HTTP_V4_PROBE_CODE = "884189.TI"
PRIOR_ERROR_MARKER = "884189.TI"


def validate_prior_dual(prior: Path) -> tuple[set[str], set[str]]:
    receipt = load_json(prior / "receipt.json")
    require(receipt.get("status") == "FAILED_CLOSED", "prior dual status changed")
    require(
        receipt.get("semantics") == "FROZEN_SECTOR_RECOVERY_THS_DUAL_BOUNDED_FALLBACK_CANDIDATE_ONLY",
        "prior dual semantics changed",
    )
    require(receipt.get("hithink_new_requests") == 0, "prior dual made new HiThink requests")
    require(receipt.get("production_state_writes") == 0, "prior dual wrote production state")
    require(receipt.get("events_created") == 0, "prior dual created events")
    require(receipt.get("restore_authority") == "NONE", "prior dual restore authority changed")
    require(receipt.get("research_authority") == "NONE", "prior dual research authority changed")
    require(receipt.get("investment_authority") == "NONE", "prior dual investment authority changed")
    err = receipt.get("error") or {}
    require(PRIOR_ERROR_MARKER in str(err.get("message", "")), "prior dual blocker changed")

    checks = receipt.get("overlap_checks")
    require(isinstance(checks, list) and len(checks) == EXPECTED_PRIOR_OVERLAP_CHECKS, "prior overlap count changed")
    require(all(isinstance(x, dict) and x.get("exact") is True for x in checks), "prior overlap not exact")
    checked_codes = {str(x.get("code")) for x in checks}
    require(len(checked_codes) == 222, "prior exact identity count changed")
    public_checked = {
        str(x.get("code"))
        for x in checks
        if str(x.get("source_kind", "")).startswith("PUBLIC_THS_")
    }
    require(len(public_checked) == EXPECTED_PRIOR_PUBLIC, "prior public exact identity count changed")

    rv4 = prior / "raw-v4"
    rv6 = prior / "raw-v6"
    require(rv4.is_dir() and rv6.is_dir(), "prior raw dirs missing")
    v4 = {p.name[:6] + ".TI" for p in rv4.glob("*.js")}
    v6 = {p.name[:6] + ".TI" for p in rv6.glob("*.js")}
    require(len(v4) == 42 and len(v6) == 70, "prior canonical raw counts changed")
    require(v4.isdisjoint(v6), "prior canonical source overlap")
    require(v4 | v6 == public_checked, "prior canonical raw identity set changed")
    return v4, v6


def validate_probe(probe: Path) -> bytes:
    result = load_json(probe / "result.json")
    require(result.get("status") == "EXACT_OVERLAP_HTTP_V4_AVAILABLE", "884189 HTTP-v4 probe not accepted")
    require(result.get("code") == HTTP_V4_PROBE_CODE, "884189 probe identity changed")
    require(result.get("transport") == "THS_V4_HTTP", "884189 probe transport changed")
    require(result.get("http_status") == 200, "884189 probe HTTP status changed")
    require(result.get("network_calls") == 1, "884189 probe request count changed")
    require(result.get("hithink_calls") == 0, "884189 probe made HiThink call")
    require(result.get("production_state_writes") == 0, "884189 probe wrote production state")
    require(result.get("events_created") == 0, "884189 probe created events")
    checks = result.get("checks")
    require(isinstance(checks, list) and len(checks) == 3, "884189 probe overlap count changed")
    require(all(isinstance(x, dict) and x.get("exact") is True for x in checks), "884189 probe overlap not exact")
    raw = probe / "884189.js"
    require(raw.is_file() and not raw.is_symlink(), "884189 probe raw missing")
    body = raw.read_bytes()
    require(hashlib.sha256(body).hexdigest() == HTTP_V4_PROBE_RAW_SHA256, "884189 probe raw hash changed")
    return body


def seed_sources(prior: Path, probe: Path, out: Path) -> tuple[set[str], set[str]]:
    v4, v6 = validate_prior_dual(prior)
    rv4 = out / "raw-v4"
    rv6 = out / "raw-v6"
    rv4.mkdir(parents=True)
    rv6.mkdir(parents=True)
    for p in sorted((prior / "raw-v4").glob("*.js")):
        _atomic_bytes(rv4 / p.name, p.read_bytes())
    for p in sorted((prior / "raw-v6").glob("*.js")):
        _atomic_bytes(rv6 / p.name, p.read_bytes())

    require(HTTP_V4_PROBE_CODE not in v4 and HTTP_V4_PROBE_CODE not in v6, "884189 already canonical in prior")
    probe_body = validate_probe(probe)
    _atomic_bytes(rv4 / "884189-2026.js", probe_body)
    v4.add(HTTP_V4_PROBE_CODE)
    require(len(v4 | v6) == EXPECTED_STARTING_PUBLIC, "starting public coverage changed")
    return v4, v6


def existing_sources(out: Path) -> tuple[set[str], set[str]]:
    rv4 = out / "raw-v4"
    rv6 = out / "raw-v6"
    require(rv4.is_dir() and rv6.is_dir(), "canonical raw dirs missing")
    v4 = {p.name[:6] + ".TI" for p in rv4.glob("*.js")}
    v6 = {p.name[:6] + ".TI" for p in rv6.glob("*.js")}
    require(v4.isdisjoint(v6), "canonical source identity ambiguous")
    return v4, v6


def public_http_v4_get(code: str, cookie_value: str, out: Path) -> tuple[bytes, dict[str, Any]]:
    require(CODE_RE.fullmatch(code) is not None, f"identity invalid {code}")
    symbol = code[:6]
    url = f"http://d.10jqka.com.cn/v4/line/bk_{symbol}/01/2026.js"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "http://q.10jqka.com.cn",
        "Host": "d.10jqka.com.cn",
        "Cookie": "v=" + cookie_value,
    }
    started = datetime.now(tz=SHANGHAI)
    request_error = None
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS, allow_redirects=False)
        body = response.content
        status = response.status_code
    except requests.RequestException as exc:
        body = b""
        status = None
        request_error = {"type": type(exc).__name__, "message": " ".join(str(exc).split())[:500]}
    finished = datetime.now(tz=SHANGHAI)
    require(len(body) <= MAX_BODY, f"HTTP-v4 response too large {code}")

    attempts = out / "attempts"
    attempts.mkdir(parents=True, exist_ok=True)
    attempt_name = f"{symbol}-http-v4-attempt1.js"
    _atomic_bytes(attempts / attempt_name, body)
    metadata = {
        "code": code,
        "transport": "THS_V4_HTTP",
        "attempt": 1,
        "retry": False,
        "url": url,
        "http_status": status,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "attempt_raw_file": f"attempts/{attempt_name}",
        "request_error": request_error,
    }
    return body, metadata


def require_http_v4_identity(body: bytes, code: str) -> None:
    symbol = code[:6]
    prefix = f"quotebridge_v4_line_bk_{symbol}_01_2026(".encode()
    require(body.startswith(prefix), f"HTTP-v4 wrapper identity mismatch {code}")


def compose(
    source: Path,
    out: Path,
    capture: bool,
    prior: Path | None = None,
    probe: Path | None = None,
    cookie_value: str | None = None,
):
    report = source_report(source)
    cal_env, cat_env, retained = retained_inputs(source, report)
    bundle = load_sector_radar_persistent_bundle(
        source / "input",
        expected_repository=REPO,
        expected_workflow=SOURCE_WORKFLOW,
        expected_parent_hint_mapping_hash=report["binding"]["request"]["parent"]["parent_hint_mapping_hash"],
    )
    state = bundle.market_state
    sessions = normalize_hithink_calendar(cal_env)
    observed = datetime.fromisoformat(report["observed_at"])
    target = latest_completed_a_share_session(sessions, observed_at=observed)
    require(target == TARGET, "target changed")
    require(state.sessions[-1] == date(2026, 9, 9), "state end changed")
    overlap = state.sessions[-3:]
    needed = (*overlap, target)
    catalog = normalize_hithink_industry_catalog(cat_env)
    require(catalog.catalog_hash == state.catalog_hash, "catalog changed")

    allcodes = tuple(x.thscode for x in state.series)
    public = tuple(c for c in allcodes if c not in retained)
    require(len(allcodes) == 321, "total identity count changed")
    require(len(retained) == EXPECTED_HITHINK, "retained HiThink count changed")
    require(len(public) == EXPECTED_PUBLIC_TOTAL, "public identity count changed")

    if capture:
        require(prior is not None and probe is not None and cookie_value is not None, "capture inputs missing")
        v4, v6 = seed_sources(prior, probe, out)
        require((v4 | v6).issubset(set(public)), "starting public identity not in missing set")
        remaining = tuple(c for c in public if c not in v4 and c not in v6)
        require(len(remaining) == EXPECTED_NEW, f"remaining count {len(remaining)}")
    else:
        v4, v6 = existing_sources(out)
        require(v4 | v6 == set(public), "offline public coverage incomplete")
        remaining = ()

    receipt = {
        "schema_version": 1,
        "status": "RECORDING" if capture else "VERIFYING",
        "semantics": "FROZEN_SECTOR_RECOVERY_THS_HTTP_V4_CONTINUATION_CANDIDATE_ONLY",
        "prior_dual": {
            "run_id": PRIOR_DUAL_RUN,
            "artifact_id": PRIOR_DUAL_ARTIFACT,
            "digest": PRIOR_DUAL_DIGEST,
        },
        "http_v4_884189_probe": {
            "run_id": HTTP_V4_PROBE_RUN,
            "artifact_id": HTTP_V4_PROBE_ARTIFACT,
            "digest": HTTP_V4_PROBE_DIGEST,
            "raw_sha256": HTTP_V4_PROBE_RAW_SHA256,
        },
        "target_session": TARGET.isoformat(),
        "starting_exact_coverage": EXPECTED_STARTING_TOTAL,
        "starting_public_exact_coverage": EXPECTED_STARTING_PUBLIC,
        "requested_identity_count": EXPECTED_NEW if capture else 0,
        "new_identity_count": 0,
        "network_calls": 0,
        "retry_count": 0,
        "http_attempts": [],
        "overlap_checks": [],
        "event_ledger_sha256": _sha((source / "input" / "candidate-events.json").read_bytes()),
        "candidate_state_hash": None,
        "candidate_state_sha256": None,
        "hithink_new_requests": 0,
        **AUTHORITY,
        "error": None,
    }

    oldby = {x.thscode: x for x in state.series}
    done: dict[str, tuple[Any, Any]] = {}
    remaining_set = set(remaining)

    for code in allcodes:
        old = oldby[code]
        oldpts = {
            d: (close, turnover)
            for d, close, turnover in zip(state.sessions, old.closes, old.turnovers, strict=True)
        }

        if code in retained:
            env = load_json(retained[code])
            hist = normalize_hithink_completed_index_history(
                env, thscode=code, sessions=sessions, observed_at=observed
            )
            require(hist.response_session == hist.expected_latest_session == TARGET, f"retained target {code}")
            by = {p.as_of.date(): (p.close, p.volume, p.turnover) for p in hist.points}
            source_kind = "RETAINED_HITHINK"
        elif capture and code in remaining_set:
            body, meta = public_http_v4_get(code, cookie_value, out)
            receipt["http_attempts"].append(meta)
            receipt["network_calls"] += 1
            save_json(out / "receipt.partial.json", receipt)
            require(meta["request_error"] is None, f"HTTP-v4 request failed {code}")
            require(meta["http_status"] == 200, f"HTTP-v4 HTTP {meta['http_status']} {code}")
            require_http_v4_identity(body, code)
            by = parse_v4(body, code, needed)
            source_kind = "PUBLIC_THS_V4_HTTP"

            for d in overlap:
                close, _volume, turnover = by[d]
                expected_close, expected_turnover = oldpts[d]
                exact = close == expected_close and turnover == expected_turnover
                receipt["overlap_checks"].append(
                    {
                        "code": code,
                        "source_kind": source_kind,
                        "session": d.isoformat(),
                        "close_exact": close == expected_close,
                        "turnover_exact": turnover == expected_turnover,
                        "exact": exact,
                    }
                )
                require(exact, f"overlap mismatch {code} {d}")

            _atomic_bytes(out / "raw-v4" / f"{code[:6]}-2026.js", body)
            v4.add(code)
            receipt["new_identity_count"] += 1
            save_json(out / "receipt.partial.json", receipt)
            close, _volume, turnover = by[TARGET]
            done[code] = (close, turnover)
            time.sleep(SPACING_SECONDS)
            continue
        else:
            p4 = out / "raw-v4" / f"{code[:6]}-2026.js"
            p6 = out / "raw-v6" / f"{code[:6]}.js"
            require(p4.is_file() ^ p6.is_file(), f"canonical public source ambiguous/missing {code}")
            if p4.is_file():
                by = parse_v4(p4.read_bytes(), code, needed)
                source_kind = "PUBLIC_THS_V4"
            else:
                by = parse_v6(p6.read_bytes(), code, needed)
                source_kind = "PUBLIC_THS_V6"

        require(all(d in by for d in needed), f"needed dates missing {code}")
        for d in overlap:
            close, _volume, turnover = by[d]
            expected_close, expected_turnover = oldpts[d]
            exact = close == expected_close and turnover == expected_turnover
            receipt["overlap_checks"].append(
                {
                    "code": code,
                    "source_kind": source_kind,
                    "session": d.isoformat(),
                    "close_exact": close == expected_close,
                    "turnover_exact": turnover == expected_turnover,
                    "exact": exact,
                }
            )
            require(exact, f"overlap mismatch {code} {d}")
        close, _volume, turnover = by[TARGET]
        done[code] = (close, turnover)

    require(len(done) == len(allcodes), "coverage incomplete")
    if capture:
        require(receipt["network_calls"] == EXPECTED_NEW, "network call count incomplete")
        require(receipt["new_identity_count"] == EXPECTED_NEW, "new identity count incomplete")
        require(len(v4 | v6) == EXPECTED_PUBLIC_TOTAL, "public coverage incomplete")

    series = []
    for old in state.series:
        points = tuple(
            SectorPricePoint(d, close, turnover)
            for d, close, turnover in zip(state.sessions, old.closes, old.turnovers, strict=True)
        )
        close, turnover = done[old.thscode]
        points += (SectorPricePoint(TARGET, close, turnover),)
        series.append(SectorPriceSeries(old.thscode, old.name, points))

    parent = report["binding"]["request"]["parent"]
    lineage = (
        *state.source_lineage,
        SectorRadarStateSourceLineage(
            "RECOVERY_PARENT_STATE",
            parent["run_id"],
            parent["artifact_id"],
            parent["artifact_digest"],
            bundle.manifest.last_result_hash,
        ),
    )
    candidate = create_sector_radar_market_state(
        catalog=catalog,
        benchmark=series[0],
        broad_series=series[1 : 1 + len(state.broad_identities)],
        granular_series=series[1 + len(state.broad_identities) :],
        created_at=observed,
        source="RECOVERY_CANDIDATE_RETAINED_HITHINK_THS_HTTP_V4_NOT_RESTORE_AUTHORITY",
        source_lineage=lineage,
    )
    candidate_bytes = serialize_sector_radar_market_state(candidate).encode()
    event_bytes = (source / "input" / "candidate-events.json").read_bytes()
    receipt.update(
        status="RECOVERY_CANDIDATE_REVIEW_REQUIRED",
        candidate_state_hash=candidate.state_hash,
        candidate_state_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
        final_v4_count=sum(
            1 for c in public if (out / "raw-v4" / f"{c[:6]}-2026.js").is_file()
        ),
        final_v6_count=sum(
            1 for c in public if (out / "raw-v6" / f"{c[:6]}.js").is_file()
        ),
        final_exact_coverage=len(allcodes),
    )
    return candidate_bytes, event_bytes, receipt


def capture(source: Path, prior: Path, probe: Path, out: Path) -> int:
    out.mkdir(parents=True, exist_ok=False)
    try:
        candidate_bytes, event_bytes, receipt = compose(
            source, out, True, prior, probe, cookie()
        )
        _atomic_bytes(out / "candidate-state.json", candidate_bytes)
        _atomic_bytes(out / "candidate-events.json", event_bytes)
        save_json(out / "receipt.json", receipt)
        print(
            f"status={receipt['status']} new={receipt['new_identity_count']} "
            f"calls={receipt['network_calls']} v4={receipt['final_v4_count']} "
            f"v6={receipt['final_v6_count']} candidate={receipt['candidate_state_hash']}"
        )
        return 0
    except Exception as exc:
        partial = out / "receipt.partial.json"
        receipt = (
            load_json(partial)
            if partial.is_file()
            else {
                "schema_version": 1,
                "status": "FAILED_CLOSED",
                "network_calls": 0,
                "http_attempts": [],
                "hithink_new_requests": 0,
                **AUTHORITY,
            }
        )
        receipt["status"] = "FAILED_CLOSED"
        receipt["error"] = {
            "type": type(exc).__name__,
            "message": " ".join(str(exc).split())[:1000],
        }
        save_json(out / "receipt.json", receipt)
        print(f"FAILED_CLOSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


def verify(source: Path, capture_dir: Path, out: Path) -> int:
    out.mkdir(parents=True, exist_ok=False)
    try:
        saved = load_json(capture_dir / "receipt.json")
        require(saved.get("status") == "RECOVERY_CANDIDATE_REVIEW_REQUIRED", "capture incomplete")
        candidate_bytes, event_bytes, rebuilt = compose(source, capture_dir, False)
        require(candidate_bytes == (capture_dir / "candidate-state.json").read_bytes(), "candidate bytes differ")
        require(event_bytes == (capture_dir / "candidate-events.json").read_bytes(), "event bytes differ")
        require(rebuilt["candidate_state_hash"] == saved["candidate_state_hash"], "state hash differs")
        result = {
            "schema_version": 1,
            "status": "OFFLINE_REBUILD_EXACT_MATCH",
            "candidate_state_hash": rebuilt["candidate_state_hash"],
            "candidate_state_sha256": rebuilt["candidate_state_sha256"],
            "event_ledger_sha256": rebuilt["event_ledger_sha256"],
            "network_calls": 0,
            "hithink_new_requests": 0,
            **AUTHORITY,
        }
        save_json(out / "verification.json", result)
        print(result["status"], result["candidate_state_hash"])
        return 0
    except Exception as exc:
        save_json(
            out / "verification.json",
            {
                "schema_version": 1,
                "status": "FAILED_CLOSED",
                "network_calls": 0,
                "hithink_new_requests": 0,
                "error": {
                    "type": type(exc).__name__,
                    "message": " ".join(str(exc).split())[:1000],
                },
                **AUTHORITY,
            },
        )
        return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    cap = sub.add_parser("capture")
    cap.add_argument("--source", type=Path, required=True)
    cap.add_argument("--prior", type=Path, required=True)
    cap.add_argument("--probe", type=Path, required=True)
    cap.add_argument("--output", type=Path, required=True)

    ver = sub.add_parser("verify")
    ver.add_argument("--source", type=Path, required=True)
    ver.add_argument("--capture", type=Path, required=True)
    ver.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.cmd == "capture":
        return capture(args.source, args.prior, args.probe, args.output)
    return verify(args.source, args.capture, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
