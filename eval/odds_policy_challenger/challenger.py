from __future__ import annotations

import argparse
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = Path(__file__).with_name("manifest.json")
ZONE_ORDER = ("EXCEPTIONAL_ODDS", "ATTRACTIVE_ODDS", "ACCEPTABLE_ODDS")
ZONE_KEYS = {
    "ACCEPTABLE_ODDS": "acceptable",
    "ATTRACTIVE_ODDS": "attractive",
    "EXCEPTIONAL_ODDS": "exceptional",
}
ZERO = Decimal("0")
ONE = Decimal("1")


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _scenario_payoffs(snapshot: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    scenarios: list[dict[str, Any]] = []
    for scenario in snapshot["scenarios"]:
        payoff = _decimal(scenario["terminal_equity_value_per_share"])
        for flow in scenario.get("expected_cash_flows", []):
            if flow["basis"] != "PER_SHARE":
                raise ValueError("policy challenger supports PER_SHARE cash flows only")
            payoff += _decimal(flow["amount"])
        scenarios.append(
            {
                "name": scenario["name"],
                "probability": _decimal(scenario["probability"]),
                "payoff": payoff,
            }
        )
    probability_sum = sum((item["probability"] for item in scenarios), ZERO)
    if probability_sum != ONE:
        raise ValueError("policy challenger requires an exact probability distribution")
    return tuple(scenarios)


def _current_case(raw: dict[str, Any], *, root: Path) -> dict[str, Any]:
    payload = _load_json(root / raw["path"])
    snapshot = payload["research_snapshot"]
    return {
        "ticker": snapshot["ticker"],
        "company_name": snapshot["company_name"],
        "model_risk_level": snapshot["model_risk_level"],
        "market_date": date.fromisoformat(raw["market_date"]),
        "observed_price": _decimal(raw["observed_price_cny"]),
        "valuation_horizon_date": date.fromisoformat(snapshot["valuation_horizon_date"]),
        "scenarios": _scenario_payoffs(snapshot),
        "source": raw["path"],
        "cohort": "CURRENT_RESEARCH_UNIVERSE",
    }


def _historical_case(raw: dict[str, Any]) -> dict[str, Any]:
    scenarios = tuple(
        {
            "name": item["name"],
            "probability": _decimal(item["probability"]),
            "payoff": _decimal(item["payoff_cny_per_share"]),
        }
        for item in raw["scenarios"]
    )
    if sum((item["probability"] for item in scenarios), ZERO) != ONE:
        raise ValueError("historical policy reference requires exact probability distribution")
    return {
        "ticker": raw["ticker"],
        "company_name": raw["company_name"],
        "model_risk_level": raw["model_risk_level"],
        "market_date": date.fromisoformat(raw["market_date"]),
        "observed_price": _decimal(raw["observed_price_cny"]),
        "valuation_horizon_date": date.fromisoformat(raw["valuation_horizon_date"]),
        "scenarios": scenarios,
        "source": f'{raw["source_repo"]}@{raw["source_commit"]}',
        "cohort": "HISTORICAL_OPERATIONAL_REFERENCE",
    }


def _policy(raw: dict[str, Any], *, name: str, return_mode: str) -> dict[str, Any]:
    return {
        "name": name,
        "return_mode": return_mode,
        "base_returns": {
            "acceptable": _decimal(raw["acceptable_min_expected_return"]),
            "attractive": _decimal(raw["attractive_min_expected_return"]),
            "exceptional": _decimal(raw["exceptional_min_expected_return"]),
        },
        "positive_probabilities": {
            "acceptable": _decimal(raw["acceptable_min_positive_probability"]),
            "attractive": _decimal(raw["attractive_min_positive_probability"]),
            "exceptional": _decimal(raw["exceptional_min_positive_probability"]),
        },
        "risk_addons": {
            "LOW": _decimal(raw["low_model_risk_addon"]),
            "MEDIUM": _decimal(raw["medium_model_risk_addon"]),
            "HIGH": _decimal(raw["high_model_risk_addon"]),
            "VERY_HIGH": _decimal(raw["very_high_model_risk_addon"]),
        },
    }


def _annual_hurdle_to_cumulative(annual_hurdle: Decimal, holding_days: int) -> Decimal:
    with localcontext() as context:
        context.prec = 80
        years = Decimal(holding_days) / Decimal(365)
        return ((ONE + annual_hurdle).ln() * years).exp() - ONE


def _required_return(
    policy: dict[str, Any], *, risk: str, zone: str, holding_days: int
) -> Decimal:
    key = ZONE_KEYS[zone]
    hurdle = policy["base_returns"][key] + policy["risk_addons"][risk]
    if policy["return_mode"] == "CUMULATIVE":
        return hurdle
    if policy["return_mode"] == "ANNUALIZED_TO_CUMULATIVE":
        return _annual_hurdle_to_cumulative(hurdle, holding_days)
    raise ValueError(f'unsupported return mode: {policy["return_mode"]}')


def _weighted_payoff(scenarios: tuple[dict[str, Any], ...]) -> Decimal:
    return sum(
        (item["probability"] * item["payoff"] for item in scenarios),
        ZERO,
    )


def _positive_probability(
    scenarios: tuple[dict[str, Any], ...], *, price: Decimal
) -> Decimal:
    return sum(
        (
            item["probability"]
            for item in scenarios
            if item["payoff"] > price
        ),
        ZERO,
    )


def _probability_boundary(
    scenarios: tuple[dict[str, Any], ...], *, required_probability: Decimal
) -> Decimal:
    # The production calculation counts only strictly positive scenario returns.
    # Therefore this is an exclusive boundary: price must be below the returned payoff
    # when the scenario at that payoff is needed to satisfy the probability gate.
    for payoff in sorted({item["payoff"] for item in scenarios}, reverse=True):
        probability_at_just_below = sum(
            (
                item["probability"]
                for item in scenarios
                if item["payoff"] >= payoff
            ),
            ZERO,
        )
        if probability_at_just_below >= required_probability:
            return payoff
    raise ValueError("positive-return probability gate cannot be satisfied")


def _zone_gate(
    case: dict[str, Any], policy: dict[str, Any], *, zone: str
) -> dict[str, Any]:
    holding_days = (case["valuation_horizon_date"] - case["market_date"]).days
    required_return = _required_return(
        policy,
        risk=case["model_risk_level"],
        zone=zone,
        holding_days=holding_days,
    )
    key = ZONE_KEYS[zone]
    required_probability = policy["positive_probabilities"][key]
    weighted = _weighted_payoff(case["scenarios"])
    return_price_ceiling = weighted / (ONE + required_return)
    probability_boundary = _probability_boundary(
        case["scenarios"], required_probability=required_probability
    )
    if return_price_ceiling < probability_boundary:
        binding_gate = "EXPECTED_RETURN"
    elif probability_boundary < return_price_ceiling:
        binding_gate = "POSITIVE_PROBABILITY_EXCLUSIVE"
    else:
        binding_gate = "BOTH_AT_BOUNDARY"
    return {
        "required_return": required_return,
        "required_positive_probability": required_probability,
        "return_price_ceiling": return_price_ceiling,
        "positive_probability_boundary_exclusive": probability_boundary,
        "effective_price_boundary": min(return_price_ceiling, probability_boundary),
        "binding_gate": binding_gate,
    }


def _classify(case: dict[str, Any], policy: dict[str, Any]) -> str:
    holding_days = (case["valuation_horizon_date"] - case["market_date"]).days
    expected_return = _weighted_payoff(case["scenarios"]) / case["observed_price"] - ONE
    positive_probability = _positive_probability(
        case["scenarios"], price=case["observed_price"]
    )
    for zone in ZONE_ORDER:
        key = ZONE_KEYS[zone]
        if (
            expected_return
            >= _required_return(
                policy,
                risk=case["model_risk_level"],
                zone=zone,
                holding_days=holding_days,
            )
            and positive_probability >= policy["positive_probabilities"][key]
        ):
            return zone
    return "INSUFFICIENT_ODDS"


def evaluate(*, root: Path = ROOT, manifest_path: Path = MANIFEST_PATH) -> dict[str, Any]:
    manifest = _load_json(manifest_path)
    production = _load_json(root / manifest["production_policy_path"])
    legacy = manifest["legacy_policy"]
    policies = (
        _policy(legacy, name="legacy_cumulative", return_mode="CUMULATIVE"),
        _policy(production, name="current_live_cumulative", return_mode="CUMULATIVE"),
        _policy(
            legacy,
            name="legacy_horizon_aware",
            return_mode="ANNUALIZED_TO_CUMULATIVE",
        ),
    )
    cases = [
        *(_current_case(item, root=root) for item in manifest["current_cases"]),
        *(_historical_case(item) for item in manifest["historical_references"]),
    ]

    results: list[dict[str, Any]] = []
    for case in cases:
        holding_days = (case["valuation_horizon_date"] - case["market_date"]).days
        weighted = _weighted_payoff(case["scenarios"])
        expected_return = weighted / case["observed_price"] - ONE
        positive_probability = _positive_probability(
            case["scenarios"], price=case["observed_price"]
        )
        policy_results: dict[str, Any] = {}
        for policy in policies:
            policy_results[policy["name"]] = {
                "participation_zone": _classify(case, policy),
                "gates": {
                    zone: _zone_gate(case, policy, zone=zone)
                    for zone in (
                        "ACCEPTABLE_ODDS",
                        "ATTRACTIVE_ODDS",
                        "EXCEPTIONAL_ODDS",
                    )
                },
            }
        results.append(
            {
                **case,
                "holding_days": holding_days,
                "weighted_payoff": weighted,
                "expected_holding_period_return": expected_return,
                "positive_return_probability": positive_probability,
                "policy_results": policy_results,
            }
        )
    return {
        "experiment_id": manifest["experiment_id"],
        "production_change": manifest["production_change"],
        "authority": manifest["authority"],
        "cases": results,
    }


def _q2(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))


