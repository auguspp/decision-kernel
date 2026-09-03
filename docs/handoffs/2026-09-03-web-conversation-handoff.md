# 2026-09-03 Web Conversation Handoff

Status: **working handoff for the next ChatGPT conversation / operational context only**  
Repository: `auguspp/decision-kernel`  
Baseline main before this handoff commit: `4b492637ab75ed6472533c22be7f25d06a74ca5d`  
Previous handoff: `docs/handoffs/2026-09-02-web-conversation-handoff.md`  
Recorded: **2026-09-03**

> If this handoff conflicts with current `main`, a frozen Research / Human Decision / Action artifact, or newer evidence, the authoritative artifact wins. This file is a conversation-operating handoff, not Kernel Constitution and not a second truth store.

---

## 0. Read this first

The project has moved materially beyond the 2026-09-02 handoff.

The current phase is no longer mainly about building another stock-analysis pipeline. The system now has:

- multiple real Research dogfoods across different economic species;
- explicit prospective Human investment decisions for Sanhua, GigaDevice and Micron;
- a mutable `Live Decision Book` navigation layer;
- an evidence-trigger reopen design for YTO;
- a positive and negative control for `Analysis Divergence`;
- a docs-only `Economic Species Underwriting Playbook v0`;
- an external code-diligence review of AlphaAnalyst's citation / numeric-claim guardrails;
- a prospective Decision / Action / Outcome capture protocol;
- no change to Kernel investment authority, wake semantics, production market-data policy or Constitution.

The most important operating doctrine now is:

```text
Research complete
!= Probability established
!= Odds ready

Evidence changes Belief.
Price changes Odds.
Human decides.
```

Do not regress to a generic:

```text
data -> AI score -> BUY / SELL
```

or:

```text
every company -> five scenarios -> probabilities sum to 100%
```

---

## 1. Product objective and authority boundary

Canonical flow remains:

```text
Reality
-> claims / evidence
-> Radar / Attention Allocation
-> Research
-> frozen ResearchSnapshot
-> Observed Market
-> Odds
-> Decision Rehearsal
-> Human Surface
-> Human decides
```

Current philosophy is better described as:

> **Decision Kernel is a Decision Hygiene layer, not a Truth Machine.**

Core semantics:

- Reality exists outside the system.
- Harness / Research gathers and interprets claims and evidence.
- Kernel owns PIT-bound validated / admissible records and deterministic invariants, not Reality itself.
- Research != Recommendation.
- Odds != Recommendation.
- Human is final Investment Decision Owner.
- `HumanResearchSurface.status + attention_eligible` remains the sole Human wake gate.
- `Investment Authority = NONE` remains non-negotiable unless the Human explicitly changes it.
- Research Method is replaceable; Constitution is much harder to change.
- `Live Decision Book` is navigation only, never authoritative state.

Quality bar:

> **少、真、静、可审计、不越权。**

Engineering split:

> Mature external tools handle dirty mechanics; LLM handles semantic Research; Kernel guards invariants; Human decides.

---

## 2. Non-negotiable implementation preferences

- Prefer small, direct PRs.
- For repo work, normal operating pattern is `branch -> file/code -> PR -> CI -> squash merge`.
- Reuse before rebuild.
- Do not add DB / event store / queues / provider frameworks without a demonstrated need.
- Do not create a second Radar, a second Human wake gate or another state machine.
- Do not create automation unless the Human explicitly asks.
- HiThink remains the **sole production market-data source**.
- Do not introduce production market-data fallback / provider abstraction for convenience.
- Never expose the HiThink API key.
- Public Web prices may be used as clearly labeled `MARKET_CONTEXT`; they are not production `ObservedMarket` unless the production boundary supports them.
- U.S.-equity Research is allowed; U.S. production `ObservedMarket` / live Numerical Odds are currently not available through the A-share-specific HiThink runtime.
- Do not overstate maturity just because a docs-only method note looks elegant.
- Failed / negative dogfood results are valuable and should remain visible.

User interaction preference:

- Chinese, direct, technically substantive.
- When the Human says “做吧 / 继续”, execute rather than repeatedly asking for confirmation.
- Do not ask a clarifying question when current lineage can resolve the ambiguity.
- Preserve exact Human wording when it constitutes an investment decision.
- Never infer a Human investment decision from approval of Research, a PR or arithmetic.

---

## 3. Research Method — current discipline

### 3.1 Recover lineage before inventing

Before new Research:

1. search current `decision-kernel` lineage;
2. recover prior frozen Research / dogfood / Human decisions;
3. consult older prior art only when useful;
4. do not silently rewrite old mistakes into a clean story.

### 3.2 Source policy is role-based, not citation-count based

Current Research Method v2 uses source roles such as:

```text
PRIMARY_REALIZED
PRIMARY_STATEMENT
SECONDARY_OBSERVATION
MARKET_EXPECTATION
ANALYST_MODEL
ANALYST_OPINION
```

and assertion scopes such as:

