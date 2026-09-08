# P0-4A pre-execution admission

Harness only. This is a call boundary around the installed input model and #288,
not a Kernel schema, Research state machine, registry, new executor or scheduler.
No Web/market/Research call is made by the admission module.

## Failure provenance and current scope

Demand-side classified #289 as **PRE-EXECUTION FAILURE**, not Research execution:
`INPUT_REJECTED / Funnel NOT_REACHED / Research execution NOT_ACCEPTED`. Its seed
`published_at=null` was correctly rejected by the existing model. Independently,
`SOURCE_PREFLIGHT_INCOMPLETE` records the unreadable material later primary lead.
Neither is a validator-produced EXECUTION_GAP. The original input is retained
byte-for-byte as an offline regression fixture, not repaired or registered.
#289, #285, #287 and #263 remain independent drafts. No further MU or Shennong
execution is part of this batch. Their historical clocks and conclusions stay intact.

The gate's engineering tests and a later real complete research acceptance are
separate. A synthetic callback proving the boundary is not Web Research; a real
negative input fixture is not a new attempt. Consult the implementation PR's exact
CI/readback receipt before marking engineering complete. A later positive case
needs its own input, admission and execution records plus demand-side acceptance.

## Required order

```text
existing lawful saved observation (not selected by hindsight return or conclusion)
  -> separate bounded accessibility preflight, including latest-update inventory
  -> install the exact trusted code version
  -> original ExternalResearchInputPacket parse; original canonical_hash(model)
  -> #288 identity check against all declared pinned inputs + proposed key
  -> commit the exact validated input to its isolated candidate input.json
  -> fetch it back by exact commit; reparse; exact bytes AND canonical hash match
  -> recheck preflight, publication provenance and freshly pinned #288 scope
  -> durably retain admission record
  -> invoke the external Research executor ONCE through the guarded boundary
```

A failure before invocation returns **NOT_EXECUTED**, zero formal Research tool
calls and `funnel_status=NOT_REACHED`. The input writer is not called on a failed
preflight/model/publication/initial-identity check. A failed readback can leave the
input committed, but the executor is never called. A failed admission-record save
also blocks invocation. Do not retry automatically or reclassify a later executor
failure as NOT_EXECUTED. The original post-execution validator remains unchanged.

## Actual interfaces and transport contract

`decision_kernel.runtime.external_research_admission` provides:

- `check_source_preflight(plan_raw, report_raw, now=...)`: usable before any input
  exists; validates recorded accessibility and dynamic inventory coverage.
- `prepare_input(...)`: parses the installed original model, recomputes the key,
  checks preflight, seed publication and #288. Returns an immutable PreparedInput,
  which is **not launch permission**.
- `admit_committed_input(...)`: reads exact committed bytes, reparses them,
  checks the original canonical key and commit clock, revalidates the preflight,
  and reloads the currently pinned identity catalogue before admitting execution.
- `freeze_and_execute(...)`: the trusted writer/retention/executor call boundary.
  Only a complete successful admission reaches its supplied executor callback.

Callbacks are provided by the trusted caller, never by repository/source prose:

```python
admission, output = freeze_and_execute(
    proposed_input_bytes,
    read_file=read_exact_github_file,       # spec -> bytes; exact repo/ref/path
    catalogue_source=resolve_catalogue,    # fresh exact source spec, not 'latest'
    commit_metadata=read_git_commit,       # (repo, sha) -> actual Git commit JSON
    commit_input=write_isolated_input,     # PreparedInput -> exact committed spec
    retain_admission=save_admission_record,
    executor=run_explicit_external_case,   # receives parsed packet + admission
    now=utc_clock,
    environment_id=current_preflight_environment,
    code_commit=installed_trusted_code_sha,
)
```

Git source specs carry `repository`, full 40-hex `ref`, `path`, `git_blob` and
optionally `sha256`; #288's byte/source checker is reused. `commit_input` writes
only `PreparedInput.raw` to `packet.candidate_output_prefix + 'input.json'`, then
returns the resulting immutable source reference. `commit_metadata` is Git's
commit object with `sha` and `committer.date`, not a caller-invented timestamp.
The record includes both preparation and admission clocks. Git commit timestamps
have second resolution; comparisons preserve that precision rather than inventing
subsecond publication clocks. The wrapper reuses already fetched exact sources;
it never inserts local proposed input bytes into the remote readback cache.

For a Web ChatGPT integration with tool calls between phases, run prepare on the
installed package **before** the GitHub write, preserve that exact PreparedInput,
then run admit against actual fresh tool readbacks before any Research tool call.
Save the admission before proceeding. Do not use a CI result received after Web
Research started to retroactively authorize that execution. CI is an engineering
check, not a replacement for this per-case live boundary.

## Bound plan and preflight, without changing the input schema

The input's existing `source_refs` bind exactly one source of each purpose:

- `PRE_EXECUTION_REQUIRED_SOURCE_PLAN`
- `PRE_EXECUTION_ACCESSIBILITY_RECORD`

