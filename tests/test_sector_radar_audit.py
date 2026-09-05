from __future__ import annotations

import copy
import json
import shutil
import socket
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.hithink_index import normalize_hithink_industry_catalog
from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import hithink_http, hithink_index_http, hithink_sector_breadth_http
from decision_kernel.runtime import sector_radar_audit as audit
from decision_kernel.runtime.sector_parent_hints import parse_sector_parent_hints
from decision_kernel.runtime.sector_radar import SectorPricePoint, SectorPriceSeries
from decision_kernel.runtime.sector_radar_events import create_sector_radar_candidate_event_ledger
from decision_kernel.runtime.sector_radar_persistence import (
    SOURCE_COMMITTED_BOOTSTRAP,
    SOURCE_LATEST_SUCCESS_ARTIFACT,
    SectorRadarPersistenceResolution,
    load_sector_radar_persistent_bundle,
    resolve_sector_radar_persistence,
)
from decision_kernel.runtime.sector_radar_producer import (
    PRODUCER_STATUS_APPENDED_QUIET,
    PRODUCER_STATUS_APPENDED_WITH_CANDIDATES,
    PRODUCER_STATUS_VALIDATED_ALREADY_CURRENT,
    SECTOR_RADAR_WORKFLOW_PATH,
    SectorRadarProducerContext,
)
from decision_kernel.runtime.sector_radar_state import (
    SectorRadarStateSourceLineage,
    create_sector_radar_market_state,
)


TZ = ZoneInfo("Asia/Shanghai")
FRIDAY = date(2026, 9, 4)
MONDAY = date(2026, 9, 7)
TUESDAY = date(2026, 9, 8)
OBSERVED = datetime.combine(MONDAY, time(16), tzinfo=TZ)
PRODUCED = OBSERVED + timedelta(minutes=5)
CREATED = datetime.combine(FRIDAY, time(16), tzinfo=TZ)
REPOSITORY = "auguspp/decision-kernel"
# Synthetic weekday calendar: fixture data, not an exchange-calendar source.
SESSIONS = tuple(
    FRIDAY - timedelta(days=index)
    for index in reversed(range(220))
    if (FRIDAY - timedelta(days=index)).weekday() < 5
)[-127:]
IDENTITIES = (
    ("881101.TI", "Synthetic broad one", "0.3"),
    ("881102.TI", "Synthetic broad two", "0.4"),
    ("884001.TI", "Synthetic child one", "0.5"),
    ("884275.TI", "Synthetic child two", "0.6"),
)
STEPS = {code: Decimal(step) for code, _, step in IDENTITIES}
STEPS["000300.SH"] = Decimal("0.2")


def ms(session: date, hour: int = 15, minute: int = 30) -> int:
    return int(datetime.combine(session, time(hour, minute), tzinfo=TZ).timestamp() * 1000)


def catalog_envelope():
    return {"code": 0, "data": {"timestamp": ms(MONDAY), "item": [
        {"thscode": code, "name": name} for code, name, _ in IDENTITIES
    ]}}


