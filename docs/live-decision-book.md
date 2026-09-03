# Live Decision Book

Status: **MUTABLE NAVIGATION LAYER / NOT AUTHORITATIVE STATE / NO NEW WAKE GATE / NO AUTOMATION**  
Updated: **2026-09-03**  
Repository: `auguspp/decision-kernel`

## Purpose

This page answers one operational question:

> **If the Human opens the repository today, which securities matter, what is the current decision state, and what evidence or price condition justifies the next review?**

It is intentionally a **small mutable index**, not a frozen decision artifact and not a second Research store.

Authoritative state remains in the linked Research, Decision Hygiene, Human Decision, Action and later Outcome checkpoints. If this page conflicts with a frozen artifact, the frozen artifact wins and this page must be corrected.

Investment Authority remains `NONE`.

---

## Operating rules

1. **Evidence changes Belief; price changes Odds.**
2. **A lower price cannot repair a broken thesis.**
3. **A price condition is never an automatic order.**
4. **Human Decision and Action remain separate.**
5. **Research complete != Probability established != Odds ready.**
6. **This page is navigation only; frozen lineage is authoritative.**
7. **No stale live-price theater.** A-share production market observations remain HiThink-only; U.S.-equity public prices are MARKET_CONTEXT until a production U.S. boundary exists.
8. **Do not duplicate full research here.** Keep only the current state, decision/action boundary, next review gate and authoritative lineage.

---

## Current book

| Security | Current frame / Belief | Human decision | Action | Next review gate |
| --- | --- | --- | --- | --- |
| **三花智控 / 002050.SZ** | Qualified thermal-management franchise; core is relatively auditable; robot / liquid cooling remain upside until measurable economics exist. | **CONDITIONAL BUY** — first tranche around **CNY30**; intended evaluation window **~3–6 months after actual execution**. | **NOT YET EXECUTED** | Price may satisfy the condition only if core revenue / margin, cash conversion and capex / ROIC remain intact; optionality must not become necessary Base. |
| **兆易创新 / 603986.SH** | Cycle-amplified fabless platform; thesis is **longer specialty-memory duration + materially higher post-cycle earnings floor**. Analysis-divergence dogfood retains only **partial / ordinal** probability knowledge; full cardinal probability remains unqualified. | **CONDITIONAL BUY** — around **CNY350** re-check assumptions; **CNY320–335** first-entry band only if thesis survives. | **NOT YET EXECUTED** | At ~350 re-underwrite duration, supply, storage GM, foundry / procurement economics, inventory / OCF, MCU / custom memory and 2030 earnings floor. |
| **Micron / MU / NASDAQ** | Memory oligopoly potentially transitioning toward contracted strategic AI-memory economics; SCA trough cushioning supported, company-wide earnings rebase unproven. | **WAIT / DO NOT BUY FOR NOW** because Human is temporarily not buying U.S. equities; this is not bearish Micron Belief. | **NO_ACTION** | **2026-09-30 FY2026/FQ4 earnings**: SCA coverage / floor, HBM, FY27 GM, capex / depreciation, normalized FCF and incremental ROIC. |
| **圆通速递 / 600233.SH** | Scaled franchised network with improving efficiency; durable low-reinvestment compounder transition possible but unproven; franchise economics load-bearing. | **NO HUMAN INVESTMENT DECISION** | **NONE** | **Evidence-driven only.** Price is `QUIET`; use frozen YTO `QUIET / REOPEN / FRAME CHANGE` trigger design. |
| **美的集团 / 000333.SZ** | Mature high-ROE global consumer-industrial franchise. Analysis-divergence negative control found OBM / B2B narratives largely collapse into the same **incremental-ROIC → per-share owner-return** model; divergence is not a probability blocker here. | **NO HUMAN INVESTMENT DECISION** | **NONE** | Evidence-driven: Smart Home durability, overseas OBM economics, B2B incremental ROIC, normalized owner cash, and cancellation / incentive-adjusted diluted share count. No price trigger yet. |
| **厦门钨业 / 600549.SH** | Negative control: integrated cyclical resource / industrial business; old mixed-regime framing rejected. | **NOT A CURRENT ACTION CANDIDATE** | **NONE** | Process guard only unless new evidence maps tungsten price + self-sufficiency + ownership / quota / capex into attributable through-cycle cash returns. |