```text
REALIZED_OUTCOME
ATTRIBUTED_STATEMENT
ATTRIBUTED_SECONDARY_OBSERVATION
MARKET_EXPECTATION
MODEL_FORECAST
OPINION
```

Core rule:

> **Citation correctness != source admissibility != belief integration.**

Sell-side can be useful as:

- hypothesis generator;
- market expectation;
- information map;
- analyst model / opinion.

It does **not** own realized company economics.

Useful shorthand:

> **研报负责告诉我该查什么，一手资料负责告诉我发生了什么。**

Do not create fake credibility scores merely to make source discipline look quantitative.

### 3.3 Expectation / anchoring discipline

The preferred sequence is now:

```text
Observed / Reported Record
-> Causal Underwriting
-> Pre-expectation View
-> reveal Published Expectations
-> Anchoring / Gap Audit
-> Post-expectation Fundamental Belief
-> compare with Price-Implied Worlds
-> Odds only when probability is genuinely qualified
```

Important refinement from Analysis Divergence work:

When comparing multiple Reference Frames, freeze the same **published-expectation evidence / source set**, not one already-processed shared `Expectation Envelope`.

Use:

```text
SAME PIT RECORD / EVIDENCE
SAME CLAIM AUDIT

Frame A -> pre-expectation underwriting A
Frame B -> pre-expectation underwriting B
...

then reveal SAME published-expectation evidence / source set

-> expectation / anchoring audit per frame
-> post-expectation belief per frame
-> reveal same market price
-> price-implied world / owner-value comparison
```

Reason: a preprocessed common Expectation Envelope can smuggle a common Frame into the experiment before the Frame battle starts.

### 3.4 Driver -> transmission -> owner economics

Every important claim should connect through:

```text
driver
-> economic transmission
-> owner economics
```

Do not stop at narrative, revenue growth or headline EPS.

Examples:

```text
memory shortage
-> ASP / mix / foundry economics
-> margin capture
-> owner cash
-> normalized earnings floor
```

```text
global / B2B growth
-> revenue / margin
-> working capital / capex / marketing
-> incremental ROIC
-> sustainable per-share growth
```

### 3.5 Good Research may reduce conviction

Research is allowed to conclude:

```text
Research complete enough = YES
Probability = NOT ESTABLISHED
Numerical Odds = WITHHELD
```

That is a valid result, not a failure.

---

## 4. Probability maturity — current method state

The strongest repeated method lesson is:

> **Research complete != Probability established != Odds ready.**

Useful distinction:

```text
Research / Causal World
= coherent economic world, may have no cardinal probability

Odds Scenario
= world + qualified probability + valuation
```

Published expectations may challenge Belief only if they expose:

- admissible evidence;
- a missed driver;
- better causal reasoning;
- a model / arithmetic error.

Price-Implied Worlds normally challenge Belief; price itself does not become Belief.

### Human research language currently used

Docs-only method language may use:

```text
CARDINAL_PROBABILITY_SUPPORTED
PARTIAL / ORDINAL_ONLY
PROBABILITY_NOT_ESTABLISHED
```

These are **not production schema enums**.

### Constitution status

There is repeated evidence that forced cardinal probability can create false precision, and probability maturity varies by economic species.

However:

- strict prospective Human Decision / Outcome negative controls are still immature;
- implementation benefit is not proven;
- post-outcome calibration is still insufficient.

Therefore there is **no Constitution / schema / live Odds / wake-semantics change**.

A standing hypothesis only:

> **Decouple ability to freeze decision-useful Research from requirement to certify a complete cardinal probability measure, while numerical Odds remain hard-dependent on a qualified cardinal distribution.**

---

## 5. Economic Species Underwriting Playbook v0 — latest method synthesis

Authoritative docs-only method file:

`docs/economic-species-underwriting-playbook-v0-2026-09-03.md`

This was merged in PR #103, commit before AlphaAnalyst diligence:

`422bdca14809ae87ac60c3ba2f8ca3143a2ef3ff`

The playbook is explicitly **not** an `EconomicSpecies` schema or automatic router.

It asks first:

> **What kind of uncertainty most changes owner economics?**

Current dominant uncertainty classes:

### A. Model-class uncertainty

```text
What is this business economically?
```

Use admissible `Analysis Divergence` only if the Frame choice changes causal structure / terminal economic model class.

### B. Duration / normalization uncertainty

```text
How long do unusually favorable economics last, and what survives afterward?
```

Use duration worlds + post-cycle floor + owner cash.

### C. Continuous reinvestment / owner-return uncertainty

```text
What return does retained capital earn, and how does it translate to per-share owner return?
```

Use:

```text
retention x incremental ROIC
+ dividend
+ true net share shrinkage
+/- valuation change
```

### D. Network / economic-ownership uncertainty

```text
Who actually owns the reported economics, and what evidence proves durability?
```

Use evidence-trigger / reopen design rather than price theater.

### Current cross-case mapping

```text
GigaDevice
= positive control for Analysis Divergence

Midea
= negative control; strategic narratives collapse into variable underwriting

YTO
= evidence-trigger / economic-ownership case

Sanhua
= qualified core + immature optionality

Micron
= duration + contractual cycle-floor + capital intensity

Xiamen Tungsten
= Reference-Frame negative control
```

