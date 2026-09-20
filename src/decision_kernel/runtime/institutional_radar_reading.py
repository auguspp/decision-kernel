"""Optional institutional source + company reading in the existing publisher.

Only GitHub saved products are read. Original archive bytes are retained in the
same read ref; artifact source code is NEVER executed. Existing budgets win.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import zipfile

from . import current_state as model
from . import current_state_delivery as delivery
from . import institutional_radar_capture as capture
from . import radar_company_reading as companies
from .stock_research_reading import call_limit

WORKFLOW = '.github/workflows/radar-institutional-source.yml'
PREFIX = 'details/radar/'
ERRORS = (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError,
          RuntimeError, OverflowError, zipfile.BadZipFile)


def _reserve(collector, *, calls=0, files=0, replacements=None):
    used = getattr(collector.api, 'calls', None)
    model.check(type(used) is int and used >= 0, 'Radar API accounting unavailable')
    from .read_blob_reuse import pending_blob_writes
    retained = collector.files if replacements is None else {**collector.files, **replacements}
    model.check(used + calls + pending_blob_writes(collector.api, retained) + files + 5 <= call_limit(collector.api),
                'Radar reading cannot consume existing publication reserve')


def _run(run, *, cutoff, completed=False, workflow=WORKFLOW):
    model.check(run.get('repository', {}).get('full_name') == model.REPOSITORY
                and run.get('head_repository', {}).get('full_name') == model.REPOSITORY
                and run.get('path') == workflow and run.get('head_branch') == 'main'
                and run.get('event') == 'workflow_dispatch' and type(run.get('run_attempt')) is int
                and run['run_attempt'] == 1 and model.SHA.fullmatch(run.get('head_sha', '')) is not None
                and type(run.get('id')) is int and run['id'] > 0, 'Institutional run identity differs')
    model.check(model.clock(run['created_at']) <= model.clock(run['updated_at']) <= model.clock(cutoff),
                'Institutional run is future or reversed')
    if completed:
        model.check(run['status'] == 'completed' and run['conclusion'] == 'success',
                    'Institutional latest attempt not successful')


def _institutional(collector, cutoff):
    # Reserve the whole bounded read + its blob publication before any new GET.
    collector.radar_read_attempt = None
    collector.radar_read_stage = 'BUDGET_PREFLIGHT'
    _reserve(collector, calls=5, files=16)
    collector.radar_read_stage = 'RUN_DISCOVERY'
    result = collector.api.get('actions/workflows/radar-institutional-source.yml/runs?branch=main&per_page=20')
    runs = result['workflow_runs']
    model.check(isinstance(runs, list) and len(runs) <= 20 and type(result['total_count']) is int
                and result['total_count'] >= len(runs) and (runs or result['total_count'] == 0),
                'Institutional run query incomplete')
    model.check(len({r['id'] for r in runs}) == len(runs), 'Duplicate institutional run')
    if not runs:
        return None, None, {'status': 'NO_RETAINED_RUN', 'meaning': 'NOT_ZERO_INSTITUTIONAL_ACTIVITY'}
    selected = max(runs, key=lambda r: (model.clock(r['created_at']), r['id']))
    collector.radar_read_stage = 'RUN_IDENTITY'
    _run(selected, cutoff=cutoff)
    collector.radar_read_attempt = model.concise_run(selected)
    # Read the chosen run once. Do not search earlier successes after rejection.
    run = collector.api.get(f'actions/runs/{selected["id"]}')
    _run(run, cutoff=collector.now())
    model.check(all(run[k] == selected[k] for k in ('id', 'head_sha', 'created_at', 'event', 'run_attempt')),
                'Institutional selected run identity changed')
    status = {'status': 'LATEST_ATTEMPT_NOT_SUCCESSFUL', 'latest_attempt': model.concise_run(run),
              'query_scope': 'NEWEST_TWENTY_MAIN_INVOCATIONS_NOT_ALL_HISTORY',
              'meaning': 'NO_FALLBACK_TO_OLDER_SUCCESS_AND_NOT_QUIET'}
    if run['status'] != 'completed' or run['conclusion'] != 'success':
        return None, None, status
    _run(run, cutoff=collector.now(), completed=True)
    collector.radar_read_stage = 'ARCHIVE_FETCH'
    artifact = model.select_artifact(collector.artifacts(run), f'institutional-radar-{run["id"]}-1')
    files, archive = collector.archive(artifact, run)
    expected = {'capture.json', 'plan.json', 'index.html', 'observation.json',
                'request-1.json', 'request-2.json', 'response-1.json', 'response-2.json'}
    payload = {k.removeprefix('payload/'): v for k, v in files.items() if k.startswith('payload/')}
    model.check(set(payload) == expected, 'Institutional successful payload file scope differs')
    collector.radar_read_stage = 'PAYLOAD_REPLAY'
    receipt = json.loads(payload['capture.json'])
    wf = receipt['workflow']
    capture.workflow_identity(wf, run['head_sha'])
    model.check(str(wf['GITHUB_RUN_ID']) == str(run['id']) and receipt['provenance'] == 'LIVE_HITHINK'
                and receipt['status'] == capture.COMPLETE
                and model.clock(run['created_at']) <= model.clock(receipt['started_at'])
                <= model.clock(receipt['finished_at']) <= model.clock(run['updated_at']),
                'Institutional capture provenance or clock differs')
    # Use trusted installed code and exact retained payload; never unpack/run TAR.
    with tempfile.TemporaryDirectory(prefix='institutional-read-') as directory:
        root = Path(directory)
        for name, raw in payload.items():
            (root / name).write_bytes(raw)
        replay = capture.verify(root)
    model.check(json.loads(files['verification.json']) == {k: replay[k] for k in ('status', 'capture_hash')},
                'Institutional original replay receipt differs')
    report = json.loads(payload['observation.json'])
    collector.radar_read_stage = 'READ_RETENTION'
    path = f'details/institutional/{run["id"]}/'
    details = {name: collector.retain(path + name, raw) for name, raw in payload.items()}
    details['verification.json'] = collector.retain(path + 'verification.json', files['verification.json'])
    details['run.json'] = collector.retain(path + 'run.json', model.json_bytes(run))
    status.update(status='VERIFIED_SAVED_INSTITUTIONAL_SOURCE', archive=archive, details=details,
                  market_session=report['projection']['market_session'],
                  source_observed_at=report['projection']['origin']['requests'][-1]['received_at'],
                  projection_hash=report['projection_hash'], replay=replay,
                  meaning='ORIGINAL_BYTES_REBUILT_NOT_EXCHANGE_TRUTH_OR_RESEARCH; NOT_A_NEW_MARKET_SCAN')
    return report, details['observation.json'], status


def attach(collector, baseline):
    model.validate_read_package(baseline)
    before_files, before_sources, before_cache = dict(collector.files), dict(collector.sources), dict(collector.archive_cache)
    research = deepcopy(baseline['research'])
    source_status = {}
    report = reference = None
    try:
        report, reference, source_status['institutional'] = _institutional(collector, collector.now())
    except ERRORS as exc:
        collector.files, collector.sources, collector.archive_cache = dict(before_files), dict(before_sources), dict(before_cache)
        source_status['institutional'] = {'status': 'UNAVAILABLE_OR_REJECTED', 'error_type': type(exc).__name__,
            'failed_stage': getattr(collector, 'radar_read_stage', 'UNKNOWN'),
            'latest_attempt': getattr(collector, 'radar_read_attempt', None),
            'meaning': 'SOURCE_READ_GAP_NOT_ZERO_ACTIVITY; NO_OLDER_SUCCESS_FALLBACK'}
    include_concept = getattr(collector, 'include_concept_discovery', False)
    concept_report = concept_reference = None
    # Rollback point AFTER institutional success: optional concept cannot erase it.
    concept_files, concept_sources, concept_cache = dict(collector.files), dict(collector.sources), dict(collector.archive_cache)
    if include_concept:
        try:
            from .concept_radar_reading import read
            concept_report, concept_reference, source_status['concept'] = read(collector, collector.now())
        except ERRORS as exc:
            collector.files, collector.sources, collector.archive_cache = dict(concept_files), dict(concept_sources), dict(concept_cache)
            source_status['concept'] = _concept_gap(collector, exc)
    try:
        return _compose(collector, baseline, research, report, reference, source_status,
                        include_concept, concept_report, concept_reference)
    except ERRORS as exc:
        if include_concept and concept_report is not None:
            collector.files, collector.sources, collector.archive_cache = dict(concept_files), dict(concept_sources), dict(concept_cache)
            source_status['concept'] = _concept_gap(collector, exc, stage='COMPANY_COMPOSITION')
            try:
                return _compose(collector, baseline, deepcopy(baseline['research']), report, reference,
                                source_status, True, None, None)
            except ERRORS as fallback:
                exc = fallback
        collector.files, collector.sources, collector.archive_cache = before_files, before_sources, before_cache
        research = deepcopy(baseline['research'])
        research['radar_discovery'] = {'status': 'UNAVAILABLE_OR_REJECTED', 'error_type': type(exc).__name__,
            'meaning': 'RADAR_READING_GAP_NOT_QUIET; BASELINE_PRESERVED', **companies.AUTHORITY}
        return _assemble(collector, baseline, research)


def _concept_gap(collector, exc, *, stage=None):
    from .read_blob_reuse import pending_blob_writes
    return {'status': 'UNAVAILABLE_OR_REJECTED', 'error_type': type(exc).__name__,
            'failed_stage': stage or getattr(collector, 'concept_read_stage', 'UNKNOWN'),
            'latest_attempt': getattr(collector, 'concept_read_attempt', None),
            'api_calls_after_attempt': getattr(collector.api, 'calls', None),
            'retained_file_count': len(collector.files),
            'pending_blob_writes': pending_blob_writes(collector.api, collector.files),
            'meaning': 'CONCEPT_READ_GAP_NOT_ZERO; OTHER_SOURCES_PRESERVED; NO_OLDER_SUCCESS_FALLBACK'}


def _compose(collector, baseline, research, report, reference, source_status,
             include_concept, concept_report, concept_reference, *,
             include_detail=False, detail_report=None, detail_reference=None):
    _reserve(collector, files=3)
    sector = baseline['lanes'].get('sector', {})
    product = sector.get('last_qualified_result') or {}
    sector_ref = product.get('details', {}).get('result.json')
    sector_result = None
    source_status['sector'] = {'status': 'NO_READABLE_SAVED_RESULT', 'lane_health': sector.get('health', 'UNKNOWN')}
    if sector_ref:
        sector_result = json.loads(companies.retained_bytes(collector.files, sector_ref))
        model.check(sector_result['market_session'] == product['market_session']
                    and sector_result['output_market_state_hash'] == product['market_state_hash']
                    and sector_result['event_ledger_update']['event_ledger_hash'] == product['event_ledger_hash'], 'Sector saved result binding differs')
        source_status['sector'].update(status='SAVED_SECTOR_RESULT', market_session=product['market_session'],
                                      source=sector_ref)
    built = companies.build(baseline, sector_result=sector_result, sector_source=sector_ref,
        institution_report=report, institution_source=reference, source_status=source_status,
        generated_at=collector.now(), concept_report=concept_report,
        concept_source=concept_reference, include_concept=include_concept, include_detail=include_detail,
        detail_report=detail_report, detail_source=detail_reference)
    context = collector.retain(PREFIX + 'base-context.json', model.json_bytes(baseline))
    detail = collector.retain(PREFIX + 'company-reading.json', model.json_bytes(built))
    page = collector.retain(PREFIX + 'index.html', companies.render(built).encode())
    research['radar_discovery'] = {'status': ('READ_OK' if report is not None and sector_result is not None
            and (not include_concept or (concept_report is not None
                and not concept_report['projection']['coverage']['detail_gaps']))
            and (not include_detail or (detail_report is not None and not detail_report['projection']['coverage']['detail_gaps']))
            else 'READ_OK_WITH_SOURCE_GAPS'),
        'coverage': built['projection']['coverage'], 'source_status': source_status,
        'details': {'base_context': context, 'company_reading': detail, 'index': page},
        'projection_hash': built['projection_hash'], 'meaning': 'COMPANY_DISCOVERY_AND_SAVED_RESEARCH_CONTEXT_NOT_NEW_RESEARCH',
        **companies.AUTHORITY}
    return _assemble(collector, baseline, research)


def _assemble(collector, baseline, research):
    payload = model.assemble(code_commit=collector.code_commit, checked_at=collector.now(),
        check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
        capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
    data = {'current-state.json': model.read_package_bytes(payload), 'README.md': (model.render_summary(payload) + '\n' + companies.navigation(research['radar_discovery'])).encode()}
    model.check(sum(len(v) for k, v in collector.files.items() if k not in data) + sum(map(len, data.values()))
                <= delivery.MAX_RETAINED_OUTPUT, 'Radar reading exceeds existing byte bound')
    _reserve(collector, replacements=data)
    collector.files.update(data)
    return payload
