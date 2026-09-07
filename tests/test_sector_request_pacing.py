"""Synthetic socket-boundary tests, never provider quota or live acceptance proof."""
from __future__ import annotations

import io
import json
import socket
from datetime import timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlsplit

import pytest

from decision_kernel.runtime import hithink_http as http
from decision_kernel.runtime import hithink_index_http as indices
from decision_kernel.runtime import hithink_sector_breadth_http as breadth
from decision_kernel.runtime import sector_radar_audit as audit
from decision_kernel.runtime.sector_parent_hints import parse_sector_parent_hints
from decision_kernel.runtime.sector_radar_producer import (
    SECTOR_RADAR_WORKFLOW_PATH, SectorRadarProducerContext,
)
from test_sector_radar_audit import (
    OBSERVED, REPOSITORY, SyntheticProvider, execute, hints_json, resolution,
)


class Clock:
    def __init__(self):
        self.seconds = 0.0
        self.waits = []

    def monotonic(self):
        return self.seconds

    def sleep(self, seconds):
        assert seconds > 0
        self.waits.append(seconds)
        self.seconds += seconds


def forbidden(*args, **kwargs):
    raise AssertionError("unexpected network access or offline wait")


@pytest.fixture
def clock(monkeypatch):
    value = Clock()
    monkeypatch.setenv(http.HITHINK_SECTOR_PACING_ENV, "1")
    monkeypatch.setattr(http, "_sector_request_finished_at", None)
    monkeypatch.setattr(http, "_sector_rate_limited", False)
    monkeypatch.setattr(http.time, "monotonic", value.monotonic)
    monkeypatch.setattr(http.time, "sleep", value.sleep)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(http, "urlopen", forbidden)
    return value


def request(path=http.HITHINK_CALENDAR_PATH, params=None):
    return http._request_hithink_json(
        api_key="pytest-private-canary", path=path,
        params={} if params is None else params, timeout_seconds=10.0,
    )


def stub_success(monkeypatch, clock, starts):
    def open_response(req, *, timeout):
        starts.append(clock.seconds)
        assert timeout == 10.0
        clock.seconds += 3.0
        return io.BytesIO(b'{"code":0,"data":{}}')
    monkeypatch.setattr(http, "urlopen", open_response)


def test_first_request_is_immediate_and_completed_response_gap_counts_work(monkeypatch, clock):
    starts = []
    stub_success(monkeypatch, clock, starts)
    request()
    request()
    clock.seconds += 7.0
    request()
    clock.seconds += 21.0
    request()
    assert http.HITHINK_SECTOR_REQUEST_GAP_SECONDS == 20.0
    assert starts == [0.0, 23.0, 46.0, 70.0]
    assert clock.waits == [20.0, 13.0]


def test_other_workflows_keep_existing_transport_behavior(monkeypatch, clock):
    monkeypatch.delenv(http.HITHINK_SECTOR_PACING_ENV)
    starts = []
    stub_success(monkeypatch, clock, starts)
    request()
    request()
    assert starts == [0.0, 3.0]
    assert clock.waits == []


def test_invalid_opt_in_is_rejected_before_network_without_echoing_value(monkeypatch, clock):
    monkeypatch.setenv(http.HITHINK_SECTOR_PACING_ENV, "invalid-private-value")
    with pytest.raises(http.HithinkRuntimeError) as exc:
        request()
    assert "invalid-private-value" not in str(exc.value)
    assert clock.waits == []


def test_429_preserves_diagnostic_and_prevents_even_caught_in_process_retry(monkeypatch, clock):
    calls = []
    def limited(req, *, timeout):
        calls.append(req.full_url)
        raise HTTPError(req.full_url, 429, "provider text not retained", {"Retry-After": "3600"}, None)
    monkeypatch.setattr(http, "urlopen", limited)
    with pytest.raises(http.HithinkRuntimeError, match="status 429; Retry-After=3600") as exc:
        request()
    assert "pytest-private-canary" not in str(exc.value)
    with pytest.raises(http.HithinkRuntimeError, match="stopped after HTTP 429"):
        request()
    assert len(calls) == 1
    assert clock.waits == []


def test_non_429_error_is_not_automatically_retried(monkeypatch, clock):
    calls = []
    def failed(req, *, timeout):
        calls.append(req.full_url)
        raise HTTPError(req.full_url, 503, "synthetic failure", {}, None)
    monkeypatch.setattr(http, "urlopen", failed)
    with pytest.raises(http.HithinkRuntimeError, match="status 503"):
        request()
    assert len(calls) == 1
    assert clock.waits == []


