"""Xingsen 002436.SZ: deterministic business/capital checks, 2026-09-24.
Run with Python 3: python calculations.py. No price, probability, Odds or trade logic.
CNY inputs below are reported FACTs unless explicitly in ASSUMPTIONS.
Source IDs/locations are in report.md. Output units are explicit; 1 yi = 1e8 CNY.
A conditional identity is not a forecast. Annualisation is a scale, not guidance.
"""
from decimal import Decimal, getcontext
from pathlib import Path
import json
getcontext().prec = 32
D = Decimal
YI = D('100000000')

def ds(values):
    return [D(str(v)) for v in values]

# F23 (restated comparatives), F24, F25; revenue / parent NI / recurring parent NI / CFO.
ANNUALS = {
 '2021': ds(['5039987053.24','621490008.76','590978178.87','579717794.17']),
 '2022': ds(['5353854994.29','525633105.29','395499812.73','727441912.21']),
 '2023': ds(['5359923893.28','211212047.25','47763493.83','125467202.79']),
 '2024': ds(['5817324197.22','-198289785.26','-195768453.58','375814830.73']),
 '2025': ds(['7194624804.67','134946022.66','141005996.98','-62747124.30']),
}
# Historical capex inputs recovered from predecessor; H126 independently read from H26F.
# Do not describe all historical cash-capex lines as newly verified in this run.
CAPEX = {y:D(v) for y,v in {'2022':'2368749140.53','2023':'1881202066.28','2024':'1127871170.01','2025':'852683193.60'}.items()}
# F24/F25 quarterly tables; 2025 entries recovered from predecessor and cross-checked at annual aggregate.
QUARTERS = {
 '2024Q3':ds(['1470396547.99','-51103115.83']),
 '2024Q4':ds(['1465834570.60','-166687709.72']),
 '2025Q1':ds(['1579603763.29','9372438.91']),
 '2025Q2':ds(['1846259672.66','19460510.24']),
 '2025Q3':ds(['1947164444.92','102658486.21']),
 '2025Q4':ds(['1821596923.80','3454587.30']),
 '2026Q1':ds(['1818166949.77','18744694.13']),
}
# H26F: consolidated statements, cash flow pp7-8 and supplement p82 (printed pages).
H = {k:D(v) for k,v in {
 'revenue':'4037832294.13','cost':'3191709457.60','parent_ni':'110507734.74',
 'ni':'-5595585.26','minority_ni':'-116103320.00','pretax':'24552173.05','tax':'30147758.31',
 'cfo':'2840926.52','capex':'726030484.96','refund':'328768366.23',
 'cfi':'-581039152.76','cff':'1114062373.02','fx':'-16938658.18',
 'begin_cash':'684243704.46','end_cash':'1203169193.06','bank_cash':'1332839284.83',
 'short_debt':'593567164.73','current_debt_lease':'1360779353.74',
 'long_debt':'4315997733.73','noncurrent_lease':'16153269.96','put_liability':'1295391988.21',
 'ar':'2635378698.78','ar_begin':'2216171249.98','inventory':'1250431529.86',
 'inventory_begin':'982470447.10','ap':'1881803525.81','ap_begin':'1567357690.31',
 'other_biz_rev':'176520006.03','other_biz_cost':'5867741.70',
 'other_biz_rev_prev':'119052772.31','other_biz_cost_prev':'4160166.29',
 'gz_rev':'32735027.43','gz_op':'-281436038.67','gz_ni':'-272845264.14',
 'gxk_rev':'588730298.37','gxk_ni':'32616921.48','bga_cost_envelope':'329373900',
 'shares':'1699673563'
}.items()}
PREV = {k:D(v) for k,v in {'revenue':'3425863435.95','cost':'2793646199.47',
 'ni':'-87012295.16','parent_ni':'28832949.15','minority_ni':'-115845244.31',
 'cfo':'-168986106.18','capex':'492913540.26','refund':'25284070.99'}.items()}