These are small, pinned Harness records, not seed or supplemental Research
Evidence. The report binds the plan file's SHA256; the input canonical hash binds
both source references. A changed plan, missing class, different environment,
expired check, unretained journal, wrong source identity or changed bytes rejects
admission. Human-defined source requirements cannot be silently shortened to make
an execution pass; determining that the plan matches the question remains review,
not a claim that JSON validates semantic completeness.

Plan fields are `schema_version=1`, `case_id`, `security_id`, `environment_id`,
`expires_at`, and `required_classes`. Each class specifies `id`, `kind` (STATIC or
DYNAMIC), and `subject_ids` for issuer/peer/official bodies. A dynamic class also
specifies `window_start`, `max_queries` (1..32) and `max_leads` (0..128). This is a
predeclared accessibility bound, independent of the formal Research budget.

The report has the same case/security/environment, `plan_sha256`, `started_at`,
`finished_at`, `provenance_status=RETAINED_ACTION_RECORDS`, and exactly one `classes`
row for every required id. Each row records `status=ACCESSIBLE` and `reads`. Each
read records `subject_id`, `source_identity`, primary `authority`, exact `locator`,
`body_kind=SUBSTANTIVE_BODY`, `read_status=SUCCEEDED`, `checked_at`, and the actual
`tool_return_reference`. A directory, shell, snippet or secondary transcript does
not satisfy a primary-body requirement. This phase records access/identity only:
no ResearchClaim, WAIT/STOP/DEEPEN, company judgment or investment conclusion.

DYNAMIC classes must additionally include an `inventory` with declared
`window_start`, `checked_through` inside the preflight, `truncated=false`, actual
bounded `queries` and all discovered `leads`. Each successful query records its
query text, check clock and return reference. Each lead points to its discovering
query. REQUIRED and UNKNOWN leads must have a primary locator in successful reads.
An OUT_OF_SCOPE lead requires an explicit identity/date/duplicate exclusion and
basis reference; an adverse or inconvenient business implication is not a reason
to exclude it. Empty leads with actual bounded queries means only no lead found
in that inventory, **not proof that no later disclosure exists**.

The three named latest-update classes cannot be disguised as STATIC. Custom
latest-update requirements must also be declared DYNAMIC. Preflight finishes before
selection/cutoff; all checks must remain inside the explicitly declared validity
window. No background discovery, unbounded search or calendar service is added.
Formal Research must reread its sources and form lawful Evidence after admission;
preflight body reads are not automatically research Evidence or research budget.

## Seed publication and identity

This initial ingress supports **retained Git observation seeds**. For each seed,
its locator must match a pinned input source reference; exact source bytes are
read and their SHA256 must equal the seed content hash. Its `published_at` must
match the verified commit clock of that selected retained edition. Availability,
retrieval and cutoff must preserve order. This is not the original market day,
underlying company-event time, earliest-ever observation or inferred disclosure
clock. Missing/null/unproven dates reject INPUT; no 'reasonable' date is filled.
Unsupported publication proof forms reject at this ingress; the original Evidence
schema and post-execution validator are neither changed nor weakened.

Identity uses #288 `ExecutionKey` and `ExecutionScope.require_unambiguous` throughout.
Pre-write adds the proposed key only to a provisional checked set. Post-write
rebuilds the original #288 scope from the pinned catalogue plus the real committed
input reference. No key-only provisional set grants execution/promotion rights.
The admission records the catalogue reference and the augmented scope hash. It
does not edit `research_runs/execution-inputs.json` or the handoff registry. Later
promotion still requires the appropriate current catalogue and Human approval.
A known conflicting id blocks both sides, including when the conflict appears
between preparation and readback. Unrelated historical conflicts do not block
otherwise unambiguous new identities. No preferred-input or bypass flag exists.

## Receipt and limits

Admission has zero formal research use because it precedes execution. After
invocation, preserve the original receipt fields and action journal as actions
happen. Count `successful_read_events` separately from
`distinct_research_source_bodies` (exact source/body identity). Repeated sections,
headings, indexes, shells and input reads do not increase substantive source
breadth. If the original journal is lost, mark **PROVENANCE_INCOMPLETE**; do not
reconstruct a full execution certification from memory. Missing necessary sources
after legitimate admission still lead through the original incomplete-execution
validator to EXECUTION_GAP, not completed WAIT/STOP.

This is a trusted Harness boundary, **not a hard permission sandbox, global lock,
all-branch discovery service or proof of web truth**. A forged transport/record or
a privileged caller bypassing the wrapper is outside its enforcement. Native
source accessibility and source-plan adequacy still need actual tool evidence and
review. Reusing a saved ALLOWED report is not permission to rerun an execution.
Budget enforcement and executor provenance retain their explicitly declared limits.

The existing single-pair validation CLI audits outputs; it cannot authorize a new
execution. Source instructions never determine callback functions, tools or write
scope. No formal Research, Human state, authority, market budget, 18:13 cron,
recovery, state/ledger or workflow trigger changes are part of this gate.
