"""Optional saved supplement in the existing company reader; no source execution."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import tempfile

from decision_kernel.identity import canonical_hash
from . import current_state as model
from . import concept_detail_capture as capture
from . import concept_detail_compat as compat
from . import concept_detail_supplement as detail
from . import institutional_radar_reading as shared
from . import radar_company_reading as companies

WORKFLOW = '.github/workflows/radar-concept-detail.yml'
QUERY = 'actions/workflows/radar-concept-detail.yml/runs?branch=main&per_page=20'
VERSION = 'radar-company-reading-with-concept-detail-v3'


def read(collector, cutoff, primary):
    collector.detail_read_attempt = None
    collector.detail_read_stage = 'PRIMARY_BINDING'
    model.check(primary.get('status') == 'VERIFIED_SAVED_CONCEPT_SOURCE', 'Detail primary unavailable')
    collector.detail_read_stage = 'BUDGET_PREFLIGHT'
    shared._reserve(collector, calls=5, files=24)
    collector.detail_read_stage = 'RUN_DISCOVERY'
    found = collector.api.get(QUERY); runs = found['workflow_runs']
    model.check(isinstance(runs, list) and len(runs) <= 20 and type(found['total_count']) is int
                and found['total_count'] >= len(runs) and (runs or found['total_count'] == 0)
                and len({r['id'] for r in runs}) == len(runs), 'Detail run query incomplete')
    if not runs:
        return None, None, {'status': 'NO_RETAINED_RUN', 'meaning': 'NOT_ZERO_ACTIVITY_OR_FULL_COVERAGE'}
    selected = max(runs, key=lambda r: (model.clock(r['created_at']), r['id']))
    collector.detail_read_stage = 'RUN_IDENTITY'
    shared._run(selected, cutoff=cutoff, workflow=WORKFLOW)
    collector.detail_read_attempt = model.concise_run(selected)
    run = collector.api.get(f'actions/runs/{selected["id"]}')
    shared._run(run, cutoff=collector.now(), workflow=WORKFLOW)
    model.check(all(run[k] == selected[k] for k in ('id', 'head_sha', 'created_at', 'event', 'run_attempt')),
                'Detail selected run changed')
    status = {'status': 'LATEST_ATTEMPT_NOT_SUCCESSFUL', 'latest_attempt': model.concise_run(run),
              'query_scope': 'LATEST_OF_TWENTY_MAIN_INVOCATIONS_NOT_CUMULATIVE_ALL_BATCHES',
              'meaning': 'NO_OLDER_SUCCESS_FALLBACK; NOT_ZERO_ACTIVITY'}
    if run['status'] != 'completed' or run['conclusion'] != 'success':
        return None, None, status
    collector.detail_read_stage = 'ARCHIVE_FETCH'
    artifact = model.select_artifact(collector.artifacts(run), f'concept-detail-{run["id"]}-1')
    model.check(model.clock(artifact['created_at']) <= model.clock(run['updated_at'])
                and model.clock(collector.now()) < model.clock(artifact['expires_at']), 'Detail artifact clock rejected')
    files, archive = collector.archive(artifact, run)
    payload = {k[8:]: v for k, v in files.items() if k.startswith('payload/')}
    model.check(5 <= len(payload) <= 17 and all(name in {'base.zip', 'source.json', 'plan.json', 'capture.json', 'observation.json'}
                or re.fullmatch(r'(request|response)-[1-6]\.json', name) for name in payload), 'Detail payload scope differs')
    collector.detail_read_stage = 'PRIMARY_BINDING'
    meta = json.loads(payload['source.json']); original = primary['archive']
    model.check(meta['run']['id'] == original['origin_run']['id']
                and meta['run']['head_sha'] == original['origin_run']['head_sha']
                and meta['artifact']['id'] == original['artifact_id']
                and meta['artifact']['digest'] == 'sha256:' + original['sha256']
                and len(payload['base.zip']) == original['bytes']
                and model.sha256(payload['base.zip']) == original['sha256']
                and model.blob_sha(payload['base.zip']) == original['git_blob'], 'Detail belongs to another primary')
    collector.detail_read_stage = 'PAYLOAD_REPLAY'
    receipt = json.loads(payload['capture.json'])
    wf = capture.workflow_identity(receipt['workflow'], run['head_sha'])
    model.check(wf['GITHUB_RUN_ID'] == str(run['id']) and receipt['provenance'] == 'LIVE_HITHINK'
                and receipt['status'] in {capture.COMPLETE, capture.PARTIAL}
                and model.clock(run['created_at']) <= model.clock(receipt['started_at'])
                <= model.clock(receipt['finished_at']) <= model.clock(run['updated_at']), 'Detail capture identity differs')
    # Never unpack or execute artifact TARs. The installed trusted verifier reads data only.
    with tempfile.TemporaryDirectory(prefix='concept-detail-read-') as directory:
        root = Path(directory)
        for name, raw in payload.items(): (root / name).write_bytes(raw)
        replay, replay_mode = compat.verify(root)
    model.check(json.loads(files['verification.json']) == replay, 'Detail origin verification differs')
    report = json.loads(payload['observation.json']); p = report['projection']
    model.check(p['base_projection_hash'] == primary['projection_hash']
                and p['market_session'] == primary['market_session']
                and p['base_observed_at'] == primary['source_observed_at'], 'Detail base projection differs')
    collector.detail_read_stage = 'READ_RETENTION'
    prefix = f'details/concept-detail/{run["id"]}/'
    refs = {name: collector.retain(prefix + name, raw) for name, raw in payload.items()}
    refs['verification.json'] = collector.retain(prefix + 'verification.json', files['verification.json'])
    refs['run.json'] = collector.retain(prefix + 'run.json', model.json_bytes(run))
    status.update(status='VERIFIED_SAVED_CONCEPT_DETAIL', archive=archive, details=refs,
                  capture_status=receipt['status'], market_session=p['market_session'], source_observed_at=p['as_of'],
                  base_projection_hash=p['base_projection_hash'], projection_hash=report['projection_hash'],
                  coverage=p['coverage'], replay=replay, replay_mode=replay_mode,
                  meaning='SEPARATE_SAVED_SUPPLEMENT_NOT_NEW_PRIMARY_OR_RESEARCH; NOT_ALL_BATCHES')
    return report, refs['observation.json'], status


def add_members(company, report, primary, reference, cutoff):
    """Enrich the original composition before its existing Stock/Research join."""
    p, base = report['projection'], primary['projection']
    model.check(reference is not None and p['version'] == detail.VERSION and p['policy'] == detail.POLICY
                and report['projection_hash'] == canonical_hash(p)
                and all(p.get(k) == v for k, v in detail.AUTHORITY.items())
                and p['base_projection_hash'] == primary['projection_hash']
                and p['base_observed_at'] == base['as_of'] and p['market_session'] == base['market_session']
                and model.clock(base['as_of']) <= model.clock(p['started_at']) <= model.clock(p['as_of']) <= cutoff,
                'Detail company source differs')
    codes = [d['thscode'] for d in p['details']]
    missing = sorted(set(r['thscode'] for r in base['concepts']) - set(base['detail_selected_codes']))
    model.check(codes and len(set(codes)) == len(codes) <= detail.MAX_DETAILS and codes[0] in missing,
                'Detail company scope differs')
    selection = detail.plan(primary, offset=missing.index(codes[0]))
    model.check(codes == selection['plan']['selected_codes'] and p['plan_hash'] == selection['plan_hash'],
                'Detail company plan differs')
    names = {r['thscode']: r['name'] for r in base['concepts']}
    expected, additions = {}, []
    for d in p['details']:
        model.check(d['name'] == names[d['thscode']], 'Detail concept name differs')
        membership = d['current_membership']
        if membership is None:
            model.check(d['membership_status'] != 'CURRENT_MEMBERS_CHECKED_NOT_ECONOMIC_EXPOSURE', 'Missing detail members')
            continue
        i = d['membership_request_index']
        model.check(type(i) is int and 0 <= i < len(p['requests']), 'Detail member request missing')
        request = p['requests'][i]
        values = [m['thscode'] for m in membership['members']]
        model.check(values and len(set(values)) == len(values) and membership['sector_thscode'] == d['thscode']
                    and d['membership_status'] == 'CURRENT_MEMBERS_CHECKED_NOT_ECONOMIC_EXPOSURE'
                    and request['path'] == detail.source.probe.MEMBERS and request['params'] == {'thscode': d['thscode']}
                    and model.clock(p['started_at']) <= model.clock(request['requested_at'])
                    <= model.clock(request['received_at']) <= model.clock(p['as_of']), 'Detail member binding differs')
        origin = {'concept_thscode': d['thscode'], 'concept_name': d['name'], 'market_session': p['market_session'],
                  'membership_hash': membership['constituent_set_hash'], 'membership_captured_at': membership['captured_at']}
        for member in membership['members']:
            code, name = member['thscode'], member['name']
            item = expected.setdefault(code, {'thscode': code, 'source_names': [], 'origins': [],
                    'business_linkage': 'NOT_ESTABLISHED', 'pre_quick_execution': 'NOT_EXECUTED'})
            if name not in item['source_names']: item['source_names'].append(name)
            item['origins'].append(deepcopy(origin))
            additions.append((code, name, {**origin, 'kind': 'CONCEPT_CURRENT_MEMBER',
                'acquisition_kind': 'SUPPLEMENTAL_DETAIL', 'membership_request_index': i,
                'history_status': d['history_status'], 'source_observed_at': request['received_at'],
                'source': deepcopy(reference), 'projection_hash': report['projection_hash'],
                'base_projection_hash': p['base_projection_hash'], 'business_linkage': 'NOT_ESTABLISHED',
                'historical_membership': 'NOT_ESTABLISHED', 'publication_time': 'UNKNOWN'}))
    model.check(p['companies'] == [expected[c] for c in sorted(expected)], 'Detail company membership reconstruction differs')
    for code, name, origin in additions: company(code, name)['origins'].append(deepcopy(origin))
    context = {'status': 'SAVED_SUPPLEMENT_AVAILABLE', 'source': deepcopy(reference),
               'market_session': p['market_session'], 'base_observed_at': p['base_observed_at'],
               'source_observed_at': p['as_of'], 'coverage': deepcopy(p['coverage']), 'overlaps': deepcopy(p['overlaps']),
               'details': [{k: deepcopy(d[k]) for k in ('thscode', 'name', 'history_status', 'membership_status', 'path', 'gaps')}
                           for d in p['details']], 'meaning': 'ONE_SEPARATE_BATCH_NOT_COMPLETE_OR_CUMULATIVE_COVERAGE'}
    return set(expected), context


def attach(collector, parent):
    model.validate_read_package(parent)
    reading = parent['research'].get('radar_discovery', {})
    if reading.get('status') not in {'READ_OK', 'READ_OK_WITH_SOURCE_GAPS'}:
        return parent
    before = dict(collector.files), dict(collector.sources), dict(collector.archive_cache)
    statuses = deepcopy(reading['source_status'])
    report = reference = None
    try:
        report, reference, statuses['concept_detail'] = read(collector, collector.now(), statuses.get('concept', {}))
    except shared.ERRORS as exc:
        collector.files, collector.sources, collector.archive_cache = map(dict, before)
        statuses['concept_detail'] = gap(collector, exc)
    try:
        def source(key):
            ref = statuses[key].get('details', {}).get('observation.json')
            return (json.loads(companies.retained_bytes(collector.files, ref)), ref) if ref else (None, None)
        original = json.loads(companies.retained_bytes(collector.files, reading['details']['base_context']))
        primary, primary_ref = source('concept'); institutional, institutional_ref = source('institutional')
        # These are derived replacements, never original capture or base context bytes.
        for key in ('company_reading', 'index'): del collector.files[reading['details'][key]['read_path']]
        return shared._compose(collector, original, deepcopy(original['research']), institutional, institutional_ref,
            statuses, True, primary, primary_ref, include_detail=True, detail_report=report, detail_reference=reference)
    except shared.ERRORS as exc:
        collector.files, collector.sources, collector.archive_cache = map(dict, before)
        research = deepcopy(parent['research']); radar = research['radar_discovery']
        radar['status'] = 'READ_OK_WITH_SOURCE_GAPS'
        radar['source_status']['concept_detail'] = gap(collector, exc, 'COMPANY_COMPOSITION')
        return shared._assemble(collector, parent, research)


def gap(collector, exc, stage=None):
    return {'status': 'UNAVAILABLE_OR_REJECTED', 'error_type': type(exc).__name__,
            'failed_stage': stage or getattr(collector, 'detail_read_stage', 'UNKNOWN'),
            'latest_attempt': getattr(collector, 'detail_read_attempt', None),
            'meaning': 'SUPPLEMENT_GAP_NOT_ZERO_ACTIVITY; ORIGINAL_SOURCES_PRESERVED; NO_OLDER_SUCCESS_FALLBACK'}
