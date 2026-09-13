"""Offline arithmetic replay, not a Kernel validator or an investment model.

Inputs are explicit extractions from the pinned research records documented in
research-handoff-replay-2026-09-13.md. No network, credentials, repo writes,
probabilities, position sizing, or model calls. Stdlib only.
"""
from decimal import Decimal, localcontext
import json
import unittest

D = Decimal
YI, BN = D('100000000'), D('1000000000')
N = D('582727468')
T, H = D('3'), D('0.10')


def terminal(profit_yi, pe):
    with localcontext() as ctx:
        ctx.prec = 40
        return D(profit_yi) * YI * D(pe) / N


def cagr(end, start):
    if D(end) <= 0 or D(start) <= 0:
        raise ValueError('Positive endpoints required for this bounded replay')
    with localcontext() as ctx:
        ctx.prec = 40
        return (D(end) / D(start)) ** (D(1) / T) - 1


def entry(end):
    return D(end) / ((1 + H) ** T)


def near(actual, expected, tolerance='0.00005'):
    return abs(actual - D(expected)) <= D(tolerance)


class Replay(unittest.TestCase):
    def test_01_yi_is_one_tenth_billion(self):
        self.assertEqual(YI / BN, D('0.1'))

    def test_02_recorded_unit_error_is_rejected(self):
        bad_prose = D('2.3') * BN
        retained_json = D('230000000')
        self.assertEqual(bad_prose / retained_json, D(10))
        self.assertFalse(near(bad_prose, retained_json, '1'))

    def test_03_core_endpoints_match_retained_yuan_inputs(self):
        self.assertEqual(terminal('2.3', 28).quantize(D('.01')), D('11.05'))
        self.assertEqual(terminal('2.9', 35).quantize(D('.01')), D('17.42'))

    def test_04_fourteen_does_not_clear_core_hurdle(self):
        self.assertLess(cagr(terminal('2.9', 35), 14), H)
        self.assertLess(cagr(terminal('2.3', 28), 14), D(0))
        self.assertEqual(D(14) * (1 + H) ** T, D('18.634'))

    def test_05_core_high_entry_bound_is_below_fourteen(self):
        self.assertLess(entry(terminal('2.9', 35)), D(14))

    def test_06_profit_growth_with_multiple_compression(self):
        self.assertGreater(D('2.9'), D('2.3'))
        self.assertLess(terminal('2.9', 28), terminal('2.3', 40))

    def test_07_hengrui_required_terminal(self):
        self.assertEqual(D('42.93') * (1 + H) ** T, D('57.13983'))

    def test_08_hengrui_reference_return_is_not_ten_percent(self):
        self.assertTrue(near(cagr('47.31', '42.93'), '0.0329', '.0001'))
        self.assertLess(cagr('47.31', '42.93'), H)

    def test_09_hengrui_core_boundary(self):
        self.assertTrue(near(entry('52.7'), '39.59429', '.0001'))

    def test_10_hengrui_downside_is_not_just_its_good_end(self):
        lo = D('22.6') / D(38) - 1
        hi = D('32.5') / D(38) - 1
        self.assertTrue(near(lo, '-0.405263', '.000001'))
        self.assertTrue(near(hi, '-0.144737', '.000001'))
        self.assertLess(lo, hi)

    def test_11_annual_loss_is_not_cumulative_loss(self):
        self.assertEqual(D('.85') ** T - 1, D('-.385875'))
        self.assertNotEqual(D('.85') ** T - 1, D('-.15'))

    def test_12_price_only_sensitivity_keeps_worlds_fixed(self):
        world = ('2.3', 28, '2.9', 35, str(N), str(T))
        before = world
        endpoints = (terminal(world[0], world[1]), terminal(world[2], world[3]))
        for value in endpoints:
            self.assertGreater(cagr(value, 14), cagr(value, '19.98'))
        self.assertEqual(world, before)


def main():
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Replay))
    payload = {
        'scope': 'LOCAL_STDLIB_ARITHMETIC_REPLAY_ONLY',
        'kernel_validator_run': False,
        'independent_model_or_new_chat_test': False,
        'calibration_or_investment_outcome_validation': False,
        'tests_run': result.testsRun,
        'failures': len(result.failures),
        'errors': len(result.errors),
        'passed': result.wasSuccessful(),
        'unit_conflict_ratio': '10',
        'electro_optic_core_endpoints': [str(terminal('2.3', 28)), str(terminal('2.9', 35))],
        'electro_optic_cagr_at_14': [str(cagr(terminal('2.3', 28), 14)), str(cagr(terminal('2.9', 35), 14))],
        'electro_optic_core_high_entry_bound': str(entry(terminal('2.9', 35))),
        'hengrui_cagr_4731_at_4293': str(cagr('47.31', '42.93')),
        'hengrui_core_boundary': str(entry('52.7')),
        'hengrui_downside_cumulative_at_38': [str(D('22.6') / D(38) - 1), str(D('32.5') / D(38) - 1)],
        'three_year_cumulative_at_minus_15pct_annual': str(D('.85') ** T - 1),
        'investment_authority': 'NONE',
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
