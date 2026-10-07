"""Two fixed, retained-input D1 arithmetic controls; offline and create-only.

These are analyst-transcribed inputs. No numerical check authenticates source
text, a company filing, forecast skill, issuer timing or Human acceptance.
"""
from __future__ import annotations
import argparse
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'duplicate key')
        value[key] = item
    return value


def number(value):
    require(type(value) is str, 'decimal string required')
    result = Decimal(value)
    require(result.is_finite(), 'nonfinite input')
    return result


def calculate(raw):
    require(type(raw) is bytes and 0 < len(raw) < 65536, 'bounded input bytes')
    inp = json.loads(raw, object_pairs_hook=unique,
                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    require(inp['kind'] == 'D1_BOUNDED_MECHANISM_CONTROLS_NOT_FULL_OR_PIT_PERFORMANCE', 'input purpose')
    require(inp['limits']['investment_authority'] == 'NONE', 'no investment authority')
    a, b = inp['beidahuang'], inp['rigol']
    require(a['symbol'] == '600598.SH' and a['amount_unit'] == 'CNY', 'tax case identity/unit')
    require(b['symbol'] == '688337.SH', 'share case identity')
    with localcontext() as c:
        c.prec = 40
        money = lambda x: format(x.quantize(Decimal('.01')), 'f')
        ratio = lambda x: format(x.quantize(Decimal('.000000000001')), 'f')
        current = number(a['reported_current_profit']); prior = number(a['reported_prior_profit'])
        settlement = number(a['historical_settlement_company_described_net_impact'])
        require(prior > 0 and settlement > 0, 'positive comparison base/settlement')
        adjusted = current + settlement
        old = number(b['old_declared_total_shares']); new = number(b['new_issued_h_shares'])
        require(old > 0 and new > 0 and old == old.to_integral_value()
                and new == new.to_integral_value(), 'positive integer share counts')
        total = old + new
        rows = []
        for value in b['hypothetical_total_profit_growth']:
            g = number(value); require(g > -1, 'invalid hypothetical growth')
            change = (1 + g) * old / total - 1
            rows.append({'hypothetical_total_profit_growth': str(g),
                         'constant_count_per_share_change': ratio(change)})
        return {
            'kind': inp['kind'], 'input_sha256': hashlib.sha256(raw).hexdigest(),
            'analysis_frozen_at': inp['analysis_frozen_at'],
            'beidahuang': {
                'analyst_h1_excluding_retained_settlement': money(adjusted),
                'difference_from_prior_h1': money(adjusted-prior),
                'fraction_change_from_prior_h1': ratio(adjusted/prior-1),
                'meaning': 'INHERITED_PROFIT_BRIDGE_NOT_COMPANY_ADJUSTED_PROFIT_OR_FUTURE_TAX_FORECAST',
                'next_quarter_profit_prediction': None, 'new_short_horizon_payoff': None},
            'rigol': {
                'declared_static_count_after_issuance': str(total),
                'profit_growth_for_unchanged_static_per_share_value': ratio(new/old),
                'unchanged_profit_static_per_share_change': ratio(old/total-1),
                'hypothetical_controls': rows,
                'meaning': b['calculation_scope'],
                'reported_basic_eps_restatement': None,
                'actual_weighted_diluted_share_count': None,
                'net_issuance_cash': None,
                'new_short_horizon_payoff': None},
            'qualified_historical_pit_case_count': None,
            'pooled_score': None, 'opportunity_probability': None,
            'investment_authority': 'NONE'}


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs', type=Path, required=True)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', type=Path)
    mode.add_argument('--output', type=Path)
    a = p.parse_args()
    require(a.inputs.is_file() and not a.inputs.is_symlink(), 'regular inputs required')
    raw = encode(calculate(a.inputs.read_bytes()))
    if a.check:
        require(a.check.is_file() and not a.check.is_symlink(), 'regular result required')
        require(a.check.read_bytes() == raw, 'retained result differs')
        print('RETAINED_D1_CONTROLS_MATCH')
    else:
        with a.output.open('xb') as out:
            out.write(raw)
        print('CREATED', a.output)


if __name__ == '__main__':
    main()
