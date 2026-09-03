# Claim Audit Numeric-Clause Fail-Closed Dogfood — 2026-09-03

Status: **ZERO-SCHEMA DOGFOOD / TEST-HARNESS EXPERIMENT / NO CLAIM AUDIT SCHEMA CHANGE / NO KERNEL CHANGE**  
Repository: `auguspp/decision-kernel`  
External trigger: `docs/external/alphaanalyst-claim-audit-code-diligence-2026-09-03.md`  
Prior experiment: `docs/dogfood/claim-audit-derived-number-lineage-zero-schema-2026-09-03.md`  
Real case: `research_cases/600233-yto-deep-research-v2.json`

## Purpose

AlphaAnalyst diligence identified a distinct failure mode from derived-number lineage:

```text
paragraph contains several numerical claims
+ one valid citation / fact tag somewhere in the paragraph
-> paragraph passes
```

That is too weak for Decision Hygiene.

A material numerical clause should not inherit provenance merely because a nearby number is properly sourced.

This dogfood asks:

> **Can a zero-schema harness require each explicitly declared material numeric clause to carry its own admissible provenance path, and fail the whole section closed if even one clause does not?**

This is deliberately narrower than natural-language claim extraction. It does not attempt to discover numbers with a regex or infer semantic warrant from arbitrary prose.

---

## 1. Why this is separate from derived-number lineage

The prior derived-number experiment tested:

```text
formula / version
-> exact input claim
-> Evidence structured inputs
-> PIT
-> deterministic derived output
```

This experiment tests a synthesis boundary instead:

```text
section prose
-> material numeric clause A -> provenance path
-> material numeric clause B -> provenance path
-> material numeric clause C -> provenance path

if any material numeric clause lacks a path
-> Insufficient evidence
```

The point is not to prove every number is derived.

The point is to prevent one valid provenance path from laundering neighboring unsupported numerical prose.

---

## 2. Explicit clauses, not regex parsing

The test-only harness in:

`tests/test_claim_audit_numeric_clause_fail_closed_dogfood.py`

uses an explicit `_NumericClause` declaration containing:

```text
clause text
+ exact input Research claim hash
+ ClaimAuditV1NumericalCheck
```

The harness deliberately does **not** scan prose for numbers.

That preserves an existing project caution:

> Numeric-token detection is an implementation choice, not epistemic truth.

For this experiment, the producer / test declares what is a material numeric clause. The mechanical audit only checks whether that declared clause has a valid path.

---

## 3. Real YTO positive control

The frozen YTO H1 filing EvidenceArtifact retains structured values including:

```text
unit_rev     = 2.17
unit_cost    = 1.90
aviation_gm  = -47.86
```

The synthesized test section is:

```text
YTO H1 unit revenue was CNY2.17/parcel,
unit cost was CNY1.90/parcel,
and aviation gross margin was -47.86%.
```

The clauses are bound independently:

```text
unit revenue 2.17
-> exact unit-economics Research claim
-> H1 filing EvidenceArtifact
-> structured field unit_rev
-> PIT

unit cost 1.90
-> exact unit-economics Research claim
-> H1 filing EvidenceArtifact
-> structured field unit_cost
-> PIT

aviation GM -47.86%
-> exact aviation-margin Research claim
-> H1 filing EvidenceArtifact
-> structured field aviation_gm
-> PIT
```

All clauses are supported, so the original section is preserved.

---

## 4. Negative control A — one good number cannot cover one unsupported number

Test section:

```text
YTO H1 unit revenue was CNY2.17/parcel and a modeled margin was 90%.
```

The first clause has a valid path.

The `90%` clause is explicitly declared material but has:

```text
input claim = NONE
numerical check = NONE
```

Expected behavior:

```text
one supported numeric clause
+ one unsupported material numeric clause
!= acceptable section

-> Insufficient evidence
```

The harness replaces the section rather than preserving the supported sentence fragment and silently leaving the unsupported number beside it.

This is the fail-closed behavior worth preserving.

---

## 5. Negative control B — a valid source elsewhere does not rescue wrong claim lineage

YTO Research contains both:

- official H1 filing evidence for aviation gross margin;
- separate sell-side expectation claims from CICC / Huachuang.

The negative control deliberately binds:

```text
aviation gross margin = -47.86%
```

to the unrelated sell-side Research claim while retaining the real H1 filing numerical input.

The number is real.

The H1 filing is real.

Both exist somewhere in the Research package.

But the Evidence input is outside the declared sell-side claim lineage, so the section fails closed.

This rejects:

```text
valid number
+ valid source somewhere in Research
= sufficient provenance
```

---

## 6. CI result

The first CI run failed because the experiment guessed the YTO structured field name as:

```text
unit_revenue
```

while the frozen EvidenceArtifact actually stores:

```text
unit_rev
```

The experiment was corrected to the exact retained field name and rerun without changing its logic.

The corrected full `kernel-tests` run passed.

This small failure is itself useful: exact structured-field identity is part of provenance and should not be normalized by guesswork merely because the human-readable meaning is obvious.

---

## 7. What this dogfood proves

```text
PER-MATERIAL-NUMERIC-CLAUSE PROVENANCE = mechanically viable in zero-schema harness
SECTION-LEVEL ONE-CITATION LAUNDERING = rejectable
FAIL-CLOSED SECTION SEMANTICS = viable
EXACT CLAIM HASH + Evidence field + PIT CHECK = reusable existing primitives
NUMERIC REGEX PARSER = not required for proof of concept
```

The useful rule is:

> **A section with three material numerical clauses needs three qualified provenance paths, even if two or more paths share the same underlying filing.**

---

## 8. What this dogfood does NOT prove

### 8.1 Material-clause discovery is still unsolved

The test harness is told which clauses are material.

It does not answer:

```text
How should production synthesis identify every material numeric clause?
```

Do not infer that a regex over digits is the correct answer.

### 8.2 Exact claim identity is not the same as semantic warrant

The harness verifies that declared numerical Evidence sits inside the declared claim's Evidence lineage.

It does not mechanically prove that an arbitrary source excerpt semantically warrants every word in an arbitrary clause.

In particular, if two different Research claims both cite the same broad EvidenceArtifact, EvidenceArtifact membership alone cannot distinguish all semantic warrant questions.

That remains a separate claim-to-source warrant problem.

### 8.3 No production output contract is authorized

This experiment does not justify adding:

- `NumericClause` to Kernel;
- Claim Audit v3;
- a prose parser;
- a new final-memo schema;
- a generic citation service;
- automatic LLM repair / regeneration loops.

---

## 9. Current disposition

```text
NUMERIC-CLAUSE LAUNDERING FAILURE MODE = REAL
ZERO-SCHEMA FAIL-CLOSED CHECK = VIABLE
KERNEL CHANGE = NO
CLAIM AUDIT SCHEMA CHANGE = NO
HARNESS PRODUCTION CHANGE = NOT YET AUTHORIZED
REGEX NUMBER EXTRACTION = NOT AUTHORIZED
SILENT CITATION PATCHING = REJECTED
```

Together with the derived-number lineage experiment, the current mechanical evidence says:

```text
derived number
-> preserve derivation lineage

synthesized numeric prose
-> preserve clause-level provenance

unsupported numeric clause
-> fail closed
```

The next step should not be automatic implementation. A materially different dogfood, a claim-to-source warrant experiment, or a real prospective Research / price / Human Decision / Action event may provide more valuable evidence. Real prospective events remain higher priority than continued method construction.
