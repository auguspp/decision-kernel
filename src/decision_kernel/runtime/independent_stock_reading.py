"""Publish the existing independent sample from this collection's saved bytes.

No source request, second selector, retry, unbounded historical scan or production admission.
Acquisition is still Sector-owned; missing pages/history remain explicit gaps.
"""
from __future__ import annotations

from copy import deepcopy
import json
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
            n = comparison['qualified_windows']
            result['summary'] += (f'\n\n同一保存16名的独立Tushare复权价格比较：5/20/60日'
                f"分别{n['5']}/{n['20']}/{n['60']}名合格（各分母16）。"
                '详见price_comparison；原HiThink覆盖/失败保持，不是新交易日或每日独立采集证明。')
        except ERRORS as exc:
            collector.files, collector.archive_cache = old_files, old_cache
            result['price_comparison'] = {'status': 'SAVED_PRICE_INPUT_REJECTED_NOT_QUIET',
                'error_type': type(exc).__name__, 'no_older_gap_success_fallback': True}
        after = getattr(collector.api, 'calls', before)
        result['new_read_requests'] = after-before
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
        'comparison_basis': 'PROVIDER_FACTOR_ADJUSTED_PRICE_NOT_TOTAL_RETURN',
        'corporate_action_details': 'NOT_OBTAINED', 'pit_knowledge': 'NOT_ESTABLISHED',
        'daily_acquisition': 'NOT_ESTABLISHED', 'subset_not_full_member_ranking': True,
        'investment_authority': 'NONE'}


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