def hints_json():
    catalog = normalize_hithink_industry_catalog(catalog_envelope())
    start, end = "2026-09-04T15:30:00+08:00", "2026-09-04T16:00:00+08:00"
    hints = []
    for child_index, parent_index in ((2, 0), (3, 1)):
        child, child_name, _ = IDENTITIES[child_index]
        parent, parent_name, _ = IDENTITIES[parent_index]
        hints.append({
            "child_thscode": child, "child_name": child_name,
            "child_member_count_at_capture": 1,
            "child_constituent_set_hash_at_capture": "c" * 64,
            "child_membership_captured_at": start,
            "parent_thscode": parent, "parent_name": parent_name,
            "parent_member_count_at_capture": 2,
            "parent_constituent_set_hash_at_capture": "d" * 64,
            "parent_membership_captured_at": start,
            "intersection_count_at_capture": 1, "child_fully_contained_at_capture": True,
        })
    payload = {
        "schema_version": 1, "captured_at": end,
        "membership_capture_window": {"start": start, "end": end},
        "source": "SYNTHETIC_TEST_ONLY", "source_workflow_run_id": 1,
        "source_artifact_id": 2, "source_artifact_digest": "sha256:" + "a" * 64,
        "source_result_hash": "b" * 64, "catalog_hash": catalog.catalog_hash,
        "catalog_shape": {"broad_881": 2, "granular_884": 2},
        "mapping_result": {
            "unique_full_containment": 2, "ambiguous": 0, "unmapped": 0,
            "exact_duplicate_granular_member_sets": 0, "overlapping_broad_member_sets": 0,
            "parents_with_granular_children": 2, "broad_parents_without_granular_children": 0,
        },
        "parent_hints": hints,
        "use_semantics": {
            "purpose": "CURRENT_PARENT_HINT_FOR_CANDIDATE_TIME_REVALIDATION",
            "catalog_rule": "CURRENT_CATALOG_IDENTITY_AND_HASH_MUST_BE_CHECKED_EXPLICITLY",
            "membership_rule": "FETCH_CANDIDATE_CHILD_AND_HINTED_PARENT_CURRENT_MEMBERSHIPS_AND_REVALIDATE_FULL_CONTAINMENT_BEFORE_GROUPING",
            "failure_rule": "CATALOG_OR_CONTAINMENT_DRIFT_REMAINS_VISIBLE_AND_PREVENTS_AUTOMATIC_GROUPING",
            "historical_taxonomy_authority": "NONE", "research_authority": "NONE",
            "human_attention_authority": "NONE", "investment_authority": "NONE",
        },
    }
    payload["mapping_hash"] = canonical_hash(payload)
    return json.dumps(payload)


def resolution():
    def series(code, name, step):
        return SectorPriceSeries(thscode=code, name=name, points=tuple(
            SectorPricePoint(session=day, close=Decimal(100) + Decimal(step) * index, turnover=Decimal(1000 + index))
            for index, day in enumerate(SESSIONS)
        ))
    state = create_sector_radar_market_state(
        catalog=normalize_hithink_industry_catalog(catalog_envelope()),
        benchmark=series("000300.SH", "Synthetic benchmark", "0.2"),
        broad_series=tuple(series(*row) for row in IDENTITIES[:2]),
        granular_series=tuple(series(*row) for row in IDENTITIES[2:]),
        created_at=CREATED, source="SYNTHETIC_TEST_ONLY",
        source_lineage=(SectorRadarStateSourceLineage(
            role="SYNTHETIC_TEST_ONLY", workflow_run_id=1, artifact_id=2,
            artifact_digest="sha256:" + "a" * 64, result_hash="b" * 64,
        ),),
    )
    return SectorRadarPersistenceResolution(
        source_kind=SOURCE_COMMITTED_BOOTSTRAP, market_state=state,
        event_ledger=create_sector_radar_candidate_event_ledger(created_at=CREATED, source="SYNTHETIC_TEST_ONLY"),
        source_bundle_manifest=None, bootstrap_manifest_hash="a" * 64,
    )


