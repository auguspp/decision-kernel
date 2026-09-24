"""Reproducible conditional research arithmetic, not an investment/Odds engine.
Run: python calculations.py. Outputs calculations.json next to this script.
All money inputs are CNY. 1 yi (亿元) = 100,000,000 CNY.
Source IDs refer to report.md. Missing capex stays None, never zero.
"""
from decimal import Decimal, getcontext
from pathlib import Path
import json

getcontext().prec = 36
D = Decimal
YI = D('100000000')
ANNUALS = {
 '2021': ['5039987053.24','621490008.76','590978178.87','579717794.17',None],
 '2022': ['5353854994.29','525633105.29','395499812.73','727441912.21','2368749140.53'],
 '2023': ['5359923893.28','211212047.25','47763493.83','125467202.79','1881202066.28'],
 '2024': ['5817324197.22','-198289785.26','-195768453.58','375814830.73','1127871170.01'],
 '2025': ['7194624804.67','134946022.66','141005996.98','-62747124.30','852683193.60'],
 '2026H1': ['4037832294.13','110507734.74','124745879.46','2840926.52',None],
}
# Sources: 2021-23 F23; 2024 F24/F25; 2025 F25; H1 H26 (partial source extraction).
QUARTERS_2025 = [
 ['Q1','1579603763.29','9372438.91','6899959.42','16926344.30'],
 ['Q2','1846259672.66','19460510.24','39839425.60','-185912450.48'],
 ['Q3','1947164444.92','102658486.21','101971476.08','47185567.73'],
 ['Q4','1821596923.80','3454587.30','-7704864.12','59053414.15'],
]

