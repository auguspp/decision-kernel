"""Explicit case input for the existing comparison consumer; no source acquisition.

Usage: python replay.py facts.json original-research-use.json absent-output-directory
This is a retained case workpaper, not a production detector or new comparator.
"""
from pathlib import Path
import sys
from decision_kernel.identity import canonical_json, canonical_hash
from decision_kernel.runtime import current_state as state, research_comparison as comparison
from decision_kernel.runtime.research_commit_only import _json, _read, _publish_report_files

FACT_REF = '422f83d2af8357a4f6d7dff8aec2a306a088d459'
FACT_PATH = 'docs/readings/c2-shanshui-transmission-2026-10-01/facts.json'
FACT_BLOB = '6e1f61ef5c259601f25ab06549022d0cf484704b'
FACT_SHA = '4044cb11b77b654193a80478dde99294b640cac02692f683820c5a795f54ead4'
FACT_BYTES = 9706
REVIEWED_AT = '2026-10-01T14:07:18.798717+00:00'


def make_input(facts_raw, prior_raw):
    state.check((len(facts_raw), state.blob_sha(facts_raw), state.sha256(facts_raw)) ==
                (FACT_BYTES, FACT_BLOB, FACT_SHA), 'reviewed fact bytes differ')
    f = _json(facts_raw)
    state.check(f['record_hash'] == canonical_hash({k:v for k,v in f.items() if k != 'record_hash'}), 'fact record differs')
    prior = f['sources']['PREDECESSOR']
    state.check((len(prior_raw), state.blob_sha(prior_raw), state.sha256(prior_raw)) ==
                (prior['bytes'], prior['git_blob'], prior['sha256']), 'predecessor bytes differ')
    source = dict(id='facts', subject='301190.SZ', ref=FACT_REF, path=FACT_PATH,
                  git_blob=FACT_BLOB, sha256=FACT_SHA, bytes=FACT_BYTES,
                  qualification='RETAINED_RESEARCH', acquired_at=None, published_at=None,
                  identity_basis='Pinned native Git fact extraction; source carriers and access limits remain in facts.json. Not original issuer bytes.')
    old = dict(id='prior', subject='301190.SZ', **prior, qualification='RETAINED_RESEARCH',
               acquired_at=None, published_at=None, identity_basis='Exact predecessor research-use.json; not fresh issuer evidence.')
    value = dict(version=comparison.VERSION, subject='301190.SZ',
        question='Which saved industry proxies match Shanshui products, and how do actual product revenue and cash sources constrain the transmission claim?',
        predecessor='PR701 five-file archive cbe0806a5cfcd18531bd2a575e841d358d4a3d0c; original bytes and failures unchanged.',
        analysis_cutoff=None, reviewed_at=REVIEWED_AT, sources=[source, old],
        observations=[], comparisons=[], authority=dict(comparison.AUTHORITY),
        remaining_evidence='Realized product prices/quantities, comparable prior H1 product scope, original source custody, customer commitments and durable owner cash remain unestablished. No historical roles, causal inflection, Full or Human acceptance.')
    def observation(key, pointer, amount, period, metric, source_id='facts'):
        value['observations'].append(dict(id=key, subject='301190.SZ', status='KNOWN',
            type='NUMBER', source_id=source_id, locator={'pointer':pointer}, value=amount,
            metric=metric, scope='CONSOLIDATED', restatement='REVIEWED_AS_REPORTED',
            basis_note='CNY; selected consolidated line, not parent-only table. Derived checkpoints are labelled in their pointer.',
            currency='CNY', scale='1', period=dict(kind='FLOW', start=period[:4]+'-01-01',
                                                 end=period[:4]+('-06-30' if period.endswith('H1') else '-12-31'))))
    for period, metrics in f['periods_cny'].items():
        for metric, products in metrics.items():
            for product, amount in products.items():
                observation(f'{period}-{metric}-{product}', f'/periods_cny/{period}/{metric}/{product}', amount, period, metric+'-'+product)
    for key, amount in f['cash_2025_cny'].items():
        # Opening/closing balances are intentionally not input to FLOW arithmetic.
        if key not in {'opening_cash','closing_cash'}:
            observation(key, '/cash_2025_cny/'+key, amount, '2025FY', key)
    for key, amount in f['researcher_derived_checkpoints_cny'].items():
        observation(key, '/researcher_derived_checkpoints_cny/'+key, amount, '2025FY', 'year_on_year_revenue_change')
    for metric in ('revenue','cost'):
        observation('prior-'+metric, '/reported_values/'+metric+'/0', _json(prior_raw)['reported_values'][metric][0], '2026H1', metric+'-group', 'prior')
    def check(key, terms, interpretation, operation='signed_sum', kind='CASH_DIAGNOSTIC', limitations=None):
        value['comparisons'].append(dict(id=key, kind=kind, operation=operation,
            terms=[dict(observation=o,sign=s) for o,s in terms],
            compatibility_note='Exact declared consolidated CNY basis; FY changes use like seasonal windows. H1 and FY are not growth comparators.',
            interpretation=interpretation, challenge_disposition='Keep arithmetic and source limitations; no causal or investment certification.',
            limitations=limitations or 'Not price/volume attribution, sustainable margin, owner cash, capital return or Human acceptance.'))
    for period in f['periods_cny']:
        for metric in f['periods_cny'][period]:
            check(f'{period}-{metric}-reconciliation', [(f'{period}-{metric}-{p}',1) for p in ('dye','chloro','other')]+[(f'{period}-{metric}-group',-1)], 'All three product lines reconcile to their disclosed total.')
    for period in ('2025FY','2026H1'):
        for product in ('group','dye','chloro','other'):
            check(f'{period}-{product}-gross-profit', [(f'{period}-revenue-{product}',1),(f'{period}-cost-{product}',-1)], 'Revenue less reported product cost; not factory operating profit.')
    for product in ('group','dye','chloro','other'):
        check('annual-revenue-change-'+product, [('2024FY-revenue-'+product,-1),('2025FY-revenue-'+product,1)], 'Same annual table product scope: 2025 minus 2024.', 'difference','PERIOD_CHANGE')
    # The named derived checkpoints are independently checked in validation.json;
    # their ratio is a decomposition share, not company market share.
    check('chloro-share-of-annual-revenue-increase', [('chloro_revenue_increase_2025',1),('group_revenue_increase_2025',1)], 'Share of this company annual revenue increase; not industry market share or profit attribution.', 'ratio')
    for product in ('dye','chloro'):
        check('H1-cost-ratio-'+product, [('2026H1-cost-'+product,1),('2026H1-revenue-'+product,1)], 'One minus this cost ratio is current-period product gross margin, not comparable constant-mix margin improvement.', 'ratio')
    for metric in ('revenue','cost'):
        check('inherited-H1-'+metric, [('prior-'+metric,-1),('2026H1-'+metric+'-group',1)], 'New detail leaves the predecessor H1 aggregate unchanged.', 'difference','CHECKED_UNCHANGED')
    check('operating-cash-reconciliation', [('operating_receipts',1),('operating_payments',-1),('cfo',-1)], 'Operating cash subtotal reconciles; not net-profit-to-cash bridge.')
    check('investing-cash-reconciliation', [('investment_recovery',1),('investment_income_received',1),('asset_disposal_net',1),('cash_capex',-1),('investment_payments',-1),('cfi',-1)], 'Investment recovery and long-lived asset spending remain separate.')
    check('cash-change-residual', [('cfo',1),('cfi',1),('cff',1),('cash_change',-1)], 'Residual is zero; blank reported FX field is not filled as an observed zero.')
    check('operating-cash-less-cash-capex', [('cfo',1),('cash_capex',-1)], 'This period cash diagnostic is not FCFE, maintenance capex or investment NPV.')
    check('net-investment-recovery', [('investment_recovery',1),('investment_payments',-1)], 'Investment principal flows net positive; not operating revenue or recurring cash generation.')
    # Match the existing CLI JSON boundary before rendering its period dictionaries.
    return _json(canonical_json(value).encode())


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    facts, prior = _read(Path(sys.argv[1])), _read(Path(sys.argv[2]))
    value = make_input(facts, prior)
    report = comparison.build(value, {'facts':facts, 'prior':prior})
    _publish_report_files(Path(sys.argv[3]), {
        'comparison.json':(canonical_json(report)+'\n').encode(),
        'comparison.md':comparison.render(report).encode()})


if __name__ == '__main__':
    main()
