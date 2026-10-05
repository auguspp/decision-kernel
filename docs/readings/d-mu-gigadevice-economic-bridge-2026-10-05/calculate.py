"""One retained case's Decimal arithmetic. No market, model, network or file writes."""
from __future__ import annotations
import argparse
from decimal import Decimal, localcontext
import json
from pathlib import Path


def number(value: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError('Case numerical inputs must be decimal strings')
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError('Nonfinite input')
    return result


def text(value: Decimal) -> str:
    return format(value.quantize(Decimal('0.000000000001')), 'f')


def calculate(inputs: dict) -> dict:
    if inputs['version'] != 'd-gigadevice-economic-bridge-case-v1':
        raise ValueError('Wrong retained case version')
    with localcontext() as ctx:
        ctx.prec = 48
        f, a = inputs['facts'], inputs['scenario_assumptions']
        s, u = number(f['storage_revenue_cny']), number(f['mcu_revenue_cny'])
        g, h = number(f['storage_gross_margin_pct'])/100, number(f['mcu_gross_margin_pct'])/100
        if not (s > 0 and u > 0 and 0 < g < 1 and 0 < h < 1):
            raise ValueError('Revenue or margin outside case arithmetic domain')
        gp, ugp = s*g, u*h
        drop = number(a['fixed_revenue_margin_drop_pp'])/100
        if not 0 <= drop <= g:
            raise ValueError('Invalid margin drop')
        loss = s*drop
        rows = []
        for value in a['storage_margin_pct']:
            margin = number(value)/100
            if not 0 < margin < 1:
                raise ValueError('Scenario margin must be positive and below 100%')
            rows.append({'margin_pct': value, 'fixed_revenue_gp_cny': text(s*margin),
                         'fixed_revenue_gp_change_cny': text(s*margin-gp),
                         'required_revenue_growth_pct_for_unchanged_gp': text((g/margin-1)*100)})
        normalized = []
        for price, cost in a['price_cost_changes_pct']:
            p, c = 1+number(price)/100, (1-g)*(1+number(cost)/100)
            if p <= 0 or c < 0:
                raise ValueError('Invalid normalized price/cost')
            normalized.append({'price_change_pct': price, 'unit_cost_change_pct': cost,
                               'fixed_volume_gp_change_pct': text(((p-c)/g-1)*100),
                               'new_gross_margin_pct': text((p-c)/p*100)})
        mu = inputs['micron']
        capex = number(mu['q4_ppe_expenditure'])-number(mu['q4_ppe_sales'])-number(mu['q4_government_incentives'])
        fcf = number(mu['q4_cfo'])-capex
        if capex != number(mu['q4_reported_net_capex']) or fcf != number(mu['q4_reported_adjusted_fcf']):
            raise ValueError('MU reported reconciliation differs')
        if mu['deposit_flow_period'] != 'FY2026_NOT_Q4' or mu['deposit_classification'] != 'FINANCING_NOT_OPERATING':
            raise ValueError('Do not mix deposit period or cash-flow category')
        return {'meaning': inputs['meaning'], 'rounding_decimal_places': 12,
                'storage_h1_gp_cny': text(gp), 'mcu_h1_gp_cny': text(ugp),
                'storage_one_percentage_point_gp_cny': text(s/100),
                'ten_pp_loss_at_fixed_revenue_cny': text(loss),
                'loss_over_existing_mcu_gp': text(loss/ugp),
                'incremental_mcu_revenue_to_offset_loss_cny': text(loss/h),
                'incremental_mcu_revenue_pct_of_old_base': text(loss/h/u*100),
                'h1_cfo_over_deducted_profit': text(number(f['operating_cash_flow_cny'])/number(f['deducted_net_profit_cny'])),
                'storage_margin_sensitivity': rows, 'normalized_fixed_volume_cases': normalized,
                'micron_q4_usd_million': {'net_capex': text(capex), 'adjusted_fcf': text(fcf),
                    'cfo_less_gross_ppe': text(number(mu['q4_cfo'])-number(mu['q4_ppe_expenditure'])),
                    'fy_deposit_subtracted_from_q4_cfo': False},
                'probability': None, 'target_price': None, 'investment_authority': 'NONE'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Compare against retained results.json without writing')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    result = calculate(json.loads((root/'inputs.json').read_text(encoding='utf-8')))
    if args.check:
        if result != json.loads((root/'results.json').read_text(encoding='utf-8')):
            raise SystemExit('Retained calculation mismatch')
        print('RETAINED_CASE_ARITHMETIC_MATCH; NO_SOURCE_REQUEST; NOT_FULL_RESEARCH_OR_CI')
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
