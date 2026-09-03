# Decision Accounting / Human Response Gap Review — 2026-09-03

Status: **FROZEN METHOD REVIEW / DOCS-ONLY / NO KERNEL SCHEMA CHANGE / NO EXECUTION LEDGER / NO AUTOMATION**  
Repository: `auguspp/decision-kernel`  
Parent protocol: `docs/prospective-decision-outcome-capture-protocol-2026-09-03.md`  
External comparison: `longsizhuo/openInvest` Decision Accounting documentation  
Recorded: **2026-09-03**

---

## 0. Purpose

The current prospective protocol already preserves a clean investment-decision chain:

```text
PIT Research
-> explicit Human Decision
-> Action / No Action
-> later Outcome
-> Attribution
```

An external comparison with openInvest raises a narrower question:

> **Is there decision-useful information in the Human's explicit response to a surfaced research / decision-use artifact that is not always identical to either a Human investment decision or an execution record?**

This review asks whether a very thin `Human Response` audit layer would improve longitudinal learning without turning Decision Kernel into a Portfolio OS.

It does not create:

- a `HumanResponse` Kernel entity;
- a new state machine;
- a trade ledger;
- broker / portfolio ingestion;
- order or fill ownership;
- adoption-rate metrics;
- automatic decision-action matching;
- a new Human wake gate;
- an automation;
- any investment authority.

---

## 1. What openInvest gets right

openInvest's documented Decision Accounting joins several existing records:

```text
committee decision
<-> rule intervention
<-> user execution / rejection
<-> later result
```

It also exposes explicit write-back of execution / rejection plus reason.

The useful idea for Decision Kernel is not the committee verdict or CIO authority.

It is the longitudinal question:

> **After a decision-use surface reached the Human, what did the Human explicitly do with it?**

That can eventually help distinguish:

- Research that was useful and acted on;
- Research that was explicitly rejected;
- Research that was deferred pending evidence;
- Research that produced an intentional no-action choice;
- Research that was superseded before action;
- outcomes caused by the thesis versus outcomes never exposed to a Human commitment.

This is potentially valuable for proving whether the system reduces bad decisions rather than merely producing clean research artifacts.

---

## 2. What must be rejected from the external pattern

openInvest documents a fallback linkage rule when no explicit decision linkage exists:

> match a trade occurring within seven days after the decision when symbol and direction align.

Decision Kernel must reject this category of heuristic.

Rule:

```text
same ticker
+ same direction
+ nearby time
!= proof of Action lineage
```

Why:

- the Human may have acted for a different thesis;
- the Human may have changed their mind for new evidence;
- a portfolio action can have tax, liquidity, concentration or operational motives;
- an apparent fill may only partially represent the prior decision;
- a later trade can occur at materially different Odds;
- automatic matching silently converts correlation into causal attribution.

The existing prospective protocol is stricter and should remain so:

> **Never infer Decision from Action; never infer Action from Decision.**

Any longitudinal accounting must preserve that boundary.

---

## 3. Current protocol already solves more than it first appears

The existing prospective protocol already captures:

### Explicit Human investment decision

Examples:

```text
BUY
PASS / DO NOT BUY
HOLD / NO CHANGE
SELL
WAIT FOR EVIDENCE X
```

### Decision reason and constraints

It preserves Human wording where possible and keeps execution / mandate constraints separate from Fundamental Belief.

### Action / No Action separation

It explicitly allows:

```text
Decision = BUY
Action = NOT YET EXECUTED
```

and:

```text
Decision = PASS
Action = NO_ACTION
```

### Later attribution

It separately reviews Research, Reference Frame, inference, probability, valuation, Odds, Human decision and Action failure.

Therefore the missing layer is **not** a broad Decision Accounting subsystem.

The only plausible gap is narrower:

> **an explicit Human response to a surfaced artifact when that response is useful longitudinal evidence but does not cleanly constitute a new investment decision or an execution record.**

---

## 4. Where a Human Response layer could add information

Potential examples:

### A. Explicit rejection of a surfaced research direction

```text
Surface reaches Human
Human: "这条先不研究 / 这个 frame 我不接受，原因是 X"
```

This may matter for Research-method learning without being an investment decision.

### B. Explicit deferral

```text
Human: "先不决定，等下一季毛利 / 订单 / capex 数据"
```

Sometimes this is itself a `WAIT` investment decision and should use the existing decision protocol.

Other times it is only a response to the research workflow.

The distinction must be preserved rather than normalized away.

### C. Explicit no-action response to attention

```text
Human: "看到了，但现在不需要动作"
```

If this clearly commits to an investment choice, capture it as a Human Decision.

If it only acknowledges the surface, do not manufacture a decision.

### D. Explicit supersession

A later Human statement can replace a prior research response or prospective decision before any action occurs.

The original record should remain immutable; the later response should reference it rather than editing history.

---

## 5. Proposed v0 vocabulary — human research language only

If a future real case demonstrates value, the first experiment may use a tiny documentation vocabulary:

```text
ACTED
REJECTED
DEFERRED
NO_ACTION
SUPERSEDED
```

These are **not schema values** and should not yet be normalized into production state.

### ACTED

Meaning:

> The Human explicitly states that they took an action in response to the relevant decision-use context.

Important limitation:

```text
ACTED
!= broker fill proof
!= exact execution price
!= exact size
!= complete portfolio lineage
```

If exact execution becomes decision-critical, it belongs in a separate prospective Action / audit artifact with Human-confirmed details, not inferred from this response label.

### REJECTED

Meaning:

> The Human explicitly rejects the surfaced proposal, frame, condition or prospective investment choice.

This does not automatically mean bearish Fundamental Belief.

