# Surprise Radar v0 — GigaDevice Counterfactual Human Triage Checkpoint

Status: **HUMAN COUNTERFACTUAL TRIAGE / CONTROL PROMOTION RETRACTED / PRE-RESEARCH WINDOW / ALERT-POLICY PROBE / NO DETECTOR / NO INVESTMENT AUTHORITY**  
Date: **2026-09-04**  
Security: **兆易创新 / GigaDevice / 603986.SH**

## Correction

This checkpoint originally promoted GigaDevice's 2026-07-21 → 2026-08-03 price dislocation as the first Human-labeled Surprise Radar positive control.

That promotion was methodologically invalid for the current Surprise Radar v0 semantics.

The current shadow design binds each observation to an exact frozen `ResearchSnapshot` id / as-of / information-bundle hash. Therefore a historical window can qualify as an actual Radar observation only if the relevant frozen Research already existed **before the anomaly being evaluated**.

Repository history shows:

```text
GigaDevice first Full Research package commit
= 1174a0b22e3aa4322db7451fc0862905b9662a08
= 2026-09-02 09:37:02 +08:00

candidate anomaly window
= 2026-07-21 → 2026-08-03
```

Therefore:

```text
PRE-ANOMALY FROZEN RESEARCH = NO
SURPRISE RADAR v0 OBSERVATION = INELIGIBLE / PRE-RESEARCH
POSITIVE-CONTROL PROMOTION = RETRACTED
```

## What remains valid

The mechanical history remains a useful retrospective price-path example:

```text
2026-07-21 close = CNY475.53
2026-08-03 close = CNY340.74
window max drawdown ~= -28.3%
largest down day ~= -10.0%
2026-09-03 close = CNY383.20
```

The Human was first asked the counterfactual question:

```text
If Radar had surfaced this anomaly at the time,
would it have been worth alerting me and triggering Research triage?
```

Human response:

```text
A = worth alerting me; should trigger Research triage
```

The Human then clarified the broader alert preference:

> “如果是已经做过研究的，价格异动这两个都可以提醒，除非我明确说不再关注”

The broader statement supersedes the need to treat the earlier `A` as a special per-event permission.

## Correct interpretation

For current Surprise Radar v0:

```text
frozen ResearchSnapshot already exists
+ case remains followed
+ mechanical path qualifies as a price anomaly
→ MAY ALERT BY DEFAULT
```

Suppression requires an explicit Human opt-out that the case is no longer followed / no longer of interest.

Therefore the GigaDevice answer is best preserved as a **counterfactual policy probe**:

```text
IF prior frozen Research had existed
AND GigaDevice remained followed
AND this path qualified mechanically as an anomaly
THEN alerting would have been acceptable / useful.
```

It does not backdate Radar eligibility and does not create a valid historical control.

## Consequence for evaluation

The primary experiment is no longer:

```text
each anomaly → ask Human A/B/C whether alert was wanted
```

For active researched cases, alert permission is already specified by the Human preference.

The remaining experiment is mechanical signal quality:

```text
what qualifies as a price anomaly?
what is ordinary noise?
what meaningful later evidence was preceded by a quieter path and could become a false-negative candidate?
```

Natural post-Research windows are required before testing a detector.

## Authority boundary

```text
DEFAULT ALERT FOR FOLLOWED RESEARCHED CASE + QUALIFIED ANOMALY = MAY ALERT
EXPLICIT HUMAN NO-LONGER-FOLLOWING = SUPPRESS
AUTOMATIC RESEARCH REOPEN = NO
FUNDAMENTAL BELIEF CHANGE FROM PRICE = NO
RADAR SCORE = NO
DETECTOR THRESHOLD = NO
KERNEL SCHEMA CHANGE = NO
INVESTMENT AUTHORITY = NONE
```

## Disposition

```text
GIGADEVICE POSITIVE-CONTROL PROMOTION = RETRACTED
HUMAN RESPONSE A = PRESERVED AS COUNTERFACTUAL POLICY PROBE
PER-ANOMALY ALERT PERMISSION LABELING = NOT REQUIRED FOR ACTIVE FOLLOWED CASES
NEXT = ACCUMULATE ELIGIBLE POST-RESEARCH WINDOWS + CALIBRATE QUALIFIED PRICE ANOMALY / FALSE-NEGATIVE BEHAVIOR
```
