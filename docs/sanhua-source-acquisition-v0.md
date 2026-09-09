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
  anchored by publication on August 27/28, including an explicitly linked revised
  title in the complete window. Publication is not the meeting/activity date;
  acquisition does not interpret the meeting contents or economics.
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

Qualify both the `2026年半年度报告` title family and the declared IR family
before any primary PDF request, as specified below. Only returned `adjunctUrl` originals matching
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

## Document version qualification (pure, before PDF download)

`runtime/sanhua_document_versions.py` receives only the already complete,
identity/date-qualified inventory. It performs no HTTP, Evidence or Research.
It distinguishes `FULL_BODY`, `SUMMARY`, `REVISED_OR_CORRECTED_BODY`,
`LANGUAGE_OR_MARKET_VARIANT`, `CORRECTION_NOTICE_ONLY`,
`CANCELLATION_NOTICE_ONLY` and `OTHER`. Full-width parentheses and the exact
issuer prefix are normalized only in the derived classification; raw titles,
publication clocks, IDs and returned original locators remain unchanged.

A single ordinary body is selected. One explicit revised/corrected/updated body
in the same title family supersedes at most one ordinary body, provided its
reported publication does not predate that ordinary body. Multiple ordinary
bodies or multiple revised bodies remain `REPORT_VERSION_AMBIGUOUS`, even when
one has a later timestamp. There is no score, shortest-title, ID-size or
latest-date tie breaker. Summary-only is `FORMAL_REPORT_MISSING`.

A related correction/clarification/cancellation notice does not establish a
notice-to-body relationship. It blocks the family with
`VERSION_RELATION_UNRESOLVED`, rather than leaving the old body current. An
unscoped cancellation notice likewise cannot be guessed away. Unsupported
revision labels require review; they are not silently treated as ordinary full
bodies. Language/market variants do not become second current A-share bodies.

IR uses the same rules, with `RELEVANT_IR_AMBIGUOUS` and
`IR_VERSION_RELATION_UNRESOLVED`. The Aug27/28 publication scope anchors the
requested lead; the complete captured inventory is checked for later versions.
A revision must match the normalized target title family, including any date
stated in that title. A differently titled revision is not silently assumed to
refer to the target. Multiple target families or indistinguishable generic IR
bodies require review. No IR contents or robot relevance are interpreted here;
a unique selected title still does not certify the target activity.

Both family decisions finish before the **first** primary PDF request. Ambiguity
or unresolved relations in either family therefore result in zero primary PDF
requests. Only a genuinely missing IR retains the prior behavior of allowing
an unambiguous H1 download while leaving the whole package incomplete. If a
selected revision download fails, the original is not used as fallback.

`capture.json.outcome.version_qualification` records each classification,
selection/refusal reason and `CURRENT`/`SUPERSEDED`/unresolved disposition.
The existing offline reconstruction calls this same pure layer on retained raw
responses. Changing a disposition and rehashing the manifest cannot make it
pass replay. Decision-record ordering by ID is solely for reproducible output,
never for selection. These are Harness projections, not a Kernel schema change.

Implementation and tests are independently written from the approved behavior.
The external diligence reference is `ykkai-w/Disclosure-Evidence-Pipeline`,
commit `f1a708a0a3294823a4d056ff12d9e4aab6e4de6d` (MIT), specifically
`classification.py`, `versioning.py` and `test_versioning.py`. No upstream source
is vendored or installed. In particular, this layer does not copy that annual
selector's general latest-day rule, infer cancellation targets, or treat annual
report rules as already qualified for H1/IR.

This amendment changes only version qualification, its capture call site and
tests/documentation. The transport, plan/request budgets, workflow and one-time
source request are unchanged. A new-head PR CI must actually execute and pass
before merge is reconsidered; no Re-run or real acquisition is part of this
amendment's acceptance. No local synthetic result substitutes for that CI.

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

## Relation-only follow-up: one separate official source-channel test

