# Decision Hygiene Method Note — 2026-09-03

## Purpose

This note freezes the current methodological conclusions from an external-review / adversarial design discussion around Decision Kernel.

It is **not** a new Kernel Constitution, not a request to implement new state machines, and not a claim that the concepts below already deserve permanent schemas. The immediate purpose is to preserve the reasoning so it can be dogfooded against real investment cases before any further structure is promoted into code.

The central shift is:

> Decision Kernel should not try to become a Truth Machine. It should provide Decision Hygiene: preserve what was known at the time, separate record from interpretation, expose uncertainty and causal assumptions, and make later failure attributable without silently rewriting the past.

---

## 1. Kernel does not own Reality

The system never directly owns "reality itself." It owns PIT-bounded records, observations, statements, calculations, interpretations, forecasts, and market observations.

This corrects an earlier framing in which a `Reality Map` could psychologically over-promote official filings or audited financial statements into unquestioned truth.

A primary filing can still strongly support a precise reported claim. For example:

- `FY2025 audited reported revenue = CNY 10bn` can be a strong reported fact.
- `FY2025 sustainable economic revenue = CNY 10bn` is a different analytical claim and may remain uncertain.

The correction is **not** to blur records into arbitrary ranges. It is to preserve source semantics exactly and keep observation separate from interpretation.

> Record preserves what the source actually reported; interpretation carries the uncertainty about economic meaning.

---

## 2. Evidence authority is claim-level, not source-level

A source should not receive one global credibility score that determines everything it can prove.

The useful question is:

> What exact claim is this exact source admissible to support, under this assertion scope?

The same annual report may contain:

- reported revenue;
- management estimates;
- impairment assumptions;
- future plans;
- industry commentary.

Those statements do not share one epistemic status merely because they appear in the same artifact.

The current preferred direction therefore remains:

- claim-level source admissibility;
- explicit assertion scope;
- exact provenance and lineage;
- no broker / source credibility score as a substitute for classification.

This is aligned with Research Method v2 rather than a change to Kernel Evidence identity.

---

## 3. Belief and expectation should be distinguishable, not falsely "pure"

A completely market-blind belief is unrealistic. Research selection itself is already influenced by price, news, industry attention, prior knowledge, and existing narratives.

The more honest discipline is to preserve two auditable stages where useful:

1. **Pre-expectation underwriting** — causal underwriting from the available record and first-principles driver model before a deliberate expectation-reconstruction pass.
2. **Post-expectation belief** — belief after sell-side / consensus / market-implied expectations are explicitly compared and any update is explained.

The purpose is not to claim contamination can be eliminated. It is to make anchoring visible.

A material movement from pre-expectation underwriting toward consensus without new fundamental justification should itself be reviewable as potential consensus capture.

---

## 4. Market expectation is broader than sell-side consensus

Sell-side research is useful primarily as:

- an expectation source;
- a hypothesis generator;
- an information map;
- a pointer toward variables and primary evidence worth checking.

It is not default reality authority.

Market expectation should eventually include both:

- observed / reconstructed consensus expectations; and
- **market-implied worlds** derived from current price.

However, price should not be reduced to a single pseudo-precise "implied growth rate." Many combinations of growth, margin, reinvestment, ROIC, discount rate, and terminal economics can explain the same price.

The preferred concept is therefore an **Implied Expectations Surface**:

> What economically coherent future worlds does the current price require to be plausible?

The investment question then becomes:

> What does the market require to be true, and which required condition do we believe is most likely wrong?

---

## 5. Price changes Odds; evidence changes Belief

The current separation remains useful:

> Evidence changes probability / fundamental belief; price changes Odds.

This is a discipline against silently letting price appreciation rewrite fundamental probabilities.

It is not a claim that price contains no information. Market-implied expectations should be inspected explicitly, but the Research layer should prevent price from becoming an untraceable fundamental input.

This separation also helps expose double counting across:

- scenario assumptions;
- valuation multiples / terminal economics;
- market regime;
- current price;
- required return / Odds hurdle.