Key anti-patterns:

- scenario monoculture;
- narrative diversity theater;
- consensus as Frame selector;
- convergence as confidence machine;
- divergence as automatic probability veto;
- gross buyback as shareholder yield;
- price as evidence;
- better arithmetic on the wrong Reference Frame.

No schema / Constitution / mandatory workflow follows from this playbook.

The playbook itself says the next evidence should come from future prospective cases and outcomes, not repeatedly reclassifying the same six companies until the framework looks universal.

---

## 6. Analysis Divergence — positive and negative controls

### 6.1 GigaDevice positive control

File:

`docs/dogfood/gigadevice-analysis-divergence-v0-2026-09-03.md`

Experiment controls:

- same PIT evidence;
- same Claim Audit;
- Frames independently do pre-expectation underwriting;
- same published-expectation evidence revealed later;
- same price revealed last.

Admissibility result:

```text
Frame A = specialty-memory scarcity-cycle model
Frame B = structural product-share / platform-rebase model
Frame C = hybrid synthesis
Frame D = duration / terminal-economics lens, correlated with C
```

Important negative result inside the positive control:

> C and D are not independent votes.

The real opposed model-class pair is A vs B.

Why divergence matters:

It propagates into materially different:

- scarcity-rent interpretation;
- duration;
- margin capture;
- 2030 normalized earnings;
- terminal model class;
- owner-value surface.

Existing no-probability owner-value stress map spans roughly:

```text
CNY192/share -> CNY592/share
```

Current PIT evidence cannot resolve the disagreement because decisive evidence requires future normalization, margin-capture, non-memory scaling, owner cash and post-cycle ROIC.

Verdict:

```text
PROBABILITY QUALIFICATION = PARTIAL / ORDINAL_ONLY
FULL CARDINAL PROBABILITY = NOT ESTABLISHED
NUMERICAL ODDS = WITHHELD
```

This is specific evidence; it does not imply every model disagreement blocks probability.

### 6.2 Midea negative control

File:

`docs/dogfood/midea-analysis-divergence-v0-2026-09-03.md`

Frames included:

```text
A mature cash-return franchise
B global OBM compounder
C B2B reinvestment platform
D capital-allocation / per-share owner-return lens
```

Result:

- D is not an independent model class;
- B and C look strategically different but largely collapse into the same retained-capital -> incremental-ROIC -> per-share-growth bridge;
- return sensitivity is material, but mostly continuous parameter sensitivity inside one shared owner-return model;
- Analysis Divergence is therefore **not** a strong probability blocker for Midea.

Verdict:

```text
ANALYSIS DIVERGENCE = WEAK / PARTIALLY COLLAPSED
PROBABILITY = PARTIAL / ORDINAL_ONLY
FULL CARDINAL = not established / not currently necessary
```

Reason for withholding a full distribution is different from GigaDevice: continuous parameter distributions are not credibly calibrated, and forced discrete worlds add little decision value.

Method rule:

> **Use multi-Frame divergence selectively when Reference Frame uncertainty changes causal model class. If narratives collapse into one owner-return equation, measure the variables better instead.**

---

## 7. AlphaAnalyst Claim Audit code diligence — already completed

File:

`docs/external/alphaanalyst-claim-audit-code-diligence-2026-09-03.md`

Merged in PR #104.

Baseline main before this handoff is the merge commit:

`4b492637ab75ed6472533c22be7f25d06a74ca5d`

External repo reviewed:

`kbhujbal/AlphaAnalyst-open-source-autonomous-equity-research-agent`

Public code lineage reviewed around:

`2cf3d4ee6c99ed8aee9871710825d25aca30e687`

### Mechanisms confirmed in code

- deterministic `decimal.Decimal` valuation arithmetic;
- typed Pydantic finding / citation / memo schemas;
- programmatically assigned fact tags (`F1`, `F2`, ...);
- unknown fact tags fail / downgrade final memo sections;
- numerical prose with no source tag is downgraded;
- outward final citation list is derived programmatically from tags used in prose;
- some fundamentals cross-check FMP versus EDGAR, preserve divergence and prefer EDGAR;
- deterministic arithmetic once numeric inputs are formed.

### Important weaknesses

- validator mostly checks tag existence, not whether each numerical clause is actually supported by the tagged fact;
- several numbers can hide behind one valid tag;
- LLM-generated citation snippets are not mechanically proven to match the source chunk;
- filing `page_hint` is retrieval-order-oriented rather than robust filing-page provenance;
- multi-source Findings may collapse to the first evidence item during synthesis;
- richer source lineage can become generic synthetic `fact` provenance;
- no assertion scope / epistemic role / PIT admissibility / source-authority contract comparable to current Decision Kernel Research Method;
- LLM qualitative judgments can still become cardinal valuation adjustments even if Python performs the arithmetic.

Core conclusion:

> **Borrow mechanical integrity patterns, not AlphaAnalyst's epistemic model or architecture.**

