# Saved Stock batch disposition: zero new execution is not an empty market

Scope: #297 P0-A, Human continuation on 2026-09-21.
Reuse Decision: **THIN_ADAPTER** into the existing saved-question reading.

## Actual need and review

At main `2ec361f6b5a9776aaa1f642946e47b0c88678683`, reading
`d5191f188a8a054a7992ee061094959c5903e388` exposes the six-row 2026-09-18
Stock batch from run35334355692. The original reader correctly reports automatic
observation prompts and historical research relations, but cannot display an
explicitly saved whole-batch no-launch disposition. Re-reading remains
NOT_PERFORMED even after a researcher has reviewed the routing and recovered
same-question financial progress.

The saved record covers all six rows, in original order. Three retain original
CONDITIONS_NOT_MET (688066 is a risk-name filter, not a failed price-path test),
one retains a data-qualification failure, and two retain existing failed
FIRST_BUSINESS_BASELINE roots. Woton's existing r3 locator is linked separately;
its source custody and financial progress do not erase the original failure or
create a new daily question. This review did not produce a source-ready new
question under policy5748820065. It does not assert that no distinct economic
question could exist, no opportunity exists, or any company has reached WAIT/DROP.

## Implementation and preserved contracts

One bounded, explicit `research_runs/stock-batch-disposition.json` is data on
reviewed main. Normal Git history preserves prior versions; it is not a queue,
registry, new research stage, scheduler or execution request. The small reader
composes it into the existing reviewed-questions JSON/Markdown and root pointer
through the existing production Collector; no new workflow or CLI flag.

The declaration must match the original batch identity, run, market day, complete
ordered security list, per-row data/filter status and original execution roots.
It accepts only no-launch routing categories. Non-null question sources, unknown
fields or dispositions, future clocks, changed roots, missing rows and duplicate
identities reject. Economic-qualification flags and all original observation and
execution records remain unchanged. A different batch gets an explicit stale,
not-applied result, never a carried-forward zero. Invalid/unreadable declarations
are visible gaps, not completed reviews. Saved reading commit is declared
provenance; the consumer validates current batch/row/root identity rather than
claiming to reread every historical reading body.

Progress links use the existing on-demand index validator and must match both
security and original question ID. They are locators, not body reads or acceptance.
Source text is escaped; it is never executed or used as a tool argument.

The source shares the existing question/Stock source-file allowance and uses
native pinned Git reading. No additional network read is needed. Atomic generated
output replacement retains original sources and checks the unchanged retained
bytes, publication-call reserve and 192KiB root bound. The original eager source
registry, production workflows, model wire, daily request/policy, source/egress
contracts and create-only execution/day reservations are untouched.

## Three-layer reuse

Internal: inspected current `stock_daily_question`, `reviewed_question_reading`
(batch identity, full rows, source reserve and renderer), the existing production
Collector, native Git/source/hash helpers and on-demand archive validator.
Official ecosystem and public GitHub prior art: reuse the same exact Git
Contents/history and PyGithub implementation audit in #297 comment5749609810.
That audit inspected the actual create/update-file implementation and found no
missing capability that justified a new library. The same conclusion applies to
this small read-only composition; no new dependency or infrastructure candidate
is adopted. The previously audited source parsers/acquisition remain unchanged.

## Verification and limits

Local pure projection suite: 32 passed. The local environment is a retained
historical checkout plus this new module, not a complete current-main checkout.
The production wrapper was reconstructed and matched current Git blob
31fd9a5a67008316ab475e34c3f8ae4a6058ed71 before adding only two composition lines.
Additional integration tests exercise actual main helpers in CI: preserved
original rows/failures, no networking or writes, exact source/root hashes,
partial/corrupt/oversize input, stale batches, original budgets and archive links.
Full exact-head CI, independent main CI, normal publication and pinned readback
remain distinct acceptance facts; this document does not preclaim them.

No source/model/market execution or daily slot is consumed. No Brief task is
changed or duplicated. A saved routing review is not a successful Pre/Quick,
Human research acceptance, an investment decision, or a completed P0 usage day.
P0 still requires a legitimate new input/question execution and actual delivery
and response. Continue that main line; do not restart Woton PDF acquisition or
use an existing failed question under a new key to manufacture acceptance.