---

## 6. Falsifiers should remove silent validity, not create investment authority

A predeclared falsifier should not automatically allow the system to conclude that a thesis is definitively dead, because whether a trigger is structurally meaningful can itself require interpretation.

Preferred behavior:

```text
Falsifier condition observed
    -> FALSIFIER_TRIGGERED
    -> prior thesis can no longer remain silently valid
    -> mandatory human research review
```

The system may remove the ability to ignore a previously declared falsifier.

It should not gain authority to announce a new investment truth.

The underlying principle is:

> Preserve Human interpretation authority; remove Human escape from prior commitments.

---

## 7. Do not give Evidence a permanent "Working Fact" certificate

An earlier proposal considered a global `PROVISIONAL -> CONTESTED -> WORKING_FACT` epistemic lifecycle.

That was rejected because it reintroduced a state-machine architecture and confused multiple concepts:

- source count is not truth;
- corroboration only helps when error modes are genuinely independent;
- alternative explanations contest inference, not the underlying observation;
- materiality determines attention, not epistemic truth;
- uncertain inputs must still be allowed into scenarios.

The more accurate question is not:

> Is this Evidence now a fact forever?

It is:

> For this exact ResearchSnapshot and decision, how are we using this exact claim?

A stable baseline is therefore contextual, not ontological.

> Stable enough for this decision != true.

---

## 8. Decision Use and Uncertainty Representation are separate dimensions

A prior four-state treatment proposal mixed two different questions.

For example, a future margin can simultaneously be a model variable **and** be represented as a range.

Therefore keep conceptually separate:

### Decision Use

- `BASELINE_INPUT` — treated as fixed within this Snapshot's underwriting.
- `VARIABLE_INPUT` — materially participates in the model and must carry uncertainty.
- `CONTEXT_ONLY` — retained for lineage / interpretation but not directly used in core underwriting computation.

### Uncertainty Representation

- `POINT`
- `RANGE`
- `SCENARIO_LINKED`

These are not an upgrade ladder and should not create transition-state machinery.

A new Snapshot simply redeclares how the claim is used and represented at the new PIT.

---

## 9. Uncertainty Origin is distinct from Uncertainty Representation

`RANGE` describes form, not cause.

The system should remain able to distinguish why something is uncertain. Conceptually useful origins include:

- **Measurement / Reporting uncertainty** — uncertainty about how faithfully an already-occurring phenomenon has been observed or represented.
- **Estimation uncertainty** — uncertainty from estimating a parameter using finite / noisy historical information.
- **Model / Structural uncertainty** — uncertainty that the causal model or Reference Frame is wrong.
- **Future-state uncertainty** — uncertainty because the relevant future state has not occurred and cannot be eliminated through present diligence.

These can coexist for one variable.

This distinction matters mainly for later attribution: a measurement failure, model failure, and low-probability future outcome demand different corrective actions.

Do not automatically promote this list into enums until real cases prove mechanical validation is useful.

---

## 10. Resolution Path turns uncertainty into an attention-allocation problem

For a decision-critical uncertainty, Research should be able to express:

> Through what future observable, new evidence, or elapsed time could this uncertainty begin to resolve?

Examples:

- revenue-quality uncertainty may resolve through cash collection, receivable ageing, returns, audit detail, or later filings;
- future gross-margin uncertainty may resolve through pricing, utilization, product mix, and unit-cost disclosures;
- a long-duration competitive-moat question may remain structurally unresolved for years.

This creates a practical distinction:

- **resolvable through more diligence now** -> consider more Research attention;
- **resolvable mainly through future observation** -> set monitoring triggers and wait;
- **material but currently unresolvable** -> model the uncertainty rather than research indefinitely.

A useful qualitative attention heuristic is:

```text
Research Attention ~ Materiality x Uncertainty x Resolvability
```

This is a reasoning aid, not a proposed production scoring formula.

---

## 11. Cross-Snapshot change must be explicit, but does not require new external Evidence

