#!/usr/bin/env python3
"""Offline conditional economics. Standard library only; no network or trading effects.
All monetary arithmetic uses Decimal. Inputs are NOT forecasts or a probability set.
Run: python calculate.py --check  (byte-for-byte deterministic replay)
"""
from __future__ import annotations
import argparse
import json
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent

def D(x: Any) -> Decimal:
    if not isinstance(x, str):
        raise ValueError('Decimal inputs must be explicit strings, never bool/float')
    d = Decimal(x)
    if not d.is_finite():
        raise ValueError('non-finite input')
    return d

def encoded(obj: Any) -> bytes:
    def conv(x: Any) -> Any:
        if isinstance(x, Decimal):
            return format(x, 'f')
        if isinstance(x, dict):
            return {k: conv(v) for k,v in x.items()}
        if isinstance(x, list):
            return [conv(v) for v in x]
        return x
    return (json.dumps(conv(obj), ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode()

def irr(initial: Decimal, cash: list[Decimal]) -> Decimal:
    if initial <= 0 or not cash or any(x < 0 for x in cash) or cash[-1] <= 0:
        raise ValueError('IRR routine is for one initial outflow and nonnegative future cash only')
    def f(r: Decimal) -> Decimal:
        return sum(x/(1+r)**(i+1) for i,x in enumerate(cash))-initial
    lo,hi = Decimal('-.999999'),Decimal('10')
    if f(lo)*f(hi) >= 0:
        raise ValueError('IRR outside declared bracket')
    for _ in range(180):
        mid=(lo+hi)/2
        if f(mid)>0: lo=mid
        else: hi=mid
    return (lo+hi)/2

def model(a: dict) -> dict:
    with localcontext() as ctx:
        ctx.prec=40
        S=D(a['securities']['CMES']['shares']); P=D(a['securities']['CMES']['reference_price_cny'])
        if S<=0 or P<=0: raise ValueError('positive shares and reference price required')
        o=a['operating_bridge']; v=a['valuation']; hist=a['historical_cmes']
        coeff=D(o['equivalent_vlccs'])*D(o['operating_days_per_year'])*D(o['usd_cny_assumption'])*D(o['marginal_parent_conversion_assumption'])
        cost=D(o['all_in_pnl_cost_usd_per_day_assumption']); other=D(o['other_net_parent_profit_cny_assumption'])
        def rate_for(ni: Decimal) -> Decimal: return cost+(ni-other)/coeff
        out={'research_id':a['research_id'],'probabilities':None,'canonical_odds':False,'investment_authority':'NONE'}
        out['operating']=[{'tce_usd_per_day':D(t),'parent_profit_cny':coeff*(D(t)-cost)+other,'eps_cny':(coeff*(D(t)-cost)+other)/S} for t in o['rates_usd_per_day']]
        out['delta_profit_per_10000_usd_day']=[{'name':e['name'],'delta_parent_profit_cny':D(e['n'])*D(e['days'])*D(e['fx'])*D(e['conversion'])*10000} for e in o['exposure_stress']]
        out['historical_checks']={
            '2025_cfo_less_cash_capex_cny': D(hist['2025']['cfo_cny'])-D(hist['2025']['cash_long_asset_capex_cny']),
            '2025_adjusted_profit_growth':D(hist['2025']['adjusted_parent_profit_cny'])/D(hist['2024']['adjusted_parent_profit_cny'])-1,
            '2025_parent_profit_growth':D(hist['2025']['parent_profit_cny'])/D(hist['2024']['parent_profit_cny'])-1,
            '2025_dividend_ratio':D(hist['2025']['dividend_cny'])/D(hist['2025']['parent_profit_cny']),
            '2026H1_cfo_less_rounded_capex_cny':D(hist['2026H1']['cfo_cny'])-D(hist['2026H1']['cash_long_asset_capex_cny_rounded'])}
        out['peer']=[]
        for name,z in a['securities'].items():
            s,p,ni,e=D(z['shares']),D(z['reference_price_cny']),D(z['h1_2026_parent_profit_cny']),D(z['h1_2026_parent_equity_cny'])
            scale=p*s
            out['peer'].append({'name':name,'a_price_times_total_shares_cny':scale,'h1_simple_annualized_pe':scale/(2*ni),'h1_book_value_per_share_cny':e/s,'a_price_to_h1_parent_book':scale/e,'old_named_forecast_pe':scale/D(z['previous_named_forecast_2026_cny'])})
        out['worlds']=[]
        for w in v['worlds']:
            ni=list(map(D,w['annual_parent_profit_cny']));q=D(w['payout']);k=D(w['exit_pe'])
            if len(ni)!=3 or not 0<=q<=1 or k<=0 or any(x<0 for x in ni) or ni[-1]<=0:
                raise ValueError('this PE stress requires three nonnegative earnings and a positive terminal year')
            div=[n*q/S for n in ni];terminal=ni[-1]*k/S; cash=div.copy();cash[-1]+=terminal
            pv={r:sum(c/(1+D(r))**(i+1) for i,c in enumerate(cash)) for r in v['discount_rates']}
            row={'id':w['id'],'name':w['name'],'annual_parent_profit_cny':ni,'implied_tce_central_usd_day':[rate_for(n) for n in ni],'payout':q,'exit_pe':k,'dividends_per_share_cny':div,'terminal_share_price_cny':terminal,'nominal_wealth_per_share_cny':sum(cash),'cumulative_return':sum(cash)/P-1,'annualized_unreinvested_wealth_return':(sum(cash)/P)**(Decimal(1)/3)-1,'annual_cashflow_irr':irr(P,cash),'present_price_cny':pv}
            # Headroom is not FCFE: omits working-capital, cash tax/classification,
            # JV/cash perimeter differences, leasing, debt principal and capex timing.
            da=D(hist['2025']['depreciation_amortization_cny'])*3
            row['capital_cash_stress_not_fcfe']=[{'hypothetical_3y_capex_cny':D(cap),'retained_profit_plus_constant_da_less_capex_cny':sum(ni)*(1-q)+da-D(cap)} for cap in v['capital_stress_total_capex_cny']]
            row['exit_multiple_pv_at_central_hurdle']={kstr:sum(d/(1+D(v['central_hurdle']))**(i+1) for i,d in enumerate(div))+ni[-1]*D(kstr)/S/(1+D(v['central_hurdle']))**3 for kstr in v['exit_pe_sensitivity']}
            out['worlds'].append(row)
        n1,n2=map(D,v['reverse_first_two_profit_cny']);q=D(v['reverse_payout']);k=D(v['reverse_exit_pe'])
        out['reverse']=[]
        for p in v['reverse_prices_cny']:
            for r in v['discount_rates']:
                z=1+D(r);n3=(D(p)*S*z**3-q*n1*z**2-q*n2*z)/(k+q)
                out['reverse'].append({'reference_price_cny':D(p),'required_return':D(r),'required_third_year_profit_cny':n3,'implied_tce_central_usd_day':rate_for(n3)})
        # Correlation and scope matter: this is a diagnostic, never a completed NAV.
        mc=out['peer'][0]['a_price_times_total_shares_cny'];equity=D(a['securities']['CMES']['h1_2026_parent_equity_cny']);n=D(o['equivalent_vlccs']);fx=D(o['usd_cny_assumption'])
        out['asset_cross_check']={'gross_50_ship_analogy_cny':n*fx*D(a['asset_cross_check']['external_2017_vlcc_sale_price_usd_each']),'market_above_h1_book_cny':mc-equity,'required_uplift_usd_per_ship_if_all_other_net_assets_stay_book':(mc-equity)/n/fx,'meaning':'Not NAV, not liquidation equity, not a price floor; selected peer transaction.'}
        out['cosco_equivalent_ships_for_same_price_scaled_delta']=n*out['peer'][1]['a_price_times_total_shares_cny']/mc
        # Explicitly hypothetical two-world break-even confidence, NOT estimated odds.
        b=out['worlds'][1]['present_price_cny'][v['central_hurdle']];d=out['worlds'][3]['present_price_cny'][v['central_hurdle']]
        out['binary_B_D_discounted_break_even_weight_not_probability_estimate']=(P-b)/(d-b)
        return out

def verify(a: dict, z: dict) -> dict:
    checks=[]
    def ok(name: str, truth: bool):
        if not truth: raise AssertionError(name)
        checks.append(name)
    with localcontext() as c:
        c.prec=40
        S=D(a['securities']['CMES']['shares']);P=D(a['securities']['CMES']['reference_price_cny'])
        ok('cash capex and CFO units', z['historical_checks']['2025_cfo_less_cash_capex_cny']==Decimal('1258048555.88'))
        ok('central 10k sensitivity independent arithmetic',z['delta_profit_per_10000_usd_day'][1]['delta_parent_profit_cny']==Decimal('1011500000'))
        ok('half-year profit is not a full-year datum',D(a['securities']['CMES']['h1_2026_parent_profit_cny'])*2!=D(a['securities']['CMES']['previous_named_forecast_2026_cny']))
        ok('C and E same earnings different financial/valuation world',z['worlds'][2]['annual_parent_profit_cny']==z['worlds'][4]['annual_parent_profit_cny'] and z['worlds'][2]['present_price_cny']['0.12']>z['worlds'][4]['present_price_cny']['0.12'])
        for w in z['worlds']:
            ni=w['annual_parent_profit_cny'];q=w['payout'];k=w['exit_pe']; r=Decimal('.12')
            alternate=(sum(n*q/(1+r)**(i+1) for i,n in enumerate(ni))+ni[-1]*k/(1+r)**3)/S
            ok('equity/per-share PV equivalence '+w['id'],abs(alternate-w['present_price_cny']['0.12'])<Decimal('1e-30'))
            cf=w['dividends_per_share_cny'].copy();cf[-1]+=w['terminal_share_price_cny']
            discounted=sum(x/(1+w['annual_cashflow_irr'])**(i+1) for i,x in enumerate(cf))
            ok('IRR cash timing '+w['id'],abs(discounted-P)<Decimal('1e-25'))
            ok('discount monotonicity '+w['id'],w['present_price_cny']['0.10']>w['present_price_cny']['0.12']>w['present_price_cny']['0.15'])
        for x in z['reverse']:
            n1,n2=map(D,a['valuation']['reverse_first_two_profit_cny']);n3=x['required_third_year_profit_cny'];q=D(a['valuation']['reverse_payout']);k=D(a['valuation']['reverse_exit_pe']);r=x['required_return']
            pv=(n1*q/(1+r)+n2*q/(1+r)**2+n3*(q+k)/(1+r)**3)/S
            ok('reverse closes to price '+str(x['reference_price_cny'])+'/'+str(r),abs(pv-x['reference_price_cny'])<Decimal('1e-30'))
        for bad in [True,2.3,'NaN','Infinity']:
            try:D(bad)
            except (ValueError, TypeError):checks.append('reject '+repr(bad))
            else:raise AssertionError('accepted unsafe value')
        ok('no probability or canonical promotion',z['probabilities'] is None and z['canonical_odds'] is False)
    return {'status':'PASS','checks_count':len(checks),'checks':checks,'scope':'Local arithmetic and serialization only, not source authenticity, valuation validity, full repository CI, independent research review or predictive validity.'}

def main() -> int:
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');ns=p.parse_args()
    a=json.loads((BASE/'inputs.json').read_text());z=model(a);results=encoded(z);verification=encoded(verify(a,z))
    if ns.check:
        if (BASE/'results.json').read_bytes()!=results:raise SystemExit('REPLAY_MISMATCH')
        print('REPLAY_MATCH; local arithmetic checks passed')
    else:
        (BASE/'results.json').write_bytes(results);(BASE/'verification.json').write_bytes(verification)
        print('results.json and verification.json written')
    return 0

if __name__=='__main__':raise SystemExit(main())
