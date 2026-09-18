# Independent concept source v1

Status: IMPLEMENTATION; FIRST LIVE CAPTURE AND COMPANY-READING INTEGRATION NOT YET ACCEPTED.
Continues #297/5725898629, #364 and #351 HOME-14 under Human Radar-r3 authorization.
Reuse Decision: REUSE + THIN_ADAPTER. Investment Authority = NONE.

## Why this slice exists

The existing theme probe accepts explicit manual themes or literal mentions in
retained sources, and its live CLI uses an old frozen Sector bootstrap. That is
not independent current concept discovery. Keep that historical contract intact.
This source obtains its own calendar/benchmark/catalogs; no Sector homepage,
Industry strength gate, prior Research or caller-selected stock/theme is required.
It does not replace the completed #425/#427 pools/readers or #432 Stock executor.

Reuse existing calendar/index/member normalizers, `theme_radar_probe._record` and
`_path_observation` (5/20/60-day excess, persistence and acceleration), membership
overlap, fixed-host Requests session/status, JSON/byte safety, create-only I/O,
canonical identity and native GitHub Actions/artifacts. No new dependencies,
provider/taxonomy/queue/scheduler/Research engine or scoring system. Previously
reviewed EasyStock is product prior art, not copied code or a licensed dependency.

Official upstream source contract: HiThink-Tech/Financial-API at
`0a629aba2b3977a419f7c4330972d2047c8612da`, `docs/api/index/`:
- `catalog-ths-index-list.md`, blob `03cbdab488365d9232213d95255a1bcb553dd252`;
- `prices-snapshot.md`, blob `51bfacf9fcd1da0a41092d53fef6f0dec8439e04`;
- `prices-historical.md`, blob `87f5e4f9dfb41be73be62daf696db9412356698d`;
- `constituents-ths-stock-list.md`, blob `728baf0459ff866087e826aaf20c960a55903dda`.
These establish documented routes, not live account access or exchange completeness.

## Complete snapshots; deliberately bounded multiday detail

A fresh main attempt accepts an explicit SAME-DAY completed session and starts
at or after 15:30 Asia/Shanghai. It uses the provider calendar, not weekdays, and
binds 126 completed sessions to the original benchmark history. No historical
date paired with current intraday quotes, no next-day carry or automatic fallback.
Actual requests/receipts are monotone, same-day and within 30 minutes; the next
request is refused before transport once that window expires or reverses.

It obtains the complete `cn_concept` and separate industry catalogs, validates
exact identities and rejects overlaps. Prefixes alone do not establish taxonomy.
All catalog concepts receive explicit batch snapshots (up to 1024 per request,
4096 concepts maximum). Missing/duplicate/extra snapshot identities fail closed;
unsupported catalog size is not silently truncated. Industry ranks are untouched.
Each chunk keeps its own clock; this is not an atomic snapshot. All concept
snapshots have benchmark-bound session context, not individually proven history.

Only THREE detail slots are used initially, reusing the old theme budget. Select
largest absolute same-day index return, tie by exact code; keep declines too.
This is an explicit ACQUISITION EXPERIMENT, not a validated discovery threshold,
research priority, investment score, complete multiday concept ranking or mature
trend radar. It is biased toward same-day movement and may miss a quietly strong
ongoing theme. All other concepts remain DEFERRED_NOT_ACQUIRED, not rejected or
no opportunity. Broader continuous/multiday selection is still required by HOME-14.

Each selected concept gets its own exact 126-session history and current members.
Price/volume/turnover identity is checked against its snapshot; benchmark anchoring
uses original price identity without a new unused volume gate. Existing theme math
is reused without ranking the small subset against the full universe. A history
with gaps cannot fabricate returns or a trend start. Known per-detail data absence
is isolated; shared/rate/authentication/transport/clock failures stop the attempt.
History and membership statuses remain separate so one unavailable history does
not erase already-observable member companies. No retries or substitute sources.

The original 15-request ceiling covers calendar + two catalogs + up to five
snapshot chunks + benchmark history + six detail requests. Existing 20-second
spacing, 8MiB per body and 32MiB retained capture bound remain explicit. No next
batch or recurring run is authorized by a successful capture or merged PR.

## Companies, provenance and reuse by the existing reading

Every acquired current member is retained, joined only by exact security code,
with all concept origins and any differing source names. Pairwise membership
intersection/union is observable, not independent confirmation. Current members
are not historical memberships or evidence of business exposure. Member price
breadth, economic benefit, source publication time and first-vintage historical
availability remain unknown/unestablished. Midnight market keys do not create PIT.
Company records say Stock/Pre/Quick NOT_EXECUTED_BY_THIS_SOURCE, not that the
repository has never researched the company. No automatic Research/Odds/Action.

Output `observation.json` and `index.html` retain all concepts, selected path
metrics, members, overlaps, source references and gaps. Source text is escaped;
HTML has no scripts or external assets. This SOURCE slice is NOT yet attached to
normal `details/radar/company-reading.json` or Brief. Reuse #427 for that later
connection after one actual original source has been inspected; do not introduce
a second company registry or pretend the existing 83 companies include concepts.

## Capture, replay, failure and execution

`.github/workflows/radar-concept-source.yml` is manual-only, read-only repository
permission, exact reviewed code/main/attempt1. Only acquisition sees the existing
provider secret. Replay must not receive credentials. Safe original JSON bytes,
not reformatted copies, are stored with each request clock. A normal source
capture may be PARTIAL with explicit per-theme detail gaps; that is not full
trend coverage. A failed/unsealed attempt never becomes a successful empty scan.

The original verifier checks implementation fingerprints, complete file scope,
raw bytes, actual clocks and original request sequence; it rebuilds all successful
or partial JSON/HTML without network. Rehashed derived-output tampering is still
rejected. Transport/unsafe failures only certify their retained subset, not the
remote cause. Native exact-code Git archive/tree accompanies the artifact for
offline reproduction, not production restore. Artifacts expire after 30 days;
fixed Git reading integration/retention is a separate unfinished acceptance.

Live execution needs a separately reconciled fresh dispatch on a then-current
reviewed main, successful full CI, valid completed-day clock and no equivalent
attempt. Do not Re-run, blindly reuse 9/17, change triggers, or move credentials to
work around connector limitations. A 204 without run ID requires read-only
reconciliation before any further write. No daily activation is introduced.

## Acceptance remains layered

Tests use explicitly synthetic dates/prices/companies with network blocked. They
cover full catalog/chunk/request bounds, no silent truncation, independent entry,
negative movers, old math reuse, missing history/members, shared fatal failures,
exact clocks/identity, overlap/name preservation, escaped labels, original-byte
capture/replay, rehashed tampering, create-only/symlink and workflow/secret scope.
Local archived-source focused tests do not replace full exact-head PR CI,
independent main CI/normal publication, first live original-byte acceptance or
Human usefulness. Actual receipts belong in #297/#364/#351, not prefilled here.

Still open: first live concept capture, normal fixed-company-reading/Brief
integration, continuous all-concept multiday state, member breadth and leadership,
real Stock page execution, existing Pre/necessary Quick, remaining Smart Money
dimensions, and the old Stock policy/reader mismatch. None is closed by this slice.