Old snapshots remain immutable.

A new Snapshot may change:

- Reference Frame;
- claim Decision Use;
- uncertainty representation;
- uncertainty origin;
- interpretation;
- scenario structure.

Such change must leave a new PIT-bound, auditable justification.

It does **not** always require new external Evidence. Legitimate causes can include:

- reinterpretation of existing evidence;
- model correction;
- reference-frame change;
- improved extraction from existing evidence;
- calculation correction.

However, "I changed my mind" is not sufficient.

If the change is not driven by new evidence, a good Research discipline is:

### Retrospective Fit

What old data did the previous interpretation fail to explain, and why does the new interpretation explain it better?

### Prospective Discrimination

What future observable would cause the old and new interpretations to make meaningfully different predictions?

This prevents reinterpretation from becoming hindsight storytelling.

> A better explanation must not only fit the past; it should expose itself to future discrimination.

---

## 12. Uncertainty cannot disappear silently

Confidence drift is a real failure mode.

If a previously material uncertain variable becomes a fixed baseline in a new Snapshot, that change must be explicit and justified.

But do not force the Human to re-approve every unchanged variable in every Snapshot. That would become checklist theatre.

Preferred behavior:

- unchanged material uncertainties may carry forward;
- changed treatment requires explanation;
- the system may surface unresolved decision-critical variables;
- absence of explicit change must not be interpreted as automatic certainty increase.

> Absent an explicit new declaration, uncertainty does not disappear.

---

## 13. Reference Frame / Model Class should be explicit and challengeable

Before causal underwriting, Research should declare the current model class / reference frame used to understand the business.

Examples may include:

- cyclical manufacturer;
- commodity producer;
- regulated utility;
- network business;
- capital allocator;
- luxury franchise;
- hardware + recurring service model.

Reference Frame affects:

- relevant drivers;
- comparable historical periods;
- sustainable margins;
- reinvestment requirements;
- ROIC interpretation;
- terminal economics;
- applicable base rates.

The frame should be frozen with the Snapshot and challenged again before freeze:

```text
Frame Challenge Review
- Strongest challenge
- Current disposition: retain / revise / unresolved
- Implications for frame-dependent claims
```

Unresolved frame uncertainty should **not** automatically block Human attention. Sometimes frame uncertainty is itself the most important research result.

A frame change should force re-underwriting of frame-dependent interpretations, not reset stable observations merely for convenience.

---

## 14. Scenarios are causally coherent joint worlds

This is a core conclusion.

> A Scenario is not a set of independently chosen assumptions. It is a causally coherent joint state of the world.

Marginally plausible variable ranges can produce jointly impossible combinations if treated independently.

Example:

- high volume growth may require price concessions;
- price concessions may reduce margin;
- utilization may improve unit cost;
- market-share gains may raise capex or working-capital requirements.

Therefore scenarios should explain why key variables move together.

A scenario that combines all favorable marginals — e.g. maximum share gain + higher ASP + higher margin + lower capex — must explain the causal mechanism making those outcomes jointly plausible. Otherwise it is a right-tail wish list, not a scenario.

Do not introduce correlation matrices, copulas, Monte Carlo dependency graphs, or Bayesian networks merely to look rigorous. If real cases later prove finite coherent scenarios insufficient, richer joint-distribution methods can be revisited.

---

## 15. Full uncertainty annotation is only for decision-critical inputs

The architecture must not become a four-dimensional annotation matrix across every field in a research package.

Complete treatment is reserved for variables where being materially wrong could change:

- core Belief;
- important scenario economics;
- Odds;
- Human attention allocation.

Non-critical baseline or context inputs may retain a default assumption and short note.

Avoid introducing a universal numeric threshold such as `>5% impact = critical` until dogfood proves such a rule is stable and useful.

The current methodological principle is qualitative:

> Research should not give every input equal uncertainty-analysis depth. Expand the variables whose plausible error could materially change the decision.

---

## 16. Failure attribution should prevent "black swan" from becoming an excuse

