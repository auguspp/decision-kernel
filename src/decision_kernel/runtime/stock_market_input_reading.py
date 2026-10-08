"""Read the daily stock artifact through the existing Collector; no source I/O."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import BadZipFile

from . import current_state as model
from . import current_state_delivery as delivery
from . import stock_market_inputs as inputs

PATH = 'details/stock/daily-market-inputs.json'
LAST_PATH = 'details/stock/last-qualified-market-inputs.json'
ERRORS = (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, BadZipFile)



def _factor_coverage_attention(report):
    """Read-only row-count contrast, not a diagnosis of the upstream cause."""
    coverage = report.get('source_row_coverage') or {}
    gaps = []
    for window, base in (report.get('bases') or {}).items():
        if base is None:
            continue
        prices = coverage.get('daily:' + base) or {}
        factors = coverage.get('adj_factor:' + base) or {}
        p, f = prices.get('returned_rows'), factors.get('returned_rows')
        if (prices.get('status') == factors.get('status') == 'SOURCE_ROWS_READ'
                and type(p) is int and type(f) is int and f < p):
            gaps.append({'window': window, 'base_date': base, 'price_rows': p, 'factor_rows': f,
                         'status': 'FACTOR_ROWS_FEWER_THAN_DATE_PRICE_ROWS'})
    return gaps



SKIP_REASONS = frozenset({'SOURCE_ALREADY_RETAINED_THIS_CLOSE_DATE',
                          'OTHER_SOURCE_ATTEMPT_UNCERTAIN',
                          'OUTSIDE_AUTHORIZED_AFTER_CLOSE_WINDOW',
                          'RUN_QUERY_SCOPE_INCOMPLETE'})


def _declared_no_source_skip(collector, run):
    """Distinguish a signed-by-originated-workflow no-source artifact from missing data."""
    if run['status'] != 'completed':
        return None
    artifacts = collector.artifacts(run)
    source_name = f'{inputs.TITLE}-{run["id"]}-1'
    skip_name = f'{inputs.TITLE}-skip-{run["id"]}-1'
    if not any(item['name'] == skip_name for item in artifacts):
        return None
    model.check(not any(item['name'] == source_name for item in artifacts),
                'source and skip artifact conflict')
    artifact = model.select_artifact(artifacts, skip_name)
    previous_files, previous_cache = dict(collector.files), dict(collector.archive_cache)
    try:
        files, _ = collector.archive(artifact, run)
        model.check(set(files) == {'skip.json'} and len(files['skip.json']) <= 2048,
                    'invalid no-source receipt inventory')
        obj = json.loads(files['skip.json'])
        model.check(
            isinstance(obj, dict)
            and obj.get('version') == 'daily-stock-native-skip-v1'
            and obj.get('repository') == model.REPOSITORY
            and obj.get('run_id') == run['id']
            and obj.get('head_sha') == run['head_sha']
            and obj.get('reason') in SKIP_REASONS
            and obj.get('source_requests') == 0
            and (obj.get('prior_run_id') is None
                 or type(obj['prior_run_id']) is int and obj['prior_run_id'] > 0)
            and model.clock(obj['recorded_at']) is not None,
            'invalid declared no-source receipt identity')
    finally:
        collector.files, collector.archive_cache = previous_files, previous_cache
    return {'run_id': run['id'], 'reason': obj['reason'],
            'prior_run_id': obj.get('prior_run_id'), 'source_requests': 0}


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
        matches = sorted((r for r in runs if r.get('display_title') == inputs.TITLE),
                         key=lambda r: (model.clock(r['created_at']), r['id']), reverse=True)
        result['run_query_complete'] = query.get('total_count', len(runs)) <= len(runs)
        if not matches:
            return result
        suppressed = []
        for possible in matches[:6]:
            marker = _declared_no_source_skip(collector, possible)
            if marker is not None:
                suppressed.append(marker)
                continue
            run = possible
            break
        if suppressed:
            result['source_capture_suppressed'] = suppressed
            skipped_ids = {m['run_id'] for m in suppressed}
            matches = [r for r in matches if r['id'] not in skipped_ids]
        if run is None:
            result.update(status='SOURCE_ATTEMPT_NOT_FOUND_AFTER_BOUNDED_SKIP_RESOLUTION',
                summary='原收盘时钟出现无来源请求回执；本次至多六条跳过记录后未取得实际输入。')
            return result
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
            attention = _factor_coverage_attention(report)
            if attention:
                result['source_coverage_attention'] = attention
                for gap in attention:
                    result['summary'] += (
                        f"\n来源覆盖注意：{gap['base_date']}日{gap['window']}日基期复权因子返回"
                        f"{gap['factor_rows']}条，同日价格返回{gap['price_rows']}条；"
                        "尚未证明是供应商截断、停牌或条件不满足。\n")
    except ERRORS as exc:
        collector.files, collector.archive_cache = old_files, old_cache
        result.update(status='DAILY_INPUT_READING_GAP_NOT_QUIET', error_type=type(exc).__name__,
            summary='本次日常个股输入未能读回；不把旧结果或空白当成当前市场无变化。')
    # Keep latest status and usable windows; read-only archive recovery is
    # bounded by source qualification, never a cross-run price/factor splice.
    if matches and run is not None and (not any(result.get('qualified_windows', {}).values())
                                        or result.get('source_coverage_attention')):
        candidates = [r for r in matches if r['id'] != run['id']
                      and r.get('status') == 'completed' and r.get('conclusion') == 'success'
                      and (model.clock(r['created_at']), r['id']) < (model.clock(run['created_at']), run['id'])]
        ordered = sorted(candidates, key=lambda r: (model.clock(r['created_at']), r['id']), reverse=True)
        # Keep the original single-candidate guard for fully unavailable inputs.
        # When some windows survive but a dated factor cross-section shrinks,
        # examine at most three valid-but-inferior older artifacts of the same
        # market session. Never skip an invalid, expired, or damaged candidate.
        limit = 3 if result.get('source_coverage_attention') and any(
            result.get('qualified_windows', {}).values()) else 1
        checks = []
        for candidate in ordered[:limit]:
            saved_files, saved_cache = dict(collector.files), dict(collector.archive_cache)
            try:
                reserve = len(set(collector.files) | {LAST_PATH, 'current-state.json', 'README.md'}) + 12
                model.check(collector.api.calls + reserve + 3 <= collector.api.max_calls,
                            'saved daily stock publication reserve')
                report, archive, descriptor = _read_run(collector, baseline, candidate, LAST_PATH)
                model.check(any(report['qualified_windows'].values()), 'saved daily stock has no usable window')
                latest_usable = any(result.get('qualified_windows', {}).values())
                affected_windows = {gap['window'] for gap in result.get('source_coverage_attention', [])}
                if latest_usable and result.get('market_session') != report['market_session']:
                    collector.files, collector.archive_cache = saved_files, saved_cache
                    checks.append({'run_id': candidate['id'], 'status': 'DIFFERENT_MARKET_SESSION_STOP'})
                    break
                eligible = (not latest_usable or
                    any(report['qualified_windows'][window] > result['qualified_windows'][window]
                        for window in affected_windows))
                if not eligible:
                    collector.files, collector.archive_cache = saved_files, saved_cache
                    checks.append({'run_id': candidate['id'], 'status': 'VALID_BUT_NOT_BETTER',
                                   'qualified_windows': report['qualified_windows']})
                    continue
                saved = {'status': 'VERIFIED_SAVED_INPUT_NOT_LATEST_ATTEMPT',
                    'origin_run': model.concise_run(candidate), 'file': descriptor, 'source_archive': archive,
                    'market_session': report['market_session'], 'received_through': report['received_through'],
                    'cohort_denominator': report['cohort_denominator'], 'qualified_windows': report['qualified_windows'],
                    'publication_verification': 'REBUILT_FROM_EXACT_RETAINED_RESPONSE_BYTES',
                    'new_source_requests': 0, 'investment_authority': 'NONE'}
                saved['selection_reason'] = ('SAME_SESSION_WINDOW_COVERAGE_IMPROVEMENT' if latest_usable
                                             else 'LATEST_INPUT_HAS_NO_USABLE_WINDOW')
                result['last_qualified_result'] = saved
                note = ('\n\n## 最近已验证可用输入（保留原日期）\n\n'
                    f"最新尝试状态：{result['status']}。以下来自较早采集，不表示最新尝试成功。\n"
                    f"原采集完成：{report['received_through']}；"
                    f"[原运行]({candidate['html_url']})。按原市场日使用，不能当作更新交易日的行情。\n\n")
                result['summary'] += note + inputs.render(report).replace(
                    '# 日常个股输入', '### 已保存的日常个股输入', 1)
                result['summary'] += '\n[最近可用完整证券表及缺口](details/stock/last-qualified-market-inputs.json)。\n'
                if latest_usable:
                    result['summary'] += ('旧批只是同一市场日较完整期限的独立参照；'
                                          '最新批其余合格期限仍有效，两批证券/因子不拼接。\n')
                checks.append({'run_id': candidate['id'], 'status': 'QUALIFIED_REFERENCE_SELECTED',
                               'qualified_windows': report['qualified_windows']})
                break
            except ERRORS as exc:
                collector.files, collector.archive_cache = saved_files, saved_cache
                checks.append({'run_id': candidate['id'], 'status': 'SAVED_INPUT_UNAVAILABLE_STOP',
                               'error_type': type(exc).__name__})
                result['last_qualified_reading_gap'] = {'origin_run': model.concise_run(candidate),
                    'status': 'SAVED_INPUT_UNAVAILABLE', 'error_type': type(exc).__name__}
                result['summary'] += '\n较早保存输入未能校验，已停止；不越过受损候选继续搜索。\n'
                break
        if checks:
            result['last_qualified_checks'] = checks
            if not result.get('last_qualified_result') and not result.get('last_qualified_reading_gap'):
                result['last_qualified_comparison'] = (
                    'NO_IMPROVING_SAME_SESSION_WINDOW_WITHIN_BOUNDED_VERIFIED_CANDIDATES')
    # D is a read-only derivation over these exact retained inputs. A missing
    # membership/structure source cannot cancel any qualified price window.
    from .d_market_expression import read_saved
    result['market_expression'] = read_saved(collector, baseline, result)
    result['summary'] += result['market_expression']['summary']
    return result


def _identity(run):
    model.check(run['path'] == inputs.WORKFLOW and run['head_branch'] == 'main'
                and run['event'] in ('schedule', 'workflow_dispatch', 'workflow_run') and run['run_attempt'] == 1
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
    from .d_auction_minute_reading import read_saved as read_minutes
    minutes = read_minutes(collector, baseline, run_query=query if query is not None else {},
                           retained_limit=delivery.MAX_RETAINED_OUTPUT)
    result['auction_minutes'] = minutes
    result['summary'] += minutes['summary']
    return result
