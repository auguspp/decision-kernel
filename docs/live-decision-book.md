# Live Decision Book

Status: **MUTABLE NAVIGATION LAYER / NOT AUTHORITATIVE STATE / NO NEW WAKE GATE / NO AUTOMATION**  
Updated: **2026-09-03**  
Repository: `auguspp/decision-kernel`

## Purpose

This file answers one operational question:

> **If the Human opens the repository today, which securities matter, what is the current decision state, and what new evidence or price condition would justify the next review?**

It is intentionally a **mutable index**, not a frozen decision artifact.

Authoritative state remains in the linked Research, Decision Hygiene, Human Decision, Action and later Outcome checkpoints. Updating this page must never rewrite those historical records.

This page does not create:

- a Kernel entity;
- a second Human wake gate;
- a recommendation engine;
- an order / execution system;
- an automation or watcher;
- a probability-readiness schema;
- a market-data fallback;
- investment authority.

Investment Authority remains `NONE`.

---

## Operating rules

1. **Evidence changes Belief; price changes Odds.**
2. **A lower price cannot repair a broken thesis.** If company-specific evidence deteriorates, reopen Research before any Action.
3. **A price condition is never an automatic order.** It is a Human review / entry condition subject to surviving evidence.
4. **Human Decision and Action remain separate.** A decision to buy at a future condition is not proof of execution.
5. **Research complete != Probability established != Odds ready.** Do not manufacture cardinal probability merely to make the page look complete.
6. **The Decision Book is navigation only.** When it disagrees with a frozen artifact, the frozen artifact wins and this page must be corrected.
7. **No stale live-price theater.** This page does not store continuously changing prices. A-share production price observations remain HiThink-only; U.S.-equity public prices remain market context until a production U.S. market-data boundary exists.

---

## Current book

| Security | Current belief / economic frame | Human decision | Action | Next review condition |
| --- | --- | --- | --- | --- |
| **三花智控 / 002050.SZ** | Qualified thermal-management industrial franchise; core is relatively auditable, robot / liquid cooling remain upside until measurable economics exist. | **CONDITIONAL BUY** — first tranche around **CNY30**. Intended evaluation window **~3–6 months after actual execution**. | **NOT YET EXECUTED** | If price approaches the entry condition, verify core revenue / margin, cash conversion, capex / ROIC and that optionality has not silently become Base. |
| **兆易创新 / 603986.SH** | Cycle-amplified fabless platform; differentiated thesis is **longer specialty-memory duration + materially higher post-cycle earnings floor**, not merely “memory stays tight.” | **CONDITIONAL BUY** — around **CNY350** re-check assumptions; **CNY320–335** is first-entry band if thesis survives. | **NOT YET EXECUTED** | Around CNY350, re-underwrite duration, new supply, storage GM, foundry / procurement economics, inventory / OCF, MCU / custom-memory and the 2030 earnings floor. |
| **Micron / MU / NASDAQ** | Capital-intensive memory oligopoly potentially transitioning toward strategic contracted AI-memory economics; SCA trough cushioning is supported, company-wide earnings rebase is not yet proven. | **WAIT / DO NOT BUY FOR NOW** because the Human is temporarily not buying U.S. equities. This is a mandate / action constraint, not bearish Micron Belief. | **NO_ACTION** | **2026-09-30 FY2026/FQ4 earnings** validation window: SCA RPO / coverage / floor economics, HBM, FY27 GM slope, capex / depreciation, normalized FCF and incremental ROIC. |
| **圆通速递 / 600233.SH** | Scaled franchised express network with improving HQ efficiency; transition to a durable low-reinvestment compounder is possible but not proven. Franchisee economics remain load-bearing. | **NO HUMAN INVESTMENT DECISION** | **NONE** | Wait for evidence that changes probability knowledge: sustainable unit profit, franchise / network health, rolling OCF versus cash capex, and through-cycle ROIC. Do not invent a buy band merely because price falls. |
| **厦门钨业 / 600549.SH** | Negative control: integrated cyclical resource / industrial business. Prior H1 annualization / impairment-normalization framing mixed incompatible commodity regimes and is rejected. | **NOT A CURRENT ACTION CANDIDATE** | **NONE** | Use only as a process guard unless new evidence maps tungsten price + resource self-sufficiency + ownership / quota / capex into attributable through-cycle cash returns. |

---

## 1. 三花智控 — core-first conditional entry

### Current state

```text
HUMAN DECISION = CONDITIONAL BUY
FIRST ENTRY = around CNY30/share
POSITION STEP = first tranche
ACTION = NOT YET EXECUTED
INTENDED HOLDING / EVALUATION WINDOW = ~3–6 months after execution
AUTOMATIC TIME EXIT = NONE
```

