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
- Candles use day, adjust_kind=none, exact millisecond bounds, no truncating
  limit, one request per symbol. The endpoint Skill's bare array and the official
  SDK's `data` array envelope are supported. The envelope must have integer
  code 0/200 and only code/data/optional string-or-null message keys; no missing,
  boolean or string code, nested records/items, alternative container, or
  conflicting rejection is accepted. The same row/date/unit checks apply to both
- Factors use symbol, start_date=20260707, end_date=20260930, page_size=50,
  at most two pages. Unknown envelope/pagination fails closed; recognized
  pagination alone never qualifies factor meanings, row identity or date coverage
- Effective dividends use v2, symbol, page_size=200 and only page 1. There is no
  announcement-date bound, avoiding exclusion of earlier-announced in-window
  ex-dates. Source total_cash_dividend_ratio is consumed once per ex-date group,
  never summed across duplicate group rows. Incomplete page scope remains visible

No upstream implementation was copied or dependency added. No price/free-tier
claim is inferred from the user's account-access confirmation. Provider results
remain scoped to the actual attempted routes; an HTTP 403 alone does not establish
its underlying cause.

### Candle-envelope correction after the first diagnostic run

Run [36821818724](https://github.com/auguspp/decision-kernel/actions/runs/36821818724)
at main `1d2e277572f20c57f1ca4d36e02136317043700e` retained only HTTP 200,
integer provider code 200, top-level dict, 251 bytes and `CANDLE_SHAPE` for
001246.SZ candles. Its ephemeral raw body is unavailable: the `data` field,
row count and actual bar comparison are **not established**. This correction
must not be reported as a successful replay of that body or real comparison.

Reuse Decision remains REUSE + THIN_ADAPTER. The pinned official SDK
[`src/ftshare/response.py`](https://github.com/FTShare-Lab/FTShare-python-sdk/blob/23eb471c9aae1f6c3ad940d73c4c0fab431761b2/src/ftshare/response.py)
explicitly supports a data-array envelope and documents code 0/200 as success.
This adapter adopts only that narrow form alongside the endpoint Skill's bare
array; it does not adopt the SDK's generic nested/items extraction or code
coercion. Synthetic documented fixtures establish adapter behavior, not the
unrecovered live response's contents. The retained #508/#511 and internal reuse
review above still apply; no new client, generic parser or dependency is needed.
The correction authorizes no new source request or retry.

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

The exact native manual diagnostic run title is excluded before the existing
reader's latest-production selection and control's daily production-attempt
count. The publisher's notification-title filter is only an early optimization:
the existing delivery wrapper checks the exact native upstream attempt before
collection or any public Git write. Other manual/scheduled purposes retain their
normal routes. Excluded run IDs remain in diagnostic metadata; the provider still
counts their real source calls. This is not free or unlimited FTShare quota.
The existing 30-run all-today bounded-history guard still counts every scanned
run, so diagnostics cannot hide an incomplete daily scope.

### Diagnostic publication isolation correction

The first real comparison [run 36821818724](https://github.com/auguspp/decision-kernel/actions/runs/36821818724)
did not stay isolated at the publisher boundary. The existing downstream
[job 110238843955](https://github.com/auguspp/decision-kernel/actions/runs/36821822294/job/110238843955)
logged that exact trigger and wrote reading `00d3aa0b61ffbb07a4076009357f28b90a2b6817`.
The reader still retained normal Smart Money run `36755230971`; diagnostics were
not promoted to production observations. The original webhook payload/action
was not retained, so its precise missing or differing field remains UNKNOWN.
The native exact-attempt response has the expected path and diagnostic title;
full-field synthetic expression tests alone did not establish trigger isolation.

Reuse Decision: REUSE + THIN_ADAPTER in the existing delivery wrapper and bounded
GitHub API client. The official [exact-attempt API](https://docs.github.com/en/rest/actions/workflow-runs#get-a-workflow-run-attempt)
supplies run/attempt, source SHA, repository/head-repository, main branch,
workflow path and purpose. A workflow-run publication reads that one pinned
attempt using the event's exact locator, never a latest run or another attempt.
Missing/conflicting identity or unavailable Smart Money purpose fails closed at
`TRIGGER_QUALIFICATION`. An identified comparison returns
`READ_ENTRY_PUBLICATION_SKIPPED: FTSHARE_DIAGNOSTIC` before reading collection,
local export, blobs, trees, commits or ref writes. Normal Smart Money native
title `radar-smart-money` remains eligible for requested/completed publication;
other producers and direct scheduled publication keep their existing routes.
The early workflow filter, reader and daily control exclusions remain in place.

This is suppression of publication, not a promise that GitHub creates zero
downstream runs/jobs. A downstream job may install the existing package and read
metadata before recording the skip. No new owner, framework, dependency,
permission, schedule, provider call, retry or fallback is introduced. Offline
regressions use the observed native metadata plus explicitly counterfactual
missing-notification fields and unknown/conflicting identities. They do not
replay the consumed source comparison or assert live adoption of this correction.

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
and bounded comparison counts/differences. Shape diagnostics use fixed allowlists
of structural and row field names, a 64-character identifier pattern and at most
64 names; other key counts saturate at 64. They expose root/data types and known
keys without arbitrary key text or values. Diagnostic provider codes must be
integers in -99999..99999. Error-body shape decoding is best effort and cannot
override an HTTP stop; a code or the legacy `ENTITLEMENT_DENIED` status label
does not determine a 403's cause. No raw body, price series, dividend record,
provider message, credential or arbitrary exception text is logged or uploaded.
The raw bodies exist only in the runner's temporary directory and are
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