Do **not** add AlphaAnalyst as a dependency.

### Highest-value borrowing candidates

Docs-only recommendation from the diligence:

1. programmatic outward citation derivation;
2. fail-closed unsupported numeric prose;
3. explicit cross-source numeric divergence record;
4. deterministic derived-number lineage tests.

Potential zero-schema harness experiments:

```text
A. claim-to-source warrant test
B. derived-number lineage test
C. multi-source preservation test
D. unsupported numeric-clause fail-closed test
E. source disagreement audit
```

No Claim Audit schema change is justified by the external review alone.

---

## 8. Prospective Human Decision / Outcome protocol

Authoritative file:

`docs/prospective-decision-outcome-capture-protocol-2026-09-03.md`

Purpose:

```text
PIT Research
-> explicit Human Decision
-> Action / No Action
-> later Outcome
-> Attribution
```

### Trigger rule — never infer Human Decision

Create a Human Decision checkpoint only when the Human explicitly commits to an investment choice.

Examples that normally qualify:

- “我决定买。”
- “这只不买 / PASS。”
- “继续持有，不加仓。”
- “卖掉。”
- “我决定先不做，等 X。”

Not sufficient:

- approving Research;
- approving a probability calculation;
- saying “继续”;
- saying “可以合并”;
- approving a PR;
- asking for a buy price;
- hypothetical sizing discussion;
- receiving a Human wake surface.

Rule:

> **If a reasonable observer could interpret the Human statement as approval of Research rather than commitment to an investment choice, do not freeze it as a Human Decision.**

### Human Decision and Action are separate

Never infer Action from Decision.

Never infer Decision from a broker fill / portfolio change without explicit Human confirmation of the investment choice represented by that Action.

If an actual purchase occurs later, create a **separate Action checkpoint** and preserve:

- Human-confirmed price;
- size;
- timestamp;
- exact linkage to the prior Decision;
- latest Research lineage at execution.

Do not edit the original frozen Human Decision.

### Evaluation horizon

Freeze prospectively where known. Do not choose a convenient horizon after seeing the result.

### Outcome attribution

Later review should distinguish:

- Evidence Failure;
- Classification Failure;
- Reference Frame Failure;
- Inference Failure;
- Assumption Failure;
- Probability Failure;
- Valuation Failure;
- Odds Failure;
- Human Decision Failure;
- Action Failure;
- Exogenous Surprise.

Do not let `Probability Failure` absorb upstream Research errors.

---

## 9. Decision Accounting / Human Response gap — reviewed, not implemented

File:

`docs/decision-accounting-human-response-gap-review-2026-09-03.md`

External inspiration came from openInvest Decision Accounting.

Useful longitudinal question:

> **After a decision-use surface reached the Human, what did the Human explicitly do with it?**

Potential docs-only vocabulary, if a future real case proves useful:

```text
ACTED
REJECTED
DEFERRED
NO_ACTION
SUPERSEDED
```

These are **not schema values** and currently are not implemented.

Hard rejection of heuristic action linkage:

```text
same ticker
+ same direction
+ nearby time
!= proof of Action lineage
```

Do not copy openInvest-style time-window auto-linking.

Current conclusion:

- conceptually a thin Human Response evidence class may exist;
- existing Sanhua / GigaDevice / Micron checkpoints are already clean and must not be retroactively split just to create more data;
- first response-only dogfood should wait for a genuine prospective case where explicit Human response adds information not already owned by the Human Decision protocol;
- execution / broker / portfolio ledger should remain outside Kernel, likely Harness / separate prospective audit layer if ever needed.

---

## 10. Live Decision Book — current authoritative navigation

File:

`docs/live-decision-book.md`

Status:

```text
MUTABLE NAVIGATION LAYER
NOT AUTHORITATIVE STATE
NO NEW WAKE GATE
NO AUTOMATION
```

It must remain small. Frozen lineage wins if there is a conflict.

Current book:

| Security | Human decision | Action | Next review gate |
| --- | --- | --- | --- |
| Sanhua / `002050.SZ` | **CONDITIONAL BUY**, first tranche around CNY30 | **NOT YET EXECUTED** | Price condition only if core evidence remains intact; optionality must not become Base |
| GigaDevice / `603986.SH` | **CONDITIONAL BUY**, ~CNY350 assumption review, CNY320–335 first-entry band if thesis survives | **NOT YET EXECUTED** | Recheck duration, supply, storage GM, foundry economics, inventory/OCF, MCU/custom memory, 2030 floor |
| Micron / `MU` | **WAIT / DO NOT BUY FOR NOW**, Human temporarily not buying U.S. equities | **NO_ACTION** | 2026-09-30 FY26/FQ4 validation window |
| YTO / `600233.SH` | **NO HUMAN INVESTMENT DECISION** | **NONE** | Evidence-trigger only; price is QUIET |
| Midea / `000333.SZ` | **NO HUMAN INVESTMENT DECISION** | **NONE** | Evidence-driven incremental ROIC / owner-cash / net-share-shrinkage review |
| Xiamen Tungsten / `600549.SH` | **NOT A CURRENT ACTION CANDIDATE** | **NONE** | Negative-control / process guard only |