Q1 = {k:D(v) for k,v in {'revenue':'1818166949.77','parent_ni':'18744694.13',
 'cfo':'-247107316.08','capex':'261016959.11','refund':'22076257.93'}.items()}
PRODUCTS = {
 'PCB':ds(['2502545217.94','1862867490.89']),
 'IC_CSP_AND_BGA':ds(['1208965067.54','1213338026.99']),
 'TEST':ds(['120006624.09','91825364.74']),
 'OTHER_PRODUCTS_AND_BUSINESS':ds(['206315384.56','23678574.98'])
}
# Signed entries: depreciation and finance adjustment are not all distributable cash.
CFO_BRIDGE = {k:D(v) for k,v in {
 'ni':'-5595585.26','impairment':'40948619.79','fixed_da':'319143469.57',
 'rou_da':'11643484.93','intang_amort':'21004037.24','deferred_amort':'6738251.50',
 'disposal_gain':'-9044275.22','scrapping_loss':'1893857.39','fv_loss':'18159293.93',
 'finance_adjustment':'90515734.25','investment_loss':'6544836.26',
 'dta_change':'-22984950.34','dtl_change':'-4258489.39',
 'inventory_movement':'-269409108.60','operating_receivables':'-396432434.31',
 'operating_payables':'193140851.45','other':'833333.33'
}.items()}
# CAP: preplan and feasibility; annual nameplate is monthly capacity times twelve.
PROJECTS = {
 'Zhuhai_mSAP': dict(zip(['investment','equipment','facilities','initial_wc','annual_m2'],ds(['2002616000','1614942000','250874000','136800000','120000']))),
 'Zhuhai_CSP_III':dict(zip(['investment','equipment','facilities','initial_wc','annual_m2'],ds(['1178391000','956069000','160762000','61560000','300000'])))
}
ASSUMPTIONS = {
 'project_tax_rates':ds(['0.15','0.25']),
 'project_nopat_to_initial_capital_tests':ds(['0.08','0.10','0.12']),
 'utilisation_tests':ds(['1','0.70']),
 'equipment_lives_years':ds(['10','5']), # H26 stated machinery policy; project allocation unknown.
 'equipment_residual':D('0.03'),
 'bga_incremental_contribution_tests':ds(['0.25','0.35','0.45']),
 'nominal_gz_parent_fraction_test':D('0.5231'), # G1 pre-transaction nominal; NOT effective P&L allocation.
 'mature_ic_margin_increase':D('0.10'),'mature_pcb_margin_increase':D('0.02'),
 'mature_incremental_tax_test':D('0.25'),
 'redemption_rounded_stress':D('1300000000'), # G1 approximate exit scale, not exact due-date cash demand.
}

