from __future__ import annotations

import json
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from test_stock_daily_successor import ROOT, WORKFLOW, environment, module, write_dispatch_jobs


def seal(value: dict, field: str) -> dict:
    value = dict(value)
    value[field] = canonical_hash(value)
    return value


def audit(tmp_path: Path, *, result: bool, status: str | None = None,
          state_update_status: str | None = None, result_hash_override=None) -> Path:
    root = tmp_path / "sector-audit"
    root.mkdir()
    if result:
        result_value = seal({"schema_version": 1, "composition": {}}, "result_hash")
        (root / "result.json").write_text(json.dumps(result_value), encoding="utf-8")
        result_hash = result_value["result_hash"] if result_hash_override is None else result_hash_override
        status = status or "APPENDED_COMPLETED_SESSION_WITH_SHADOW_CANDIDATES"
        state_update_status = state_update_status or "APPENDED_NEW_COMPLETED_SESSION"
        candidate_count = 1
    else:
        result_hash = result_hash_override
        status = status or "VALIDATED_ALREADY_CURRENT_NO_PROSPECTIVE_EVENT"
        state_update_status = state_update_status or "ALREADY_CURRENT_IDEMPOTENT"
        candidate_count = 0
    operations = seal({
        "schema_version": 1,
        "repository": "auguspp/decision-kernel",
        "workflow_path": ".github/workflows/sector-radar-shadow.yml",
        "run_id": 499,
        "run_attempt": 1,
        "commit_sha": "a" * 40,
        "status": status,
        "state_update_status": state_update_status,
        "result_hash": result_hash,
        "candidate_count": candidate_count,
    }, "operations_hash")
    (root / "operations.json").write_text(json.dumps(operations), encoding="utf-8")
    return root


def test_exact_result_bearing_sector_run_is_stock_ready(tmp_path):
    mod = module()
    root = audit(tmp_path, result=True)
    assert mod["validate_stock_input"](str(root), environment()) is True


def test_exact_already_current_sector_run_is_successful_noop(tmp_path):
    mod = module()
    root = audit(tmp_path, result=False)
    assert mod["validate_stock_input"](str(root), environment()) is False


@pytest.mark.parametrize("problem", [
    "missing-result-wrong-status",
    "missing-result-hash",
    "result-status",
    "result-update",
    "result-hash-disagreement",
    "result-seal-tamper",
    "wrong-run",
    "wrong-commit",
])
def test_missing_malformed_or_wrong_exact_sector_result_fails_closed(tmp_path, problem):
    mod = module()
    if problem == "missing-result-wrong-status":
        root = audit(tmp_path, result=False, status="APPENDED_COMPLETED_SESSION_QUIET",
                     state_update_status="APPENDED_NEW_COMPLETED_SESSION")
    elif problem == "missing-result-hash":
        root = audit(tmp_path, result=False, result_hash_override="b" * 64)
    elif problem == "result-status":
        root = audit(tmp_path, result=True, status="VALIDATED_ALREADY_CURRENT_NO_PROSPECTIVE_EVENT")
    elif problem == "result-update":
        root = audit(tmp_path, result=True, state_update_status="ALREADY_CURRENT_IDEMPOTENT")
    elif problem == "result-hash-disagreement":
        root = audit(tmp_path, result=True, result_hash_override="b" * 64)
    else:
        root = audit(tmp_path, result=True)
        if problem == "result-seal-tamper":
            value = json.loads((root / "result.json").read_text())
            value["composition"]["tampered"] = True
            (root / "result.json").write_text(json.dumps(value), encoding="utf-8")
        else:
            value = json.loads((root / "operations.json").read_text())
            value["run_id" if problem == "wrong-run" else "commit_sha"] = (
                498 if problem == "wrong-run" else "b" * 40
            )
            value.pop("operations_hash")
            value = seal(value, "operations_hash")
            (root / "operations.json").write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(mod["SuccessorCheckError"]):
        mod["validate_stock_input"](str(root), environment())


def test_workflow_downloads_only_exact_upstream_audit_before_pat_dispatch():
    raw = WORKFLOW.read_text(encoding="utf-8")
    gate = raw.split("- name: Require exact result-bearing Sector input for Stock", 1)[1].split(
        "- name: Dispatch existing bounded Stock reading once", 1
    )[0]
    dispatch = raw.split("- name: Dispatch existing bounded Stock reading once", 1)[1]
    assert 'gh run download "$UPSTREAM_RUN_ID"' in gate
    assert '--name "sector-radar-run-$UPSTREAM_RUN_ID"' in gate
    assert '--dir "$UPSTREAM_RUN_AUDIT"' in gate
    assert "SUCCESSOR_CHECK_MODE: stock-input" in gate
    assert "GH_TOKEN: ${{ github.token }}" in gate
    assert "DAILY_CHAIN_DISPATCH_TOKEN" not in gate
    assert "latest" not in gate.lower() and "/rerun" not in gate
    assert "steps.stock-input.outputs.stock_input_ready == 'true'" in dispatch
    assert "GH_TOKEN: ${{ secrets.DAILY_CHAIN_DISPATCH_TOKEN }}" in dispatch
    assert raw.index("Require exact result-bearing Sector input for Stock") < raw.index(
        "Dispatch existing bounded Stock reading once"
    )


def test_result_gate_revalidates_dispatched_produce_identity(tmp_path):
    mod = module()
    jobs = write_dispatch_jobs(tmp_path / "jobs.json", "produce")
    env = environment(UPSTREAM_EVENT="workflow_dispatch", UPSTREAM_JOBS_JSON=str(jobs))
    root = audit(tmp_path, result=True)
    assert mod["validate_successor"](env) == (499, "WORKFLOW_DISPATCH_PRODUCE")
    assert mod["validate_stock_input"](str(root), env) is True


def test_result_gate_does_not_add_market_or_research_authority():
    helper = (ROOT / ".github/scripts/check-stock-daily-successor.py").read_text(encoding="utf-8")
    assert "HITHINK_FINANCE_API_KEY" not in helper
    assert "stock-business-research.yml" not in helper
    assert "/dispatches" not in helper
    assert "sleep(" not in helper and "while " not in helper
