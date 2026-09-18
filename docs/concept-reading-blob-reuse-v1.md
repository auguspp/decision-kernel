# Concept publication reserve: reuse already-present immutable Git blobs

Continues #297/5728699813. The first #435 normal publisher succeeded but its
concept lane was rejected at BUDGET_PREFLIGHT: Rb9dea6db5d014970e8e9071304e97a0ce1624063
retained83 companies, concept0, READ_OK_WITH_SOURCE_GAPS. This is a real failed
integration acceptance, not a passed238-company production reading.

Reuse Decision: REUSE + THIN_ADAPTER. Keep the original publisher's Git tree,
commit, exact current-state readback and fast-forward-only ref update untouched.
Git object content identity already exists; avoid re-uploading identical objects
from the previous immutable reading. No source acceptance, budget or schedule
changes. The total API envelope is still180+72 and retained output is still128MiB.

The concept-aware CLI alone uses `GitHubReadReuseAPI`, a thin subclass of the
existing GitHub API client. At the concept stage it reserves two bounded GitHub
reads, resolves the exact previous reading commit to its tree, and requires a
complete/nontruncated tree with valid unique paths, blob identities and modes.
Only after the whole tree qualifies does it expose a frozen set of proved existing
blob hashes. Invalid proof supplies no cache. The prior identity cannot change
within this publication. Default/non-concept calls keep the old API client.

The native publisher still passes the actual complete raw bytes to its unchanged
`publish()` function. For its exact base64 `git/blobs` call, the thin cache computes
the content's Git hash. If it is proved present, the existing object identity is
returned without another network POST; `blob_reuse_hits` records that fact and
API call counters are NOT incremented. This is object reuse, not a fabricated
remote write acknowledgement. Unknown or changed bytes use the original POST.
All tree/commit/ref writes and final readback use the original client unchanged.
The CLI reports READ_BLOB_REUSE_HITS separately from READ_ENTRY_COMMIT.

Radar reserve checks use the same pending-blob rule and include final replacement
index/README bytes before publication. Unknown future payload files stay reserved
conservatively. Network calls already spent are never reset. Concept gaps now
include finite calls/files/pending-write counters. Failed optional input still
cannot erase already-read Sector/institutional data or bypass final reserve.

A previous blob's existence is NOT source qualification: latest run, attempt,
clock, unexpired artifact, original response replay and implementation identity
are still independently required. An old payload in Git cannot revive an expired
or failed new source. No third source dispatch or production retry is introduced.

Tests exercise the real existing get/write/publish logic with a mocked wire,
proven same bytes vs changed bytes, path rename, incomplete/malformed tree, true
network counters, unchanged unprimed behavior, reserve for changed final indexes,
failed final readback and a synthetic large-prior-reading concept integration.
The old publication function is unmodified. Actual PR/main CI and a new ordinary
publisher with raw-retention readback remain separate gates; this note does not
pre-certify them. Full continuous concept trends, redundant detail selection and
new Pre/Quick remain outside this correction.

External reuse: GitHub's official Git Trees API documentation, checked2026-09-18,
https://docs.github.com/en/rest/git/trees . Tree entries may reference existing
blob SHAs; complete-tree/truncated semantics are used, not a custom object store.
