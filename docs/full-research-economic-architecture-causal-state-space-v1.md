# Full Research — Economic Architecture & Causal State Space v1

Status: **HUMAN-APPROVED PROCESS DISCIPLINE / CURRENT GENERIC FULL-RESEARCH METHOD LAYER / NO SCHEMA OR RUNTIME CHANGE**  
Date: 2026-09-14  
Scope: decision-use Full Research before valuation, Odds, first-entry review, publication compression, or Human-facing investment judgment.  
Investment Authority: **NONE**

## 0. Precedence and role

This document is the current generic modeling layer for Full Research in Decision Kernel.

It does not replace `docs/RESEARCH-ENTRY.md`, Kernel validators, source identity controls, PIT rules, Odds semantics, or Human authority. It sits between source/evidence preparation and valuation/Odds:

```text
Data / Sources
→ Evidence
→ Economic Architecture
→ Causal State Space
→ Owner Economics
→ Valuation / Price-Implied Requirements
→ Odds
→ Human Judgment / Decision
```

The earlier `docs/readings/transition-company-full-research-lessons-2026-09-14.md` is preserved as a historical origin-case / special-case predecessor. Its transition-company lessons remain useful when relevant, but they do not define the general method.

Core rule:

> **Do not start from a neat scenario table. Start from the economic system that can generate the scenarios.**

A numerically consistent model can still be wrong if its reference frame, causal axes, cash economics, competitive state, or valuation bridge are incomplete.

## 1. First define the economic architecture

Before constructing Bull / Base / Bear, identify the economic engines that actually create or destroy owner value.

For each material engine, state at least:

- what is sold and to whom;
- unit economics and principal revenue drivers;
- gross-margin / contribution-margin drivers;
- fixed-cost and utilization sensitivity;
- working-capital requirements;
- maintenance and growth capex;
- capital employed and incremental return on capital;
- cash conversion and financing dependence;
- what can structurally improve or deteriorate it.

Do not assume the accounting segment structure is the correct economic structure. A segment may need to be split when different products have different demand, price, capital intensity, or competitive dynamics. Conversely, several reported segments may share one economic engine.

Minimum output is an **Economic Architecture Map**, not necessarily a new schema. Markdown is sufficient.

A useful representation is:

```text
Economic engine
→ volume / price / mix
→ gross economics
→ operating cost
→ working capital / capex
→ owner cash
→ reinvestment opportunity
→ durability / decay
```

Hard failure:

> Revenue categories are copied into a scenario table without showing how they become owner economics.

## 2. Identify independent causal axes before joint worlds

Do not let one label such as `Bull`, `Base`, `Bear`, `legacy weak`, `AI strong`, or `cycle recovery` carry several unrelated assumptions.

Build a small set of load-bearing causal axes first. Typical axes include:

- end-demand / industry volume;
- price / ASP / take rate;
- market share / customer penetration;
- utilization / yield / operating leverage;
- raw-material or input cost;
- product mix;
- competitive intensity / supply response;
- reinvestment requirement / capital allocation;
- financing / dilution;
- regulation / policy;
- evidence-integrity / governance state;
- new-business commercialization;
- legacy-business decay or repair.

Only use axes that matter for the case. Usually 3–5 load-bearing variables are enough.

For each axis record:

```text
current state
supporting evidence
counterevidence
causal mechanism
time lag
leading indicators
failure condition
what remains UNKNOWN
```

This prevents a common failure:

```text
strong demand
→ higher revenue
→ higher margin
→ higher market share
→ higher P/E
```

when only the first link is evidenced.

## 3. Mechanism must be explicit, not just correlation

A research claim should explain **how** evidence changes the economic state.

For each load-bearing driver, ask:

- What physical, contractual, behavioral, or financial mechanism connects the evidence to revenue, margin, cash, or duration?
- What has to happen in between?
- What is the likely lag?
- What observation would show the mechanism is failing?
- Is the evidence about capability, intent, order, shipment, revenue, margin, cash collection, or durable economics?

Preserve proof ladders. Examples:

```text
capacity
!= utilization
!= shipment
!= revenue
!= margin
!= cash
!= acceptable ROIC
```

```text
customer certification
!= repeat order
!= material order
!= stable share
!= durable pricing power
```

```text
industry growth
!= company growth
!= company value capture
```

If the bridge is missing, mark it `NOT ESTABLISHED` rather than filling it with narrative.

## 4. Close the owner-economics chain

