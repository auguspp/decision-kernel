# Sites owner identity fingerprint bootstrap

Date: 2026-09-27. Scope: unblock the already-deployed v8 owner-only Site without exposing or manually copying the raw Sites runtime user id.

## Why this exists

The v8 real-owner browser reached the Worker successfully, but both write actions returned 503 before GitHub because `DECISION_KERNEL_OWNER_USER_ID` and both enable flags were unset. Production logs confirmed that `oai-authenticated-user-id` exists, but the value is intentionally redacted. A management-account id must not be guessed as the runtime identity.

The prior external probe's Cloudflare 1010 is not reused as application-failure evidence. The owner browser did not reproduce 1010.

## Minimal replacement for raw owner-id configuration

The preferred path no longer requires storing the raw runtime id. The unified Site router supports a one-time GET:

`/api/owner-fingerprint`

When and only when `DECISION_KERNEL_ENABLE_OWNER_BOOTSTRAP=1`, the existing hosted GitHub token and the trusted runtime `oai-authenticated-user-id` produce:

`HMAC-SHA256(token, "decision-kernel/owner-fingerprint/v1\\n" + runtime_user_id)`

Only the 64-hex fingerprint is returned. The raw id and token are never returned, logged by this module, written to GitHub, or stored in the repository. Set the returned value as `DECISION_KERNEL_OWNER_FINGERPRINT`, then disable/remove `DECISION_KERNEL_ENABLE_OWNER_BOOTSTRAP`.

Normal API routing recomputes the fingerprint on every request. Only a match receives an in-memory compatibility env containing the request's raw id for the existing #602/#603 handlers. That injected value is not persistent and is not returned. A mismatched/missing identity is 403; missing/invalid configuration is 503.

For rollback compatibility, an explicitly configured legacy `DECISION_KERNEL_OWNER_USER_ID` still works. Configuring both raw id and fingerprint is rejected as ambiguous. The v8 adoption path should use fingerprint only.

Token rotation changes the fingerprint because the token is also the HMAC key. After an intentional token rotation, temporarily re-run bootstrap and replace the fingerprint before re-enabling writes. This is explicit fail-closed behavior, not a persistent identity database.

## Production adoption sequence

1. Keep Quick Inbox and News Refresh disabled.
2. Deploy this small router increment while preserving the original domain, owner-only access, CSP, static fallback and v7 rollback.
3. Confirm the existing GitHub token Secret is present.
4. Set only `DECISION_KERNEL_ENABLE_OWNER_BOOTSTRAP=1`.
5. From the normal authenticated owner browser open `/api/owner-fingerprint`. Record only the returned fingerprint inside Sites hosted configuration; do not paste it into chat or GitHub.
6. Set `DECISION_KERNEL_OWNER_FINGERPRINT=<returned fingerprint>`; remove/disable the bootstrap flag.
7. Enable both existing write features together:
   - Quick Inbox: the current `DECISION_KERNEL_ENABLE_INBOX=1`
   - News Refresh: `DECISION_KERNEL_ENABLE_NEWS_REFRESH=1`
8. In the same owner browser perform the already-defined real acceptance: one actual wanted public material add/remove in #601 and one news refresh run through publisher and same-run R/body readback.
9. Verify a non-owner/missing-identity request fails and that no unprotected alternate Worker URL bypasses the Sites identity edge. Do not weaken Browser Integrity to make automated probes pass.

The fingerprint is an identity comparator, not a credential and not new authority. Browser callers still cannot choose repository, Issue, workflow, ref, URLs, model or research execution. Existing token scopes remain Issues:write for Inbox and Actions:write for news refresh; no Contents write is added.

## Validation boundary

New dependency-free Node tests cover deterministic HMAC, no raw-id/token disclosure, bootstrap enable/disable, cross-site refusal, fingerprint match/mismatch, ambiguous config rejection, legacy rollback compatibility, unknown API JSON and original static fallback. Existing Quick Inbox and News Refresh tests remain unchanged and continue to exercise the exact handlers. This does not claim production edge header integrity, Worker outbound access, GitHub write success, phone layout, real Inbox selection or news acquisition until the Site performs those actions.
