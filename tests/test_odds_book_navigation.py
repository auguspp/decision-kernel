"""Odds Book uses existing purpose retention; no semantic or investment acceptance."""
import copy
import json
import re
from pathlib import Path

import pytest

from decision_kernel.runtime import current_state as reading
from decision_kernel.runtime import current_state_delivery as delivery

ROOT = Path(__file__).resolve().parents[1]
M = "a" * 40
R1, R2 = "b" * 40, "c" * 40


def registry():
    return json.loads((ROOT / "current_state/registry.json").read_text(encoding="utf-8"))


def test_book_is_one_explicit_navigation_record_not_a_production_package():
    rows = [r for r in registry()["references"] if r["id"] == "odds-book"]
    assert len(rows) == 1
    assert rows[0]["use"] == "NAVIGATION_ONLY"
    assert rows[0]["source"]["path"] == "docs/ODDS-BOOK.md"
    source = (ROOT / "docs/ODDS-BOOK.md").read_text(encoding="utf-8")
    assert "DECLARED_COVERAGE_BACKFILL" in source
    assert "WATCH_NOT_ENABLED" in source
    assert "NOT_SAVED / REGISTRATION_INCOMPLETE / PUBLICATION_PENDING" in source
    assert "全仓自动扫描器" in source
    workflow = (ROOT / reading.WORKFLOWS["inbox"]).read_text(encoding="utf-8")
    assert rows[0]["source"]["path"] not in reading.configured_paths(workflow, "decision_packages")
    assert rows[0]["source"]["path"] not in reading.configured_paths(workflow, "research_attention_handoffs")
    assert "Odds Book v0" in (ROOT / "docs/RESEARCH-ENTRY.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("code", ["600276.SH", "600967.SH", "002674.SZ", "600184.SH",
    "600598.SH", "002050.SZ", "603986.SH", "600519.SH", "601088.SH", "300750.SZ", "600036.SH"])
def test_declared_real_case_has_visible_book_row_without_fabricating_an_odds_run(code):
    text = (ROOT / "docs/ODDS-BOOK.md").read_text(encoding="utf-8")
    table = text.split("## 2.")[0]
    assert f"**{code}**" in table
    assert "非本日价格" in table and "未启用" in table


def test_old_branch_and_accepted_provisional_sources_have_exact_separate_identities():
    rows = {r["id"]: r for r in registry()["references"]}
    old = rows["odds-guangdian-historical"]
    assert old["source"]["ref"] == "9cd072a8e8b5ec1b5fd88e7bfcf9e1d6ae2cd21a"
    assert old["source"]["git_blob"] == "895ba811d96750d02a4f0d7c08358b5e7fed3088"
    assert rows["odds-guangdian-challenge"]["source"]["git_blob"] == "174e02ecc48eb851324b830798f996c0f6705a02"
    for key in ("odds-hengrui-provisional", "odds-hengrui-human", "odds-neimeng-human",
                "odds-xingye-revision", "odds-xingye-human", "odds-beidahuang-provisional",
                "odds-inbox-history-20260911"):
        assert re.fullmatch(r"[0-9a-f]{40}", rows[key]["source"]["ref"])
        assert re.fullmatch(r"[0-9a-f]{40}", rows[key]["source"]["git_blob"])
        assert rows[key]["use"] != "CONFIRMED_ACTION_CHECKPOINT"
    # Leave room for the original config, production packages, handoffs and gaps.
    specs = {(r["source"].get("ref", M), r["source"]["path"]) for r in rows.values()}
    assert len(specs) + 12 <= delivery.MAX_SOURCE_FILES


class SavedAPI:
    def __init__(self, values):
        self.values, self.reads = values, []

    def file(self, path, ref):
        self.reads.append((path, ref))
        return self.values[(path, ref)]

    def write(self, *_args, **_kwargs):
        raise AssertionError("Reading the Odds Book must not write or dispatch")


def test_existing_collector_retains_old_and_new_versions_without_ticker_supersession(tmp_path, monkeypatch):
    path = "docs/synthetic-odds.json"
    values = {(path, R1): b'{"human_acceptance":"NOT_RECORDED","odds":"PROVISIONAL"}',
              (path, R2): b'{"human_acceptance":"NOT_ACCEPTED_YET","odds":"CHALLENGED"}'}
    api = SavedAPI(values)
    collector = delivery.Collector(api, M, tmp_path)
    config = b"decision_packages=(\n)\nresearch_attention_handoffs=(\n)\n"
    monkeypatch.setattr(delivery, "git_file", lambda root, ref, p: config)
    rows = [{"id": f"synthetic-{n}", "case": "600184.SH", "use": "RETAINED_ODDS_DOCUMENT",
             "purpose_note": "Synthetic retention check, not real company evidence",
             "source": {"path": path, "ref": ref, "git_blob": reading.blob_sha(values[(path, ref)])}}
            for n, ref in enumerate((R1, R2))]
    before = copy.deepcopy(rows)
    result = collector.research({"references": rows, "historical_handoffs": []})
    assert rows == before and len(result["records"]) == 2 and result["gaps"] == []
    assert result["confirmed_actions"] == []
    assert not result["handoffs"]["active"]
    assert all(r["qualification"] == "EXPLICIT_PURPOSE_REFERENCE_NOT_AUTOMATIC_SUPERSESSION"
               for r in result["records"])
    for record in result["records"]:
        source = record["source"]
        assert source["read_ref_rule"] == "USE_THE_SAME_PINNED_READING_COMMIT"
        assert collector.files[source["read_path"]] == values[(path, source["ref"])]
    assert api.reads == [(path, R1), (path, R2)]


def test_wrong_frozen_odds_blob_is_a_visible_reference_gap_not_a_new_good_result(tmp_path, monkeypatch):
    path = "docs/synthetic-odds.json"
    collector = delivery.Collector(SavedAPI({(path, R1): b"changed"}), M, tmp_path)
    monkeypatch.setattr(delivery, "git_file", lambda *_: b"decision_packages=(\n)\nresearch_attention_handoffs=(\n)\n")
    result = collector.research({"references": [{"id": "synthetic-old", "case": "600184.SH",
        "use": "RETAINED_ODDS_DOCUMENT", "purpose_note": "not real",
        "source": {"path": path, "ref": R1, "git_blob": "0" * 40}}], "historical_handoffs": []})
    assert result["records"] == []
    assert result["gaps"] == [{"id": "synthetic-old", "status": "RESEARCH_REFERENCE_REJECTED", "error_type": "ValueError"}]
    assert result["confirmed_actions"] == []


def test_book_links_use_immutable_repository_refs_or_exact_process_receipts():
    text = (ROOT / "docs/ODDS-BOOK.md").read_text(encoding="utf-8")
    definitions = dict(re.findall(r"^\[([^\]]+)\]: (https://\S+)$", text, re.M))
    references = set(re.findall(r"\]\[([^\]]+)\]", text))
    assert references <= definitions.keys()
    assert len(definitions) >= 10
    for url in definitions.values():
        assert url.startswith("https://github.com/auguspp/decision-kernel/")
        assert re.search(r"/blob/[0-9a-f]{40}/", url) or re.search(r"/issues/\d+#issuecomment-\d+$", url)
    assert "NOT_ACCEPTED_YET" in text and "不是REJECTED" in text
    assert "本次未typed复验" in text
