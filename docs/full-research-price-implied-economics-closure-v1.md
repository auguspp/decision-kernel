# Full Research Price-Implied Economics Closure v1

Status: **PROCESS-GATE EXTENSION / REAL-FAILURE-DERIVED / NO NEW RESEARCH SCHEMA**  
Parent gate: `docs/full-research-review-gate-v1.md` — Gate 6  
Investment Authority: **NONE**

## Why this exists

The Sanhua dogfood exposed a second failure after the first valuation repair.

Research had already done this correctly:

```text
observed price
→ normalized observable business economics
→ independently underwritten valuation
→ residual value above the observable base
```

But that was still not enough to answer the actual valuation question.

A residual such as `CNY50bn of future / optionality value` is only an intermediate result. If that residual is material to the conclusion, Research must ask what future economics could justify it and, where possible, translate those economics back into the same unit as the observed price.

This note turns that failure into a reusable extension of Gate 6.

## Core rule

A price reverse-underwriting is not closed merely because a residual has been isolated.

When the residual is load-bearing, continue the chain:

```text
observed price
→ supported observable-base value
→ residual price / value
→ future economics required by the residual
→ operational requirements that produce those economics, when supportable
→ future economics translated back into today's price / value
```

The purpose is to explain **what the current price requires**, not to generate a target price.

## 1. Start from a clean observable base

Before assigning optionality, state what is already inside the base.

The base may include economics that are commercially real but not separately disclosed. A segment labelled `refrigeration`, `cloud`, `software`, or another broad category can already contain part of a newer business.

Therefore:

```text
observable base
!=
automatically pure legacy business
```

If a future business is already partly embedded in reported or normalized base economics, only its **incremental future economics above that base** may enter the residual bridge.

Hard failure:

```text
base already contains part of Business X
+
full Business X option value added again
```

## 2. A residual is one bill, not several free option buckets

Use the identity:

```text
residual
=
extra duration / quality value
+ incremental future-business value
+ other asset / SOTP value
+ market-expression premium
```

The pieces share one residual.

Never do this without an explicit subtraction / reconciliation:

```text
residual
+ full robot value
+ full liquid-cooling value
+ higher core multiple
```

If one success-state scenario already consumes most of the residual, other narratives cannot be added as if the residual were still untouched.

## 3. Reverse residual value into future economics

When future operating economics are supposed to justify a material residual, make the bridge explicit.

Typical inputs are:

```text
future earnings / owner earnings
× mature valuation at the future horizon
× discount factor back to the observation date
=
present value of future economics
```

All load-bearing inputs must be declared:

- future horizon;
- mature valuation method / multiple;
- required return / discount rate where used;
- future profit / cash-flow definition;
- share count or other unit conversion.

Do not hide these inside a neat residual calculation.

If they cannot be independently supported even as a bounded challenger sensitivity, leave the valuation `NOT METHOD-READY` rather than inventing a point estimate.

## 4. Convert economic requirements into operating requirements when possible

A future-profit number is often still too abstract.

If the causal bridge is supportable, continue into operating variables:

```text
industry / customer volume
× company share
× unit economics / ASP
× margin
→ revenue / profit
→ present value
→ price
```

or the case-appropriate equivalent.

This is useful because it exposes simultaneous assumptions.

For example, a future-profit scenario may quietly require all of these at once:

- very high industry volume;
- high company share;
- high unit value;
- stable margin;
- sufficient capacity utilization;
- acceptable capital intensity.

The operating bridge must follow the proof ladder. A capacity target or customer ambition is not an achieved volume forecast.

## 5. Scenario anchors are not expected values

A sell-side or management success-state can be useful for scale comparison.

Label it correctly:

```text
SUCCESS-STATE REFERENCE
MARKET-CONTEXT SCENARIO
ASSUMPTION
```

not:

```text
EXPECTED EARNINGS
CANONICAL FORECAST
PROBABILITY-WEIGHTED VALUE
```

A scenario showing that `full success ≈ current residual` means the current price is asking for economics on roughly that scale under the stated assumptions.

It does **not** prove the scenario will occur.

