# YTO Evidence-Trigger Design — 2026-09-03

Status: **FROZEN DECISION-USE RESEARCH SUPPLEMENT / EVIDENCE-DRIVEN REOPEN DESIGN / NO HUMAN DECISION / NO NUMERICAL ODDS / NO AUTOMATION / NO KERNEL CHANGE**  
Security: **圆通速递 / YTO Express / 600233.SH**  
Parent Research: `research_cases/600233-yto-deep-research-v2.json`  
Parent Research Contract: `research_cases/600233-yto-research-contract-v2.json`  
Parent Decision Hygiene dogfood: `docs/dogfood/yto-decision-hygiene-zero-schema-2026-09-03.md`

---

## 0. Purpose

YTO is currently a useful negative case for price-driven action:

```text
Research = complete enough to stop current public-diligence loop
Probability qualification = NOT ESTABLISHED
Numerical Odds = WITHHELD under the current Decision Hygiene method
Human investment decision = NONE
Price trigger = NONE
```

The problem is therefore not “what price should wake us?”

It is:

> **What new evidence would be capable of changing the current Fundamental Belief, probability knowledge, or Reference Frame enough to justify reopening Research?**

This note converts the existing monitoring indicators and falsifiers into explicit **manual evidence semantics**.

It does not create:

- a new Kernel state machine;
- a new Human wake gate;
- an automation / scheduled watcher;
- a numerical probability model;
- a price alert;
- a recommendation;
- a Human investment decision;
- a new authoritative ResearchSnapshot.

The existing frozen Research and Research Contract remain authoritative. This supplement only says when they should be reconsidered.

---

## 1. Current Reference Frame

Retained hybrid frame:

> **Scaled franchised network with structurally improving operating efficiency, but monetization, franchise economics and owner-cash duration remain policy / cycle sensitive; transition to a mature low-reinvestment network compounder is possible but not yet proven.**

The load-bearing causal chain is:

```text
parcel volume / share
-> unit revenue
-> unit cost
-> sustainable unit profit
-> franchise / network health
-> capital investment
-> OCF / FCF
-> incremental ROIC
-> owner economics
```

A valid evidence trigger should discriminate somewhere along this chain. Evidence that cannot plausibly do so should normally remain quiet.

---

## 2. Three evidence-action semantics

This note uses three **documentation labels only**. They are not schema or runtime states.

### QUIET

New information is worth recording as context but is not strong enough to reopen Fundamental Research.

Typical result:

```text
BELIEF = unchanged
PROBABILITY KNOWLEDGE = unchanged
RESEARCH = stays frozen
```

### REOPEN

New admissible evidence materially discriminates among retained worlds or hits an existing Research Contract falsifier.

Typical result:

```text
RESEARCH = reopen
BELIEF = re-underwrite from evidence
PROBABILITY KNOWLEDGE = may strengthen / weaken / remain unresolved
PRICE = not allowed to decide direction
```

### FRAME CHANGE

New evidence suggests the retained hybrid Reference Frame itself is no longer the best economic model.

Typical result:

```text
REFERENCE FRAME = challenged
CAUSAL WORLDS = rebuild before valuation / probability
OLD PRICE ANCHORS = non-driving until Research is rebuilt
```

A FRAME CHANGE can be positive or negative. “The business became a better compounder” is as much a frame change as “HQ margins were achieved by weakening the network.”

---

## 3. What must stay QUIET

The following should **not by themselves** reopen Fundamental Research:

1. **Share-price decline or rally.** Price changes Odds, not Belief.
2. **Broad-market / logistics-sector multiple moves** without YTO-specific operating evidence.
3. **A broker target-price or P/E change** unsupported by new company evidence. This changes Published Expectations, not realized economics.
4. **One analyst earnings revision** whose causal basis is merely valuation / sentiment or already-known data.
5. **General anti-involution / price-war headlines** without YTO-specific unit economics.
6. **Industry regulator evidence alone** about franchise stress at other networks. It remains useful prior evidence but not YTO-specific proof.
7. **One month of parcel volume / market-share data alone.** Share growth is not quality growth unless unit economics and network health are also understood.
8. **Management language about digitalization, AI, network quality or capex maturity** without realized economic transmission.
9. **One isolated half-year in which OCF exceeds cash capex.** H1 2026 is encouraging, but the 2025 full-year record points the other way.
10. **Aviation / international revenue growth alone** while segment margin, capital employed and incremental return remain weak or undisclosed.

Rule:

> **If the new fact is interesting but cannot distinguish sustainable owner economics from temporary accounting / cycle / price effects, record it and stay quiet.**

---

## 4. Trigger family A — sustainable unit owner economics

### Current unresolved question

H1 2026 express unit attributable profit was roughly `CNY0.206/parcel`, materially above the roughly `CNY0.148/parcel` 2025 level.

The current Research refuses to assume that the H1 run-rate is permanent because YTO has historically converted a meaningful part of structural efficiency gains into lower unit revenue.

### REOPEN — negative

