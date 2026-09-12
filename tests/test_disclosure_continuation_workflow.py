"""Host permission scope; no live Human input is created by this test."""
from pathlib import Path


def test_existing_host_has_read_only_issue_permission_and_explicit_continuation_switch():
    workflow=(Path(__file__).parents[1]/'.github/workflows/saved-disclosure-research.yml').read_text()
    assert '      issues: read' in workflow and 'issues: write' not in workflow
    assert 'continue-research:' in workflow and 'default: false' in workflow
    assert "github.event_name == 'workflow_dispatch' && inputs.continue-research" in workflow
    assert 'extra+=(--continuation)' in workflow
