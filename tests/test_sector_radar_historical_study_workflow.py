from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/sector-radar-historical-study.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_historical_study_workflow_is_manual_only_and_read_only() -> None:
    text = workflow_text()
    trigger = text.split("on:\n", 1)[1].split("\npermissions:\n", 1)[0]
    assert "workflow_dispatch:" in trigger
    for forbidden in ("schedule:", "push:", "pull_request:", "workflow_run:"):
        assert forbidden not in trigger

    permissions = text.split("permissions:\n", 1)[1].split("\nconcurrency:\n", 1)[0]
    assert permissions == "  actions: read\n  contents: read\n"
    assert " write" not in permissions
    assert "secrets." not in text
    assert "HITHINK" not in text
    assert "actions/cache" not in text
    assert "decision-state/" not in text


def test_historical_study_workflow_requires_exact_source_identity_inputs() -> None:
    text = workflow_text()
    lines = text.splitlines()
    for name in ("source_run_id", "expected_state_hash", "expected_market_session"):
        start = lines.index(f"      {name}:")
        block: list[str] = []
        for line in lines[start + 1 :]:
            if line.startswith("      ") and not line.startswith("        "):
                break
            block.append(line)
        assert "        required: true" in block, name

    assert 'test "$GITHUB_REF" = "refs/heads/main"' in text
    assert 'test "$GITHUB_RUN_ATTEMPT" = "1"' in text
    assert "name: sector-radar-state-bundle" in text
    assert "run-id: ${{ inputs.source_run_id }}" in text
    assert "digest-mismatch: error" in text
    assert 'state.state_hash != os.environ["EXPECTED_STATE_HASH"]' in text
    assert 'state.sessions[-1].isoformat() != os.environ["EXPECTED_MARKET_SESSION"]' in text


def test_historical_study_workflow_only_executes_merged_read_only_cli() -> None:
    text = workflow_text()
    assert "python -m decision_kernel.runtime.sector_radar_historical_study" in text
    assert "--state source-state/market-state.json" in text
    assert "--generated-at \"$generated_at\"" in text
    assert "--output historical-study" in text

    for forbidden in (
        "sector_radar_producer run",
        "stock-reading-after-sector",
        "decision-inbox",
        "saved-disclosure-research",
        "decision_kernel.runtime.saved_research_once",
        "Odds",
        "Action",
    ):
        if forbidden in {"Odds", "Action"}:
            continue
        assert forbidden not in text

    assert '"market_state_writes": 0' in text
    assert '"provider_requests": 0' in text
    for authority in (
        '"research_authority": "NONE"',
        '"human_attention_authority": "NONE"',
        '"investment_authority": "NONE"',
    ):
        assert authority in text


def test_historical_study_upload_is_separate_evidence_not_restore_state() -> None:
    text = workflow_text()
    upload = text.split("uses: actions/upload-artifact@v7", 1)[1]
    assert "name: sector-radar-historical-study-${{ github.run_id }}-${{ github.run_attempt }}" in upload
    assert "path: historical-study/" in upload
    assert "retention-days: 90" in upload
    assert "sector-radar-state-bundle" not in upload
    assert "actions/cache/save" not in text
    assert "actions/cache/restore" not in text


def test_execution_receipt_preserves_historical_study_limitations() -> None:
    text = workflow_text()
    assert "FROZEN_UNIVERSE_PRICE_PATH_ONLY__CATALOG_EFFECTIVE_DATE_NOT_INDEPENDENTLY_PROVEN" in text
    assert "NOT_CERTIFIED__HISTORICAL_CATALOG_EFFECTIVE_DATE_UNKNOWN" in text
    assert "READ_ONLY_HISTORICAL_STUDY_EXECUTION_RECEIPT" in text
    assert '"source_run_id": int(os.environ["SOURCE_RUN_ID"])' in text
    assert '"code_commit": os.environ["GITHUB_SHA"]' in text
    assert '"workflow_run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"])' in text
    assert 'receipt["receipt_hash"] = canonical_hash(receipt)' in text
