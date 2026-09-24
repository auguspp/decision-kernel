"""Same-root retained primary/supplement maps; synthetic acquisition only."""
from copy import deepcopy
import json
import zipfile

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import concept_observation_map as view
from decision_kernel.runtime import concept_observation_map_delivery as delivery
from decision_kernel.runtime import concept_radar as source
from decision_kernel.runtime import current_state as model
from tests.test_concept_detail_supplement import execute
from tests.test_concept_observation_map_delivery import prepared
from tests.test_concept_radar import no_network


def pair(tmp_path, **kwargs):
    out, _, _, inputs, _ = execute(tmp_path, **kwargs)
    with zipfile.ZipFile(inputs / 'base.zip') as archive:
        primary = json.loads(archive.read('payload/observation.json'))
    return primary, json.loads((out / 'observation.json').read_bytes())


def test_combines_only_actual_details_and_keeps_original_clocks_and_bytes(tmp_path):
    primary, supplement = pair(tmp_path)
    before = deepcopy((primary, supplement))
    old = view.build(primary)
    value = view.build(primary, supplement=supplement); p = value['projection']
    assert (primary, supplement) == before and old == view.build(primary)
    assert p['version'] == view.SUPPLEMENT_VERSION
    assert p['coverage']['history_count'] == p['coverage']['membership_count'] == 6
    assert p['coverage']['unexamined_details'] == 4
    assert p['coverage']['cumulative_all_batches'] is False
    assert p['coverage']['actual_new_pages_executed'] == 0
    assert not p['coverage']['full_multiday_coverage'] and not p['automatic_dispatch']
    expected = set(primary['projection']['detail_selected_codes']) | {
        d['thscode'] for d in supplement['projection']['details']}
    assert set(p['known_history_codes']) == expected
    assert set(p['unexamined_codes']).isdisjoint(expected)
    assert p['source_observed_at'] == primary['projection']['as_of']
    assert p['supplement']['observed_at'] == supplement['projection']['as_of']
    rows = {r['thscode']: r for r in p['universe']}
    for d in supplement['projection']['details']:
        assert rows[d['thscode']]['path'] == d['path']
        assert rows[d['thscode']]['detail_source']['kind'] == 'SUPPLEMENT'
        for group in p['groups']:
            for relation in group['relations']:
                if relation['thscode'] == d['thscode']:
                    req = supplement['projection']['requests'][d['membership_request_index']]
                    assert relation['membership_observed_at'] == req['received_at']
    assert view.verify(value, primary, supplement=supplement)['new_market_requests'] == 0
    assert value == view.build(primary, supplement=supplement)  # Repeat read is not another batch.
    assert '不是全部批次' in view.render(value)
    pages = list(view.pages(value, expected_source_hash=primary['projection_hash']))
    assert [c for page in pages for c in page['codes']] == p['unexamined_codes']
    assert all(page['version'] == view.SUPPLEMENT_VERSION and not page['workflow_compatible'] for page in pages)
    with pytest.raises(ValueError, match='MAP_REBUILD_DIFFERS'):
        view.verify(value, primary)  # A primary alone cannot reproduce the merged result.


@pytest.mark.parametrize('kind', ['history', 'membership'])
def test_partial_detail_does_not_become_unexamined_or_zero_activity(tmp_path, kind):
    endpoint = source.probe.HISTORY if kind == 'history' else source.probe.MEMBERS
    primary, supplement = pair(tmp_path, mutation=lambda p, q, v: {'code': 3001} if p == endpoint else v)
    p = view.build(primary, supplement=supplement)['projection']
    codes = {d['thscode'] for d in supplement['projection']['details']}
    assert set(p['incomplete_detail_codes']) == codes
    assert set(p['unexamined_codes']).isdisjoint(codes)
    assert p['coverage']['history_count'] == (3 if kind == 'history' else 6)
    assert p['coverage']['membership_count'] == (6 if kind == 'history' else 3)


def test_later_offset_does_not_claim_earlier_offsets_were_acquired(tmp_path):
    primary, supplement = pair(tmp_path, offset=6)
    p = view.build(primary, supplement=supplement)['projection']
    assert p['coverage']['history_count'] == 4
    assert len(p['unexamined_codes']) == 6 and len(p['supplement']['detail_codes']) == 1


@pytest.mark.parametrize('field', ['root', 'day', 'base_clock', 'clock', 'policy', 'authority',
    'duplicate', 'primary_overlap', 'plan', 'name', 'request_code', 'request_index',
    'request_clock', 'path_status', 'window', 'empty_members'])
def test_rehashed_wrong_lineage_or_detail_is_rejected(tmp_path, field):
    primary, supplement = pair(tmp_path); p = supplement['projection']; d = p['details'][0]
    if field == 'root': p['base_projection_hash'] = '0' * 64
    elif field == 'day': p['market_session'] = '2026-09-17'
    elif field == 'base_clock': p['base_observed_at'] = p['started_at']
    elif field == 'clock': p['as_of'] = '2026-09-19T10:00:00+08:00'
    elif field == 'policy': p['policy']['next_batch'] = 'AUTOMATIC'
    elif field == 'authority': p['model_calls'] = 1
    elif field == 'duplicate': p['details'][1] = deepcopy(d)
    elif field == 'primary_overlap': d['thscode'] = primary['projection']['detail_selected_codes'][0]
    elif field == 'plan': p['plan_hash'] = '0' * 64
    elif field == 'name': d['name'] = 'different concept'
    elif field == 'request_code': p['requests'][0]['params']['thscode'] = '886999.TI'
    elif field == 'request_index': d['history_request_index'] = True
    elif field == 'request_clock': p['requests'][0]['received_at'] = '2026-09-19T10:00:00+08:00'
    elif field == 'path_status': d['path'] = None
    elif field == 'window': d['path']['history_window_end'] = '2026-09-17'
    else: d['current_membership']['members'] = []
    supplement['projection_hash'] = canonical_hash(p)
    with pytest.raises(ValueError): view.build(primary, supplement=supplement)


