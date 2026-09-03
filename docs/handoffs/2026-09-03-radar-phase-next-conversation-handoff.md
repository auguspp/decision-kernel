# 2026-09-03 Radar-Phase Next-Conversation Handoff

Status: **working handoff for the next ChatGPT conversation / operational context only**  
Repository: `auguspp/decision-kernel`  
Current `main` at handoff start: `0102e69f5062d0e5e2d6e5070d562c11c9dbde8e`  
Supersedes for day-to-day operations: `docs/handoffs/2026-09-03-web-conversation-handoff.md`  
Recorded: **2026-09-03**

> If this handoff conflicts with current `main`, a frozen Research / Human Decision / Action artifact, or newer admissible evidence, the newer authoritative artifact wins. This file is not Constitution, not Kernel state, and not a second truth store.

---

## 0. Read these ten points first

1. **Decision Kernel is Decision Hygiene, not a Truth Machine and not a Stock-Picking AI.** Reality stays outside the system; Research interprets; Kernel guards hard invariants; Human decides.
2. **Current product priority is Attention Acquisition + longitudinal evidence**, not more Kernel / Research Method elaboration.
3. **Commitment Radar v0 exists as a zero-schema lineage dogfood.** Semantic matching remains Research cognition; exact Research / commitment / assessment-packet / Evidence lineage is mechanically fail-closed.
4. **Surprise Radar has qualified HiThink history + short-lived shadow sampling, but NO detector yet.** Do not invent thresholds from synthetic data or one day of observations.
5. **Heterogeneous case coverage is now sufficient to stop category-filling by default.** New cases should come from real Radar surprises, commitment resolution, or a genuine method mismatch.
6. **The biggest missing evidence is longitudinal:** `PIT Research -> explicit Human Decision -> confirmed Action -> later Outcome -> Attribution`. No complete executed chain exists yet.
7. **Odds time semantics have a real demonstrated failure mode** (#110/#111), but replacement policy is not established. Freeze the finding; do not keep designing CAGR/IRR/buckets without new real evidence.
8. **Scheduled Human Inbox now uses an explicit curated package list.** File presence in `dogfood/` no longer grants Human-facing Odds eligibility. CMB was the real failure that forced this change (#120).
9. **Human accountability is currently outside Kernel state.** Explicit Decision / Action / Outcome accountability is preserved via prospective Markdown + immutable Git history. Do not create `HumanDecision`, `Action`, or `Outcome` Kernel entities without a proven need.
10. When the Human says **“继续 / 做吧”**, execute operational work. That wording is **not an investment decision** and must never be frozen as one.

---

## 1. Canonical project boundary

Canonical conceptual flow:

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

Core doctrine:

```text
Research complete
!= Probability established
!= Odds ready

Evidence changes Belief.
Price changes Odds.
Human decides.
```

Authority boundary:

- Human is final investment authority.
- System `Investment Authority = NONE`.
- `HumanResearchSurface.status + attention_eligible` remains the **sole** Human wake gate.
- Do not create a second wake / attention policy under Radar.
- Kernel guards PIT, exact lineage, frozen identity, authority boundaries, wake invariants, deterministic committed inputs and related hard invariants.
- Kernel does **not** own investment truth or all Human accountability state.
- Explicit Human Decision / Action / Outcome audit artifacts currently live outside Kernel via prospective Markdown + immutable Git history.

Engineering posture:

> **少、真、静、可审计、不越权。**

Prefer small direct changes and the normal repo pattern:

```text
branch -> file/code -> PR -> CI -> squash merge
```

Always re-check current `main` before writes. `main` beats this handoff.

---

## 2. Project phase changed today

The project should now be understood as:

```text
Phase 1  Trustworthy cognition core
         STABLE ENOUGH TO STOP EXPANDING WITHOUT FAILURE

Phase 2  Research Method dogfood
         SUFFICIENTLY DOGFOODED TO STOP METHOD-LED DEVELOPMENT

Phase 3  Attention Acquisition
         ACTIVE PRIORITY

Phase 4  Heterogeneous longitudinal cases
         ACTIVE IN PARALLEL, BUT EVENT-DRIVEN NOT CATEGORY-DRIVEN

Phase 5  Revisit Odds / Constitution
         ONLY WHEN NEW CASES + OUTCOMES PROVIDE NEW EVIDENCE
```

Do **not** say Phases 1/2 are “proven correct” or permanently complete. The correct claim is that they are mature enough that new work must be justified by real failure.

The operating idea now is:

> **Radar brings new reality into the system. Cases make the system keep the scars.**

---

## 3. Attention Acquisition — current state

### 3.1 Commitment Radar v0 — merged #112

PR #112: `Dogfood Commitment Radar v0 exact lineage`.

Real CATL corpus was used.

Positive control:

- CATL 2026-08-12 capital-allocation disclosure batch;
- exact frozen open question:
  `在大规模扩产下，自由现金流转化能否跟上利润增长？`
- exact official Evidence announcements include `1225470687` and `1225470688`.

Mechanics:

```text
semantic match
= replaceable Research cognition

if a match is proposed:
exact Research identity
+ verbatim frozen commitment text
+ exact assessment-input identity
+ exact official Evidence lineage
= mechanically validated / fail closed
```

Negative controls:

- a plausible paraphrase is rejected because it is not the exact frozen commitment text;
- a real later CATL announcement cannot be smuggled into the wrong assessment packet;
- a valid but irrelevant Hong Kong address-change packet does not manufacture relevance.

Important boundary:

```text
commitment hit
!= Human wake
```

No Radar schema, relevance score, keyword policy, embedding policy, second wake gate, or Human Decision state was added.

### 3.2 Surprise Radar input foundation — merged #113

PR #113 exposes the already-fetched HiThink 45-day raw completed-close history as a qualified Harness input.

It preserves:

- ordered raw closes;
- completed-session timestamps;
- exact thscode;
- provider response session;
- expected latest session;
- existing raw-unadjusted / exchange-calendar / no-future-bar / staleness discipline.

Production live Odds still uses the latest qualified completed close from the same history.

No detector, factor score, ranking, provider fallback, or Human wake behavior was added.

### 3.3 Surprise Radar natural sampling — merged #114

PR #114 adds short-lived shadow capture to the existing weekday `decision-inbox` workflow.

Current behavior:

```text
weekday Decision Inbox
-> independent non-fatal market-history shadow capture
-> qualified 45-day HiThink windows
-> GitHub Actions artifact
-> retention 14 days
```

Boundaries:

- no new scheduler / cadence;
- shadow failure cannot make Human Inbox fail;
- no anomaly detector;
- no z-score / factor score / stock ranking;
- no Research route;
- no Human attention authority;
- no Git state for sampled windows.

Required evidence before building a detector:

```text
A. obvious anomaly that later truly deserved Research
B. large move that later proved noise / IGNORE
C. initially quiet case that later became important (false-negative candidate)
```

Do not choose `20d return`, volatility thresholds, change-point parameters, etc. merely because they look mathematically tidy.

---

## 4. What actually happened in today’s manual Radar run

A one-off manual Radar run was executed on 2026-09-03 after the Human explicitly asked to run today rather than wait for the normal schedule.

Historical run reference (operational only, not authoritative state):

- run id: `33742568111`
- one-off workflow branch was temporary / ops-only and is not part of `main`.

The run successfully completed:

- Decision Inbox;
- HiThink market-history shadow capture;
- official disclosure scan;
- artifact upload.

It captured **6 qualified HiThink windows** for the then-current universe.

### 4.1 Price Surprise result

There was **no validated Surprise Radar price alert**.

Important wording:

> This does **not** mean “nothing moved.” It means the project intentionally has no validated detector yet, so no arbitrary move was promoted to an alert.

Today’s windows are calibration samples, not proof of a threshold.

### 4.2 Commitment / disclosure result

Two 2026-09-03 disclosure batches were the truly new dated disclosures in the one-off scan:

- CATL / 宁德时代: `关于回购公司A股股份的进展公告` (`1225545968`)
- Sanhua / 三花智控: `H股公告-翌日披露报表` (`1225544315`)

CATL manual triage:

```text
capital-allocation commitment touched
actual cash-deployment question not resolved
=> KEEP_ON_RADAR / WAIT_FOR_TRIGGER
=> no new Human wake solely from this disclosure
```

Sanhua manual triage:

```text
qualified disclosure identity
insufficient semantic support for thesis-level conclusion
=> no escalation
```

The one-off scan showed `9 unassessed` because it did not restore the normal scheduled receipt memory; most were older CATL backlog, not nine new 2026-09-03 events. Do not confuse missing receipt memory with nine fresh signals.

### 4.3 The most valuable result was a system failure, not a stock alert

The pre-fix one-off Inbox surfaced CMB / 招商银行 as `ACCEPTABLE_ODDS`.

That was **wrong at the product-governance level** because #115 had already explicitly stated:

```text
legacy CMB 25/50/25 scenarios = historical mechanics fixture
fresh cardinal probability = NOT ESTABLISHED
fresh Numerical Odds = WITHHELD
```

Root cause:

```text
scheduled Inbox used dogfood/*.json
-> checked-in fixture presence
-> automatic live Odds path access
-> stale / superseded research could regain Human-facing power
```

This was not a Kernel classifier bug and not a second wake-gate problem. It was Harness input governance.

---

## 5. Inbox governance fix — merged #120 and real-run verified

PR #120: `Fix scheduled Inbox stale Odds eligibility`.

Current `main` at handoff start:

`0102e69f5062d0e5e2d6e5070d562c11c9dbde8e`

Scheduled Human Inbox now uses an **explicit curated package list**:

```text
dogfood/600519-moutai.json
dogfood/300750-catl.json
dogfood/601088-shenhua.json
research_cases/603986-gigadevice-deep-research-v2.json
research_cases/002050-sanhua-deep-research-v1.json
```

CMB is excluded from scheduled Human Inbox.

CMB is intentionally still allowed in:

- Surprise Radar shadow observation;
- official disclosure acquisition;
- deliberate historical/manual replay.

Reason:

> **Replayability / file presence != current Human-facing Research / Odds eligibility.**

No Kernel change, no Odds policy change, no `HumanResearchSurface` change, no second gate, no eligibility enum, no deletion of historical fixture.

A separate one-off post-#120 verification was executed:

- run id: `33743787675`
- result: **1 attention / 5 total**
- explicit fail-closed check grepped for `招商银行|600036`; job would fail if CMB appeared.
- job passed.

Corrected 2026-09-03 Human Inbox snapshot from that verification:

```text
ATTENTION
- 宁德时代 300750 @ CNY349.5 -> ACCEPTABLE_ODDS

QUIET
- 三花智控 002050 @ CNY36.3 -> INSUFFICIENT_ODDS
- 贵州茅台 600519 @ CNY1298.88 -> INSUFFICIENT_ODDS
- 中国神华 601088 @ CNY47.78 -> INSUFFICIENT_ODDS
- 兆易创新 603986 @ CNY383.2 -> INSUFFICIENT_ODDS

WITHHELD / NOT IN HUMAN INBOX
- 招商银行 600036
```

These prices are **2026-09-03 run context only**. Do not treat them as durable state in a later conversation.

The temporary ops verification workflow was removed from its ops branch after the run. Do not merge or revive ops-only trigger changes into `main`.

---

## 6. Heterogeneous case coverage — stop category-filling

The project deliberately added several uncertainty-structure stress tests and then froze a coverage checkpoint.

### #115 CMB / financial institution

File:

`docs/dogfood/cmb-financial-institution-underwriting-zero-schema-2026-09-03.md`

Primary causal language:

```text
funding franchise
+ asset yield
+ credit migration
+ fee economics
+ capital / RWA
-> sustainable ROE
-> per-share book-value compounding
```

Key lesson:

- do not use industrial `revenue -> margin -> FCF -> ROIC` as the main bank language;
- P/B is terminal translation, not causal model;
- old `25/50/25` probabilities were not re-qualified.

### #116 Shandong Gold / purer resource case

File:

`docs/dogfood/shandong-gold-resource-underwriting-zero-schema-2026-09-03.md`

Primary causal language:

```text
gold price
× mine volume
- unit mine cost
-> mine cash generation
- sustaining / development capital
+ reserve replacement
-> normalized owner cash
```

Key negative controls:

- consolidated revenue can fall because low-margin purchased-gold pass-through shrinks while core mine economics improve;
- profit can rise on gold price while physical mine production falls;
- exact comparable unit cost / AISC and sustaining capex remain incomplete, so no fake normalized model was forced.

### #117 Ninghu / finite concession

File:

`docs/dogfood/ninghu-regulated-concession-underwriting-zero-schema-2026-09-03.md`

Primary causal language:

```text
traffic / traffic mix
× toll economics
× remaining concession life
-> concession cash
-> distributions and/or replacement concessions
-> per-share owner value
```

Key lesson:

> Concession expiry is a **model-class variable**, not a generic risk add-on.

### #118 BeOne / high-R&D pipeline optionality

File:

`docs/dogfood/beone-pipeline-optionality-underwriting-zero-schema-2026-09-03.md`

Core split:

```text
validated franchise economics
!= pipeline option book
```

Rules:

- current profitability does not validate the entire pipeline;
- R&D spend != option value;
- pipeline count != probability;
- phase label != cardinal probability;
- early data normally advances evidence state, not terminal revenue;
- program-specific milestones fit naturally into Commitment Radar.

### #119 Case Coverage Checkpoint

File:

`docs/case-coverage-checkpoint-2026-09-03.md`

Main conclusion:

> The project now has enough underwriting-language diversity to stop category-filling by default.

Do **not** create an `EconomicSpecies` enum/router or start asking “which species are still missing?”

Economic Species Playbook remains an **underwriting-language selector**, not company taxonomy.

Correct first question:

> **What is the truly load-bearing uncertainty for this company, and what analytic language creates the least false precision?**

New cases should now normally be acquired through:

```text
Surprise Radar
-> Human / Research triage
-> Quick Research
-> real mismatch / importance
-> Full Case
-> frozen commitments
-> Commitment Radar
```

---

## 7. Claim Audit mechanical work — frozen unless real new failure

Sequence:

- #106 derived-number lineage
- #107 numeric-clause fail-closed
- #108 multi-source preservation
- #109 mechanical-integrity health checkpoint

### #106 Derived-number lineage

Real YTO H1 example:

```text
OCF - cash capex
-> formula/version
-> exact material input claim
-> exact EvidenceArtifact structured fields
-> PIT
-> deterministic Decimal output
```

Rule:

> A derived number is auditable because its derivation and exact inputs are auditable, not because the system invents a source identity for the output.

No `DerivedClaim`, derivation graph or Claim Audit v3 authorized.

### #107 Numeric-clause fail closed

Test harness explicitly declares material numeric clauses; it does **not** regex-parse prose.

Every material numeric clause needs its own qualified provenance path.

Rule:

> One supported number cannot launder a neighboring unsupported number.

Unsupported material clause -> whole section fails closed.

Material-clause discovery remains unsolved; regex number extraction is not authorized.

### #108 Multi-source preservation

Existing Claim Audit v2 already requires exact `source_uses` coverage for FACT / MARKET_CONTEXT claim Evidence lineage.

Dropping one material source yields `SOURCE_USE_COVERAGE_MISMATCH`.

No new mechanism was needed.

### #109 Health checkpoint

Important conclusions:

- recent helper duplication is real but too small / YTO-specific to justify abstraction;
- all three mechanical dogfoods were YTO-centered;
- cross-case failure is required before productizing shared helpers;
- Xiamen Tungsten is a real historical inference/warrant negative control, but not structured enough for a clean mechanical regression without backfilling artifacts;
- no clean same-quantity admissible source-disagreement case was found;
- no Claim Audit v3 / warrant score / provenance service / disagreement abstraction justified.

Standing candidate gaps only when a **real** negative control appears:

- claim-to-source semantic warrant;
- same-quantity admissible source disagreement.

Do not manufacture artifacts just to complete these experiments.

---

## 8. Odds validity — real failure found, policy intentionally frozen

### #110 Odds Validity Audit v0

Current policy spans 180–730 days while using fixed cumulative return hurdles.

Real mechanical finding:

```text
same 20% cumulative return
180d -> ~44.7% annualized equivalent
365d -> 20.0%
730d -> ~9.5%

current classifier: ACCEPTABLE for all three
```

And approximately same 20% annualized attractiveness across horizons was classified differently:

```text
180d -> INSUFFICIENT
365d -> ACCEPTABLE
730d -> ATTRACTIVE
```

Therefore current `ParticipationZone` semantics are not horizon-invariant.

### #111 Real CMB semantic replay

Real near-one-year CMB case was a convergence control: current cumulative and time-normalized variants all stayed `ACCEPTABLE` around the original ~363-day horizon.

Holding the exact same CMB worlds / probabilities / payoff / price and changing only realization horizon:

```text
                   180d          730d
current            ACCEPTABLE    ACCEPTABLE
time-normalized    EXCEPTIONAL   INSUFFICIENT
```

Important simplification:

> For terminal-only payoff cases, CAGR / horizon-normalized hurdle / discount-rate semantics collapse into the same time-normalized opportunity-cost family.

A naive horizon bucket produced a one-day cliff, so buckets are not an automatically safe compromise.

Current verdict:

```text
Odds horizon failure mode        REAL
generic counterfactual           CONFIRMED
real-case replay                 CONFIRMED
replacement policy               NOT ESTABLISHED
policy change                     NOT AUTHORIZED
```

Do not continue Odds design unless new evidence arrives, such as:

- real Decision / Outcome;
- real different-horizon case;
- case with dated interim cash flows / distributions;
- evidence that attention allocation actually failed because of time semantics.

---

## 9. Current live Human decisions — preserve exactly

`docs/live-decision-book.md` is mutable navigation only. Frozen linked artifacts win.

### Sanhua / 002050.SZ

```text
HUMAN DECISION = CONDITIONAL BUY
FIRST TRANCHE = around CNY30/share
ACTION = NOT YET EXECUTED
EVALUATION WINDOW = ~3–6 months after actual execution
```

Price can satisfy the condition only if core revenue / margin / cash conversion / capex / ROIC remain intact. Robot / liquid-cooling optionality must not become necessary Base.

### GigaDevice / 603986.SH

```text
HUMAN DECISION = CONDITIONAL BUY
around CNY350 = assumption review
CNY320–335 = first-entry band only if thesis survives
ACTION = NOT YET EXECUTED
PROBABILITY = PARTIAL / ORDINAL_ONLY
fresh Numerical Odds = WITHHELD under current Decision Hygiene state
```

Do not treat CNY350 as automatic buy. It wakes assumptions; 320–335 only permits a first tranche if those assumptions survive.

### Micron / MU

```text
HUMAN DECISION = WAIT / DO NOT BUY FOR NOW
reason = Human temporarily not buying U.S. equities
reason != bearish Micron Belief
ACTION = NO_ACTION
NEXT VALIDATION = 2026-09-30 FY2026/FQ4 earnings
```

No production U.S. ObservedMarket / Numerical Odds through current A-share HiThink runtime.

### YTO / 600233.SH

```text
HUMAN DECISION = NONE
ACTION = NONE
PROBABILITY = NOT ESTABLISHED
NUMERICAL ODDS = WITHHELD
PRICE TRIGGER = NONE
```

Evidence-driven only; use frozen `QUIET / REOPEN / FRAME CHANGE` trigger design.

### Midea / 000333.SZ

```text
HUMAN DECISION = NONE
ACTION = NONE
PROBABILITY = PARTIAL / ORDINAL_ONLY
NUMERICAL ODDS = WITHHELD
PRICE TRIGGER = NONE
```

Primary analytic language is owner-return decomposition via retention × incremental ROIC, dividends, true net share shrinkage, duration and valuation.

### Xiamen Tungsten / 600549.SH

Negative control / process guard, not current action candidate.

Do not retrospectively create decisions, actions, prices or outcomes for any of the above.

---

## 10. Prospective Human Decision / Action / Outcome protocol

Human Decision must be explicit commitment wording, for example:

- `我决定买`
- `这只不买 / PASS`
- `继续持有，不加仓`
- `卖掉`
- `我决定先不做，等X`

Not sufficient:

- “继续” / “做吧” about repo work;
- approving Research;
- approving probability arithmetic;
- merging a PR;
- asking a buy price;
- hypothetical language;
- a Human wake surface.

Decision and Action are separate.

Never infer Action from a Decision or from a price band.

If the Human confirms a real execution, that becomes top priority:

1. create separate Action checkpoint;
2. preserve exact Human-confirmed execution timestamp / price / size;
3. bind prior explicit Decision and latest Research lineage used at execution;
4. record deviations without editing the original Decision;
5. preserve the prospective evaluation horizon.

The most valuable missing project sample is currently:

```text
PIT Research
-> explicit Human Decision
-> confirmed Action
-> later Outcome
-> Attribution
```

Do **not** infer old broker trades into this chain retrospectively.

---

## 11. Research Method refinements that must not regress

### Economic Species Playbook correction

It is an **underwriting-language selector**, not taxonomy / routing.

Do not think:

```text
classify company as species
-> apply template
```

Think:

```text
what uncertainty is load-bearing?
-> choose the least falsely precise analytic language
```

### Analysis Divergence

Use only when Reference Frame uncertainty changes causal model class / terminal economics.

- GigaDevice = positive control.
- Midea = negative control; strategic narratives mostly collapse into the same owner-return equation.
- Correlated frames are not independent votes.
- convergence != truth / confidence;
- divergence != automatic probability failure.

### Source discipline

Remember:

> `citation correctness != source admissibility != belief integration`

Sell-side is useful for hypotheses / expectations / analyst model / opinion, not as substitute for realized company economics.

Useful shorthand:

> `研报负责告诉我该查什么，一手资料负责告诉我发生了什么。`

### Research quality can reduce conviction

Valid end state:

```text
Research complete enough = YES
Probability = NOT ESTABLISHED
Numerical Odds = WITHHELD
```

Do not force a 100% probability distribution merely because the schema can represent one.

---

## 12. Market-data and automation boundaries

- HiThink remains sole production A-share market-data source.
- No fallback / provider registry / provider abstraction for convenience.
- Public web prices are `MARKET_CONTEXT`, not production `ObservedMarket`.
- Do not leak HiThink API key.
- Existing weekday `decision-inbox` automation is legitimate and should not be removed merely because “no new automation without Human request.”
- Do not add new automation unless Human explicitly requests it.
- Surprise Radar shadow sampling piggybacks on existing workflow; do not create a parallel scheduler.

Scheduled Inbox currently uses curated Human-facing packages; shadow history and disclosure acquisition may have a broader non-authoritative universe.

This distinction is intentional.

---

## 13. What to do next

Default next-step priority:

### Priority A — real Radar / prospective events

Watch for:

- real new official disclosures that hit frozen commitments;
- naturally accumulated Surprise Radar windows;
- a genuine market/fundamental mismatch that deserves Quick Research;
- a real Human trade execution;
- later Outcome / attribution.

These outrank method work.

### Priority B — if Human asks to inspect today’s Radar

Do not say “nothing happened” merely because there was no price alert.

Distinguish:

```text
Price Surprise alert
Commitment / disclosure progress
Human Inbox / Odds attention
system integration failures
```

2026-09-03 specifically:

- no validated price Surprise alert;
- CATL buyback progress touched an existing commitment but did not resolve cash-deployment / FCF economics;
- Sanhua new H-share disclosure did not support thesis escalation;
- stale CMB Odds reaching Human Inbox was a real product failure and is now fixed / verified.

### Priority C — Surprise Radar detector only after real labels

Do not build a detector just because the history input exists.

First collect real A/B/C examples (true useful anomaly / noisy large move / missed quiet precursor). Then dogfood a shadow-only detector with no Human authority.

### Priority D — new case only when reality earns it

Do not continue “financial / commodity / utility / biotech / next species...” category collection.

New Full Case should be generated by Radar or a real method mismatch.

---

## 14. Explicit do-not-do list

Do not:

- treat this handoff above current `main`;
- turn Decision Kernel into a Truth Machine or recommendation engine;
- create `EconomicSpecies` enum/router;
- create mandatory multi-agent Analysis Divergence;
- count correlated Frames as votes;
- treat convergence as confidence or divergence as automatic probability veto;
- build a common preprocessed expectation envelope before independent Frame underwriting;
- add AlphaAnalyst dependency;
- reduce Claim Audit to “tag exists”;
- invent generic confidence scores;
- invent source provenance for derived numbers;
- let one valid citation launder neighboring unsupported numerical clauses;
- add Claim Audit v3 / DerivedClaim / generic provenance service without real repeated failure;
- infer semantic warrant mechanically from source presence alone;
- invent a source-disagreement framework without a real same-quantity case;
- abstract recent YTO-only test helpers merely because they repeat;
- redesign Odds policy now just because #110/#111 found a real problem;
- create a second Human wake gate for Radar;
- use directory wildcard as scheduled Human Inbox eligibility;
- delete useful historical fixtures merely because they lose Human-facing standing;
- infer Human Decision from “继续 / 做吧”, Research approval, PR merge, price discussion or wake surface;
- infer Action from Decision, a price band, or nearby trade-like evidence;
- create Kernel-owned broker / portfolio ledger;
- use U.S. public web prices for production Numerical Odds;
- add market-data fallback / provider abstraction;
- add a new scheduler for Surprise Radar;
- create anomaly thresholds from one day or synthetic-only series;
- retrospectively alter frozen Sanhua / Giga / Micron decisions;
- invent YTO / Midea buy points for symmetry;
- pretend current methods are proven correct merely because test suites are green.

---

## 15. Fast restart checklist for the next conversation

If the next Human message is simply `继续` / `做吧`:

1. re-read latest `main` / recent commits first;
2. check whether a real prospective event has occurred since this handoff;
3. if a Human Action was explicitly confirmed, prioritize Action capture immediately;
4. otherwise inspect current Radar run / disclosures / shadow observations if relevant;
5. do not resume method/schema construction by inertia;
6. if no real event exists, it is acceptable to stop rather than fabricate another experiment.

If the Human asks “今天 Radar 有什么？”:

- query actual workflow runs / artifacts first;
- distinguish `NO RUN`, `QUIET`, `NO VALIDATED SURPRISE ALERT`, and `REAL DISCLOSURE / COMMITMENT PROGRESS`;
- never substitute stale previous-day output for a current run.

If the Human asks “下一步做什么？”:

> **优先等现实：Radar surprise、commitment resolution、真实 Action、Outcome。没有这些，就不要为了保持开发速度继续长 schema。**

---

## 16. Recent merge chronology to preserve

Important recent sequence:

```text
#105  previous 2026-09-03 handoff
#106  derived-number Claim Audit lineage
#107  numeric-clause fail-closed Claim Audit
#108  multi-source Claim Audit preservation
#109  Claim Audit mechanical-integrity health checkpoint
#110  Odds Validity Audit v0
#111  real CMB Odds semantic replay
#112  Commitment Radar v0 exact lineage
#113  qualified HiThink history foundation
#114  Surprise Radar short-lived shadow sampling
#115  CMB financial-institution underwriting stress test
#116  Shandong Gold resource underwriting stress test
#117  Ninghu finite-concession underwriting stress test
#118  BeOne pipeline optionality underwriting stress test
#119  heterogeneous case coverage checkpoint
#120  scheduled Inbox stale Odds eligibility fix
```

Current `main` before this handoff commit:

`0102e69f5062d0e5e2d6e5070d562c11c9dbde8e`

---

## 17. Closing operating stance

The project is now more likely to improve from **new reality** than from another round of internal framework polishing.

Use this default:

```text
new reality
-> Radar input
-> Human / Research triage
-> Research only if earned
-> freeze commitments
-> later commitment resolution
-> explicit Human Decision if any
-> explicit Action if any
-> later Outcome
-> attribution
-> only then reconsider Kernel / Odds / Constitution when the evidence demands it
```

The desired product feeling is still:

> **打开系统以后，我更清楚今天该看什么，也更清楚什么根本不用看。**
