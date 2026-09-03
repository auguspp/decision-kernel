# Economic Species Underwriting Playbook v0 — 2026-09-03

Status: **DOCS-ONLY METHOD SYNTHESIS / DOGFOOD-DERIVED / NO KERNEL SCHEMA CHANGE / NO CONSTITUTION CHANGE / NO NEW WAKE GATE / NO AUTOMATION**  
Repository: `auguspp/decision-kernel`  
Recorded: **2026-09-03**

## 0. Purpose

This note is not a taxonomy for its own sake.

It exists to answer a practical Research question:

> **Given a new company, what underwriting language should be used first, and when is a Reference-Frame battle actually worth the complexity?**

The motivation comes from two opposite dogfood results:

```text
GigaDevice
-> admissible frame disagreement changed causal model class
-> changed duration / post-cycle floor / terminal economics
-> Analysis Divergence was decision-useful

Midea
-> several strategic narratives collapsed into one owner-return equation
-> most disagreement was continuous parameter sensitivity
-> Analysis Divergence added limited incremental value
```

The method implication is deliberately narrow:

> **Choose the underwriting language that matches the economic uncertainty before choosing a scenario format.**

This playbook does not create:

- an `EconomicSpecies` Kernel entity;
- a routing enum;
- a new Research lifecycle;
- a scenario mandate;
- a probability-readiness state machine;
- a recommendation engine;
- a second Human wake gate;
- numerical Odds;
- any investment authority.

It is human Research language only.

---

## 1. First question: what kind of uncertainty dominates owner economics?

Do not begin by asking:

> “How many scenarios should I create?”

Begin by asking:

> **What uncertainty most changes the economic object I am trying to value?**

Four broad uncertainty types have appeared repeatedly in current dogfood.

### A. Model-class uncertainty

Question:

> **What is this business economically?**

Examples:

- cycle rent-capture business versus structurally rebased platform;
- HQ-margin optimization versus healthy full-network economics;
- commodity/resource exposure versus integrated value-added industrial economics.

When this dominates, a Reference-Frame battle may be useful.

### B. Duration / normalization uncertainty

Question:

> **How long do unusually favorable economics last, and what survives afterward?**

Examples:

- specialty-memory scarcity;
- contracted memory-cycle floor;
- peak margins versus normalized earnings floor.

When this dominates, use duration worlds and post-cycle normalization rather than one-year target earnings.

### C. Continuous reinvestment / owner-return uncertainty

Question:

> **What return does retained capital earn, and how does it translate into per-share owner return?**

Examples:

- mature compounder;
- global brand expansion;
- B2B reinvestment pools;
- dividend / cancellation / dilution trade-offs.

When this dominates, variable underwriting is usually cleaner than dramatic discrete worlds.

### D. Evidence-ownership / network uncertainty

Question:

> **Who actually owns the reported economics, and what evidence can prove durability?**

Examples:

- franchised networks where HQ P&L differs from full-network economics;
- apparent margin gains that may be value-chain redistribution;
- earnings that do not yet translate into owner cash.

When this dominates, evidence-trigger design may be more useful than price-conditioned scenario work.

These categories can coexist. The goal is to identify the **load-bearing uncertainty**, not force every company into one box.

---

## 2. Route 1 — use Analysis Divergence only for real model-class uncertainty

### Trigger condition

Use a multi-Frame audit only when at least two admissible economic model classes could reasonably explain the same PIT evidence **and** choosing between them would materially change owner economics.

Required chain:

```text
admissible frame difference
-> different causal transmission
-> different duration and/or normalized economics
-> different terminal model class / owner-value surface
-> current PIT evidence cannot reasonably resolve the difference
```

If any link fails, do not use Frame divergence as a probability blocker.

### Experimental controls

When a Frame battle is justified:

```text
SAME PIT RECORD / EVIDENCE
SAME CLAIM AUDIT

Frame A -> pre-expectation underwriting A
Frame B -> pre-expectation underwriting B
...

then reveal the SAME published-expectation evidence / source set

-> expectation / anchoring audit per frame
-> post-expectation belief per frame
-> reveal the SAME market price
-> compare price-implied worlds / owner-value surfaces
```

Do **not** freeze one already-processed common Expectation Envelope before the Frame work. Different Frames may legitimately interpret what the market is betting on differently.

### Frame admissibility gate

A Frame must explain why it is a reasonable economic model class using the frozen PIT record.

Do not manufacture divergence by inventing colorful narratives.

Minimum admissibility questions:

1. What observed economics make this Frame plausible?
2. What causal chain does the Frame assert?
3. What evidence would falsify it?
4. Does it predict materially different owner economics from the competing Frame?
5. Is it actually independent, or merely a lens on another Frame?

### Anti-voting rule

