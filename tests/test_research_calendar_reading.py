"""Registered archive/replay mechanics; fake transport, never live source acceptance."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import research_calendar as calendar
from decision_kernel.runtime.research_calendar_reading import read_registered, navigation, STATUS

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = 'docs/readings/2026-09-28-b2-bls-calendar'
RAW = {p.name: p.read_bytes() for p in (ROOT / DIRECTORY).iterdir()}
CONFIG = {'ref':'74691f486beb6e9f2e011bb8ce9af7d14f146a30', 'directory':DIRECTORY,
          'calendar_hash':json.loads(RAW['calendar.json'])['calendar_hash'],
          'blobs':{name:m.blob_sha(body) for name,body in RAW.items()}}


class SavedCollector:
    """Same source/retain descriptor contract as the existing Collector."""
    def __init__(self, files=None, ref=CONFIG['ref']):
        self.ref = ref
        self.raw = dict(RAW if files is None else files)
        self.files, self.sources, self.calls = {'unrelated': b'kept'}, {}, []
        self.now = lambda: '2026-09-28T08:00:00Z'

    def source(self, spec):
        self.calls.append(deepcopy(spec))
        assert spec['ref'] == self.ref
        name = Path(spec['path']).name
        raw = self.raw[name]
        blob = m.blob_sha(raw)
        if blob != spec['git_blob']:
            raise ValueError('registered frozen blob changed')
        path = 'sources/git/' + blob + '/' + name
        source = dict(repository=m.REPOSITORY, path=spec['path'], ref=spec['ref'], git_blob=blob,
                      bytes=len(raw), sha256=m.sha256(raw), read_path=path,
                      read_ref_rule='USE_THE_SAME_PINNED_READING_COMMIT')
        self.files[path] = raw
        self.sources[(spec['path'],spec['ref'])] = raw, source
        return raw, source


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
