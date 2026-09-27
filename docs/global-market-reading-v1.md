# B1 saved global-market reading and Markets

2026-09-27. Current successor: six-family reading v2 under #297 comments5856024596 and5856288961. The prior v1 delivery (#612 /5854807338) joined only the two Relay families. #614 subsequently delivered four public source codecs and real captures; this change consumes those existing captures without rebuilding or re-running the sources. Original codecs, credentials, finite source requests and no-investment-authority contracts are unchanged.

## What this slice joins

The existing optional Collector reads `radar-global-market.yml` and `radar-global-public.yml` captures and publishes them in one original fixed R. `research.global_market` contains a registered `details/markets/global-market.json` / Markdown locator. The bounded report distinguishes each family's latest attempt from its last byte-verified readable capture. Original ZIP bytes are retained as `sources/artifacts/<SHA256>.zip` in the same Git reading commit, not left dependent only on 30-day Actions retention.

Reading v2 has six independently scoped families: selected international indices, CNY Shibor, US Treasury par yields, ECB per-EUR reference rates, Yahoo gold/WTI/Brent futures daily closes, and Coinbase BTC/ETH-USD daily candles. Their original #610/#614 source contracts apply. Shibor does not replace Treasury; par yields are not bond total returns; ECB is not implicitly rebased to USD; Yahoo `=F` roll identity remains UNKNOWN and produces no interval return; Coinbase is a single venue. This is not complete global-market coverage or synchronized real-time quotes.

The Markets page adds a compact global-context panel ahead of the existing A-share panels. Values, units, source dates, two actually returned comparison dates, capture time and partial-source gaps are separate. Calendar age is explicitly age, not a judgment that an exchange must have traded. Index/FX/crypto interval percentages and interest-rate basis-point changes remain distinct. Technical metadata is folded; raw source text is not executable HTML or a research instruction.

## Existing capabilities reused

Reuse Decision: REUSE existing saved-reading seam with THIN_ADAPTER for the second codec. Use unchanged `global_market_context.replay` and `global_public_context.replay`, `Collector.archive/retain`, `current_state.unpack_archive`, shared budget reserve and browser registered fixed-R reader. Keep the original Relay and public HTTP transport unchanged. #508/5773538785 and the retained #511 candidate/negative-evidence checks apply; reuse the same-day #614 exact OpenBB/yfinance/CCXT source audit and #612/EasyStock stale-state/Markets audit, since this change adds no supplier or new acquisition capability. No third-party framework is installed or copied.

Native `run-name` is only a family-discovery hint, including pending/failed runs without artifacts. Earlier captures are discovered from unique exact artifact names, with at most four such metadata lookups per workflow query. Values are admitted only after full run/repository/code/attempt/family/time and original-byte replay. Relay and public workflow queries are independent; failure of one does not erase the other's existing results. Unknown family or bounded-query absence stays a visible gap, not an inferred zero or a shared latest timestamp.

## Failure and historical retention

Each family is independent. An unavailable, rejected, empty or failed new attempt does not delete the already-published old capture. The UI says when it is displaying an older readable result rather than the latest update. A latest capture containing useful partial rows keeps its own partial status; failed workflow checkpoints are not relabeled successful workflows. Invalid newest bytes do not start a hunt through older green Actions runs.

V2 can recover both exact v1 two-family and v2 six-family prior reports. A prior capture is recovered from the exact previous R and verified against registered size, SHA-256 and Git blob, then its original ZIP and historical `artifact_at_read` metadata are replayed using trusted installed code. Historical metadata does not claim the Actions artifact is still downloadable. On unchanged source-run metadata, the exact Git-retained capture remains readable after Actions expiry without acquiring market data. Failed recovery keeps the prior locator in read gaps; it does not fabricate values. The browser retains v1 reading support as well.

The report body remains bounded to 256 KiB. Existing overall publication/index/API budgets remain enforced. Family-local failures roll back only that attempted attachment; News, A-share, Quick Inbox, Research/Odds and history are not rewritten. If publication fails before pointer update, the previous R remains the entry; uncertain writes follow existing reconciliation discipline.

## Operational and delivery boundary

The normal publisher listens to both existing source workflows and reuses `--include-global-market`. It consumes GitHub saved artifacts only. It does not dispatch a source, query providers, execute code inside an artifact, run Quick/Full, calculate Odds, create Watch/holdings, or grant investment authority. Both source workflows remain manual-only. There is no new schedule, key, PAT scope, Worker route, cache/database, provider framework or paid subscription.

Use the existing #610 indices36308774368/Shibor36309047326 and #614 treasury36317799016/fx36317890212/commodities36317970476/crypto36318059164 captures for integration verification. Do not repeat source calls to prove reading. Source-specific failures and actual dates survive the join. Original source summaries are preserved under their own scopes; a v1 summary's historical narrower coverage statement is not the v2 aggregate's coverage claim.

Code/CI, normal R publication and actual Sites/mobile adoption remain separate. Sites later adopts this module together with the still-unadopted #612 Markets import/call, preserving the actual host adapter and protections. No Site deployment or extra News/Inbox mutation is performed by this repository change.

Controlled tests cover six-family replay, v1 recovery, independent query failure, partial/failed captures, retained Git bytes after Actions expiry, wrong workflow/family/hash, percent/bp/quote direction, prohibited futures returns, local UI errors and navigation races. Local syntax/Node checks do not stand in for full CI or browser/mobile acceptance. Actual run IDs, hashes and fixed-R readback belong in the PR/#297 delivery receipt, not pre-written PASS claims here.