Full Research is not complete at net profit.

For material worlds, close as much of this chain as evidence allows:

```text
Revenue
→ gross / contribution economics
→ operating profit
→ parent / normalized profit
→ operating cash flow
→ working-capital need
→ maintenance capex
→ growth capex
→ financing / dilution
→ owner cash
→ capital employed
→ ROIC / incremental ROIC
```

Important distinctions:

- accounting profit is not owner cash;
- growth capex is not free because it supports future revenue;
- early new-business profit may coexist with negative owner cash;
- stable revenue can coexist with declining economic value if capital intensity rises or returns fall;
- small position size reduces portfolio exposure, not business risk or valuation error;
- equity issuance can fund growth while reducing per-share economics;
- acquisitions can create accounting growth while destroying incremental ROIC.

When exact owner cash cannot be established, use bounded ranges and identify the missing bridge.

## 5. Add cycle and competition as causal state, not background color

This is a current weak area that must be strengthened systematically.

For businesses where cycle or competition is material, explicitly distinguish:

```text
company-specific improvement
vs
industry-cycle improvement
vs
market-expression rerating
```

At minimum inspect whichever are relevant:

- demand cycle and order lead times;
- channel / customer inventory;
- capacity additions and supply response;
- utilization and fixed-cost absorption;
- cost curve / marginal producer;
- price elasticity and switching cost;
- customer concentration and bargaining power;
- competitor capex and price behavior;
- substitute technology / product migration;
- regulatory or subsidy dependence;
- whether current margin is above, below, or near a plausible through-cycle level.

Do not call a cyclical peak a structural margin without a duration bridge. Do not call a cyclical trough permanent impairment without a mechanism.

Where a reference class exists, use outside-view history to bound feasible cycle states. Do not transfer peer success probability to the target company.

## 6. Construct the causal state space

Only after the axes are explicit should joint worlds be built.

The goal is not to create many scenarios. It is to avoid missing economically plausible combinations.

Required discipline:

- test anti-diagonal worlds when axes are partly independent;
- separate correlated assumptions from independent assumptions;
- include at least one world that breaks the preferred narrative;
- include meaningful downside, not only the comfortable end of a downside band;
- do not force every variable to be low in Bear and high in Bull;
- do not assign probabilities merely because a table has rows.

Example:

```text
Axis A: demand weak / normal / strong
Axis B: share loss / stable / gain
Axis C: margin compression / stable / expansion
Axis D: reinvestment heavy / normal / light
```

A useful world can be:

```text
demand strong + share stable + margin compresses + capex rises
```

which a diagonal Bull/Base/Bear table often omits.

If the axes cannot be reasonably bounded, the correct output is `BOUNDED CONDITIONAL REQUIREMENTS`, not a fabricated probability distribution.

## 7. Counterfactual and falsification are mandatory

This is another weak area that should be strengthened.

For every central thesis, write at least one serious counterfactual:

> If the thesis is wrong, what else could generate the observations we currently see?

Then identify evidence that would distinguish the competing explanations.

Examples:

- revenue growth from channel inventory rather than end-demand;
- margin improvement from temporary raw-material relief rather than pricing power;
- order growth from one customer rather than broad adoption;
- high ROE from leverage rather than better business returns;
- apparent share gain from competitor disruption rather than durable advantage;
- high market multiple from style / liquidity / scarcity rather than superior owner economics.

A thesis is stronger when it survives plausible alternative explanations, not when more supporting facts are collected.

Do not invent the reason an observation occurred. If the discriminator is unavailable, preserve `UNKNOWN` and define the next evidence that could resolve it.

## 8. Independent business underwriting comes before market expectation comparison

Preserve a pre-market-comparison operating view before reading consensus or price-implied requirements aggressively.

Then compare against:

- sell-side / external expectations;
- peer economics;
- current price-implied requirements;
- historical or cross-market expression where relevant.

The comparison can revise Belief only when the new material is Evidence or a legitimate reinterpretation. Price by itself changes Odds, not Belief.

Do not infer a unique market belief from price. A price can be consistent with many combinations of earnings, duration, risk premium, liquidity, and optionality.

Use price inversion to answer:

> **What would need to be true for this price to deliver the required return?**

not:

> **What exactly does the market believe?**

unless the belief is directly evidenced.

## 9. Valuation must be a second causal bridge

Profit and valuation are separate claims.

For any higher terminal multiple, lower discount rate, or longer duration assumption, separately support why the horizon business should have:

