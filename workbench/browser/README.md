# Isolated Workbench browser verification

Owned by the AN2 slice of #625; calendar consumer scenes extend it under #620 and saved Concept member scenes under #645. This exercises the **actual** `workbench/index.html`
and its imported modules in Chromium. No replacement app, real account, secret,
GitHub write, market acquisition, research call or Sites deployment is involved.
The normal `kernel-tests` full/evidence/main/publisher contracts remain separate.

## Run

From a complete reviewed checkout with Python 3.12 or later:

```sh
python -m venv /tmp/kernel-browser-venv
/tmp/kernel-browser-venv/bin/python -m pip install -r workbench/browser/requirements.txt
/tmp/kernel-browser-venv/bin/python -m playwright install --with-deps chromium
/tmp/kernel-browser-venv/bin/python workbench/browser/smoke.py --output /tmp/kernel-browser-proof-001
```

Installation needs an authorized dependency/network/OS-package environment.
After installation, test traffic is completely intercepted and the browser
context is offline. An already-installed Chromium can be explicitly selected
with `--chromium /path/to/chromium`; its **actual** version is recorded, not
assumed equivalent to the Playwright-managed build. Do not disable browser
security, change management policy or use another URL to evade a denial.
A process that launches successfully is not proof that its page can load.

The output directory must be new and outside `workbench/`. The command exits
nonzero on an assertion, environment failure, undeclared request, credential,
JavaScript error, unproven transport failure or unexpected console failure. No scene reruns or automatic
retries. Playwright assertions wait for asynchronous UI state; that is not a
rerun of a failed scene. Do not use Python `-O` (assertions are required).

A source bundle contains only its declared paths. Running every Node test from
an incomplete bundle is not a complete-checkout validation: some existing Node
tests also read `.github/workflows/radar-newsnow-daily.yml`. Do not invent a
replacement workflow fixture to turn missing-source failures green.

## What the scenes prove

Each scene uses a fresh context at 1360×900 and 390×844:

1. Recover a registered synthetic item, read its correction, original and old
   response, then copy exact R/request/history without writing or closing it.
2. Search and paginate the company catalogue; a held preview cannot replace an
   explicitly selected company's body or reset its query.
3. Reject an equal-byte-length altered body using actual native Web Crypto,
   while preserving the independently registered request.
4. Refresh to a different pinned R, select its body, then finish the old-R read;
   the old response must not overwrite the new selection.
5. Preserve six synthetic index rows and a stock panel alongside explicit
   unavailable source families; no zero quote or completeness inference.
6. A declared HTTP 503 affects only the global-market panel, not the stock panel.
7. Read three saved calendar appointments with original/local clocks, then read
   their same-R excerpt; embedded source script remains inert text.
8. Reject an equal-length calendar-body change via native SHA-256 while other
   market and stock panels remain readable.
9. After refresh, a held old-R three-row calendar cannot replace the new-R
   one-row window, even after its native digest completes.
10. A legacy R without calendar registration is explicit absence, not no events;
    no calendar body is fetched and the stock panel remains available.
11. Search the complete synthetic Concept catalog, open its members, distinguish
    qualified / conditions-not-met / unavailable / not-checked Stock states,
    inspect exact shared-member counts with both denominators, and read an
    existing same-R company document. Source markup stays literal text.
12. Reject equal-length member-body tampering via actual Web Crypto while
    preserving the original Concept quotes, calendar and independent Stock panel.
13. Finish a held old-R membership response after refreshing and selecting a
    new-R concept. The old members cannot replace the new reading or its detail.

The fixtures follow existing controller/global-markets test shapes. Repeated
`a`/`b`/`c` identities and all numeric quotes are **TEST_ONLY**, not actual Git
commits or financial observations. Descriptor sizes, SHA-256 and blob identities
are calculated from the actual fixture bytes. Synthetic `reading_hash` and
projection markers are shape inputs, not a claim that canonical hashes were
recomputed (the existing consumer explicitly does not do that).
Calendar fixtures also provide a REVIEWED_WEB_EXCERPT display shape solely as
TEST_ONLY data; this is not source review, admission, or a publisher replay.
The separate backend tests reject actually synthetic bundles from publication.

`context.route` fulfils only declared GET requests. Unknown paths, writes and
credential headers are aborted and fail the scene; service workers are blocked.
No local HTTP service is opened. `127.0.0.1:4173` is an intercepted test origin,
not a destination for real traffic. Existing HTML CSP/MIME, DOM, module imports,
reader/renderer and digest decisions remain in use. A narrow digest-completion
observer delegates to the native `SubtleCrypto.digest` and returns its unchanged
result; it only lets late-response assertions wait for real processing rather
than accidentally passing before the response completes.

A second passive tap observes the **original** Fetch stream reaching EOF; it
never clones/tees a body, changes cache policy, replaces a verdict or suppresses
a rejection. Each fulfilled response gets a test-only correlation header.
Chromium can emit `net::ERR_ABORTED` even after complete stream consumption (see
upstream https://github.com/microsoft/playwright/issues/42742; a report, not proof
of this run). Such events are never discarded: the runner requires the exact
response ID, HTTP 200, URL, actual EOF, byte count and SHA match before recording
`STREAM_EOF_BYTES_SHA_MATCH_TERMINAL_EVENT_CONFLICT`. Any missing/mismatched proof
or other failure still fails the run. UI assertions remain separately required.
Declared HTTP errors are separately recorded as status rejection, **not**
successful body consumption; the product is not required to consume a 503 body.
The runner waits for actual successful Fetch EOF, not `networkidle`, and checks
terminal events again after context cleanup. This is not a claim that arbitrary
network errors are harmless.

## Evidence and CI scope

`summary.json` contains actual scene results, source/fixture hashes, Git head
when available, browser/Playwright versions, requests/responses, console/errors,
and elapsed scene times. Source hashes inventory the recorded checkout inputs;
the request/response list identifies the bytes actually loaded. `git_head=null`
is explicit when there is no complete Git checkout. Success
keeps a few screenshots; failures retain screenshot, original traceback and a
Playwright trace. Native tracing captures browser/network activity, **not** the
`expect` assertions; the JSON report records scene outcomes separately.

The native `workbench-browser` workflow runs on Workbench-related pull requests
and explicit manual invocation only. It uses no business secrets or write token,
does not trigger the production publisher, and does not add a browser `needs`
to unrelated PRs or change their full-suite scope. Browser-affecting changes
need both their applicable ordinary full proof and this browser result before
adoption. A green ordinary CI does not substitute for a missing/failed browser
run. A manual rerun is not allowed to replace a failure; fix the cause and retain
both results. Artifact retention is 14 days, not a permanent archive.

This is not browser testing of the real Sites adapter/identity/CSP, server-side
write permissions, mobile hardware, live upstream availability, independent
AI-context recovery or Human acceptance. Those boundaries remain with #625/#621.
There is no new registry or monitoring service. If this verification surface is
retired, remove its runner, fixtures, optional requirements, workflow and this
entry together; keep the relevant historical failures and current lower-level
contracts.

Official reuse references: https://playwright.dev/python/docs/network and
https://playwright.dev/python/docs/api/class-tracing .
