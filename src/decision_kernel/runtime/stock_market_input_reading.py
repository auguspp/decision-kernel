"""Read the daily stock artifact through the existing Collector; no source I/O."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import BadZipFile

from . import current_state as model
from . import current_state_delivery as delivery
from . import stock_market_inputs as inputs

PATH = 'details/stock/daily-market-inputs.json'


def read_current(collector, baseline):
    old_files, old_cache = dict(collector.files), dict(collector.archive_cache)
    result = {'status': 'DAILY_INPUT_NOT_AVAILABLE_NOT_QUIET', 'source': inputs.SOURCE,
              'market_session': None, 'latest_attempt': None, 'new_source_requests': 0,
              'summary': '日常个股输入尚未取得；下方历史样本不是当前扫描。'}
    try:
        api = collector.api
        reserve = len(set(collector.files) | {PATH, 'current-state.json', 'README.md'}) + 12
        model.check(api.calls + reserve + 4 <= api.max_calls, 'daily stock reading publication reserve')
        query = api.get('actions/workflows/stock-reading-after-sector.yml/runs?branch=main&per_page=100')
        runs = query['workflow_runs']
        model.check(isinstance(runs, list) and len(runs) <= 100, 'daily stock run list')
        matches = [r for r in runs if r.get('display_title') == inputs.TITLE]
        if not matches:
            return result
        run = max(matches, key=lambda r: (model.clock(r['created_at']), r['id']))
        result['latest_attempt'] = model.concise_run(run)
        model.check(run['path'] == inputs.WORKFLOW and run['head_branch'] == 'main'
                    and run['event'] in ('schedule', 'workflow_dispatch') and run['run_attempt'] == 1
                    and model.SHA.fullmatch(run['head_sha']) is not None, 'daily stock run identity')
        for field in ('repository', 'head_repository'):
            model.check(run[field]['full_name'] == model.REPOSITORY, 'daily stock repository identity')
        if run['status'] != 'completed':
            result.update(status='DAILY_INPUT_ATTEMPT_PENDING', summary='日常个股输入正在执行；未用旧样本冒充本次结果。')
            return result
        artifact = model.select_artifact(collector.artifacts(run), f'{inputs.TITLE}-{run["id"]}-1')
        model.check(model.clock(artifact['expires_at']) > model.clock(baseline['checks']['finished_at']),
                    'daily stock input artifact expired')
        files, archive = collector.archive(artifact, run)
        expected = {'GITHUB_REPOSITORY': model.REPOSITORY, 'GITHUB_REF': 'refs/heads/main',
            'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_JOB': 'daily-market-inputs', 'GITHUB_EVENT_NAME': run['event'],
            'GITHUB_WORKFLOW_REF': model.REPOSITORY+'/'+inputs.WORKFLOW+'@refs/heads/main',
            'GITHUB_SHA': run['head_sha'], 'GITHUB_RUN_ID': str(run['id'])}
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name, raw in files.items():
                path = root/model.safe_path(name); path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            report = inputs.verify(root, expected_workflow=expected)
        model.check(report['provenance'] == 'LIVE_TUSHARE_RELAY', 'synthetic data is not live stock input')
        raw = inputs.dumps(report)
        model.check(len(raw) <= inputs.MAX_REPORT, 'daily stock detail byte bound')
        model.check(sum(map(len, collector.files.values())) + len(raw) + 24*1024 <= delivery.MAX_RETAINED_OUTPUT,
                    'daily stock retained byte bound')
        descriptor = collector.retain(PATH, raw)
        result.update(status=report['status'], market_session=report['market_session'],
            received_through=report['received_through'], source_archive=archive, file=descriptor,
            cohort_denominator=report['cohort_denominator'], qualified_windows=report['qualified_windows'],
            summary=inputs.render(report) + '\n[本次完整证券表、逐期限缺口与来源](details/stock/daily-market-inputs.json)。\n',
            acquisition='CURRENT_CALENDAR_DATED_CROSS_SECTIONS_WITHOUT_SECTOR_DEPENDENCY',
            publication_verification='REBUILT_FROM_EXACT_RETAINED_RESPONSE_BYTES',
            investment_authority='NONE')
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, BadZipFile) as exc:
        collector.files, collector.archive_cache = old_files, old_cache
        result.update(status='DAILY_INPUT_READING_GAP_NOT_QUIET', error_type=type(exc).__name__,
            summary='本次日常个股输入未能读回；不把旧结果或空白当成当前市场无变化。')
    return result