Post-outcome review should attempt to distinguish at least:

- **Evidence Failure** — the record or underlying evidence proved wrong / unreliable.
- **Classification Failure** — a source or claim was given an invalid epistemic role / assertion scope.
- **Inference Failure** — observations were correct but causal interpretation was wrong.
- **Assumption Failure** — key future assumption did not hold.
- **Probability Failure** — scenario set was reasonable but probability assignment was badly calibrated.
- **Valuation Failure** — business judgment was broadly right but terminal economics / discounting / value translation was wrong.
- **Odds Failure** — fundamental belief may have been reasonable but the price paid / odds were poor.
- **Reference Frame Failure** — the wrong model class / comparison frame structured the entire underwriting.
- **Exogenous Surprise** — a genuinely new state emerged that was not reasonably inferable from the PIT information set.

`Exogenous Surprise` should be used cautiously and only after the other failure layers have been inspected. Otherwise "black swan" becomes a confirmation-machine escape hatch.

---

## 17. Current combined cognitive map

```text
PIT-bound Observation / Record
        ↓
Reference Frame / Model Class
        ↓
Causal Underwriting
        ↓
Decision-critical claim treatment:
    Decision Use
        ×
    Uncertainty Representation
        ×
    Uncertainty Origin
        ×
    Resolution Path
        ↓
Causally Coherent Scenarios
        ↓
Belief
        ↓
Expectation Gap
        ↓
Market-Implied Worlds
        ↓
Odds
        ↓
Human Decision
```

With two cross-cutting disciplines:

1. **Reinterpretation requires retrospective fit plus prospective discrimination.**
2. **Old uncertainty cannot silently disappear in a later Snapshot.**

---

## 18. Explicit non-goals / rejected directions

Do **not** infer from this note that the repository should now add:

- a new global Evidence lifecycle state machine;
- `PROVISIONAL / CONTESTED / WORKING_FACT / ACTIVE` states;
- a source credibility score;
- mandatory three-source triangulation;
- a hard materiality threshold;
- automatic thesis invalidation;
- automatic frame rejection;
- a four-dimensional mandatory annotation form for every claim;
- a correlation engine / copula / Monte Carlo system;
- new investment authority.

The battle repeatedly found that more precise conceptual separation often removed the need for more Guardrails.

> If a conceptual boundary can solve the problem, do not build a state machine to simulate that boundary.

---

## 19. Dogfood before schema

The next step is not to encode this entire map into Pydantic models.

Use a small number of real cases first, preferably including:

- YTO / 圆通速递;
- GigaDevice / 兆易创新;
- Sanhua / 三花智控;
- at least one historical case where the Human's investment judgment was materially wrong.

For each case, ask only:

1. What Reference Frame are we using?
2. What are the 3–5 truly decision-critical variables?
3. For each critical variable:
   - how is it used?
   - how is uncertainty represented?
   - where does uncertainty come from?
   - what observable / event could resolve it?
4. Are scenarios causally coherent joint worlds?
5. What did pre-expectation underwriting say?
6. What does sell-side / consensus say?
7. What future worlds does current price appear to require?
8. What is the discriminating gap?
9. What would force the Research to reopen?

After enough real cases:

- fields that repeatedly improve decisions / attribution may graduate into structured Research Method payloads;
- fields that become compliance text or checklist theatre should be deleted;
- only invariants whose violation would corrupt PIT, identity, lineage, deterministic Odds, Human accountability, or authority boundaries should be considered for Kernel promotion.

---

## 20. Working definition

The current best internal description is:

> **Decision Kernel is not a Truth Machine. It is a Decision Hygiene layer that preserves what was known, what was assumed, how uncertainty entered the decision, what the market appeared to require, and why the Human chose to pay attention — without silently rewriting the past or acquiring investment authority.**

It does not guarantee that the investment will be right.

Its ambition is narrower and more useful:

> Make it increasingly difficult to be wrong for reasons that could have been made explicit at the time, and increasingly easy to understand afterward exactly where the reasoning failed.
