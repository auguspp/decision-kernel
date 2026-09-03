# Surprise Radar v0 — First Real Scheduled Window Review

Status: **REAL SCHEDULED SHADOW BATCH / ELIGIBILITY + HUMAN ALERT POLICY CORRECTED / NO DETECTOR / NO INVESTMENT AUTHORITY**  
Date: **2026-09-04**

## Purpose

Review the first naturally scheduled `market-history-shadow` batch before its short-lived Actions artifact expires, without promoting any anomaly rule or inferring Fundamental Belief from price.

A later Human-triage pass initially promoted GigaDevice as the first positive control. That promotion was retracted because the candidate anomaly occurred before GigaDevice had a frozen ResearchSnapshot in the repository.

The Human subsequently clarified a more important policy point: for a case that **already has frozen Research and remains followed**, a qualified price anomaly may be surfaced by default; alert permission does not need to be re-earned case by case. Only an explicit Human statement that the case is no longer followed should suppress future Surprise Radar alerts.

Relevant follow-on checkpoints:

- `docs/dogfood/surprise-radar-v0-gigadevice-positive-control-2026-09-04.md` — retained filename; corrected counterfactual GigaDevice checkpoint, not a valid control.
- `docs/dogfood/surprise-radar-v0-human-alert-policy-2026-09-04.md` — frozen Human alert preference.

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

## Eligibility correction

Current Surprise Radar v0 shadow observations bind to an exact frozen `ResearchSnapshot` id / as-of / information-bundle hash.

Therefore a historical anomaly can qualify as a real current-v0 observation only if:

```text
frozen ResearchSnapshot exists before anomaly
+ anomaly occurs after Research freeze
```

A full retained history window can extend **before** the ResearchSnapshot used by the scheduled observation. Those older bars are mechanically valid price history, but they are not automatically eligible Surprise Radar observations.

### 603986 / GigaDevice

Repository history:

```text
first Full Research package = 2026-09-02 09:37:02 +08:00
candidate anomaly = 2026-07-21 → 2026-08-03
```

Therefore:

```text
PRE-ANOMALY RESEARCH = NO
VALID SURPRISE RADAR v0 OBSERVATION = NO
```

The Human answered the earlier counterfactual usefulness question with:

```text
A = worth alerting me; should trigger Research triage
```

That answer remains useful as a counterfactual preference, but it does not backdate Radar eligibility.

### 002050 / Sanhua

The same issue applies to the 2026-08-19 `-7.10%` day:

```text
first Sanhua Full Research package = 2026-09-02 20:24:02 +08:00
candidate large move = 2026-08-19
PRE-ANOMALY RESEARCH = NO
```

It is not an actual current-v0 Radar observation either.

The Human later clarified that **if prior Research had existed and the case remained followed**, both the GigaDevice and Sanhua price anomalies could have been surfaced as alerts. That is a Human alert-policy statement, not historical control promotion.

### 300750 / CATL and other windows

They remain context windows until a candidate anomaly **after their applicable frozen ResearchSnapshot** is identified.

## Human alert preference — replaces per-anomaly alert labeling

The frozen Human preference is:

```text
PRE-EXISTING FROZEN RESEARCH = YES
CASE STILL FOLLOWED = YES
QUALIFIED PRICE ANOMALY = YES
→ MAY ALERT BY DEFAULT
```

Suppression requires an explicit Human opt-out:

```text
Human explicitly says no longer follow / no longer interested
→ suppress Surprise Radar alerts for that case
```

Do not treat `WAIT`, `NO_ACTION`, a frozen Research stop state, or lack of recent discussion as an opt-out.

This means the earlier evaluation plan — earn a `positive control` when the Human says alert, and a `negative control` when the Human says a large move should be ignored — is no longer the right primary experiment for active researched cases.

Alerting remains only attention allocation:

```text
ALERT
!= automatic Research reopen
!= Fundamental Belief change
!= Odds change
!= Recommendation
!= Action
!= Investment Authority
```

After receiving an alert, the Human may still triage `DEEPEN / WAIT / DROP`.

## What still needs evidence

The Human policy does **not** define what mechanical path qualifies as a `price anomaly`.

That is now the main Surprise Radar experiment:

1. observe natural **post-Research** price windows;
2. distinguish mechanically meaningful anomalies from ordinary price noise without tuning to one case;
3. identify quieter post-Research paths followed by decision-relevant evidence as false-negative candidates;
4. preserve cross-case diversity and exact ResearchSnapshot / price-source lineage;
5. only after enough natural evidence, test a simple explainable shadow rule.

The detector still must avoid turning routine fluctuations into alerts.

## What this review proves

```text
REAL SCHEDULED SHADOW BATCH = YES
SIX QUALIFIED HISTORY WINDOWS = YES
ARTIFACT RETENTION / REPLAY IDENTITY = YES
MECHANICALLY DISTINCT HISTORICAL PATHS = YES
HISTORICAL PRE-RESEARCH PRICE PATHS EXIST = YES
DEFAULT HUMAN ALERT PREFERENCE FOR FOLLOWED RESEARCHED CASES = FROZEN
VALID POST-RESEARCH ANOMALY EXAMPLE = NOT YET EARNED
FALSE-NEGATIVE CANDIDATE = NOT YET EARNED
DETECTOR THRESHOLD = NOT JUSTIFIED
RADAR SCORE = NO
KERNEL CHANGE = NO
INVESTMENT AUTHORITY = NONE
```

## Next evidence

Do not tune a threshold from this batch.

Next useful step:

1. use each exact frozen ResearchSnapshot timestamp as the left boundary for Surprise Radar eligibility;
2. let post-Research price windows accumulate naturally;
3. evaluate which mechanical paths deserve the label `qualified price anomaly` versus ordinary noise;
4. look explicitly for quieter false-negative candidates;
5. only then test a simple explainable shadow rule.

## Disposition

```text
FIRST REAL SHADOW REVIEW = COMPLETE
603986 HISTORICAL ANOMALY = COUNTERFACTUAL ONLY / PRE-RESEARCH
002050 2026-08-19 LARGE MOVE = COUNTERFACTUAL ONLY / PRE-RESEARCH
PER-ANOMALY HUMAN ALERT A/B LABELING = NOT THE PRIMARY EXPERIMENT
FOLLOWED + RESEARCHED + QUALIFIED ANOMALY = MAY ALERT BY DEFAULT
EXPLICIT HUMAN NO-LONGER-FOLLOWING = SUPPRESS
DETECTOR DESIGN = WAIT
CURRENT PROJECT PRIORITY = ACCUMULATE POST-RESEARCH NATURAL WINDOWS + CALIBRATE QUALIFIED-ANOMALY / FALSE-NEGATIVE BEHAVIOR
```