### What the first tranche is supposed to buy

The first tranche is a **core-first** decision:

```text
refrigeration economics remain resilient
+ automotive thermal-management economics remain intact
+ core margins stay broadly within the qualified historical band
+ cash conversion remains healthy
+ capital allocation / capex do not impair owner economics
-> core alone carries materially more of the underwriting near CNY30
```

Robot and liquid cooling are upside only until revenue, margin, capital requirements and attributable returns become measurable.

### Evidence gate before Action

Reopen Research before execution if:

- refrigeration / auto-thermal revenue or margin evidence weakens materially;
- cash conversion deteriorates;
- capex rises without credible incremental ROIC;
- 2027 earnings revisions reveal a core deterioration rather than mere expectation noise;
- the only way CNY30 looks attractive is by making robot / liquid-cooling success necessary.

Rule:

> **Price can satisfy the entry condition; unchanged-or-improved admissible evidence preserves the thesis.**

### Authoritative lineage

- `research_cases/002050-sanhua-deep-research-v1.json`
- `docs/dogfood/sanhua-decision-hygiene-zero-schema-2026-09-03.md`
- `docs/decisions/002050-sanhua-human-decision-2026-09-03.md`
- `docs/decisions/002050-sanhua-human-horizon-supplement-2026-09-03.md`

---

## 2. 兆易创新 — assumption review before first entry

### Current state

```text
HUMAN DECISION = CONDITIONAL BUY
PRE-ENTRY ASSUMPTION REVIEW = around CNY350/share
FIRST ENTRY = CNY320–335/share
POSITION STEP = first tranche
ACTION = NOT YET EXECUTED
HUMAN EVALUATION HORIZON = NOT YET SPECIFIED
CARDINAL PROBABILITY = not established
NUMERICAL ODDS = withheld under current Decision Hygiene state
```

### Why CNY350 and CNY320–335 are different

`~CNY350` is a **Belief checkpoint**, not a buy trigger.

At that level, the question is whether the original long-duration thesis still survives:

- specialty DRAM / SLC / relevant NOR shortage duration;
- mature-node / domestic supply timing;
- storage ASP and gross margin;
- foundry / procurement cost and shortage-rent capture;
- inventory and operating cash conversion;
- MCU / custom-memory commercialization;
- whether 2030 normalized earnings remain materially above the old-cycle floor.

Only after that review survives does `CNY320–335` remain a valid **conditional first-entry band**.

Rule:

> **CNY350 wakes the assumptions; CNY320–335 permits a first tranche only if those assumptions survive.**

### Authoritative lineage

- `research_cases/603986-gigadevice-deep-research-v2.json`
- `docs/dogfood/gigadevice-decision-hygiene-zero-schema-2026-09-03.md`
- `docs/dogfood/gigadevice-first-entry-reverse-underwriting-2026-09-03.md`
- `docs/dogfood/gigadevice-specialty-memory-duration-underwriting-2026-09-03.md`
- `docs/decisions/603986-gigadevice-human-decision-2026-09-03.md`

---

## 3. Micron — live research hypothesis, not a live trade

### Current state

```text
HUMAN DECISION = WAIT / DO NOT BUY FOR NOW
CURRENT HUMAN CONSTRAINT = temporarily not buying U.S. equities
CONSTRAINT != BEARISH FUNDAMENTAL BELIEF
ACTION = NO_ACTION
VALIDATION WINDOW = 2026-09-30 FY2026 / FQ4 earnings
PRODUCTION U.S. OBSERVEDMARKET = NOT AVAILABLE
PRODUCTION U.S. NUMERICAL ODDS = WITHHELD
```

### Load-bearing research question

The investment question is not whether FY2027 peak EPS is high.

It is:

> **Do SCA economics, HBM / AI-memory mix and the associated capital cycle lift Micron's post-cycle normalized EPS / FCF floor enough to justify a different model class from the historical commodity-memory cycle?**

Current stress anchors remain decision-useful but non-probabilistic:

- merely avoiding the old catastrophic trough is insufficient;
- roughly `USD55–60+` normalized EPS begins to support a strategic-memory rebase framework;
- roughly `USD70–80+` normalized EPS would represent materially stronger economics;
- the key proof must include normalized FCF and incremental ROIC, not EPS alone.

### Validation window — 2026-09-30

Review:

- SCA total RPO and next-12-month RPO;
- number / revenue coverage of signed SCAs;
- fixed / price-banded revenue share and floor / ceiling economics;
- HBM4 / HBM4E qualification and economics;
- DRAM / NAND supply-demand slope;
- FY2027 gross-margin trajectory;
- capex split, depreciation and owner cash;
- whether customer commitments actually share capacity risk without taking all of the economics.

