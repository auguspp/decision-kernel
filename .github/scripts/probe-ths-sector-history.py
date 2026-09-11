#!/usr/bin/env python3
"""One-shot AKShare/10jqka exact-identity probe for Sector recovery.

No production state writes, no HiThink calls, no retry loop.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests
from akshare.stock_feature import stock_board_industry_ths as ak_ths

AKSHARE_COMMIT = "8e95744b79ae22326308ccd2b4e62650c5b53c55"
SOURCE_RUN_ID = 34566950303
SOURCE_ARTIFACT_ID = 10187281705
SOURCE_ARTIFACT_SHA256 = "aedf5fc5507fa33c00f316be72c14b50962486961ba7199e097d2628205dc60b"
TARGET_DATES = ("2026-09-09", "2026-09-10")
TARGET_CODES = (
    "884002.TI",
    "884003.TI",
    "884023.TI",
)
CODE_RE = re.compile(r"^(?:881|884)\d{3}\.TI$")
SHANGHAI = ZoneInfo("Asia/Shanghai")
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
TIMEOUT_SECONDS = 12.0


class ProbeError(RuntimeError):
    pass


@dataclass(frozen=True)
class Point:
    close: Decimal
    volume: Decimal
    turnover: Decimal


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ProbeError(f"{field} is not numeric") from exc
    if not result.is_finite():
        raise ProbeError(f"{field} is not finite")
    return result


def _date_ms_to_iso(value: Any) -> str:
    try:
        ms = int(value)
    except (TypeError, ValueError) as exc:
        raise ProbeError("HiThink date_ms is invalid") from exc
    return datetime.fromtimestamp(ms / 1000, tz=SHANGHAI).date().isoformat()


def _load_expected(root: Path) -> dict[str, dict[str, Point]]:
    report_path = root / "capture" / "report.json"
    if not report_path.is_file():
        raise ProbeError("retained recovery report is missing")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "FAILED_CLOSED":
        raise ProbeError("retained recovery report status disagrees")
    if report.get("restore_authority") is not False:
        raise ProbeError("retained recovery report unexpectedly carries restore authority")

    by_code: dict[str, str] = {}
    for row in report.get("requests", []):
        if not isinstance(row, dict):
            continue
        params = row.get("params")
        if not isinstance(params, dict):
            continue
        code = str(params.get("thscode", "")).strip().upper()
        response_file = row.get("response_file")
        if code in TARGET_CODES and isinstance(response_file, str):
            if code in by_code:
                raise ProbeError(f"duplicate retained response for {code}")
            by_code[code] = response_file

    if set(by_code) != set(TARGET_CODES):
        raise ProbeError(
            "retained HiThink responses do not cover exact probe identities; "
            f"found={sorted(by_code)}"
        )

    result: dict[str, dict[str, Point]] = {}
    for code in TARGET_CODES:
        response_path = root / "capture" / by_code[code]
        if not response_path.is_file():
            raise ProbeError(f"retained response file missing for {code}")
        envelope = json.loads(response_path.read_text(encoding="utf-8"))
        if envelope.get("code") != 0:
            raise ProbeError(f"retained HiThink response is not successful for {code}")
        data = envelope.get("data")
        if not isinstance(data, dict) or str(data.get("thscode", "")).upper() != code:
            raise ProbeError(f"retained HiThink identity mismatch for {code}")
        rows = data.get("item")
        if not isinstance(rows, list):
            raise ProbeError(f"retained HiThink item list missing for {code}")
        points: dict[str, Point] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ProbeError(f"malformed retained HiThink row for {code}")
            day = _date_ms_to_iso(row.get("date_ms"))
            if day in TARGET_DATES:
                points[day] = Point(
                    close=_decimal(row.get("close_price"), f"{code}.{day}.close"),
                    volume=_decimal(row.get("volume"), f"{code}.{day}.volume"),
                    turnover=_decimal(row.get("turnover"), f"{code}.{day}.turnover"),
                )
        if set(points) != set(TARGET_DATES):
            raise ProbeError(
                f"retained HiThink target dates missing for {code}; found={sorted(points)}"
            )
        result[code] = points
    return result


def _cookie_value() -> str:
    js_code = ak_ths.py_mini_racer.MiniRacer()
    js_code.eval(ak_ths._get_file_content_ths("ths.js"))
    value = js_code.call("v")
    if not isinstance(value, str) or not value.strip():
        raise ProbeError("AKShare ths.js did not produce a cookie value")
    return value


def _parse_ths_year_body(body: bytes, code: str) -> dict[str, Point]:
    if len(body) > MAX_RESPONSE_BYTES:
        raise ProbeError(f"public THS response exceeds byte cap for {code}")
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProbeError(f"public THS response is not UTF-8 for {code}") from exc
    start = text.find("{")
    if start < 0 or len(text) <= start + 2:
        raise ProbeError(f"public THS response has no object for {code}")
    # Match AKShare's existing parser contract: wrapper text, object body, one trailing char.
    try:
        payload = ak_ths.demjson.decode(text[start:-1])
    except Exception as exc:
        raise ProbeError(f"AKShare parser rejected public THS response for {code}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), str):
        raise ProbeError(f"public THS response has no data series for {code}")

    points: dict[str, Point] = {}
    for record in payload["data"].split(";"):
        cols = record.split(",")
        if len(cols) not in (11, 12):
            raise ProbeError(f"public THS row width is unsupported for {code}")
        raw_day = cols[0].strip()
        if len(raw_day) == 8 and raw_day.isdigit():
            day = f"{raw_day[:4]}-{raw_day[4:6]}-{raw_day[6:]}"
        else:
            try:
                day = datetime.fromisoformat(raw_day).date().isoformat()
            except ValueError as exc:
                raise ProbeError(f"public THS date is invalid for {code}") from exc
        if day not in TARGET_DATES:
            continue
        if day in points:
            raise ProbeError(f"public THS contains duplicate target date for {code}")
        points[day] = Point(
            close=_decimal(cols[4], f"{code}.{day}.public_close"),
            volume=_decimal(cols[5], f"{code}.{day}.public_volume"),
            turnover=_decimal(cols[6], f"{code}.{day}.public_turnover"),
        )

    if set(points) != set(TARGET_DATES):
        raise ProbeError(
            f"public THS target dates missing for {code}; found={sorted(points)}"
        )
    return points


def _fetch_public(code: str, cookie: str, raw_dir: Path) -> tuple[dict[str, Point], dict[str, Any]]:
    if not CODE_RE.fullmatch(code):
        raise ProbeError(f"probe identity is not an exact 881/884 THS code: {code}")
    numeric = code[:6]
    url = f"https://d.10jqka.com.cn/v4/line/bk_{numeric}/01/2026.js"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/89.0.4389.90 Safari/537.36"
        ),
        "Referer": "http://q.10jqka.com.cn",
        "Host": "d.10jqka.com.cn",
        "Cookie": f"v={cookie}",
    }
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=TIMEOUT_SECONDS,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        raise ProbeError(f"public THS request failed for {code}: {type(exc).__name__}") from exc
    body = response.content
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{numeric}-2026.js"
    raw_path.write_bytes(body)
    meta = {
        "code": code,
        "url": url,
        "http_status": response.status_code,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "redirect": response.headers.get("Location"),
    }
    if response.status_code != 200:
        raise ProbeError(
            f"public THS request returned HTTP {response.status_code} for {code}"
        )
    return _parse_ths_year_body(body, code), meta


def _point_payload(point: Point) -> dict[str, str]:
    return {
        "close": str(point.close),
        "volume": str(point.volume),
        "turnover": str(point.turnover),
    }


def run(root: Path, output: Path) -> int:
    output.mkdir(parents=True, exist_ok=True)
    raw_dir = output / "raw"
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "FAILED_CLOSED",
        "semantics": "AKSHARE_THIN_ADAPTER_EXACT_THS_IDENTITY_REUSE_PROBE_ONLY",
        "akshare_commit": AKSHARE_COMMIT,
        "source_run_id": SOURCE_RUN_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_sha256": SOURCE_ARTIFACT_SHA256,
        "target_codes": list(TARGET_CODES),
        "target_dates": list(TARGET_DATES),
        "public_market_request_cap": len(TARGET_CODES),
        "automatic_retries": 0,
        "hithink_requests": 0,
        "production_state_writes": 0,
        "restore_authority": "NONE",
        "research_authority": "NONE",
        "investment_authority": "NONE",
        "comparisons": [],
        "requests": [],
        "error": None,
    }
    exit_code = 2
    try:
        expected = _load_expected(root)
        cookie = _cookie_value()
        all_match = True
        for code in TARGET_CODES:
            observed, meta = _fetch_public(code, cookie, raw_dir)
            result["requests"].append(meta)
            for day in TARGET_DATES:
                exp = expected[code][day]
                obs = observed[day]
                fields = {
                    "close": obs.close == exp.close,
                    "volume": obs.volume == exp.volume,
                    "turnover": obs.turnover == exp.turnover,
                }
                exact = all(fields.values())
                all_match = all_match and exact
                result["comparisons"].append(
                    {
                        "code": code,
                        "date": day,
                        "expected_hithink": _point_payload(exp),
                        "observed_public_ths": _point_payload(obs),
                        "field_exact_match": fields,
                        "exact_match": exact,
                    }
                )
        if not all_match:
            raise ProbeError("one or more public THS fields disagree with retained HiThink")
        result["status"] = "EXACT_MATCH_ALL_FIELDS"
        exit_code = 0
    except Exception as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": " ".join(str(exc).split())[:1000],
        }
    finally:
        canonical = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        result["receipt_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        (output / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(
            f"status={result['status']} requests={len(result['requests'])} "
            f"receipt={result['receipt_sha256']}"
        )
        if result["error"]:
            print(
                f"error={result['error']['type']}: {result['error']['message']}",
                file=sys.stderr,
            )
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    return run(args.source, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
