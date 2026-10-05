# Sector Radar prospective producer operations

Status: **MANUAL SHADOW WORKFLOW CONTRACT / NO SCHEDULE / NO CANONICAL HUMAN WAKE / NO INVESTMENT AUTHORITY**

## Purpose

This document defines the first independent operational shell around the merged pure Sector Radar composition root.

```text
qualified persistent state
→ current HiThink calendar and formal-industry catalog
→ latest completed-session index snapshot
→ exact continuity check
→ pure daily preparation
→ candidate-only membership acquisition
→ current breadth and hierarchy revalidation
→ pure finalization
→ immutable run artifact
→ next persistent state artifact
```

The workflow remains separate from `decision-inbox.yml` and is started only by `workflow_dispatch`. It has no schedule in this phase.

Each execution must be a **fresh** `workflow_dispatch` with `GITHUB_RUN_ATTEMPT = 1`. GitHub's “re-run jobs” action is rejected because it reuses a run identity and can collide with artifacts from an earlier attempt. A same-session idempotence proof therefore uses a second fresh dispatch, not a rerun of the first run.

## Authority boundary

Every run remains:

```text
SHADOW OBSERVATION ONLY
NOT RESEARCH
NOT A RECOMMENDATION
HUMAN ATTENTION AUTHORITY = NONE
INVESTMENT AUTHORITY = NONE
```

The producer does not mutate Fundamental Belief, probability, Odds, Human Decision or Action. It does not route candidates into the Research Funnel or canonical Attention Inbox.

## Signal-state authority

False→true remains determined only by the previous and current snapshots reconstructed from `SectorRadarMarketState`.

```text
previous/current market state
→ sole false→true calculation authority

candidate event ledger
→ append-only signal-time audit
→ same-event idempotence
→ later objective outcome alignment
→ signal-transition authority = NONE
```

The event ledger is never consulted by the selector to decide whether a candidate is active or newly triggered.

## Restore authority

The exact state artifact from the **newest prior successful run of the same workflow on `main`** is the ordinary restore authority.

```text
latest successful state artifact
= restore truth

Actions cache
= byte-identical acceleration copy only
```

The discovery step first qualifies a current native workflow-run frontier as described below, then inspects only the newest prior successful main run's state artifact. If that artifact is absent or expired, the producer does not inspect an older successful run's artifacts because doing so could bridge an unobserved state transition.

### Cache and artifact rules

```text
artifact valid + no cache
→ restore artifact

artifact valid + cache valid + identical manifest/state/ledger hashes
→ restore artifact; cache is accepted as an identical copy

artifact valid + cache disagreement
→ fail closed

prior successful run exists + artifact missing/expired
→ fail closed
→ explicit qualified recovery required

cache exists without matching successful artifact authority
→ fail closed
```

The committed 2026-09-04 bootstrap is allowed only before the workflow has any successful state-producing run and only when no cache exists.

## Retention and expiry

Both the complete run-audit artifact and the persistent state bundle use:

```text
retention = 90 days
```

There is deliberately no automatic long-term checkpoint in v0.

```text
latest successful artifact expired
→ do not trust cache alone
→ do not fall back to an older artifact
→ do not restart from the 2026-09-04 bootstrap
→ run a separate explicit qualified recovery procedure
```

A later recovery implementation may construct a new checkpoint from qualified source lineage. That is not part of ordinary daily production and is not silently invoked by this workflow.

## Persistent bundle

The state artifact is named:

```text
sector-radar-state-bundle
```

It contains:

```text
manifest.json
market-state.json
candidate-events.json
```

The manifest binds:

- producer contract version;
- repository, workflow, run, attempt and commit identity;
- exact completed market session;
- market-state file SHA-256 and content hash;
- event-ledger file SHA-256 and content hash;
- formula, shadow policy, benchmark and catalog identity;
- parent-hint mapping identity;
- latest result hash and operation status;
- 90-day retention and explicit expiry policy;
- zero signal-transition, Research, Human-attention and investment authority.

The workflow publishes in this order:

```text
1. complete run-audit artifact
2. authoritative state bundle artifact
3. cache acceleration copy
```

Therefore a failure before the state artifact is uploaded cannot advance cache. A cache disagreement on a later run remains visible and fails closed.

## Completed-session discipline

The current trading calendar must contain the restored cached session. The producer determines the latest completed A-share session using the observation clock.

```text
latest completed session == cached session
→ exact same-session snapshot validation
→ no membership acquisition
→ no retrospective candidate-event append
→ publish unchanged market state and event ledger as a new validated bundle

exactly one completed session follows cached state
→ require that session to be the direct next calendar session
→ append exactly once
→ proceed to prospective composition

more than one completed session follows cached state
→ fail closed
→ ordinary production must not bridge the gap
```

For the committed initial state:

```text
cached session = 2026-09-04
direct next A-share session = 2026-09-07
```

A producer first run after 2026-09-07 that sees 2026-09-08 or a later completed session cannot use the ordinary bootstrap path.

## Acquisition budget

All false→true candidates entering hierarchical composition require current breadth. Every surfaced granular child also requires current child and hinted-parent memberships for containment revalidation.

