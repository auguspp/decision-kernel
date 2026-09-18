"""Synthetic source projections; no live observation or research claims."""
from copy import deepcopy
from decimal import Decimal

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import concept_observation_map as m
from decision_kernel.runtime import concept_radar as source
from tests.test_concept_radar import Fixture, no_network


def fixture_sets(sets):
    f = Fixture(len(sets))
    def change(path, params, body):
        if path == source.probe.MEMBERS:
            body['data']['item'] = [{'thscode': f'600{i:03d}.SH', 'ticker': f'600{i:03d}',
                                    'name': f'Synthetic {i}'} for i in sets[f.codes.index(params['thscode'])]]
        return body
    f.change = change
    return f.run()


def test_nested_sets_collapse_navigation_without_losing_any_paths_or_origins():
    report = fixture_sets([{1, 2, 3}, {1, 2}, {1}]); before = deepcopy(report)
    result = m.build(report); p = result['projection']
    assert len(p['groups']) == 1 and p['groups'][0]['representative'] == '886000.TI'
    assert p['coverage']['contained_nonrepresentative_details'] == 2
    assert len(p['known_history_codes']) == 3 and len(p['universe']) == 3
    assert [r['path'] for r in p['universe']] == [r['path'] for r in report['projection']['details']]
    assert report == before and m.verify(result, report)['new_market_requests'] == 0
    assert all(r['additional_members_beyond_representative'] == 0 for r in p['groups'][0]['relations'])
    assert p['coverage']['economic_themes_established'] is False


def test_equal_members_do_not_mean_equal_indices():
    report = fixture_sets([{1, 2}, {1, 2}, {1, 2}])
    p = m.build(report)['projection']
    assert p['groups'][0]['representative'] == '886000.TI'
    assert [r['relation'] for r in p['groups'][0]['relations']] == ['REPRESENTATIVE', 'EQUAL_OBSERVED_SET', 'EQUAL_OBSERVED_SET']
    assert len({str(r['path']) for r in p['universe']}) == 3


def test_partial_overlap_chain_does_not_turn_into_one_theme():
    p = m.build(fixture_sets([{1, 2}, {2, 3}, {3, 4}]))['projection']
    assert len(p['groups']) == 3 and p['coverage']['contained_nonrepresentative_details'] == 0


def test_containment_by_two_maxima_preserves_ambiguity_not_false_partition():
    p = m.build(fixture_sets([{1, 2}, {1, 3}, {1}]))['projection']
    assert len(p['groups']) == 2
    for group in p['groups']:
        small = next(r for r in group['relations'] if r['thscode'] == '886002.TI')
        assert len(small['other_maximal_containers']) == 1
    assert p['coverage']['contained_nonrepresentative_details'] == 1


@pytest.mark.parametrize('endpoint', [source.probe.MEMBERS, source.probe.HISTORY])
def test_failed_detail_remains_incomplete_not_never_acquired_or_empty(endpoint):
    f = Fixture(4)
    f.change = lambda path, params, v: {'code': 3001} if path == endpoint and params.get('thscode') == f.codes[0] else v
    p = m.build(f.run())['projection']
    assert p['incomplete_detail_codes'] == [f.codes[0]]
    assert f.codes[0] not in p['unexamined_codes']
    if endpoint == source.probe.MEMBERS:
        assert p['unresolved_membership_details'] == [f.codes[0]]
        assert f.codes[0] in p['known_history_codes']
    else:
        assert f.codes[0] not in p['known_history_codes'] and not p['unresolved_membership_details']


def test_zero_daily_path_is_still_visible():
    f = Fixture(3); old = f.rate
    f.rate = lambda c: Decimal(0) if c == f.codes[1] else old(c)
    value = m.build(f.run())
    assert f.codes[1] in value['projection']['known_history_codes']
    assert '+0.00%' in m.render(value)


