from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from decision_kernel.market import ObservedMarket
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import current_state_delivery as base
from decision_kernel.runtime import current_state_delivery_with_odds_watch as reading
from decision_kernel.runtime import odds_watch


ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
NOW = "2026-09-16T08:30:00Z"
OBSERVED = datetime(2026, 9, 16, 16, 30, tzinfo=ZoneInfo("Asia/Shanghai"))


def run():
    return {
        "id": 55,
        "repository": {"full_name": model.REPOSITORY},
        "head_repository": {"full_name": model.REPOSITORY},
        "path": model.WORKFLOWS["inbox"],
        "head_branch": "main",
        "head_sha": SHA,
        "event": "schedule",
        "run_attempt": 1,
        "status": "completed",
        "conclusion": "success",
        "created_at": "2026-09-16T08:20:00Z",
        "updated_at": "2026-09-16T08:30:00Z",
    }


def market(price: str):
    return ObservedMarket(
        market_price=Decimal(price),
        market_timestamp=datetime(2026, 9, 16, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        market_utc_offset_minutes=480,
        market_data_source="HiThink Financial-API raw daily close | synthetic-test",
        price_convention="RAW_UNADJUSTED_COMPLETED_A_SHARE_CLOSE",
        currency="CNY",
    )


def watch_report():
    config = json.loads((ROOT / reading.WATCH_CONFIG_PATH).read_text(encoding="utf-8"))
    registry = json.loads((ROOT / base.REGISTRY_PATH).read_text(encoding="utf-8"))
    prices = {
        "600276.SH": "42.5", "002674.SZ": "18", "600598.SH": "12.33",
        "002050.SZ": "31", "603986.SH": "360",
    }
    return odds_watch.build_watch(
        config=config,
        registry=registry,
        observed_at=OBSERVED,
        fetch_market=lambda *, thscode, observed_at: market(prices[thscode]),
    )


class API:
    def __init__(self, *, report=None, partial=False):
        self.value = run()
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w") as archive:
            archive.writestr("summary.md", "Synthetic saved delivery")
            archive.writestr("index.html", "<p>saved</p>")
            if report is not None:
                archive.writestr(reading.WATCH_JSON_PATH, odds_watch.canonical_json(report) + "\n")
                if not partial:
                    archive.writestr(reading.WATCH_SUMMARY_PATH, odds_watch.render_markdown(report))
        self.raw = memory.getvalue()
        self.artifact = {
            "id": 77,
            "name": "decision-inbox",
            "expired": False,
            "size_in_bytes": len(self.raw),
            "digest": "sha256:" + model.sha256(self.raw),
            "workflow_run": {"id": 55, "head_sha": SHA},
        }

    def get(self, endpoint):
        if endpoint.startswith("actions/workflows/"):
            return {"total_count": 1, "workflow_runs": [self.value]}
        if endpoint.endswith("/artifacts?per_page=100"):
            return {"total_count": 1, "artifacts": [self.artifact]}
        raise AssertionError(endpoint)

    def archive(self, artifact):
        assert artifact["id"] == 77
        return self.raw


def patch_sources(monkeypatch):
    config = (ROOT / reading.WATCH_CONFIG_PATH).read_bytes()
    registry = (ROOT / base.REGISTRY_PATH).read_bytes()

    def git_file(root, ref, path):
        assert ref == SHA
        if path == reading.WATCH_CONFIG_PATH:
            return config
        if path == base.REGISTRY_PATH:
            return registry
        raise AssertionError(path)

    monkeypatch.setattr(base, "git_file", git_file)


def test_typed_watch_is_hash_and_source_validated_then_retained_in_fixed_reading(tmp_path, monkeypatch):
    patch_sources(monkeypatch)
    report = watch_report()
    collector = reading.Collector(API(report=report), SHA, tmp_path, now=lambda: NOW)
    lane = collector.lane("inbox")
    saved = lane["last_qualified_result"]
    assert saved["status"] == "SAVED_INBOX_DELIVERY_ONLY"
    assert saved["numeric_result_validation"] == "NOT_AVAILABLE_IN_EXISTING_ARTIFACT"
    typed = saved["odds_watch"]
    assert typed["status"] == "TYPED_ODDS_WATCH_READ_OK"
    assert typed["report"] == report
    assert typed["report"]["watch"]["active_case_count"] == 5
    assert typed["meaning"].endswith("NOT_REVALIDATED_DECISION_SPINE_ODDS_OR_ACTION")
    assert reading.WATCH_JSON_PATH in saved["details"]
    assert reading.WATCH_SUMMARY_PATH in saved["details"]
    retained = collector.files[saved["details"][reading.WATCH_JSON_PATH]["read_path"]]
    assert json.loads(retained) == report


def test_old_inbox_without_watch_is_explicitly_not_available_not_quiet(tmp_path, monkeypatch):
    patch_sources(monkeypatch)
    collector = reading.Collector(API(), SHA, tmp_path, now=lambda: NOW)
    lane = collector.lane("inbox")
    typed = lane["last_qualified_result"]["odds_watch"]
    assert typed == {
        "status": "NOT_AVAILABLE_IN_EXISTING_ARTIFACT",
        "meaning": "NO_TYPED_WATCH_BYTES_NO_TRIGGER_OR_QUIET_INFERRED",
    }


def test_partial_or_tampered_watch_rejects_latest_inbox_instead_of_parsing_prose(tmp_path, monkeypatch):
    patch_sources(monkeypatch)
    report = watch_report()
    partial = reading.Collector(API(report=report, partial=True), SHA, tmp_path, now=lambda: NOW).lane("inbox")
    assert partial["last_qualified_result"] is None

    tampered = json.loads(json.dumps(report))
    tampered["watch"]["active_case_count"] = 999
    broken = reading.Collector(API(report=tampered), SHA, tmp_path, now=lambda: NOW).lane("inbox")
    assert broken["last_qualified_result"] is None
