# Prospective Human Decision / Outcome Capture Protocol — 2026-09-03

Status: **ZERO-SCHEMA OPERATING PROTOCOL / NO KERNEL CONSTITUTION CHANGE**  
Repository: `auguspp/decision-kernel`  
Predecessor: `docs/decision-hygiene-constitution-review-checkpoint-2026-09-03.md`  
Recorded: **2026-09-03**

## Purpose

The Decision Hygiene Constitution-review checkpoint found a specific missing evidence class:

```text
PIT Research
→ explicit Human Decision
→ Action / No Action
→ later Outcome
→ Attribution
```

The historical repository contains strong Research and review lineage, but it does not contain a clean investment case with the complete chain needed to test whether forced cardinal probability improved or degraded an actual Human decision.

The next step is therefore **not** another schema, lifecycle, watcher, or Outcome subsystem.

It is a behavioral protocol:

> **When the Human actually makes an investment decision, freeze enough contemporaneous context that later outcome review cannot rewrite what was known, what was decided, or what standard the decision was supposed to satisfy.**

This protocol is deliberately zero-schema.

It does not create:

- a `HumanDecision` Kernel entity;
- an `Outcome` Kernel entity;
- a new state machine;
- a second Human wake gate;
- a recommendation engine;
- an execution system;
- an automation or scheduled monitor;
- a probability-readiness enum;
- a new source/provider abstraction;
- any investment authority.

Repository Markdown + immutable Git history are sufficient for the first prospective cases.

If repeated real cases later prove that manual capture corrupts identity, PIT, lineage, or attribution, the smallest structured representation can be reconsidered then.

---

## 1. Existing Kernel semantics remain authoritative

Current Kernel artifacts stop before a Human investment decision.

`DecisionRehearsalArtifact` explicitly declares:

```text
DECISION_REHEARSAL_ONLY
HUMAN_DECISION_REQUIRED
NO_SYSTEM_INVESTMENT_DECISION
NO_POSITION_SIZE_OR_TARGET_WEIGHT
Investment Authority = NONE
```

`HumanDecisionBrief` is a projection of frozen Research + Odds + Decision Rehearsal for Human review.

It is **not** proof that a Human decision occurred.

`HumanResearchSurface` is the only Kernel-owned Human wake surface. Its status and `attention_eligible` value remain the sole wake gate.

Therefore:

```text
DecisionRehearsal != Human Decision
HumanDecisionBrief != Human Decision
HumanResearchSurface != Human Decision
attention_eligible == true != Human Decision
review / discussion != Human Decision
```

A prospective Human-decision record may reference those exact frozen artifacts.

It must not mutate their semantics or pretend to be a Kernel artifact.

---

## 2. Trigger rule — never infer a Human Decision

Create a prospective decision capture only when the Human explicitly communicates an investment decision.

Examples that are sufficient in ordinary language:

- “我决定买。”
- “这只不买，PASS。”
- “继续持有，不加仓。”
- “卖掉。”
- “我决定先不做，等 X。”
- “我接受这个仓位 / 不接受这个仓位。”

The exact Human wording should be preserved where practical.

The following are **not** sufficient:

- “这个研究我同意。”
- “这个概率分布可以。”
- “这个 Odds 算法没问题。”
- “有意思。”
- “继续。”
- “可以合并。”
- approving a PR;
- approving a ResearchSnapshot;
- approving participation-zone arithmetic;
- asking for a buy price;
- asking what the system would do;
- receiving `DECISION_WORTHY_REVIEW`;
- discussing hypothetical position sizing.

Rule:

> **If a reasonable observer could read the Human statement as approval of research rather than commitment to an investment choice, do not freeze it as a Human Decision.**

No semantic guesswork should manufacture longitudinal evidence.

---

## 3. Human Decision and Action are separate

A decision is not an execution receipt.

Examples:

```text
Decision = BUY
Action = NOT YET EXECUTED
```

```text
Decision = PASS / DO NOT BUY
Action = NO_ACTION
```

```text
Decision = SELL
Action = PARTIALLY EXECUTED
```

