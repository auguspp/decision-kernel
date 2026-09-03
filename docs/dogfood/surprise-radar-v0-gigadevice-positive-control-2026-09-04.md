# Surprise Radar v0 — GigaDevice Counterfactual Human Triage Checkpoint

Status: **HUMAN COUNTERFACTUAL TRIAGE / CONTROL PROMOTION RETRACTED / PRE-RESEARCH WINDOW / NO DETECTOR / NO HUMAN-WAKE CHANGE / NO INVESTMENT AUTHORITY**  
Date: **2026-09-04**  
Security: **兆易创新 / GigaDevice / 603986.SH**

## Correction

This checkpoint originally promoted GigaDevice's 2026-07-21 → 2026-08-03 price dislocation as the first Human-labeled Surprise Radar positive control.

That promotion was methodologically invalid for the current Surprise Radar v0 semantics.

The current shadow design binds each observation to an exact frozen `ResearchSnapshot` id / as-of / information-bundle hash. Therefore a historical window can qualify as a Radar evaluation control only if the relevant frozen Research already existed **before the anomaly being evaluated**.

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
SURPRISE RADAR v0 POSITIVE CONTROL = INVALID / RETRACTED
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

The Human was asked the counterfactual question:

```text
If Radar had surfaced this anomaly at the time,
would it have been worth alerting me and triggering Research triage?
```

Human response:

```text
A = worth alerting me; should trigger Research triage
```

That answer is preserved as a **counterfactual Human usefulness judgment**.

It does not qualify the window as a Surprise Radar v0 control because the required pre-anomaly Research state did not exist.

## Correct current corpus state

```text
VALID POSITIVE CONTROL = NOT YET EARNED
VALID NEGATIVE CONTROL = NOT YET EARNED
VALID FALSE-NEGATIVE CANDIDATE = NOT YET EARNED
GIGADEVICE HISTORICAL COUNTERFACTUAL = A / TRIAGE-WORTHY IF PRIOR RESEARCH HAD EXISTED
DETECTOR DESIGN = WAIT
```

## Eligibility rule clarified

For current Surprise Radar v0 evaluation, a candidate control must satisfy:

```text
frozen ResearchSnapshot exists before candidate anomaly
+ anomaly is observed after that freeze
+ Human judges whether the anomaly should trigger Research triage
```

Without the first condition, the example belongs to a different possible experiment: **cold-start anomaly discovery**. That is not the current Surprise Radar v0 experiment and should not be silently mixed into its corpus.

## Authority boundary

```text
FUNDAMENTAL BELIEF CHANGE FROM PRICE = NO
RADAR SCORE = NO
DETECTOR THRESHOLD = NO
SECOND HUMAN WAKE GATE = NO
KERNEL CHANGE = NO
INVESTMENT AUTHORITY = NONE
```

## Disposition

```text
GIGADEVICE POSITIVE-CONTROL PROMOTION = RETRACTED
HUMAN RESPONSE A = PRESERVED AS COUNTERFACTUAL ONLY
NEXT = ACCUMULATE POST-RESEARCH NATURAL WINDOWS
```
