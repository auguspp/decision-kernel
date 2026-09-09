# P0-4A Source Acquisition Bridge v0 — Sanhua only

This is a Harness source-package seam, not Research, Evidence admission, a new
crawler, market-data collection, Human attention, or a company conclusion. The
previous Sanhua preflight remains SOURCE_PREFLIGHT_INCOMPLETE / NOT_EXECUTED.
#291, #288, original Kernel/Funnel schemas, production packages and Human state
are unchanged. Timeline failure 34294226918 remains independently UNKNOWN.

## Fixed plan, before the single real acquisition

- Issuer: 三花智控, 002050.SZ / SZSE:002050. Resolve orgId from the actual official
  stock map, including its exact issuer name; do not copy an ID from a mirror.
- CNINFO window: **2026-08-01 through 2026-09-09**, Asia/Shanghai date filter.
  This is the observed inventory at capture time, not proof of future-day
  completeness or an exhaustive all-channel disclosure audit.
- One credential-free stock-map GET; one issuer/date inventory query with
  explicitly numbered pages: page size 30, at most 3 pages / 90 announcements.
  Blank searchkey/category intentionally retains the whole returned issuer
  window. No silent page truncation, query fallback or retry.
- At most 4 original bodies; this plan selects at most **2**: the unique exact
  full 2026 H1 report (not its summary), and the unique IR activity record
  published on August 27/28. The reported timestamp/date identifies the selected
  IR lead; acquisition does not interpret the meeting contents or economics.
- 8 maximum HTTP requests, 8 MiB per body (existing transport bound), 48 MiB total,
  zero retries/redirects, fixed connect/read timeouts 10/20 seconds. A ten-minute
  one-shot workflow bounds the attempt; it has no schedule or manual-dispatch trigger.

Reuse `adapters.cninfo` org resolution and announcement normalization, plus the
existing `stock_field_source_study` constants, public Requests session and HTTP
body checker. A thin wrapper retains actual content type and status rather than
inventing MIME metadata from a suffix. **The existing source-study runtime and
workflow are deliberately not edited:** their path-triggered main push would
otherwise start the excluded Muyuan capture. No existing workflow is dispatched.

## Deterministic source selection and fail-closed behavior

Require exact secCode/orgId on every returned row, unique IDs across all pages,
stable total count, numeric qualified publication timestamps inside the query
window and not after capture, and a consistent boolean hasMore. All rows and raw
pages are retained. More than the declared page budget, unqualified publication,
missing final rows, cross-issuer rows or ambiguity stops before selecting bodies.
No older result, secondary mirror or inferred CNINFO URL repairs that failure.

Select `2026年半年度报告` (with optional exact issuer prefix) and the declared IR
record from actual normalized rows. Only returned `adjunctUrl` originals matching
`https://static.cninfo.com.cn/finalpage/YYYY-MM-DD/<digits>.PDF` are fetched. A
summary is not the full report; multiple matching versions require review.
Missing IR permits retaining the uniquely selected full report, but the package
remains SOURCE_CAPTURE_INCOMPLETE. An ambiguous IR blocks further acquisition.
Any 429, 5xx, redirect, transport failure or invalid PDF container stops the attempt.
Successful earlier bytes and all attempted-request records remain available.

v0 enables **no alternate direct URL**. Existing reviewed HKEX locators in the
old source register refer to other periods/documents; they are not substitutes
for missing 2026 H1/IR. Adding a future alternate requires a predeclared reviewed
exact official locator and identity, HTTPS host/path qualification, GET only,
credential-free/no-redirect/byte bounds. There is no arbitrary-URL CLI. The
MOA/SPB-only `economic_source_capture` allowlist is not altered or misrepresented
as CNINFO/HKEX support.

## Source package and verification

