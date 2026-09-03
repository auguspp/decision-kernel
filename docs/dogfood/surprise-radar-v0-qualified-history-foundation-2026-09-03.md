# Surprise Radar v0 — qualified history foundation

Status: **HARNESS FOUNDATION / NO RADAR SCORE / NO HUMAN-WAKE CHANGE / NO PROVIDER CHANGE**

Date: 2026-09-03

## Why this slice exists

The first Surprise Radar question is intentionally narrow:

> Can the Harness observe a mechanical price-path anomaly from qualified market history without turning that observation into a stock-selection score or a second Human attention policy?

Before this change, the HiThink runtime already requested a 45-day raw daily history window in order to construct the latest `ObservedMarket`, but the adapter normalized only the latest completed close. The already-fetched historical closes were validated and then discarded.

That is the wrong place to begin an anomaly detector. The missing primitive is not a more sophisticated model; it is a qualified, replayable history window.

## Boundary

This slice therefore adds only commodity acquisition / normalization:

```text
HiThink raw daily history
→ exact thscode check
→ raw-unadjusted check
→ trading-calendar check
→ finite positive close check
→ no duplicate/off-calendar/future bar
→ completed-session gate
→ qualified close window
```

The live Odds path still consumes only the latest completed close as `ObservedMarket`.

The new history window is Harness-owned input for future shadow experiments. It has no:

- anomaly threshold;
- z-score;
- factor score;
- stock ranking;
- Research route;
- fundamental-state migration authority;
- Human wake authority;
- investment authority.

## Data authority remains unchanged

A-share market data remains HiThink-only for qualified production market observations.

No fallback provider, provider registry, public-web price substitution, or alternate market authority is introduced.

The existing price convention is preserved exactly:

`RAW_UNADJUSTED_COMPLETED_A_SHARE_CLOSE`

## New adapter shape

The adapter now exposes:

- `HithinkCompletedPricePoint`
  - exact raw close;
  - exact completed-session `as_of` clock;
- `HithinkCompletedPriceHistory`
  - exact `thscode`;
  - ordered qualified points;
  - provider `response_session`;
  - `expected_latest_session` from the trading calendar and observation clock.

`normalize_hithink_completed_price_history(...)` uses the same fail-closed raw-history validation already used by live price normalization.

A stale provider response is not relabeled as fresh. At the pure adapter layer:

```text
response_session < expected_latest_session
```

remains visible in the returned object.

A response that includes an unfinished same-day bar before the A-share close fails closed.

## Runtime shape

`fetch_hithink_completed_price_history(...)` reuses the existing two-call live acquisition path:

1. A-share trading calendar;
2. 45-day raw daily history.

The live runtime requires the history response to reach the latest completed A-share session. Stale live history therefore fails visibly rather than feeding a future detector.

`fetch_latest_hithink_observed_market(...)` now derives the same latest `ObservedMarket` from the qualified history window. No live Odds semantics change.

## Why no detector yet

A detector should be judged on real historical windows and later attribution, not on a synthetic threshold chosen because it produces an interesting alert.

The repository now has the required qualified input seam. The next Surprise Radar experiment should be a **shadow-only price-dislocation detector** run on naturally fetched HiThink windows, with outputs recorded as observation candidates rather than attention decisions.

The first detector should remain deliberately simple and explainable. A library such as `ruptures`, `river`, or `pyod` is still not justified until a native 20–50 line baseline has a demonstrated failure mode.

## Required next evidence

Before promoting any price anomaly rule, collect real windows that include at least:

1. one obvious price-path dislocation that a Human agrees was worth Research triage;
2. one large price move that should remain `IGNORE` because no decision-relevant evidence followed;
3. one quieter case where later important evidence reveals a potential false negative;
4. exact source/freshness metadata for every window.

Then evaluate:

```text
mechanical observation
→ Human triage usefulness
→ later Research consequence
```

not trading returns and not stock-picking accuracy.

## Disposition

```text
QUALIFIED HISTORICAL PRICE INPUT = NOW EXPOSED
A-SHARE MARKET AUTHORITY = HITHINK ONLY
LIVE ODDS PRICE SEMANTICS = UNCHANGED
SURPRISE RADAR DETECTOR = NOT YET
RADAR SCORE = NO
HUMAN WAKE CHANGE = NO
NEW DEPENDENCY = NO
NEXT = SHADOW PRICE-DISLOCATION DOGFOOD ON REAL WINDOWS
```
