"""One approved missing-session capture; existing adapters/state, not production.

Decoded provider JSON is retained (not raw HTTP). No model, retry, fallback,
prospective event, cache update, or automatic installation of the candidate.
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
from decision_kernel.runtime.sector_radar_state import SectorRadarStateSourceLineage, create_sector_radar_market_state, parse_sector_radar_market_state, serialize_sector_radar_market_state

REPO = 'auguspp/decision-kernel'
WORKFLOW = '.github/workflows/sector-recovery-once.yml'
PARENT_WORKFLOW = '.github/workflows/sector-radar-shadow.yml'
REQUEST = 'sector-gap-20260911-v1'
REQUEST_FILE = Path('radar_inputs/sector-recovery-once-2026-09-11.json')
LAUNCH_REF = 'refs/tags/sector-recovery-once/' + REQUEST
MAX_CALLS = 323
CAPTURE_SECONDS = 140 * 60  # Leaves ten minutes inside the 150-minute job for retention.
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
            and env.get('GITHUB_RUN_ID', '').isdigit(), 'INVALID_RUN_IDENTITY')
    return {k: env[k] for k in ('GITHUB_REPOSITORY', 'GITHUB_REF', 'GITHUB_EVENT_NAME',
            'GITHUB_RUN_ATTEMPT', 'GITHUB_WORKFLOW_REF', 'GITHUB_SHA', 'GITHUB_RUN_ID')}


def prepare(root, plan, env):
    """Validate native CLI metadata plus the exact original persistent bundle."""
    identity = invocation(env)
    require(plan['request_id'] == REQUEST and plan['authorization_comment_id'] == 5628923881
            and plan['max_hithink_requests'] == MAX_CALLS and plan['job_timeout_minutes'] == 150
            and plan['technical_retries'] == 0 and plan['request_gap_seconds'] == 20,
            'UNAPPROVED_RECOVERY_PLAN')
    parent = plan['parent']
    run, artifacts, newest, launch = [load(root / 'metadata' / n) for n in
                                      ('run.json', 'artifacts.json', 'newest.json', 'launch.json')]
    require(run['id'] == parent['run_id'] and run['head_sha'] == parent['commit']
            and run['path'] == PARENT_WORKFLOW and run['head_branch'] == 'main'
            and run['status'] == 'completed' and run['conclusion'] == 'success'
            and run['run_attempt'] == 1 and run['event'] in {'schedule', 'workflow_dispatch'}
            and run['repository']['full_name'] == run['head_repository']['full_name'] == REPO,
            'PARENT_RUN_IDENTITY_REJECTED')
    require(bool(newest['workflow_runs']) and newest['workflow_runs'][0]['id'] == run['id']
            and newest['workflow_runs'][0]['head_sha'] == run['head_sha'], 'PARENT_NO_LONGER_LATEST_SUCCESS')
    require(artifacts['total_count'] == len(artifacts['artifacts']), 'ARTIFACT_ENUMERATION_INCOMPLETE')
    matches = [a for a in artifacts['artifacts'] if a['name'] == 'sector-radar-state-bundle']
    require(len(matches) == 1, 'UNIQUE_STATE_ARTIFACT_REQUIRED')
    artifact = matches[0]
    require(artifact['id'] == parent['artifact_id'] and artifact['digest'] == parent['artifact_digest']
            and artifact['size_in_bytes'] == parent['artifact_bytes'] and artifact['expired'] is False
            and artifact['workflow_run']['id'] == parent['run_id']
            and artifact['workflow_run']['head_sha'] == parent['commit'], 'PARENT_ARTIFACT_REJECTED')
    require(launch['tag'] == REQUEST and launch['object']['type'] == 'commit'
            and launch['object']['sha'] == identity['GITHUB_SHA']
            and json.loads(launch['message']) == {'request_id': REQUEST,
                'run_id': identity['GITHUB_RUN_ID'], 'authorization_comment_id': 5628923881},
            'LAUNCH_NOT_BOUND_TO_THIS_RUN')
    bundle = load_sector_radar_persistent_bundle(root / 'input', expected_repository=REPO,
                expected_workflow=PARENT_WORKFLOW, expected_parent_hint_mapping_hash=parent['parent_hint_mapping_hash'])
    require(bundle.manifest.source_run_id == parent['run_id']
            and bundle.manifest.source_commit_sha == parent['commit']
            and bundle.market_state.state_hash == parent['state_hash']
            and bundle.market_state.sessions[-1].isoformat() == parent['market_session'], 'PARENT_BUNDLE_REJECTED')
    save(root / 'binding.json', {'request': plan, 'workflow': identity, 'artifact': artifact, **AUTHORITY})
    return bundle


def rebuild(bundle, plan, observed_at, read, *, state_clock):
    """Exact source-to-state composition, also called offline with saved JSON."""
    state = bundle.market_state
    require(observed_at.tzinfo is not None and observed_at > state.updated_at, 'INVALID_OBSERVATION_CLOCK')
    sessions = normalize_hithink_calendar(read(http.HITHINK_CALENDAR_PATH, {}))
    target = latest_completed_a_share_session(sessions, observed_at=observed_at)
    require(target > state.sessions[-1], 'NO_MISSING_COMPLETED_SESSION')
    require(tuple(d for d in sessions if state.sessions[0] <= d <= state.sessions[-1]) == state.sessions,
            'SAVED_CALENDAR_CONTINUITY_CHANGED')
    needed = tuple(d for d in sessions if state.sessions[-3] <= d <= target)
    added = tuple(d for d in needed if d > state.sessions[-1])
    require(added and len(state.series) + 2 <= MAX_CALLS, 'RECOVERY_REQUEST_BOUND')
    catalog = normalize_hithink_industry_catalog(read(index.HITHINK_INDEX_CATALOG_PATH, {'tag': 'industry'}))
    require(catalog.catalog_hash == state.catalog_hash, 'CATALOG_CHANGED')
    # End inside target day: both inclusive/exclusive APIs must not include next midnight.
    start = datetime.combine(needed[0], day_time(), tzinfo=SHANGHAI_TZ)
    end = datetime.combine(target + timedelta(days=1), day_time(), tzinfo=SHANGHAI_TZ) - timedelta(milliseconds=1)
    series = []
    for old in state.series:
        params = {'thscode': old.thscode, 'interval': '1d',
                  'start': str(int(start.timestamp() * 1000)), 'end': str(int(end.timestamp() * 1000))}
        history = normalize_hithink_completed_index_history(read(index.HITHINK_INDEX_HISTORY_PATH, params),
                    thscode=old.thscode, sessions=sessions, observed_at=observed_at)
        require(history.response_session == history.expected_latest_session == target
                and tuple(p.as_of.date() for p in history.points) == needed, 'HISTORY_SESSION_COVERAGE_REJECTED')
        by_day = {p.as_of.date(): p for p in history.points}
        for day, close, turnover in zip(state.sessions[-3:], old.closes[-3:], old.turnovers[-3:]):
            require((by_day[day].close, by_day[day].turnover) == (close, turnover), 'OVERLAP_VALUES_CHANGED')
        points = tuple(SectorPricePoint(d, c, t) for d, c, t in zip(state.sessions, old.closes, old.turnovers))
        points += tuple(SectorPricePoint(d, by_day[d].close, by_day[d].turnover) for d in added)
        series.append(SectorPriceSeries(old.thscode, old.name, points))
    parent = plan['parent']
    lineage = (*state.source_lineage, SectorRadarStateSourceLineage('RECOVERY_PARENT_STATE',
        parent['run_id'], parent['artifact_id'], parent['artifact_digest'], bundle.manifest.last_result_hash))
    constructed_at = state_clock()
    require(constructed_at >= observed_at, 'STATE_CLOCK_REVERSED')
    candidate = create_sector_radar_market_state(catalog=catalog, benchmark=series[0],
        broad_series=series[1:1 + len(state.broad_identities)],
        granular_series=series[1 + len(state.broad_identities):], created_at=constructed_at,
        source='RECOVERY_CANDIDATE_NOT_RESTORE_AUTHORITY:' + REQUEST,
        source_lineage=lineage)
    return candidate, [d.isoformat() for d in added]


def collect(root, bundle, plan, *, api_key=None, request=None, provenance=LIVE, now=None, monotonic=None):
    require(provenance in {LIVE, SYNTHETIC} and ((provenance == LIVE and request is None and api_key)
            or (provenance == SYNTHETIC and request is not None and not api_key)), 'INJECTED_TRANSPORT_NOT_LIVE')
    if provenance == LIVE:
        require(os.environ.get(http.HITHINK_SECTOR_PACING_ENV) == '1', 'ORIGINAL_PACING_REQUIRED')
        request = lambda path, params: http._request_hithink_json(api_key=api_key,
                    path=path, params=params, timeout_seconds=10.0)
    now = now or (lambda: datetime.now(timezone.utc))
    monotonic = monotonic or time.monotonic
    out = root / 'capture'
    out.mkdir(exist_ok=False)
    started, tick = now(), monotonic()
    report = {'format': REQUEST, 'status': 'RECORDING', 'provenance': provenance,
        'request': plan, 'observed_at': started.isoformat(), 'implementation': _implementation(),
        'script_sha256': _sha(Path(__file__).read_bytes()), 'binding_hash': canonical_hash(load(root / 'binding.json')),
        'requests': [], 'files': {},
        'candidate_state_hash': None, 'unobserved_event_sessions': [], 'error_type': None,
        'technical_retries': 0, 'restore_authority': False, **AUTHORITY}
    def flush():
        report['report_hash'] = canonical_hash({k: v for k, v in report.items() if k != 'report_hash'})
        save(out / 'report.json', report)
    def read(path, params):
        require(len(report['requests']) < min(plan['max_hithink_requests'], MAX_CALLS), 'REQUEST_LIMIT_REACHED')
        require(monotonic() - tick < CAPTURE_SECONDS - 30, 'CAPTURE_DEADLINE_REACHED')
        row = {'path': path, 'params': params, 'started_at': now().isoformat(),
               'completed_at': None, 'response_file': None, 'error_type': None}
        report['requests'].append(row)
        flush()  # Reserved attempt survives interruption; not proof every reserved call reached the server.
        try:
            value = request(path, params)
            _check_safe_json(value, api_key)
            raw = _json_bytes(value)
            require(len(raw) <= 8 * 1024 * 1024, 'RESPONSE_BYTE_LIMIT')
            require(sum(f['bytes'] for f in report['files'].values()) + len(raw) <= 64 * 1024 * 1024,
                    'CAPTURE_BYTE_LIMIT')
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
        candidate, missed = rebuild(bundle, plan, started, read, state_clock=now)
        require(monotonic() - tick < CAPTURE_SECONDS, 'CAPTURE_DEADLINE_REACHED')
        _atomic_bytes(out / 'candidate-state.json', serialize_sector_radar_market_state(candidate).encode())
        _atomic_bytes(out / 'candidate-events.json', (root / 'input/candidate-events.json').read_bytes())
        report.update(status='CAPTURED_CANDIDATE_REVIEW_REQUIRED', candidate_state_hash=candidate.state_hash,
                      unobserved_event_sessions=missed, candidate_created_at=candidate.created_at.isoformat())
    except Exception as exc:
        report.update(status='FAILED_CLOSED', error_type=type(exc).__name__)
        raise
    finally:
        report['finished_at'] = now().isoformat()
        report['elapsed_seconds'] = int(monotonic() - tick)
        report['input_files'] = {n: _sha((root / 'input' / n).read_bytes())
                for n in ('market-state.json', 'candidate-events.json', 'manifest.json')}
        flush()
    return report


def verify(root):
    """No credentials/network: original normalizers and state constructor again."""
    out = root / 'capture'
    report = load(out / 'report.json')
    require(report['report_hash'] == canonical_hash({k: v for k, v in report.items() if k != 'report_hash'}), 'REPORT_HASH_MISMATCH')
    require(report['format'] == REQUEST and report['implementation'] == _implementation()
            and report['script_sha256'] == _sha(Path(__file__).read_bytes())
            and all(report[k] == v for k, v in AUTHORITY.items())
            and report['restore_authority'] is False and report['technical_retries'] == 0, 'RECOVERY_CONTRACT_CHANGED')
    require(report['status'] == 'CAPTURED_CANDIDATE_REVIEW_REQUIRED', 'CAPTURE_NOT_COMPLETE')
    for name, digest in report['input_files'].items():
        require(name in {'market-state.json', 'candidate-events.json', 'manifest.json'}
                and _sha((root / 'input' / name).read_bytes()) == digest, 'PARENT_BYTES_CHANGED')
    binding = load(root / 'binding.json')
    require(binding['request'] == report['request'] and canonical_hash(binding) == report['binding_hash'], 'BINDING_CHANGED')
    require(report['provenance'] in {LIVE, SYNTHETIC}
            and 0 <= report['elapsed_seconds'] < CAPTURE_SECONDS, 'CAPTURE_BOUNDS_INVALID')
    previous_clock = datetime.fromisoformat(report['observed_at'])
    for row in report['requests']:
        began, ended = (datetime.fromisoformat(row[k]) for k in ('started_at', 'completed_at'))
        require(previous_clock <= began <= ended, 'REQUEST_CLOCK_REVERSED')
        previous_clock = ended
    require(previous_clock <= datetime.fromisoformat(report['candidate_created_at'])
            <= datetime.fromisoformat(report['finished_at']), 'CANDIDATE_CLOCK_REVERSED')
    bundle = load_sector_radar_persistent_bundle(root / 'input', expected_repository=REPO, expected_workflow=PARENT_WORKFLOW)
    require(bundle.market_state.state_hash == report['request']['parent']['state_hash'], 'PARENT_STATE_CHANGED')
    position = 0
    def read(path, params):
        nonlocal position
        require(position < len(report['requests']) <= MAX_CALLS, 'REQUEST_TRANSCRIPT_INCOMPLETE')
        row = report['requests'][position]
        name = f'responses/{position:04d}.json'
        position += 1
        require(row['path'] == path and row['params'] == params and row['response_file'] == name
                and row['error_type'] is None, 'REQUEST_TRANSCRIPT_DIFFERS')
        require(datetime.fromisoformat(row['started_at']) <= datetime.fromisoformat(row['completed_at']), 'REQUEST_CLOCK_REVERSED')
        raw = (out / name).read_bytes()
        require(report['files'][name] == {'bytes': len(raw), 'sha256': _sha(raw)}, 'RESPONSE_BYTES_CHANGED')
        return json.loads(raw)
    candidate, missed = rebuild(bundle, report['request'], datetime.fromisoformat(report['observed_at']), read,
        state_clock=lambda: datetime.fromisoformat(report['candidate_created_at']))
    require(position == len(report['requests']) == len(report['files']), 'UNCONSUMED_REQUEST_OR_FILE')
    require({p.name for p in (out / 'responses').iterdir()} == {Path(n).name for n in report['files']}, 'EXTRA_RESPONSE_FILE')
    require(serialize_sector_radar_market_state(candidate).encode() == (out / 'candidate-state.json').read_bytes()
            and parse_sector_radar_market_state((out / 'candidate-state.json').read_text()).state_hash == report['candidate_state_hash']
            and missed == report['unobserved_event_sessions'], 'CANDIDATE_REBUILD_DIFFERS')
    require((out / 'candidate-events.json').read_bytes() == (root / 'input/candidate-events.json').read_bytes(), 'OLD_EVENTS_CHANGED')
    proof = {'status': 'ORIGINAL_SOURCE_AND_CANDIDATE_REBUILT', 'network_calls': 0,
        'report_hash': report['report_hash'], 'state_hash': candidate.state_hash,
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
            invocation(os.environ)
            binding = load(args.root / 'binding.json')
            require(binding['workflow'] == invocation(os.environ), 'BOUND_RUN_CHANGED')
            bundle = load_sector_radar_persistent_bundle(args.root / 'input', expected_repository=REPO, expected_workflow=PARENT_WORKFLOW)
            require(bundle.market_state.state_hash == binding['request']['parent']['state_hash'], 'PARENT_STATE_CHANGED')
            collect(args.root, bundle, binding['request'], api_key=os.environ.get(http.HITHINK_API_KEY_ENV))
        else:
            verify(args.root)
        print(args.operation + ': completed; NOT production recovery acceptance')
        return 0
    except Exception as exc:
        print(args.operation + ': FAILED_CLOSED / ' + type(exc).__name__ + '; inspect retained files; no retry')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