```text
4 frames
!= 4 independent experts

3/4 bullish
!= 75% probability

all frames agree
!= Truth
```

Correlated Frames must be identified explicitly.

### GigaDevice positive control

The GigaDevice dogfood found a meaningful opposed pair:

```text
specialty-memory cycle dominance
vs
structural product-share / platform rebase
```

That disagreement changed:

- how much current earnings are scarcity rent;
- how long elevated earnings persist;
- the post-cycle earnings floor;
- the terminal model class / multiple;
- the owner-value surface.

The existing stress map spans roughly `CNY192` to `CNY592/share`, so the disagreement is not merely linguistic.

Current evidence cannot yet settle the argument because decisive evidence requires future realized margin normalization, non-memory scaling, foundry rent sharing, owner-cash conversion and post-cycle ROIC.

Therefore Analysis Divergence materially strengthens the conclusion:

```text
PROBABILITY QUALIFICATION = PARTIAL / ORDINAL_ONLY
FULL CARDINAL PROBABILITY = NOT ESTABLISHED
```

It does **not** imply that all probability knowledge is absent.

---

## 3. Route 2 — when narratives collapse into one owner-return model, stop the Frame battle

### Trigger condition

If apparently different strategic narratives ultimately translate through the same causal equation, prefer variable underwriting.

Typical shared equation:

```text
retained capital
x incremental ROIC
-> sustainable per-share earnings / owner-earnings growth

+ cash dividend
+ genuine net share shrinkage
+/- valuation change
-> owner return
```

### Midea negative control

The Midea dogfood tested:

```text
mature cash-return franchise
global OBM compounder
B2B reinvestment platform
capital-allocation / owner-return lens
```

The result:

- the owner-return lens was not an independent model class;
- global OBM and B2B looked strategically different but were economically correlated;
- both required attractive incremental ROIC on retained capital;
- the important unknowns were continuous variables rather than incompatible terminal economic species.

Therefore:

> **Midea does not provide strong Analysis-Divergence evidence for `PROBABILITY_NOT_ESTABLISHED`.**

The full cardinal distribution is still not established or required, but for another reason:

> continuous parameter distributions are not credibly calibrated, and forcing a discrete world table adds little decision value.

### Preferred underwriting language

For mature compounders, start with:

```text
per-share owner return
≈ per-share owner-earnings growth
+ cash dividend yield
+ true net share shrinkage
+/- valuation multiple change
```

Then decompose growth:

```text
growth
≈ retention ratio
x incremental return on retained capital
```

The main Research burden is to measure:

- core durability;
- incremental ROIC by growth pool;
- reinvestment intensity;
- payout durability;
- actual cancellation versus incentive-driven repurchase;
- diluted share count;
- normalized owner cash;
- growth duration.

Do not create more Frames merely because management has more strategic labels.

---

## 4. Route 3 — cyclical / scarcity businesses: duration first, peak earnings second

### Core mistake to avoid

```text
peak earnings
x peak-ish multiple
= target value
```

This is especially dangerous when the market can begin discounting normalization before accounting earnings peak.

### Preferred causal sequence

```text
scarcity / cycle driver
-> ASP / mix / volume
-> gross margin
-> supplier / foundry / capital-cost sharing
-> recurring earnings
-> owner cash harvested during the cycle
-> normalization timing
-> post-cycle earnings floor
-> terminal model class
```

### GigaDevice

The duration work showed that being right about shortage through 2029 is not sufficient if 2030 earnings normalize sharply.

The decisive variant is closer to:

```text
shortage duration
+ Giga margin capture
+ owner-cash conversion
+ post-cycle platform floor
```

### Micron

The Micron work adds a related but distinct case:

```text
traditional memory cycle
+ SCA contract protection
+ HBM / AI-memory mix
+ extreme capital intensity
```

The key question is not merely how profitable FY2027 becomes.

It is:

> **Do SCA and AI-memory economics permanently raise the next-cycle normalized earnings / cash-flow floor after accounting for the capital required to serve those contracts?**

For capital-intensive cyclical businesses, owner cash and incremental ROIC must remain first-order. EPS alone is insufficient.

### Probability implication

Duration worlds can be useful even without cardinal probabilities.

A valid output may be:

```text
2027 persistence = strongly supported
2028 duration = serious world
2029 duration = plausible but weaker
post-cycle floor = materially unresolved

ORDINAL KNOWLEDGE = useful
CARDINAL PROBABILITY = not established
```

That is not a Research failure.

---

## 5. Route 4 — networks / value chains: underwrite economic ownership before margins

### Core mistake to avoid

```text
HQ margin improves
-> network economics improve
```

This is not automatically true in franchised or multi-layer value chains.

### Preferred causal sequence

For YTO:

