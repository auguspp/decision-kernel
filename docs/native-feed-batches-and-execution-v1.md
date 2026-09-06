# Native feed batches and exact market-stage confirmation — v1

Status: IMPLEMENTED OPT-IN BATCHING AND EXACT PLAN EXECUTION / SEE EXACT PR CI FOR SYNTHETIC ACCEPTANCE / NO NEW LIVE SOURCE OR MARKET PROOF.

This extends the v0 source-scan consumer rather than replacing its source registry, parser, matcher or market math. A complete source-scan receipt remains a source-scan receipt. A separate retained execution can demonstrate that its exact market plan produced a reproducible result; it cannot demonstrate remote publication, Human delivery, article acceptance, Research or an investment decision.

## Complete inventory, bounded work

The default `radar_feed_intake.source_rows(registry, delta)` and default consumer scan retain their old complete-export contract. Their original output shape, hashes, 32-source refusal and original-byte replay remain unchanged. An explicitly selected `--batch-size 1..32` opts into the new per-operation contract. The shared per-source qualification is reused, not copied into a second parser.

Every post-baseline version is first inspected for the same original time, identity, description and simultaneous-representation constraints. One semantic gap, including an unzoned publication outside the selected prefix, still blocks the batch. Batching does not convert the actual unqualified NBS strings into Evidence or ignore an inconvenient source. Baseline entries never enter a batch.

After exact historical scan receipts are verified, unscanned rows are ordered by first actual receipt time, first recorded time and version hash as a deterministic tie-breaker. A contiguous prefix is selected before any theme matching. The prefix respects the declared count (at most 32), 131072 retained characters and existing 64 MiB label-count × text-length work bound. A large head row is not skipped to take smaller/later stories. No text is trimmed. A batch matching more than three themes still blocks in the unchanged matcher; it is not automatically retried as several smaller successful batches. Batch size is an operational choice, never a score, rank or post-outcome selection rule.

The retained manifest lists every post-baseline row key, previously scanned keys, the complete pending order, selected keys and all deferred keys. The HTML displays this manifest. A 33-source synthetic example can scan 32, explicitly register that complete receipt, then scan one. The source registry retains all 33 versions and the old whole-export status can still be blocked. `pending_versions` is not reduced by source scans; it is not a count of market work completed. This explicit batch contract is different from silently taking the first 32 and declaring the entire input processed.

Existing v0 receipts remain verifiable and reusable. Changed source versions or matcher/catalog/industry-probe scope do not inherit an unrelated completion. Original source clocks and all producer market state remain unchanged. Standalone receipts prove their listed selected scans, not completeness of caller-supplied historical receipts. The live service still has no automatic registration, cross-writer concurrency control, cloud latest pointer or indefinitely retained history.

## Operator sequence

Use the existing optional `feeds` environment and exact current market/catalog inputs. Add `--batch-size 32` to the existing consumer scan command described in `native-feed-source-consumer-v0.md`. Inspect the full deferred inventory and any blockers. Verify the resulting successful scan and explicitly register its whole directory; a blocked or quiet attempt has no completion receipt.

Only a scan with a non-null acquisition plan may be passed to the new workflow adapter:

```sh
python .github/scripts/capture-native-theme-plan.py capture \
  --scan /work/exact-completed-source-scan --output /work/new-market-attempt

# Separate step with HITHINK_FINANCE_API_KEY absent:
python .github/scripts/capture-native-theme-plan.py verify \
  --output /work/new-market-attempt
```

The capture command requires the canonical fresh main `hithink-stock-dump-trial` workflow identity and its existing configured market credential. These are interface examples, not a new workflow option or proof of a deployed job. This change adds no workflow wiring, dispatch or schedule. The fixed version-controlled adapter loads only its existing sibling collector's `workflow_identity` and `request_raw`; users cannot choose an import path. Requests, authentication, redirects, timeouts, raw-body bounds and HTTP failure handling remain in that existing transport. No second HTTP client implementation is introduced.

The source scan is rebuilt, copied and reverified before the first detail request. The exact saved plan is written before requests. Previously captured concept/industry catalogs are reused, not fetched again or replaced. Only the plan's ordered detail requests execute, once each, with 20-second pacing and no retry/fallback. The existing maximum of 15 including two catalog inputs remains; there are at most 13 new detail requests. The saved-day/adjacent-weekend rule and the existing 30-minute plan-to-capture cutoff are separate constraints. A weekend does not extend a Friday plan's lifetime. A later planner must create a new qualified scan/plan, not silently rebind the old one or bridge missing market sessions.

`execution.json`, copied `source-scan/`, `plan.json`, exact raw `responses/`, normalized input, original theme result and HTML are retained. The execution wrapper keeps the 32 MiB total bound, allowing at most 64 files for the nested scan plus market inputs; it does not enlarge the original 32-file scan-bundle limit. Interrupted preparation may leave an incomplete, unbindable attempt that cannot be registered. Failed HTTP or computation keeps the available attempt evidence and no successful market page. Credential echoes are refused and exception text is not persisted.

