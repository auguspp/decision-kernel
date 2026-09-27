# Controlled news refresh — original Sites integration

Authority: Human “好，继续”, adopted NEXT-PHASE-CONSTRUCTION v3 and #297/5851755041. Base main `efd2ab603aff1bcc681f30206561621d7087ac2c`; previously published reading `f776e0d66f3901b5c15515bf5439e855c4a0bb38`. This batch implements the bounded refresh seam; it does not deploy Sites, configure credentials or repeat the earlier live news acquisition. Exact PR/main/publication evidence belongs to the delivery receipt.

## User result, not a research executor

“刷新最新新闻” performs an explicit same-origin prepare then submit. Preparation checks the current exact main, the allowlisted workflow bytes, its active status, the latest independent successful main CI, unfinished native news runs and the workflow-wide last run number. Neither page load nor preparation dispatches. The browser cannot choose repository, workflow, ref, source, model, inputs or arbitrary URLs.

A submitted request is not a completed capture. “检查本次更新” is a separate user action that reads only that request's exact GitHub run. After a successful run, publication/body verification is deliberately delegated to the existing browser pinned-R reader instead of duplicating GitHub ref/body reads inside the Worker. Clicking “读取最新保存结果” invokes that immutable-reader refresh; only the resulting fixed R, registered original body and size/SHA256 checks establish what is actually readable. This is not a second acquisition, and run success alone is never presented as published content.

Quick remains “加入待 Quick → #601 → web research”, not an automatic follow-on. No model calls, Full authorization, Odds recalculation, Watch/holdings registration or Human acceptance is added. Original news/source clocks remain visible. Failed/unknown requests do not clear old news. Native GitHub/copy/status alternatives remain in a secondary disclosure, not a second scheduling service.

## Concurrency and uncertain submissions

A short-lived signed permit binds a random correlation ID, exact main, the last native workflow run ID/number and issue time. The existing hosted token signs a purpose-separated HMAC together with the configured owner; neither token nor owner value is returned. No additional signing secret or persistent store is needed. Submission rechecks all preconditions and the 120-second deadline immediately before the one POST. It does not silently rebase to a newer main or run. Status lookup may use the permit for up to 30 days; this is not a 30-day execution permission.

GitHub API version `2026-03-10` returns the dispatched run ID; the response's repository URLs are checked. A legacy 204 is submitted-without-identified-run, not a failed submission to retry. Lost responses, server errors, malformed JSON and HTML fallback are unconfirmed. A later lookup must match the nonce-bearing run name, repository, workflow, main branch, event, owner actor and native identity, or remain unknown; it cannot choose the newest unrelated run. Multiple matching runs are not silently collapsed into success. No automatic retry or polling was added.

An in-isolate bounded promise map prevents concurrent POSTs for the same permit locally. It is NOT durable idempotency. The source-side protection is the existing workflow's optional `site_*` preflight: only the exact expected next native `run_number`, exact code and attempt 1 can reach the source container. Two Worker instances observing the same baseline can create two GitHub runs, but their different native numbers cannot both satisfy that same expected slot. The extra run fails before acquisition; if native concurrency cancels a pending run or another run takes the slot, zero captures may occur. This is conservative at-most-one acquisition for the same baseline, NOT exactly-once dispatch or guaranteed success. Native/direct GitHub executions with all three inputs empty retain their original behavior and permissions; users manually issuing independent native commands are outside this Site permit's deduplication scope.

Failed/racing/cancelled runs remain real history and can appear as the latest-attempt gap. They are not filtered away to preserve a green display. A fresh explicit request after a confirmed terminal outcome is a different intent; an uncertain request stays in reconciliation rather than automatically obtaining a new permit. No localStorage queue or new canonical ledger is used.

## Original host integration and security

Mount `handleWorkbenchAPI` from `workbench/server/routes.mjs` ahead of the ORIGINAL host's static routing. It handles the new `/api/actions/news-refresh` and existing `/api/quick-inbox`; unknown `/api` paths return JSON 404, while non-API paths return null for the existing asset/fallback implementation. It does not guess a Worker asset binding or replace `.openai/hosting.json`, the root, old links, owner-only configuration or rollback. The #602 browser CSP already permits same-origin connect; no additional relaxation is introduced here.

