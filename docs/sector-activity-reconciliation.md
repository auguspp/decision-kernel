# Sector activity metadata reconciliation — 2026-09-25

This updates only the metadata preflight contract described in the historical `sector-radar-scheduled-production.md`. It does not change the producer, source qualification, market-state continuity, scheduler, Research or investment authority.

## Observed failure, not an invented cause

Human authorized “那 sector 修一下”; scope/reuse record: [#297/5829043734](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5829043734).

Sector run `35985939145`, job `107588493161`, stopped on 2026-09-24 before any market acquisition with `GITHUB_ACTIVITY_RESPONSE_INCOMPLETE`. No structured market output existed for upload. The response that triggered that historical run was not retained: the exact sub-condition and deeper cause remain UNKNOWN.

One isolated metadata-only diagnostic on 2026-09-25 reproduced the count/list inconsistency class: [run36110665643](https://github.com/auguspp/decision-kernel/actions/runs/36110665643), job107993165395, commitbb78695d2940e5ee0a248c4f2a801116cce12645. The queued query returned HTTP200, 36 bytes, total_count=1, workflow_runs=[], no next link; body SHA256 `134d1a5f88fc6e48e9e6689b031e057d67c1fff70cbbba5c0e4fa98e8804795c`. Four other statuses returned0/0. This does not prove the historical response was identical or establish why the API count differed. The diagnostic did not query a provider or rerun Sector.

## Bounded repair

Keep the existing normal path: one repository GET for each of in_progress, queued, waiting, pending and requested. Complete count/list/row results still finish in five requests.

If a well-formed repository page has count/list drift or pagination, do not accept its empty list as absence. Reconcile once using the native workflow-scoped endpoint for every declared key-sharing peer and every active status. This is a narrower, fresh metadata observation, not a repeat of the same broad query. Every scoped page must have valid identity, exact count/list completeness and no next page. Any blocker observed in either stage remains a blocker. The check remains a non-atomic observation, never a global key lock or provider quota proof.

The default three peers permit at most 5+3*5=20 GETs. The existing Stock successor passes four peers, at most25. Each URL is fixed to this repository, a validated workflow filename, an allowlisted status and page1/per_page100. No new dependency, polling, sleeps, HTTP retry, redirect or arbitrary URL following. Invalid JSON/rows, oversized bodies, HTTP/auth/transport errors stop immediately; incomplete scoped visibility also stops. Market requests, 429 handling and direct-next/session validation are unchanged.

## Diagnostics and lifecycle

The existing precheck log/Job Summary now includes safe per-query scope, status, request/finish clocks, HTTP status, byte count, body hash, reported/returned counts and pagination indication, plus the final result. No token, raw HTTP error body, or new file in the sealed market inventory is written. This improves failure localization before operations.json exists; it does not claim those logs are already in the durable read-model.

The one-off diagnostic workflow lives only on its diagnostic branch and must be retired by a forward commit after bounded validation. Do not merge it into main or delete the original run. Production has no added workflow or clock.

## Reuse and acceptance

Internal: existing activity checker and caller, original schedule/Stock-successor regression obligations, existing CI v2. Official: [workflow run REST](https://docs.github.com/en/rest/actions/workflow-runs) supports workflow-scoped status queries; [pagination](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api) explains Link metadata. External: cli/cli `pkg/cmd/run/shared/shared.go`, reviewed blob1d1d3d34ed9bbea7f83bee9fdb23119baece50f8, uses workflow-specific queries and Link handling. Reuse the native API and standard library, not an independent scheduler.

The new offline tests exercise the real 1/0 payload at the transport boundary, every active blocker status, preservation of earlier blockers, scoped incompleteness/wrong identity, pagination, auth/429/timeouts, malformed/oversized responses, URL limits, extra peer propagation and failure diagnostics. Existing incomplete-input tests still require rejection when the scoped response is also incomplete; no guard is skipped to obtain success.

Formal exact-head PR full CI, normal merge, applicable main reuse/smoke and ordinary publisher/readback are separate from these local tests. A successful metadata-only probe does not certify a real Sector market run.

## Remaining historical gap

At the repair baseline M2606e7f8ceed06d25c6ca13cf783ffb6778436b7 / R3bd1e879e62b1403953b53a3f0f6fb50b7a01f18, the last Sector checkpoint was9/23. This patch does not recreate missing9/24 source bytes or make9/25 a direct-next session. Qualified recovery remains a separate explicit obligation. Do not silently skip/reset the gap, backfill historical events, or claim the next natural daily chain is accepted.
