# Odds Validity Audit v0 — 2026-09-03

Status: **ZERO-SCHEMA AUDIT / CURRENT POLICY PRESERVED / NO ODDS POLICY CHANGE / NO CONSTITUTION CHANGE / NO WAKE-GATE CHANGE**

Repository baseline before this audit: `18debd569333f4d62a3557f41f8f4f09d44f82d7`.

## Question

Does the preserved `decision-os-live-odds-v0.1` participation policy retain a consistent economic meaning across its declared 180–730 day holding-period range?

This audit does **not** ask whether annualized return is automatically the correct future policy. It asks a narrower question:

> If holding period changes while the economic opportunity is held constant in a controlled way, does the current cumulative-return policy preserve the meaning of its ParticipationZone labels?

## Current policy under audit

The preserved policy uses one cumulative expected-return threshold set across the full 180–730 day range:

```text
ACCEPTABLE   20%
ATTRACTIVE   35%
EXCEPTIONAL  55%
```

with positive-return probability thresholds:

```text
55% / 65% / 75%
```

and cumulative required-return add-ons:

```text
model risk:  LOW 0 / MEDIUM +3pp / HIGH +7pp / VERY_HIGH +12pp
context:     BASELINE 0 / ELEVATED +3pp / HIGH +7pp
```

Production Odds explicitly declares:

```text
UNDISCOUNTED_NOMINAL_CUMULATIVE_PAYOFF
NOT_ANNUALIZED
```

The audit preserves all of those rules unchanged.

## Construction

`tests/test_odds_validity_audit_v0.py` builds committed counterfactual ResearchSnapshots and sends them through the real:

```text
ResearchSnapshot
→ deterministic calculation
→ build_odds_research()
→ adjusted thresholds
→ ParticipationZone
```

The positive-return probability is held at 80% in the horizon controls so the audit isolates expected-return / holding-period semantics rather than the probability gate.

No production code is changed.

## Control 1 — same cumulative return, different horizons

Hold the expected cumulative return at exactly 20% and only vary the valuation horizon.

| Holding period | Expected cumulative return | Approx annualized equivalent | Current zone |
| --- | ---: | ---: | --- |
| 180d | 20.0% | 44.73% | ACCEPTABLE_ODDS |
| 365d | 20.0% | 20.00% | ACCEPTABLE_ODDS |
| 730d | 20.0% | 9.54% | ACCEPTABLE_ODDS |

### Result

```text
SAME CURRENT ZONE = YES
SAME ECONOMIC TIME VALUE = NO
```

The current classifier is internally consistent in cumulative-return space. But the same `ACCEPTABLE_ODDS` label spans materially different rates of return once time is considered.

## Control 2 — same annualized attractiveness, different horizons

Hold annualized economic attractiveness at approximately 20% and convert it into cumulative returns appropriate to each horizon.

| Holding period | Approx cumulative return for 20% annualized | Positive-return probability | Current zone |
| --- | ---: | ---: | --- |
| 180d | 9.41% | 80% | INSUFFICIENT_ODDS |
| 365d | 20.0% | 80% | ACCEPTABLE_ODDS |
| 730d | 44.0% | 80% | ATTRACTIVE_ODDS |

### Result

```text
SAME ANNUALIZED ECONOMIC ATTRACTIVENESS = YES
SAME CURRENT ZONE = NO
```

This is the stronger counterexample.

A 20% annualized opportunity can currently be quiet at 180 days, acceptable at one year, and attractive at two years solely because the policy consumes cumulative return rather than a horizon-normalized economic measure.

Because `HumanResearchSurface` eligibility is downstream of ParticipationZone, this horizon effect is not presentation-only. Under the current decision spine it can affect whether a case reaches Human attention.

This audit does **not** authorize changing the wake gate. It establishes policy pressure on the existing same gate.

## Control 3 — fixed risk/context add-ons change economic burden with horizon

At the ACCEPTABLE threshold:

```text
LOW model risk + BASELINE context
= 20% cumulative required return

VERY_HIGH model risk + HIGH context
= 20% + 12pp + 7pp
= 39% cumulative required return
```

Annualized equivalents:

| Holding period | Base 20% cumulative | Stressed 39% cumulative | Approx annualized burden added |
| --- | ---: | ---: | ---: |
| 180d | 44.73% | 94.99% | +50.25pp |
| 730d | 9.54% | 17.90% | +8.35pp |

### Result

The same `+19pp` cumulative risk/context adjustment has a radically different annualized economic burden depending on horizon.

This does **not** prove the add-ons are wrong, nor that they must be annualized. It proves their current cardinal meaning is horizon-dependent despite being represented as fixed policy constants.

## Verdict

```text
CURRENT POLICY ARITHMETIC = DETERMINISTIC
CURRENT POLICY IMPLEMENTATION = INTERNALLY CONSISTENT
HOLDING-PERIOD RANGE ENFORCEMENT = YES
HORIZON-NORMALIZED ECONOMIC SEMANTICS = NO
PARTICIPATION-ZONE SEMANTIC INVARIANCE ACROSS HORIZONS = NO
RISK-ADDON ECONOMIC BURDEN INVARIANCE = NO

ODDS POLICY CHANGE AUTHORIZED = NO
CONSTITUTION CHANGE AUTHORIZED = NO
SECOND WAKE GATE AUTHORIZED = NO
```

The failure mode is real:

> **A deterministic cumulative-return classifier can produce ParticipationZone labels whose economic meaning changes materially with holding period.**

That matters because current Odds has attention authority downstream even though its economic policy remains explicitly v0 and non-annualized.

## What this audit does not prove

It does not prove that the future policy should use CAGR, IRR, discount rates, duration buckets, or any specific hurdle curve.

It does not calibrate the 20/35/55 thresholds against realized outcomes.

It does not test whether 55/65/75 positive-return probabilities have stable meaning across horizons.

It does not prove that the model-risk or context add-on constants should be removed.

It does not change frozen historical Odds artifacts or existing Human Decisions.

## Next evidence required before policy change

A future policy review should compare at least these candidate semantics without changing production first:

```text
A. preserved cumulative-return policy
B. horizon-bucketed cumulative hurdles
C. annualized / CAGR-style hurdle semantics
D. discount-rate / opportunity-cost semantics where cash-flow timing matters
```

The comparison should use real frozen cases where cardinal Odds were legitimately available and should inspect both:

```text
ParticipationZone stability
+ downstream Human attention consequences
```

Outcome calibration remains the strongest eventual evidence.

Until then:

> **Preserve Live Odds v0.1 as historical policy, but do not treat its ParticipationZone labels as horizon-invariant economic truth.**