class SyntheticProvider:
    """Only HTTP-shaped fixture responses; real adapters, ranks and gates run."""
    def __init__(self, restored, *, session=MONDAY, jump=True, failure=None):
        self.restored, self.session = restored, session
        self.jump, self.failure = jump, failure
        self.calls = []
        self.same_session = session == restored.market_state.sessions[-1]
        self.rows = {}
        for series in restored.market_state.series:
            if self.same_session:
                previous, last = series.closes[-2:]
                turnover = series.turnovers[-1]
            else:
                previous = series.closes[-1]
                extra = Decimal(20) if jump and series.thscode in {"881101.TI", "884001.TI"} else Decimal(0)
                last = previous + STEPS[series.thscode] + extra
                turnover = series.turnovers[-1] + Decimal(10)
            change = last - previous
            self.rows[series.thscode] = {
                "thscode": series.thscode,
                "ticker": "1B0300" if series.thscode == "000300.SH" else series.thscode[:6],
                "last_price": str(last), "prev_price": str(previous),
                "price_change": str(change), "price_change_ratio_pct": str(change / previous * Decimal(100)),
                "open_price": str(previous), "high_price": str(max(last, previous) + 1),
                "low_price": str(min(last, previous) - 1), "volume": "100", "turnover": str(turnover),
            }

    def __call__(self, path, params):
        self.calls.append((path, dict(params)))
        if path == hithink_http.HITHINK_CALENDAR_PATH:
            sessions = self.restored.market_state.sessions
            additions = tuple(day for day in (MONDAY, TUESDAY) if sessions[-1] < day <= self.session)
            return {"code": 0, "data": {"item": [{"date": day.strftime("%Y%m%d")} for day in (*sessions, *additions)]}}
        if path == hithink_index_http.HITHINK_INDEX_CATALOG_PATH:
            envelope = catalog_envelope()
            if self.failure == "catalog":
                envelope["data"]["item"][0]["name"] += " changed"
            return envelope
        if path == hithink_index_http.HITHINK_INDEX_SNAPSHOT_PATH:
            rows = [copy.deepcopy(self.rows[code]) for code in params["thscodes"].split(",")]
            if self.failure == "continuity":
                next(row for row in rows if row["thscode"] == "881101.TI")["prev_price"] = "1"
            return {"code": 0, "data": {"timestamp": ms(self.session), "total": len(rows), "item": rows}}
        if path == hithink_index_http.HITHINK_INDEX_HISTORY_PATH:
            code = params["thscode"]
            dates = (self.restored.market_state.sessions[-2], self.session) if self.same_session else (self.restored.market_state.sessions[-1], self.session)
            prices = (self.rows[code]["prev_price"], self.rows[code]["last_price"])
            return {"code": 0, "data": {
                "thscode": code, "interval": "1d", "adjust": None, "timestamp": ms(self.session, 0, 0),
                "item": [{"date_ms": ms(day, 0, 0), "close_price": price, "volume": "100", "turnover": "1000"} for day, price in zip(dates, prices)],
            }}
        if path == hithink_sector_breadth_http.HITHINK_SECTOR_CONSTITUENTS_PATH:
            if self.failure == "transport":
                raise hithink_http.HithinkRuntimeError("synthetic transport interruption")
            codes = {
                "881101.TI": ["600001.SH", "600002.SH"],
                "884001.TI": ["600003.SH"] if self.failure == "containment" else ["600001.SH"],
            }[params["thscode"]]
            return {"code": 0, "data": {"timestamp": ms(self.session), "item": [
                {"thscode": code, "ticker": code[:6], "name": "Synthetic company"} for code in codes
            ]}}
        if path == hithink_sector_breadth_http.HITHINK_A_SHARE_SNAPSHOT_PATH:
            total = 501 if self.failure == "pagination" else 3
            offset, limit = int(params["offset"]), int(params["limit"])
            rows = [{
                "thscode": f"{600001 + index:06d}.SH", "ticker": f"{600001 + index:06d}",
                "last_price": "103", "prev_price": None if self.failure == "breadth" else "100", "turnover": "1000",
            } for index in range(offset, min(offset + limit, total))]
            if offset and self.failure == "pagination":
                rows[0]["thscode"], rows[0]["ticker"] = "600001.SH", "600001"
            return {"code": 0, "data": {"timestamp": ms(self.session), "total": total, "item": rows}}
        raise AssertionError(f"unplanned fixture endpoint: {path}")


def execute(tmp_path, *, restored=None, session=MONDAY, jump=True, failure=None, run_id=101):
    restored = restored or resolution()
    provider = SyntheticProvider(restored, session=session, jump=jump, failure=failure)
    observed_at = datetime.combine(session, time(16), tzinfo=TZ)
    if restored.source_bundle_manifest is not None:
        observed_at += timedelta(minutes=10)
    context = SectorRadarProducerContext(
        repository=REPOSITORY, workflow_path=SECTOR_RADAR_WORKFLOW_PATH,
        run_id=run_id, run_attempt=1, commit_sha="a" * 40, observed_at=observed_at,
    )
    raw_hints = hints_json()
    outcome = audit.run_audited_sector_radar_producer(
        resolution=restored, parent_hints=parse_sector_parent_hints(raw_hints),
        parent_hints_json=raw_hints, context=context,
        state_directory=tmp_path / "live-state", output_directory=tmp_path / "run",
        api_key="fixture-credential-do-not-retain", request_json=provider,
        provenance=audit.SYNTHETIC_PROVENANCE,
        now=lambda: observed_at + timedelta(minutes=5), capture_now=lambda: observed_at,
    )
    return outcome, provider, tmp_path / "run" / "input-audit"


