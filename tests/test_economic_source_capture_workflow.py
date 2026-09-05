from __future__ import annotations

import re
from pathlib import Path


WORKFLOW = Path(".github/workflows/economic-source-capture.yml")


def _step(raw, title):
    return raw.split(f"      - name: {title}\n", 1)[1].split("      - name: ", 1)[0]


def test_public_capture_trigger_is_bounded_to_reviewed_main_changes():
    raw = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in raw
    assert "branches: [main]" in raw
    assert "schedule:" not in raw and "pull_request:" not in raw and "workflow_run:" not in raw
    paths = raw.split("    paths:\n", 1)[1].split("\n\n", 1)[0]
    assert [line.strip()[2:] for line in paths.splitlines()] == [
        ".github/workflows/economic-source-capture.yml",
        "src/decision_kernel/runtime/economic_source_capture.py",
        "src/decision_kernel/runtime/economic_node_study.py",
        "radar_inputs/economic-node-study-2026-09-05.json",
    ]
    assert '"${GITHUB_REF}" != "refs/heads/main"' in raw
    assert "timeout-minutes: 5" in raw
    assert "cancel-in-progress: false" in raw


def test_public_capture_workflow_has_no_provider_secrets_or_market_state_access():
    raw = WORKFLOW.read_text(encoding="utf-8")
    assert "persist-credentials: false" in raw and "contents: read" in raw
    assert "secrets." not in raw and "HITHINK_FINANCE_API_KEY" not in raw
    assert "decision-state/" not in raw and "actions/cache" not in raw
    assert "sector_radar_producer" not in raw and "decision-inbox" not in raw
    assert "continue-on-error" not in raw
    assert not re.search(r"\b(write|write-all)\b", raw)


def test_capture_rejection_is_not_masked_by_verification_or_artifact_publication():
    raw = WORKFLOW.read_text(encoding="utf-8")
    names = (
        "Record proof provenance", "Capture four reviewed official pages once",
        "Verify retained source archive without network", "Upload bounded public-source proof",
        "Publish source compatibility summary",
    )
    positions = [raw.index(name) for name in names]
    assert positions == sorted(positions)
    actual = _step(raw, names[1])
    assert actual.count("economic_source_capture capture") == 1
    assert "--output economic-source-proof/capture" in actual
    assert "|| true" not in raw and "exit 0" not in raw
    verify = _step(raw, names[2])
    assert "if: always()" in verify and "exit 1" in verify
    assert "economic_source_capture verify" in verify
    assert "> economic-source-proof/verification.json" in verify
    upload = _step(raw, names[3])
    assert "if: always()" in upload and "retention-days: 90" in upload
    assert "github.run_id" in upload and "github.run_attempt" in upload
    assert "path: economic-source-proof/" in upload
    assert "steps.proof.outputs.artifact-url" in _step(raw, names[4])


def test_proof_identity_is_separate_from_capture_inventory():
    raw = WORKFLOW.read_text(encoding="utf-8")
    record = _step(raw, "Record proof provenance")
    for key in ("GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "GITHUB_EVENT_NAME"):
        assert f'os.environ["{key}"]' in record
    assert 'record["provenance_hash"] = canonical_hash(record)' in record
    assert 'root / "workflow.json"' in record
    assert 'Path("economic-source-proof")' in record
    assert "PUBLIC_SOURCE_COMPATIBILITY_PROOF_NOT_CONTINUOUS_MONITORING" in record
