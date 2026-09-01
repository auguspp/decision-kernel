from __future__ import annotations

import json
from importlib.resources import files

from .odds import OddsResearchPolicy
from .primitives import DomainValidationError


LIVE_ODDS_V0_1_RESOURCE = "policy_data/live_odds_v0_1.json"


def load_live_odds_v0_1() -> OddsResearchPolicy:
    """Load the exact Decision OS Live Odds v0.1 policy preserved as package data."""

    try:
        text = files("decision_kernel").joinpath(LIVE_ODDS_V0_1_RESOURCE).read_text(
            encoding="utf-8"
        )
        payload = json.loads(text)
    except (FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        raise DomainValidationError(
            "frozen Live Odds v0.1 policy is unavailable or invalid"
        ) from exc
    return OddsResearchPolicy.model_validate(payload)