```text
parcel volume / share
-> unit revenue
-> unit cost
-> sustainable unit profit
-> franchise / endpoint economics
-> network health
-> capital investment
-> OCF / FCF
-> incremental ROIC
-> owner economics
```

The key uncertainty is partly **who owns the efficiency gain**.

If HQ margin rises while franchise economics weaken, the economic model itself may need to change.

### Preferred research tool

When current Research is complete enough but probability remains weak, use evidence-trigger design:

```text
QUIET
REOPEN
FRAME CHANGE
```

These are documentation labels only.

Price moves remain `QUIET` for Fundamental Belief.

Reopen only when new evidence discriminates the load-bearing causal chain, such as:

- sustainable unit economics;
- franchise / network health;
- rolling OCF versus capex;
- owner-cash conversion;
- credible incremental ROIC;
- evidence that non-core businesses create or destroy owner value.

This route is especially useful when uncertainty is **future-resolvable but not searchable-away today**.

---

## 6. Route 5 — qualified core plus low-maturity optionality: value the core first

Sanhua provides a useful mixed case.

Retained frame:

> **Qualified thermal-management industrial franchise with a relatively stable, auditable core earnings engine and genuine but economically unproven adjacent call options.**

### Preferred underwriting language

```text
core economics
-> revenue / margin / cash / capex / ROIC
-> core value

adjacent optionality
-> separate upside until realized economics exist
```

Do not allow optionality to silently become Base.

Anti-error rule:

> **If the stock only looks cheap when robot / liquid-cooling success is required, the optionality has already been smuggled into the core thesis.**

This species often needs less broad Frame divergence than a cyclical model-class dispute, but more separation between:

```text
qualified core
and
unqualified upside
```

Probability maturity may therefore be asymmetric by business layer.

---

## 7. Route 6 — resource / commodity businesses: Reference Frame owns everything downstream

Xiamen Tungsten remains the negative control.

The failure chain was:

```text
wrong Reference Frame
-> wrong causal inference
-> probability theater
-> valuation / timing failure
```

For resource / commodity-linked businesses, the Research must explicitly map:

```text
commodity price
+ self-sufficiency / external procurement
+ pass-through
+ inventory
+ quota / ownership economics
+ project timing
+ capex
+ resource / product mix
-> attributable through-cycle owner cash
```

A generic “advanced materials / manufacturing growth” frame can be dangerously flattering if commodity exposure remains first-order.

Method rule:

> **Do not probabilize a bad Frame more carefully. Fix the economic model first.**

---

## 8. Choosing the underwriting language — practical routing table

| Dominant uncertainty | First underwriting language | Analysis Divergence? | Typical probability state |
| --- | --- | --- | --- |
| incompatible economic model classes | admissible Frame battle + causal worlds | **YES, selectively** | often partial / ordinal until model dependence resolves |
| cycle duration / normalization | duration worlds + post-cycle floor + owner cash | sometimes | ordinal duration knowledge may be useful before cardinal weights |
| mature compounder / reinvestment | owner-return decomposition + incremental ROIC | usually **NO** | cardinal worlds often unnecessary; parameter knowledge may be partial |
| franchised / network ownership | causal chain + evidence-trigger reopen design | only if network model itself changes | often ordinal until duration / ownership is observed |
| qualified core + immature optionality | core-first valuation + optionality separation | selective | core can be more mature than optionality |
| resource / commodity model risk | corrected Reference Frame + through-cycle cash map | **YES if model class disputed** | probability should wait for Frame coherence |

This table is a routing aid, not a schema.

---

## 9. A lightweight new-case protocol

For a new company, the first public-diligence pass should be able to answer these questions before scenario probabilities are considered.

### Step 1 — PIT record and Claim Audit

```text
What is actually observed?
Who owns each fact / statement / forecast?
What is derived versus reported?
```

### Step 2 — economic object

Ask:

> **What is the load-bearing owner-economics chain?**

Examples:

```text
cycle -> margin -> normalization -> owner cash
retention -> incremental ROIC -> per-share growth
unit economics -> network health -> capex -> FCF
core -> optionality
commodity -> ownership / pass-through -> through-cycle cash
```

### Step 3 — uncertainty diagnosis

Classify the uncertainty informally:

```text
MODEL CLASS?
DURATION?
CONTINUOUS PARAMETERS?
ECONOMIC OWNERSHIP?
OPTIONALITY MATURITY?
```

No enum is required.

### Step 4 — choose the smallest useful tool

Use:

- Frame divergence only for model-class uncertainty;
- duration worlds for cycle persistence / normalization;
- owner-return decomposition for compounders;
- evidence triggers for future-resolvable network / operating uncertainty;
- core-first separation for optionality;
- corrected through-cycle frame for resource cases.

### Step 5 — reconstruct Published Expectations after pre-expectation underwriting

