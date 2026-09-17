# Human-origin Direct Deep Loop v0

Scope: #321 Acceptance 1–2 **mechanics only**. Reuse Decision: **THIN_ADAPTER**.

This contract fills one narrow gap between the already-approved Full Research Operating Method v3 and the existing method-agnostic `ResearchCommitPackage`. It does not create a second Research engine.

## Existing owners remain unchanged

- `docs/full-research-method-v3.md` and `docs/RESEARCH-ENTRY.md` own research behavior: economic architecture, empirical work, shareholder cash, Challenger, valuation challenge, UNKNOWN/STOP and one-request bounded autonomy.
- `runtime.external_research_execution.ResearchExecutionBudget` and `ResearchExecutionReceipt` own execution budgets and auditable tool/action accounting.
- `EvidenceArtifact`, `ResearchSnapshot`, `ResearchCommitPackage` and `commit_research_package()` own Evidence/PIT/Belief/commit identity.
- Existing Research retention/archive owns persistence.
- Existing Method-v1 Funnel remains Discovery → Pre → Quick → Deep for machine-origin work and is not changed here.

## What the adapter adds

`decision_kernel.runtime.direct_deep` adds only the state that the existing objects do not express:

1. one explicit Human Deep request with exact security, cutoff and hard `max_passes`;
2. ordered pass results from a caller-supplied executor;
3. a persistent UNKNOWN ledger with `OPEN`, `REDUCED`, `CLOSED` and `STOP_PUBLIC_EVIDENCE_EXHAUSTED`;
4. explicit stop reasons and completion/incompletion semantics;
5. an exact handoff check from accumulated Evidence + final UNKNOWN state into an existing schema-v2 `ResearchCommitPackage`.

The adapter has no provider, web client, model client, scheduler, workflow dispatcher, source selector, Market input, Odds calculator or Git writer.

## One request, bounded passes

The caller supplies one `Request` and one pass executor callback. `run_direct_deep()` calls that callback until:

- `SUFFICIENTLY_COMPRESSED`;
- `PUBLIC_EVIDENCE_EXHAUSTED`;
- `MARGINAL_VALUE_LOW`;
- explicit `BUDGET_REACHED` / `TECHNICAL_GAP`; or
- the hard pass count is exhausted.

The last two states are incomplete and cannot carry a final Research package. Exhausting `max_passes` also returns `INCOMPLETE_BUDGET`; ending a loop is not automatically completing Research.

Existing tool/search/source/retry/time budget counters are summed across passes and fail closed if the declared budget is exceeded.

## UNKNOWN continuity

Each UNKNOWN has a stable id, question, importance, why it matters, next discriminating evidence, whether current public evidence can reduce it, and status.

A later pass may reduce, close or stop an UNKNOWN and may add a newly discovered UNKNOWN, but an existing UNKNOWN cannot silently disappear or change its question under the same id. A final Research package must list every non-`CLOSED` ledger question, in ledger order, as its `ResearchSnapshot.open_questions`.

This ledger is loop trace, not a new global Kernel Evidence schema and not a probability model.

## Evidence / PIT

Seed Evidence may predate execution. New Evidence returned by a pass must:

- have a new identity rather than replace an existing artifact;
- have been available by the frozen Research cutoff;
- record retrieval inside that pass's execution clock.

On completed Research, the final package must contain exactly the accumulated Evidence bytes/identities. The existing generic commit validator then independently checks all referenced Evidence, PIT and information-bundle identity.

## No fake Funnel

The Direct Deep route is explicitly `HUMAN_ORIGIN_DIRECT_DEEP`. It does not accept or synthesize Discovery, Pre, Quick or DEEPEN state and does not call `run_research_funnel()`.

A valid terminal package must be schema-v2 Research-only handoff, preserve Human-origin Direct Deep provenance, exact case/cutoff and remain `REVIEW`. `run_direct_deep()` does **not** commit it. The caller must separately invoke the existing commit/retention path. Market and Odds remain `NOT_REQUESTED / NOT_COMPUTED` in this layer.

## What current tests establish

The retained Hengrui package from #413 is replayed as a real identity fixture. One root request drives three pass results, carries an UNKNOWN through reduction/closure, stops the four remaining decisive UNKNOWNs at the retained public-evidence boundary and hands back the exact existing Hengrui schema-v2 package. The fixture makes no fresh source requests and therefore establishes loop mechanics/replayability, not fresh Research truth or autonomous research quality.

Synthetic negative tests cover pass/cutoff/request tampering, silent UNKNOWN removal/change, Evidence replacement/future availability, execution-budget overflow, budget/technical incomplete stops and mismatched final Research.

## Still not established by this slice

- the qualitative part of #321 Acceptance 1: a **fresh** single Human request achieving approximately prior Hengrui Round-3 research quality without Human prompting;
- provider/model selection or a hosted autonomous researcher;
- qualified Market or Acceptance 9 real-price recomputation;
- Human thesis acceptance, Decision, Action, Watch or Investment Authority.

After this core contract passes main/publication gates, Acceptance 1 quality requires a separate real Human-origin dogfood. Until then it remains `NOT_ESTABLISHED` rather than being inferred from replay tests.
