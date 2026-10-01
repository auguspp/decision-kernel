# Stock qualification: action-aware reference prices and bounded 3002 recovery

Date: 2026-10-01

This change closes two issuer-local qualification gaps without changing schedules,
notifications, research routing, investment authority, Sector gates, company
selection, or the existing 26-request Stock ceiling.

## Problem reproduced from retained 2026-09-30 inputs

The retained Stock capture `36702153468` showed two different failures.

- A successful corporate-action response can report an ex-date on the latest
  session. In that case the snapshot `prev_price` can be an ex-rights reference
  rather than the prior raw close. Comparing it to the raw close before reading
  the already-fetched action rows falsely classifies a coherent input as
  `PRICE_REFERENCE_DISCONTINUITY_REQUIRES_SEPARATE_REVIEW`.
- Corporate-action business code `3002` is not an empty event result. It remains
  an unavailable action response and must not be relabelled as “no actions”.

The production example that exposed the first bug was 600585.SH: retained
2026-09-29 raw close 16.98, retained 2026-09-30 cash dividend 0.13 per share, and
retained snapshot previous reference 16.85. The arithmetic identity is evidence
for the generic rule, not a ticker-specific exception.

## Generic qualification rule

For a successful corporate-action response, retained event fields are validated
before the snapshot previous-reference comparison. This change qualifies only
a cash dividend with zero bonus/share-transfer. For an event on
`(base close, end close]`, the price-comparison reference factor is:

`(previous_raw_close - cash_per_share) / previous_raw_close`

The factor is used only when every crossing event has supported, positive,
source-bound cash arithmetic. Raw bars and event rows stay unchanged and retained.
Bonus/share-transfer events remain separate-review because the required exchange
rounding/reference-price convention has not been established here. A zero-effect
or unsupported event, missing required bar, invalid arithmetic, identity mismatch,
pagination/truncation, or malformed event still fails closed.

This is a price-reference adjustment for comparison. It is not a total-return
series, dividend reinvestment, economic return, valuation adjustment, or
investment judgment.

## Bounded recovery when the action lane returns 3002

A `3002` action response remains recorded as unavailable and is never converted
to an empty event list. If the frozen request plan has room under the existing
26-call ceiling, the reader may spend **one** reserved call for the same
provider's `adjust=forward` historical price path.

That fallback must independently pass the same dated-session, identity, clock,
latest-OHLC, volume/turnover, and snapshot previous-reference checks. The result
records that the action query failed, that event details were not inferred, and
that provider forward-adjusted prices supplied the comparison path. If the
fallback is unavailable or invalid, the issuer remains unavailable. There is no
second retry, provider switch, synthetic event, or batch-wide rerun.

The planner reserves at most one such call and never raises `MAX_REQUESTS=26`.
Normal issuers retain the original three issuer-specific requests.

## Compatibility and authority

The selection qualification contract advances to v6 and Stock reader versions
advance so old captures continue to replay at their captured commits. Existing
raw-path cases retain their old arithmetic. Company-action-aware and provider
forward-fallback cases are explicitly labelled in JSON/HTML.

No schedule, notification, credential, repository authority, Research authority,
Human attention authority, Odds, Action, or Investment authority is changed.
AI Investment Authority = NONE.
