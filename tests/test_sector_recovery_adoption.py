from __future__ import annotations

import runpy
from pathlib import Path

import pytest


SCRIPT = Path(".github/scripts/adopt-sector-recovery-checkpoint.py")
WORKFLOW = Path(".github/workflows/sector-radar-shadow.yml")


def module():
    return runpy.run_path(str(SCRIPT), run_name="sector_recovery_adoption_test")


def step(raw: str, name: str) -> str:
    return raw.split(f"      - name: {name}\n", 1)[1].split("      - name: ", 1)[0]


def set_identity(monkeypatch, **changes):
    values = {
        "GITHUB_REPOSITORY": "auguspp/decision-kernel",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_RUN_ID": "12345",
        "GITHUB_SHA": "a" * 40,
        "RECOVERY_OPERATION": "adopt-recovery-2026-09-10",
        "HITHINK_FINANCE_API_KEY": "",
    }
    values.update(changes)
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_adoption_adapter_is_exact_case_bound_and_has_no_market_transport_import():
    raw = SCRIPT.read_text(encoding="utf-8")
    m = module()
    assert m["OPERATION"] == "adopt-recovery-2026-09-10"
    assert m["PARENT_RUN_ID"] == 34364727989
    assert m["PARENT_ARTIFACT_ID"] == 10109790767
    assert m["CHECKPOINT_RUN_ID"] == 34593517648
    assert m["CHECKPOINT_ARTIFACT_ID"] == 10196584150
    assert m["CANDIDATE_STATE_HASH"] == "98c1f4425cf087a15a72c03af4a34ab7be43bdefea4d2467d20757b73d0ecd10"
    assert m["CANDIDATE_STATE_SHA256"] == "ff76904ee48aa8613095e91392b469989801080f5befec672225203985e391bf"
    assert "import requests" not in raw
    assert "urlopen" not in raw
    assert "hithink_http" not in raw
    assert "HITHINK_FINANCE_API_KEY" in raw
    assert "write_sector_radar_persistent_bundle" in raw
    assert "parse_sector_radar_market_state" in raw
    assert "parse_sector_radar_candidate_event_ledger" in raw


@pytest.mark.parametrize(
    "change",
    [
        {"GITHUB_REPOSITORY": "other/repo"},
        {"GITHUB_REF": "refs/heads/feature"},
        {"GITHUB_EVENT_NAME": "schedule"},
        {"GITHUB_RUN_ATTEMPT": "2"},
        {"RECOVERY_OPERATION": "produce"},
        {"HITHINK_FINANCE_API_KEY": "must-not-reach-adoption"},
        {"GITHUB_RUN_ID": "0"},
        {"GITHUB_SHA": "not-a-sha"},
    ],
)
def test_adoption_invocation_fails_closed_before_file_access(monkeypatch, change):
    set_identity(monkeypatch, **change)
    with pytest.raises(ValueError):
        module()["invocation"]()


def test_adoption_invocation_accepts_only_credential_free_fresh_main_dispatch(monkeypatch):
    set_identity(monkeypatch)
    assert module()["invocation"]() == {
        "run_id": 12345,
        "run_attempt": 1,
        "commit_sha": "a" * 40,
    }


def test_original_sector_workflow_has_one_bounded_adoption_mode_and_normal_default():
    raw = WORKFLOW.read_text(encoding="utf-8")
    assert "default: produce" in raw
    assert raw.count("adopt-recovery-2026-09-10") >= 5
    assert "artifact-ids: '10196584150'" in raw
    assert "run-id: '34593517648'" in raw
    adoption = step(raw, "Adopt exact recovery checkpoint into original Sector lineage")
    verification = step(raw, "Verify recovery adoption exact offline match")
    producer = step(raw, "Run independent Sector Radar shadow producer")
    assert "inputs.operation == 'adopt-recovery-2026-09-10'" in adoption
    assert 'HITHINK_FINANCE_API_KEY: ""' in adoption
    assert "--discovered-run-id" in adoption
    assert "--discovered-artifact-id" in adoption
    assert "--discovered-head-sha" in adoption
    assert "if: success()" in verification
    assert 'HITHINK_FINANCE_API_KEY: ""' in verification
    assert "inputs.operation == 'produce'" in producer
    assert "${{ secrets.HITHINK_FINANCE_API_KEY }}" in producer
    assert 'HITHINK_SECTOR_REQUEST_PACING: "1"' in producer
    assert "continue-on-error" not in raw


def test_adoption_is_verified_before_existing_authoritative_upload_and_cache():
    raw = WORKFLOW.read_text(encoding="utf-8")
    names = [
        "Download exact recovery checkpoint",
        "Adopt exact recovery checkpoint into original Sector lineage",
        "Verify recovery adoption exact offline match",
        "Upload complete run audit",
        "Upload authoritative state bundle",
        "Save cache acceleration copy",
    ]
    positions = [raw.index(name) for name in names]
    assert positions == sorted(positions)
    assert "if: success()" in step(raw, "Upload authoritative state bundle")
    assert "if: success()" in step(raw, "Save cache acceleration copy")
    assert "name: sector-radar-state-bundle" in step(raw, "Upload authoritative state bundle")
    assert "group: sector-radar-prospective-state" in raw
    assert "cancel-in-progress: false" in raw


def test_normal_replay_context_and_reading_are_not_used_to_fake_adoption():
    raw = WORKFLOW.read_text(encoding="utf-8")
    for name in (
        "Verify exact offline replay before publication",
        "Render read-only saved-state context",
        "Package joint economic and company reading",
    ):
        body = step(raw, name)
        assert "if: success()" in body
        assert "inputs.operation == 'produce'" in body
    summary = step(raw, "Publish separate shadow summary")
    assert "Sector production recovery adoption" in summary
    assert "later ordinary Sector production run" in summary
