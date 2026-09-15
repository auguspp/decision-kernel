# Sector Radar Historical Outcome Study v0

Status: **SHADOW EVALUATION / NO INVESTMENT AUTHORITY**

This is the first bounded implementation of #375-B. It asks whether the existing Sector Radar false-to-true discovery policy shows useful forward market-path behavior relative to one deliberately simple baseline. It is not a portfolio backtester and does not change Research, Odds, Action, or Human authority.

## Frozen ex-ante contract

The study reuses the existing production formula and state-entry policy unchanged:

- formula: `sector-rs-5-20-60-persistence126-v0`;
- state-entry policy: `sector-shadow-state-entry-hierarchy-v0`;
- Radar cohort: exact existing false-to-true persistent / acceleration entries;
- baseline: `20d excess > 0` and `20d cross-sectional rating >= 90`, with no persistence or acceleration condition;
- forward horizons: 5, 20, and 60 completed sessions;
- outcomes: forward sector return, benchmark return, excess return, close-path MFE/MAE, and excess-path MFE/MAE;
- outcome-sign false-positive / false-negative counts are descriptive proxies only, not investment-error labels.

These choices are versioned before real outcome inspection. v0 has no threshold input and no same-sample parameter tuning surface.

## Point-in-time discipline

For each historical signal session `T`, the adapter physically truncates every sector and benchmark price series at `T` before calling the existing Radar calculator. The `T-1` snapshot is separately prefix-truncated. Only after selection flags are frozen does the evaluator read retained closes after `T`.

This proves price-path no-hindsight behavior for the supplied frozen state.

It does **not** independently prove that the final state's catalog was the official effective catalog on every historical date inside the rolling window. HiThink's current source contracts provide current catalog/current constituents and historical price bars, not a historical catalog-effective-date or historical constituent-change service.

Therefore every v0 report carries:

`FROZEN_UNIVERSE_PRICE_PATH_ONLY__CATALOG_EFFECTIVE_DATE_NOT_INDEPENDENTLY_PROVEN`

and:

`NOT_CERTIFIED__HISTORICAL_CATALOG_EFFECTIVE_DATE_UNKNOWN`

Do not relabel these results as a full historical production replay or certified investment edge.

## Output

One validated 127-session `SectorRadarMarketState` produces:

- one compact row for every eligible `(session, sector)` observation;
- exact Radar-selected and baseline-selected flags;
- T+5 / T+20 / T+60 outcome status and metrics;
- per-family/per-horizon Radar and baseline cohort summaries;
- cohort overlap counts;
- explicit forward-excess-sign miss / false-positive proxies;
- deterministic `study_hash` independent of the report-generation clock.

Pending horizons remain pending; no partial-horizon return is substituted.

## Non-goals

No provider call, new market-data source, portfolio construction, transaction costs, position sizing, Sharpe optimization, model fitting, automatic Research, Odds, Action, or Investment Authority. A later requirement may add stronger historical universe identity if an exact source contract exists; v0 does not invent it.