---

## Decision / review cards

### 三花智控

```text
DECISION = CONDITIONAL BUY
FIRST ENTRY = around CNY30/share
POSITION STEP = first tranche
ACTION = NOT YET EXECUTED
HUMAN EVALUATION WINDOW = ~3–6 months after actual execution
AUTOMATIC TIME EXIT = NONE
```

Core rule:

> **Price can satisfy the entry condition; unchanged-or-improved admissible evidence preserves the thesis.**

Authoritative lineage:

- `research_cases/002050-sanhua-deep-research-v1.json`
- `docs/dogfood/sanhua-decision-hygiene-zero-schema-2026-09-03.md`
- `docs/decisions/002050-sanhua-human-decision-2026-09-03.md`
- `docs/decisions/002050-sanhua-human-horizon-supplement-2026-09-03.md`

### 兆易创新

```text
DECISION = CONDITIONAL BUY
PRE-ENTRY ASSUMPTION REVIEW = around CNY350/share
FIRST ENTRY = CNY320–335/share
POSITION STEP = first tranche
ACTION = NOT YET EXECUTED
HUMAN EVALUATION HORIZON = NOT YET SPECIFIED
PROBABILITY QUALIFICATION = PARTIAL / ORDINAL_ONLY
CARDINAL PROBABILITY = not established
NUMERICAL ODDS = withheld under current Decision Hygiene state
```

Core rule:

> **CNY350 wakes the assumptions; CNY320–335 permits a first tranche only if those assumptions survive.**

Authoritative lineage:

- `research_cases/603986-gigadevice-deep-research-v2.json`
- `docs/dogfood/gigadevice-decision-hygiene-zero-schema-2026-09-03.md`
- `docs/dogfood/gigadevice-first-entry-reverse-underwriting-2026-09-03.md`
- `docs/dogfood/gigadevice-specialty-memory-duration-underwriting-2026-09-03.md`
- `docs/dogfood/gigadevice-analysis-divergence-v0-2026-09-03.md`
- `docs/decisions/603986-gigadevice-human-decision-2026-09-03.md`

### Micron

```text
DECISION = WAIT / DO NOT BUY FOR NOW
CURRENT HUMAN CONSTRAINT = temporarily not buying U.S. equities
CONSTRAINT != BEARISH FUNDAMENTAL BELIEF
ACTION = NO_ACTION
VALIDATION WINDOW = 2026-09-30 FY2026/FQ4 earnings
PRODUCTION U.S. OBSERVEDMARKET = NOT AVAILABLE
PRODUCTION U.S. NUMERICAL ODDS = WITHHELD
```

Validation hinge:

> **Do SCA economics, HBM / AI-memory mix and the capital cycle raise post-cycle normalized EPS / FCF enough to justify a different model class from historical commodity memory?**

Authoritative lineage:

- `docs/dogfood/micron-decision-hygiene-zero-schema-2026-09-03.md`
- `docs/dogfood/micron-sca-floor-economics-underwriting-2026-09-03.md`
- `docs/decisions/MU-micron-human-wait-validation-2026-09-03.md`

### 圆通速递

```text
RESEARCH = complete enough to stop current loop
PROBABILITY = NOT ESTABLISHED
NUMERICAL ODDS = WITHHELD
HUMAN DECISION = NONE
ACTION = NONE
PRICE TRIGGER = NONE
```

Manual evidence semantics, documentation-only:

```text
QUIET = record context; keep Research frozen
REOPEN = admissible evidence discriminates retained worlds or hits a hard falsifier
FRAME CHANGE = evidence challenges the hybrid economic model; rebuild causal worlds first
```

Inherited hard REOPEN triggers include:

- unit express profit materially below `CNY0.18` for two quarters without structural cost reset;
- YTO-specific franchise / network deterioration despite HQ margin gains;
- rolling cash capex at / above OCF while unit economics / utilization fail to improve;
- 2027 **company/core earnings evidence** materially below `CNY6.0bn` on weaker core economics;
- aviation / international continuing to absorb material capital without credible positive incremental returns.

