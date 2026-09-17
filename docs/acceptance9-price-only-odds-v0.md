# #321 Acceptance 9 — Price-only Odds recompute contract v0

Status: **BOUNDED ACCEPTANCE CONTRACT / REUSE / NO NEW RUNTIME**  
Scope: #321 Acceptance 9 only. Investment Authority = `NONE`.

## 1. Why this needs a split

The original shorthand was:

```text
same frozen Research + qualified price
→ Canonical Odds
```

That statement is only valid when the frozen Research is already **numerical / decision-ready**. Current Kernel contracts deliberately allow another legitimate state: schema-v2 Research-only with no cardinal scenario distribution. A qualified price cannot manufacture missing Belief.

Therefore Acceptance 9 has two different cases:

### A. Numerical committed Research

If one exact `COMMITTED ResearchSnapshot` already contains a complete probability-bearing scenario distribution, a new `ObservedMarket` may be consumed by the existing canonical Odds engine. Research is not rerun or rewritten.

```text
same COMMITTED ResearchSnapshot
+ new ObservedMarket
→ new OddsResearchArtifact
```

Required invariants:

- exact ResearchSnapshot id/hash/bytes remain unchanged;
- only Market/Odds clocks and price-sensitive results change;
- `calculate_research_economics()` already requires `ResearchStatus.COMMITTED`;
- no ResearchCommit or Research executor is needed for each price update;
- no Investment Authority is gained.

This is existing behavior in `build_odds_research()` / `run_decision_spine()`. No new adapter is justified.

### B. Probability-free committed Research

If frozen Research intentionally has no scenario probability distribution, a qualified market observation can improve **price authority**, but cannot create cardinal probability.

The existing `docs/conditional-odds-v0.md` contract remains authoritative:

```text
qualified Market
+ probability-free frozen Research
≠ canonical numerical Odds
```

The valid outcomes are:

- price-qualified conditional / reverse-underwriting analysis where an approved consumer exists; and/or
- canonical numerical Odds = `NOT_ESTABLISHED`.

A new Research version may later establish a defensible distribution, but price alone cannot do so.

## 2. Reuse evidence

No new runtime is added because the required positive mechanics already exist:

- `calculation._validate_calculation_inputs()` requires a `COMMITTED ResearchSnapshot` and a complete scenario distribution;
- `build_odds_research()` consumes one frozen ResearchSnapshot and one ObservedMarket;
- `run_decision_spine()` composes the same frozen Research into Odds/Rehearsal/Human Surface;
- the probability-free conditional contract explicitly forbids silent promotion to canonical Odds.

Reuse Decision: **REUSE**.

## 3. Acceptance fixtures

### Positive canonical mechanics fixture

`dogfood/600519-moutai.json` is reused only as an existing **numerical mechanics fixture**. It is committed once, then two otherwise-identical synthetic `ObservedMarket` objects differ only in price. The test requires:

- identical committed Research bytes/hash before and after both calculations;
- both Odds artifacts bind the same Research id/information bundle;
- expected return changes in the correct direction as price changes;
- no second Research execution or Research mutation occurs.

This does **not** claim the old Moutai scenario probabilities are a current investment judgment or that a current production Moutai price is qualified for decision use.

### Real qualified-market negative fixture

The fixed reading `36a466aab671b609869fd0af6103d8771e28ad34` retained a HiThink latest-completed A-share close for Hengrui:

```text
600276.SH
2026-09-17 15:00 +08:00
CNY 43.23
price_contract = QUALIFIED_LATEST_COMPLETED_A_SHARE_RAW_CLOSE_VIA_EXISTING_HITHINK_RUNTIME
```

The exact source identity is retained in `docs/dogfood/321-acceptance9-qualified-market-2026-09-17.json`.

That real qualified price is applied only to the earlier committed probability-free Hengrui Research snapshot from #413, whose cutoff predates the market observation. The canonical numerical Odds engine must still fail closed with an incomplete-scenario-distribution error and must not modify Research.

This is a deliberate negative acceptance: **qualified price improves Odds input authority, not Belief completeness**.

## 4. Current product qualification remains separate

Current Odds Watch may label a case `PRICE_ONLY_RECOMPUTE_ELIGIBLE...` or `HUMAN_PRICE_CONDITION_REVIEW_NOT_NUMERICAL_ODDS_RECOMPUTE`. Those are current product/read-model qualifications and must not be overridden merely because a historical numerical Research package exists.

In particular, stale/historical numerical distributions are not reactivated to create a convenient Acceptance 9 sample.

## 5. What this slice establishes

If its full regression suite passes:

- **A9 core canonical mechanics = ESTABLISHED** for already-numerical committed Research;
- **probability-free qualified-price negative rule = ESTABLISHED**;
- **real current-case canonical numerical recompute = NOT ESTABLISHED unless a currently qualified numerical Research case exists**.

No provider, scheduler, workflow, Research engine, Odds engine, persistence layer, Watch, Action or authority change is introduced.