Inherit the existing hard falsifier exactly:

> **Express unit profit stays materially below CNY0.18 for two quarters without a structural cost reset.**

This is a strong reason to reopen because it directly weakens the claim that H1 2026 represented a durable unit-economics inflection.

Also reopen if official company data show a renewed meaningful decline in unit revenue that overwhelms structural cost gains and pushes owner economics toward the pre-2026 regime.

### REOPEN — positive

Reopen positively when multiple official reporting periods show that elevated unit economics survive **without relying on one favorable cost / settlement line**.

The evidence bundle should ideally show together:

- unit revenue broadly resilient rather than collapsing;
- core transport / hub costs continuing to improve or stay efficient;
- pickup / delivery economics explained well enough to distinguish productivity from value-chain redistribution;
- express unit profit remaining around the stronger post-inflection range across more than one reporting period;
- parcel / share growth not requiring obvious underpricing.

This does not automatically establish the `network compounder` world. It only upgrades the durability evidence.

### FRAME CHANGE — positive

A positive Frame change becomes plausible if **multi-period** evidence shows:

```text
high / resilient unit owner economics
+ sustained share gains
+ no evidence of franchise extraction
+ lower reinvestment intensity
+ durable owner cash conversion
```

At that point the hybrid frame may be too conservative and the `harvest / network compounder` frame deserves primary status.

---

## 5. Trigger family B — franchise / network economic health

### Current unresolved question

YTO is a franchised network. HQ P&L and full-network economics are not the same economic object.

The current dogfood therefore treats franchise health as load-bearing rather than as a soft ESG / service-quality footnote.

### REOPEN — negative

Inherit the existing hard falsifier exactly:

> **YTO-specific evidence shows material franchise or network deterioration despite HQ margin gains.**

Evidence capable of satisfying this condition can include, where YTO-specific and economically material:

- franchisee exits / churn or visible network instability;
- sustained delivery-fee / settlement stress;
- service deterioration linked to endpoint economics;
- YTO-specific regulator intervention;
- later HQ measures that materially redistribute economics back to endpoints because the prior margin structure proved unsustainable.

### FRAME CHANGE — negative

If YTO-specific evidence shows that HQ margin strength systematically coexists with weakening franchise economics, the current hybrid frame should be challenged toward:

> **HQ-margin optimization inside a fragile network rather than durable full-network productivity.**

That is not a small parameter update. It changes the economic owner of the apparent efficiency gain.

### REOPEN — positive

Positive evidence requires more than “no bad news.” It should show that network health remains stable while HQ unit economics stay strong.

Useful evidence includes:

- stable / improving service quality with strong unit economics;
- stable franchise participation / retention;
- economically credible delivery-fee / settlement structure;
- absence of YTO-specific network stress through a period of high HQ margin;
- evidence that digitalization / density improvements lower **full-network** cost rather than merely shift economics upstream.

---

## 6. Trigger family C — OCF, cash capex and the harvest transition

### Current unresolved question

The two key records point in different directions:

```text
2025 OCF < cash long-term-asset purchases
2026H1 OCF > cash long-term-asset purchases
```

One half-year is not enough to call the business a low-reinvestment compounder.

### REOPEN — negative

Inherit the existing hard falsifier exactly:

> **Rolling cash capex stays at / above OCF while unit economics and utilization fail to improve.**

This would weaken the harvest-transition thesis because strong accounting earnings would not be converting into distributable owner economics.

### REOPEN — positive

Reopen positively when a **rolling multi-period** record shows:

```text
OCF consistently clears cash capex
+ capex intensity falls or stabilizes at a lower level
+ network utilization / asset turns remain healthy
+ service quality / share do not deteriorate
```

The important signal is not merely lower capex. It is lower reinvestment **without starving the network**.

### FRAME CHANGE — positive

A real harvest transition would require enough evidence to say:

> **The network can sustain competitive economics with materially lower incremental capital intensity.**

If established, terminal economics should be re-underwritten from owner FCF / ROIC rather than from one-year earnings alone.

---

## 7. Trigger family D — earnings evidence versus Published Expectations

### Existing hard falsifier

Inherit the Research Contract condition:

> **2027 company earnings evidence moves materially below CNY6.0bn on weaker core economics.**

The phrase **company earnings evidence** matters.

A sell-side estimate below CNY6.0bn is not automatically Fundamental evidence. It matters only to the extent that the revision is grounded in new admissible evidence about YTO's core economics.

### REOPEN

Reopen when official / primary company evidence makes the current 2027 owner-economics range materially less plausible, for example through:

- realized unit profit weakness;
- weaker-than-underwritten unit revenue / cost transmission;
- company-specific network deterioration;
- cash conversion deterioration;
- material new capital requirements.

### Stay QUIET on Belief, but update Expectations

If analysts cut target multiples or forecasts for macro / risk-premium reasons without new company evidence:

```text
PUBLISHED EXPECTATIONS = update
FUNDAMENTAL BELIEF = unchanged
```

