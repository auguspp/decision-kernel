"""One retained 688337 cash-conversion workpaper; stdlib, offline and create-only.

Numbers below are manually reviewed, paired columns from an exact saved text.
Token checks and arithmetic do not authenticate the issuer or original PDF layout.
No production method, forecast, probability, source call or Human decision.
"""
from __future__ import annotations
import argparse
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path

CONTEXT_SHA256 = 'b27853cd4db25ad8f8830cb33c6e06dab958f2b82912c2d47a318501e85ae463'
CONTEXT_BLOB = '62c24a0c3e5f76d09384439f0dcc6a8e459ed8b2'
# Each tuple: current H1 / prior H1 (or ending / beginning balance), source page.
PAIRS = {
 'revenue': ('486842894.90','354968365.55',84),
 'cost': ('220805439.15','158352858.95',84),
 'selling': ('61317886.54','58351596.87',85),
 'admin': ('45455329.18','49882850.44',85),
 'research': ('115651532.56','108363247.61',85),
 'surtax': ('5052180.01','5638071.13',85),
 'pretax': ('41441061.86','9183223.92',85),
 'net_profit': ('37147734.08','16215794.21',85),
 'investment_income': ('88628242.35','8653738.04',85),
 'fair_value_income': ('-72926183.85','18748574.97',85),
 'fx_expense': ('11299512.06','-9993466.63',168),
 'cfo': ('-13693036.03','-13676150.84',89),
 'capex': ('10633920.19','32298494.06',89),
 'cash_inventory': ('-70649300.70','-28421725.02',174),
 'cash_receivables': ('-16326871.96','10330901.39',174),
 'cash_payables': ('4001603.47','-32732328.47',174),
 'cash_contracts': ('-10692962.01','-1133221.82',174),
 'rebates': ('32707929.50','37369987.06',157),
 'customer_advances': ('13221767.03','19252671.48',157),
 'contract_total': ('45929696.53','56622658.54',157),
 'inventory_gross': ('413021547.82','345514672.39',138),
 'inventory_allowance': ('21048263.69','18786769.01',138),
 'inventory_net': ('391973284.13','326727903.38',138),
 'raw_material_net': ('244391693.75','193071153.79',138),
 'finished_goods_net': ('77705820.86','60763139.89',138),
 'parent_net_profit': ('14038650.60','18692031.19',87),
 'parent_cfo': ('44666857.64','-13460807.89',90),
}
AR = [
 ('not_due','99239271.12','11720.79'),
 ('overdue_1_30','48221213.82','54751.36'),
 ('overdue_31_60','23124739.14','49943.09'),
 ('overdue_61_90','15558563.76','327235.42'),
 ('overdue_91_120','10258832.33','91976.95'),
 ('overdue_121_360','9592891.61','260414.76'),
 ('overdue_1year_plus','3249876.01','3249876.01'),
]
SINGLE = {'restricted_cash_release': ('7044387.10',172),
          'ar_gross': ('209245387.79',130), 'ar_allowance': ('4045918.38',130)}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def number(text):
    require(type(text) is str, 'decimal-string required')
    value = Decimal(text)
    require(value.is_finite(), 'nonfinite input')
    return value


def encode(value):
    return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()


