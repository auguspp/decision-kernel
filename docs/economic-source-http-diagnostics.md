# Economic-source HTTP diagnostics

Status: DIAGNOSTIC IMPLEMENTATION / NEW CONTROLLED LIVE PROBE REQUIRED / NO SOURCE-SUCCESS OR MARKET CLAIM.

## The observed failure, not a guessed cause

Public compatibility run `33947395994` (implementation `1c19360e5b400933339f452ba159117d5a8408e2`) retained two matched SPB bodies and two MOA `HTTPError` failures. That version did not preserve numeric HTTP status. Its archive and `docs/economic-source-raw-capture-proof-2026-09-05.md` remain unchanged; neither a later status nor later success may be retroactively assigned to that run.

The next probe has one diagnostic question: which HTTP status does the exact current request return? It keeps the same four reviewed URLs, request headers, per-page timeout and byte budgets. No cookie, credentials, user-agent impersonation, proxy rotation, redirect following, retry or source fallback is added. A refusal is evidence to report, not permission to evade access controls.

## Numeric record and safe failure handling

Capture schema 2 adds mandatory `http_status` to every source record:

- accepted or rejected response bodies: exact integer status, reconciled with retained response metadata;
- `HTTPError`: retain only a valid integer error status, not the exception URL, server reason, headers or error body;
- blocked redirect: retain only a numeric 3xx code, not the destination or cookies;
- unknown or malformed status / non-HTTP transport failure: explicit null, never guessed from exception text.

Booleans, strings, floats and out-of-range values are not coerced. `HTTPError` bodies are not read; the file-like exception is closed. The original reviewed URL remains the request identity. Only successful bounded body acquisition can supply raw HTML for the existing reviewed-excerpt binding; an error record is not a body capture.

Python 3.12 documents the numeric status in `HTTPError.code` separately from the reason, headers and body: https://docs.python.org/3.12/library/urllib.error.html . Redirect processing remains disabled as documented in https://docs.python.org/3.12/library/urllib.request.html . No library or provider is added.

The summary now shows each source ordinal, acquisition/binding disposition and numeric HTTP status (or UNKNOWN). The offline verifier regenerates that summary and rejects inconsistent status fields or response metadata, even when outer hashes are recomputed. It continues to reconstruct accepted and rejected bindings. An HTTP error without a body has integrity and operational evidence only: offline verification cannot authenticate the remote status or reproduce the outage.

HTTP 200 does not imply matching facts; a changed page can still be REJECTED_BINDING. Similarly, an HTTP status by itself cannot prove why access was refused, that the source moved, that a condition is permanent, or that economic facts changed.

## Schema and evidence compatibility

Schema 2 does not alter market state, the event ledger, economic observation/binding schemas, the reviewed source list or existing workflow definitions. Old schema-1 archives must be checked at their exact recorded implementation; the new verifier refuses an implicit upgrade. Missing old status is not filled from new observations. Fresh captures receive separate run/attempt identities and archive directories.

All of the current request and storage limits remain unchanged. Unit tests use explicit synthetic provenance and do not contact official servers. They exercise the lowest opener error path, safe code extraction, error-stream closure without reads, mixed response/rejection results, blocked redirects, non-HTTP failures, invalid codes, summary/status tampering and old-schema refusal.

## Controlled operational follow-through

The already-maintained `economic-source-capture.yml` workflow is path-filtered to the capture implementation, so merging this diagnostic change intentionally invokes one new four-source compatibility run. The purpose is new status evidence, not repeating unchanged code until a favourable result. Review its exact run/SHA, per-source codes, failures and private proof artifact once. Do not rerun merely to turn a red run green.

The workflow remains INCOMPLETE/nonzero if any source is unavailable or a reviewed statement fails binding, even if retained archive integrity passes. This diagnostic change does not add a schedule, make HiThink calls, write market state/events, activate continuous economic monitoring or change authority.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
