# GigaDevice market-regime Human calibration — 2026-09-02

Status: **EXPERIMENTAL HUMAN CALIBRATION / NON-PRODUCTION / NON-PARAMETRIC**

This checkpoint freezes one Human judgment for later Odds-policy evaluation. It does not change production policy, Research, Human wake semantics, Recommendation, sizing, execution, or investment authority.

## Frozen case context

- Security: 兆易创新 / 603986.SS
- Research: current Full Research v2 on `main` at commit `5ca09ad5ca6593e20abfa05f03a71850bbb0e66e`
- Observed 2026-09-02 close used in the preceding Decision Inbox / calibration discussion: **CNY 388.86**
- Existing v2 probability-weighted terminal value used in the discussion: approximately **CNY 436.52/share**
- Existing v2 expected holding-period return at CNY 388.86: approximately **12.3%**
- Calibration recorded at: **2026-09-02T18:39:00+08:00**

## Human judgment

At the current structure, **the Human would not buy GigaDevice at CNY 388.86**.

The Human's stated reason is not a new company-specific fundamental contradiction. The stated concern is the broader market regime: Shanghai Composite and ChiNext are described as below their annual moving averages, market turnover as extremely contracted, and the Human believes historical monthly bearish-cross regimes have had materially greater downside than upside probability.

This is preserved as the Human's contemporaneous market-regime judgment. The individual market-condition claims and the claimed historical conditional probability have **not** been independently validated by this checkpoint and must not be promoted to Kernel truth merely because the Human uses them in judgment.

## Semantic interpretation

The calibration implies:

```text
GigaDevice company Belief
= unchanged by price / broad-market technical state alone

Broad-market regime concern
→ Human demands greater compensation for risk
→ current first-participation hurdle is higher than the no-regime-overlay interpretation

CNY 388.86
→ NOT A HUMAN-ACCEPTED FIRST-PARTICIPATION PRICE at this PIT
```

Because the current v2 expected holding-period return at CNY 388.86 is about 12.3%, any challenger that mechanically treats roughly 10%–12% expected return as sufficient for first participation **without accounting for the current market-regime concern** conflicts with this Human calibration.

This checkpoint does **not** establish an exact replacement hurdle or an exact lower entry price. Inferring one would manufacture precision the Human did not provide.

## Architecture implication under test

The narrow hypothesis to test later is:

> A market-regime risk premium may legitimately raise the required-return hurdle used by Odds / participation evaluation while leaving company fundamental Belief unchanged.

This must remain distinct from these stronger, currently unsupported claims:

- a moving-average or monthly-cross signal deterministically predicts the market;
- a technical regime directly changes company fundamental probabilities;
- a market-regime indicator deserves a second Human wake gate;
- the Kernel should build a new technical-analysis Radar;
- one Human calibration is enough to set a universal market-regime add-on.

If this hypothesis is later operationalized, prefer reusing an existing observed-market / market-context seam and keep the existing `HumanResearchSurface.status + attention_eligible` wake contract. Do not create a parallel attention state machine.

## Evaluation use

For future challengers, this checkpoint provides one bounded gold constraint:

```text
under the Human-described 2026-09-02 weak-market regime,
GigaDevice at CNY 388.86 must not be interpreted as
Human-approved first participation.
```

It does not specify where first participation begins. A later explicit Human price boundary, or repeated natural cases, is required before graduating a parameterized market-regime policy.

`Research ≠ Recommendation · Investment Authority = NONE`
