"""Read the daily stock artifact through the existing Collector; no source I/O."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import BadZipFile

from . import current_state as model
from . import current_state_delivery as delivery
from . import stock_market_inputs as inputs

PATH = 'details/stock/daily-market-inputs.json'
LAST_PATH = 'details/stock/last-qualified-market-inputs.json'
ERRORS = (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, BadZipFile)


def _read_current_prices(collector, baseline):
    old_files, old_cache = dict(collector.files), dict(collector.archive_cache)
    result = {'status': 'DAILY_INPUT_NOT_AVAILABLE_NOT_QUIET', 'source': inputs.SOURCE,
              'market_session': None, 'latest_attempt': None, 'new_source_requests': 0,
              'summary': '日常个股输入尚未取得；下方历史样本不是当前扫描。'}
    matches, run = [], None
    try:
        api = collector.api
        reserve = len(set(collector.files) | {PATH, 'current-state.json', 'README.md'}) + 12
        model.check(api.calls + reserve + 4 <= api.max_calls, 'daily stock reading publication reserve')
        # Share this native query with the independent auction reader. An
        # attempted-but-failed query is not permission to retry it in a sibling.
        result['_run_query'] = {}
        query = api.get('actions/workflows/stock-reading-after-sector.yml/runs?branch=main&per_page=100')
        result['_run_query'] = query
        runs = query['workflow_runs']
        model.check(isinstance(runs, list) and len(runs) <= 100, 'daily stock run list')
        matches = [r for r in runs if r.get('display_title') == inputs.TITLE]
        result['run_query_complete'] = query.get('total_count', len(runs)) <= len(runs)
        if not matches:
            return result
        run = max(matches, key=lambda r: (model.clock(r['created_at']), r['id']))
        result['latest_attempt'] = model.concise_run(run)
        _identity(run)
        if run['status'] != 'completed':
            result.update(status='DAILY_INPUT_ATTEMPT_PENDING', summary='日常个股输入正在执行；尚无本次结果。')
        else:
            report, archive, descriptor = _read_run(collector, baseline, run, PATH)
            result.update(status=report['status'], market_session=report['market_session'],
                received_through=report['received_through'], source_archive=archive, file=descriptor,
                cohort_denominator=report['cohort_denominator'], qualified_windows=report['qualified_windows'],
                summary=inputs.render(report) + '\n[本次完整证券表、逐期限缺口与来源](details/stock/daily-market-inputs.json)。\n',
                acquisition='CURRENT_CALENDAR_DATED_CROSS_SECTIONS_WITHOUT_SECTOR_DEPENDENCY',
                publication_verification='REBUILT_FROM_EXACT_RETAINED_RESPONSE_BYTES',
                investment_authority='NONE')
    except ERRORS as exc:
        collector.files, collector.archive_cache = old_files, old_cache
        result.update(status='DAILY_INPUT_READING_GAP_NOT_QUIET', error_type=type(exc).__name__,
            summary='本次日常个股输入未能读回；不把旧结果或空白当成当前市场无变化。')
    # Keep the latest failure/pending state intact. Read one prior successful
    # artifact separately; no endpoint mixing or search past a damaged candidate.
    if not any(result.get('qualified_windows', {}).values()) and matches and run is not None:
        candidates = [r for r in matches if r['id'] != run['id']
                      and r.get('status') == 'completed' and r.get('conclusion') == 'success'
                      and (model.clock(r['created_at']), r['id']) < (model.clock(run['created_at']), run['id'])]
        if candidates:
            candidate = max(candidates, key=lambda r: (model.clock(r['created_at']), r['id']))
            saved_files, saved_cache = dict(collector.files), dict(collector.archive_cache)
            try:
                reserve = len(set(collector.files) | {LAST_PATH, 'current-state.json', 'README.md'}) + 12
                model.check(collector.api.calls + reserve + 3 <= collector.api.max_calls,
                            'saved daily stock publication reserve')
                report, archive, descriptor = _read_run(collector, baseline, candidate, LAST_PATH)
                model.check(any(report['qualified_windows'].values()), 'saved daily stock has no usable window')
                saved = {'status': 'VERIFIED_SAVED_INPUT_NOT_LATEST_ATTEMPT',
                    'origin_run': model.concise_run(candidate), 'file': descriptor, 'source_archive': archive,
                    'market_session': report['market_session'], 'received_through': report['received_through'],
                    'cohort_denominator': report['cohort_denominator'], 'qualified_windows': report['qualified_windows'],
                    'publication_verification': 'REBUILT_FROM_EXACT_RETAINED_RESPONSE_BYTES',
                    'new_source_requests': 0, 'investment_authority': 'NONE'}
                result['last_qualified_result'] = saved
                note = ('\n\n## 最近已验证可用输入（保留原日期）\n\n'
                    f"最新尝试状态：{result['status']}。以下来自较早采集，不表示最新尝试成功。\n"
                    f"原采集完成：{report['received_through']}；"
                    f"[原运行]({candidate['html_url']})。按原市场日使用，不能当作更新交易日的行情。\n\n")
                result['summary'] += note + inputs.render(report).replace('# 日常个股输入', '### 已保存的日常个股输入', 1)
                result['summary'] += '\n[最近可用完整证券表及缺口](details/stock/last-qualified-market-inputs.json)。\n'
            except ERRORS as exc:
                collector.files, collector.archive_cache = saved_files, saved_cache
                result['last_qualified_reading_gap'] = {'origin_run': model.concise_run(candidate),
                    'status': 'SAVED_INPUT_UNAVAILABLE', 'error_type': type(exc).__name__}
                result['summary'] += '\n最近成功运行的保存输入未能校验；未继续倒找更旧成功。\n'
    # D is a read-only derivation over these exact retained inputs. A missing
    # membership/structure source cannot cancel any qualified price window.
    from .d_market_expression import read_saved
    result['market_expression'] = read_saved(collector, baseline, result)
    result['summary'] += result['market_expression']['summary']
    return result


def _identity(run):
    model.check(run['path'] == inputs.WORKFLOW and run['head_branch'] == 'main'
                and run['event'] in ('schedule', 'workflow_dispatch') and run['run_attempt'] == 1
                and model.SHA.fullmatch(run['head_sha']) is not None, 'daily stock run identity')
    for field in ('repository', 'head_repository'):
        model.check(run[field]['full_name'] == model.REPOSITORY, 'daily stock repository identity')


def _read_run(collector, baseline, run, output_path):
    _identity(run)
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
    descriptor = collector.retain(output_path, raw)
    return report, archive, descriptor


def read_current(collector, baseline):
    """Independent saved purposes share the existing run query, not data gates."""
    result = _read_current_prices(collector, baseline)
    from .d_auction_reading import read_saved as read_auction
    query = result.pop('_run_query', None)
    auction = read_auction(collector, baseline, run_query=query)
    result['auction_probe'] = auction
    result['summary'] += auction['summary']
    from .d_auction_follow_through import read_saved as read_follow_through
    outcome = read_follow_through(collector, baseline, result, auction,
                                  retained_limit=delivery.MAX_RETAINED_OUTPUT)
    result['auction_follow_through'] = outcome
    result['summary'] += outcome['summary']
    return result
