#!/usr/bin/env python3
"""One-time mixed-source Sector gap capture; candidate only, never restore authority.

Reuse retained HiThink responses for already-successful histories and exact-identity
10jqka public board history only for the missing histories. No retries, no signals.
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

from decision_kernel.adapters.hithink import (
    latest_completed_a_share_session,
    normalize_hithink_calendar,
)
from decision_kernel.adapters.hithink_index import (
    normalize_hithink_completed_index_history,
    normalize_hithink_industry_catalog,
)
from decision_kernel.identity import canonical_json
from decision_kernel.runtime.sector_radar import SectorPricePoint, SectorPriceSeries
from decision_kernel.runtime.sector_radar_audit import _atomic_bytes, _sha
from decision_kernel.runtime.sector_radar_persistence import (
    load_sector_radar_persistent_bundle,
)
from decision_kernel.runtime.sector_radar_state import (
    SectorRadarStateSourceLineage,
    create_sector_radar_market_state,
    serialize_sector_radar_market_state,
)

REPO = "auguspp/decision-kernel"
AKSHARE_COMMIT = "8e95744b79ae22326308ccd2b4e62650c5b53c55"
SOURCE_RUN_ID = 34566950303
SOURCE_ARTIFACT_ID = 10187281705
SOURCE_ARTIFACT_SHA256 = (
    "aedf5fc5507fa33c00f316be72c14b50962486961ba7199e097d2628205dc60b"
)
SOURCE_WORKFLOW = ".github/workflows/sector-radar-shadow.yml"
EXPECTED_PARENT_RUN_ID = 34364727989
EXPECTED_PARENT_ARTIFACT_ID = 10109790767
EXPECTED_RETAINED_HISTORY_COUNT = 110
EXPECTED_PUBLIC_HISTORY_COUNT = 211
TARGET_SESSION = date(2026, 9, 10)
PUBLIC_YEAR = 2026
PUBLIC_SPACING_SECONDS = 1.0
PUBLIC_TIMEOUT_SECONDS = 12.0
MAX_PUBLIC_RESPONSE_BYTES = 4 * 1024 * 1024
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CaptureError(message)


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CaptureError(f"{field} is not numeric") from exc
    if not result.is_finite():
        raise CaptureError(f"{field} is not finite")
    return result


def _save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_bytes(path, (canonical_json(value) + "\n").encode("utf-8"))


def _load_json(path: Path) -> Any:
    require(path.is_file() and not path.is_symlink(), f"missing input {path}")
    require(path.stat().st_size <= 16 * 1024 * 1024, f"input too large {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _source_report(source: Path) -> dict[str, Any]:
    report = _load_json(source / "capture" / "report.json")
    require(report.get("status") == "FAILED_CLOSED", "source recovery status disagrees")
    require(report.get("restore_authority") is False, "source carried restore authority")
    require(report.get("production_state_writes") == 0, "source wrote production state")
    require(report.get("events_created") == 0, "source created events")
    binding = report.get("binding")
    require(isinstance(binding, dict), "source binding missing")
    request = binding.get("request")
    require(isinstance(request, dict), "source request binding missing")
    parent = request.get("parent")
    require(isinstance(parent, dict), "source parent binding missing")
    require(parent.get("run_id") == EXPECTED_PARENT_RUN_ID, "source parent run changed")
    require(
        parent.get("artifact_id") == EXPECTED_PARENT_ARTIFACT_ID,
        "source parent artifact changed",
    )
    return report


def _response_path(source: Path, response_file: str) -> Path:
    path = source / "capture" / response_file
    require(path.is_file() and not path.is_symlink(), "retained response missing")
    require(path.stat().st_size <= 8 * 1024 * 1024, "retained response too large")
    return path


def _retained_inputs(
    source: Path, report: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path]]:
    calendar: dict[str, Any] | None = None
    catalog: dict[str, Any] | None = None
    histories: dict[str, Path] = {}

    for row in report.get("requests", []):
        require(isinstance(row, dict), "malformed source request row")
        response_file = row.get("response_file")
        if not isinstance(response_file, str):
            continue
        path = str(row.get("path", ""))
        params = row.get("params")
        require(isinstance(params, dict), "malformed source request params")
        response_path = _response_path(source, response_file)
        if path.endswith("/calendar/trading-days"):
            require(calendar is None, "duplicate retained calendar")
            calendar = _load_json(response_path)
        elif path.endswith("/catalog/ths-index-list"):
            require(catalog is None, "duplicate retained catalog")
            catalog = _load_json(response_path)
        elif path.endswith("/prices/historical"):
            code = str(params.get("thscode", "")).strip().upper()
            require(code and code not in histories, "duplicate retained history identity")
            histories[code] = response_path

    require(calendar is not None, "retained calendar missing")
    require(catalog is not None, "retained catalog missing")
    require(
        len(histories) == EXPECTED_RETAINED_HISTORY_COUNT,
        f"retained history count changed: {len(histories)}",
    )
    return calendar, catalog, histories


def _cookie_value() -> str:
    engine = ak_ths.py_mini_racer.MiniRacer()
    engine.eval(ak_ths._get_file_content_ths("ths.js"))
    value = engine.call("v")
    require(isinstance(value, str) and value.strip(), "AKShare ths.js cookie failed")
    return value


def _parse_public_year(
    body: bytes, *, code: str
) -> dict[date, tuple[Decimal, Decimal, Decimal]]:
    require(len(body) <= MAX_PUBLIC_RESPONSE_BYTES, f"public response too large {code}")
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CaptureError(f"public response is not UTF-8 {code}") from exc
    start = text.find("{")
    require(start >= 0 and len(text) > start + 2, f"public object missing {code}")
    try:
        payload = ak_ths.demjson.decode(text[start:-1])
    except Exception as exc:
        raise CaptureError(f"AKShare parser rejected public response {code}") from exc
    require(
        isinstance(payload, dict) and isinstance(payload.get("data"), str),
        f"public data series missing {code}",
    )

    points: dict[date, tuple[Decimal, Decimal, Decimal]] = {}
    for record in payload["data"].split(";"):
        columns = record.split(",")
        require(len(columns) in (11, 12), f"public row width unsupported {code}")
        raw_day = columns[0].strip()
        if len(raw_day) == 8 and raw_day.isdigit():
            day = date(int(raw_day[:4]), int(raw_day[4:6]), int(raw_day[6:8]))
        else:
            try:
                day = datetime.fromisoformat(raw_day).date()
            except ValueError as exc:
                raise CaptureError(f"public date invalid {code}") from exc
        require(day not in points, f"public duplicate date {code} {day}")
        points[day] = (
            _decimal(columns[4], f"{code}.{day}.close"),
            _decimal(columns[5], f"{code}.{day}.volume"),
            _decimal(columns[6], f"{code}.{day}.turnover"),
        )
    return points


def _public_get(
    code: str, cookie: str, raw_dir: Path
) -> tuple[dict[date, tuple[Decimal, Decimal, Decimal]], dict[str, Any]]:
    require(CODE_RE.fullmatch(code) is not None, f"public identity rejected {code}")
    numeric = code[:6]
    url = f"https://d.10jqka.com.cn/v4/line/bk_{numeric}/01/{PUBLIC_YEAR}.js"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/89.0.4389.90 Safari/537.36"
        ),
        "Referer": "http://q.10jqka.com.cn",
        "Host": "d.10jqka.com.cn",
        "Cookie": f"v={cookie}",
    }
    started = datetime.now(tz=SHANGHAI)
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=PUBLIC_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        raise CaptureError(f"public request failed {code}: {type(exc).__name__}") from exc
    finished = datetime.now(tz=SHANGHAI)
    body = response.content
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_name = f"{numeric}-{PUBLIC_YEAR}.js"
    _atomic_bytes(raw_dir / raw_name, body)
    meta = {
        "code": code,
        "url": url,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "http_status": response.status_code,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "redirect": response.headers.get("Location"),
        "raw_file": f"raw/{raw_name}",
    }
    require(response.status_code == 200, f"public HTTP {response.status_code} {code}")
    return _parse_public_year(body, code=code), meta


def _compose(
    *,
    source: Path,
    public_root: Path,
    capture_mode: bool,
    spacing: float,
    cookie: str | None = None,
) -> tuple[bytes, bytes, dict[str, Any]]:
    report = _source_report(source)
    calendar_envelope, catalog_envelope, retained_histories = _retained_inputs(
        source, report
    )
    bundle = load_sector_radar_persistent_bundle(
        source / "input",
        expected_repository=REPO,
        expected_workflow=SOURCE_WORKFLOW,
        expected_parent_hint_mapping_hash=report["binding"]["request"]["parent"][
            "parent_hint_mapping_hash"
        ],
    )
    state = bundle.market_state
    sessions = normalize_hithink_calendar(calendar_envelope)
    observed_at = datetime.fromisoformat(report["observed_at"])
    target = latest_completed_a_share_session(sessions, observed_at=observed_at)
    require(target == TARGET_SESSION, f"target session changed: {target}")
    require(state.sessions[-1] == date(2026, 9, 9), "frozen state no longer ends 2026-09-09")
    overlap = state.sessions[-3:]
    needed = (*overlap, target)
    catalog = normalize_hithink_industry_catalog(catalog_envelope)
    require(catalog.catalog_hash == state.catalog_hash, "catalog hash changed")

    all_codes = tuple(item.thscode for item in state.series)
    retained_codes = set(retained_histories)
    missing_codes = tuple(code for code in all_codes if code not in retained_codes)
    require(
        len(retained_codes) == EXPECTED_RETAINED_HISTORY_COUNT,
        "retained identity count changed",
    )
    require(
        len(missing_codes) == EXPECTED_PUBLIC_HISTORY_COUNT,
        f"public identity count changed: {len(missing_codes)}",
    )
    require(
        set(all_codes) == retained_codes | set(missing_codes),
        "source identity coverage incomplete",
    )
    require(
        all(CODE_RE.fullmatch(code) for code in missing_codes),
        "missing set contains non-THS-board identity",
    )
    if capture_mode:
        require(cookie is not None, "public cookie missing")

    public_dir = public_root / "raw"
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "status": "RECORDING" if capture_mode else "VERIFYING",
        "semantics": "ONE_TIME_MIXED_RETAINED_HITHINK_AND_PUBLIC_THS_RECOVERY_CANDIDATE_ONLY",
        "akshare_commit": AKSHARE_COMMIT,
        "source_run_id": SOURCE_RUN_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_sha256": SOURCE_ARTIFACT_SHA256,
        "target_session": target.isoformat(),
        "overlap_sessions": [day.isoformat() for day in overlap],
        "retained_hithink_history_count": len(retained_codes),
        "public_ths_history_count": len(missing_codes),
        "public_request_cap": EXPECTED_PUBLIC_HISTORY_COUNT,
        "public_requests": [],
        "overlap_checks": [],
        "candidate_state_hash": None,
        "candidate_state_sha256": None,
        "event_ledger_sha256": _sha((source / "input/candidate-events.json").read_bytes()),
        "technical_retries": 0,
        **AUTHORITY,
        "error": None,
    }

    old_by_code = {item.thscode: item for item in state.series}
    completed: dict[str, tuple[Decimal, Decimal]] = {}

    for code in all_codes:
        old = old_by_code[code]
        old_lookup = {
            day: (close, turnover)
            for day, close, turnover in zip(
                state.sessions, old.closes, old.turnovers, strict=True
            )
        }
        if code in retained_histories:
            envelope = _load_json(retained_histories[code])
            history = normalize_hithink_completed_index_history(
                envelope,
                thscode=code,
                sessions=sessions,
                observed_at=observed_at,
            )
            require(
                history.response_session == history.expected_latest_session == target,
                f"retained history target changed {code}",
            )
            by_day = {
                point.as_of.date(): (point.close, point.volume, point.turnover)
                for point in history.points
            }
            require(
                all(day in by_day for day in needed),
                f"retained history missing needed dates {code}",
            )
            source_kind = "RETAINED_HITHINK"
        else:
            raw_path = public_dir / f"{code[:6]}-{PUBLIC_YEAR}.js"
            if capture_mode:
                by_day, meta = _public_get(code, cookie, public_dir)
                receipt["public_requests"].append(meta)
                _save_json(public_root / "receipt.partial.json", receipt)
                if len(receipt["public_requests"]) < len(missing_codes):
                    time.sleep(spacing)
            else:
                require(raw_path.is_file(), f"public raw missing {code}")
                by_day = _parse_public_year(raw_path.read_bytes(), code=code)
            require(
                all(day in by_day for day in needed),
                f"public history missing needed dates {code}",
            )
            source_kind = "PUBLIC_10JQKA_VIA_AKSHARE"

        for day in overlap:
            close, _, turnover = by_day[day]
            expected_close, expected_turnover = old_lookup[day]
            exact = close == expected_close and turnover == expected_turnover
            receipt["overlap_checks"].append(
                {
                    "code": code,
                    "source_kind": source_kind,
                    "session": day.isoformat(),
                    "close_exact": close == expected_close,
                    "turnover_exact": turnover == expected_turnover,
                    "exact": exact,
                }
            )
            require(exact, f"overlap mismatch {code} {day}")

        target_close, _, target_turnover = by_day[target]
        completed[code] = (target_close, target_turnover)

    require(len(completed) == len(all_codes), "candidate series coverage incomplete")

    series: list[SectorPriceSeries] = []
    for old in state.series:
        points = tuple(
            SectorPricePoint(day, close, turnover)
            for day, close, turnover in zip(
                state.sessions, old.closes, old.turnovers, strict=True
            )
        )
        target_close, target_turnover = completed[old.thscode]
        points += (SectorPricePoint(target, target_close, target_turnover),)
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
        created_at=observed_at,
        source=(
            "RECOVERY_CANDIDATE_MIXED_RETAINED_HITHINK_AND_PUBLIC_10JQKA_"
            "NOT_RESTORE_AUTHORITY"
        ),
        source_lineage=lineage,
    )
    candidate_bytes = serialize_sector_radar_market_state(candidate).encode("utf-8")
    event_bytes = (source / "input/candidate-events.json").read_bytes()
    receipt.update(
        status="RECOVERY_CANDIDATE_REVIEW_REQUIRED",
        candidate_state_hash=candidate.state_hash,
        candidate_state_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
        public_request_count=(
            len(receipt["public_requests"])
            if capture_mode
            else EXPECTED_PUBLIC_HISTORY_COUNT
        ),
    )
    return candidate_bytes, event_bytes, receipt


def capture(source: Path, output: Path, spacing: float) -> int:
    output.mkdir(parents=True, exist_ok=False)
    receipt: dict[str, Any] | None = None
    try:
        candidate, events, receipt = _compose(
            source=source,
            public_root=output,
            capture_mode=True,
            spacing=spacing,
            cookie=_cookie_value(),
        )
        _atomic_bytes(output / "candidate-state.json", candidate)
        _atomic_bytes(output / "candidate-events.json", events)
        _save_json(output / "receipt.json", receipt)
        print(
            f"status={receipt['status']} public_requests={receipt['public_request_count']} "
            f"candidate={receipt['candidate_state_hash']}"
        )
        return 0
    except Exception as exc:
        partial_path = output / "receipt.partial.json"
        if partial_path.is_file():
            receipt = _load_json(partial_path)
        else:
            receipt = {
                "schema_version": 1,
                "status": "FAILED_CLOSED",
                "public_requests": [],
                **AUTHORITY,
            }
        receipt["status"] = "FAILED_CLOSED"
        receipt["error"] = {
            "type": type(exc).__name__,
            "message": " ".join(str(exc).split())[:1000],
        }
        _save_json(output / "receipt.json", receipt)
        print(
            f"FAILED_CLOSED: {type(exc).__name__}: {str(exc)[:500]}",
            file=sys.stderr,
        )
        return 2


def verify(source: Path, capture_root: Path, output: Path) -> int:
    output.mkdir(parents=True, exist_ok=False)
    try:
        saved_receipt = _load_json(capture_root / "receipt.json")
        require(
            saved_receipt.get("status") == "RECOVERY_CANDIDATE_REVIEW_REQUIRED",
            "saved capture is not complete",
        )
        candidate, events, rebuilt = _compose(
            source=source,
            public_root=capture_root,
            capture_mode=False,
            spacing=0.0,
        )
        require(
            candidate == (capture_root / "candidate-state.json").read_bytes(),
            "offline rebuilt candidate bytes differ",
        )
        require(
            events == (capture_root / "candidate-events.json").read_bytes(),
            "event ledger bytes changed",
        )
        require(
            rebuilt["candidate_state_hash"] == saved_receipt["candidate_state_hash"],
            "candidate state hash changed",
        )
        verification = {
            "schema_version": 1,
            "status": "OFFLINE_REBUILD_EXACT_MATCH",
            "candidate_state_hash": rebuilt["candidate_state_hash"],
            "candidate_state_sha256": rebuilt["candidate_state_sha256"],
            "event_ledger_sha256": rebuilt["event_ledger_sha256"],
            "network_calls": 0,
            **AUTHORITY,
        }
        _save_json(output / "verification.json", verification)
        print(
            f"status={verification['status']} candidate={verification['candidate_state_hash']}"
        )
        return 0
    except Exception as exc:
        _save_json(
            output / "verification.json",
            {
                "schema_version": 1,
                "status": "FAILED_CLOSED",
                "error": {
                    "type": type(exc).__name__,
                    "message": " ".join(str(exc).split())[:1000],
                },
                "network_calls": 0,
                **AUTHORITY,
            },
        )
        print(f"verify failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_capture = sub.add_parser("capture")
    p_capture.add_argument("--source", required=True, type=Path)
    p_capture.add_argument("--output", required=True, type=Path)
    p_capture.add_argument("--spacing-seconds", type=float, default=PUBLIC_SPACING_SECONDS)
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--source", required=True, type=Path)
    p_verify.add_argument("--capture", required=True, type=Path)
    p_verify.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if args.command == "capture":
        require(0.5 <= args.spacing_seconds <= 5.0, "public spacing outside bounded range")
        return capture(args.source, args.output, args.spacing_seconds)
    return verify(args.source, args.capture, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
