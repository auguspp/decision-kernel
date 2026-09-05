from __future__ import annotations

import copy
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import stock_field_source_study as study
from decision_kernel.runtime.hithink_dump_diagnostics import INPUT_SEMANTICS

PROFILE = "remaining-listings"
NOW = datetime(2026, 9, 6, 1, tzinfo=timezone.utc)


def seal(value, field):
    body = {key: item for key, item in value.items() if key != field}
    return {**body, field: canonical_hash(body)}


def report():
    missing = sorted(set(study.LISTING_KEYWORDS) | (set(study.COVERAGE_KEYWORDS) - {"920289.BJ"}))
    inspection = seal({
        "schema_version": 1, "semantics": INPUT_SEMANTICS,
        "inspection_status": "DIFFERENCES_REQUIRE_REVIEW",
        "production_qualification": "NOT_ESTABLISHED", "input_authenticity": "SYNTHETIC_TEST_ONLY",
        "checked_priced_latest_identities": 1, "expected_sessions": ["2026-09-03", "2026-09-04"],
        "reference_mismatches": [{"thscode": "920289.BJ", "field": "previous_bar",
                                  "reason": "MISSING_OR_NEW_LISTING_REQUIRES_REVIEW"}],
        "current_universe_missing_latest_bar": missing, "unpriced_reference_identities": missing,
        "current_universe_missing_reference": [], "dump_identities_outside_current_universe": [],
        "missing_sessions": [], "human_attention_authority": "NONE", "research_authority": "NONE",
        "investment_authority": "NONE", "market_state_writes": 0, "events_created": 0,
    }, "inspection_hash")
    return seal({"input_file_sha256": dict.fromkeys(
        ("parquet", "sessions", "universe", "snapshot"), "a" * 64),
        "inspection": inspection}, "report_hash")


def symbols():
    return {"stockList": [{"code": code[:6], "orgId": "org" + code[:6]}
                          for code in study.LISTING_KEYWORDS]}


def query(code="603448.SH"):
    spec = study.notice_query(code, symbols(), date(2026, 9, 4))
    spec["params"]["searchkey"] = study.LISTING_KEYWORDS[code]
    return spec


def row(code="603448.SH", ident=None, day=4):
    ident = ident or ("1225547191" if code == "603448.SH" else "1" + code[:6])
    title = (study.REVIEWED_LISTING_ORIGINAL[code]["title"] if code == "603448.SH"
             else "公司首次公开发行股票" + study.LISTING_KEYWORDS[code])
    return {"secCode": code[:6], "orgId": "org" + code[:6], "announcementId": ident,
            "announcementTitle": title,
            "announcementTime": int(datetime(2026, 9, day, tzinfo=study.TZ).timestamp() * 1000),
            "adjunctUrl": f"finalpage/2026-09-{day:02d}/{ident}.PDF"}


def payload(*rows):
    return {"hasMore": False, "totalAnnouncement": len(rows), "announcements": list(rows)}


def select(body, code="603448.SH"):
    return study.coverage_notice_pdf(code, body, query(code), profile=PROFILE)


def test_plan_covers_only_eleven_remaining_leads_and_preserves_denominator():
    source = report()
    original = copy.deepcopy(source)
    plan = study.build_plan(source, profile=PROFILE)
    assert source == original
    assert plan["notice_sample_codes"] == sorted(study.LISTING_KEYWORDS)
    assert len(plan["notice_sample_codes"]) == 11
    assert len(plan["unqueried_gap_codes"]) == 9  # earlier acquired sources not re-requested
    assert set(plan["notice_sample_codes"]) & set(plan["unqueried_gap_codes"]) == set()
    assert plan["provider_requests"] == []
    assert 1 + 2 * len(plan["notice_sample_codes"]) == 23 < study.MAX_REQUESTS
    assert plan["reviewed_originals"] == study.REVIEWED_LISTING_ORIGINAL
    assert plan["production_qualification"] == "NOT_ESTABLISHED"
    assert plan == seal(plan, "plan_hash")


def test_legacy_plan_shapes_are_unchanged():
    source = report()
    events = study.build_plan(source)
    assert events["schema_version"] == 1 and "profile" not in events
    coverage = study.build_plan(source, profile="coverage-notices")
    assert coverage["schema_version"] == 2 and "reviewed_originals" not in coverage
    assert coverage["notice_sample_codes"] == sorted(study.COVERAGE_KEYWORDS)
    assert "920289.BJ" not in study.build_plan(source, profile=PROFILE)["notice_sample_codes"]


def test_exact_previously_reviewed_full_original_resolves_only_its_known_tie():
    full = row()
    pointer = row(ident="1225547199")
    pointer["announcementTitle"] += "提示性公告"
    body = payload(pointer, full)
    before = copy.deepcopy(body)
    assert select(body)["url"] == study.REVIEWED_LISTING_ORIGINAL["603448.SH"]["source_locator"]
    assert select(payload(full, pointer)) == select(body)
    assert body == before
    with pytest.raises(ValueError, match="AMBIGUOUS"):
        study.coverage_notice_pdf("603448.SH", body, query())  # old profile still rejects


