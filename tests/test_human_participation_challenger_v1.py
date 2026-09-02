import json
from decimal import Decimal
from pathlib import Path


GIGA_PATH = Path("research_cases/603986-gigadevice-deep-research-v2.json")
SANHUA_PATH = Path("research_cases/002050-sanhua-deep-research-v1.json")
POLICY_PATH = Path("src/decision_kernel/policy_data/live_odds_v0_1.json")

DONGSHAN = (
    (Decimal("82"), Decimal("0.15")),
    (Decimal("138"), Decimal("0.25")),
    (Decimal("207"), Decimal("0.35")),
    (Decimal("288"), Decimal("0.20")),
    (Decimal("360"), Decimal("0.05")),
)


def _load_distribution(path: Path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    snapshot = raw["research_snapshot"]
    return tuple(
        (
            Decimal(item["terminal_equity_value_per_share"]),
            Decimal(item["probability"]),
        )
        for item in snapshot["scenarios"]
    ), snapshot["model_risk_level"]


def _weighted(distribution):
    return sum((value * probability for value, probability in distribution), Decimal("0"))


def _metrics(distribution, price: Decimal):
    weighted = _weighted(distribution)
    positive_probability = sum(
        (probability for value, probability in distribution if value > price),
        Decimal("0"),
    )
    positive_contribution = sum(
        (
            probability * max(value / price - Decimal("1"), Decimal("0"))
            for value, probability in distribution
        ),
        Decimal("0"),
    )
    negative_contribution = sum(
        (
            probability * max(Decimal("1") - value / price, Decimal("0"))
            for value, probability in distribution
        ),
        Decimal("0"),
    )
    return {
        "expected_return": weighted / price - Decimal("1"),
        "positive_probability": positive_probability,
        "asymmetry": positive_contribution / negative_contribution,
    }


def _acceptable_boundary(weighted: Decimal, risk: str) -> Decimal:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    addon = Decimal(policy[f"{risk.lower()}_model_risk_addon"])
    hurdle = Decimal(policy["acceptable_min_expected_return"]) + addon
    return weighted / (Decimal("1") + hurdle)


def test_three_case_challenger_reproduces_frozen_weighted_values() -> None:
    giga, giga_risk = _load_distribution(GIGA_PATH)
    sanhua, sanhua_risk = _load_distribution(SANHUA_PATH)

    assert _weighted(DONGSHAN) == Decimal("194.85")
    assert _weighted(giga) == Decimal("436.5220")
    assert _weighted(sanhua) == Decimal("37.5435")
    assert giga_risk == "VERY_HIGH"
    assert sanhua_risk == "HIGH"


def test_two_to_one_asymmetry_cannot_be_a_universal_first_entry_gate() -> None:
    dongshan_first = _metrics(DONGSHAN, Decimal("167.5"))
    giga_no_buy = _metrics(_load_distribution(GIGA_PATH)[0], Decimal("388.86"))
    giga_first = _metrics(_load_distribution(GIGA_PATH)[0], Decimal("322"))
    sanhua_first = _metrics(_load_distribution(SANHUA_PATH)[0], Decimal("31.25"))

    assert dongshan_first["asymmetry"] > Decimal("2")
    assert giga_no_buy["asymmetry"] > Decimal("2")
    assert giga_no_buy["asymmetry"] > dongshan_first["asymmetry"]
    assert giga_first["asymmetry"] > Decimal("9")
    assert sanhua_first["asymmetry"] > Decimal("10")

    # Human gold contradicts any universal 2:1 gate: 388.86 Giga was rejected,
    # while 167.5 Dongshan is inside an approved first-participation band.
    assert giga_no_buy["positive_probability"] == Decimal("0.70")
    assert dongshan_first["positive_probability"] == Decimal("0.60")


def test_human_first_participation_return_hurdles_are_not_universal() -> None:
    giga = _load_distribution(GIGA_PATH)[0]
    sanhua = _load_distribution(SANHUA_PATH)[0]

    dongshan_first = _metrics(DONGSHAN, Decimal("167.5"))["expected_return"]
    giga_first = _metrics(giga, Decimal("322"))["expected_return"]
    sanhua_first = _metrics(sanhua, Decimal("31.25"))["expected_return"]

    assert Decimal("0.16") < dongshan_first < Decimal("0.17")
    assert Decimal("0.35") < giga_first < Decimal("0.36")
    assert Decimal("0.20") < sanhua_first < Decimal("0.21")


def test_current_acceptable_floor_maps_to_different_human_semantics() -> None:
    giga, _ = _load_distribution(GIGA_PATH)
    sanhua, _ = _load_distribution(SANHUA_PATH)

    dongshan_boundary = _acceptable_boundary(_weighted(DONGSHAN), "HIGH")
    giga_boundary = _acceptable_boundary(_weighted(giga), "VERY_HIGH")
    sanhua_boundary = _acceptable_boundary(_weighted(sanhua), "HIGH")

    # Dongshan current ACCEPTABLE falls in Human High-Odds 150–160, not first 165–170.
    assert Decimal("153") < dongshan_boundary < Decimal("154")

    # Sanhua current ACCEPTABLE falls in Human High-Odds 28–30, not first 30.5–32.
    assert Decimal("29.5") < sanhua_boundary < Decimal("29.6")

    # Giga current ACCEPTABLE is near, but looser than, Human first consideration ~322.
    assert Decimal("330") < giga_boundary < Decimal("331")
    assert giga_boundary > Decimal("322")

    # Positive-probability floor is satisfied at each return boundary, so the return
    # hurdle is the binding current ACCEPTABLE constraint in these examples.
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    required_positive = Decimal(policy["acceptable_min_positive_probability"])
    assert _metrics(DONGSHAN, dongshan_boundary)["positive_probability"] >= required_positive
    assert _metrics(giga, giga_boundary)["positive_probability"] >= required_positive
    assert _metrics(sanhua, sanhua_boundary)["positive_probability"] >= required_positive
