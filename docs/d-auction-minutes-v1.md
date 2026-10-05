# D / #317: exact-minute observations from the existing auction cohort

This batch continues #509/5987694684: connect a finite source capture, original
byte replay, complete-cohort observation and normal reading. It does not repeat
#741–743 or establish full D acceptance, timely discovery, leadership, Odds or
trading. The 09:40 checkpoint belongs to the registered auction use, not to all
price analysis. No new standing schedule is activated.

## Reuse decision: REUSE + THIN_ADAPTER

The existing FTShare transport owns authentication, bounded response reads,
redirect rejection and safe credential handling. Existing auction replay owns the
original selection, exclusions, name/turnover conditions and source clocks.
Existing stock run discovery, Collector, archive validator, byte/hash helpers,
publication reservation and Git history own retention and normal reading.
No SDK, database, universal provider abstraction, backtest or trader is added.

External/official code inspected before this adapter:

- FTShare Python SDK 1.0.10 at `23eb471c9aae1f6c3ad940d73c4c0fab431761b2`:
  `src/ftshare/apis/stock.py::stock_minutes_batch`, endpoint registry,
  `src/ftshare/base.py` and MIT licence. The method forwards the query; `raw=True`
  is decoded JSON, not original HTTP bytes. It is not necessary to install a
  second client to issue this request through the already installed transport.
- FTShare-skill at `d31ee34c86d68569a486feedec5dd8d5cc29db31`:
  `ftshare-market-data/sub-skills/stock-minutes-batch/SKILL.md` and
  `scripts/handler.py` (blob `9140c844188f31071bf99db335d4a51a23ee60eb`). The
  actual handler sends **repeated `symbols` parameters**, interval_value=1,
  omits adjust_kind for its none default, and calls
  `/api/v2/market/data/stock_minutes/batch`. The documented per-batch maximum is
  20 symbols, span at most three days, limit 1–1000. This is not the old daily
  candlestick route and does not revive the consumed C2 pilot.
- AKShare official stock documentation, `stock_zh_a_hist_min_em`, was reviewed
  as a mature alternative: one named security per call, recent one-minute data
  (documented five trading days), and DataFrame output. It remains a practical
  candidate, not rejected as unusable. Replacing the existing authorized batch
  source with 57 single-security calls or adopting its stack is unnecessary for
  this need. No AKShare code was copied or executed. Documentation was inspected
  at <https://akshare.akfamily.xyz/data/stock/stock.html>; this mutable reference
  is review evidence, not a pinned runtime dependency.

No upstream code is vendored. Source/data rights and account entitlement are not
proved by code licensing or these documentation reads. The first actual response
must still be checked; an unknown schema is not silently made compatible.

## One explicit source-only invocation

The existing `stock-reading-after-sector` workflow gains a manual
`auction-minutes` mode with an exact `minute-reading-commit`. Existing cron strings,
other modes and permission scopes remain unchanged. This mode is excluded from
reconciliation, so a source-only request cannot dispatch unrelated production.
It uses the original independent-main-CI qualification before capture.

Preparation reads three saved files through the original GitHub API: root,
independent-stock detail and its exact auction archive at one R. It validates the
root/descriptor, source ZIP and original auction replay. The seed must be a real
retained source, not a synthetic cohort. No new auction/calendar query occurs.

All original rows and groups are retained. Valid unique identities form batches
of at most 20, querying the original market day's 09:30–09:41, interval=1,
limit=1000. The present 57-row original therefore needs three calls (20/20/17),
not 57 calls or a separate request for every group. The invocation safety budget
is 16 batches; rows beyond it remain explicit unrequested members, not a claimed
complete capture or a new admission rule. No unbounded paging, retry or fallback.

Only the capture step receives the existing FTShare credential; preparation's
GitHub token is not sent to the provider. Authentication/entitlement/rate-limit,
transport and parse failures are distinguished. Any failed call stops later
calls. Earlier usable responses remain usable, with stop and unrequested rows
visible. Receipt intent is saved before each request; exact response bytes, hash,
HTTP/provider outcome and request/receive clocks are retained. Errors that leave
an incomplete artifact stay gaps, never reconstructed success.

