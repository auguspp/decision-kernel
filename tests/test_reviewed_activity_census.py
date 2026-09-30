"""Explicitly synthetic reviewed-assignment census and retained-byte boundaries."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as state
from decision_kernel.runtime import institutional_context as raw_context
from decision_kernel.runtime import reviewed_activity_census as c


EX = {'repository': 'auguspp/decision-kernel', 'workflow': raw_context.WORKFLOW,
      'ref': 'refs/heads/main', 'event': 'workflow_dispatch', 'code_commit': 'a' * 40,
      'run_id': 123, 'attempt': 1}


def descriptor(sid, raw, qualification='SYNTHETIC_FIXTURE'):
    return {'id': sid, 'subject': '002436.SZ', 'ref': 'a' * 40,
            'path': 'tests/fixtures/synthetic-census/' + sid + '.json',
            'git_blob': state.blob_sha(raw), 'sha256': state.sha256(raw), 'bytes': len(raw),
            'qualification': qualification, 'published_at': None, 'acquired_at': None}


def fact(rid, field, value):
    return {'record_id': rid, 'binding': {'value': value,
            'locator': {'pointer': '/' + rid + '/' + field}}}


def sample():
    """Two synthetic events: one repeated visitor/institution and an excluded host."""
    rows, records, events = {}, [], []
    entities = [
        {'id': 'institution', 'kind': 'INSTITUTION', 'identity_value': 'synthetic-firm-1',
         'names': ['Synthetic Firm']},
        {'id': 'alice', 'kind': 'PERSON', 'identity_value': 'synthetic-person-1',
         'names': ['Synthetic Alice']},
        {'id': 'bob', 'kind': 'PERSON', 'identity_value': 'synthetic-person-2',
         'names': ['Synthetic Bob']},
        {'id': 'host', 'kind': 'PERSON', 'identity_value': 'synthetic-host-1',
         'names': ['Synthetic Host']},
    ]
    for entity in entities:
        entity.update(identity_basis='PROVIDER_ID', identity_qualification='REVIEWED_RESOLVED',
                      namespace='synthetic-provider',
                      equivalence_note='Explicit synthetic stable provider identity')
    for index in (1, 2):
        rid, eid = 'r' + str(index), 'e' + str(index)
        row = {'event_id': 'synthetic-event-' + str(index), 'event_date': '2026-09-0' + str(index),
               'disclosure_date': '2026-09-03', 'institutions_complete': 'Synthetic complete institution roster',
               'persons_complete': 'Synthetic complete person roster'}
        attendance = []
        for entity in entities:
            if entity['id'] == 'bob' and index == 1:
                continue
            key = entity['id']; role = 'HOST' if key == 'host' else 'VISITOR'
            row[key + '_name'] = entity['names'][0]
            row[key + '_id'] = entity['identity_value']
            row[key + '_role'] = role
            attendance.append({'entity_id': key, 'name': fact(rid, key + '_name', row[key + '_name']),
                'provider_id': fact(rid, key + '_id', row[key + '_id']), 'role': role,
                'role_evidence': fact(rid, key + '_role', role),
                'role_note': 'Explicit synthetic source role'})
        rows[rid] = row
        records.append({'id': rid, 'source_id': 's', 'kind': 'RETAINED_REFERENCE',
            'locator': {'pointer': '/' + rid}, 'disposition': 'SELECTED',
            'review_note': 'Synthetic flat event and participant record',
            'event_assignment': eid, 'variant': 'original'})
        events.append({'id': eid, 'records': [rid], 'selected_variant': 'original',
            'identity_basis': 'ORIGINAL_EVENT_ID', 'identity_namespace': 'synthetic-events', 'equivalence_note': 'Distinct synthetic original event ID',
            'identity': fact(rid, 'event_id', row['event_id']),
            'event_date': fact(rid, 'event_date', row['event_date']),
            'disclosure_date': fact(rid, 'disclosure_date', row['disclosure_date']),
            'variant_resolved': True, 'variant_note': 'Only selected synthetic roster variant',
            'roster': {'INSTITUTION': 'COMPLETE', 'PERSON': 'COMPLETE'},
            'roster_evidence': {'INSTITUTION': fact(rid, 'institutions_complete', row['institutions_complete']),
                                'PERSON': fact(rid, 'persons_complete', row['persons_complete'])},
            'roster_note': {'INSTITUTION': 'Synthetic full roster statement', 'PERSON': 'Synthetic full roster statement'},
            'attendance': attendance})
    raw = json.dumps(rows, sort_keys=True).encode()
    value = {'version': c.VERSION, 'authority': deepcopy(c.AUTHORITY), 'subject': '002436.SZ',
        'question': 'Count selected synthetic event attendance without inferring issuer coverage',
        'limitations': 'Synthetic fixtures only; no real issuer activity or economic inference',
        'reviewed_at': '2026-09-30T00:00:00Z',
        'scope': {'basis': 'EVENT_DATE', 'begin': '2026-09-01', 'end': '2026-09-03',
                  'coverage': 'SELECTED_EVIDENCE_ONLY', 'inventory_complete': True,
                  'selection_note': 'Only the explicit synthetic records'},
        'sources': [descriptor('s', raw)], 'records': records, 'events': events, 'entities': entities}
    return value, {'s': raw}


def replace_rows(value, files, rows):
    files['s'] = json.dumps(rows, sort_keys=True).encode()
    value['sources'][0] = descriptor('s', files['s'])


def test_unique_people_are_not_person_event_attendances_and_hosts_are_excluded():
    value, files = sample(); report = c.build(value, files)
    expected = {'events': 2, 'distinct_institutions': 1, 'distinct_participants': 2,
                'participant_event_attendances': 3}
    assert {k: v['selected_set_total'] for k, v in report['counts'].items()} == expected
    assert all(v['issuer_window_total'] is None for v in report['counts'].values())
    assert all(v['qualification'] == 'REVIEWED_SELECTED_SET_ONLY' for v in report['counts'].values())
    assert report['authority'] == c.AUTHORITY
    assert report['historical_availability'] == 'NOT_ESTABLISHED_BY_RETRIEVAL'
    assert report == c.build(value, files)
    assert report['report_hash'] == canonical_hash({k: v for k, v in report.items() if k != 'report_hash'})


def test_host_does_not_increase_counts_even_when_present_at_both_events():
    value, files = sample(); first = c.build(value, files)
    for event in value['events']:
        event['attendance'] = [e for e in event['attendance'] if e['entity_id'] != 'host']
    assert c.build(value, files)['counts'] == first['counts']


@pytest.mark.parametrize('key,bad', [('ref', 'main'), ('git_blob', 'b' * 40),
    ('sha256', 'b' * 64), ('bytes', 0), ('subject', '002281.SZ'), ('path', '../source.json')])
def test_immutable_source_descriptor_tampering_rejected(key, bad):
    value, files = sample(); value['sources'][0][key] = bad
    with pytest.raises(ValueError): c.build(value, files)


def test_source_clock_after_review_is_rejected():
    value, files = sample(); value['sources'][0]['acquired_at'] = '2026-10-01T00:00:00Z'
    with pytest.raises(ValueError, match='clock after review'): c.build(value, files)


@pytest.mark.parametrize('status', ['PARTIAL', 'UNKNOWN'])
def test_person_roster_gap_preserves_event_and_institution_totals(status):
    value, files = sample(); value['events'][0]['roster']['PERSON'] = status
    report = c.build(value, files)['counts']
    assert report['events']['selected_set_total'] == 2
    assert report['distinct_institutions']['selected_set_total'] == 1
    for key in ('distinct_participants', 'participant_event_attendances'):
        assert report[key]['selected_set_total'] is None
        assert report[key]['observed_subset'] in (2, 3)
        assert 'e1:' + status in report[key]['blockers']


def test_unknown_role_does_not_silently_become_a_visitor():
    value, files = sample(); edge = value['events'][0]['attendance'][1]; edge['role'] = 'UNKNOWN'
    counts = c.build(value, files)['counts']
    assert counts['events']['selected_set_total'] == 2
    assert counts['participant_event_attendances']['observed_subset'] == 2
    assert counts['participant_event_attendances']['selected_set_total'] is None
    assert 'e1:ROLE_UNKNOWN' in counts['distinct_participants']['blockers']


@pytest.mark.parametrize('target', ['name', 'provider_id', 'role_evidence', 'roster', 'identity', 'date'])
def test_cross_record_binding_cannot_borrow_literal_evidence(target):
    value, files = sample(); event = value['events'][0]
    if target in ('name', 'provider_id', 'role_evidence'):
        item = event['attendance'][0][target]
    elif target == 'roster': item = event['roster_evidence']['PERSON']
    elif target == 'identity': item = event['identity']
    else: item = event['event_date']
    item['binding']['locator']['pointer'] = item['binding']['locator']['pointer'].replace('/r1/', '/r2/')
    with pytest.raises(ValueError, match='member of one JSON record'): c.build(value, files)


def test_complete_roster_needs_bound_evidence():
    value, files = sample(); value['events'][0]['roster_evidence']['PERSON']['binding']['value'] = 'unsupported full roster'
    with pytest.raises(ValueError, match='bound value differs'): c.build(value, files)


def test_provider_id_must_match_source_while_reviewed_equivalence_is_explicit():
    value, files = sample(); value['entities'][0]['identity_value'] = 'reviewed-firm-key'
    with pytest.raises(ValueError, match='provider identity differs'): c.build(value, files)
    value['entities'][0].update(identity_basis='REVIEWED_EQUIVALENCE',
        equivalence_note='Synthetic reviewer explicitly reconciles this firm across both records')
    assert c.build(value, files)['counts']['distinct_institutions']['selected_set_total'] == 1
    value['entities'][0]['identity_basis'] = 'NAME_ONLY'
    with pytest.raises(ValueError, match='equivalence'): c.build(value, files)


def test_duplicate_canonical_entity_key_cannot_inflate_population():
    value, files = sample(); duplicate = deepcopy(value['entities'][1]); duplicate['id'] = 'alias'
    value['entities'].append(duplicate)
    with pytest.raises(ValueError, match='multiple entity keys'): c.build(value, files)


def test_same_event_duplicate_attendance_is_rejected():
    value, files = sample(); value['events'][0]['attendance'].append(deepcopy(value['events'][0]['attendance'][0]))
    with pytest.raises(ValueError, match='duplicate or unknown attendee'): c.build(value, files)


def test_flat_source_record_guard_rejects_event_container():
    value, files = sample(); rows = json.loads(files['s']); rows['container'] = deepcopy(rows)
    replace_rows(value, files, rows); value['records'][0]['locator']['pointer'] = '/container'
    with pytest.raises(ValueError, match='flat source record'): c.build(value, files)


def add_superseded(value, files):
    rows = json.loads(files['s']); rows['old'] = dict(rows['r1'], persons_complete='Synthetic obsolete roster')
    replace_rows(value, files, rows)
    old = deepcopy(value['records'][0]); old.update(id='old', locator={'pointer': '/old'},
        disposition='SUPERSEDED', successor='r1', variant='earlier-roster',
        correction_note='Synthetic corrected roster directly selects its same-event successor')
    value['records'].append(old)


def test_superseded_same_event_variant_is_retained_without_extra_event():
    value, files = sample(); add_superseded(value, files)
    report = c.build(value, files)
    assert report['counts']['events']['selected_set_total'] == 2
    assert report['records'][-1]['status'] == 'SUPERSEDED'


@pytest.mark.parametrize('mutation', ['other_event', 'self', 'not_selected', 'wrong_variant'])
def test_supersession_requires_direct_selected_same_event_and_matching_variant(mutation):
    value, files = sample(); add_superseded(value, files)
    if mutation == 'other_event': value['records'][-1]['successor'] = 'r2'
    elif mutation == 'self': value['records'][-1]['successor'] = 'old'
    elif mutation == 'not_selected': value['records'][0]['disposition'] = 'UNRESOLVED'
    else: value['events'][0]['selected_variant'] = 'earlier-roster'
    with pytest.raises(ValueError): c.build(value, files)


def test_unresolved_variant_or_partial_inventory_does_not_become_total():
    value, files = sample(); value['events'][0]['variant_resolved'] = False
    counts = c.build(value, files)['counts']
    assert counts['events']['observed_subset'] == 1
    assert all(item['selected_set_total'] is None for item in counts.values())
    value, files = sample(); value['scope']['inventory_complete'] = False
    assert all(item['selected_set_total'] is None for item in c.build(value, files)['counts'].values())


def test_unknown_window_date_is_not_zero_events():
    value, files = sample()
    for event in value['events']: event['event_date'] = None
    counts = c.build(value, files)['counts']
    assert all(item['observed_subset'] is None and item['selected_set_total'] is None for item in counts.values())


def test_provider_qualification_cannot_be_relabelled_as_plain_reference():
    value, files = sample(); value['sources'][0]['qualification'] = 'PROVIDER_CAPTURE'
    with pytest.raises(ValueError, match='provider source must use replayed'): c.build(value, files)


def test_failed_provider_capture_preserves_unknown_not_zero(tmp_path):
    value, files = sample()
    root = tmp_path / 'synthetic-capture'
    scope = raw_context.scope('002436.SZ', '2026-09-01', '2026-09-03')
    calls = []
    def transport(spec, selected_scope):
        calls.append(spec['family']); assert selected_scope == scope
        return 502, b'synthetic gateway failure'
    raw_context.capture(root, scope, EX, transport=transport, clock=lambda: '2026-09-04T00:00:00+00:00')
    mapping = {}
    for name in ('capture.json', 'activity.body', 'reports.body'):
        sid = 'capture-' + name.replace('.', '-')
        files[sid] = (root / name).read_bytes(); mapping[name] = sid
        value['sources'].append(descriptor(sid, files[sid], 'PROVIDER_CAPTURE'))
    value['capture'] = {'files': mapping, 'execution': EX}
    value['events'] = []; value['entities'] = []
    for record in value['records']:
        record['disposition'] = 'UNRESOLVED'
    report = c.build(value, files)
    assert calls == ['activity', 'reports']
    assert all(item['selected_set_total'] is None and item['observed_subset'] is None
               and 'PROVIDER_ACTIVITY_UNAVAILABLE' in item['blockers'] for item in report['counts'].values())
    assert report['authority']['network_requests'] == 0


def test_cli_pinned_input_is_create_only(tmp_path):
    value, files = sample(); input_path = tmp_path / 'input.json'; raw = json.dumps(value).encode()
    input_path.write_bytes(raw); source_path = tmp_path / 'synthetic.json'; source_path.write_bytes(files['s'])
    out = tmp_path / 'output'
    args = [sys.executable, '-m', 'decision_kernel.runtime.reviewed_activity_census', str(input_path),
            '--sha256', state.sha256(raw), '--source', 's=' + str(source_path), '--output', str(out)]
    first = subprocess.run(args, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    assert set(before) == {'census.json', 'census.md'}
    assert json.loads(before['census.json']) == c.build(value, files)
    assert subprocess.run(args, capture_output=True, text=True).returncode != 0
    assert before == {p.name: p.read_bytes() for p in out.iterdir()}
    args[args.index('--sha256') + 1] = '0' * 64
    args[-1] = str(tmp_path / 'wrong-pin')
    assert subprocess.run(args, capture_output=True, text=True).returncode != 0
    assert not (tmp_path / 'wrong-pin').exists()


def test_repeated_original_event_identity_cannot_be_split_into_two_events():
    value, files = sample(); rows = json.loads(files['s'])
    rows['r2']['event_id'] = rows['r1']['event_id']; replace_rows(value, files, rows)
    value['events'][1]['identity']['binding']['value'] = rows['r1']['event_id']
    with pytest.raises(ValueError, match='event identity has multiple event keys'): c.build(value, files)


def test_reviewed_person_equivalence_requires_bound_non_name_discriminator():
    value, files = sample(); person = value['entities'][1]
    person.update(identity_basis='REVIEWED_EQUIVALENCE', identity_value='reviewed-alice')
    for event in value['events']:
        edge = next(e for e in event['attendance'] if e['entity_id'] == 'alice')
        edge['identity_evidence'] = [deepcopy(edge['provider_id'])]
    assert c.build(value, files)['counts']['distinct_participants']['selected_set_total'] == 2
    for event in value['events']:
        edge = next(e for e in event['attendance'] if e['entity_id'] == 'alice')
        edge['identity_evidence'] = [deepcopy(edge['name'])]
    with pytest.raises(ValueError, match='only a name'): c.build(value, files)


def test_unresolved_person_identity_is_unknown_not_a_new_unique_person():
    value, files = sample(); value['entities'][1]['identity_qualification'] = 'UNRESOLVED'
    counts = c.build(value, files)['counts']
    assert counts['events']['selected_set_total'] == 2
    assert counts['distinct_institutions']['selected_set_total'] == 1
    assert counts['distinct_participants']['selected_set_total'] is None
    assert counts['distinct_participants']['observed_subset'] == 1
    assert counts['participant_event_attendances']['observed_subset'] == 1
    assert 'e1:IDENTITY_UNRESOLVED' in counts['distinct_participants']['blockers']


def test_missing_source_bytes_preserve_unknown_without_crashing():
    value, files = sample(); report = c.build(value, {})
    assert report['source_gaps'] == ['s']
    assert all(item['observed_subset'] is None and item['selected_set_total'] is None
               for item in report['counts'].values())
    assert all(event['blockers'] == ['EVENT_SOURCE_BYTES_UNAVAILABLE'] for event in report['events'])


def excluded_record(value, files):
    rows = json.loads(files['s']); rows['outside'] = {'event_date': '2026-08-31', 'label': 'Synthetic outside event'}
    replace_rows(value, files, rows)
    value['records'].append({'id': 'outside', 'source_id': 's', 'kind': 'RETAINED_REFERENCE',
        'locator': {'pointer': '/outside'}, 'disposition': 'EXCLUDED',
        'review_note': 'Synthetic record falls outside the requested event-date window',
        'exclusion': {'reason': 'OUTSIDE_WINDOW', 'basis': 'EVENT_DATE',
                      'date': {'value': '2026-08-31', 'locator': {'pointer': '/outside/event_date'}},
                      'note': 'Explicit original date precedes selected window'}})


def test_only_bound_outside_window_record_can_be_excluded():
    value, files = sample(); excluded_record(value, files)
    report = c.build(value, files)
    assert report['counts']['events']['selected_set_total'] == 2
    assert report['records'][-1]['status'] == 'EXCLUDED'


@pytest.mark.parametrize('mutation', ['wrong_basis', 'unbound_date', 'wrong_reason', 'in_window'])
def test_exclusion_cannot_hide_unresolved_or_in_window_evidence(mutation):
    value, files = sample(); excluded_record(value, files); exclusion = value['records'][-1]['exclusion']
    if mutation == 'wrong_basis': exclusion['basis'] = 'DISCLOSURE_DATE'
    elif mutation == 'unbound_date': exclusion['date']['locator']['pointer'] = '/r1/event_date'
    elif mutation == 'wrong_reason': exclusion['reason'] = 'UNRESOLVED'
    else:
        rows = json.loads(files['s']); rows['outside']['event_date'] = '2026-09-02'
        replace_rows(value, files, rows); exclusion['date']['value'] = '2026-09-02'
    with pytest.raises(ValueError): c.build(value, files)


def test_successful_synthetic_provider_rows_replay_with_integer_fields(tmp_path):
    value, files = sample(); rows = list(json.loads(files['s']).values())
    for index, row in enumerate(rows):
        row.update(SECUCODE='002436.SZ', SECURITY_CODE='002436',
            NOTICE_DATE='2026-09-03 00:00:00', RECEIVE_START_DATE=row['event_date'] + ' 00:00:00',
            RECEIVE_OBJECT='Synthetic Firm', INVESTIGATORS='Synthetic Alice',
            RECEIVE_WAY_EXPLAIN='Synthetic meeting', RAW_INTEGER_FIELD=index + 1)
    root = tmp_path / 'synthetic-provider'
    def transport(spec, selected_scope):
        assert selected_scope == raw_context.scope('002436.SZ', '2026-09-01', '2026-09-03')
        if spec['family'] == 'activity':
            return 200, raw_context.encoded({'success': True, 'result': {'data': rows, 'count': 2, 'pages': 1}})
        return 200, raw_context.encoded({'data': [], 'hits': 0, 'TotalPage': 1})
    raw_context.capture(root, raw_context.scope('002436.SZ', '2026-09-01', '2026-09-03'), EX,
        transport=transport, clock=lambda: '2026-09-04T00:00:00+00:00')
    files = {}; value['sources'] = []; mapping = {}
    for name in ('capture.json', 'activity.body', 'reports.body'):
        sid = name.replace('.', '-')
        files[sid] = (root / name).read_bytes(); mapping[name] = sid
        value['sources'].append(descriptor(sid, files[sid], 'PROVIDER_CAPTURE'))
    value['capture'] = {'files': mapping, 'execution': EX}
    for index, record in enumerate(value['records']):
        record.update(source_id=mapping['activity.body'], kind='PROVIDER_ACTIVITY_ROW',
                      locator={'pointer': '/result/data/' + str(index)})
    def repoint(item):
        if isinstance(item, dict):
            if 'pointer' in item:
                for index in (1, 2):
                    item['pointer'] = item['pointer'].replace('/r' + str(index) + '/', '/result/data/' + str(index - 1) + '/')
            for child in item.values(): repoint(child)
        elif isinstance(item, list):
            for child in item: repoint(child)
    repoint(value['events'])
    report = c.build(value, files)
    assert report['counts']['events']['selected_set_total'] == 2
    assert report['counts']['participant_event_attendances']['selected_set_total'] == 3
    assert report['capture'] == value['capture']
    assert all(s['qualification'] == 'PROVIDER_CAPTURE' for s in report['sources'])
    files[mapping['activity.body']] += b' '
    with pytest.raises(ValueError, match='source byte identity differs'): c.build(value, files)


def test_missing_one_source_preserves_unrelated_observed_subset():
    value, files = sample(); rows = json.loads(files['s'])
    missing_raw = json.dumps({'r1': rows['r1']}).encode()
    value['sources'].append(descriptor('missing', missing_raw))
    value['records'][0]['source_id'] = 'missing'
    counts = c.build(value, files)['counts']
    assert counts['events']['observed_subset'] == 1
    assert counts['distinct_participants']['observed_subset'] == 2
    assert counts['participant_event_attendances']['observed_subset'] == 2
    assert all(item['selected_set_total'] is None for item in counts.values())


def test_fact_cannot_name_another_events_record_even_with_matching_value():
    value, files = sample(); edge = value['events'][0]['attendance'][0]
    edge['name'] = deepcopy(value['events'][1]['attendance'][0]['name'])
    with pytest.raises(ValueError, match='fact belongs to another event'): c.build(value, files)


def test_original_timestamp_is_normalized_but_window_basis_remains_explicit():
    value, files = sample(); rows = json.loads(files['s'])
    rows['r1']['event_date'] = '2026-08-31 00:00:00'; replace_rows(value, files, rows)
    value['events'][0]['event_date']['binding']['value'] = rows['r1']['event_date']
    event_counts = c.build(value, files)['counts']['events']
    assert event_counts['observed_subset'] == 1 and event_counts['selected_set_total'] is None
    assert 'e1:OUTSIDE_SELECTED_WINDOW' in event_counts['blockers']
    value['scope']['basis'] = 'DISCLOSURE_DATE'
    report = c.build(value, files)
    assert report['events'][0]['event_date'] == '2026-08-31'
    assert report['counts']['events']['selected_set_total'] == 2


def test_unassigned_selected_record_keeps_selected_total_unknown():
    value, files = sample(); value['events'].pop()
    counts = c.build(value, files)['counts']
    assert counts['events']['observed_subset'] == 1
    assert all(item['selected_set_total'] is None and
               'SELECTED_RECORDS_WITHOUT_RESOLVED_EVENT' in item['blockers'] for item in counts.values())


def test_render_escapes_review_text_without_promoting_authority():
    value, files = sample(); value['limitations'] = '<script>synthetic only</script> | not instructions'
    report = c.build(value, files); rendered = c.render(report)
    assert '<script>' not in rendered and '&lt;script&gt;' in rendered and '&#124;' in rendered
    value['authority']['investment_authority'] = 'BUY'
    with pytest.raises(ValueError, match='contract differs'): c.build(value, files)


def test_explicit_source_host_cannot_be_reclassified_as_visitor():
    value, files = sample()
    host = next(edge for edge in value['events'][0]['attendance'] if edge['entity_id'] == 'host')
    host['role'] = 'VISITOR'
    with pytest.raises(ValueError, match='explicit source role differs'): c.build(value, files)


def test_reviewed_person_identity_discriminator_cannot_be_a_role():
    value, files = sample(); value['entities'][1]['identity_basis'] = 'REVIEWED_EQUIVALENCE'
    for event in value['events']:
        edge = next(edge for edge in event['attendance'] if edge['entity_id'] == 'alice')
        edge['identity_evidence'] = [deepcopy(edge['role_evidence'])]
    with pytest.raises(ValueError, match='name|role'): c.build(value, files)


@pytest.mark.parametrize('case,sources', [
    ('provider-failure', {'capture': 'provider-capture.json', 'activity': 'provider-activity.body',
                          'reports': 'provider-reports.body'}),
    ('ir-reference', {'ir': 'ir-reconciliation.md'}),
])
def test_real_retained_boundary_artifacts_replay_without_claiming_positive_census(case, sources):
    """Real retained failure/reference evidence; never a complete issuer census."""
    root = Path(__file__).resolve().parents[1] / 'docs/readings/c-reviewed-activity-boundaries-2026-09-30'
    value = json.loads((root / (case + '-input.json')).read_bytes())
    files = {sid: (root / name).read_bytes() for sid, name in sources.items()}
    report = c.build(value, files)
    assert report == json.loads((root / (case + '-report.json')).read_bytes())
    assert c.render(report).encode() == (root / (case + '-report.md')).read_bytes()
    assert report['report_hash'] == canonical_hash({k: v for k, v in report.items() if k != 'report_hash'})
    assert all(item['issuer_window_total'] is None for item in report['counts'].values())
    if case == 'provider-failure':
        assert all(item['selected_set_total'] is None and item['observed_subset'] is None
                   for item in report['counts'].values())
    else:
        assert report['counts']['events']['selected_set_total'] == 1
        assert all(report['counts'][key]['selected_set_total'] is None
                   for key in ('distinct_institutions', 'distinct_participants', 'participant_event_attendances'))


def test_unresolved_host_identity_does_not_block_visiting_population():
    value, files = sample()
    expected = c.build(value, files)['counts']
    next(entity for entity in value['entities'] if entity['id'] == 'host')['identity_qualification'] = 'UNRESOLVED'
    assert c.build(value, files)['counts'] == expected
