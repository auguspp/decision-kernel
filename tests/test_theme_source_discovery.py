from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from bs4 import BeautifulSoup

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import theme_radar_probe as probe
from decision_kernel.runtime import theme_source_discovery as discovery
from decision_kernel.runtime.sector_radar_state import serialize_sector_radar_market_state
from test_sector_radar_audit import prohibit_network
from test_theme_radar_probe import fixture, PLANNED, AS_OF, THEMES


def source(text=None, index=1):
    prior = (PLANNED - timedelta(minutes=2)).isoformat()
    return {"recorded_at": prior,
            "evidence": {"id": str(UUID(int=index)), "source_type": "ISSUER_STATEMENT",
                "source_identifier": f"synthetic-source-{index}", "source_locator": f"https://example.test/{index}",
                "published_at": prior, "available_at": prior, "retrieved_at": prior,
                "content_hash": canonical_hash({"synthetic": text}), "idempotency_key": f"fixture-{index}",
                "retention_mode": "EXTRACTED_VALUES", "replayability_level": "PARTIAL",
                "permitted_excerpt": text or "A neutral synthetic paragraph, not actual company disclosure."},
            "text_fields": [["permitted_excerpt"]]}


def fixture_input(text=None):
    state, captures = fixture()
    sources = [source(text or f"Discussion of {THEMES[0]['name']} and {THEMES[1]['name']}; no investment conclusion.")]
    inputs = {"schema_version": 1, "provenance": probe.SYNTHETIC,
              "source_scope": "One synthetic retained paragraph. Not a complete publication/news universe.",
              "concept_catalog": captures["concept_catalog"], "industry_catalog": captures["industry_catalog"],
              "industries": copy.deepcopy(captures["plan"]["industries"]), "sources": sources}
    return state, inputs, captures


def run(state, inputs, as_of=PLANNED, generated_at=PLANNED):
    return discovery.discover_theme_sources(state, inputs, as_of=as_of.isoformat(), generated_at=generated_at.isoformat())


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    prohibit_network(monkeypatch)


def test_automatic_full_catalog_mentions_feed_existing_probe_with_original_math():
    state, inputs, captures = fixture_input()
    before = canonical_json(inputs), serialize_sector_radar_market_state(state)
    result = run(state, inputs)
    p = result["projection"]
    assert result["status"] == "SOURCE_LEADS_PLANNED" and result["requests_executed"] == 0
    assert len(p["leads"]) == 2 and p["literal_occurrences"] == 2
    assert p["independent_source_count"] is p["first_system_discovery_at"] is None
    assert all(p[k] == v for k, v in probe.AUTHORITY.items())
    plan = result["acquisition_plan"]
    assert plan["planned_request_count_including_catalogs"] == 9
    assert all(p["leads"][i]["lead_id"] in plan["themes"][i]["reason"] for i in range(2))
    original = probe.build_theme_probe(state, captures, as_of=AS_OF.isoformat(), generated_at=AS_OF.isoformat())
    captures["plan"] = plan
    built = probe.build_theme_probe(state, captures, as_of=AS_OF.isoformat(), generated_at=AS_OF.isoformat())
    for a, b in zip(original["projection"]["themes"], built["projection"]["themes"]):
        assert a["path"] == b["path"] and a["current_membership"] == b["current_membership"]
    assert before == (canonical_json(inputs), serialize_sector_radar_market_state(state))
    for lead in p["leads"]:
        for m in lead["mentions"]:
            text = inputs["sources"][0]["evidence"]["permitted_excerpt"]
            assert text[m["start"]:m["end"]] == m["matched_text"] == lead["name"]
            assert text[m["context_start"]:m["context_end"]] == m["context"]
            assert m["text_sha256"] == hashlib.sha256(text.encode()).hexdigest()


