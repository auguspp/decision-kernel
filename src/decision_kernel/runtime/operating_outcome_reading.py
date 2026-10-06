"""Optional D2 projection of already retained reviews in the existing publisher.

Git reads only; no archived Python, issuer request, price dependency or new clock.
"""
from __future__ import annotations

from copy import deepcopy

from decision_kernel.identity import canonical_hash, canonical_json
from . import current_state as model
from . import operating_outcomes as outcomes
from .institutional_radar_reading import _reserve

CONFIG = 'decision_inputs/d-operating-outcomes.json'
KEY = 'd_operating_outcomes'
PATH = 'details/research/operating-outcomes.json'
ERRORS = (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, ArithmeticError)


def _source(collector, spec):
    """Reuse calendar/horizon's bounded optional cache scope, not a new quota."""
    _reserve(collector, calls=1, files=3)
    cache = collector.sources
    key = (spec['path'], spec.get('ref', collector.code_commit))
    collector.sources = {key: cache[key]} if key in cache else {}
    try:
        return collector.source(spec)
    finally:
        collector.sources = cache


def _navigation(collector, baseline, entry):
    records = [r for r in baseline['research']['records'] if r['id'] == entry['navigation_id']]
    model.check(len(records) == 1 and records[0]['use'] == 'NAVIGATION_ONLY', 'outcome existing navigation')
    descriptor = records[0]['source']
    raw = collector.files[descriptor['read_path']]
    outcomes.bound(raw, descriptor)
    spec = entry['sources']['review']
    link = f"https://github.com/{model.REPOSITORY}/blob/{spec['ref']}/{spec['path']}"
    model.check(link in raw.decode('utf-8'), 'outcome review not in declared existing navigation')
    return descriptor


def _publish(collector, baseline, report, *, retained_limit):
    checked = collector.now()
    model.check(model.clock(checked) >= model.clock(baseline['checks']['finished_at']), 'outcome publication clock')
    report = {**report, 'checked_at': checked, **model.AUTHORITY}
    report['report_hash'] = canonical_hash(report)
    raw = (canonical_json(report) + '\n').encode()
    model.check(len(raw) <= outcomes.MAX_BYTES, 'outcome detail capacity')
    descriptor = {'read_path': PATH, 'bytes': len(raw), 'sha256': model.sha256(raw),
                  'git_blob': model.blob_sha(raw), 'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}
    research = deepcopy(baseline['research']); research[KEY] = descriptor
    payload = model.assemble(code_commit=baseline['code_commit'], checked_at=checked,
        check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
        capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
    updates = {PATH: raw, 'current-state.json': model.read_package_bytes(payload),
               'README.md': collector.files['README.md'] + outcomes.render(report).encode() +
                            f'\n[D2完整比较、各项时钟及来源限制]({PATH})。\n'.encode()}
    model.check(sum(map(len, {**collector.files, **updates}.values())) <= retained_limit, 'outcome total capacity')
    _reserve(collector, replacements=updates)
    collector.files.update(updates)
    return payload


def attach(collector, baseline, *, retained_limit):
    before, cache = dict(collector.files), dict(collector.sources)
    phase = 'DECLARATION'
    try:
        model.validate_read_package(baseline)
        model.check(collector.code_commit == baseline['code_commit'], 'outcome code identity')
        raw, config_ref = _source(collector, {'path': CONFIG})
        config = outcomes.loads(raw)
        cases = config['cases']
        model.check(config['version'] == outcomes.VERSION and isinstance(cases, list) and
                    0 <= len(cases) <= 8, 'outcome bounded selection')
        model.check(len({c['id'] for c in cases}) == len(cases) and
                    len({c['event_id'] for c in cases}) == len(cases), 'outcome duplicate review or event')
        items = []
        for entry in cases:
            saved, sources = dict(collector.files), dict(collector.sources)
            phase = 'NAVIGATION'
            try:
                navigation = _navigation(collector, baseline, entry)
                phase = 'SELECTED_RETAINED_SOURCES'
                files, refs = {}, {}
                for key in ('inputs', 'notes', 'review'):
                    spec = entry['sources'][key]
                    files[key], refs[key] = _source(collector, {k: spec[k] for k in ('path', 'ref', 'git_blob')})
                    outcomes.bound(files[key], spec)
                phase = 'RETAINED_COMPARISON'
                item = outcomes.review(entry, files, checked_at=collector.now())
                item.update(retained_files=refs, navigation_source=navigation)
                item['report_hash'] = canonical_hash({k:v for k,v in item.items() if k != 'report_hash'})
            except ERRORS as exc:
                collector.files, collector.sources = saved, sources
                item = {'id': entry.get('id'), 'subject': entry.get('subject'), 'event_id': entry.get('event_id'),
                        'status': 'RETAINED_OUTCOME_UNAVAILABLE_NOT_ECONOMIC_FAILURE',
                        'phase': phase, 'error_type': type(exc).__name__, 'difference': None,
                        'probability_score': None, **model.AUTHORITY}
            items.append(item)
        phase = 'PUBLICATION'
        report = {'version': outcomes.VERSION, 'code_commit': collector.code_commit, 'config': config_ref,
                  'items': items, 'selected_events': len(cases),
                  'compared_events': sum(i['status'] == 'RETAINED_REVIEW_COMPARED' for i in items),
                  'source_or_comparison_gap_events': sum(i['status'] != 'RETAINED_REVIEW_COMPARED' for i in items),
                  'independent_forecast_sample_count': None, 'pooled_score': None,
                  'ai_forecast_score': None, 'method_effectiveness': None,
                  'new_market_requests': 0, 'new_model_calls': 0, 'new_attention_events': 0,
                  'automatic_method_change': False}
        return _publish(collector, baseline, report, retained_limit=retained_limit)
    except ERRORS as exc:
        collector.files, collector.sources = before, cache
        # Even failure is a visible current disposition; never an empty-success list.
        gap = {'version': outcomes.VERSION, 'code_commit': collector.code_commit,
               'items': [{'id': 'operating-outcomes', 'status': 'RETAINED_OUTCOME_UNAVAILABLE_NOT_ECONOMIC_FAILURE',
                          'phase': phase, 'error_type': type(exc).__name__}],
               'selected_events': None, 'compared_events': None, 'pooled_score': None,
               'new_market_requests': 0, 'new_model_calls': 0, 'new_attention_events': 0,
               'automatic_method_change': False}
        try:
            return _publish(collector, baseline, gap, retained_limit=retained_limit)
        except ERRORS:
            collector.files, collector.sources = before, cache
            return baseline
