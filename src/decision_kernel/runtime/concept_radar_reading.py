"""Bounded saved concept input for the existing Radar reader; never acquire markets."""
from __future__ import annotations

import json
from pathlib import Path
import re
import tempfile

from . import concept_radar_capture as capture
from . import current_state as model
from . import institutional_radar_reading as shared

WORKFLOW = '.github/workflows/radar-concept-source.yml'
QUERY = 'actions/workflows/radar-concept-source.yml/runs?branch=main&per_page=20'


def read(collector, cutoff):
    collector.concept_read_attempt = None
    collector.concept_read_stage = 'BUDGET_PREFLIGHT'
    # 34 maximum payload files + ZIP + origin verification/run + 3 composition files.
    shared._reserve(collector, calls=5, files=40)
    collector.concept_read_stage = 'RUN_DISCOVERY'
    result = collector.api.get(QUERY)
    runs = result['workflow_runs']
    model.check(isinstance(runs, list) and len(runs) <= 20
                and type(result['total_count']) is int and result['total_count'] >= len(runs)
                and (runs or result['total_count'] == 0), 'Concept run query incomplete')
    model.check(len({r['id'] for r in runs}) == len(runs), 'Duplicate concept run')
    if not runs:
        return None, None, {'status': 'NO_RETAINED_RUN', 'meaning': 'NOT_ZERO_CONCEPT_ACTIVITY'}
    selected = max(runs, key=lambda r: (model.clock(r['created_at']), r['id']))
    collector.concept_read_stage = 'RUN_IDENTITY'
    shared._run(selected, cutoff=cutoff, workflow=WORKFLOW)
    collector.concept_read_attempt = model.concise_run(selected)
    run = collector.api.get(f'actions/runs/{selected["id"]}')
    shared._run(run, cutoff=collector.now(), workflow=WORKFLOW)
    model.check(all(run[k] == selected[k] for k in ('id', 'head_sha', 'created_at', 'event', 'run_attempt')),
                'Concept selected run identity changed')
    status = {'status': 'LATEST_ATTEMPT_NOT_SUCCESSFUL', 'latest_attempt': model.concise_run(run),
              'query_scope': 'NEWEST_TWENTY_MAIN_INVOCATIONS_NOT_ALL_HISTORY',
              'meaning': 'NO_OLDER_SUCCESS_FALLBACK; NOT_ZERO_CONCEPT_ACTIVITY'}
    if run['status'] != 'completed' or run['conclusion'] != 'success':
        return None, None, status
    shared._run(run, cutoff=collector.now(), completed=True, workflow=WORKFLOW)
    collector.concept_read_stage = 'ARCHIVE_FETCH'
    artifact = model.select_artifact(collector.artifacts(run), f'concept-radar-{run["id"]}-1')
    files, archive = collector.archive(artifact, run)
    payload = {k.removeprefix('payload/'): v for k, v in files.items() if k.startswith('payload/')}
    model.check(4 <= len(payload) <= 34 and all(name in {'capture.json', 'plan.json', 'index.html', 'observation.json'}
                or re.fullmatch(r'(request|response)-(?:[1-9]|1[0-5])\.json', name) for name in payload),
                'Concept payload scope differs')
    collector.concept_read_stage = 'PAYLOAD_REPLAY'
    receipt = json.loads(payload['capture.json'])
    wf = capture.workflow_identity(receipt['workflow'], run['head_sha'])
    model.check(wf['GITHUB_RUN_ID'] == str(run['id']) and receipt['provenance'] == 'LIVE_HITHINK'
                and receipt['status'] in {capture.COMPLETE, capture.PARTIAL}
                and model.clock(run['created_at']) <= model.clock(receipt['started_at'])
                <= model.clock(receipt['finished_at']) <= model.clock(run['updated_at']),
                'Concept capture provenance or clock differs')
    # Artifact TAR/scripts are NEVER executed. Only trusted installed verifier code.
    with tempfile.TemporaryDirectory(prefix='concept-read-') as directory:
        root = Path(directory)
        for name, raw in payload.items():
            (root / name).write_bytes(raw)
        replay = capture.verify(root)
    model.check(json.loads(files['verification.json']) == replay, 'Concept origin verification differs')
    report = json.loads(payload['observation.json'])
    collector.concept_read_stage = 'READ_RETENTION'
    path = f'details/concept/{run["id"]}/'
    details = {name: collector.retain(path + name, raw) for name, raw in payload.items()}
    details['verification.json'] = collector.retain(path + 'verification.json', files['verification.json'])
    details['run.json'] = collector.retain(path + 'run.json', model.json_bytes(run))
    status.update(status='VERIFIED_SAVED_CONCEPT_SOURCE', archive=archive, details=details,
                  capture_status=receipt['status'], market_session=report['projection']['market_session'],
                  source_observed_at=report['projection']['as_of'], projection_hash=report['projection_hash'],
                  coverage=report['projection']['coverage'], replay=replay,
                  meaning='ORIGINAL_BYTES_REBUILT; NOT_NEW_ACQUISITION_OR_COMPLETE_TRENDS_OR_RESEARCH')
    return report, details['observation.json'], status
