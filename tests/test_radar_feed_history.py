from __future__ import annotations

import copy
import json
import shutil
from datetime import timedelta
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import radar_feed_history as history
from decision_kernel.runtime import radar_feed_consumer as consumer
from decision_kernel.runtime import radar_feed_intake as feed
from decision_kernel.runtime.hithink_dump_trial import DumpTrialError
from test_radar_feed_consumer import setup, contents, AS_OF
from test_radar_feed_intake import capture, item, AT, OTHER
from test_theme_plan_execution import prepared
from test_sector_radar_audit import prohibit_network

REGISTERED = AS_OF + timedelta(hours=1)
LATER = REGISTERED + timedelta(minutes=1)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)
    monkeypatch.setattr(feed.feedparser.http, 'get', lambda *a, **k: pytest.fail('no RSS refetch'))


def sealed(tmp_path, *, execute=True):
    values, output, calls, pauses, run = prepared(tmp_path)
    if execute:
        assert run()['status'] == 'COMPLETE_EXACT_PLAN_CAPTURE'
    capsule = tmp_path/'history'
    value = history.register_history(values[1], capsule, as_of=REGISTERED.isoformat(), initialize=True,
                scans=[tmp_path/'scan'], executions=[output] if execute else [])
    return values, capsule, value, output


def rehash(root):
    value = consumer._json(root/'history.json')
    value['files'] = {k: v for k, v in history._inventory(root).items() if k != 'history.json'}
    value = feed._sealed({k: v for k, v in value.items() if k != 'history_hash'}, 'history_hash')
    (root/'history.json').write_bytes(feed.data(value))
    return value


def test_saved_history_restores_original_consumer_and_exact_market_stage(tmp_path):
    values, root, manifest, execution = sealed(tmp_path)
    before = contents(values[1]), contents(tmp_path/'scan'), contents(execution)
    restored = tmp_path/'restored'
    value = history.restore_history(root, values[1], restored, as_of=LATER.isoformat(), expected_hash=manifest['history_hash'])
    assert value['scan_count'] == value['execution_count'] == 1
    assert value['network_calls'] == 0
    assert not value['source_delivery_acknowledged'] and not value['remote_publication_verified']
    assert before == (contents(values[1]), contents(tmp_path/'scan'), contents(execution))
    state, source, _, context = values
    handoff = consumer.scan(source, state, context, restored/'scans', tmp_path/'next',
        as_of=LATER.isoformat(), generated_at=LATER.isoformat(), batch_size=32, executions=restored/'executions')
    assert handoff['status'] == 'NO_PENDING_SOURCE_SCAN'
    assert handoff['unexecuted_prior_plans'] == []
    assert len(handoff['market_execution_observations']) == 1
    assert handoff['market_execution_observations'][0]['market_stage_succeeded']
    receipt = consumer.verify_scan(next((restored/'scans').iterdir()))['receipt']
    assert receipt['acquisition_status'] == 'PLAN_NOT_EXECUTED'


def test_scan_only_restore_keeps_outstanding_plan_without_executing_it(tmp_path):
    values, root, manifest, _ = sealed(tmp_path, execute=False)
    state, source, _, context = values
    history.restore_history(root, source, tmp_path/'restored', as_of=LATER.isoformat(), expected_hash=manifest['history_hash'])
    result = consumer.scan(source, state, context, tmp_path/'restored/scans', tmp_path/'later',
        as_of=LATER.isoformat(), generated_at=LATER.isoformat(), batch_size=32, executions=tmp_path/'restored/executions')
    assert result['status'] == 'NO_PENDING_SOURCE_SCAN'
    assert len(result['unexecuted_prior_plans']) == 1
    assert result['market_execution_observations'] == []


def test_snapshot_is_self_contained_after_original_working_directories_are_removed(tmp_path):
    values, root, manifest, output = sealed(tmp_path)
    shutil.rmtree(values[1]); shutil.rmtree(tmp_path/'scan'); shutil.rmtree(output)
    restored = tmp_path/'restored'
    history.restore_history(root, root/'feed-capture', restored, as_of=LATER.isoformat(), expected_hash=manifest['history_hash'])
    assert consumer.verify_scan(next((restored/'scans').iterdir()))['receipt']['source_keys']


