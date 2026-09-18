"""Manual detail supplement: original source qualification, bounded I/O, replay.

The primary concept capture modules stay byte-identical. Artifact TARs are inert;
only payload data is materialized for the trusted installed original verifier.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from decision_kernel.identity import canonical_hash, canonical_json
from . import concept_radar_capture as original
from . import concept_detail_supplement as detail
from . import current_state as model
from .current_state_delivery import GitHubAPI, GitHubReadError

VERSION = 'concept-detail-original-capture-v1'
WORKFLOW = 'radar-concept-detail'
SOURCE_WORKFLOW = '.github/workflows/radar-concept-source.yml'
COMPLETE, PARTIAL, FAILED = 'CAPTURED_CONCEPT_DETAILS', 'CAPTURED_CONCEPT_DETAILS_WITH_GAPS', 'FAILED_CONCEPT_DETAILS'
ERRORS = (ValueError, RuntimeError, TypeError, KeyError, AttributeError, OSError, OverflowError, zipfile.BadZipFile)
require = detail.require
_bytes, _write, _digest, _clock = original._bytes, original._write, original._digest, original._clock


def workflow_identity(env, expected_code):
    require(env.get('GITHUB_WORKFLOW') == WORKFLOW, 'DETAIL_WORKFLOW_REJECTED')
    value = original.workflow_identity({**env, 'GITHUB_WORKFLOW': 'radar-concept-source'}, expected_code)
    value['GITHUB_WORKFLOW'] = WORKFLOW
    return value


def _source_run(run, at):
    require(run.get('repository', {}).get('full_name') == model.REPOSITORY
        and run.get('head_repository', {}).get('full_name') == model.REPOSITORY
        and run.get('path') == SOURCE_WORKFLOW and run.get('head_branch') == 'main'
        and run.get('event') == 'workflow_dispatch' and type(run.get('run_attempt')) is int
        and run['run_attempt'] == 1 and type(run.get('id')) is int and run['id'] > 0
        and model.SHA.fullmatch(run.get('head_sha', '')) is not None
        and run.get('status') == 'completed' and run.get('conclusion') == 'success'
        and model.clock(run['created_at']) <= model.clock(run['updated_at']) <= _clock(at),
        'DETAIL_SOURCE_RUN_REJECTED')


def load_base(raw, metadata, *, at):
    run, artifact = metadata['run'], metadata['artifact']
    _source_run(run, at)
    require(model.clock(run['updated_at']) <= _clock(metadata['prepared_at']) <= _clock(at)
        and model.clock(artifact['created_at']) <= model.clock(run['updated_at'])
        and _clock(at) < model.clock(artifact['expires_at'])
        and artifact['name'] == f'concept-radar-{run["id"]}-1', 'DETAIL_SOURCE_CLOCK_OR_ARTIFACT_REJECTED')
    files = model.unpack_archive(raw, artifact, run)
    payload = {k.removeprefix('payload/'): v for k, v in files.items() if k.startswith('payload/')}
    require(payload and all('/' not in k for k in payload), 'DETAIL_BASE_PAYLOAD_REJECTED')
    receipt = json.loads(payload['capture.json'])
    wf = original.workflow_identity(receipt['workflow'], run['head_sha'])
    require(wf['GITHUB_RUN_ID'] == str(run['id'])
        and receipt['status'] in {original.COMPLETE, original.PARTIAL}
        and model.clock(run['created_at']) <= _clock(receipt['started_at'])
        <= _clock(receipt['finished_at']) <= model.clock(run['updated_at']), 'DETAIL_BASE_IDENTITY_REJECTED')
    with tempfile.TemporaryDirectory(prefix='concept-base-data-') as directory:
        root = Path(directory)
        for name, value in payload.items(): _write(root, name, value)
        replay = original.verify(root)
    require(json.loads(files['verification.json']) == replay, 'DETAIL_BASE_REPLAY_DIFFERS')
    return payload, json.loads(payload['observation.json']), receipt


def prepare(api, *, source_run_id: int, output: Path, now):
    """Four bounded GitHub reads; no market token and no fallback to old success."""
    require(type(source_run_id) is int and source_run_id > 0, 'DETAIL_SOURCE_SELECTOR_REJECTED')
    original._safe_path(output)
    require(not output.exists(), 'CREATE_ONLY_INPUT_REQUIRED')
    found = api.get('actions/workflows/radar-concept-source.yml/runs?branch=main&per_page=20')
    runs = found['workflow_runs']
    require(isinstance(runs, list) and 0 < len(runs) <= 20
        and type(found['total_count']) is int and found['total_count'] >= len(runs)
        and len({r['id'] for r in runs}) == len(runs), 'DETAIL_SOURCE_QUERY_REJECTED')
    selected = max(runs, key=lambda r: (model.clock(r['created_at']), r['id']))
    require(selected['id'] == source_run_id, 'DETAIL_NOT_LATEST_SOURCE')
    _source_run(selected, now())
    run = api.get(f'actions/runs/{source_run_id}')
    _source_run(run, now())
    require(all(run[k] == selected[k] for k in ('id', 'head_sha', 'run_attempt', 'created_at')),
            'DETAIL_SOURCE_CHANGED')
    found = api.get(f'actions/runs/{source_run_id}/artifacts?per_page=100')
    require(type(found['total_count']) is int and found['total_count'] == len(found['artifacts']) <= 100,
            'DETAIL_ARTIFACT_QUERY_INCOMPLETE')
    artifact = model.select_artifact(found['artifacts'], f'concept-radar-{source_run_id}-1')
    raw = api.archive(artifact)
    at = _clock(now())
    metadata = {'run': run, 'artifact': artifact, 'prepared_at': at.isoformat()}
    _, report, receipt = load_base(raw, metadata, at=at)
    require(receipt['provenance'] == 'LIVE_HITHINK'
        and at.astimezone(detail.source.SHANGHAI_TZ).date() == detail.source.session_date(report['projection']['market_session']),
        'DETAIL_LIVE_SAME_SESSION_REQUIRED')
    output.mkdir(parents=True)
    _write(output, 'base.zip', raw)
    _write(output, 'source.json', _bytes(metadata))
    return {'source_run_id': source_run_id, 'base_projection_hash': report['projection_hash'],
            'github_api_calls': api.calls, 'market_requests': 0}


def _read(root, name, limit=original.MAX_BYTES):
    original._safe_path(root); original._safe_path(root / name)
    require((root / name).is_file() and (root / name).stat().st_size <= limit, 'DETAIL_INPUT_SIZE_REJECTED')
    return (root / name).read_bytes()


def _implementation():
    root = Path(__file__).resolve().parents[1]
    names = ('runtime/concept_detail_supplement.py', 'runtime/concept_detail_capture.py',
             'runtime/current_state.py', 'runtime/current_state_delivery.py')
    return {**original._implementation(), **{n: _digest((root/n).read_bytes())['sha256'] for n in names}}


def _inventory(root):
    original._safe_path(root)
    files, total = {}, 0
    for p in sorted(root.iterdir()):
        if p.name == 'capture.json': continue
        require(p.name in {'base.zip', 'source.json', 'plan.json', 'observation.json'}
            or re.fullmatch(r'(request|response)-[1-6]\.json', p.name), 'DETAIL_FILE_SCOPE_REJECTED')
        raw = _read(root, p.name, model.MAX_ARCHIVE if p.name == 'base.zip' else original.MAX_BYTES)
        total += len(raw)
        require(total <= original.MAX_TOTAL, 'DETAIL_OUTPUT_BUDGET_REJECTED')
        files[p.name] = _digest(raw)
    return files


def capture(output, *, inputs, offset, workflow, expected_code, transport, now,
            pause=time.sleep, credential='', provenance='SYNTHETIC_TEST_ONLY'):
    wf = workflow_identity(workflow, expected_code)
    original._safe_path(output)
    require(not output.exists(), 'CREATE_ONLY_OUTPUT_REQUIRED')
    started = _clock(now())
    raw = _read(inputs, 'base.zip', model.MAX_ARCHIVE)
    meta_raw = _read(inputs, 'source.json'); metadata = json.loads(meta_raw)
    base, report, receipt = load_base(raw, metadata, at=started)
    require(provenance == receipt['provenance'] and provenance in {'LIVE_HITHINK', 'SYNTHETIC_TEST_ONLY'}
        and (provenance != 'LIVE_HITHINK' or bool(credential)), 'DETAIL_PROVENANCE_REJECTED')
    selection = detail.plan(report, offset=offset)
    plan = {'version': VERSION, 'workflow': wf, 'started_at': started, 'provenance': provenance,
            'base_capture_hash': receipt['capture_hash'], 'selection': selection, **detail.AUTHORITY}
    original._check_safe_json(plan, credential or None)
    original._check_safe_json(metadata, credential or None)
    require(len(raw) + len(meta_raw) + len(_bytes(plan)) + 65536 <= original.MAX_TOTAL,
            'DETAIL_BASE_OUTPUT_RESERVE_REJECTED')
    output.mkdir(parents=True)
    for name, data in {'base.zip': raw, 'source.json': meta_raw, 'plan.json': _bytes(plan)}.items(): _write(output, name, data)
    records, stage, status, reason, error_type = [], 'INPUT_WINDOW', FAILED, None, None

    def acquire(path, params):
        nonlocal stage
        require(len(records) < detail.MAX_REQUESTS, 'DETAIL_REQUEST_BUDGET_REACHED')
        if records: pause(20)
        at = _clock(now()); stage = 'REQUEST_CLOCK'
        prior = _clock(records[-1]['received_at']) if records else started
        require(prior <= at <= started + timedelta(minutes=30)
            and at.astimezone(detail.source.SHANGHAI_TZ).date() == detail.source.session_date(report['projection']['market_session']),
            'DETAIL_REQUEST_CLOCK_REJECTED')
        record = {'path': path, 'params': dict(params), 'requested_at': at,
                  'received_at': None, 'http_status': None, 'response_file': None}
        records.append(record); i = len(records)
        _write(output, f'request-{i}.json', _bytes({k: record[k] for k in ('path', 'params', 'requested_at')}))
        stage = 'TRANSPORT'
        try:
            body = transport(path, dict(params))
        except original.DumpTrialError as exc:
            _, http = original._response_diagnostic(exc)
            if http is not None: record.update(http_status=http, received_at=_clock(now()))
            raise
        received = _clock(now()); record.update(received_at=received, http_status=200)
        stage = 'BODY_SAFETY'
        detail.source.decode(body, credential or None)
        require(sum(p.stat().st_size for p in output.iterdir()) + len(body) + 65536 <= original.MAX_TOTAL,
                'DETAIL_OUTPUT_BUDGET_REJECTED')
        _write(output, f'response-{i}.json', body); record['response_file'] = f'response-{i}.json'
        stage = 'SOURCE_QUALIFICATION'
        return body, at, received

    try:
        built = detail.observe(acquire, base_files=base, report=report, selection=selection, started_at=started)
        stage = 'REPORT_WRITE'
        report_raw = _bytes(built)
        require(len(report_raw) <= original.MAX_BYTES
            and sum(p.stat().st_size for p in output.iterdir()) + len(report_raw) + 65536 <= original.MAX_TOTAL,
            'DETAIL_REPORT_BUDGET_REJECTED')
        _write(output, 'observation.json', report_raw)
        status = PARTIAL if built['projection']['coverage']['detail_gaps'] else COMPLETE
    except ERRORS as exc:
        reason = (original._response_diagnostic(exc)[0] if isinstance(exc, original.DumpTrialError)
                  else str(exc) if isinstance(exc, detail.source.ConceptSourceError) else 'DETAIL_SOURCE_REJECTED')
        error_type = type(exc).__name__
        (output/'observation.json').unlink(missing_ok=True)
    finished = _clock(now())
    require(started <= finished and all(r['received_at'] is None or _clock(r['received_at']) <= finished for r in records),
            'DETAIL_FINISH_CLOCK_REJECTED')
    value = {'version': VERSION, 'workflow': wf, 'provenance': provenance,
        'started_at': started, 'finished_at': finished, 'requests': records,
        'status': status, 'reason_code': reason, 'failed_stage': stage if reason else None,
        'failure_type': error_type, 'implementation': _implementation(),
        'files': _inventory(output), **detail.AUTHORITY}
    value['capture_hash'] = canonical_hash(value)
    _write(output, 'capture.json', _bytes(value))
    return json.loads(_bytes(value))


def verify(output):
    receipt = json.loads(_read(output, 'capture.json'))
    require(receipt['version'] == VERSION and receipt['implementation'] == _implementation()
        and receipt['capture_hash'] == canonical_hash({k:v for k,v in receipt.items() if k != 'capture_hash'})
        and receipt['files'] == _inventory(output)
        and all(receipt.get(k) == v for k,v in detail.AUTHORITY.items()), 'DETAIL_CAPTURE_IDENTITY_REJECTED')
    wf = workflow_identity(receipt['workflow'], receipt['workflow']['GITHUB_SHA'])
    started, finished = _clock(receipt['started_at']), _clock(receipt['finished_at'])
    require(started <= finished, 'DETAIL_FINISH_CLOCK_REJECTED')
    base, report, base_receipt = load_base(_read(output, 'base.zip', model.MAX_ARCHIVE),
        json.loads(_read(output, 'source.json')), at=started)
    saved_plan = json.loads(_read(output, 'plan.json'))
    selection = detail.plan(report, offset=saved_plan['selection']['plan']['offset'])
    expected_plan = {'version': VERSION, 'workflow': wf, 'started_at': started,
        'provenance': receipt['provenance'], 'base_capture_hash': base_receipt['capture_hash'],
        'selection': selection, **detail.AUTHORITY}
    require(_read(output, 'plan.json') == _bytes(expected_plan)
        and receipt['provenance'] == base_receipt['provenance'], 'DETAIL_PLAN_IDENTITY_REJECTED')
    sessions, _, _, _ = detail._base_context(base, report)
    intended = [(path, params) for c in selection['plan']['selected_codes'] for path,params in (
        (detail.source.probe.HISTORY, detail.source._history_params(c, sessions)),
        (detail.source.probe.MEMBERS, {'thscode': c}))]
    records = receipt['requests']
    require(isinstance(records, list) and len(records) <= len(intended), 'DETAIL_REQUEST_SCOPE_REJECTED')
    names = {'base.zip', 'source.json', 'plan.json'}; last = started
    for i, r in enumerate(records, 1):
        require((r['path'], r['params']) == intended[i-1], 'DETAIL_REQUEST_DIFFERS')
        names.add(f'request-{i}.json')
        require(_read(output, f'request-{i}.json') == _bytes({k:r[k] for k in ('path','params','requested_at')}),
                'DETAIL_REQUEST_BYTES_DIFFER')
        at = _clock(r['requested_at']); require(last <= at <= finished, 'DETAIL_REQUEST_CLOCK_REJECTED'); last = at
        if r['received_at'] is not None:
            last = _clock(r['received_at']); require(at <= last <= finished, 'DETAIL_RESPONSE_CLOCK_REJECTED')
        if r['response_file'] is not None:
            require(r['response_file'] == f'response-{i}.json' and r['http_status'] == 200
                and r['received_at'] is not None, 'DETAIL_RESPONSE_IDENTITY_REJECTED')
            names.add(r['response_file']); detail.source.decode(_read(output, r['response_file']))
        else:
            require(i == len(records) and receipt['status'] == FAILED, 'DETAIL_INCOMPLETE_SCOPE_REJECTED')
            http = r['http_status']
            require(http is None or (type(http) is int and 100 <= http <= 599 and r['received_at'] is not None),
                    'DETAIL_HTTP_STATUS_REJECTED')
            if http is not None and receipt['failed_stage'] == 'TRANSPORT':
                require(receipt['failure_type'] == 'DumpTrialError' and receipt['reason_code'] in original._RESPONSE_REASONS
                    and ((receipt['reason_code'] == 'HTTP_REJECTED') == (http != 200)), 'DETAIL_HTTP_DIAGNOSTIC_REJECTED')
    if receipt['status'] != FAILED: names.add('observation.json')
    require(set(receipt['files']) == names, 'DETAIL_FILE_SET_REJECTED')
    if receipt['status'] == FAILED:
        require(receipt['reason_code'] and receipt['failed_stage'] and receipt['failure_type'], 'DETAIL_FAILED_RECEIPT_REJECTED')
        return {'status':'RETAINED_FAILED_DETAIL_REMOTE_CAUSE_NOT_REPROVEN', 'capture_hash':receipt['capture_hash'], 'network_calls':0}
    position = 0
    def replay(path, params):
        nonlocal position
        require(position < len(records), 'DETAIL_UNRECORDED_REQUEST')
        r = records[position]; position += 1
        require((r['path'], r['params']) == (path, params), 'DETAIL_REPLAY_REQUEST_DIFFERS')
        return _read(output, r['response_file']), r['requested_at'], r['received_at']
    rebuilt = detail.observe(replay, base_files=base, report=report, selection=selection, started_at=started)
    expected = PARTIAL if rebuilt['projection']['coverage']['detail_gaps'] else COMPLETE
    require(position == len(records) and receipt['status'] == expected
        and all(receipt[k] is None for k in ('reason_code','failed_stage','failure_type'))
        and _read(output, 'observation.json') == _bytes(rebuilt), 'DETAIL_REBUILD_DIFFERS')
    return {'status':'ORIGINAL_CONCEPT_DETAIL_REQUESTS_AND_RESULTS_REBUILT', 'capture_hash':receipt['capture_hash'],
            'projection_hash':rebuilt['projection_hash'], 'coverage':rebuilt['projection']['coverage'], 'network_calls':0}



def preflight_diagnostic(exc, phase):
    """Finite local labels only; never echo transport/source text or credentials."""
    known = {
        'DETAIL_WORKFLOW_REJECTED', 'WORKFLOW_IDENTITY_REJECTED',
        'DETAIL_SOURCE_RUN_REJECTED', 'DETAIL_SOURCE_CLOCK_OR_ARTIFACT_REJECTED',
        'DETAIL_BASE_PAYLOAD_REJECTED', 'DETAIL_BASE_IDENTITY_REJECTED',
        'DETAIL_BASE_REPLAY_DIFFERS', 'CAPTURE_IDENTITY_REJECTED',
        'DETAIL_SOURCE_SELECTOR_REJECTED', 'DETAIL_SOURCE_QUERY_REJECTED',
        'DETAIL_NOT_LATEST_SOURCE', 'DETAIL_SOURCE_CHANGED', 'DETAIL_ARTIFACT_QUERY_INCOMPLETE',
        'DETAIL_LIVE_SAME_SESSION_REQUIRED', 'CREATE_ONLY_INPUT_REQUIRED',
        'CREATE_ONLY_OUTPUT_REQUIRED', 'DETAIL_INPUT_SIZE_REJECTED',
        'DETAIL_PROVENANCE_REJECTED', 'DETAIL_OFFSET_REJECTED',
        'DETAIL_BASE_OUTPUT_RESERVE_REJECTED', 'EXISTING_PROVIDER_CREDENTIAL_REQUIRED',
        'DETAIL_REPLAY_MUST_NOT_RECEIVE_CREDENTIAL', 'DETAIL_PREPARE_MUST_NOT_RECEIVE_MARKET_CREDENTIAL',
    }
    message = exc.args[0] if len(exc.args) == 1 and type(exc.args[0]) is str else None
    code = message if message in known else 'DETAIL_PHASE_REJECTED'
    http = None
    if isinstance(exc, GitHubReadError):
        match = re.fullmatch(r'GitHub HTTP ([1-5][0-9]{2})', message or '')
        code = 'GITHUB_HTTP_REJECTED' if match else 'GITHUB_READ_UNAVAILABLE'
        http = int(match[1]) if match else None
    return {'version': VERSION, 'phase': phase, 'status': 'PRE_EXECUTION_OR_REPLAY_REJECTION',
            'reason_code': code, 'http_status': http,
            'meaning': 'NO_REMOTE_CAUSE_INFERRED; NO_AUTOMATIC_RETRY'}


def main(argv=None):
    p = argparse.ArgumentParser(description='One source-bound concept detail batch; no automatic next batch.')
    p.add_argument('mode', choices=('prepare','capture','verify')); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--inputs',type=Path); p.add_argument('--source-run-id',type=int)
    p.add_argument('--expected-code'); p.add_argument('--offset',type=int,default=0)
    p.add_argument('--failure-output',type=Path)
    a = p.parse_args(argv); now = lambda: datetime.now(timezone.utc)
    try:
        key = os.environ.get(original.HITHINK_API_KEY_ENV, '')
        if a.mode == 'verify':
            require(not key, 'DETAIL_REPLAY_MUST_NOT_RECEIVE_CREDENTIAL'); result = verify(a.output)
        elif a.mode == 'prepare':
            require(not key, 'DETAIL_PREPARE_MUST_NOT_RECEIVE_MARKET_CREDENTIAL')
            workflow_identity(os.environ, a.expected_code)
            api = GitHubAPI(os.environ.get('GITHUB_TOKEN',''), max_calls=6)
            try: result = prepare(api, source_run_id=a.source_run_id, output=a.output, now=now)
            finally: api.session.close()
        else:
            require(bool(key), 'EXISTING_PROVIDER_CREDENTIAL_REQUIRED')
            result = capture(a.output, inputs=a.inputs, offset=a.offset, workflow=os.environ,
                expected_code=a.expected_code, transport=lambda path,params: original.request_raw(path,params,credential=key),
                now=now, credential=key, provenance='LIVE_HITHINK')
        print(canonical_json(result if a.mode != 'capture' else {k:result[k] for k in ('status','capture_hash')}))
        return 2 if result.get('status') == FAILED else 0
    except ERRORS as exc:
        failure = preflight_diagnostic(exc, a.mode)
        failure['diagnostic_retention'] = 'NOT_REQUESTED' if a.failure_output is None else 'NOT_SAVED'
        if a.failure_output is not None:
            try:
                original._safe_path(a.failure_output)
                a.failure_output.parent.mkdir(parents=True, exist_ok=True)
                failure['diagnostic_retention'] = 'SAVED_CREATE_ONLY'
                _write(a.failure_output.parent, a.failure_output.name, _bytes(failure))
            except (OSError, ValueError):
                failure['diagnostic_retention'] = 'NOT_SAVED'
        print(canonical_json(failure))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
