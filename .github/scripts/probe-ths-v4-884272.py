#!/usr/bin/env python3
"""One-request same-source THS plain-HTTP v4 qualification for 884272.TI."""
import hashlib
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import requests
from akshare.stock_feature import stock_board_industry_ths as ak

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
CODE = "884272.TI"
SYMBOL = "884272"
NEED = (date(2026, 9, 7), date(2026, 9, 8), date(2026, 9, 9), date(2026, 9, 10))
URL = "http://d.10jqka.com.cn/v4/line/bk_884272/01/2026.js"


def require(value, message):
    if not value:
        raise RuntimeError(message)


state = json.loads((SRC / "input/market-state.json").read_text())
row = next(x for x in state["series"] if x["thscode"] == CODE)
days = [date.fromisoformat(x) for x in state["sessions"]]
old = {
    d: (Decimal(str(close)), Decimal(str(turnover)))
    for d, close, turnover in zip(days, row["closes"], row["turnovers"], strict=True)
}

js = ak.py_mini_racer.MiniRacer()
js.eval(ak._get_file_content_ths("ths.js"))
cookie_v = js.call("v")
headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "http://q.10jqka.com.cn",
    "Host": "d.10jqka.com.cn",
    "Cookie": "v=" + cookie_v,
}

try:
    response = requests.get(URL, headers=headers, timeout=12, allow_redirects=False)
    body = response.content
    http_status = response.status_code
    request_error = None
except requests.RequestException as exc:
    body = b""
    http_status = None
    request_error = {"type": type(exc).__name__, "message": " ".join(str(exc).split())[:500]}

(OUT / "884272.js").write_bytes(body)
result = {
    "schema_version": 1,
    "status": "FAILED_CLOSED",
    "code": CODE,
    "retained_name": row.get("name"),
    "transport": "THS_V4_HTTP",
    "url": URL,
    "http_status": http_status,
    "sha256": hashlib.sha256(body).hexdigest(),
    "bytes": len(body),
    "request_error": request_error,
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

try:
    require(request_error is None, "request failed")
    require(http_status == 200, f"HTTP {http_status}")
    prefix = f"quotebridge_v4_line_bk_{SYMBOL}_01_2026(".encode()
    require(body.startswith(prefix), "wrapper identity mismatch")
    text = body.decode()
    start = text.find("{")
    require(start >= 0, "object missing")
    payload = ak.demjson.decode(text[start:-1])
    series = payload.get("data")
    require(isinstance(series, str), "data missing")
    points = {}
    for record in series.split(";"):
        cols = record.split(",")
        require(len(cols) in (11, 12), "row width")
        raw = cols[0]
        session = date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
        if session in NEED:
            points[session] = (Decimal(cols[4]), Decimal(cols[5]), Decimal(cols[6]))
    require(set(points) == set(NEED), "needed dates missing")
    for session in NEED[:3]:
        close, _volume, turnover = points[session]
        expected_close, expected_turnover = old[session]
        exact = close == expected_close and turnover == expected_turnover
        result["checks"].append({
            "date": session.isoformat(),
            "close": str(close),
            "expected_close": str(expected_close),
            "turnover": str(turnover),
            "expected_turnover": str(expected_turnover),
            "close_exact": close == expected_close,
            "turnover_exact": turnover == expected_turnover,
            "exact": exact,
        })
        require(exact, f"overlap mismatch {session.isoformat()}")
    close, volume, turnover = points[NEED[-1]]
    result["target"] = {
        "date": "2026-09-10",
        "close": str(close),
        "volume": str(volume),
        "turnover": str(turnover),
    }
    result["status"] = "EXACT_OVERLAP_HTTP_V4_AVAILABLE"
except Exception as exc:
    result["error"] = {"type": type(exc).__name__, "message": " ".join(str(exc).split())[:1000]}

(OUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
print(result["status"], result["error"])
raise SystemExit(0 if result["status"] == "EXACT_OVERLAP_HTTP_V4_AVAILABLE" else 2)