This distinction preserves the existing finding that the 2026 formal H1 selloff was not clean evidence of a comparable earnings collapse.

---

## 8. Trigger family E — aviation / international capital drag

### Current unresolved question

H1 2026 aviation gross margin was deeply negative and international parcel margin was thin. The current Research gives these businesses no central optionality credit.

### REOPEN — negative

Inherit the existing hard falsifier exactly:

> **Aviation / international keep absorbing material capital without credible positive incremental returns.**

This becomes more decision-relevant if non-core capital absorption grows enough to offset the cash improvement of the core express network.

### REOPEN — positive

Positive evidence requires realized economics, not strategic language:

- sustained margin improvement;
- lower cash absorption;
- attributable returns on invested capital;
- evidence that international / aviation assets improve the core network economics rather than existing as separate low-return growth projects.

Only then should optionality enter central owner-economics underwriting.

---

## 9. Evidence bundles that are strong enough to change probability knowledge

YTO's probability problem is not a lack of scenario labels. It is a lack of repeated evidence on **duration and economic ownership**.

The following bundles would materially improve probability qualification.

### Bundle 1 — Durable discipline

```text
unit profit stays strong across multiple periods
+ unit revenue does not resume destructive decline
+ share remains healthy
+ franchise health remains stable
```

This would shift ordinal belief away from `competitive relapse` and `HQ margin / weak network` worlds.

### Bundle 2 — Harvest transition

```text
Bundle 1
+ rolling OCF consistently clears cash capex
+ capex intensity / asset turns improve
+ incremental ROIC becomes supportable
```

This would materially strengthen the `durable network economics / harvest` world.

### Bundle 3 — False margin inflection

```text
unit profit falls materially
+ revenue competition resumes
and/or
HQ economics stay strong while franchise health deteriorates
```

This would shift belief toward `competitive relapse` or `HQ margin / weak network` worlds.

### Bundle 4 — Accounting profit without owner cash

```text
reported earnings stay high
but
rolling OCF fails to clear cash capex
+ utilization / ROIC do not improve
```

This would weaken terminal economics even if headline EPS remains close to sell-side expectations.

These bundles are deliberately **ordinal**. They do not assign probability percentages.

---

## 10. Manual reopen protocol

When a material new YTO event arrives, use this sequence:

```text
1. Identify the new record and source role.
2. Ask which causal link it changes.
3. Classify it as QUIET / REOPEN / FRAME CHANGE for documentation purposes.
4. If REOPEN or FRAME CHANGE, recover the exact frozen YTO lineage first.
5. Re-underwrite Fundamental Belief without using the contemporaneous share-price move as evidence.
6. Reconstruct Published Expectations separately.
7. Only after Belief is frozen, compare with price-implied worlds / Odds.
8. Do not manufacture cardinal probability if the new evidence still supports only ordinal discrimination.
```

The share price may make the event more economically interesting. It does not make the evidence more true.

---

## 11. What should trigger immediate Human research attention versus ordinary recordkeeping

This note does **not** create a Kernel wake gate. The following is only a manual Decision Book priority rule.

### High-priority manual REOPEN

- an existing hard falsifier is satisfied;
- YTO-specific franchise / network deterioration appears;
- rolling owner-cash economics contradict the harvest thesis;
- official data show a material reversal in unit-profit durability;
- evidence forces a Reference Frame change.

### Normal evidence update

- routine monthly volume / share data;
- normal sell-side revisions;
- industry-only regulatory evidence;
- non-material one-period cost fluctuations;
- price moves without company evidence.

---

## 12. Current next-step synthesis

The YTO case should now remain quiet until evidence arrives that can discriminate the retained worlds.

Current operating rule:

```text
PRICE MOVE ALONE = no Research reopen
LOWER PRICE = no buy band
NEW SELL-SIDE TARGET = expectation update only unless evidence-backed

UNIT ECONOMICS HARD FALSIFIER = REOPEN
YTO-SPECIFIC NETWORK STRESS = REOPEN / possible FRAME CHANGE
ROLLING OCF-CAPEX FAILURE = REOPEN
OFFICIAL CORE-EARNINGS DETERIORATION = REOPEN
MATERIAL NON-CORE CAPITAL DRAG = REOPEN

MULTI-PERIOD STRONG UNIT ECONOMICS
+ HEALTHY FRANCHISE NETWORK
+ DURABLE OWNER CASH CONVERSION
= positive REOPEN / possible harvest-frame promotion
```

Probability remains:

```text
ORDINAL KNOWLEDGE = useful but incomplete
CARDINAL PROBABILITY = NOT ESTABLISHED
NUMERICAL ODDS = WITHHELD under current Decision Hygiene state
HUMAN DECISION = NONE
INVESTMENT AUTHORITY = NONE
```

The central discipline is:

> **Do not reopen YTO because the stock becomes cheaper. Reopen when new evidence tells us who really owns the unit-economics improvement, how long it lasts, and whether it converts into owner cash after the full network and capital cycle are paid for.**