def with_supplement(tmp_path):
    col, baseline, _ = prepared(tmp_path)
    folder = tmp_path / 'pair'; folder.mkdir()
    primary, supplement = pair(folder)
    statuses = baseline['research']['radar_discovery']['source_status']
    for name, report, status in [('concept', primary, 'VERIFIED_SAVED_CONCEPT_SOURCE'),
                                ('concept_detail', supplement, 'VERIFIED_SAVED_CONCEPT_DETAIL')]:
        p = report['projection']
        ref = col.retain(f'details/{name}/new/observation.json', model.json_bytes(report))
        statuses[name] = {'status': status, 'details': {'observation.json': ref},
            'projection_hash': report['projection_hash'], 'market_session': p['market_session'],
            'source_observed_at': p['as_of']}
    statuses['concept_detail']['base_projection_hash'] = primary['projection_hash']
    col.now = lambda: '2026-09-18T10:00:00+00:00'
    baseline = model.assemble(code_commit=baseline['code_commit'], checked_at=col.now(),
        check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'],
        research=baseline['research'], capabilities=[], refresh_identity={})
    return col, baseline, primary, supplement


def test_real_collector_reuses_already_retained_supplement_without_new_requests(tmp_path):
    col, baseline, primary, supplement = with_supplement(tmp_path); before = dict(col.files)
    result = delivery.attach(col, baseline); model.validate_read_package(result)
    value = result['research']['radar_discovery']['concept_observation_map']
    assert value['status'] == 'READ_OK' and value['coverage']['history_count'] == 6
    assert value['supplement_source'] == baseline['research']['radar_discovery']['source_status']['concept_detail']['details']['observation.json']
    assert col.api.calls == 0 and not col.api.reads
    for path, raw in before.items():
        if path not in {'README.md', 'current-state.json'}: assert col.files[path] == raw
    saved = json.loads(col.files[delivery.PREFIX + 'json'])
    view.verify(saved, primary, supplement=supplement)


@pytest.mark.parametrize('failure', ['reference', 'digest', 'root', 'time', 'missing_body'])
def test_bad_verified_supplement_keeps_source_and_company_bytes_with_visible_map_gap(tmp_path, failure):
    col, b, _, _ = with_supplement(tmp_path)
    status = b['research']['radar_discovery']['source_status']['concept_detail']
    if failure == 'reference': status['details']['observation.json']['read_ref_rule'] = 'LATEST_REF'
    elif failure == 'digest': status['projection_hash'] = '0' * 64
    elif failure == 'root': status['base_projection_hash'] = '0' * 64
    elif failure == 'time': status['source_observed_at'] = '2099-01-01T00:00:00+08:00'
    else: del col.files[status['details']['observation.json']['read_path']]
    b['reading_hash'] = canonical_hash({k: v for k, v in b.items() if k != 'reading_hash'})
    before = dict(col.files); result = delivery.attach(col, b)
    assert result['research']['radar_discovery']['concept_observation_map']['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert result['research']['radar_discovery']['source_status'] == b['research']['radar_discovery']['source_status']
    assert col.api.calls == 0 and not any(p.startswith(delivery.PREFIX) for p in col.files)
    for path, raw in before.items():
        if path not in {'README.md', 'current-state.json'}: assert col.files[path] == raw


def test_failed_latest_supplement_not_read_or_hidden_by_primary_success(tmp_path):
    col, b, _, _ = with_supplement(tmp_path)
    status = b['research']['radar_discovery']['source_status']['concept_detail']
    status['status'] = 'LATEST_ATTEMPT_NOT_SUCCESSFUL'
    del col.files[status['details']['observation.json']['read_path']]
    b['reading_hash'] = canonical_hash({k: v for k, v in b.items() if k != 'reading_hash'})
    result = delivery.attach(col, b)
    value = result['research']['radar_discovery']['concept_observation_map']
    assert value['status'] == 'READ_OK' and value['coverage']['history_count'] == 3
    assert value['supplement_status'] == 'LATEST_ATTEMPT_NOT_SUCCESSFUL'
    assert 'supplement_source' not in value and col.api.calls == 0


@pytest.mark.parametrize('rate', ['0', '-.01'])
def test_quiet_or_negative_supplement_path_survives_merge(tmp_path, rate):
    from datetime import timedelta
    from decimal import Decimal
    from tests.test_concept_detail_supplement import base, START, raw
    from decision_kernel.runtime import concept_detail_supplement as detail
    def change(fixture):
        old = fixture.rate
        fixture.rate = lambda c: Decimal(rate) if c == fixture.codes[1] else old(c)
    inputs, fixture, _ = base(tmp_path, change_fixture=change)
    with zipfile.ZipFile(inputs / 'base.zip') as archive:
        files = {n[8:]: archive.read(n) for n in archive.namelist() if n.startswith('payload/')}
    primary = json.loads(files['observation.json']); stamp = START
    def request(path, params):
        nonlocal stamp
        stamp += timedelta(seconds=1)
        return raw(fixture.body(path, params)), stamp, stamp
    supplement = detail.observe(request, base_files=files, report=primary,
        selection=detail.plan(primary, offset=0), started_at=START)
    value = view.build(primary, supplement=supplement)
    assert fixture.codes[1] not in primary['projection']['detail_selected_codes']
    assert fixture.codes[1] in value['projection']['known_history_codes']
    assert fixture.codes[1] in view.render(value)
