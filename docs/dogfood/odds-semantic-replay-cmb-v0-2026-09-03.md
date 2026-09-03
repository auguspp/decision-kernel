# Odds Semantic Replay — CMB real-case control v0 — 2026-09-03

Status: **ZERO-SCHEMA DOGFOOD / REAL-CASE SEMANTIC REPLAY / NO ODDS POLICY CHANGE / NO CONSTITUTION CHANGE / NO WAKE-GATE CHANGE**

Security: **招商银行 / CMB / 600036.SH**

Primary checked-in Research package: `dogfood/600036-cmb.json`

Frozen market fixture already used by the Decision Inbox regression:

```text
market price = CNY 40.86
market timestamp = 2026-09-01 15:00 +08:00
source = HiThink fixture
```

Preserved production policy under audit: `decision-os-live-odds-v0.1`

Investment Authority: **NONE**

---

## 1. Purpose

`Odds Validity Audit v0` established a generic failure mode:

> fixed cumulative-return thresholds do not preserve the same economic meaning across 180–730 day horizons.

This follow-up asks a narrower question using a real checked-in case that previously passed the production-style Odds path:

> If the exact same CMB Research worlds, probabilities and observed price are replayed under several candidate time semantics, what actually changes?

The goal is **not** to select a replacement policy.

The goal is to collapse fake alternatives, expose new failure modes, and identify what evidence would be needed before changing live Odds.

---

## 2. Real-case control inputs

The checked-in CMB package freezes these scenario terminal values and probabilities:

| World | Probability | Terminal value / share |
| --- | ---: | ---: |
| downside | 25% | CNY 39.00 |
| base | 50% | CNY 55.10 |
| upside | 25% | CNY 73.60 |

At the frozen CNY 40.86 market fixture:

```text
probability-weighted terminal payoff = CNY 55.70
expected cumulative holding-period return = 36.3191%
positive-return probability = 75%
model risk = HIGH
```

The preserved policy therefore applies a +7 percentage-point model-risk addon:

```text
ACCEPTABLE required cumulative return = 27%
ATTRACTIVE required cumulative return = 42%
EXCEPTIONAL required cumulative return = 62%
```

The real holding period is 363 days, from the frozen market date to the Research valuation horizon.

Current production-style classification:

```text
CMB @ CNY 40.86
363 days
36.32% expected cumulative return
75% positive-return probability
→ ACCEPTABLE_ODDS
```

This is the real-case convergence control.

---

## 3. Candidate semantics under replay

Four audit-only semantics are compared.

### A. Preserved cumulative policy

This is current behavior:

```text
expected cumulative return
vs
fixed cumulative return thresholds
```

Holding-period days are range-validated but do not transform the hurdle.

### B. Annualized / CAGR-style comparison

Audit-only transformation:

```text
annualized return = (1 + cumulative return)^(365 / holding_days) - 1
```

The existing adjusted thresholds are treated as one-year annual hurdle rates only for comparison.

This is **not** a proposal to change production Odds.

### C. Horizon-normalized cumulative hurdle

Instead of annualizing the realized opportunity, transform the hurdle into the case horizon:

```text
required cumulative return
= (1 + annual hurdle)^(holding_days / 365) - 1
```

For a terminal-only payoff this is algebraically equivalent to B.

### D. Opportunity-cost / discount-rate replay

Treat each adjusted annual hurdle as a required discount rate and ask whether the probability-weighted terminal payoff discounted back to the market date still covers the current price.

For a terminal-only payoff with no separately dated distributions, this is also algebraically equivalent to B/C.

That collapse is itself an important result:

> **CAGR and discount-rate semantics are not meaningfully separate candidates for terminal-only Odds.**

They become distinct only when timing of interim cash flows, multiple horizons, reinvestment assumptions, or other path-dependent economics matter.

---

## 4. Real 363-day case — convergence sanity check

At the actual 363-day CMB horizon:

```text
A. current cumulative policy          → ACCEPTABLE_ODDS
B. annualized / CAGR replay           → ACCEPTABLE_ODDS
C. horizon-normalized hurdle replay   → ACCEPTABLE_ODDS
D. discount-rate replay               → ACCEPTABLE_ODDS
```

This is desirable.

A replacement time semantic should not gratuitously change a near-one-year case simply because the mathematical representation changed.

---

## 5. Same CMB payoff, only time-to-payoff changes

Now preserve:

```text
same Research worlds
same 25/50/25 probabilities
same CNY 55.70 probability-weighted terminal payoff
same CNY 40.86 market price
same HIGH model-risk judgment
same 75% positive-return probability
```

and change only the time until the same terminal payoff is received.

### At 180 days

The same 36.32% cumulative return is approximately 87.4% annualized.

