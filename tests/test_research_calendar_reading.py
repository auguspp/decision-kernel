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


# Fabricated pair fixtures exercise admission with a REVIEWED_WEB_EXCERPT label.
# That label is a caller assertion, NOT proof of an actual official review. Both
# source bodies carry a synthetic marker; none of these fixtures is published.
def registered_pair(tmp_path, *, source=None, previous_changes=None, current_changes=None):
    before_source = RAW['source.txt'] + b'\nSYNTHETIC_TEST_FIXTURE_NOT_REAL_OFFICIAL_REVIEW\n'
    after_source = (before_source.replace(b'Friday, October 2,', b'Friday, October 9,')
                    if source is None else source + b'\nSYNTHETIC_TEST_FIXTURE_NOT_REAL_OFFICIAL_REVIEW\n')
    request = json.loads(RAW['request.json'])
    mapping, configs = {}, []
    for index, body, changes in ((1, before_source, previous_changes or {}),
                                 (2, after_source, {'reviewed_at':'2026-09-28T06:00:00Z',
                                                   'as_of':'2026-09-28T06:00:00Z', **(current_changes or {})})):
        folder = tmp_path / str(index)
        saved = calendar.save_calendar(folder, body, **(request | changes))
        files = {name:(folder/name).read_bytes() for name in calendar.FILES}
        config = {'ref':str(index)*40, 'directory':f'docs/readings/synthetic-calendar-{index}',
                  'calendar_hash':saved['calendar_hash'],
                  'blobs':{name:m.blob_sha(raw) for name,raw in files.items()}}
        mapping.update({(config['directory']+'/'+name, config['ref']):raw for name,raw in files.items()})
        configs.append(config)
    c = SavedCollector()
    def transport(path, ref):
        c.api.calls += 1
        c.api.requests.append({'path':path, 'ref':ref})
        assert c.api.calls <= c.api.max_calls
        return mapping[(path, ref)]
    c.api.file = transport
    return c, {**configs[1], 'predecessor':configs[0]}, mapping


