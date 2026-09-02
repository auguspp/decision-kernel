# Odds Policy Challenger v0

Experiment only. Production policy, Human wake semantics, Recommendation, sizing, execution and investment authority are unchanged.

## Current close classifications

Prices are the 2026-09-02 HiThink close from Decision Inbox run `33611493578`. GigaDevice uses the same observed close with the newly frozen Full Research v2.

| Case | Expected return | Positive probability | Legacy cumulative | Current live | Legacy horizon-aware |
| --- | ---: | ---: | --- | --- | --- |
| 宁德时代 300750 | 33.2% | 75.0% | `ATTRACTIVE_ODDS` | `ACCEPTABLE_ODDS` | `ATTRACTIVE_ODDS` |
| 招商银行 600036 | 36.3% | 75.0% | `ATTRACTIVE_ODDS` | `ACCEPTABLE_ODDS` | `ATTRACTIVE_ODDS` |
| 贵州茅台 600519 | 26.4% | 75.0% | `ATTRACTIVE_ODDS` | `INSUFFICIENT_ODDS` | `ATTRACTIVE_ODDS` |
| 中国神华 601088 | -6.5% | 25.0% | `INSUFFICIENT_ODDS` | `INSUFFICIENT_ODDS` | `INSUFFICIENT_ODDS` |
| 兆易创新 603986 v2 | 12.3% | 70.0% | `INSUFFICIENT_ODDS` | `INSUFFICIENT_ODDS` | `INSUFFICIENT_ODDS` |

The immediate noise delta is therefore concrete: a straight rollback from the current policy to the old operational calibration would add **贵州茅台** to the Human wake set and would label all three waking names `ATTRACTIVE_ODDS`, not merely first-participation candidates.

## ACCEPTABLE_ODDS price boundary

The probability boundary is exclusive when it binds because zero-return scenarios do not count as positive. In these five current cases the expected-return gate binds first.

| Case | Holding days from 2026-09-02 | Legacy cumulative | Current live | Legacy horizon-aware |
| --- | ---: | ---: | ---: | ---: |
| 宁德时代 300750 | 328 | ¥393.22 | ¥351.52 | ¥399.87 |
| 招商银行 600036 | 362 | ¥48.43 | ¥43.86 | ¥48.49 |
| 贵州茅台 600519 | 354 | ¥1426.09 | ¥1291.34 | ¥1432.11 |
| 中国神华 601088 | 362 | ¥39.07 | ¥35.37 | ¥39.11 |
| 兆易创新 603986 v2 | 365 | ¥369.93 | ¥330.70 | ¥369.93 |

## Historical operational reference — 东山精密 002384

The preserved `decision-os` operational proof uses five Human-reviewed scenario worlds with probability-weighted payoff **¥194.85**, model risk `HIGH`, market date `2026-08-24`, and valuation horizon `2027-12-31` (**494 days**).

At the historical observed price **¥193.60**, all three challengers remain `INSUFFICIENT_ODDS`; the useful comparison is the first `ACCEPTABLE_ODDS` boundary:

- Legacy cumulative: **¥169.43**
- Current live calibration: **¥153.43**
- Legacy horizon-aware: **¥161.27**

That isolates two effects. The current live calibration materially moved the first acceptable boundary downward. But horizon normalization alone does **not** restore the historical operational boundary: because Dongshan's horizon is longer than one year, annualizing the same legacy hurdle makes it stricter, not looser.

## Readout

1. **Do not roll production back to `10/20/35` unchanged.** On today's real five-name dogfood it wakes an extra weak/generic Research case (Moutai) and upgrades CATL/CMB/Moutai to `ATTRACTIVE_ODDS`.
2. **Do not pretend annualization is the whole fix.** It is conceptually cleaner across variable horizons, but the 494-day Dongshan reference moves from ¥169.43 to ¥161.27 under horizon-aware legacy calibration.
3. **GigaDevice v2 is still not a first-participation candidate at ¥388.86.** The Research correction lifts expected return to about 12.3% with 70% positive-scenario probability, but even the legacy acceptable boundary is only about ¥369.93.
4. **The current `ACCEPTABLE_ODDS` threshold is doing useful noise suppression, but its semantic label is stronger than the old first-participation meaning.** The next challenger should target that semantic/calibration gap without adding a second Human wake gate.

No production policy change is justified by this experiment alone.

`Research ≠ Recommendation · Investment Authority = NONE`
