"""Real installed eltdx file parser, synthetic retained input, no live markets."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import socket

import pytest

from decision_kernel.runtime import tdx_concept_membership as m, tdx_concept_snapshot as tdx
from test_tdx_concept_snapshot import DAY, WF, SHA, source


def saved(tmp_path, damage=None):
    root = tmp_path / 'capture'
    def capture_files(out, target):
        d = out / 'source-files'; d.mkdir()
        text = '#GN_Concept A,2,880001\n1#600001,0#000001\n#GN_Concept B,1,880002\n0#000001\n'
        securities = [{'market': 1, 'code': '600001', 'name': 'TEST <script>'},
                      {'market': 0, 'code': '000001', 'name': 'TEST B'}]
        cache = {'last_success_date': DAY.isoformat(), 'downloaded_at': '2026-09-25T04:00:00Z'}
        if damage == 'taxonomy-collision': text += '#FG_Other,2,880001\n1#600001,0#000001\n'
        if damage == 'count': text = text.replace('Concept A,2', 'Concept A,3')
        if damage == 'catalog': text = text.replace('Concept B,1,880002', 'Different,1,880002')
        if damage == 'missing-security': securities.pop()
        if damage == 'duplicate-security': securities.append(deepcopy(securities[0]))
        if damage == 'market': securities[0]['market'] = True
        if damage == 'date': cache['last_success_date'] = '2026-09-23'
        if damage == 'clock': cache['downloaded_at'] = '2026-09-26T04:00:00Z'
        raw = text.encode('gb18030')
        (d / 'infoharbor_block.dat').write_bytes(raw)
        (d / 'security_list.json').write_text(json.dumps(securities))
        (d / 'tdxhy.cfg').write_text('TEST unused industry file')
        cache['sha256'] = {'infoharbor_block.dat': sha256(raw).hexdigest()}
        (d / '.eltdx_board_cache.json').write_text(json.dumps(cache))
        return source()
    ticks = iter([datetime(2026, 9, 25, 4, 0, i, tzinfo=timezone.utc) for i in (0, 1)])
    receipt = tdx.capture(root, market_session=DAY, workflow=WF, expected_code=SHA,
                          source_fn=capture_files, now=lambda: next(ticks))
    return root, tdx.replay(root), receipt


@pytest.fixture(autouse=True)
def no_live_source(monkeypatch):
    from eltdx.helpers.boards import BoardService
    def reject(*a, **k): raise AssertionError('no source acquisition in member reading')
    monkeypatch.setattr(socket.socket, 'connect', reject)
    monkeypatch.setattr(socket, 'create_connection', reject)
    monkeypatch.setattr(BoardService, '_prepare', reject)
    monkeypatch.setattr(BoardService, '_snapshot_batches', reject)


def test_complete_members_use_installed_parser_without_rewriting_old_capture(tmp_path):
    root, observation, receipt = saved(tmp_path)
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    report = m.build(root, observation, receipt); p = report['projection']
    assert p['catalog_count'] == 2 and p['relation_count'] == 3
    assert p['concepts'][0]['members'] == ['600001.SH', '000001.SZ']
    assert p['securities']['600001.SH']['name'] == 'TEST <script>'
    assert p['historical_membership'] == p['business_benefit'] == 'NOT_ESTABLISHED'
    assert p['member_ranking'] == 'NOT_COMPUTED' and p['source_calls'] == 0
    assert json.loads(m.encoded(report)) == report
    assert before == {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    assert tdx.replay(root) == observation


@pytest.mark.parametrize('damage', ['count', 'catalog', 'duplicate-security', 'market', 'date', 'clock', 'taxonomy-collision'])
def test_membership_rejection_does_not_reinterpret_valid_old_short_history(tmp_path, damage):
    root, observation, receipt = saved(tmp_path, damage)
    with pytest.raises(ValueError): m.build(root, observation, receipt)
    assert tdx.replay(root) == observation


def test_raw_member_absent_from_security_catalog_stays_visible(tmp_path):
    root, observation, receipt = saved(tmp_path, 'missing-security')
    p = m.build(root, observation, receipt)['projection']
    assert p['relation_count'] == 3
    assert p['securities']['000001.SZ'] == {'name': None, 'in_source_catalog': False}


def test_source_byte_damage_parser_version_and_consumer_bound_reject(tmp_path, monkeypatch):
    root, observation, receipt = saved(tmp_path)
    monkeypatch.setattr(m, 'MAX_READING_BYTES', 10)
    with pytest.raises(ValueError, match='READING_SIZE'): m.build(root, observation, receipt)
    monkeypatch.setattr(m, 'MAX_READING_BYTES', 1024 * 1024)
    monkeypatch.setattr(m, 'version', lambda _: 'different')
    with pytest.raises(ValueError, match='PARSER_VERSION'): m.build(root, observation, receipt)
    monkeypatch.setattr(m, 'version', lambda _: '3.2.2')
    path = root / 'source-files/infoharbor_block.dat'; path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError, match='FILE_IDENTITY'): m.build(root, observation, receipt)


def test_publisher_retains_same_source_and_isolates_member_failure(tmp_path):
    from test_tdx_concept_reading import setup
    from decision_kernel.runtime import tdx_concept_reading as reading
    root, _, _ = saved(tmp_path)
    files = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    col, base, _, _ = setup(tmp_path, files=files)
    result = reading.attach(col, base); section = result['research']['tdx_concept_context']
    assert section['status'] == 'VERIFIED_SAVED_TDX_CONCEPT_SOURCE'
    assert section['membership']['status'] == 'VERIFIED_SAVED_MEMBERSHIP'
    d = section['membership']['file']
    assert sha256(col.files[d['read_path']]).hexdigest() == d['sha256']
    assert result['lanes'] == base['lanes']
    # The legacy synthetic fixture has no usable membership text: old quotes remain valid.
    other = tmp_path / 'legacy'; other.mkdir()
    col, base, _, _ = setup(other)
    section = reading.attach(col, base)['research']['tdx_concept_context']
    assert section['status'] == 'VERIFIED_SAVED_TDX_CONCEPT_SOURCE'
    assert section['membership']['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert 'file' not in section['membership']
