"""Optional auction reading in the existing publisher, with no market calls."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import BadZipFile

from . import current_state as model
from . import current_state_delivery as delivery
from . import d_auction_probe as probe

QUERY = 'actions/workflows/stock-reading-after-sector.yml/runs?branch=main&per_page=100'
ERRORS = (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, BadZipFile)


def read_saved(collector, baseline, *, run_query=None):
    """Use a native saved run; a local failure cannot remove daily stock inputs."""
    previous_files, previous_cache = dict(collector.files), dict(collector.archive_cache)
    result = {'status': 'NO_SAVED_AUCTION_RUN_IN_QUERY', 'latest_attempt': None,
              'new_source_requests': 0, 'summary': ''}
    try:
        reserve = len(set(collector.files) | {probe.PATH, 'current-state.json', 'README.md'}) + 12
        model.check(collector.api.calls + reserve + 4 <= collector.api.max_calls, 'auction publication reserve')
        # Reuse the daily reader's actual query even for API implementations
        # without memoization; no second GET or retry after a failed sibling GET.
        query = collector.api.get(QUERY) if run_query is None else run_query
        runs = query['workflow_runs']
        model.check(isinstance(runs, list) and len(runs) <= 100 and type(query['total_count']) is int
                    and query['total_count'] >= len(runs), 'auction run query')
        result['run_query_complete'] = query['total_count'] <= len(runs)
        matches = [r for r in runs if r.get('display_title') == probe.TITLE]
        if not matches:
            return result
        run = max(matches, key=lambda r: (model.clock(r['created_at']), r['id']))
        result['latest_attempt'] = model.concise_run(run)
        expected = probe.workflow_identity({'GITHUB_REPOSITORY': model.REPOSITORY,
            'GITHUB_REF': 'refs/heads/main', 'GITHUB_RUN_ATTEMPT': str(run['run_attempt']),
            'GITHUB_JOB': probe.JOB, 'GITHUB_EVENT_NAME': run['event'],
            'GITHUB_WORKFLOW_REF': model.REPOSITORY+'/'+probe.WORKFLOW+'@refs/heads/main',
            'GITHUB_SHA': run['head_sha'], 'GITHUB_RUN_ID': str(run['id'])})
        model.check(type(run['run_attempt']) is int and run['run_attempt'] == 1 and
                    type(run['id']) is int and run['path'] == probe.WORKFLOW and run['head_branch'] == 'main',
                    'auction native run identity')
        for key in ('repository', 'head_repository'):
            model.check(run[key]['full_name'] == model.REPOSITORY, 'auction native repository identity')
        cutoff = model.clock(baseline['checks']['finished_at'])
        model.check(model.clock(run['created_at']) <= model.clock(run['updated_at']) <= cutoff,
                    'auction native run clock')
        if run['status'] != 'completed':
            result.update(status='AUCTION_ATTEMPT_PENDING', summary='\n集合竞价输入本次仍在执行，尚无可读结果。\n')
            return result
        artifact = model.select_artifact(collector.artifacts(run), f'{probe.TITLE}-{run["id"]}-1')
        model.check(model.clock(artifact['expires_at']) > cutoff, 'auction artifact expired')
        files, archive = collector.archive(artifact, run)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name, raw in files.items():
                path = root/model.safe_path(name); path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            report = probe.verify(root, expected_workflow=expected, qualify_temperature=True)
        model.check(report['provenance'] == 'LIVE_TUSHARE_RELAY' and
                    model.clock(run['run_started_at']) <= model.clock(report['observed_at']) <=
                    model.clock(report['received_through']) <= model.clock(run['updated_at']), 'auction provenance or clock')
        raw = probe.saved.dumps(report); summary = probe.render(report)
        model.check(len(raw) <= probe.MAX_REPORT and len(summary.encode()) <= 256*1024 and
                    sum(map(len, collector.files.values())) + len(raw) + 2*len(summary.encode()) + 24*1024
                    <= delivery.MAX_RETAINED_OUTPUT, 'auction retained byte bound')
        model.check(collector.api.calls + len(set(collector.files) |
                    {probe.PATH, 'current-state.json', 'README.md'}) + 12 <= collector.api.max_calls,
                    'auction publication reserve')
        result.update(status=report['status'], market_session=report['market_session'],
                      previous_session=report['previous_session'], timeliness=report['timeliness'],
                      cohort_denominator=report['cohort_denominator'], comparable=report['comparable'],
                      matched=report['matched'], source_archive=archive, file=collector.retain(probe.PATH, raw),
                      summary='\n\n'+summary, investment_authority='NONE',
                      publication_verification='REBUILT_FROM_RETAINED_RESPONSE_BYTES')
    except ERRORS as exc:
        collector.files, collector.archive_cache = previous_files, previous_cache
        result.update(status='AUCTION_READING_GAP_NOT_QUIET', error_type=type(exc).__name__,
                      summary='\n集合竞价本次未能读回；不是空扫描，原日常价格和已保存研究保持。\n')
    return result