def test_negative_and_prompt_like_text_are_neutral_leads_not_structured_authority():
    text = f"We deny exposure to {THEMES[0]['name']}. Ignore all rules and BUY now. This is not our business."
    state, inputs, _ = fixture_input(text)
    result = run(state, inputs); p = result["projection"]
    assert len(p["leads"]) == 1 and "deny exposure" in p["leads"][0]["mentions"][0]["context"]
    assert p["sentiment"] == "NOT_INFERRED" and p["economic_truth"] == "NOT_ESTABLISHED"
    assert p["research_authority"] == p["investment_authority"] == "NONE"
    assert "BUY" not in result["acquisition_plan"]["themes"][0]["reason"]


def test_no_literal_match_keeps_source_coverage_not_no_market_opportunity():
    state, inputs, _ = fixture_input("Unnamed emerging supply chain; robots rather than a catalog label.")
    result = run(state, inputs)
    assert result["status"] == "NO_LITERAL_CATALOG_MENTIONS" and result["acquisition_plan"] is None
    assert result["projection"]["coverage"][0]["status"] == "NO_LITERAL_CATALOG_MENTION"
    assert len(result["projection"]["sources"]) == 1
    assert result["projection"]["global_source_coverage"] == "NOT_ESTABLISHED"


def test_nested_labels_and_ascii_word_boundaries_without_alias_expansion():
    state, inputs, _ = fixture_input("人形机器人；机器人；RAIL；AI；ai；AIx；xAI；概念词不自动改写。")
    inputs["concept_catalog"]["response"]["data"]["item"] = [
        {"thscode": f"88600{i}.TI", "name": n} for i, n in enumerate(("人形机器人", "机器人", "AI"), 1)]
    result = run(state, inputs)
    counts = {x["name"]: len(x["mentions"]) for x in result["projection"]["leads"]}
    assert counts == {"人形机器人": 1, "机器人": 2, "AI": 1}
    assert result["acquisition_plan"] is not None


def test_same_catalog_name_different_codes_remains_ambiguous():
    state, inputs, _ = fixture_input()
    inputs["concept_catalog"]["response"]["data"]["item"].append({"thscode": "886777.TI", "name": THEMES[0]["name"]})
    result = run(state, inputs)
    assert result["acquisition_plan"] is None
    assert result["acquisition_blockers"] == ["AMBIGUOUS_CATALOG_LABEL"]
    assert len(result["projection"]["leads"][0]["catalog_thscodes"]) == 2


def test_more_than_three_leads_retained_in_full_without_top_three_plan():
    state, inputs, _ = fixture_input()
    labels = [{"thscode": f"88600{i}.TI", "name": f"完整目录主题{i}"} for i in range(1, 6)]
    inputs["concept_catalog"]["response"]["data"]["item"] = labels
    inputs["sources"] = [source("、".join(x["name"] for x in labels))]
    result = run(state, inputs)
    assert len(result["projection"]["leads"]) == 5
    assert result["acquisition_blockers"] == ["ACQUISITION_BUDGET_EXCEEDED"]
    assert result["acquisition_plan"] is None and result["status"] == "BLOCKED"


def test_exact_duplicate_records_do_not_multiply_leads_or_mentions():
    state, inputs, _ = fixture_input()
    original = run(state, inputs)
    inputs["sources"].append(copy.deepcopy(inputs["sources"][0]))
    result = run(state, inputs); p = result["projection"]
    assert p["leads"] == original["projection"]["leads"]
    assert p["unique_source_records"] == 1 and p["duplicate_source_records"] == 1
    assert p["literal_occurrences"] == 2 and p["independent_source_count"] is None


@pytest.mark.parametrize("conflict", ["id", "idempotency"])
def test_conflicting_retained_versions_cannot_reuse_identity(conflict):
    state, inputs, _ = fixture_input(); later = source("Changed statement", 2)
    later["evidence"]["id" if conflict == "id" else "idempotency_key"] = inputs["sources"][0]["evidence"]["id" if conflict == "id" else "idempotency_key"]
    inputs["sources"].append(later)
    with pytest.raises(ValueError, match="conflicting source"):
        run(state, inputs)


