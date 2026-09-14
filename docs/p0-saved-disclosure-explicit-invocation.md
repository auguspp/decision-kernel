# P0-C: explicit invocation of the existing saved-disclosure host

Status: IMPLEMENTATION CONTRACT / NOT A LIVE EXECUTION RECEIPT.
Authority: #297 Human 5660584568, RM5660297398; Reuse Check5662799515.
Reuse Decision: THIN_ADAPTER / REUSE_EXISTING_FIRST_ADDITION_AND_HOST.

## Scope and reuse

The connector's missing native workflow_dispatch operation must not require the
Human to shuttle run IDs between chats. This optional Harness adapter uses the
existing Sanhua first-addition main-commit pattern, GitHub's native push event,
and the SAME saved-disclosure-research job, concurrency group and original host.
Native workflow_dispatch and normal completed decision-inbox events still work.
No scheduler, dispatcher service, model loop or new Research identity is added.
The adapter does not affect Stock successor or source-recovery modes.

GitHub's maintained event documentation:
https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow
An ordinary GITHUB_TOKEN push generally does not generate another workflow run;
use an actually authorized connector/GitHub App invocation and verify the real
event. A successful Git write alone is not evidence a workflow started.

## Two separate changes, never a concealed launch

First accept the code PR, exact-head full tests, review, main tests and normal
publication. The implementation PR includes NO activation request. Afterwards,
check the current main, fixed reading, work ref and actual active/recent runs.
An explicit invocation is a separate reviewed single-parent main commit that
adds exactly one request and nothing else: no code, source, permission, registry
or legacy result edits. No automatic retry follows an uncertain write or run.

Request path is stable, not date-based:
- .github/saved-disclosure-invocations/scan-<source-run-id>.json
- or .github/saved-disclosure-invocations/continue-<original-request-sha256>.json

The second form selects the existing reviewed
research_runs/disclosure-continuation-request.json. It does not itself grant a
company-specific continuation or repair an already-consumed child identity.
The original continuation checker still verifies genuine permission and lineage.

Exactly these JSON fields are required:

```
schema_version: 1
profile: SAVED_DISCLOSURE_MAIN_REQUEST_V1
approved_parent: <exact accepted main before this request-only commit>
source_run_id: <exact successful saved decision-inbox run>
reading_commit: <current accepted read-model/current-state commit>
work_commit: <current research-work/disclosures-v0 commit>
continuation_sha256: null, or the exact existing continuation request SHA256
expires_at: <future UTC timestamp within the reading recheck window>
```

These placeholders are documentation, not an executable request. No new quota,
privacy permission or automatic Research authority can come from source text.
Project resource authorization5646037620 remains distinct from continuation
permission, Research acceptance, Human decisions and investment authority.

## Checks and composition

The adapter uses Git's committed bytes and mode, exact single parent and entire
diff. It rejects mixed commits, request edits, symlinks, invalid/duplicate JSON,
wrong stable paths, repeat attempts, prior history (including delete/re-add),
moved main/reading/work, and expired or mismatched reading identities. The original
read-package validator is called; the request-only child uses its accepted
parent's reading, not a invented new publication. No core validator is relaxed.
The adapter exports only checked integer/boolean/SHA values, not shell commands.

The original host rechecks the pinned reading and initial work before consuming,
and checks the first normal FIFO work snapshot again before reservation. These
checks plus the original concurrency/create-only/dedup/admission contracts are
not a global atomic lock. Legitimate writes inside this finite batch advance the
work ref; those are not mistaken for a competing invocation. Default paths keep
their previous behavior when these optional expectations are not supplied.

The full input path, source authenticity limits, original Pre and conditional
Quick, SDK bounds, no-progress/error handling and Retainer are unchanged. A scan
with no unreserved questions is a valid NOOP; it must not create new identities
or re-execute old failures simply to demonstrate the invocation.

## Retention, publication and acceptance

invocation-audit is separate until the original host has created run-output.
The always-save step copies it to run-output/invocation, preserving the existing
batch-receipt and artifact layout. A rejected invocation retains its own error
status, not a fabricated Research failure or WAIT. The normal publisher also
accepts completion of this specific saved-disclosure push event, including a
failure; it receives no model credential and grants no research acceptance.

Acceptance layers stay separate:
- synthetic real-Git and original-host regressions (no source/provider network);
- exact PR/main CI and normal fixed-reading readback;
- one genuinely authorized invocation and actual invocation/batch/artifact proof;
- natural producer-driven research, Human delivery/response, and real 5–10 days.

A NOOP demonstrates request-to-host-to-publication wiring, not new Pre/Quick.
A manual push invocation is not natural daily execution. An invocation cannot
repair prior missing source/provenance, certify model reasons or prove delivery.
If inputs change or the run fails, retain it and reconcile first; do not rename
a request, edit a consumed key or automatically create another attempt.

If reliable native dispatch becomes available, prefer that mature interface.
This optional, explicit first-addition route remains a replaceable Harness seam,
not a permanent Kernel cognition rule or a mandate to migrate other workflows.