```text
sanhua-source-package/
  workflow.json              exact GitHub run / attempt / SHA
  capture/
    plan.json                fixed source-only plan
    request-journal.jsonl    request-before-send and completed response records
    001.json ...             exact original stock-map / inventory response bytes
    00N.pdf ...              exact returned selected PDF bytes
    capture.json             issuer/inventory/selection/metadata and capture hash
  verification.json          offline verifier result, distinct from capture success
```

Each attempted request records exact method/URL/form, local start/completion
clock, HTTP status or null, actual Content-Type or null, safe failure code/type
and retained body path/length/SHA256. No cookies, redirect targets, environment
credentials, source exception prose or Secret values are logged. Even malformed
HTTP-200 bodies remain raw failure material, not accepted Evidence.

Each successful selected body binds announcement ID, issuer/org, title, original
URL, **CNINFO-reported published_at**, capture clocks, HTTP/MIME, length, SHA256,
raw path and request ID. Source-reported timestamps are not independently verified
intraday availability. Missing/invalid publication clocks remain unqualified in
raw response bytes and block a complete package; no date is filled. Capture time
is not publication time. There is **no Research cutoff** in this acquisition.

Raw PDFs are the originals. This v0 does not extract text; signature/MIME checks
only identify a PDF container, not valid Research claims or semantic completeness.
A later deterministic text projection must retain raw PDFs and separate page
indices and extraction provenance. Reading segment/cash/capital sufficiency
belongs to later preflight/Research, not this selector.

The verifier hashes all files, checks the exact file/journal inventory, and
replays the original issuer resolver, pagination and selection from retained
responses. It does not request the network or create Evidence/Funnel outputs.
`OFFLINE_VERIFICATION_PASS` may coexist with `SOURCE_CAPTURE_INCOMPLETE`: intact
failure evidence is not successful acquisition. Damaged bytes, mismatched source
identity, missing journal, changed derived outcome, extra files or symlinks reject.
This is integrity/consistency verification, not source truth or an HTTP signature.

```sh
python -m decision_kernel.runtime.sanhua_source_acquisition capture <NEW_DIRECTORY>
python -m decision_kernel.runtime.sanhua_source_acquisition verify <CAPTURE_DIRECTORY>
```

A real attempt must use the fixed public transport; injected responses are marked
SYNTHETIC_TEST_ONLY. The capture refuses an existing directory. The dedicated one-shot workflow is triggered only by addition of
`.github/source-acquisition/sanhua-v0-20260909.json` on main. It requires attempt 1,
exact approved parent main `15b74321c6d152b2984c11b556bbfb336c279509`, and proves the
request did not exist at that parent. Other main pushes and changes to the capture
code do not initiate acquisition. Editing the request later fails the first-add
and parent checks. This is the single Human-requested capture on this legitimate
engineering merge, not a scheduler or an empty push to manufacture a sample.
There is no automatic recovery, alternate-run retry, workflow dispatch or global
lock. No old source workflow is triggered, and no existing trigger is modified.

## Actual acceptance and retention

Engineering CI proves deterministic behavior with synthetic transports; it does
not prove current source accessibility. One real run must separately establish
issuer resolution, complete bounded inventory, H1 original, IR acquisition or an
explicit IR gap, exact retained bytes and offline verification. If a required
source is missing, **SOURCE ACQUISITION REALITY TEST = INCOMPLETE**. Do not switch
company, extend the window/budget, change selectors, or label it EXECUTION_GAP.

Artifacts are retained for **90 days**, not permanent backups. Downloaded verified
copies retain the same raw package for offline review. An artifact ID/hash is not
a backup, and an expired artifact without a retained copy is SOURCE_UNAVAILABLE.
No code-main commit is made for each capture; the source package is not a market
restore bundle or a Research registry. Any remote retained copy must keep exact
run/artifact/hash provenance and its own retention limitations.

After successful acquisition, future Research still needs **new** accessibility
preflight and #291 full admission with a separately frozen execution/input/cutoff/
budget. Old preflight is never rewritten as PASS. No research launch, normal/
adversarial pair, Deep, Odds, Human write-back or attention is part of this batch.