Authoritative lineage:

- `research_cases/600233-yto-deep-research-v2.json`
- `research_cases/600233-yto-research-contract-v2.json`
- `research_cases/600233-yto-claim-audit-v2.json`
- `docs/dogfood/yto-decision-hygiene-zero-schema-2026-09-03.md`
- `docs/dogfood/yto-evidence-trigger-design-2026-09-03.md`

### 美的集团

```text
RESEARCH = complete enough to stop first public-diligence loop
REFERENCE FRAME = mature high-ROE global consumer-industrial franchise
PRIMARY TOOL = per-share owner-return decomposition
ANALYSIS DIVERGENCE = WEAK / PARTIALLY COLLAPSED
PROBABILITY QUALIFICATION = PARTIAL / ORDINAL_ONLY
CARDINAL PROBABILITY = not established / not currently required
NUMERICAL ODDS = WITHHELD
HUMAN DECISION = NONE
ACTION = NONE
PRICE TRIGGER = NONE
```

Core owner-return decomposition:

```text
per-share owner return
≈ per-share earnings / owner-earnings growth
+ cash dividend yield
+ genuine net share shrinkage
+/- valuation multiple change
```

Primary method rule:

> **For Midea, strategic narratives should first be translated into retention × incremental ROIC. OBM / B2B narrative divergence is not an independent reason to reject cardinal probability when the owner-economics model is shared.**

Primary anti-error rule:

> **Gross repurchase cash != shareholder yield. Trace cancellation, employee-plan usage, dilution and financing to determine true net per-share accretion.**

Next evidence:

- Smart Home share / margin durability;
- overseas own-brand margin, working capital and ROIC;
- Building Tech / Industrial Tech / Robotics incremental ROIC;
- normalized OCF / owner cash after finance-business and FX / hedge effects;
- dividends + canceled shares + employee grants + diluted share count.

Authoritative lineage:

- `docs/dogfood/midea-compounder-decision-hygiene-zero-schema-2026-09-03.md`
- `docs/dogfood/midea-analysis-divergence-v0-2026-09-03.md`

### 厦门钨业

```text
ROLE = negative control / process guard
CURRENT ACTION CANDIDATE = NO
```

Failure chain to avoid:

```text
wrong Reference Frame
-> wrong causal inference
-> fake probability precision
-> wrong valuation / timing
```

Authoritative lineage:

- `docs/dogfood/xiamen-tungsten-research-error-negative-control-2026-09-03.md`

---

## Navigation priority

This is not an automated ranking and does not create Human wake semantics.

### Explicit Action always comes first

If the Human confirms an actual trade under a frozen decision:

1. create a separate Action checkpoint;
2. record Human-confirmed execution timestamp, price and size;
3. bind the latest Research lineage used at execution;
4. record any deviation from the original entry condition;
5. do not edit the original Human Decision checkpoint.

### Price-conditioned reviews

- **GigaDevice:** around CNY350 -> assumption review; CNY320–335 -> first-entry condition only if review survives.
- **Sanhua:** around CNY30 -> first-entry condition only if core thesis remains intact.

No automation or scheduled price watcher is implied.

### Evidence / event-conditioned reviews

- **Micron:** 2026-09-30 FY2026/FQ4 earnings validation window.
- **YTO:** frozen evidence-trigger design; price remains QUIET.
- **Midea:** incremental ROIC / owner-cash / true net-share-shrinkage evidence; no price trigger yet.
- **Xiamen Tungsten:** only evidence strong enough to rebuild the corrected resource / owner-cash frame.

---

## Update protocol

Preferred sequence:

```text
new evidence
-> new / reopened Research artifact or supplement
-> if applicable, new explicit Human Decision checkpoint
-> if applicable, separate Action checkpoint
-> then update this Decision Book summary
```

Do **not** use this page to create a decision retroactively, silently alter a Human horizon / entry condition / rationale, convert a market move into Fundamental Belief, or manufacture numerical Odds from unqualified probabilities.

The page succeeds when it stays:

> **small, current, auditable, and subordinate to frozen lineage.**