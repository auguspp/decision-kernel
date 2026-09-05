# Handoff and evidence — real stock dump delivered, reference not qualified

Date: 2026-09-05. Repository: `auguspp/decision-kernel`.
Status: FIRST REAL RECENT-STOCK PARQUET RETAINED / PYARROW FOOTER READ / FULL ROW RECONCILIATION NOT RUN / NO MULTI-DAY BREADTH ADOPTION.

## Read first

Read `docs/project-state.md`, `docs/hithink-stock-dump-trial.md` and this record. Verify current main, full CI, open PR/issues and actual workflow artifacts. User direction remains reuse-first. Market work must not quietly become another generic ingestion platform. Requests and Apache PyArrow are used here; the official provider downloader was also reviewed, not claimed absent. Prior public-source and Sector proofs remain authoritative for their own limited scopes.

Implementation baseline before this documentation synchronization: `bde9bad7ef725fbca54f5c7a567227e6b9b7dd56`; main kernel CI `33957604920` completed successfully. Full code suite is 639 passing tests, up from 587 at this round's start. Tests ran in GitHub CI, not a claimed full local checkout. New cases physically write/read synthetic Parquet through the actual pinned PyArrow; synthetic cases are not real market evidence.

## Exact PR lineage

| PR | Base SHA | Head SHA | Merge SHA | Full PR CI |
| --- | --- | --- | --- | --- |
| #210 | 15aaa3aa14142db3cdb699d238e3b3f5dd0e3eca | 702bbbb0b4dfd08c694c86a16ddd9c81e773045d | 659dc36c9c4ec081d0e825ac58fcb3fc23b10fbe | 33956469915 / success / 619 passed |
| #211 | 659dc36c9c4ec081d0e825ac58fcb3fc23b10fbe | cc15fc76ae7b9ab8687a4745bbbba40dc42b8c87 | 73e6c2859174149849a3f654567012cc7020c885 | 33956861040 / success / 632 passed |
| #212 | 73e6c2859174149849a3f654567012cc7020c885 | f553c51224bab6228fe28e3231ad59f7f91916f5 | c8fb17e1e087a895b936e7e27653a4f584c26be5 | 33957187147 / success / 639 passed |
| #213 | c8fb17e1e087a895b936e7e27653a4f584c26be5 | 0f81e138ad15c8dff3f226da9c55e38430dd6293 | bde9bad7ef725fbca54f5c7a567227e6b9b7dd56 | 33957511182 / success / 639 passed |

Main kernel CI after #210/#211/#212/#213: `33956532569`, `33956943845`, `33957265642`, `33957604920`, all success. Source trials have their own failure conclusions; green kernel CI does not override those.

Exact changed files:

```text
#210
.github/workflows/hithink-stock-dump-trial.yml
pyproject.toml
src/decision_kernel/runtime/hithink_dump_trial.py
tests/test_hithink_dump_trial.py
tests/test_hithink_dump_trial_workflow.py
docs/hithink-stock-dump-trial.md

#211
src/decision_kernel/runtime/hithink_dump_trial.py
tests/test_hithink_dump_cdn.py
docs/hithink-stock-dump-trial.md

#212
src/decision_kernel/runtime/hithink_dump_trial.py
tests/test_hithink_dump_destination_diagnostics.py

#213
src/decision_kernel/runtime/hithink_dump_trial.py
tests/test_hithink_dump_cdn.py
tests/test_hithink_dump_destination_diagnostics.py
```

Only #210 adds a workflow and optional dependencies. #211–#213 do not change workflows or dependencies; existing narrow path filters intentionally execute changed-code compatibility probes. No economic-source probe or Sector producer was triggered by these files.

## What was built and what was corrected

The isolated trial uses Requests 2.34.2 for bounded HTTPS and PyArrow 25.0.1 for Parquet. Pins are optional `.[dump-study]` and CI `.[dev]`, not Kernel base dependencies. Existing calendar, benchmark, paginated all-stock snapshot, safe JSON/request checks and row inspector are reused unchanged. No handwritten Parquet decoder, pandas warehouse or price provider fallback was added.

