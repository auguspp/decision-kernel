"""Offline conditional arithmetic on explicitly retained inputs; not new Odds.

No network, imports of archived code, source requests, or repository writes.
Default creates results.json exclusively; --check only compares existing bytes.
"""
import argparse
from decimal import Decimal, localcontext
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent

def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode()

def calculate(inputs):
    D = Decimal
    with localcontext() as ctx:
        ctx.prec = 40
        price, shares = D(inputs['price_cny']), D(inputs['shares'])
        assert price > 0 and shares > 0
        reference = price * shares
        multiples = [D(v) for v in inputs['pe_assumptions']]
        equivalent = [{'pe_x': str(pe), 'annual_profit_cny': str(reference / pe)}
                      for pe in multiples]
        forecasts = [{'annual_profit_cny': value,
                      'price_equivalent_pe_x': str(reference / D(value))}
                     for value in inputs['old_forecast_context_cny']]
        conditional = []
        for pe in (D('15'), D('19')):
            p = D(inputs['same_earnings_world_cny']) * pe / shares
            conditional.append({'annual_profit_cny': inputs['same_earnings_world_cny'],
                                'pe_x': str(pe), 'conditional_price_cny': str(p),
                                'static_price_difference_fraction': str(p / price - 1)})
        gm = D(inputs['storage_gross_margin'])
        assert 0 < gm < 1
        supply = []
        for scenario in inputs['inherited_supply_assumptions']:
            v, p, c = (D(scenario[k]) for k in ('volume', 'price', 'unit_cost'))
            unit_gp = (1+p) - (1-gm)*(1+c)
            assert unit_gp > 0
            change = (1+v)*unit_gp/gm - 1
            # Independent standardized-amount route, not another source claim.
            amount_gp = (D('100')*(1+p)-D('100')*(1-gm)*(1+c))*(1+v)
            assert abs(change - (amount_gp/(D('100')*gm)-1)) < D('1e-35')
            supply.append({**scenario, 'gross_profit_change_fraction': str(change),
                           'break_even_volume_growth_fraction': str(gm/unit_gp-1)})
        ocf, np, stock = (D(inputs[k]) for k in ('ocf_cny', 'deducted_parent_profit_cny', 'inventory_cny'))
        extra = stock * D(inputs['extra_inventory_fraction_assumption'])
        cash = {'historical_group_ocf_less_deducted_parent_profit_cny': str(ocf-np),
                'assumed_extra_cash_financed_inventory_cny': str(extra),
                'hypothetical_ocf_after_extra_use_cny': str(ocf-extra),
                'hypothetical_ratio_to_old_deducted_parent_profit': str((ocf-extra)/np),
                'basis': 'ILLUSTRATIVE_EXTRA_USE_NOT_A_RECONCILIATION_OF_HISTORICAL_OCF'}
        return {'purpose': 'STATIC_CONDITIONAL_COMPARISON_NOT_HORIZON_ODDS_OR_FORECAST',
                'price_session': inputs['price_session'],
                'a_price_times_old_total_shares_cny': str(reference),
                'not_combined_a_h_market_cap': True,
                'profit_equivalents': equivalent, 'old_forecast_context': forecasts,
                'same_earnings_different_multiple': conditional,
                'inherited_supply_sensitivity_rechecked': supply, 'inherited_cash_sensitivity_rechecked': cash,
                'probabilities': None, 'annualized_return': None, 'investment_authority': 'NONE'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = json.loads((ROOT/'inputs.json').read_text(encoding='utf-8'))
    raw = encoded(calculate(data))
    target = ROOT/'results.json'
    if args.check:
        if target.read_bytes() != raw:
            raise SystemExit('RESULT_MISMATCH')
        print('CONDITIONAL_ARITHMETIC_MATCHED; not source verification or full CI')
    else:
        with target.open('xb') as out:
            out.write(raw)
        print('CREATED_CONDITIONAL_RESULTS')

if __name__ == '__main__':
    main()