Keep refresh disabled until the actual Sites edge has been tested to supply trustworthy `oai-authenticated-user-id`, strip spoofed identity values and prevent an unprotected alternate Worker URL. The exact origin, owner, JSON content type and intent header are checked; cross-origin requests are rejected. Browser input and upstream responses are streamed under byte/time limits with fatal UTF-8 parsing. Credential-bearing requests are fixed GitHub repository Actions paths; raw workflow/source reads and public ref reads do not receive the token. No response includes upstream exception text, environment contents, private identity or credentials.

Hosted configuration, not chat or public Git: `DECISION_KERNEL_OWNER_USER_ID`, existing `DECISION_KERNEL_GITHUB_TOKEN`, and `DECISION_KERNEL_ENABLE_NEWS_REFRESH=1` only after host checks. Refresh requires single-repository Actions write; Inbox separately requires Issues write. No Contents write or GitHub App is introduced. The present actor path is the owner's fine-grained PAT; a different bot/App requires explicit identity review. Token rotation invalidates outstanding permits, whose status then needs native GitHub reconciliation; rotation is not permission to automatically resubmit.

The route pins the reviewed workflow SHA256. A legitimate later workflow change must update and test that pin with its Site adapter, rather than silently allowing changed downstream actions. This is a bounded compatibility responsibility, not an assertion that GitHub CI establishes research truth.

## Reuse First and concrete references

Internal: existing news workflow/source/archive/publisher; unchanged same-R `reading.mjs` and `product.mjs`; #602 trusted-owner/Origin/limited JSON pattern and existing Inbox route; native UI and original update alternatives. Thin adaptation only, no new dependency, database, queue, Agent or scheduling platform.

Official references inspected for this batch:
- https://docs.github.com/en/rest/actions/workflows — fine-grained Actions write and versioned dispatch return contract.
- https://github.blog/changelog/2026-02-19-workflow-dispatch-api-now-returns-run-ids/ — explicit old-version return_run_details and direct native run identity.
- https://docs.github.com/en/actions/reference/workflows-and-actions/variables — GITHUB_RUN_NUMBER is unique per new workflow run, unchanged by reruns; GITHUB_RUN_ATTEMPT separates reruns.
- https://docs.github.com/en/rest/actions/workflow-runs — status filters and exact run metadata.
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency — native concurrency is not exactly-once delivery; no new queue option was adopted.

External: `lasith-kg/dispatch-workflow` at `2597e9a3d222d7959052dea1c009560bbeb495e4`, actual `src/api/index.ts` blob `e4dd238295f0e5172b50839cf6af6006274620f9`. Its direct workflow dispatch/run-ID path was examined, not just README. We reuse the native endpoint idea, not its Actions package, generic repository dispatcher, polling/executor or error behavior. Legacy/uncertain responses here remain explicit and are never blindly retried. No third-party source was copied. Earlier EasyStock/Vibe display review remains applicable without a new full product survey. Reuse Decision: THIN_ADAPTER.

## Validation, non-claims and exit

Node coverage keeps owner/Origin/shape/config refusal, exact workflow/CI/state, signed permits, expiry including expiry during preparation, lost responses, duplicate submits in one and two isolated module instances, malformed/oversized replies, run correlation, wrong actor/head/attempt/native number, double-click, navigation and explicit status interaction. It also asserts that successful Worker status no longer re-reads the mutable reading ref or saved body, while the existing browser reader remains the sole byte-verified publication path. Three Python tests continue to execute the exact YAML pre-source script with native/valid/race/malformed inputs and original CI failures. These are controlled tests, not live GitHub native-counter/Worker/network acceptance.

The unchanged local reader and product bytes were checked against their current Git blobs. Existing remote regression files are preserved; the original pytest wrapper only adds the new files. No claim of a whole-repository local run or a rendered browser is made. Formal full CI, raw artifacts, normal merge, independent main validation, original publisher and fixed readback are separately required. The previously policy-blocked browser path is not retried or bypassed.

Only the existing news workflow receives optional correlation/admission fields; its original source image, source list, transport, permissions, downstream completion trigger and publisher are unchanged. No live source dispatch, model request, task, token, permission or deployment is performed this batch. Source-side GitHub context, production owner identity/outbound, actual Site click, CSS/phone and the existing Inbox's real research consumption remain live-acceptance gaps. The next product step is consolidated adoption on the original v7 host, not more transitional buttons or repeated source probes.

On retirement remove this route/control, enable flag and its exclusive tests; reconcile the optional workflow fields and the workflow pin in the same change. Keep native source history, research/Inbox records, source reader and shared safeguards. GitHub remains canonical; source refresh does not change Belief or create investment authority.
