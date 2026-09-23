"""Same saved question's first formal invocation, never resetting a prior launch."""
import pytest
from decision_kernel.runtime import saved_research_once as once, stock_question_host as host
from test_industry_daily_question import setup_industry
from test_reviewed_full_input import seal_full


@pytest.mark.parametrize("packed", [True, False])
def test_retained_interactive_analysis_keeps_same_question_and_cannot_spend_twice(tmp_path, monkeypatch, packed):
    from datetime import timedelta
    from decision_kernel.runtime import current_state as reading
    c = setup_industry(tmp_path, monkeypatch)
    prior_ref = "1234567890abcdef1234567890abcdef12345678"
    raw = once.raw({"question_id": c.q["question_id"], "status": "RETAINED_INTERACTIVE_ANALYSIS_NOT_FORMAL_EXECUTION"})
    source = once.source_ref("docs/readings/synthetic/prior-analysis.json", prior_ref, raw, "RETAINED_ANALYSIS_PREDECESSOR")
    c.api.files[prior_ref] = {source["path"]: raw}
    c.commits[prior_ref] = {"sha": prior_ref, "committer": {"date":
        (reading.clock(c.args["clock"]()) - timedelta(minutes=60)).isoformat()}}
    c.q["existing_research_relation"] = {"kind": "CONTINUE_ANALYSIS",
        "note": "Same retained interactive question; first formal host execution, not a new distinct question.",
        "source_refs": [source]}
    if packed:
        c.context["source_limitations"] += "x" * 550_000
        seal_full(c)
    else:
        from test_stock_daily_question import refresh
        refresh(c)
    result = host.run_question(**c.args)
    if not packed:
        assert result["status"] == "NOT_EXECUTED", result
        assert c.calls == [] and c.writes == []
        return
    assert result["status"] == "VALIDATED_FUNNEL_RESULT", result
    assert result["question_id"] == c.q["question_id"] and c.calls == ["pre"]
    before = len(c.writes)
    again = host.run_question(**{**c.args, "output": tmp_path / "again"})
    assert again["status"] == "EXISTING_QUESTION_REUSED_NO_EXECUTION", again
    assert c.calls == ["pre"] and len(c.writes) == before
