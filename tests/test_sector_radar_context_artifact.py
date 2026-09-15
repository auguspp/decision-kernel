from __future__ import annotations

import json
import zipfile
from datetime import timedelta
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import sector_radar_context as surface
from test_sector_radar_audit import PRODUCED, execute, prohibit_network


WORKFLOW = Path(".github/workflows/sector-radar-shadow.yml")


def _step(raw: str, name: str) -> str:
    return raw.split(f"      - name: {name}\n", 1)[1].split("      - name: ", 1)[0]


def test_context_is_rendered_after_calculation_before_remote_state_publication():
    raw = WORKFLOW.read_text(encoding="utf-8")
    names = (
        "Run independent Sector Radar shadow producer",
        "Render read-only saved-state context",
        "Upload complete run audit",
        "Upload authoritative state bundle",
        "Save cache acceleration copy",
    )
    positions = [raw.index(name) for name in names]
    assert positions == sorted(positions)
    render = _step(raw, names[1])
    assert "if: success()" in render
    assert "--bundle decision-state/sector-radar" in render
    assert "--output sector-radar-run/context" in render
    assert 'HITHINK_FINANCE_API_KEY: ""' in render
    assert "continue-on-error" not in raw
    assert "if: always()" in _step(raw, names[2])
    for name in names[3:]:
        assert "if: success()" in _step(raw, name)
    assert "path: sector-radar-run/" in _step(raw, names[2])


def test_context_summary_only_advertises_an_uploaded_successful_projection():
    raw = WORKFLOW.read_text(encoding="utf-8")
    summary = _step(raw, "Publish separate shadow summary")
    assert "steps.context-view.outcome" in summary
    assert "steps.run-audit.outputs.artifact-url" in summary
    assert '[ "$CONTEXT_OUTCOME" = "success" ] && [ -n "$RUN_AUDIT_URL" ]' in summary
    assert "context/index.html" in summary and "context/context.json" in summary
    assert "不要使用旧页面冒充本次结果" in summary
    assert 'cat sector-radar-run/summary.md >> "$GITHUB_STEP_SUMMARY"' in summary
    trigger = raw.split("on:\n", 1)[1].split("\npermissions:", 1)[0]
    assert "workflow_dispatch:" in trigger and "schedule:" not in trigger and "cron:" not in trigger


@pytest.mark.parametrize("jump", [False, True])
def test_real_calculation_bundle_can_be_projected_and_packaged_without_mutation(
    tmp_path, monkeypatch, jump,
):
    outcome, _, audit_root = execute(tmp_path / "calculation", jump=jump)
    state = audit_root / "expected/state"
    hints = audit_root / "inputs/parent-hints.json"
    before_state = {path.name: path.read_bytes() for path in state.iterdir()}
    before_audit = {str(path.relative_to(audit_root)): path.read_bytes()
                    for path in audit_root.rglob("*") if path.is_file()}

    class Clock:
        @staticmethod
        def now(tz=None):
            return PRODUCED + timedelta(minutes=1)

    monkeypatch.setattr(surface, "datetime", Clock)
    prohibit_network(monkeypatch)
    target = tmp_path / "downloadable-run/context"
    assert surface.main([
        "--bundle", str(state), "--parent-hints", str(hints),
        "--output", str(target),
    ]) == 0
    payload = json.loads((target / "context.json").read_text(encoding="utf-8"))
    assert payload["market_state_hash"] == outcome.persistent_bundle.market_state.state_hash
    assert payload["event_ledger_hash"] == outcome.persistent_bundle.event_ledger.ledger_hash
    assert payload["recorded_events_latest_session"] == (2 if jump else 0)
    assert payload["new_alerts_created"] == 0
    assert payload["context_hash"] == canonical_hash(
        {key: value for key, value in payload.items() if key != "context_hash"}
    )
    assert before_state == {path.name: path.read_bytes() for path in state.iterdir()}
    assert before_audit == {str(path.relative_to(audit_root)): path.read_bytes()
                           for path in audit_root.rglob("*") if path.is_file()}
    # This verifies local packaging, not a real GitHub upload or cache save.
    with zipfile.ZipFile(tmp_path / "run.zip", "w") as archive:
        for path in sorted(target.iterdir()):
            archive.write(path, str(path.relative_to(target.parent)))
    with zipfile.ZipFile(tmp_path / "run.zip") as archive:
        assert archive.namelist() == ["context/context.json", "context/index.html"]
        assert archive.read("context/index.html").decode("utf-8").startswith("<!doctype html>")


def test_render_failure_leaves_no_successful_view_and_does_not_modify_state(tmp_path, monkeypatch):
    _, _, audit_root = execute(tmp_path / "calculation", jump=True)
    state = audit_root / "expected/state"
    before = {path.name: path.read_bytes() for path in state.iterdir()}

    class Clock:
        @staticmethod
        def now(tz=None):
            return PRODUCED + timedelta(minutes=1)

    def fail_render(payload):
        raise RuntimeError("synthetic renderer failure")

    monkeypatch.setattr(surface, "datetime", Clock)
    monkeypatch.setattr(surface, "render_sector_radar_context_html", fail_render)
    prohibit_network(monkeypatch)
    target = tmp_path / "run/context"
    with pytest.raises(SystemExit) as error:
        surface.main([
            "--bundle", str(state), "--parent-hints", str(audit_root / "inputs/parent-hints.json"),
            "--output", str(target),
        ])
    assert error.value.code == 2
    assert not target.exists()
    assert before == {path.name: path.read_bytes() for path in state.iterdir()}
