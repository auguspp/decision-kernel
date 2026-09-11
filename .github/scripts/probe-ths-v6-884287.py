#!/usr/bin/env python3
"""Single-identity THS v6 qualification for 884287.TI.

One public request, no retry, no HiThink call, no production/current-state/event/Research/Odds/Action write.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import requests
from akshare.stock_feature import stock_board_industry_ths as ak_ths

SOURCE = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=False)
RAW = OUT / "raw"
RAW.mkdir()
CODE = "884287.TI"
TARGETS = (date(2026, 9, 7), date(2026, 9, 8), date(2026, 9, 9), date(2026, 9, 10))


class ProbeError(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise ProbeError(message)


def dec(value, field: str) -> Decimal:
    try:
        out = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ProbeError(f"{field} not numeric") from exc
    require(out.is_finite(), f"{field} not finite")
    return out


def cookie() -> str:
    js = ak_ths.py_mini_racer.MiniRacer()
    js.eval(ak_ths._get_file_content_ths("ths.js"))
    value = js.call("v")
    require(isinstance(value, str) and value, "cookie failed")
    return value


def state_points() -> dict[date, tuple[Decimal, Decimal]]:
    path = SOURCE / "input" / "market-state.json"
    require(path.is_file(), "frozen state missing")
    state = json.loads(path.read_text(encoding="utf-8"))
    sessions = [date.fromisoformat(x) for x in state["sessions"]]
    row = next((x for x in state["series"] if x["thscode"] == CODE), None)
    require(row is not None, f"state identity missing {CODE}")
    return {
        d: (dec(c, f"{CODE}.{d}.state_close"), dec(t, f"{CODE}.{d}.state_turnover"))
        for d, c, t in zip(sessions, row["closes"], row["turnovers"], strict=True)
    }


def parse_v6(body: bytes) -> dict[date, tuple[Decimal, Decimal, Decimal]]:
    text = body.decode("utf-8")
    start = text.find("{")
    require(start >= 0, "v6 object missing")
    payload = json.loads(text[start:-1])
    series = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(series, str) and isinstance(payload, dict):
        node = payload.get("48_" + CODE[:6])
        if isinstance(node, dict):
            series = node.get("data")
    require(isinstance(series, str), "v6 data series missing")
    out = {}
    for record in series.split(";"):
        cols = record.split(",")
        require(len(cols) >= 7, "v6 row too short")
        raw = cols[0].strip()
        require(len(raw) == 8 and raw.isdigit(), "v6 date invalid")
        d = date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
        if d not in TARGETS:
            continue
        require(d not in out, "v6 duplicate date")
        out[d] = (
            dec(cols[4], f"{CODE}.{d}.close"),
            dec(cols[5], f"{CODE}.{d}.volume"),
            dec(cols[6], f"{CODE}.{d}.turnover"),
        )
    return out


def main() -> int:
    result = {
        "schema_version": 1,
        "status": "FAILED_CLOSED",
        "code": CODE,
        "request": None,
        "checks": [],
        "target": None,
        "network_calls": 0,
        "retries": 0,
        "hithink_calls": 0,
        "production_state_writes": 0,
        "events_created": 0,
        "restore_authority": "NONE",
        "research_authority": "NONE",
        "investment_authority": "NONE",
        "error": None,
    }
    rc = 2
    try:
        old = state_points()
        value = cookie()
        url = f"https://d.10jqka.com.cn/v6/line/48_{CODE[:6]}/01/last1800.js"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "http://q.10jqka.com.cn",
            "Host": "d.10jqka.com.cn",
            "Cookie": "v=" + value,
        }
        response = requests.get(url, headers=headers, timeout=12, allow_redirects=False)
        body = response.content
        raw_path = RAW / f"{CODE[:6]}.js"
        raw_path.write_bytes(body)
        result["network_calls"] = 1
        result["request"] = {
            "url": url,
            "http_status": response.status_code,
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "raw_file": f"raw/{raw_path.name}",
        }
        require(response.status_code == 200, f"HTTP {response.status_code} {CODE}")
        points = parse_v6(body)
        require(all(d in points for d in TARGETS), "target dates missing")
        for d in TARGETS[:3]:
            close, _volume, turnover = points[d]
            exp_close, exp_turnover = old[d]
            exact = close == exp_close and turnover == exp_turnover
            result["checks"].append({
                "date": d.isoformat(),
                "close_exact": close == exp_close,
                "turnover_exact": turnover == exp_turnover,
                "exact": exact,
            })
            require(exact, f"old-state mismatch {d}")
        close, volume, turnover = points[TARGETS[-1]]
        result["target"] = {
            "date": TARGETS[-1].isoformat(),
            "close": str(close),
            "volume": str(volume),
            "turnover": str(turnover),
        }
        result["status"] = "EXACT_OVERLAP_V6_AVAILABLE"
        rc = 0
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": " ".join(str(exc).split())[:1000]}
    (OUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(result["status"], result["error"])
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
