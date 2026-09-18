from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/decision-inbox.yml"
READ_WORKFLOW = ROOT / ".github/workflows/current-state-read-entry.yml"


def text():
    return WORKFLOW.read_text(encoding="utf-8")


def test_watch_reuses_existing_inbox_dispatch_secret_and_job_not_a_new_scheduler():
    value = text()
    trigger = value.split("on:\n", 1)[1].split("\npermissions:", 1)[0]
    assert "workflow_dispatch:" in trigger
    assert "schedule:" not in trigger and "cron:" not in trigger
    assert "HITHINK_FINANCE_API_KEY: ${{ secrets.HITHINK_FINANCE_API_KEY }}" in value
    assert "python -m decision_kernel.runtime.attention_inbox_with_odds_watch" in value
    assert "--odds-watch-config decision_inputs/odds-watch-v0.json" in value
    assert "--odds-watch-registry current_state/registry.json" in value
    assert "--odds-watch-output decision-inbox/odds-watch" in value
    assert "permissions:\n  contents: read" in value


def test_existing_inbox_delivery_step_identity_is_preserved_for_reader_qualification():
    value = text()
    assert "- name: Build Attention Inbox\n" in value
    assert "- name: Upload mobile HTML snapshot\n" in value
    assert "- name: Upload typed Odds Watch\n" in value
    assert "name: decision-inbox\n          path: decision-inbox/" in value
    assert "name: odds-watch\n          path: decision-inbox/odds-watch/" in value


def test_watch_summary_is_human_attention_only_and_missing_watch_is_not_quiet():
    value = text()
    assert "cat decision-inbox/odds-watch/summary.md" in value
    assert "No price-condition state is inferred from a missing typed Watch artifact." in value
    assert "BUY" not in value
    assert "standing order" not in value.lower()


def test_fixed_reading_reuses_original_workflow_triggers_and_only_switches_to_watch_aware_reader():
    value = READ_WORKFLOW.read_text(encoding="utf-8")
    # #427 preserves the original six sources and adds exactly the approved
    # institutional saved-source refresh. No arbitrary workflow or new clock.
    assert "workflows: [sector-radar-shadow, hithink-stock-dump-trial, decision-inbox, kernel-tests, saved-disclosure-research, stock-business-research, radar-institutional-source]" in value
    assert value.count("    workflows:") == 1
    assert "types: [requested, completed]" in value
    assert "branches: [main]" in value
    assert "contents: write" in value and "actions: read" in value
    assert "python -m decision_kernel.runtime.current_state_delivery_with_odds_watch" in value
    assert "--code-commit \"$READ_CODE_COMMIT\"" in value
    assert "--include-radar-discovery" in value
    assert "--publish" in value
    assert "workflow_dispatch:" not in value
    assert "schedule:" not in value and "cron:" not in value
    assert "secrets." not in value
