# Pre/Quick model-visible route contract — 2026-09-23

Engineering scope: #297/5789661998, following actual failure #297/5789296851.
Reuse Decision: REUSE. This is schema description metadata, not new runtime
validation, a schema-version migration, a recovery framework or research acceptance.

## Actual failure and smallest repair

Run 35819538967 / artifact 10732853090 completed one Pre and one Quick provider
response. Pre validated. Quick chose DEEPEN but supporting_claims[10] and
contradictory_claims[5] were INFERENCE. The application validator requires both
DEEPEN evidence groups to be nonempty and entirely evidenced FACT/MARKET_CONTEXT.
Its generated wire schema did not explain that cross-field condition.

Use existing Pydantic Field descriptions on the original model fields. The
existing request-local Evidence-ID schema and pinned SDK carry those descriptions
to both request paths. No new fields, defaults, enum values, required conditions,
validators, serialization values or stage transitions are introduced. All seven
original validation/transition function bodies remain unchanged.

Descriptions explain the existing conditional rules rather than narrowing every
route to all-factual claims. WAIT_FOR_TRIGGER and STOP can still carry honestly
labelled inference. Inferences remain labelled narrative, not manufactured facts.
The guidance also distinguishes available-now discriminating work from future
publication triggers, and declared source preflight from whole-issuer coverage
or certification of economic truth. Missing quantitative closure alone does not
force DEEPEN; a statement that no variant is established is not a positive variant.

Descriptions are guidance, NOT machine-enforced conditional JSON Schema. No claim
is made that Python model validators compile to JSON Schema or that a provider
will always follow prose. Original application validation still occurs after
retention of the raw response. No unsupported if/then or root-union wire extension
is assumed compatible with the provider.

## Reuse evidence

- Internal: research_funnel models/validators; saved_research_once request-local
  schema, native SDK builder, raw-output retention and original validation;
  stock_question_continuation._deepseek_request and the original host/preview.
- Official: Pydantic schema-only field description support:
  https://docs.pydantic.dev/latest/concepts/json_schema/#field-level-customization
- Public GitHub: inspected openai/openai-python src/openai/lib/_pydantic.py,
  to_strict_json_schema and _ensure_strict_json_schema; also issue #2024 on
  metadata/$ref inlining. Real SDK-wire regressions are required, not just
  inspection of field definitions. Existing dependencies and versions are reused;
  no external code is copied and no new dependency/license obligation is added.

## Evidence preservation and tests

The fixture directory tests/fixtures/industry_quick_contract_20260923 retains the
exact rejected Quick text, original Pre/Quick wire formats, partial candidate and
input. provenance.json records artifact and per-file hashes. These are historical
negative-sample data, not executable requests or approved financial conclusions.
The rejected text can contain incorrect numbers and economic interpretations.
No fixture is rewritten to make the issuer result pass. Counterfactual route
examples in tests are explicitly synthetic and cannot be published as corrections.

Regressions cover actual SDK description delivery and old wire equivalence after
removing only new descriptions; original saved Pre/candidate hashes; preserved
rejection of the real Quick; all existing DEEPEN condition edges; non-DEEPEN
inference compatibility; and raw-response retention before failure, without retry.
Complete PR/main CI and normal publisher/readback remain separate acceptance facts.
No live Research or economic-quality improvement is pre-certified by these tests.

## Continuation boundary

Original slot02/day2026-09-22 and launch remain consumed. This patch does not
activate a request, reissue a label, extend the expired source preflight, fetch
PDFs, rerun Pre, relabel inference, silently repair Quick, or execute Deep/Odds.
Any necessary Quick-only correction must preserve and bind the valid original Pre,
original failure and source scope through the existing host. That live continuation
and semantic/financial review are not implemented or claimed by this metadata repair.
