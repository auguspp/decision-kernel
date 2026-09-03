# Surprise Radar v0 — First Real Scheduled Window Review

Status: **REAL SCHEDULED SHADOW BATCH / CONTROL ELIGIBILITY CORRECTED / NO DETECTOR / NO HUMAN-WAKE CHANGE**  
Date: **2026-09-04**

## Purpose

Review the first naturally scheduled `market-history-shadow` batch before its short-lived Actions artifact expires, without promoting any anomaly rule or inferring Fundamental Belief from price.

A later Human-triage pass initially promoted GigaDevice as the first positive control. That promotion has now been **retracted** because the candidate anomaly occurred before GigaDevice had a frozen ResearchSnapshot in the repository.

The corrected follow-on checkpoint is:

`docs/dogfood/surprise-radar-v0-gigadevice-positive-control-2026-09-04.md`

The filename is retained for lineage, but the document now records a counterfactual Human triage response rather than a valid positive control.

## Source batch

GitHub Actions run:

```text
workflow = decision-inbox
run_id = 33757562673
event = schedule
status = success
created_at = 2026-09-03T12:50:43Z
head_sha = a3ea934249a4b1a5a81d339cd85dc8af29f9934e
```

Shadow artifact:

```text
name = market-history-shadow
artifact_id = 9894080655
artifact_digest = sha256:1ff066f5560982f84af004aa482af0c29be857fa85fbeb300a7bd04b463ddf16
retention = 14 days
```

The artifact contained six qualified HiThink raw-unadjusted completed-close windows through **2026-09-03**:

```text
002050.SZ  Sanhua / 三花智控
300750.SZ  CATL / 宁德时代
600036.SH  CMB / 招商银行
600519.SH  Kweichow Moutai / 贵州茅台
601088.SH  China Shenhua / 中国神华
603986.SH  GigaDevice / 兆易创新
```

Every observation retained the existing boundary:

```text
RADAR SEMANTICS = SHADOW_OBSERVATION_ONLY
HUMAN ATTENTION AUTHORITY = NONE
INVESTMENT AUTHORITY = NONE
```

## Mechanical review only

The following calculations use only the close sequence inside the retained window. They are descriptive diagnostics, not detector thresholds.

| Security | Window return | 5d | 10d | 20d | Max drawdown inside window | Largest down day |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **603986 兆易创新** | **-19.4%** | **-6.8%** | -5.0% | -0.5% | **-28.3%** | **-10.0%** |
| **300750 宁德时代** | -8.6% | -6.3% | **-9.2%** | **-9.9%** | -14.0% | -4.2% |
| **002050 三花智控** | -4.7% | -1.4% | +0.4% | -6.2% | -10.3% | -7.1% |
| **600519 贵州茅台** | -0.7% | +0.5% | +0.6% | -0.7% | -6.5% | -3.6% |
| **601088 中国神华** | +5.9% | ~0.0% | +2.6% | +8.7% | -5.9% | -4.3% |
| **600036 招商银行** | +8.1% | +3.8% | +5.7% | +5.4% | -5.8% | -2.7% |

The most mechanically distinct path in this batch is **GigaDevice**:

```text
2026-07-21 close = CNY475.53
2026-08-03 close = CNY340.74
window max drawdown = -28.3%
2026-09-03 close = CNY383.20
```

CATL is different: the path is less discontinuous but shows a sustained late-window decline.

## Same-batch Decision Inbox / disclosure context

The same scheduled run produced:

```text
Decision Inbox attention = CATL only
GigaDevice = INSUFFICIENT_ODDS at CNY383.20
official disclosure scan = 9 unassessed packets
```

The 2026-09-03 CATL official disclosure batch contained, among other things, a buyback-progress announcement stating that **as of 2026-08-31 the approved A-share repurchase had not yet been executed**.

That disclosure is relevant to capital allocation context, but it remains another **CATL capital-allocation variant**. It does not satisfy the existing Commitment Radar promotion threshold requiring a different naturally encountered case.

Sanhua's 2026-09-03 packet was an H-share next-day disclosure form and does not, on its face, reopen the five robot operating-economics evidence buckets.

No new GigaDevice official disclosure packet appeared in this scheduled scan.

## Control eligibility correction

Current Surprise Radar v0 shadow observations bind to an exact frozen `ResearchSnapshot` id / as-of / information-bundle hash.

Therefore a historical anomaly can qualify as a control only if:

```text
frozen ResearchSnapshot exists before anomaly
+ anomaly occurs after Research freeze
+ Human later labels whether that anomaly deserved Research triage
```

This matters because a full retained history window can extend **before** the ResearchSnapshot used by the scheduled observation. Those older bars are mechanically valid price history, but they are not automatically eligible Radar controls.

### 603986 / GigaDevice

Repository history:

```text
first Full Research package = 2026-09-02 09:37:02 +08:00
candidate anomaly = 2026-07-21 → 2026-08-03
```

Therefore:

```text
PRE-ANOMALY RESEARCH = NO
VALID SURPRISE RADAR POSITIVE CONTROL = NO
```

The Human subsequently answered the counterfactual usefulness question with:

```text
A = worth alerting me; should trigger Research triage
```

That answer remains useful as a Human preference / cold-start counterfactual, but **does not belong in the current Surprise Radar v0 control corpus**.

### 002050 / Sanhua

The same issue invalidates using the 2026-08-19 `-7.10%` day as a negative-control candidate:

```text
first Sanhua Full Research package = 2026-09-02 20:24:02 +08:00
candidate large move = 2026-08-19
PRE-ANOMALY RESEARCH = NO
```

Do not ask the Human to label that move for the current Radar corpus.

### 300750 / CATL and other windows

They remain context windows until a candidate anomaly **after their applicable frozen ResearchSnapshot** is identified and labeled.

## What this review proves

```text
REAL SCHEDULED SHADOW BATCH = YES
SIX QUALIFIED WINDOWS = YES
ARTIFACT RETENTION / REPLAY IDENTITY = YES
MECHANICALLY DISTINCT PATHS = YES
HISTORICAL PRE-RESEARCH PRICE PATHS EXIST = YES
VALID POSITIVE CONTROL = NOT YET
VALID NEGATIVE CONTROL = NOT YET
VALID FALSE-NEGATIVE CONTROL = NOT YET
DETECTOR THRESHOLD = NOT JUSTIFIED
RADAR SCORE = NO
HUMAN WAKE CHANGE = NO
KERNEL CHANGE = NO
```

## Next evidence

Do not tune a threshold from this batch.

Next useful step:

1. use the exact frozen ResearchSnapshot timestamp as the left boundary for control eligibility;
2. let post-Research price windows accumulate naturally;
3. obtain Human triage only on anomalies that occur after that freeze;
4. earn a valid positive, negative and false-negative candidate from those prospective windows;
5. only then test a simple explainable shadow rule.

## Disposition

```text
FIRST REAL SHADOW REVIEW = COMPLETE
603986 HISTORICAL ANOMALY = COUNTERFACTUAL ONLY / NOT VALID CONTROL
002050 2026-08-19 LARGE MOVE = PRE-RESEARCH / NOT VALID CONTROL CANDIDATE
VALID CONTROL CORPUS = EMPTY
DETECTOR DESIGN = WAIT
CURRENT PROJECT PRIORITY = ACCUMULATE POST-RESEARCH NATURAL WINDOWS + HUMAN TRIAGE
```