def prohibit_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("offline replay attempted network access")
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(hithink_http, "_request_hithink_json", denied)
    monkeypatch.setattr(hithink_http, "_request_hithink_calendar", denied)


@pytest.mark.parametrize("jump", [False, True])
def test_real_next_session_pipeline_replays_all_outputs_without_network(tmp_path, monkeypatch, jump):
    restored = resolution()
    outcome, provider, root = execute(tmp_path, restored=restored, jump=jump)
    assert outcome.status == (PRODUCER_STATUS_APPENDED_WITH_CANDIDATES if jump else PRODUCER_STATUS_APPENDED_QUIET)
    assert outcome.persistent_bundle.market_state.sessions[-1] == MONDAY
    assert len(outcome.persistent_bundle.market_state.sessions) == 127
    assert outcome.persistent_bundle.market_state.sessions[:-1] == restored.market_state.sessions[1:]
    assert outcome.result is not None
    assert not (tmp_path / "live-state").exists(), "synthetic state must not publish to the live target"
    calls = [path for path, _ in provider.calls]
    assert calls.count(hithink_http.HITHINK_CALENDAR_PATH) == 1
    assert calls.count(hithink_index_http.HITHINK_INDEX_SNAPSHOT_PATH) == 1
    assert calls.count(hithink_index_http.HITHINK_INDEX_HISTORY_PATH) == 1
    assert calls.count(hithink_sector_breadth_http.HITHINK_SECTOR_CONSTITUENTS_PATH) == (2 if jump else 0)
    assert calls.count(hithink_sector_breadth_http.HITHINK_A_SHARE_SNAPSHOT_PATH) == (1 if jump else 0)
    if jump:
        assert {event.candidate.thscode for event in outcome.persistent_bundle.event_ledger.events} == {"881101.TI", "884001.TI"}
        assert len(outcome.result.composition.all_groups) == 1
        assert outcome.result.composition.all_groups[0].primary_candidate.thscode == "881101.TI"
        assert len(outcome.result.parent_revalidations) == 1
        assert len(outcome.result.breadth_observations) == 2
        assert len(outcome.result.composition.surfaced_groups) <= 3
    else:
        assert outcome.persistent_bundle.event_ledger.events == ()
    observations = json.loads((root / "expected/output/observations.json").read_text())
    digest = observations.pop("observation_audit_hash")
    assert canonical_hash(observations) == digest
    assert len(observations["decisions"]) == 4
    assert {row["family"] for row in observations["decisions"]} == {"BROAD_881", "GRANULAR_884"}
    prohibit_network(monkeypatch)
    report = audit.replay_sector_radar_input_audit(root)
    assert report["status"] == "MATCHED_SUCCEEDED"
    assert report["network_calls"] == report["production_state_writes"] == 0
    assert report["provenance"] == "SYNTHETIC_TEST_ONLY"
    assert audit.replay_sector_radar_input_audit(root) == report


