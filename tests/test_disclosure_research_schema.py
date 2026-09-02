from decision_kernel.runtime.disclosure_research import DisclosureResearchAssessment


def test_disclosure_research_schema_exposes_only_research_handoff_fields() -> None:
    schema = DisclosureResearchAssessment.model_json_schema()

    assert set(schema["properties"]) == {
        "assessment_input_hash",
        "discovery",
        "pre_research",
        "quick_research",
        "supplemental_evidence_artifacts",
        "schema_version",
    }
    assert set(schema["required"]) == {
        "assessment_input_hash",
        "discovery",
        "pre_research",
    }

    forbidden_authority_fields = {
        "terminal_state",
        "assessment_disposition",
        "receipt",
        "seen",
        "human_attention",
        "attention_eligible",
        "recommendation",
        "position_size",
        "trade_action",
        "investment_authority",
    }
    assert forbidden_authority_fields.isdisjoint(schema["properties"])

    definitions = schema["$defs"]
    assert "DiscoveryInput" in definitions
    assert "PreResearchResult" in definitions
    assert "QuickResearchResult" in definitions
    assert "EvidenceArtifact" in definitions
