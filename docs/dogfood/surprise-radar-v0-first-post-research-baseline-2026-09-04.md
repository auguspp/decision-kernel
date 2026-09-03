# Surprise Radar v0 — First Post-Research Prospective Baseline

Status: **REAL POST-RESEARCH BASELINE / NO ANOMALY LABEL / NO DETECTOR / NO INVESTMENT AUTHORITY**  
Date: **2026-09-04**

## Purpose

Slice the first real scheduled `market-history-shadow` artifact by the actual Research creation boundary so only price changes that occurred after the relevant `ResearchSnapshot.created_at` remain eligible for prospective Surprise Radar evaluation.

This checkpoint exists because the first review exposed a real lineage ambiguity:

```text
ResearchSnapshot.as_of_datetime
= PIT information cutoff
!= Research existence time

ResearchSnapshot.created_at
= Research creation time used for prospective eligibility
```

PR #138 (`radar/shadow-research-created-at`) adds the already-existing `created_at` field to future shadow `research_identity` output. This note reconstructs the same boundary for the already-captured 2026-09-03 artifact.

## Source artifact

```text
workflow = decision-inbox
run_id = 33757562673
artifact = market-history-shadow
artifact_id = 9894080655
artifact_digest = sha256:1ff066f5560982f84af004aa482af0c29be857fa85fbeb300a7bd04b463ddf16
qualified history through = 2026-09-03
price convention = RAW_UNADJUSTED_COMPLETED_A_SHARE_CLOSE
```

No price history is re-sourced here. This checkpoint uses the exact retained artifact and the ResearchSnapshot creation timestamps already present in the source Research packages.

## Eligibility convention

For daily-close observation:

```text
if Research is created before a market session begins:
    that session's close-to-close daily move may be observed prospectively

if Research is created after that session closes:
    the first eligible daily move is from that close to the next completed session close
```

The previous close may be a pre-Research reference price. The **observed market move itself** must occur after Research creation.

This is observation lineage only. It does not define a threshold or detector.

## Research creation boundaries

```text
600519 Moutai     created_at = 2026-09-01 23:30 +08:00
300750 CATL       created_at = 2026-09-02 08:10 +08:00
600036 CMB        created_at = 2026-09-02 08:10 +08:00
601088 Shenhua    created_at = 2026-09-02 08:10 +08:00
603986 GigaDevice created_at = 2026-09-02 17:18 +08:00
002050 Sanhua     created_at = 2026-09-02 19:45 +08:00
```

Moutai, CATL, CMB and Shenhua therefore had Research before the 2026-09-02 A-share session. GigaDevice and Sanhua were created after the 2026-09-02 close, so their first eligible daily move is the 2026-09-02 close → 2026-09-03 close interval.

## Eligible post-Research daily observations

| Security | Eligible session move | Previous close | New close | Daily return |
| --- | --- | ---: | ---: | ---: |
| **300750 CATL** | 2026-09-02 | 358.10 | 348.29 | **-2.74%** |
| **300750 CATL** | 2026-09-03 | 348.29 | 349.50 | +0.35% |
| **600036 CMB** | 2026-09-02 | 40.86 | 40.87 | +0.02% |
| **600036 CMB** | 2026-09-03 | 40.87 | 41.07 | +0.49% |
| **600519 Moutai** | 2026-09-02 | 1299.56 | 1297.50 | -0.16% |
| **600519 Moutai** | 2026-09-03 | 1297.50 | 1298.88 | +0.11% |
| **601088 Shenhua** | 2026-09-02 | 48.30 | 48.05 | -0.52% |
| **601088 Shenhua** | 2026-09-03 | 48.05 | 47.78 | -0.56% |
| **603986 GigaDevice** | 2026-09-03 | 388.86 | 383.20 | **-1.46%** |
| **002050 Sanhua** | 2026-09-03 | 35.62 | 36.30 | **+1.91%** |

Count:

```text
eligible post-Research daily observations = 10
securities represented = 6
largest absolute daily move = 2.74% / CATL / 2026-09-02
```

## Interpretation boundary

These ten observations are the first actual prospective Surprise Radar baseline.

They do **not** establish:

- that ±2.74% is a noise boundary;
- that none is a qualified anomaly;
- that CATL's -2.74% move should alert;
- that smaller moves should not alert;
- any z-score, volatility normalization, rank or threshold;
- any Fundamental Belief change;
- any causal explanation for price changes.

Current label state remains:

```text
ELIGIBLE POST-RESEARCH OBSERVATIONS = YES / 10
QUALIFIED PRICE ANOMALY LABEL = NOT YET EARNED
FALSE-NEGATIVE CANDIDATE = NOT YET EARNED
DETECTOR DESIGN = WAIT
```

The useful fact is simply that the first prospective baseline is **mechanically quiet relative to the much larger pre-Research historical paths** that originally dominated visual review.

## Why this matters

Without creation-time slicing, the 45-day window made GigaDevice's July/August drawdown and other historical movements look like candidate Radar evidence even though Research did not exist yet.

After correct slicing:

```text
historical context = still useful
prospective Radar evidence = 10 post-Research daily moves
large historical dislocation != prospective anomaly evidence
```

This gives future batches a clean comparison base without inventing a detector from hindsight.

## Next evidence

1. let the next scheduled shadow batch arrive naturally;
2. append new post-`created_at` observations without changing the boundary;
3. surface a candidate only when its mechanical path is meaningfully distinct from the accumulating prospective baseline;
4. still require Human triage after alert; alert permission is already default for followed researched cases;
5. preserve quieter cases for later false-negative review if decision-relevant evidence arrives without a notable price path.

## Authority boundary

```text
RADAR SEMANTICS = SHADOW_OBSERVATION_ONLY
ALERT AUTHORITY = ATTENTION ONLY
FUNDAMENTAL BELIEF CHANGE = NO
ODDS CHANGE = NO
RECOMMENDATION = NO
ACTION = NO
INVESTMENT AUTHORITY = NONE
```

## Disposition

```text
FIRST TRUE POST-RESEARCH BASELINE = ESTABLISHED
OBSERVATIONS = 10 / SIX SECURITIES
QUALIFIED ANOMALY = NOT YET
FALSE NEGATIVE = NOT YET
DETECTOR = WAIT
NEXT = NATURAL BATCH ACCUMULATION
```
