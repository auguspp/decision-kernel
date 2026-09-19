# Explicit on-demand Research archive navigation

Radar-r3 continuation of #440's actual source-file capacity rejection.
Reuse Decision: THIN_ADAPTER; #297 pre-implementation receipt5737711951.
This extends the existing purpose registry/Collector/archive reader and company
reading. It is not another registry, storage service, research engine or scheduler.

## Registration is not materialization

Existing references retain their original eager behavior. A new reference may
explicitly use `read_policy: ON_DEMAND_ARCHIVE`, but only with
`use: RETAINED_RESEARCH_DOCUMENT` and archive format `RETAINED_FILES` or
`RESEARCH_PROGRESS`. No Action, Watch, numerical Odds or COMMITTED package is
silently switched to deferred reading. Missing policy remains legacy eager;
unknown or malformed policy is a visible rejection with no eager fallback.

The archive_source must declare exact path/commit/blob/SHA256/byte count.
It must not also contain an eager source field. Older base collectors therefore
fail closed rather than accidentally fetching a future deferred declaration. The bounded
archive directory rules remain unchanged. A progress reference also retains its
external progress descriptor digest and exact question identity. The initial
registration must follow the existing actual archive/readback discipline; these
fields are declarations, not new proof of the source body or its economic claims.

The existing production Collector subclass projects these records into `research.on_demand_archives`.
This is a derived field of the existing reading, not canonical stored Research.
Qualification is `REGISTERED_ARCHIVE_NOT_MATERIALIZED`; no `read_path` or
same-reading-body assertion is invented. No source or archive API is requested
for these bodies. Original eager source/accounting and retained byte limits stay
unchanged. Registry/index metadata still consumes the original192KiB index and
128MiB overall retention budgets; this is not unlimited capacity.

README and company reading expose the exact historical archive link and explain
that its body is not in this reading. A locator-only company is not counted as
having a saved Research body/context. Existing research/failure/root and Stock
state remain separate, and unknown companies do not acquire research authority.
Multiple archive versions retain separate record IDs; no newest-wins policy.

## Recovery uses the original entry and validator

Use the existing command with ONE pinned R and explicit record ID:

```sh
python -m decision_kernel.runtime.research_archive \
  --reading-commit '<R>' --record-id '<registered-id>' --output '<new-directory>'
```

The reader validates the original sealed reading, exact same-R registry bytes,
and equality of the shown deferred declaration to the registered reference.
Ambiguity across eager and deferred entries is rejected. It then uses the existing
commit/tree/blob inventory and byte validation, and the original typed progress
reader. A locator cannot bypass missing/truncated trees, wrong hash/size/source,
foreign subjects/questions, missing progress bytes, or exclusive output I/O.
On success it adds `RECOVERED_ON_DEMAND_AFTER_REGISTERED_ONLY` to the receipt.
It does not rewrite the earlier daily reading into a claim that the body was read.

No fallback to main/latest, text execution, model/market/company-source request,
auto-continuation, remote writes, Human acceptance, Odds or Watch registration.
The original16-file/512KiB-per-file/24-call recovery bounds remain unchanged.
Errors preserve the original failure/partial-directory behavior.

## First real registration and limits

Fibocom300638.SZ already has a two-file progress archive at immutable250efdc82567f9988d43cadae0a5b715e50d85da.
This change registers it without rewriting its text/time/question or copying a
financial PDF that was never acquired. Eastsoft's existing eager reference and
all49 pre-existing references are retained unchanged. The original budget test
still asserts eager source specifications plus13 reserve fit MAX_SOURCE_FILES60;
it now separately verifies strict opt-in declarations rather than treating a
locator as an already-read body. Tests are not removed or skipped.

Acceptance requires full exact-head PR CI, independent main CI, normal publisher,
actual same-R visibility and original archive byte recovery. Synthetic tests and
local partial-checkout execution are not live Git recovery or research evidence.
This does not repair CNINFO PDF fetching, complete Fibocom financial research,
refresh Eastsoft triggers, run Pre/Quick, or complete Radar-r3's other dimensions.

External reuse checked2026-09-19: GitHub official Git Blobs/Trees documentation
and PyGithub's GitBlob implementation. Native immutable objects and the existing
reader already provide the required mechanism; no extra dependency is adopted.
- https://docs.github.com/en/rest/git/blobs
- https://docs.github.com/en/rest/git/trees
- https://github.com/PyGithub/PyGithub/blob/main/github/GitBlob.py
