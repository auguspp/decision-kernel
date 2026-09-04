# Next conversation handoff — Sector Discovery Radar

Date: **2026-09-05**  
Repository: `auguspp/decision-kernel`  
Clean verified implementation baseline before the state-only sync PR: `e3d8611b40d7b59694d1d86a4d85c8342de1cd39`  
Authority: **SHADOW OBSERVATION ONLY / HUMAN ATTENTION AUTHORITY NONE / INVESTMENT AUTHORITY NONE**

## Read this first

Do not continue from chat memory alone.

1. Fetch current `main`; confirm it includes the state-sync PR that added this file.
2. Read `docs/project-state.md` completely.
3. Read, in order:
   - `docs/sector-discovery-radar-prior-art-and-v0-decision-2026-09-04.md`
   - `docs/sector-discovery-radar-frozen-pit-replay-result-2026-09-04.md`
   - `docs/sector-discovery-radar-884-replay-result-2026-09-04.md`
   - `docs/sector-discovery-radar-current-breadth-proof-2026-09-04.md`
   - `docs/sector-discovery-radar-full-current-hierarchy-result-2026-09-05.md`
   - `docs/sector-radar-state-bootstrap-2026-09-04.md`
4. Inspect these contracts before writing code:
   - `src/decision_kernel/runtime/sector_radar.py`
   - `src/decision_kernel/runtime/sector_breadth.py`
   - `src/decision_kernel/runtime/sector_radar_shadow.py`
   - `src/decision_kernel/runtime/sector_parent_hints.py`
   - `src/decision_kernel/runtime/sector_radar_state.py`
   - `src/decision_kernel/adapters/hithink_index.py`
   - `src/decision_kernel/runtime/hithink_index_http.py`
   - `src/decision_kernel/runtime/hithink_sector_breadth_http.py`
5. Verify the current workflow directory. At handoff time there is no Sector Radar scheduler.

Repository state and frozen files are the source of truth. Previous chat text that claims a daily Sector Radar producer, persistent future ledger or production activation is not authoritative unless current `main` contains it and a real workflow artifact proves it.

---

## What has been completed

### Discovery design

The project has an accepted, explainable Sector Discovery Radar v0:

```text
5 / 20 / 60-session relative strength
rank change / acceleration
persistence / trend age
turnover pulse
current constituent breadth for finalists
```

It deliberately excludes a composite opportunity score, LLM ranking authority, automatic Research routing and investment authority.

### Replay evidence

- 90-member `881*.TI` broad replay:
  - agriculture and livestock could have been found before the final acceleration;
  - trend age is visible;
  - broad-only shipbuilding coverage is insufficient.
- Separate 230-member `884*.TI` replay:
  - recovers marine-equipment and water-product distinctions;
  - is too noisy to replace 881 as the primary universe;
  - must remain separately ranked.
- Current breadth proof:
  - distinguishes broad participation from concentrated leadership;
  - requires visible denominator and concentration for tiny groups;
  - proves parent-child duplication must be removed.

### Pure runtime contracts

Merged code now supports:

- exact frozen-PIT 881/884 calculations;
- current constituent breadth;
- false-to-true shadow state entries;
- hierarchical grouping and deterministic 0–3 compression;
- current-PIT parent hints with candidate-time containment revalidation;
- content-hashed 127-session rolling state;
- exact next-session append and same-session idempotence;
- strict HiThink industry catalog, index history/snapshot, current membership and all-A-share snapshot acquisition.

### Durable initial data

The 2026-09-04 bootstrap contains:

```text
127 sessions
1 benchmark
90 broad industries
230 granular industries
321 total series
state hash 3a87b66cdf947b0102634d31f29e31adfc1a8b2c2151c425c26b55ae3ed226cd
```

Parent hints contain 230 exact current-PIT child→parent mappings. They are routing hints, not permanent taxonomy.

### Main-branch health repair

PR #183 initially left a fail-closed identity omission and a one-time repair workflow on `main`. PR #184 fixed the source directly, kept the regression, removed that workflow and produced:

```text
main baseline = e3d8611b40d7b59694d1d86a4d85c8342de1cd39
main CI run = 33930589341
pytest = 342 passed
```

Do not reintroduce a temporary self-modifying repair workflow.

---

## What has not been completed

This is the most important part of the handoff:

```text
scheduled Sector Radar workflow = absent
daily prospective producer = absent
future rolling state cache = absent
candidate-state cache = absent
prospective candidates = 0
prospective T+5 / T+20 evaluations = 0
Attention Inbox integration = not authorized
```

