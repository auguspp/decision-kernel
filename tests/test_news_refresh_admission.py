"""Execute the exact workflow's pre-source Python gate with local input data only."""
from pathlib import Path
import json
import os
from types import SimpleNamespace
from unittest.mock import patch
import textwrap

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/radar-newsnow-daily.yml'
M = '1' * 40


def script():
    text = WORKFLOW.read_text()
    return textwrap.dedent(text.split("          python - <<'PY'\n", 1)[1].split('\n          PY', 1)[0])


def invoke(tmp_path, changes=None, ci_changes=None):
    ci = dict(head_sha=M, head_branch='main', path='.github/workflows/ci.yml',
              event='push', run_attempt=1, status='completed', conclusion='success',
              id=1, created_at='2026-09-27T01:00:00Z')
    ci.update(ci_changes or {})
    (tmp_path / 'news-ci.json').write_text(json.dumps({'workflow_runs': [ci]}))
    env = {**os.environ, 'RUNNER_TEMP': str(tmp_path), 'GITHUB_SHA': M,
           'GITHUB_RUN_NUMBER': '8', 'GITHUB_RUN_ATTEMPT': '1',
           'GITHUB_EVENT_NAME': 'workflow_dispatch', 'SITE_REQUEST_ID': '',
           'SITE_EXPECTED_RUN_NUMBER': '', 'SITE_EXPECTED_CODE_COMMIT': ''}
    env.update(changes or {})
    # Exercise the exact same Python gate, without twenty repeated interpreters.
    # All source acquisition remains outside this extracted preflight fragment.
    with patch.dict(os.environ, env, clear=True):
        try:
            exec(compile(script(), str(WORKFLOW), 'exec'), {})
        except AssertionError as error:
            return SimpleNamespace(returncode=1, stderr=str(error))
    return SimpleNamespace(returncode=0, stderr='')


def test_native_empty_inputs_keep_original_ci_gate(tmp_path):
    assert invoke(tmp_path).returncode == 0
    for key, value in [('conclusion', 'failure'), ('run_attempt', 2),
                       ('head_sha', '2' * 40), ('event', 'workflow_dispatch')]:
        assert invoke(tmp_path, ci_changes={key: value}).returncode != 0, key


def test_unique_native_slot_admits_at_most_one_run_for_the_same_site_permit(tmp_path):
    request = {'SITE_REQUEST_ID': 'a' * 32, 'SITE_EXPECTED_RUN_NUMBER': '8',
               'SITE_EXPECTED_CODE_COMMIT': M}
    assert invoke(tmp_path, request).returncode == 0
    # A second Worker can dispatch, but its distinct native number cannot capture.
    for change in [{'GITHUB_RUN_NUMBER': '9'}, {'GITHUB_RUN_ATTEMPT': '2'},
                   {'GITHUB_SHA': '3' * 40}, {'GITHUB_EVENT_NAME': 'workflow_run'}]:
        assert invoke(tmp_path, {**request, **change}).returncode != 0, change


def test_partial_or_malformed_site_inputs_never_fall_back_to_native(tmp_path):
    good = {'SITE_REQUEST_ID': 'a' * 32, 'SITE_EXPECTED_RUN_NUMBER': '8',
            'SITE_EXPECTED_CODE_COMMIT': M}
    for field, values in [('SITE_REQUEST_ID', ['', 'x', 'a' * 32 + '\n', '${{ secrets.X }}']),
                          ('SITE_EXPECTED_RUN_NUMBER', ['', '08', '8.0', '8\n']),
                          ('SITE_EXPECTED_CODE_COMMIT', ['', 'main', M + '\n'])]:
        for value in values:
            assert invoke(tmp_path, {**good, field: value}).returncode != 0, (field, value)
    text = WORKFLOW.read_text()
    assert text.index('SITE_SLOT_CHANGED_NO_CAPTURE') < text.index('docker pull')
    assert 'contents: write' in text and 'actions: write' not in text
    assert text.index('docker rm -f newsnow') < text.index('decision_kernel.runtime.news_live_publication')
    assert "cron: '3,13,23,33,43,53 * * * *'" in text and '\n  push:' not in text
