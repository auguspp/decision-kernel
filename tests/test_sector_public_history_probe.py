from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github/scripts/probe-sector-public-history.py"
r = runpy.run_path(str(SCRIPT))


class JSONDecoder:
    @staticmethod
    def decode(value):
        return json.loads(value)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _source(tmp_path: Path):
    root = tmp_path / "source"
    capture = root / "capture"
    (capture / "responses").mkdir(parents=True)
    files = {}
    requests = []
    for idx, code in enumerate(r["PROBE_CODES"], start=2):
        envelope = {
            "code": 0,
            "message": "success",
            "data": {
                "thscode": code,
                "interval": "1d",
                "adjust": None,
                "timestamp": 1788969600000,
                "item": [
                    {"date_ms": 1788883200000, "close_price": 10 + idx, "volume": 100 + idx, "turnover": 1000 + idx},
                    {"date_ms": 1788969600000, "close_price": 20 + idx, "volume": 200 + idx, "turnover": 2000 + idx},
                ],
            },
        }
        raw = (json.dumps(envelope, separators=(",", ":")) + "\n").encode()
        rel = f"responses/{idx:04d}.json"
        (capture / rel).write_bytes(raw)
        files[rel] = {"bytes": len(raw), "sha256": _sha(raw)}
        requests.append({"path": "/api/a-share-index/prices/historical", "params": {"thscode": code}, "response_file": rel})
    report = {
        "status": "FAILED_CLOSED",
        "production_state_writes": 0,
        "binding": {"workflow": {"GITHUB_RUN_ID": str(r["SOURCE_RUN_ID"])}},
        "files": files,
        "requests": requests,
    }
    (capture / "report.json").write_text(json.dumps(report))
    return root


def test_hithink_reference_binds_exact_codes_and_sessions(tmp_path):
    source = _source(tmp_path)
    got = r["load_hithink_reference"](source)
    assert tuple(got) == r["PROBE_CODES"]
    assert all(tuple(row) == r["PROBE_SESSIONS"] for row in got.values())
    assert got["884002.TI"]["2026-09-10"]["turnover"].isdigit()


def test_public_year_parser_keeps_close_volume_turnover():
    invalid = 'callback({"data":"20260909,1,2,0.5,1638.889,149911920,1818865100,x;x2026,1,2,0.5,4,5,6,x;20260910,1,2,0.5,1581.727,126610432,1472693800,x"})'
    with pytest.raises(r["ProbeError"]):
        r["parse_ths_year_text"](invalid, demjson_module=JSONDecoder)
    valid = 'callback({"data":"20260909,1,2,0.5,1638.889,149911920,1818865100,x;20260910,1,2,0.5,1581.727,126610432,1472693800,x"})'
    points = r["parse_ths_year_text"](valid, demjson_module=JSONDecoder)
    assert points["2026-09-09"] == {"close": "1638.889", "volume": "149911920", "turnover": "1818865100"}
    assert points["2026-09-10"]["turnover"] == "1472693800"


def test_compare_is_exact_decimal_not_string_format():
    reference = {code: {session: {field: "1.0" for field in ("close", "volume", "turnover")} for session in r["PROBE_SESSIONS"]} for code in r["PROBE_CODES"]}
    public = {code: {session: {field: "1" for field in ("close", "volume", "turnover")} for session in r["PROBE_SESSIONS"]} for code in r["PROBE_CODES"]}
    matches, mismatches = r["compare"](reference, public)
    assert len(matches) == 30 and not mismatches
    public["884002.TI"]["2026-09-10"]["turnover"] = "2"
    matches, mismatches = r["compare"](reference, public)
    assert len(matches) == 29
    assert mismatches == [{"thscode": "884002.TI", "session": "2026-09-10", "field": "turnover", "hithink": "1.0", "public_ths": "2"}]


def test_probe_scope_is_five_and_crosses_881_884():
    assert r["MAX_PUBLIC_REQUESTS"] == 5
    assert len(r["PROBE_CODES"]) == 5
    assert any(code.startswith("881") for code in r["PROBE_CODES"])
    assert any(code.startswith("884") for code in r["PROBE_CODES"])
    assert r["PROBE_SESSIONS"] == ("2026-09-09", "2026-09-10")


def test_workflow_is_manual_no_secret_and_pinned():
    workflow = (ROOT / ".github/workflows/sector-public-history-probe.yml").read_text()
    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "HITHINK_FINANCE_API_KEY" not in workflow
    assert "SUB2API" not in workflow
    assert "10187281705" in workflow and "34566950303" in workflow
    assert r["AKSHARE_COMMIT"] in workflow
    assert "timeout-minutes: 10" in workflow
    assert "This probe never writes Sector state/cache/events" in workflow
