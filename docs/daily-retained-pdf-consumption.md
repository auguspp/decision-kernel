# Daily Research: full retained PDF consumption

Scope: #297 / 5761785366 and the subsequent Human approval to implement the mainline connection.
Reuse Decision: **REUSE**. This change has no new command, dependency, downloader,
provider, scheduler, model call, or Research authority.

The daily host already downloads and qualifies its original source artifact.
For a PDF larger than the generic 512 KiB metadata/file reader, reuse those exact
artifact bytes. Resolve the declared immutable Git commit's complete bounded
tree and require the exact path, regular 100644 blob, length, Git blob digest,
SHA256 and historical commit clock. The PDF's CNINFO locator, issuer, original
source run, capture journal, complete extracted pages and context are still
checked by the original daily binder. No file body is fetched twice through the
Contents API; no arbitrary URL is followed. Small PDFs retain the original
checked-source reader.

The existing 32 MiB **aggregate** PDF budget, four-document maximum, 448 KiB
context and 512 KiB prompt are unchanged. Generic JSON, declarations, progress,
source manifests and normal file reads remain at 512 KiB. `retained_source_file_bytes`
continues to describe that generic path, not an additional budget for every PDF.
The PDF-only archive path does not widen `external_research_identity.MAX_BYTES`.
The original parser still reconstructs every page; large PDF size is not permission
to truncate text or convert unavailable material into a valid source.

A complete tree with the wrong path/blob, a truncated/oversized tree, a symlink,
executable or submodule, changed bytes, an invalid or future commit, or an
unqualified source artifact is rejected before a daily reservation/model call.
Cryptographic consistency is not issuer authenticity, truth or economic review.

## Reuse evidence

Internal: original `_source_archive`, `_saved_document`, `GitHubAPI.get`, Git
inventory conventions, existing hashes, PDF parser, and daily host tests. The
previous Woton `_read_blob` shows why file bytes and small metadata are distinct;
there is no need to generalize that case-specific downloader here.

Official: https://docs.github.com/en/rest/git/trees and
https://github.blog/changelog/2022-05-03-increased-file-size-limit-when-retrieving-file-contents-via-rest-api/.
A Contents JSON response for a large file is not guaranteed to carry inline base64.
Public mature-project failure evidence: hub4j/github-api#1558 and n8n-io/n8n#16417.
Their `encoding=none` failure mode informs the regression; neither Java nor Node
nor a new SDK dependency is needed when the verified original bytes already exist.

## Still separate

This slice does not change `_source_archive`'s native main-workflow identity gate.
An isolated FTShare/CNINFO probe is still not an accepted daily source run. The
retained Zhenjiang report can demonstrate byte binding, but must not be labelled
an actual daily Pre/Quick result. Importing its historical custody into the native
source path, enabling a fully bound request, real bounded execution, normal Brief
and Human response remain separate mainline work. No individual-company deeper
financial analysis is a prerequisite for this engineering step.
