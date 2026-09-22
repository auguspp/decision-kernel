"""Arithmetic on retained issuer disclosures; no I/O, model or trading authority.

Inputs were checked against physical H1 pages154/165/166. Values are CNY,
consolidated unless explicitly labelled. No forecast or cash-availability claim.
"""
from decimal import Decimal
import json


def build():
    cash_bridge = {
        "group_net_profit": (9500773307, 4417391454),
        "asset_impairment": (2881045213, 782641135),
        "credit_impairment": (23497011, 160597643),
        "ppe_and_investment_property_depreciation": (1528934382, 1289512975),
        "intangibles_amortization": (199908026, 196166749),
        "asset_disposal_loss": (6082121, 5324132),
        "special_reserve_increase": (277870219, 291743561),
        "rou_depreciation": (82750580, 92425540),
        "fair_value_gain_adjustment": (-3182537965, 307000273),
        "financial_expense": (1450007570, 1242880810),
        "investment_income_adjustment": (-1531544635, -191537382),
        "deferred_income_amortization": (-32361851, -35192272),
        "deferred_tax_asset_increase": (-440277042, -248214070),
        "deferred_tax_liability_decrease": (-13874911, -17285250),
        "inventory_decrease_or_increase": (648784432, -7827695974),
        "operating_receivables_increase": (-7367120878, -5507965675),
        "operating_payables_increase": (1782295414, 7913612150),
    }
    observed_ocf = (5814230993, 2871405799)
    working = ("inventory_decrease_or_increase", "operating_receivables_increase", "operating_payables_increase")
    checks = []
    def check(name, actual, expected):
        checks.append({"name": name, "computed": actual, "disclosed_or_reconciled": expected,
                       "difference": actual - expected})
        if actual != expected:
            raise ValueError(name + ": arithmetic difference")
    wc = tuple(sum(cash_bridge[k][i] for k in working) for i in range(2))
    for i, period in enumerate(("2026H1", "2025H1")):
        check(period + "_group_profit_to_ocf", sum(v[i] for v in cash_bridge.values()), observed_ocf[i])
    other = tuple(observed_ocf[i] - cash_bridge["group_net_profit"][i] - wc[i] for i in range(2))
    changes = {"group_profit_change": cash_bridge["group_net_profit"][0]-cash_bridge["group_net_profit"][1],
               "other_reconciliation_change": other[0]-other[1], "three_operating_adjustments_change": wc[0]-wc[1]}
    check("ocf_change_bridge", sum(changes.values()), observed_ocf[0]-observed_ocf[1])
    revenue = {"industry_and_other_nontrade": 247712523385, "trade": 58456809999,
               "other": 777966499, "construction_services": 207638860}
    cost = {"industry_and_other_nontrade": 230685032579, "trade": 57750971573,
            "other": 695151035, "construction_services": 136453632}
    check("H1_revenue_parts", sum(revenue.values()), 307154938743)
    check("H1_cost_parts", sum(cost.values()), 289267608819)
    gross = {k: revenue[k]-cost[k] for k in revenue}
    check("H1_gross_profit_parts", sum(gross.values()), 307154938743-289267608819)
    liquid = (27437264230, 14959025454)
    excluded = (56452003318, 19585110307)
    monetary = (83889267548, 34544135761)
    for i, day in enumerate(("2026-06-30", "2025-12-31")):
        check(day + "_monetary_funds_perimeter", liquid[i]+excluded[i], monetary[i])
    increase = {"cash_and_equivalents": liquid[0]-liquid[1], "excluded_margin_and_restricted": excluded[0]-excluded[1]}
    check("monetary_funds_increase_split", sum(increase.values()), monetary[0]-monetary[1])
    check("H1_net_acquisition_cash", 6966935286-90891382, 6876043904)
    return {
        "qualification": "ARITHMETIC_CHECK_ONLY_NOT_RESEARCH_ADMISSION_OR_TRUTH_CERTIFICATION",
        "currency": "CNY", "perimeter": "CONSOLIDATED_GROUP",
        "period_columns": ["2026H1", "2025H1"],
        "cash_reconciliation_inputs": cash_bridge, "reported_ocf": observed_ocf,
        "three_disclosed_operating_adjustments": wc,
        "other_profit_to_cash_adjustments": other, "ocf_change_bridge": changes,
        "H1_revenue": revenue, "H1_cost": cost, "H1_gross_profit": gross,
        "H1_gross_margin_fraction": {k: str(Decimal(gross[k])/Decimal(revenue[k])) for k in revenue},
        "balance_dates": ["2026-06-30", "2025-12-31"],
        "cash_and_equivalents": liquid, "excluded_margin_and_restricted_funds": excluded,
        "monetary_funds": monetary, "increase_split": increase,
        "excluded_share_of_monetary_funds_increase": str(Decimal(increase["excluded_margin_and_restricted"])/Decimal(sum(increase.values()))),
        "checks": checks,
        "limitations": ["No inference of mining profit from the nontrade gross-profit bucket.",
            "The three operating adjustments are cash-flow disclosures, not raw balance-sheet differences or all working capital.",
            "No parent-only or parent-attributable numerator is mixed into group cash reconciliation.",
            "Cash-equivalent classification is not proof of distributable cash, net cash or permanent illiquidity.",
            "Investment-income adjustment in the cash bridge is not assumed to equal the P&L investment-income line.",
            "No report-correction inventory, full input/admission, Pre/Quick, valuation, Odds or investment judgment is certified."]}

if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, sort_keys=True, indent=2))