#293 merged at `b71ff68984a243f3aa397819336b7aaf7e586515`. Its real fulltext
run `34316364031`, artifact `10090204888`, retained the formal H1 original but
reported `RELEVANT_IR_MISSING_FROM_BOUNDED_INVENTORY`. That accepted history and
its plan/hash remain unchanged; it is not rerun or relabelled as relation.

The existing runtime now accepts only two fixed `--channel` values. The default
`fulltext` plan is byte-identical to the old frozen request. `relation` changes
only the official query form's `tabName`, selects at most one IR and applies a
five-request ceiling: issuer map once, up to three pages of 30, one IR PDF.
Issuer, dates (2026-08-01..2026-09-09), exact public HTTPS endpoint, 8MiB/body,
48MiB total, zero retries/redirects/credentials, and all original page/identity/
time checks are retained. There is no second HTTP client, journal, hash layer,
verifier, source database or version classifier.

The parameter reference is `akfamily/akshare` at
`8e95744b79ae22326308ccd2b4e62650c5b53c55`,
`akshare/stock_feature/stock_disclosure_cninfo.py`, function
`stock_zh_a_disclosure_relation_cninfo`. Only the already-reviewed official
relation form semantics are adopted. AKShare is neither installed nor vendored;
its HTTP scheme, unbounded pagination and repeated first-page request are not
adopted. This code starts with the accepted local relation draft, not a redesign.

Complete relation inventory precedes the existing IR version qualification and
the first PDF. H1 rows can remain in the raw inventory but are never selected or
downloaded. Ambiguity/unresolved relations stop before PDF requests. A complete
inventory without qualified IR is `SOURCE_CAPTURE_INCOMPLETE` with
`RELEVANT_IR_MISSING_FROM_RELATION_INVENTORY`. It does not establish absence from
other official channels. A selected IR title/container does not certify the
activity, robotics/thermal claims, source sufficiency or Research admission.

```sh
python -m decision_kernel.runtime.sanhua_source_acquisition capture <NEW_DIRECTORY> --channel relation
python -m decision_kernel.runtime.sanhua_source_acquisition verify <CAPTURE_DIRECTORY> --channel relation
```

Verification must explicitly request the matching channel. The original
`verify(old_directory)` remains fulltext; no automatic cross-channel fallback
or changed historical plan hash. The new workflow first retrieves the **saved**
GitHub artifact `10090204888`, verifies its exact 1008406-byte ZIP SHA256
`0c67714a58dc46bbf9fdd391ff44c29ff7ebc6821f9d449630446d8e6a17dfd0`, and calls the
installed new verifier. Its result must equal the archived verification.json,
including the old incomplete outcome and zero replay network calls. All old
file hashes must remain unchanged. This is a retained-artifact read, not an H1
source acquisition. Only the small compatibility receipt enters the new package;
the old H1 bytes keep their original lineage. Artifact unavailable/corrupt or
compatibility failure prevents the source step; no similar/older package fallback.

One frozen request, `.github/source-acquisition/sanhua-relation-v0-20260909.json`,
is activated only by its first addition on a legitimate reviewed main merge.
The dedicated workflow requires attempt 1 and exact previous main
`b71ff68984a243f3aa397819336b7aaf7e586515`. No schedule or workflow_dispatch.
Main must be reread before merge; a changed parent means stop, not relax the guard.
The old fulltext request/workflow and other workflows are unmodified. Permissions
are contents:read plus actions:read solely for retrieving the saved artifact;
the built-in token is scoped to that step and never sent to CNINFO.

The separate relation artifact retains invocation, plan, raw response/IR bytes,
request journal, actual capture outcome, relation verification and old-fulltext
compatibility receipt for 90 days. Capture failure stays failure even when
`OFFLINE_VERIFICATION_PASS`; no new channel, retry or second company is attempted.
Engineering CI, old-package compatibility, real relation capture and remote
readback are separate acceptance levels. Stop after this one source-channel test;
any later source preflight/admission/Research requires a new authorized batch.
