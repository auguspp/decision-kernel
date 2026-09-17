"""Bounded research arithmetic. No market access, no Kernel or investment authority."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
price = 191.22
shares = 827_848_838
shares_yi = shares / 1e8
fy25 = {'revenue':11928697127.38,'parent_profit':946320781.21,'deducted_profit':915411336.26,'cfo':1627903629.64,'capex':825419173.80}
h125 = {'revenue':5242939494.93,'parent_profit':372368765.82,'deducted_profit':360004853.58,'cfo':-107323990.68,'capex':323238311.01}
h126 = {'revenue':6609670765.36,'parent_profit':582178717.03,'deducted_profit':567996131.78,'cfo':-1236139694.41,'capex':600397792.73}
ttm = {k:fy25[k] + h126[k] - h125[k] for k in fy25}
profit_bridge={'revenue':6609670765.36,'cost':-4922515323.82,'surcharges':-19798181.82,'selling':-152489601.05,'administration':-105180333.46,'expensed_rd':-586408269.63,'net_financial_expense':-14089327.60,'other_income':49352573.52,'equity_investment_loss':-7029309.25,'credit_reversal':75877.71,'asset_impairment':-193548861.13,'disposal_gain':64851.29,'nonoperating_income':403250.21,'nonoperating_expense':-2086415.11,'income_tax':-83402919.56,'less_noncontrolling_profit':9159941.37}
assert abs(sum(profit_bridge.values())-h126['parent_profit']) < .1
cash_bridge = {'consolidated_net_profit':573018775.66,'impairment':193472983.42,'depreciation':201169912.73,'rou_depreciation':4933746.04,'amortization':41671167.19,'long_term_deferred_amort':6953087.14,'asset_disposal_gain':-64851.29,'asset_retirement_loss':2062185.05,'financial_adjustment':14089327.60,'investment_loss':7029309.25,'deferred_tax':-23786395.17,'inventory_movement':-3402600372.69,'operating_receivables_movement':-1395700628.66,'operating_payables_movement':2501221378.43,'other':40390680.89}
assert abs(sum(cash_bridge.values()) - h126['cfo']) < .1
other_non_cash = sum(v for k,v in cash_bridge.items() if k not in ['consolidated_net_profit','inventory_movement','operating_receivables_movement','operating_payables_movement'])
nwc_cash_impact = sum(cash_bridge[k] for k in ['inventory_movement','operating_receivables_movement','operating_payables_movement'])
cash_roll = {'opening':4441844115.15,'cfo':-1236139694.41,'cfi':-600325522.23,'cff':3360716492.95,'ending':5925704710.57}
cash_roll['fx_and_other'] = cash_roll['ending']-cash_roll['opening']-cash_roll['cfo']-cash_roll['cfi']-cash_roll['cff']

world_specs = [
    # amounts in CNY 100 million; financial/world assumptions, not forecasts
    dict(id='W1',name='需求放缓与库存压力',transmission=35,data_access=70,gm_t=.24,gm_d=.18,sga=.04,rd=.09,impair=.03,stranded=0,tax=.15,da=.035,capex=.05,end_growth=0,nwc_ratio=.35,extra_nwc=0),
    dict(id='W2',name='收入增长但毛利承压',transmission=50,data_access=130,gm_t=.26,gm_d=.21,sga=.04,rd=.09,impair=.025,stranded=0,tax=.15,da=.03,capex=.05,end_growth=.10,nwc_ratio=.40,extra_nwc=0),
    dict(id='W3',name='组合升级与现金改善',transmission=55,data_access=150,gm_t=.29,gm_d=.29,sga=.038,rd=.085,impair=.02,stranded=0,tax=.15,da=.03,capex=.04,end_growth=.15,nwc_ratio=.25,extra_nwc=0),
    dict(id='W3C',name='同样利润但资金继续沉淀',transmission=55,data_access=150,gm_t=.29,gm_d=.29,sga=.038,rd=.085,impair=.02,stranded=0,tax=.15,da=.03,capex=.06,end_growth=.15,nwc_ratio=.50,extra_nwc=8),
    dict(id='W4',name='高速数据成功而传输回落',transmission=35,data_access=180,gm_t=.25,gm_d=.33,sga=.04,rd=.09,impair=.02,stranded=1.5,tax=.15,da=.035,capex=.06,end_growth=.20,nwc_ratio=.35,extra_nwc=0),
    dict(id='W5',name='份额良率强兑现',transmission=60,data_access=220,gm_t=.30,gm_d=.34,sga=.035,rd=.08,impair=.015,stranded=0,tax=.15,da=.03,capex=.055,end_growth=.25,nwc_ratio=.30,extra_nwc=0),
    dict(id='W6',name='双引擎规模跃升但重资本占用',transmission=100,data_access=350,gm_t=.26,gm_d=.26,sga=.035,rd=.08,impair=.02,stranded=0,tax=.15,da=.03,capex=.07,end_growth=.35,nwc_ratio=.40,extra_nwc=0),
]
worlds=[]
for s in world_specs:
    s.update(surcharges=.003,net_financial_expense=.002,other_net_income_yi=0,noncontrolling_profit_yi=0)
    revenue=s['transmission']+s['data_access']
    gross=s['transmission']*s['gm_t']+s['data_access']*s['gm_d']
    pretax=gross-revenue*(s['sga']+s['rd']+s['impair']+s['surcharges']+s['net_financial_expense'])-s['stranded']+s['other_net_income_yi']
    profit=pretax*(1-s['tax'])-s['noncontrolling_profit_yi']
    nwc=s['nwc_ratio']*revenue*s['end_growth']/(1+s['end_growth'])+s['extra_nwc']
    owner_cash_proxy=profit+revenue*s['da']-revenue*s['capex']-nwc
    d={**s,'revenue':revenue,'gross_profit':gross,'pretax_profit':pretax,'parent_profit_proxy':profit,'net_margin':profit/revenue,'owner_cash_proxy':owner_cash_proxy,'nwc_investment':nwc,'capex_cash':revenue*s['capex'],'depreciation_amortization':revenue*s['da'],'eps':profit/shares_yi,'revenue_cagr_from_h1_annualized':(revenue/(2*h126['revenue']/1e8))**(1/3)-1}
    d['end_price_sensitivity']={str(pe):{'price':profit*pe/shares_yi,'capital_return':profit*pe/shares_yi/price-1,'annualized_return':(profit*pe/shares_yi/price)**(1/3)-1} for pe in [20,30,40,60]}
    worlds.append(d)

requirements=[]
for pe in [20,30,40,50,60]:
    cap=price*shares_yi
    p0=cap/pe
    p10=cap*1.1**3/pe
    requirements.append({'terminal_pe':pe,'break_even_profit_yi':p0,'profit_for_3yr_10pct_yi':p10,'required_revenue_at_10pct_margin_yi':p10/.10,'required_revenue_at_15pct_margin_yi':p10/.15,'required_revenue_at_20pct_margin_yi':p10/.20,'check_price':p10*pe/(shares_yi*1.1**3)})
    assert abs(requirements[-1]['check_price']-price)<1e-9

def justified_pe(g,roe,r,n,gs=.03,roes=.12):
    payout=1-g/roe
    terminal=(1-gs/roes)*(1+gs)/(r-gs)
    pe=sum(payout*(1+g)**t/(1+r)**t for t in range(1,n+1))+terminal*((1+g)/(1+r))**n
    return {'g':g,'roe':roe,'r':r,'years':n,'stable_g':gs,'stable_roe':roes,'payout':payout,'terminal_pe':terminal,'justified_pe':pe}
pe_checks=[justified_pe(.10,.15,.10,5),justified_pe(.15,.25,.10,10),justified_pe(.15,.25,.12,10),justified_pe(.20,.30,.10,10),justified_pe(.20,.30,.10,15)]

market_context={'price_cny':price,'shares':shares,'equity_value_yi':price*shares_yi,'ttm_pe':price*shares/ttm['parent_profit'],'fy25_pe':price*shares/fy25['parent_profit'],'price_authority':'CONTEXT_ONLY','observed_date':'2026-09-17','current_share_basis':'2026-09-05 registered-capital announcement: completed share issuance, excluding future cancellation','horizon_years':3,'required_return_assumption':.10,'dividend_assumption_cny':0,'capital_loss_tolerance':'NOT_PROVIDED'}
sell_side=[{'institution':'国联民生','date':'2026-08-31','parent_profit_yi':[16.09,37.72,50.28],'revenue_yi':[200.57,407.40,535.19]}, {'institution':'西南证券','date':'2026-08-30','parent_profit_yi':[16.42,29.62,44.83],'revenue_yi':[171.87,256.96,363.91]}]
for row in sell_side:
    row['target_years']=[2026,2027,2028]
    row['source']='https://basic.10jqka.com.cn/002281/worth.html'
    row['profit_scope']='PARENT_NET_PROFIT_FORECAST_NOT_REPORTED'
    row['recomputed_forward_pe']=[price*shares_yi/p for p in row['parent_profit_yi']]
    row['implied_net_margins']=[p/r for p,r in zip(row['parent_profit_yi'],row['revenue_yi'])]
    row['profit_cagr_2025_2028']=(row['parent_profit_yi'][-1]/(fy25['parent_profit']/1e8))**(1/3)-1
    row['revenue_cagr_2025_2028']=(row['revenue_yi'][-1]/(fy25['revenue']/1e8))**(1/3)-1
    row['required_h2_2026_profit_yi']=row['parent_profit_yi'][0]-h126['parent_profit']/1e8
    row['h2_2026_profit_growth_required']=row['required_h2_2026_profit_yi']/((fy25['parent_profit']-h125['parent_profit'])/1e8)-1

stress=[]
for p in [5,10,25,45,60]:
    for pe in [20,30,40,60]:
        end_price=p*pe/shares_yi
        stress.append({'terminal_parent_profit_yi':p,'pe':pe,'end_price':end_price,'capital_return':end_price/price-1,'annualized_return':(end_price/price)**(1/3)-1})

result={'method':'Bounded research arithmetic, not canonical Odds','inputs':{'fy2025_cny':fy25,'h12025_cny':h125,'h12026_cny':h126,'h126_cash_bridge_cny':cash_bridge,'h126_cash_roll_cny':cash_roll},'ttm_cny':ttm,'financial_checks':{'cfo_bridge_cny':sum(cash_bridge.values()),'other_adjustments_cny':other_non_cash,'nwc_cash_impact_cny':nwc_cash_impact,'h126_cfo_minus_capex_cny':h126['cfo']-h126['capex'],'ttm_cfo_minus_capex_cny':ttm['cfo']-ttm['capex'],'ttm_cfo_parent_profit_ratio':ttm['cfo']/ttm['parent_profit'],'h126_parent_margin':h126['parent_profit']/h126['revenue'],'transmission_growth_contribution':(2283334437.83-1517055973.79)/(h126['revenue']-h125['revenue'])},'market_context':market_context,'conditional_worlds':worlds,'price_implied_requirements':requirements,'pe_reinvestment_checks':pe_checks,'published_expectations_proxy':sell_side,'profit_pe_stress':stress,'limitations':['World inputs are analyst assumptions, not calibrated forecasts.','Reported CFO already includes working capital.','Projected owner cash is an economic proxy, not forecast reported CFO or exact FCFE.','No probabilities; no weighted return; no Kernel or market validator.','No added cash, chip business, CPO option or dividend double count.','5/10/15 year high-growth durations and ROE assumptions are sensitivities, not established company attributes.','Quoted 2028 forecasts are not automatically 2029 forecasts.']}
result['inputs']['h126_reported_parent_profit_bridge_cny']=profit_bridge
result['financial_checks']['parent_profit_bridge_cny']=sum(profit_bridge.values())
result['revision_bridge']={'builder_v1_to_v2':['Add explicit surcharges 0.3% of revenue, net financial expense 0.2%, other net income zero, minority profit zero as forward assumptions; historical bridge reconciles exactly.','Add W6 after challenger/outside-view review: a larger transmission+data scale can deliver profit without W5 gross margins; this is not a probability update.','Preserve W3C: same profit and different capital absorption.','No forward profit adopted as company guidance.']}
result['sell_side_same_institution_revision']={'institution':'长江证券','earlier_date':'2026-04-30','later_date':'2026-09-10','target_years':[2026,2027,2028],'earlier_parent_profit_yi':[14.71,19.89,27.03],'later_parent_profit_yi':[17.35,33.86,45.41],'revision_rates':[b/a-1 for a,b in zip([14.71,19.89,27.03],[17.35,33.86,45.41])],'current_forward_pe':[price*shares_yi/p for p in [17.35,33.86,45.41]]}
result['near_term_requirements']=[{'institution':i,'2026_profit_yi':p,'h2_required_yi':p-h126['parent_profit']/1e8,'h2_yoy_required':(p-h126['parent_profit']/1e8)/((fy25['parent_profit']-h125['parent_profit'])/1e8)-1} for i,p in [('中金公司',16.74),('长江证券',17.35)]]
result['proposed_h_share_sensitivity']={'status':'BOARD_PROPOSAL_PENDING_2026_09_21_SHAREHOLDER_MEETING','initial_post_issue_h_fraction':.074,'max_greenshoe':.15,'initial_new_shares_over_existing':.074/(1-.074),'full_greenshoe_new_shares_over_existing':.074/(1-.074)*1.15,'eps_dilution_if_profit_unchanged_initial':.074,'eps_dilution_if_profit_unchanged_full_greenshoe':1-1/(1+.074/(1-.074)*1.15),'assumed_in_main_price_calculation':False}
(OUT/'accelink-calculations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'financial_checks':result['financial_checks'],'market':market_context,'worlds':[{k:v for k,v in d.items() if k in ['id','name','revenue','parent_profit_proxy','owner_cash_proxy','eps','revenue_cagr_from_h1_annualized']} for d in worlds],'requirements':requirements,'pe_checks':pe_checks,'sell_side':sell_side},ensure_ascii=False,indent=2))