def main():
    assert sum(v[0] for v in PRODUCTS.values()) == H['revenue']
    assert sum(v[1] for v in PRODUCTS.values()) == H['cost']
    assert H['ni'] == H['parent_ni'] + H['minority_ni']
    assert H['ni'] == H['pretax'] - H['tax']
    assert sum(CFO_BRIDGE.values()) == H['cfo']
    assert H['begin_cash'] + sum(H[k] for k in ['cfo','cfi','cff','fx']) == H['end_cash']
    for i in (0,1):
        assert sum(QUARTERS[f'2025Q{q}'][i] for q in range(1,5)) == ANNUALS['2025'][i]
    q2 = {k:H[k]-Q1[k] for k in Q1}
    QUARTERS['2026Q2'] = [q2['revenue'],q2['parent_ni']]
    gp = H['revenue']-H['cost']; gp_prev = PREV['revenue']-PREV['cost']
    other_gp=H['other_biz_rev']-H['other_biz_cost']
    other_gp_prev=H['other_biz_rev_prev']-H['other_biz_cost_prev']
    debt_like=sum(H[k] for k in ['short_debt','current_debt_lease','long_debt','noncurrent_lease','put_liability'])
    refund_increment=H['refund']-PREV['refund']
    mature_gross_gain=PRODUCTS['IC_CSP_AND_BGA'][0]*ASSUMPTIONS['mature_ic_margin_increase']+PRODUCTS['PCB'][0]*ASSUMPTIONS['mature_pcb_margin_increase']
    mature_pretax_gain=mature_gross_gain-(other_gp-other_gp_prev)
    mature_net_gain=mature_pretax_gain*(1-ASSUMPTIONS['mature_incremental_tax_test'])
    conditional=[]
    for name,p in PROJECTS.items():
        assert p['equipment']+p['facilities']+p['initial_wc']==p['investment']
        for tax in ASSUMPTIONS['project_tax_rates']:
            for r in ASSUMPTIONS['project_nopat_to_initial_capital_tests']:
                for u in ASSUMPTIONS['utilisation_tests']:
                    for life in ASSUMPTIONS['equipment_lives_years']:
                        da=p['equipment']*(1-ASSUMPTIONS['equipment_residual'])/life
                        ebit=p['investment']*r/(1-tax)
                        conditional.append({'project':name,'tax_assumption':tax,'nopat_capital_test':r,
                          'utilisation_assumption':u,'equipment_life_assumption':life,
                          'required_ebit_cny':ebit,'equipment_da_cny':da,
                          'unit_contribution_before_equipment_da_and_unallocated_amort_cny_m2':(ebit+da)/(p['annual_m2']*u)})
    # These sensitivity experiments cannot be added to each other without a combined cost model.
    result = {
      'qualification':'RETAINED_FILES_BUSINESS_CAPITAL_CONDITIONAL_CHECKS_NOT_FORECAST_OR_ODDS',
      'period':'2026H1 unless stated','currency':'CNY','investment_authority':'NONE',
      'checks_passed':['product sums','parent+minority=consolidated NI','pretax-tax=NI',
       'NI-to-CFO signed bridge','cash roll-forward','2025 quarterly revenue/NI totals','project cost sums'],
      'quarter_revenue_parent_ni_yi':{k:[x/YI for x in v] for k,v in QUARTERS.items()},
      'cash_yi':{
       'cfo':H['cfo']/YI,'cash_capex':H['capex']/YI,'cfo_less_capex':(H['cfo']-H['capex'])/YI,
       'net_wc_absorption':-sum(CFO_BRIDGE[k] for k in ['inventory_movement','operating_receivables','operating_payables'])/YI,
       'refunds':H['refund']/YI,'refund_increment_yoy':refund_increment/YI,
       'cfo_yoy_change':(H['cfo']-PREV['cfo'])/YI,
       'cfo_at_prior_year_refund_amount':(H['cfo']-refund_increment)/YI,
       'cfo_without_all_tax_refunds':(H['cfo']-H['refund'])/YI,
       'cfo_less_capex_at_prior_refunds':(H['cfo']-H['capex']-refund_increment)/YI,
       'q2_cfo':q2['cfo']/YI,'q2_capex':q2['capex']/YI,'q2_gap':(q2['cfo']-q2['capex'])/YI,
       'q2_refund':q2['refund']/YI,'q2_cfo_without_all_refunds':(q2['cfo']-q2['refund'])/YI,
       'cfi':H['cfi']/YI,'cff':H['cff']/YI,'fx':H['fx']/YI,
       'begin_cash':H['begin_cash']/YI,'end_cash':H['end_cash']/YI,
       'legacy_2022_2025_gap':sum(ANNUALS[y][3]-CAPEX[y] for y in CAPEX)/YI},
      'product_gross_yi':{k:(v[0]-v[1])/YI for k,v in PRODUCTS.items()},
      'product_gross_margin':{k:(v[0]-v[1])/v[0] for k,v in PRODUCTS.items()},
      'gross_diagnostics':{'total_yi':gp/YI,'other_business_yi':other_gp/YI,
       'other_business_share':other_gp/gp,'total_yoy_increase_yi':(gp-gp_prev)/YI,
       'other_business_yoy_increase_yi':(other_gp-other_gp_prev)/YI,
       'other_business_share_of_gp_growth':(other_gp-other_gp_prev)/(gp-gp_prev),
       'group_ni_improvement_yi':(H['ni']-PREV['ni'])/YI,
       'parent_ni_improvement_yi':(H['parent_ni']-PREV['parent_ni'])/YI,
       'minority_ni_change_yi':(H['minority_ni']-PREV['minority_ni'])/YI},
      'financing_yi':{'debt_like_including_put':debt_like/YI,
       'less_cash_equivalents':(debt_like-H['end_cash'])/YI,
       'bank_cash_less_equivalents':(H['bank_cash']-H['end_cash'])/YI,
       'put_balance':H['put_liability']/YI,
       'rounded_redemption_less_june_cash':(ASSUMPTIONS['redemption_rounded_stress']-H['end_cash'])/YI,
       'redemption_plus_short_and_current_less_cash':(ASSUMPTIONS['redemption_rounded_stress']+H['short_debt']+H['current_debt_lease']-H['end_cash'])/YI,
       'project_investment_less_project_raise':(sum(p['investment'] for p in PROJECTS.values())-D('3100000000'))/YI},
      'counterfactuals_not_forecasts':{
       'mature_gross_gain_yi':mature_gross_gain/YI,
       'mature_gain_after_other_biz_reversion_and_25pct_tax_yi':mature_net_gain/YI,
       'mature_resulting_consolidated_ni_yi':(H['ni']+mature_net_gain)/YI,
       'mature_ni_gain_does_not_close_existing_cash_gap_yi':(H['cfo']-H['capex']+mature_net_gain)/YI,
       'gz_zero_loss_group_ni_gain_yi':-H['gz_ni']/YI,
       'gz_zero_loss_parent_ni_gain_at_nominal_fraction_test_yi':-H['gz_ni']*ASSUMPTIONS['nominal_gz_parent_fraction_test']/YI,
       'gz_zero_loss_parent_result_at_nominal_fraction_test_yi':(H['parent_ni']-H['gz_ni']*ASSUMPTIONS['nominal_gz_parent_fraction_test'])/YI,
       'gz_incremental_h1_sales_to_cover_current_operating_loss_yi':{str(c):-H['gz_op']/c/YI for c in ASSUMPTIONS['bga_incremental_contribution_tests']},
       'csp_total_ic_revenue_per_nameplate_m2_not_asp':PRODUCTS['IC_CSP_AND_BGA'][0]/D('300000'),
       'csp_iii_full_year_sales_at_mixed_ic_capacity_proxy_yi':PRODUCTS['IC_CSP_AND_BGA'][0]/YI},
      'project_unit_economics_columns':['project','tax_assumption','nopat_capital_test','utilisation_assumption','equipment_life_assumption','required_ebit_cny','equipment_da_cny','unit_contribution_cny_m2'],
      'project_unit_economics_tests':[[str(v) for v in x.values()] for x in conditional],
      'unidentified':['project customer ASP and qualified sellable m2','non-machine amortisation and plant rent',
       'full additional WC and replacement capex','unit/entity effective parent attribution after contracts',
       'credible durable owner cash and enterprise/equity valuation','current transaction completion'],
      'not_run':['Kernel typed validators','independent-context review','Odds','investment decision']
    }
    Path(__file__).with_name('calculations.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'),default=str)+'\n',encoding='utf-8')
    # Compact review extract, full grid remains in saved JSON.
    compact={k:v for k,v in result.items() if k!='project_unit_economics_tests'}
    compact['project_10pct_25pct_full_utilisation']=[x for x in conditional if x['nopat_capital_test']==D('.10') and x['tax_assumption']==D('.25') and x['utilisation_assumption']==1]
    print(json.dumps(compact,ensure_ascii=False,indent=2,default=str))

if __name__=='__main__':
    main()
