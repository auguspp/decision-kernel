# Pre-execution admission — no Research before a qualified input

Harness only. The original Evidence/Input models, Funnel, #288 identity guard,
Research registry, market schedules, producers and authority remain unchanged.

## Failure provenance and status

Demand-side disposition of #289 is **PRE-EXECUTION FAILURE**:
`INPUT_REJECTED / Funnel NOT_REACHED / Research execution NOT_ACCEPTED`.
The independent later-primary-source gap is `SOURCE_PREFLIGHT_INCOMPLETE`, not a
validator-produced EXECUTION_GAP. Its immutable input and rejected test remain in
Draft #289; no date is filled, candidate promoted or history rewritten. #285/#287
retain their distinct earlier semantics. Do not execute MU or Shennong again for
this acceptance. These cases are not a matched normal/adversarial pair.

## One launch path, two checks

`runtime/external_research_admission.py` provides:

1. `check_preflight`: before a formal input is frozen, verify a bounded recorded
   accessibility inventory for EVERY declared required class. No ResearchClaim,
   Evidence production, route or investment conclusion is created.
2. `prepare_input`: parse the **installed original ExternalResearchInputPacket**,
   verify retained-seed publication provenance, then compute `identity.input_key`
   with the original canonical model hash. Reuse #288 on the pinned catalogue
   plus the prospective key. A prepare result permits input commitment only.
3. Commit the unchanged input bytes into its isolated candidate prefix and obtain
   the exact commit. Do not infer this step from a branch name or write request.
4. `assess_admission` with exact `input_source` and `expected_key`: repeat prepare,
   actually load the exact committed input, compare bytes AND parsed model hash,
   check the publication clock, reload the pinned scope and reuse #288's original
   `load_execution_scope` / `require_unambiguous` with that exact committed input.
5. A trusted adapter MUST enter via `execute_after_admission(executor=..., ...)`.
   It takes the raw admission inputs, not a saved PASS, and checks again before
   invoking its fixed callable. Any rejection returns NOT_EXECUTED and never calls
   the executor. Formal Research budget usage at the gate is always zero.

No generic command runner, model client, scheduler, registry writer or new
Research state machine is introduced. The unchanged historical validation CLI is
NOT a launch endpoint. A gate report's `status=NOT_EXECUTED` describes the check
itself even on `reason=RESEARCH_EXECUTION_ALLOWED`: permission is not execution.
The later actual executor still owes a separate original execution receipt.

## Small input-bound preflight record

The input model does not change. An exact source ref with purpose
`PRE_EXECUTION_SOURCE_PREFLIGHT` binds the recorded preflight JSON; the input's
`known_unknowns` explicitly declares each requirement as, for example:

```text
REQUIRED_SOURCE_CLASS:FORMAL_REPORT:STATIC
REQUIRED_SOURCE_CLASS:LATEST_UPDATE_CHECK:LATEST_INVENTORY
```

The declarations must equal the entire preflight required-class set; arbitrary
prose is never parsed by an LLM to infer a missing requirement. Ordinary explanatory
unknowns remain alongside these machine-readable Harness declarations.

`required_classes` holds id, mode, body_ids and (for dynamic classes) inventory_id.
`reads` holds exact locator, source identity, primary/secondary authority, BODY /
INDEX / SHELL classification, actual success, checked_at, tool reference and body
SHA256. Every static class needs a successfully read primary BODY, not a shell.
`inventories` holds planned query strings, each actual successful query's return
reference/time, and all discovered leads with an explicit relevance explanation.
Every relevant lead must resolve to its readable PRIMARY body; a primary lead
cannot be replaced by a different older document. A relevant secondary lead must
resolve to an identified primary body rather than being silently accepted as fact.
No leads after a completed bounded search means only no relevant leads found in
THAT search, never proof that no later disclosure exists anywhere.

Dynamic aliases SUBSEQUENT_ISSUER_UPDATE_CHECK, LATEST_UPDATE_CHECK and
RECENT_MATERIAL_DISCLOSURE_CHECK may not be labeled STATIC. A failed query,
important inaccessible lead, missing class, lost provenance, future/reversed clock,
stale record, or preflight committed after input selection blocks admission.
Read/query limits and validity expiry are explicit in the preflight, separate from
Research budget. Reconstructed/missing provenance cannot claim RECORDED_TOOL_RETURNS.
The synthetic fixture in `tests/test_external_research_admission.py` is an executable
format example, NOT source evidence or a new research observation.

## Publication clocks and exact scope

This minimal gate supports retained Git-file seeds with GIT_COMMIT publication
proofs. Each seed_publications row pins the same source spec as the input, binds
its actual Git blob / SHA256 and exact GitHub locator, and names the Evidence id.
The loader reads the commit metadata: seed.published_at MUST equal that internal
artifact's proved commit clock. The observation's market day is a different time.
Unknown publication or unsupported provenance is rejected, not filled. Supporting
other proof types later requires an explicit verifier, not a plausible date.

The preflight is committed before selected_at; the formal input is committed after
cutoff; exact readback occurs before launch. Its code_commit pins the declaration
catalogue. Callers must choose current trusted code and recheck the current declared
scope at admission. A later attempt must not reuse an old clean snapshot to evade
newly recorded conflicts. There is no cross-branch/global lock or hard tool sandbox;
unrecorded inputs and privileged bypasses of trusted code are not authenticated.
No new formal registration is made by appending the prospective input to an
in-memory checked #288 catalogue. Promotion still requires the normal durable
identity catalogue, original validation and separate Human semantic approval.

## Read-only CLI

The CLI uses only `file` and `get(git/commits/...)` of the existing bounded GitHub
client, with the already provisioned credential. It does not print/read Secrets
APIs, call the client's writer, request market data or dispatch anything.

```sh
python -m decision_kernel.runtime.external_research_admission \
  --input input.provisional.json --preflight preflight.json \
  --catalog-source catalog-source.json
# Requires INPUT_READY_TO_COMMIT_NOT_EXECUTION_ADMISSION; still no Research.
# After the exact input commit and actual readback:
python -m decision_kernel.runtime.external_research_admission \
  --input input.json --preflight preflight.json --catalog-source catalog-source.json \
  --input-source input-source.json --expected-key execution-key.json
```

Source specs have repository/ref/path/git_blob/sha256; refs are full commit SHAs.
A read adapter must return actual GitHub bytes and metadata, not caller-authored
success booleans. Input/source errors print NOT_EXECUTED and exit 2. Output is an
admission check, never a Funnel result or successful Research execution receipt.

## Formal execution and acceptance

After launch, reread sources and form new lawful Evidence; preflight bodies are
not automatically recycled as Research Evidence. Record tool events, query counts,
failures/retries, budget use, source dispositions and output/validation refs.
Separately report successful_read_events and distinct_research_source_bodies;
indexes, shells, repeated pages and input reads do not add Evidence breadth.
Loss of the action journal means PROVENANCE_INCOMPLETE, not reconstructed full
certification. Missing necessary source classes after admission still invoke the
original INCOMPLETE_SOURCE / EXECUTION_GAP path, without budget extension.

Engineering tests, a source-accessible new real case, original Funnel validation,
remote readback and demand-side semantic acceptance are separate gates. No real
positive case or independent normal/adversarial executor pair is claimed by this
engineering patch. New cases exclude MU/Shennong and must originate from an already
legal saved observation, not post-hoc price selection or a preferred conclusion.
