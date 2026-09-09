"""Version selection is pure; capture tests use synthetic HTTP, never live CNINFO."""
from __future__ import annotations

import copy
import itertools
from datetime import datetime, timezone

import pytest

from decision_kernel.runtime.sanhua_document_versions import classify_title, qualify_versions

REPORT = "2026年半年度报告"
IR = "2026年8月27日投资者关系活动记录表"
DATES = ["2026-08-27", "2026-08-28"]


def row(number, title, day="2026-08-27"):
    return {"announcement_id": str(100 + number), "title": title,
            "published_at": day + "T00:00:00+08:00"}


def decide(rows):
    return qualify_versions(rows, ir_publication_dates=DATES)


def disposition(decision, record_id):
    return next(r["disposition"] for r in decision["records"] if r["announcement_id"] == record_id)


@pytest.mark.parametrize("title, expected", [
    (REPORT, "FULL_BODY"),
    ("三花智控：" + REPORT, "FULL_BODY"),
    (REPORT + "摘要", "SUMMARY"),
    (REPORT + "（修订版）", "REVISED_OR_CORRECTED_BODY"),
    (REPORT + "（更正后）", "REVISED_OR_CORRECTED_BODY"),
    (REPORT + "（更新版）", "REVISED_OR_CORRECTED_BODY"),
    (REPORT + "（英文版）", "LANGUAGE_OR_MARKET_VARIANT"),
    ("H股公告：" + REPORT, "LANGUAGE_OR_MARKET_VARIANT"),
    ("Sanhua 2026 Interim Report", "LANGUAGE_OR_MARKET_VARIANT"),
    ("关于" + REPORT + "的更正公告", "CORRECTION_NOTICE_ONLY"),
    ("关于" + REPORT + "的修订说明", "CORRECTION_NOTICE_ONLY"),
    ("关于取消" + REPORT + "的公告", "CANCELLATION_NOTICE_ONLY"),
    ("董事会决议", "OTHER"),
    ("2025年半年度报告", "OTHER"),
])
def test_pure_report_family_classification(title, expected):
    assert classify_title(title, "H1_REPORT")["classification"] == expected


@pytest.mark.parametrize("suffix", ["修订版", "更正版", "更新版"])
def test_pure_revision_not_bare_title_is_current(suffix):
    rows = [row(1, REPORT), row(2, REPORT + f"（{suffix}）", "2026-08-28")]
    before = copy.deepcopy(rows)
    # Reproduce e8566c81's three-bare-title predicate: it loses the revised body.
    old_matches = [r for r in rows if r["title"] in {
        REPORT, "三花智控：" + REPORT, "三花智控:" + REPORT}]
    assert [r["announcement_id"] for r in old_matches] == ["101"]
    result = decide(rows)["report"]
    assert result["status"] == "SELECTED" and result["selected_announcement_id"] == "102"
    assert disposition(result, "101") == "SUPERSEDED"
    assert disposition(result, "102") == "CURRENT"
    assert rows == before


def test_pure_two_ordinary_bodies_are_not_resolved_by_id_or_newer_time():
    for day in ["2026-08-27", "2026-08-28"]:
        result = decide([row(999, REPORT), row(1, REPORT, day)])["report"]
        assert result["status"] == "REPORT_VERSION_AMBIGUOUS"
        assert result["selected_announcement_id"] is None


def test_pure_unique_revision_cannot_resolve_two_originals_or_two_revisions():
    for rows in [
        [row(1, REPORT), row(2, REPORT), row(3, REPORT + "（修订版）")],
        [row(1, REPORT), row(2, REPORT + "（修订版）"), row(3, REPORT + "（更正版）")],
    ]:
        assert decide(rows)["report"]["status"] == "REPORT_VERSION_AMBIGUOUS"


def test_pure_predating_revision_requires_review_not_date_ranking():
    result = decide([row(1, REPORT, "2026-08-28"), row(2, REPORT + "（修订版）")])["report"]
    assert result["status"] == "VERSION_RELATION_UNRESOLVED"


def test_pure_order_invariance_and_explicit_limits():
    rows = [row(1, REPORT), row(2, REPORT + "（修订版）", "2026-08-28"), row(3, IR)]
    expected = decide(rows)
    for permutation in itertools.permutations(rows):
        assert decide(list(permutation)) == expected
    assert "ACTIVITY" in expected["ir"]["proof_scope"]
    with pytest.raises(ValueError, match="DUPLICATE_ANNOUNCEMENT_ID"):
        decide([rows[0], rows[0]])


