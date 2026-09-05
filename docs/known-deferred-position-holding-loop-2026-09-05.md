# Known deferred gap — Position / Holding Decision Loop

Status: **DEFERRED / FUTURE DOGFOOD TARGET / NO NEW KERNEL SCHEMA / NO AUTOMATION**  
Recorded: **2026-09-05**  
Repository: `auguspp/decision-kernel`

## Purpose

The current system is intentionally incomplete after the first real executed investment Action.

Existing Research, Decision Hygiene, Human Decision, Action and Outcome protocols already preserve several relevant boundaries, but they do **not** yet define a live position-management loop for what happens after a position exists.

This note records the gap only. It does not solve it.

## Known unresolved questions

Future real-position dogfood should determine, at minimum:

- how a live position is re-underwritten after a material price move or material new evidence;
- what to do when an expected-horizon return is realized materially earlier than expected;
- how to respond to a large adverse price move without laundering price action into Fundamental Belief;
- the semantics of later `HOLD / ADD / REDUCE / EXIT` Human Decisions;
- when an earlier Human Decision should be superseded by a new PIT decision while preserving the original lineage;
- how later opportunity cost and portfolio / capital-allocation constraints should interact with a single-security decision.

## Already-established boundaries

The following existing principles remain in force:

```text
evaluation horizon != automatic exit date
price change alone != Fundamental Belief change
favorable short-term PnL != validation of the original decision
adverse short-term PnL != invalidation of the original decision
Human Decision != Action
Investment Authority = NONE
```

Existing first-entry decisions may specify a first tranche and an evaluation horizon without thereby defining an automatic sell rule.

## Deliberate non-decisions

Do **not** infer or formalize yet:

- fixed take-profit percentages;
- automatic stop-loss percentages;
- a generic sell score;
- a Position Kernel entity;
- a Holding state machine;
- automatic `HOLD / ADD / REDUCE / EXIT` decisions;
- portfolio optimization or target-weight authority;
- a claim that a material price move itself proves thesis change.

Ideas discussed before real dogfood — including forward-Odds re-evaluation after rapid gains, review rather than automatic sell authority after large losses, or treating `HOLD` as a renewed PIT choice — remain hypotheses, not accepted production policy.

## Disposition

```text
DEFERRED UNTIL FIRST REAL EXECUTED POSITION
DOGFOOD REAL POSITION PATHS BEFORE DESIGN
NO SCHEMA / LIFECYCLE / AUTOMATION UNTIL A REAL FAILURE REQUIRES IT
```

When the first real position exists, freeze the actual path and use it to discover the smallest necessary operating protocol. Do not backfill a theoretically neat Holding Module before reality creates the requirement.
