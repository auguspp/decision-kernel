#!/usr/bin/env python3
"""Two-code probe for the mature THS v2 board-history endpoint.

Tests exact field/scale agreement against frozen Decision Kernel evidence. No retry,
no HiThink call, no production write.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

KNOWN = "884002.TI"
STUBBORN = "884189.TI"
CODES = (KNOWN, STUBBORN)
TARGETS = (date(2026, 9, 7), date(2026, 9, 8), date(2026, 9, 9), date(2026, 9, 10))
SH = ZoneInfo("Asia/Shanghai")
MAX_BODY = 4 * 1024 * 1024
DATA_RE = re.compile(r'"data"\s*:\s*"([^"]*)"')


class ProbeError(RuntimeError):
    pass


def require(v: bool, m: str) -> None:
    if not v:
        raise ProbeError(m)


def dec(v: Any, field: str) -> Decimal:
    try:
        x = Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ProbeError(f"{field} is not numeric") from exc
    require(x.is_finite(), f"{field} is not finite")
    return x


def ms_day(v: Any) -> date:
    return datetime.fromtimestamp(int(v) / 1000, tz=SH).date()


def load_state(source: Path) -> dict[str, Any]:
    p = source / "input" / "market-state.json"
    require(p.is_file(), "frozen state missing")
    return json.loads(p.read_text(encoding="utf-8"))


def state_points(state: dict[str, Any], code: str) -> dict[date, tuple[Decimal, Decimal]]:
    sessions = [date.fromisoformat(x) for x in state["sessions"]]
    row = next((x for x in state["series"] if x["thscode"] == code), None)
    require(row is not None, f"state identity missing {code}")
    return {
        d: (dec(c, f"{code}.{d}.state_close"), dec(t, f"{code}.{d}.state_turnover"))
        for d, c, t in zip(sessions, row["closes"], row["turnovers"], strict=True)
    }


def retained_known(source: Path) -> dict[date, tuple[Decimal, Decimal, Decimal]]:
    report = json.loads((source / "capture" / "report.json").read_text(encoding="utf-8"))
    for row in report["requests"]:
        if row.get("params", {}).get("thscode") == KNOWN and row.get("response_file"):
            envelope = json.loads((source / "capture" / row["response_file"]).read_text(encoding="utf-8"))
            out = {}
            for item in envelope["data"]["item"]:
                d = ms_day(item["date_ms"])
                if d in TARGETS:
                    out[d] = (
                        dec(item["close_price"], "known close"),
                        dec(item["volume"], "known volume"),
                        dec(item["turnover"], "known turnover"),
                    )
            require(all(d in out for d in TARGETS), "known retained target dates missing")
            return out
    raise ProbeError("known retained history missing")


def parse_v2(body: bytes, code: str) -> dict[date, tuple[Decimal, Decimal, Decimal]]:
    require(len(body) <= MAX_BODY, f"v2 response too large {code}")
    text = None
    for encoding in ("utf-8", "gb18030"):
        try:
            text = body.decode(encoding)
            break
        except UnicodeDecodeError:
            pass
    require(text is not None, f"v2 response undecodable {code}")
    match = DATA_RE.search(text)
    require(match is not None, f"v2 data string missing {code}")
    series = match.group(1).replace("\\/", "/")
    out = {}
    for rec in series.split(";"):
        cols = rec.split(",")
        require(len(cols) >= 7, f"v2 row too short {code}")
        raw = cols[0].strip()
        require(len(raw) == 8 and raw.isdigit(), f"v2 date invalid {code}")
        d = date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
        if d not in TARGETS:
            continue
        require(d not in out, f"v2 duplicate date {code}")
        out[d] = (
            dec(cols[4], f"{code}.{d}.close"),
            dec(cols[5], f"{code}.{d}.volume"),
            dec(cols[6], f"{code}.{d}.amount_raw"),
        )
    require(all(d in out for d in TARGETS), f"v2 target dates missing {code}")
    return out


def fetch(code: str, raw_dir: Path) -> tuple[dict[date, tuple[Decimal, Decimal, Decimal]], dict[str, Any]]:
    url = f"http://d.10jqka.com.cn/v2/line/bk_{code[:6]}/01/last.js"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0",
        "Referer": "https://q.10jqka.com.cn/",
        "Host": "d.10jqka.com.cn",
    }
    r = requests.get(url, headers=headers, timeout=12, allow_redirects=False)
    body = r.content
    raw_dir.mkdir(parents=True, exist_ok=True)
    p = raw_dir / f"{code[:6]}.js"
    p.write_bytes(body)
    meta = {
        "code": code,
        "url": url,
        "http_status": r.status_code,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "location": r.headers.get("Location"),
    }
    require(r.status_code == 200, f"v2 HTTP {r.status_code} {code}")
    return parse_v2(body, code), meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "FAILED_CLOSED",
        "requests": [],
        "checks": [],
        "turnover_scale": None,
        "stubborn_target": None,
        "network_calls": 0,
        "hithink_calls": 0,
        "production_state_writes": 0,
        "restore_authority": "NONE",
        "error": None,
    }
    rc = 2
    try:
        state = load_state(args.source)
        known = retained_known(args.source)
        observed = {}
        for code in CODES:
            points, meta = fetch(code, args.output / "raw")
            result["requests"].append(meta)
            result["network_calls"] += 1
            observed[code] = points

        # Determine amount scale only from the known identity against retained HiThink.
        candidates = (Decimal("1"), Decimal("0.01"), Decimal("100"))
        matching_scales = []
        for scale in candidates:
            if all(
                observed[KNOWN][d][0] == known[d][0]
                and observed[KNOWN][d][1] == known[d][1]
                and observed[KNOWN][d][2] * scale == known[d][2]
                for d in (date(2026, 9, 9), date(2026, 9, 10))
            ):
                matching_scales.append(scale)
        require(len(matching_scales) == 1, f"v2 turnover scale not uniquely established: {matching_scales}")
        scale = matching_scales[0]
        result["turnover_scale"] = str(scale)

        for code in CODES:
            old = state_points(state, code)
            for d in TARGETS[:3]:
                close, _vol, amount = observed[code][d]
                exp_close, exp_turn = old[d]
                turn = amount * scale
                exact = close == exp_close and turn == exp_turn
                result["checks"].append({
                    "code": code,
                    "date": d.isoformat(),
                    "scope": "OLD_STATE_OVERLAP",
                    "close_exact": close == exp_close,
                    "turnover_exact": turn == exp_turn,
                    "exact": exact,
                })
                require(exact, f"v2 old-state mismatch {code} {d}")

        for d in (date(2026, 9, 9), date(2026, 9, 10)):
            close, vol, amount = observed[KNOWN][d]
            exp_close, exp_vol, exp_turn = known[d]
            turn = amount * scale
            exact = close == exp_close and vol == exp_vol and turn == exp_turn
            result["checks"].append({
                "code": KNOWN,
                "date": d.isoformat(),
                "scope": "RETAINED_HITHINK",
                "close_exact": close == exp_close,
                "volume_exact": vol == exp_vol,
                "turnover_exact": turn == exp_turn,
                "exact": exact,
            })
            require(exact, f"v2 retained-HiThink mismatch {d}")

        close, vol, amount = observed[STUBBORN][date(2026, 9, 10)]
        result["stubborn_target"] = {
            "code": STUBBORN,
            "date": "2026-09-10",
            "close": str(close),
            "volume": str(vol),
            "turnover": str(amount * scale),
            "amount_raw": str(amount),
        }
        result["status"] = "EXACT_OVERLAP_KNOWN_HITHINK_AND_SCALE_MATCH"
        rc = 0
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": " ".join(str(exc).split())[:1000]}
    (args.output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(result["status"], result["error"])
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