The merged modules are prerequisites, not the product loop.

---

## Next task

Build the **independent prospective daily Sector Radar shadow producer** from clean green `main`.

### Required behavior

```text
load durable bootstrap or exact later persisted state
→ fetch current formal industry catalog
→ qualify the latest completed-session index snapshot
→ require direct one-session continuity
→ append exactly one completed session
→ reconstruct previous/current 881 and 884 snapshots
→ emit only false→true shadow entries
→ use 881 as primary and 884 as bounded secondary
→ revalidate frozen parent hints only for surfaced granular children
→ group parent/child and siblings without mixing ranks
→ fetch current memberships and all-market snapshot only for finalists
→ calculate current breadth
→ retain the complete candidate/group artifact
→ publish at most 3 shadow groups in a separate GitHub Summary
→ persist exact market state and candidate state
```

### First implementation slice

Keep the first PR narrow:

1. Add a runtime composition root for the above pure contracts.
2. Add parsers/serializers for persistent candidate state only if the existing shadow types do not already provide a complete content-hashed representation.
3. Add tests for:
   - clean bootstrap load;
   - one-session append;
   - same-session rerun;
   - missed-session failure;
   - catalog drift;
   - 881/884 separate ranks;
   - parent-hint validation;
   - breadth coverage failure;
   - unchanged strong-sector suppression;
   - deterministic full artifact and 0–3 summary.
4. Do not add scheduling until this composition root passes full CI.

Second PR may add the independent workflow, cache/artifact lifecycle and one real post-close proof.

### Persistence discipline

A cache is an optimisation, not truth.

```text
cache restored + exact hash + direct continuity
→ may append

cache missing / malformed / stale by more than one completed session
→ fail closed
→ publish explicit operations state
→ do not silently restart from the 2026-09-04 seed
```

A later explicit recovery mechanism may rebuild from qualified checkpoint lineage, but ordinary daily runs must not bridge gaps.

### Candidate-time hierarchy discipline

Never trust the parent hint by itself.

```text
surface 884 child
→ verify current catalog
→ fetch current child membership
→ fetch hinted 881 parent membership
→ require full containment
→ only then group
```

Do not fetch memberships for all 320 industries every day.

### Output discipline

The Human-visible shadow summary should answer:

```text
what changed?
how old / mature is the move?
is current participation broad or concentrated?
which granular driver is inside which broad parent?
what failed or was unavailable?
```

Always display:

```text
SHADOW OBSERVATION ONLY
NOT RESEARCH
NOT A RECOMMENDATION
HUMAN ATTENTION AUTHORITY = NONE
INVESTMENT AUTHORITY = NONE
```

Do not insert this surface into `decision-inbox.yml` yet.

---

## Prospective evaluation after activation

After the first real false→true candidate:

- freeze signal-time path, identity, formula, benchmark, universe and breadth state;
- later add objective T+5 and T+20 sector/benchmark/excess outcomes;
- keep original signal immutable;
- record false-positive/false-negative candidates;
- review repetition suppression and 0–3 compression;
- do not tune thresholds until a meaningful prospective corpus exists.

---

## Non-negotiable guardrails

```text
no mixed 881 / 884 ranks
no historical membership backfill
no permanent-taxonomy assumption
no composite opportunity score
no automatic Research route
no third canonical Human wake
no Recommendation / Action
no stale price or provider fallback
no missed-session bridge
no silent cache reset
no daily 320-membership fan-out
no threshold tuning to retrospective examples
```

Sector strength is only a discovery fact. It does not prove listed-company revenue, profit, owner cash, valuation or odds.

---

## Existing live-case posture

Do not change without new discriminating evidence:

- CATL: followed; cheapness/probability not established; numerical Odds withheld; no Human decision/action.
- GigaDevice: conditional buy only under its frozen price/thesis conditions; no action.
- Sanhua: conditional buy around CNY30; no action.
- Tinavi: WATCH / NO_ACTION.
- Micron: WAIT / DO NOT BUY; next natural hinge 2026-09-30.
- unresolved `DEEPEN_REQUIRED`: none.

---

## Completion definition for the next conversation

A satisfactory next round ends with:

```text
composition root merged and full CI green
independent workflow merged only after the root is proven
first real post-close run reviewed
persistent state continuity proven
no duplicate same-session candidate
full audit artifact retained
0–3 separate shadow groups rendered
no canonical Attention Inbox insertion
open PR / issue state explicitly reported
docs/project-state.md synced with only real deltas
```
