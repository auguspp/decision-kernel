"""Synthetic reading presentation; never a new market/Research acceptance sample."""
import copy
import socket
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import current_state_delivery as delivery


def ref(path):
    return {"read_path": path, "read_ref_rule": "USE_THE_SAME_PINNED_READING_COMMIT"}


def packet():
    def row(code, name, failure=None):
        return {"thscode": code, "company_name": name, "status": "CONTRACT_CHECKED_RAW_READING",
                "excluded_reasons": [], "input_failure": failure}
    stock = {"market_session": "2026-09-11", "status": "PARTIAL_STOCKS_FOR_SHADOW_READING",
             "coverage": {"planned_issuers": 6, "price_path_checked_issuers": 4,
                          "qualified_issuers": 4, "conditions_not_met_issuers": 0,
                          "unavailable_issuers": 2, "scope_complete": False},
             "dispositions": [row("600184.SH", "光电股份"), row("300183.SZ", "东软载波"),
                 row("603353.SH", "和顺石油"), row("300711.SZ", "广哈通信"),
                 row("600967.SH", "内蒙一机", {"reason_code": "CURRENT_QUOTE_HISTORY_MISMATCH"}),
                 row("001316.SZ", "润贝航科", {"reason_code": "REPORTED_CORPORATE_ACTION_IN_WINDOW_REQUIRES_REVIEW"})],
             "surfaced_codes": ["600184.SH", "603353.SH", "300711.SZ"],
             "omitted_eligible_codes": ["300183.SZ"],
             "details": {"reading/stock-reading.json": ref("details/stock/1/reading/stock-reading.json")}}
    sector = {"market_session": "2026-09-11", "status": "SAVED_SYNTHETIC",
              "coverage": [{"family": "BROAD_881", "nodes": 90, "ongoing": 10},
                           {"family": "GRANULAR_884", "nodes": 230, "ongoing": 25}],
              "details": {"summary.md": ref("details/sector/2/summary.md"),
                          "context/context.json": ref("details/sector/2/context/context.json")}}
    research = {"handoffs": {"active": []}, "records": [], "gaps": []}
    lanes = {k: {"health": "LATEST_ATTEMPT_SUCCEEDED", "gaps": [], "last_qualified_result": v}
             for k, v in (("stock", stock), ("sector", sector))}
    return read.assemble(code_commit="a" * 40, checked_at="2026-09-14T07:00:00+00:00",
                         check_started_at="2026-09-14T06:59:00+00:00", lanes=lanes,
                         research=research, capabilities=[], refresh_identity={})


def reseal(p):
    p["reading_hash"] = canonical_hash({k: v for k, v in p.items() if k != "reading_hash"})
    return p


def test_full_dispositions_and_omitted_qualified_stock_remain_visible_without_network(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *a: pytest.fail("network in renderer"))
    p = packet(); before = copy.deepcopy(p)
    result = read.render_summary(p)
    assert p == before
    assert "计划 6 只" in result and "通过价格观察 4 只" in result and "数据不可用 2 只" in result
    for row in p["lanes"]["stock"]["last_qualified_result"]["dispositions"]:
        assert row["company_name"] in result and row["thscode"] in result
    assert "仅因展示上限未列首页" in result
    assert "SYSTEM RECHECK" in result and "CAPABILITY GAP" in result
    assert "未作价格条件否决" in result
    assert "不要求 Human 手工复权" in result
    assert "暂不值得投资" not in result
    assert not p["pending"] and all(p[k] == "NONE" for k in read.AUTHORITY)


def test_full_ongoing_context_is_linked_separately_from_new_events():
    result = read.render_summary(packet())
    assert "details/sector/2/context/context.json" in result
    assert "details/sector/2/summary.md" in result
    assert "覆盖 90 个；仍满足原条件 10 个" in result
    assert "覆盖 230 个；仍满足原条件 25 个" in result
    assert "不据此重发新事件" in result
    assert "未覆盖的概念/主题不能写成没有变化" in result


def test_missing_or_partial_old_fields_are_unknown_not_zero_or_no_research():
    p = packet(); stock = p["lanes"]["stock"]["last_qualified_result"]
    del stock["coverage"]["qualified_issuers"]
    stock["coverage"]["price_path_checked_issuers"] = True
    stock["dispositions"] = []
    result = read.render_summary(reseal(p))
    assert "通过价格观察 UNKNOWN 只" in result and "完成价格路径判断 UNKNOWN 只" in result
    assert "未提供逐股处置" in result and "不代表没有历史研究" in result


