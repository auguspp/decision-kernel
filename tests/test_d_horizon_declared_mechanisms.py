"""Finite multi-case integration; all clocks/quotes/I/O here are synthetic.

Retires with the declared-case reader; not economic acceptance or live use.
"""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import d_horizon_follow_up as h
from decision_kernel.runtime import d_delivery_reading as joint
from decision_kernel.runtime import research_archive_index as index
from decision_kernel.runtime import stock_market_inputs as p
from test_d_horizon_follow_up import AT, SOURCE, case, parts, seeded


def test_explicit_null_long_date_is_not_a_synthetic_valuation_date():
    c = case(); c['long_research_deadline'] = None
    result = h.project(c, *parts(), checked_at=AT, source=SOURCE)
    assert result['long_research_deadline'] is None
    assert result['anchor_session'] == '2026-10-08'
    assert result['opportunity_probability'] is None
    note = h.render({'checked_at': AT, 'latest_price_status': 'SYNTHETIC',
                     'cases': [result], 'case_bodies': [{'read_path': 'source.md'}]})
    assert '期限未在本声明单独设定' in note
    assert '长期Research期限：None' not in note
    old = case()
    assert h.project(old, *parts(), checked_at=AT, source=SOURCE)['long_research_deadline'] == '2027-09-02'
    with pytest.raises(ValueError, match='contract changed'):
        h.project(old, *parts(), checked_at=AT, source=SOURCE, previous=result)


@pytest.mark.parametrize('value', ['', 'UNKNOWN', '2027-02-30', '20270902', False, 0, []])
def test_non_date_is_not_silently_an_absent_date(value):
    with pytest.raises(ValueError):
        h._long_deadline_assertion(value)


def multi(monkeypatch, tmp_path, occupied=60, remove_marker=False, corrupt=False):
    """Existing price/registry/quota seams, actual Collector.source/retain/binding."""
    original, root = seeded(monkeypatch)
    raw, _ = original.source({'path': h.CONFIG})
    first = p.loads(raw)['cases'][0]
    template = deepcopy(index.read_entries(root['research'], original.files.__getitem__)[0])
    cases, records, documents = [], [], {}
    for i, symbol in enumerate(('603986.SH', '600233.SH', '600598.SH', '688337.SH')):
        c = deepcopy(first)
        if i:
            c.update(id=f'case-{i}', record_id=f'retained-case-{i}', symbol=symbol,
                     frozen_at='2026-10-07T01:00:00Z', long_research_deadline=None)
            c['interpretation'] = {'intermediate': f'Explicit hypothesis {i}',
                                   'invalidation': f'Explicit counterevidence {i}'}
        long_text = h._long_deadline_assertion(c['long_research_deadline'])
        body = '\n'.join([symbol, c['frozen_at'], c['analyst_review_by'], long_text,
                          *c['interpretation'].values()]).encode()
        if remove_marker and i == 1:
            body = body.replace(long_text.encode(), b'Unrelated source words')
        c['document_sha256'] = model.sha256(body)
        c['source_assertions'] = [symbol, c['frozen_at']]
        record = deepcopy(template)
        record.update(id=c['record_id'], case=symbol)
        path = f'docs/readings/synthetic-case-{i}/README.md'
        record['source'].update(path=path, ref='c'*40, bytes=len(body),
            git_blob=model.blob_sha(body), sha256=model.sha256(body))
        cases.append(c); records.append(record); documents[path] = body
    calls = []
    def read_file(path, ref):
        calls.append((path, ref))
        assert ref == 'c'*40
        return documents[path] + (b'changed' if corrupt and 'case-1/' in path else b'')
    collector = delivery.Collector(SimpleNamespace(calls=0, max_calls=500, file=read_file),
                                   'a'*40, tmp_path, now=lambda: AT)
    collector.files, collector.archive_cache = dict(original.files), original.archive_cache
    collector.sources = {(f'docs/base-{i}.md', 'a'*40): (b'baseline', {}) for i in range(occupied)}
    before = deepcopy(collector.sources)
    native_source = collector.source
    def source(spec):
        if spec['path'] == h.CONFIG:
            config = p.dumps({'version': h.VERSION, 'cases': cases})
            return config, collector.retain('sources/multi-config.json', config)
        return native_source(spec)
    collector.source = source
    monkeypatch.setattr(index, 'read_entries', lambda *args, **kwargs: records)
    return collector, root, cases, before, calls


