"""Conditional H2 burden on retained inputs; not a forecast, revision or Odds.

Units: RMB 100 million (亿元), profit attributable to parent shareholders.
Inputs: P2=649f2820b3139cef9c1dd6fa08f2fe6ee079f187,
  docs/readings/002436-xingsen-full-2026-09-24-r2/calculations.json,
  quarter_revenue_parent_ni_yi and cash_yi.
Forecasts: P1=a4cb0c0b44970ef3b96f0f570107093e7a1eb7ae,
  docs/readings/002436-xingsen-full-2026-09-24/report.md, section 7.
These are rounded broker forecasts retained in prior research, not our estimates.
No network, prices, credentials, third-party dependencies or remote writes.
"""
from decimal import Decimal, localcontext
import json
from pathlib import Path


def calculate() -> dict:
    with localcontext() as ctx:
        ctx.prec = 32
        q1 = Decimal('0.1874469413')
        q2 = Decimal('0.9176304061')
        h1 = q1 + q2
        assert h1 == Decimal('1.1050773474')
        cfo = Decimal('0.0284092652')
        capex = Decimal('7.2603048496')
        assert cfo - capex == Decimal('-7.2318955844')
        rows = []
        for broker, year_profit in [('SPDB International', '3.2'), ('Kaiyuan', '5.16')]:
            forecast = Decimal(year_profit)
            h2 = forecast - h1
            average = h2 / 2
            assert h1 + h2 == forecast and average * 2 == h2
            rows.append({'broker': broker, 'retained_rounded_2026_forecast_yi': str(forecast),
                         'required_h2_parent_profit_yi': str(h2),
                         'required_h2_average_quarter_yi': str(average),
                         'average_relative_to_actual_q2': str(average / q2)})
        return {'qualification': 'CONDITIONAL_ARITHMETIC_ON_RETAINED_INPUTS_NOT_FORECAST_OR_ODDS',
                'security': '002436.SZ', 'currency': 'CNY', 'unit': '100000000_CNY',
                'q1_parent_profit_yi': str(q1), 'q2_parent_profit_yi': str(q2),
                'h1_parent_profit_yi': str(h1), 'rows': rows,
                'h1_cfo_minus_cash_capex_yi': str(cfo - capex),
                'limits': ['Rounded broker targets do not gain precision from subtraction.',
                           'Average quarter is not a quarterly trajectory or seasonal forecast.',
                           'No EPS year/currency/share-basis equivalence or vintage revision is validated.',
                           'CFO minus cash capex is not parent FCFE.',
                           'Inputs were recovered from prior research, not freshly audited issuer statements.'],
                'investment_authority': 'NONE', 'odds_recomputed': False}


if __name__ == '__main__':
    output = Path(__file__).with_name('calculations.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(calculate(), stream, ensure_ascii=False, indent=2)
        stream.write('\n')
