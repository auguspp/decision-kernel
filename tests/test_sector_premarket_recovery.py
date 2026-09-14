from __future__ import annotations

import json
from datetime import datetime, time

from decision_kernel.runtime import hithink_http, hithink_index_http
from test_sector_radar_audit import (
    FRIDAY,
    MONDAY,
    PRODUCER_STATUS_VALIDATED_ALREADY_CURRENT,
    REPOSITORY,
    SECTOR_RADAR_WORKFLOW_PATH,
    TZ,
    SectorRadarProducerContext,
    SyntheticProvider,
    audit,
    hints_json,
    parse_sector_parent_hints,
    prohibit_network,
    resolution,
)


def test_audited_sector_reuses_receipt_bound_premarket_carry_and_replays(tmp_path, monkeypatch):
    restored = resolution()
    base = SyntheticProvider(restored, session=FRIDAY, jump=False)
    ready = datetime.combine(MONDAY, time(7, 7, 48), tzinfo=TZ)
    captured = datetime.combine(MONDAY, time(7, 7, 49), tzinfo=TZ)
    qualified = datetime.combine(MONDAY, time(7, 7, 50), tzinfo=TZ)

    def provider(path, params):
        if path == hithink_http.HITHINK_CALENDAR_PATH:
            base.calls.append((path, dict(params)))
            sessions = (*restored.market_state.sessions, MONDAY)
            return {"code": 0, "data": {"item": [
                {"date": day.strftime("%Y%m%d")} for day in sessions
            ]}}
        value = base(path, params)
        if path == hithink_index_http.HITHINK_INDEX_SNAPSHOT_PATH:
            value["data"]["timestamp"] = int(ready.timestamp() * 1000)
        return value

    context = SectorRadarProducerContext(
        repository=REPOSITORY, workflow_path=SECTOR_RADAR_WORKFLOW_PATH,
        run_id=34907311896, run_attempt=1, commit_sha="a" * 40,
        observed_at=datetime.combine(MONDAY, time(7, 6, 44), tzinfo=TZ),
    )
    raw_hints = hints_json()
    outcome = audit.run_audited_sector_radar_producer(
        resolution=restored, parent_hints=parse_sector_parent_hints(raw_hints),
        parent_hints_json=raw_hints, context=context,
        state_directory=tmp_path / "live-state", output_directory=tmp_path / "run",
        api_key="fixture-credential-do-not-retain", request_json=provider,
        provenance=audit.SYNTHETIC_PROVENANCE, now=lambda: qualified,
        capture_now=lambda: captured,
    )
    assert outcome.status == PRODUCER_STATUS_VALIDATED_ALREADY_CURRENT
    assert outcome.persistent_bundle.market_state.sessions[-1] == FRIDAY
    root = tmp_path / "run" / "input-audit"
    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["status"] == "SUCCEEDED"
    assert len(manifest["run_clocks"]) >= 3
    prohibit_network(monkeypatch)
    replay = audit.replay_sector_radar_input_audit(root)
    assert replay["status"] == "MATCHED_SUCCEEDED"
    assert replay["network_calls"] == 0
