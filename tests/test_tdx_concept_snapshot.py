from __future__ import annotations

import copy
import json
import socket
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import tdx_concept_snapshot as tdx

DAY = date(2026, 9, 24)
SHA = "a" * 40
WF = {
    "GITHUB_REPOSITORY": "auguspp/decision-kernel",
    "GITHUB_WORKFLOW": "tdx-concept-snapshot",
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_EVENT_NAME": "workflow_dispatch",
    "GITHUB_RUN_ID": "123456",
    "GITHUB_RUN_ATTEMPT": "1",
    "GITHUB_SHA": SHA,
}
ROOT = Path(__file__).resolve().parents[1]


def source_file_records():
    return [{"name": name, "bytes": 1, "sha256": "0" * 64} for name in sorted(tdx.SOURCE_FILES)]


def bars(offset=0, count=15):
    start = datetime(2026, 9, 4, 15, tzinfo=timezone(timedelta(hours=8)))
    # The exact calendar gaps are irrelevant to this source contract; the last
    # source timestamp is the declared completed session identity.
    points = []
    for i in range(count):
        when = start + timedelta(days=i)
        points.append({"time": when.isoformat(), "close": 100 + offset + i, "record_hex": f"{i:02x}"})
    points[-1]["time"] = "2026-09-24T15:00:00+08:00"
    # Keep strict monotonicity after forcing the target date.
    for i in range(count - 1):
        points[i]["time"] = (datetime(2026, 9, 4, 15, tzinfo=timezone(timedelta(hours=8)))
                              + timedelta(days=i)).isoformat()
    return points


def board(code, name, offset=0, count=15):
    rows = bars(offset, count)
    return {
        "source_order": 0,
        "board_code": code,
        "board_name": name,
        "full_code": "sh" + code,
        "snapshot": {"last_price": rows[-1]["close"], "pre_close_price": rows[-2]["close"], "tail_raw": "00"},
        "bars": rows,
    }


def source(*, short_second=False, name="Concept A"):
    first = board("880001", name, 0, 15)
    second = board("880002", "Concept B", 20, 6 if short_second else 15)
    second["source_order"] = 1
    return {
        "source_kind": "ELTDX_TDX_7709",
        "package_version": tdx.ELTDX_VERSION,
        "wheel_sha256": "1" * 64,
        "upstream_inspected_commit": tdx.UPSTREAM_INSPECTED,
        "chosen_host": "1.2.3.4:7709",
        "host_probes": [{"host": "1.2.3.4:7709", "ok": True, "latency_ms": 12.3, "error_type": None}],
        "protocol_attempts": [{
            "host": "1.2.3.4:7709",
            "started_at": "2026-09-25T04:00:00+00:00",
            "finished_at": "2026-09-25T04:00:01+00:00",
            "status": "CONNECTED",
            "error_type": None,
        }],
        "handshake": {"server_datetime": "2026-09-25T12:00:00+08:00", "server_name": "Synthetic TDX"},
        "prepared_date": DAY.isoformat(),
        "requested_market_session": DAY.isoformat(),
        "boards": [first, second],
        "source_file_records": source_file_records(),
        "raw_protocol_frames": tdx.POLICY["raw_protocol_frames"],
    }


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network forbidden in unit tests")
    monkeypatch.setattr(socket, "create_connection", forbidden)


def test_complete_source_builds_local_1_5_10_windows_and_no_eastmoney_requirement():
    report = tdx.build_observation(source(), DAY)
    p = report["projection"]
    assert p["status"] == "MATCHED_TDX_CONCEPT_CATALOG"
    assert p["catalog_count"] == 2
    assert p["coverage"]["history_5d_rows"] == p["coverage"]["history_10d_rows"] == 2
    assert p["coverage"]["eastmoney_required"] is False
    assert p["taxonomy"].startswith("TDX_CATEGORY_CONCEPT")
    assert p["source_calls_during_replay"] == 0
    assert p["investment_authority"] == "NONE"
    assert p["observations"][0]["periods"]["today"]["change_percent"] is not None
    assert p["observations"][0]["periods"]["5d"]["change_percent"] is not None
    assert p["observations"][0]["periods"]["10d"]["change_percent"] is not None


def test_newer_short_history_is_explicit_gap_not_zero_or_dropped():
    report = tdx.build_observation(source(short_second=True), DAY)
    p = report["projection"]
    assert p["status"] == "MATCHED_TDX_CURRENT_WITH_HISTORY_GAPS"
    assert p["coverage"]["history_5d_rows"] == 2
    assert p["coverage"]["history_10d_rows"] == 1
    row = p["observations"][1]
    assert row["periods"]["5d"]["change_percent"] is not None
    assert row["periods"]["10d"]["change_percent"] is None


@pytest.mark.parametrize("kind", ["prepared", "last_date", "snapshot", "duplicate"])
def test_session_identity_or_snapshot_mismatch_fails_closed(kind):
    value = source()
    if kind == "prepared":
        value["prepared_date"] = "2026-09-23"
    elif kind == "last_date":
        value["boards"][0]["bars"][-1]["time"] = "2026-09-23T15:00:00+08:00"
    elif kind == "snapshot":
        value["boards"][0]["snapshot"]["last_price"] += 1
    else:
        value["boards"][1]["board_code"] = value["boards"][0]["board_code"]
    with pytest.raises(ValueError):
        tdx.build_observation(value, DAY)


