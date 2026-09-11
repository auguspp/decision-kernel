"""Local arithmetic checks only. This is not a Decision Kernel validator."""
from decimal import Decimal as D, getcontext
from pathlib import Path
import json
getcontext().prec=40
root=Path(__file__).resolve().parent
a=json.loads((root/"calculation_audit.json").read_text(encoding="utf-8"))
h={k:D(v) for k,v in a["historical_cny"].items()}
checks={}
checks["cash_closing_cny"]=h["opening_cash"]+h["cfo"]-h["capex_total"]+h["investment_returns"]+h["asset_disposals"]-h["equity_investment_outflow"]+h["borrowing"]-h["debt_repayment"]-h["dividend_interest_payment"]-h["buybacks"]-h["lease_payment"]+h["fx_cash_effect"]-h["closing_cash"]
checks["rd_expense_capitalized_reconcile_cny"]=h["expensed_rd"]+h["accrued_capitalized_rd"]-h["total_rd_investment"]
checks["rd_net_balance_additions_cny"]=h["rd_balance_additions"]-h["rd_transfer_to_expense"]-h["accrued_capitalized_rd"]
checks["cash_diagnostic_cny"]=h["cfo"]-h["capex_total"]-h["cash_interest_in_cfo"]-D(a["calculations"]["cfo_minus_capex_minus_gross_interest"])*D("1e8")
checks["selected_cash_receipts_usd"]=D("500000000")+D("200000000")+D("75000000")+D("32500000")+D("2000000")-D(a["new_calc_checks"]["selected_verified_receipts_usd"])
for name,residual in checks.items():
    if residual!=0:
        raise AssertionError(f"{name}: nonzero residual {residual}")
print(json.dumps({"engine":"Python Decimal; not Kernel", "checks":{k:str(v) for k,v in checks.items()},"status":"PASS","probabilities":None,"qualified_odds":False},ensure_ascii=False,indent=2))