def live_wiring(tmp_path, monkeypatch, clock, *, fail_path=None):
    """Real producer/adapters, but fake socket, credential, calendar and prices.

    The LIVE branch here tests the workflow's default transport wiring only.
    Every file is temporary; no market request or remote state publication occurs.
    """
    restored = resolution()
    provider = SyntheticProvider(restored, jump=True)
    starts = []
    def open_response(req, *, timeout):
        parsed = urlsplit(req.full_url)
        params = dict(parse_qsl(parsed.query))
        starts.append((parsed.path, params, clock.seconds))
        assert timeout == 10.0
        clock.seconds += 1.0
        if parsed.path == fail_path:
            raise HTTPError(req.full_url, 429, "synthetic throttle", {}, None)
        if parsed.path == breadth.HITHINK_A_SHARE_SNAPSHOT_PATH:
            # Independently construct TWO valid fixture pages, not repaired real data.
            offset, limit, total = int(params["offset"]), int(params["limit"]), 501
            rows = [{"thscode": f"{600001 + i:06d}.SH", "ticker": f"{600001 + i:06d}",
                     "last_price": "103", "prev_price": "100", "turnover": "1000"}
                    for i in range(offset, min(offset + limit, total))]
            envelope = {"code": 0, "data": {"timestamp": int((OBSERVED - timedelta(minutes=30)).timestamp() * 1000),
                                             "total": total, "item": rows}}
        else:
            envelope = provider(parsed.path, params)
        return io.BytesIO(json.dumps(envelope).encode("utf-8"))
    monkeypatch.setattr(http, "urlopen", open_response)
    raw_hints = hints_json()
    def run():
        return audit.run_audited_sector_radar_producer(
            resolution=restored, parent_hints=parse_sector_parent_hints(raw_hints),
            parent_hints_json=raw_hints,
            context=SectorRadarProducerContext(REPOSITORY, SECTOR_RADAR_WORKFLOW_PATH, 301, 1, "a" * 40, OBSERVED),
            state_directory=tmp_path / "state", output_directory=tmp_path / "run",
            api_key="pytest-private-canary",
            now=lambda: OBSERVED + timedelta(seconds=clock.seconds),
            capture_now=lambda: OBSERVED + timedelta(seconds=clock.seconds),
        )
    return run, starts, restored


def forbid_live_and_waits(monkeypatch):
    monkeypatch.setattr(http, "urlopen", forbidden)
    monkeypatch.setattr(http, "_request_hithink_json", forbidden)
    monkeypatch.setattr(http.time, "sleep", forbidden)


def test_audited_default_wiring_paces_all_routes_and_both_pages_and_replays(tmp_path, monkeypatch, clock):
    run, starts, restored = live_wiring(tmp_path, monkeypatch, clock)
    outcome = run()
    paths = [path for path, _, _ in starts]
    assert paths[:4] == [http.HITHINK_CALENDAR_PATH, indices.HITHINK_INDEX_CATALOG_PATH,
                         indices.HITHINK_INDEX_SNAPSHOT_PATH, indices.HITHINK_INDEX_HISTORY_PATH]
    assert paths[4:6] == [breadth.HITHINK_SECTOR_CONSTITUENTS_PATH] * 2
    assert paths[6:] == [breadth.HITHINK_A_SHARE_SNAPSHOT_PATH] * 2
    assert [row[1]["offset"] for row in starts[6:]] == ["0", "500"]
    assert [row[2] for row in starts] == [21.0 * i for i in range(8)]
    assert clock.waits == [20.0] * 7
    assert outcome.persistent_bundle.market_state.sessions[-1] > restored.market_state.sessions[-1]
    root = tmp_path / "run/input-audit"
    manifest = audit.validate_sector_radar_input_audit(root)
    assert len(manifest["requests"]) == 8
    assert [r["captured_at"] for r in manifest["requests"]] == [
        (OBSERVED + timedelta(seconds=21 * i + 1)).isoformat() for i in range(8)
    ]
    forbid_live_and_waits(monkeypatch)
    report = audit.replay_sector_radar_input_audit(root)
    assert report["status"] == "MATCHED_SUCCEEDED"
    assert report["network_calls"] == report["production_state_writes"] == 0


@pytest.mark.parametrize("fail_path", [http.HITHINK_CALENDAR_PATH, indices.HITHINK_INDEX_CATALOG_PATH])
def test_audited_429_stops_and_keeps_previous_state_bytes(tmp_path, monkeypatch, clock, fail_path):
    run, starts, _ = live_wiring(tmp_path, monkeypatch, clock, fail_path=fail_path)
    target = tmp_path / "state"
    target.mkdir()
    before = {"market-state.json": b"previous state", "candidate-events.json": b"previous ledger",
              "manifest.json": b"previous manifest"}
    for name, data in before.items():
        (target / name).write_bytes(data)
    with pytest.raises(audit.SectorRadarAuditError, match="status 429"):
        run()
    assert len(starts) == (1 if fail_path == http.HITHINK_CALENDAR_PATH else 2)
    assert {p.name: p.read_bytes() for p in target.iterdir()} == before
    root = tmp_path / "run/input-audit"
    assert audit.validate_sector_radar_input_audit(root)["status"] == "REJECTED"
    forbid_live_and_waits(monkeypatch)
    assert audit.replay_sector_radar_input_audit(root)["status"] == "MATCHED_REJECTED"


def test_synthetic_capture_and_replay_never_enter_opted_in_transport(tmp_path, monkeypatch, clock):
    forbid_live_and_waits(monkeypatch)
    _, _, root = execute(tmp_path)
    assert clock.waits == []
    assert audit.replay_sector_radar_input_audit(root)["status"] == "MATCHED_SUCCEEDED"


def test_only_sector_capture_step_enables_pacing():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/sector-radar-shadow.yml").read_text()
    capture = workflow.split("- name: Run independent Sector Radar shadow producer", 1)[1].split("- name: Verify exact offline replay", 1)[0]
    assert 'HITHINK_SECTOR_REQUEST_PACING: "1"' in capture
    assert workflow.count("HITHINK_SECTOR_REQUEST_PACING") == 1
    assert "timeout-minutes: 20" in workflow
    assert "cancel-in-progress: false" in workflow
    for path in (root / ".github/workflows").glob("*.yml"):
        if path.name != "sector-radar-shadow.yml":
            assert "HITHINK_SECTOR_REQUEST_PACING" not in path.read_text()