# Every integration below calls the real capture/verify functions and original
# CNINFO normalizer. Only the HTTP transport and capture clocks are synthetic.
def capture(tmp_path, rows, *, fail_pdf=False, first_page_size=None):
    from decision_kernel.runtime import sanhua_source_acquisition as m
    calls = []
    originals = [{"announcementId": r["announcement_id"], "announcementTitle": r["title"],
                  "secCode": m.CODE, "orgId": "gssz002050",
                  "announcementTime": int(datetime.fromisoformat(r["published_at"]).timestamp() * 1000),
                  "adjunctUrl": "finalpage/" + r["published_at"][:10] + "/" + r["announcement_id"] + ".PDF"}
                 for r in rows]
    def request(spec):
        calls.append(copy.deepcopy(spec))
        if spec["id"] == "issuer-map":
            payload = {"stockList": [{"code": m.CODE, "orgId": "gssz002050", "zwjc": m.ISSUER}]}
        elif spec["id"].startswith("inventory-"):
            number = int(spec["params"]["pageNum"])
            size = first_page_size or m.PAGE_SIZE
            items = originals[(number - 1) * size:number * size]
            payload = {"announcements": items, "hasMore": number * size < len(originals),
                       "totalAnnouncement": len(originals)}
        else:
            assert spec["id"].startswith("primary-")
            if fail_pdf:
                return m.Response(503, "text/html", None, "HTTP_REJECTED")
            return m.Response(200, "application/pdf", b"%PDF-1.4\nSynthetic test only.\n%%EOF\n")
        return m.Response(200, "application/json", m.data(payload))
    root = tmp_path / "capture"
    result = m.capture(root, request=request,
                       now=lambda: datetime(2026, 9, 9, 2, 0, tzinfo=timezone.utc))
    return m, root, result, calls


@pytest.mark.parametrize("suffix", [None, "修订版", "更正版", "更新版"])
def test_capture_only_current_full_report_is_requested(tmp_path, suffix):
    rows = [row(1, REPORT), row(2, IR)]
    selected = "101"
    if suffix:
        rows.append(row(3, "三花智控：" + REPORT + f"（{suffix}）", "2026-08-28"))
        selected = "103"
    m, root, result, calls = capture(tmp_path, rows)
    pdfs = [s for s in calls if s["id"].startswith("primary-")]
    assert len(pdfs) == 2 and pdfs[0]["url"].endswith("/" + selected + ".PDF")
    assert result["outcome"]["status"] == m.COMPLETE
    decision = result["outcome"]["version_qualification"]["report"]
    assert decision["selected_announcement_id"] == selected
    if suffix:
        assert disposition(decision, "101") == "SUPERSEDED"
        assert not any(s["url"].endswith("/101.PDF") for s in pdfs)
    assert m.verify(root)["status"] == "OFFLINE_VERIFICATION_PASS"


@pytest.mark.parametrize("reports, expected", [
    ([REPORT, REPORT], "REPORT_VERSION_AMBIGUOUS"),
    ([REPORT + "摘要"], "FORMAL_REPORT_MISSING"),
    ([REPORT, "关于" + REPORT + "的更正公告"], "VERSION_RELATION_UNRESOLVED"),
    (["关于" + REPORT + "的修订说明"], "VERSION_RELATION_UNRESOLVED"),
    ([REPORT, "关于取消" + REPORT + "的公告"], "VERSION_RELATION_UNRESOLVED"),
    ([REPORT, "关于取消部分公告的说明"], "VERSION_RELATION_UNRESOLVED"),
    ([REPORT, REPORT + "（修订版）", REPORT + "（更正版）"], "REPORT_VERSION_AMBIGUOUS"),
])
def test_capture_report_gap_is_decided_before_any_pdf(tmp_path, reports, expected):
    rows = [row(i, title) for i, title in enumerate(reports, 10)] + [row(2, IR)]
    m, root, result, calls = capture(tmp_path, rows)
    assert result["outcome"]["problem"] == expected
    assert [s["id"] for s in calls] == ["issuer-map", "inventory-1"]
    assert result["outcome"]["bodies"] == []
    assert m.verify(root)["capture_status"] == m.INCOMPLETE


@pytest.mark.parametrize("variant", [REPORT + "（英文版）", "H股公告：" + REPORT,
                                    "2026 Interim Report"])
def test_capture_language_or_market_variant_is_not_a_second_current_body(tmp_path, variant):
    m, root, result, calls = capture(tmp_path, [row(1, REPORT), row(2, IR), row(3, variant)])
    assert result["outcome"]["status"] == m.COMPLETE
    report = result["outcome"]["version_qualification"]["report"]
    assert report["selected_announcement_id"] == "101"
    assert disposition(report, "103") == "NOT_CANDIDATE"
    assert not any(s["url"].endswith("/103.PDF") for s in calls)
    assert m.verify(root)["status"] == "OFFLINE_VERIFICATION_PASS"


