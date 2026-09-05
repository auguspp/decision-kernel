# Sector Radar — bounded input audit and offline replay

Status: **IMPLEMENTATION AND SYNTHETIC INTEGRATION COVERAGE / NOT A NEW LIVE PROOF / NOT A PROSPECTIVE CORPUS / NO SCHEDULE / NO INVESTMENT AUTHORITY**

Implementation PR: #193. The last real operational proof remains the successful bootstrap and same-session restore runs documented in `docs/sector-radar-live-bootstrap-restore-proof-2026-09-05.md`.

## Purpose

Retain enough exact inputs to repeat provider qualification and the existing producer calculation offline. A green workflow or a result hash alone does not make the original input qualification independently replayable.

This is a Harness audit capability. It does not add a signal, threshold, ranking authority, Research route, Human wake or investment authority.

## Production entry point

The existing `sector_radar_producer` command now invokes an audited wrapper after the ordinary persistence resolver has selected and validated the input state. The workflow YAML is unchanged. Its existing complete-run artifact upload includes the new `input-audit/` directory and `observations.json` when present.

```text
resolve and validate the ordinary artifact/cache input state
→ freeze exact input market state, event ledger, parent hints and run context
→ capture only provider requests actually used by the existing adapters
→ calculate in a temporary state directory
→ retain and seal input audit plus expected output bytes
→ read back and verify the audit inventory and hashes
→ publish the state bundle with the existing transactional writer
```

A calculation, qualification, acquisition, audit-write or audit-validation failure cannot publish the staged state. Failure during final directory replacement uses the existing bundle writer's backup/rollback behavior. The old target is covered by byte-preservation tests, including a failure after it has been moved to backup.

The audit manifest's `SUCCEEDED` status describes the staged producer calculation. It is **not** proof that final state publication, artifact upload, cache save or the entire workflow succeeded. Those remain separate operational checks. A retained calculation can replay successfully even when a later storage operation failed.

## Captured inputs

The recorder accepts only the existing exact endpoint families and their declared parameter keys:

- normalized calendar source envelope;
- current industry catalog envelope;
- requested index snapshot and benchmark historical prices;
- current memberships for the actual candidate/parent request plan;
- the pages of the same-session all-A-share snapshot, only when candidates require them.

One calendar response is used throughout an audited run. Recording does not make extra provider requests, retry until success, widen the member universe or enrich only the displayed top three.

Each successful request record contains the path, exact parameters, capture clock and a content-addressed response file. Transport failures retain the request identity and exception class, not response bodies or potentially secret-bearing exception messages.

The capture is **decoded JSON**, not original HTTP wire bytes. JSON object ordering/spacing is normalized for file hashing; finite JSON numbers retain their decoded representation. Provider JSON file hashes are distinct from domain content hashes. The domain Decimal/date canonical encoder is not used to hash raw JSON floats.

Observed-at and run-clock ISO offsets are preserved where the existing state format uses those exact strings. Converting an equivalent instant to a different offset would change that established market-state hash contract, so replay does not rewrite it.

## Audit layout

```text
sector-radar-run/
├── operations.json / operations.md
├── observations.json                 # new-session previous/current observations
├── preparation.json / preparation.md # when preparation was reached
├── result.json / summary.md           # when composition completed
├── same-session-validation.json       # same-session branch only
└── input-audit/
    ├── manifest.json
    ├── inputs/
    │   ├── market-state.json
    │   ├── candidate-events.json
    │   ├── parent-hints.json
    │   ├── context.json
    │   └── resolution.json
    ├── responses/0000.json ...
    └── expected/
        ├── state/                    # successful staged bundle only
        └── output/                   # complete or partial calculated outputs
```

The manifest binds every retained file's byte size and SHA-256, ordered request identities, observed clocks, provenance, disposition and relevant implementation-file hashes. It has its own content hash. Missing, extra, reordered or changed inputs are not silently accepted. Symlinks and paths outside the fixed inventory are rejected.

`observations.json` retains full previous/current 881 and 884 snapshots separately. Per identity it exposes both existing gate predicates' previous/current booleans, whether the gate entered, remained active or was inactive/exited, and the actual selected event type. It reuses existing predicates; it does not reimplement thresholds. The ledger is not an input to gate decisions.

This full observation record supports later false-negative review. It does not classify every omitted sector as a missed investment opportunity.

## Offline command

Use the recorded implementation checkout and its pinned project environment. Extract a trusted workflow run artifact, then run:

