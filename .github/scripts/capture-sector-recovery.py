"""One approved historical gap capture; candidate only, never daily production.

Reuse the original client, normalizers, state constructor and atomic file helpers.
Retain decoded provider JSON, not raw HTTP. No retry, model or new signal event.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, time as day_time, timedelta, timezone
from pathlib import Path

from decision_kernel.adapters.hithink import SHANGHAI_TZ, latest_completed_a_share_session, normalize_hithink_calendar
from decision_kernel.adapters.hithink_index import normalize_hithink_completed_index_history, normalize_hithink_industry_catalog
from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import hithink_http as http, hithink_index_http as index
from decision_kernel.runtime.sector_radar import SectorPricePoint, SectorPriceSeries
from decision_kernel.runtime.sector_radar_audit import _atomic_bytes, _check_safe_json, _implementation, _json_bytes, _sha
from decision_kernel.runtime.sector_radar_persistence import load_sector_radar_persistent_bundle
from decision_kernel.runtime.sector_radar_producer import discover_previous_sector_radar_artifact
from decision_kernel.runtime.sector_radar_state import SectorRadarStateSourceLineage, create_sector_radar_market_state, serialize_sector_radar_market_state

REPO = 'auguspp/decision-kernel'
WORKFLOW = '.github/workflows/sector-recovery-once.yml'
PARENT_WORKFLOW = '.github/workflows/sector-radar-shadow.yml'
REQUEST = 'sector-gap-20260911-v1'
REQUEST_FILE = Path('radar_inputs/sector-recovery-once-2026-09-11.json')
LAUNCH_REF = 'refs/tags/sector-recovery-once/' + REQUEST
MAX_CALLS, CAPTURE_SECONDS = 323, 138 * 60
INPUTS = ('market-state.json', 'candidate-events.json', 'manifest.json')
AUTHORITY = {'research_authority': 'NONE', 'human_attention_authority': 'NONE',
             'investment_authority': 'NONE', 'events_created': 0, 'production_state_writes': 0}
LIVE, SYNTHETIC = 'LIVE_HITHINK', 'SYNTHETIC_TEST_ONLY'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def save(path, value):
    _atomic_bytes(path, (canonical_json(value) + '\n').encode())


def load(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 8 * 1024 * 1024, 'INVALID_INPUT_FILE')
    return json.loads(path.read_text(encoding='utf-8'))


def invocation(env):
    require(all(env.get(k) == v for k, v in {
        'GITHUB_REPOSITORY': REPO, 'GITHUB_REF': 'refs/heads/main',
        'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_RUN_ATTEMPT': '1',
        'GITHUB_WORKFLOW_REF': REPO + '/' + WORKFLOW + '@refs/heads/main',
    }.items()), 'FRESH_MAIN_RECOVERY_ONLY')
    require(re.fullmatch('[0-9a-f]{40}', env.get('GITHUB_SHA', '')) is not None
            and env.get('GITHUB_RUN_ID', '').isdigit() and int(env['GITHUB_RUN_ID']) > 0, 'INVALID_RUN_IDENTITY')
    return {k: env[k] for k in ('GITHUB_REPOSITORY', 'GITHUB_REF', 'GITHUB_EVENT_NAME',
            'GITHUB_RUN_ATTEMPT', 'GITHUB_WORKFLOW_REF', 'GITHUB_SHA', 'GITHUB_RUN_ID')}


def prepare(root, plan, env, *, save_binding=True):
    identity = invocation(env)
    require(plan['request_id'] == REQUEST and plan['authorization_comment_id'] == 5628923881
            and type(plan['max_hithink_requests']) is int and plan['max_hithink_requests'] == MAX_CALLS
            and plan['job_timeout_minutes'] == 150 and plan['technical_retries'] == 0
            and plan['request_gap_seconds'] == 20, 'UNAPPROVED_RECOVERY_PLAN')
    parent = plan['parent']
    run, artifacts, newest, launch, ref = [load(root / 'metadata' / n) for n in
        ('run.json', 'artifacts.json', 'newest.json', 'launch.json', 'launch-ref.json')]
    require(run['id'] == parent['run_id'] and run['head_sha'] == parent['commit']
            and run['path'] == PARENT_WORKFLOW and run['head_branch'] == 'main'
            and run['status'] == 'completed' and run['conclusion'] == 'success'
            and run['run_attempt'] == 1 and run['event'] in {'schedule', 'workflow_dispatch'}
            and run['repository']['full_name'] == run['head_repository']['full_name'] == REPO,
            'PARENT_RUN_IDENTITY_REJECTED')
    # Original latest-success discovery, with native CLI responses, no new HTTP client.
    responses = {f'https://api.github.com/repos/{REPO}/actions/workflows/sector-radar-shadow.yml/runs?branch=main&status=success&per_page=2': newest,
                 f'https://api.github.com/repos/{REPO}/actions/runs/{parent["run_id"]}/artifacts?per_page=100': artifacts}
    found = discover_previous_sector_radar_artifact(repository=REPO, workflow_file='sector-radar-shadow.yml',
        current_run_id=int(identity['GITHUB_RUN_ID']), token=None, request_json=responses.__getitem__)
    require(found.artifact_available and found.prior_run_id == parent['run_id']
            and found.prior_head_sha == parent['commit'] and found.artifact_id == parent['artifact_id'],
            'PARENT_NO_LONGER_LATEST_SUCCESS')
    require(artifacts['total_count'] == len(artifacts['artifacts']), 'ARTIFACT_ENUMERATION_INCOMPLETE')
    matches = [a for a in artifacts['artifacts'] if a['name'] == 'sector-radar-state-bundle']
    require(len(matches) == 1, 'UNIQUE_STATE_ARTIFACT_REQUIRED')
    a = matches[0]
    require(a['id'] == parent['artifact_id'] and a['digest'] == parent['artifact_digest']
            and a['size_in_bytes'] == parent['artifact_bytes'] and a['expired'] is False
            and a['workflow_run']['id'] == parent['run_id'] and a['workflow_run']['head_sha'] == parent['commit'],
            'PARENT_ARTIFACT_REJECTED')
    require(ref['ref'] == LAUNCH_REF and ref['object']['type'] == 'tag'
            and ref['object']['sha'] == launch['sha'] == env['RECOVERY_LAUNCH_SHA']
            and launch['tag'] == REQUEST and launch['object']['type'] == 'commit'
            and launch['object']['sha'] == identity['GITHUB_SHA']
            and json.loads(launch['message']) == {'request_id': REQUEST,
                'run_id': identity['GITHUB_RUN_ID'], 'authorization_comment_id': 5628923881}, 'LAUNCH_NOT_BOUND_TO_THIS_RUN')
    bundle = load_sector_radar_persistent_bundle(root / 'input', expected_repository=REPO,
        expected_workflow=PARENT_WORKFLOW, expected_parent_hint_mapping_hash=parent['parent_hint_mapping_hash'])
    require(bundle.manifest.source_run_id == parent['run_id'] and bundle.manifest.source_run_attempt == 1
            and bundle.manifest.source_commit_sha == parent['commit']
            and bundle.market_state.state_hash == parent['state_hash']
            and bundle.market_state.sessions[-1].isoformat() == parent['market_session'], 'PARENT_BUNDLE_REJECTED')
    binding = {'request': plan, 'workflow': identity, 'launch_sha': launch['sha'], **AUTHORITY}
    if save_binding:
        save(root / 'binding.json', binding)
    return bundle, binding


def rebuild(bundle, plan, observed_at, calendar, read, source_marker):
    """Same deterministic composition is used during capture and offline verification."""
    state = bundle.market_state
    require(observed_at.tzinfo is not None and observed_at > state.updated_at, 'INVALID_OBSERVATION_CLOCK')
    sessions = normalize_hithink_calendar(calendar)
    target = latest_completed_a_share_session(sessions, observed_at=observed_at)
    require(target > state.sessions[-1], 'NO_MISSING_COMPLETED_SESSION')
    require(tuple(d for d in sessions if state.sessions[0] <= d <= state.sessions[-1]) == state.sessions,
            'SAVED_CALENDAR_CONTINUITY_CHANGED')
    needed = tuple(d for d in sessions if state.sessions[-3] <= d <= target)
    added = tuple(d for d in needed if d > state.sessions[-1])
    require(added and len(state.series) + 2 <= MAX_CALLS, 'RECOVERY_REQUEST_BOUND')
    catalog = normalize_hithink_industry_catalog(read(index.HITHINK_INDEX_CATALOG_PATH, {'tag': 'industry'}))
    require(catalog.catalog_hash == state.catalog_hash, 'CATALOG_CHANGED')
    start = datetime.combine(needed[0], day_time(), tzinfo=SHANGHAI_TZ)
    # Avoid a next-session midnight under an inclusive historical endpoint.
    end = datetime.combine(target + timedelta(days=1), day_time(), tzinfo=SHANGHAI_TZ) - timedelta(milliseconds=1)
    series = []
    for old in state.series:
        params = {'thscode': old.thscode, 'interval': '1d',
                  'start': str(int(start.timestamp() * 1000)), 'end': str(int(end.timestamp() * 1000))}
        h = normalize_hithink_completed_index_history(read(index.HITHINK_INDEX_HISTORY_PATH, params),
                thscode=old.thscode, sessions=sessions, observed_at=observed_at)
        require(h.response_session == h.expected_latest_session == target
                and tuple(p.as_of.date() for p in h.points) == needed, 'HISTORY_SESSION_COVERAGE_REJECTED')
        by_day = {p.as_of.date(): p for p in h.points}
        for day, close, turnover in zip(state.sessions[-3:], old.closes[-3:], old.turnovers[-3:]):
            require((by_day[day].close, by_day[day].turnover) == (close, turnover), 'OVERLAP_VALUES_CHANGED')
        points = tuple(SectorPricePoint(d, c, t) for d, c, t in zip(state.sessions, old.closes, old.turnovers))
        points += tuple(SectorPricePoint(d, by_day[d].close, by_day[d].turnover) for d in added)
        series.append(SectorPriceSeries(old.thscode, old.name, points))
    parent = plan['parent']
    lineage = (*state.source_lineage, SectorRadarStateSourceLineage('RECOVERY_PARENT_STATE',
        parent['run_id'], parent['artifact_id'], parent['artifact_digest'], bundle.manifest.last_result_hash))
    candidate = create_sector_radar_market_state(catalog=catalog, benchmark=series[0],
        broad_series=series[1:1 + len(state.broad_identities)], granular_series=series[1 + len(state.broad_identities):],
        created_at=observed_at, source='RECOVERY_CANDIDATE_NOT_RESTORE_AUTHORITY:' + source_marker,
        source_lineage=lineage)
    return candidate, [d.isoformat() for d in added]


def collect(root, bundle, binding, *, api_key=None, request=None, provenance=LIVE, now=None, monotonic=None):
    require((provenance == LIVE and request is None and api_key)
            or (provenance == SYNTHETIC and request is not None and not api_key), 'INJECTED_TRANSPORT_NOT_LIVE')
    if provenance == LIVE:
        require(now is None and monotonic is None, 'LIVE_CLOCK_OVERRIDE_REJECTED')
        require(os.environ.get(http.HITHINK_SECTOR_PACING_ENV) == '1', 'ORIGINAL_PACING_REQUIRED')
        request = lambda path, params: http._request_hithink_json(api_key=api_key, path=path, params=params, timeout_seconds=10.0)
    now, monotonic = now or (lambda: datetime.now(timezone.utc)), monotonic or time.monotonic
    plan, out = binding['request'], root / 'capture'
    out.mkdir(exist_ok=False)
    started, tick = now(), monotonic()
    report = {'format': REQUEST, 'status': 'RECORDING', 'provenance': provenance, 'binding': binding,
        'started_at': started.isoformat(), 'observed_at': None, 'implementation': _implementation(),
        'script_sha256': _sha(Path(__file__).read_bytes()), 'requests': [], 'files': {},
        'candidate_state_hash': None, 'unobserved_event_sessions': [], 'error_type': None,
        'input_files': {n: _sha((root / 'input' / n).read_bytes()) for n in INPUTS},
        'technical_retries': 0, 'restore_authority': False, **AUTHORITY}
    def flush():
        save(out / 'report.json', {**report, 'report_hash': canonical_hash(report)})
    def read(path, params):
        require(len(report['requests']) < min(plan['max_hithink_requests'], MAX_CALLS), 'REQUEST_LIMIT_REACHED')
        require(monotonic() - tick < CAPTURE_SECONDS - 30, 'CAPTURE_DEADLINE_REACHED')
        row = {'path': path, 'params': params, 'started_at': now().isoformat(),
               'completed_at': None, 'response_file': None, 'error_type': None}
        report['requests'].append(row)
        flush()  # Reserved attempt, not proof that the provider received it.
        try:
            value = request(path, params)
            _check_safe_json(value, api_key)
            raw = _json_bytes(value)
            require(len(raw) <= 8 * 1024 * 1024, 'RESPONSE_BYTE_LIMIT')
            require(sum(f['bytes'] for f in report['files'].values()) + len(raw) <= 64 * 1024 * 1024, 'CAPTURE_BYTE_LIMIT')
            name = f"responses/{len(report['requests']) - 1:04d}.json"
            _atomic_bytes(out / name, raw)
            report['files'][name] = {'bytes': len(raw), 'sha256': _sha(raw)}
            row['response_file'] = name
            return json.loads(raw)
        except Exception as exc:
            row['error_type'] = type(exc).__name__
            if isinstance(exc, http.HithinkRuntimeError):
                row['safe_diagnostic'] = str(exc).replace(api_key or '\0', '***')[:1000]
            raise
        finally:
            row['completed_at'] = now().isoformat()
            flush()
    flush()
    try:
        calendar = read(http.HITHINK_CALENDAR_PATH, {})
        observed = now()  # Real clock after the sole calendar request; fixed for all histories.
        report['observed_at'] = observed.isoformat()
        flush()
        marker = REQUEST + ':run=' + binding['workflow']['GITHUB_RUN_ID']
        candidate, missed = rebuild(bundle, plan, observed, calendar, read, marker)
        require(monotonic() - tick < CAPTURE_SECONDS, 'CAPTURE_DEADLINE_REACHED')
        _atomic_bytes(out / 'candidate-state.json', serialize_sector_radar_market_state(candidate).encode())
        _atomic_bytes(out / 'candidate-events.json', (root / 'input/candidate-events.json').read_bytes())
        report.update(status='CAPTURED_CANDIDATE_REVIEW_REQUIRED', candidate_state_hash=candidate.state_hash,
                      unobserved_event_sessions=missed)
    except Exception as exc:
        report.update(status='FAILED_CLOSED', error_type=type(exc).__name__,
                      error_code=str(exc) if re.fullmatch('[A-Z_]{1,80}', str(exc)) else None)
        raise
    finally:
        report['finished_at'], report['elapsed_seconds'] = now().isoformat(), int(monotonic() - tick)
        flush()
    return report


def verify(root):
    out, report = root / 'capture', load(root / 'capture/report.json')
    require(report.pop('report_hash') == canonical_hash(report), 'REPORT_HASH_MISMATCH')
    require(report['format'] == REQUEST and report['implementation'] == _implementation()
            and report['script_sha256'] == _sha(Path(__file__).read_bytes())
            and all(report[k] == v for k, v in AUTHORITY.items()) and report['restore_authority'] is False
            and report['technical_retries'] == 0 and report['provenance'] in {LIVE, SYNTHETIC}, 'RECOVERY_CONTRACT_CHANGED')
    require(report['status'] == 'CAPTURED_CANDIDATE_REVIEW_REQUIRED', 'CAPTURE_NOT_COMPLETE')
    binding = load(root / 'binding.json')
    require(binding == report['binding'] and set(report['input_files']) == set(INPUTS), 'BINDING_CHANGED')
    for name in INPUTS:
        require(_sha((root / 'input' / name).read_bytes()) == report['input_files'][name], 'PARENT_BYTES_CHANGED')
    bundle, rebuilt_binding = prepare(root, binding['request'],
        {**binding['workflow'], 'RECOVERY_LAUNCH_SHA': binding['launch_sha']}, save_binding=False)
    require(rebuilt_binding == binding and type(report['elapsed_seconds']) is int
            and 0 <= report['elapsed_seconds'] <= CAPTURE_SECONDS, 'BOUND_EXECUTION_CHANGED')
    require(not any(p.is_symlink() for p in root.rglob('*')), 'SYMLINK_REJECTED')
    position, previous = 0, datetime.fromisoformat(report['started_at'])
    def read(path, params):
        nonlocal position, previous
        require(position < len(report['requests']) <= MAX_CALLS, 'REQUEST_TRANSCRIPT_INCOMPLETE')
        row, name = report['requests'][position], f'responses/{position:04d}.json'
        position += 1
        require(row['path'] == path and row['params'] == params and row['response_file'] == name
                and row['error_type'] is None, 'REQUEST_TRANSCRIPT_DIFFERS')
        begin, end = datetime.fromisoformat(row['started_at']), datetime.fromisoformat(row['completed_at'])
        require(previous <= begin <= end <= datetime.fromisoformat(report['finished_at']), 'REQUEST_CLOCK_REVERSED')
        previous = end
        raw = (out / name).read_bytes()
        require(report['files'][name] == {'bytes': len(raw), 'sha256': _sha(raw)}, 'RESPONSE_BYTES_CHANGED')
        return json.loads(raw)
    calendar = read(http.HITHINK_CALENDAR_PATH, {})
    observed = datetime.fromisoformat(report['observed_at'])
    require(previous <= observed <= datetime.fromisoformat(report['finished_at']), 'FREEZE_CLOCK_REJECTED')
    previous = observed
    candidate, missed = rebuild(bundle, binding['request'], observed, calendar, read,
                               REQUEST + ':run=' + binding['workflow']['GITHUB_RUN_ID'])
    require(position == len(report['requests']) == len(report['files']), 'UNCONSUMED_REQUEST_OR_FILE')
    expected = {'report.json', 'candidate-state.json', 'candidate-events.json', *report['files']}
    actual = {p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()} - {'verification.json'}
    require(actual == expected, 'FILE_INVENTORY_DIFFERS')
    require(serialize_sector_radar_market_state(candidate).encode() == (out / 'candidate-state.json').read_bytes()
            and candidate.state_hash == report['candidate_state_hash'] and missed == report['unobserved_event_sessions'], 'CANDIDATE_REBUILD_DIFFERS')
    require((out / 'candidate-events.json').read_bytes() == (root / 'input/candidate-events.json').read_bytes(), 'OLD_EVENTS_CHANGED')
    proof = {'status': 'ORIGINAL_SOURCE_AND_CANDIDATE_REBUILT', 'network_calls': 0,
        'report_hash': canonical_hash(report), 'state_hash': candidate.state_hash,
        'restore_authority': False, 'provenance': report['provenance'], **AUTHORITY}
    save(out / 'verification.json', proof)
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'capture', 'verify'))
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.operation == 'prepare':
            prepare(args.root, load(REQUEST_FILE), os.environ)
        elif args.operation == 'capture':
            bundle, binding = prepare(args.root, load(REQUEST_FILE), os.environ)
            collect(args.root, bundle, binding, api_key=os.environ.get(http.HITHINK_API_KEY_ENV))
        else:
            verify(args.root)
        print(args.operation + ': completed; NOT production recovery acceptance')
        return 0
    except Exception as exc:
        code = str(exc) if re.fullmatch('[A-Z_]{1,80}', str(exc)) else type(exc).__name__
        print(args.operation + ': FAILED_CLOSED / ' + code + '; inspect retained files; no retry')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
