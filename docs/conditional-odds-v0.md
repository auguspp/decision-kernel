# Probability-free Conditional Worlds v0

Scope: #321-B. Reuse Decision: **THIN_ADAPTER**.

This contract exists because real Decision Kernel usage often has a frozen business
Belief and explicit conditional operating/value worlds without any defensible
Bear/Base/Bull probability calibration. `UNKNOWN` is valid. Do not invent a
probability distribution merely to make Odds executable.

## What this adds

`decision_kernel.conditional_odds` adds two first-class typed objects:

1. `FrozenConditionalWorldSet`
   - binds one set of declared conditional worlds to the **full hash** of one exact
     `COMMITTED ResearchSnapshot`;
   - carries an explicit decision-use horizon;
   - each world states operating conditions, valuation expression and provenance
     Evidence already linked to that Research;
   - has **no `probability` field** and cannot accept one.

2. `FrozenConditionalProvisionalOdds`
   - combines those exact worlds with #405 `HumanPriceContext`;
   - calculates each world's dated per-share payoff and undiscounted conditional
     return using the existing Phase 2A decimal context, normalization and payoff
     convention;
   - serializes no probability-weighted aggregate, participation zone, calibrated
     probability or favorable/unfavorable recommendation.

This is not a replacement for `Scenario`, `ObservedMarket`,
`OddsResearchArtifact`, the canonical Odds policy or the Funnel.

## Canonical contract stays strict

Existing canonical `ResearchSnapshot.scenarios` remain the numerical object used
by canonical Odds and still require a complete probability distribution.
`build_odds_research()` and `calculate_research_economics()` are unchanged.

A probability-free world set is an **analytical overlay bound to frozen
Research**, not a mutation of Research into fake scenarios. A later qualified
market observation does not manufacture missing probabilities and does not
silently promote this result to canonical numerical Odds.

## Research and provenance binding

Create the world set only from one already validated, committed Research snapshot:

```python
worlds = build_conditional_world_set(
    research_snapshot=frozen_research,
    worlds=(downside, middle, upside),
    valuation_horizon_date=decision_horizon,
    world_set_id=...,
    created_at=...,
)
```

The builder verifies:

- exact Research snapshot id, information-bundle hash and full canonical hash;
- world creation cannot precede Research commit;
- any world `valuation_basis_id`, when supplied, belongs to that Research;
- every declared world/distribution provenance artifact is already linked to the
  frozen Research;
- an existing frozen Research horizon cannot be silently replaced.

For schema-v2 Research-only snapshots with no numerical `Scenario` distribution,
the decision-use conditional horizon may be declared here without rewriting the
Research snapshot.

## Human price and clock semantics

Analysis uses #405 `HumanPriceContext` only:

```python
result = build_conditional_provisional_odds(
    research_snapshot=frozen_research,
    conditional_worlds=worlds,
    price_context=human_context_price,
    artifact_id=...,
    created_at=...,
)
```

The result stays:

```text
Odds = PROVISIONAL_CONDITIONAL_ORDINAL
CARDINAL PROBABILITY = NOT_ESTABLISHED
probability_input = ABSENT_BY_DESIGN
weighted_aggregate = NOT_COMPUTED
market_qualification = NOT_ESTABLISHED
canonical_odds = NOT_ESTABLISHED
investment_authority = NONE
```

Two price-clock states are explicit:

- `AT_OR_AFTER_RESEARCH_CUTOFF_CONTEXT_ONLY`
- `PRE_RESEARCH_RETROSPECTIVE_REFERENCE_NOT_PIT`

The second state is allowed for retrospective reverse-underwriting such as asking
what a later frozen Research would have implied at an earlier reference price.
It is explicitly **not PIT analysis**, not a qualified historical market state
and not evidence that the later Research was available then.

A Human price still cannot be passed as `ObservedMarket`.

## Arithmetic and horizon

This adapter uses the same:

- `CALCULATION_CONTEXT`
- decimal normalization
- dated distribution result shape
- `UNDISCOUNTED_NOMINAL_CUMULATIVE_PAYOFF_V1`

as the existing calculator. Tests project existing probability-bearing scenarios
through the probability-free path and require identical per-world arithmetic
after removing the probability field.

The conditional horizon is not the canonical live policy. A three-year
decision-use horizon can therefore be represented for provisional conditional
analysis when it is consistent with frozen Research. This does **not** widen the
canonical 180–730 day policy or make a three-year result canonical.

No annualized return is manufactured in v0. A world result is the declared
terminal equity value plus dated per-share distributions, divided by the
reference price, minus one.

## Fail closed

The adapter returns `NO_CALCULATION / ORDINAL_NOT_ESTABLISHED` when the declared
horizon or a distribution is already behind the reference-price date. It never
drops the passed cash flow to make the result run.

The deterministic verifier rebuilds the world set and result against the exact
trusted Research. Rehashed edits to saved returns fail verification.

## What is still separate

This slice does **not**:

- migrate old Hengrui/Beidahuang Markdown or ordinal records into new typed data;
- establish a new company Research version;
- recover the damaged Hengrui Round-2 ZIP;
- qualify a market source;
- calibrate scenario probabilities;
- register a Watch or Action;
- establish Human acceptance or Investment Authority;
- claim a real-company remote round-trip before one is actually run.

Existing #406 result retention can be extended to this result type only after the
core contract passes its own main/publication gates. Do not change old records
merely to create an acceptance sample.