def test_thirty_three_sources_advance_32_then_1_after_two_separate_restores(tmp_path):
    rows = [item('No literal label.', url=f'https://www.stats.gov.cn/sj/zxfb/202609/t20260904_{1234500+i}.html', guid=f'e{i}') for i in range(33)]
    state, source, receipts, context = setup(tmp_path, rows)
    first = consumer.scan(source, state, context, receipts, tmp_path/'scan-one',
        as_of=AS_OF.isoformat(), generated_at=AS_OF.isoformat(), batch_size=32)
    assert first['selected_source_records'] == 32 and len(first['batch']['deferred_source_keys']) == 1
    at1 = AS_OF + timedelta(seconds=10)
    one = history.register_history(source, tmp_path/'one', as_of=at1.isoformat(), initialize=True, scans=[tmp_path/'scan-one'])
    at2 = AS_OF + timedelta(seconds=20)
    history.restore_history(tmp_path/'one', source, tmp_path/'restored-one', as_of=at2.isoformat(), expected_hash=one['history_hash'])
    second = consumer.scan(source, state, context, tmp_path/'restored-one/scans', tmp_path/'scan-two',
        as_of=at2.isoformat(), generated_at=at2.isoformat(), batch_size=32, executions=tmp_path/'restored-one/executions')
    assert second['selected_source_records'] == 1 and second['already_scanned_source_records'] == 32
    at3 = AS_OF + timedelta(seconds=30)
    two = history.register_history(source, tmp_path/'two', as_of=at3.isoformat(), previous=tmp_path/'one',
        previous_hash=one['history_hash'], scans=[tmp_path/'scan-two'])
    history.restore_history(tmp_path/'two', source, tmp_path/'restored-two', as_of=LATER.isoformat(), expected_hash=two['history_hash'])
    quiet = consumer.scan(source, state, context, tmp_path/'restored-two/scans', tmp_path/'quiet',
        as_of=LATER.isoformat(), generated_at=LATER.isoformat(), batch_size=32, executions=tmp_path/'restored-two/executions')
    assert quiet['status'] == 'NO_PENDING_SOURCE_SCAN' and quiet['already_scanned_source_records'] == 33
    assert quiet['upstream_pending_versions'] == 33  # Seen/scanned is not generic delivery.
    assert len(two['scans']) == 2 and not two['executions']
    assert two['parent_history_hash'] == one['history_hash']
    assert not (tmp_path/'two/one').exists()  # No recursive predecessor artifacts.


def test_failed_execution_remains_then_later_success_is_added_not_overwritten(tmp_path):
    values, output, calls, pauses, run = prepared(tmp_path)
    def failed(*args):
        raise DumpTrialError('HTTP_REJECTED', http_status=429)
    assert run(transport=failed)['status'] == 'INCOMPLETE_EXACT_PLAN_CAPTURE'
    failed_path = tmp_path/'failed'; output.rename(failed_path)
    first = history.register_history(values[1], tmp_path/'first', as_of=REGISTERED.isoformat(), initialize=True,
        scans=[tmp_path/'scan'], executions=[failed_path])
    assert not next(iter(first['executions'].values()))['market_stage_succeeded']
    assert run()['status'] == 'COMPLETE_EXACT_PLAN_CAPTURE'
    second = history.register_history(values[1], tmp_path/'second', as_of=LATER.isoformat(), previous=tmp_path/'first',
        previous_hash=first['history_hash'], executions=[output])
    assert len(second['executions']) == 2
    assert sorted(v['market_stage_succeeded'] for v in second['executions'].values()) == [False, True]
    assert all(second['executions'][k] == v for k, v in first['executions'].items())


def test_duplicate_copies_do_not_add_records_and_preserve_original_bytes(tmp_path):
    values, root, manifest, output = sealed(tmp_path)
    shutil.copytree(tmp_path/'scan', tmp_path/'scan-copy')
    shutil.copytree(output, tmp_path/'execution-copy')
    next_value = history.register_history(values[1], tmp_path/'next-history', as_of=LATER.isoformat(), previous=root,
        previous_hash=manifest['history_hash'], scans=[tmp_path/'scan', tmp_path/'scan-copy'], executions=[output, tmp_path/'execution-copy'])
    assert next_value['scans'] == manifest['scans'] and next_value['executions'] == manifest['executions']


