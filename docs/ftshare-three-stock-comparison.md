# FTShare three-stock comparison: isolated producer-side diagnostics

This is the explicit 2026-10-01 comparison of `001246.SZ`, `920202.BJ`,
`301190.SZ` over the original 2026-07-07–2026-09-30 Shanghai window. It does not
replace HiThink, qualify adjusted prices, add Research/Watch, or change normal
Smart Money schedules and publication. New-stock pre-listing bars are never
fabricated. A source response is not proof of complete expected trading history.

## Reuse and contracts

Reviewed main: `a136c06afb8e9528d2e4fc217748eb631f023a42`. Reuse Decision:
REUSE + THIN_ADAPTER. The existing `ftshare_market_inputs.request` owns bounded
FTShare HTTP, existing `FTSHARE_API_KEY`, fixed host, redirect/reflection guards,
2 MiB response cap and 20-second timeout. The three new fixed request contracts
use that transport; no arbitrary endpoint/config/client, new dependency, secret,
storage service or provider framework is introduced. Existing source capture,
strict JSON/Decimal, clock and hash primitives are reused.

Prior-art entry reviewed: #508 High-Relevance Living Prior Art and #511 candidate
pool, plus existing `docs/ftshare-integration.md` and
`docs/provider-batch-cnequity.md`. Existing CNEquity adjustment/query machinery is
not needed for source diagnostics; unknown factors are not handed to its adjusted
reader. The exact official SDK/Skill implementation is the matching external
prior art, not a new multi-provider library.

- FTShare Skill `d31ee34c86d68569a486feedec5dd8d5cc29db31`, each SKILL.md and
  scripts/handler.py under stock-candlesticks, stock-adjust-factor and
  stock-dividends-effective were inspected
- Official SDK `23eb471c9aae1f6c3ad940d73c4c0fab431761b2`,
  src/ftshare/apis/stock.py `stock_adjust_factor`: start_date/end_date YYYYMMDD;
  omitted trade_date otherwise defaults current/prior trading day
- Candles use documented bare array, day, adjust_kind=none, exact millisecond
  bounds, no truncating limit, one request per symbol
- Factors use symbol, start_date=20260707, end_date=20260930, page_size=50,
  at most two pages. Unknown envelope/pagination fails closed; recognized
  pagination alone never qualifies factor meanings, row identity or date coverage
- Effective dividends use v2, symbol, page_size=200 and only page 1. There is no
  announcement-date bound, avoiding exclusion of earlier-announced in-window
  ex-dates. Source total_cash_dividend_ratio is consumed once per ex-date group,
  never summed across duplicate group rows. Incomplete page scope remains visible

No upstream implementation was copied or dependency added. Provider entitlement,
quota or success is untested until an authorized real run. No price/free-tier
claim is inferred from the user's account-access confirmation.

## Exact execution boundary

Only the existing `radar-smart-money.yml` owner receives this opt-in mode:

- workflow_dispatch, current main, attempt 1, reviewed code-sha equal github.sha
- ftshare-stock-history=three-stock-20260930
- relay-only=false, relay-reports-only=false, repair-pending=false
- exact main CI must already be successful
- current main ref, checked-out SHA and CI's repository/head-repository/push
  identity must bind that exact code
- normal primary and Relay jobs do not run in comparison mode
- nine planned first requests; only validated factor pagination can add one
  request per symbol; absolute twelve-request cap; zero retries or fallback
- authentication, entitlement, rate-limit and credential-reflection stop the batch
- same fixed FTShare host/secret owner; no HiThink/Relay/source/model extra calls

The exact manual diagnostic run title is excluded before the existing reader's
latest-production selection, control's daily production-attempt count, and
publisher's requested/completed trigger. Other manual/scheduled invocations are
unchanged. Excluded run IDs remain in diagnostic metadata; the provider still
counts their real source calls. This is not free or unlimited FTShare quota.
The existing 30-run all-today bounded-history guard still counts every scanned
run, so diagnostics cannot hide an incomplete daily scope.

HiThink comparison reads the already-saved exact run36815556951/artifact11141865519
(artifact digest `f985274834e5ca99f995912148fe1af1ebf83f3e0ad7dee05ea8aeeb4807bfde`).
Each of the six consumed response files is SHA256-checked before a source call.
Its one/two/61-bar history and nonzero3002 responses remain unchanged; 3002 does
not become an empty corporate-action list. Candles compare unadjusted OHLC,
share volume and CNY turnover by Shanghai session. Dividend comparison is limited
to overlapping event-date numeric cash amounts; factors and HiThink event records have
different semantics, and no adjusted-price arithmetic is performed.

Unit evidence: the pinned FTShare candlestick Skill explicitly specifies yuan
and share/unit volume. HiThink Financial-API `3bca7805a4127ece8d81961917e740d2effac6ec`
`docs/api/a-share/prices.md` explicitly says A-share prices/turnover CNY and volume
shares. For these three stocks that supports unadjusted bar-unit comparison.
Both effective-dividend and HiThink corporate-actions documents specify pretax
per-share cash, not per-ten-share cash. FTShare's dividend table does not name
the currency explicitly, so the event numeric difference is deliberately
`NUMERIC_DIFFERENCE_UNQUALIFIED_UNITS`, not a qualified monetary mismatch.

The existing download-artifact@v8 input was checked against upstream action.yml:
artifact-ids, run-id, github-token and digest-mismatch=error are supported.
Its src/download-artifact.ts extracts one artifact directly at the selected
path; the original ZIP's independent-stock-capture directory is preserved.

## Custody and acceptance limits

Only a safe technical report is uploaded: request identities, clocks,
HTTP/provider codes, raw byte counts/hashes, field names, pagination/coverage,
and bounded comparison counts/differences. No raw body, price series, dividend
record, provider message, credential or arbitrary exception text is logged or
uploaded. The raw bodies exist only in the runner's temporary directory and are
lost with that runner. This is explicitly PRODUCER_SIDE_ONLY verification,
not independent raw replay or durable source custody. Capture time is not
historical availability/PIT. Missing data never imply factor1 or no event.

The mode itself does not publish to current-state or the two previously approved
C2 observation files. Raw-publication permission or a separately authorized
private custody route would be needed before durable raw archive/replay; this
change creates neither. Do not rerun an inconclusive capture automatically.

Exit: report actual source contract/coverage differences and decide whether any
further narrow qualification is useful. Real errors and unknowns remain visible;
this diagnostic increment does not sign off the full C2 discovery route.
