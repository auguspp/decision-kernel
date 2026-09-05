# Sector Radar: saved-state context, not another alert lane

Status: IMPLEMENTED READ-ONLY CLI / NO NEW SIGNAL / NO SCHEDULE / NO LIVE ACQUISITION.

## Product distinction

The existing producer summary remains the only 0–3-group *shadow* new-event projection. This command adds an on-demand view of all saved industry paths. A zero-event bootstrap or same-session run does not hide an already strong industry. Conversely, recalculating a transition from saved history must not create a prospective event.

The report has three folded read partitions for each of the two independent universes: paths satisfying an existing gate; paths with recent weakening or a gate exit; all industries ordered by exact code. Partitions may overlap. They are neither competing signal states nor additional top-three lists. There is no combined 881/884 rank.

`recent_weakening` means both the existing five-session change in 20-session rank and excess acceleration are negative. A gate exit means the previous predicate was true and the current predicate is false. These are declared presentation predicates only; they do not change selection, order, event persistence or Research authority.

Every industry displays 5/20/60-session sector, benchmark and excess returns plus ranks/ratings; persistence and its left-censoring; rank change, acceleration and turnover pulse. In particular, relative resilience while falling is not described as an absolute gain. A left-censored run is shown as 'at least N sessions', without asserting a precise start date.

Three times remain distinct:

- trend start: from the actual saved price window, with censoring;
- system first observed: unavailable unless explicitly recorded; not inferred;
- first prospective event: first compatible record in the supplied ledger, not the start of the trend or first Human awareness.

The latest-session ledger must agree with market state, formula, benchmark, catalog and the recomputed candidate. Older incompatible records are not used to infer a current event. The ledger is read only after selection has been independently computed and never drives gate evaluation.

## Use

Use an extracted, trusted `sector-radar-state-bundle` plus the matching parent hints:

```bash
python -m decision_kernel.runtime.sector_radar_context \
  --bundle /path/to/sector-radar-state-bundle \
  --parent-hints radar_inputs/sector-parent-hints-2026-09-05.json \
  --output /path/to/new-context-report
```

Open `index.html`; `context.json` retains exact values and the context hash. No JavaScript, remote image, external font, public hosting or provider credential is needed. HTML source strings are escaped. Output must be a new directory outside all input paths; the state and event ledger are never written.

This first slice is a standalone read command, not automatically inserted in the producer workflow. Automatic artifact publication can be added separately after the view is reviewed. The existing workflow YAML, producer result, input-audit fingerprint set, event schema and canonical Attention Inbox are unchanged.

## Freshness and unavailable data

The header says exactly which saved market session was rendered and when. Calendar-day age is not a count of missing trading sessions. The command cannot assert that a saved bundle is the latest completed market state, because it makes no network call and has no newly qualified calendar.

The report does not fetch membership or reuse a previous day's breadth. It directs the reviewer to the same-session run audit for breadth and grouping. A saved strong path is not evidence of current participation, business improvement, cheapness or a recommendation.

## Verification

Tests run the saved 321-series bootstrap and the existing real-calculation synthetic pipeline. They cover active paths with an empty event ledger, separate 90/230 universes, exact latest-session event reconciliation, determinism, no state writes/network, future-ledger rejection, clocks, left-censoring, HTML escaping and output-path protection.

These are software tests, not a new live provider proof. First real next-session append, real-input audit replay, benchmark sensitivity, multi-day constituent breadth and schedule remain separate work.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
