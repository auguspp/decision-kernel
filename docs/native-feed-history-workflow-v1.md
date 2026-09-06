# Native feed: pinned workflow history — v1

Status: OPT-IN WORKFLOW CONNECTION IMPLEMENTED / FULL CI REPORTED IN PR / REAL CLOUD CONTINUATION NOT YET PROVEN.

This connects the existing `radar_feed_history` snapshots to the existing `native-feed-acceptance` manual mode in `hithink-stock-dump-trial.yml`. It does not introduce another workflow, parser, queue, database, signal state, or completion rule. The original source scanner and exact-execution replayers decide what was scanned or executed. Kernel, sources, market mathematics and authority do not change.

## Three explicit history modes

Select `main`, `trial-purpose=native-feed-acceptance`. Keep the existing exact source run, optional-if-needed market run, batch size and independent execution switch. `native-execute` remains false by default.

| native-history-mode | Meaning | Additional required input |
|---|---|---|
| `isolated` (default) | Original v0 empty-history study; no history registered | None; prior run/hash must be empty |
| `initialize` | Explicit first consumer-history branch from the selected source capture; NOT RSS initialization | None; prior run/hash must be empty |
| `continue` | Consume the exact named prior history, then preserve it in a successor snapshot | `native-history-run-id` and exact 64-character `native-history-hash` |

Initialization does not claim that no other branch exists. Continuation never searches for a latest run, recovers from cache/bootstrap, silently creates an empty history, or overwrites its predecessor. Old isolated acceptance artifacts have no history envelope and cannot be supplied as a predecessor. Repeating initialization creates separate explicitly declared branches, not independent forecasts or a migration of existing progress.

## Processing order and scope

The source artifact is bound by exact run/commit/repository/attempt and official artifact digest, downloaded, and rebuilt first. Source-time or text gaps still block the run before market access. Baseline-only or no-post-baseline sources make no market request. They may establish or extend an explicitly selected consumer-history branch without forwarding old source entries.

For continuation, the exact history artifact is downloaded using `actions/download-artifact@v8`, exact artifact ID and `digest-mismatch: error`. Its `publication.json` must identify that remote manual run and the pinned `history/history.json`. Every original scan/execution and source anchor is rebuilt; incompatible source chronology/versions, changed bytes, wrong identity or future registration stop the run before market credentials or state access.

For qualified pending sources, two catalogs are obtained as before. `restore_history` supplies the original consumer's `scans/` and `executions/` directories before matching. One FIFO batch is scanned. Already scanned source keys are suppressed only in the original matching scope. A changed catalog/method scope can require a new scan. Even when all records are already scanned, checking a fresh scope can require two catalog calls; this is not zero-network daily operation.

The explicit execution switch permits only a new exact plan from this scan. Old unfinished/failed plans remain visible but are NOT automatically retried, refreshed or treated as current. A quiet source scan can coexist with outstanding old plans. Restoring an exact successful execution closes only that execution stage, not source truth or Human delivery. The original scan receipt remains immutable.

Source/market/scan/replay/upload failures remain distinct. Credential-free replay precedes registration. A blocked scan, malformed execution or unreconstructable attempt does not create a successor history; its separate failure artifact is still retained. A fully reconstructable failed market attempt CAN be included together with its completed source scan. The workflow remains failed for that market stage; saving history does not turn it green.

## History publication and restoration

A separate artifact named `native-feed-history-<run>-<attempt>` contains:

```text
history/             existing complete snapshot and original object bundles
publication.json     workflow/run/commit, pinned history/parent, registration and attempt status
```

The larger `native-feed-acceptance-<run>-<attempt>` retains the input artifacts, remote metadata, prechecks, current trial and history envelope for audit. History upload runs only after successful history registration and verification, including on an otherwise failed market run. Summary shows history registration, actual history upload and market status separately. It displays the run/hash for continuation only after the history artifact really uploaded successfully.

A preceding run may have overall conclusion `success` OR `failure`, but must be completed, manual, main, attempt 1, and possess the exact unexpired history artifact with matching digest, publication identity, pinned history hash and rebuilt originals. A green run alone is insufficient; a red run alone does not authorize restoration. Cancelled/timed-out runs are not accepted. Source RSS runs and Sector market-state runs still require success; that rule was not relaxed.

`publication.json` is prepared before upload and is not an upload acknowledgment, signature, proof of Human reading or full source acceptance. Its `remote_publication_verified` and `source_delivery_acknowledged` flags remain false. Remote artifact metadata and the official transfer separately establish which published bytes were retrieved. Content hashes do not define truth or globally latest progress.

## Capacity, expiry and remaining proof

The inherited 32 MiB history-total budget, per-file limits and 64 objects per kind remain. No content-dedup storage service or automatic pruning is added; large real RSS originals can exhaust capacity early. Registration failure preserves prior history and does not publish a partial successor. Artifacts retain 90 days. Preserve exact originals and code or use a separately qualified archival/recovery process before expiry; an expired predecessor does not authorize reinitialization.

No schedule, next-batch loop, aggregate daily budget, exactly-once transport, cross-writer branch convergence or canonical latest pointer is introduced. The existing concurrency group is not proof that a caller selected the newest branch. Selection of an older pinned predecessor is an explicit branch, not automatic rollback detection.

Tests run actual RSS/source/history/execution modules with synthetic transport and forbidden network, including 33 -> 32 + 1 -> quiet through this adapter, exact successful/unfinished plans, metadata/time/byte rejection, no-work history publication and simulated public-branch success/failure registration. Fake public metadata in tests is not a real capture. Real cloud history upload/restore, natural new qualified source arrival, NBS publication timezone qualification and ordinary Sector next-session append remain separate acceptance milestones. No old RSS baseline or company excerpt is repackaged as new evidence.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION / RESEARCH / INVESTMENT AUTHORITY = NONE.
