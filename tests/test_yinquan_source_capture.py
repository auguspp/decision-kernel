"""No network or secrets: scoped source, failure, replay, and non-PIT tests."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from decision_kernel.runtime import yinquan_source_capture as s

def env():
    return {"GITHUB_REPOSITORY": "auguspp/decision-kernel",
            "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
            "GITHUB_RUN_ATTEMPT": "1", "GITHUB_SHA": "a"*40,
            "EXPECTED_CODE": "a"*40, "GITHUB_RUN_ID": "123456",
            "TUSHARE_PROXY_API_KEY": "fake-test-only"}

def body(api, code, bad=False):
    fields = s.DAILY.split(",") if api == "daily" else s.BASIC.split(",")
    if api == "daily":
        row = [code, "20260930", "10", "11", "9", "10.5", "10", "10000", "100000"]
    else:
        row = [code, "20260930", "2.5"]
    return json.dumps({"code": 0, "api_name": api,
        "data": {"fields": fields, "items": [row], "count": 1 if not bad else 2}},
        separators=(",", ":")).encode()

def fake(api, params, key):
    assert key == "fake-test-only"
    slot = s.SYMBOLS.index(params["ts_code"]) * 2 + (api == "daily_basic")
    now = datetime(2026, 10, 8, 1, tzinfo=timezone.utc) + timedelta(seconds=slot * 2)
    return {"http_status": 200, "raw": body(api, params["ts_code"]),
            "requested_at": now.isoformat(),
            "received_at": (now + timedelta(seconds=1)).isoformat(), "headers": {}}

def test_complete_and_replay(tmp_path):
    root = tmp_path / "research"
    result = s.capture(root, env(), transport=fake)
    assert result["status"] == "COMPLETE_SOURCE_CAPTURE_NOT_PIT"
    assert len(result["calls"]) == 28
    assert s.verify(root)["source_calls_during_verify"] == 0
    assert len(list((root / "prices").glob("*.csv"))) == 14
    assert (root / "prices" / "000151.csv").read_text().count("2026-09-30") == 1
    assert "fake-test-only" not in (root / "receipt.json").read_text()
    p = root / "raw" / "01-daily-000001.SZ.json"
    p.write_bytes(p.read_bytes() + b" ")
    with pytest.raises(ValueError, match="RAW_HASH_OR_BUDGET"):
        s.verify(root)

def test_fail_closed_and_no_retry(tmp_path):
    called = []
    def denied(api, params, key):
        called.append((api, params["ts_code"]))
        v = fake(api, params, key)
        if len(called) == 3:
            v["http_status"] = 403
        return v
    root = tmp_path / "denied"
    r = s.capture(root, env(), transport=denied)
    assert r["status"] == "STOPPED_AT_2"
    assert len(called) == 3 and len(r["calls"]) == 3
    assert s.verify(root)["capture_status"] == "STOPPED_AT_2"
    assert not list((root / "prices").iterdir())

def test_credential_identity_and_scope(tmp_path):
    with pytest.raises(ValueError, match="EXECUTION_IDENTITY"):
        s.capture(tmp_path / "wrong", {**env(), "GITHUB_REF": "refs/heads/foo"}, transport=fake)
    with pytest.raises(ValueError, match="SOURCE_AUTH_UNAVAILABLE"):
        s.capture(tmp_path / "no-key", {**env(), "TUSHARE_PROXY_API_KEY": ""}, transport=fake)
    assert len(s.plan()) == 28
    assert len(s.SYMBOLS) == 14
    assert all(x["params"]["end_date"] == "20260930" for x in s.plan())

def test_reject_truncation_wrong_symbol_bad_hsl():
    spec = s.plan()[0]
    raw = body("daily", "000002.SZ")
    with pytest.raises(ValueError, match="SYMBOL_MISMATCH"):
        s.rows(raw, spec)
    with pytest.raises(ValueError, match="COUNT_MISMATCH"):
        s.rows(body("daily", "000001.SZ", bad=True), spec)
    spec = s.plan()[1]
    b = json.loads(body("daily_basic", "000001.SZ"))
    b["data"]["items"][0][2] = "-3"
    with pytest.raises(ValueError, match="NUM_RANGE"):
        s.rows(json.dumps(b).encode(), spec)

def test_missing_hsl_remains_blank():
    raw = {}
    for i, spec in enumerate(s.plan()):
        if spec["api"] == "daily_basic":
            b = json.loads(body(spec["api"], spec["params"]["ts_code"]))
            b["data"]["items"] = []; b["data"]["count"] = 0
            raw[i] = json.dumps(b).encode()
        else:
            raw[i] = body(spec["api"], spec["params"]["ts_code"])
    csvs, coverage = s.normalized(raw)
    assert "100000,,000151.SZ" in csvs["000151.csv"].decode()
    assert all(x["matched_hsl"] == 0 for x in coverage)


def test_clock_must_be_ordered_and_replay_checks_it(tmp_path):
    def backwards(api, params, key):
        r = fake(api, params, key)
        if params["ts_code"] == "000002.SZ":
            r["requested_at"] = "2026-10-08T00:00:00Z"
        return r
    root = tmp_path / "clock"
    r = s.capture(root, env(), transport=backwards)
    assert r["status"] == "STOPPED_AT_2"
    assert s.verify(root)["capture_status"] == r["status"]
    good = tmp_path / "good"
    s.capture(good, env(), transport=fake)
    receipt = json.loads((good / "receipt.json").read_text())
    receipt["calls"][1]["received_at"] = "2026-10-08T00:00:00Z"
    (good / "receipt.json").write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="RECEIPT_CLOCK_ORDER"):
        s.verify(good)
