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


def test_cache_reuses_pip_downloads_not_an_environment_or_a_test_result():
    text = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
    setup = text.split('      - uses: actions/setup-python@', 1)[1].split('      - name: Install\n', 1)[0]
    assert '          cache: pip\n' in setup
    assert '          cache-dependency-path: pyproject.toml\n' in setup
    install = text.split('      - name: Install\n', 1)[1].split('      - name:', 1)[0]
    assert "run: python -m pip install -e '.[dev]'" in install
    assert "if: steps.scope.outputs.scope != 'content'" in install
    assert 'cache-hit' not in text  # Full runs still install even on a cache hit.
    assert 'actions/cache@' not in text and '.venv' not in text
    # The existing real isolated base-only installation stays independently cold.
    base = (ROOT / 'tests/test_external_research_minimal_install.py').read_text(encoding='utf-8')
    assert '"--no-cache-dir", "--retries", "0"' in base
    assert '"--isolated", "install"' in base
