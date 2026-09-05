# Sector Radar — live bootstrap and same-session restore proof — 2026-09-05

Status: **LIVE SAME-SESSION VALIDATION AND RESTORE PROVEN / NO NEW-SESSION APPEND YET / PROSPECTIVE CORPUS EMPTY / NO SCHEDULE / NO INVESTMENT AUTHORITY**

Repository: `auguspp/decision-kernel`  
Executed implementation: `5f8f635d191dd8559844d1b74af0dca0cf4c02df`  
Workflow: `.github/workflows/sector-radar-shadow.yml`

## Proven scope

Two fresh manual dispatches succeeded against the same completed market session, 2026-09-04:

| Run | Number | Attempt | Restore source | Conclusion |
| --- | ---: | ---: | --- | --- |
| `33938625934` | 3 | 1 | `COMMITTED_DURABLE_BOOTSTRAP` | success |
| `33939414197` | 4 | 1 | `LATEST_SUCCESS_ARTIFACT` | success |

Both executed on `main` at the implementation SHA above. Run 4 started at `2026-09-05T02:33:36Z` and completed at `2026-09-05T02:34:08Z`.

```text
status = VALIDATED_ALREADY_CURRENT_NO_PROSPECTIVE_EVENT
state_update_status = ALREADY_CURRENT_IDEMPOTENT
latest_cached_session = 2026-09-04
latest_completed_session = 2026-09-04
prospective candidates = 0
candidate event ledger = empty
membership requests = 0
same-session all-A snapshot acquisition = not invoked
```

This is evidence for bootstrap validation, durable workflow-state publication, recovery from the immediately preceding successful artifact, cache agreement and same-session idempotence. It is not evidence for a future-session append or candidate quality.

## Run 4 recovery evidence

The job log records:

```text
cache restored = sector-radar-state-33938625934-1
prior_success = True
artifact_available = True
prior_run_id = 33938625934
downloaded state artifact id = 9961018489
input source = LATEST_SUCCESS_ARTIFACT
new cache saved = sector-radar-state-33939414197-1
```

The downloaded predecessor ZIP digest matched the published GitHub digest. The producer's persistence resolver strictly loaded both the restored cache bundle and the authoritative artifact bundle, checked their manifest and market/event hashes, and returned the artifact as the restore authority. It did not fall back to the committed bootstrap.

Run 4 operations records the predecessor manifest hash:

```text
input_bundle_manifest_hash
= bdc50a2fbe8615c3637a51b6ea0918a7a3399d7e47206c2e9dff944d9a2c281e
```

This equals the manifest inside run 3's downloaded state artifact.

## Frozen artifact identities

### Run 3 predecessor state

```text
name = sector-radar-state-bundle
artifact id = 9961018489
ZIP SHA-256 = 2fc14a8d3d02f3c7d9ed21f8b9fb315bb16aabd73ed9dad4ad02291344fc6f06
bundle manifest hash = bdc50a2fbe8615c3637a51b6ea0918a7a3399d7e47206c2e9dff944d9a2c281e
```

### Run 4 state and audit

```text
name = sector-radar-state-bundle
artifact id = 9961284050
ZIP bytes = 431180
ZIP SHA-256 = 3c8c3bec756932abed10de450666f5814aec3c82938acf79cbe7c27487f95539
bundle manifest hash = d730a78e1580a23dd167fa8ac28a411b569a9ddeacf3c8e386b3cc8803e079fd

name = sector-radar-run-33939414197
artifact id = 9961283551
ZIP bytes = 2465
ZIP SHA-256 = a91165eedba443fabb4d31ee543b2d0ab3f0e03855e149aead7714c6d7791fba
operations hash = a7c46a5fc2192b7a6ac8e2d8c89bd7e5e60e7cfb71588eddfa304c9c1201d41d
same-session validation hash = 20a38915168b95e85e28d4a57debf19849f0de5319f49dfb8660d8a4ce4b88e4
```

Run 4 artifacts have a declared 90-day retention window and GitHub reports expiry at `2026-12-04T02:33:37Z`. Immutable upload identity does not imply indefinite retention. There is no automatic long-term checkpoint in v0; an unavailable latest successful state artifact still requires explicit qualified recovery.

