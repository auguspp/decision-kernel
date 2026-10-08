# B1 saved global-market reading and Markets

## 2026-10-08 successor: morning reference-date continuity

Scope and authority remain in [#297/6050939177](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-6050939177) and the linked PR receipts. This is a source-specific timing repair, not full B1/morning acceptance. Reading v2 still joins the same six families; **public capture v2** below is a separate version from that reading format.

| Existing public family | Daily capture opportunity (UTC+08) | Maximum requested source date at actual capture start |
| --- | --- | --- |
| Treasury par yields | 07:07 (23:07 UTC) | Local New York date after 18:00, otherwise the preceding local date |
| ECB reference rates | 07:27 (23:27 UTC) | Local Berlin date after 17:00, otherwise the preceding local date |
| Yahoo futures daily values | 09:37, unchanged | Previous UTC date; finality and roll identity still unestablished |
| Coinbase daily candles | 09:57, unchanged | Previous UTC date; never use an unfinished UTC daily bucket |

Treasury says its curve is usually available by 18:00 Eastern, with possible delays. ECB says around 16:00 CET; **17:00 Berlin is the project's conservative request gate, not an observed publication time**. `ZoneInfo` applies the actual source-zone daylight-saving offset. A weekend/holiday or delayed release may leave only an older returned date; the date ceiling does not fabricate a trading day or fill missing values. The latest row and every original null keep their own identity. An explicit requested date still has the original 31-day lower bound.

`global-public-context-v2` records `date_policy` against the actual `started_at`. The CLI delegates default selection to that same capture clock, preventing a separate midnight race. Replay recomputes and checks the policy before reading rows; changing a hash alone cannot alter its zone, gate or ceiling. **v1 archives keep the original UTC-date restriction, v1 report version and original JSON/Markdown bytes.** They are not upgraded in place or requalified using today's clock. The original reader continues to consume both versions via full source replay.

Only the two reference-family opportunities move, with one existing daily call sequence per family. The completed-day family times, fixed destinations, transport/refusal stops, request/byte limits and create-only checkpoints remain. The original publisher already follows these sources and retains its 07:50/19:10 opportunities; no extra scheduler, retry, fallback source or source dispatch is added. GitHub scheduling can be delayed: a planned slot, a completed capture, a published fixed R and real morning consumption are separate observations.

The **08:00 morning task, its existing H4 gate, notifications and Library permissions do not change**. A morning consumer must report actual source dates and the original coverage/availability gaps, not infer a successful overnight refresh from a new read-model commit. Quick's authorized handoff and Brief's create-only handoff remain noncanonical alternatives to their original GitHub path; this change does not retry a denied canonical write, grant morning write access or make those alternatives canonical. Hosted execution and interactive-session capability remain distinct.

Reuse: original capture/replay, `global_market_reading`, HTTP safeguards and standard-library `ZoneInfo`. The inspected `pandas_market_calendars.market_calendar` time-zone/schedule functions model exchange sessions, not official reference publication; no calendar engine, dependency or framework is installed. Backout uses an ordinary PR to restore the two original cron slots and the v1 writer while retaining the v2 historical reader, its original bytes and applicable tests; deleting v2 replay support would break already saved captures.

Primary contracts: [Treasury publication timing](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology), [ECB reference-rate timing and purpose](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html), [Coinbase candle buckets](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles). Formal CI, merge, publication, fixed-R recovery and first natural timely use are recorded separately in #297/PR, not pre-signed by this document.

## Retained 2026-09-27 delivery scope

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

The normal publisher listens to both existing source workflows and reuses `--include-global-market`. It consumes GitHub saved artifacts only. It does not dispatch a source, query providers, execute code inside an artifact, run Quick/Full, calculate Odds, create Watch/holdings, or grant investment authority. At this initial 2026-09-27 slice both source workflows were manual-only; later daily authorization and the current timing successor above govern now. That initial slice added no schedule, key, PAT scope, Worker route, cache/database, provider framework or paid subscription.

Use the existing #610 indices36308774368/Shibor36309047326 and #614 treasury36317799016/fx36317890212/commodities36317970476/crypto36318059164 captures for integration verification. Do not repeat source calls to prove reading. Source-specific failures and actual dates survive the join. Original source summaries are preserved under their own scopes; a v1 summary's historical narrower coverage statement is not the v2 aggregate's coverage claim.

Code/CI, normal R publication and actual Sites/mobile adoption remain separate. Sites later adopts this module together with the still-unadopted #612 Markets import/call, preserving the actual host adapter and protections. No Site deployment or extra News/Inbox mutation is performed by this repository change.

Controlled tests cover six-family replay, v1 recovery, independent query failure, partial/failed captures, retained Git bytes after Actions expiry, wrong workflow/family/hash, percent/bp/quote direction, prohibited futures returns, local UI errors and navigation races. Local syntax/Node checks do not stand in for full CI or browser/mobile acceptance. Actual run IDs, hashes and fixed-R readback belong in the PR/#297 delivery receipt, not pre-written PASS claims here.
