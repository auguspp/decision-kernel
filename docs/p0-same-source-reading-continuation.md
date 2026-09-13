# Same-source reading continuation — P0, 2026-09-13

**Reuse Decision: THIN_ADAPTER.** #297 Human permission 5649730121,
pre-construction Reuse Check 5649753465. This is the specific continuation of
603986's 2026-09-10 group and 300750's 2026-09-11 group, not general retry authority.

## Reuse and identity

Use the existing `research_runs/disclosure-continuation-request.json` with an
explicit v2 `HUMAN_AUTHORIZED_SAME_SOURCE_READING_CONTINUATIONS` envelope. V1
still requires a different qualified saved packet and discriminating source.
V2 binds the SAME byte-exact parent packet, a retained pre-execution source
failure, the genuine Issue response and the reading shown before that response.
It does not create a new assessment key, new discovery or independent PDF source.

The existing `saved-disclosure-research` workflow and its `continue-research`
input remain unchanged. Default false never consumes this enabled v2 request.
True selects only the finite listed parents from the exact original saved scan,
not the FIFO's exhausted old questions or a newly selected company. All target
bindings are checked before any child preparation; shared capture failures stop
before mutation. A per-question failure stops the explicit continuation batch.

The parent packet and failure stay where they are. Each successor uses:

`<original-key>/continuations/<permission-comment-id>/`

with execution ID `saved-disclosure-<original-key>-reading-<permission-comment-id>`.
Changing code, time, explanatory wording or representation hashes cannot obtain
another execution for the same parent/permission. Another permission ID already
present in this parent family also blocks this first-recovery mode; subsequent
continuation needs its actual latest predecessor/materials, not reuse of the old
root failure. Any prior child preparation,
failure, launch or result blocks automatic execution. No marker deletion,
renaming, silent resume, source packet copy or automatic retry is supported.
New authority cannot be inferred from an AI-written GitHub username.

## Original checks, execution and retention

The original source archive, capture manifest, pypdf extraction identity and
#342 same-PDF representation checks still run. V2 additionally requires the
exact set of missing/damaged required PDFs to receive bound readable page
representations. Actual reading hashes enter the frozen public context. For
scanned pages, the real main-pinned visual note is checked again before egress.
This is new readability of the same original source, not new independent Evidence.
Tables, signatures and economic effects are not certified by these hashes.

Reuse the original preparation, declared Discovery cutoff and commit-time
barrier, original input model, original admission, original #337 launch marker,
Pre / conditional Quick, candidate validator and Retainer. Permission is checked
from the actual Issue comment again after launch/admission and before a model
call. The code checks bindings and time, not Human intent or source truth.
The interaction layer's actual scoped interpretation is recorded in #297.

The exposed reading uses an exact Git-blob-pinned reference, as already supported
by `_checked_source`. Its actual fetched bytes supply the SHA256 used in the
original input model. No invented hash, reconstructed historical reading or
current exposure substituted for the original shown version is used.

The original Collector now reads both the parent failure and its separate child
outcome. Children are explicitly marked `new_disclosure=false`, have their own
execution identity and carry no automatic handoff/Research/Human attention or
investment authority. Seven parents plus two children need nine reading items;
the explicit registry capacity moves from eight to ten. The original source-file,
API, retained-byte and publication reserves remain unchanged. Capacity failure
stays an explicit read gap and cannot damage baseline market publication.

## Verification and operation

Synthetic tests reuse the existing fake Git, source preparation and Pre/Quick
fixtures, and call the original admission/executor/Collector. They cover two
companies sharing one consent without sharing executions, immutable parents,
repeat and partial-history blocking, revoked/misbound/future permission, missing
visual material, model failure, original v1 and default-FIFO preservation, and
child outcome reading/budget isolation. Synthetic permission/visual records are
not presented as real Human responses or issuer facts.

Local tests use a verified archived repository baseline plus exact relevant
current files. They are not a complete current-main checkout. Local dependency
versions and missing SDK are not substituted for pinned complete PR CI. Full PR
CI, code review, expected-head merge, main CI and ordinary read-entry publication
remain separate acceptance steps. Real same-source preparation and model output
still require a live native run and subsequent semantic review.

For the recorded two-item request, after release verification use ONE fresh
native dispatch with `source-run-id=34601025149`, `continue-research=true` on the
verified main. Recheck main and active/queued/uncertain invocations first. Do not
use Re-run or ordinary false-mode dispatch to reopen exhausted keys. An uncertain
request must be reconciled, never automatically sent again. Existing natural
publication remains the result delivery path.

No scheduler, workflow, provider, dependency, parallel executor, Kernel model or
investment authority is added. Sub2API's existing project resource grant stays
valid. CI or retained permission does not establish Research acceptance, a real
Human continuation outcome or 5–10 completed trading days.