---

## 11. Sanhua / 三花智控 (`002050.SZ`)

### Current Research frame

> **Qualified thermal-management industrial franchise with a relatively stable, auditable core earnings engine and genuine but economically unproven adjacent call options.**

Core first:

- refrigeration / HVAC;
- auto thermal management.

Adjacent upside only until realized economics are measurable:

- robot actuators;
- liquid cooling.

Do not let optionality secretly become Base because price is high.

### Key H1 2026 facts

Approximate frozen facts:

- revenue ~CNY16.9bn, +3.92%;
- parent NP ~CNY2.044bn, -3.12%;
- deducted NP ~CNY2.147bn, +6.82%;
- OCF ~CNY2.50bn;
- refrigeration revenue ~CNY10.445bn, GM ~28.37%;
- auto revenue ~CNY6.455bn, GM ~27.56%;
- FX loss ~CNY293m.

2027 fresh expectation evidence broadly clustered around ~CNY5.26–5.77bn NP.

Research core probability knowledge is materially stronger than YTO / GigaDevice, but exact total-company cardinal weights remain unqualified because adjacent optionality is not mature enough.

### Explicit Human Decision

Authoritative files:

- `docs/decisions/002050-sanhua-human-decision-2026-09-03.md`
- `docs/decisions/002050-sanhua-human-horizon-supplement-2026-09-03.md`

Frozen Human wording / meaning:

```text
DECISION = CONDITIONAL BUY
FIRST ENTRY = around CNY30/share
POSITION STEP = first tranche
ACTION = NOT YET EXECUTED
```

Human also stated:

> if bought around CNY30, intended holding / evaluation period may be about **3–6 months**.

Important semantics:

- 3M and 6M are review checkpoints, not automatic exits;
- Research valuation horizon and Human holding horizon are distinct;
- price reaching ~30 is not automatic Action;
- thesis must be unchanged or improved when price condition is met.

Reverse underwriting at CNY30 roughly implies 2027 P/E:

```text
4.7bn NP -> ~26.8x
5.0bn -> ~25.2x
5.25bn -> ~24.0x
5.5bn -> ~22.9x
5.7bn -> ~22.1x
```

First tranche is core-first, not a robot / liquid-cooling lottery ticket.

---

## 12. GigaDevice / 兆易创新 (`603986.SH`)

### Current Research frame

> **Cycle-amplified fabless platform: near-term earnings are dominated by exceptional specialty-memory scarcity while a real multi-product platform develops underneath; duration and the post-cycle normalized earnings floor remain load-bearing.**

2026H1 frozen record includes:

- revenue ~CNY11.566bn;
- parent NP ~CNY6.857bn;
- deducted NP ~CNY4.883bn;
- OCF ~CNY6.048bn;
- storage revenue ~CNY9.827bn, GM ~67.57%;
- MCU revenue ~CNY1.430bn, GM ~38.49%;
- large non-recurring gains in headline NP;
- company explicitly warns memory prices are historically high and eventual rebalance remains real.

The real thesis is not merely “shortage lasts.” It is:

```text
longer specialty-memory duration
+ meaningful GigaDevice margin capture
+ strong owner-cash conversion
+ MCU / custom-memory / adjacent products raise the post-cycle earnings floor
```

Every `+` must survive.

### Duration dogfood

Authoritative file:

`docs/dogfood/gigadevice-specialty-memory-duration-underwriting-2026-09-03.md`

Current duration read:

```text
2027 tightness = strongly supported
2028 specialty-DRAM tightness = serious / supportable world
2029 tightness = plausible Human thesis, not established
2030 post-cycle floor = materially unresolved
```

Existing no-probability duration stress worlds span roughly:

```text
rapid normalization -> end-2029 owner value ~CNY192/share
...
long shortage + durable platform -> ~CNY592/share
```

At historical market context around CNY388.86, simply being right that shortage lasts to 2029 was not enough; a high post-cycle floor also mattered.

### Analysis Divergence status

`PARTIAL / ORDINAL_ONLY`; full cardinal probability not established.

### Explicit Human Decision

Authoritative file:

`docs/decisions/603986-gigadevice-human-decision-2026-09-03.md`

Frozen Human wording:

> “那我决定320-335就是第一笔吧！不过到350左右我会回来重新检查假设。”

Normalized navigation only:

```text
DECISION = CONDITIONAL BUY
PRE-ENTRY ASSUMPTION REVIEW = around CNY350/share
FIRST ENTRY = CNY320–335/share
POSITION STEP = first tranche
ACTION = NOT YET EXECUTED
HUMAN EVALUATION HORIZON = NOT YET SPECIFIED
```

Core rule:

> **CNY350 wakes the assumptions; CNY320–335 permits a first tranche only if those assumptions survive.**

CNY350 review must recheck:

1. specialty DRAM / SLC / relevant NOR duration;
2. new supply timing, especially mature-node / domestic DRAM;
3. storage GM / pricing;
4. foundry / procurement cost and margin capture;
5. inventory and OCF;
6. MCU / custom-memory economics;
7. post-cycle normalized earnings floor;
8. Reference Frame changes.

