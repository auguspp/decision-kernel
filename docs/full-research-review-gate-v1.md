# Full Research Review Gate v1

Status: **PROCESS GATE / REAL-FAILURE-DERIVED / NO NEW RESEARCH SCHEMA**  
Scope: decision-use Full Research before a valuation surface, numerical Odds, or Human-facing participation context is treated as supported.  
Investment Authority: **NONE**

## Why this exists

The Sanhua dogfood exposed a real failure mode: operating evidence and earnings scenarios had been researched more carefully than the terminal valuation multiples applied to them. The resulting surface looked internally coherent while mixing business duration, optionality, and market-expression premium.

This gate turns that failure into reusable discipline.

It does **not** require every case to use P/E, SOTP, DCF, or any other fixed valuation method. It requires the chosen valuation bridge to be underwritten with the same epistemic discipline as the earnings bridge.

## Core rule

```text
Research is not complete merely because the business story is complete.

owner earnings
+ duration / reinvestment economics
+ valuation bridge
+ current-price requirements

must each be independently supportable.
```

Unknown is an allowed output.

```text
NOT ESTABLISHED
NOT METHOD-READY
BOUNDED ONLY
```

are preferable to a guessed point estimate.

## Gate 1 — Earnings scope is explicit

Before valuing an earnings number, state exactly what it contains.

Required questions:

- Is the number reported, normalized, sell-side total-company, pure core, or a scenario assumption?
- Does it already include emerging businesses, cyclical normalization, acquisitions, FX normalization, or other optionality?
- If consensus is used, what business assumptions are embedded in that consensus?
- If a `core + optionality` decomposition is used, has optionality already entered the core earnings anchor?

Hard failure:

> A total-company forecast that already contains an emerging-business contribution is labelled `core`, then the emerging business is valued again separately.

## Gate 2 — The valuation method is independently underwritten

A multiple or discount rate is not allowed merely because it looks familiar or matches the current market.

For a material valuation input, use whichever lenses are actually relevant, normally at least two independent lenses and preferably three:

1. direct / mature economic comparables;
2. premium / higher-quality comparables, with the quality difference named;
3. same-company historical or cross-market expression where available;
4. fundamental return / growth / reinvestment sanity check;
5. asset / replacement / SOTP / cash-flow lens when more appropriate than a multiple.

The output may be a range.

A point value requires more evidence than a range.

Hard failure:

> `25x`, `30x`, `WACC 8%`, or another load-bearing input appears in the model without an explicit economic bridge explaining why the business deserves it.

## Gate 3 — Profit level and valuation duration are not double counted

For every upside/downside world, ask whether the same driver changes both earnings and the valuation input.

That can be legitimate, but only when two separate claims are supported:

```text
Driver A
→ higher owner earnings

and independently

Driver A
→ longer growth duration / better reinvestment returns / lower business risk
→ higher justified valuation
```

If the second bridge is absent, do not automatically raise the multiple merely because earnings rose.

Typical failure:

```text
new business succeeds
→ profit rises
→ P/E also rises
```

with no evidence that the success changes long-run duration or returns.

## Gate 4 — Business value and market expression are separated

Observed market multiples contain more than business economics.

They can include:

- liquidity;
- investor base;
- listing venue;
- market risk appetite;
- style / factor regime;
- scarcity premium;
- technical participation context.

When the same business has different market expressions — for example A/H shares — use that divergence as a category check.

Do not silently import a venue premium into `Fundamental Belief`, then apply another market-regime overlay later.

Hard failure:

> A multiple is adjusted because of broad-market conditions while still being described as a pure company-fundamental input.

## Gate 5 — Uncertainty stays visible

The research surface must preserve what is actually known.

Examples:

- cardinal probability unsupported → `NOT ESTABLISHED`;
- valuation input only bounded → publish the band, not a fake center with false precision;
- emerging-business economics unknown → use a proof ladder rather than a TAM-to-profit leap;
- residual value cannot be uniquely attributed → call it residual / premium / unexplained price, not `robot value`, `AI value`, or another false decomposition.

A polished table is not evidence.

## Gate 6 — Reverse the current price

Before a valuation surface is treated as decision-useful, reverse the observed price into business requirements.

Ask:

- What earnings does this price require under the bounded valuation range?
- What duration / margin / market share / ROIC assumptions are required?
- Which assumptions must hold simultaneously?
- Which part is supported by observable core economics?
- What residual is being paid for growth, optionality, or market-expression premium?
- Is the same narrative being counted twice?

This is an adversarial check, not a recommendation engine.

A useful final sentence is often:

> At this price, the market is requiring ______ to be true.

If that blank cannot be filled without unsupported assumptions, the valuation is not finished.

## Review outcome

A reviewer should leave one of four states:

```text
PASS
BOUNDED / DECISION-USEFUL WITH EXPLICIT RANGE
RESEARCH CHALLENGE — REUNDERWRITE
NOT METHOD-READY — WITHHOLD NUMERICAL VALUATION / ODDS
```

`PASS` does not mean the investment thesis is correct. It means the valuation reasoning is sufficiently explicit and auditable for its stated use.

## Publication as an adversarial compression test

Writing is downstream from Research, but writing can expose Research defects.

A publication question forces compression:

```text
What does the price actually assume?
What is already proven?
What still has to happen?
What single assumption carries the optimistic case?
```

If a note cannot answer those questions using the frozen claims without smuggling in a guessed bridge, the correct response is **not** to make the prose smoother.

It is to open a Research challenger.

Canonical loop:

```text
Frozen Research
→ Publication compression test
→ contradiction / unsupported bridge discovered
→ Research Challenge
→ re-underwrite Research
→ freeze new Research if earned
→ rebuild PublicationBrief
```

Never:

```text
Publishing discovers a problem
→ Publishing silently edits the investment truth
```

Publishing has no authority to mutate Belief, Odds, Human Decision, or Action.

## Research-challenge triggers from writing

A writing run should stop and return to Research when it exposes any of these:

- `EARNINGS_SCOPE_AMBIGUOUS` — core versus total-company economics cannot be separated;
- `VALUATION_INPUT_UNDERWRITTEN` — the load-bearing multiple / discount rate has no independent support;
- `OPTIONALITY_DOUBLE_COUNT_RISK` — one narrative appears in both earnings and valuation without a second bridge;
- `MARKET_EXPRESSION_MIXED_WITH_FUNDAMENTALS` — venue/regime premium is being called company value;
- `PRICE_REQUIREMENT_UNEXPLAINED` — current price cannot be translated into explicit business requirements;
- `PROOF_LADDER_GAP` — capability / demand / order is being upgraded to revenue / margin / durable profit;
- `FALSE_PRECISION` — the prose requires a point estimate where Research only supports ordinal or bounded knowledge.

These are attention signals for Research. They are not automatic thesis changes.

## Stop rule

Do not turn this document into a generic valuation framework, scoring system, or schema expansion unless more real cases require it.

Use the gate on future Full Research. Record failures. Expand only when repeated observed failures earn new machinery.
