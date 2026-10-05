"""Read a finite minute capture through the existing stock query and Collector."""
from __future__ import annotations

from pathlib import Path
import re
from tempfile import TemporaryDirectory
from zipfile import BadZipFile

from . import current_state as model
from . import stock_market_inputs as saved
from . import d_auction_minutes as minute
from .stock_market_input_reading import _identity

ERRORS = (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, ArithmeticError, BadZipFile)


def _reserve(collector, **kwargs):
    from .institutional_radar_reading import _reserve as reserve
    return reserve(collector, **kwargs)


def previous_reference(collector):
    """One proved previous file, not a guessed same-R link to absent bytes."""
    previous, commit = getattr(collector, 'previous', None), getattr(collector, 'previous_commit', None)
    if not previous or not commit:
        return None
    model.check(model.SHA.fullmatch(commit) is not None, 'minute prior reading identity')
    description = previous['research'].get('independent_stock_observations') or {}
    if not description.get('read_path'):
        return None
    _reserve(collector, calls=1, files=1)
    raw = collector.api.file(description['read_path'], commit); minute.bound(raw, description)
    old = saved.loads(raw).get('daily_market_inputs', {}).get('auction_minutes', {})
    if 'file' in old:
        model.check(old['file']['read_path'] == minute.PATH, 'minute previous detail path')
        return {'reading_commit': commit, 'file': old['file'],
                'meaning': 'PREVIOUS_READING_RESULT_NOT_CURRENT_SOURCE_SUCCESS'}
    retained = old.get('previous_result')
    if retained:
        description = retained['file']
        model.check(model.SHA.fullmatch(retained['reading_commit']) is not None
                    and description['read_path'] == minute.PATH
                    and type(description['bytes']) is int and 0 < description['bytes'] <= saved.MAX_REPORT
                    and re.fullmatch(r'[0-9a-f]{64}', description['sha256']) is not None
                    and model.SHA.fullmatch(description['git_blob']) is not None, 'minute carried prior locator')
    return retained


def read_saved(collector, baseline, *, run_query, retained_limit):
    before, cache = dict(collector.files), dict(collector.archive_cache)
    result = {'status': 'NO_SAVED_MINUTE_RUN_IN_QUERY', 'summary': '', 'latest_attempt': None,
              'new_source_requests': 0, 'previous_result': None}
    try:
        try:
            result['previous_result'] = previous_reference(collector)
        except ERRORS as exc:
            result['previous_result_gap'] = type(exc).__name__
        _reserve(collector, calls=3, files=2)
        # Supplied by the existing stock run query. Its failure never causes a
        # second query, a market call, or a silent search for an older success.
        runs = run_query['workflow_runs']
        model.check(isinstance(runs, list) and len(runs) <= 100
                    and type(run_query['total_count']) is int and run_query['total_count'] >= len(runs),
                    'minute shared run query')
        result['run_query_complete'] = run_query['total_count'] <= len(runs)
        candidates = [r for r in runs if r.get('display_title') == minute.TITLE]
        if not candidates:
            if result['previous_result']:
                result['summary'] = '\n09:40来源未出现在本次运行查询范围，既有结果从明确的前一读取版本恢复；不是无变化。\n'
            return result
        run = max(candidates, key=lambda r: (model.clock(r['created_at']), r['id']))
        result['latest_attempt'] = model.concise_run(run); _identity(run)
        model.check(run['event'] == 'workflow_dispatch' and type(run['run_attempt']) is int
                    and type(run['id']) is int and run['id'] > 0, 'minute native run identity')
        cutoff = model.clock(baseline['checks']['finished_at'])
        model.check(model.clock(run['created_at']) <= model.clock(run['updated_at']) <= cutoff, 'minute native clock')
        if run['status'] != 'completed':
            result.update(status='MINUTE_CAPTURE_PENDING', summary='\n09:40分钟采集尚未完成；已有日频/研究不受影响。\n')
            return result
        artifact = model.select_artifact(collector.artifacts(run), f'{minute.TITLE}-{run["id"]}-1')
        model.check(model.clock(artifact['expires_at']) > cutoff, 'minute capture artifact expired')
        files, archive = collector.archive(artifact, run)
        expected = minute.workflow_identity({'GITHUB_REPOSITORY': model.REPOSITORY,
            'GITHUB_REF': 'refs/heads/main', 'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_JOB': minute.JOB,
            'GITHUB_EVENT_NAME': run['event'], 'GITHUB_WORKFLOW_REF': model.REPOSITORY+'/'+minute.WORKFLOW+'@refs/heads/main',
            'GITHUB_SHA': run['head_sha'], 'GITHUB_RUN_ID': str(run['id'])})
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name, body in files.items():
                path = root/model.safe_path(name); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(body)
            report = minute.verify(root, expected_workflow=expected)
        model.check(report['provenance'] == 'LIVE_FTSHARE' and
                    model.clock(run['run_started_at']) <= model.clock(report['observed_at']) <=
                    model.clock(report['received_through']) <= model.clock(run['updated_at']), 'minute capture provenance/clock')
        raw, summary = minute.encode(report), minute.render(report)
        summary += f"\n原生来源运行结论：{run['conclusion']}；来源字段可读不改写原运行结论。\n"
        model.check(len(raw) <= saved.MAX_REPORT and len(summary.encode()) <= saved.MAX_REPORT and
                    sum(map(len, collector.files.values())) + len(raw) + 2*len(summary.encode()) + 24*1024 <= retained_limit,
                    'minute reading byte capacity')
        _reserve(collector, files=2)
        result.update(status=report['status'], market_session=report['market_session'],
            capture_timing=report['capture_timing'], received_through=report['received_through'],
            cohort_denominator=report['cohort_denominator'], observed_0940=report['observed_0940'],
            source_archive=archive, file=collector.retain(minute.PATH, raw), summary=summary,
            publication_verification='REBUILT_FROM_RETAINED_RESPONSE_BYTES', source_stop=report['source_stop'],
            investment_authority='NONE')
    except ERRORS as exc:
        collector.files, collector.archive_cache = before, cache
        result.update(status='MINUTE_READING_GAP_NOT_QUIET', error_type=type(exc).__name__,
                      summary='\n09:40分钟结果本次未能恢复，不是空扫描；原竞价、日线、研究和前一结果保持。\n')
    return result
