"""One retained MU guidance/actual workpaper; stdlib only, no source or Git I/O.

This is not a runtime schema, score engine, forecast or method-quality test.
Inputs are manual source extracts. Arithmetic checks do not authenticate sources.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, localcontext
import hashlib
import json
from pathlib import Path


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def number(value: str) -> Decimal:
    require(type(value) is str, 'numeric inputs must be decimal strings')
    result = Decimal(value)
    require(result.is_finite(), 'nonfinite input')
    return result


def text(value: Decimal) -> str:
    return format(value.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP), 'f')


def encode(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def calculate(source: dict) -> dict:
    require(source['case'] == 'MU_FQ4_2026_VALIDATION_ONLY', 'wrong case')
    require((source['currency'], source['amount_unit'], source['shares_unit'], source['eps_unit']) ==
            ('USD', 'USD_million', 'million_shares', 'USD_per_diluted_share'), 'units differ')
    require(source['comparison'] == 'JUNE_24_COMPANY_GUIDANCE_NOT_CONSENSUS_OR_AI_FORECAST', 'comparator role')
    g, a = source['guide'], source['actual']
    require(g['period'] == a['period'] == 'FQ4_2026', 'period mismatch')
    require(g['source_id'] == 'S1' and a['source_id'] == 'S2', 'source role mismatch')
    require(g['basis'] == a['basis'] == 'NON_GAAP_EXCEPT_REVENUE', 'GAAP basis mismatch')
    clocks = [datetime.fromisoformat(x['published_at']) for x in (g, a)]
    require(all(c.tzinfo is not None for c in clocks) and clocks[0] < clocks[1], 'guide is not earlier')
    q = source['qualification']
    require(q['investment_authority'] == 'NONE' and q['cardinal_probability'] is None and
            q['normalized_eps_floor'] is None and q['market_requests'] == 0 and
            q['original_human_decision_modified'] is False and q['new_human_decision'] is False,
            'qualification must not be promoted')
    with localcontext() as ctx:
        ctx.prec = 40
        delta = {}
        for metric in ('revenue', 'eps'):
            actual, midpoint, width = (number(a[metric]), number(g[metric+'_mid']), number(g[metric+'_half_width']))
            require(midpoint > width >= 0 and actual > 0, 'invalid comparison range')
            upper = midpoint + width
            delta[metric] = {'actual_minus_midpoint': text(actual-midpoint),
                             'fraction_of_midpoint': text(actual/midpoint-1),
                             'actual_minus_upper': text(actual-upper),
                             'fraction_of_upper': text(actual/upper-1)}
        rev, gp, opex, oi = [number(a[k]) for k in ('revenue','gross_profit','operating_expenses','operating_income')]
        gm, gr, go = number(g['gross_margin_fraction_approx']), number(g['revenue_mid']), number(g['operating_expenses_approx'])
        require(0 < gm < 1 and gp-opex == oi, 'operating tie-out')
        revenue_effect = (rev-gr)*gm
        margin_residual = gp-rev*gm
        expense_offset = opex-go
        oi_proxy = gr*gm-go
        require(revenue_effect+margin_residual-expense_offset == oi-oi_proxy, 'bridge tie-out')
        net_adjustment = sum(number(v) for v in a['net_income_adjustments'].values())
        require(number(a['gaap_net_income'])+net_adjustment == number(a['net_income']), 'net income tie-out')
        for prefix in ('gaap_', ''):
            per_share = number(a[prefix+'net_income'])/number(a[prefix+'diluted_shares'])
            require(abs(per_share-number(a[prefix+'eps'])) < Decimal('0.005'), 'EPS/denominator tie-out')
        require(source['cash']['source_id'] == 'S2', 'cash source')
        cash = {}
        for period in ('FQ4_2026','FY2026'):
            row = {k:number(v) for k,v in source['cash'][period].items()}
            require(all(v >= 0 for v in row.values()), 'cash magnitudes must be nonnegative')
            benefit = row['ppe_sale_proceeds']+row['government_incentives']
            net_capex = row['gross_ppe']-benefit
            simple = row['cfo']-row['gross_ppe']
            require(net_capex == row['net_capex_reported'] and simple+benefit == row['adjusted_fcf_reported'], 'cash tie-out')
            cash[period] = {'cfo_less_gross_ppe':text(simple),'ppe_sale_and_incentives':text(benefit),
                            'net_capex':text(net_capex),'company_adjusted_fcf':text(simple+benefit)}
        return {'case':source['case'],'amount_unit':source['amount_unit'], 'rounding':'fractions and derived amounts: six decimal places, not source precision',
                'comparison_role':source['comparison'],'guide_actual':delta,
                'gross_margin_delta_percentage_points_rounded':text(number(a['gross_margin_pct_reported'])-gm*100),
                'operating_bridge_USD_million':{'guide_oi_proxy_not_explicit_company_guide':text(oi_proxy),
                    'revenue_change_at_guide_margin':text(revenue_effect),'gross_profit_residual_not_causal_mix_attribution':text(margin_residual),
                    'extra_opex_subtracted':text(expense_offset),'opex_fraction_increase':text(opex/go-1),
                    'actual_oi_less_proxy':text(oi-oi_proxy)},
                'eps_quality':{'net_income_adjustment_USD_million':text(net_adjustment),
                    'gaap_shares_million':a['gaap_diluted_shares'],'non_gaap_shares_million':a['diluted_shares'],
                    'reported_eps_difference':text(number(a['eps'])-number(a['gaap_eps'])),
                    'adjusted_is_not_certified_recurring':True},
                'cash_bridge_USD_million':cash,'company_guidance_events':1,
                'ai_forecast_error':None,'brier_score':None,'win_rate':None,'price_return':None,
                'execution_outcome':None,'normalized_eps_floor':None,'incremental_roic':None,
                'method_effectiveness':None,'investment_authority':'NONE'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--output', type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    raw = (here/'inputs.json').read_bytes()
    result = calculate(json.loads(raw))
    result['inputs_sha256'] = hashlib.sha256(raw).hexdigest()
    output = encode(result)
    if args.check:
        require(output == (here/'results.json').read_bytes(), 'saved results differ')
        print('CHECK_OK: arithmetic only; no source authentication or economic acceptance')
    else:
        with args.output.open('xb') as handle:
            handle.write(output)
        print('CREATED: '+str(args.output))


if __name__ == '__main__':
    main()
