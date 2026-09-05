# Stock snapshot clocks: isolated reference-window correction

Status: IMPLEMENTED FOR ISOLATED DUMP STUDY / LIVE RESULT MUST BE REVIEWED SEPARATELY / NOT PRODUCTION STOCK DATA QUALIFICATION.

## Primary evidence and scope

Reviewed 2026-09-05:

- HiThink official stock snapshot contract: https://github.com/HiThink-Tech/Financial-API/blob/main/skills/hithink-finance/references/api/endpoints-prices.md (inspected blob `c8d9cc7d636dbb944404328f0e254387afb80585`). `data.timestamp` is data-ready time, in paginated mode the latest effective time in the sequence. Explicit ticker-batch mode can return null. The documented stock rows have no individual trade/session timestamp.
- SSE stock trading page: https://one.sse.com.cn/onething/gptz/ . Ordinary trading days are Monday through Friday; fixed-price trading extends to 15:30. The separate reference capture guard starts no earlier than 15:30. This is an operations boundary, not a guarantee of vendor finality or a change to the existing index-close formula.
- Retained real run `33957604949`, artifact `9966871869`, original ZIP SHA256 `d6b5bd578daacbb05d1bac05995ab494d74e9dc70ab9046f0eb08c601fba2b91`. Stock page 0 had timestamp `1788599907000` (Saturday 2026-09-05 17:18:27 Shanghai), received at `2026-09-05T09:18:28.548563+00:00`; qualified benchmark comparison session was Friday 2026-09-04. All original bytes/hashes and the failed run remain unchanged.

The old all-stock date-equality gate conflated a response-level ready clock with a represented session. But simply removing the check, borrowing the index rule, or declaring all stocks fresh because CSI300 matches would make a different unsupported claim. This change separates what is established from what still needs reconciliation.

## Explicit opt-in, no silent production migration

`HithinkStockSnapshotReference` is a small immutable request context used only by the isolated dump trial. It composes the existing qualified CSI300 object, exact provider trading calendar, timezone-aware observation/receipt clocks and Python date operations. It is not another calendar feed, signal state, parser, scheduler or data platform. No additional dependency is added; Requests, PyArrow and the existing pager/identity/price/row inspector remain reused.

Without that context, `fetch_hithink_all_market_snapshot` preserves the original same-date Sector producer behavior. No production caller is switched here. An opt-in batch instead carries:

```text
OBSERVED_STOCK_QUOTES_FOR_OFFLINE_RECONCILIATION_NOT_PER_SECURITY_SESSION_PROOF
PROVIDER_DATA_READY_TIME_NOT_MARKET_SESSION
```

The comparison session comes from the independently qualified benchmark/calendar. Each stock's true last-trade date is not thereby proven. Assigning the comparison session in the normalized input is an explicit reconciliation reference convention, not a vendor-supplied row timestamp. Original response timestamps and prices are never overwritten.

## Narrow supported capture windows

Accept only one of:

1. The observed Shanghai date is the independently established completed session, at or after 15:30.
2. The anchor is Friday and observation is its directly following Saturday or Sunday, with no intervening weekday.

Require exact sorted unique weekday calendar entries, anchor membership and agreement with the existing latest-completed-session calculation. A later weekday is rejected, even when missing from the provider calendar. A Thursday-to-weekend gap, stale following weekend, unfinished Monday, or holiday-like weekday omission fails. **Calendar absence is never holiday proof.** Holiday support is deliberately absent until there is an explicit independently reviewed closure basis; no added third-party calendar or inferred working-day substitution.

For every page, its original ready timestamp must be a positive integer millisecond clock, at or after the anchor's 15:30 boundary and no later than actual receipt. Receipt must be timezone-aware, at/after reference observation and on the same Shanghai observation date. A future time on the same day fails too, not just a future date. Across-page min/max clocks are retained. This does not establish an atomic cross-page snapshot; all total/identity/coverage checks still apply.

The existing strict rules for exact identities, stable total, no duplicate rows, complete pagination, null prices and zero/invalid numeric values remain. No price tolerance, filling, fallback provider, new universe filter or excluded-security assumption is added.

## Trial outputs and interpretation

Trial report schema 2 saves `reference-window.json` (calendar and qualified benchmark hashes, capture basis and unavailable per-security-time authority), original decoded pages, normalized inputs and timestamp range. `snapshot.json` explicitly marks reference semantics. Report and file hashes bind these records. Original schema-1 trial failures remain original failures, not upgraded records.

Only after complete collection does the unchanged PyArrow row inspector compare date-keyed raw dump closes, turnover and previous raw closes. Any mismatch or missing/unpriced reference remains a non-success result. Even perfect checked-field agreement remains same-provider consistency, not independent exchange authentication, historical constituent membership, corporate-action PIT, revision stability or continuous entitlement. The dump trial always retains `production_qualification=NOT_ESTABLISHED` and has no production state/event writer.

Tests use the retained clock values as a regression, plus synthetic physical Parquet, multi-page, incomplete-session, malformed/future clock, unchanged production default, null preservation and exact mismatch cases. They do not relabel a synthetic reference as a live scan or manufacture the eleven pages absent from the old artifact. The local environment lacks PyArrow and package-network access; full physical-reader tests execute in the existing GitHub CI, not as a claimed local run.

## Controlled verification

This code change to the existing trial module will trigger its existing narrow main-path workflow once after merge. No workflow file, dependency, schedule, budget, secret scope or authority is changed. Review the actual report, complete raw-page inventory, all normalized inputs and the row result before reporting success. A failed row-level inspection remains useful evidence, not permission to weaken the checks until green. Old failed probes are retained.

The prospective Sector producer, live market state, candidate ledger, company postures and canonical Attention Inbox are untouched. No multi-day breadth is activated. SHADOW OBSERVATION ONLY; HUMAN ATTENTION / RESEARCH / INVESTMENT AUTHORITY = NONE.