def test_restore_then_same_session_does_not_repeat_real_candidate_entries(tmp_path, monkeypatch):
    first, _, root = execute(tmp_path / "first")
    state = root / "expected/state"
    artifact, cache = tmp_path / "artifact", tmp_path / "cache"
    shutil.copytree(state, artifact)
    shutil.copytree(state, cache)
    restored = resolve_sector_radar_persistence(
        cache_directory=cache, artifact_directory=artifact,
        prior_success_found=True, artifact_available=True,
        bootstrap_path=tmp_path / "must-not-read-bootstrap",
        bootstrap_manifest_path=tmp_path / "must-not-read-bootstrap-manifest",
        observed_at=PRODUCED + timedelta(minutes=1),
        expected_repository=REPOSITORY, expected_workflow=SECTOR_RADAR_WORKFLOW_PATH,
        expected_parent_hint_mapping_hash=parse_sector_parent_hints(hints_json()).mapping_hash,
    )
    assert restored.source_kind == SOURCE_LATEST_SUCCESS_ARTIFACT
    before = {name: (artifact / name).read_bytes() for name in ("market-state.json", "candidate-events.json")}
    second, provider, second_root = execute(tmp_path / "second", restored=restored, run_id=102)
    assert second.status == PRODUCER_STATUS_VALIDATED_ALREADY_CURRENT
    assert second.persistent_bundle.market_state == first.persistent_bundle.market_state
    assert second.persistent_bundle.event_ledger == first.persistent_bundle.event_ledger
    assert len(second.persistent_bundle.event_ledger.events) == 2
    assert second.result is None
    assert not any("constituents" in path or path == hithink_sector_breadth_http.HITHINK_A_SHARE_SNAPSHOT_PATH for path, _ in provider.calls)
    for name, data in before.items():
        assert (second_root / "expected/state" / name).read_bytes() == data
    prohibit_network(monkeypatch)
    assert audit.replay_sector_radar_input_audit(second_root)["status"] == "MATCHED_SUCCEEDED"


def test_continued_active_market_does_not_emit_even_without_ledger_memory(tmp_path):
    first, _, _ = execute(tmp_path / "first")
    bundle = first.persistent_bundle
    with_ledger = SectorRadarPersistenceResolution(
        source_kind=SOURCE_LATEST_SUCCESS_ARTIFACT, market_state=bundle.market_state,
        event_ledger=bundle.event_ledger, source_bundle_manifest=bundle.manifest,
        bootstrap_manifest_hash=None,
    )
    continued, provider, _ = execute(tmp_path / "continued", restored=with_ledger,
        session=TUESDAY, jump=False, run_id=102)
    assert continued.status == PRODUCER_STATUS_APPENDED_QUIET
    assert continued.persistent_bundle.event_ledger == bundle.event_ledger
    # A deliberately independent synthetic input demonstrates selection authority:
    # the same market snapshots with an empty ledger still have no state entry.
    without_ledger = replace(resolution(), market_state=bundle.market_state)
    independent, _, _ = execute(tmp_path / "independent", restored=without_ledger,
        session=TUESDAY, jump=False, run_id=103)
    assert independent.status == PRODUCER_STATUS_APPENDED_QUIET
    assert independent.persistent_bundle.event_ledger.events == ()
    assert continued.result.composition == independent.result.composition
    assert not any("constituents" in path for path, _ in provider.calls)


@pytest.mark.parametrize("failure", ["continuity", "catalog", "containment", "breadth", "pagination", "transport", "gap"])
def test_rejected_inputs_keep_previous_files_and_replay_failure(tmp_path, monkeypatch, failure):
    target = tmp_path / "live-state"
    target.mkdir()
    previous = {"market-state.json": b"original-market", "candidate-events.json": b"original-ledger", "manifest.json": b"original-manifest"}
    for name, value in previous.items():
        (target / name).write_bytes(value)
    with pytest.raises(audit.SectorRadarAuditError, match="rejected input"):
        execute(tmp_path, failure=failure, session=TUESDAY if failure == "gap" else MONDAY)
    assert {path.name: path.read_bytes() for path in target.iterdir()} == previous
    root = tmp_path / "run/input-audit"
    manifest = audit.validate_sector_radar_input_audit(root)
    assert manifest["status"] == "REJECTED"
    assert not any(name.startswith("expected/state/") for name in manifest["files"])
    if failure in {"containment", "breadth", "pagination", "transport"}:
        assert "expected/output/observations.json" in manifest["files"]
    prohibit_network(monkeypatch)
    assert audit.replay_sector_radar_input_audit(root)["status"] == "MATCHED_REJECTED"


