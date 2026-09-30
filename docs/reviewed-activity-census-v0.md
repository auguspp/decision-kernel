# Reviewed institutional activity census v0

## Purpose and reuse

Original C1 requires understanding institutional activity, not merely counting
provider rows. Scope is recorded in [#504/5913679388](https://github.com/auguspp/decision-kernel/issues/504#issuecomment-5913679388).
This is an offline supplied-input consumer. It adds no provider, network request,
model, scheduler, Watch membership, Research acceptance or investment authority.
It does not establish a complete census of an issuer's activities in a window.

**Reuse Decision: THIN_ADAPTER.** The existing
[institutional context](institutional-context.md) owns bounded capture, replay,
raw-row deduplication, provider scope and unknown source qualifications. Its
`project` validates the supplied original capture and raw files again, without
source calls. Exact source identity, record-local bindings, canonical hashing,
bounded files and create-only CLI reuse existing modules. Counts do not masquerade
as money in `research_comparison`.

The inspected AKShare/Vibe/EasyStock implementations and their pinned references
in the institutional-context contract provide endpoint/field and acquisition
patterns, not reviewed event/entity equivalence. Standard sets/dictionaries are
sufficient for this bounded calculation; no new dependency or entity-resolution
platform. This is not a historical executor revival or a source-discovery route.

## Selected evidence and explicit review

The input identifies one issuer, review clock, inclusive window and
`EVENT_DATE` or `DISCLOSURE_DATE` inclusion basis. Coverage is always
`SELECTED_EVIDENCE_ONLY`. `inventory_complete` is a reviewed declaration about
that selected set, never all issuer disclosures or all events in the window.

Sources retain immutable Git ref/path/blob, SHA256, bytecount, explicit
qualification and known/unknown publication/acquisition clocks. Supplied wrong
bytes fail identity validation; missing bytes leave dependent counts unknown.
A capture cannot finish after the review clock. Event/date corrections do not
backdate knowledge, and retrieval clocks do not establish historical availability.

Every record has one disposition:
- SELECTED: assigned to exactly one reviewed event and selected variant
- SUPERSEDED: directly references a selected same-event successor, preserving its
  original bytes, variant and correction rationale; cycles/chains through an
  unresolved successor cannot qualify
- EXCLUDED: currently only a source-bound date outside the selected window,
  using the same inclusion basis; an arbitrary exclusion cannot hide a missing row
- UNRESOLVED or UNAVAILABLE: preserves a blocker, not a zero

For provider captures, the inventoried row hashes must equal the existing replay's
complete deduplicated returned-row inventory. Row identity uses the original
replay and its source locations, not a second JSON numeric normalization.
Provider bodies cannot bypass replay by being called retained references.

An input is bounded to 16 sources, 128 records, 64 events and 128 entities.
JSON source records are flat objects, with primitive values or scalar arrays.
Bindings are direct members/scalar-array slots within the record, not fields
borrowed from another event or a response-wide container. Exact retained text
excerpts can support explicitly reviewed references. Their interpretation remains
a reviewed assertion: byte equality does not prove economic or identity truth.

## Event, person, institution and roster semantics

Event keys and equivalence notes are explicit reviewed assignments. An original
event number is retained when available. Date alone is not event identity.
Event and disclosure dates are separate; provider date prefixes preserve their
date-only qualification. The chosen variant and its resolution rationale are
retained, and different active variants cannot be silently unioned.

Entities are institutions or people. Local keys cannot duplicate the same
reviewed `(kind, namespace, identity_value)`. Source provider IDs require exact
bindings. Reviewed equivalence retains its rationale; a resolved person also
requires non-name discriminating evidence. A bare repeated name is not automatic
proof of one person. Explicitly unresolved visitor or unknown-role identities block their population
totals. These guards validate the supplied assignments, not real-world identity.

Attendance edges bind names and role evidence to an inventoried record of that
event. VISITOR, HOST and UNKNOWN are distinct. Hosts do not enter visiting
institution/person counts. An explicit source HOST cannot be relabelled VISITOR.
Same person at two events means one distinct person and two participant-event
attendances; two records or copies are not automatically two events.

Institution and person roster completeness are separate COMPLETE/PARTIAL/UNKNOWN
declarations. COMPLETE needs a source-bound statement and reviewed rationale,
not just an empty array or boolean. A complete event set with unknown rosters can
have an event total while institution/person/attendance totals remain null.
An unresolved person identity or role never silently becomes a visiting person.

## Output and qualification

Four dimensions are reported independently:
1. Reviewed unique events
2. Reviewed distinct visiting institutions
3. Reviewed distinct visiting participants
4. Participant-event attendances

Each exposes `observed_subset`, `selected_set_total`, qualification and blockers.
An observed zero means zero explicitly qualified identities in the selected
observations, not zero people actually attended. Total stays null when the
inventory, source, event resolution, role, identity or relevant roster is missing.
`issuer_window_total` is always null. No institutional-interest score, consensus,
cross-window growth comparison or inferred aggregate attendance is added.

Reports preserve reviewed record/event declarations alongside derived statuses,
source locators and hash, so corrections, variants, role and completeness decisions
remain auditable. Source-reported aggregate attendance is not substituted for
distinct identities. The original input remains part of the retained archive.

## Real boundaries and engineering positives

The retained #504 activity request is HTTP200 but contains
`success=false`, `result=null`, `code=9201`. Existing replay classifies it as
`RETAINED_BODY_NOT_QUALIFIED`. All census totals remain UNKNOWN, not zero.

The retained Xingsen R2 reconciliation corrects IR event `2026-05-001` from a
mistaken May11 mirror date to May8, 15:00–16:00. This supports one reviewed
referenced event in that explicitly selected paragraph, without an institution
or person roster. It is not a May-wide count, does not belong to the separate
August11–September24 provider window, and is not original disclosure custody.
Later exact copies of the paragraph are not independent events or evidence.

These are limited real boundary consumers. Positive multi-event/identity/roster
examples are explicitly synthetic engineering tests. A qualified real positive
institutional census and its later research use are still separate obligations.

## Consumption and finite acceptance

Use current qualified code, an externally pinned SHA256 of the selected input,
and explicit `--source ID=LOCAL_FILE` arguments:

`python -m decision_kernel.runtime.reviewed_activity_census INPUT --sha256 HASH --source ID=FILE --output ABSENT_DIRECTORY`

The CLI emits `census.json` and `census.md`, never overwrites an existing output,
never executes retained source instructions and makes no network/model call.
Normal fixed-R archive recovery remains the existing `research_archive` route.
The source capture's derived context/summary can separately be checked by its
original replay; this census does not become the capture owner.

Acceptance separates counterexample tests, real boundary replay, original
source qualification, exact-head PR/main checks, publication, independent fixed-R
recovery and subsequent research use. This document alone proves none of those
execution stages. No full C1/C2 completion, Human acceptance or investment action
is claimed. Extensions and retirement belong to the existing C task, preserving
historical evidence without a new permanent census service.
