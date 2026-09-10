"""Decimal-boundary regression for failed run 34448843822; no live market calls.

The small ZIP is synthetic. Only bundle/context validation and state parsing are
stubbed to isolate snapshot decoding; run, ZIP and response-digest checks run.
The original failed archive is replayed separately, not fabricated by this test.
"""
import io
import json
import sys
import zipfile
from datetime import date
from types import SimpleNamespace

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.primitives import DomainValidationError
from decision_kernel.runtime import sector_member_reading as m


@pytest.fixture
def saved_source(tmp_path, monkeypatch):
    members = [{'thscode': '600598.SH', 'name': '北大荒'},
               {'thscode': '601952.SH', 'name': '苏垦农发'}]
    # Deliberately unquoted decimals, trailing zeros, and scientific notation.
    # These are synthetic encoding cases, not qualified stock histories.
    response = (b'{"code":0,"data":{"timestamp":null,"item":['
                b'{"thscode":"600598.SH","ticker":"600598","last_price":13.920000,'
                b'"volume":123,"extra_decimal":1.234567890123456789e-7},'
                b'{"thscode":"601952.SH","ticker":"601952","last_price":10.2800,'
                b'"volume":456,"already_string":"001.2500"}]}}')
    files = {f'input-audit/expected/state/{n}': b'{}' for n in
             ('market-state.json', 'candidate-events.json', 'manifest.json')}
    files['result.json'] = json.dumps({'market_session': '2026-09-09',
        'breadth_observations': [{'sector_thscode': '884002.TI',
            'constituent_set_hash': 'b' * 64, 'member_count': 2,
            'priced_member_count': 2, 'missing_or_unpriced_member_count': 0,
            'leaders': members}]}).encode()
    files['input-audit/responses/0001.json'] = response
    files['input-audit/manifest.json'] = json.dumps({
        'files': {'responses/0001.json': {'sha256': m.saved.sha256(response), 'bytes': len(response)}},
        'requests': [{'path': m.own.SNAPSHOT, 'error_type': None,
            'response_file': 'responses/0001.json',
            'captured_at': '2026-09-09T14:45:00+00:00'}]}).encode()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    raw = stream.getvalue()
    run = {'id': 1, 'repository': {'full_name': m.saved.REPOSITORY},
        'head_repository': {'full_name': m.saved.REPOSITORY},
        'head_sha': 'a' * 40, 'head_branch': 'main', 'event': 'schedule',
        'path': m.saved.WORKFLOWS['sector'], 'run_attempt': 1,
        'status': 'completed', 'conclusion': 'success'}
    artifact = {'id': 2, 'digest': 'sha256:' + m.saved.sha256(raw),
        'expired': False, 'size_in_bytes': len(raw),
        'workflow_run': {'id': 1, 'head_sha': run['head_sha']}}
    request = {'version': m.VERSION, 'max_requests': 4, 'windows': [5, 20, 60],
        'members': members, 'market_session': '2026-09-09', 'sector': '884002.TI',
        'benchmark': '000300.SH', 'constituent_set_hash': 'b' * 64,
        'price_convention': 'RAW_WITH_REPORTED_ACTION_WINDOW_EXCLUSIONS',
        'automatic_research': False, 'source': {'run_id': 1, 'artifact_id': 2,
            'head_sha': run['head_sha'], 'digest': artifact['digest']}}
    for name, value in [('request.json', request), ('source-run.json', run),
                        ('source-artifact.json', artifact)]:
        (tmp_path / name).write_text(json.dumps(value), encoding='utf-8')
    (tmp_path / 'source.zip').write_bytes(raw)
    monkeypatch.setattr(m.saved, 'validate_sector', lambda *a: None)
    monkeypatch.setattr(m, 'parse_sector_radar_market_state',
        lambda _: SimpleNamespace(sessions=(date(2026, 9, 9),)))
    return tmp_path, raw, response


def test_prepare_cli_preserves_stored_decimal_lexemes(saved_source, monkeypatch):
    root, original_zip, response = saved_source
    monkeypatch.setattr(sys, 'argv', ['sector_member_reading', 'prepare', '--root', str(root)])
    m.main()
    quotes = m.read(root / 'derived-quotes.json')
    a = quotes['600598.SH']['quote']['data']['item'][0]
    b = quotes['601952.SH']['quote']['data']['item'][0]
    assert a['last_price'] == '13.920000'
    assert a['extra_decimal'] == '1.234567890123456789e-7'
    assert b['last_price'] == '10.2800' and b['already_string'] == '001.2500'
    assert type(a['volume']) is int and type(b['volume']) is int
    assert quotes['600598.SH']['quote']['code'] == 0
    assert quotes['600598.SH']['quote']['data']['timestamp'] is None
    assert all(q['source_sha256'] == m.saved.sha256(response) for q in quotes.values())
    assert (root / 'source.zip').read_bytes() == original_zip
    assert canonical_hash(quotes)
    assert m.read(root / 'source-check.json')['status'] == 'SOURCE_BOUND'
    assert not (root / 'capture').exists()  # No transport or market acquisition.


@pytest.mark.parametrize('value', [1.25, float('nan'), float('inf'), float('-inf')])
def test_domain_float_guard_stays_strict_and_leaves_no_empty_file(tmp_path, value):
    target = tmp_path / 'derived-quotes.json'
    with pytest.raises(DomainValidationError, match='binary float'):
        m.write(target, {'nested': [{'price': value}]})
    assert not target.exists()


def test_canonical_writer_remains_create_only(tmp_path):
    target = tmp_path / 'result.json'
    m.write(target, {'price': '1.25'})
    original = target.read_bytes()
    with pytest.raises(FileExistsError):
        m.write(target, {'price': '2.50'})
    assert target.read_bytes() == original