```text
Decision = HOLD / NO CHANGE
Action = NO_TRADE
```

The protocol should preserve the distinction because later attribution differs:

- a good decision can be badly executed;
- a bad decision can accidentally receive a favorable price move;
- a no-action decision can be intentional rather than forgotten;
- an execution constraint can prevent Action without changing Fundamental Belief;
- a later Action can occur at a materially different price and therefore different Odds.

Do not infer Action from Decision.

Do not infer Decision from a broker fill or portfolio change without explicit Human confirmation of what investment choice that Action represented.

---

## 4. Capture at the decision PIT

When the Human explicitly makes a decision, freeze a small Markdown checkpoint as close to that decision PIT as practical.

The checkpoint should reference rather than duplicate existing immutable artifacts.

Minimum capture:

```text
IDENTITY
- security / expression
- decision timestamp / PIT cutoff

RESEARCH CONTEXT
- exact ResearchSnapshot id
- exact information_bundle_hash
- Research version / file locator
- core thesis at that PIT
- thesis falsifiers / material unresolved questions

MARKET / ODDS CONTEXT
- ObservedMarket timestamp
- market price
- market data source
- Odds artifact id + hash, if numerical Odds legitimately existed
- ParticipationZone, if applicable
- valuation horizon / holding-period semantics

HUMAN CONTEXT
- exact or faithfully preserved Human decision wording
- normalized descriptive summary for navigation only
- Action / No Action state as explicitly known
- decision reason in the Human's own terms if stated
- explicit constraints that affected the choice

EVALUATION CONTRACT
- evaluation horizon or review event
- what evidence would count as thesis support / falsification
- what would make the decision look well-founded, poorly founded, or still unresolved
- what must NOT be used as a shortcut for attribution
```

This is an audit checkpoint, not a recommendation record.

---

## 5. Evaluation horizon must be frozen before outcome

A later outcome cannot be evaluated fairly if the horizon is selected after seeing the price path.

Prefer one of these forms:

### Calendar horizon

```text
Evaluate at: 2027-09-03 close
```

### Fundamental-event horizon

```text
Evaluate after FY2027 audited results are public
```

### Thesis-resolution horizon

```text
Evaluate after two quarters of the declared unit-economics / margin / order / cash-flow evidence
```

### Dual horizon

When both investment return and thesis maturation matter:

```text
Market-return checkpoint: 12 months
Fundamental checkpoint: FY2027 audited results
```

Do not silently extend the horizon because the outcome is inconvenient.

If the original decision itself explicitly allowed a range, freeze that range.

If no meaningful horizon can be declared, record that limitation at the decision PIT rather than inventing one later.

---

## 6. Predeclare what “wrong” means

A stock going down after BUY does not automatically prove the decision was wrong.

A stock going up after PASS does not automatically prove the decision was wrong.

Price is an outcome observation, not attribution.

Before outcome, the capture should state the relevant adjudication questions.

At minimum:

### Fundamental judgment

Did the causal thesis and its material world assumptions evolve roughly as expected?

### Valuation / Odds judgment

Given what was knowable at the decision PIT, did the price paid / refused offer the intended payoff asymmetry over the declared horizon?

### Human decision judgment

Was the chosen action consistent with the Human's explicitly stated risk, return, uncertainty, and capital-allocation requirements?

### Action judgment

Was the decision implemented as intended, at a price and timing consistent with the decision?

### Counterfactual discipline

Would an alternative decision have been genuinely available at the PIT, or is it being invented after the outcome?

The record may later conclude:

```text
GOOD DECISION / BAD OUTCOME
BAD DECISION / GOOD OUTCOME
GOOD DECISION / GOOD OUTCOME
BAD DECISION / BAD OUTCOME
STILL UNRESOLVED
INSUFFICIENT EVIDENCE TO ATTRIBUTE
```

These are explanatory phrases in the protocol, **not production enums**.

---

## 7. Price-return outcome is necessary but insufficient

When a market outcome is reviewed, preserve the actual price observations using the production market-data boundary.

For A-share production price observations:

```text
HiThink remains the sole production market-data source.
```