@pytest.mark.parametrize("change", ["bytes", "missing", "extra", "symlink", "manifest", "code"])
def test_replay_rejects_incomplete_or_tampered_audit_before_network(tmp_path, monkeypatch, change):
    _, _, root = execute(tmp_path, jump=False)
    path = root / "responses/0000.json"
    if change == "bytes":
        data = path.read_bytes()
        path.write_bytes(data.replace(b"2026", b"2025", 1))
    elif change == "missing":
        path.unlink()
    elif change == "extra":
        (root / "unknown.json").write_text("{}")
    elif change == "symlink":
        path.unlink()
        path.symlink_to(tmp_path / "outside")
    elif change == "manifest":
        manifest = json.loads((root / "manifest.json").read_text())
        manifest["provenance"] = "changed"
        (root / "manifest.json").write_text(json.dumps(manifest))
    else:
        monkeypatch.setattr(audit, "_implementation", lambda: {"changed": "a" * 64})
    prohibit_network(monkeypatch)
    with pytest.raises(audit.SectorRadarAuditError):
        audit.replay_sector_radar_input_audit(root)


def test_replay_checks_transcript_order_even_with_rehashed_manifest(tmp_path, monkeypatch):
    _, _, root = execute(tmp_path, jump=False)
    path = root / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["requests"][1]["params"]["tag"] = "concept"
    manifest.pop("audit_hash")
    manifest["audit_hash"] = canonical_hash(manifest)
    path.write_text(json.dumps(manifest))
    prohibit_network(monkeypatch)
    with pytest.raises(audit.SectorRadarAuditError, match="order or parameters"):
        audit.replay_sector_radar_input_audit(root)


@pytest.mark.parametrize("payload", [{"api_key": "x"}, {"data": {"token": "x"}}, {"data": {"value": "fixture-credential-do-not-retain"}}])
def test_credentials_are_not_retained_in_raw_response_audit(tmp_path, payload):
    recorder = audit._Recorder(tmp_path / "audit", provenance=audit.SYNTHETIC_PROVENANCE,
        credential="fixture-credential-do-not-retain", capture_now=lambda: OBSERVED)
    request = recorder.request(lambda path, params: payload)
    with pytest.raises(audit.SectorRadarAuditError, match="credential"):
        request(hithink_http.HITHINK_CALENDAR_PATH, {})
    for path in recorder.root.rglob("*"):
        if path.is_file():
            assert b"fixture-credential-do-not-retain" not in path.read_bytes()
    assert not (recorder.root / "responses").exists()


def test_audit_request_and_byte_budgets_are_not_candidate_filters(tmp_path, monkeypatch):
    recorder = audit._Recorder(tmp_path / "audit", provenance=audit.SYNTHETIC_PROVENANCE,
        credential=None, capture_now=lambda: OBSERVED)
    calls = []
    request = recorder.request(lambda path, params: calls.append(path) or {"code": 0, "data": {"value": 1.25}})
    monkeypatch.setattr(audit, "MAX_REQUESTS", 1)
    request(hithink_http.HITHINK_CALENDAR_PATH, {})
    with pytest.raises(audit.SectorRadarAuditError, match="request budget"):
        request(hithink_http.HITHINK_CALENDAR_PATH, {})
    assert len(calls) == 1
    monkeypatch.setattr(audit, "MAX_FILE_BYTES", 1)
    with pytest.raises(audit.SectorRadarAuditError, match="byte budget"):
        recorder.add("inputs/context.json", b"{}")


def test_injected_transport_cannot_claim_live_provenance(tmp_path):
    restored = resolution()
    raw = hints_json()
    with pytest.raises(audit.SectorRadarAuditError, match="SYNTHETIC_TEST_ONLY"):
        audit.run_audited_sector_radar_producer(
            resolution=restored, parent_hints=parse_sector_parent_hints(raw), parent_hints_json=raw,
            context=SectorRadarProducerContext(REPOSITORY, SECTOR_RADAR_WORKFLOW_PATH, 1, 1, "a" * 40, OBSERVED),
            state_directory=tmp_path / "live-state", output_directory=tmp_path / "run",
            api_key="fixture", request_json=SyntheticProvider(restored),
        )
    assert not (tmp_path / "live-state").exists()