def test_unavailable_lanes_preserve_unknown_not_quiet():
    p = packet()
    for v in p["lanes"].values():
        v.update(health="CHECK_INCOMPLETE", last_qualified_result=None, gaps=["UNAVAILABLE"])
    result = read.render_summary(reseal(p))
    assert "不是零候选" in result and "不是无持续状态" in result
    assert "CHECK&#95;INCOMPLETE" in result


@pytest.mark.parametrize("path", ["../main", "https://example.com/run", "javascript:alert(1)",
                                 "/details/a", "sources/git/../bad", "details/a\\b", "docs/a.md"])
def test_navigation_rejects_non_retained_or_unsafe_paths(path):
    p = packet()
    p["lanes"]["stock"]["last_qualified_result"]["details"]["reading/stock-reading.json"] = ref(path)
    result = read.render_summary(reseal(p))
    assert "全部股票、发现来路及原条件（入口未核验）" in result
    assert f"]({path})" not in result


def test_wrong_ref_rule_does_not_link_mutable_main():
    p = packet()
    p["lanes"]["sector"]["last_qualified_result"]["details"]["summary.md"]["read_ref_rule"] = "MAIN"
    assert "全部新变化与被首页省略的组（入口未核验）" in read.render_summary(reseal(p))


def test_source_markup_escaped_and_path_uri_encoded():
    p = packet(); row = p["lanes"]["stock"]["last_qualified_result"]["dispositions"][0]
    row["company_name"] = "<script>|[BUY](javascript:x)\nnew"
    p["research"]["records"] = [{"id": "<img>", "case": "600184.SH", "use": "METHOD_SUPPLEMENT",
        "purpose_note": "[run](https://evil.example) <script>", "source": ref("sources/git/abc/a (1).md")}]
    result = read.render_summary(reseal(p))
    assert "<script>" not in result and "<img>" not in result and "[BUY]" not in result
    assert "&lt;script&gt;" in result and "a%20%281%29.md" in result
    assert "[run](https://evil.example)" not in result


def test_review_and_old_execution_remain_separate_no_retroactive_terminal_change():
    p = packet(); source = ref("sources/git/" + "b" * 40 + "/review.md")
    p["research"]["records"] = [{"id": "exact-old-candidate-review", "case": "603353.SH",
        "use": "METHOD_SUPPLEMENT", "purpose_note": "旧终局理由受挑战；不是新WAIT或Human接受", "source": source}]
    old = {"thscode": "603353.SH", "status": "PRE_EXECUTION_FAILURE",
           "sources": {"failure": ref("sources/git/" + "c" * 40 + "/failure.json")},
           "source_successor_continuation": {"status": "VALIDATED_FUNNEL_CANDIDATE",
               "terminal_state": "WAIT_FOR_TRIGGER", "semantic_acceptance": "NOT_ESTABLISHED_BY_READER",
               "sources": {"candidate": ref("sources/git/" + "d" * 40 + "/candidate.json")}}}
    p["research"]["stock_business_work"] = {"status": "READ_OK", "items": [old]}
    before = copy.deepcopy(reseal(p)); result = read.render_summary(p)
    assert p == before
    assert "exact-old-candidate-review" in result and "旧终局理由受挑战" in result
    assert "原始执行记录" in result and "技术接续记录" in result
    assert "仅按同一股票代码取代" in result
    assert "本读取未提供对应记录；不代表已查且无业务证据" in result


def test_failed_registered_review_is_visible_not_silently_absent():
    p = packet(); p["research"]["gaps"] = [{"id": "review-a", "status": "RESEARCH_REFERENCE_REJECTED"}]
    assert "研究读取缺口：review-a；不能据此断言无研究或无更正" in read.render_summary(reseal(p))


def test_registered_supplement_uses_original_source_binding_and_single_copy(monkeypatch, tmp_path):
    raw = b"An append-only review is not an execution or permission.\n"
    calls = []
    def file(root, commit, path):
        calls.append((commit, path)); return raw
    monkeypatch.setattr(delivery, "git_file", file)
    c = delivery.Collector(None, "a" * 40, tmp_path)
    spec = {"path": "docs/readings/review.md", "git_blob": read.blob_sha(raw)}
    one = c.source(spec); two = c.source(spec)
    assert one == two and len(calls) == 1 and len(c.files) == 1
    assert c.files[one[1]["read_path"]] == raw
    with pytest.raises(ValueError, match="frozen blob"):
        c.source({**spec, "git_blob": "0" * 40})
