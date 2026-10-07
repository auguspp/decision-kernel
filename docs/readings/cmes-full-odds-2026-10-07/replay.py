"""Retained CMES conditional study, 2026-10-07. No network or canonical Odds.
Run: python replay.py
All amounts: 亿元; shares: 亿股. Prices: dated third-party context.
Assumptions are not forecasts, complete FCFE or calibrated probabilities.
"""
from decimal import Decimal as D, getcontext
import json
getcontext().prec=40
P=D("20.15"); SH=D("80.74538502"); R=D(".12")
N=D(50); DAYS=D(345); FX=D("6.8"); COST=D(30000)
TAX=D(".15"); DISTR=D(".4"); CREDIT=D(100); UNIT=D(100000000)
WORLDS=[
("W1","一年冲击后恢复",[200000,80000,50000,45000,45000],45000,20),
("W2","三年较强后回落",[200000,160000,120000,90000,70000],70000,20),
("W3","五年持续高景气",[250000,230000,200000,180000,150000],100000,20),
("W4","极强且长期抬升",[400000,350000,300000,250000,200000],150000,20),
("WS","油运与其他业务共振下行",[80000,40000,25000,35000,40000],40000,10)]
def cash(t,other):
    gross=N*DAYS*(D(t)-COST)*FX/UNIT
    return gross*(1-TAX if gross>0 else D(1))+D(other)
def irr(flows):
    lo,hi=D("-.99"),D(10)
    def npv(x):return sum(v/(1+x)**i for i,v in enumerate(flows))
    if npv(lo)*npv(hi)>0:return None
    for _ in range(180):
        mid=(lo+hi)/2
        if npv(mid)>0:lo=mid
        else:hi=mid
    return (lo+hi)/2
def run():
    output=[]
    for ident,label,path,steady,other in WORLDS:
        cf=[cash(t,other) for t in path]; tv=cash(steady,other)/R
        operating=sum(v/(1+R)**i for i,v in enumerate(cf,1))+tv/(1+R)**5
        distributions=[max(D(0),v)*DISTR for v in cf[:3]]
        retained=sum(cf[:3])-sum(distributions)
        exit_operating=cf[3]/(1+R)+cf[4]/(1+R)**2+tv/(1+R)**2
        terminal=exit_operating+retained+CREDIT*(1+R)**3
        flows=[-P,distributions[0]/SH,distributions[1]/SH,(terminal+distributions[2])/SH]
        paid=sum(flows[1:]); entry=sum(v/(1+R)**i for i,v in enumerate(flows[1:],1))
        output.append(dict(id=ident,label=label,tce=path,steady_tce=steady,cf_yi=cf,
          capacity_price=(operating+CREDIT)/SH,three_year_total=paid,
          cumulative=paid/P-1,irr=irr(flows),entry_for_12pct=entry))
    reverse=[]
    for r in map(D,[".10",".12",".14"]):
        for credit in map(D,["0","100","200"]):
            cf=r*(P*SH-credit)
            tce=COST+(cf-20)*UNIT/(N*DAYS*FX*(1-TAX))
            reverse.append(dict(r=r,credit_yi=credit,required_cash_yi=cf,required_tce=tce))
    low,high=output[1],output[3]
    weights={"undiscounted_break_even":(P-low["three_year_total"])/(high["three_year_total"]-low["three_year_total"]),
      "discounted_12pct_requirement":(P-low["entry_for_12pct"])/(high["entry_for_12pct"]-low["entry_for_12pct"]),
      "NOT_PROBABILITY_ESTIMATES":True}
    return {"semantics":"MANUAL_CONDITIONAL_NOT_CANONICAL_OR_HUMAN_ACCEPTED",
      "reference_date":"2026-09-30","study_date":"2026-10-07","horizon":"2029-10-07",
      "worlds":output,"reverse":reverse,"two_endpoint_requirements":weights,
      "complete_distribution":False,"calibrated_probability":None,"investment_authority":"NONE"}
if __name__=="__main__":
    print(json.dumps(run(),default=str,ensure_ascii=False,indent=2))
