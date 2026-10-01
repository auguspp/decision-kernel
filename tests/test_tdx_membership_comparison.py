"""The new read seam, not a source/PIT/Research acceptance test suite."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import socket
import subprocess

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import current_state as state
from decision_kernel.runtime import tdx_membership_comparison as c


@pytest.fixture(autouse=True)
def no_sources(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('comparison must not invoke a source or subprocess')
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(subprocess, 'run', denied)


def raw(value):
    return (canonical_json(value) + '\n').encode()


def reading(p, day):
    member = {'projection': p, 'projection_hash': canonical_hash(p)}
    member_raw = raw(member)
    section = {'status': 'VERIFIED_SAVED_TDX_CONCEPT_SOURCE', **c.AUTHORITY,
               'membership': {'status': 'VERIFIED_SAVED_MEMBERSHIP',
                              'catalog_count': p['catalog_count'], 'relation_count': p['relation_count'],
                              'projection_hash': member['projection_hash'],
                              'file': {'read_path': c.MEMBER_PATH,
                                       'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT',
                                       'bytes': len(member_raw), 'sha256': state.sha256(member_raw),
                                       'git_blob': state.blob_sha(member_raw)}},
               'result': {'market_session': p['market_session'], 'taxonomy': p['taxonomy'],
                          'projection_hash': p['observation_hash']}}
    t = day + 'T12:00:00+00:00'
    root = state.assemble(code_commit='a' * 40, checked_at=t, check_started_at=t,
                          lanes={}, research={'handoffs': {'active': []}, 'tdx_concept_context': section},
                          capabilities=[], refresh_identity={})
    return raw(root), member_raw, root['reading_hash']


def snapshot(day='2026-09-29', rows=None):
    if rows is None:
        rows = [{'code': '880001', 'name': 'TEST_ONLY A', 'members': ['000001.SZ', '600001.SH']},
                {'code': '880002', 'name': 'TEST_ONLY B', 'members': ['000001.SZ']}]
    p = {'version': 'tdx-concept-membership-v1', 'taxonomy': c.TAXONOMY,
         'membership_time_basis': c.TIME_BASIS, 'historical_membership': 'NOT_ESTABLISHED',
         'member_ranking': 'NOT_COMPUTED', 'business_benefit': 'NOT_ESTABLISHED', 'source_calls': 0,
         'market_session': day, 'source_prepared_date': day, 'source_observed_at': day + 'T10:00:00+00:00',
         'observation_hash': canonical_hash(['observation', day]),
         'capture_hash': canonical_hash(['capture', day]), 'parser_version': '3.2.2',
         'concepts': rows, 'catalog_count': len(rows),
         'relation_count': sum(len(x['members']) for x in rows),
         'securities': {x: {'name': None, 'in_source_catalog': True} for r in rows for x in r['members']},
         **c.AUTHORITY}
    return reading(p, day)


def compare(b, a, **kwargs):
    options = dict(before_ref='b' * 40, after_ref='c' * 40, before_hash=b[2], after_hash=a[2])
    options.update(kwargs)
    return c.build(b[0], b[1], a[0], a[1], **options)


def test_complete_relation_diff_and_catalog_absence():
    b = snapshot()
    a = snapshot('2026-09-30', [{'code': '880001', 'name': 'TEST_ONLY renamed', 'members': ['600001.SH', '000001.SH']},
                              {'code': '880003', 'name': 'TEST_ONLY new empty', 'members': []}])
    result = compare(b, a)
    assert result['coverage']['before_relations'] == 3
    assert result['coverage']['after_relations'] == 2
    assert result['coverage']['observed_added_relations'] == 1
    assert result['coverage']['observed_removed_relations'] == 2
    assert result['coverage']['present_at_both_observations'] == 1
    assert result['coverage']['catalog_added'] == ['880003']
    assert result['coverage']['catalog_removed'] == ['880002']
    assert result['changes'][0]['observed_added'] == ['000001.SH']
    assert result['changes'][0]['observed_removed'] == ['000001.SZ']
    assert result['changes'][1]['after_count'] is None
    assert result['changes'][2]['after_count'] == 0
    assert all(x['effective_change_date'] is None for x in result['changes'])
    assert result['between_observations_continuity'] == 'NOT_ESTABLISHED'
    assert result['multi_horizon_stock_roles'] == 'NOT_COMPUTED'
    assert result['report_hash'] == canonical_hash({k:v for k,v in result.items() if k != 'report_hash'})


def test_repeated_publication_is_not_a_new_observation():
    b = snapshot()
    p = json.loads(b[1])['projection']
    a = reading(p, '2026-09-30')
    assert compare(b, a)['status'] == 'SAME_SAVED_OBSERVATION'
    assert compare(b, a)['changes'] == []
    assert compare(b, b, after_ref='b' * 40)['status'] == 'SAME_SAVED_OBSERVATION'


def test_equal_endpoints_not_interval_constancy_or_effective_date():
    result = compare(snapshot(), snapshot('2026-09-30'))
    assert result['status'] == 'TWO_SAVED_OBSERVATIONS_COMPARED'
    assert result['changes'] == []
    assert result['coverage']['unchanged_observed_concepts'] == 2
    assert result['historical_effective_membership'] == result['historical_pit_knowledge'] == 'NOT_ESTABLISHED'


def test_member_order_is_not_ranking():
    b = snapshot()
    p = json.loads(snapshot('2026-09-30')[1])['projection']
    p['concepts'].reverse()
    p['concepts'][1]['members'].reverse()
    assert compare(b, reading(p, '2026-09-30'))['changes'] == []


@pytest.mark.parametrize('mutation', [
    lambda p: p.update(version='future-v2'),
    lambda p: p.update(taxonomy='OTHER_TAXONOMY'),
    lambda p: p.update(membership_time_basis='EFFECTIVE_HISTORY'),
    lambda p: p.update(historical_membership='ESTABLISHED'),
    lambda p: p.update(investment_authority='TRADE'),
    lambda p: p.update(source_calls=True),
    lambda p: p.update(catalog_count=True),
    lambda p: p.update(relation_count=4),
    lambda p: p.update(source_observed_at='2026-10-01T10:00:00+00:00'),
    lambda p: p.update(source_prepared_date='not-a-date'),
    lambda p: p['concepts'].append(deepcopy(p['concepts'][0])),
    lambda p: p['concepts'][0]['members'].append('000001.SZ'),
    lambda p: p['concepts'][0]['members'].__setitem__(0, '000001'),
    lambda p: p['securities'].update({'000002.SZ': {'name': None}}),
    lambda p: p.update(concepts=[]),
    lambda p: p.update(parser_version='different-parser'),
])
def test_rehashed_semantic_contradictions_rejected(mutation):
    b = snapshot(); p = json.loads(snapshot('2026-09-30')[1])['projection']
    mutation(p)
    a = reading(p, '2026-09-30')
    with pytest.raises(ValueError):
        compare(b, a)


def test_external_pin_wrong_ref_and_mixed_reading_rejected():
    b, a = snapshot(), snapshot('2026-09-30')
    with pytest.raises(ValueError): compare(b, a, after_hash='0' * 64)
    with pytest.raises(ValueError): compare(b, a, after_ref='main')
    with pytest.raises(ValueError): compare(b, a, after_ref='b' * 40)
    with pytest.raises(ValueError): compare(b, (a[0], b[1], a[2]))
    with pytest.raises(ValueError): compare(a, b)


def test_same_source_contradiction_rejected():
    b = snapshot(); p = json.loads(b[1])['projection']
    p['concepts'][0]['name'] = 'changed under same capture'
    with pytest.raises(ValueError): compare(b, reading(p, '2026-09-30'))


def test_tampered_bytes_duplicate_json_and_size_rejected():
    b, a = snapshot(), snapshot('2026-09-30')
    with pytest.raises(ValueError): compare(b, (a[0], a[1] + b' ', a[2]))
    with pytest.raises(ValueError): compare((b'{"x":1,"x":2}', b[1], b[2]), a)
    with pytest.raises(ValueError): compare((b' ' * (192*1024+1), b[1], b[2]), a)
    with pytest.raises(ValueError): compare(b, (a[0], b' ' * (c.MAX_MEMBER_BYTES+1), a[2]))


def test_safe_markdown_names():
    b = snapshot()
    p = json.loads(snapshot('2026-09-30')[1])['projection']
    p['concepts'][0]['name'] = '[click](https://test.invalid)|<script>\nnew'
    text = c.render(compare(b, reading(p, '2026-09-30')))
    assert '<script>' not in text and '[click]' not in text and '&#124;' in text


def test_cli_reproducible_create_only_and_inputs_unchanged(tmp_path, capsys):
    b, a = snapshot(), snapshot('2026-09-30')
    argv = []
    original = {}
    for side, value, ref in [('before', b, 'b' * 40), ('after', a, 'c' * 40)]:
        for field, content in [('reading', value[0]), ('membership', value[1])]:
            p = tmp_path / (side + '-' + field + '.json'); p.write_bytes(content)
            original[p] = content; argv += ['--'+side+'-'+field, str(p)]
        argv += ['--'+side+'-ref', ref, '--'+side+'-hash', value[2]]
    out = tmp_path / 'output'
    assert c.main(argv + ['--output', str(out)]) == 0
    expected = compare(b, a)
    assert (out / 'comparison.json').read_bytes() == raw(expected)
    assert (out / 'comparison.md').read_text() == c.render(expected)
    with pytest.raises(FileExistsError): c.main(argv + ['--output', str(out)])
    assert all(p.read_bytes() == v for p,v in original.items())
    symlink = tmp_path / 'link'; symlink.symlink_to(next(iter(original)))
    with pytest.raises(ValueError): c._read(symlink, 1024)


def test_empty_concept_survives_both_catalog_denominators():
    rows = [{'code': '880001', 'name': 'TEST_ONLY empty', 'members': []},
            {'code': '880002', 'name': 'TEST_ONLY populated', 'members': ['000001.SZ']}]
    result = compare(snapshot(rows=rows), snapshot('2026-09-30', rows))
    assert result['coverage']['union_concepts'] == result['coverage']['unchanged_observed_concepts'] == 2
    assert result['coverage']['before_relations'] == result['coverage']['after_relations'] == 1
    assert result['changes'] == []
