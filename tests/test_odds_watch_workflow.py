from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/decision-inbox.yml"
READ_WORKFLOW = ROOT / ".github/workflows/current-state-read-entry.yml"


def text():
    return WORKFLOW.read_text(encoding="utf-8")


def test_watch_reuses_existing_inbox_schedule_secret_and_job_not_a_new_scheduler():
    value = text()
    assert 'cron: "20 8 * * 1-5"' in value
    assert value.count("schedule:") == 1
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
    assert "workflows: [sector-radar-shadow, hithink-stock-dump-trial, decision-inbox, kernel-tests, saved-disclosure-research, stock-business-research]" in value
    assert "types: [requested, completed]" in value
    assert "branches: [main]" in value
    assert "contents: write" in value and "actions: read" in value
    assert "python -m decision_kernel.runtime.current_state_delivery_with_odds_watch" in value
    assert "--code-commit \"$READ_CODE_COMMIT\"" in value
    assert "--publish" in value
    assert "workflow_dispatch:" not in value
