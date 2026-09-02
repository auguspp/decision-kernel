from __future__ import annotations

import json
import subprocess
import sys
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path


SCRIPT = Path("eval/odds_policy_challenger/challenger.py")


def _run() -> dict:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _case(result: dict, ticker: str) -> dict:
    return next(item for item in result["cases"] if item["ticker"] == ticker)


def _q2(value: str) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def test_policy_challenger_is_non_production_and_uses_current_live_policy() -> None:
    result = _run()

    assert result["production_change"] is False
    assert result["authority"] == "NONE"

    current = json.loads(
        Path("src/decision_kernel/policy_data/live_odds_v0_1.json").read_text(
            encoding="utf-8"
        )
    )
    catl = _case(result, "300750")
    gate = catl["policy_results"]["current_live_cumulative"]["gates"][
        "ACCEPTABLE_ODDS"
    ]
    expected = Decimal(current["acceptable_min_expected_return"]) + Decimal(
        current["very_high_model_risk_addon"]
    )
    assert Decimal(gate["required_return"]) == expected == Decimal("0.32")


def test_current_close_noise_delta_is_not_a_simple_legacy_rollback() -> None:
    result = _run()
    expected = {
        "300750": {
            "legacy_cumulative": "ATTRACTIVE_ODDS",
            "current_live_cumulative": "ACCEPTABLE_ODDS",
            "legacy_horizon_aware": "ATTRACTIVE_ODDS",
        },
        "600036": {
            "legacy_cumulative": "ATTRACTIVE_ODDS",
            "current_live_cumulative": "ACCEPTABLE_ODDS",
            "legacy_horizon_aware": "ATTRACTIVE_ODDS",
        },
        "600519": {
            "legacy_cumulative": "ATTRACTIVE_ODDS",
            "current_live_cumulative": "INSUFFICIENT_ODDS",
            "legacy_horizon_aware": "ATTRACTIVE_ODDS",
        },
        "601088": {
            "legacy_cumulative": "INSUFFICIENT_ODDS",
            "current_live_cumulative": "INSUFFICIENT_ODDS",
            "legacy_horizon_aware": "INSUFFICIENT_ODDS",
        },
        "603986": {
            "legacy_cumulative": "INSUFFICIENT_ODDS",
            "current_live_cumulative": "INSUFFICIENT_ODDS",
            "legacy_horizon_aware": "INSUFFICIENT_ODDS",
        },
    }

    for ticker, policy_zones in expected.items():
        case = _case(result, ticker)
        assert {
            name: policy["participation_zone"]
            for name, policy in case["policy_results"].items()
        } == policy_zones


def test_current_acceptable_price_boundaries_are_reproducible() -> None:
    result = _run()
    expected = {
        "300750": ("393.22", "351.52", "399.87"),
        "600036": ("48.43", "43.86", "48.49"),
        "600519": ("1426.09", "1291.34", "1432.11"),
        "601088": ("39.07", "35.37", "39.11"),
        "603986": ("369.93", "330.70", "369.93"),
    }

    for ticker, values in expected.items():
        case = _case(result, ticker)
        policies = case["policy_results"]
        actual = tuple(
            _q2(
                policies[name]["gates"]["ACCEPTABLE_ODDS"][
                    "effective_price_boundary"
                ]
            )
            for name in (
                "legacy_cumulative",
                "current_live_cumulative",
                "legacy_horizon_aware",
            )
        )
        assert actual == tuple(Decimal(value) for value in values)


def test_dongshan_reference_separates_calibration_from_horizon_normalization() -> None:
    result = _run()
    dongshan = _case(result, "002384")
    policies = dongshan["policy_results"]

    assert dongshan["holding_days"] == 494
    assert Decimal(dongshan["weighted_payoff"]) == Decimal("194.85")
    assert _q2(
        policies["legacy_cumulative"]["gates"]["ACCEPTABLE_ODDS"][
            "effective_price_boundary"
        ]
    ) == Decimal("169.43")
    assert _q2(
        policies["current_live_cumulative"]["gates"]["ACCEPTABLE_ODDS"][
            "effective_price_boundary"
        ]
    ) == Decimal("153.43")
    assert _q2(
        policies["legacy_horizon_aware"]["gates"]["ACCEPTABLE_ODDS"][
            "effective_price_boundary"
        ]
    ) == Decimal("161.27")

    assert Decimal(
        policies["legacy_horizon_aware"]["gates"]["ACCEPTABLE_ODDS"][
            "required_return"
        ]
    ) > Decimal(
        policies["legacy_cumulative"]["gates"]["ACCEPTABLE_ODDS"][
            "required_return"
        ]
    )


def test_gigadevice_v2_research_correction_does_not_manufacture_participation() -> None:
    result = _run()
    gigadevice = _case(result, "603986")

    assert Decimal(gigadevice["expected_holding_period_return"]) > Decimal("0.12")
    assert Decimal(gigadevice["positive_return_probability"]) == Decimal("0.70")
    assert all(
        policy["participation_zone"] == "INSUFFICIENT_ODDS"
        for policy in gigadevice["policy_results"].values()
    )