The validation window does **not** obligate a Human investment decision.

### Authoritative lineage

- `docs/dogfood/micron-decision-hygiene-zero-schema-2026-09-03.md`
- `docs/dogfood/micron-sca-floor-economics-underwriting-2026-09-03.md`
- `docs/decisions/MU-micron-human-wait-validation-2026-09-03.md`

---

## 4. 圆通速递 — evidence before price

### Current state

```text
RESEARCH = complete enough to stop the current loop
PROBABILITY = NOT ESTABLISHED
NUMERICAL ODDS = WITHHELD
HUMAN DECISION = NONE
ACTION = NONE
PRICE TRIGGER = NONE
```

Current frame:

> **Scaled franchised network with improving efficiency, but terminal economics depend on the durability of unit profit, franchise-network health, reinvestment needs and owner cash conversion.**

The key causal chain remains:

```text
parcel volume / share
-> unit revenue
-> unit cost
-> sustainable unit profit
-> franchise / network health
-> capital investment
-> OCF / FCF
-> ROIC
-> owner economics
```

### Next evidence worth attention

Do not reopen merely because the share price is lower.

Reopen when new evidence materially informs:

1. **unit profit durability** — whether the strong unit economics persist rather than representing a short policy / pricing window;
2. **franchise / network health** — whether HQ margin gains coexist with a healthy network rather than extracting economics from franchisees;
3. **rolling cash conversion** — whether OCF begins to clear cash capex through a meaningful period;
4. **capital efficiency** — whether incremental investment translates into durable ROIC rather than continued heavy reinvestment;
5. **non-core drag** — whether aviation / international operations become economically relevant to consolidated owner returns.

Existing contract-level falsifiers remain especially useful, including sustained unit profit weakness, YTO-specific franchise deterioration and rolling cash capex staying at or above OCF without a structural economic reset.

### Authoritative lineage

- `research_cases/600233-yto-deep-research-v2.json`
- `research_cases/600233-yto-research-contract-v2.json`
- `research_cases/600233-yto-claim-audit-v2.json`
- `docs/dogfood/yto-decision-hygiene-zero-schema-2026-09-03.md`

---

## 5. 厦门钨业 — negative control / process guard

This case is not a current trade candidate in this book.

Its job is to prevent a recurring failure mode:

```text
wrong Reference Frame
-> wrong causal inference
-> fake probability precision
-> wrong valuation / timing
```

The corrected frame requires explicit treatment of:

- long-run tungsten price regime;
- resource self-sufficiency;
- ownership / attributable economics;
- quota and project timing;
- capex;
- through-cycle cash returns.

Do not revive the historical H1-annualization / impairment-normalization thesis. Reopen only if new evidence can map the resource thesis into attributable owner cash without mixing incompatible commodity regimes.

### Authoritative lineage

- `docs/dogfood/xiamen-tungsten-research-error-negative-control-2026-09-03.md`

---

## Navigation priority

This is **not** an automated ranking and does not create Human wake semantics. It is simply the manual order in which the current book should be consulted when the relevant event occurs.

### Explicit Action always comes first

If the Human confirms an actual trade in a security with a frozen decision:

1. create a separate Action checkpoint;
2. record the Human-confirmed execution timestamp, price and size;
3. bind the latest Research lineage used at execution;
4. record any deviation from the original entry condition;
5. do not edit the original Human Decision checkpoint.

### Price-conditioned reviews

- **GigaDevice:** around CNY350 -> assumption review; CNY320–335 -> first-entry condition only if the review survives.
- **Sanhua:** around CNY30 -> first-entry condition only if the core thesis remains intact.

No automation or scheduled price watcher is implied.

### Evidence / event-conditioned reviews

- **Micron:** 2026-09-30 FY2026/FQ4 earnings validation window.
- **YTO:** next material operating evidence on unit economics, network health and owner cash conversion.
- **Xiamen Tungsten:** only if new evidence is strong enough to rebuild the corrected resource / owner-cash frame.

---

## Update protocol for this page

This file may be edited as the current navigation surface changes, but every material update must be traceable to a stronger artifact.

Preferred sequence:

```text
new evidence
-> new / reopened Research artifact or supplement
-> if applicable, new explicit Human Decision checkpoint
-> if applicable, separate Action checkpoint
-> then update this Decision Book summary
```

Do **not** use this page to create a decision retroactively.

Do **not** silently change a Human horizon, entry condition or rationale here.

Do **not** convert a market move into Fundamental Belief.

Do **not** create fake numerical Odds for cases whose cardinal probability remains unqualified.

The page succeeds when it stays:

> **small, current, auditable, and subordinate to frozen lineage.**