```text
A. current cumulative policy          → ACCEPTABLE_ODDS
B. annualized / CAGR replay           → EXCEPTIONAL_ODDS
C. horizon-normalized hurdle replay   → EXCEPTIONAL_ODDS
D. discount-rate replay               → EXCEPTIONAL_ODDS
```

### At 730 days

The same 36.32% cumulative return is approximately 16.8% annualized.

```text
A. current cumulative policy          → ACCEPTABLE_ODDS
B. annualized / CAGR replay           → INSUFFICIENT_ODDS
C. horizon-normalized hurdle replay   → INSUFFICIENT_ODDS
D. discount-rate replay               → INSUFFICIENT_ODDS
```

This is a stronger real-case restatement of the generic v0 result:

> **The preserved cumulative classifier deliberately ignores the economic cost of time after validating that the horizon lies inside 180–730 days.**

The arithmetic is internally correct.

The semantic question is whether this is the intended meaning of `ParticipationZone` when that zone sits directly upstream of the sole Human wake gate.

---

## 6. Wake implication — same gate, different semantic input

No second wake gate is introduced here.

Under the existing product rule:

```text
INSUFFICIENT_ODDS
→ HumanResearchSurface not attention-eligible

ACCEPTABLE / ATTRACTIVE / EXCEPTIONAL
→ decision-worthy review surface may be attention-eligible
```

Therefore, for the same CMB payoff moved to a 730-day realization horizon:

```text
current cumulative policy
→ ACCEPTABLE_ODDS
→ attention path remains open

annualized / normalized / discount-rate semantics
→ INSUFFICIENT_ODDS
→ quiet path
```

That is why Odds time semantics are not merely presentation mathematics.

They can alter Human attention.

---

## 7. Horizon buckets — useful implementation idea, dangerous policy shortcut

A fourth commonly suggested implementation is to use broad horizon buckets rather than exact normalization.

This dogfood includes an intentionally naive nearest-anchor proxy using:

```text
180d / 365d / 730d
```

The proxy is **not proposed policy**.

It demonstrates a new failure mode:

```text
same CMB economics at 272 days → EXCEPTIONAL_ODDS
same CMB economics at 273 days → ACCEPTABLE_ODDS
```

The one-day discontinuity occurs only because the case crosses the arbitrary nearest-anchor boundary.

Therefore:

> **Horizon buckets may be operationally simple, but they add boundary semantics that themselves need evidence and policy justification.**

A bucket scheme should not be adopted merely because fixed cumulative hurdles are flawed.

---

## 8. What this replay establishes

```text
REAL NEAR-ONE-YEAR CONTROL CONVERGES                    YES
CURRENT CUMULATIVE POLICY IS INTERNALLY DETERMINISTIC   YES
CURRENT POLICY TIME SEMANTICS ARE ECONOMICALLY NEUTRAL  NO
ANNUALIZED AND NORMALIZED HURDLES DIVERGE FROM CURRENT  YES
CAGR VS DISCOUNT-RATE ARE DISTINCT HERE                 NO
NAIVE HORIZON BUCKETS ADD DISCONTINUITIES               YES
WAKE IMPLICATION CAN CHANGE                              YES
```

The most useful narrowing is:

> The real design choice is not a four-way contest between cumulative / CAGR / normalized hurdle / discount rate.
>
> For terminal-only Odds, the latter three collapse into one **time-normalized opportunity-cost family**.

The meaningful unresolved choice is therefore closer to:

```text
fixed cumulative hurdle across 180–730d
vs
time-normalized opportunity-cost semantics
```

with a separate future question about how to handle dated distributions and path-dependent cash flows.

---

## 9. What this does NOT authorize

This replay does **not** authorize:

- changing `decision-os-live-odds-v0.1`;
- adding an annualized-return field to Kernel schema;
- adding a discount-rate engine;
- adding horizon buckets;
- changing ParticipationZone thresholds;
- changing ModelRisk or OddsContext addon constants;
- changing the sole Human wake gate;
- reopening frozen historical Human Decisions;
- treating CMB as a current Recommendation or Action candidate.

The CMB Research itself remains a dogfood artifact with illustrative valuation assumptions.

---

## 10. Next evidence required before policy change

One real near-one-year control is not enough to select a replacement policy.

The next useful evidence should come from at least one of these:

1. a real case with materially shorter or longer legitimate valuation horizon;
2. a case with separately dated distributions, where CAGR and discount-rate treatment no longer trivially collapse;
3. prospective Human Decision / Outcome evidence showing whether time-normalized versus cumulative classification better matched actual decision usefulness;
4. a cross-case replay showing that any candidate improves semantic consistency without creating noisy wake churn.

Until then:

```text
ODDS VALIDITY FAILURE MODE = REAL
REAL-CASE REPLAY = SUPPORTIVE
REPLACEMENT POLICY = NOT ESTABLISHED
POLICY CHANGE = NOT AUTHORIZED
```
