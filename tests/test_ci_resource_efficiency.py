"""Resource policy checks; platform cancellation/cache hits need live evidence."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_only_same_pr_heads_share_a_cancellable_ci_group():
    text = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
    concurrency = text.split('\nconcurrency:\n', 1)[1].split('\njobs:\n', 1)[0]
    assert 'group: ${{ github.workflow }}-${{ github.event_name }}-${{ github.event.pull_request.number || github.run_id }}' in concurrency
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in concurrency
    # A constant main group with cancel=false can still displace pending runs.
    # The unique run_id fallback preserves every independent main CI identity.
    assert 'github.ref' not in concurrency
    assert text.count('\nconcurrency:\n') == 1
    assert '\n  push:\n    branches: [main]\n' in text


def test_installer_always_installs_and_does_not_reuse_an_environment_or_result():
    action = (ROOT / '.github/actions/ci-python/action.yml').read_text()
    assert 'actions/setup-python@' in action and 'astral-sh/setup-uv@' in action
    assert 'enable-cache: false' in action
    assert 'uv pip install --system --python "$pythonLocation/bin/python"' in action
    assert 'cache-hit' not in action and '.venv' not in action
    # This existing genuinely isolated pip installation remains an independent contract.
    base = (ROOT / 'tests/test_external_research_minimal_install.py').read_text()
    assert '"--no-cache-dir", "--retries", "0"' in base
    assert '"--isolated", "install"' in base
