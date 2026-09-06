# Manual native-feed acceptance — v0

Status: IMPLEMENTED MANUAL WORKFLOW ENTRY / FULL CI MUST BE REPORTED SEPARATELY / NO NATURAL-SOURCE OR LIVE EXECUTION CLAIM.

Offline history registration/restoration is now described in `docs/native-feed-consumer-history-v0.md`. Those commands reuse the original consumer directories; this manual workflow STILL uses the explicitly empty isolated history below until a separately verified remote integration.

This connects the existing source qualification, opt-in batching, source scanner and exact-plan executor in one isolated run of the existing `hithink-stock-dump-trial` workflow. It does not create another RSS feed, a production queue, an automatic consumer, a new Kernel object or another canonical attention lane. Reuse-first: the fixed sibling collector supplies Requests transport; feedparser, original RSS replay, source metadata binding, persistent Sector bundle loading, decoded response protection and all theme calculations remain existing implementations. Official `actions/download-artifact@v8` and `upload-artifact@v7` provide transfer; no custom ZIP downloader or extractor is introduced.

## Explicit manual inputs

From Actions -> hithink-stock-dump-trial -> Run workflow, select **main** and **native-feed-acceptance**. The default stock-dump option is a different operation and must not be used for this task.

- `native-feed-run-id`: exact successful main `economic-release-discovery` run with its native RSS artifact. No latest-run guessing, refetching, baseline initialization or substitution.
- `native-market-run-id`: exact successful main `sector-radar-shadow` state artifact. Required only when the source precheck actually finds qualified pending versions. An empty field cannot silently load bootstrap or stale state.
- `native-batch-size`: 1, 4, 8, 16 or 32. An explicit operational size selected before matching, not an opportunity threshold.
- `native-execute`: false by default. False still permits the two fresh catalog queries needed to scan qualified sources, but not history/snapshot/member requests. True permits only the exact plan produced by that scan.

Each invocation declares `EXPLICIT_EMPTY_HISTORY_FOR_ISOLATED_ACCEPTANCE_NOT_DAILY_CONSUMPTION`. This is a deliberately isolated compatibility study, not resumption of the registered scan/execution history. It never clears a prior store or resets RSS. Repeating this study can rescan the same post-baseline descriptions and, with explicit execution enabled, make another market attempt. Do not describe it as cross-run exactly-once delivery or use repeated studies as independent prospective samples. Existing full receipt registration and dedup interfaces remain available separately; remote consumer-history restoration is not wired here.

## Source first, then market only when needed

1. Require a fresh manual main invocation and decimal run IDs. Keep inputs in environment variables; only validated outputs enter GitHub CLI GET paths.
2. Bind the selected source run and its exact unexpired artifact, repository, commit, branch, first attempt and server digest. The official download action must fail on digest mismatch.
3. Rebuild the original RSS capture and compare its workflow identity to the selected remote run. Inspect all post-baseline source versions using the existing qualification rules.
4. Baseline-only or no-post-baseline-version input produces an explicit no-work result. Unqualified source time/text or simultaneous representations produce a blocked result. Neither path retrieves a market artifact, reads a market credential or makes catalog/price/member calls.
5. Only for qualified pending sources, download the specified Sector state artifact by exact ID and digest. Validate its complete manifest/state/ledger package and bind the stored run/commit to metadata. This is a read-only comparison input, not the producer's restoration path. No implicit bootstrap, cache fallback, day append or missing-session bridge.
6. Acquire two catalogs once, using the existing raw transport and decoded JSON safety check. Current saved-session/weekend checks precede each catalog request and follow receipt. Preserve exact response bytes and clocks.
7. Run one explicit batch through the existing source scanner using an explicitly empty isolated receipt scope. Preserve every deferred version. All source-time constraints and the three-theme limit still apply. No favorable substring selection, automatic batch splitting or next-batch loop.
8. With a plan and explicit execution enabled, immediately invoke the existing exact-plan executor. It reuses the two catalogs and enforces the original 30-minute plan lifetime, request-time checks, pacing, raw response rules and all-market-input validation. There is no hand-editable plan between jobs.
9. Remove market credentials and independently replay the original feed, catalog records, batch selection, source page and optional exact market execution. Only then may a successful-stage page link be shown after real artifact upload. Failed attempts still upload evidence and remain failed.

The study currently sets `industries=[]`: it does not infer or fetch industry-membership probes from article text. With at most three themes this yields two catalog requests plus at most seven detail requests (nine total); the inherited hard ceiling of fifteen is retained, not increased. Calls are paced by the existing 20-second policy, with no retry/fallback or second batch. Daily aggregate budgets across several manually requested studies are not established.

## Files, recovery and status

The artifact is `native-feed-acceptance-<run>-<attempt>`, retained for 90 days. `source/` contains the selected original RSS artifact; `market/` exists only when needed. Remote run/artifact metadata, bindings, explicit request and source qualification remain beside `trial/`. The trial retains original catalog bytes, complete source scan and optional execution bundle.

Open `trial/scan/index.html` for source leads and `trial/execution/index.html` only when the exact market stage actually succeeded. No-work/blocked runs do not invent these pages. Their source originals and `source-qualification.json` explain the result. Summary displays source, capture, replay and upload outcomes separately. A successful upload of a failed attempt is not successful source/market processing; a scan-only successful run is not a successful market execution.

Run/commit/artifact identity and source/body hashes describe what was supplied and rebuilt; they are not signatures or proof of article truth. `source_delivery_acknowledged` and `remote_publication_verified` inside the source/market objects remain false. Actual upload status and URL are separately provided by GitHub; neither proves Human reading or acceptance. The wrapper is not a production recovery authority. Preserve full original artifacts and exact code before expiry; hashes cannot recover missing originals. Existing finite per-file, scan and execution bundle budgets remain; packaging failure cannot qualify partial output.

## Verification and remaining milestones

Tests use actual existing feedparser, RSS baseline/successor/replay, source qualification, deterministic batching, matcher, exact-plan execution and market math with synthetic transport. They cover manual intent, wrong/expired/foreign metadata, no-work and unqualified sources before any market request, scan-only, no-match, successful execution, failed requests, decoded unsafe content, mutated inputs and fabricated success. Workflow assertions enforce credential scope, source-before-market ordering, official transfer settings and successful-upload-only links. Local syntax checks are not full CI or a real cloud run.

The actual saved NBS baseline and unchanged successor do not contain a natural new post-baseline version. Their raw unzoned publication strings have not become qualified. Do not refetch these windows or invent timezone-qualified entries merely to make the new path run. Natural new-source/time qualification, real manual job transfer and optional market acceptance, remote receipt-history registration/restoration, durable archival and daily aggregate budgets remain separate milestones. Ordinary Sector next-trading-session append and joint-reading publication also remain independent.

No workflow schedule or automatic native push trigger. Changes to this adapter, its tests or this workflow do not initiate native collection. No modification of producer market state, cache, candidates, 881/884 rank, thresholds, company judgments, Human Decision/Action, Research/Odds or authority. SHADOW OBSERVATION ONLY; HUMAN ATTENTION / RESEARCH / INVESTMENT AUTHORITY = NONE.

References: `docs/native-feed-batches-and-execution-v1.md`, `docs/native-feed-source-consumer-v0.md`, `docs/native-rss-successor-v0.md`; official action inputs at https://github.com/actions/download-artifact/blob/v8/action.yml and https://github.com/actions/upload-artifact .