Do not infer Action merely because price enters 320–335.

If the Human later confirms an actual buy, create a separate Action checkpoint with exact Human-provided details.

Do not inherit Sanhua's 3–6 month evaluation horizon; GigaDevice Human horizon is still unspecified.

---

## 13. Micron / 美光 (`MU`)

### Why U.S. Research is allowed

ResearchSnapshot concepts are not inherently A-share-only.

The current limitation is production market runtime:

- HiThink runtime is currently A-share-specific;
- U.S. public prices may be used only as `MARKET_CONTEXT`;
- do not pretend public Web prices are production `ObservedMarket`;
- production U.S. Numerical Odds are withheld.

### Current frame

> **Capital-intensive memory oligopoly transitioning from brutally cyclical commodity producer toward a strategically contracted AI-memory supplier; SCA transition has real evidence, but company-wide post-cycle earnings rebase remains unproven.**

Key Research files:

- `docs/dogfood/micron-decision-hygiene-zero-schema-2026-09-03.md`
- `docs/dogfood/micron-sca-floor-economics-underwriting-2026-09-03.md`

Core question:

> **What is post-cycle normalized EPS / FCF after scarcity fades?**

Not:

> “Is FY27 EPS huge?”

SCA findings:

- multi-year take-or-pay / commitment structure is materially real;
- SCA can cushion trough economics;
- SCA is not a whole-company 60%+ margin floor;
- protected revenue share matters;
- price-band contracts trade some peak upside for downside protection;
- refundable customer deposits / commitments are financing / commitment evidence, not free shareholder cash;
- capex / depreciation / incremental ROIC remain first-order.

Useful normalized EPS stress concepts from the dogfood:

```text
~$45–60 = traditional-cycle / limited rebase territory
~$70–90 = meaningful strategic-memory rebase
~$100+ = strong durable platform re-rating world
```

Do not assign probabilities yet.

### Explicit Human Decision

Authoritative file:

`docs/decisions/MU-micron-human-wait-validation-2026-09-03.md`

Frozen meaning:

```text
HUMAN DECISION = WAIT / DO NOT BUY FOR NOW
CURRENT HUMAN CONSTRAINT = temporarily not buying U.S. equities
ACTION = NO_ACTION
VALIDATION WINDOW = 2026-09-30 FY2026/FQ4 earnings
```

Critical distinction:

> **“暂时不买美股” is a Human market / mandate constraint, not bearish Micron Fundamental Belief.**

Validation should focus on:

```text
SCA coverage / floor economics
-> HBM / AI-memory mix
-> FY27 gross-margin slope
-> capex / depreciation
-> normalized FCF
-> incremental ROIC
-> post-cycle earnings floor
```

Do not create an automation unless the Human explicitly asks.

---

## 14. YTO / 圆通速递 (`600233.SH`)

### Current frame

> **Scaled franchised network with improving efficiency; transition to a durable low-reinvestment compounder is possible but unproven; franchise / network economics are load-bearing.**

Current Research state:

```text
RESEARCH = complete enough
PROBABILITY = NOT ESTABLISHED
NUMERICAL ODDS = WITHHELD
HUMAN DECISION = NONE
ACTION = NONE
PRICE TRIGGER = NONE
```

Key files:

- `research_cases/600233-yto-deep-research-v2.json`
- `research_cases/600233-yto-research-contract-v2.json`
- `research_cases/600233-yto-claim-audit-v2.json`
- `docs/dogfood/yto-decision-hygiene-zero-schema-2026-09-03.md`
- `docs/dogfood/yto-evidence-trigger-design-2026-09-03.md`

Frozen H1 2026 facts include approximately:

- revenue ~CNY38.893bn;
- parent NP ~CNY3.175bn, +73.44%;
- express attributable NP ~CNY3.361bn;
- parcel volume 16.278bn, +9.52%;
- market share ~16.2%, +0.7ppt;
- unit express revenue ~CNY2.17, -1.04%;
- unit cost ~CNY1.90, -5.99%;
- unit gross profit ~CNY0.27, +57.11%;
- unit attributable NP ~CNY0.2065/parcel;
- OCF ~CNY3.959bn;
- long-term asset purchase cash ~CNY3.482bn;
- aviation and international remain economically weak / capital-intensive.

Causal chain:

```text
volume / share
-> unit revenue
-> unit cost
-> sustainable unit profit
-> network / franchisee health
-> capital investment
-> OCF / FCF
-> ROIC
-> owner economics
```

### Evidence-trigger design

Manual docs-only semantics:

```text
QUIET = record context; keep Research frozen
REOPEN = admissible evidence discriminates worlds / hits falsifier
FRAME CHANGE = evidence challenges the hybrid model class
```

Price decline is `QUIET` by itself.

Inherited hard REOPEN triggers include:

