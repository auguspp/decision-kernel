# Human Participation Challenger v1

Status: **EXPERIMENT / NOT PRODUCTION POLICY**

Purpose: compare the current live Odds floor with three real Human calibration cases without changing Research, Odds semantics, Human wake, or investment authority.

## Calibration inputs

### Dongshan Precision 002384 — historical Decision OS Human gold

Frozen distribution (2027-12-31 horizon):

| terminal value | probability |
|---:|---:|
| 82 | 15% |
| 138 | 25% |
| 207 | 35% |
| 288 | 20% |
| 360 | 5% |

Weighted terminal value = **194.85**.

Human-approved participation bands:

- 165–170 = first-participation candidate
- 150–160 = attractive / high odds
- 145–150 = strong odds, but re-check Belief before adding

Historical source: `decision-os/docs/cases/dongshan-precision-002384/2026-08-23-150500Z-price-odds-human-review.md`.

### GigaDevice 603986 — current Research v2 + Human calibration

Frozen distribution is loaded from `research_cases/603986-gigadevice-deep-research-v2.json`.

Human calibration:

- 388.86 = no first position under the stated weak-market regime
- around 322 = first-participation consideration area; long-duration price structure and valuation odds overlap

### Sanhua Intelligent Controls 002050 — current Research v1 + historical Human calibration

Frozen distribution is loaded from `research_cases/002050-sanhua-deep-research-v1.json`.

Human calibration:

- 30.5–32 = first-participation candidate
- 28–30 = high-odds / high-interest area
- below 28 = re-underwrite before heavy participation

## Metrics

The experiment computes only deterministic projections from frozen terminal distributions:

1. probability-weighted holding-period return;
2. positive-return scenario probability;
3. expected positive payoff contribution;
4. expected negative payoff contribution;
5. positive / negative contribution ratio (distribution-wide payoff asymmetry);
6. current live-policy `ACCEPTABLE` return boundary using the production model-risk addon and no extra OddsContext addon.

The asymmetry ratio is explanatory only:

```text
sum[p * max(V/P - 1, 0)]
--------------------------------
sum[p * max(1 - V/P, 0)]
```

It is deliberately not promoted to policy.

## Result

| case / point | expected return | positive probability | distribution asymmetry |
|---|---:|---:|---:|
| Dongshan first midpoint 167.5 | ~16.3% cumulative | 60% | ~2.35x |
| Giga current no-buy 388.86 | ~12.3% | 70% | ~2.39x |
| Giga first 322 | ~35.6% | 70% | ~9.02x |
| Sanhua current wait 36.17 | ~3.8% | 60% | ~1.53x |
| Sanhua first midpoint 31.25 | ~20.1% | 85% | ~10.62x |

### Finding 1 — 2:1 is not a universal gate

Giga at 388.86 is an explicit Human **NO FIRST POSITION**, yet its distribution-wide payoff asymmetry is already about **2.39x**, slightly above Dongshan's Human-approved first-participation midpoint (~2.35x).

Therefore a generic `payoff asymmetry >= 2` gate would create a false positive. The old Sanhua 2:1 Base/Stress heuristic remains useful case-specific reasoning, not Constitution.

### Finding 2 — positive probability alone is also insufficient

Giga at 388.86 has 70% positive-return scenario probability and is still Human-rejected. Dongshan first participation has only 60%.

Positive probability is useful distribution shape information, not a complete participation rule.

### Finding 3 — one return hurdle does not reproduce Human first participation

Human first-participation expected-return requirements differ materially:

- Dongshan 165–170: ~14.6%–18.1% cumulative over ~1.36 years (historical supplemental map put the band around low-teens annualized return);
- Sanhua 30.5–32: ~17.3%–23.1% over the one-year horizon;
- Giga 322: ~35.6% over the one-year horizon.

The differences are too large to justify a universal ~10% annualized first-entry hurdle.

### Finding 4 — current `ACCEPTABLE` semantics drift across Human cases

Using current live policy with no extra OddsContext addon:

- Dongshan HIGH model risk: ACCEPTABLE expected-return floor = 27%; boundary ~**153.43**, inside Human **High-Odds 150–160**.
- Sanhua HIGH model risk: floor = 27%; boundary ~**29.56**, inside Human **High-Odds 28–30**.
- Giga VERY_HIGH model risk: floor = 32%; boundary ~**330.70**, near but slightly looser than Human first consideration around **322**.

So `ACCEPTABLE_ODDS` does not have one stable Human meaning across the three calibration cases.

## Interpretation

The experiment does **not** show that current live policy should simply be lowered or restored to the old Decision OS thresholds.

Instead it shows a missing semantic separation:

```text
Fundamental terminal distribution
→ core Odds metrics
→ model uncertainty
→ path / volatility risk
→ market-regime risk
→ participation context
→ SYSTEM_CANDIDATE
→ Human decides
```

`model risk` cannot safely stand in for all three of model uncertainty, price-path risk, and broad-market regime.

The terminal Research distribution also cannot, by itself, recover the Human's participation aesthetic. Dongshan, GigaDevice and Sanhua require materially different first-participation hurdles even when the same deterministic metrics are available.

## Challenger decision

- **Do not change the live Odds champion from this experiment.**
- Keep expected return and positive probability as core deterministic Odds fields.
- Keep payoff asymmetry as an explanatory challenger metric, not a gate.
- Do not hard-code `HIGH_VOL = +X%` or `WEAK_MARKET = +Y%` from three cases.
- The next useful evidence is deterministic HiThink-derived path-risk context (for example realized volatility, drawdown and gap/path characteristics) evaluated against the same Human golds; this should remain an Odds/participation input, not a second Radar or a change to Fundamental Belief.

Investment Authority = **NONE**.
