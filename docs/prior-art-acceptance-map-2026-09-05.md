# TradingAgents / ARTi prior-art acceptance map — 2026-09-05

Status: TESTS AT EXISTING BOUNDARIES / NO NEW RUNTIME OR KERNEL SCHEMA.

Implementation baseline reviewed: `76b95cbc1a6958dcca4a5c5148f653f61850b152`.
This is not a TradingAgents integration, a Judgment subsystem, or proof of real prospective performance. The Human approved starting with acceptance cases and prospective exposure capture, not importing another project's semantics.

## Source identity and scope

TradingAgents source was reviewed at `9dee508c44662702281a8dbaad1f7b42179b5ba7`:

- https://github.com/TauricResearch/TradingAgents/blob/9dee508c44662702281a8dbaad1f7b42179b5ba7/CHANGELOG.md — latest-bar, vintage, reflection, structured-output and checkpoint failures.
- https://github.com/TauricResearch/TradingAgents/blob/9dee508c44662702281a8dbaad1f7b42179b5ba7/tests/test_memory_pointintime.py — outcome availability versus analysis date; also documents live-mode exemptions we do NOT adopt.
- https://github.com/TauricResearch/TradingAgents/blob/9dee508c44662702281a8dbaad1f7b42179b5ba7/tests/test_fred.py — both observations and metadata must use the historical vintage.
- https://github.com/TauricResearch/TradingAgents/blob/9dee508c44662702281a8dbaad1f7b42179b5ba7/tradingagents/dataflows/errors.py — useful diagnostic distinctions, but router/fallback semantics are not ours.
- https://github.com/TauricResearch/TradingAgents/blob/9dee508c44662702281a8dbaad1f7b42179b5ba7/tests/test_symbol_normalization_paths.py — an explicit proxy mapping is not financial-identity equivalence.

New tests are independently written using existing project fixtures and pytest. No external implementation or test body was copied. ARTi details below are Human-supplied product observations, not an independently audited backend or settlement rule. Do not claim an ARTi defect or verification based on these examples.

## Reuse current contracts instead of creating a parallel model

`ResearchSnapshot` already owns frozen Belief, scenarios, horizon, falsifiers and evidence identity. `ObservedMarket` owns the represented market clock and price convention. Frozen Odds and Rehearsal own exact references; `HumanResearchSurface` owns eligibility, NOT proof of Human exposure, assent or decision.

Existing Human Decision / Action / Outcome discipline is in:

- `docs/prospective-decision-outcome-capture-protocol-2026-09-03.md`
- `docs/decision-accounting-human-response-gap-review-2026-09-03.md`
- `docs/live-decision-book.md`

Those frozen protocols and existing case checkpoints are not rewritten by this work.

## Acceptance disposition