@pytest.mark.parametrize('occupied', [0, 59, 60])
def test_four_distinct_cases_fit_without_evicting_baseline_or_inventing_prices(monkeypatch, tmp_path, occupied):
    collector, root, declared, before, calls = multi(monkeypatch, tmp_path, occupied)
    output = h.attach(collector, root, retained_limit=20*1024*1024)
    model.validate_read_package(output)
    report = p.loads(collector.files[h.PATH]); h._bound(collector.files[h.PATH], output['research'][h.KEY])
    assert [r['id'] for r in report['cases']] == [c['id'] for c in declared]
    assert [r['contract_hash'] for r in report['cases']] == [canonical_hash(c) for c in declared]
    assert [r['long_research_deadline'] for r in report['cases']] == ['2027-09-02', None, None, None]
    assert all(r['opportunity_established'] is None for r in report['cases'])
    assert all(r['historical_price_context']['row'] is None for r in report['cases'][1:])
    assert all(point['change'] is None for r in report['cases'][1:] for point in r['checkpoints'])
    assert output['lanes'] == root['lanes'] and output['research']['records'] == root['research']['records']
    assert collector.sources == before and len(calls) == 4 and delivery.MAX_SOURCE_FILES == 60
    # The real downstream projection must consume exactly what the producer sealed.
    joined = joint.build(output, collector.files, checked_at=AT)
    component = joined['components'][0]
    assert component['status'] == 'VERIFIED_SAME_READING_COMPONENT'
    assert component['data']['cases'] == report['cases']
    text = joint.render(joined)
    assert '本声明未单设（不覆盖原长期研究）' in text and '2027-09-02' in text
    assert all(c['symbol'] in text for c in declared)
    assert joined['pooled_score'] is None and joined['new_source_requests'] == 0
    # A correctly sealed but structurally invalid producer still cannot pass.
    for key, value in (('symbol', None), ('frozen_at', None), ('analyst_review_by', None),
                       ('long_research_deadline', False), ('long_research_deadline', 0),
                       ('long_research_deadline', [])):
        invalid = deepcopy(report); invalid['cases'][1][key] = value
        invalid['report_hash'] = canonical_hash({k: v for k, v in invalid.items() if k != 'report_hash'})
        raw = p.dumps(invalid)
        descriptor = {'read_path': h.PATH, 'bytes': len(raw), 'sha256': model.sha256(raw),
                      'git_blob': model.blob_sha(raw),
                      'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}
        rejected = joint.component({h.KEY: descriptor}, {h.PATH: raw}, joint.COMPONENTS[0],
                                   code_commit=collector.code_commit, checked_at=AT)
        assert rejected['status'] == 'COMPONENT_READ_GAP'


@pytest.mark.parametrize('damage', ['undeclared_null', 'changed_source'])
def test_bad_new_declaration_does_not_publish_qualified_cases_or_erase_other_products(monkeypatch, tmp_path, damage):
    collector, root, _, before, _ = multi(monkeypatch, tmp_path,
        remove_marker=damage == 'undeclared_null', corrupt=damage == 'changed_source')
    original = dict(collector.files)
    output = h.attach(collector, root, retained_limit=20*1024*1024)
    assert h.PATH not in collector.files
    assert output['research'][h.KEY]['phase'] == 'CASE_BODY'
    assert collector.sources == before and output['lanes'] == root['lanes']
    for name, value in original.items():
        if name not in ('README.md', 'current-state.json'):
            assert collector.files[name] == value


def test_real_configuration_keeps_original_case_and_binds_three_new_mechanisms():
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / h.CONFIG).read_bytes())
    assert canonical_hash(config['cases'][0]) == '0ea868b1888753dce6d1a9021cf69116d8cb30b78bcb6b01f194077636450656'
    new = config['cases'][1:]
    assert len(new) == 3 and {c['symbol'] for c in new} == {'600233.SH', '600598.SH', '688337.SH'}
    registry = json.loads((root / 'current_state/registry.json').read_bytes())
    entries = {r['id']: r for r in registry['references']}
    for c in new:
        record = entries[c['record_id']]; entry = index.project(record)
        assert entry['case'] == c['symbol'] and c['long_research_deadline'] is None
        assert c['checkpoints'] == [5, 20] and c['frozen_at'].startswith('2026-10-07T')
        source = entry['source']; raw = (root / source['path']).read_bytes()
        h._bound(raw, source)
        assert model.sha256(raw) == c['document_sha256']
        assert all(t in raw.decode() for t in [c['frozen_at'], c['analyst_review_by'],
                   h._long_deadline_assertion(None), *c['source_assertions'], *c['interpretation'].values()])