def test_new_feed_version_extends_source_but_is_not_marked_scanned(tmp_path):
    values, root, manifest, _ = sealed(tmp_path, execute=False)
    later = tmp_path/'new-feed'
    capture(later, [item('Later description.', url=OTHER, guid='new')], AT+timedelta(minutes=5), values[1])
    value = history.register_history(later, tmp_path/'new-history', as_of=LATER.isoformat(), previous=root, previous_hash=manifest['history_hash'])
    assert len(value['source_anchor']['versions']) == len(manifest['source_anchor']['versions']) + 1
    assert value['scans'] == manifest['scans']


def test_unknown_publication_time_is_preserved_as_a_gap_not_qualified_by_storage(tmp_path):
    state, source, _, _ = setup(tmp_path, [item(published='2026-09-04 09:30:00')])
    before = contents(source)
    value = history.register_history(source, tmp_path/'history', as_of=REGISTERED.isoformat(), initialize=True)
    assert value['scans'] == value['executions'] == {}
    assert before == contents(source)
    _, _, exports = consumer._load_feed(tmp_path/'history/feed-capture', REGISTERED.isoformat())
    assert exports['status'] == 'SOURCE_EXPORT_BLOCKED'


@pytest.mark.parametrize('mode', ['implicit-empty', 'both', 'missing', 'unbound', 'wrong-hash', 'equal-time', 'future'])
def test_predecessor_and_registration_boundaries_fail_closed(tmp_path, mode):
    values, root, manifest, _ = sealed(tmp_path, execute=False)
    kwargs = {'previous': root, 'previous_hash': manifest['history_hash'], 'as_of': LATER.isoformat()}
    if mode == 'implicit-empty': kwargs.update(previous=None, previous_hash=None)
    elif mode == 'both': kwargs['initialize'] = True
    elif mode == 'missing': kwargs['previous'] = tmp_path/'absent'
    elif mode == 'unbound': kwargs['previous_hash'] = None
    elif mode == 'wrong-hash': kwargs['previous_hash'] = '0'*64
    elif mode == 'equal-time': kwargs['as_of'] = REGISTERED.isoformat()
    else: kwargs['as_of'] = AS_OF.isoformat()
    with pytest.raises((ValueError, OSError)):
        history.register_history(values[1], tmp_path/'rejected', **kwargs)
    assert not (tmp_path/'rejected').exists()


@pytest.mark.parametrize('change', ['version', 'first-clock', 'appearance', 'baseline', 'provenance', 'policy', 'time'])
def test_source_extension_never_resets_or_rewrites_prior_identity(tmp_path, change):
    values, root, manifest, _ = sealed(tmp_path, execute=False)
    old = manifest['source_anchor']; new = copy.deepcopy(old); key = next(iter(old['versions']))
    if change == 'version': del new['versions'][key]
    elif change == 'first-clock': new['versions'][key]['first_identity'] = 'a'*64
    elif change == 'appearance': new['versions'][key]['appearances'] = []
    elif change == 'baseline': new['initialized_at'] = LATER.isoformat()
    elif change == 'provenance': new['provenance'] = 'PUBLIC_HTTP_CAPTURE'
    elif change == 'policy': new['policy_hash'] = 'a'*64
    else: new['recorded_at'] = (AT-timedelta(days=1)).isoformat()
    with pytest.raises(ValueError): history._extends(old, new)


@pytest.mark.parametrize('change', ['missing-dir', 'loose-receipt', 'changed-page', 'unknown-file', 'wrong-pin', 'future'])
def test_restore_never_falls_back_to_empty_or_trusts_loose_status(tmp_path, change):
    values, root, manifest, _ = sealed(tmp_path, execute=False)
    pin = manifest['history_hash']; at = LATER.isoformat()
    if change == 'missing-dir': shutil.rmtree(root/'scans')
    elif change == 'loose-receipt': (root/'scans/success.json').write_text('{"success":true}')
    elif change == 'changed-page': next((root/'scans').glob('*/index.html')).write_text('fabricated')
    elif change == 'unknown-file': (root/'unexpected').write_text('extra')
    elif change == 'wrong-pin': pin = 'b'*64
    else: at = AS_OF.isoformat()
    with pytest.raises((ValueError, OSError)):
        history.restore_history(root, values[1], tmp_path/'restored', as_of=at, expected_hash=pin)
    assert not (tmp_path/'restored').exists()