def main() -> None:
    annual = {}
    for period, vals in ANNUALS.items():
        rev, profit, recurring, ocf = map(D, vals[:4])
        capex = D(vals[4]) if vals[4] is not None else None
        annual[period] = {
            'revenue_yi': rev / YI, 'parent_profit_yi': profit / YI,
            'recurring_parent_profit_yi': recurring / YI, 'ocf_yi': ocf / YI,
            'cash_capex_yi': capex / YI if capex is not None else None,
            'ocf_less_cash_capex_yi': (ocf-capex)/YI if capex is not None else None,
            'parent_profit_margin': profit/rev,
        }
    for idx in range(1,5):
        assert sum(D(q[idx]) for q in QUARTERS_2025) == D(ANNUALS['2025'][idx-1])
    capex_total = sum(D(ANNUALS[y][4]) for y in ('2022','2023','2024','2025'))
    ocf_total = sum(D(ANNUALS[y][3]) for y in ('2022','2023','2024','2025'))
    shares = D('1699673563')
    price = D('45.90') # 2026-09-23 close; PUBLIC_CONTEXT_ONLY, not qualified ObservedMarket.
    cap = shares*price
    ttm_profit = D(ANNUALS['2025'][1])-D('9372438.91')-D('19460510.24')+D(ANNUALS['2026H1'][1])
    ttm_rev = D(ANNUALS['2025'][0])-D('1579603763.29')-D('1846259672.66')+D(ANNUALS['2026H1'][0])
    ttm_recurring = D(ANNUALS['2025'][2])-D('6899959.42')-D('39839425.60')+D(ANNUALS['2026H1'][2])
    # These are analyst assumptions, not Human preferences or fair multiples.
    years = D('3'); hurdle = D('0.10'); zero_dividends = D('0')
    fv = cap*(1+hurdle)**3
    requirements = []
    for pe in map(D, ('20','25','30','40')):
        earnings = fv/pe
        assert abs((earnings*pe/(1+hurdle)**3)/shares-price) < D('1e-28')
        requirements.append({'terminal_pe_assumption': pe, 'required_parent_profit_yi': earnings/YI,
                             'required_net_margin_on_120yi_revenue': earnings/(D('120')*YI)})
    stress = []
    for profit_yi in map(D, ('5','10','20','30')):
        for pe in map(D, ('15','20','30','40')):
            terminal_price = profit_yi*YI*pe/shares
            stress.append({'parent_profit_yi_assumption':profit_yi,'terminal_pe_assumption':pe,
                           'terminal_price':terminal_price,'cumulative_return':terminal_price/price-1,
                           'annual_return_3y':D(str((float(terminal_price/price))**(1/3)-1))})
    dilution = []
    for issue_price in map(D,('30','40')):
        newshares = D('3900000000')/issue_price
        dilution.append({'issue_price_assumption':issue_price,'new_shares':newshares,
                         'share_count_increase':newshares/shares,
                         'old_holders_percentage_reduction':newshares/(newshares+shares),
                         'required_parent_profit_at_30pe_yi':fv*(1+newshares/shares)/D('30')/YI})
    # FV/share use is an equity P/E method. Do NOT subtract debt again from P/E values.
    put_debt = D('1275768497.83')
    debt25 = sum(map(D,('574441571.71','981552136.76','3657238516.14','16768988.09')))+put_debt
    debt26_ex_put = sum(map(D,('593567164.73','1360779353.74','4315997733.73','16153269.96')))
    bridge25 = {
      'consolidated_profit': D('-103986017.84'), 'parent_profit':D('134946022.66'),
      'minority_profit':D('-103986017.84')-D('134946022.66'),
      'ocf':D('-62747124.30'), 'cash_capex':D('852683193.60'),
      'ocf_less_cash_capex':D('-62747124.30')-D('852683193.60'),
      'ocf_bridge_other_noncash_and_working_capital_net':D('-62747124.30')-D('-103986017.84'),
      'net_investing':D('-746434271.44'),'net_financing':D('1028339288.53'),
      'cash_equivalent_change':D('251569793.00'),
    }
    bridge25['fx_and_other_cash_reconciliation_residual'] = bridge25['cash_equivalent_change']-sum(bridge25[k] for k in ('ocf','net_investing','net_financing'))
    assert bridge25['consolidated_profit'] == bridge25['parent_profit']+bridge25['minority_profit']
    result = {
      'qualification':'BOUNDED_CONDITIONAL_ARITHMETIC_NOT_CANONICAL_ODDS',
      'probability':'NOT_ESTABLISHED','investment_authority':'NONE','annuals':annual,
      'annual_quarter_check':'2025 revenue/parent profit/recurring profit/OCF sums pass exactly',
      'cash_2022_2025':{'ocf_yi':ocf_total/YI,'cash_capex_yi':capex_total/YI,'gap_yi':(ocf_total-capex_total)/YI},
      'equity_bridge_2025':bridge25,
      'market_context':{'price':price,'price_date':'2026-09-23','shares':shares,'equity_value_yi':cap/YI,
                        'ttm_parent_profit_yi':ttm_profit/YI,'ttm_recurring_profit_yi':ttm_recurring/YI,
                        'ttm_revenue_yi':ttm_rev/YI,'ttm_pe':cap/ttm_profit},
      'assumptions':{'years':years,'required_return':hurdle,'interim_dividends':zero_dividends,
                     'new_shares_in_primary_grid':0,'terminal_profit_definition':'parent net income CNY',
                     'drawdown_during_holding_period':'UNKNOWN; endpoint loss is not maximum drawdown'},
      'price_implied_requirements':requirements,'stress_surface':stress,'dilution_sensitivity':dilution,
      'debt_diagnostics':{'2025_debt_like_gross_including_put_yi':debt25/YI,
          '2025_less_total_cash_not_all_cash_unrestricted_yi':(debt25-D('858607630.03'))/YI,
          '2026H1_gross_loans_current_maturities_leases_excluding_put_yi':debt26_ex_put/YI,
          '2026H1_put_obligation_amount':'NOT_RETRIEVED; do not assert FY25 unchanged',
          'H1_cash_increase_yi':(D('1332839284.83')-D('858607630.03'))/YI,
          'H1_AR_increase_yi':(D('2635378698.78')-D('2216171249.98'))/YI},
      'broker_context_sensitivity': {'Kaiyuan_2028_profit_yi':D('20.21'),
          'current_cap_to_Kaiyuan_2028_profit':cap/(D('20.21')*YI),
          'SPDBI_2028_profit_yi':D('11.4'),'current_cap_to_SPDBI_2028_profit':cap/(D('11.4')*YI),
          'source_status':'SECONDARY_REPORT_SUMMARIES_ONLY_NOT_FULL_MODEL_AUDIT'},
      'first_entry':'NOT_METHOD_READY','kernel_validator':'NOT_RUN',
    }
    out = Path(__file__).with_name('calculations.json')
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str)+'\n', encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('cash_2022_2025','market_context','price_implied_requirements','dilution_sensitivity','debt_diagnostics','broker_context_sensitivity')},ensure_ascii=False,indent=2,default=str))

if __name__ == '__main__':
    main()