Do not let sell-side consensus silently choose the Reference Frame.

Use the same sequence:

```text
Observed / Reported Record
-> Causal Underwriting
-> Pre-expectation View
-> Reveal Published Expectations
-> Anchoring / Gap Audit
-> Post-expectation Fundamental Belief
-> Compare with Price-Implied Worlds
```

### Step 6 — probability qualification

Ask what probability knowledge is actually supported.

Human Research language may include:

```text
CARDINAL_PROBABILITY_SUPPORTED
PARTIAL / ORDINAL_ONLY
PROBABILITY_NOT_ESTABLISHED
```

These are not production enums.

Crucially:

```text
Research complete
!= cardinal probability established
!= numerical Odds ready
```

### Step 7 — price comes last

```text
Evidence changes Belief.
Price changes Odds.
```

Price cannot repair an inadmissible Frame or missing owner economics.

---

## 10. When to stop Research

A good stop condition is not “every uncertainty has a number.”

Research can be complete enough when:

1. the PIT record and source roles are clear;
2. the load-bearing causal chain is explicit;
3. material economic model classes are retained or rejected;
4. the important unknowns are named;
5. the unknowns have prospective resolution paths;
6. Published Expectations have been reconstructed separately;
7. price-implied worlds can be compared without feeding price into Belief;
8. remaining uncertainty is genuinely future-resolvable rather than searchable-away now.

At that point the honest output may still be:

```text
Research = complete enough
Probability = partial / ordinal only
Numerical Odds = withheld
```

That is a valid Decision Hygiene result.

---

## 11. Anti-patterns

### Anti-pattern A — scenario monoculture

```text
every company
-> five worlds
-> probabilities sum to 100%
```

Reject.

### Anti-pattern B — narrative diversity theater

```text
OBM story
B2B story
AI story
international story
-> four independent Frames
```

Reject unless they produce genuinely different causal model classes.

### Anti-pattern C — consensus as Frame selector

```text
Street models 15bn
-> 15bn becomes Base
```

Reject. Published Expectations challenge Belief; they do not own it.

### Anti-pattern D — convergence as confidence machine

```text
all analyses agree
-> confidence HIGH
```

Reject. Inspect common-mode assumptions and shared Evidence first.

### Anti-pattern E — divergence as automatic probability veto

```text
models disagree
-> PROBABILITY_NOT_ESTABLISHED
```

Reject unless disagreement reaches material owner economics and current evidence cannot resolve it.

### Anti-pattern F — gross buyback as shareholder yield

Reject. Trace cancellation, incentive usage, dilution and financing.

### Anti-pattern G — price as evidence

Reject.

### Anti-pattern H — better arithmetic on the wrong Reference Frame

Reject hardest.

---

## 12. Method status after current dogfood

Current evidence supports a restrained hypothesis:

> **Different economic species benefit from different underwriting languages, and Analysis Divergence should be invoked only when model-class uncertainty changes the owner-economics surface.**

Evidence so far:

```text
GigaDevice
= positive control for Analysis Divergence

Midea
= negative control / narrative collapse into variable underwriting

YTO
= evidence-trigger / economic-ownership case

Sanhua
= qualified core + immature optionality case

Micron
= duration + contractual cycle-floor + capital-intensity case

Xiamen Tungsten
= Reference-Frame negative control
```

This is enough for a docs-only playbook.

It is **not** enough to justify:

- an Economic Species schema;
- an automatic router;
- a Constitution change;
- a mandatory multi-Frame workflow;
- a probability policy change.

The next evidence should come from future prospective cases and outcomes, not from repeatedly reclassifying the same six companies until the playbook appears universal.

---

## 13. Frozen synthesis

```text
METHOD = choose underwriting language by dominant economic uncertainty

MODEL-CLASS UNCERTAINTY
-> admissible Analysis Divergence

CYCLE / NORMALIZATION UNCERTAINTY
-> duration worlds + post-cycle floor + owner cash

COMPOUNDER / REINVESTMENT UNCERTAINTY
-> retention x incremental ROIC + payout + true share shrinkage

NETWORK / ECONOMIC-OWNERSHIP UNCERTAINTY
-> evidence-trigger reopen design

QUALIFIED CORE + OPTIONALITY
-> core-first underwriting; optionality remains upside until realized

RESOURCE / COMMODITY MODEL RISK
-> correct Reference Frame before probability or valuation

RESEARCH COMPLETE != PROBABILITY ESTABLISHED != ODDS READY
EVIDENCE CHANGES BELIEF; PRICE CHANGES ODDS
INVESTMENT AUTHORITY = NONE
```

The playbook succeeds if it helps the Research process use **fewer, better-fitting analytical tools** rather than becoming one more framework that every company is forced to satisfy.
