"""Publish saved independent inputs, preserving the historical sample contract.

The normal publisher additionally reads current dated stock inputs when enabled.
Neither reader makes source requests; current inputs do not depend on Sector.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Context, Decimal, InvalidOperation, localcontext
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import BadZipFile

from decision_kernel.identity import canonical_hash, canonical_json
from . import current_state as model

KEY = 'independent_stock_observations'
PATH = 'details/stock/independent-observations.json'
MAX_DETAIL_BYTES = 512 * 1024
ERRORS = (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, BadZipFile)


def _cached(collector, reference, checked_at):
    """Only a currently validated Collector cache entry; never fetch a missing one."""
    files, original = collector.archive_cache[reference['artifact_id']]
    model.check(original == reference, 'independent source cache identity differs')
    model.check(model.clock(reference['expires_at']) > model.clock(checked_at), 'independent source expired')
    raw = collector.files[model.safe_path(reference['read_path'])]
    model.check(len(raw) == reference['bytes'] and model.sha256(raw) == reference['sha256']
                and model.blob_sha(raw) == reference['git_blob'], 'independent retained archive differs')
    run = reference['origin_run']
    artifact = {'expired': False, 'digest': 'sha256:' + reference['sha256'],
        'size_in_bytes': reference['bytes'],
        'workflow_run': {'id': run['id'], 'head_sha': run['head_sha']}}
    # The expiration check above and exact current-cache match are prerequisites,
    # not an assertion that any historical copy is a live restoration source.
    rebuilt = model.unpack_archive(raw, artifact, run)
    model.check(rebuilt == files, 'independent cached archive bytes differ')
    return files


def _restore(files, prefix, manifest_name, root):
    """Restore only inventory-bound data in a fresh private temporary directory."""
    raw = files[prefix + manifest_name]
    manifest = json.loads(raw)
    model.check(isinstance(manifest['files'], dict), 'independent inventory missing')
    for name, descriptor in manifest['files'].items():
        model.safe_path(name)
        body = files[prefix + name]
        model.check(len(body) == descriptor['bytes'] and model.sha256(body) == descriptor['sha256'],
                    'independent input inventory differs')
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    target = root / manifest_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return manifest


def derive(collector, baseline):
    from . import independent_stock_observations as independent

    sector = baseline['lanes'].get('sector', {})
    stock = baseline['lanes'].get('stock', {})
    last = sector.get('last_qualified_result') or {}
    attempt = sector.get('latest_attempt') or {}
    failed = (attempt.get('operation') or {}).get('source') if attempt.get('conclusion') == 'failure' else None
    reference = failed or last.get('archive')
    result = {'version': 'independent-stock-saved-reading-v1',
        'status': 'INPUT_UNAVAILABLE_NOT_QUIET', 'checked_at': baseline['checks']['finished_at'],
        'code_commit': collector.code_commit, 'source': reference, 'stock_source': None,
        'source_selection': 'LATEST_FAILED_ATTEMPT_INPUTS' if failed else 'EXISTING_LAST_QUALIFIED_SOURCE',
        'latest_sector_attempt': attempt, 'latest_stock_attempt': stock.get('latest_attempt'),
        'source_lane_gaps': {'sector': sector.get('gaps', []), 'stock': stock.get('gaps', [])},
        'acquisition': 'SECTOR_OWNED_NOT_UNCONDITIONAL_DAILY_INDEPENDENT_CAPTURE',
        'new_source_requests': 0, 'new_read_requests': 0, 'production_admission': False,
        'observations': None, 'gaps': [], **model.AUTHORITY}
    phase = 'SOURCE_ARCHIVE'
    try:
        files = _cached(collector, reference, result['checked_at'])
        with TemporaryDirectory() as directory:
            root = Path(directory)
            phase = 'ALL_MARKET_INPUTS'
            manifest = _restore(files, 'input-audit/', 'manifest.json', root / 'audit')
            # The expected pin comes from bytes bound to the externally verified
            # archive above, not from the new derived output.
            options = {'expected_audit_hash': manifest['audit_hash']}
            report = independent.build(root / 'audit', **options)
            if not failed:
                model.check(report['context']['comparison_session'] == last['market_session'],
                            'independent comparison session differs from selected source')
            original_stock = stock.get('last_qualified_result') or {}
            if original_stock.get('market_session') == report['context']['comparison_session']:
                try:
                    own_files = _cached(collector, original_stock['archive'], result['checked_at'])
                    own = _restore(own_files, 'reading/', 'capture.json', root / 'stock')
                    model.check(own['capture_hash'] == original_stock['capture_hash'],
                                'independent stock source pin differs')
                    enriched = independent.build(root / 'audit', **options, stock_root=root / 'stock',
                        expected_capture_hash=original_stock['capture_hash'])
                    model.check(enriched['selection'] == report['selection'], 'history changed independent selection')
                    report = enriched
                    result['stock_source'] = original_stock['archive']
                except ERRORS as exc:
                    result['gaps'].append({'phase': 'OPTIONAL_OWN_HISTORY', 'error_type': type(exc).__name__,
                        'meaning': 'QUOTE_SAMPLE_RETAINED_HISTORY_NOT_QUALIFIED'})
            else:
                result['gaps'].append({'phase': 'OPTIONAL_OWN_HISTORY', 'meaning': 'NO_SAME_SESSION_STOCK_SOURCE'})
            result.update(status='SAVED_INPUT_SAMPLE_WITH_EXPLICIT_GAPS', observations=report)
    except ERRORS as exc:
        result['gaps'].append({'phase': phase, 'error_type': type(exc).__name__,
                              'meaning': 'MISSING_OR_REJECTED_INPUT_NOT_EMPTY_SCAN'})
    result['summary'] = (independent.render(result['observations']) if result['observations'] else
        '独立观察输入未取得或未通过原资格检查；不是空扫描，也不是市场无变化。')
    # This fixed retained cohort is a saved-reading supplement, not a new daily
    # producer. Never carry its September comparison into a different session.
    if result['observations'] and result['observations']['context']['comparison_session'] == '2026-09-30':
        before = getattr(collector.api, 'calls', 0)
        old_files, old_cache = dict(collector.files), dict(collector.archive_cache)
        try:
            comparison = saved_tushare_comparison(collector, result['observations'], result['checked_at'])
            result['price_comparison'] = comparison
            result['summary'] += '\n\n' + render_intervals(comparison['interval_performance'])
        except ERRORS as exc:
            collector.files, collector.archive_cache = old_files, old_cache
            result['price_comparison'] = {'status': 'SAVED_PRICE_INPUT_REJECTED_NOT_QUIET',
                'error_type': type(exc).__name__, 'no_older_gap_success_fallback': True}
        after = getattr(collector.api, 'calls', before)
        result['new_read_requests'] = after-before
    if os.environ.get('INCLUDE_CURRENT_STOCK_INPUTS') == '1':
        from .stock_market_input_reading import read_current
        before = getattr(collector.api, 'calls', 0)
        current = read_current(collector, baseline)
        result['daily_market_inputs'] = current
        result['historical_sample_status'] = result['status']
        result['historical_sample_acquisition'] = result['acquisition']
        result['status'] = current['status']
        result['acquisition'] = current.get('acquisition', 'DAILY_INPUT_ATTEMPT_NOT_AVAILABLE')
        result['preferred_current_input'] = 'daily_market_inputs'
        result['summary'] = current['summary'] + '\n\n## 历史独立样本（保留原日期）\n' + result['summary']
        result['new_read_requests'] += getattr(collector.api, 'calls', before) - before
    result['report_hash'] = canonical_hash(result)
    return result



def saved_tushare_comparison(collector, observation, checked_at):
    """Use the existing Collector's native archive/readback, never its source key."""
    from . import tushare_c2_price_check as price
    api = collector.api
    reserve = len(set(collector.files) | {'current-state.json', PATH, 'README.md'}) + 12
    model.check(api.calls + reserve + 6 <= api.max_calls, 'saved price publication reserve')
    data = api.get('actions/workflows/hithink-stock-dump-trial.yml/runs?branch=main&per_page=20')
    rows = data['workflow_runs']
    model.check(isinstance(rows, list) and len(rows) <= 20 and (rows or data['total_count'] == 0),
                'saved price run query incomplete')
    candidates = [r for r in rows if r.get('display_title') == price.GAP_TITLE]
    latest = max(candidates, key=lambda r: (model.clock(r['created_at']), r['id']), default=None)
    gap_ready = latest is not None and latest.get('status') == 'completed' and latest.get('conclusion') == 'success'
    # Never discard a newer rejected gap result in search of an older success.
    run = latest if gap_ready else api.get(f'actions/runs/{price.BASE_RUN}')
    mode = price.GAP_MODE if gap_ready else price.MODE
    model.run_identity(run, 'stock', success=True)
    model.check(run['event'] == 'workflow_dispatch' and run['display_title'] ==
                (price.GAP_TITLE if gap_ready else price.TITLE), 'saved price purpose differs')
    if not gap_ready:
        model.check(run['id'] == price.BASE_RUN and run['head_sha'] == price.BASE_COMMIT, 'saved base run differs')
    artifact = model.select_artifact(collector.artifacts(run), f"{mode}-{run['id']}-1")
    model.check(model.clock(artifact['expires_at']) > model.clock(checked_at), 'saved price artifact expired')
    files, archive = collector.archive(artifact, run)
    expected = {'GITHUB_REPOSITORY': model.REPOSITORY, 'GITHUB_REF': 'refs/heads/main',
        'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'GITHUB_JOB': price.MODE, 'TRIAL_PURPOSE': mode, 'GITHUB_SHA': run['head_sha'], 'GITHUB_RUN_ID': str(run['id'])}
    with TemporaryDirectory() as directory:
        root = Path(directory)
        for name, raw in files.items():
            target = root/model.safe_path(name); target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        if gap_ready:
            proof = price.verify_gaps(root, expected_identity=expected)
        else:
            model.check(artifact['id'] == price.BASE_ARTIFACT and artifact['digest'] == 'sha256:'+price.BASE_ZIP_SHA256
                        and artifact['size_in_bytes'] == price.BASE_BYTES, 'saved base artifact differs')
            proof = price.verify(root, expected_identity=expected)
    report = price.raw_json(files['report.json']); ref = report['reference']
    model.check(ref['sessions'] == observation['context']['sessions'] and
        ref['symbols'] == [r['thscode'] for r in observation['selected_observations']] and
        ref['selection_hash'] == observation['selection']['selection_hash'], 'saved price cohort differs')
    inventory = observation['inventory']; columns = inventory['columns']
    closes = {r[columns.index('thscode')]: r[columns.index('last_price')] for r in inventory['rows']}
    model.check(all(price.number(ref['end_closes'][code]) == price.number(closes[code])
                    for code in ref['symbols']), 'saved price end quotes differ')
    receipt = price.raw_json(files['receipt.json'])
    return {'status': 'VERIFIED_SAVED_COHORT_PRICE_COMPARISON', 'source': 'THIRD_PARTY_TUSHARE_RELAY',
        'market_session': ref['sessions'][-1], 'received_through': receipt['finished_at'],
        'cohort_denominator': report['cohort_denominator'], 'qualified_windows': report['qualified_windows'],
        'observations': report['observations'], 'factor_repair': report.get('factor_repair'),
        'source_stop': receipt['stopped'], 'latest_gap_attempt': model.concise_run(latest),
        'gap_reading': 'LATEST_COMPLETED_GAP_INPUT' if gap_ready else 'ORIGINAL_ONLY_NO_COMPLETED_SUCCESSFUL_GAP_INPUT',
        'source_archive': archive, 'verification': proof,
        'interval_performance': _interval_performance(files, report, proof),
        'comparison_basis': 'PROVIDER_FACTOR_ADJUSTED_PRICE_NOT_TOTAL_RETURN',
        'corporate_action_details': 'NOT_OBTAINED', 'pit_knowledge': 'NOT_ESTABLISHED',
        'daily_acquisition': 'NOT_ESTABLISHED', 'subset_not_full_member_ranking': True,
        'investment_authority': 'NONE'}


def _interval_performance(files, original, proof):
    """A use-specific interpretation AFTER the caller verifies the original capture.

    Acquisition, the legacy full-window verifier/report and source stops remain
    unchanged. A close-to-close ratio uses only its two prices and two factors;
    it does not certify daily OHLC/volume, drawdown, total return, PIT or roles.
    """
    from . import tushare_c2_price_check as price
    receipt = price.raw_json(files['receipt.json'])
    ref = original['reference']
    if receipt['version'] == price.GAP_VERSION:
        parent = price.original_input(files['original.zip'])
        tables = parent['tables']
        # Reuse the exact, already replay-verified repair's row locators, rather
        # than implementing another factor merger or filling absent dates.
        calls = {a['response_file']: call for call in receipt['calls']
                 for a in call['attempts'] if a['response_file'] is not None}
        parsed = {}
        for item in original['factor_repair']['filled_keys']:
            name = item['response_file']
            if name not in parsed:
                call = calls[name]
                parsed[name] = price.table(files[name], call['api'], call['params'])
            row = parsed[name][item['row_position']]
            model.check(row['ts_code'] == item['symbol'] and row['trade_date'] == item['trade_date'],
                        'saved interval repair row differs')
            tables[2 + 2*ref['symbols'].index(item['symbol'])].append(row)
    else:
        tables = {i: price.table(files[call['attempts'][-1]['response_file']], call['api'], call['params'])
                  for i, call in enumerate(receipt['calls']) if call['status'] == 'SUCCESS'}
    snapshot = {r['ts_code']: r for r in tables.get(0, [])}
    days = [d.replace('-', '') for d in ref['sessions']]
    rows = []
    for k, code in enumerate(ref['symbols']):
        bars = {r['trade_date']: r for r in tables.get(1 + 2*k, [])}
        factors = {r['trade_date']: r for r in tables.get(2 + 2*k, [])}
        windows = {}
        for n in (5, 20, 60):
            endpoints = [days[-n-1], days[-1]]
            value = {'base_session': ref['sessions'][-n-1], 'end_session': ref['sessions'][-1],
                'status': 'ENDPOINT_INPUT_UNAVAILABLE', 'price_change': None,
                'missing_price_dates': [d for d in endpoints if d not in bars],
                'missing_factor_dates': [d for d in endpoints if d not in factors],
                'legacy_full_window_status': original['observations'][k]['windows'][str(n)]['status']}
            windows[str(n)] = value
            if value['missing_price_dates'] or value['missing_factor_dates'] or code not in snapshot:
                continue
            try:
                start, end = (price.number(bars[d]['close']) for d in endpoints)
                start_factor, end_factor = (price.number(factors[d]['adj_factor']) for d in endpoints)
                model.check(end == price.number(snapshot[code]['close']) == price.number(ref['end_closes'][code]),
                            'saved interval end quote differs')
                with localcontext(Context(prec=28)):
                    change = end * end_factor / (start * start_factor) - 1
                value.update(status='PROVIDER_ADJUSTED_INTERVAL_COMPARABLE', price_change=str(change),
                    base_raw_close=str(start), end_raw_close=str(end),
                    base_factor=str(start_factor), end_factor=str(end_factor))
            except (ValueError, TypeError, KeyError, InvalidOperation):
                value['status'] = 'ENDPOINT_VALUE_OR_REFERENCE_REJECTED'
        rows.append({'symbol': code, 'windows': windows})
    return {'version': 'c2-price-purpose-qualification-v2',
        'source': 'THIRD_PARTY_TUSHARE_RELAY', 'market_session': ref['sessions'][-1],
        'cohort_denominator': len(rows), 'observations': rows,
        'qualified_windows': {str(n): sum(r['windows'][str(n)]['price_change'] is not None for r in rows)
                              for n in (5, 20, 60)},
        'legacy_full_window_qualified': original['qualified_windows'],
        'source_report_sha256': proof['report_sha256'], 'source_stop': receipt['stopped'],
        'received_through': receipt['finished_at'],
        'formula': 'end_close * end_factor / (base_close * base_factor) - 1',
        'use': 'INTERVAL_PRICE_PERFORMANCE_ONLY_NOT_CONTINUOUS_PATH',
        'basis': 'PROVIDER_FACTOR_ADJUSTED_PRICE_NOT_TOTAL_RETURN',
        'corporate_action_details': 'NOT_OBTAINED', 'pit_knowledge': 'NOT_ESTABLISHED',
        'role_inference': 'NOT_GRANTED', 'new_source_requests': 0,
        'investment_authority': 'NONE'}


def render_intervals(result):
    """Plain reading of each selected security, including the unavailable ones."""
    counts, old, total = result['qualified_windows'], result['legacy_full_window_qualified'], result['cohort_denominator']
    lines = [f"截至{result['market_session']}的供应商口径区间表现：5/20/60日分别"
             f"{counts['5']}/{counts['20']}/{counts['60']}只可比（各分母{total}）。",
             f"原完整逐日检查分别{old['5']}/{old['20']}/{old['60']}只通过；"
             '缺中间数据不否定已核实的两端涨跌幅，但不能据此描述完整走势、回撤或领先角色。',
             '', '| 证券 | 5日 | 20日 | 60日 |', '|---|---:|---:|---:|']
    with localcontext(Context(prec=28)):
        for row in result['observations']:
            values = [row['windows'][str(n)]['price_change'] for n in (5, 20, 60)]
            shown = ['不可比' if v is None else format(Decimal(v), '+.2%') for v in values]
            lines.append('| ' + row['symbol'] + ' | ' + ' | '.join(shown) + ' |')
    lines += ['', '不可比项保留在分母中，具体缺端点或数值问题见 interval_performance；'
              '原逐日缺口和来源失败见原 price_comparison。不是总回报、当前行情或新增采集。']
    return '\n'.join(lines)


def attach(collector, baseline):
    """One compact descriptor; preserve the existing root/retention/API bounds."""
    from . import current_state_delivery as delivery

    model.validate_read_package(baseline)
    model.check(collector.code_commit == baseline['code_commit'], 'independent consumer code differs')
    result = derive(collector, baseline)
    raw = (canonical_json(result) + '\n').encode()
    payload = deepcopy(baseline)
    note = ('\n\n## 独立个股观察（已保存输入）\n\n'
        '[完整分母、独立样本与输入缺口](details/stock/independent-observations.json)。'
        '先读 status、summary、coverage 和 selected_observations；输入仍有自己的市场日。'
        '样本选择不依赖行业入选，不代表已建立每日独立采集、全市场多周期或研究受益。\n').encode()
    intervals = result.get('price_comparison', {}).get('interval_performance')
    if intervals:
        note += ('\n' + render_intervals(intervals) + '\n').encode()
    if result.get('daily_market_inputs'):
        current = result['daily_market_inputs']
        note = ('\n\n' + current['summary'] + '\n\n## 历史样本（保留原日期）\n').encode() + note
    descriptor = {'read_path': PATH, 'sha256': model.sha256(raw), 'git_blob': model.blob_sha(raw),
        'bytes': len(raw), 'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}
    try:
        model.check(len(raw) <= MAX_DETAIL_BYTES, 'independent detail bound')
        payload['research'][KEY] = descriptor
        payload['reading_hash'] = canonical_hash({k: v for k, v in payload.items() if k != 'reading_hash'})
        entry = model.read_package_bytes(payload)
        total = sum(len(v) for k, v in collector.files.items() if k not in ('current-state.json', PATH))
        model.check(total + len(entry) + len(raw) + len(note) <= delivery.MAX_RETAINED_OUTPUT,
                    'independent retained byte bound')
        limit = getattr(collector.api, 'max_calls', delivery.MAX_API_CALLS)
        model.check(collector.api.calls + len(set(collector.files) | {PATH, 'current-state.json', 'README.md'}) + 5 <= limit,
                    'independent publication reserve')
    except ERRORS:
        # Keep other lanes available. This explicit small failure entry does not
        # inherit a prior descriptor or suggest that the old sample is current.
        payload = deepcopy(baseline)
        payload['research'][KEY] = {'status': 'NOT_PUBLISHED_CAPACITY_GAP_NOT_QUIET'}
        payload['reading_hash'] = canonical_hash({k: v for k, v in payload.items() if k != 'reading_hash'})
        entry = model.read_package_bytes(payload)
        note = b'\n\nIndependent stock observations: NOT_PUBLISHED_CAPACITY_GAP_NOT_QUIET.\n'
        total = sum(len(v) for k, v in collector.files.items() if k != 'current-state.json')
        model.check(total + len(entry) + len(note) <= delivery.MAX_RETAINED_OUTPUT,
                    'independent failure note exceeds retained byte bound')
    else:
        collector.retain(PATH, raw)
    model.validate_read_package(payload)
    collector.files['current-state.json'] = entry
    collector.files['README.md'] += note
    return payload
