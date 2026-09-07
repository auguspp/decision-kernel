# Stock corporate-action query: history through the completed session

This is a small existing-HiThink request/adapter change after #272, not a new
provider, event platform, selector, adjustment engine or error-to-empty rule.

## What was actually found

The retained stock run 34142455382 used exact code
6fdcf85e7dee404e360491700aea2a5f20b50f5a. Two stocks completed condition checks;
Muyuan and Shennong had HTTP200/business3002/data:null on a June12–September7
event query. The `No adjustment events` text does not override the nonzero code.
Neither our tests nor the official Python client establish successful absence
from that response. The old run and its original evidence remain unchanged.

Primary sources read for this change:

- HiThink website corporate-actions contract:
  https://fuyao.aicubes.cn/docs/api-reference/corporate-actions/
- Official repository contract, pinned version:
  https://github.com/HiThink-Tech/Financial-API/blob/765513c2616030803ad80915ed65b205f425a942/docs/api/endpoints-prices.md
- Official Python REST client, same pinned version:
  https://github.com/HiThink-Tech/Financial-API/blob/765513c2616030803ad80915ed65b205f425a942/python/marketdb/providers/rest.py

Both from and to are optional; the documentation demonstrates single-issuer
history retrieval without a starting date. The official client independently
omits date_from and retains date_to when supplied. No public backend code or
specific official confirmation that 3002 means successful no-events was found.
The official response to issue25 describes a full-market event dump/CLI route;
we do not introduce that larger acquisition/database path here.

## Uniform single request, not retry or adaptive widening

For every planned issuer, the one existing action request becomes:

```
GET /api/a-share/corporate-actions/adjustment-factors
thscode=<exact issuer>
to=<exact latest qualified completed session>
```

There is no initial 61-day event query, retry after 3002, alternate provider,
stock-specific date choice, extra request or automatic next page. The current
four-issuer plan still reserves 18 calls; the global 26-call/30-minute, byte,
256-event-row and pacing limits remain unchanged. Exceeding the event-row bound
is failure, not silent truncation. Known issuer errors stay isolated; rate
limits, auth/shared-input/unknown/transport/security/clock failures still stop.

Success and valid event identity, numeric fields, sorted unique dates and query
end are mandatory. Every event is checked before window use. Events older than
the retained price window are preserved, not deleted or changed to empty. No
trading-session qualification is asserted for those older dates. Dates inside
the retained calendar must still be actual retained sessions. Dates after the
query end, malformed/duplicate events, exposed pagination/truncation, conflicting
counts or contradictory query echoes are rejected; no cursor is followed.

The unchanged #272 rule checks whether an event crosses `(base close, end close]`
of each actual 5/20-day selection or context interval. Older reported events can
be outside those windows without claiming that the issuer has never had an
event. A successful response can support only 'no event reported in this
interval by this provider', never independently certified exhaustive absence.
A new 3002 response remains unavailable, regardless of its message.

## Version, tests and operating acceptance

The adapter source contract advances from v3 to
`hithink-own-61-bars-history-actions-through-session-v4`. The original planner
binds it through POLICY.source_contract and the plan hash. Capture serialization
remains capture-replay-v6: its schema is unchanged and its exact request recorder
and replayer already bind path/params/receipt clocks and original source inputs.
Old captures must use their captured commit, not this implementation.

Regressions cover uniform to-only requests, older/mixed events, selection
crossings, dates/identity/numerics, row limits, partial-response rejection,
nonzero-code refusal, actual transport parameters, issuer isolation, batch-fatal
errors and tampered request/event replay. Integration market/event envelopes are
explicitly synthetic. They are not evidence that a new live history query will
succeed or that a stock will satisfy the unchanged selection conditions.

This removes dependence on an ambiguous short-window empty response when the
provider can return successful history. It is not a claim that the supplier's
3002 semantics are now known or that the hypothesis already succeeded online.
A single fresh run at the merged, CI-qualified commit is still required, with
its own qualified calendar/Sector input, original responses, replay and HTML
acceptance. No old restricted response is relabelled full-history proof.

Prices/volume, turnover tolerance, company scope, ranking/gates, Sector state,
#263 and all authority boundaries remain unchanged. No live request is made by
these changes or tests. Real-stock P0 remains NOT_ESTABLISHED until real evidence.
SHADOW OBSERVATION ONLY; Human Attention / Research / Investment authority = NONE.