### DEFERRED

Meaning:

> The Human explicitly postpones further judgment until a stated event, evidence item or condition.

If the language clearly constitutes an investment decision (`WAIT / DO NOT BUY UNTIL X`), the existing Human Decision protocol remains authoritative.

### NO_ACTION

Meaning:

> The Human explicitly chooses no action at the current PIT.

Again, when this is clearly an investment decision, it should be captured as such rather than demoted to a response tag.

### SUPERSEDED

Meaning:

> A later explicit Human response or decision replaces the practical relevance of an earlier one before outcome attribution.

The earlier record remains immutable.

---

## 6. The response layer must not blur Surface, Decision and Action

Preferred conceptual separation:

```text
Research / Decision-use artifact
-> HumanResearchSurface or equivalent Human-visible context
-> explicit Human response, if any
-> explicit Human investment decision, if any
-> separate Action / No Action evidence, if any
-> later Outcome
```

Not every arrow must exist in every case.

Critical identities:

```text
Human response != Human investment decision
Human investment decision != Action
ACTED response != execution receipt
NO_ACTION response != bearish Belief
DEFERRED response != forgotten case
SUPERSEDED != retroactive deletion
```

The value of the layer is precisely that it avoids collapsing these meanings.

---

## 7. Execution ownership boundary

Decision Kernel should remain a Research Cognition / Decision Hygiene core.

It should not become authoritative owner of:

- broker fills;
- portfolio positions;
- average cost;
- order lifecycle;
- partial fills;
- cash balances;
- tax lots;
- execution routing;
- portfolio PnL accounting.

If future prospective auditing needs exact Action evidence, the better boundary is likely:

```text
Kernel / Research lineage
-> explicit Human decision
-> external Harness / prospective audit Action record
-> Outcome attribution references both
```

This preserves the ability to audit whether a decision was implemented without making the Kernel a Portfolio OS.

The current Markdown decision checkpoints are already compatible with this separation.

---

## 8. No heuristic linking — hard rule

A future Human Response or Action audit must require explicit lineage.

Allowed examples:

```text
Human explicitly says:
"我今天按之前 320-335 的决定在 330 买了第一笔。"
```

This can support a linked Action checkpoint because the Human explicitly states the relationship.

Not allowed:

```text
portfolio shows 603986 increased
+ price was inside 320-335
-> infer that the frozen decision was executed
```

Not allowed:

```text
same ticker trade 3 days later
-> auto-link to prior decision
```

Not allowed:

```text
Human says "买了"
but price / size / linkage are missing
-> invent missing execution details
```

Where details are absent, preserve them as absent.

---

## 9. No adoption-rate metric yet

openInvest can calculate adoption rate because its machine committee emits explicit investment verdicts.

Decision Kernel deliberately does not own machine investment-judgment authority.

Therefore a metric such as:

```text
Human adopted 63% of Kernel recommendations
```

would be conceptually wrong because the Kernel does not issue recommendations that the Human is expected to adopt.

A future metric, if ever justified, would need a different question, for example:

- response coverage of Human-visible surfaces;
- proportion of explicit decisions with predeclared evaluation horizons;
- proportion of Actions with explicit decision lineage;
- proportion of later Outcomes that can be attributed without hindsight reconstruction.

Even these should not be built until enough prospective cases exist.

---

## 10. Current-case audit — do not backfill Human Response

Current prospective cases already have explicit records:

### Sanhua

```text
explicit Human Decision = CONDITIONAL BUY around CNY30
Action = NOT YET EXECUTED
```

No separate Human Response should be retroactively invented.

### GigaDevice

```text
explicit Human Decision = CNY350 assumption review; CNY320-335 conditional first entry
Action = NOT YET EXECUTED
```

No separate response layer is needed merely to increase dataset size.

### Micron

```text
explicit Human Decision = WAIT / DO NOT BUY FOR NOW
Action = NO_ACTION
constraint = Human temporarily not buying U.S. equities
```

Again, the existing decision checkpoint already owns the meaningful Human state.

Rule:

> **Do not retroactively decompose existing clean Human Decisions into synthetic Human Response records.**

That would manufacture longitudinal evidence rather than improve it.

---

## 11. When to run the first Human Response dogfood

Do not create a response artifact merely because the concept exists.

Wait for a real prospective case where:

1. a clearly identified Research / Human surface reaches the Human;
2. the Human gives an explicit response;
3. the response is decision-useful longitudinally;
4. the response is **not already fully captured** by the Human Decision protocol;
5. recording it would not require inferring trade execution.

Then create one docs-only response checkpoint and later inspect whether it improved attribution.

If repeated real cases show no incremental value beyond the existing Human Decision protocol, drop the idea.

---

## 12. Verdict

Current gap assessment:

```text
DECISION ACCOUNTING IDEA = useful external reference
EXPLICIT HUMAN RESPONSE = plausible thin missing evidence class
KERNEL ENTITY / SCHEMA = NOT JUSTIFIED
EXECUTION LEDGER INSIDE KERNEL = NOT JUSTIFIED
HEURISTIC DECISION-ACTION LINKING = REJECTED
RETROACTIVE RESPONSE BACKFILL = REJECTED
ADOPTION-RATE METRIC = NOT APPROPRIATE FOR CURRENT AUTHORITY MODEL
FIRST IMPLEMENTATION = wait for a genuine prospective response-only case
```

The narrow hypothesis retained is:

> **A future docs-only Human Response checkpoint may improve longitudinal attribution between a Human-visible Research surface and a later explicit Decision / Action, but only when the Human response is explicit and adds information not already owned by the existing decision protocol.**

This should be proven prospectively before any schema, state machine or portfolio integration is considered.
