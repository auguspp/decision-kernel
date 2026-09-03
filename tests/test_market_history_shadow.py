from __future__ import annotations

import json
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.hithink import (
    HithinkCompletedPriceHistory,
    HithinkCompletedPricePoint,
)
from decision_kernel.runtime import hithink_http
from decision_kernel.runtime.market_history_shadow import capture_market_history_shadow


SHANGHAI = ZoneInfo("Asia/Shanghai")
CAPTURED_AT = datetime(2026, 9, 2, 8, 30, tzinfo=timezone.utc)


def _history(thscode: str, *, latest: date = date(2026, 9, 2)) -> HithinkCompletedPriceHistory:
    previous = date(2026, 9, 1)
    return HithinkCompletedPriceHistory(
        thscode=thscode,
        points=(
            HithinkCompletedPricePoint(
                close=Decimal("40.20"),
                as_of=datetime.combine(previous, time(15), tzinfo=SHANGHAI),
            ),
            HithinkCompletedPricePoint(
                close=Decimal("40.86"),
                as_of=datetime.combine(latest, time(15), tzinfo=SHANGHAI),
            ),
        ),
        response_session=latest,
        expected_latest_session=latest,
    )


def test_shadow_capture_binds_real_research_identity_to_qualified_history(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[str, datetime, str | None]] = []

    def fake_history(*, thscode: str, observed_at: datetime, api_key: str | None):
        calls.append((thscode, observed_at, api_key))
        return _history(thscode)

    monkeypatch.setattr(
        hithink_http,
        "fetch_hithink_completed_price_history",
        fake_history,
    )

    outputs = capture_market_history_shadow(
        (Path("dogfood/600036-cmb.json"),),
        output_dir=tmp_path,
        captured_at=CAPTURED_AT,
        api_key="fixture-secret",
    )

    assert calls == [("600036.SH", CAPTURED_AT, "fixture-secret")]
    assert outputs == (tmp_path / "600036-2026-09-02.json",)

    artifact = json.loads(outputs[0].read_text(encoding="utf-8"))
    assert artifact["storage_classification"] == "ACTIONS_SHORT_LIVED_HARNESS_OBSERVATION"
    assert artifact["security"] == {
        "company_name": "招商银行",
        "exchange": "SSE",
        "thscode": "600036.SH",
        "ticker": "600036",
    }
    assert artifact["research_identity"] == {
        "research_snapshot_id": "edda6f4b-0fdd-5699-9fa3-76338a58ff3d",
        "research_created_at": "2026-09-02T00:10:00+00:00",
        "research_as_of": "2026-08-30T00:00:00+00:00",
        "research_information_bundle_hash": (
            "6ad42a3b342c0bc043d8e2589ea46a9072d598e502e4755071c109d13f538872"
        ),
    }
    assert artifact["research_identity"]["research_created_at"] != artifact[
        "research_identity"
    ]["research_as_of"]
    assert artifact["market_contract"] == {
        "expected_latest_session": "2026-09-02",
        "price_convention": "RAW_UNADJUSTED_COMPLETED_A_SHARE_CLOSE",
        "response_session": "2026-09-02",
        "source": "HiThink Financial-API raw daily close",
    }
    assert artifact["points"] == [
        {"as_of": "2026-09-01T15:00:00+08:00", "close": "40.20"},
        {"as_of": "2026-09-02T15:00:00+08:00", "close": "40.86"},
    ]
    assert artifact["radar_semantics"] == "SHADOW_OBSERVATION_ONLY"
    assert artifact["human_attention_authority"] == "NONE"
    assert artifact["investment_authority"] == "NONE"
    serialized = outputs[0].read_text(encoding="utf-8")
    assert "participation_zone" not in serialized
    assert "attention_eligible" not in serialized
    assert "recommendation" not in serialized.lower()


def test_shadow_capture_rejects_duplicate_current_research_without_partial_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        hithink_http,
        "fetch_hithink_completed_price_history",
        lambda *, thscode, observed_at, api_key: _history(thscode),
    )

    with pytest.raises(
        ValueError,
        match="more than one current Research package for 600036.SH",
    ):
        capture_market_history_shadow(
            (
                Path("dogfood/600036-cmb.json"),
                Path("dogfood/600036-cmb.json"),
            ),
            output_dir=tmp_path,
            captured_at=CAPTURED_AT,
            api_key="fixture-secret",
        )

    assert not tmp_path.exists() or tuple(tmp_path.iterdir()) == ()


def test_shadow_capture_fetch_failure_leaves_no_partial_artifact_set(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fake_history(*, thscode: str, observed_at: datetime, api_key: str | None):
        if thscode == "600036.SH":
            return _history(thscode)
        raise hithink_http.HithinkRuntimeError("fixture provider failure")

    monkeypatch.setattr(
        hithink_http,
        "fetch_hithink_completed_price_history",
        fake_history,
    )

    with pytest.raises(hithink_http.HithinkRuntimeError, match="fixture provider failure"):
        capture_market_history_shadow(
            (
                Path("dogfood/600036-cmb.json"),
                Path("dogfood/300750-catl.json"),
            ),
            output_dir=tmp_path,
            captured_at=CAPTURED_AT,
            api_key="fixture-secret",
        )

    assert not tmp_path.exists() or tuple(tmp_path.iterdir()) == ()
