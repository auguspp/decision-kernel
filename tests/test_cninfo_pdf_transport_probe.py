"""Shared live identity/session guards; retired fixed-slot experiments stay historical."""
import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import textwrap

import pytest

MODULE = Path(__file__).resolve().parents[1] / 'eval' / 'cninfo_pdf_transport_probe.py'
spec = importlib.util.spec_from_file_location('pdf_probe_eval', MODULE)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('offline test attempted external networking')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


def test_native_entry_rejects_second_attempt_and_unknown_head(monkeypatch):
    env = {'GITHUB_REPOSITORY': 'auguspp/decision-kernel', 'GITHUB_REF': 'refs/heads/main',
           'GITHUB_SHA': 'a' * 40, 'EXPECTED_CODE_SHA': 'a' * 40, 'GITHUB_EVENT_NAME': 'workflow_dispatch',
           'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_RUN_ID': '123'}
    monkeypatch.setattr(p, 'version', lambda _: '2.34.2')
    assert p.native_identity(env)['GITHUB_RUN_ID'] == '123'
    for changes in ({'GITHUB_RUN_ATTEMPT': '2'}, {'EXPECTED_CODE_SHA': 'b' * 40},
                    {'GITHUB_REF': 'refs/heads/other'}, {'GITHUB_EVENT_NAME': 'push'},
                    {'GITHUB_REPOSITORY': 'other/repo'}, {'GITHUB_RUN_ID': ''}):
        with pytest.raises(ValueError): p.native_identity({**env, **changes})
    monkeypatch.setattr(p, 'version', lambda _: '2.32.5')
    with pytest.raises(ValueError, match='REQUESTS_PIN'): p.native_identity(env)


def test_existing_session_disables_env_auth_and_retries():
    with p._session() as session:
        assert session.trust_env is False
        assert len(session.cookies) == 0
        assert session.get_adapter('https://static.cninfo.com.cn/').max_retries.total == 0


def test_workflow_rejects_retired_modes_before_install_or_capture():
    path = Path(__file__).resolve().parents[1] / '.github/workflows/cninfo-announcement-source-probe.yml'
    text = path.read_text()
    guard = text.split('      - name: Require reviewed main and one fresh attempt\n', 1)[1]
    guard = guard.split('      - name: Install existing isolated transport extra', 1)[0]
    shell = textwrap.dedent(guard.split('        run: |\n', 1)[1])
    # Execute the actual guard; only checkout identity is synthetic. No CLI,
    # provider, package installation, or inherited credential is available.
    env = {'PATH': os.defpath, 'GITHUB_REF': 'refs/heads/main', 'GITHUB_RUN_ATTEMPT': '1',
           'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_SHA': 'a' * 40,
           'EXPECTED_CODE_SHA': 'a' * 40}
    for mode in ('', 'announcement', 'woton-h1-cninfo-candidate',
                 'pdf-transport', 'pdf-download-endpoint', 'exchange-pdf-source', 'unknown'):
        result = subprocess.run(['bash', '-e', '-c',
            'git() { printf "%s\\n" "$GITHUB_SHA"; }\n' + shell],
            env={**env, 'PROBE_KIND': mode}, capture_output=True, text=True, timeout=5)
        assert (result.returncode == 0) == (mode in ('', 'announcement', 'woton-h1-cninfo-candidate'))
    for retired in ('cninfo_pdf_transport_probe.py', 'cninfo_pdf_download_endpoint_probe.py',
                    'exchange_official_pdf_source_probe.py'):
        assert retired not in text
