# Smart Money continuity and first production corrections

2026-09-26. Human explicitly continues complete delivery (#351/5841579235 and
5842627678). This is a follow-up to #586/#587, not a second Radar or a claim that
all public inputs and research consumption have already passed.

## Reconcile and reuse

The user-supplied continuation package was hashed before use. Its nine-path
runtime/test patch was three-way applied to main ce940c5be23d3de065a89d56eba294afc5853075.
Keep #587 exact canonical-JSON binding and append-only Markdown; preserve all
#588 workbench changes. Internal calendar, Requests, native Git histories,
existing publisher and source-family contracts are reused. The previous
AKShare/Eastmoney, HiThink/FTShare, HKEX and pypdf review remains applicable;
this change corrects demonstrated field/identity/continuity faults, with no new
provider, subscription, dynamic connector, database or general scheduler.

## Concrete production evidence

The first production source is 36213198566/attempt1, original code325318113711c79ec880bbcb99c5cc346ad6c24c,
artifact10896403657 (17647490 bytes; SHA256
246843ac886cdc055ec37950f01a9dca6a6c5ee696bc1ae887ff4bc57947bc52).
Its 204 original requests and capture checkpoint are preserved. This code can
replay that original without new requests or rewriting its old plan/selection.

Actual findings: anonymous institution labels repeat for distinct reported seats;
whole-market holder pages also contain 160 NQ rows outside this SH/SZ/BJ reader;
some holder codes represent different named accounts, and some missing codes
have equal names at different ranks; related executive positions produce multiple
context rows. Holder-change and buyback endpoints returned500 rows even when
1000 was requested. An activity response reported code9701/server busy. HKEX
March requests returned June holdings and remain rejected, not relabelled March.

Corrections keep anonymous seat rows distinct and prohibit aggregation across
sides, retain named holder account/rank rows without certifying people, count
NQ scope exclusions, retain executive relation context, and use explicit request
revision2 with500 for three bounded Eastmoney disclosure families. Revision1
requests remain verifiable unchanged. Provider9701 is an explicit bounded
transient, not a guessed network diagnosis; authentication/rate policy stops stay.

## Continuity and recovery

A failed calendar cannot advance enumeration or lose the earliest missing date.
Complete corrected snapshots can retire current-display membership but do not
delete historical R or infer sale/zero. Partial activity cannot claim complete
attention acceleration. An unconsumed exact source run is recovered before a
new acquisition; a later skip cannot hide it. Same-source parser corrections
are marked reinterpretation, not new economic events. Old request/PDF selection
contracts remain explicit when replayed.

An explicit repair-pending dispatch requires current reviewed SHA and prior
saved state, respects the daily attempt ceiling and policy stops, and reuses
completed partitions instead of downloading both full quarters again. New
uncollected dates are never treated as previously complete. Missing historic
HKEX periods stay pending. This operation is not arbitrary rerun permission.

## Acceptance and limits

Small regressions use synthetic actors/amounts; the original204-request replay
is a separate large source check. Source/table completeness, identity ambiguity,
publication and actual Quick consumption remain separate. The pre-existing
broad name lookup is not a certified famous-investor identity service; raw
brokerage seats are not yet reliably mapped to particular hot-money people.
No automated Full, investment decision, Odds, Watch or trade is introduced.

Normal exact-head full CI and original-artifact verification precede merge;
main CI, normal publisher and exact-R readback follow. A later targeted source
capture must separately validate the corrected page requests. Temporary patch
assembly is confined to its expiring work branch and excluded from the product
PR; remove it after use. Retire changed source-specific tests with the source,
preserve shared readers and all historical failures/archives.

## Public protocol delta verified after the full-capture replay

The 90-day participant-detail endpoint returns 80,933 rows at its supported 50-row
page size; asking 500/1000 returns business9701, not a permission denial. The
existing AKShare event-summary protocol RPT_ORG_SURVEYNEW returns 5,586 disclosed
activity groups in 12 pages at500. Revision2 uses that distinct event scope,
retains its reported institution-entry count and representative label, and never
claims a full named participant roster or independently certified event count.
Legacy detail bodies keep their original interpretation. Source/page counts and
row-level gaps remain separate; full participant coverage is still incomplete.

The same public HKEX form with session continuity returned December31 for a
March31 query, but March31 for an April30 query. The search date is an as-of
availability date, not the target holdings period. New requests retain both, use
a deterministic target+30-day query bounded by capture date, and still require
the returned holdings heading to equal the target quarter. No date is relabelled
and the extra query date is not claimed as publication date. The public session
is closed after collection, cookies are never persisted, and other providers'
credentials remain isolated. Old form requests are replayed unchanged.

Evidence: preparation36215930160, artifact10897492295, SHA256
46bd280bc0a45bf94505079a0806665ed7431363a0b92cdd89b507f571fb2e57;
original public HKEX search_form.js in artifact10897636240. The JS itself only
validates the date; it was read, not executed. Formal source recovery follows
normal CI/merge. No additional source provider or standing workload is created.