## 6. Do not invent probability to finish the bridge

If cardinal probability is not established, do not repair the gap by assigning an arbitrary success probability.

A binary shortcut such as:

```text
success-state value × 50%
```

is not valid merely because it produces a convenient expected value.

The downside may have non-zero value, the upside may have multiple states, and other businesses may share the residual.

Allowed output:

```text
PRICE-IMPLIED REQUIREMENT = ESTABLISHED / BOUNDED
CARDINAL SUCCESS PROBABILITY = NOT ESTABLISHED
NUMERICAL ODDS = WITHHOLD
```

Conditional sensitivities are allowed when clearly labelled as conditions rather than beliefs.

## 7. Close back to the observation unit

If the research question starts with a quoted share price, finish in share-price terms when the evidence supports it.

Preferred chain:

```text
CNY X/share observed
→ CNY Y/share observable-base value
→ CNY Z/share residual
→ required future profit / cash flow
→ present value/share of that future economics
→ compare back with CNY X/share
```

For a market-cap, EV, NAV, or asset-value question, close in that corresponding unit.

**Unit closure is part of auditability.** Do not leave the Human to mentally convert tens of billions of residual value back into the question they asked.

## 8. Required review questions

For a material price-implied optionality / future-growth component, Gate 6 is incomplete until the reviewer can answer:

1. What is already inside the observable base?
2. What is the residual in both enterprise/equity value and the user-facing unit where useful?
3. Which distinct economic claims share that residual?
4. What future owner earnings / profit / cash flow would be required to justify the operating portion of the residual?
5. What timing and valuation assumptions connect that future economics to today?
6. Can the future economics be translated into operating requirements such as volume, share, ASP, margin or ROIC without jumping the proof ladder?
7. Does a cited success-state represent a scenario or an expected value?
8. Is any business, optionality or duration premium being counted twice?
9. Does the analysis return to the observed price / value before declaring the valuation question closed?
10. If probability is not established, is it visibly withheld rather than fabricated?

## 9. Research-challenge states

Use a Research Challenge rather than polishing through any of these:

- `BASE_SCOPE_AMBIGUOUS` — current economics already contain an unknown amount of the supposed option;
- `RESIDUAL_UNRECONCILED` — multiple narratives are being added to one residual without reconciliation;
- `FUTURE_ECONOMICS_BRIDGE_MISSING` — residual is material but no supported path links it to future owner economics;
- `OPERATING_BRIDGE_UNSUPPORTED` — profit is reverse-engineered into volume/share/margin using unsupported assumptions;
- `SUCCESS_STATE_UPGRADED_TO_EXPECTATION` — a scenario anchor is treated as expected earnings;
- `PROBABILITY_INVENTED_FOR_CLOSURE` — an arbitrary probability is introduced only to finish the model;
- `UNIT_CLOSURE_INCOMPLETE` — the final analysis never returns to the unit of the observed price/value question;
- `OPTIONALITY_DOUBLE_COUNT_RISK` — the same future economics appear in the base, profit scenario, valuation multiple, or separate option more than once.

## 10. Output states

A price-implied economics analysis may end as:

```text
CLOSED / BOUNDED REQUIREMENT SURFACE
RESEARCH CHALLENGE — REUNDERWRITE
NOT METHOD-READY
```

`CLOSED` means the current price requirement is explicit and auditable under stated assumptions.

It does **not** mean the price is fair, the scenario is probable, or an investment action is warranted.

## Sanhua earned example — not reusable constants

The Sanhua case that earned this method is documented in:

`docs/dogfood/sanhua-optionality-reverse-underwriting-2026-09-03.md`

The case-specific numbers, multiples, discount rate and robot-unit assumptions must not be copied into another company.

What is reusable is only the method:

```text
base
→ residual
→ required future economics
→ operating bridge
→ discounted value
→ observed-price closure
```

## Stop rule

Do not turn this into a generic option-pricing engine, probability engine, or target-price framework.

Use the method when a real case contains a material residual / future-growth component. Record future failures and only add machinery when repeated evidence earns it.
