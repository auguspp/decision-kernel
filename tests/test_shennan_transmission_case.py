"""Case-specific evidence checks, not an economic inference/admission framework."""
from decimal import Decimal, localcontext
import json
from pathlib import Path
import subprocess
import sys

import pytest

from decision_kernel.runtime import research_comparison as c
from decision_kernel.runtime import current_state as state

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'docs/readings/c-shennan-transmission-2026-10-01'


def case():
    value = json.loads((CASE / 'comparison-input.json').read_text())
    raw = (CASE / 'reviewed-source-facts.json').read_bytes()
    return value, {'facts': raw}, json.loads(raw)


def results():
    value, files, facts = case()
    report = c.build(value, files)
    return report, {r['id']: r['result'] for r in report['comparisons']}, facts


def test_retained_case_replays_exact_existing_consumer_and_markdown():
    report, _, _ = results()
    assert report == json.loads((CASE / 'comparison.json').read_text())
    assert c.render(report) == (CASE / 'comparison.md').read_text()
    assert report['authority'] == c.AUTHORITY
    assert report['source_gaps'] == []
    assert len(report['observations']) <= 64
    assert all(len(x['terms']) <= 16 for x in report['comparisons'])
    assert report['sources'][0]['qualification'] == 'RETAINED_RESEARCH'
    assert report['sources'][0]['ref'] == '2fdc33f00678e513172452ac7b7cde50b750a7e9'
    assert report['sources'][0]['git_blob'] == 'cffb98d891f6f39d8e49e9bf9650482f4b6e41a1'
    assert report['sources'][0]['bytes'] == 6339
    assert report['sources'][0]['acquired_at'] == '2026-10-01T06:38:42Z'
    assert report['sources'][0]['published_at'] is None
    assert report['historical_knowledge'] == 'NOT_ESTABLISHED_BY_RETRIEVAL_CLOCK'


def test_independent_decimal_reconstructs_both_raw_17_line_bridges_and_delta():
    _, out, f = results()
    rows = f['cfo_bridge_signed_cny']
    wc = {'inventory_change', 'operating_receivables', 'operating_payables'}
    assert len(rows) == 17
    for i, year in enumerate((2026, 2025)):
        cash = f['cash_totals']
        assert sum(Decimal(v[i]) for v in rows.values()) == Decimal(cash['cfo'][i])
        working = sum(Decimal(rows[k][i]) for k in wc)
        other = sum(Decimal(v[i]) for k, v in rows.items() if k not in wc | {'net_profit'})
        assert working == Decimal(cash['working_capital_cash_adjustment'][i])
        assert other == Decimal(cash['non_working_capital_adjustment'][i])
        for name in ('working_capital_cash_adjustment', 'non_working_capital_adjustment', 'profit-to-cfo'):
            assert Decimal(out[f'{year}-{name}-closure']['value']) == 0
    changes = {k: Decimal(out[k + '-change']['value']) for k in (
        'net_profit', 'working_capital_cash_adjustment', 'non_working_capital_adjustment', 'cfo')}
    assert changes['net_profit'] == Decimal('893302262.88')
    assert changes['working_capital_cash_adjustment'] == Decimal('-1466505889.77')
    assert changes['non_working_capital_adjustment'] == Decimal('579533171.14')
    assert changes['cfo'] == Decimal('6329544.25')
    assert sum(v for k, v in changes.items() if k != 'cfo') == changes['cfo']


def test_portfolio_reconciles_without_rounded_prior_product_costs():
    _, out, f = results()
    products = f['products_2026H1']
    for k in ('revenue', 'cost', 'gross_profit'):
        assert sum(Decimal(v[k + '_cny']) for v in products.values()) == Decimal(f['group'][k][0])
    for p, v in products.items():
        assert Decimal(v['revenue_cny']) - Decimal(v['cost_cny']) == Decimal(out[p + '-gross-profit']['value'])
    assert out['portfolio-gross-profit']['value'] == '4744152836.80'
    assert out['group-gross-profit-change']['value'] == '1996526762.63'
    with localcontext() as ctx:
        ctx.prec = 50
        for p in ('pcb', 'substrate'):
            expected = Decimal(products[p]['gross_profit_cny']) / Decimal(f['group']['gross_profit'][0])
            assert Decimal(out[p + '-share-group-gross-profit']['value']) == expected