| Candidate / real failure | Classification and owner | Existing equivalent or first action | Smallest proof and loss if omitted |
| --- | --- | --- | --- |
| Latest close disappears during cleaning | ALREADY_HAVE, adapters/Harness | `tests/test_hithink_adapter.py` rejects a latest NaN close, unfinished/off-calendar data and preserves an old observation clock; production runtime separately requires latest completion | Keep those cases instead of duplicating them. A replacement fetcher must not promote the prior day. No benefit from importing stockstats cleaning/fill behavior. |
| Old report period or original publication date hides a later vintage | PORT_TEST, existing Evidence/commit boundary | New value-revision and metadata-revision fixtures pass schema, recompute identity, then fail the formal CLI before any market call | An old URL/period, same evidence id or corrected hash is not PIT qualification. Otherwise hindsight can enter through perfectly valid JSON. |
| Date-only comparison or retrieval time replaces actual availability | PORT_TEST, existing Evidence/commit boundary | New same-instant/one-microsecond cases cross timezone calendar dates; known public availability can precede later retrieval | Public availability, actual run acquisition and Human exposure are separate. Reject future availability, but do not falsely reject a retained old vintage merely for later retrieval. |
| Structured invocation fails and text becomes Hold/Buy | PORT_TEST, CLI plus Kernel admission | New prose, JSON string, rating-only object and fenced JSON failures, with a valid unwrapped control | No market fetch, success/quiet surface or persistent file may be created by a rejected candidate. This verifies formal ingress, not an LLM adapter we do not have. |
| Valid JSON bypasses semantic checks | PORT_TEST, existing commit boundary | Rehashed missing-thesis and non-unit-probability candidates; external authority-field refusal | Schema PASS alone is insufficient. No permissive parser, enum default or authority upgrade is introduced. |
| Presentation changes authoritative numbers | ALREADY_HAVE + cross-object PORT_TEST, Decision Spine | Existing information-hash/framing separation, now exercised through deterministic Odds and Rehearsal | Fixed inputs/ids/clocks yield identical Odds and eligibility despite changed framing; Rehearsal hash changes honestly. No prose-to-rating interpretation. |
| Future reflection silently enters an earlier prompt | PORT_TEST design only, Research Method/Harness | Existing future-Evidence check is NOT pre-prompt isolation; no automatic reflection consumer was established in this review | Before enabling a consumer, freeze exact input manifests; exclude not-yet-known outcomes, same/cross-instrument lessons and unknown timestamps before invocation. Test UTC instants even in live mode. Do not build fake memory just to make a test green. |
| Reflection auto-promoted to method policy | REIMPLEMENT only after a real case, Method governance | Existing outcome/attribution protocol; no new memory or acceptance service | Distinguish observation availability, reflection authorship and governed acceptance/effective version. History must not replay under a later method while claiming the original. No current automatic learning claim. |
| Wrong-context checkpoint resume | PORT_TEST at future consumer, Harness | Existing Sector replay/publication gate is not long-LLM-task checkpointing | Before enabling research resume, bind input/method/prompt/config identity and prove no repeated side effects. No LangGraph or checkpoint framework needed now. |
| Empty opponent prompts fabricated counterevidence | PORT_TEST at applicable research method | Existing bounded adversarial findings remain the method; no role graph | Test an actual alternative method against identical frozen evidence, including no-opponent opening. Additional material counterevidence, not agent count, is the criterion. |
| Data-source errors and ticker paths | REIMPLEMENT diagnostics / conditional REUSE, Harness | Reuse current provider and identity validators; inventory an actual deficient consumer first | NoData is not Stale, path-safe is not instrument-valid; never inherit next-provider fallback or proxy equivalence. No new error hierarchy or sanitizer just for nominal feature parity. |
| Human exposure, response, judgment navigation | PRODUCT_IDEA / thin prospective protocol, Human Surface/Harness | Use existing checkpoints; add the separate exposure/response supplement when accepted | Missing exposure is UNKNOWN, not independent. Do not manufacture Human decisions from research approval. Timeline is a projection, not a second Research store. |

## What the new executable tests do and do not establish

`tests/test_prior_art_research_ingress.py` uses the existing `_generic_package`, `_rehash_generic`, mocked market fixture, Pydantic parsing, CLI, `commit_research_package` and Decision Spine. Sockets and provider transport are blocked. Input files and frozen original results remain unchanged. Schema failures and semantic failures are tested separately, rather than making a missing API key the rejection reason.

The revised records deliberately reuse an earlier URL/evidence id and publication date to exercise an adversarial replacement. They do not endorse reusing identity to store a genuine new vintage. The correct response to genuine revised evidence is a distinct record with accurate availability and a later research version; not editing the original accepted judgment.

These tests cannot infer truthful timestamps from a provider, prove that an undeclared source was absent from an LLM prompt, inspect a model's training knowledge, or confer semantic truth on a committed snapshot. The later-retrieval positive control certifies only the declared package's public-availability boundary, not that a historical run or blind Human forecast actually occurred.

The pre-prompt memory manifest, governed method-learning workflow, evaluation lifecycle and general checkpoint-resume tests remain design-only because their consumers are not implemented. They are not counted as passing runtime coverage. Do not describe this test PR as a new future-memory isolation system.

## Next bounded step

Preserve actual exposure and response in the next natural case using a zero-schema supplement to the existing Human protocol. Then evaluate a read-only timeline from existing frozen records; no Judgment/Episode/Outcome Kernel schema is authorized by these acceptance tests. Before any method comparison, define explicit episode links and evaluation contracts; episode count still does not prove statistical independence.

This batch makes no workflow, dependency, runtime, frozen Research, actual Human/Action record, market-state, ledger, threshold or authority change and makes no live market request. Sector's direct-next-session acceptance stays separate and pending.

External Research Method can propose. Kernel commits admissible identity and invariants, not truth. Human decides.
