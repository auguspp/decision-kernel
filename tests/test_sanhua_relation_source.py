"""Relation-only profile; synthetic HTTP only, no live CNINFO or H1 reacquisition."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from decision_kernel.runtime import sanhua_source_acquisition as m

IR = "2026年8月27日投资者关系活动记录表"
ORG = "gssz0002050"
PDF = b"%PDF-1.4\nSynthetic IR container; no Research content.\n%%EOF\n"


def row(number, title=IR, day="2026-08-27"):
    return {"announcementId": str(number), "announcementTitle": title,
            "secCode": m.CODE, "orgId": ORG,
            "announcementTime": int(datetime.fromisoformat(day + "T00:00:00+08:00").timestamp() * 1000),
            "adjunctUrl": f"finalpage/{day}/{number}.PDF"}


def capture(tmp_path, rows, *, damage=None, pdf_status=200, channel="relation", name="capture"):
    calls = []
    def request(spec):
        m.allowed(spec, channel=channel)
        calls.append(copy.deepcopy(spec))
        if spec["id"] == "issuer-map":
            payload = {"stockList": [{"code": m.CODE, "orgId": ORG, "zwjc": m.ISSUER}]}
        elif spec["id"].startswith("inventory-"):
            page = int(spec["params"]["pageNum"])
            payload = {"announcements": copy.deepcopy(rows[(page - 1) * 30:page * 30]),
                       "hasMore": page * 30 < len(rows), "totalAnnouncement": len(rows)}
            if damage:
                damage(payload)
        else:
            assert spec["id"].startswith("primary-")
            if pdf_status != 200:
                return m.Response(pdf_status, "text/html", None, "HTTP_REJECTED")
            return m.Response(200, "application/pdf", PDF)
        return m.Response(200, "application/json", m.data(payload))
    root = tmp_path / name
    result = m.capture(root, request=request, channel=channel,
                       now=lambda: datetime(2026, 9, 9, 6, 0, tzinfo=timezone.utc))
    return root, result, calls


def test_fixed_profile_does_not_rewrite_legacy_fulltext_plan():
    frozen = json.loads(Path(".github/source-acquisition/sanhua-v0-20260909.json").read_text())
    assert m.plan() == frozen["plan"]
    profile = m.plan("relation")
    assert profile["max_pages"] == 3 and profile["page_size"] == 30
    assert profile["max_primary_bodies"] == 1 and profile["max_requests"] == 5
    assert profile["technical_retries"] == 0 and profile["alternate_primary_routes"] == []
    assert profile["source_channel"] == "CNINFO_RELATION"
    assert "formal_report" not in profile
    assert "FORMAL_CURRENT_PERIOD_ACTUALS" not in profile["required_classes"]
    q = m.query(ORG, 1)
    q["params"]["tabName"] = "relation"
    assert q == m.query(ORG, 1, channel="relation")


def test_relation_retains_only_ir_and_replays_without_network(tmp_path, monkeypatch):
    root, result, calls = capture(tmp_path, [row(11), row(1225514004, "2026年半年度报告")])
    assert [s["id"] for s in calls] == ["issuer-map", "inventory-1", "primary-1"]
    assert calls[1]["params"]["tabName"] == "relation"
    assert calls[-1]["url"].endswith("/11.PDF")
    out = result["outcome"]
    assert out["status"] == m.COMPLETE and out["inventory_complete"]
    assert set(out["version_qualification"]) == {"ir"}
    assert len(out["bodies"]) == 1 and out["bodies"][0]["sha256"] == m.sha(PDF)
    assert out["bodies"][0]["source_identity"]["org_id"] == ORG
    assert out.items() >= m.AUTHORITY.items()
    assert result["research_cutoff"] is None and result["provenance"] == m.SYNTHETIC
    monkeypatch.setattr(m, "public_request", lambda *a, **kw: pytest.fail("offline HTTP"))
    verified = m.verify(root, channel="relation")
    assert verified["network_calls"] == 0 and verified["research_execution"] == "NOT_EXECUTED"
    assert verified["capture_status"] == m.COMPLETE
    with pytest.raises(m.CaptureError, match="PLAN_MISMATCH"):
        m.verify(root)  # No automatic cross-channel reinterpretation.


@pytest.mark.parametrize("rows, problem", [
    ([], "RELEVANT_IR_MISSING_FROM_RELATION_INVENTORY"),
    ([row(10, "2026年半年度报告")], "RELEVANT_IR_MISSING_FROM_RELATION_INVENTORY"),
    ([row(11), row(12)], "RELEVANT_IR_AMBIGUOUS"),
    ([row(11), row(12, "关于" + IR + "的更正公告")], "IR_VERSION_RELATION_UNRESOLVED"),
    ([row(11), row(12, "关于取消" + IR + "的公告")], "IR_VERSION_RELATION_UNRESOLVED"),
    ([row(11), row(12, IR + "（修订版）"), row(13, IR + "（更正版）")], "RELEVANT_IR_AMBIGUOUS"),
    ([row(11), row(12, "2026年8月28日投资者关系活动记录表（修订版）")], "IR_VERSION_RELATION_UNRESOLVED"),
])
def test_relation_version_gap_precedes_all_pdf_requests(tmp_path, rows, problem):
    root, result, calls = capture(tmp_path, rows)
    assert [s["id"] for s in calls] == ["issuer-map", "inventory-1"]
    assert result["outcome"]["problem"] == problem and result["outcome"]["bodies"] == []
    assert m.verify(root, channel="relation")["capture_status"] == m.INCOMPLETE


@pytest.mark.parametrize("suffix", ["修订版", "更正版"])
def test_complete_window_revision_beats_original_without_h1(tmp_path, suffix):
    rows = [row(11)] + [row(i, "其它公告") for i in range(100, 129)]
    rows.append(row(12, IR + f"（{suffix}）", "2026-09-02"))
    root, result, calls = capture(tmp_path, rows)
    assert [s["id"] for s in calls] == ["issuer-map", "inventory-1", "inventory-2", "primary-1"]
    assert calls[-1]["url"].endswith("/12.PDF")
    decision = result["outcome"]["version_qualification"]["ir"]
    assert decision["selected_announcement_id"] == "12"
    assert next(r for r in decision["records"] if r["announcement_id"] == "11")["disposition"] == "SUPERSEDED"
    assert m.verify(root, channel="relation")["status"] == "OFFLINE_VERIFICATION_PASS"


@pytest.mark.parametrize("status", [429, 503, 302])
def test_current_ir_download_failure_does_not_retry_or_fall_back(tmp_path, status):
    root, result, calls = capture(tmp_path, [row(11), row(12, IR + "（修订版）", "2026-08-28")],
                                  pdf_status=status)
    assert len(calls) == 3 and calls[-1]["url"].endswith("/12.PDF")
    assert result["outcome"]["problem"] == "HTTP_REJECTED" and result["outcome"]["bodies"] == []
    assert m.verify(root, channel="relation")["capture_status"] == m.INCOMPLETE


@pytest.mark.parametrize("damage", [
    lambda p: p["announcements"][0].update(secCode="600000"),
    lambda p: p["announcements"][0].update(orgId="other"),
    lambda p: p.update(totalAnnouncement=2),
    lambda p: p.update(hasMore=None),
    lambda p: p.update(totalAnnouncement=91, hasMore=True),
    lambda p: p["announcements"][0].update(announcementTime=None),
])
def test_existing_inventory_guards_run_before_relation_pdf(tmp_path, damage):
    root, result, calls = capture(tmp_path, [row(11)], damage=damage)
    assert len(calls) == 2 and result["outcome"]["status"] == m.INCOMPLETE
    assert result["outcome"]["bodies"] == []
    assert m.verify(root, channel="relation")["capture_status"] == m.INCOMPLETE


def test_five_http_ceiling_and_one_body_limit(tmp_path):
    rows = [row(i, "其它公告") for i in range(100, 189)] + [row(11)]
    root, result, calls = capture(tmp_path, rows)
    assert len(calls) == 5 and len(result["outcome"]["bodies"]) == 1
    assert result["outcome"]["inventory_total"] == 90
    assert m.verify(root, channel="relation")["status"] == "OFFLINE_VERIFICATION_PASS"
    with pytest.raises(m.CaptureError):
        m.allowed(m.query(ORG, 1), channel="relation")
    with pytest.raises(m.CaptureError):
        m.allowed({**calls[-1], "id": "primary-2"}, channel="relation")


def test_unsupported_channel_never_creates_capture_or_calls_transport(tmp_path):
    root = tmp_path / "forbidden"
    with pytest.raises(m.CaptureError, match="UNREVIEWED_SOURCE_CHANNEL"):
        m.capture(root, channel="hkex", request=lambda s: pytest.fail("HTTP called"))
    assert not root.exists()


def test_relabelled_fulltext_journal_cannot_be_laundered_as_relation(tmp_path):
    root, result, _ = capture(tmp_path, [row(11), row(12, "2026年半年度报告")], channel="fulltext")
    profile = m.plan("relation")
    (root / "plan.json").write_bytes(m.data(profile))
    result["plan_hash"] = m.canonical_hash(profile)
    result["capture_hash"] = m.canonical_hash({k: v for k, v in result.items() if k != "capture_hash"})
    (root / "capture.json").write_bytes(m.data(result))
    with pytest.raises(m.CaptureError):
        m.verify(root, channel="relation")


def test_changed_version_disposition_and_new_manifest_hash_still_reject(tmp_path):
    root, result, _ = capture(tmp_path, [row(11), row(12, IR + "（修订版）", "2026-08-28")])
    result["outcome"]["version_qualification"]["ir"]["records"][0]["disposition"] = "CURRENT"
    result["capture_hash"] = m.canonical_hash({k: v for k, v in result.items() if k != "capture_hash"})
    (root / "capture.json").write_bytes(m.data(result))
    with pytest.raises(m.CaptureError, match="OFFLINE_SELECTION_OR_OUTCOME_MISMATCH"):
        m.verify(root, channel="relation")


def test_frozen_relation_request_and_one_shot_wiring_do_not_reacquire_h1():
    frozen = json.loads(Path('.github/source-acquisition/sanhua-relation-v0-20260909.json').read_text())
    assert frozen['plan'] == m.plan('relation')
    assert frozen['approved_base'] == 'b71ff68984a243f3aa397819336b7aaf7e586515'
    wf = Path('.github/workflows/sanhua-relation-acquisition.yml').read_text()
    assert 'schedule:' not in wf and 'workflow_dispatch:' not in wf
    assert 'paths: [.github/source-acquisition/sanhua-relation-v0-20260909.json]' in wf
    assert 'test "$GITHUB_RUN_ATTEMPT" = "1"' in wf
    assert 'test "$SOURCE_BASE" = "b71ff68984a243f3aa397819336b7aaf7e586515"' in wf
    assert 'git cat-file -e "$SOURCE_BASE:$request"' in wf
    assert 'cancel-in-progress: false' in wf and 'timeout-minutes: 10' in wf
    assert 'contents: read' in wf and 'actions: read' in wf and 'secrets.' not in wf
    assert 'actions/artifacts/10090204888/zip' in wf
    assert 'LEGACY_FULLTEXT_EXACT_OUTCOME_PASS' in wf
    capture_cmd = 'sanhua_source_acquisition capture sanhua-relation-package/capture --channel relation'
    assert wf.index('LEGACY_FULLTEXT_EXACT_OUTCOME_PASS') < wf.index(capture_cmd)
    assert 'sanhua_source_acquisition capture sanhua-source-package/' not in wf
    assert 'sanhua_source_acquisition verify sanhua-relation-package/capture --channel relation' in wf
    assert 'retention-days: 90' in wf


def test_relation_cli_verify_uses_declared_plan(tmp_path, capsys):
    root, result, _ = capture(tmp_path, [row(11)])
    assert m.main(['verify', str(root), '--channel', 'relation']) == 0
    output = json.loads(capsys.readouterr().out)
    assert output['capture_hash'] == result['capture_hash'] and output['network_calls'] == 0


def test_relation_same_input_and_clocks_produce_same_bytes(tmp_path):
    a, _, _ = capture(tmp_path, [row(11)], name='a')
    b, _, _ = capture(tmp_path, [row(11)], name='b')
    assert {p.name: p.read_bytes() for p in a.iterdir()} == {p.name: p.read_bytes() for p in b.iterdir()}
