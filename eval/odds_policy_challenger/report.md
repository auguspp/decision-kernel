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

A straight rollback would add 贵州茅台 to the current Human wake set and would label CATL/CMB/Moutai `ATTRACTIVE_ODDS`. This is a useful behavior delta, but **not clean false-positive evidence**: Moutai is explicitly a generic dogfood Research package with simple scenario EPS/P-E assumptions, so it is not a Human-reviewed policy-calibration gold case.

## ACCEPTABLE_ODDS price boundary

The probability boundary is exclusive when it binds because zero-return scenarios do not count as positive. In these five current cases the expected-return gate binds first.

| Case | Holding days from 2026-09-02 | Legacy cumulative | Current live | Legacy horizon-aware |
| --- | ---: | ---: | ---: | ---: |
| 宁德时代 300750 | 328 | ¥393.22 | ¥351.52 | ¥399.87 |
| 招商银行 600036 | 362 | ¥48.43 | ¥43.86 | ¥48.49 |
| 贵州茅台 600519 | 354 | ¥1426.09 | ¥1291.34 | ¥1432.11 |
| 中国神华 601088 | 362 | ¥39.07 | ¥35.37 | ¥39.11 |
| 兆易创新 603986 v2 | 365 | ¥369.93 | ¥330.70 | ¥369.93 |

## Historical Human semantics — 东山精密 002384

The preserved Human-reviewed Price / Odds PIT on 2026-08-23 explicitly approved these case-specific bands, conditional on Belief remaining intact:

```text
> ¥185       = NO ACTIVE PARTICIPATION / WATCH
¥170-185     = NEAR / IMPROVING ODDS, NOT PREFERRED ENTRY
¥165-170     = FIRST-PARTICIPATION CANDIDATE ZONE
¥150-160     = ATTRACTIVE / HIGH-ODDS PARTICIPATION ZONE
¥145-150     = STRONG ODDS IF BELIEF IS UNCHANGED
```

The same Human-reviewed record also froze a supplemental annualized hurdle map from the ¥194.85 weighted payoff over roughly 495 days:

```text
10% annualized hurdle -> ~¥171.22
15% annualized hurdle -> ~¥161.21
20% annualized hurdle -> ~¥152.17
```

Those values were explanatory, not canonical engine output, but they establish that the Human-approved bands were horizon-aware in meaning.

The later operational proof used the same five Human-reviewed scenarios, model risk `HIGH`, market date 2026-08-24, and valuation horizon 2027-12-31 (494 days). Its legacy `ACCEPTABLE_ODDS` hurdle was 15% cumulative + 50% positive-return probability, giving an effective price boundary of **¥169.43**.

That is not merely close to the Human-approved first-participation band; it lands directly inside it.

By contrast, today's live calibration for the exact same historical state gives:

- current `ACCEPTABLE_ODDS`: **¥153.43** — inside the Human-approved **ATTRACTIVE / HIGH-ODDS** band;
- current `ATTRACTIVE_ODDS`: roughly **¥137.22** — below the Human-approved Strong Odds band;
- current `EXCEPTIONAL_ODDS`: roughly **¥120.28** — far below the approved Strong Odds band.

For the 494-day horizon, the effective expected-return hurdles are approximately:

| Policy tier | Legacy cumulative | Annualized equivalent | Current cumulative | Annualized equivalent |
| --- | ---: | ---: | ---: | ---: |
| ACCEPTABLE | 15% | 10.9% | 27% | 19.3% |
| ATTRACTIVE | 25% | 17.9% | 42% | 29.6% |
| EXCEPTIONAL | 40% | 28.2% | 62% | 42.8% |

This is direct evidence of **semantic calibration drift**: current `ACCEPTABLE_ODDS` behaves much more like the historical Human meaning of High Odds than First Participation.

## Independent horizon lesson — 中际旭创 300308

A separate Human challenge on Zhongji Innolight rejected a decision process that treated a nominal upside percentage as decision-useful without a stated horizon. The subsequent Odds remediation explicitly falsified the assumption that nominal upside is meaningful without time, established a 12-month primary observation convention, and showed 18/24-month annualized-hurdle sensitivities.

This is not a second numerical calibration gold case because the Human did not approve one required-return hurdle or a probability-weighted distribution. It **is** independent evidence that horizon semantics should not be ignored.

## Readout

1. **The old Dongshan operational `ACCEPTABLE_ODDS` was genuinely calibrated to Human-approved first-participation semantics.** Its ¥169.43 boundary lands inside the approved ¥165-170 band.
2. **The current live `ACCEPTABLE_ODDS` is semantically one tier too strong for that historical Human case.** Its ¥153.43 boundary lands in the approved ¥150-160 High-Odds band.
3. **Do not mechanically roll production back to `10/20/35`.** The current five-name comparison is mostly generic dogfood rather than Human-reviewed policy gold; it can show behavioral deltas but cannot adjudicate false positives.
4. **Do not treat annualization as a magic patch.** Horizon-explicit semantics are supported by both Dongshan and Zhongji, but applying the old cumulative hurdle as an annualized hurdle moves Dongshan's ACCEPTABLE boundary to ¥161.27 and no longer reproduces the approved first-participation band.
5. **GigaDevice v2 is still not a first-participation candidate at ¥388.86 under any tested candidate.** The Research correction raises expected return to about 12.3% with 70% positive-scenario probability; the legacy acceptable boundary is about ¥369.93.
6. **Production should not gain a second wake gate.** Any future correction belongs in the existing Odds policy/semantics and must preserve `HumanResearchSurface` as the sole attention gate.

The experiment supports a production policy review, but does not by itself authorize a guessed replacement threshold set.

`Research ≠ Recommendation · Investment Authority = NONE`