- unit express profit materially below CNY0.18 for two quarters without structural cost reset;
- YTO-specific franchise / network deterioration despite HQ margin gains;
- rolling cash capex at / above OCF while unit economics / utilization fail to improve;
- official company/core evidence putting 2027 earnings materially below CNY6.0bn because core economics weaken;
- aviation / international continues absorbing material capital without credible positive incremental returns.

Positive reopen requires a multi-period bundle such as:

```text
strong unit economics
+ healthy franchise network
+ OCF persistently covers capex
+ incremental ROIC becomes observable
```

Do not create a price buy point for YTO merely to make Decision Book feel complete.

---

## 15. Midea / 美的集团 (`000333.SZ`)

### Current frame

> **Mature high-ROE global consumer-industrial franchise; owner return depends on incremental ROIC, dividends and true net share shrinkage, not gross buyback headlines.**

Key files:

- `docs/dogfood/midea-compounder-decision-hygiene-zero-schema-2026-09-03.md`
- `docs/dogfood/midea-analysis-divergence-v0-2026-09-03.md`

Current state:

```text
RESEARCH = complete enough
PRIMARY TOOL = per-share owner-return decomposition
ANALYSIS DIVERGENCE = WEAK / PARTIALLY COLLAPSED
PROBABILITY = PARTIAL / ORDINAL_ONLY
CARDINAL PROBABILITY = not established / not currently required
NUMERICAL ODDS = WITHHELD
HUMAN DECISION = NONE
ACTION = NONE
PRICE TRIGGER = NONE
```

Core equation:

```text
per-share owner return
≈ per-share owner-earnings growth
+ cash dividend yield
+ genuine net share shrinkage
+/- valuation multiple change
```

Growth bridge:

```text
growth
≈ retention ratio x incremental ROIC
```

Capital-allocation anti-error:

> **Gross repurchase cash != shareholder yield.**

Trace:

- canceled shares;
- employee-plan / incentive usage;
- diluted share count;
- financing / leverage used for repurchases;
- real per-share accretion.

Current next evidence:

- Smart Home share / margin durability;
- overseas OBM margin / working capital / incremental ROIC;
- Building Tech / Industrial Tech / Robotics segment capital productivity;
- normalized owner cash after finance-business / FX / hedge effects;
- dividends + canceled shares + employee grants + diluted share count.

Do not create a buy point without an explicit Human decision process.

---

## 16. Xiamen Tungsten / 厦门钨业 (`600549.SH`)

Key file:

`docs/dogfood/xiamen-tungsten-research-error-negative-control-2026-09-03.md`

Role:

```text
negative control / process guard
NOT a current action candidate
```

Historical failure chain:

```text
wrong Reference Frame
-> wrong causal inference
-> probability theater
-> valuation / timing failure
```

Corrected frame is closer to an integrated cyclical tungsten / industrial business whose owner economics depend on:

- commodity price;
- self-sufficiency;
- pass-through;
- inventory;
- ownership / quota;
- project timing;
- capex;
- resource mix.

Use this case to veto bad method behavior, not to create a current trade.

---

## 17. Current live Odds policy — do not reopen casually

Historical live policy remains:

```text
expected-return thresholds = 20% / 35% / 55%
positive-return probability thresholds = 55% / 65% / 75%
model-risk add-ons = LOW 0 / MEDIUM 3 / HIGH 7 / VERY_HIGH 12 pp
context uncertainty add-ons = elevated 3 / high 7 pp
```

Nominal cumulative payoff remains the production convention.

Do not change live Odds policy to fit hypothetical participation zones.

Current strongest cases (GigaDevice, YTO, Midea, Micron) explicitly show that Research / probability maturity can be insufficient for fresh Numerical Odds.

Market regime can affect the Human's required hurdle without automatically changing Fundamental Belief.

---

## 18. Recent merged sequence — use for chronology

Important recent main history:

```text
#98  Add live Decision Book navigation layer
#99  Add YTO evidence-driven reopen triggers
#100 Dogfood Midea as compounder / capital-allocation case
#101 Dogfood GigaDevice Analysis Divergence + Human Response gap review
#102 Dogfood Midea as Analysis Divergence negative control
#103 Add Economic Species Underwriting Playbook v0
#104 Add AlphaAnalyst Claim Audit code diligence
```

Baseline main before this handoff:

`4b492637ab75ed6472533c22be7f25d06a74ca5d`

Earlier important explicit-decision lineage includes:

- Sanhua conditional first entry around CNY30;
- Sanhua 3–6 month Human evaluation supplement;
- GigaDevice CNY350 assumption review + CNY320–335 first tranche condition;
- Micron WAIT / NO_ACTION + 2026-09-30 validation window.

---

## 19. What the next conversation should NOT do

Do not:

