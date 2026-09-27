# B1 first source slice: global indices and CNY interbank rates

2026-09-27. Human approved starting B1 after the independent Quick Inbox recovery sample; #297 comment5854341422 records the exact scope and reuse review. This is source-only mechanical context, not research or a completed global-market dashboard.

## Reuse and limits

**Reuse Decision: THIN_ADAPTER.** Keep `runtime/tushare_relay.py` exactly at blob `d2ee02a81648eafe7204a47e7f8e41b56c3c48fd`: its destination, header credential, TLS behavior, response bounds and one 30-second temporary-queue retry are unchanged. The prior blocked replacement-client action is not repeated. Both `index_global` and `shibor` were already in the finite allowed API set and were explicitly assigned to B1 by `data-source-orchestration-v1.md`. Smart Money's checkpoint and service-refusal stop semantics were inspected, but this module never borrows its A-share calendar or source qualification.

Official field references, checked 2026-09-27:
- https://tushare.pro/document/2?doc_id=211 — international index daily rows, exact `ts_code`, `trade_date`, close in index points and reported `pct_chg`.
- https://tushare.pro/document/2?doc_id=149 — Shibor date and eight tenors; annual percentage rates, not US Treasury yields.
- https://github.com/waditu/tushare/blob/master/tushare/pro/client.py — official fields/items table seam. Its official POST/token transport does not replace the reviewed third-party Relay transport.

External implementation inspected: OpenBB `openbb_platform/providers/yfinance/openbb_yfinance/models/index_historical.py`, blob `23501fca412f5a443561f2d24cc67bce361c6e36`: explicit symbol resolution, bounded start/end dates, separate extraction/transformation and an empty-data error. Those are useful reference behaviors; no OpenBB code is copied, package installed or generic provider stack adopted. Existing credentialed Relay access is the smaller present-use seam. Yahoo/OpenBB is not silently made a fallback or considered live-tested here.

The actual source is the **third-party Tushare Relay**, not official Tushare provenance. API documentation describes a compatible contract; it does not certify what this Relay actually returns. A real source run must still establish response shape and availability.

## One family per request

The new `radar-global-market.yml` is manual-only, exact current main and successful independent main CI gated, attempt 1, with only Contents/Actions read permissions. Its existing source credential is `TUSHARE_PROXY_API_KEY`; no new key, Site secret, PAT permission or natural schedule is created.

`family=indices` requests six explicit series: SPX, IXIC, HSI, HKTECH, N225 and GDAXI. `family=shibor` requests one table with overnight, 1w, 2w, 1m, 3m, 6m, 9m and 1y. These are separate executions; neither refresh silently starts the other. Shared Relay concurrency avoids overlapping these B1 runs. This does not coordinate every other existing Relay consumer.

Each request covers 14 calendar dates ending on the selected `as-of-date`. The end defaults to yesterday UTC and is limited to the prior 31 days, avoiding an intraday/current-date claim. No exchange calendar is inferred from weekdays or missing rows. The source dates remain visible even when different regions are on different last-returned dates.

Upper bounds: indices at most 6 logical requests / 12 transport attempts; Shibor at most 1 / 2. The original client's single temporary retry remains its only retry. HTTP401/403/429, authentication/rate refusal, missing credential or an untrustworthy request receipt stops subsequent calls to this service for this run. Incomplete receipt counts are UNKNOWN, not fabricated zero. No anonymous fallback, new endpoint, retry cron or paid service is used.

## What is retained and checked

Each run writes an initial checkpoint before HTTP, updates it before/after each logical request, and retains raw response bytes plus request parameters, requested/received timestamps, bounded safe headers, status, exact byte count and SHA-256. Credentials and reflected credential content are not persisted; exception text is not logged. Partial runs remain partial; an initial failure does not delete a prior artifact or mutate existing reading state.

`capture.json` binds the exact GitHub repository/workflow/ref/code/run/attempt, family, finite plan, capture times and original body identities. `summary.json` and `summary.md` are derived by the offline replay, not independently trusted state. A raw-byte or scope mismatch fails replay. Duplicate source fields/dates, foreign symbols, impossible/out-of-window dates, non-finite/boolean/negative index values, and declared truncation cannot become confirmed observations.

Index changes calculated here compare the last two **actually returned** closes and retain both dates. They are not automatically a one-session return. The separately preserved source `pct_chg` is a provider declaration, not a requalified market price. Shibor remains annual percent; a difference of 0.05 percentage points is 5 bp, not 5 percent return. Missing latest-tenor values remain missing instead of borrowing an earlier value under the latest date.

Market open/closed state and publisher clock remain UNKNOWN/not supplied. Fetch time never replaces source date. Empty or failed output does not mean quiet markets, no change, or a decision to stop researching. Source values neither change Belief nor start Quick/Full/Odds/Watch/trading.

## Delivery stages

This slice provides executable source capture, original retention, offline replay and a human-readable artifact. Artifacts use the existing GitHub Actions surface and 30-day retention; this is not a permanent historical database. Useful results must follow the existing normal retention/reading seam in the subsequent reader integration, before long-term availability is claimed.

The source workflow is **not yet a publisher trigger** and this slice does not insert unverified values into `current-state` or the production Markets page. After real source fields/coverage are checked, the next B1 slice connects verified snapshots and latest-attempt gaps to the existing fixed-R reader/Markets. There is no Sites handoff or new deployment in this slice.

Remaining B1 families: US/global sovereign rates, gold/oil, FX, crypto; plus their units/time/market-session qualifications. Shibor must not be reported as completing the global bond/rates requirement. Existing A-share sector pages and News/Inbox are unaffected. B2 research calendar follows B1, not part of this source change.

## Validation boundary

37 controlled tests exercise the original client via injected synthetic transport, independent family scope, date/unit/interval behavior, malformed/empty/partial inputs, service stop, original retry, secret-safe failure, archive replay and manual workflow constraints. Initial local run used a partial checkout and Python 3.11; the unmodified local Relay copy was checked against its exact Git blob. This does not replace the repository's Python >=3.12 complete CI or a live source run. Actual CI/capture/artifact results are reported separately in the PR/#297, never pre-written as PASS here.
