# Sector Radar hierarchical shadow contract — 2026-09-04

Status: **SHADOW EVALUATION CONTRACT / 881 AND 884 RANKS REMAIN SEPARATE / CURRENT-BREADTH QUALIFIED / NO CANONICAL HUMAN WAKE / NO INVESTMENT AUTHORITY**

## Purpose

Compress broad and granular market observations into a small, auditable shadow surface without allowing parent and child industries to consume duplicate attention slots.

The contract follows the completed evidence sequence:

```text
90-member 881 frozen-PIT replay
→ separate 230-member 884 challenger replay
→ bounded current constituent breadth and overlap proof
→ hierarchical shadow composition
```

## State-entry semantics

Two transparent challenger conditions are retained for prospective shadow evaluation:

```text
PERSISTENT_TOP_DECILE_ENTRY
= 20-session cross-sectional rating >= 90
+ positive 20-session excess return
+ at least five consecutive sessions of positive 20-session excess
+ emit only on false-to-true transition

ACCELERATING_ENTRY
= 5-session rating >= 90
+ 20-session rank improvement >= 20 places over five sessions
+ positive 20-session excess acceleration
+ positive 20-session excess
+ at least five sessions of positive 20-session excess
+ turnover pulse >= 1.2x
+ emit only on false-to-true transition
```

These are versioned shadow challengers, not promoted investment detectors. An unchanged strong industry remains quiet.

## Universe separation

```text
881*.TI
= broad industry comparison universe

884*.TI
= separate granular comparison universe

mixed percentile or rank comparison
= prohibited
```

Formula version, benchmark, exact universe identity, names and observation sessions must agree between consecutive snapshots or state-entry selection fails closed.

## Current breadth requirement

Every candidate used in hierarchical composition must have a same-session `SectorCurrentBreadthObservation` carrying:

- exact current constituent-set hash and capture time;
- member and priced-member counts;
- coverage;
- advancer / decliner / unchanged counts;
- equal-weight mean and median return;
- turnover and positive-return concentration;
- visible missing or unpriced members.

Current breadth remains a proxy only. It does not claim historical breadth or index contribution.

## Parent-child composition

Parent-child links are built only from exact current constituent sets and retain both membership hashes and capture clocks.

Composition rules:

1. a fully contained 884 child does not automatically consume a second shadow slot when its qualified 881 parent is already present;
2. the broad candidate remains primary and qualified granular candidates appear as visible drivers;
3. when the broad parent is not a candidate, the strongest transparent granular state entry may be primary while the 881 parent remains context;
4. multiple qualifying granular siblings under one non-candidate parent are grouped into one economic-context card;
5. unlinked or only partially overlapping granular candidates remain separate;
6. all candidates and groups remain in the full artifact even when only three groups are shown;
7. compression order uses explicit lexicographic state fields, not a composite opportunity score.

## Integrity checks

Composition fails closed when:

- broad or granular families are mislabelled;
- formula, benchmark, policy or session identity disagrees;
- candidate sessions disagree with the entry set;
- current breadth is missing or from another session;
- candidate and breadth names disagree;
- parent links duplicate a child or point to a non-candidate child;
- membership hashes or capture clocks disagree with breadth lineage.

## Authority

```text
PROSPECTIVE_SHADOW_OBSERVATION_ONLY

Fundamental Belief change = NO
Research route = NO
canonical Attention Inbox insertion = NO
Recommendation = NO
Action = NO
Investment Authority = NONE
```

The next operational step is prospective state persistence and outcome capture, not immediate production alerting.