### Response and per-request boundaries

The exact-plan executor reuses `sector_radar_audit._check_safe_json` on decoded JSON before writing any raw response. Literal byte searching alone cannot detect a JSON-escaped credential. Nested credential values, sensitive key spellings after decoding and excessive JSON depth are refused with the existing guard; the original 8 MiB response bound is also checked before JSON decoding. Offline reconstruction uses the same key/depth guard without receiving a market credential. A rejected body is not retained or replaced by a sanitized success response; the attempt retains only safe failure metadata and stops before the next request. This is not a claim to detect all conceivable encodings of secrets.

Check both the original saved-day rule and unchanged 30-minute plan lifetime at preflight, after every pacing interval immediately before transport, and again at response receipt before storage. The final probe still owns the original computation and its capture-cutoff validation. Starting inside either window does not authorize crossing it while waiting. If a response arrives after a limit, retain failed-attempt metadata and issue no further requests. Preserve an invalid received-time claim instead of repairing it: when clocks reverse, the ordinary execution verifier rejects that receipt as temporally invalid rather than certifying a clean failure. An exactly 30-minute data cutoff remains allowed; report generation after that cutoff is not an extra market observation.

Regression-first record: PR #255's tests-only head `28e9275cf9d8c92ff102b45d61161502576ca8be` against merged #254 produced **13 failed, 1376 passed** in CI `34016516585` / job `101441119351`. This is a test-result count, not thirteen independent defects. Negative cases exposed missing decoded-response checks and late time rejection. All use fake credentials and synthetic transport, not real disclosure or live stale requests. The oversized-body case later received a compact test ID, without changing its rejection condition.

During correction, one new positive fixture incorrectly reused a Friday plan at Sunday midnight. CI `34016927583` and diagnostic run `34017261470` retained **1 failed, 1388 passed**: the unchanged final probe correctly refused that over-30-minute plan. The fixture now creates a genuinely later synthetic scan/plan while retaining original source clocks; no production clock is rewritten. Separate tests now require early refusal of same-day over-age plans, deadline crossings during wait/receipt, and success at the exact 30-minute cutoff. Temporary diagnostic wrappers were removed. Final fixed CI is recorded in the PR separately; no prior failed run is reclassified as successful.

## Confirmation is stage-specific

`verify_execution` reconstructs the embedded source scan, exact plan, request order/clocks and the original market probe from raw response bytes. Missing latest bars, incomplete requests, failed status, wrong plan, changed bytes or rehashed derived pages cannot confirm success. A public transport label is an execution claim bound to its recorded context, not a signature or independent GitHub upload proof. Synthetic and public source/execution provenance cannot be mixed.

An explicit `--executions-dir` on a later consumer scan accepts only complete retained execution directories. It verifies each under the requested cutoff and exact scan-receipt plus plan hash. Copies deduplicate. A successful reconstructed execution removes only that plan from the current projection of unfinished market stages. Failed attempts remain visible and do not remove it. A later execution cannot suppress earlier pending work. Missing stores, loose success JSON and executions for a different scan of the same theme fail closed.

No original scan receipt is edited: its historical `PLAN_NOT_EXECUTED` remains true of the earlier stage. The current projection separately shows `market_stage_succeeded`, while `source_delivery_acknowledged=false` and `remote_publication_verified=false` remain. Neither success nor no-literal-match means the company benefits, the thesis is true, Human saw it, or a signal/Research task was created.

## Verification and remaining boundaries

Tests use the existing real feedparser, synthetic native capture/succession, original-byte replay, exact state/catalog fixtures, actual source matcher and actual theme-market calculation. They exercise 33 -> 32 + 1 -> quiet, text-budget deferral, full-scope bad-time refusal, legacy receipts, theme-budget refusal, exact seven-detail-request sample, failures, wrong/future execution, byte tampering, rehashed false pages, secret echo and CLI. Synthetic HTTP is not a real NBS arrival or a real HiThink acquisition. Report full CI results separately; local syntax checks are not a full repository run.

Actual NBS source-time qualification and natural new-source arrival remain unresolved. This implementation deliberately makes no live calls and does not refetch the 1000 unchanged baseline entries. Remote artifact publication/restore for these new scan/execution bundles, receipt registration, aggregate daily request limits and durable archival remain separate gates. The existing 4096-version/6 MiB registry and 64-receipt directory limits remain finite; do not silently prune, reset or infer infinite operation.

No changes to Kernel schema, company judgments, 881/884 rankings, producer/cache/candidate ledger, thresholds, Research routes, canonical attention lanes, Human Decision/Action or authority. SHADOW OBSERVATION ONLY. Human / Research / Investment / signal-transition authority = NONE.
