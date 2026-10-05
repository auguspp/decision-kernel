# D / #317: follow the original auction pool into its next session

Scope: the continuing #509 delivery. The existing same-session auction-to-close
result remains unchanged. This addition observes each original member's next
completed trading-session raw open and close. It is not a trading return, strategy
backtest, 09:40 observation, new opportunity judgment or full D acceptance.

## Reuse decision: REUSE + THIN_ADAPTER

Reuse the existing Tushare Relay, `stock_market_inputs` calendar/table/key parser
and archive verifier, `d_horizon_follow_up.read_price_parts`, original auction
reader/grouping, Collector custody, shared publication reserve, root assembler
and immutable Git reading history. No new data client, dependency, workflow,
sampling clock, retry policy, state service or parallel registry is introduced.

Before implementation, the current #742 horizon consumer and its external
forward-observation review were recovered. Alphalens / Alphalens-reloaded's
[implementation](https://github.com/quantopian/alphalens/blob/master/alphalens/utils.py)
and [API contract](https://alphalens.ml4trading.io/api-reference.html) were inspected
for the same bounded need. A factor/price-panel return-analysis stack is not needed
for dated raw fields. Existing Kernel source readers directly supply them; no
external algorithm or private third-party application code is copied.

The official Tushare [daily contract](https://tushare.pro/document/2?doc_id=27)
contains both `open` and `close` and describes unadjusted prices. Its
[adjustment-factor contract](https://tushare.pro/document/2?doc_id=28) is a separate
use. This change requests `open` alongside `close` in the existing daily call,
not a new acquisition. These documentation checks are not proof that the
user's Relay has successfully returned the new field; that live check remains.

## Acquisition compatibility without a new gate

New normal `stock_market_inputs.capture` receipts declare `daily_fields=close,open`.
The same calendar plus at most eight price/factor calls, dates, limits, stop and
retry rules remain. `include_open=False` retains the exact legacy request shape.
Absent declaration means the original close-only request, not inferred open data.
Only the two explicit field scopes are admitted. The original report/table schema
and all 5/20/60 arithmetic remain; new reports additionally record the request scope.

Open is deliberately NOT added to the daily parser's required-field gate. A legacy
source or response missing open still supplies its usable close and intervals.
A bad open affects that field only. No 60-day history, factor or second supplier
is required merely to display a raw dated open/close. Original archives and their
reported failures are not rewritten to pretend that open was requested previously.

## Fixed cohort and exact next-session date

Every member of the original source archive is frozen, including matching,
nonmatching, unresolved and excluded rows. Original identity gaps never join to
prices. The exact archive identifies the cohort; the input's collection time and
auction timeliness remain visible. Later capture is not historical 09:25 knowledge.

T+1 is the first explicitly open calendar day after the auction day and no later
than the verified completed market date. Weekends/holidays are supplied by the
source calendar, not guessed. Calendar gaps stay gaps; revisions cannot silently
move an established target. A missing quote or suspended security never shifts
the target to the first later successful quote. This uses the current source's SSE
calendar convention, not a newly established calendar for every exchange.

Each observation uses one admitted daily table for the exact target date. No
quote-row splice between archives, factor=1 assumption, cross-archive price/factor
join, cross-session return or path metric is produced. Complete member rows and
field-level statuses remain in `details/stock/auction-next-session.json`; README
shows the original group denominators and counts of readable fields, not performance.

Pending cohorts survive a new auction. Completed cohorts remain visible throughout
their target day's repeated readings; when a later auction day advances beyond the
target, the old full result is linked by its exact prior Git reading. A later source
gap preserves an already recorded whole result with an explicit prior-reading
source location. It is not recast as newly acquired data. A failed optional
publication keeps a bounded locator to the last successful result, allowing
recovery without losing pending cohorts or walking an unbounded history.

## Existing publication and acceptance

The normal reader attaches after existing horizon follow-up and before optional
index structure under `INCLUDE_CURRENT_STOCK_INPUTS`. Saved JSON reading does not
require CZSC. Source/hash/calendar/size/quota failures roll back only this addition;
prices, existing auction results, Research, Human decisions and lane failures stay.
The stage closes its root clock after projection. Original root/detail/total limits
and formal PR/main/publisher obligations are unchanged.

Synthetic tests exercise calendar gaps, independent open/close gaps, raw-only
semantics, retained cohorts, explicit predecessor recovery and source/byte/budget
failures. They are not actual market observations. The partial local workspace
and its Git/quota substitutes do not establish full Collector or formal CI success.
The actual Sep30 cohort can be replayed, but no completed T+1 prices exist in those
provided source packages. Do not fabricate future-session results to pass acceptance.

Still required: formal exact-head CI/merge/main/publication/readback for this batch,
real future open-field capture, actual next-session observation and natural use.
Auction timeliness, 09:40, true intraday leadership, economic opportunity judgments
and mature outcome calibration remain their own D obligations. No trading,
probabilities, Human wake policy or new source permissions. C/D IN_PROGRESS.
