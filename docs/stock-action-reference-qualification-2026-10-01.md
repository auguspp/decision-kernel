# Stock qualification: action-aware reference prices and bounded 3002 recovery

Date: 2026-10-01

This change addresses two issuer-local qualification paths without claiming fresh coverage or changing schedules,
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

## Post-merge continuation: consumer reconciliation and actual checks

PR #704 merged at `a6d673ae2039b14d02b57a91ec718c22547cdce1` while this continuation
was examining the original failures. Its later commits already separated the raw
default and persistent-gap fixtures; those changes are preserved, not replayed.
The follow-up fixes the still-unreachable forward HTTP request, scalar reference
precision and raw convention compatibility, with dedicated regression evidence.

The adjusted-price option belongs only to the current Stock observer. The shared
`stock_path_for_sessions` and `_stock_path` remain raw by default; selection-window
history tolerance does not imply permission to change the price convention.
The observer explicitly opts in via `action_reference_adjustment=True`. Manual sector-member comparison and independent
saved-stock consumers retain their raw-window exclusions and do not inherit the
new adjustment or recovery request.

A scalar reference price uses the exact `previous_raw_close - cash`, not a
round-trip through a repeating factor. No price tolerance or rounding rule is
introduced. Forward and raw history must cover the same dates and preserve
reported volume and turnover. The source's forward normalization remains a
provider claim, not independent certification of all corporate actions.

The actual HTTP wrapper accepts only `none` or the explicit `forward` daily
request; merely mocking the observer is not sufficient to establish that seam.
Regressions exercise the real wrapper with a mock transport, the single-batch
reserve, successful capture/replay with the original 3002 preserved, and a
persistent-gap capture which still rejects a falsely relabelled complete result.

On 2026-10-01, a local component comparison used the original ZIP
`47f4ea4d31f4d575ebb5d16c64269aaaafc280d6ed5e07dc4cce35e6c333fec8`.
The four originally usable inputs remain usable. The 600585.SH triplet at
`reading/responses/23.json`–`25.json` passes the explicitly opted-in qualifier;
its snapshot 16.85 equals the exact cash subtraction. The raw-only default still
refuses the crossing interval. The 688806.SH triplet at `11.json`–`13.json` still
contains business3002; **no forward response exists in that original capture**.
No live recovery of that issuer is claimed. This is new-code component testing
on old bytes, not original-run replay, a new market capture, publisher registration
or a change to #581. Full PR, independent main and publication checks are separate.

## Reuse and primary contracts checked during continuation

- The existing [HiThink contract](https://github.com/HiThink-Tech/Financial-API/blob/765513c2616030803ad80915ed65b205f425a942/docs/api/endpoints-prices.md)
  explicitly offers forward/backward history when raw action rows are not needed.
  Only the forward variant is admitted here; the current
  [corporate-actions documentation](https://fuyao.aicubes.cn/docs/api-reference/corporate-actions/)
  was also read. Neither source makes an arbitrary business3002 a successful empty
  event list. No provider or SDK dependency is installed.
- [Zipline's dividend adjustment implementation](https://github.com/quantopian/zipline/blob/master/zipline/data/adjustments.py)
  and its [maintained interface documentation](https://zipline.ml4trading.io/appendix.html)
  support effective-date boundaries and the cash/previous-close ratio pattern.
  Its database/asset engine is unnecessary for one bounded source adapter:
  THIN_ADAPTER using the existing transport and Decimal, not a new adjustment
  platform. This continuation check does not retroactively claim that the first
  draft performed Reuse First before coding.

Exit by a normal reviewed PR, preserving the raw default, source bytes, old
commits and failure receipts. Existing schedules, notifications, credentials,
26-call ceiling and investment authority remain unchanged.