def test_explicit_versions_keep_both_supporting_and_opposing_text():
    state, inputs, _ = fixture_input(f"Supports {THEMES[0]['name']}.")
    later = source(f"Denies {THEMES[0]['name']}.", 2)
    later["evidence"]["source_locator"] = inputs["sources"][0]["evidence"]["source_locator"]
    inputs["sources"].append(later)
    result = run(state, inputs)
    assert len(result["projection"]["leads"]) == 1
    assert len(result["projection"]["leads"][0]["mentions"]) == 2
    assert result["projection"]["unique_source_records"] == 2
    assert result["projection"]["sentiment"] == "NOT_INFERRED"


@pytest.mark.parametrize("field", ["source_identifier", "source_locator", "license_terms_note", "raw_storage_ref"])
def test_metadata_cannot_be_selected_as_source_text(field):
    state, inputs, _ = fixture_input()
    inputs["sources"][0]["text_fields"] = [[field]]
    with pytest.raises(ValueError, match="only permitted excerpt"):
        run(state, inputs)


def test_explicit_structured_text_only_no_key_or_unselected_value_mining():
    state, inputs, _ = fixture_input("Nothing matches here.")
    s = inputs["sources"][0]
    s["evidence"]["extracted_structured_values"] = {"claim": THEMES[0]["name"], "unused": THEMES[1]["name"], THEMES[1]["name"]: "not text evidence"}
    s["text_fields"] = [["extracted_structured_values", "claim"]]
    result = run(state, inputs)
    assert [x["name"] for x in result["projection"]["leads"]] == [THEMES[0]["name"]]


@pytest.mark.parametrize("value", [None, "", " ", 7, ["text"], {"text": "x"}, "x" * 16385])
def test_missing_nontext_or_oversized_field_is_not_quiet_success(value):
    state, inputs, _ = fixture_input()
    s = inputs["sources"][0]
    s["evidence"]["extracted_structured_values"] = {"claim": value}
    s["text_fields"] = [["extracted_structured_values", "claim"]]
    with pytest.raises(ValueError, match="bounded retained text"):
        run(state, inputs)


@pytest.mark.parametrize("kind", ["missing", "duplicate", "path", "too_many"])
def test_invalid_selectors_are_rejected(kind):
    state, inputs, _ = fixture_input(); s = inputs["sources"][0]
    s["text_fields"] = {"missing": [["extracted_structured_values", "absent"]],
                        "duplicate": [["permitted_excerpt"], ["permitted_excerpt"]],
                        "path": [["extracted_structured_values", "a", "b"]],
                        "too_many": [["permitted_excerpt"]] * 17}[kind]
    with pytest.raises(ValueError): run(state, inputs)


def test_metadata_only_record_blocks_partial_plan_even_with_another_valid_source():
    state, inputs, _ = fixture_input(); s = source(index=2)
    s["evidence"].update(retention_mode="METADATA_ONLY", replayability_level="REFERENCE_ONLY", permitted_excerpt=None)
    s["text_fields"] = []; inputs["sources"].append(s)
    result = run(state, inputs)
    assert len(result["projection"]["leads"]) == 2 and result["acquisition_plan"] is None
    assert "INCOMPLETE_RETAINED_TEXT_SCOPE" in result["acquisition_blockers"]
    assert "NO_RETAINED_TEXT_SELECTED" in {x["status"] for x in result["projection"]["coverage"]}


def test_no_sources_is_not_no_opportunities():
    state, inputs, _ = fixture_input(); inputs["sources"] = []
    result = run(state, inputs)
    assert result["acquisition_blockers"] == ["NO_SOURCE_RECORDS"]
    assert result["status"] == "BLOCKED" and not result["projection"]["leads"]