def calculate(raw):
    require(hashlib.sha256(raw).hexdigest()==CONTEXT_SHA256,'saved context SHA256 differs')
    require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==CONTEXT_BLOB,
            'saved context Git blob differs')
    packet=json.loads(raw)
    docs=packet['issuer_documents']
    require(len(docs)==1 and docs[0]['announcement_id']=='1225502922','issuer source identity')
    doc=docs[0]
    require(doc['page_count']==205 and len(doc['pages'])==205,'complete retained text inventory')
    pages={row['page_number']:row['text'].replace(',','') for row in doc['pages']}
    require(len(pages)==205,'duplicate page')
    for name,(a,b,page) in PAIRS.items():
        require(a in pages[page] and b in pages[page], 'reviewed numeric token missing: '+name)
    for name,(v,page) in SINGLE.items():
        require(v in pages[page], 'reviewed numeric token missing: '+name)
    for label,gross,allowance in AR:
        require(gross in pages[130] and allowance in pages[130],'AR token missing: '+label)
    with localcontext() as ctx:
        ctx.prec=40
        p={k:tuple(number(x) for x in row[:2]) for k,row in PAIRS.items()}
        s={k:number(v[0]) for k,v in SINGLE.items()}
        delta=lambda k:p[k][0]-p[k][1]
        text=lambda v:format(v.quantize(Decimal('.01')),'f')
        fraction=lambda v:format(v.quantize(Decimal('.000001')),'f')
        pair=lambda v:{'current':text(v[0]),'prior':text(v[1]),'change':text(v[0]-v[1])}
        gross=tuple(p['revenue'][i]-p['cost'][i] for i in range(2))
        commercial=tuple(gross[i]-sum(p[k][i] for k in ('selling','admin','research','surtax')) for i in range(2))
        financial=tuple(p['investment_income'][i]+p['fair_value_income'][i] for i in range(2))
        pretax_without_two=tuple(p['pretax'][i]-financial[i]+p['fx_expense'][i] for i in range(2))
        wc=tuple(sum(p[k][i] for k in ('cash_inventory','cash_receivables','cash_payables','cash_contracts')) for i in range(2))
        other=tuple(p['cfo'][i]-wc[i] for i in range(2))
        simple=tuple(p['cfo'][i]-p['capex'][i] for i in range(2))
        for i in range(2):
            require(p['rebates'][i]+p['customer_advances'][i]==p['contract_total'][i],'contract components do not reconcile')
            require(p['inventory_gross'][i]-p['inventory_allowance'][i]==p['inventory_net'][i],'inventory gross/net bridge')
        require(delta('contract_total')==p['cash_contracts'][0],'contract balance and cash adjustment differ')
        ar=sum(number(v[1]) for v in AR)
        allowance=sum(number(v[2]) for v in AR)
        require(ar==s['ar_gross'] and allowance==s['ar_allowance'],'AR aging totals do not reconcile')
        overdue=ar-number(AR[0][1]);long_overdue=sum(number(v[1]) for v in AR[4:])
        return {
          'kind':'BOUNDED_RETAINED_688337_ANALYSIS_NOT_FULL_OR_PRODUCTION_RESULT',
          'periods':['2026H1','2025H1'], 'balance_dates':['2026-06-30','2025-12-31'],
          'amount_unit':'CNY', 'source_context_sha256':CONTEXT_SHA256,
          'profit':{'gross_profit':pair(gross),'commercial_surplus_before_finance_other_gains_and_tax':pair(commercial),
            'investment_plus_fair_value_income':pair(financial),
            'pretax_excluding_financial_net_income_and_fx':pair(pretax_without_two),
            'reported_net_profit':pair(p['net_profit']),
            'normalized_recurring_profit':None},
          'cash':{'reported_cfo':pair(p['cfo']), 'four_working_capital_adjustments':pair(wc),
            'cfo_less_four_adjustments_mechanical_residual_not_operating_metric':pair(other),
            'current_restricted_cash_release':text(s['restricted_cash_release']),
            'current_cfo_less_release_sensitivity_not_reported_cfo':text(p['cfo'][0]-s['restricted_cash_release']),
            'reported_capex':pair(p['capex']), 'cfo_less_capex_not_owner_fcf':pair(simple),
            'cash_balance_change_from_lower_capex':text(-delta('capex')),
            'current_cfo_less_release_less_capex':text(simple[0]-s['restricted_cash_release'])},
          'contract_liabilities':{'total_change':text(delta('contract_total')),
            'rebate_change':text(delta('rebates')),'customer_advance_change':text(delta('customer_advances')),
            'rebate_fraction_of_total_decline':fraction(delta('rebates')/delta('contract_total')),
            'order_backlog':None},
          'inventory':{'gross_change':text(delta('inventory_gross')),'allowance_change':text(delta('inventory_allowance')),
            'net_change':text(delta('inventory_net')),'raw_material_net_change':text(delta('raw_material_net')),
            'finished_goods_net_change':text(delta('finished_goods_net')),
            'other_net_change':text(delta('inventory_net')-delta('raw_material_net')-delta('finished_goods_net')),
            'cash_adjustment_magnitude_less_gross_change_unallocated':text(-p['cash_inventory'][0]-delta('inventory_gross')),
            'cash_adjustment_magnitude_less_net_change_unallocated':text(-p['cash_inventory'][0]-delta('inventory_net')),
            'product_or_subsidiary_attribution':None},
          'trade_receivables':{'gross':text(ar),'overdue':text(overdue),'overdue_fraction':fraction(overdue/ar),
            'over_90_days':text(long_overdue),'over_90_days_fraction':fraction(long_overdue/ar),
            'allowance':text(allowance),'calculated_allowance_fraction':fraction(allowance/ar),
            'prior_aging_comparison':None,'expected_loss_from_overdue_fraction':None},
          'parent_vs_consolidated':{'parent_net_profit':pair(p['parent_net_profit']),
            'consolidated_less_parent_profit_not_subsidiary_contribution':pair(tuple(p['net_profit'][i]-p['parent_net_profit'][i] for i in range(2))),
            'parent_cfo':pair(p['parent_cfo']),
            'consolidated_less_parent_cfo_not_subsidiary_cash':pair(tuple(p['cfo'][i]-p['parent_cfo'][i] for i in range(2))),
            'elimination_and_business_attribution':None},
          'qualification':{'new_company_fact':False,'fresh_primary_document_recovered':False,
            'original_pdf_visual_verified_this_review':False,'original_quick_modified':False,
            'historical_human_acceptance_inherited':False,'formal_full_research':False,
            'probability':None,'target_price':None,'investment_authority':'NONE'}
        }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context',type=Path,required=True)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',type=Path)
    mode.add_argument('--output',type=Path)
    args=parser.parse_args()
    require(args.context.is_file() and not args.context.is_symlink(),'regular context file required')
    result=encode(calculate(args.context.read_bytes()))
    if args.check:
        require(args.check.is_file() and not args.check.is_symlink(),'regular result file required')
        require(args.check.read_bytes()==result,'retained result differs')
        print('RETAINED_RESULT_MATCH')
    else:
        with args.output.open('xb') as stream:stream.write(result)
        print('CREATED',args.output)

if __name__=='__main__':main()
