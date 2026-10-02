"""Publish the existing independent sample from this collection's saved bytes.

No source request, second selector, retry, historical scan or production admission.
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
    result['report_hash'] = canonical_hash(result)
    return result


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