```bash
python -m decision_kernel.runtime.sector_radar_audit /path/to/sector-radar-run/input-audit
```

The command verifies relevant implementation file hashes before replay. A documentation-only commit does not invalidate matching implementation files; a code change does. It does not silently rerun an old audit using a changed detector.

Replay has no provider-network path, workflow-dispatch action, cache-save action or caller-selectable production-state output directory. It regenerates files in a disposable temporary directory, consumes the recorded request/clock sequence and compares the resulting inventory and every output byte with the sealed expected outputs.

The report carries:

```text
MATCHED_SUCCEEDED or MATCHED_REJECTED
original provenance
original audit hash
network_calls = 0
production_state_writes = 0
replay_semantics = OFFLINE_VERIFICATION_ONLY_NOT_A_PROSPECTIVE_EVENT_OR_RECOVERY
all authorities = NONE
```

A replayed rejection remains a rejection. The CLI's zero exit code means the recorded disposition and output bytes were reproduced, not that rejected provider input became valid.

The CLI does not extract untrusted archives, execute supplied code, import modules named by an audit or fetch missing data. A request-order or output mismatch fails rather than skipping records or returning a partial success.

## Credentials and operational budgets

No HTTP authorization headers, cookies, API keys or environment snapshots are recorded. Credential-like JSON fields and the active credential value are rejected before response persistence; they are not silently redacted into a different allegedly exact response.

```text
maximum recorded requests = 128
maximum file size = 8 MiB
maximum total retained file bytes = 64 MiB
```

These are bounded storage/request protections, not opportunity thresholds. Exceeding them blocks successful state publication. The existing 32-distinct-membership acquisition limit is unchanged.

A sensitive or oversized response intentionally is not retained. A crash during capture can leave an incomplete `RECORDING` audit. Such records may explain a failure but cannot receive a matching full replay report. Final filesystem failures and outer CLI failure summaries are not simulated as provider responses.

## Synthetic integration proof

The tests create an explicitly synthetic 127-session history and HTTP-shaped envelopes. Real normalization, benchmark qualification, relative-strength calculations, separate-universe ranks, false-to-true gates, membership containment, breadth, grouping, event append, bundle loading and artifact/cache resolution execute. Candidate selectors and gate results are not patched.

Covered paths include:

- a real calculated next-session quiet result;
- a calculated new broad/child pair grouped into one context;
- restoring the resulting artifact/cache state and same-session validation without duplicate events;
- continued active market conditions staying quiet, both with and without event memory;
- price discontinuity, catalog drift, parent noncontainment, zero priced breadth, pagination duplication, transport interruption and a missed session;
- matching replay of successful calculations and recorded rejections with the network boundary disabled;
- corrupted, incomplete, reordered or mismatched audit files and source-manifest references;
- credential exclusion and operations budgets;
- audit-before-publication ordering and old-state preservation at disk-failure boundaries.

Injected transports must declare `SYNTHETIC_TEST_ONLY`; that wrapper mode never publishes its calculated state to the live target. Tests of the default production wiring replace the lowest transport in pytest and use only temporary directories and dummy credentials. They are not live provider proofs. No test artifact is uploaded into the real state chain or prospective corpus.

## Limits and unchanged product state

Hashes establish internal integrity and reproducibility, not provider authenticity or financial truth. Inspect the trusted GitHub run and artifact lineage separately. Offline replay does not prove the remote cache bytes or a later artifact upload; those require operational evidence.

The input audit starts after ordinary state resolution. It records the selected source manifest and exact state files but does not repeat GitHub discovery or cache download offline. Existing artifact-authoritative restoration rules are unchanged.

Previous run #3/#4 artifacts did not retain this input format. They cannot be retroactively upgraded into fully replayable input proofs.

The existing 90-day run-artifact retention applies; this PR adds neither a long-term checkpoint nor a missing-session recovery mechanism. No schedule, objective T+5/T+20 evaluator, Human annotation layer or Inbox integration is added.

The next live milestone remains an exact direct completed-session append after the 2026-09-07 close, subject to the actual provider calendar and qualified data. These synthetic tests do not replace that proof, and a valid zero-candidate result must not be forced into an event.

```text
SHADOW OBSERVATION ONLY
NOT RESEARCH
NOT A RECOMMENDATION
HUMAN ATTENTION AUTHORITY = NONE
INVESTMENT AUTHORITY = NONE
```
