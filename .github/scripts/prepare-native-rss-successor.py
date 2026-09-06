"""Workflow-only predecessor binding; reuse the existing feed verifier and CLI.

No HTTP, RSS parsing, source acceptance, latest-state search or queue is added.
A reviewed push request can continue a chain, never initialize/reset one.
"""
from __future__ import annotations

import argparse
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import radar_feed_intake as intake

REPOSITORY = 'auguspp/decision-kernel'
WORKFLOW = 'economic-release-discovery'
WORKFLOW_PATH = '.github/workflows/economic-release-discovery.yml'
REQUEST_PATH = Path('radar_inputs/native-rss-successor-request.json')
PIN_FIELDS = {'previous_run_id', 'previous_commit', 'artifact_id', 'artifact_sha256',
              'capture_hash', 'registry_hash'}
CONTEXT_KEYS = ('GITHUB_REPOSITORY', 'GITHUB_WORKFLOW', 'GITHUB_REF',
                'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_SHA')


def number(value):
    if not isinstance(value, str) or not re.fullmatch(r'[1-9][0-9]{0,19}', value):
        raise ValueError('exact decimal run/artifact identity required')
    return value


def hash_value(value, length=64):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{'+str(length)+'}', value):
        raise ValueError('exact hash identity required')
    return value


def resolve(env, declaration=None, *, now):
    context = {key: env.get(key) for key in CONTEXT_KEYS}
    if (context['GITHUB_REPOSITORY'] != REPOSITORY or context['GITHUB_WORKFLOW'] != WORKFLOW
            or context['GITHUB_REF'] != 'refs/heads/main' or context['GITHUB_RUN_ATTEMPT'] != '1'):
        raise ValueError('fresh canonical main source workflow required')
    number(context['GITHUB_RUN_ID']); hash_value(context['GITHUB_SHA'], 40)
    event = env.get('SOURCE_EVENT')
    if event == 'push':
        intake._keys(declaration, {'schema_version', 'purpose', *PIN_FIELDS})
        if type(declaration['schema_version']) is not int or declaration['schema_version'] != 1:
            raise ValueError('unsupported explicit successor request')
        if not isinstance(declaration['purpose'], str) or not 1 <= len(declaration['purpose'].strip()) <= 1600:
            raise ValueError('continuation purpose required')
        for key in PIN_FIELDS:
            if key in {'previous_run_id', 'artifact_id'}: number(declaration[key])
            else: hash_value(declaration[key], 40 if key == 'previous_commit' else 64)
        previous, baseline = declaration['previous_run_id'], False
    elif event == 'workflow_dispatch':
        previous, baseline = env.get('PREVIOUS_RUN_ID', ''), env.get('BOOTSTRAP') == 'true'
        if bool(previous) == baseline:
            raise ValueError('exact predecessor OR explicit separate baseline required')
        if previous: number(previous)
        if declaration is not None: raise ValueError('manual input must not silently consume the push request')
    else:
        raise ValueError('unsupported source invocation')
    if previous == context['GITHUB_RUN_ID']: raise ValueError('a run cannot restore itself')
    value = {'workflow': context, 'event': event, 'explicit_baseline': baseline,
             'previous_run_id': previous, 'pinned_previous': declaration,
             'prepared_at': intake._clock(now).isoformat()}
    return {**value, 'preflight_hash': canonical_hash(value)}


def bind_metadata(preflight, run, listing):
    if preflight['explicit_baseline'] or not preflight['previous_run_id']:
        raise ValueError('baseline has no predecessor')
    if (type(run['id']) is not int or str(run['id']) != preflight['previous_run_id']
            or run['name'] != WORKFLOW or run['path'] != WORKFLOW_PATH
            or run['repository']['full_name'] != REPOSITORY or run['head_branch'] != 'main'
            or type(run['run_attempt']) is not int or run['run_attempt'] != 1
            or run['status'] != 'completed' or run['conclusion'] != 'success'
            or run['event'] not in {'push', 'workflow_dispatch'}):
        raise ValueError('predecessor run identity/status differs')
    hash_value(run['head_sha'], 40)
    if type(listing['total_count']) is not int or listing['total_count'] != len(listing['artifacts']):
        raise ValueError('complete predecessor artifact listing required')
    name = 'radar-feed-intake-' + preflight['previous_run_id'] + '-1'
    matches = [a for a in listing['artifacts'] if a['name'] == name]
    if len(matches) != 1: raise ValueError('exactly one native feed artifact required')
    artifact = matches[0]; relation = artifact['workflow_run']
    if (type(artifact['id']) is not int or artifact['expired'] is not False
            or type(artifact['size_in_bytes']) is not int or not 0 < artifact['size_in_bytes'] <= 32*1024*1024
            or relation['id'] != run['id'] or relation['head_branch'] != 'main'
            or relation['head_sha'] != run['head_sha']
            or relation['repository_id'] != run['repository']['id']
            or relation['head_repository_id'] != run['repository']['id']
            or intake._clock(artifact['expires_at']) <= intake._clock(preflight['prepared_at'])):
        raise ValueError('artifact is expired, oversized or belongs to another execution')
    number(str(artifact['id']))
    digest = artifact['digest']
    if not isinstance(digest, str) or not digest.startswith('sha256:'):
        raise ValueError('server artifact SHA-256 required')
    hash_value(digest[7:])
    pin = preflight['pinned_previous']
    if pin and (pin['artifact_id'] != str(artifact['id']) or pin['artifact_sha256'] != digest[7:]
                or pin['previous_commit'] != run['head_sha']):
        raise ValueError('actual predecessor differs from reviewed request')
    value = {'preflight_hash': preflight['preflight_hash'], 'previous_run_id': str(run['id']),
             'previous_commit': run['head_sha'], 'artifact_id': str(artifact['id']),
             'artifact_sha256': digest[7:], 'artifact_name': name}
    return {**value, 'binding_hash': canonical_hash(value)}


