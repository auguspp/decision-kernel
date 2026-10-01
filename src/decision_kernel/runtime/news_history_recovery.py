"""Read one bounded native predecessor for News; never fetch news or write GitHub.

The latest attempt is retained even when an older successful capture supplies
history. Failure/corruption does not prompt another archive attempt or disappear
behind a new success. The existing API transport and ZIP verifier own bytes.
"""
from __future__ import annotations

import argparse
import os
import zipfile
from pathlib import Path

import requests

from . import current_state as m
from . import current_state_delivery as delivery
from . import news_daily as source

QUERY = 'actions/workflows/radar-newsnow-daily.yml/runs?branch=main&per_page=20'


def recover(api, current_run_id, *, clock=source.now):
    m.check(type(current_run_id) is int and current_run_id > 0, 'News recovery current run required')
    receipt = {'version': 'news-history-recovery-v1', 'current_run_id': current_run_id,
               'checked_at': clock(), 'query_limit': 20, 'status': 'NO_PRIOR_CAPTURE',
               'latest_prior_attempt': None, 'selected_capture': None,
               'newer_unusable_attempts': [], 'archive': None, 'history_sha256': None,
               'history_origin': None, 'error_type': None,
               'meaning': 'VERIFIED_NATIVE_PREDECESSOR_INDEX_NOT_FULL_HISTORICAL_HTTP_REPLAY'}
    raw_history = None
    try:
        current = api.get('actions/runs/' + str(current_run_id))
        source.saved_run_identity(current, clock())
        m.check(current['id'] == current_run_id, 'News recovery current run differs')
        bound = (m.clock(current['created_at']), current_run_id)
        result = api.get(QUERY); runs = result['workflow_runs']
        m.check(isinstance(runs, list) and len(runs) <= 20 and type(result['total_count']) is int
                and result['total_count'] >= len(runs) and (runs or result['total_count'] == 0)
                and len({r['id'] for r in runs}) == len(runs), 'News recovery run page incomplete')
        prior = sorted((r for r in runs if (m.clock(r['created_at']), r['id']) < bound),
                       key=lambda r: (m.clock(r['created_at']), r['id']), reverse=True)
        for run in prior:
            source.saved_run_identity(run, clock())
        if prior:
            receipt['latest_prior_attempt'] = m.concise_run(prior[0])
            selected = next((r for r in prior if r['status'] == 'completed'
                             and r['conclusion'] == 'success'), None)
            receipt['newer_unusable_attempts'] = [m.concise_run(r) for r in prior
                if selected is None or (m.clock(r['created_at']), r['id']) >
                                       (m.clock(selected['created_at']), selected['id'])]
            if selected is None:
                receipt['status'] = 'NO_SUCCESS_IN_WINDOW'
            else:
                run = api.get('actions/runs/' + str(selected['id']))
                source.saved_run_identity(run, clock())
                m.check(all(run[k] == selected[k] for k in ('id', 'head_sha', 'created_at', 'event', 'run_attempt'))
                        and run['status'] == 'completed' and run['conclusion'] == 'success',
                        'News recovery predecessor changed')
                receipt['selected_capture'] = m.concise_run(run)
                data = api.get('actions/runs/' + str(run['id']) + '/artifacts?per_page=100')
                m.check(type(data['total_count']) is int and data['total_count'] == len(data['artifacts'])
                        and len(data['artifacts']) <= 100, 'News recovery artifact enumeration incomplete')
                artifact = m.select_artifact(data['artifacts'], 'newsnow-daily-' + str(run['id']) + '-1')
                raw = api.archive(artifact)
                files = m.unpack_archive(raw, artifact, run)
                captured = source.news._decode(files['observations.json'])
                rebuilt = source.rebuild(files, cutoff=captured['projection']['captured_through'], run=run)
                m.check(captured == rebuilt, 'News recovery raw replay differs')
                history = source.replay_history(files, rebuilt)
                raw_history = files.get(source.HISTORY_FILE, m.json_bytes(history))
                m.check(0 < len(raw_history) <= source.MAX_HISTORY_BYTES, 'News recovered history byte budget')
                receipt.update(status='RESTORED', history_sha256=m.sha256(raw_history),
                    history_origin='NATIVE_HISTORY_BYTES' if source.HISTORY_FILE in files else 'LEGACY_CAPTURE_BOOTSTRAP',
                    archive={k: artifact.get(k) for k in ('id', 'name', 'size_in_bytes', 'digest', 'expires_at')})
    except (*source.ERRORS, requests.RequestException, AttributeError, IndexError, zipfile.BadZipFile) as exc:
        raw_history = None
        receipt.update(status='RECOVERY_REJECTED', history_sha256=None, history_origin=None,
                       error_type=type(exc).__name__)
    receipt['checked_at'] = clock()
    return raw_history, receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    env = os.environ
    m.check(env['GITHUB_REPOSITORY'] == m.REPOSITORY and env['GITHUB_REF'] == 'refs/heads/main'
            and env['GITHUB_RUN_ATTEMPT'] == '1', 'News recovery host identity differs')
    # A read-only token, five bounded API calls, no source/provider credentials.
    api = delivery.GitHubAPI(env['GH_TOKEN'], max_calls=5)
    history, receipt = recover(api, int(env['GITHUB_RUN_ID']))
    args.output.mkdir(parents=True, exist_ok=False)
    source._write(args.output, source.RECOVERY_FILE, m.json_bytes(receipt))
    if history is not None:
        source._write(args.output, source.HISTORY_INPUT, history)
    print('NEWS_HISTORY_RECOVERY=' + receipt['status'])
    return 0  # A visible history gap must not prevent this run's independent news capture.


if __name__ == '__main__':
    raise SystemExit(main())
