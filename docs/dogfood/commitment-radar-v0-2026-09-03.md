# Commitment Radar v0 — zero-schema dogfood

Status: **ZERO-SCHEMA DOGFOOD / HARNESS-LINEAGE EXPERIMENT / NO KERNEL CHANGE / NO HUMAN-WAKE CHANGE**

Date: 2026-09-03

## Question

Can new qualified Evidence be linked back to one exact prior Research commitment without inventing a second attention policy, a Radar score, or a new Kernel entity?

The intended product question is:

> I previously said I was waiting for something. Did new Evidence actually bear on that exact commitment?

This experiment does **not** ask whether the system should wake the Human. Existing HumanResearchSurface semantics remain the sole Human wake gate.

## Existing foundation

The repository already has the acquisition and memory mechanics needed for a narrow Commitment Radar:

- official CNINFO disclosure acquisition;
- exact dated disclosure batches;
- Research freshness against frozen `as_of_datetime`;
- exact `DisclosureAssessmentPacket` identity;
- page-level official Evidence extraction;
- semantic Research assessment outside Kernel;
- exact disclosure assessment receipts keyed by batch + frozen Research + assessment semantics.

The missing link is narrower: a semantic producer can explain why a disclosure matters, but the current assessment payload does not persist one exact pointer from that explanation back to the specific frozen `open_question`, `thesis_invalidation`, or `monitoring_trigger` it claims to advance.

## Real positive control — CATL 2026-08-12

Use the existing frozen CATL Research package and the existing disclosure-cognition regression corpus.

Frozen Research question:

> 在大规模扩产下，自由现金流转化能否跟上利润增长？

Real official disclosure batch:

- `1225470687` — CATL committed RMB2.475bn of own funds for 49.5% of an eight-year Hainan green-industry fund;
- `1225470688` — shareholders approved an A-share repurchase program sized at RMB20–40bn for cancellation and registered-capital reduction;
- `1225470689` — legal-opinion filing retained in the exact batch but not used for a factual claim in the reviewed gold assessment.

The existing reviewed gold result is `WAIT_FOR_TRIGGER` at `QUICK_RESEARCH`. Its reason is that the batch directly intersects capital allocation, while actual cash deployment and the interaction with capex / future operating cash flow remain unresolved.

Commitment Radar v0 does not replace that semantic judgment. It adds an auditable exact linkage after the judgment:

```text
frozen ResearchSnapshot id/as-of/information hash
→ exact prior commitment kind + verbatim text
→ exact DisclosureAssessmentPacket assessment_input_hash
→ exact announcement ids
→ exact EvidenceArtifact ids
```

For the positive control the exact EvidenceArtifact ids are:

- `1225470687` → `7827cfaf-96d6-5649-8bee-73683d07db39`
- `1225470688` → `97ab96be-ff9a-5769-9266-e952c7cc4e0e`

## Mechanical fail-closed boundary

The test-local validator requires:

1. packet security equals frozen Research security;
2. packet `research_snapshot_id` equals the exact frozen Research id;
3. packet Research `as_of` equals the frozen PIT cutoff;
4. packet `research_information_bundle_hash` equals the frozen Research information identity;
5. the proposed commitment text is a **verbatim member** of the selected frozen Research field;
6. the proposed Evidence announcement ids are non-empty and belong to the exact assessment packet;
7. selected Evidence is newer than the frozen Research cutoff;
8. the lineage carries packet-derived EvidenceArtifact ids rather than invented source identities.

Allowed commitment kinds in this experiment are only the existing Research-owned fields:

- `OPEN_QUESTION`
- `THESIS_INVALIDATION`
- `MONITORING_TRIGGER`

No new production enum or schema is created.

## Negative controls

### Invented / paraphrased target

The same valid CATL Evidence is paired with a plausible paraphrase:

> 资本配置是否会削弱未来自由现金流？

That wording is **not** the exact frozen Research commitment, so lineage validation fails closed.

The semantic idea may be related; the audit identity is still invalid.

### Valid CATL announcement from the wrong packet

The real later CATL announcement `1225502236` is supplied as Evidence for the 2026-08-12 commitment match. It is a valid CATL official disclosure, but it belongs to the separate 2026-08-25 address-change packet.

The validator rejects it because:

```text
valid source somewhere in later CATL history
!=
Evidence inside this exact assessment input
```

### Semantic no-match control

The real 2026-08-25 CATL disclosure changes the principal place of business in Hong Kong. The reviewed disclosure-cognition gold result is `DROP_FOR_NOW / PRE_RESEARCH` with no decision-context impact.

Its packet is mechanically valid and correctly bound to the same frozen CATL Research state. That does **not** imply a commitment match.

This is important:

> exact lineage is necessary after a semantic match; exact lineage does not manufacture semantic relevance.

Commitment Radar v0 therefore does not add keyword rules, embedding similarity thresholds, LLM confidence scores, or generic relevance scoring.

## Human Decision conditions remain outside this experiment

The broader Commitment Radar idea may eventually include explicit Human decision conditions, but current Human Decision / Action / Outcome accountability is deliberately preserved outside Kernel state through prospective audit artifacts and immutable Git history.

This experiment does not copy those conditions into `ResearchSnapshot`, create `HumanDecision` entities, or infer Human commitments from Research approval, price bands, or nearby actions.

A future cross-boundary link should be dogfooded only when one real prospective Human condition and one later real Evidence event require it.

## What this proves

```text
DISCLOSURE ACQUISITION MECHANICS = ALREADY PRESENT
EXACT PRIOR-COMMITMENT LINEAGE GAP = REAL
ZERO-SCHEMA EXACT LINK = VIABLE
SEMANTIC MATCH = RESEARCH COGNITION, NOT KERNEL TRUTH
EXACT LINEAGE AFTER MATCH = MECHANICALLY AUDITABLE
HUMAN WAKE = UNCHANGED
```

## What this does not authorize

Do **not** infer from this one experiment that the project should add:

- a Kernel `Commitment` entity;
- a Radar state machine;
- a second Human attention / wake gate;
- a generic relevance score;
- keyword or embedding routing as Kernel law;
- a new receipt identity yet;
- Human Decision conditions inside ResearchSnapshot;
- a scheduler, queue, database, or generic Radar service;
- Surprise Radar ranking or stock-selection logic.

## Promotion threshold

Promotion into a reusable Harness primitive is not yet authorized.

Require at least one additional naturally encountered case where:

1. a new qualified Evidence packet semantically bears on a different frozen Research commitment;
2. preserving the exact commitment link materially improves recall, triage, or auditability;
3. the case is not merely another CATL capital-allocation variant;
4. the link can be added without creating a second Human wake policy.

A real prospective case should take priority over further Commitment Radar framework construction.

## Disposition

```text
COMMITMENT RADAR v0 = VIABLE AS ZERO-SCHEMA HARNESS PATTERN
CURRENT PRODUCTION GAP = EXACT MATCH-TO-COMMITMENT LINEAGE NOT PERSISTED
KERNEL CHANGE = NO
RESEARCH SCHEMA CHANGE = NO
HUMAN WAKE CHANGE = NO
HARNESS PROMOTION = NOT YET
SURPRISE RADAR = SEPARATE NEXT PRODUCT EXPERIMENT
```
