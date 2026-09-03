# Surprise Radar v0 — Human Alert Preference Checkpoint — 2026-09-04

Status: **FROZEN HUMAN ALERT PREFERENCE / HARNESS POLICY INPUT / NO KERNEL SCHEMA CHANGE / NO INVESTMENT AUTHORITY**  
Date: **2026-09-04**

## Human statement

The Human clarified the intended alert policy:

> “如果是已经做过研究的，价格异动这两个都可以提醒，除非我明确说不再关注”

## Narrow interpretation

Preserve only what the statement authorizes:

```text
ELIGIBILITY = a frozen ResearchSnapshot already exists before the price anomaly
DEFAULT HUMAN ALERT PREFERENCE = MAY ALERT on a qualified price anomaly
SUPPRESSION = only when the Human explicitly says the case is no longer followed / no longer of interest
ALERT = attention notification only
ALERT != automatic Research reopen
ALERT != Fundamental Belief change
ALERT != Odds change
ALERT != Recommendation
ALERT != Action
ALERT != Investment Authority
```

This is a case-following preference, not a new investment-decision gate.

## Consequence for the earlier control experiment

The earlier proposal to earn a `positive control` by asking whether each researched-case anomaly should alert, and a `negative control` by finding a large move the Human would prefer to `IGNORE`, is no longer the right evaluation target for active researched cases.

For a case that remains followed:

```text
qualified post-Research price anomaly
→ MAY ALERT by default
→ Human may then triage DEEPEN / WAIT / DROP
```

The relevant opt-out is case-level and explicit:

```text
Human explicitly says no longer follow / no longer interested
→ suppress future Surprise Radar alerts for that case
```

Do not infer an opt-out from:

- no current Human investment decision;
- `WAIT`;
- `NO_ACTION`;
- Research being frozen / stopped;
- price moving away from an entry band;
- absence of recent conversation about the case.

## What still needs real-window evidence

This preference does **not** define what mechanical observation qualifies as a `price anomaly`.

The remaining Surprise Radar experiment is therefore about signal quality, not per-case permission to alert:

1. observe natural **post-Research** windows;
2. distinguish mechanically meaningful anomalies from ordinary price noise without tuning to one case;
3. look for quieter paths followed by decision-relevant evidence as false-negative candidates;
4. preserve cross-case diversity and exact ResearchSnapshot / price-source lineage;
5. only after enough natural evidence, test a simple explainable shadow rule.

A detector must still avoid turning every normal fluctuation into an alert.

## Historical probes

The 2026-07/08 GigaDevice drawdown and Sanhua's 2026-08-19 large down day both occurred before their respective ResearchSnapshot existed, so they remain ineligible as actual Surprise Radar v0 controls.

However, the Human's preference establishes the counterfactual policy answer:

```text
IF a frozen ResearchSnapshot had already existed
AND the case remained followed
AND the move qualified mechanically as a price anomaly
THEN either case could have been surfaced as an alert.
```

This does not backdate Radar eligibility or create a historical control.

## Authority boundary

```text
SURPRISE RADAR = attention allocation only
DEFAULT ALERT PREFERENCE FOR FOLLOWED RESEARCHED CASES = MAY ALERT
EXPLICIT HUMAN OPT-OUT = SUPPRESS
AUTOMATIC RESEARCH REOPEN = NO
PRICE -> FUNDAMENTAL BELIEF = NO
SECOND INVESTMENT DECISION GATE = NO
KERNEL SCHEMA CHANGE = NO
INVESTMENT AUTHORITY = NONE
```

## Disposition

```text
HUMAN ALERT PREFERENCE = FROZEN
PER-ANOMALY A/B ALERT LABELING = NO LONGER THE PRIMARY EXPERIMENT
NEGATIVE CONTROL AS "LARGE MOVE HUMAN WANTS IGNORED" = NOT REQUIRED FOR ACTIVE FOLLOWED CASES
NEXT = ACCUMULATE POST-RESEARCH WINDOWS + LEARN QUALIFIED-ANOMALY / FALSE-NEGATIVE BEHAVIOR
```
