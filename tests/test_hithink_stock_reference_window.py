from __future__ import annotations

import copy
import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import hithink_sector_breadth_http as stocks
from decision_kernel.runtime.hithink_http import HithinkRuntimeError
from decision_kernel.runtime import hithink_index_http
from test_hithink_dump_trial import NOW, SESSIONS, execute, ms, parquet, responses


FRIDAY = SESSIONS[-1]
SATURDAY = date(2026, 9, 5)
MONDAY = date(2026, 9, 7)
STOCK_PATH = stocks.HITHINK_A_SHARE_SNAPSHOT_PATH


def context(observed_at=NOW):
    payloads = responses()
    benchmark = hithink_index_http.fetch_hithink_qualified_index_snapshot_batch(
        thscodes=("000300.SH",), benchmark_thscode="000300.SH",
        observed_at=NOW, api_key="synthetic-key", trading_sessions=SESSIONS,
        request_json=lambda path, params: copy.deepcopy(payloads[path]),
    )
    result = stocks.HithinkStockSnapshotReference(SESSIONS, benchmark, observed_at)
    result.validate()
    return result


def fetch(payload, *, reference=None, received=NOW):
    return stocks.fetch_hithink_all_market_snapshot(
        market_session=FRIDAY, api_key="synthetic-key",
        request_json=lambda path, params: payload,
        reference_context=reference,
        received_at=None if reference is None else (lambda: received),
    )


def test_original_failed_response_clock_is_accepted_only_as_capture_evidence():
    # Exact timestamp/request clocks from retained run 33957604949. This is a
    # pure clock regression, not a claim to replay the unavailable later pages.
    observed = datetime.fromisoformat("2026-09-05T09:18:27.469893+00:00")
    received = datetime.fromisoformat("2026-09-05T09:18:28.548563+00:00")
    ref = context(observed)
    ref.validate_ready_time(1788599907000, received_at=received)
    evidence = ref.evidence()
    assert evidence["comparison_session"] == "2026-09-04"
    assert evidence["closed_interval_basis"] == "FRIDAY_TO_SATURDAY_OR_SUNDAY_ONLY"
    assert evidence["per_security_market_session"] == "NOT_PROVEN_BY_PAGE_TIMESTAMP"
    assert evidence["production_qualification"] == "NOT_ESTABLISHED"
    assert evidence["calendar_hash"] == canonical_hash(SESSIONS)


def test_legacy_sector_path_still_rejects_weekend_provider_date():
    payload = responses()[STOCK_PATH]
    payload["data"]["timestamp"] = ms(SATURDAY, 16)
    with pytest.raises(HithinkRuntimeError, match="provider date disagrees"):
        fetch(payload)


def test_reference_mode_preserves_original_page_time_and_exact_price_fields():
    payload = responses()[STOCK_PATH]
    payload["data"]["timestamp"] = ms(SATURDAY, 16)
    payload["data"]["item"][0]["last_price"] = "109.000000001"
    before = copy.deepcopy(payload)
    result = fetch(payload, reference=context())
    assert payload == before
    assert result.provider_timestamp_min_ms == result.provider_timestamp_max_ms == ms(SATURDAY, 16)
    assert result.snapshot_semantics == stocks.HITHINK_STOCK_REFERENCE_SEMANTICS
    assert result.snapshot_semantics != stocks.HITHINK_ALL_MARKET_SNAPSHOT_SEMANTICS
    by_code = {point.thscode: point for point in result.points}
    assert by_code[before["data"]["item"][0]["thscode"]].last_price == Decimal("109.000000001")


@pytest.mark.parametrize("observed", [
    datetime(2026, 9, 4, 8, tzinfo=timezone.utc),
    datetime(2026, 9, 5, 8, tzinfo=timezone.utc),
    datetime(2026, 9, 6, 8, tzinfo=timezone.utc),
])
def test_only_same_post_close_or_direct_following_weekend_is_supported(observed):
    ref = context(observed)
    ready_ms = int(observed.timestamp() * 1000)
    ref.validate_ready_time(ready_ms, received_at=observed)


