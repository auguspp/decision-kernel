# Stock reading: issuer isolation and explicit usable-subset delivery

This is a user-authorized update to the stock reader's failure scope, not a new
selector or authority. It supersedes the older all-or-nothing rule **only for
known issuer-local HiThink data failures**. The full plan is still frozen before
requests; the 26-request budget, 30-minute lifetime, original gates and original
max-three presentation order remain unchanged.

## What continues, what stops

A typed failure bound to the currently requested stock can be isolated: missing
or insufficient own history, invalid individual data, no trading activity,
quote/history mismatch, discontinuous previous price, or reported corporate
action requiring separate review. Single-stock business codes 3001, 3002 and
3004 are recorded as **unavailable**, not interpreted as successful empty data.
The original safe response is retained. Remaining stocks are still checked.

Shared calendar/catalog/index/state/membership qualification, credentials,
transport or unsafe-response errors, future response-ready clocks, reversed or
expired actual clocks, budget exhaustion, unknown business errors and 4001/HTTP
429 still stop the batch. There is no retry, provider fallback or permission to
publish a subset after a batch-wide failure.

Only the existing HiThink raw-input path isolates these failures. Corrupted
caller-supplied synthetic reference fixtures remain rejected as before.

## Output meaning

Every planned issuer remains in `all_stock_observations`. An isolated issuer has
`input_failure` with phase, finite reason, category and business code; no price
path, selection claim or conditions-not-met reason is invented. The complete
plan remains the denominator. `coverage` separates planned, dispositioned,
evaluated, price-path-checked, qualified, conditions-not-met, unavailable and
not-evaluated counts.

- `PARTIAL_STOCKS_FOR_SHADOW_READING`: usable subset contains qualifying stocks;
  excluded data gaps remain visible. Not an exhaustive full-plan top three.
- `NO_MATCH_IN_EVALUATED_SUBSET_WITH_DATA_GAPS`: evaluated subset has no match;
  unavailable issuers remain unknown. Not a complete no-match result.
- `NO_USABLE_STOCK_DATA`: all planned stocks are unavailable, not zero matches.
- The original complete-scope and no-business-coverage statuses remain distinct.

The recorder seals partial batches as `COMPLETED_BATCH_WITH_STOCK_DATA_GAPS`,
not `COMPLETE_STOCK_READING`. The existing replayer reconstructs the plan,
request order, exact retained responses, issuer dispositions, coverage, JSON and
HTML. Its receipt says `STOCK_BATCH_WITH_DATA_GAPS_REBUILT`, never full coverage.
A successful process exit proves that the partial report was built/replayed;
it does not prove all inputs usable or the real-stock P0 complete. The capture
step adds an explicit partial-coverage warning to the Actions summary as well.

Versions: selector `stock-first-reviewed-scope-issuer-isolation-v5`, input
contract `hithink-own-61-raw-bars-receipt-bound-quote-and-reported-actions-v2`,
recorder `stock-reading-capture-replay-v4`. Old captures must be replayed at
their captured version; they are not relabelled by this change.

## Quote timestamp compatibility

The website prices documentation permits a latest upstream-ready timestamp,
or null when unavailable:
https://fuyao.aicubes.cn/llms-full.txt (prices / snapshot field table).
The older repository document instead describes null for explicit thscodes:
https://github.com/HiThink-Tech/Financial-API/blob/765513c2616030803ad80915ed65b205f425a942/docs/api/endpoints-prices.md

Both null and a positive integer timestamp are now supported. A non-null value
must be no later than **that quote's actual receipt**, checked before the next
request and again during qualification/replay. The timestamp is not an
individual trade date. Future clocks, malformed timestamps and missing actual
receipts are not fixed by waiting for the corporate-action response.

No empirical amount tolerance or rounding rule was introduced. The observed
43.20 amount difference still makes that stock unavailable. A 3002 response
saying `No adjustment events` still does not establish a covered empty event
window. All original raw-price, exact quote/previous-close, company evidence and
reported-action qualification requirements remain.

## Acceptance boundaries

The six-issuer regression plan is explicitly synthetic and uses the real
selector/recorder/replayer with network disabled. It is not six newly reviewed
real companies. Current real company coverage remains the existing curated
scope; the last real plan contained only Muyuan. Isolating that one issuer
cannot manufacture other stocks or establish majority availability.

No Sector producer, state, cache, schedule, provider or dependency is changed.
No new workflow dispatch is performed by this change. #263 remains separate.

SHADOW OBSERVATION ONLY.
HUMAN ATTENTION / RESEARCH / INVESTMENT AUTHORITY = NONE.
