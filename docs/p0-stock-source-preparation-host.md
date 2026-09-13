# Stock source-only preflight in the existing host

Status: source preparation only; not Research admission, a recovery successor,
Human acceptance, monitoring registration, or investment authority.

## Scope and reuse

Continues #297 Human response / Reuse Check 5652950925 and implementation handoff
5653558242. Reuse Decision: THIN_ADAPTER. The only targets are 603353.SH (Heshun)
and 300711.SZ (Guangha), under the two unexecuted source-recovery-v1 failures shown
in reading fe6a00cd85656396dd089a2db81fcabb9b9fc54c after run 34751517820.
600184.SH and 300183.SZ completed candidates remain untouched.

Use the original stock-business-research workflow and Stock run validation,
source selection, CNINFO transport, PDF/PDFium and preparation_only capture.
The source-only branch exits before run_item, Retainer, admission or model use.
No new scheduler, provider, parser, dependency, Research executor or work ref.

The trusted request is research_runs/stock-source-preparation-request.json.
The original authorizer verifies the exact main request and original Human
comment identity/body/time. Pinned source checks verify the exposed reading and
failed recovery selection/failure, their commits preceding the Human response,
the same original qualified Stock observation, and unchanged current history.
Any launch/input/candidate/Funnel/admission/receipt under that failed recovery
blocks preparation. Source checks never reset or append to those work items.
Permission and current history are checked again before each company capture.

## Explicit execution mode

Only after exact-head CI, review, main CI and normal publication acceptance:

```text
workflow: stock-business-research
ref: main
source-stock-run-id: "34673882756"
prepare-sources: true
recover-sources: false
```

Use one fresh native workflow_dispatch after checking for an already issued,
active, queued or unverified invocation. No Re-run or automatic retry. Do not
reuse recover-sources=true; its source-recovery-v1 work was already consumed.

The prepare-stock-sources job has contents/actions/issues READ permissions and
no Sub2API secret. The existing model job is excluded when prepare-sources is
true. CLI modes are mutually exclusive; source-only requires native dispatch,
attempt 1, exact main identity and absence of a model credential. Its ordinary
artifact is stock-source-preparation-<run>-<attempt>; no Research launch is made.

## What must actually be checked

source-preparation-batch.json binds the request, prior failures and the original
Stock input. Per-issuer sources/source-preparation.json, source-journal.json,
full PDFs and extraction/page representations remain in the same artifact.
The original capture enumerates missing required visual reviews; unrelated
transport, identity and security errors do not become successful source checks.
Any unavailable remainder stays explicit. Error text does not expose credentials.

Only complete required bodies produce prepared-context.json. The original
448KiB context and 512KiB checked-reference limits remain unchanged: oversized
complete context is retained but remains PREPARATION_INCOMPLETE, not WAIT,
Research acceptance or input readiness. A successful job is not a semantic
review of every PDF/table and is not an instruction to begin model execution.

The fixed reader distinguishes latest workflow invocation, latest identified
Research attempt, and latest source-preparation attempt using exact job identities,
not workflow green status or a title. It checks at most ten invocations within the
existing publication call reserve. Missing, inaccessible, queued-without-jobs or
ambiguous mode metadata stays explicitly unclassified; saved business candidates
and failures are still read. Source-only metadata never manufactures a new Pre,
Quick, quiet state or automatic Human handoff. These are invocation metadata,
not an independent acceptance of the source artifact's contents.

## Still not implemented by this change

The lossless large-context storage/decode/model-egress bridge is not deployed.
Do not encode a context and send compressed text to the existing model loop,
remove required bodies, or widen shared identity limits merely to pass a run.
Use the exact complete source-preflight artifacts to close all storage, source
reference and final Pre/Quick request-size checks together. Any later Research
must separately bind that complete input to the failed history and actual Human
permission; no new execution key or permission number is a retry mechanism.