@pytest.mark.parametrize("observed", [
    datetime(2026, 9, 4, 6, 59, tzinfo=timezone.utc),
    datetime(2026, 9, 4, 7, 15, tzinfo=timezone.utc),
    datetime(2026, 9, 7, 1, tzinfo=timezone.utc),
    datetime(2026, 9, 7, 8, tzinfo=timezone.utc),
    datetime(2026, 9, 12, 8, tzinfo=timezone.utc),
])
def test_pre_close_later_weekday_and_missing_weekday_calendar_tail_fail(observed):
    with pytest.raises(HithinkRuntimeError):
        replace(context(), observed_at=observed).validate()


def test_missing_weekday_is_not_accepted_as_a_holiday():
    # The same rule rejects a stale Thursday anchor before a Friday holiday;
    # calendar omission by itself remains insufficient.
    ref = context()
    with pytest.raises(HithinkRuntimeError):
        replace(ref, trading_sessions=SESSIONS[:-1],
                benchmark=replace(ref.benchmark, market_session=SESSIONS[-2])).validate()


def test_explicit_exchange_closure_qualifies_data_ready_clock_without_relabeling_session():
    ref = context()
    closed = FRIDAY
    observed = datetime(2026, 9, 4, 8, tzinfo=timezone.utc)
    qualified = replace(
        ref,
        trading_sessions=SESSIONS[:-1],
        benchmark=replace(ref.benchmark, market_session=SESSIONS[-2]),
        observed_at=observed,
        closed_dates=(closed,),
        closure_evidence=(
            "https://www.sse.com.cn/disclosure/announcement/general/c/c_20260915_10832273.shtml",
            "https://www.szse.cn/www/disclosure/notice/general/t20260917_622911.html",
        ),
    )
    qualified.validate_ready_time(ms(closed, 16), received_at=observed)
    evidence = qualified.evidence()
    assert evidence["comparison_session"] == SESSIONS[-2].isoformat()
    assert evidence["closed_dates"] == [closed.isoformat()]
    assert evidence["closed_interval_basis"] == "EXPLICIT_EXCHANGE_CLOSURE_AFTER_COMPLETED_SESSION"
    assert evidence["per_security_market_session"] == "NOT_PROVEN_BY_PAGE_TIMESTAMP"
    assert evidence["production_qualification"] == "BOUNDED_REFERENCE_ALLOWED_BY_EXPLICIT_EXCHANGE_CLOSURE"


def test_explicit_closure_requires_exact_gap_and_evidence():
    ref = context()
    observed = datetime(2026, 9, 4, 8, tzinfo=timezone.utc)
    base = replace(
        ref,
        trading_sessions=SESSIONS[:-1],
        benchmark=replace(ref.benchmark, market_session=SESSIONS[-2]),
        observed_at=observed,
    )
    for changed in (
        replace(base, closed_dates=(FRIDAY,)),
        replace(base, closure_evidence=("https://www.sse.com.cn/example",)),
        replace(base, closed_dates=(date(2026, 9, 3),), closure_evidence=("https://www.sse.com.cn/example",)),
    ):
        with pytest.raises(HithinkRuntimeError):
            changed.validate()


@pytest.mark.parametrize("timestamp", [
    None, True, "1788599907000", 1788599907000.5, 0, -1, 10**30,
    ms(FRIDAY, 14), ms(FRIDAY, 15), ms(date(2026, 9, 3), 16),
    int(NOW.timestamp() * 1000) + 1,
])
def test_missing_malformed_preclose_and_future_ready_clocks_fail(timestamp):
    with pytest.raises(HithinkRuntimeError):
        context().validate_ready_time(timestamp, received_at=NOW)


@pytest.mark.parametrize("received", [
    NOW.replace(tzinfo=None), NOW - timedelta(microseconds=1), NOW + timedelta(days=1),
])
def test_receive_clock_cannot_go_backwards_or_cross_the_capture_date(received):
    with pytest.raises(HithinkRuntimeError):
        context().validate_ready_time(ms(FRIDAY, 16), received_at=received)


@pytest.mark.parametrize("sessions", [
    (), SESSIONS[::-1], (*SESSIONS, FRIDAY), SESSIONS[:-1],
    (*SESSIONS, SATURDAY), (*SESSIONS[:-1], datetime(2026, 9, 4)),
])
def test_invalid_or_conflicting_calendar_is_not_completion_evidence(sessions):
    with pytest.raises(HithinkRuntimeError):
        replace(context(), trading_sessions=sessions).validate()


