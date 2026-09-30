"""Offline census of reviewed event/entity assignments over a selected evidence set.

Raw institutional capture/replay retains its original ownership and unknowns.
Reviewer keys, equivalence, roles and completeness are declarations, not truths
certified by a byte hash. Selected-set totals never become issuer-window totals.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime
from html import escape
import json
from pathlib import Path
import re

from ..identity import canonical_hash, canonical_json
from . import current_state as state
from . import institutional_context as raw_context
from .research_comparison import clock, require, selected, _forecast_member
from .research_commit_only import _json, _read, _write, _publish_report_files

VERSION = 'reviewed-activity-census-v0'
AUTHORITY = {'investment_authority': 'NONE', 'human_acceptance': 'NOT_ESTABLISHED',
             'network_requests': 0, 'model_calls': 0, 'research_committed': False}


def meaningful(value):
    require(isinstance(value, str) and 0 < len(value) <= 8000 and value.strip()
            and value.strip().upper() not in {'UNKNOWN', 'NONE', 'N/A', 'NOT_ESTABLISHED'},
            'substantive reviewed text required')
    return value


def day(value):
    require(isinstance(value, str) and date.fromisoformat(value).isoformat() == value,
            'canonical date required')
    return date.fromisoformat(value)


def identified(rows, maximum):
    require(isinstance(rows, list) and len(rows) <= maximum, 'bounded inventory required')
    keys = [meaningful(row['id']) for row in rows]
    require(len(set(keys)) == len(keys), 'duplicate identity')
    return {row['id']: row for row in rows}


def _sources(value, files):
    sources = identified(value['sources'], 16)
    require(sources and set(files) <= set(sources), 'source inventory differs')
    verified, missing = {}, []
    review = datetime.fromisoformat(value['reviewed_at'].replace('Z', '+00:00'))
    for sid, source in sources.items():
        require(source['subject'] == value['subject'], 'source issuer differs')
        require(re.fullmatch('[a-f0-9]{40}', source['ref']) and
                re.fullmatch('[a-f0-9]{40}', source['git_blob']) and
                re.fullmatch('[a-f0-9]{64}', source['sha256']), 'immutable source identity required')
        state.safe_path(source['path'])
        require(type(source['bytes']) is int and 0 <= source['bytes'] <= 512 * 1024,
                'source byte bound')
        require(source['qualification'] in {'RETAINED_RESEARCH', 'PROVIDER_CAPTURE',
                'ISSUER_DISCLOSURE_BYTES', 'SYNTHETIC_FIXTURE'}, 'source qualification required')
        for name in ('published_at', 'acquired_at'):
            clock(source[name])
            require(source[name] is None or
                    datetime.fromisoformat(source[name].replace('Z', '+00:00')) <= review,
                    'source clock after review')
        if sid not in files:
            missing.append(sid)
            continue
        data = files[sid]
        require(isinstance(data, bytes) and len(data) == source['bytes'] and
                state.blob_sha(data) == source['git_blob'] and
                state.sha256(data) == source['sha256'], 'source byte identity differs')
        verified[sid] = data
    return sources, verified, missing


def _capture(value, verified):
    """Use the existing complete capture checker, never a new envelope parser."""
    declaration = value.get('capture')
    if declaration is None:
        return None, []
    require(set(declaration) == {'files', 'execution'}, 'capture declaration differs')
    mapping = declaration['files']
    require(isinstance(mapping, dict) and 'capture.json' in mapping and
            set(mapping) <= {'capture.json', 'activity.body', 'reports.body'},
            'capture file inventory differs')
    require(len(set(mapping.values())) == len(mapping), 'capture file alias')
    require(set(mapping.values()) <= {s['id'] for s in value['sources']},
            'capture references an undeclared source')
    if any(sid not in verified for sid in mapping.values()):
        return None, ['CAPTURE_BYTES_UNAVAILABLE']
    files = {name: verified[sid] for name, sid in mapping.items()}
    saved = raw_context.common.decode(files['capture.json'])
    require(raw_context.common.clock(saved['finished_at']) <=
            datetime.fromisoformat(value['reviewed_at'].replace('Z', '+00:00')),
            'capture completed after review')
    payload = raw_context.project(saved,
                                  files, declaration['execution'])['projection']
    require(payload['scope']['ticker'] == value['subject'], 'capture issuer differs')
    return payload, []


def _bound(binding, record, raw):
    """Literal fact inside its selected record, with no cross-row borrowing."""
    require(set(binding) == {'value', 'locator'}, 'literal binding fields differ')
    expected = meaningful(binding['value'])
    locator = binding['locator']
    root = record['locator']
    if 'pointer' in root:
        require(set(locator) == {'pointer'} and
                _forecast_member(selected(raw, root), root['pointer'], locator['pointer']),
                'binding outside selected record')
        found = selected(raw, locator)
        require(isinstance(found, str) and found == expected, 'bound value differs')
    else:
        require(set(locator) == {'quote'} and locator['quote'] and
                locator['quote'] in root['quote'] and expected in locator['quote'],
                'binding outside selected quotation')
        selected(raw, locator)
    return expected


def build(value, source_files):
    require(value['version'] == VERSION and value['authority'] == AUTHORITY, 'contract differs')
    require(re.fullmatch(r'\d{6}\.(SH|SZ|BJ)', value['subject']), 'issuer required')
    require(len(canonical_json(value).encode()) <= 512 * 1024, 'input byte bound')
    meaningful(value['question']); meaningful(value['limitations'])
    clock(value['reviewed_at']); require(value['reviewed_at'] is not None, 'review clock required')
    scope = value['scope']
    require(scope['basis'] in {'EVENT_DATE', 'DISCLOSURE_DATE'} and
            scope['coverage'] == 'SELECTED_EVIDENCE_ONLY', 'selected-set scope required')
    begin, end = day(scope['begin']), day(scope['end'])
    require(begin <= end <= datetime.fromisoformat(value['reviewed_at'].replace('Z', '+00:00')).date(),
            'window after review or reversed')
    require(type(scope['inventory_complete']) is bool, 'explicit inventory completeness required')
    meaningful(scope['selection_note'])
    sources, verified, missing = _sources(value, source_files)
    capture, blockers = _capture(value, verified)
    records = identified(value['records'], 128)
    events = identified(value['events'], 64)
    entities = identified(value['entities'], 128)
    require(records, 'explicit record inventory required')
    usable, record_results, provider_hashes = {}, [], set()
    for rid, record in records.items():
        require(record['source_id'] in sources, 'unknown record source')
        require(record['kind'] in {'PROVIDER_ACTIVITY_ROW', 'RETAINED_REFERENCE', 'UNAVAILABLE'},
                'record kind differs')
        require(record['disposition'] in {'SELECTED', 'SUPERSEDED', 'EXCLUDED', 'UNRESOLVED', 'UNAVAILABLE'},
                'record disposition differs')
        meaningful(record['review_note'])
        sid = record['source_id']
        if sid not in verified:
            blockers.append('SOURCE_BYTES_UNAVAILABLE:' + rid)
            record_results.append({'id': rid, 'status': 'SOURCE_BYTES_UNAVAILABLE', 'reviewed': deepcopy(record)})
            continue
        found = selected(verified[sid], record['locator'])
        if isinstance(found, dict):
            require(all(not isinstance(v, dict) and (not isinstance(v, list) or
                    all(not isinstance(x, (dict, list)) for x in v)) for v in found.values()),
                    'flat source record required, not a container of events')
        if record['kind'] == 'PROVIDER_ACTIVITY_ROW':
            require(set(record['locator']) == {'pointer'} and isinstance(found, dict),
                    'provider row object required')
            require(value.get('capture') is not None and sid == value['capture']['files'].get('activity.body'),
                    'provider row requires replayed activity capture')
            if capture is None:
                blockers.append('CAPTURE_BYTES_UNAVAILABLE:' + rid)
                record_results.append({'id': rid, 'status': 'CAPTURE_BYTES_UNAVAILABLE', 'reviewed': deepcopy(record)})
                continue
            pointer = record['locator']['pointer']
            require(re.fullmatch(r'/result/data/(0|[1-9][0-9]*)', pointer), 'exact provider row locator required')
            row_index = int(pointer.rsplit('/', 1)[1])
            candidates = capture['families']['activity']['records']
            matches = [row for row in candidates if any(loc['row_index'] == row_index
                       for loc in row['source_locations'])]
            require(len(matches) == 1, 'unqualified provider row')
            # Preserve normalize/common.decode numeric semantics. selected() uses
            # Decimal lexemes for monetary facts and is not the raw row hasher.
            digest = matches[0]['record_hash']
            provider_hashes.add(digest)
        elif record['kind'] == 'RETAINED_REFERENCE':
            require(sources[sid]['qualification'] != 'PROVIDER_CAPTURE',
                    'provider source must use replayed provider-row qualification')
            require(set(record['locator']) in ({'quote'}, {'pointer'}) and
                    isinstance(found, (str, dict)), 'reference record required')
        else:
            require(record['disposition'] == 'UNAVAILABLE', 'unavailable source cannot yield events')
        if record['disposition'] in {'UNAVAILABLE', 'UNRESOLVED'}:
            blockers.append(record['disposition'] + ':' + rid)
        elif record['disposition'] == 'EXCLUDED':
            exclusion = record['exclusion']
            require(exclusion['reason'] == 'OUTSIDE_WINDOW' and exclusion['basis'] == scope['basis'],
                    'exclusion must use the selected window basis')
            excluded_date = raw_context.publication(_bound(exclusion['date'], record, verified[sid]))
            require(not begin <= excluded_date <= end, 'in-window record cannot be excluded')
            meaningful(exclusion['note'])
        elif record['disposition'] == 'SUPERSEDED':
            successor = record['successor']
            require(successor in records and records[successor]['disposition'] == 'SELECTED'
                    and successor != rid and record['event_assignment'] ==
                    records[successor]['event_assignment'], 'explicit same-event selected successor required')
            meaningful(record['event_assignment']); meaningful(record['variant'])
            meaningful(record['correction_note'])
        else:
            require(record['kind'] != 'UNAVAILABLE', 'unavailable selected record')
            meaningful(record['event_assignment']); meaningful(record['variant'])
            usable[rid] = record
        record_results.append({'id': rid, 'status': record['disposition'],
                               'selected_content_hash': canonical_hash(found), 'reviewed': deepcopy(record)})
    if capture is not None:
        activity = capture['families']['activity']
        if activity['status'] not in {'CONTEXT_READY', 'EMPTY_RETURN_NOT_PROOF_OF_NO_ACTIVITY'}:
            blockers.append('PROVIDER_ACTIVITY_UNAVAILABLE')
        require(provider_hashes == {row['record_hash'] for row in activity['records']},
                'replayed activity record inventory differs')
    if not scope['inventory_complete']:
        blockers.append('SELECTED_RECORD_INVENTORY_PARTIAL')
    if missing:
        blockers.append('SOURCE_INVENTORY_INCOMPLETE')
    entity_identities = set()
    for entity in entities.values():
        require(entity['kind'] in {'INSTITUTION', 'PERSON'}, 'entity kind differs')
        require(entity['identity_basis'] in {'PROVIDER_ID', 'REVIEWED_EQUIVALENCE'},
                'explicit entity equivalence required, never names alone')
        require(entity['identity_qualification'] in {'REVIEWED_RESOLVED', 'UNRESOLVED'},
                'explicit identity qualification required')
        meaningful(entity['namespace'])
        if entity['identity_qualification'] == 'REVIEWED_RESOLVED':
            meaningful(entity['identity_value'])
            identity = (entity['kind'], entity['namespace'], entity['identity_value'])
            require(identity not in entity_identities, 'one reviewed identity has multiple entity keys')
            entity_identities.add(identity)
        meaningful(entity['equivalence_note'])
        require(isinstance(entity['names'], list) and 1 <= len(entity['names']) <= 16,
                'bounded explicit aliases required')
        for name in entity['names']: meaningful(name)
    used_records, event_results, attending, active_entities = set(), [], set(), set()
    event_identities = set()
    roster_blockers = {'INSTITUTION': [], 'PERSON': []}
    for eid, event in events.items():
        members = event['records']
        require(isinstance(members, list) and members and len(set(members)) == len(members)
                and set(members) <= set(records) and
                all(records[r]['disposition'] == 'SELECTED' for r in members),
                'event needs selected source records')
        require(not used_records.intersection(members), 'record assigned to multiple events')
        used_records.update(members)
        if not set(members) <= set(usable):
            blockers.append(eid + ':EVENT_SOURCE_BYTES_UNAVAILABLE')
            event_results.append({'id': eid, 'source_records': members,
                                  'blockers': ['EVENT_SOURCE_BYTES_UNAVAILABLE'], 'reviewed': deepcopy(event)})
            continue
        meaningful(event['selected_variant'])
        require(all(usable[r]['event_assignment'] == eid and
                    usable[r]['variant'] == event['selected_variant'] for r in members),
                'event or selected roster variant differs')
        meaningful(event['equivalence_note'])
        require(event['identity_basis'] in {'ORIGINAL_EVENT_ID', 'REVIEWED_EVENT_EQUIVALENCE'},
                'event identity is not inferred from date')
        def fact(item):
            require(item['record_id'] in members, 'fact belongs to another event')
            record = usable[item['record_id']]
            return _bound(item['binding'], record, verified[record['source_id']])
        event_identity = fact(event['identity'])
        meaningful(event['identity_namespace'])
        original_key = (event['identity_namespace'], event_identity)
        require(original_key not in event_identities, 'one reviewed event identity has multiple event keys')
        event_identities.add(original_key)
        event_date = str(raw_context.publication(fact(event['event_date']))) if event['event_date'] is not None else None
        disclosure = str(raw_context.publication(fact(event['disclosure_date']))) if event['disclosure_date'] is not None else None
        if event_date is not None: day(event_date)
        if disclosure is not None: day(disclosure)
        require(event_date is None or disclosure is None or event_date <= disclosure,
                'event after disclosure')
        review_day = datetime.fromisoformat(value['reviewed_at'].replace('Z', '+00:00')).date()
        require(all(d is None or day(d) <= review_day for d in (event_date, disclosure)),
                'event or disclosure date after review')
        observed = event_date if scope['basis'] == 'EVENT_DATE' else disclosure
        event_blocks = []
        if observed is None:
            event_blocks.append('SELECTED_WINDOW_DATE_UNKNOWN')
        elif not begin <= day(observed) <= end:
            event_blocks.append('OUTSIDE_SELECTED_WINDOW')
        require(type(event['variant_resolved']) is bool, 'variant resolution required')
        if not event['variant_resolved']: event_blocks.append('EVENT_VARIANTS_UNRESOLVED')
        meaningful(event['variant_note'])
        roster = event['roster']
        require(set(roster) == {'INSTITUTION', 'PERSON'}, 'separate roster completeness required')
        require(all(v in {'COMPLETE', 'PARTIAL', 'UNKNOWN'} for v in roster.values()),
                'explicit roster completeness required')
        require(set(event['roster_evidence']) == set(roster) and set(event['roster_note']) == set(roster),
                'separate completeness evidence required')
        for kind, status in roster.items():
            meaningful(event['roster_note'][kind])
            if status == 'COMPLETE': fact(event['roster_evidence'][kind])
        edges = event['attendance']
        require(isinstance(edges, list) and len(edges) <= 128, 'bounded attendance required')
        seen_edges = set()
        for edge in edges:
            entity_id = edge['entity_id']
            require(entity_id in entities and entity_id not in seen_edges, 'duplicate or unknown attendee')
            seen_edges.add(entity_id)
            entity = entities[entity_id]
            require(fact(edge['name']) in entity['names'], 'attendee name not in reviewed identity')
            resolved = entity['identity_qualification'] == 'REVIEWED_RESOLVED'
            if resolved and entity['identity_basis'] == 'PROVIDER_ID':
                require(fact(edge['provider_id']) == entity['identity_value'], 'provider identity differs')
            elif resolved and entity['kind'] == 'PERSON':
                evidence = edge['identity_evidence']
                require(isinstance(evidence, list) and 1 <= len(evidence) <= 8,
                        'person equivalence requires discriminating evidence, not name alone')
                values = [fact(item) for item in evidence]
                require(any(v not in entity['names'] and v not in {'VISITOR', 'HOST', 'UNKNOWN'}
                            for v in values),
                        'person identity evidence is only a name')
            require(edge['role'] in {'VISITOR', 'HOST', 'UNKNOWN'}, 'attendance role required')
            role_evidence = fact(edge['role_evidence']); meaningful(edge['role_note'])
            require(role_evidence not in {'VISITOR', 'HOST', 'UNKNOWN'} or
                    edge['role'] in {role_evidence, 'UNKNOWN'}, 'explicit source role differs')
            if not resolved and edge['role'] != 'HOST':
                roster_blockers[entity['kind']].append(eid + ':IDENTITY_UNRESOLVED')
            if edge['role'] == 'UNKNOWN': roster_blockers[entity['kind']].append(eid + ':ROLE_UNKNOWN')
            elif edge['role'] == 'VISITOR' and resolved and not event_blocks:
                attending.add((eid, entity_id)); active_entities.add(entity_id)
        for kind, status in roster.items():
            if status != 'COMPLETE': roster_blockers[kind].append(eid + ':' + status)
        blockers.extend(eid + ':' + reason for reason in event_blocks)
        event_results.append({'id': eid, 'source_records': members, 'identity': event_identity,
            'event_date': event_date, 'disclosure_date': disclosure, 'blockers': event_blocks,
            'roster': deepcopy(roster), 'attendance': deepcopy(edges), 'reviewed': deepcopy(event)})
    if set(usable) - used_records:
        blockers.append('SELECTED_RECORDS_WITHOUT_RESOLVED_EVENT')
    event_ids = {e['id'] for e in event_results if not e['blockers']}
    counts = {}
    metrics = {'events': len(event_ids),
        'distinct_institutions': sum(entities[x]['kind'] == 'INSTITUTION' for x in active_entities),
        'distinct_participants': sum(entities[x]['kind'] == 'PERSON' for x in active_entities),
        'participant_event_attendances': sum(entities[x]['kind'] == 'PERSON' for _, x in attending)}
    for name, observed in metrics.items():
        reasons = list(blockers)
        if name != 'events':
            reasons += roster_blockers['INSTITUTION' if name == 'distinct_institutions' else 'PERSON']
        counts[name] = {'observed_subset': observed if event_ids or not reasons else None,
            'selected_set_total': None if reasons else observed,
            'qualification': 'REVIEWED_SELECTED_SET_ONLY' if not reasons else 'TOTAL_UNKNOWN',
            'blockers': sorted(set(reasons)), 'issuer_window_total': None}
    report = {'version': VERSION, 'subject': value['subject'], 'input_hash': canonical_hash(value),
        'question': value['question'], 'capture': deepcopy(value.get('capture')),
        'reviewed_at': value['reviewed_at'], 'scope': deepcopy(scope), 'sources': deepcopy(value['sources']),
        'source_gaps': missing, 'records': record_results, 'events': event_results,
        'entities': deepcopy(value['entities']), 'counts': counts,
        'historical_availability': 'NOT_ESTABLISHED_BY_RETRIEVAL',
        'qualification': 'REVIEWED_ASSIGNMENTS_NOT_AUTOMATIC_IDENTITY_OR_ECONOMIC_TRUTH',
        'limitations': value['limitations'], 'authority': deepcopy(AUTHORITY)}
    report['report_hash'] = canonical_hash(report)
    return report


def render(report):
    def safe(value): return escape(str(value)).replace('|', '&#124;').replace('\n', ' ')
    lines = ['# Reviewed institutional activity census', '', safe(report['subject']), '',
             'Selected evidence only; UNKNOWN is not zero; no issuer-window total or investment authority.', '']
    for name, count in report['counts'].items():
        lines.append(f"- {name}: observed={safe(count['observed_subset'])}; selected total={safe(count['selected_set_total'])}; {safe(count['qualification'])}")
        if count['blockers']: lines.append('  Blockers: ' + safe(', '.join(count['blockers'])))
    lines += ['', safe(report['limitations']), '', 'Report hash: ' + report['report_hash']]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input'); parser.add_argument('--sha256', required=True)
    parser.add_argument('--source', action='append', default=[], metavar='ID=LOCAL_FILE')
    parser.add_argument('--output', required=True)
    args = parser.parse_args(); raw = _read(Path(args.input))
    require(state.sha256(raw) == args.sha256, 'externally pinned input differs')
    files = {}
    for spec in args.source:
        sid, path = spec.split('=', 1)
        require(sid not in files, 'duplicate source argument')
        files[sid] = _read(Path(path))
    report = build(_json(raw), files)
    require(len((canonical_json(report) + '\n').encode()) <= 512 * 1024 and
            len(render(report).encode()) <= 512 * 1024, 'bounded output required')
    _publish_report_files(Path(args.output), {
        'census.json': (canonical_json(report) + '\n').encode(),
        'census.md': render(report).encode(),
    }, write_file=_write)


if __name__ == '__main__':
    main()
