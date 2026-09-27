# B1 saved global-market reading and Markets

2026-09-27. Successor to the source-only delivery stage in `global-market-context-v1.md`; #297 comment5854807338 records this approved slice. The source family, original Relay client, credentials, finite source requests and no-investment-authority contract are unchanged.

## What this slice joins

The existing optional Collector now reads `radar-global-market.yml` captures and publishes them in the original fixed R. `research.global_market` contains a registered `details/markets/global-market.json` / Markdown locator. The bounded report distinguishes each family's latest attempt from its last byte-verified readable capture. Original ZIP bytes are retained as `sources/artifacts/<SHA256>.zip` in the same Git reading commit, not left dependent only on 30-day Actions retention.

Current families remain six selected international indices and eight Shibor tenors. Shibor is annual CNY interbank interest, not US Treasury yields or a global bond curve. US/global sovereign rates, gold/oil, FX and crypto remain B1 follow-ups. No market-open calendar, common trading date, publication clock or economic explanation is invented.

The Markets page adds a compact global-context panel ahead of the existing A-share panels. Values, units, source dates, two actually returned comparison dates, capture time and partial-source gaps are separate. Calendar age is explicitly age, not a judgment that an exchange must have traded. Index interval percentages and interest-rate basis-point changes remain distinct. Technical metadata is folded; raw source text is not executable HTML or a research instruction.

## Existing capabilities reused

Reuse Decision: THIN_ADAPTER. Internally use `global_market_context.replay`, `Collector.archive/retain`, `current_state.unpack_archive`, the shared budget reserve and the existing browser registered fixed-R reader. Keep the original `tushare_relay.py` unchanged. The already-recorded #610 OpenBB index-historical implementation review and #598/#599 human Markets layout review apply; no third-party provider stack is installed or copied.

GitHub's native `run-name: global-market / <family>` is only a family-discovery hint for new runs, including pending/failed runs without artifacts. It is not a source qualification. Existing #610 runs are discovered from their unique exact artifact names, with at most four such metadata lookups. Values are admitted only after full run/repository/code/attempt/family/time and original-byte replay. Unknown family or a bounded query missing a family remains a visible gap, not an inferred zero or a shared latest timestamp.

## Failure and historical retention

Each family is independent. An unavailable, rejected, empty or failed new attempt does not delete the already-published old capture. The UI says when it is displaying an older readable result rather than the latest update. A latest capture containing useful partial rows keeps its own partial status; failed workflow checkpoints are not relabeled successful workflows. Invalid newest bytes do not start a hunt through older green Actions runs.

A prior capture is recovered from the exact previous R and verified against its registered size, SHA-256 and Git blob. Its original ZIP and historical `artifact_at_read` metadata are replayed using the current trusted reader. That historical metadata does not claim the Actions artifact is still unexpired or downloadable. On unchanged source-run metadata, the exact Git-retained capture can continue to be read after Actions expiry without acquiring market data. If prior bytes cannot be recovered, keep the exact prior locator in the report's read gaps; do not fabricate values or silently claim recovery.

The report body is bounded to 256 KiB. Existing overall publication/index/API budgets remain enforced. Family-local failures roll back only that attempted attachment; existing News, A-share, Quick Inbox, Research/Odds and history are not rewritten. If publication itself fails before pointer update, the previous R remains the reader entry; uncertain writes follow the existing reconciliation discipline.

## Operational and delivery boundary

The normal publisher now listens to the existing source workflow's native events and opts into `--include-global-market`. It consumes GitHub saved artifacts only. It does not dispatch a source, query the Relay, execute code inside an artifact, run Quick/Full, calculate Odds, create Watch/holdings, or grant investment authority. The source workflow remains manual-only; this slice adds no natural schedule, key, PAT scope, Worker route, cache/database, provider framework or additional paid subscription.

Code/CI, normal R publication and actual Sites/mobile adoption are separate stages. This slice can use the two #610 retained source captures for real integration verification; do not repeat those source calls just to prove reading. Sites must later adopt `global-markets.mjs` with the small Markets import/call change while preserving its host adapter and existing protections. No Sites deployment is performed by this repository change.

Controlled tests cover raw replay, family isolation, legacy navigation, metadata ambiguity, latest failure with retained historical bytes, Actions expiry, pending/rerun rejection, exact units/dates, local UI errors and navigation races. Local syntax and Node tests are only a partial development check, not the full repository CI or real browser/mobile acceptance. Actual run IDs, artifact checks and fixed-R readback belong in the PR/#297 delivery receipt, not pre-written PASS claims here.
