# Surprise Radar v0 — First Real Scheduled Window Review

Status: **HUMAN-TRIAGE PREP / REAL SCHEDULED SHADOW BATCH / NO DETECTOR / NO HUMAN-WAKE CHANGE**  
Date: **2026-09-04**

## Purpose

Review the first naturally scheduled `market-history-shadow` batch before its short-lived Actions artifact expires, without promoting any anomaly rule or inferring Fundamental Belief from price.

This note preserves the mechanical review that existed before Human labeling. A separate follow-on checkpoint now freezes the first earned Human triage label:

`docs/dogfood/surprise-radar-v0-gigadevice-positive-control-2026-09-04.md`

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

## Candidate review queue

### 603986 / GigaDevice

Mechanical state at the time this review was first prepared:

```text
CLEAR PRICE-PATH DISLOCATION CANDIDATE = YES
POSITIVE CONTROL = NOT YET
```

Relevant frozen lineage existed later in the repository:

- current Research was refreshed through the 2026-09-02 PIT;
- a prospective Human decision was frozen on 2026-09-03;
- the Human chose a CNY350 assumption-review checkpoint and a conditional CNY320–335 first-entry band.

The correct causal statement remained limited:

```text
price dislocation existed
+ later Research / Human decision work existed
!= price dislocation caused useful Research triage
```

A separate Human checkpoint has now answered the missing usefulness question. The Human explicitly selected:

```text
A = worth alerting me; should trigger Research triage
```

Therefore the current evaluation state is now:

```text
603986 SURPRISE RADAR POSITIVE CONTROL = YES / EARNED BY HUMAN TRIAGE
```

The historical pre-label state is preserved here rather than rewritten away.

### 300750 / CATL

Mechanical state:

```text
SUSTAINED REPRICING CANDIDATE = YES
20d return ~= -9.9%
max drawdown ~= -14.0%
```

The existing CATL Commitment Radar positive control is based on exact disclosure-to-frozen-commitment lineage, not this price path. Keep the two experiments separate.

The 2026-09-03 buyback-progress disclosure does not by itself explain the multi-week price path and must not be used as retrospective attribution.

### Other four windows

Current disposition:

```text
002050 / 600519 / 601088 / 600036
= CONTEXT WINDOWS / UNLABELED
```

They are not promoted as negative controls merely because their paths look quieter. A useful negative control requires a sufficiently large mechanical observation that a Human later judges should have remained `IGNORE`.

## What this review proves

```text
REAL SCHEDULED SHADOW BATCH = YES
SIX QUALIFIED WINDOWS = YES
ARTIFACT RETENTION / REPLAY IDENTITY = YES
MECHANICALLY DISTINCT PATHS = YES
FIRST HUMAN-LABELED POSITIVE CONTROL = YES / 603986
NEGATIVE CONTROL = NOT YET
FALSE-NEGATIVE CONTROL = NOT YET
DETECTOR THRESHOLD = NOT JUSTIFIED
RADAR SCORE = NO
HUMAN WAKE CHANGE = NO
KERNEL CHANGE = NO
```

## Next evidence

Do not tune a threshold from this batch.

Next useful step:

1. let another scheduled batch arrive naturally;
2. compare whether GigaDevice / CATL-style paths persist, reverse, or resolve;
3. earn at least one mechanically meaningful `IGNORE` example from Human triage;
4. identify one plausible false-negative candidate from a quieter path followed by decision-relevant evidence;
5. only then test a simple explainable shadow rule against the small reviewed corpus.

## Disposition

```text
FIRST REAL SHADOW REVIEW = COMPLETE
603986 = FIRST HUMAN-LABELED POSITIVE CONTROL
300750 = SUSTAINED-REPRICING CANDIDATE / UNLABELED
NEGATIVE CONTROL = NOT YET
FALSE-NEGATIVE CONTROL = NOT YET
DETECTOR DESIGN = WAIT
CURRENT PROJECT PRIORITY = CONTINUE REAL-WINDOW ACCUMULATION + HUMAN TRIAGE
```