The default high operations cap is:

```text
32 distinct current-membership requests per run
```

This cap is only an acquisition safety budget. It is not a signal threshold, opportunity score, ranking input or Human-attention gate.

```text
within budget
→ fetch every planned membership
→ fetch one same-session all-A snapshot
→ calculate breadth for every candidate

budget exceeded
→ retain the complete candidate and request plan
→ refuse finalization
→ publish no new persistent state
→ never silently enrich only the top three
```

Membership requests are sequential and minimally paced. There is no provider fallback or retry-until-success loop.

## Outputs

Each run retains a 90-day audit artifact containing, when available:

```text
operations.json
operations.md
preparation.json
preparation.md
result.json
summary.md
```

The Human projection remains bounded to 0–3 groups, but the full result artifact retains all candidates, all groups and all omitted groups.

A failed run uploads its operations and preparation evidence when those files exist. It does not upload or cache a new state bundle.

## Objective outcomes and Human review

Neither is implemented by this workflow slice.

When prospective candidates exist, later work must keep these separate:

```text
ObjectiveOutcomeRecord
→ T+5 / T+20 sector return
→ benchmark return
→ excess return
→ MFE / MAE
→ rank and gate persistence

HumanReviewAnnotation
→ whether Human had already noticed the move
→ whether it produced a useful Research question
→ reviewer, review time and rationale
```

Human annotations must never overwrite the signal event or enter the objective outcome hash.

## Activation sequence

```text
manual workflow merged
→ fresh same-session validation dispatch reviewed
→ first direct-next-session append reviewed
→ fresh same-session dispatch proves state and event idempotence
→ next completed-session append proves continuity
→ only then consider adding a schedule
```

Merging the workflow does not itself establish a prospective corpus or production schedule.


## 2026-10-05: qualify discovery before diagnosing a cache conflict

A real failed invocation, `37295151349` / job `111714511964`, restored cache
`sector-radar-state-36994240613-1` but discovery chose run `36554182248` and state
artifact `11027680899`. The downloaded digest matched. The producer then refused
`Sector Radar cache conflicts with the latest successful artifact` before market
acquisition. Independent run metadata now shows workflow run #42 was the failed
invocation, #41 (October 2) succeeded, and the selected #38 was September 29.
This establishes a stale selection, not corruption of the newer cache. The old
HTTP response bytes were not retained; their original ordering and the GitHub
service/cache cause remain UNKNOWN. Do not delete caches or relax equality checks.

The original discovery function now requests one unfiltered page of 20 workflow
runs, using the existing authenticated GET client. It must see this invocation's
exact run ID on main, validate the common workflow identity/path and unique native
`run_number` values, then walk every run number immediately preceding it. Page
ordering and larger cross-workflow run IDs do not select the parent. Later queued
invocations are not predecessors. A completed main success stops selection;
completed non-successes or explicitly other-branch runs do not become authorities.
An unfinished main predecessor, unknown conclusion/branch, missing run number,
missing current invocation, invalid/duplicate identities or exhausted page fails
before artifact lookup. No prior success is established only by reaching run 1.
Deleted history or a longer unqualified frontier requires reconciliation, not a
bootstrap, pagination search, repeated request, or an older usable artifact.

Only that selected success's state artifact is inspected. Existing missing,
expired, duplicate-artifact and strict bundle/cache identity checks remain. This
changes no persistence schema, source admission, provider route, cache contents,
workflow trigger, task clock, Human record or economic method. The maximum normal
GitHub call count stays two; run-list metadata grows from 2 to at most 20 entries.
It is not a new service or an atomic snapshot/future availability guarantee. It
cannot prove that a success status itself will never be corrected by the platform.

Reuse Decision: KEEP the native Actions REST client, run/artifact identity and
existing fail-closed persistence. The relevant public contract is GitHub's
[workflow-run API](https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-workflow)
and [run_number definition](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts):
the counter is unique per workflow, advances for each new run and not for reruns.
The current workflow's fresh-run requirement stays in place. Native metadata and
one bounded loop suffice; no cache manager, scheduler, external dependency or new
Outcome/Research entity is justified.

Local verification exercises the exact discovery definitions in a partial
checkout: 28 focused tests, including the two original artifact tests with updated
native-identity fixtures. Unrelated producer imports are excluded only in that
local runner; the committed tests import the actual full module in normal CI.
A separate replay uses a labelled reduction of actually retrieved current run
metadata with synthetic API assembly: the old code selects the modeled stale #38,
the correction rejects that page, and the current #42 frontier selects #41. The
artifact response in that replay is deliberately synthetic/missing. Neither this
nor the tests proves live provider acquisition, cache equality, formal full CI or
D research value. The old failed run and all immutable sources remain unchanged.

Delivery still requires normal exact-head full CI, independent main scope,
ordinary publication and readback. Actual Sector continuation is separate; do not
rerun the old failed invocation or perform a market request just to obtain green
status. If the API page is still incomplete, retain the precise discovery failure.
Rollback restores the prior discovery and associated fixtures through a normal PR;
never rewrite historical cache, artifacts or original failures to make it pass.