#210 initially assumed AWS-only signed hosts; the first real response instead named `o.thsi.cn`. #211 used the official Python SDK's example `/fuyao-market-dump/` as a fixed namespace. That too was an implementation assumption, not an API guarantee. #212 recorded only safe URL predicates and showed the example prefix was the sole failed predicate: HTTPS, exact CDN host, signed query and clean path all passed. No actual object path or signing secret was recorded or guessed.

#213 corrected the trust boundary: the fixed authenticated daily-k-10d signing service selects an absolute path on the exact reviewed HTTPS CDN origin (or previously reviewed S3 host pattern). The SDK's `derive_release_tag` already treats path layout as variable. This is an explicit URL-contract change, not a claim that earlier acceptance rules were unchanged. Other origins, userinfo, explicit ports, fragments, missing query, ambiguous CDN paths, expiry, redirects and resource violations remain rejected. No credentials are forwarded to storage; no usable signed URL, full signing response or exception traceback is saved.

The official `DumpDownloader` at commit `765513c2616030803ad80915ed65b205f425a942`, `python/marketdb/providers/dump.py`, blob `9673fa730b8c676a34b4c2ed0f7762d75cef5e27`, exists and was reviewed after the first rejection. Its mutable cache/size hit, HEAD, resume/redirect and error-body behavior differs from this bounded immutable trial; disabling retry alone is insufficient. Do not claim there was no existing wheel. The example-host/path mistakes and extra diagnostic work are ours, not provider failures or evidence of malicious URLs.

## Four retained real trial outcomes

All runs were fresh attempt 1 on main, caused by the specific code merges above. Each signing URL was requested once, with no unchanged-code rerun, retry or re-signing inside a run. The first three stopped before any object or reference GET. These were successive diagnostics/corrections, not four successful downloads.

| Trial/run | Executed implementation | Actual disposition | Artifact |
| --- | --- | --- | --- |
| #1 / 33956532596 | 659dc36c9c4ec081d0e825ac58fcb3fc23b10fbe | signing code 0, CDN rejected by AWS-only gate; no download | 9966543809 |
| #2 / 33956943929 | 73e6c2859174149849a3f654567012cc7020c885 | signing code 0, example-prefix gate rejected; no download | 9966664823 |
| #3 / 33957265676 | c8fb17e1e087a895b936e7e27653a4f584c26be5 | diagnostic proved prefix-only mismatch; no download | 9966762159 |
| #4 / 33957604949 | bde9bad7ef725fbca54f5c7a567227e6b9b7dd56 | real file downloaded, footer read, reference-date qualification rejected | 9966871869 |

All four workflows conclude failure / FAILED_CLOSED. #4 is useful partial acquisition evidence, not a successful qualification run. Each artifact keeps its original result. No state was adopted, no missing price filled and no thresholds changed.

Prior ZIP SHA-256 values, independently checked with report/workflow hashes after download:

```text
#1 bf13d7d8aeb84ab35f189d30567eca640cb4f4c291cbeaba85da88c6c545b165
#2 1a572a5dc89f3cfec4c66b90aa79951d88d8ebf364267afbcb61cabad3bc070c
#3 1ccac0e8ea993270d5afe56a21172b2310dc51b799b4e0e1282553ea32bf2373
```

## Actual file and reference evidence from #4

```text
run = 33957604949 / attempt 1 / event push / main
started_at = 2026-09-05T09:18:17.655593+00:00
download_started_at = 2026-09-05T09:18:18.998882+00:00
download_completed_at = 2026-09-05T09:18:25.520178+00:00
completed_at = 2026-09-05T09:18:28.548751+00:00
status = FAILED_CLOSED
stage = QUALIFIED_REFERENCE
error_type = HithinkRuntimeError
production_qualification = NOT_ESTABLISHED

artifact = hithink-stock-dump-trial-33957604949-1
artifact id = 9966871869
ZIP bytes = 1106743
ZIP SHA256 = d6b5bd578daacbb05d1bac05995ab494d74e9dc70ab9046f0eb08c601fba2b91
expires_at = 2026-12-04T09:18:03Z
report hash = 2512ae0867d2837f008a3e9558bbbc87263c5f7c8d55fa9bc7491013314d6c22
workflow provenance hash = 080c49a6ea94262ad3f19a36fefa5161fb186eca0fea2ae18d4523fb42d9a03f

original file = capture/daily-k-10d.parquet
file bytes = 1077266
file SHA256 = f333ddc55a614cc14872639e4831a60bcdf20590953bf9a1545764adc4ce2d6a
footer metadata row count = 55467
footer row groups = 1
declared uncompressed row-group bytes = 1660841
observed schema = exact 11 expected columns
runtime = Python 3.12.14 / Requests 2.34.2 / PyArrow 25.0.1
```

