from __future__ import annotations

import re
from pathlib import Path

from decision_kernel.runtime.sector_radar_persistence import (
    SECTOR_RADAR_STATE_ARTIFACT_NAME,
    SECTOR_RADAR_STATE_ARTIFACT_RETENTION_DAYS,
)
from decision_kernel.runtime.sector_radar_producer import (
    SECTOR_RADAR_WORKFLOW_PATH,
)


WORKFLOW = Path(SECTOR_RADAR_WORKFLOW_PATH)
OPERATIONS_DOC = Path("docs/sector-radar-prospective-producer-operations.md")


def test_sector_radar_workflow_is_manual_and_separate_from_decision_inbox() -> None:
    raw = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in raw
    assert not re.search(r"^\s*schedule:\s*$", raw, flags=re.MULTILINE)
    assert "decision-inbox" not in raw
    assert "continue-on-error" not in raw
    assert "sector-radar-prospective-state" in raw
    assert "cancel-in-progress: false" in raw
    assert "Require main branch" in raw


def test_sector_radar_workflow_restores_artifact_authority_before_running() -> None:
    raw = WORKFLOW.read_text(encoding="utf-8")

    restore_cache = raw.index("Restore cache acceleration copy")
    discover = raw.index("Discover latest successful state artifact")
    download = raw.index("Download exact latest successful state artifact")
    run = raw.index("Run independent Sector Radar shadow producer")
    assert restore_cache < discover < download < run
    assert "actions/cache/restore@v6" in raw
    assert "actions/download-artifact@v8" in raw
    assert "--prior-success-found" in raw
    assert "--artifact-available" in raw


def test_state_artifact_is_uploaded_before_cache_is_saved() -> None:
    raw = WORKFLOW.read_text(encoding="utf-8")

    audit_upload = raw.index("Upload complete run audit")
    state_upload = raw.index("Upload authoritative state bundle")
    cache_save = raw.index("Save cache acceleration copy")
    assert audit_upload < state_upload < cache_save
    assert f"name: {SECTOR_RADAR_STATE_ARTIFACT_NAME}" in raw
    assert raw.count(
        f"retention-days: {SECTOR_RADAR_STATE_ARTIFACT_RETENTION_DAYS}"
    ) == 2
    assert "if-no-files-found: error" in raw


def test_workflow_and_operations_doc_freeze_expiry_and_authority_rules() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    document = OPERATIONS_DOC.read_text(encoding="utf-8")

    assert "actions: read" in workflow
    assert "contents: read" in workflow
    assert "90 days" in document
    assert "no automatic long-term checkpoint" in document
    assert "do not trust cache alone" in document
    assert "no retrospective candidate-event append" in document
    assert "32 distinct current-membership requests" in document
    assert "ObjectiveOutcomeRecord" in document
    assert "HumanReviewAnnotation" in document
    assert "HUMAN ATTENTION AUTHORITY = NONE" in document
    assert "INVESTMENT AUTHORITY = NONE" in document
