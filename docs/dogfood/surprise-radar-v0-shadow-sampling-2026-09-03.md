# Surprise Radar v0 — short-lived real-window sampling

Status: **HARNESS SHADOW SAMPLING / NO DETECTOR / NO RADAR SCORE / NO HUMAN-WAKE CHANGE / NO NEW SCHEDULE**

Date: 2026-09-03

## Why this slice exists

PR #113 exposed the already-fetched HiThink 45-day completed raw-close window as a qualified Harness input. The next requirement is not an anomaly formula. It is a small body of naturally observed windows that can later be reviewed against what actually happened.

The repository did not yet contain enough natural price-history windows to tune or falsify even a simple price-dislocation rule. Historical manual and scheduled Decision Inbox runs were concentrated on 2026-09-02 and retained only point-in-time Decision Inbox outputs, not the underlying 45-day windows.

Therefore this slice adds **sampling, not scoring**.

## Existing automation only

No scheduler is added.

The existing `decision-inbox` workflow already runs on A-share weekdays after close and already has qualified HiThink credentials for its Human-facing Inbox job. This slice adds one independent shadow step to that same job:

```text
existing weekday Decision Inbox
        |
        +--> existing Human Inbox output (unchanged)
        |
        +--> short-lived market-history shadow artifact
```

The shadow step is deliberately `continue-on-error`. A sampling failure must not make the Human Decision Inbox unavailable.

## Capture boundary

`python -m decision_kernel.runtime.market_history_shadow` accepts the same current A-share Research packages used by the Inbox and captures one qualified HiThink history window per security.

Each JSON observation records only:

- capture time;
- package path;
- exact frozen `ResearchSnapshot` id / as-of / information-bundle hash;
- ticker / company / exchange / qualified HiThink `thscode`;
- unchanged HiThink market source and raw-close convention;
- provider response session and expected latest completed session;
- ordered completed-session closes;
- explicit `SHADOW_OBSERVATION_ONLY` boundary markers.

It does **not** record or compute:

- anomaly score;
- z-score;
- ranking;
- factor conviction;
- Research route;
- ParticipationZone;
- Human attention eligibility;
- Recommendation;
- Action;
- investment authority.

## Storage class

The output is classified as:

`ACTIONS_SHORT_LIVED_HARNESS_OBSERVATION`

It is uploaded as the existing workflow's `market-history-shadow` artifact with a 14-day retention period.

It is intentionally **not committed to Git**. A raw daily sampling stream is operational observation memory, not durable epistemic truth. Only reviewed examples that later become useful positive / negative / false-negative controls should be promoted into a durable evaluation corpus.

## Batch integrity

A shadow batch fetches and validates every requested case before writing any observation file.

If one security fails:

```text
case A fetch succeeds
case B fetch fails
        |
        v
NO partial observation set is written
```

This prevents an incomplete artifact directory from looking like a complete cross-case sample.

Duplicate current Research packages for the same qualified `thscode` also fail closed rather than silently overwriting one another.

## Why the shadow step is independent of Inbox

The cleanest long-term implementation may eventually reuse one market fetch for both the Human Inbox and Radar observation capture. That is not yet worth changing the `build-inbox` production contract.

For v0, the safer boundary is:

- leave Human-facing Inbox acquisition unchanged;
- run sampling as an independent Harness experiment;
- accept a small amount of duplicated commodity acquisition;
- make shadow failure non-fatal;
- wait for evidence that this sampling path is worth consolidating.

This favors product safety over premature runtime optimization.

## What happens after enough windows accumulate

No detector should be promoted merely because the artifact stream exists.

The first useful reviewed corpus should contain at least:

1. **positive control** — a clear price-path dislocation that later proved worth Research triage;
2. **negative control** — a large move that a Human later judges should have remained `IGNORE`;
3. **false-negative candidate** — a quieter path followed by important decision-relevant evidence;
4. cross-case diversity rather than repeated tuning on one security.

Only then should a simple explainable shadow rule be tested.

The evaluation target remains:

```text
mechanical observation
→ Human / Research triage usefulness
→ later Research consequence
```

not trading return and not stock-picking accuracy.

## Disposition

```text
QUALIFIED HISTORY INPUT = YES
NATURAL WINDOW RETENTION = NOW ENABLED, SHORT-LIVED
NEW SCHEDULE = NO
HUMAN INBOX FAILURE COUPLING = NO
RADAR DETECTOR = NO
RADAR SCORE = NO
HUMAN WAKE CHANGE = NO
KERNEL CHANGE = NO
NEXT = ACCUMULATE + REVIEW REAL WINDOWS BEFORE DETECTOR DESIGN
```
