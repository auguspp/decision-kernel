# Mobile / same-origin reading-ref resolution

Adopted after v15 real mobile Edge/WebGPT use showed the browser fixed-reader failing at the first anonymous GitHub REST pointer lookup with HTTP 403 while desktop could still read the same saved package.

The reading evidence contract is unchanged. Only the mutable pointer resolution moves server-side:

1. Browser GETs same-origin `/api/read-model/current-state` with the fixed intent header.
2. Worker uses the existing single-repository hosted PAT to read exactly `refs/heads/read-model/current-state`.
3. Worker returns only `{ref:"read-model/current-state", commit:"40hex"}`.
4. Browser then uses that exact commit with the existing raw reader. `current-state.json` and every selected registered body remain browser-fetched at fixed R and subject to the existing bytes/SHA-256 checks.

The endpoint accepts no repository, ref, path, URL or arbitrary GitHub request from the browser. It is not a content proxy and does not return token, identity, GitHub bodies or logs.

This needs the existing fine-grained PAT, still limited to `auguspp/decision-kernel`, to include **Contents: read** in addition to the already-used Issues:write and Actions:write. No Contents write is needed. Human explicitly authorized this read permission on 2026-09-27 for the real mobile Edge/WebGPT Sites path.

The original public REST pointer resolver remains available to non-Site/library tests when no endpoint is supplied; the production app explicitly chooses the same-origin endpoint. This avoids silently changing reusable reader semantics outside the hosted Site.

Failure is explicit: missing server token, GitHub Contents refusal/rate limit, or malformed ref identity keeps the reading unavailable. There is no anonymous retry, stale-R fallback, mutable-branch body read, cache/database, automatic source run or research action.
