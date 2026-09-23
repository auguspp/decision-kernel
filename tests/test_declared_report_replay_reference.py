"""Same-PDF proof by exact replay rather than duplicate complete text."""
import pytest
from decision_kernel.runtime import reviewed_full_input as full, stock_question_host as host
from test_declared_report_input import setup_declared, rebuild


@pytest.mark.parametrize("damage", [None, "reading-hash", "note-commit", "body", "current-note"])
def test_compact_reading_proof_replays_same_complete_pdf_without_duplicate_body(tmp_path, monkeypatch, damage):
    c = setup_declared(tmp_path, monkeypatch, image=True)
    doc = c.context["issuer_documents"][0]
    value = doc["page_reading"]
    doc["page_reading"] = {"policy": full.PAGE_REFERENCE, "reading_hash": value["reading_hash"],
                           "review_commit": c.args["code"]}
    doc["pages"] = [{"page_number": p["page_number"], "text": p["text"]} for p in value["pages"]]
    if damage == "reading-hash": doc["page_reading"]["reading_hash"] = "0" * 64
    elif damage == "note-commit": doc["page_reading"]["review_commit"] = "f" * 40
    elif damage == "body": doc["pages"][-1]["text"] += "removed risk"
    elif damage == "current-note": c.api.files[c.args["code"]][c.note_source["path"]] += b"changed"
    rebuild(c)
    result = host.run_question(**c.args)
    assert result["status"] == ("VALIDATED_FUNNEL_RESULT" if damage is None else "NOT_EXECUTED"), result
    if damage is None:
        assert c.calls == ["pre"]
    else:
        assert c.calls == [] and c.writes == []
