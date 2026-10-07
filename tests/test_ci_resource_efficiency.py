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


def test_prepare_cold_install_headroom_is_bounded():
    workflow = (ROOT / '.github/workflows/ci-prepare.yml').read_text()
    prepare = workflow.split('\n  prepare:\n', 1)[1].split('\n    steps:\n', 1)[0]
    assert '\n    timeout-minutes: 15\n' in prepare
    # The longer native deadline does not replace actual installation or qualification.
    assert 'uses: ./.github/actions/ci-python' in workflow
    assert 'extras: dev' in workflow
    assert 'Record full test collection' in workflow
    assert 'Verify exact PR full-suite reuse after real installation' in workflow
    assert 'continue-on-error' not in workflow
    # #774: each shard also cold-installs; keep separate finite native limits.
    full = (ROOT / '.github/workflows/ci-full-v2.yml').read_text()
    shard = full.split('\n  shard:\n', 1)[1].split('\n    steps:\n', 1)[0]
    assert '\n    timeout-minutes: 15\n' in shard
    install = full.split('      - uses: ./.github/actions/ci-python\n', 1)[1].split('      - name:', 1)[0]
    tests = full.split('      - name: Test\n', 1)[1].split('      - name:', 1)[0]
    assert 'timeout-minutes: 10' in install and 'extras: dev' in install
    assert 'constraints:' in install
    assert 'timeout-minutes: 5' in tests and '--max-worker-restart=0' in tests
    assert 'faulthandler_timeout=60' in tests and 'set -euo pipefail' in tests
    assert 'continue-on-error' not in full and 'if: always()' in full
