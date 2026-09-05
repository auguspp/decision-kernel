from __future__ import annotations

import copy
import json
from datetime import date, datetime, timezone

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import stock_field_source_study as study
from decision_kernel.runtime.hithink_dump_diagnostics import INPUT_SEMANTICS


def sealed(value, field):
    body = {key: item for key, item in value.items() if key != field}
    return {**body, field: canonical_hash(body)}


def report():
    missing = sorted(set(study.COVERAGE_KEYWORDS) - {"920289.BJ"} | {"301699.SZ"})
    inspection = sealed({
        "schema_version": 1, "semantics": INPUT_SEMANTICS,
        "inspection_status": "DIFFERENCES_REQUIRE_REVIEW",
        "production_qualification": "NOT_ESTABLISHED",
        "input_authenticity": "SYNTHETIC_TEST_ONLY",
        "checked_priced_latest_identities": 1,
        "expected_sessions": ["2026-09-03", "2026-09-04"],
        "reference_mismatches": [{"thscode": "920289.BJ", "field": "previous_bar",
                                  "reason": "MISSING_OR_NEW_LISTING_REQUIRES_REVIEW"}],
        "current_universe_missing_latest_bar": missing,
        "unpriced_reference_identities": missing,
        "current_universe_missing_reference": [], "dump_identities_outside_current_universe": [],
        "missing_sessions": [], "human_attention_authority": "NONE",
        "research_authority": "NONE", "investment_authority": "NONE",
        "market_state_writes": 0, "events_created": 0,
    }, "inspection_hash")
    return sealed({"input_file_sha256": dict.fromkeys(
        ("parquet", "sessions", "universe", "snapshot"), "a" * 64),
        "inspection": inspection}, "report_hash")


def symbols():
    return {"stockList": [{"code": code[:6], "orgId": "org" + code[:6]}
                          for code in study.COVERAGE_KEYWORDS]}


def query(code="000016.SZ"):
    value = study.notice_query(code, symbols(), date(2026, 9, 4))
    value["params"]["searchkey"] = study.COVERAGE_KEYWORDS[code]
    return value


def row(code="000016.SZ", day=3, ident="10001"):
    return {"secCode": code[:6], "orgId": "org" + code[:6], "announcementId": ident,
            "announcementTitle": "公司关于" + study.COVERAGE_KEYWORDS[code],
            "announcementTime": int(datetime(2026, 9, day, tzinfo=study.TZ).timestamp() * 1000),
            "adjunctUrl": f"finalpage/2026-09-{day:02d}/{ident}.PDF"}


def payload(*items):
    return {"hasMore": False, "totalAnnouncement": len(items), "announcements": list(items)}


def test_plan_targets_only_gap_intersection_and_keeps_unqueried_codes():
    source = report()
    original = copy.deepcopy(source)
    plan = study.build_plan(source, profile="coverage-notices")
    assert source == original
    assert plan == study.build_plan(source, profile="coverage-notices")
    assert plan["provider_requests"] == []
    assert plan["notice_sample_codes"] == sorted(study.COVERAGE_KEYWORDS)
    assert plan["notice_keywords"] == study.COVERAGE_KEYWORDS
    assert plan["unqueried_gap_codes"] == ["301699.SZ"]
    assert 1 + 2 * len(plan["notice_sample_codes"]) <= study.MAX_REQUESTS == 24
    assert plan["production_qualification"] == "NOT_ESTABLISHED"
    assert plan == sealed(plan, "plan_hash")


def test_old_event_profile_shape_is_unchanged_and_unknown_profile_rejected():
    plan = study.build_plan(report())
    assert plan["schema_version"] == 1
    assert "profile" not in plan and "notice_keywords" not in plan
    with pytest.raises(ValueError, match="UNREVIEWED_STUDY_PROFILE"):
        study.build_plan(report(), profile="live-stock-status")


def test_latest_document_selection_is_order_independent_and_not_status_classification():
    a, b = row(day=2, ident="10002"), row(day=3, ident="10003")
    body = payload(a, b)
    old = copy.deepcopy(body)
    selected = study.coverage_notice_pdf("000016.SZ", body, query())
    assert selected["url"].endswith("/10003.PDF")
    assert study.coverage_notice_pdf("000016.SZ", payload(b, a), query()) == selected
    assert body == old
    assert set(selected) == {"id", "method", "url", "params"}


def test_ipo_document_does_not_require_a_year_in_its_title():
    selected = study.coverage_notice_pdf("920289.BJ", payload(row("920289.BJ")), query("920289.BJ"))
    assert selected["url"].endswith(".PDF")


