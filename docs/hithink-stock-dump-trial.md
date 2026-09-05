# Real stock-dump compatibility trial

Status: REAL RECENT DUMP RETAINED / PYARROW FOOTER READ / STOCK REFERENCE REJECTED / NOT A STOCK PANEL.

## Why this is the next Radar slice

The existing Radar can inspect current constituent breadth, but multi-day participation needs qualified individual-stock paths. The previous dump inspector was tested only on Python row fixtures. This slice composes that inspector with a real, isolated recent-ten-session download and physical Parquet decoding. It does not add another signal, price fallback, crawler or state machine.

Reuse: Requests 2.34.2 handles HTTPS streaming and connection cleanup; Apache PyArrow 25.0.1 handles Parquet decoding. Pins are in optional `.[dump-study]` and CI `.[dev]`, not base Kernel dependencies. No pandas, browser, alternate market provider or hand-written Parquet decoder is added. Reuse the existing calendar/index/all-stock qualifiers, safe-JSON/request validation and row inspector; their production behavior is unchanged.

Reviewed primary contracts:

- https://github.com/HiThink-Tech/Financial-API/blob/main/skills/hithink-finance/references/api/endpoints-market-dumps.md (inspected blob `07e93d98ec02e33e6db6c1661c1d280a38a5fcb6`)
- https://github.com/HiThink-Tech/Financial-API/blob/765513c2616030803ad80915ed65b205f425a942/python/marketdb/providers/dump.py (inspected after the first trial; blob `9673fa730b8c676a34b4c2ed0f7762d75cef5e27`)
- https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetFile.html
- https://arrow.apache.org/release/
- https://requests.readthedocs.io/en/latest/user/advanced/

The official `DumpDownloader` is a real existing wheel, not claimed absent. Its mutable cache, size-only cache hit, HEAD probe, redirect/resume behavior, optional automatic re-signing and exception-body diagnostics target a different use case. Retries can be disabled, but that alone does not meet this bounded immutable trial's limits or secret-safe evidence contract. This slice reuses Requests/PyArrow and project qualifiers rather than importing and overriding most of that downloader or adopting its full database. Broader data ingestion should assess the upstream package again before expanding this trial into a warehouse.

## Exact acquisition and safety boundary

One request to the official `daily-k-10d/download-url` signing endpoint, then at most one object GET using its unexpired HTTPS S3-compatible URL. Allowed origins are the reviewed S3 host pattern or exactly `o.thsi.cn`, with no encoded/dot-segment/backslash ambiguity for the CDN path. The fixed authenticated signing service selects the object path; the SDK's example `/fuyao-market-dump/` is not a fixed API namespace. The initial example-prefix assumption was corrected explicitly in PR #213 after safe diagnostics, not silently loosened to admit another provider. The API key is sent only to the fixed `fuyao.aicubes.cn` API origin. No key, signing response, usable presigned URL, query signature, authorization header or exception traceback is archived/logged. Only safe provider code, expiry, hostname and bounded structural-predicate diagnostics are retained. Unsupported origins still fail; caller-provided download URLs are not accepted by the trial CLI.

Requests has no configured retry adapter; every URL is attempted once, with redirects disabled and environment credentials/proxies disabled. Signing expiration does not cause re-signing. Separate sessions do not carry cookies or provider authorization to the object host. No object-store upload occurs.

Download bounds: 256 MiB file, 180-second streamed-download clock plus connect/read timeouts; partial downloads are removed. Parquet footer metadata is checked for exact columns, at most one million rows and at most 512 MiB declared uncompressed row-group bytes before existing row iteration. These are operations protections, not signal thresholds or a guarantee against every hostile compressed file; the maintained decoder runs on a disposable time-limited runner.

Reference bounds: at most 32 JSON requests and 32 MiB retained JSON, 4 MiB per response. The reference path reuses the exact normalized calendar, qualified CSI300 latest/previous benchmark prices, and complete deterministic paginated stock-snapshot contract. The ten expected sessions are established by the calendar, never by selecting whatever dates happen to exist in the dump. The reference universe is the provider's current returned stock set, not an independently proven exchange-wide census.

Important: the existing all-stock snapshot qualifier still requires its provider date to equal the completed session. A weekend data-ready timestamp can therefore reject this trial at the reference phase, and this actually occurred in run `33957604949`. This study does NOT silently change that contract or borrow the more permissive index rule. Retain the raw reference JSON and downloaded file; diagnose independently before a separate qualified change. Missing/zero/revised/corporate-action discrepancies must also remain visible rather than receive a tolerance or backfill.

## Output and inspection