@pytest.mark.parametrize("day", ["2026-08-27", "2026-08-28", "2026-09-02"])
@pytest.mark.parametrize("suffix", ["修订版", "更正版"])
def test_capture_ir_revision_in_complete_inventory_supersedes_target(tmp_path, day, suffix):
    rows = [row(1, REPORT), row(2, IR), row(3, IR + f"（{suffix}）", day)]
    m, root, result, calls = capture(tmp_path, rows)
    assert result["outcome"]["status"] == m.COMPLETE
    ir = result["outcome"]["version_qualification"]["ir"]
    assert ir["selected_announcement_id"] == "103" and disposition(ir, "102") == "SUPERSEDED"
    assert calls[-1]["url"].endswith("/103.PDF")
    assert not any(s["url"].endswith("/102.PDF") for s in calls)
    assert m.verify(root)["status"] == "OFFLINE_VERIFICATION_PASS"


@pytest.mark.parametrize("updates, expected", [
    ([IR, IR], "RELEVANT_IR_AMBIGUOUS"),
    ([IR, "投资者关系活动记录表"], "RELEVANT_IR_AMBIGUOUS"),
    ([IR, "关于" + IR + "的更正公告"], "IR_VERSION_RELATION_UNRESOLVED"),
    (["关于投资者关系活动记录的更正公告"], "IR_VERSION_RELATION_UNRESOLVED"),
    ([IR, "关于取消" + IR + "的公告"], "IR_VERSION_RELATION_UNRESOLVED"),
    ([IR, IR + "（修订版）", IR + "（更正版）"], "RELEVANT_IR_AMBIGUOUS"),
    ([IR, "2026年8月28日投资者关系活动记录表（修订版）"], "IR_VERSION_RELATION_UNRESOLVED"),
])
def test_capture_ir_ambiguity_or_unresolved_notice_blocks_even_h1_download(tmp_path, updates, expected):
    rows = [row(1, REPORT)] + [row(i, title) for i, title in enumerate(updates, 10)]
    m, root, result, calls = capture(tmp_path, rows)
    assert result["outcome"]["problem"] == expected
    assert [s["id"] for s in calls] == ["issuer-map", "inventory-1"]
    assert result["outcome"]["bodies"] == []
    assert m.verify(root)["capture_status"] == m.INCOMPLETE


def test_capture_inventory_finishes_before_revision_is_selected(tmp_path):
    rows = [row(1, REPORT), row(2, IR)] + [row(i, "其它公告") for i in range(10, 38)]
    rows.append(row(50, REPORT + "（修订版）", "2026-08-28"))
    m, root, result, calls = capture(tmp_path, rows)
    assert result["outcome"]["status"] == m.COMPLETE
    assert [s["id"] for s in calls] == ["issuer-map", "inventory-1", "inventory-2", "primary-1", "primary-2"]
    assert calls[3]["url"].endswith("/150.PDF")
    assert m.verify(root)["status"] == "OFFLINE_VERIFICATION_PASS"


def test_capture_selected_revision_http_failure_never_falls_back_to_original(tmp_path):
    rows = [row(1, REPORT), row(2, IR), row(3, REPORT + "（修订版）", "2026-08-28")]
    m, root, result, calls = capture(tmp_path, rows, fail_pdf=True)
    assert result["outcome"]["problem"] == "HTTP_REJECTED"
    assert len(calls) == 3 and calls[-1]["url"].endswith("/103.PDF")
    assert not any(s["url"].endswith("/101.PDF") for s in calls)
    assert m.verify(root)["capture_status"] == m.INCOMPLETE


def test_capture_replay_recomputes_version_disposition_and_keeps_authority(tmp_path, monkeypatch):
    rows = [row(1, REPORT), row(2, IR), row(3, REPORT + "（修订版）", "2026-08-28")]
    m, root, result, _ = capture(tmp_path, rows)
    monkeypatch.setattr(m, "public_request", lambda _: pytest.fail("offline network"))
    assert m.verify(root)["network_calls"] == 0
    assert result["outcome"].items() >= m.AUTHORITY.items()
    versions = result["outcome"]["version_qualification"]
    versions["report"]["records"][0]["disposition"] = "CURRENT"
    result["capture_hash"] = m.canonical_hash({k: v for k, v in result.items() if k != "capture_hash"})
    (root / "capture.json").write_bytes(m.data(result))
    with pytest.raises(m.CaptureError, match="OFFLINE_SELECTION_OR_OUTCOME_MISMATCH"):
        m.verify(root)
