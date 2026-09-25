# Inbox source gaps remain visible — 2026-09-25

Human requests 9/24 completion, correction of Inbox misreporting, and a real end-to-end run (#297). The actual failed Inbox run36112372925 exhausted the existing calendar timeout recovery and raised HithinkRuntimeError through the first legacy price-recheck package; no Inbox or typed Watch was produced.

Reuse the existing odds_watch.build_watch PRICE_UNAVAILABLE_NOT_QUIET contract and validator, original Inbox renderers and calendar batch failure latch. Extend only the composition boundary. There is no source fallback, added dependency, retry budget increase, new workflow or scheduler. Legacy research/Decision inputs, Watch registration/thresholds, serialized hashes and authority remain unchanged; a gap result is not new Research or Odds acceptance.

An identified Hithink market acquisition failure now records the affected package/ticker and lets other qualified inputs and the original typed Watch be delivered. A failed ticker is not acquired a second time through Watch. Native HTTP401/403/429 rejects further account acquisition in this process; exhausted calendar acquisition retains the existing two-attempt latch. Arbitrary programming, malformed package/configuration and semantic validation failures are not swallowed into price gaps.

The combined Markdown/HTML explicitly distinguishes planned/completed/unavailable legacy package checks and enabled/checked/confirmed-trigger/non-trigger/unknown Watch counts. Empty-state wording is scoped to the completed subset rather than claiming that the whole market or daily Quick is quiet. Successful delivery can be DEGRADED_SOURCE_GAPS; exit0 means a truthful result was delivered, never that every price was acquired. Consumers must continue to read typed Watch gap rows and the coverage text instead of equating a green workflow with complete market coverage.

The prior calendar transport tests remain. Their complete-outage composition expectation changes from no artifact to a validated all-gap Watch and explicit incomplete coverage; no old price or success is restored. New tests cover partial failures, shared ticker no-retry, account rejection latching, invalid inputs, unexpected bugs and the 4-checked/1-unknown denominator.

Actual new source execution and product acceptance must be recorded separately after current-head full CI, normal merge/main checks and publisher readback. This change does not repair provider availability, backfill historical observations, or guarantee a scheduled research result.
