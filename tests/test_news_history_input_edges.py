"""Optional history failure isolation at the actual capture/CLI entry points."""
import io
import json
from pathlib import Path

import pytest

from decision_kernel.runtime import news_daily as s
from test_news_daily import body, IDENTITY, TIME, IMAGE, no_network


def assert_fresh_attempt(root):
    files = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    report = json.loads(files['observations.json'])
    assert report['projection']['status'] == 'WINDOWS_CAPTURED'
    assert all('raw/newsnow-' + label + '.json' in files for label in s.SOURCES)
    assert s.rebuild(files, cutoff=TIME) == report
    assert s.HISTORY_INPUT not in files
    assert json.loads(files[s.RECOVERY_FILE])['status'] == 'RECOVERY_REJECTED'
    history = s.replay_history(files, report)['projection']
    assert history['status'] == 'ROLLING_HISTORY_LIMITED'
    assert history['coverage']['observation_count'] == 7
    assert {x['kind'] for x in history['losses']} == {'PREDECESSOR_GAP'}


@pytest.mark.parametrize('kind', ['empty', 'oversize', 'non-bytes'])
def test_optional_history_byte_failure_does_not_prevent_current_capture(tmp_path, kind):
    raw = {'empty': b'', 'oversize': b'x' * (s.MAX_HISTORY_BYTES + 1), 'non-bytes': 'not bytes'}[kind]
    calls = []
    def request(label):
        calls.append(label)
        return 200, body(label)
    root = tmp_path / 'capture'
    s.capture(root, IDENTITY, IMAGE, request=request, clock=lambda: TIME, previous_history=raw)
    assert tuple(calls) == s.SOURCES
    assert_fresh_attempt(root)


@pytest.mark.parametrize('kind', ['not-object', 'oversize'])
def test_optional_recovery_envelope_failure_does_not_prevent_current_capture(tmp_path, kind):
    receipt = [] if kind == 'not-object' else {'untrusted': 'x' * (64 * 1024 + 1)}
    root = tmp_path / 'capture'
    s.capture(root, IDENTITY, IMAGE, request=lambda label: (200, body(label)), clock=lambda: TIME,
              history_recovery=receipt)
    assert_fresh_attempt(root)
    assert b'untrusted' not in (root / s.RECOVERY_FILE).read_bytes()


@pytest.mark.parametrize('kind', ['missing-history', 'empty-history', 'oversize-history',
                                   'missing-receipt', 'empty-receipt', 'bad-json-receipt', 'oversize-receipt'])
def test_cli_optional_file_errors_are_visible_without_retry_or_source_loss(tmp_path, monkeypatch, kind):
    env = {'GITHUB_REPOSITORY': IDENTITY['repository'], 'GITHUB_REF': IDENTITY['ref'],
           'GITHUB_EVENT_NAME': IDENTITY['event'], 'GITHUB_SHA': IDENTITY['code_commit'],
           'GITHUB_RUN_ID': str(IDENTITY['run_id']), 'GITHUB_RUN_ATTEMPT': '1', 'TRIGGER_RUN_ID': ''}
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(s, 'now', lambda: TIME)
    image = tmp_path / 'image.txt'; image.write_bytes(IMAGE)
    optional = tmp_path / 'optional.json'
    if not kind.startswith('missing'):
        raw = (b'' if kind.startswith('empty') else b'not JSON' if kind == 'bad-json-receipt'
               else b'x' * ((s.MAX_HISTORY_BYTES if kind.endswith('history') else 64 * 1024) + 1))
        optional.write_bytes(raw)
    root = tmp_path / 'capture'; calls = []
    original_capture = s.capture
    def request(label):
        calls.append(label)
        return 200, body(label)
    def capture(*args, **kwargs):
        return original_capture(*args, **kwargs, request=request, clock=lambda: TIME)
    monkeypatch.setattr(s, 'capture', capture)
    flag = '--previous-history' if kind.endswith('history') else '--history-recovery'
    assert s.main(['--output', str(root), '--image-identity', str(image), flag, str(optional)]) == 0
    assert tuple(calls) == s.SOURCES
    assert_fresh_attempt(root)


def test_optional_file_read_is_bounded_before_loading_or_decoding(monkeypatch):
    sizes = []
    class Stream(io.BytesIO):
        def read(self, size=-1):
            sizes.append(size)
            return super().read(size)
    monkeypatch.setattr(Path, 'open', lambda *a, **k: Stream(b'x' * 128))
    with pytest.raises(ValueError, match='file byte budget'):
        s._bounded_history_input(Path('unused'), 16)
    assert sizes == [17]
