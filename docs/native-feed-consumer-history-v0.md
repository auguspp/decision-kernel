# Native feed consumer history snapshots — v0

Status: IMPLEMENTED OFFLINE REGISTRATION / PINNED RESTORATION / FULL CI REPORTED SEPARATELY. NOT YET A REMOTE WORKFLOW RESTORE OR NATURAL-SOURCE PROOF.

This fills the persistence gap between the existing full source-scan and exact-plan-execution bundles. It is a Harness file-manifest wrapper, not another source registry, queue, signal ledger, market formula or Kernel object. It reuses `radar_feed_consumer.verify_scan`, `theme_plan_execution.verify_execution`, native RSS original-byte replay, canonical hashes and the existing safe bounded file reader. Standard-library copying and atomic staging replace manual directory assembly; no new dependency, parser, crawler, storage service or scheduler is introduced.

## What is retained

A snapshot contains `history.json`, `feed-capture/`, `scans/<receipt-hash>/`, `executions/<execution-hash>/` and, on a successor, the exact previous manifest as `parent.json`. Every scan/execution keeps its original complete bundle, original first clocks and original receipt bytes. The source anchor refers to the complete supplied source registry, immutable version identities and first observations. Additional appearances of the same version may accumulate, but old versions, old appearances and first clocks cannot disappear or change. Source policy, provenance, initialization and chronological compatibility must agree.

The manifest is an inventory, not a second source of completion decisions. Scans are rebuilt from original RSS and market/catalog inputs; executions are rebuilt from exact plans and raw market responses by the original implementations. Execution completion applies only to its exact registered scan bundle and plan. A scan-only record keeps the plan outstanding. A replayable failed execution can be registered and remains failed; a later successful attempt is added, never overwrites it. A malformed/unreplayable attempt or blocked scan cannot become a registered completion; its original attempt artifact must remain separately retained. Repeated copies of an identical complete object deduplicate, but two different executions remain two attempts, not independent forecasts.

A successor copies all existing objects and may add new ones. It must reference a verified, explicitly pinned predecessor; removing or rewriting an object listed in that predecessor fails. Only the previous manifest is carried forward, not a recursively nested predecessor artifact. This flattens the history layout but does not content-deduplicate common RSS bytes inside different original scan bundles.

## Explicit operations

First register an explicitly scoped initial consumer history. `--initialize` initializes ONLY this consumer-history branch. It does not run native RSS initialization, erase another receipt store or forward old baseline entries. All commands require timezone-aware cutoffs and new disjoint output directories.

```sh
python -m decision_kernel.runtime.radar_feed_history register \
  --source /work/source/capture --initialize \
  --scan /work/completed-scan --execution /work/complete-replayable-attempt \
  --as-of '<registration timestamp>' --output /work/history-1
```

`--scan` and `--execution` are repeatable and optional. A no-work history can explicitly start empty while retaining the source anchor and original RSS. Unqualified publication strings are preserved as gaps; storage never gives them a timezone or upgrades them to Evidence.

Restore against the current independently supplied source capture and the exact known history hash, not a newest-file guess:

```sh
python -m decision_kernel.runtime.radar_feed_history restore \
  --history /work/history-1 --expected-hash '<history_hash>' \
  --source /work/next-source/capture --as-of '<current cutoff>' \
  --output /work/restored-history
```

This recreates the ORIGINAL consumer's `scans/` and `executions/` directories plus `restoration.json`. Pass those directories directly as `--receipts-dir` and `--executions-dir` to `radar_feed_consumer scan`, together with its explicit current state/catalog/cutoff and `--batch-size`. The existing consumer alone decides scope applicability, prior scans and unfinished market stages. An old plan remains historical/unexecuted until its exact execution is proven; restoration does not execute it, refresh its clock or permit stale prices.

After a later operation, explicitly register its new complete objects:

```sh
python -m decision_kernel.runtime.radar_feed_history register \
  --history /work/history-1 --expected-hash '<history_hash>' \
  --source /work/next-source/capture --scan /work/next-completed-scan \
  --as-of '<later registration timestamp>' --output /work/history-2

python -m decision_kernel.runtime.radar_feed_history verify \
  --history /work/history-2 --expected-hash '<new history_hash>' \
  --as-of '<verification cutoff>'
```

Unknown/missing predecessors, equal or reversed registration time, a history formed after the requested cutoff, changed byte inventories, incompatible source versions or loose success JSON fail closed. No empty-store fallback, implicit reset, overwrite, automatic trimming or retry is available. Temporary writes are cleaned without deleting originals.

## Capacity, provenance and precise proof boundary

The existing per-file limit and 32 MiB TOTAL consumer bundle limit remain. At most 64 distinct scan bundles and 64 execution bundles are retained; at most 8192 file entries accommodate their existing 32/64-file object limits. These ceilings are simultaneous, not a promise that 64 real captures will fit. Repeated large original RSS windows can exhaust bytes much earlier. A capacity failure requires an explicit archival/storage decision; this version never silently prunes and is not an indefinitely growing data service.

A snapshot proves reconstruction of its listed objects and non-loss relative to its supplied parent manifest. It does not authenticate a missing predecessor, prove that the operator supplied all historical runs, resolve forks, find the global latest branch, or certify every intermediate source capture. Source compatibility requires preservation of all prior version identities/first clocks/appearances; it is not proof of an unseen complete publisher history. The current history hash must be bound independently to a trusted artifact/run when adding remote restoration. Merely rehashing an invented parent manifest is not external authentication.

Registration time is a caller-supplied aware clock, not a signed trusted timestamp or Human exposure event. `source_delivery_acknowledged=false` and `remote_publication_verified=false` remain. The source registry's `pending_versions` is unchanged and is not a number of unfinished market requests. A successful historical execution still does not prove Human reading, article acceptance, thesis validity or investment quality.

No workflow is changed by this slice. The manual `native-feed-acceptance` entry from #256 STILL uses its explicit isolated empty history. These snapshot commands do not silently turn it into a successor service. Official artifact transfer and exact run/digest binding can be connected separately only after testing; expired or missing remote input must not recreate an empty branch. Current 90-day workflow retention is not extended by this module. Preserve the complete snapshot and exact code externally before expiry; a hash cannot recover missing bytes.

## Acceptance

Tests use the actual existing feedparser, RSS baseline/successor replay, real batch scanner and exact market calculator with synthetic transport and forbidden network. They cover 33 -> 32 -> save/restore -> 1 -> save/restore -> quiet; exact successful-stage recognition; failed then successful attempts without overwriting; duplicate copies; deleted original working directories; no-odds/no-market writes; source version/first-clock compatibility; explicit initial-vs-successor choice; pinned hashes; missing/corrupt stores; parent object removal; capacity, atomic interruption and CLI. No natural NBS arrival, real new market capture or GitHub cloud restoration is claimed by these tests.

No change to native source publication-time qualification, baseline registry, 881/884 rankings, false-to-true transitions, production market/cache/candidate state, research routing, canonical Human wakes, company judgments, Human Decision/Action, thresholds, schedule or authority. SHADOW OBSERVATION ONLY. HUMAN ATTENTION / RESEARCH / INVESTMENT AUTHORITY = NONE.

See `docs/native-feed-source-consumer-v0.md`, `docs/native-feed-batches-and-execution-v1.md`, and `docs/native-feed-manual-acceptance-v0.md`.
