# Reviewed institutional forecast comparison v0

## Scope and reuse

This is an opt-in qualification path in the existing offline
[`research_comparison`](research-comparison-v0.md) consumer. It separates an
institution/report relationship from permission to compute a comparable forecast
difference. It adds no provider, source acquisition, parser service, registry,
schedule, model call or investment authority. The original
[`institutional_context`](institutional-context.md) raw projection and its
`forecast_revision=NOT_COMPARABLE` boundary remain unchanged.

**Reuse Decision: THIN_ADAPTER.** Reuse the existing exact-source checks, bounded
JSON/Decimal arithmetic, safe create-only CLI and retained archive route. The
[existing Reuse Decision](research-comparison-v0.md#reuse-decision-and-finite-acceptance)
links the internal, official and #508/#511 external prior-art evidence, including
why report wrappers do not supply missing historical target, currency or share
bases. This contract introduces no dependency or replacement data framework.

## Explicit input contract

The outer version remains `reviewed-research-comparison-v0`. Each participating
observation supplies `forecast.contract=reviewed-institutional-forecast-v0`.
The comparison uses `kind=FORECAST_COMPARISON`,
`operation=forecast_difference` and exactly two ordered terms with signs
`[-1, 1]`: new minus old. Forecast-bearing observations cannot use the legacy
`difference` operation to bypass qualification. This is an explicit declaration,
not automatic detection of forecasts in arbitrary historical input.

Forecast metadata carries institution identity and mapping rationale, report
namespace/record/original-report identities, report label date and qualification,
target period, metric/accounting basis, currency, scale label, share basis,
source bindings, forecast-role rationale and limitations. The ordinary source
descriptors retain immutable commit/path/blob/SHA256/byte count, source
qualification and known or unknown publication/acquisition clocks. Hashes prove
the supplied byte identity, not the truth of these reviewed declarations.

### One record, source-bound facts

The report's `source_id` must equal the observation's source. Its
`record_locator` is a single JSON pointer to one object, and the value locator
must be within that record. Claimed source facts use pointers within the same
record: a direct member, or one element of a scalar array. A list of records,
nested record-container traversal, text quote or mixed quote/pointer locator
cannot supply the qualification. Facts cannot be borrowed from a neighboring
report or from a response-wide `currentYear`.

Bindings validate institution name and any claimed provider code, record ID,
optional original-report ID, report date, target, metric label and basis,
currency, scale and forecast role; EPS also binds its share basis. Missing or
invalid bindings yield explicit blockers. Reviewed namespace, identity keys and
mapping notes remain reviewed declarations, not invented official identifiers.
Supported transformations are narrow: exact equality, date prefix, listed
currency aliases, metric-basis fields, JSON key, or an identified forecast value
field. `FORECAST_FIELD` must bind the actual observation slot, never a sibling
forecast value used to relabel a reported actual. Currency aliases do not infer
currency from an amount unit or perform FX conversion.

Institution identity can use a source-bound provider code within its declared
namespace, exact displayed name, or an explicitly reviewed alias with meaningful
mapping rationale. Different names alone do not prove different institutions;
codes from different provider namespaces do not establish a cross-broker pair.
Even under name-based identity, a claimed provider code requires its own binding.

## Relation is separate from numerical qualification

Read `relation`, `status`, `blockers` and source/date qualifications together:

- `DUPLICATE_BOUND_RECORD`: same namespaced record and canonical record content;
  qualified equal values return `DUPLICATE_NOT_NEW_FORECAST` with no difference
- `SAME_RECORD_CONTENT_VARIANT_NOT_NEW_REPORT`: changed content under the same
  record identity, not automatically a new broker report
- `SAME_RECORD_IDENTITY_CONFLICT_OR_CORRECTION`: the same provider record changes
  institution identity; comparison is blocked
- `CROSS_INSTITUTION_ATTRIBUTION_NOT_REVISION`: different comparable institution
  identities; any qualified difference is cross-institution disagreement
- `SAME_INSTITUTION_FORECAST_VINTAGE_CHANGE`: same resolved institution, distinct
  records and bound distinct original-report IDs, with strictly increasing
  label dates qualified as `ORIGINAL_REPORT_DATE`
- `DISTINCT_PROVIDER_RECORDS_ORIGINAL_VINTAGE_UNESTABLISHED`: provider records can
  be ordered, but original broker vintage is not established
- `DISTINCT_RECORDS_NOT_TEMPORALLY_ORDERED`, `DIFFERENT_FORECAST_HORIZON` and
  `IDENTITY_UNRESOLVED` preserve their respective limits

A relationship label alone never qualifies the number. Conversely, where all
numeric qualifications hold, the consumer may compute a difference for a
content variant, cross-institution pair or pair without established original
vintage; the relationship label still prevents calling it a same-broker model
revision. Successful arithmetic is only `REVIEWED_FORECAST_ARITHMETIC_ONLY`.
Different qualified target periods block arithmetic. Report dates after the
review or explicit analysis cutoff also block it. Provider date prefixes and
retrieval clocks never establish historical public availability.

### Total profit versus EPS

Both values must be known numbers, declared as forecasts and bound to the same
qualified fiscal target, currency, measure, attribution and adjustment basis.
The target explicitly contains `start`, `end` and `fiscal_basis`, and matches the
observation's FLOW period. Currency is qualified CNY or USD; supported amount
scales are normalized with Decimal, not binary floats.

For this opt-in forecast path, the source-bound `forecast.metric_basis` is the
canonical accounting basis. Before numerical qualification, the observation's
outer fields must be its exact projection: `metric = measure`,
`scope = attribution`, and `restatement = adjustment`. They are not independent
free-text descriptions or an additional unbound accounting basis. Each
observation must agree internally, and the two canonical bases must also agree
with each other. Matching outer fields cannot override conflicting inner bases;
matching inner bases cannot override conflicting or unknown outer fields.
`OBSERVATION_BASIS_DIFFERS:<field>` and `OBSERVATION_BASIS_UNKNOWN:<field>` block
arithmetic without changing the separately established institution/report
relationship.

`forecast.metric_label` retains the independently bound source display label;
it is not an alias that replaces canonical `measure`. A provider's label does
not by itself establish a normalized accounting basis. Different bound display
labels or review notes may describe the same qualified canonical basis, but
`mapping_note` and `basis_note` cannot authorize a conflicting outer field or
replace the actual source binding. The synthetic positive fixtures therefore
project `REPORTED_ESTIMATE` into outer `restatement`, rather than the earlier
unbound `SYNTHETIC_UNCHANGED_BASIS` description.

Projection validation runs only after the inner basis has passed its existing
shape, known-value and source-binding checks. An unqualified inner basis already
blocks arithmetic; the consumer does not infer a replacement basis from outer
labels or append derivative projection claims to that refusal. This preserves
the retained real negative reports and their hashes/Markdown. Non-forecast
inputs keep their existing outer-basis contract and output bytes unchanged;
historical inputs and archives are not rewritten.

`TOTAL_PARENT_PROFIT` requires `share_basis={"application":"NOT_APPLICABLE"}`.
It is a total amount, so a missing EPS denominator is not its blocker and a
per-share unit is invalid. Output is in base currency.

`EPS` requires a source-bound `PER_SHARE` basis with known `share_class`,
`denominator`, `split_basis` and `model_basis`; both observations must agree.
Only scale 1 with a qualified `1` or `元/股` label is supported. Output is
currency/share. Basic versus diluted, split rebasing, unknown model denominator
or monetary amount units cannot silently pass as comparable EPS.

Missing values remain null with `UNKNOWN`/`NOT_CHECKED`, never zero. Missing
targets or currency remain unknown rather than inferred from provider relative
slots, a listing market, publication year or review note. Whitespace and explicit
unknown markers do not qualify substantive basis fields. Blocked comparisons
return `NOT_COMPARABLE`, null value and specific reasons. Missing supplied
source bytes retain the existing `SOURCE_BYTES_UNAVAILABLE` behavior; mismatched
bytes fail identity validation rather than becoming new evidence.

## Real evidence and engineering examples

The [two retained real cases](readings/c-reviewed-forecast-boundaries-2026-09-30/README.md)
demonstrate bounded relationship recognition and numerical refusal:

- Accelink: the two Changjiang synopses share an exact displayed institution
  name, but original broker vintage, fiscal target, complete accounting basis
  and currency are not independently established. The total-profit denominator
  is explicitly not applicable
- Xingsen: Puyin International and Kaiyuan have different provider institution
  codes/names. Their relative EPS slots lack qualified target, currency and
  share bases. This is cross-institution attribution, not a same-broker revision

Neither case is a positive qualified full-model revision. Both retain the
original source bytes and qualifications; this path does not upgrade a synopsis
or retained extraction to broker PDF/model custody. Prior nominal arithmetic
remains history, without retrospective certification by the new contract.

The positive fixtures in
[`tests/test_reviewed_forecasts.py`](../tests/test_reviewed_forecasts.py) are
explicitly `SYNTHETIC_FIXTURE`. They exercise total-profit and EPS arithmetic,
units, source binding and relation/refusal counterexamples. They are engineering
proofs, not real-company research evidence. Tests also rebuild the existing
cash-bridge semantic reports without changing their report objects/hashes or
Markdown. Inputs without forecast metadata keep their original path and output;
no historical archive or raw projection is migrated.

## Consumption and finite acceptance

Recover the selected archive through the ordinary fixed-R
[`research_archive`](research-archive-v0.md) route. Use current qualified code
and the explicit externally pinned input SHA256 and `--source ID=LOCAL_FILE`
arguments in the [case README](readings/c-reviewed-forecast-boundaries-2026-09-30/README.md).
The command remains `python -m decision_kernel.runtime.research_comparison`.
It creates `comparison.json` and `comparison.md` in an absent output directory;
it never overwrites a previous result or executes retained source instructions.
Canonical versus pretty JSON formatting may differ, but the report object and
`report_hash` must agree; rendered Markdown must agree.

Finite acceptance separates contract/counterexample tests, deterministic real
negative cases, legacy compatibility, normal exact-head PR/main/publication,
independent fixed-R recovery and actual explanation/use. Passing local tests or
writing this contract does not establish later stages. Original broker-source
qualification, full-model economic adequacy, later natural use and remaining
original C1/C2 scope remain separate obligations. Every result keeps
`full_model_revision=NOT_CERTIFIED`, historical knowledge unestablished by
retrieval, Human acceptance unestablished and investment authority **NONE**.
This document makes no shipped-state or full-C completion claim. Extension or
retirement belongs to the original C task, preserving historical readers and
evidence rather than creating a standing forecast platform.