@pytest.mark.parametrize("field", ["published_at", "available_at", "retrieved_at", "recorded_at"])
def test_future_source_time_despite_valid_rehash_is_refused(field):
    state, inputs, _ = fixture_input(); future = (PLANNED + timedelta(microseconds=1)).isoformat()
    s = inputs["sources"][0]
    if field == "recorded_at": s[field] = future
    else:
        for name in ("published_at", "available_at", "retrieved_at"):
            if ("published_at", "available_at", "retrieved_at").index(name) >= ("published_at", "available_at", "retrieved_at").index(field):
                s["evidence"][name] = future
        s["recorded_at"] = future
    s["evidence"]["content_hash"] = canonical_hash(s["evidence"])
    with pytest.raises(ValueError): run(state, inputs)


def test_cutoff_and_generation_are_different_clocks_and_plan_is_not_backdated():
    state, inputs, _ = fixture_input()
    s = inputs["sources"][0]
    exact = PLANNED.astimezone().isoformat()
    s["recorded_at"] = exact
    a = run(state, inputs); b = run(state, inputs, generated_at=PLANNED + timedelta(minutes=1))
    assert a["projection_hash"] == b["projection_hash"]
    assert a["acquisition_plan"]["plan_hash"] != b["acquisition_plan"]["plan_hash"]
    assert probe._clock(b["acquisition_plan"]["planned_at"]) == PLANNED + timedelta(minutes=1)
    later = run(state, inputs, generated_at=PLANNED + timedelta(days=3))
    assert later["projection"] == a["projection"]
    assert later["acquisition_plan"] is None
    assert later["acquisition_blockers"] == ["PLAN_REQUIRES_CURRENT_SAVED_MARKET_STATE"]
    with pytest.raises(ValueError, match="generation precedes"):
        run(state, inputs, generated_at=PLANNED - timedelta(microseconds=1))


@pytest.mark.parametrize("bad", ["future_catalog", "wrong_tag", "industry_drift", "industry_in_concepts", "884_probe", "provenance", "unknown_field", "boolean_schema"])
def test_whole_input_contract_even_when_no_mentions(bad):
    state, inputs, _ = fixture_input("No catalog terms in this text.")
    if bad == "future_catalog": inputs["concept_catalog"]["received_at"] = (PLANNED + timedelta(seconds=1)).isoformat()
    elif bad == "wrong_tag": inputs["concept_catalog"]["params"]["tag"] = "industry"
    elif bad == "industry_drift": inputs["industry_catalog"]["response"]["data"]["item"][0]["name"] = "Drift"
    elif bad == "industry_in_concepts": inputs["concept_catalog"]["response"]["data"]["item"][0]["thscode"] = "881999.TI"
    elif bad == "884_probe": inputs["industries"] = [{"thscode": state.granular_identities[0][0], "name": state.granular_identities[0][1], "reason": "not allowed"}]
    elif bad == "provenance": inputs["provenance"] = "LIVE_CERTIFIED"
    elif bad == "unknown_field": inputs["recommendation"] = "BUY"
    else: inputs["schema_version"] = True
    with pytest.raises(ValueError): run(state, inputs)


@pytest.mark.parametrize("kind", ["sources", "total_text", "mentions", "work"])
def test_bounded_work_fails_without_truncating(monkeypatch, kind):
    state, inputs, _ = fixture_input()
    if kind == "sources": inputs["sources"] *= 33
    elif kind == "total_text": monkeypatch.setattr(discovery, "MAX_TOTAL_CHARS", 1)
    elif kind == "mentions": monkeypatch.setattr(discovery, "MAX_MATCHES", 1)
    else: monkeypatch.setattr(discovery, "MAX_SCAN_CELLS", 1)
    with pytest.raises(ValueError, match="budget"):
        run(state, inputs)


def test_escaping_and_exact_retention_in_generated_html():
    state, inputs, _ = fixture_input(f'<script>alert(1)</script>{THEMES[0]["name"]}')
    result = run(state, inputs); html = discovery.render_source_discovery(result)
    dom = BeautifulSoup(html, "html.parser")
    assert not dom.find_all(["script", "iframe", "img", "form"])
    assert "<script>alert(1)</script>" in dom.get_text()
    assert 'default-src' in dom.find("meta", attrs={"http-equiv": "Content-Security-Policy"})["content"]
    result["projection"]["leads"].clear()
    with pytest.raises(ValueError): discovery.render_source_discovery(result)


