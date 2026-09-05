# Sector Radar: replay-gated publication

Status: IMPLEMENTED PREPUBLICATION CHECK / REAL WORKFLOW PROOF STILL REQUIRED.

## Why this change

The producer already seals decoded provider inputs and supports exact offline replay. Previously, sector-radar-shadow could publish its state artifact and cache without invoking that replay. The context page also did not prove that the actual upload files matched the sealed outputs. This change composes existing capabilities rather than adding a producer, replay engine, state store or new workflow.

The existing manual workflow now runs:

```text
restore latest successful artifact and compare cache
→ run audited producer, seal inputs and create runner-local state
→ invoke existing offline replay with market credential cleared
→ require MATCHED_SUCCEEDED and live provenance
→ bind audit repository/workflow/run/attempt/commit to this execution
→ compare all three upload-state files and all ordinary outputs byte-for-byte
→ render the existing read-only context
→ upload complete audit (also when earlier steps fail)
→ only on success, upload authoritative state and save cache
```

The small .github/scripts/verify-sector-radar-publication.py script is workflow-specific glue around sector_radar_audit.replay_sector_radar_input_audit. It does not fetch network data or update a market state. No dependency, detector, ranking, gate, current membership rule, restore authority, schedule or candidate transition semantics changed. GitHub's documented success() condition requires preceding steps to succeed; always() is reserved here for preserving audit and displaying the actual outcome. See https://docs.github.com/en/actions/reference/workflows-and-actions/expressions#status-check-functions .

## What is checked

A successful calculation is not enough. The precheck requires the exact implementation and sealed inventory accepted by the existing replay verifier. It rejects synthetic audits, a reproducible REJECTED run, another run's identity, unsealed/stale outputs, incomplete bundles, symbolic links and any upload-byte difference (including whitespace-only changes). It refuses an existing receipt rather than overwriting it. The replayer's standalone CLI can legitimately return success for MATCHED_REJECTED; that is deliberately not accepted for state publication.

The new publication-verification.json is outside input-audit/, so it does not mutate the sealed audit. It binds run identity, audit hash, replay result, state/ledger hashes and the hashes of actual compared upload files. Its semantics are LOCAL_PREPUBLICATION_CHECK_NOT_REMOTE_ARTIFACT_OR_CACHE_SUCCESS. It is not a restore source, a Human review or a new authority.

A precheck failure may leave the newly calculated runner-local state on the ephemeral runner: the producer finished before this step. It must not upload that state as the next authoritative artifact or save its cache. The previously successful remote state chain is unchanged. The full failed audit is retained. Context generation or later upload/cache failures likewise do not become a successful workflow just because this precheck passed.

The existing context reader is unchanged. It reads the checked state, creates no events, keeps 881/884 separate and leaves historical breadth unavailable instead of reusing it. The later context JSON/HTML is not part of the producer's sealed output inventory or this byte-comparison receipt; context identity is separately validated by its existing renderer and integration tests. A context link is not a claim that all remote publication steps succeeded.

## Verification and limits

Tests reuse the existing SyntheticProvider HTTP-shaped fixtures, real adapters, relative-strength calculations, gates, composition, persistence, offline replayer and context renderer. They cover same-session validation, one-session quiet append and one-session candidate append. The LIVE code branch is tested only with mocked transport under pytest temporary directories and blocked sockets; this is not real LIVE_HITHINK evidence. Separately, explicitly SYNTHETIC_TEST_ONLY audits are rejected by the publication check. No fixture is uploaded into the real state chain.

The last independently verified real Sector run at the start of this change was #4 / 33939414197, whose implementation predates the input-audit format. It cannot be retroactively converted into a new-format audit or publication receipt. Its market state ends 2026-09-04, with an empty prospective ledger. New-session acceptance remains pending; offline tests do not alter this fact.

## Next real acceptance

Use a fresh main workflow_dispatch after the directly next completed session. Do not use Re-run jobs, fabricate the observation clock, enable schedule early, or bridge missing index sessions using a stock dump. If the first available snapshot is beyond the direct next completed session, qualified recovery is a separate prerequisite.

Check the exact run SHA and source artifact, one-session state append, 127-session window, current catalog, direct previous-price continuity, independent family calculations, candidate-time parent/breadth checks when candidates exist, publication receipt, context files, state artifact and cache. Download the actual run audit and independently replay it with the recorded implementation. Zero candidates can prove the quiet append path but not a live candidate-enrichment path. Remote success, same-day fresh-dispatch idempotence and the absence of historical candidate backfill must be reported separately.

This work makes no provider request, adds no push/schedule trigger to sector-radar-shadow and does not change existing company postures or canonical Inbox routing.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