Do not introduce a fallback price provider merely for retrospective convenience.

Market outcome should normally include:

- decision-PIT price / exact convention;
- action price if an Action occurred;
- evaluation-horizon price;
- dividends / distributions when economically relevant and reliably captured;
- split / corporate-action treatment if relevant;
- nominal cumulative return semantics;
- comparison horizon.

But a market return should not overwrite the original ResearchSnapshot or probability beliefs.

Outcome evidence is new later evidence.

It belongs to the later review PIT.

---

## 8. Fundamental outcome is separate from price outcome

A later review should ask what happened to the business, not merely the stock.

Useful outcome observations include case-specific realized evidence such as:

- revenue / unit economics;
- gross margin / operating margin;
- volume / share;
- order conversion;
- capital intensity;
- OCF / FCF;
- ROIC;
- franchise / channel economics;
- product commercialization;
- regulatory state;
- dilution / capital allocation;
- falsifier realization.

Current source policy already recognizes `REALIZED_OUTCOME` as a claim-level assertion scope.

That semantic may be used for evidence admissibility where applicable.

It does **not** create an investment-Outcome object.

The later attribution note may simply cite the exact new evidence and explain what it resolved.

---

## 9. Probability-qualified versus probability-withheld cases

The prospective protocol exists partly to test the Constitution-review hypothesis.

Therefore the decision PIT should preserve which epistemic state actually existed.

### Case A — cardinal probability genuinely qualified

If the Human intentionally accepts a frozen cardinal scenario distribution as qualified Research:

```text
ResearchSnapshot
→ numerical Odds
→ Decision Rehearsal
→ Human Surface
→ Human Decision
```

Capture the exact production artifacts normally.

### Case B — Decision Hygiene says cardinal probability is not qualified

If Research is decision-useful but Decision Hygiene explicitly withholds a full cardinal measure:

freeze the Decision Hygiene conclusion as such.

If the current production Kernel requires a complete distribution for a comparison artifact, the closest cardinal construction may be preserved only as a **counterfactual**.

That counterfactual must be labeled:

```text
PRODUCTION-COMPATIBLE CARDINAL COUNTERFACTUAL
NON-DRIVING
NOT A RECOMMENDATION
NOT HUMAN BELIEF UNLESS THE HUMAN EXPLICITLY ADOPTS IT
```

It must not be used to backfill the Human's decision reason after the fact.

This creates the prospective controlled comparison requested by the Constitution-review checkpoint without changing Kernel schema.

---

## 10. Counterfactual must be frozen before outcome

A useful counterfactual cannot be created after seeing the result.

If a probability-withheld case is intended to contribute to Constitution review, freeze before outcome:

1. the actual Decision Hygiene Research state;
2. the exact unsupported / partially supported probability knowledge that was available;
3. the closest production-compatible cardinal counterfactual, if one is constructed;
4. the resulting hypothetical numerical Odds from that counterfactual, if mechanically available;
5. an explicit statement of whether the Human saw it and whether it influenced the decision.

Preferred strongest design:

```text
Human decision reason is frozen first from the qualified Research state.
Counterfactual is frozen as non-driving comparison evidence.
```

If the Human does inspect the counterfactual before deciding, record that contamination honestly.

Do not pretend the Human was blind to information they actually saw.

---

## 11. No fake probability to create a cleaner experiment

The experiment must not create the pathology it is supposed to test.

A counterfactual cardinal distribution may be constructed only when it is a plausible representation of how the current production path would otherwise have been completed.

Do not deliberately choose absurd weights so the probability-withheld method looks superior.

Do not optimize weights to current price.

Do not optimize weights to the Human's desired answer.

Do not change live Odds thresholds.

Do not import broad market weakness into Fundamental Belief merely to make the counterfactual conservative.

Do not turn “unknown” into a mechanically large model-risk addon unless current policy already requires it.

---

## 12. Human decision reason should not be rewritten by the assistant

The assistant may compress or organize the Human's reason, but the record should preserve enough original wording to distinguish:

```text
Human reason
from
assistant reconstruction
```

For a material decision, prefer:

```text
Human wording:
"..."

Audit summary:
- ...
```

The summary has navigation value only.

If the Human does not state a reason, record:

```text
Human reason = NOT EXPLICITLY STATED
```

Do not infer a rationale from Research merely because it would sound coherent.

---

## 13. Decision constraints must not be laundered into Belief

Execution and portfolio constraints may affect the Human decision without being bearish or bullish evidence.

Examples:

- market-access eligibility;
- liquidity requirements;
- available capital;
- tax / account constraints;
- existing concentration;
- inability to trade a market;
- operational timing.

Record them as decision/action constraints.

Do not project them backward into Fundamental Belief.

Historical YMTC lineage is an important precedent: STAR Market eligibility was separate from the investment judgment and must remain so.

---

## 14. No-action decisions deserve full capture when explicit

`NO_ACTION` is not absence of data when it is the chosen action.

Examples:

```text
Decision = PASS / DO NOT BUY
Action = NO_ACTION
```

or:

```text
Decision = HOLD / WAIT FOR EVIDENCE X
Action = NO_TRADE
```

These cases are especially valuable for learning because later temptation to call every rally a “miss” is strong.

A PASS followed by +50% does not automatically mean the decision was bad.

Questions include:

- did the favorable outcome depend on a world that was reasonably knowable at the PIT?
- did the price at the PIT satisfy the Human's return requirement under qualified evidence?
- was the uncertainty intentionally outside the Human's mandate?
- was the security actually executable?
- what capital alternative was available?
- did the later gain arrive through an exogenous re-rating rather than the rejected thesis?

Do not turn opportunity regret into epistemic attribution.

---

## 15. Buy decisions are not vindicated by short-term rallies

The symmetrical error also matters.

A BUY followed by a rally may still have been a poor decision if:

- the thesis was wrong but beta / liquidity drove the price;
- downside risk was misunderstood;
- the chosen price offered poor ex-ante payoff asymmetry;
- an unmodeled speculative multiple expansion generated the gain;
- the Action violated the Human's stated sizing / concentration constraints;
- the outcome horizon is much shorter than the thesis horizon.

Likewise, a BUY followed by a decline may remain a defensible decision if the thesis remains intact and the declared horizon has not resolved.

Outcome and decision quality must remain separable.

---

## 16. Later outcome review protocol

At the predeclared horizon or genuine thesis-resolution event, create a new later-PIT attribution note.

Do not edit the original decision checkpoint.

The later note should reference the original Git commit / decision checkpoint and ask in order:

1. **Evidence Failure** — were material source records wrong or unreliable?
2. **Classification Failure** — did we grant a claim an invalid epistemic role or assertion scope?
3. **Reference Frame Failure** — was the business understood through the wrong model class?
4. **Inference Failure** — were observations correct but causal transmission misunderstood?
5. **Assumption Failure** — did a declared future-state assumption fail?
6. **Probability Failure** — were the worlds reasonable but probability qualification / weighting badly calibrated?
7. **Valuation Failure** — was business judgment broadly right but value / horizon / terminal economics wrong?
8. **Odds Failure** — was Fundamental Belief reasonable but price / payoff asymmetry poor?
9. **Human Decision Failure** — did the Human choose inconsistently with their own declared objective or constraints despite a reasonable surface?
10. **Action Failure** — did execution materially diverge from the decision?
11. **Exogenous Surprise** — only after the above have been inspected.

This ordering is not a production workflow.

It is an anti-excuse discipline.

---

## 17. Probability failure must not absorb upstream mistakes

A later bad result should not automatically be labeled `Probability Failure` merely because a 20% world occurred.

First ask:

- was the Reference Frame wrong?
- was a material world omitted entirely?
- were the causal worlds incoherent?
- was a source misclassified?
- was terminal value wrong independently of scenario incidence?

Only after the world set and model class survive review does probability calibration become the primary suspect.

This matters directly to the Constitution question.

If forced cardinal probability repeatedly looks bad only because upstream Research is bad, decoupling Research freeze from probability certification may not solve the real problem.

---

## 18. Valuation and Odds failure must be separated

