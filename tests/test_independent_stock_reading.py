"""Synthetic source envelopes; real saved-input consumer; never source calls."""
from copy import deepcopy
import io
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import independent_stock_reading as reading
from decision_kernel.runtime import independent_stock_observations as independent
from test_independent_stock_observations import source, capture, audit_pin, rebuild_audit, offline


SHA = 'a' * 40


def archive(collector, root, prefix, artifact_id, run_id):
    files = {prefix + p.relative_to(root).as_posix(): p.read_bytes()
             for p in root.rglob('*') if p.is_file()}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, raw in sorted(files.items()): z.writestr(name, raw)
    raw = stream.getvalue()
    ref = collector.retain('sources/artifacts/' + model.sha256(raw) + '.zip', raw)
    ref.update(artifact_id=artifact_id, expires_at='2099-01-01T00:00:00Z',
               origin_run={'id': run_id, 'head_sha': SHA})
    collector.archive_cache[artifact_id] = (files, ref)
    return ref


def seeded(tmp_path, *, with_stock=False, cls=delivery.Collector):
    case = source(tmp_path)
    collector = cls(SimpleNamespace(calls=0, max_calls=1000), SHA, tmp_path)
    sector_ref = archive(collector, case.root, 'input-audit/', 1, 101)
    lanes = {'sector': {'latest_attempt': {'id': 101, 'conclusion': 'success'},
        'last_qualified_result': {'archive': sector_ref, 'market_session': case.days[-1].isoformat()}},
        'stock': {}}
    if with_stock:
        root, pin = capture(case)
        stock_ref = archive(collector, root, 'reading/', 2, 102)
        lanes['stock']['last_qualified_result'] = {'archive': stock_ref, 'capture_hash': pin,
            'market_session': case.days[-1].isoformat()}
    baseline = model.assemble(code_commit=SHA, checked_at=case.at.isoformat(),
        check_started_at=case.at.isoformat(), lanes=lanes,
        research={'handoffs': {'active': []}}, capabilities=[], refresh_identity={})
    collector.files.update({'current-state.json': model.read_package_bytes(baseline), 'README.md': b'original navigation\n'})
    return case, collector, baseline


def detail(collector, payload):
    d = payload['research'][reading.KEY]
    raw = collector.files[d['read_path']]
    assert len(raw) == d['bytes'] and model.sha256(raw) == d['sha256'] and model.blob_sha(raw) == d['git_blob']
    return json.loads(raw)


def test_real_reader_complete_denominator_and_no_added_reads(tmp_path):
    case, c, baseline = seeded(tmp_path, with_stock=True)
    original = deepcopy(baseline)
    payload = reading.attach(c, baseline)
    report = detail(c, payload)
    assert baseline == original and payload['lanes'] == baseline['lanes']
    assert c.api.calls == report['new_read_requests'] == report['new_source_requests'] == 0
    observed = report['observations']
    assert observed['coverage']['unique_identities'] == len(observed['inventory']['rows']) == 503
    assert observed['coverage']['independently_selected'] == 16
    assert observed['coverage']['selected_qualified'] == 1
    pin = baseline['lanes']['stock']['last_qualified_result']['capture_hash']
    assert observed == independent.build(case.root, expected_audit_hash=audit_pin(case),
        stock_root=case.root.parent/'stock', expected_capture_hash=pin)
    assert observed['selection']['selected'][0]['signed_quote_change'] == '-0.5'
    assert all(report[k] == 'NONE' for k in model.AUTHORITY)
    assert report['acquisition'] == 'SECTOR_OWNED_NOT_UNCONDITIONAL_DAILY_INDEPENDENT_CAPTURE'
    assert c.files['README.md'].startswith(b'original navigation')
    assert reading.PATH.encode() in c.files['README.md']
    model.validate_read_package(payload)


def test_no_history_and_mismatched_history_do_not_change_selection(tmp_path):
    _, c, baseline = seeded(tmp_path, with_stock=True)
    supplied = reading.derive(c, baseline)
    baseline['lanes']['stock']['last_qualified_result']['market_session'] = '2000-01-01'
    different = reading.derive(c, baseline)
    assert supplied['observations']['selection'] == different['observations']['selection']
    assert different['observations']['coverage']['selected_qualified'] == 0
    assert different['stock_source'] is None
    assert different['gaps'][0]['meaning'] == 'NO_SAME_SESSION_STOCK_SOURCE'


