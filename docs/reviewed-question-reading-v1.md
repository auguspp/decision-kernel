# Saved reviewed-question return to the normal reading

2026-09-20. P0-A continuation under #297/5748559847 and the subsequent Human implementation approval; pre-construction receipt5749095785. Reuse Decision: THIN_ADAPTER.

## User-visible gap fixed

The old Stock reader intentionally projects only `stock-business/` baselines for current price-qualified Stock members. New reviewed-question executions use the sibling `stock-questions/` namespace. Their results therefore require an explicit reading path independent of today's price membership; otherwise a genuine completed question can disappear from the normal Brief even though its original work is retained.

The existing publisher now opts into `--include-reviewed-questions`. It uses the same Collector, exact work ref, immutable Git tree/blob reads, original candidate validator, sealed current-state output and ordinary publisher. No new scheduler, state store, model, source client, question generator, dependency or Research execution is introduced. Old Stock baseline and recovery contracts remain unchanged. The existing invocation classifier additionally recognizes the already-present `deepseek-compatibility` job and keeps it separate from a Research job or source-preparation job. Classified invocation metadata is not a model-call receipt.

## What is read and validated

Pin the original `research-work/stock-business-v0` once. Within the untruncated, bounded tree, enumerate all saved `stock-questions/<stable-root>/` entries, including only the original fixed `technical-continuation-v1` child shape. Do not choose questions by latest Stock membership or the newest successful run. Partial, failed and successful roots remain separate.

Read and retain the original preparation, input, launch, candidate, validation, receipt, funnel, host receipt and admission files when present. Read the exact bound researcher-authored question; check content identity, securities, stable question root, revision, reservation/input/launch bindings. Re-run `validate_external_research_candidate` and compare the original saved validation and, where present, funnel/receipt/host hashes. For a technical child, check its declared predecessor bytes against the preserved parent at the pinned work tree.

This is historical saved-candidate consistency checking. It does NOT replay launch-time admission, refresh source preflight, authenticate issuer documents, recreate provider calls, certify the researcher's question quality or accept an economic conclusion. Historical permission/preflight expiry does not erase an earlier execution. Current execution permission is never inferred from reading it. A validated candidate without the last host receipt is explicitly marked as lacking that receipt, not advertised as proof all writes completed.

Output lives in `research.reviewed_question_work`, with same-reading `details/research/reviewed-questions.md` and `.json`. It preserves the original question, why-now, unknowns, terminal route/reason, actual original cutoff/completion, and exact source references. `registered_current_handoff` stays false; it cannot add pending Human requests or inherit Human acceptance. Re-reading an old result is not new Research.

## Current Stock batch is a scope, not an invented triage result

The same detail projects all dispositions from the latest qualified saved Stock result. Its batch identity depends on the original source run, saved market session/projection and full dispositions, not the current publisher time. Preserve data-unavailable versus original price disposition. A currently qualified row without a question-review receipt is `QUESTION_NOT_YET_REVIEWED`, never `NO_USEFUL_QUESTION` or a synthetic WAIT. Existing historical question outcomes remain independently visible; they do not prove the current batch has been reviewed.

This is not an automatic economic-question triager. Reviewer judgments, new required-source acquisition, distinct-question dedup/admission, an authorized new Pre, actual Brief delivery and real Human response are still separately required for the broader daily P0 acceptance.

## Bounds and failure behavior

Use the already accepted Stock source allowance of32 files, shared with old Stock work references, not an extra32. Reuse the original252-call maximum and128MiB retention budget; question scopes have at most8 root/child execution directories and each source remains at most512KiB. These are representation bounds, not research quotas. An over-budget or truncated inventory is a visible scope gap, not permission to truncate the universe or scan only successes.

Per-question binding/validation failures retain an explicit rejected row. Inventory/transport/capacity failures roll back partial optional files and leave an explicit compact `UNAVAILABLE_OR_REJECTED` record and navigation notice while preserving the other lanes. If even the compact marker cannot be published safely inside the original bounds, the original publisher fails and retains its prior reading; it must not silently publish a complete-looking zero.

Source text remains untrusted data and Markdown is escaped. No source code/commands, secrets, market sites or model services are executed by this reader.

## Acceptance

Tests use the original question and continuation hosts, synthetic Git/model boundaries, and the real original validator. They cover WAIT/STOP/conditional Quick, actual typed execution gaps, price-membership loss, absent Stock, preserved parent/child history, tampered or partial bytes, shared capacity, unknown scope and text escaping. No synthetic test is a new live company Research sample.

Complete exact-head CI, reviewed merge, independent main CI, normal publisher and actual same-R readback are separate gates. The previously completed300711 run35485210755 is only a historical readback control, never a new daily execution or permission to rerun. This slice cannot close all of #297 by itself.

AI Investment Authority = NONE.