These are **footer metadata**, not a claim that all 55,467 rows passed economic/schema/price validation. The trial validates references before calling the row inspector, and it stopped before that call (`inspection=null`). A real decoded row stream and full row-by-row reconciliation remain unproven for this file. No local PyArrow reader was available; independent local verification checked file bytes/hashes and JSON, not physical Parquet decoding or a full project test run.

Exactly one signing request, one object GET and four reference JSON requests occurred in #4: calendar, CSI300 snapshot, CSI300 daily history, stock snapshot offset 0/limit 500. The four recorded reference responses, normalized ten sessions and benchmark result are retained with the file: seven inventoried inputs, plus report, summary and workflow identity. There is no full stock-universe/snapshot output or offline-inspection result. The workflow's offline step explicitly reported missing inputs; its exit 0 for that unavailable step did not mask the acquisition failure.

The provider calendar independently yielded these ten completed sessions: August 24–28, August 31, September 1–4. Completed benchmark history closes were 4552.58 on September 3 and 4548.05 on September 4; the snapshot previous/latest prices matched exactly. Local JSON checks independently confirmed that pair and the reported calendar tail. These do not independently qualify every stock row or establish an exchange census.

The first stock page declared total 5,567 and returned 500 rows, but its `data.timestamp=1788599907000` is **2026-09-05 17:18:27 Asia/Shanghai**, while the qualified completed market session is **2026-09-04**. The unchanged `fetch_hithink_all_market_snapshot` checks date equality before processing stock rows and raises on this difference. This identifies the rejection by retained response plus executed code; the safe report itself stores only the error class and generic code. The declared total is a first-page assertion, not a completed 5,567-security coverage proof. No second stock page was requested.

## Review limits and next work

Downloaded ZIP bytes matched GitHub's digest. All seven input file sizes/SHA-256 values, report/provenance canonical hashes, request clocks, exact run/SHA, calendar tail, benchmark price pair and stock-page timestamp were independently checked. This was local hash/JSON reconciliation, not full network replay or full Parquet-row inspection. The original file and reference response must not be rewritten to remove the date disagreement.

Stop blind compatibility reruns. The next narrow task is a separately reviewed **stock-snapshot timestamp/session contract**, using official endpoint semantics and the retained raw response. Do not simply borrow the index rule or treat calendar date absence as holiday proof. Maintain incomplete-session rejection, exact identity/price checks, visible missing/unpriced members and no stale fallback. Offline tests should use these retained shapes before another controlled acquisition. A successful file GET does not establish recurring entitlement, freshness, full reference coverage, corporate-action correctness or production readiness.

After reference qualification is sound, reuse the existing PyArrow inspector to decode and reconcile this vintage; then examine a naturally later overlapping vintage, corrections and corporate-action/coverage rules before multi-day stock breadth. Ten rows per stock alone do not supply 20/60-session breadth. Neither stock dumps nor current membership lists can bridge missing industry-index sessions or prove historical membership.

The independent stock trial has no market cache/state/event access or schedule. Original economic workflows did not run. Current real Sector proof remains #4 / `33939414197` on `5f8f635d191dd8559844d1b74af0dca0cf4c02df`, ending 2026-09-04 with zero prospective events. The next directly completed-session append, real input-audit replay and context HTML/JSON publication remain pending; do not ask for another same-session run just to repeat them. Sector schedule remains absent. Company postures and all Human/Research/Investment authorities remain unchanged.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
