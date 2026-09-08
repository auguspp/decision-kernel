# External execution identity: read exact pairs, fail closed on promotion

This is a Harness guard, not a Kernel schema, state database, scheduler or Research
registry. It performs no Web/market acquisition and creates no Research/Human state.
The existing single-candidate validator and original Funnel are unchanged.

## Observed failure and demand-side disposition

The Human accepted #287 / CI `34238567252` as a real **fail-closed execution-gap
sample**, not complete Research. That acceptance is demand-supplied; CI success
alone cannot supply it. #285 v1 keeps deterministic PASS / complete-Research
semantic FAIL. Both actual v2 attempts remain `INCOMPLETE_SOURCE` and unaccepted
as complete Research. #285 and #287 must remain separate DRAFTs.

Their shared execution_id is `p0-4a-605296-2026-09-08-v2`, but their input keys differ:

| Origin | Frozen input commit | Canonical input hash |
|---|---|---|
| #287 | `fd0fb8f96ddff135530ee0c12a4b44fa5db4adbd` | `0d20328995d5da2a31b6af2a0578c003304d3c676ea2828695acbef008d0ab55` |
| #285 | `1d6e2053714982e7add41531f40dd723411b5f17` | `a1092651e5240013f31aeaef511c62f56fc09d68606888883acd218ccada4cd7` |

`research_runs/execution-inputs.json` records only immutable input references for
identity checking. It is NOT `current_state/registry.json`, a handoff registration,
an accepted Research record, or a new execution. Exact input byte copies under
`tests/fixtures/execution-identity/` support offline regression; neither historical
branch/path/input/candidate/receipt is renamed or edited. No v3 is started.

## Guarded interfaces

`runtime/external_research_identity.py` exposes:

- `ExecutionKey(execution_id, canonical_input_hash)`: both components required.
- `read_bound_execution(input_raw, candidate_raw, expected)`: parse the installed
  input model, recompute canonical hash, bind candidate AND receipt, then call the
  original validator. A historical exact pair remains readable even if its name
  is conflicted; reading/validation never means promotion.
- `load_execution_scope(catalog_raw, load)`: verify every declared input's pinned
  repository/commit/path/blob and recomputed key BEFORE choosing any result.
  Duplicate identical keys are idempotent; different hashes under one id are not.
- `require_promotion(...)` and `check_handoff_registration(...)`: mandatory gates
  for external-execution promotion and proposed handoff admission. Conflict raises
  `EXECUTION_ID_CONFLICT` for BOTH inputs, including an otherwise valid complete
  candidate. Incomplete input scope, missing binding, invalid receipt or source,
  and `EXECUTION_GAP` also reject admission. No flag selects a preferred collision.

These gates are necessary, not sufficient for semantic promotion: demand-side
acceptance and original handoff authority still apply. This batch adds no formal
registry writer, automatic promotion, semantic-approval boolean or Human writeback.
The unchanged historical `external_research_execution validate` command is a
single-pair audit tool, explicitly NOT an alternative promotion endpoint.

A proposed external entry carries `external_execution` alongside its existing
`source`/registration metadata: `execution_id`, `canonical_input_hash`, and exact
`input` and `candidate` source specs (repository/ref/path/git_blob). Its existing
handoff Funnel must equal the result validated from that exact candidate. Source
text cannot supply tool permissions, acceptance or a replacement catalogue.

## Existing read-entry integration and update limits

The current-state Collector now calls `project_registered_handoffs`, which reads
the catalogue at the Collector's pinned code commit and uses its existing bounded
GitHub source loader. This adds only GitHub file reads and retained read copies,
not market requests, retries, new providers or a schedule. Input reads are memoized
by exact source. One read never resolves main again or uses a name-only lookup.

Conflicts appear under `research.handoffs.gaps` / `execution_identity_scope`, never
`pending`. A registered external handoff is denied before the old projection;
its exact binding is included in an admitted reading. A bare handoff using a
catalogued discovery id cannot evade the check by omitting external metadata.
Unrelated legacy explicit handoffs keep their original validation and resolution
semantics, including when the external input catalogue is unavailable.

This is an explicit checked scope, not a cross-repository/global lock. New external
inputs must be added as exact references before promotion. Recheck the current
pinned catalogue at admission; an earlier clean scope does not certify a later
catalogue. Manually bypassing the Harness or changing trusted code/registration
files is not prevented by a Python helper or a soft tool boundary. Do not claim
that undiscovered branches are automatically reconciled.

Code CI, real-input conflict regression, downstream read-entry publication and
consumer acceptance must be reported separately. No natural Sector acceptance,
Research completion or real normal/adversarial executor pair is signed here.
Next completed research must use a different already legal observation, first
preflight only source accessibility, then freeze a fresh identity/cutoff/budget.
Preflight is not Research. Missing sources still yield EXECUTION_GAP; no budget
extension, no third Shennong attempt, and no use of the colliding v2s as a matched
pair. #263, the 18:13 schedule, recovery/provider rules and all authorities remain
unchanged.