- treat this handoff as more authoritative than current main;
- create another Economic Species schema / router;
- turn Analysis Divergence into a mandatory multi-agent workflow;
- treat convergence as confidence / Truth;
- treat any divergence as automatic `PROBABILITY_NOT_ESTABLISHED`;
- use a preprocessed shared Expectation Envelope before Frame-specific pre-expectation underwriting;
- copy AlphaAnalyst architecture or add it as a dependency;
- reduce Claim Audit to “citation tag exists”;
- invent a generic `high / medium / low` confidence machine;
- drop multi-source provenance to one source;
- invent source provenance for derived numbers;
- convert LLM sentiment into cardinal valuation deltas merely because Python performs the multiplication;
- infer Human Decision from Research approval;
- infer Action from price entering a band;
- infer Action from portfolio / trade proximity;
- create a Kernel-owned broker / portfolio ledger;
- create U.S. production Odds from public Web prices;
- add market-data fallback/provider abstraction;
- create a second wake gate / Radar / state machine;
- add automation without explicit Human request;
- alter Sanhua / GigaDevice / Micron frozen decisions retrospectively;
- give YTO / Midea a buy point merely to make every case symmetrical;
- change Constitution or live Odds policy from docs-only method evidence.

---

## 20. Recommended next work — not a frozen Human decision

The immediately preceding plan (`Economic Species Playbook -> AlphaAnalyst code diligence`) is already complete on current main.

The next sensible method step is **not** another broad framework.

Highest-value candidate:

> **Run one small zero-schema Claim Audit mechanical-integrity dogfood using the AlphaAnalyst lessons against the current Decision Kernel Research Method v2.**

Suggested order:

### Candidate 1 — derived-number lineage dogfood

Test whether a material derived numeric claim can preserve:

```text
derivation name / formula
input claim IDs
input units
PIT
output value
```

and verify the arithmetic deterministically without inventing a fake source for the derived number.

### Candidate 2 — unsupported numeric-clause fail-closed dogfood

Test whether every material numeric clause in synthesized Research has an admissible provenance path, rather than merely one valid citation somewhere in the paragraph.

### Candidate 3 — explicit source disagreement dogfood

When two admissible records disagree:

```text
value A
value B
difference
selection / rejection rule
```

must survive rather than being silently collapsed.

### Candidate 4 — multi-source preservation dogfood

Verify that a claim with multiple material evidence records does not lose lineage during synthesis / freeze.

Guardrail:

> Start as docs / tests / harness experiment. Do not change Claim Audit schema unless a real failure mode proves the current representation insufficient.

A second valid path is simply to stop method construction and let the Decision Book run until prospective evidence / price / Action / Outcome naturally reopens a case.

In particular, the next natural real-world hinges are:

- GigaDevice around CNY350 -> assumption review;
- GigaDevice CNY320–335 -> first tranche only if review survives;
- Sanhua around CNY30 -> thesis check before any Action;
- Micron 2026-09-30 FY26/FQ4 -> validation window;
- YTO -> only evidence-trigger reopen;
- Midea -> incremental ROIC / owner-cash / net-share-shrinkage evidence.

Do not manufacture a new case just to keep the system busy.

---

## 21. Suggested first action / message for the next conversation

If the Human simply says “继续”, first read:

```text
docs/handoffs/2026-09-03-web-conversation-handoff.md
docs/live-decision-book.md
docs/economic-species-underwriting-playbook-v0-2026-09-03.md
docs/external/alphaanalyst-claim-audit-code-diligence-2026-09-03.md
```

Then verify current `main` before acting.

A good continuation is:

> “当前 Playbook 和 AlphaAnalyst diligence 都已经落地。下一步我会先挑一个最小 Claim Audit mechanical-integrity dogfood，而不是再造框架；优先测试 derived-number lineage 或 numeric-clause fail-closed，保持 zero-schema，跑完再决定有没有资格改 harness。”

If the Human instead brings a live stock / price / execution event, prioritize that real prospective event over method work.

---

## 22. Final compact state

```text
KERNEL ROLE = Decision Hygiene, not Truth Machine
INVESTMENT AUTHORITY = NONE
HUMAN WAKE GATE = existing HumanResearchSurface only
PRODUCTION MARKET DATA = HiThink only
U.S. PUBLIC PRICE = MARKET_CONTEXT only

RESEARCH COMPLETE != PROBABILITY ESTABLISHED != ODDS READY
EVIDENCE CHANGES BELIEF; PRICE CHANGES ODDS

ANALYSIS DIVERGENCE
= selective tool for genuine model-class uncertainty

ECONOMIC SPECIES PLAYBOOK
= docs-only method navigation, no router/schema

ALPHAANALYST DILIGENCE
= borrow mechanical guardrails selectively; no dependency

HUMAN DECISION != ACTION
NO HEURISTIC TRADE LINKING

SANHUA
= conditional first tranche ~30, not executed, 3–6m Human evaluation after execution

GIGADEVICE
= ~350 assumption review; 320–335 conditional first tranche; not executed; horizon unspecified

MICRON
= WAIT / NO_ACTION; Human temporarily not buying U.S. equities; validate 2026-09-30

YTO
= evidence-driven only; no Human decision; price QUIET

MIDEA
= owner-return / incremental-ROIC case; no Human decision; no price trigger

XIAMEN TUNGSTEN
= negative control
```

The next conversation should preserve the project's strongest property:

> **When evidence is insufficient, the system is allowed to stay quiet rather than manufacture precision, action or confidence.**