@pytest.mark.parametrize('count', [4, 5, 390, 4096])
def test_full_missing_universe_paginates_exactly_once_without_daily_ranking(count):
    # This tests the map's full projection coverage, not the provider normalizer
    # already exercised at4096 in the unchanged original source test suite.
    report = Fixture(4).run(); original = report['projection']; template = original['concepts'][-1]
    for i in range(4, count):
        row = deepcopy(template); row['thscode'] = f'{886000+i:06d}.TI'
        row['snapshot']['thscode'] = row['thscode']; row['snapshot']['ticker'] = row['thscode'][:6]
        original['concepts'].append(row)
    original['catalog_count'] = original['snapshot_count'] = count
    report['projection_hash'] = canonical_hash(original)
    value = m.build(report); p = value['projection']
    wanted = sorted(set(r['thscode'] for r in report['projection']['concepts']) - set(report['projection']['detail_selected_codes']))
    assert p['unexamined_codes'] == wanted
    seen = []
    for page in m.pages(value, expected_source_hash=report['projection_hash']):
        offset = page['offset']
        if count < 10:
            assert page == m.page(value, expected_source_hash=report['projection_hash'], offset=offset)
        else:
            assert page['codes'] == wanted[offset:offset+3]
        assert page['execution'] == 'NOT_EXECUTED' and page['workflow_compatible'] is False
        assert 0 < len(page['codes']) <= 3 and page['automatic_dispatch'] is False
        seen += page['codes']
    assert seen == wanted and len(seen) == len(set(seen))
    assert len(p['universe']) == count and any(Decimal(r['daily_return']) < 0 for r in p['universe'])
    assert p['coverage']['actual_new_pages_executed'] == 0
    assert m.page(value, expected_source_hash=report['projection_hash'], offset=len(wanted))['codes'] == []


@pytest.mark.parametrize('offset', [-1, True, '0', 1, 2, 99])
def test_bad_cursor_rejected(offset):
    report = Fixture(10).run(); value = m.build(report)
    with pytest.raises(ValueError, match='MAP_PAGE_OFFSET_REJECTED'):
        m.page(value, expected_source_hash=report['projection_hash'], offset=offset)


def test_foreign_source_page_rejected():
    value = m.build(Fixture().run())
    with pytest.raises(ValueError, match='MAP_SOURCE_SELECTOR_DIFFERS'):
        m.page(value, expected_source_hash='0'*64, offset=0)


@pytest.mark.parametrize('key', ['groups', 'unexamined_codes', 'known_history_codes', 'market_session'])
def test_rehashed_derived_tampering_rejected_by_rebuild(key):
    report = Fixture().run(); value = m.build(report)
    value['projection'][key] = [] if key != 'market_session' else '2099-01-01'
    value['projection_hash'] = canonical_hash(value['projection'])
    with pytest.raises(ValueError, match='MAP_REBUILD_DIFFERS'): m.verify(value, report)


@pytest.mark.parametrize('mutation', ['duplicate', 'count', 'selection', 'membership', 'empty'])
def test_structural_source_mismatch_not_hidden_by_new_hash(mutation):
    report = Fixture().run(); p = report['projection']
    if mutation == 'duplicate': p['concepts'][-1] = p['concepts'][0]
    elif mutation == 'count': p['catalog_count'] += 1
    elif mutation == 'selection': p['detail_selected_codes'].pop()
    elif mutation == 'membership': p['details'][0]['current_membership'] = None
    else: p['details'][0]['current_membership']['members'] = []
    report['projection_hash'] = canonical_hash(p)
    with pytest.raises(ValueError): m.build(report)


def test_labels_remain_escaped_data_and_html_has_no_active_external_content():
    f = Fixture()
    def change(path, params, body):
        if path == source.probe.CATALOG and params['tag'] == 'cn_concept':
            body['data']['item'][0]['name'] = '<script>BUY NOW</script>'
        return body
    f.change = change
    html = m.render(m.build(f.run()))
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert 'src=' not in html and 'http://' not in html and 'https://' not in html
    assert '尚未接到采集执行器' in html
    assert '不是已执行批次' in html