## Independent file and content-hash checks

The two state ZIPs and run 4 audit ZIP were downloaded for offline inspection. Verification used the repository's canonical JSON rule: UTF-8, sorted keys, compact separators, excluding each object's own hash field.

Checks passed:

- all three downloaded ZIP digests matched their GitHub identities;
- both manifests' content hashes recomputed exactly;
- each manifest's market-state and event-ledger file SHA-256 matched the contained bytes;
- market-state and candidate-ledger content hashes recomputed exactly;
- run 4 operations and same-session validation content hashes recomputed exactly;
- run 4's input manifest hash matched run 3's manifest;
- `market-state.json` was byte-for-byte identical between runs 3 and 4;
- `candidate-events.json` was byte-for-byte identical between runs 3 and 4;
- input/output state and ledger hash references reconciled across manifest, operations and validation records;
- the state retained 127 sessions, 321 series, 90 broad identities and 230 granular identities, ending on 2026-09-04;
- the ledger contained zero events.

Frozen observed identities, not replacement bootstrap authority:

```text
market-state content hash
= 2963d7fa62757a56e7296b3d9855a7d6d067d59816738078361f86c51d1f41d7

market-state file SHA-256
= 2c2d659570db1de13552d4358ee3ea9560948bbc8b271c0755edc569cd45f920

event-ledger content hash
= f58b84b97127444242596e98c5ea514750cf82358e7e7ad3b247e4a6225aff09

event-ledger file SHA-256
= cecbde2c9d4b90dd33f9a0b5a1d2ceb02e9b71533e4bbfb2ad40ce5d1e633ecd
```

The bundle manifest and ZIP hashes changed normally because run identity and update time changed. Market state and event-ledger bytes did not change. Same-session idempotence applies to those underlying states, not to the per-run provenance wrapper.

The committed bootstrap manifest remains the sole canonical bootstrap identity source: `radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json`.

### Limits of this review

Offline inspection verified artifact integrity and state lineage; it did not replay raw HiThink network responses, which are not included in these audit ZIPs. Successful live qualification is evidenced by the executed producer and its validation record. The cache payload was not independently downloaded for this review; cache/artifact agreement is evidenced by the cache-hit log and the persistence checks executed by the successful run.

## Earlier failures remain part of the record

- Run `33936773283` failed before same-session validation because the provider calendar did not expose a later session. PR #190 moved exact same-session validation ahead of the future-session requirement.
- Run `33937883228` failed because the index snapshot data-ready date was treated as the market session. PR #191 separated those meanings while retaining benchmark-price and calendar qualification.

Neither failed run published a successful state bundle. The failures are not deleted or reclassified by the later successes.

## What is still unproven

```text
first post-bootstrap completed-session append = not executed
live false-to-true candidate production = not observed
live candidate-time hierarchy/breadth within this producer = not exercised
prospective candidate corpus = empty
objective T+5 / T+20 outcomes = not started
Human review annotations = not started
schedule = absent
canonical Attention Inbox integration = not authorized
```

The zero-event result means validation-only, not a new-session screening result declaring that the market has no qualifying opportunities.

## Next step

No further same-session dispatch is required to repeat this proof. The next validation target is a fresh `main` dispatch after the 2026-09-07 close, with the actual next completed session still determined from the provider calendar and qualified snapshot.

```text
restore latest successful state, ending 2026-09-04
→ require exactly one subsequent completed session
→ require every provider prev_price to equal the cached close
→ append only 2026-09-07
→ retain full audit and persist both states
```

Zero candidates on that new session would be a valid quiet outcome. Do not force a candidate to demonstrate functionality. If the latest completed session is already 2026-09-08 or later while state still ends at 2026-09-04, ordinary production must fail closed; recovery remains a separate qualified procedure.

Review the real new-session append before adding a schedule. Signal-time events, objective outcomes and Human annotations remain separate; no threshold tuning or Inbox promotion is earned by this operational proof.

```text
SHADOW OBSERVATION ONLY
NOT RESEARCH
NOT A RECOMMENDATION
SIGNAL TRANSITION AUTHORITY OF LEDGER = NONE
HUMAN ATTENTION AUTHORITY = NONE
INVESTMENT AUTHORITY = NONE
```