@pytest.mark.parametrize("field,value", [
    ("announcementId", "1225547199"),
    ("announcementTitle", "更改后的上市公告书"),
    ("announcementTime", int(datetime(2026, 9, 3, tzinfo=study.TZ).timestamp() * 1000)),
    ("adjunctUrl", "finalpage/2026-09-04/1225547199.PDF"),
])
def test_reviewed_original_cannot_drift_in_identity_title_date_or_url(field, value):
    record = row()
    record[field] = value
    with pytest.raises(ValueError, match="REVIEWED_ORIGINAL"):
        select(payload(record))


def test_other_full_document_ties_still_fail_closed():
    code = "301689.SZ"
    with pytest.raises(ValueError, match="AMBIGUOUS"):
        select(payload(row(code, "101"), row(code, "102")), code)


def test_pointer_only_is_not_a_full_issuance_document():
    code = "301689.SZ"
    record = row(code)
    record["announcementTitle"] += "提示性公告"
    with pytest.raises(ValueError, match="AMBIGUOUS_OR_MISSING"):
        select(payload(record), code)


@pytest.mark.parametrize("field", ["secCode", "orgId"])
def test_explicit_row_identity_is_required(field):
    record = row()
    record.pop(field)
    with pytest.raises(ValueError, match="EXPLICIT_LISTING_NOTICE_IDENTITY"):
        select(payload(record))


@pytest.mark.parametrize("change", ["hasMore", "total", "future", "duplicate"])
def test_incomplete_or_out_of_window_queries_are_not_repaired(change):
    record = row()
    body = payload(record)
    if change == "hasMore": body["hasMore"] = True
    if change == "total": body["totalAnnouncement"] = 2
    if change == "future": record["announcementTime"] = int(NOW.timestamp() * 1000)
    if change == "duplicate": body = payload(record, dict(record))
    with pytest.raises(ValueError):
        select(body)


@pytest.mark.parametrize("change", ["override", "keyword", "provider", "unreviewed"])
def test_rehashed_but_unreviewed_plan_is_rejected_before_network(tmp_path, change):
    plan = study.build_plan(report(), profile=PROFILE)
    if change == "override": plan["reviewed_originals"]["603448.SH"]["announcement_id"] = "7"
    if change == "keyword": plan["notice_keywords"]["301689.SZ"] = "任何公告"
    if change == "provider": plan["provider_requests"] = [{"url": study.EVENTS}]
    if change == "unreviewed": plan["notice_sample_codes"].append("000001.SZ")
    plan = seal(plan, "plan_hash")
    with pytest.raises(ValueError):
        study.capture_sources(plan, tmp_path/"new", api_key="", provenance="SYNTHETIC_TEST_ONLY",
                              request=lambda spec: pytest.fail("network must not run"), now=lambda: NOW)
    assert not (tmp_path/"new").exists()


def test_full_synthetic_capture_reuses_public_transport_without_state_or_acceptance(tmp_path):
    calls = []
    def reply(spec):
        calls.append(spec)
        if spec["url"] == study.SYMBOLS: value = symbols()
        elif spec["url"] == study.NOTICES:
            ticker = spec["params"]["stock"].split(",")[0]
            code = next(code for code in study.LISTING_KEYWORDS if code[:6] == ticker)
            value = payload(row(code))
        else:
            assert spec["url"].startswith(study.PDF_ORIGIN)
            return 200, b"%PDF-1.7\nSYNTHETIC_CONTAINER_ONLY\n%%EOF"
        return 200, json.dumps(value, ensure_ascii=False).encode()
    original = report()
    result = study.capture_sources(study.build_plan(original, profile=PROFILE), tmp_path/"new", api_key="",
        request=reply, now=lambda: NOW, provenance="SYNTHETIC_TEST_ONLY")
    assert len(calls) == len(result["files"]) == 23
    assert len({spec["id"] for spec in calls}) == 23
    assert all(not spec["url"].startswith(study.BASE) for spec in calls)
    assert result["status"] == "CAPTURE_COMPLETE_REVIEW_REQUIRED"
    assert result["production_qualification"] == "NOT_ESTABLISHED"
    assert result["causes_automatically_accepted"] == result["market_state_writes"] == result["events_created"] == 0
    assert original == report()
    assert result["study_profile"] == PROFILE


def test_missing_query_is_retained_without_retry_or_a_listing_inference(tmp_path):
    plan = study.build_plan(report(), profile=PROFILE)
    calls = []
    def reply(spec):
        calls.append(spec["id"])
        value = symbols() if spec["url"] == study.SYMBOLS else payload()
        return 200, json.dumps(value).encode()
    result = study.capture_sources(plan, tmp_path/"new", api_key="", request=reply,
        now=lambda: NOW, provenance="SYNTHETIC_TEST_ONLY")
    assert len(calls) == len(set(calls)) == 12
    assert len(result["problems"]) == 11
    assert result["status"] == "INCOMPLETE_SOURCE_STUDY"
    assert result["coverage_status_classification"] == "REVIEW_REQUIRED_NO_AUTOMATIC_EXCLUSIONS"