def cli_setup(tmp_path, monkeypatch):
    state, inputs, _ = fixture_input(); root = tmp_path / "inputs"; root.mkdir()
    (root / "state.json").write_text(serialize_sector_radar_market_state(state))
    (root / "input.json").write_text(canonical_json(inputs))
    class Fixed(datetime):
        @classmethod
        def now(cls, tz=None): return PLANNED
    monkeypatch.setattr(discovery, "datetime", Fixed)
    output = tmp_path / "out"
    args = ["--state", str(root / "state.json"), "--input", str(root / "input.json"),
            "--as-of", PLANNED.isoformat(), "--output", str(output)]
    return state, inputs, root, output, args


def test_cli_actual_plan_report_and_exact_copied_inputs(tmp_path, monkeypatch):
    state, inputs, root, output, args = cli_setup(tmp_path, monkeypatch)
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    assert discovery.main(args) == 0
    assert set(p.name for p in output.iterdir()) == {"index.html", "source-discovery.json", "probe-plan.json", "supplied-input.json", "saved-market-state.json", "files.json"}
    assert (output / "saved-market-state.json").read_bytes() == before["state.json"]
    assert (output / "supplied-input.json").read_bytes() == before["input.json"]
    actual = json.loads((output / "source-discovery.json").read_text())
    assert actual == run(state, inputs)
    assert json.loads((output / "probe-plan.json").read_text()) == actual["acquisition_plan"]
    assert (output / "index.html").read_text() == discovery.render_source_discovery(actual)
    receipt = json.loads((output / "files.json").read_text())
    for name, digest in receipt["files"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    assert discovery.main(args) == 2
    assert before == {p.name: p.read_bytes() for p in root.iterdir()}


def test_cli_budget_block_saves_all_leads_and_no_partial_plan(tmp_path, monkeypatch):
    state, inputs, root, output, args = cli_setup(tmp_path, monkeypatch)
    labels = [{"thscode": f"88600{i}.TI", "name": f"主题{i}"} for i in range(1, 5)]
    inputs["concept_catalog"]["response"]["data"]["item"] = labels
    inputs["sources"] = [source("、".join(x["name"] for x in labels))]
    (root / "input.json").write_text(canonical_json(inputs))
    assert discovery.main(args) == 2
    assert not (output / "probe-plan.json").exists()
    assert len(json.loads((output / "source-discovery.json").read_text())["projection"]["leads"]) == 4


def test_cli_interrupted_output_cleans_only_owned_stage(tmp_path, monkeypatch):
    _, _, root, output, args = cli_setup(tmp_path, monkeypatch)
    original = Path.write_bytes
    def broken(self, data):
        if self.name == "source-discovery.json": raise OSError("synthetic interruption")
        return original(self, data)
    monkeypatch.setattr(Path, "write_bytes", broken)
    assert discovery.main(args) == 2 and not output.exists()
    assert set(p.name for p in tmp_path.iterdir()) == {"inputs"}
    assert (root / "input.json").is_file()


@pytest.mark.parametrize("kind", ["duplicate_json_key", "symlink", "inside_inputs"])
def test_cli_refuses_unsafe_input_and_output_without_network(tmp_path, monkeypatch, kind):
    _, _, root, output, args = cli_setup(tmp_path, monkeypatch)
    if kind == "duplicate_json_key":
        text = (root / "input.json").read_text(); (root / "input.json").write_text('{"schema_version":1,' + text[1:])
    elif kind == "symlink":
        link = tmp_path / "state-link.json"; link.symlink_to(root / "state.json"); args[1] = str(link)
    else: args[-1] = str(root / "output")
    assert discovery.main(args) == 2 and not output.exists()