def assert_current_only(c, result):
    assert result['status'] == STATUS and result['event_count'] == 3
    assert result['comparison']['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert result['comparison']['limitation'] == 'COMPARISON_GAP_NOT_NO_CHANGE_OR_CANCELLATION'
    assert set(c.files) == {'unrelated'} | {s['read_path'] for s in result['files'].values()}
    assert '前驱比较读取失败' in navigation(result).decode()


def test_pair_retains_original_comparison_and_both_exact_sources_with_full_baseline(tmp_path):
    from decision_kernel.runtime.research_calendar_reading import COMPARISON_STATUS, COMPARISON_PATHS
    c, config, mapping = registered_pair(tmp_path)
    c.sources = {(f'docs/old-{n}.md', '9'*40):(b'old', {}) for n in range(delivery.MAX_SOURCE_FILES)}
    baseline = c.sources
    result = read_registered(c, config)
    comparison = result['comparison']
    assert result['status'] == STATUS and comparison['status'] == COMPARISON_STATUS
    assert comparison['counts']['SOURCE_SCHEDULE_CHANGED'] == 1
    assert comparison['counts']['UNCHANGED_SCHEDULE'] == 2
    assert c.sources is baseline and c.api.calls == 8 and len(c.calls) == 8
    for snapshot, spec in ((result, config), (comparison['predecessor'], config['predecessor'])):
        assert snapshot['source_commit'] == spec['ref'] and set(snapshot['files']) == calendar.FILES
        for name, desc in snapshot['files'].items():
            assert c.files[desc['read_path']] == mapping[(spec['directory']+'/'+name, spec['ref'])]
    report = json.loads(c.files[comparison['files']['json']['read_path']])
    original = calendar.compare_calendars(tmp_path/'1', tmp_path/'2',
        predecessor_hash=config['predecessor']['calendar_hash'], successor_hash=config['calendar_hash'])
    assert report == original and c.files[COMPARISON_PATHS['json']] == calendar._encoded(original)
    assert comparison['comparison_hash'] == report['comparison_hash']
    assert comparison['successor_hash'] == result['calendar_hash'] == report['successor']['calendar_hash']
    assert all(comparison[k] == 'NONE' for k in m.AUTHORITY)
    for desc in comparison['files'].values():
        raw = c.files[desc['read_path']]
        assert desc['bytes'] == len(raw) and desc['sha256'] == m.sha256(raw) and desc['git_blob'] == m.blob_sha(raw)
    assert report['cancellation'] == 'NOT_INFERRED_NO_EXPLICIT_CANCELLATION_SOURCE'
    note = navigation(result).decode()
    assert all(path in note for path in COMPARISON_PATHS.values())
    # Resolve the detail document's relative links in the same R, not in main.
    import posixpath
    import re
    markdown = c.files[COMPARISON_PATHS['markdown']].decode()
    links = re.findall(r'\[[^\]]+\]\(([^)]+)\)', markdown)
    assert len(links) == 8
    assert all(posixpath.normpath(posixpath.join('details/research', path)) in c.files for path in links)
    assert '2026-10-02T08:30:00-04:00' in markdown and '2026-10-09T08:30:00-04:00' in markdown
    assert 'SYNTHETIC_TEST_FIXTURE' not in markdown  # Raw source text is never interpolated.


def test_single_snapshot_is_explicitly_uncompared_and_old_navigation_remains_readable():
    c = SavedCollector(); result = read_registered(c, CONFIG)
    assert result['comparison']['status'] == 'NOT_CONFIGURED' and c.api.calls == 4
    assert '未登记显式前驱' in navigation(result).decode()
    legacy = {key:value for key,value in result.items() if key != 'comparison'}
    assert '未登记显式前驱' in navigation(legacy).decode()


@pytest.mark.parametrize('change', [None, [], {'ref':'main'}, {'predecessor':CONFIG}, CONFIG])
def test_invalid_or_self_predecessor_never_turns_into_unconfigured_or_fallback(change):
    c = SavedCollector(); result = read_registered(c, {**CONFIG, 'predecessor':change})
    assert_current_only(c, result)
    assert c.api.calls == 4 and len(c.calls) == 4 and not c.sources


@pytest.mark.parametrize('side', ['current', 'predecessor'])
def test_each_external_hash_is_required_and_failed_current_never_reads_predecessor(tmp_path, side):
    c, config, _ = registered_pair(tmp_path)
    (config if side == 'current' else config['predecessor'])['calendar_hash'] = '0'*64
    result = read_registered(c, config)
    if side == 'current':
        assert result['status'] == 'UNAVAILABLE_OR_REJECTED' and c.api.calls == 4
        assert c.files == {'unrelated':b'kept'} and 'comparison' not in result
    else:
        assert_current_only(c, result)
        assert c.api.calls == 8


def test_corrupt_third_predecessor_member_preserves_current_without_refunding_requests(tmp_path):
    c, config, mapping = registered_pair(tmp_path)
    old = config['predecessor']; mapping[(old['directory']+'/request.json', old['ref'])] += b' '
    result = read_registered(c, config)
    assert_current_only(c, result)
    assert c.api.calls == 7 and result['comparison']['diagnostic']['code'] == 'SOURCE_BLOB_MISMATCH'


@pytest.mark.parametrize('changes,stage', [
    ({'reviewed_at':'2026-09-28T07:00:00Z', 'as_of':'2026-09-28T07:00:00Z'}, 'COMPARISON'),
    ({'observation_kind':'SYNTHETIC_TEST_ONLY'}, 'PREDECESSOR'),
])
def test_reverse_source_clock_or_synthetic_predecessor_cannot_be_promoted(tmp_path, changes, stage):
    c, config, _ = registered_pair(tmp_path, previous_changes=changes)
    result = read_registered(c, config)
    assert_current_only(c, result)
    assert result['comparison']['failed_stage'] == stage and c.api.calls == 8


@pytest.mark.parametrize('used,ok', [(154,True), (155,False)])
def test_pair_reserves_both_derived_outputs_before_predecessor_requests(tmp_path, used, ok):
    from decision_kernel.runtime.research_calendar_reading import COMPARISON_STATUS
    c, config, _ = registered_pair(tmp_path); c.api.calls = used
    result = read_registered(c, config)
    if ok:
        assert result['comparison']['status'] == COMPARISON_STATUS and c.api.calls == used+8
        assert c.api.calls + len(set(c.files)|{'current-state.json','README.md'}) + 5 == delivery.MAX_API_CALLS
    else:
        assert_current_only(c, result)
        assert c.api.calls == used+4 and result['comparison']['diagnostic']['code'] == 'PUBLICATION_RESERVE'
    assert delivery.MAX_SOURCE_FILES == 60 and delivery.MAX_API_CALLS == 180


@pytest.mark.parametrize('source,change', [
    (RAW['source.txt'], 'UNCHANGED_SCHEDULE'),
    (RAW['source.txt'].replace(b'08:30 AM ',b''), 'TIME_PRECISION_CHANGED'),
    (b'\n'.join(line for line in RAW['source.txt'].split(b'\n') if b'Employment Situation' not in line), 'PREDECESSOR_ONLY'),
])
def test_saved_comparison_keeps_original_precision_absence_and_unchanged_semantics(tmp_path, source, change):
    c, config, _ = registered_pair(tmp_path, source=source)
    result = read_registered(c, config); report = json.loads(c.files[result['comparison']['files']['json']['read_path']])
    employment = next(row for row in report['events'] if row['event_id'] == 'BLS:employment:2026-09')
    assert employment['change'] == change and report['actual_release'] == 'NOT_CHECKED'
    markdown = c.files[result['comparison']['files']['markdown']['read_path']].decode()
    assert '不证明官方修订链' in markdown
    if change == 'PREDECESSOR_ONLY':
        assert '仅前驱可见；非取消' in markdown and '本端摘录/窗口未见' in markdown
    if change == 'TIME_PRECISION_CHANGED':
        assert '时刻 UNKNOWN' in markdown and '时间精度变化' in markdown


@pytest.mark.parametrize('mode', ['second_write_failure', 'byte_limit'])
def test_comparison_retention_failure_rolls_back_only_optional_files(tmp_path, monkeypatch, mode):
    from decision_kernel.runtime.research_calendar_reading import COMPARISON_PATHS
    c, config, _ = registered_pair(tmp_path)
    baseline = c.sources
    if mode == 'second_write_failure':
        original = c.retain
        def failing(path, raw):
            if path == COMPARISON_PATHS['markdown']:
                raise RuntimeError('sensitive transport body must not leak')
            return original(path, raw)
        c.retain = failing
    else:
        # Both complete inputs fit, but the two-ended derived JSON is larger.
        bound = max(p.stat().st_size for d in ('1','2') for p in (tmp_path/d).iterdir())
        monkeypatch.setattr(calendar, 'MAX_SAVED_BYTES', bound)
    result = read_registered(c, config)
    assert_current_only(c, result)
    assert result['comparison']['failed_stage'] == 'RETENTION'
    assert c.api.calls == 8 and c.sources is baseline
    assert 'sensitive' not in json.dumps(result) and not (set(COMPARISON_PATHS.values()) & set(c.files))