Later attribution should distinguish:

```text
Valuation Failure
= our translation from business world to value was wrong
```

from:

```text
Odds Failure
= value map may have been reasonable, but participation at the actual price was unattractive
```

and from:

```text
Action Failure
= decision may have been reasonable, but execution occurred at a materially different price
```

This protects the core doctrine:

> Evidence changes Belief; price changes Odds.

---

## 19. Minimal manual decision-capture template

Use this only after an explicit Human investment decision.

It is a Markdown aid, not schema.

```markdown
# Prospective Human Decision Checkpoint

Status: FROZEN PIT / HUMAN DECISION CAPTURE / ZERO-SCHEMA

## Identity
- Security / expression:
- Decision PIT cutoff:
- Recorded at:

## Frozen Research context
- ResearchSnapshot id:
- information_bundle_hash:
- Research locator / version:
- Reference Frame:
- Core thesis:
- Material falsifiers:
- Decision-critical unresolved variables:
- Probability qualification actually supported:

## Frozen market / Odds context
- ObservedMarket timestamp:
- Price:
- Source:
- Odds artifact id/hash, if legitimately available:
- ParticipationZone, if applicable:
- Valuation / holding horizon:

## Human Decision
- Human wording:
- Audit summary:
- Human reason explicitly stated? YES / NO
- Decision constraints explicitly stated:

## Action
- Action state explicitly known:
- Execution price/time if already occurred:
- Execution constraints:

## Prospective evaluation contract
- Market-return horizon:
- Fundamental / thesis-resolution horizon:
- What would support the thesis:
- What would falsify / materially weaken it:
- What would count as a decision-quality failure:
- What would remain unresolved:
- What must NOT be treated as proof by itself:

## Decision Hygiene counterfactual, if applicable
- Actual qualified state:
- Cardinal production-compatible counterfactual:
- Counterfactual Odds:
- Human exposure to counterfactual before decision:
- Explicitly NON-DRIVING? YES / NO / CONTAMINATED

## Authority
- Research != Recommendation
- Odds != Recommendation
- Decision Rehearsal != Human Decision
- Human decision was explicitly supplied by the Human
- Investment Authority = NONE for the system
```

Do not pre-populate `Human wording` or decision reason from assistant inference.

---

## 20. Minimal later outcome / attribution template

Create a new file; never rewrite the original decision checkpoint.

```markdown
# Human Decision Outcome / Attribution Review

Status: LATER PIT / OUTCOME REVIEW / ZERO-SCHEMA

## Lineage
- Original decision checkpoint:
- Original ResearchSnapshot:
- Original Odds artifact, if any:
- Original Action state:
- Original evaluation contract:

## Realized market outcome
- Evaluation timestamp:
- Price / distribution observations:
- Market-data source:
- Return calculation and convention:

## Realized fundamental outcome
- New realized evidence:
- Original falsifiers triggered / not triggered / unresolved:
- Original decision-critical uncertainties resolved / unresolved:

## Action outcome
- Intended action:
- Actual action:
- Execution deviation:

## Attribution review
- Evidence Failure:
- Classification Failure:
- Reference Frame Failure:
- Inference Failure:
- Assumption Failure:
- Probability Failure:
- Valuation Failure:
- Odds Failure:
- Human Decision Failure:
- Action Failure:
- Exogenous Surprise:

## Synthesis
- Decision quality:
- Outcome quality:
- What the process should change:
- What the process should explicitly NOT change:
```

Again, the labels are analytical headings, not enums.

---

## 21. Strict negative-control eligibility

A future case counts as a strict Decision Hygiene negative control only if all material elements existed before outcome contamination.

Checklist:

```text
[ ] PIT Research lineage frozen
[ ] Human Decision explicitly stated and frozen
[ ] Action / No Action frozen separately
[ ] evaluation horizon / event frozen prospectively
[ ] decision-quality adjudication questions frozen prospectively
[ ] market price / Odds context frozen at decision PIT
[ ] probability qualification state frozen
[ ] if relevant, cardinal counterfactual frozen before outcome
[ ] Human exposure to counterfactual recorded honestly
[ ] later Outcome captured from new evidence
[ ] attribution performed without rewriting original artifacts
```