## Exact purpose, not strongest-common-denominator qualification

The documented response is a data list of symbol/total/items. A row qualifies for
this observation only with one exact integer closing timestamp of 09:40, its
09:39 opening timestamp, and a positive finite close. Until a real response proves
these fields, the field contract remains unverified in this account. Missing,
conflicting, wrong-date or wrong-time records are not replaced with a nearest
minute, interpolated value or next-day record.

Other minute bars, volume, amount and OHLC are not required for this exact close.
Their absence, or different total metadata, does not cancel an otherwise valid
point. Reported counts are retained separately. This does not certify a complete
intraday path, MAE/MFE, 09:40 trade execution, fresh in-session quotes, or a market
leader. The original source ZIP and full responses allow those separate questions
to be examined later without changing this point's purpose.

Decimal parsing precedes any arithmetic; returned close strings retain their
precision. Auction and minute prices come from different admitted sources and
are shown side by side without a fabricated cross-provider return. Adjustment is
reported as the omitted official none default, not independently audited corporate
actions. No second provider is a prerequisite to using FTShare's own exact point.

Capture starts only after the requested window ends. Historical/late acquisition
is explicitly labelled, with market time and actual receipt time separate. It
cannot establish historical same-time knowledge or natural timely discovery.

## Original normal reading, not an isolated attachment

`stock_market_input_reading.read_current` shares its existing run query with the
auction, same-day close and minute consumers. A failed query is not retried in a
sibling. The minute reader selects the newest matching attempt, preserves its
native conclusion, admits its exact artifact and rebuilds using trusted current
code. Archived source code is never executed.

The result is `details/stock/auction-minutes.json`, indexed through the existing
independent-stock detail and rendered in the original README, including **every
original member** and its gap. The existing publisher title filter admits this
manual source outcome; no new publisher or clock is created. Raw responses remain
in the admitted source archive at the same R.

A pending/failed/unreadable latest attempt does not erase original auctions,
daily prices, Research, Human decisions or other D outputs. A previous result has
an explicit prior-reading commit/path/hash locator, not a false same-R link or
silent current success. Failure to recover that optional prior locator does not
block a valid new capture. Publication capacity is checked against existing
limits; no existing bound is raised.

## Validation and remaining delivery

Tests exercise the original source replay and current transport with synthetic
responses, full 57-row ordering, 20/20/17 batching, per-field gaps, unchanged
source bytes, wrong dates, ambiguous points, HTTP/business denials, no retry,
source-stop propagation, report/receipt tampering, shared-query reading and old
input preservation. Git I/O/shared quota are fixtures in reader tests; they are
not real publishing. Existing actionlint/full CI remains the workflow validator.

The local workspace is partial-source Python 3.13.5, not the full project CI
Python 3.12 environment. Its local harness forbids use of an unrelated unchanged
Research projector whose full dependency graph is not present. Full formal CI
must use the real project modules, including all native obligations, without that
harness. No tests are waived for merge.

The unchanged real Sep30 auction archive was replayed and generated the exact
57-member plan. It is **not** a minute response. Current local FTShare credential
availability is false and the attempted public code download had a DNS failure;
no live minute call or account-entitlement conclusion was made locally.

Delivery requires exact-head full CI, normal merge, independent main validation,
then one explicit manual source execution for the retained seed, actual response
review, normal publisher and fixed-R full readback. If the source clearly refuses
access, preserve the refusal and do not retry that route or upgrade an account.
Do not rewrite thresholds or timestamps to manufacture a successful observation.
No cron activation or natural timeliness acceptance follows from this batch.

C/D remain IN_PROGRESS. Core economic transmission/opportunity judgments, actual
intraday persistence, natural Quick/Brief use and mature calibration retain their
separate responsibilities. Investment Authority = NONE.
