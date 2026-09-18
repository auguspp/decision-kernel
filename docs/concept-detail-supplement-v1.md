# Concept detail supplement v1

Continues Radar-r3 and #297/5730594181 after #437. Reuse Decision: REUSE +
THIN_ADAPTER. The change is an executable source entry, not another map.

## Purpose and reuse

A qualified primary concept capture already has the complete catalogue,
same-session snapshots, calendar and benchmark history. Replaying that exact
archive lets a supplementary batch request only the missing concept histories
and current memberships. Original normalizers, history/snapshot comparison,
126-session window, path maths, fixed-host transport, HTTP diagnostics and
no-retry rules are reused. The original concept source/capture modules and their
implementation fingerprints are unchanged, so historical replay remains valid.

`radar-concept-detail.yml` is a separate, manual-only execution boundary and
artifact name. It is not a second discovery registry, scheduler or source
provider. It cannot replace or poison the primary concept workflow's latest-run
selection. It does not modify publisher listeners or the current company report.

## Deterministic selection and time

Inputs: reviewed current `code-sha`, exact latest primary `source-run-id`, and an
internal `offset` (default0, multiple of3). The full never-attempted universe is
recomputed from the original source and ordered by exact concept identity.
At most3 are selected and at most6 market requests occur. Quiet/negative concepts
are eligible; daily rank, supplied company lists and AI research priority play
no part. Base attempted-but-incomplete details are not silently retried.

All unselected codes remain explicit, including earlier offsets; an offset is
not proof earlier batches ran. No automatic next page or cumulative coverage
claim is made. Users are not expected to operate129 batches. Continuous selection
and coverage remain follow-on work, not implied by this bounded execution seam.

The actual source run must be the latest of the bounded main query, completed
success/attempt1, correct workflow/repository/code, with a unique unexpired
artifact whose exact bytes/digest/run binding pass the original verifier.
Original failed or expired roots are not replaced by older success or by an
unauthenticated projection. Only data is unpacked; archived TAR/scripts are never
executed. GitHub prepare uses existing transport, at most6 GitHub API calls and
no market credentials. Market capture has no explicit GitHub token.

Acquisition requires the primary source's own completed market day after15:30,
base receipt before new requests, and all responses inside the original30-minute
same-day window. No weekend/holiday/next-session inference. New historical close,
previous close, volume and turnover must still match the original same-day
snapshot exactly. A later revision/mismatch stays a gap, not a repaired old bar.
Each baseline and new observation clock remains separately inspectable.

## Output and failure

The new artifact retains `payload/base.zip`, original source metadata, source-
derived plan, exact request/response bytes, supplement capture and observation.
The original archive is unchanged. Supplementary membership overlap is computed
against actually acquired original sets and within the new batch. A new company
count is only set coverage; it does not establish business exposure, broad
participation, an independent signal, Research admission or investment value.

Provider detail-unavailable codes and data qualification gaps remain explicit;
authentication/rate/unknown business failure stops the attempt. Transport uses
#434 finite diagnostics without leaking body/header/URL/exception text. Failed
capture replay proves saved structure only, not the remote cause. Successful
replay rebuilds exact requests, calculations and output with zero network.

Original raw limits apply:32MiB archive,32MiB retained supplement including its
base,8MiB JSON bodies, no arbitrary routes or redirects. New capture is create-
only; source and supplement workflow attempt1/main gates remain. No Re-run,
automatic retry, automatic research, Stock, Odds or Action follows this entry.

## Acceptance and remaining scope

Code/CI, first live supplementary capture, integration of that capture into the
existing reading, continuous coverage and Human usefulness are separate gates.
Do not claim new real histories merely because tests execute synthetic requests.
The primary source's original3 histories and387 missing details stay historical
facts. Fresh source input or a new single-run authorization must satisfy its
actual clocks; this document is not a standing dispatch permission.

External reuse checked2026-09-18: GitHub official Actions artifacts REST API
(https://docs.github.com/en/rest/actions/artifacts) and script injection guidance
(https://docs.github.com/en/actions/concepts/security/script-injections).
Inputs go through quoted environment variables, never shell interpolation.