def test_rehashed_removal_cannot_erase_a_predecessor_scan(tmp_path):
    values, root, first, _ = sealed(tmp_path, execute=False)
    second = tmp_path/'second'
    history.register_history(values[1], second, as_of=LATER.isoformat(), previous=root, previous_hash=first['history_hash'])
    shutil.rmtree(next((second/'scans').iterdir()))
    value = consumer._json(second/'history.json'); value['scans'] = {}
    (second/'history.json').write_bytes(feed.data(value)); rehash(second)
    with pytest.raises(ValueError, match='removed or rewritten'): history.verify_history(second)


def test_execution_without_registered_scan_cannot_be_a_completion(tmp_path):
    values, output, _, _, run = prepared(tmp_path); run()
    with pytest.raises(ValueError, match='exact registered scan'):
        history.register_history(values[1], tmp_path/'rejected', as_of=REGISTERED.isoformat(), initialize=True, executions=[output])
    assert not (tmp_path/'rejected').exists()


def test_blocked_scan_and_loose_success_json_are_not_registered(tmp_path):
    state, source, receipts, context = setup(tmp_path, [item(published='')])
    consumer.scan(source, state, context, receipts, tmp_path/'blocked', as_of=AS_OF.isoformat(), generated_at=AS_OF.isoformat())
    with pytest.raises(ValueError):
        history.register_history(source, tmp_path/'rejected', as_of=REGISTERED.isoformat(), initialize=True, scans=[tmp_path/'blocked'])
    assert not (tmp_path/'rejected').exists()


def test_existing_output_and_input_overlap_are_rejected(tmp_path):
    values, root, manifest, _ = sealed(tmp_path, execute=False)
    before = contents(root)
    for target in (root, root/'nested', values[1]/'nested'):
        with pytest.raises(ValueError):
            history.restore_history(root, values[1], target, as_of=LATER.isoformat(), expected_hash=manifest['history_hash'])
    assert contents(root) == before


def test_byte_budget_is_still_the_existing_total_bound(tmp_path, monkeypatch):
    values, root, manifest, _ = sealed(tmp_path, execute=False)
    monkeypatch.setattr(consumer, 'MAX_BUNDLE_BYTES', 100)
    with pytest.raises(ValueError, match='budget'):
        history.restore_history(root, values[1], tmp_path/'restored', as_of=LATER.isoformat(), expected_hash=manifest['history_hash'])
    assert not (tmp_path/'restored').exists()


def test_interrupted_write_cleans_only_its_new_temporary_directory(tmp_path, monkeypatch):
    values, root, manifest, _ = sealed(tmp_path, execute=False)
    before = contents(root), contents(values[1]); actual = history._write
    def fail(path, value):
        if path.name == 'restoration.json': raise OSError('synthetic interruption')
        return actual(path, value)
    monkeypatch.setattr(history, '_write', fail)
    with pytest.raises(OSError):
        history.restore_history(root, values[1], tmp_path/'restored', as_of=LATER.isoformat(), expected_hash=manifest['history_hash'])
    assert not (tmp_path/'restored').exists() and not list(tmp_path.glob('.restore-native-history-*'))
    assert before == (contents(root), contents(values[1]))


def test_cli_register_verify_restore_and_wrong_pin(tmp_path):
    _, source, _, _ = setup(tmp_path)
    root = tmp_path/'history'
    assert history.main(['register', '--source', str(source), '--output', str(root), '--initialize', '--as-of', REGISTERED.isoformat()]) == 0
    pin = consumer._json(root/'history.json')['history_hash']
    assert history.main(['verify', '--history', str(root), '--expected-hash', pin, '--as-of', LATER.isoformat()]) == 0
    assert history.main(['restore', '--history', str(root), '--source', str(source), '--output', str(tmp_path/'restored'), '--expected-hash', pin, '--as-of', LATER.isoformat()]) == 0
    assert history.main(['restore', '--history', str(root), '--source', str(source), '--output', str(tmp_path/'bad'), '--expected-hash', '0'*64, '--as-of', LATER.isoformat()]) == 2