def test_source_order_and_source_native_names_are_preserved_without_taxonomy_translation():
    report = tdx.build_observation(source(name="网络安全 | <b>source</b>"), DAY)
    p = report["projection"]
    assert p["observations"][0]["name"] == "网络安全 | <b>source</b>"
    summary = tdx.render(report)
    assert "网络安全 &#124; &lt;b&gt;source&lt;/b&gt;" in summary
    assert "EASTMONEY" not in p["observations"][0]["code"]


def write_source_files(root: Path):
    source_dir = root / "source-files"
    source_dir.mkdir()
    for i, name in enumerate(sorted(tdx.SOURCE_FILES), 1):
        (source_dir / name).write_bytes((name + str(i)).encode())


def fake_source(root: Path, target: date):
    write_source_files(root)
    value = source()
    value["requested_market_session"] = target.isoformat()
    value["prepared_date"] = target.isoformat()
    return value


def test_capture_and_replay_are_create_only_and_network_free(tmp_path):
    out = tmp_path / "capture"
    now_values = iter([
        datetime(2026, 9, 25, 4, tzinfo=timezone.utc),
        datetime(2026, 9, 25, 4, 0, 1, tzinfo=timezone.utc),
    ])
    receipt = tdx.capture(
        out, market_session=DAY, workflow=WF, expected_code=SHA,
        source_fn=fake_source, now=lambda: next(now_values),
    )
    assert receipt["status"] == "CAPTURED_TDX_CONCEPT_SNAPSHOT"
    result = tdx.replay(out)
    assert result["projection"]["catalog_count"] == 2
    assert result["projection"]["source_calls_during_replay"] == 0
    assert set(x["name"] for x in json.loads((out / "source.json").read_text())["source_file_records"]) == tdx.SOURCE_FILES
    with pytest.raises(ValueError, match="CREATE_ONLY"):
        tdx.capture(out, market_session=DAY, workflow=WF, expected_code=SHA, source_fn=fake_source)


@pytest.mark.parametrize("name", ["source.json", "observation.json", "summary.md", "source-files/infoharbor_block.dat"])
def test_retained_tampering_rejected(name, tmp_path):
    out = tmp_path / "capture"
    now_values = iter([
        datetime(2026, 9, 25, 4, tzinfo=timezone.utc),
        datetime(2026, 9, 25, 4, 0, 1, tzinfo=timezone.utc),
    ])
    receipt = tdx.capture(
        out, market_session=DAY, workflow=WF, expected_code=SHA,
        source_fn=fake_source, now=lambda: next(now_values),
    )
    path = out / name
    path.write_bytes(path.read_bytes() + b"x")
    # Rehashing the outer receipt is not enough: replay still binds source files
    # and recomputes the observation/summary.
    receipt["files"] = tdx._inventory(out)
    receipt["capture_hash"] = canonical_hash({k: v for k, v in receipt.items() if k != "capture_hash"})
    (out / "capture.json").write_bytes(tdx._encoded(receipt))
    with pytest.raises(ValueError):
        tdx.replay(out)


def test_failed_source_retained_without_implicit_eastmoney_fallback(tmp_path):
    def fail(root, target):
        raise OSError("synthetic remote failure")
    out = tmp_path / "failed"
    now_values = iter([
        datetime(2026, 9, 25, 4, tzinfo=timezone.utc),
        datetime(2026, 9, 25, 4, 0, 1, tzinfo=timezone.utc),
    ])
    receipt = tdx.capture(
        out, market_session=DAY, workflow=WF, expected_code=SHA,
        source_fn=fail, now=lambda: next(now_values),
    )
    assert receipt["status"] == "INCOMPLETE_TDX_SOURCE_CAPTURE"
    assert receipt["reason_code"] == "SOURCE_UNAVAILABLE_OR_REJECTED"
    replay = tdx.replay(out)
    assert replay["source_calls_during_replay"] == 0
    assert "Eastmoney" in (out / "summary.md").read_text()


@pytest.mark.parametrize("key,value", [
    ("GITHUB_REF", "refs/heads/other"),
    ("GITHUB_RUN_ATTEMPT", "2"),
    ("GITHUB_EVENT_NAME", "push"),
    ("GITHUB_SHA", "b" * 40),
    ("GITHUB_WORKFLOW", "vibe-concept-snapshot"),
])
def test_wrong_execution_identity_rejected(key, value):
    with pytest.raises(ValueError, match="WORKFLOW_IDENTITY_REJECTED"):
        tdx.workflow_identity({**WF, key: value}, SHA)


def test_workflow_is_manual_read_only_keyless_and_pins_eltdx():
    text = (ROOT / ".github/workflows/tdx-concept-snapshot.yml").read_text()
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text and "workflow_run:" not in text
    assert "contents: read" in text and "actions: read" in text
    assert "contents: write" not in text and "secrets." not in text
    assert 'eltdx==3.2.2' in text
    assert "market-session:" in text and "code-sha:" in text
    assert "actions/workflows/ci.yml/runs" in text
    assert "tdx_concept_snapshot replay" in text


def test_vibe_stays_available_but_documented_secondary():
    text = (ROOT / "docs/vibe-concept-snapshot.md").read_text()
    assert "SECONDARY" in text
    assert "tdx-concept-snapshot" in text