- longer remaining growth duration;
- attractive incremental ROIC;
- durable competitive advantage / customer stickiness;
- better cash conversion;
- lower capital intensity;
- lower business / governance risk;
- or an explicitly separated market-expression premium.

Never allow one success label to do both jobs silently:

```text
new business succeeds
→ profit rises
→ P/E rises
```

The second arrow needs its own evidence and mechanism.

Run off-diagonal valuation stress:

- better operations + multiple compression;
- ordinary operations + premium multiple persists;
- strong accounting profit + weak cash conversion;
- strong growth + heavy reinvestment / dilution.

Numerical coincidence between two models does not validate either model.

## 10. Probability and Odds qualification

A causal state-space table is not automatically a probability model.

Use cardinal probabilities only when there is a defensible calibration basis such as a relevant reference class, repeated measurable process, or otherwise auditable probability basis.

If not, use:

```text
CARDINAL PROBABILITY = NOT ESTABLISHED
```

and provide ordinal / conditional judgment instead.

When Belief is frozen and only a qualified market price changes, recomputing return requirements or Odds should not silently alter the economic model.

When new Evidence changes the economic state, reopen Research first; do not label it a price-only Odds refresh.

## 11. Minimum decision-use Full Research packet

A Full Research result is method-ready only when the following are either established or explicitly marked bounded / unknown:

1. **Reference Frame** — what economic problem is being answered, for what security and horizon.
2. **Economic Architecture Map** — the material engines of owner value.
3. **Causal Driver Register** — the few independent axes that determine the case.
4. **Mechanism / Proof Ladders** — how evidence reaches economics and where it stops.
5. **Owner-Economics Closure** — profit, cash, capital, reinvestment, financing and per-share consequences.
6. **Cycle / Competition State** — when material, separate company alpha from industry beta and market rerating.
7. **Causal State Space** — include anti-diagonal and narrative-breaking worlds where plausible.
8. **Counterfactual / Falsification** — strongest alternative explanation and discriminating evidence.
9. **Valuation Bridge** — independently underwritten from profit.
10. **Price-Implied Requirements** — what must be true for the observed / candidate price to work.
11. **Uncertainty / Reopen Conditions** — decisive UNKNOWNs, STOP reasons and future evidence triggers.
12. **Odds Qualification** — cardinal, ordinal, provisional, canonical, or NOT ESTABLISHED as appropriate.

A polished report that lacks one or more load-bearing items above is not automatically Full Research.

## 12. Strengthening rules for current weak areas

The following are explicit reinforcements, not new runtime machinery:

### Mechanism quality

Prefer fewer claims with full causal bridges over many facts with weak linkage. Every load-bearing claim should identify the mechanism, intermediate steps and a failure indicator.

### Owner economics

Prioritize incremental ROIC, reinvestment need, owner cash and per-share consequences. Net profit alone is insufficient when capital intensity, M&A, dilution or working capital is material.

### Cycle and competition

Separate structural improvement from cycle recovery. Use capacity, inventory, pricing, utilization and competitor behavior to locate the economic state.

### Valuation bridge

Underwrite duration and returns independently from near-term profit. Never use current market multiple as self-justification.

### Counterevidence

Search deliberately for the strongest plausible disconfirming explanation. Research quality is not the count of supporting citations.

### Probability discipline

Use base rates only when the reference class is genuinely comparable. Otherwise keep uncertainty ordinal or bounded. Do not manufacture precision to make Odds look complete.

## 13. Review outcomes

After applying this method and the existing Review Gate, a decision-use result should land in one of:

```text
PASS
BOUNDED / DECISION-USEFUL WITH EXPLICIT RANGE
RESEARCH CHALLENGE — REUNDERWRITE
NOT METHOD-READY — WITHHOLD NUMERICAL VALUATION / ODDS
```

`PASS` means the reasoning chain is explicit and auditable for its stated use. It does not mean the thesis is true.

## 14. What this document does not do

This document does not create:

- a new Kernel schema;
- a generic scenario engine;
- mandatory Monte Carlo;
- a universal valuation model;
- an agent / DAG / provider framework;
- automatic research continuation;
- automatic Odds or trading authority.

It is a method layer only. Requirements Management owns requirement definition and prioritization. Main Construction owns runtime implementation.

Core reusable lesson:

> **Economic architecture first. Causal state space second. Owner economics third. Valuation and Odds come after.**
