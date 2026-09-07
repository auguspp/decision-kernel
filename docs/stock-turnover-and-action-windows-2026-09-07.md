# Stock input policy: bounded turnover tolerance and action-scoped windows

This is the user's authorized compatibility change, not a new selector, provider,
price adjustment engine or investment authority. A few unavailable fields must
not invalidate unrelated usable intervals. It does not promise a positive match.

## Primary implementations consulted

- Python PEP 485: https://peps.python.org/pep-0485/ — use an explicit symmetric
  relative/absolute comparison. Its defaults are not universal domain policy.
  We implement the comparison using Decimal instead of converting amounts to
  binary floats, and add a project-specific absolute safety cap.
- Zipline `SQLiteAdjustmentWriter` and adjustment interface:
  https://zipline.ml4trading.io/_modules/zipline/data/adjustments.html — retains
  dividend effective dates and applies adjustments to earlier history. This
  supports distinguishing an interval which crosses an event from one entirely
  after it. We do not import its dividend-ratio calculation or claim adjusted data.
- LEAN / QuantConnect normalization modes:
  https://www.quantconnect.com/docs/v2/writing-algorithms/securities/asset-classes/us-equity/requesting-data
  — raw, adjusted and total-return data have different meanings. A raw-price
  observation cannot silently become adjusted performance or investor return.

The particular numbers below are our user-authorized reconciliation policy,
not a HiThink precision specification, benchmark result or industry standard.
Public implementation patterns do not prove absence of unreported events.

## Amount-only policy

For positive, valid CNY turnover values `a` and `b`, permit:

```
abs(a-b) <= min(100 CNY, max(0.01 CNY, 0.0000001 * max(a,b)))
```

The relative component is 0.00001%, not 0.01%. Examples: roughly 1 million CNY
permits 0.10 CNY, 100 million permits 10 CNY, and the cap never permits more than
100 CNY. This is not a blanket 100-CNY tolerance on a small trade. Zero, missing,
negative, boolean, nonfinite or out-of-schema amounts remain invalid. The
comparison is symmetric and independent of the caller's Decimal context.

Only the snapshot/history turnover reconciliation changes. Security identity,
dated calendar, all 61 bars, OHLC, current/previous prices, volume, clocks and
other existing checks remain strict. Calculations continue to use the original
dated history amounts. The raw responses, both amount values, absolute delta,
computed bound, policy version and reconciliation result are retained. No
rounding, replacing values, filling gaps or automatic tolerance growth.

## Corporate actions follow the actual dependency window

The original stock selector uses 5-day and 20-day raw close comparisons. Its
60-day value is context, not a gate. A reported ex-date affects a close-to-close
comparison if `base_close_session < ex_date <= end_close_session`. An ex-date on
the base session is outside that comparison: both endpoint closes follow it.

A successful validated action query is still mandatory. Nonzero business codes,
including 3002 with a `No adjustment events` message, are not converted to empty
success. Existing stock-local isolation and batch-fatal rate-limit/auth/shared
input/security/clock/budget behavior are unchanged.

Validated events crossing a 5/20-day selection interval still isolate that stock.
Earlier reported events are retained and disclosed rather than excluding the
whole stock. Any affected 60-day or shifted-20-day comparison becomes JSON null,
including stock excess comparisons, with explicit per-window reasons. The
original bars and event records remain available; no adjusted or total-return
claim is created. Malformed or duplicate event records are not bypassed just
because their apparent dates are older. Other planned stocks continue normally.

## Existing evidence, not a new live success

The already retained run 34131183418 (original commit
`ba29867eb2a3a1b38af62dd92f88c84b029c1bd3`) supplied four full individual histories
and quotes. Its original ZIP SHA-256 is
`ea5f1dc633a61e9497636d947b375c4f5089a6e715fa8ce5b1bf3e2d493f93ee`.
Local execution of the modified standalone adapter on those unchanged responses
accepted the Wens and Juxing input windows. Muyuan and Shennong still failed the
business-response check. Their respective amount deltas, 43.20 / 3.61 / 2.25 /
1.36 CNY, fit the explicit new amount policy; this does not resolve the two 3002s.

Wens' June24 and Juxing's July2 events are before the August10 base close of the
20-day interval ending September7. The affected 60-day comparison is withheld.
Separate arithmetic using the retained closes shows both companies' 20-day raw
changes still below both linked sector changes. Input qualification is not
selection: do not tune gates or promise new cards to make this example positive.

This is a new-policy component regression using old inputs, NOT replay/acceptance
of the old run under new code, a fresh provider capture, or a full local checkout.
The old run remains NO_USABLE_STOCK_DATA under its captured implementation. Full
repository CI separately exercises the original planner/selector/capture/replayer
with explicit synthetic inputs, including partial coverage and tamper rejection.

## Delivery semantics

The policy and capture versions change. JSON/HTML identify tolerance and window
availability. Actions' final stock summary now uses business status and coverage,
not merely a green process plus an empty card list. Only that summary body is
changed in workflow YAML; triggers, credentials, permissions, acquisition,
concurrency, retry policy and all other jobs are unchanged.

No fresh live request is needed to test this fix against retained inputs. Fresh
production acceptance remains a separate bounded run at its own exact commit,
qualified calendar and Sector input. This change alone does not establish P0.
#263, company scope, Sector state/cache and all authorities remain untouched.
SHADOW OBSERVATION ONLY. Human Attention / Research / Investment authority = NONE.
