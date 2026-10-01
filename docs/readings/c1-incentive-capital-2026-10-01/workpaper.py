"""Explicit Xingsen incentive/capital workpaper; no live source or valuation.

Usage: python workpaper.py evidence.json retained-r2-calculations.py absent-result.json
Use the qualified Kernel package for its canonical identity and create-only writer.
The old researcher script is parsed as literal data, never imported or executed.
"""
from __future__ import annotations

import ast
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import sys

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime.research_commit_only import _json, _read, _write

FACT_HASH = 'f60b78d3f25d045f66ab602abd91853ff2c138aca7d2921b1e4a893f6785dce1'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def original_revenue(raw):
    """Only literal slots in one already pinned researcher source format."""
    tree = ast.parse(raw)
    def named(name):
        return next(n.value for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
    annual = named('ANNUALS')
    fy = next(ast.literal_eval(v.args[0])[0] for k, v in zip(annual.keys, annual.values)
              if ast.literal_eval(k) == '2025')
    def table(name):
        return ast.literal_eval(named(name).generators[0].iter.func.value)['revenue']
    return {'revenue_2025_fy': fy, 'revenue_2025_h1': table('PREV'),
            'revenue_2026_h1': table('H')}


def company_conditions(values, annual, cumulative):
    """Only the three first-grant company revenue tests; not award entitlement."""
    require(len(values) == 3, 'three explicitly supplied years required')
    out = []
    for i, minimum in enumerate(annual):
        standalone = None if values[i] is None else values[i] >= minimum
        total = None if any(x is None for x in values[:i + 1]) else sum(values[:i + 1])
        alternate = (None if total is None else total >= cumulative[i]) if i else False
        out.append(True if standalone is True or alternate is True else
                   False if standalone is False and alternate is False else None)
    return out


def build(e, original):
    body = {k: v for k, v in e.items() if k != 'record_hash'}
    require(e['record_hash'] == canonical_hash(body) == FACT_HASH, 'reviewed facts differ')
    source = e['sources']['R2']
    require(len(original) == source['bytes'] and sha256(original).hexdigest() == source['sha256'],
            'original retained R2 bytes differ')
    require(original_revenue(original) == e['retained_baseline_cny'], 'literal baseline differs')
    b = {k: Decimal(v) for k, v in e['retained_baseline_cny'].items()}
    terms = e['plan_company_revenue_conditions']
    annual = list(map(Decimal, terms['annual_cny']))
    cumulative = [None] + list(map(Decimal, terms['cumulative_alternative_cny'][1:]))
    prior_h2 = b['revenue_2025_fy'] - b['revenue_2025_h1']
    required_h2 = annual[0] - b['revenue_2026_h1']
    arithmetic = {
        'revenue_2025_h2_cny': prior_h2,
        'required_2026_h2_cny_for_first_company_revenue_condition': required_h2,
        'required_h2_change_cny': required_h2 - prior_h2,
        'required_h2_yoy_fraction': required_h2 / prior_h2 - 1,
        'required_h2_vs_2026_h1_fraction': required_h2 / b['revenue_2026_h1'] - 1,
        'first_company_condition_vs_2025_fy_fraction': annual[0] / b['revenue_2025_fy'] - 1,
    }
    cap = e['plan_capital_terms']; expense = cap['hypothetical_expense']
    n, price = Decimal(cap['maximum_shares']), Decimal(cap['purchase_price_cny_per_share'])
    market_assumption = Decimal(expense['assumed_price_cny_per_share'])
    reported_total = Decimal(expense['reported_total_cny_10000']) * 10000
    schedule_total = sum(Decimal(v) * 10000 for v in expense['reported_annual_cny_10000'].values())
    arithmetic.update({
        'prior_treasury_batch_shares_sum': sum(map(Decimal, cap['treasury_prior_batches_shares'])),
        'maximum_plan_consideration_cny_not_actual_receipt': n * price,
        'hypothetical_compensation_cny_at_plan_price_assumption': n * (market_assumption - price),
        'reported_hypothetical_total_cny': reported_total,
        'sum_reported_annual_hypothetical_expense_cny': schedule_total,
        'annual_sum_minus_reported_total_cny': schedule_total - reported_total,
        'reported_total_minus_price_difference_estimate_cny': reported_total - n * (market_assumption - price),
    })
    # Deliberately constructed logical controls, NOT company forecasts/outcomes.
    scenarios = [
        ('annual_equalities', ['80', '100', '120'], [True, True, True]),
        ('second_cumulative_only', ['90', '90', '120'], [True, True, True]),
        ('third_cumulative_only', ['90', '100', '110'], [True, True, True]),
        ('first_failed_not_reinstated', ['79', '101', '120'], [False, True, True]),
        ('second_failed_third_annual_only', ['80', '90', '120'], [True, False, True]),
        ('third_both_fail', ['80', '100', '119'], [True, True, False]),
        ('unknown_not_zero', [None, '90', '110'], [None, None, None]),
        ('known_annual_suffices_with_unknown_prior', [None, '100', '120'], [None, True, True]),
    ]
    controls = []
    for name, yi, expected in scenarios:
        values = [None if x is None else Decimal(x) * 100000000 for x in yi]
        actual = company_conditions(values, annual, cumulative)
        require(actual == expected, 'company revenue control differs: ' + name)
        controls.append({'name': name, 'synthetic_revenue_cny_100000000': yi,
                         'company_revenue_condition_only': actual})
    # Exact fraction cross-checks use independent expressions and integer cents.
    f_h2 = Fraction('8000000000') - Fraction('4037832294.13')
    f_old = Fraction('7194624804.67') - Fraction('3425863435.95')
    checks = [Fraction(required_h2) == f_h2, Fraction(prior_h2) == f_old,
              Fraction(n * price) == Fraction(5694900) * Fraction('19.40'),
              Fraction(n * (market_assumption - price)) == Fraction(5694900) * Fraction('19.93')]
    require(all(checks), 'exact arithmetic cross-check differs')
    f = f_h2 / f_old - 1
    fractional_growth = Decimal(f.numerator) / Decimal(f.denominator)
    require(abs(fractional_growth - arithmetic['required_h2_yoy_fraction']) < Decimal('1e-47'),
            'growth cross-check differs')
    result = {
        'kind': 'C1_INCENTIVE_CONDITIONS_AND_CAPITAL_DIAGNOSTIC_NOT_VALUATION',
        'subject': e['subject'], 'source_record_hash': FACT_HASH,
        'arithmetic': {k: format(v, 'f') for k, v in arithmetic.items()},
        'logical_controls': controls,
        'verification': {'synthetic_controls_passed': len(controls),
                         'exact_fraction_checks_passed': len(checks), 'growth_fraction_check': True,
                         'annual_rounding_residual_preserved': True},
        'limits': ['First-grant company revenue tests only; not personal eligibility or actual vesting.',
                   'Reserved-grant timing is unestablished; no schedule assigned.',
                   'Hypothetical expense and maximum consideration are neither actual expense nor cash receipt.',
                   'The displayed 100 CNY schedule residual is not silently repaired or declared an issuer error.',
                   'No original broker-model qualification, sustainable owner-cash forecast or whole-C acceptance.'],
        'investment_authority': 'NONE', 'human_acceptance': 'NOT_ESTABLISHED',
        'research_committed': False, 'source_calls': 0,
    }
    result['report_hash'] = canonical_hash(result)
    return result


def main(argv):
    require(len(argv) == 4, 'usage: workpaper.py evidence.json r2-calculations.py absent-result.json')
    with localcontext() as ctx:
        ctx.prec = 50
        result = build(_json(_read(Path(argv[1]))), _read(Path(argv[2])))
    _write(Path(argv[3]), (canonical_json(result) + '\n').encode())
    print(result['report_hash'])


if __name__ == '__main__':
    main(sys.argv)
