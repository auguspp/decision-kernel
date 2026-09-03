# Surprise Radar v0 — GigaDevice First Human-Labeled Positive Control

Status: **FROZEN HUMAN TRIAGE LABEL / SURPRISE RADAR EVALUATION CONTROL / NO DETECTOR / NO HUMAN-WAKE CHANGE / NO INVESTMENT AUTHORITY**  
Date: **2026-09-04**  
Security: **兆易创新 / GigaDevice / 603986.SH**

## Purpose

Freeze the first Human-earned Surprise Radar triage label on top of a naturally scheduled, qualified HiThink price-history observation.

This checkpoint does not infer Fundamental Belief from price and does not claim that the price path caused later Research. It records only the Human's answer to the counterfactual triage question:

> If the Radar had surfaced this price-path anomaly at the time, would it have been worth alerting the Human and triggering Research triage?

## Source observation lineage

Parent mechanical review:

`docs/dogfood/surprise-radar-v0-first-real-window-review-2026-09-04.md`

GitHub Actions source:

```text
workflow = decision-inbox
run_id = 33757562673
market-history-shadow artifact_id = 9894080655
artifact_digest = sha256:1ff066f5560982f84af004aa482af0c29be857fa85fbeb300a7bd04b463ddf16
qualified history through = 2026-09-03
```

Mechanical GigaDevice path retained by that review:

```text
2026-07-21 close = CNY475.53
2026-08-03 close = CNY340.74
window max drawdown = -28.3%
largest down day = -10.0%
2026-09-03 close = CNY383.20
```

The same review also established that no new GigaDevice official-disclosure packet appeared in that scheduled scan.

## Contemporaneous Research context

Existing frozen Research later reconstructed the relevant information boundary:

- headline H1 earnings had already been substantially preannounced on 2026-07-09;
- at least one matched sell-side house kept its earnings framework broadly unchanged while the stock repriced materially;
- the valid Research question was duration / valuation / positioning rather than a price-implies-fundamentals shortcut.

The repository's prior conclusion was deliberately limited:

```text
material price repricing
+ headline earnings already substantially known
+ at least one broadly stable matched earnings framework
→ valid duration / valuation / positioning Research question

but

price action itself
!= answer to that Research question
```

## Human triage checkpoint

The Human was shown the historical anomaly in this form:

```text
GigaDevice fell from about CNY475.53 on 2026-07-21
 to about CNY340.74 on 2026-08-03
≈ -28%
while headline H1 earnings had already been preannounced.
```

The Human was asked to choose:

```text
A = worth alerting me; should trigger Research triage
B = not worth alerting me; large move only / IGNORE
C = insufficient information to judge
```

Human response:

```text
A
```

Normalized label:

```text
HUMAN TRIAGE = DEEPEN / RESEARCH TRIAGE WORTHY
SURPRISE RADAR POSITIVE CONTROL = YES
```

This is a Human usefulness label, not a claim that buying or selling on the anomaly would have produced returns.

## What the positive label means

It means the mechanical observation would have been useful enough to earn scarce Research attention at the time.

It does **not** mean:

- the decline was caused by hidden negative fundamentals;
- the later GigaDevice thesis was caused by the Radar observation;
- the anomaly should automatically wake the Human in production;
- a 28% drawdown is the correct detector threshold;
- the largest one-day move should become a trigger;
- every comparable drawdown is Research-relevant;
- price changes Fundamental Belief;
- a trade, Recommendation, Odds change, or Action is authorized.

## Evaluation consequence

The Surprise Radar evaluation corpus now has its first earned positive example:

```text
POSITIVE CONTROL = 603986 / GigaDevice / YES
NEGATIVE CONTROL = NOT YET EARNED
FALSE-NEGATIVE CANDIDATE = NOT YET EARNED
```

One positive control is still insufficient for detector design.

Before testing even a simple explainable shadow rule, the project still needs at minimum:

1. a mechanically meaningful large move that the Human judges should remain `IGNORE`;
2. a quieter price path where later decision-relevant evidence suggests a plausible false negative;
3. another naturally scheduled batch so persistence, reversal and cross-case behavior can be compared without tuning to GigaDevice.

## Authority boundary

```text
OBSERVATION AUTHORITY = SHADOW ONLY
HUMAN TRIAGE LABEL = YES / POSITIVE CONTROL
FUNDAMENTAL BELIEF CHANGE FROM PRICE = NO
RADAR SCORE = NO
DETECTOR THRESHOLD = NO
SECOND HUMAN WAKE GATE = NO
KERNEL CHANGE = NO
INVESTMENT AUTHORITY = NONE
```

## Disposition

```text
FIRST HUMAN-LABELED SURPRISE RADAR POSITIVE CONTROL = EARNED
CASE = 603986 / GigaDevice
LABEL = RESEARCH TRIAGE WORTHY
PROMOTE DETECTOR = NO
NEXT = EARN NEGATIVE + FALSE-NEGATIVE CONTROLS FROM NATURAL WINDOWS
```