The new `stock-dump-trial/capture` directory can retain the original Parquet, numbered decoded reference JSON responses, exact request clocks, normalized sessions/universe/snapshot, benchmark evidence and a hashed report. A failed reference still leaves an explicitly failed report and any completed dump, not a claimed fully inspected file. `metadata_row_count` is a footer claim, not a row-level proof until row iteration succeeds.

The report includes input-file hashes, implementation hashes and actual reader versions. Its inventory covers inputs; `report.json` hashes its own payload and `summary.md` is a reading projection, not an additional source of truth. Workflow identity and optional independent row re-inspection are outside this input inventory. Public cloud/HTTP assertions and local hashes do not independently authenticate all market values.

When all normalized reference inputs exist, the existing offline inspector can reproduce the field comparison:

```bash
python -m pip install -e '.[dump-study]'
python -m decision_kernel.runtime.hithink_dump_inspection \
  --parquet /capture/daily-k-10d.parquet --sessions /capture/sessions.json \
  --universe /capture/universe.json --snapshot /capture/snapshot.json \
  --output /new/offline-inspection.json
```

This re-inspects the file against frozen references without network. It is not a replay of signing/HTTP or a newly acquired independent market source. Compare exact implementation, input hashes and the `inspection` result. Old standalone-inspector claims remain unchanged: a local comparison cannot itself prove account entitlement; this separate trial's actual successful download is the evidence for that operation, not a guarantee of ongoing service rights/health.

## Workflow and completion discipline

`hithink-stock-dump-trial.yml` is maintained and independent: manual fresh main dispatch, or narrowly path-filtered main pushes changing this trial module/workflow. No pull-request execution with secrets, no schedule, no self-modification, no `continue-on-error`, no market cache/state access or canonical Inbox. Adding it intentionally creates one bounded post-merge trial; documentation-only changes do not trigger it. The HiThink secret exists only in the acquisition step. Artifacts last 90 days, not indefinitely.

A transport/schema/reference failure returns nonzero, retains safe evidence and never creates a fallback file or adopts a stock panel. Field mismatches and partial coverage also remain nonzero. A `CHECKED_FIELDS_MATCH` result means only this downloaded vintage matched the checked same-provider fields. `production_qualification = NOT_ESTABLISHED` is unconditional.

Two overlapping vintages, revision policy, delisting/new-listing/suspension coverage, corporate-action semantics and actual publication/PIT limitations must be examined before multi-day stock breadth. Stock dumps do not provide historical sector membership and cannot replace or repair missing 881/884 index sessions. No signal, ranking, Research route, market-state/event write or company posture changes here.

## Retained live results, not a green qualification claim

Run `33956532596` on `659dc36c9c4ec081d0e825ac58fcb3fc23b10fbe` reached the real signing endpoint, returned provider code 0 and offered `o.thsi.cn`. The initial AWS-only destination check rejected it before any object or reference GET. The workflow remains failure, `stage=SIGNING`, `download_completed=false`, `production_qualification=NOT_ESTABLISHED`. Artifact `9966543809` retains the safe report and workflow identity, not the usable URL. ZIP SHA256 `bf13d7d8aeb84ab35f189d30567eca640cb4f4c291cbeaba85da88c6c545b165`; report hash `ffae7f95f174c682d29f68c7043c0caec834fa03ce07469fdff54c99217fd73e`. Independent local hashing matched both report and workflow hashes.

After the initial CDN allowance, `33956943929` still rejected at signing. The diagnostic-only run `33957265676` established that only the assumed example directory differed. PR #213 therefore adopted issuer-selected paths on the exact trusted origin instead of guessing another private path. All three original failures remain. Their extra work resulted from our incorrect fixed-host/path assumptions, not evidence of provider market-data failure.

Run `33957604949` on `bde9bad7ef725fbca54f5c7a567227e6b9b7dd56` finally retained a 1,077,266-byte Parquet file and successfully read its 11-column footer with PyArrow. Footer row count is 55,467; full row inspection did not run. Calendar and exact benchmark history/snapshot checks qualified September 4, but stock page 0 carried a September 5 timestamp and the unchanged stock adapter rejected it before further pagination. The overall run remains FAILED_CLOSED at QUALIFIED_REFERENCE, with `inspection=null`. No full stock reference universe, successful offline row comparison or stock panel was created.

Exact file/artifact hashes, four-run lineage, CI, request clocks and verification limits are in `docs/handoffs/2026-09-05-stock-dump-trial-next.md`. Next work is separate stock-snapshot timestamp qualification from retained original evidence; do not retimestamp the response, disable the existing check or keep retrying until green. All results remain distinct from prospective Sector state updates.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
