#!/usr/bin/env python3
"""One-request same-source THS v2 qualification for 884287.TI.

The turnover scale is inferred only if exactly one candidate scale makes the
2026-09-07..09 overlap match the frozen accepted state. No retry, no HiThink
request, no production/current-state/event/Research/Odds/Action authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import requests

CODE = "884287.TI"
SYMBOL = "884287"
TARGETS = (date(2026, 9, 7), date(2026, 9, 8), date(2026, 9, 9), date(2026, 9, 10))
URL = "http://d.10jqka.com.cn/v2/line/bk_884287/01/last.js"
MAX_BODY = 4 * 1024 * 1024
DATA_RE = re.compile(r'"data"\s*:\s*"([^"]*)"')


class ProbeError(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise ProbeError(message)


def dec(value: Any, field: str) -> Decimal:
    try:
        out = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ProbeError(f"{field} is not numeric") from exc
    require(out.is_finite(), f"{field} is not finite")
    return out


def load_state(source: Path) -> tuple[dict[date, tuple[Decimal, Decimal]], str]:
    state = json.loads((source / "input" / "market-state.json").read_text(encoding="utf-8"))
    sessions = [date.fromisoformat(x) for x in state["sessions"]]
    row = next((x for x in state["series"] if x["thscode"] == CODE), None)
    require(row is not None, f"state identity missing {CODE}")
    points = {
        d: (dec(close, f"{CODE}.{d}.state_close"), dec(turnover, f"{CODE}.{d}.state_turnover"))
        for d, close, turnover in zip(sessions, row["closes"], row["turnovers"], strict=True)
    }
    require(all(d in points for d in TARGETS[:3]), "frozen overlap dates missing")
    return points, str(row.get("name", ""))


def parse_v2(body: bytes) -> dict[date, tuple[Decimal, Decimal, Decimal]]:
    require(len(body) <= MAX_BODY, "v2 response too large")
    text = None
    for encoding in ("utf-8", "gb18030"):
        try:
            text = body.decode(encoding)
            break
        except UnicodeDecodeError:
            pass
    require(text is not None, "v2 response undecodable")
    require(text.startswith(f"quotebridge_v2_line_bk_{SYMBOL}_01_last("), "v2 wrapper identity mismatch")
    match = DATA_RE.search(text)
    require(match is not None, "v2 data string missing")
    series = match.group(1).replace("\\/", "/")
    out = {}
    for record in series.split(";"):
        cols = record.split(",")
        require(len(cols) >= 7, "v2 row too short")
        raw = cols[0].strip()
        require(len(raw) == 8 and raw.isdigit(), "v2 date invalid")
        session = date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
        if session not in TARGETS:
            continue
        require(session not in out, "v2 duplicate date")
        out[session] = (
            dec(cols[4], f"{CODE}.{session}.close"),
            dec(cols[5], f"{CODE}.{session}.volume"),
            dec(cols[6], f"{CODE}.{session}.amount_raw"),
        )
    require(set(out) == set(TARGETS), "v2 target dates missing")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "FAILED_CLOSED",
        "code": CODE,
        "transport": "THS_V2_HTTP",
        "url": URL,
        "http_status": None,
        "bytes": 0,
        "sha256": None,
        "request_error": None,
        "turnover_scale": None,
        "checks": [],
        "target": None,
        "error": None,
        "network_calls": 1,
        "retry_count": 0,
        "hithink_calls": 0,
        "production_state_writes": 0,
        "events_created": 0,
        "restore_authority": "NONE",
        "research_authority": "NONE",
        "investment_authority": "NONE",
    }

    rc = 2
    try:
        state_points, retained_name = load_state(args.source)
        result["retained_name"] = retained_name
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0",
            "Referer": "https://q.10jqka.com.cn/",
            "Host": "d.10jqka.com.cn",
        }
        try:
            response = requests.get(URL, headers=headers, timeout=12, allow_redirects=False)
            body = response.content
            status = response.status_code
            request_error = None
        except requests.RequestException as exc:
            body = b""
            status = None
            request_error = {"type": type(exc).__name__, "message": " ".join(str(exc).split())[:500]}

        raw = args.output / "884287.js"
        raw.write_bytes(body)
        result["http_status"] = status
        result["bytes"] = len(body)
        result["sha256"] = hashlib.sha256(body).hexdigest()
        result["request_error"] = request_error
        require(request_error is None, "v2 request failed")
        require(status == 200, f"v2 HTTP {status} {CODE}")

        observed = parse_v2(body)
        candidates = (Decimal("1"), Decimal("0.01"), Decimal("100"))
        matching = []
        for scale in candidates:
            if all(
                observed[d][0] == state_points[d][0]
                and observed[d][2] * scale == state_points[d][1]
                for d in TARGETS[:3]
            ):
                matching.append(scale)
        require(len(matching) == 1, f"v2 turnover scale not uniquely established: {matching}")
        scale = matching[0]
        result["turnover_scale"] = str(scale)

        for d in TARGETS[:3]:
            close, _volume, amount = observed[d]
            expected_close, expected_turnover = state_points[d]
            turnover = amount * scale
            exact = close == expected_close and turnover == expected_turnover
            result["checks"].append(
                {
                    "date": d.isoformat(),
                    "close": str(close),
                    "expected_close": str(expected_close),
                    "turnover": str(turnover),
                    "expected_turnover": str(expected_turnover),
                    "close_exact": close == expected_close,
                    "turnover_exact": turnover == expected_turnover,
                    "exact": exact,
                }
            )
            require(exact, f"v2 overlap mismatch {d}")

        close, volume, amount = observed[TARGETS[-1]]
        result["target"] = {
            "date": TARGETS[-1].isoformat(),
            "close": str(close),
            "volume": str(volume),
            "turnover": str(amount * scale),
            "amount_raw": str(amount),
        }
        result["status"] = "EXACT_OVERLAP_V2_AVAILABLE"
        rc = 0
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": " ".join(str(exc).split())[:1000]}

    (args.output / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"], result["error"])
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