A case failing the checklist may still be useful historical learning.

It should not be promoted to strict controlled evidence for a Constitution change.

---

## 22. What would qualify the Constitution hypothesis

The prospective cases are not designed to “prove” that the Constitution must change.

They should discriminate both directions.

Evidence **for** eventual decoupling could include repeated cases where:

- Research was causally mature and decision-useful;
- cardinal probability was explicitly unqualified;
- production-compatible cardinal counterfactuals nevertheless created material false conviction or misleading Odds;
- probability-withheld surfaces better preserved uncertainty and later attribution;
- the Human decision process benefited from freezing Research before probability was available.

Evidence **against** decoupling could include repeated cases where:

- probability withholding mainly concealed unresolved causal research;
- forcing a complete distribution exposed contradictions that materially improved Research;
- cardinal counterfactuals were reasonably calibrated and useful;
- a separate Research freeze created complacent “complete enough” labels without improving decision quality;
- the current invariant did not actually cause operational corruption.

The protocol must be capable of falsifying the preferred architecture hypothesis.

Otherwise it is not an experiment.

---

## 23. No automatic monitoring

This protocol does not authorize:

- an automation;
- a scheduled price check;
- an earnings watcher;
- an Outcome daemon;
- a recurring GitHub workflow;
- a notification system.

Later outcome capture occurs when the Human explicitly asks to review the case, when a naturally authorized research workflow revisits it, or when another separately authorized process supplies the relevant later-PIT evidence.

Do not create hidden ongoing work.

---

## 24. No new Human wake semantics

The protocol applies **after** an explicit Human investment decision.

It does not decide when the Human should be awakened.

The sole Kernel wake gate remains:

```text
HumanResearchSurface.status + attention_eligible
```

Decision capture must never become:

- a second wake gate;
- a reason to surface low-Odds cases;
- a probability-readiness gate;
- a portfolio reminder engine.

---

## 25. No new investment authority

Nothing in this protocol grants the system permission to:

- decide BUY / SELL / HOLD;
- choose position size;
- execute an order;
- reinterpret silence as approval;
- convert Decision Rehearsal into Recommendation;
- convert a Human decision into system authority for a different security or later PIT.

The authority statement remains:

```text
Investment Authority = NONE
```

A Human decision is evidence of what the Human decided.

It is not delegated authority for the assistant to make future decisions.

---

## 26. Operational behavior for the assistant

When a real case reaches an explicit Human decision, the preferred assistant behavior is:

1. recognize the decision only if explicit;
2. do not ask the Human to repeat information already present;
3. recover the exact frozen Research / Odds lineage;
4. preserve the Human wording and separately summarize it;
5. capture Action / No Action separately;
6. infer no unstated investment rationale;
7. use a concrete evaluation horizon already stated by the Human or inherent in the frozen Research horizon; if neither exists, record the limitation rather than fabricate certainty;
8. freeze the prospective checkpoint in a small auditable PR / commit when repository capture is authorized by the ongoing workflow;
9. do not start monitoring;
10. later, on an authorized revisit, create a new attribution artifact rather than editing history.

Within an already authorized case workflow, complete the natural capture chain rather than returning with “the next step would be to record it.”

---

## 27. Current disposition

```text
ZERO-SCHEMA PROSPECTIVE CAPTURE = AUTHORIZED AS METHOD / DOCUMENTATION
HUMAN DECISION ENTITY = NONE
OUTCOME ENTITY = NONE
NEW STATE MACHINE = NONE
NEW WAKE GATE = NONE
AUTOMATION = NONE
LIVE ODDS POLICY CHANGE = NONE
MARKET PROVIDER CHANGE = NONE
PRODUCTION INBOX CHANGE = NONE
INVESTMENT AUTHORITY = NONE
```

The next real Human investment decision can now become valid longitudinal evidence without requiring a Kernel redesign first.

The key discipline is simple:

> **Freeze the decision standard before the result. Freeze the result later. Attribute the difference without rewriting either.**
