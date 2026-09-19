"""Reproducible arithmetic on retained issuer statements. No networking or forecast."""
from decimal import Decimal, getcontext
import json
from pathlib import Path
getcontext().prec=40
D=Decimal
x={
 'revenue':'414836129.08','cost':'302021581.15','selling':'28705547.47','admin':'52574989.84','research':'73670051.96',
 'plc_revenue':'258967979.04','plc_cost':'169075962.42','ic_revenue':'140376940.20','ic_cost':'123884910.52','smart_revenue':'14151761.70','smart_cost':'8593833.44',
 'remaining_performance_revenue':'278741923.44','operating_profit':'-27108923.06',
 'contract_gross_open':'43540230.62','contract_gross_close':'33326456.11','contract_reserve_open':'5518684.03','contract_reserve_close':'9034627.09','contract_net_open':'38021546.59','contract_net_close':'24291829.02',
 'contract_provision':'5607053.07','contract_writeoff':'2091110.01','contract_single_gross_close':'14865728.78','contract_single_reserve_close':'7432864.39',
 'contract_single_gross_open':'7991682.44','contract_single_reserve_open':'2397504.73',
 'prior_revenue':'504205161.20','prior_cost':'354394726.80','prior_selling':'30994663.16','prior_admin':'48475826.55','prior_research':'69210423.22',
 'tax_surcharges':'5455538.31','financial_expenses':'-8949916.89','other_income':'13878422.69','investment_income':'688010.34','fair_value':'369898.39','credit_impairment_gain':'2248602.22','asset_impairment_loss':'-5668538.61','disposal_gain':'16344.67',
}
v={k:D(a) for k,a in x.items()};gp=v['revenue']-v['cost'];fee=v['selling']+v['admin']+v['research'];margin=gp/v['revenue']
subtotal=gp-fee
assert subtotal-v['tax_surcharges']-v['financial_expenses']+sum(v[k] for k in ['other_income','investment_income','fair_value','credit_impairment_gain','asset_impairment_loss','disposal_gain'])==v['operating_profit']
out={'inputs_cny':x,'calculations':{'gross_profit':gp,'three_expenses':fee,'gross_less_three_expenses_not_ebit':subtotal,'blended_margin':margin,
 'expense_cover_revenue_at_same_mix_not_forecast':fee/margin,'increment_vs_h1_revenue_at_same_mix':fee/margin-v['revenue'],'increment_ratio_vs_h1':(fee/margin-v['revenue'])/v['revenue'],
 'rpo_fraction_of_h1_revenue':v['remaining_performance_revenue']/v['revenue'],
 'rpo_fraction_of_conditional_expense_cover':v['remaining_performance_revenue']/(fee/margin),
 'contract_net_drop':v['contract_net_open']-v['contract_net_close'],
 'contract_gross_drop':v['contract_gross_open']-v['contract_gross_close'],
 'contract_reserve_increase':v['contract_reserve_close']-v['contract_reserve_open'],
 'contract_net_drop_from_reserve_increase_fraction':(v['contract_reserve_close']-v['contract_reserve_open'])/(v['contract_net_open']-v['contract_net_close']),
 'reserve_rate_open':v['contract_reserve_open']/v['contract_gross_open'],'reserve_rate_close':v['contract_reserve_close']/v['contract_gross_close'],
 'reserve_rollforward':v['contract_reserve_open']+v['contract_provision']-v['contract_writeoff'],
 'prior_gross_less_three_expenses':v['prior_revenue']-v['prior_cost']-v['prior_selling']-v['prior_admin']-v['prior_research'],
},'scope':'Sensitivity at unchanged half-year expense amount and gross margin/mix; not profit forecast, not normalized EBIT, not FCF, no cardinal probability or valuation.'}
assert out['calculations']['contract_net_drop']==out['calculations']['contract_gross_drop']+out['calculations']['contract_reserve_increase']
assert out['calculations']['reserve_rollforward']==v['contract_reserve_close']
nonplc=gp-(v['plc_revenue']-v['plc_cost']);plc_m=(v['plc_revenue']-v['plc_cost'])/v['plc_revenue']
# Holding other businesses' gross profits and group expense amount constant is a declared sensitivity.
out['calculations'].update({'plc_gross_margin':plc_m,'nonplc_gross_profit':nonplc,'plc_revenue_to_cover_gap_at_same_margin':(fee-nonplc)/plc_m,'plc_revenue_growth_to_cover_gap':((fee-nonplc)/plc_m-v['plc_revenue'])/v['plc_revenue']})
Path(__file__).with_name('calculations.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n')
for k,a in out['calculations'].items(): print(k,a)
