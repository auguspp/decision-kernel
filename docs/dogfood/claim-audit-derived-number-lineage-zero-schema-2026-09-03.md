# Claim Audit Derived-Number Lineage Dogfood — 2026-09-03

Status: **ZERO-SCHEMA DOGFOOD / TEST-HARNESS EXPERIMENT / NO CLAIM AUDIT SCHEMA CHANGE / NO KERNEL CHANGE**  
Repository: `auguspp/decision-kernel`  
External trigger: `docs/external/alphaanalyst-claim-audit-code-diligence-2026-09-03.md`  
Real case: `research_cases/600233-yto-deep-research-v2.json`

## Purpose

AlphaAnalyst diligence identified a specific mechanical failure mode:

```text
derived number
-> synthetic `fact` source
-> upstream input provenance disappears
```

The preferred Decision Hygiene shape is instead:

```text
derived claim
-> derivation / formula / version
-> exact input claims
-> exact source lineage for each input
-> PIT
-> deterministic output
```

This dogfood asks a narrow question:

> **Can the current Decision Kernel Claim Audit primitives support that chain mechanically without adding a production schema or inventing a source for the derived number itself?**

This is not a roadmap commitment and does not authorize a new Kernel entity.

---

## 1. Existing capability before this experiment

`ClaimAuditV1NumericalCheck` already provides useful mechanical guarantees:

- arithmetic is recalculated deterministically with `Decimal`;
- every numerical operand must bind to an exact `EvidenceArtifact` structured value or an explicitly declared literal;
- the Claim Audit assessment rejects numerical Evidence outside the reviewed claim lineage;
- the Evidence value is replayed from `extracted_structured_values` rather than trusted from prose.

Claim Audit v2 adds source-role / assertion-scope qualification while retaining the v1 numerical checks.

What is not currently persisted as one explicit production object is:

```text
formula version
+ exact input claim identity
+ PIT binding
+ derived output
```

That is the gap under test.

---

## 2. Real YTO test case

Use the frozen YTO v2 Research package rather than inventing a synthetic company example.

Relevant exact Research claim:

```text
H1 OCF/cash capex were ~CNY3.959bn/3.482bn; 2025 OCF/cash capex ~CNY7.850bn/8.607bn.
```

The 2026H1 official-filing `EvidenceArtifact` is:

```text
047e2546-389b-5274-a8dc-e4a0ce3931f4
```

Its retained structured values include:

```text
ocf   = 3958827124.74
capex = 3482399714.60
```

YTO v2 Research PIT:

```text
2026-09-02T01:00:00Z
```

The H1 filing was available by:

```text
2026-08-20T00:00:00Z
```

Therefore the input evidence is PIT-admissible for this frozen Research state.

### Derived claim under test

Formula identity:

```text
name    = ocf_minus_cash_capex
version = v1
operation = DIFFERENCE
```

Deterministic calculation:

```text
3958827124.74
- 3482399714.60
= 476427410.14 CNY
```

The derived output is **not** assigned a fake source such as:

```text
source_type = fact
source_id = yto-ocf-surplus
```

Its provenance remains the derivation chain.

---

## 3. Zero-schema harness contract

The test-only harness in:

`tests/test_claim_audit_derived_number_lineage_dogfood.py`

requires all of the following before accepting the derived number:

```text
non-empty formula name
+ explicit formula version
+ canonical hash of each exact material input claim
+ numerical operands bound to EvidenceArtifact structured fields
+ every numerical EvidenceArtifact inside the declared input-claim lineage
+ every numerical EvidenceArtifact available by the frozen Research PIT
+ retained structured Evidence value exactly equals the declared operand
+ deterministic Decimal recalculation equals the claimed output
```

The input claim ID is derived at test time with the repository's existing `canonical_hash()` rather than introducing a new claim-ID field.

This is intentionally a harness experiment, not a production model.

---

## 4. Negative control

The same valid OCF / capex numerical inputs are then paired with an unrelated exact Research claim:

```text
After that prealert, sampled CICC and Huachuang 2027 parent-NP forecasts were CNY7.306bn and CNY7.50bn.
```

The arithmetic still exists.

The H1 filing still exists.

But the derived-number harness must reject the lineage because the OCF / capex Evidence is outside that input claim's exact Evidence lineage.

This tests the important distinction:

```text
valid number
+ valid source somewhere in Research
!= valid derivation lineage
```

---

## 5. Dogfood result

The experiment supports two conclusions at once.

### Result A — no schema change is required to prove the concept

The existing primitives are sufficient to construct a mechanically checkable zero-schema chain:

```text
canonical input claim hash
-> existing EvidenceArtifact IDs / structured values
-> existing PIT timestamps
-> existing deterministic Decimal operation
-> derived output
```

The experiment therefore does **not** justify adding:

- `DerivedClaim` to Kernel;
- a derivation graph entity;
- Claim Audit v3;
- a generic provenance service;
- a new Research state machine.

### Result B — the persistent representation gap is real

The current production Claim Audit payload does not itself freeze the full chain as one reusable record:

```text
formula/version
-> exact input claim IDs
-> derived output
```

So a future synthesis layer could still lose this information unless the harness preserves it deliberately.

That is a real mechanical gap, but one dogfood is not enough evidence to choose its permanent software representation.

---

## 6. Current disposition

```text
DERIVED-NUMBER LINEAGE FAILURE MODE = REAL
ZERO-SCHEMA MECHANICAL CHECK = VIABLE
KERNEL CHANGE = NO
CLAIM AUDIT SCHEMA CHANGE = NO
HARNESS CHANGE = NOT YET AUTHORIZED
FAKE SOURCE FOR DERIVED NUMBER = REJECTED
```

The useful rule is:

> **A derived number is auditable because its derivation and exact inputs are auditable, not because the system invents a source identity for the output.**

A next experiment may either repeat this pattern on a materially different derived number or attack the parallel `numeric-clause fail-closed` gap. A real prospective Research / price / Human Decision / Action event takes priority over further method construction.
