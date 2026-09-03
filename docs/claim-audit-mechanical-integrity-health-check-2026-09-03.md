# Claim Audit Mechanical-Integrity Health Check — 2026-09-03

Status: **CHECKPOINT / NO KERNEL CHANGE / NO CLAIM AUDIT SCHEMA CHANGE / NO HARNESS PROMOTION**  
Scope: post-PR #106 / #107 / #108 review  
Repository: `auguspp/decision-kernel`

## Purpose

Review the three recent Claim Audit mechanical-integrity dogfoods before adding more method machinery.

Questions:

1. Are the test-only experiments starting to duplicate enough logic to justify abstraction?
2. Are the tests proving production behavior, or only zero-schema feasibility?
3. Is the evidence base too concentrated in one company shape?
4. Is there already a real claim-warrant or source-disagreement case strong enough to justify the next experiment?

## Verdict

```text
CURRENT TEST DUPLICATION = REAL BUT SMALL
ABSTRACT SHARED HARNESS NOW = NO
PRODUCTION CLAIM AUDIT CHANGE = NO
CLAIM AUDIT V3 = NO
YTO-ONLY EVIDENCE SUFFICIENT FOR PROMOTION = NO
CROSS-CASE EVIDENCE REQUIRED BEFORE PROMOTION = YES
REAL WARRANT NEGATIVE CONTROL EXISTS = YES, HISTORICAL / Xiamen Tungsten
STRUCTURED WARRANT DOGFOOD READY = NO
CLEAN SAME-QUANTITY SOURCE-DISAGREEMENT CASE FOUND = NO, NOT IN THIS PASS
```

The correct action is to preserve the recent tests as dogfood/regression evidence and stop method construction until either a real prospective event or a stronger cross-case failure appears.

## 1. Duplication review

The derived-number and numeric-clause dogfoods both carry small local helpers for:

- loading the frozen YTO package;
- enumerating material claims;
- locating an exact claim;
- mapping claim identity through `canonical_hash()`;
- replaying EvidenceArtifact structured fields;
- enforcing PIT availability.

Claim Audit v1 itself also contains its own internal material-claim enumeration.

This is duplication, but it is not yet a reason to create a shared production abstraction.

Why not:

- the recent helpers are explicitly experimental;
- their shapes are not yet proven across materially different Research cases;
- extracting them now risks turning one dogfood representation into an accidental public contract;
- the production contract and the test-only experiments still answer different questions.

Disposition:

> Keep the helpers local until at least one materially different case needs the same mechanism and the duplication begins to create maintenance errors rather than aesthetic discomfort.

## 2. Green CI does not mean production coverage

PR #106 and PR #107 deliberately implement test-only checking logic around existing primitives.

Therefore their green CI proves:

```text
zero-schema mechanical check is feasible
```

It does not prove:

```text
production synthesis already invokes this check
```

That distinction must remain explicit.

PR #108 is stronger as a regression test because it directly exercises `assess_claim_audit_contract_v2()` and proves the existing production Research-Method contract rejects first-source collapse for FACT / MARKET_CONTEXT claims.

No current evidence justifies promoting the #106 / #107 helpers into `src/`.

## 3. Case-concentration risk

All three recent experiments use YTO v2 as the real frozen carrier.

This is better than synthetic examples, but it creates a different risk:

> YTO's claim and Evidence shape may accidentally become the implicit design template for a supposedly general harness.

Before any permanent harness/schema promotion, require a materially different case.

A useful cross-case should differ in at least one important dimension, for example:

- cyclical / model-class uncertainty rather than network economics;
- multi-period derived values rather than single-filing values;
- management outlook + independent industry evidence rather than mostly filing-derived realized values;
- an actual historical inference failure rather than a clean current package.

## 4. Real claim-warrant candidate

The strongest real negative control found in this health check is Xiamen Tungsten.

Its frozen retrospective explicitly attributes the failure primarily to Reference Frame and inference rather than fabricated or unavailable evidence:

```text
correct / plausible observations
-> incomplete Reference Frame
-> overly fast economic inference
-> probability theater
-> valuation contamination
```

The especially useful historical failure is the incompatible-regime normalization:

```text
high-tungsten-price H1 earnings
+ impairment normalization
+ lower long-run tungsten-price intuition
-> persuasive but causally inconsistent normalized earnings
```

This is a real warrant/inference failure: individually plausible inputs did not warrant the combined economic conclusion.

However, the historical case does not currently exist as a clean structured `DeepResearchPackage + Claim Audit` pair with exact frozen claim/evidence objects suitable for a mechanical regression.

Therefore:

> Do not reverse-engineer or invent a structured package merely to make the test convenient.

Wait for either a naturally structured cross-case or a future prospective case that exposes the same failure.

## 5. Current structured warrant gap

Current Claim Audit v2 intentionally treats `INFERENCE` and `ASSUMPTION` as Research-owned cognition rather than source truth.

For FACT / MARKET_CONTEXT, v2 requires full source-use coverage and checks source-role / assertion-scope admissibility.

For INFERENCE / ASSUMPTION, declared `source_uses` only need to remain inside the claim's declared Evidence lineage; `source_uses` may be empty.

That means Claim Audit v2 does not mechanically prove:

```text
these admissible inputs
actually warrant
this full causal inference
```

This is a real semantic gap, but it is also an intentional boundary. Closing it carelessly would risk pretending that source authority can certify Research cognition.

A future warrant dogfood must therefore test reasoning support without promoting inference into FACT or building a generic confidence score.

## 6. Source-disagreement search

This pass did not find a clean case with all of the following:

```text
same claimed quantity
+ same relevant period / identity
+ two independently admissible records
+ materially different values
+ no obvious timing / definition explanation
```

Examples that do not qualify:

- CICC vs Huachuang 2027 forecasts: legitimate model disagreement, not conflicting records of realized truth;
- management specialty-memory outlook vs independent supply-response research: competing outlooks / frames, not the same measured quantity;
- preliminary earnings range vs later formal result: different information states, not same-PIT record disagreement;
- H1 vs FY OCF/capex: different periods.

Therefore no source-disagreement harness should be added yet.

## 7. Stop rule after this checkpoint

Do not create another Claim Audit experiment merely to complete the AlphaAnalyst candidate list.

Resume mechanical-integrity development only if one of these occurs:

1. a real prospective Research / price / Human Decision / Action event creates a concrete audit failure;
2. a non-YTO structured case reproduces the derived-number or numeric-clause problem;
3. a real same-quantity source disagreement appears;
4. a structured inference case demonstrates a warrant failure that can be tested without pretending source authority owns cognition;
5. repeated local helper duplication begins causing real maintenance mistakes.

Until then:

```text
KEEP ZERO-SCHEMA DOGFOODS
KEEP EXISTING PRODUCTION CONTRACT
NO CLAIM AUDIT V3
NO GENERIC PROVENANCE SERVICE
NO WARRANT SCORE
NO SOURCE-DISAGREEMENT ABSTRACTION
```

## Final read

The recent work has produced useful evidence precisely because it stayed small.

The next risk is no longer under-engineering. It is mistaking three successful YTO experiments for enough evidence to generalize the mechanism.

> **The correct next move is to wait for a cross-case or prospective failure that earns the next abstraction.**