def verify_restored(preflight, binding, root, *, now):
    if (canonical_hash({k:v for k,v in preflight.items() if k != 'preflight_hash'}) != preflight['preflight_hash']
            or canonical_hash({k:v for k,v in binding.items() if k != 'binding_hash'}) != binding['binding_hash']
            or binding['preflight_hash'] != preflight['preflight_hash']
            or binding['previous_run_id'] != preflight['previous_run_id']):
        raise ValueError('preflight/metadata binding differs')
    checked = intake.verify_capture(root)
    receipt = intake.decode(intake._read(root / 'capture.json'))
    registry = intake.decode(intake._read(root / 'registry.json'))
    expected = {**preflight['workflow'], 'GITHUB_RUN_ID': binding['previous_run_id'],
                'GITHUB_SHA': binding['previous_commit']}
    if (checked['capture_status'] != 'COMPLETE_FEED_INTAKE'
            or receipt['provenance'] != 'PUBLIC_HTTP_CAPTURE' or receipt['workflow'] != expected):
        raise ValueError('restored original capture does not match successful remote execution')
    at = intake._clock(now)
    if not intake._clock(receipt['finished_at']) < intake._clock(preflight['prepared_at']) <= at:
        raise ValueError('predecessor must finish before this invocation, checked BEFORE requests')
    pin = preflight['pinned_previous']
    if pin and (pin['capture_hash'] != receipt['capture_hash'] or pin['registry_hash'] != registry['registry_hash']):
        raise ValueError('restored source identity differs from reviewed request')
    return {'status': 'EXACT_PREDECESSOR_REBUILT_BEFORE_REQUESTS', 'binding_hash': binding['binding_hash'],
            'capture_hash': receipt['capture_hash'], 'registry_hash': registry['registry_hash'],
            'verified_at': at.isoformat(), 'network_calls': 0, **intake.AUTHORITY}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['request', 'metadata', 'restore'])
    parser.add_argument('--root', type=Path, default=Path('native-rss-intake'))
    parser.add_argument('--previous', type=Path, default=Path('previous-native-rss/capture'))
    args = parser.parse_args(argv)
    try:
        intake._safe_path(args.root)
        if args.mode == 'request':
            args.root.mkdir(parents=True, exist_ok=False)
            declaration = intake.decode(intake._read(REQUEST_PATH)) if os.environ.get('SOURCE_EVENT') == 'push' else None
            value = resolve(os.environ, declaration, now=datetime.now(timezone.utc).isoformat())
            name = 'preflight.json'
            outputs = {'previous_run_id': value['previous_run_id'], 'baseline': str(value['explicit_baseline']).lower()}
        else:
            preflight = intake.decode(intake._read(args.root / 'preflight.json'))
            if args.mode == 'metadata':
                value = bind_metadata(preflight, intake.decode(intake._read(args.root / 'predecessor-run.json')),
                                      intake.decode(intake._read(args.root / 'predecessor-artifacts.json')))
                name, outputs = 'predecessor-binding.json', {'artifact_id': value['artifact_id']}
            else:
                value = verify_restored(preflight, intake.decode(intake._read(args.root / 'predecessor-binding.json')),
                                        args.previous, now=datetime.now(timezone.utc).isoformat())
                name, outputs = 'predecessor-verification.json', {}
        with (args.root / name).open('xb') as f: f.write(intake.data(value))
        if outputs:
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                for key, value in outputs.items(): f.write(f'{key}={value}\n')
        return 0
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as exc:
        print(canonical_json({'status': 'SOURCE_PREFLIGHT_REJECTED', 'error_type': type(exc).__name__}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
