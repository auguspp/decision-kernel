# Concept members: compare the already-checked Stock subset

Owned by [#645](https://github.com/auguspp/decision-kernel/issues/645), continuing
#647 members and #648 long paths. This is an optional Workbench read consumer,
not a new source, qualification algorithm, full-member rank or canonical state.

Selecting a saved TDX concept now exposes how many of its actual members have a
saved Stock disposition. All original dispositions survive, including a high
20-session return whose 5-session condition failed, unavailable prices, and
members absent from the saved check scope. Existing company reading remains the
only drill-down action; no Research, Watch, order or investment authority is added.

The consumer lazily reads exactly the same R's registered
`lanes.stock.last_qualified_result.details['reading/stock-reading.json']` through
`Reading.readFile`. It checks the saved projection identity, full observation set,
root dispositions/counts, original policy, price convention and declared windows.
The existing byte/SHA limit and native Web Crypto are not bypassed. This is not
re-execution of provider admission or canonical hashing in JavaScript.

Only the actually checked price subset with equal member/Stock dates and matching
20-session start/end windows is ordered by that one original raw close return.
Decimal digits are compared exactly with native BigInt; display rounding does not
choose order. No composite score, positive-only filter, top-three cutoff or new
eligibility gate. Other periods, original market benchmark and excess are separate
saved fields. Missing 60-session values remain unknown. An earlier/different Stock
date is visible historical reference, not a current-member rank. The entire source
member list remains independently available in its original order.

Original `current_origins.direction_sources` are joined only by the same security,
with exact retained member/sector codes and separate 881/884 families. This is a
traceable TDX-member-to-HiThink-origin relationship, NOT proof of equal taxonomies,
index correlation, all-sector overlap, business benefit or complete cross-source
trend corroboration. No source names are used as an identity mapping.

One in-memory promise belongs to one page/R; opening other concepts does not
retry a rejected read. A late read checks the original active-page guard plus
whether its target still belongs to the selected detail. Missing/unreadable Stock
body affects only this optional comparison, never the original members, long
paths, calendar, Stock panel or company reader. No file is fetched for legacy R
without the exact descriptor.

## Reuse, verification and exit

Reuse: existing Stock reading/TDX membership/Reading/displayDecimal/text DOM and
isolated browser harness. Retained prior art starts in
[radar-stock-discovery-pool-v1](radar-stock-discovery-pool-v1.md); current EasyStock
`bd47fc3db1d366c69612b4ed36efe68c2a133268` radar.go confirms the provider/fallback
and fused-theme boundary is still distinct. Borrow readable direction/member
navigation, not its runtime, source calls, fusion semantics or code.
Official primitives: [BigInt](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/BigInt)
and [Array.sort](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/sort).
No package, backend projection, external quote request or scheduler is added.

The existing `workbench/browser/smoke.py` registers six scoped scenarios from
`concept_stock.py`: checked-subset reading/company drill-down, same-length tamper
and no retry, old-R lateness, old-concept lateness, differing dates, and legacy
absence. Each uses the original offline harness at desktop and narrow widths;
all prior scenarios remain. Pure Node tests cover identity/coverage, exact decimal
order, preserved non-qualified rows, explicit unknowns and lazy failure isolation.
Synthetic scenes prove browser behavior, not source truth or natural delivery.

On retirement remove concept-stock.mjs, its one Concept-page import/call, its Node
tests, the six browser scenarios/import and this note together. Keep shared readers,
original Stock qualification, source/member history and all prior failure records.
Full-member leading ranks, natural long-history/Brief consumption, complete
cross-source corroboration, Sites/phone and overall #645 acceptance remain separate.

The existing `test_workbench_web.py` wrapper explicitly runs both Concept Node test files and syntax-checks both consumers; this also closes the previous omission of `concept-members.test.mjs` from its list. Backend test-identity counts do not count every nested Node case separately. Exact-head CI/browser, pinned-data checks, source adoption and actual Human use remain separate in #645.