def test_wrong_anchor_or_requested_session_fails_before_stock_request():
    ref = context()
    for benchmark in (
        replace(ref.benchmark, benchmark_thscode="000001.SH"),
        replace(ref.benchmark, qualification_method="UNQUALIFIED"),
        replace(ref.benchmark, points=()),
    ):
        with pytest.raises(HithinkRuntimeError):
            replace(ref, benchmark=benchmark).validate()
    with pytest.raises(HithinkRuntimeError, match="disagrees with requested"):
        stocks.fetch_hithink_all_market_snapshot(
            market_session=MONDAY, api_key="synthetic-key", reference_context=ref,
            request_json=lambda *args: pytest.fail("invalid context must not fetch"),
        )


def test_each_page_is_time_checked_and_received_without_retaining_a_partial_batch():
    payload = responses()[STOCK_PATH]
    rows = payload["data"]["item"]
    calls = []
    def request(path, params):
        offset = int(params["offset"])
        calls.append(offset)
        return {"code": 0, "data": {"total": 2, "item": [rows[offset]],
                "timestamp": ms(SATURDAY, 16) + (1 if offset else 0)}}
    with pytest.raises(HithinkRuntimeError, match="follows response receipt"):
        stocks.fetch_hithink_all_market_snapshot(
            market_session=FRIDAY, api_key="synthetic-key", page_size=1,
            reference_context=context(), received_at=lambda: NOW, request_json=request,
        )
    assert calls == [0, 1]


@pytest.mark.parametrize("corruption", ["duplicate", "total", "invalid_code", "zero_price"])
def test_pagination_and_identity_price_contracts_remain_strict(corruption):
    rows = responses()[STOCK_PATH]["data"]["item"]
    def request(path, params):
        offset = int(params["offset"])
        row = copy.deepcopy(rows[0 if corruption == "duplicate" else offset])
        if corruption == "invalid_code":
            row["thscode"] = "ABCDEF.XY"
        if corruption == "zero_price":
            row["last_price"] = "0"
        return {"code": 0, "data": {"timestamp": ms(SATURDAY, 16),
            "total": 3 if offset and corruption == "total" else 2, "item": [row]}}
    with pytest.raises(HithinkRuntimeError):
        stocks.fetch_hithink_all_market_snapshot(
            market_session=FRIDAY, api_key="synthetic-key", page_size=1,
            reference_context=context(), received_at=lambda: NOW, request_json=request,
        )


def test_weekend_trial_physically_reconciles_parquet_without_altering_raw_json(parquet, tmp_path):
    payloads = responses()
    payloads[STOCK_PATH]["data"]["timestamp"] = ms(SATURDAY, 16)
    before = copy.deepcopy(payloads[STOCK_PATH])
    root = tmp_path / "study"
    report, calls = execute(root, parquet, payloads)
    assert report["schema_version"] == 2
    assert report["status"] == "CHECKED_FIELDS_MATCH"
    assert report["inspection"]["row_count"] == 20
    assert report["production_qualification"] == "NOT_ESTABLISHED"
    assert json.loads((root / "reference-04.json").read_text()) == before
    assert report["reference_summary"]["provider_timestamp_max_ms"] == ms(SATURDAY, 16)
    assert (root / "reference-window.json").exists()
    assert report["market_state_writes"] == report["events_created"] == 0
    assert len(calls) == 6


def test_unpriced_reference_remains_null_and_non_success(parquet, tmp_path):
    payloads = responses()
    payloads[STOCK_PATH]["data"]["timestamp"] = ms(SATURDAY, 16)
    payloads[STOCK_PATH]["data"]["item"][0]["last_price"] = None
    report, _ = execute(tmp_path / "study", parquet, payloads)
    assert report["reference_summary"]["unpriced"] == 1
    assert report["status"] == "INCOMPLETE_REFERENCE_COVERAGE"
    assert len(report["inspection"]["unpriced_reference_identities"]) == 1


def test_weekend_reference_does_not_make_an_exact_price_difference_pass(parquet, tmp_path):
    payloads = responses()
    payloads[STOCK_PATH]["data"]["timestamp"] = ms(SATURDAY, 16)
    payloads[STOCK_PATH]["data"]["item"][0]["prev_price"] = "107.99999999"
    report, _ = execute(tmp_path / "study", parquet, payloads)
    assert report["status"] == "DIFFERENCES_REQUIRE_REVIEW"
    assert report["inspection"]["reference_mismatches"][0]["field"] == "raw_previous_close"
    assert report["production_qualification"] == "NOT_ESTABLISHED"
