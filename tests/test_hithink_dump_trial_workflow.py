from pathlib import Path


WORKFLOW = Path(".github/workflows/hithink-stock-dump-trial.yml")


def test_dump_trial_runs_only_reviewed_main_and_has_no_state_lane():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text and "branches: [main]" in text
    assert "test \"$GITHUB_REF\" = \"refs/heads/main\"" in text
    assert "test \"$GITHUB_RUN_ATTEMPT\" = \"1\"" in text
    assert "schedule:" not in text and "pull_request" not in text
    for forbidden in ("actions/cache", "decision-state/", "sector_radar_producer run", "decision-inbox", "contents: write", "continue-on-error", "gh workflow"):
        assert forbidden not in text
    assert "persist-credentials: false" in text
    assert "cancel-in-progress: false" in text
    assert "timeout-minutes: 12" in text
    assert "if: github.event_name == 'workflow_dispatch' && inputs.trial-purpose == 'stock-dump'" in text


def test_secret_is_only_in_acquisition_step_and_optional_libraries_are_installed():
    text = WORKFLOW.read_text(encoding="utf-8")
    stock = text.split("  inspect:\n", 1)[1].split("  stock-reading:\n", 1)[0]
    acquisition = stock.split("- name: Acquire one recent dump", 1)[1].split("- name: Repeat row inspection", 1)[0]
    assert "${{ secrets.HITHINK_FINANCE_API_KEY }}" in acquisition
    assert stock.count("${{ secrets.HITHINK_FINANCE_API_KEY }}") == 1
    theme = text.split("  theme-probe:\n", 1)[1].split("  native-feed:\n", 1)[0]
    capture = theme.split("- name: Capture bounded theme", 1)[1].split("- name: Rebuild from original", 1)[0]
    assert "${{ secrets.HITHINK_FINANCE_API_KEY }}" in capture
    assert theme.count("${{ secrets.HITHINK_FINANCE_API_KEY }}") == 1
    assert "pip install -e '.[dump-study]'" in text
    assert "python -m decision_kernel.runtime.hithink_dump_inspection" in text
    assert "retention-days: 90" in text and "if: always()" in text


def test_trial_is_not_an_unbounded_compatibility_trigger():
    text = WORKFLOW.read_text(encoding="utf-8")
    paths = text.split("    paths:\n", 1)[1].split("\n\n", 1)[0]
    assert paths.splitlines() == [
        "      - .github/scripts/capture-theme-probe.py",
        "      - radar_inputs/theme-source-sample-v0.json",
    ]
    assert "presigned_url" not in text and "curl " not in text