@pytest.mark.parametrize('damage', ['cache_missing', 'cache_changed', 'archive_changed', 'expired'])
def test_rejected_source_is_explicit_not_empty_or_old_sample(tmp_path, damage):
    _, c, baseline = seeded(tmp_path)
    ref = baseline['lanes']['sector']['last_qualified_result']['archive']
    if damage == 'cache_missing': c.archive_cache.clear()
    elif damage == 'cache_changed': c.archive_cache[1][0]['foreign.txt'] = b'changed'
    elif damage == 'archive_changed': c.files[ref['read_path']] += b'changed'
    else: ref['expires_at'] = '2000-01-01T00:00:00Z'
    report = detail(c, reading.attach(c, baseline))
    assert report['status'] == 'INPUT_UNAVAILABLE_NOT_QUIET' and report['observations'] is None
    assert report['gaps'][0]['phase'] == 'SOURCE_ARCHIVE'
    assert c.api.calls == 0


def test_optional_stock_damage_keeps_independent_quote_sample(tmp_path):
    _, c, baseline = seeded(tmp_path, with_stock=True)
    del c.archive_cache[2]
    report = reading.derive(c, baseline)
    assert report['observations']['coverage']['unique_identities'] == 503
    assert report['observations']['coverage']['selected_qualified'] == 0
    assert report['gaps'][0]['phase'] == 'OPTIONAL_OWN_HISTORY'


def test_failed_sector_does_not_gate_valid_saved_independent_inputs(tmp_path):
    _, c, baseline = seeded(tmp_path)
    lane = baseline['lanes']['sector']
    ref = lane['last_qualified_result']['archive']
    lane['last_qualified_result'] = None
    lane['latest_attempt'] = {'id': 101, 'conclusion': 'failure', 'operation': {'source': ref}}
    report = reading.derive(c, baseline)
    assert report['observations']['coverage']['unique_identities'] == 503
    assert report['source_selection'] == 'LATEST_FAILED_ATTEMPT_INPUTS'
    assert report['latest_sector_attempt']['conclusion'] == 'failure'


def test_quiet_source_without_pages_is_not_an_empty_scan(tmp_path):
    case, c, baseline = seeded(tmp_path)
    manifest = json.loads((case.root/'manifest.json').read_bytes())
    pages = [r for r in manifest['requests'] if r['path'] == independent.own.SNAPSHOT]
    manifest['requests'] = [r for r in manifest['requests'] if r not in pages]
    for r in pages:
        del manifest['files'][r['response_file']]
        (case.root/r['response_file']).unlink()
    (case.root/'manifest.json').write_text(json.dumps(manifest))
    rebuild_audit(case)
    baseline['lanes']['sector']['last_qualified_result']['archive'] = archive(c, case.root, 'input-audit/', 3, 103)
    report = reading.derive(c, baseline)
    assert report['observations'] is None and report['gaps'][0]['phase'] == 'ALL_MARKET_INPUTS'
    assert report['status'] == 'INPUT_UNAVAILABLE_NOT_QUIET'


def test_index_capacity_preserves_baseline_and_records_nonquiet_gap(tmp_path):
    _, c, baseline = seeded(tmp_path)
    baseline['capacity_fixture'] = ''
    baseline['reading_hash'] = canonical_hash({k: v for k, v in baseline.items() if k != 'reading_hash'})
    baseline['capacity_fixture'] = 'x' * (192*1024 - 100 - len(model.read_package_bytes(baseline)))
    baseline['reading_hash'] = canonical_hash({k: v for k, v in baseline.items() if k != 'reading_hash'})
    c.files['current-state.json'] = model.read_package_bytes(baseline)
    out = reading.attach(c, baseline)
    assert len(c.files['current-state.json']) <= 192*1024
    assert out['lanes'] == baseline['lanes'] and out['capacity_fixture'] == baseline['capacity_fixture']
    assert out['research'][reading.KEY]['status'] == 'NOT_PUBLISHED_CAPACITY_GAP_NOT_QUIET'
    assert reading.PATH not in c.files


def test_normal_publisher_calls_saved_consumer_without_new_flag(tmp_path, monkeypatch):
    from decision_kernel.runtime import current_state_delivery_with_odds_watch as publisher
    _, c, baseline = seeded(tmp_path, cls=publisher.Collector)
    monkeypatch.setattr(delivery.Collector, 'collect', lambda self, refresh: baseline)
    out = c.collect({})
    assert detail(c, out)['observations']['coverage']['unique_identities'] == 503
    assert c.api.calls == 0