@pytest.mark.parametrize("change", [
    {"hasMore": True}, {"hasMore": None}, {"totalAnnouncement": 2},
    {"totalAnnouncement": True}, {"announcements": None},
])
def test_incomplete_or_malformed_pages_are_not_no_update(change):
    value = payload(row())
    value.update(change)
    with pytest.raises(ValueError):
        study.coverage_notice_pdf("000016.SZ", value, query())


@pytest.mark.parametrize("change", [
    {"secCode": "000017"}, {"orgId": "anotherOrg"}, {"announcementTime": None},
    {"announcementTime": int(datetime(2026, 9, 5, tzinfo=study.TZ).timestamp() * 1000)},
    {"announcementTime": int(datetime(2026, 8, 1, tzinfo=study.TZ).timestamp() * 1000)},
    {"announcementTitle": "2026年半年度报告"},
    {"adjunctUrl": "https://evil.example/10001.PDF"},
    {"adjunctUrl": "finalpage/2026-09-03/../10001.PDF"},
])
def test_wrong_identity_date_title_or_path_rejected(change):
    item = row()
    item.update(change)
    with pytest.raises(ValueError):
        study.coverage_notice_pdf("000016.SZ", payload(item), query())


@pytest.mark.parametrize("duplicate_id", [True, False])
def test_duplicate_ids_or_tied_latest_documents_require_review(duplicate_id):
    a, b = row(), row(ident="10001" if duplicate_id else "10002")
    with pytest.raises(ValueError):
        study.coverage_notice_pdf("000016.SZ", payload(a, b), query())


def test_empty_search_does_not_prove_listing_or_suspension():
    with pytest.raises(ValueError, match="AMBIGUOUS_OR_MISSING"):
        study.coverage_notice_pdf("000016.SZ", payload(), query())


def reply(spec):
    if spec["url"] == study.SYMBOLS:
        value = symbols()
    elif spec["url"] == study.NOTICES:
        code = next(code for code in study.COVERAGE_KEYWORDS
                    if spec["params"]["stock"].startswith(code[:6] + ","))
        assert spec["params"]["searchkey"] == study.COVERAGE_KEYWORDS[code]
        value = payload(row(code))
    elif spec["url"].startswith(study.PDF_ORIGIN):
        return 200, b"%PDF-1.7\nSYNTHETIC_TEST_ONLY\n%%EOF"
    else:
        raise AssertionError("No quote, event or history endpoint is permitted here")
    return 200, json.dumps(value, ensure_ascii=False).encode()


def test_full_public_profile_reuses_collector_without_key_or_market_requests(tmp_path):
    calls = []
    def request(spec):
        calls.append(spec)
        return reply(spec)
    result = study.capture_sources(study.build_plan(report(), profile="coverage-notices"),
        tmp_path / "new", api_key="", request=request,
        now=lambda: datetime(2026, 9, 5, 12, tzinfo=timezone.utc), provenance="SYNTHETIC_TEST_ONLY")
    assert len(calls) == len(result["files"]) == 21
    assert all(spec["url"] not in {study.EVENTS, study.HISTORY} for spec in calls)
    assert result["status"] == "CAPTURE_COMPLETE_REVIEW_REQUIRED"
    assert result["coverage_status_classification"] == "REVIEW_REQUIRED_NO_AUTOMATIC_EXCLUSIONS"
    assert result["source_disposition"] == "DIFFERENCES_REQUIRE_REVIEW"
    assert result["market_state_writes"] == result["events_created"] == result["causes_automatically_accepted"] == 0
    assert result == sealed(result, "study_hash")


@pytest.mark.parametrize("mutation", ["provider", "duplicate", "unknown", "keyword"])
def test_public_profile_cannot_be_repurposed_by_rehashing_plan(tmp_path, mutation):
    plan = study.build_plan(report(), profile="coverage-notices")
    if mutation == "provider":
        plan["provider_requests"] = [{"id": "forbidden", "method": "GET", "url": study.EVENTS, "params": {}}]
    elif mutation == "duplicate":
        plan["notice_sample_codes"].append(plan["notice_sample_codes"][0])
    elif mutation == "unknown":
        plan["notice_sample_codes"] = ["000001.SZ"]
    else:
        plan["notice_keywords"]["000016.SZ"] = "任意查询"
    plan = sealed(plan, "plan_hash")
    with pytest.raises(ValueError, match="PUBLIC_ONLY_AND_BOUNDED"):
        study.capture_sources(plan, tmp_path / "new", api_key="")
    assert not (tmp_path / "new").exists()
