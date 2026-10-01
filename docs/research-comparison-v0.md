# Reviewed longitudinal comparison v0

## Need, ownership and scope

C1 originally requires more than retaining documents: a later consumer must distinguish changed financial facts, newly obtained old evidence, revised research interpretation and unchecked claims. #672 only proved a bounded synopsis loop. Scope/selection is retained at [#297/5910147844](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5910147844).

`research_comparison` is an **offline thin consumer** of explicitly reviewed inputs and supplied exact source bytes. It is not an autonomous analyst, filing parser, latest-version resolver, new domain state owner, source provider or economic admission gate. `RETAINED_FILES`, existing on-demand registry, fixed-R archive recovery and company re-entry keep their responsibilities. `RESEARCH_PROGRESS` strict inventory is unchanged. The existing re-entry reader still does not itself perform semantic comparisons.

## Input and output

Input identifies one subject/question and predecessor, explicit review clock, optional analysis cutoff, at most16 immutable source descriptors,64 observations and32 comparisons. Sources preserve commit/path/blob/SHA256/byte count, declared qualification and known/unknown publication and acquisition clocks. Subject attribution and economic source qualification are reviewed declarations, not facts a hash can certify. Late retrieval is not historical knowledge proof; unknown clocks stay unknown. Publication later than an explicit cutoff is rejected, as are future review/source-clock inconsistencies.

Observations bind an exact JSON pointer or literal text anchor to a decimal string/claim, or explicit UNKNOWN/NOT_CHECKED. JSON numerical lexemes are parsed with Decimal; saved float-derived approximation tails are not executed or rewritten. Text numbers must occur as complete, unambiguous numeric tokens; exponents, Unicode signs and accounting parentheses require a separately reviewed unambiguous representation rather than substring matching. Declared currency, scale, metric, attribution scope, stock/flow dates, restatement and basis are retained. Supported money scales are1,10,000,1,000,000,100,000,000 and1,000,000,000; this is not a general dimensional-analysis system.

Comparisons explicitly classify PERIOD_CHANGE, SOURCE_REVISION, RESEARCH_CORRECTION, EVIDENCE_COVERAGE_CHANGE, CHECKED_UNCHANGED, NOT_CHECKED, INCOMPARABLE, CASH_DIAGNOSTIC or DERIVED_QUARTER. Narrow operations are new−old, signed money sum, monetary ratio, same-year H1−Q1, coverage change and claim comparison. There is no formula language, DAG, chaining, script execution or automatic selection. The classification, economic interpretation, alternatives/challenge disposition and limitations remain the researcher's reviewed declarations. Numerical checks do not certify them.

Basis checks prevent issuer/currency/scope/restatement mismatch, stock/flow mixing, incompatible seasonal windows/year spans and nonidentical periods for same-period revisions. Unknown→known is coverage gained, never growth from zero. A zero denominator is distinct from absent evidence. CFO−cash capex is a cash diagnostic, not automatic FCFE/owner earnings. Parent-attributable profit and consolidated CFO cannot be added as if they share the same scope.

Missing supplied bytes produce dependent SOURCE_BYTES_UNAVAILABLE results while independent comparisons remain available. Wrong supplied bytes fail identity validation. Duplicate input is deterministic and creates no event/state. Reports repeat qualification and NONE authority; exclusive CLI output never overwrites a previous result.

The opt-in [reviewed institutional forecast contract](reviewed-forecast-comparison-v0.md) adds `FORECAST_COMPARISON` / `forecast_difference` for explicitly source-bound forecast observations. Institution/report relation and numerical qualification are separate; legacy inputs and retained outputs keep their existing meaning. The [real forecast boundary cases](readings/c-reviewed-forecast-boundaries-2026-09-30/README.md) remain numerical refusals, not full broker-model revision acceptance.

## Consumption

First recover the selected on-demand archive through the ordinary fixed-R entry and `research_archive` contract. Each real archive README provides the externally pinned input SHA256 and exact explicit local-source arguments. Run current qualified code's `python -m decision_kernel.runtime.research_comparison`, not any recovered script. An absent output directory receives comparison.json/md. No network, model, Market, Watch or remote-write call occurs. The standalone consumer does not pretend to have performed live archive retrieval.

The two output files follow the shared [create-only report publication contract](report-output-publication-v0.md): finish both in private staging, then atomically publish without replacing an existing destination. Report values, hashes and Markdown are unchanged.

Real retained cases:
- [Accelink profit versus cash absorption](readings/c-longitudinal-accelink-2026-09-30/README.md): parent profit increases while consolidated CFO deteriorates, cash capex increases and the historical seasonality challenge remains limited by inventory/financing evidence
- [Xingsen R1→R2 cash-capex recovery](readings/c-longitudinal-xingsen-2026-09-30/README.md): missing→known capex, derived Q2 CFO/capex/refunds, unchanged displayed-precision old arithmetic and explicitly unchecked historical notes

Copied original files retain exact historical bytes. A separate current Sina issuer-disclosure mirror check corroborates selected H1 inputs, but is not original PDF byte custody or contemporaneous knowledge. No complete original-note audit, new Full, typed COMMITTED Research, Human acceptance or investment action is claimed.

## Reuse decision and finite acceptance

Reuse Decision: **THIN_ADAPTER**. Internal research archive/index/re-entry/progress/workpaper interfaces were inspected; narrative workpapers have no structured comparison consumer, and adding siblings to RESEARCH_PROGRESS would violate its inventory. Existing bounded file I/O, canonical hashes and safe paths are reused. Official [Decimal](https://docs.python.org/3/library/decimal.html) and [JSON parse hooks](https://docs.python.org/3/library/json.html) provide arithmetic/lexical parsing; no new dependency.

External review starts from [#508 current C evidence](https://github.com/auguspp/decision-kernel/issues/508#issuecomment-5908718008) and #511: EasyStock/AKShare report wrappers do not establish historical target/share/currency bases; missing→zero and current-year labelling are retained negative evidence. Anthropic earnings/model-update methods inform revision structure, not source custody or an executable replacement. This adapter adds only project-specific reviewed identity/basis semantics; no duplicated market-data framework. Existing licensing/maintenance caveats remain in those records.

Acceptance separates: structural/basis arithmetic tests; real two-company deterministic output; normal PR/main/publication and fixed-R recovery; independent consumer explanation; original-source qualification; economic adequacy and later relevant use. Passing the first stages does not sign the later stages or complete C1/C2. Initial review found quote-number substring, explicit clock and period-span defects; repaired counterexamples stay in tests. Retirement/extension belongs to the same C task, not a new ongoing platform.
