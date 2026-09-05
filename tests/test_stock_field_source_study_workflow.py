from pathlib import Path


WORKFLOW = Path('.github/workflows/stock-field-source-study.yml')


def test_source_study_is_explicit_bounded_and_read_only():
    text = WORKFLOW.read_text(encoding='utf-8')
    assert 'workflow_dispatch:' in text
    assert 'branches: [main]' in text
    assert 'schedule:' not in text
    assert 'pull_request' not in text
    assert 'contents: read' in text and 'actions: read' in text
    assert 'contents: write' not in text
    assert 'actions/cache' not in text
    assert 'decision-state' not in text
    assert 'continue-on-error' not in text
    assert 'test "$GITHUB_RUN_ATTEMPT" = "1"' in text
    assert 'timeout-minutes: 12' in text


def test_source_study_restores_fixed_artifact_and_never_redownloads_market():
    text = WORKFLOW.read_text(encoding='utf-8')
    assert 'actions/download-artifact@v8' in text
    assert 'name: hithink-stock-dump-trial-33959190974-1' in text
    assert 'run-id: 33959190974' in text
    assert 'source_artifact_id=9967375391' in text
    assert 'python -m decision_kernel.runtime.hithink_dump_trial' not in text
    assert 'daily-k-10d/download-url' not in text
    assert 'retention-days: 90' in text


def test_public_profile_has_no_provider_credential_and_offline_check_always_runs():
    text = WORKFLOW.read_text(encoding='utf-8')
    assert 'secrets.' not in text and 'HITHINK_FINANCE_API_KEY' not in text
    source = text.split('- name: Collect targeted public')[1].split('- name: Verify retained')[0]
    assert '--profile coverage-notices' in source
    verify = text.split('- name: Verify retained')[1].split('- name: Retain complete')[0]
    assert 'if: always()' in verify
    assert 'build_plan(source, profile="coverage-notices") == plan' in verify
    assert 'plan["provider_requests"] == []' in verify
    assert 'hashlib.sha256(raw).hexdigest() == item["sha256"]' in verify
    assert 'production_qualification' in verify
