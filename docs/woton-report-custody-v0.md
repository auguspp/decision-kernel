# Known Woton report: source-only native Git custody

Scope: #297/5753902322, following Human “好，继续”. Reuse Decision:
**THIN_ADAPTER**. This closes the custody gap identified by #297/5750454664:
the previously acquired Sina issuer PDF was retained as an earlier chat file,
not as an Actions source artifact or a repository source record. That success
is not erased by the absence of that attachment in the current conversation.

## Exact bounded operation

The existing `stock-business-research` workflow has one additional, default-false
`retain-report-source` input and an isolated source-only job. All original jobs
reject that flag. The new job requires trusted exact main, dispatch, attempt 1,
no other mode and no source-stock-run-id. It installs only existing documents
and feeds extras and receives no model/market credentials. The request is fixed
at `research_runs/woton-report-custody-request.json`; its exact retained scope
and permission comment are checked before reservation and again before I/O.
The operator's short execution window ends at 2026-09-23T00:00:00Z; no renewal or
automatic retry is implemented.

The one permitted source is the already identified Sina 2026H1 issuer report:

`https://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESZ_STOCK/2026/2026-8/2026-08-21/12512184.PDF`

Expected: **1,262,185 bytes**, SHA256
`27c74e31c8aaf5a38d27b688f0841d81797816420b591647bfb6763e485b7728`,
133 pages, printed 000920 / 2026 / half-year identity. This is a mirror of an
issuer-authored report, not proven byte equality to CNINFO attachment1225486931.
No DataSinking service text is redistributed.

A create-only `prepare.json` under
`research_runs/sources/public-reports/<expected-pdf-sha256>/` on the ORIGINAL
`research-work/stock-business-v0` ref reserves this source attempt before a
single ordinary unauthenticated GET. An existing file at that prefix means
`EXISTING_SOURCE_ATTEMPT_NO_ACQUISITION`, not success or permission to retry.
The original Research roots, launch markers, daily slots and failures are not
changed. The root is content-bound, not a new economic question or execution.

Requests uses its existing streaming API and a fresh Session with trust_env=false;
no repository Authorization, .netrc/proxy credentials, custom disguise header,
redirect, fallback URL or retry. Partial downloaded bytes stay in the source
artifact. A different PDF does not receive the expected file's identity.

## Preserve original bytes before interpreting them

After the exact byte/length check, the original PDF is saved through the existing
Retainer's native create-only Git mutation. The existing PDF parser then reads
all 133 pages with original source limits; a missing or damaged text page remains
a source-representation failure. All page text is retained, without clipping.
No OCR, model, issuer query or economic inference is invoked.

The PDF is larger than GitHub Contents' inline-body threshold. The small adapter
therefore binds exact commit/path/size/blob metadata and reads the raw Git blob,
checking decoded bytes, SHA256 and Git blob identity. This does not widen
`ResearchInputSourceRef`, its 512KiB bound, the daily PDF/context/prompt budgets,
or the original Collector file reader. Binary custody and model-input admission
remain different operations. Raw metadata references must not be passed off as
admitted Research source refs.

A small `source.json` manifest binds the fixed scope, exact original and parsed
file references, source clocks, code and no-authority fields. `recover()` uses
the original small-manifest verifier, checks exact Git file/blob binding, and
replays the existing PDF parser against the retained bytes. It has no source
acquisition, model or write path. This proves byte custody and reconstruction,
not report truth, current disclosure completeness or Research acceptance.

A failed/uncertain mutation stops further writes. Original partial work remains;
no automatic retry or replacement is permitted. Native workflow artifacts retain
local original bytes and diagnostics for 30 days. Git is append-only under the
existing repository assumptions; it is not a guarantee against repo deletion or
force rewriting by another authorized actor.

## Correct attempt meaning and reuse

The existing Stock attempt reader recognizes the isolated job as
`latest_report_source_attempt`, separately from Research, legacy source
preparation and provider compatibility. A successful source workflow is not a
new Pre/Quick, daily Research success or a reset of the old source failure.

Internal review reused `saved_research_once.acquire/Retainer`,
`stock_research_host.authorize`, `GitHubAPI`, `adapters/pdf_text`,
`stock_daily_question.bind` and the original continuation contracts. The exact
three-layer acquisition/parsing/retention prior-art review remains the existing
`handoffs/2026-09-20-report-priority-and-reuse.md` and #297/5750454664; no new
provider/parser/scheduler or dependency was adopted. Requests' official Session
implementation and streaming/redirect contracts and GitHub Contents/Git blob
contracts were additionally inspected. Native GitHub.com dispatch now supports
25 inputs, so this eleventh input does not require replacing old typed fields.

Official references:
- https://requests.readthedocs.io/en/latest/user/advanced/#body-content-workflow
- https://requests.readthedocs.io/en/latest/_modules/requests/sessions/
- https://docs.github.com/en/rest/repos/contents#get-repository-content
- https://docs.github.com/en/rest/git/blobs#get-a-blob
- https://github.blog/changelog/2025-12-04-github-actions-you-can-now-use-up-to-25-inputs-in-manual-workflows/

## Verification stages and remaining P0 scope

New tests exercise a real synthetic 133-page PDF with a ToUnicode CJK mapping
and >1MiB inert padding, original parser and create-only Retainer, fake GitHub
boundaries, credential-free HTTP, expiry, duplicate/mixed modes, tampering,
partial failures, lost write responses, reconstruction and attempt classification.
They do not use a live issuer PDF or claim live acquisition.

Local focused tests used a verified historical source tree with exact relevant
current-main files and the proposed files, Python3.13.5/pytest9.0.2/pypdf5.9.0;
this is NOT the complete current-main checkout or the pinned CI environment.
Full unchanged exact-head CI, independent main CI and normal publication are
separate gates. Actual source-only dispatch, artifact checks, Git readback and
registration must be recorded from actual results; none is predeclared here.

After source custody, Woton remains the SAME original financial question.
Current daily NEW_DISTINCT/STATIC/CNINFO guards and the old 300711-specific
technical continuation remain unchanged; this source-only slice does not grant
a fresh Woton model call through either path. It enables direct use of the known
report and an honest future source-consumer connection without renaming the
question, lowering necessary source classes, or asking the Human to move files.
P0 new-input -> bounded Research -> Brief -> real Human response is not closed
by source retention alone. AI Investment Authority = NONE.
