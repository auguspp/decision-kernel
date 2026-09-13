# Explicit recovery of the three Stock source-preparation failures

**Reuse Decision: THIN_ADAPTER.** Human's exact response “好，同意，你做吧”
and the pre-construction reuse check are retained in #297 comment **5652047028**.
The prior source diagnosis is **5652012258**. The existing first-business permission
5651083343 and project Sub2API authorization remain separate and unchanged.

## Scope and original records

The original research run **34744840053** consumed Stock run **34673882756**.
600184.SH and 603353.SH failed because valid company-prefixed report titles were
not recognized. 300711.SZ failed on an unreadable signature page; later required
bodies were not captured. 300183.SZ completed Pre/Quick and is NOT selected here.

The main request `research_runs/stock-source-recovery-request.json` binds exactly
those three original prepare/failure pairs at work commit
`9c1c78980de5f8ba6d83e12614d5b3a6538fb7b8`, the exposed reading
`5401ad55e02edd06948610c801368aadd80ac58b`, the actual permission and exact repaired
report/page identities. Their parent results remain immutable.

## Reuse, not a second executor

The existing source selector still chooses the latest reporting period and its
latest version, retaining every disclosure from the first full version of that
period. Prefixed titles are discovery candidates only: the short name must match
the original Stock identity, or occur in a bounded legal-company-name prefix.
Summaries and ancillary board/audit/verification titles do not count. Original
CNINFO security/org checks and the printed PDF security check remain. A recognized
title is not evidence that the complete PDF was acquired or read.

The existing `disclosure_source_reading` consumes the actual reviewed whole-page
note for PDF `cc65030bd9e676f5289d2bc2649eb7ff23b26a5b406b08b88cd20392d45df342`,
page 4. Its original PDFium engine and full RGB pixel identity are preserved.
The page is a signature/seal page, not blank; the note does not authenticate names,
signatures, seals, dates or legal effect. This representation is NOT an independent
primary-source vote. The original page-reading module is unchanged.

`stock_source_recovery` binds the original unexecuted source failure, selection,
shown reading and actual permission, using the existing checked-source and clock
functions. The original disclosure continuation cannot directly accept Stock
packets, so its checks are not weakened or bypassed. The original Stock host still
performs source capture, input freezing, two admission checks, `research()`,
conditional Quick, unchanged validation, public-output retention and Retainer.
No second model loop, provider, dependency, Kernel model or scheduler is added.

## One stable recovery, not a retry or re-key

Each child is under the parent's **fixed** `source-recovery-v1/` directory. Its
execution identity depends on the original security/question, not a new permission
number, price, date, source run, code version or wording. Any child preparation,
launch, failure or result prevents another execution. A parent with input or model
execution history is ineligible. The current adapter does not implement a general
later continuation or a second recovery after this child fails.

Permission, latest parent history and exact trusted-main request are checked before
reservation and again before each model stage. The original parent commit and
shown-reading commit must precede the retained permission time; an earlier
`checks.finished_at` cannot hide a later exposure commit. The child keeps the exact
original price selection/question. The required full report and bound page repair
must actually be present before Research; a new timestamp alone cannot repair it.
The current source acquisition is not a backdated price-day causal explanation.

Default natural Stock processing remains first-baseline-only. It reuses consumed
history instead of consuming this recovery request. The existing workflow gains
only `recover-sources` (boolean, default false), mapped to `--recover-sources` only
for explicit native manual dispatch. Its original main/attempt1/concurrency guards
and artifact retention remain. No automatic retry or new trigger is added.

For the approved recovery, after exact-head CI and publication acceptance, the
existing native workflow inputs are `source-stock-run-id: "34673882756"` and
`recover-sources: true`. An uncertain or already-issued dispatch must be reconciled
read-only, never repeated. This document does not trigger it.

## Reading and budgets

The original reader retains each parent item unchanged and attaches its child as
`source_recovery`; child counts are separate from parent counts. The original
Eastsoft candidate remains one completed first baseline. No automatic handoff,
Human acceptance, Belief, Odds, Action or investment authority follows.

Matching-ref discovery reuses the original publisher's approach to distinguish
normal first absence from read failure. It does not depend on exception-class
identity between `python -m` and a subsequent module import. Permission/transport
errors, malformed lists and duplicate exact refs remain gaps, not NOT_STARTED.

Original market/disclosure collection and publication reserves take precedence.
The existing additive 64-call/24-source Stock allowance remains unchanged; the
three parent failures, three children and Eastsoft fit within it. There is no
first-N truncation. Over-capacity remains explicit; no quota is interpreted as
Human permission or a monetary budget. Complete source/context bounds remain.

## Verification is layered

Synthetic tests exercise original admission/Pre/Quick/retention, immutable parents,
partial-child deduplication, scope, revoked permission, late exposure/parent changes,
required repairs and parent/child reading. They do not manufacture issuer facts.

Original saved CNINFO query replay selects report1225518050 with 10 required bodies
and report1225531021 with 20; this does not acquire those bodies. The actual saved
Guangha PDF and new note can be replayed through the unchanged representation code,
but a labelled synthetic local source ref is not trusted-main production admission.

Local verification uses a hash-checked 614-blob archived repository plus exact
necessary current files, not a complete current-main checkout. Dependency versions
and unmaterialized old test fixtures differ. Complete pinned PR CI, reviewed-head
merge, main CI/publication and actual source/model results remain separate.
Natural Brief readability and real-trading-day acceptance are not implied.
