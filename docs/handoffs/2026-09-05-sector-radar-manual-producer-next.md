# Next conversation handoff — manual Sector Radar producer merged

Date: **2026-09-05**  
Repository: `auguspp/decision-kernel`  
Verified implementation baseline before this state-only sync: `d0c18690f406d2a2d90b32048ede37f643669a93`  
Baseline CI: `33934306867` — **374 passed**  
Authority: **SHADOW OBSERVATION ONLY / HUMAN ATTENTION AUTHORITY NONE / INVESTMENT AUTHORITY NONE**

## Read and verify first

Do not continue from chat memory alone.

1. Fetch current `main`; confirm it includes the state-sync PR that added this file.
2. Read `docs/project-state.md` completely.
3. Read `docs/sector-radar-prospective-producer-operations.md`.
4. Inspect:
   - `src/decision_kernel/runtime/sector_radar_daily.py`
   - `src/decision_kernel/runtime/sector_radar_events.py`
   - `src/decision_kernel/runtime/sector_radar_persistence.py`
   - `src/decision_kernel/runtime/sector_radar_producer.py`
   - `.github/workflows/sector-radar-shadow.yml`
5. Verify current open PR / Issue state, workflow directory and latest `main` CI.
6. Inspect actual Sector Radar workflow runs and artifacts before claiming any live producer state.

Repository state, workflow artifacts and strict content hashes are authoritative over chat summaries.

---

## What changed in this round

### PR #186 — bootstrap identity source

The committed manifest is now the sole canonical bootstrap identity source:

```text
radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json
```

The mutable state index projects the correct manifest-backed state hash, and CI checks future documentation consistency.

### PR #187 — pure daily composition root

Merged pure contracts now provide:

```text
market state + current catalog + qualified snapshot
→ exact append or same-session no-op
→ previous/current 881 and 884 snapshots
→ false→true selection within separate universes
→ exact candidate membership plan

planned memberships + one same-session all-A snapshot
→ candidate-time parent validation
→ current breadth for every candidate
→ hierarchy composition
→ full audit artifact
→ bounded 0–3 Human projection
```

The high operations-only budget is:

```text
32 distinct current-membership requests per run
```

Exceeding it retains the complete plan and prevents finalization. It never silently enriches only the top three.

### Append-only event ledger

The content-hashed candidate event ledger is only:

```text
immutable signal-time audit
same-event idempotence
future objective-outcome alignment anchor
```

It has:

```text
signal-transition authority = NONE
Human attention authority = NONE
investment authority = NONE
```

False→true remains decided solely from previous/current market state.

### PR #188 — independent manual producer

The new workflow is:

```text
.github/workflows/sector-radar-shadow.yml
```

It is:

```text
workflow_dispatch only
main only
fresh run attempt only
separate from decision-inbox.yml
no schedule
no continue-on-error masking
```

The producer restores and persists:

```text
market-state.json
candidate-events.json
manifest.json
```

Ordinary restore authority is the exact state artifact from the newest prior successful run. Actions cache is accepted only as a byte-identical acceleration copy.

```text
cache/artifact disagreement
→ fail closed

newest successful artifact missing or expired
→ fail closed
→ explicit qualified recovery required

older artifact fallback
→ prohibited
```

State and run artifacts are retained for 90 days. No automatic long-term checkpoint exists in v0.

---

## What is still not proven

This is the key current-state boundary:

```text
successful Sector Radar workflow run = NONE
live HiThink validation = NONE
persistent live state artifact = NONE
persistent live cache = NONE
future completed-session append = NONE
prospective candidate event = NONE
T+5 / T+20 objective outcome = NONE
Human review annotation = NONE
schedule = ABSENT
canonical Attention Inbox insertion = NOT AUTHORIZED
```

The merged workflow is an operational prerequisite, not proof that the live loop has run.

---

## Immediate next action

Run a **fresh** manual dispatch of `sector-radar-shadow.yml` from `main`.

Do not use GitHub's “rerun jobs” command. The workflow requires `GITHUB_RUN_ATTEMPT = 1` so every state-producing execution has a unique run and artifact identity.

### Expected first proof on 2026-09-05

The committed state ends at 2026-09-04 and 2026-09-05 is a Saturday. The latest completed A-share session should still be 2026-09-04.

Expected path:

```text
verify committed bootstrap manifest and gzip
→ fetch current formal-industry catalog
→ fetch and qualify complete 321-series 2026-09-04 snapshot
→ require exact same-session close and turnover equality
→ no membership requests
→ no all-A snapshot
→ no retrospective candidate event
→ persist unchanged market state and empty event ledger
→ upload 90-day authoritative state artifact
```

A catalog, close, turnover, session or identity mismatch is a real proof failure. Do not weaken the fail-closed contract merely to make the first run green.

### Second proof

After the first successful validation, start another fresh manual dispatch:

```text
restore newest successful artifact
+ restore cache copy
→ require exact agreement
→ validate the same completed session
→ market-state hash unchanged
→ event-ledger hash unchanged
→ zero prospective events
```

This is the same-session restoration and idempotence proof.

### First prospective append

The direct next completed A-share session after the bootstrap is:

```text
2026-09-07
```

A successful post-close run on that session may append exactly one day. If the restored state still ends at 2026-09-04 and the latest completed session is 2026-09-08 or later, ordinary production must fail closed and use a separate qualified recovery procedure.

---

## Live-run review checklist

For every manual run, verify:

```text
run id and attempt
head SHA and branch
operations status
restore source kind
input and output market-state hashes
input and output event-ledger hashes
qualified completed session
candidate count
membership request count
preparation hash
result hash when present
state artifact id and expiry
run-audit artifact id and expiry
cache save result
```

First same-session validation must show:

```text
status = VALIDATED_ALREADY_CURRENT_NO_PROSPECTIVE_EVENT
state update = ALREADY_CURRENT_IDEMPOTENT
candidate event append = NONE
membership fetch = NONE
all-market fetch = NONE
```

Do not describe a run as successful based only on workflow conclusion; inspect the structured operations artifact and state manifest.

---

## Prospective outcome separation

After a real false→true event exists, later work must add two separate records:

```text
ObjectiveOutcomeRecord
→ T+5 / T+20 sector return
→ benchmark return
→ excess return
→ MFE / MAE
→ rank and gate persistence

HumanReviewAnnotation
→ whether Human already noticed the move
→ whether it produced a useful Research question
→ reviewer, reviewed_at and rationale
```

Human annotations cannot overwrite the signal event and cannot enter the objective outcome hash.

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
no older-artifact fallback
no daily 320-membership fan-out
no silent top-three-only enrichment
no GitHub job rerun for state production
no threshold tuning before a prospective corpus
```

Sector strength is a discovery fact only. It does not establish company revenue, profit, owner cash, valuation, probability or Odds.

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

## Completion definition for the next round

A satisfactory next round ends with verified evidence, not merely code presence:

```text
first fresh same-session validation reviewed
second fresh same-session restoration/idempotence run reviewed
state and run artifact identities reported
no retrospective event written
2026-09-07 direct append reviewed when the session is complete
future market state and event ledger persisted only after success
no schedule added before manual proofs
no canonical Attention Inbox insertion
open PR / Issue state explicitly reported
docs/project-state.md synced with only real deltas
```
