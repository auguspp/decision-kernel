from decimal import Decimal as D, getcontext
import json
from pathlib import Path

getcontext().prec = 50
SHARES = D("1699673563")
PRICE = D("40.93")
HURDLE = D("0.10")
YEARS = 3
FACTOR = (D("1") + HURDLE) ** YEARS
YI = D("100000000")

def q(x, digits):
    return str(x.quantize(D(digits)))

def main():
    requirements = []
    for pe in (D("30"), D("35"), D("40")):
        profit_yi = SHARES * PRICE * FACTOR / pe / YI
        requirements.append({
            "terminal_pe_assumption": str(pe),
            "required_terminal_parent_profit_yi": q(profit_yi, "0.0001"),
        })

    cases = []
    for case_id, profit_yi, pe in (
        ("PUBLIC_HIGH_2028_PROFIT_HIGH_MULTIPLE", D("20.21"), D("40")),
        ("PUBLIC_HIGH_2028_PROFIT_MID_MULTIPLE", D("20.21"), D("30")),
        ("PUBLIC_LOW_2028_PROFIT_HIGH_MULTIPLE", D("11.4"), D("40")),
    ):
        terminal_price = profit_yi * YI * pe / SHARES
        cumulative = terminal_price / PRICE - D("1")
        cagr = (terminal_price / PRICE) ** (D("1") / D("3")) - D("1")
        max_entry = terminal_price / FACTOR
        cases.append({
            "id": case_id,
            "terminal_parent_profit_yi": str(profit_yi),
            "terminal_pe_assumption": str(pe),
            "terminal_price": q(terminal_price, "0.0001"),
            "cumulative_return_from_reference_price": q(cumulative, "0.000001"),
            "annualized_return_3y": q(cagr, "0.000001"),
            "max_starting_price_for_10pct_cagr": q(max_entry, "0.0001"),
        })

    expected = json.loads(Path(__file__).with_name("calculations.json").read_text(encoding="utf-8"))
    assert requirements == expected["market_implied_requirements"]
    assert cases == expected["conditional_cases"]
    print(json.dumps({"market_implied_requirements": requirements, "conditional_cases": cases}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
