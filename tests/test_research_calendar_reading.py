"""Registered archive/replay mechanics; fake transport, never live source acceptance."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import research_calendar as calendar
from decision_kernel.runtime.research_calendar_reading import read_registered, navigation, STATUS

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = 'docs/readings/2026-09-28-b2-bls-calendar'
RAW = {p.name: p.read_bytes() for p in (ROOT / DIRECTORY).iterdir()}
CONFIG = {'ref':'74691f486beb6e9f2e011bb8ce9af7d14f146a30', 'directory':DIRECTORY,
          'calendar_hash':json.loads(RAW['calendar.json'])['calendar_hash'],
          'blobs':{name:m.blob_sha(body) for name,body in RAW.items()}}


class SavedAPI:
    """Only the transport is fake; production source/retain checks really run."""
    def __init__(self, files, ref):
        self.raw, self.ref = dict(files), ref
        self.calls, self.max_calls, self.requests = 0, delivery.MAX_API_CALLS, []

    def file(self, path, ref):
        self.calls += 1
        self.requests.append({"path": path, "ref": ref})
        assert self.calls <= self.max_calls
        assert ref == self.ref and path.startswith(DIRECTORY + "/")
        return self.raw[Path(path).name]


class SavedCollector(delivery.Collector):
    def __init__(self, files=None, ref=CONFIG['ref']):
        super().__init__(SavedAPI(RAW if files is None else files, ref), "0" * 40, ROOT,
                         now=lambda: '2026-09-28T08:00:00Z')
        self.files = {'unrelated': b'kept'}

    @property
    def calls(self):
        return self.api.requests


def config_for(raw):
    conf = deepcopy(CONFIG)
    conf['blobs'] = {name:m.blob_sha(body) for name,body in raw.items()}
    conf['calendar_hash'] = json.loads(raw['calendar.json'])['calendar_hash']
    return conf


def test_existing_real_archive_is_replayed_and_all_members_have_same_ref_descriptors():
    c = SavedCollector(); result = read_registered(c, CONFIG)
    assert result['status'] == STATUS
    assert result['event_count'] == 3 and result['calendar_hash'] == CONFIG['calendar_hash']
    assert result['as_of'] == json.loads(RAW['calendar.json'])['as_of']
    assert result['checked_at'] != result['as_of']
    assert all(result[k] == 'NONE' for k in m.AUTHORITY)
    assert set(result['files']) == calendar.FILES
    assert len(c.calls) == 4 and {s['ref'] for s in c.calls} == {CONFIG['ref']}
    for name, ref in result['files'].items():
        assert c.files[ref['read_path']] == RAW[name]
        assert ref['git_blob'] == CONFIG['blobs'][name]
    note = navigation(result).decode()
    assert result['files']['calendar.md']['read_path'] in note
    assert '实时日历' in note and c.files['unrelated'] == b'kept'


def test_no_registration_is_no_fetch_not_no_events():
    c = SavedCollector()
    result = read_registered(c, None)
    assert result['status'] == 'NOT_CONFIGURED' and not c.calls
    assert navigation(result) == b''


@pytest.mark.parametrize('change', [
    {'ref':'main'}, {'directory':'../outside'}, {'directory':'docs/readings/../outside'},
    {'directory':'research_cases/sample'}, {'calendar_hash':'0'*64}, {'blobs':{}},
    {'blobs':{'source.txt':'a'*40}}, {'ref':None}, {'unexpected':True},
])
def test_bad_registration_never_falls_back_or_erases_unrelated_files(change):
    c = SavedCollector(); conf = deepcopy(CONFIG); conf.update(change)
    result = read_registered(c, conf)
    assert result['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert result['limitation'] == 'CALENDAR_READ_GAP_NOT_NO_EVENTS_OR_CANCELLATION'
    assert 'files' not in result and c.files == {'unrelated':b'kept'} and c.sources == {}


@pytest.mark.parametrize('name', sorted(calendar.FILES))
def test_missing_or_corrupt_registered_members_reject_whole_calendar_only(name):
    for mode in ('missing','corrupt'):
        raw = dict(RAW)
        if mode == 'missing': raw.pop(name)
        else: raw[name] += b'\n'
        c = SavedCollector(raw)
        result = read_registered(c, CONFIG)
        assert result['status'] == 'UNAVAILABLE_OR_REJECTED' and 'files' not in result
        assert c.files == {'unrelated':b'kept'} and not c.sources


def test_hash_and_blob_updated_together_cannot_skip_actual_source_replay():
    raw = dict(RAW); value = json.loads(raw['calendar.json']); value['source']['bytes'] = 316
    raw['calendar.json'] = calendar._encoded(value)
    c = SavedCollector(raw)
    assert read_registered(c, config_for(raw))['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert c.files == {'unrelated':b'kept'}


def test_synthetic_bundle_is_not_promoted_even_when_replay_is_valid(tmp_path):
    request = json.loads(RAW['request.json']); request['observation_kind'] = 'SYNTHETIC_TEST_ONLY'
    folder = tmp_path/'synthetic'
    calendar.save_calendar(folder, RAW['source.txt'], **request)
    raw = {p.name:p.read_bytes() for p in folder.iterdir()}
    c = SavedCollector(raw)
    assert read_registered(c, config_for(raw))['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert not c.sources


def test_transport_stop_is_not_retried_and_error_body_not_leaked():
    c = SavedCollector()
    def fail(spec):
        c.calls.append(spec)
        raise RuntimeError('private diagnostic not for publication')
    c.source = fail
    result = read_registered(c, CONFIG)
    assert len(c.calls) == 1 and result['error_type'] == 'RuntimeError'
    assert 'private' not in json.dumps(result)


def test_future_review_and_wrong_returned_source_identity_reject():
    c = SavedCollector(); c.now = lambda:'2026-09-27T08:00:00Z'
    assert read_registered(c, CONFIG)['status'] == 'UNAVAILABLE_OR_REJECTED'
    c = SavedCollector(); original = c.source
    def wrong(spec):
        raw, source = original(spec)
        return raw, {**source,'ref':'0'*40}
    c.source = wrong
    assert read_registered(c, CONFIG)['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert c.files == {'unrelated':b'kept'}


def test_window_passage_never_mutates_saved_source_or_promotes_release():
    c = SavedCollector(); c.now = lambda:'2026-11-01T08:00:00Z'
    result = read_registered(c, CONFIG)
    assert result['status'] == STATUS and result['as_of'].startswith('2026-09-28')
    value = json.loads(c.files[result['files']['calendar.json']['read_path']])
    assert value == json.loads(RAW['calendar.json'])
    assert all(e['date_status'] == 'SCHEDULED' and e['actual_release_at'] == 'UNKNOWN' for e in value['events'])


def test_current_registry_calendar_replays_without_hard_coding_its_current_snapshot():
    config = json.loads((ROOT / 'current_state/registry.json').read_bytes())['research_calendar']
    folder = ROOT / config['directory']
    raw = {name:(folder/name).read_bytes() for name in calendar.FILES}
    result = read_registered(SavedCollector(raw, ref=config['ref']), config)
    assert result['status'] == STATUS
    assert result['calendar_hash'] == config['calendar_hash']


@pytest.mark.parametrize('occupied', [0, 58, delivery.MAX_SOURCE_FILES])
def test_calendar_has_four_file_capacity_without_consuming_baseline_cache(occupied):
    c = SavedCollector()
    c.sources = {(f'docs/old-{n}.md', '1' * 40): (b'old', {}) for n in range(occupied)}
    before = c.sources
    result = read_registered(c, CONFIG)
    assert result['status'] == STATUS
    assert c.sources is before and len(c.sources) == occupied
    assert c.api.calls == len(c.calls) == len(calendar.FILES) == 4
    assert len(c.files) == 5 and c.files['unrelated'] == b'kept'
    assert delivery.MAX_SOURCE_FILES == 60 and delivery.MAX_API_CALLS == 180
    if occupied == delivery.MAX_SOURCE_FILES:
        # The ordinary source limit was NOT relaxed by calendar success.
        with pytest.raises(ValueError, match='source registry bound'):
            c.source({'path': 'docs/new.md', 'ref': '1' * 40})
        assert c.api.calls == 4


@pytest.mark.parametrize('used,ok', [(164, True), (165, False)])
def test_calendar_preserves_original_publication_reserve(used, ok):
    c = SavedCollector(); c.api.calls = used
    before_files, before_sources = c.files, c.sources
    result = read_registered(c, CONFIG)
    if ok:
        assert result['status'] == STATUS and c.api.calls == used + 4
    else:
        assert result['diagnostic']['code'] == 'PUBLICATION_RESERVE'
        assert result['diagnostic']['stage'] == 'CAPACITY'
        assert c.api.calls == used and not c.calls and c.files is before_files
    assert c.sources is before_sources


@pytest.mark.parametrize('calls', [None, -1, True])
def test_unknown_api_accounting_cannot_gain_calendar_read_authority(calls):
    c = SavedCollector(); c.api.calls = calls
    result = read_registered(c, CONFIG)
    assert result['diagnostic']['code'] == 'API_ACCOUNTING_UNAVAILABLE'
    assert not c.calls and c.files == {'unrelated': b'kept'}


def test_third_file_failure_rolls_back_files_but_not_actual_api_calls():
    raw = dict(RAW); raw['request.json'] += b' '
    c = SavedCollector(raw)
    c.sources = {(f'docs/old-{n}.md', '1' * 40): (b'old', {}) for n in range(58)}
    before_files, before_sources = c.files, c.sources
    result = read_registered(c, CONFIG)
    assert result['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert result['diagnostic'] == {'stage': 'SOURCE', 'code': 'SOURCE_BLOB_MISMATCH',
                                    'baseline_source_count': 58}
    assert c.api.calls == 3 and len(c.calls) == 3
    assert c.files is before_files and c.sources is before_sources
    assert 'files' not in result


def test_retained_byte_limit_is_still_enforced_inside_isolated_calendar(monkeypatch):
    c = SavedCollector(); before_files, before_sources = c.files, c.sources
    monkeypatch.setattr(delivery, 'MAX_RETAINED_OUTPUT', 1)
    result = read_registered(c, CONFIG)
    assert result['diagnostic']['code'] == 'RETENTION_BYTE_BUDGET'
    assert c.api.calls == 1 and c.files is before_files and c.sources is before_sources