def test_bad_inference_all_group_growth_is_bga_stays_unsupported():
    report, out, f = results()
    obs = {o['id']: o for o in report['observations']}
    assert f['scope_limits']['substrate'] == 'MIXED_PACKAGING_SUBSTRATE_NOT_PURE_FC_BGA'
    assert f['exposure']['qualification'] == 'ISSUER_REPORTED_EXPOSURE_NOT_INDEPENDENT_CAUSALITY'
    assert f['exposure']['relation'] == 'STRICTLY_GREATER_THAN'
    assert f['exposure']['exact_share'] is None and f['exposure']['profit_contribution'] is None
    assert obs['pure_fc_bga_profit']['status'] == 'UNKNOWN'
    assert out['pure_fc_bga_profit-not-established'] == {'status': 'NOT_CHECKED', 'value': None}
    # Level shares cannot identify growth attribution. The case refuses both
    # unsupported acceptance and a spurious numerical disproof of that hypothesis.
    change = next(x for x in report['comparisons'] if x['id'] == 'group-gross-profit-change')
    assert 'exact attribution of the increase to products is not' in change['challenge_disposition']
    value, files, _ = case()
    narrower = next(o for o in value['observations'] if o['id'] == 'pure_fc_bga_profit')
    narrower.update(status='KNOWN', value='1996526762.63')
    with pytest.raises(ValueError, match='selected value differs'):
        c.build(value, files)


def test_bad_inference_subsidiary_profit_is_factory_operations_fails_scope():
    report, out, f = results()
    original = f['subsidiary_original_wan_cny']
    subsidiary = f['guangzhou_subsidiary']
    for k in original:
        assert Decimal(original[k]) * 10000 == Decimal(subsidiary[k + '_cny'])
    assert out['guangzhou-net-profit-less-dividend-diagnostic']['value'] == '136231400'
    with localcontext() as ctx:
        ctx.prec = 50
        assert Decimal(out['guangzhou-dividend-share-net-profit']['value']) == Decimal('390000000') / Decimal('526231400')
    assert f['scope_limits']['dividend'] == 'ALREADY_ELIMINATED_IN_CONSOLIDATION_DO_NOT_SUBTRACT_AGAIN_OR_ADD_WUXI'
    assert out['normalized_guangzhou_plant_profit-not-established']['value'] is None
    value, files, _ = case()
    # A group-minus-subsidiary dividend reconstruction is not a valid same-scope bridge.
    target = next(x for x in value['comparisons'] if x['id'] == 'guangzhou-net-profit-less-dividend-diagnostic')
    target['terms'][0]['observation'] = '2026-net_profit'
    with pytest.raises(ValueError, match='incompatible basis'):
        c.build(value, files)


def test_bad_inference_positive_cfo_is_self_funded_expansion_contradicts_cash_gap():
    _, out, f = results()
    assert Decimal(f['cash_totals']['cfo'][0]) > 0
    assert out['2026-cfo-less-cash-capex']['value'] == '-3176780928.12'
    assert out['2025-cfo-less-cash-capex']['value'] == '-50403396.15'
    assert Decimal(f['cash_totals']['cfo'][0]) < Decimal(f['cash_totals']['cash_capex'][0])
    assert f['scope_limits']['cash_diagnostic'] == 'CFO_MINUS_TOTAL_CASH_CAPEX_NOT_FCFE_MAINTENANCE_CAPEX_OR_INVESTMENT_RETURN'
    assert f['external_financing_cny']['qualification'] == 'FINANCING_CASH_NOT_OPERATING_CASH_NOT_ALL_DEBT'


def test_source_custody_and_missing_bytes_are_not_silent_success():
    value, files, f = case()
    assert f['original_source']['sha256'] == '2ac44e797a7c7f4e8f1a306a48a5760e078fc7b9086c182fa77d2c502f21c753'
    assert f['original_source']['custody'] == 'LOCAL_ORIGINAL_BYTES_ONLY'
    assert not any(p.suffix.lower() in {'.pdf', '.png'} for p in CASE.iterdir())
    missing = c.build(value, {})
    assert all(x['result']['status'] == 'SOURCE_BYTES_UNAVAILABLE' for x in missing['comparisons'])
    with pytest.raises(ValueError, match='source byte identity differs'):
        c.build(value, {'facts': files['facts'] + b' '})


def test_cli_replay_uses_pinned_input_and_create_only_outputs(tmp_path):
    value, files, _ = case()
    raw = (CASE / 'comparison-input.json').read_bytes()
    out = tmp_path / 'replay'
    args = [sys.executable, '-m', 'decision_kernel.runtime.research_comparison',
            str(CASE / 'comparison-input.json'), '--sha256', state.sha256(raw),
            '--source', 'facts=' + str(CASE / 'reviewed-source-facts.json'), '--output', str(out)]
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads((out / 'comparison.json').read_text()) == c.build(value, files)
    assert (out / 'comparison.json').read_bytes() == (CASE / 'comparison.json').read_bytes()
    assert (out / 'comparison.md').read_bytes() == (CASE / 'comparison.md').read_bytes()
    assert subprocess.run(args, capture_output=True).returncode != 0