def _pct(value: Decimal) -> str:
    return f'{(value * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_EVEN)}%'


def render_markdown(result: dict[str, Any]) -> str:
    current = [item for item in result["cases"] if item["cohort"] == "CURRENT_RESEARCH_UNIVERSE"]
    historical = [
        item for item in result["cases"] if item["cohort"] == "HISTORICAL_OPERATIONAL_REFERENCE"
    ]
    lines = [
        "# Odds Policy Challenger v0",
        "",
        "Experiment only. Production policy, Human wake semantics, Recommendation, sizing, execution and investment authority are unchanged.",
        "",
        "## Current close classifications",
        "",
        "| Case | Expected return | Positive probability | Legacy cumulative | Current live | Legacy horizon-aware |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    for item in current:
        p = item["policy_results"]
        lines.append(
            "| "
            f'{item["company_name"]} {item["ticker"]} | '
            f'{_pct(item["expected_holding_period_return"])} | '
            f'{_pct(item["positive_return_probability"])} | '
            f'{p["legacy_cumulative"]["participation_zone"]} | '
            f'{p["current_live_cumulative"]["participation_zone"]} | '
            f'{p["legacy_horizon_aware"]["participation_zone"]} |'
        )

    lines.extend(
        [
            "",
            "## ACCEPTABLE_ODDS price boundary",
            "",
            "The probability boundary is exclusive when it binds because zero-return scenarios do not count as positive.",
            "",
            "| Case | Holding days | Legacy cumulative | Current live | Legacy horizon-aware |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in current:
        p = item["policy_results"]
        lines.append(
            "| "
            f'{item["company_name"]} {item["ticker"]} | {item["holding_days"]} | '
            f'¥{_q2(p["legacy_cumulative"]["gates"]["ACCEPTABLE_ODDS"]["effective_price_boundary"])} | '
            f'¥{_q2(p["current_live_cumulative"]["gates"]["ACCEPTABLE_ODDS"]["effective_price_boundary"])} | '
            f'¥{_q2(p["legacy_horizon_aware"]["gates"]["ACCEPTABLE_ODDS"]["effective_price_boundary"])} |'
        )

    lines.extend(["", "## Historical operational reference", ""])
    for item in historical:
        p = item["policy_results"]
        lines.extend(
            [
                f'### {item["company_name"]} {item["ticker"]}',
                "",
                f'- Holding period: {item["holding_days"]} days',
                f'- Weighted payoff: ¥{_q2(item["weighted_payoff"])}',
                f'- Historical observed price: ¥{_q2(item["observed_price"])}',
                f'- Legacy cumulative ACCEPTABLE boundary: ¥{_q2(p["legacy_cumulative"]["gates"]["ACCEPTABLE_ODDS"]["effective_price_boundary"])}',
                f'- Current live ACCEPTABLE boundary: ¥{_q2(p["current_live_cumulative"]["gates"]["ACCEPTABLE_ODDS"]["effective_price_boundary"])}',
                f'- Legacy horizon-aware ACCEPTABLE boundary: ¥{_q2(p["legacy_horizon_aware"]["gates"]["ACCEPTABLE_ODDS"]["effective_price_boundary"])}',
                "",
            ]
        )

    lines.extend(
        [
            "## Readout",
            "",
            "- A straight legacy rollback is materially noisier in the current five-name universe: it promotes Moutai from quiet to ATTRACTIVE while CATL and CMB also become ATTRACTIVE.",
            "- Horizon normalization is directionally cleaner but does not recover the Dongshan historical first-participation boundary: at 494 days it becomes stricter than legacy cumulative.",
            "- GigaDevice v2 remains below ACCEPTABLE at the 2026-09-02 close under all three candidates; the Research correction narrows the gap without manufacturing a buy signal.",
            "- The evidence does not support replacing production policy with either challenger unchanged.",
            "",
            "Investment Authority = NONE",
            "",
        ]
    )
    return "\n".join(lines)


def _json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = evaluate()
    if args.json:
        print(json.dumps(_json_ready(result), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
