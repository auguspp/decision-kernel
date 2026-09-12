# P0-4B: one prepared disclosure, using the existing executor

Status: ENGINEERING SLICE / NOT DAILY DEPLOYMENT / NOT RESEARCH ACCEPTANCE.
Main Construction authority: #297; pre-construction Reuse Check: comment 5644717422.
Reuse Decision: **THIN_ADAPTER**. No new Kernel entity, Funnel, model loop,
provider, scheduler, dependency or semantic-approval service.

## What was actually missing

`incremental_disclosure` already owns the bounded six-company FIFO and work-key
reservation. `external_research_admission.execute_after_admission()` already owns
fresh admission. `saved_research_once.research()` already accepts a packet,
Discovery and context; copying/extracting another Pre/Quick loop is unnecessary.
Its surrounding production host, however, is deliberately fixed to the authorized
Suken experiment. Do not remove those guards to make it look generic.

The first reusable ingress is `runtime.prepared_disclosure_research.run_prepared`.
It consumes a prepared, committed original input; it does not prepare it, select a
company or discover sources. It reuses the original Retainer, admission, research
loop and disclosure outcome validator. Existing files and Suken history are unchanged.

## Exact supported path

1. A trusted caller supplies current tested `code_commit`, exact `input_source`,
   original `expected_key`, a separately approved public-egress digest and an empty
   local output directory, using the existing bounded GitHub client.
2. Read/validate the original `ExternalResearchInputPacket`; require its original
   `CNINFO_INCREMENTAL` lane, an existing allowed company, and a packet already
   reserved on `research-work/disclosures-v0` at the original assessment key.
3. Read exactly one source for each required purpose: `INCREMENTAL_DISCLOSURE_PACKET`,
   `MODEL_CONTEXT`, `PREPARED_DISCLOSURE_DISCOVERY`, and
   `PRE_EXECUTION_SOURCE_PREFLIGHT`. Discovery is an original `DiscoveryInput`,
   not another schema. Its identity, source lineage and commit clock are checked.
4. Require one context bundle / one matching seed Evidence. The existing loop
   attributes its context read to the first seed; arbitrary multi-seed packets
   are therefore **not** supported. `context.disclosure_packet` must equal the
   complete original parsed reserved packet, without substituting or clipping it.
5. Verify the separately approved digest against exact input identity, Discovery
   and context. This digest binds potential prompt material, not provider HTTP
   bytes, an independent fact check, or proof of Human consent. Approval and data
   minimization belong to the trusted caller. Permission prose in other source
   refs is not read or sent as model context.
6. Check original admission before mutation, create/read back `launch.json` with
   the existing native create-only Retainer, then invoke **fresh original
   admission again** after that I/O. A stored PASS cannot launch the executor.
7. Only its fixed callback calls `saved_research_once.research()`: one Pre, at most
   one conditional Quick, no model tools, no technical retry or forced route.
8. Revalidate the reserved disclosure-to-output binding using the existing
   `describe_outcome`; retain the original candidate, receipt, validation, optional
   Funnel, generic reading and host receipt through the existing Retainer.

Discovery identity and execution identity remain different concepts. There is no
requirement that their names coincide. Kernel still validates identity/time/source
consistency, not the truth of the supplied public material or model interpretation.

## Bounds and failure behavior

Supported declared budget: 3–6 formal tool events, 3–4 successful reads, zero
searches/retries, 15 minutes, with the existing `SOFT_EXECUTOR` declarations.
The underlying SDK retains its existing model, endpoint, per-call timeout,
64 KiB prompt bound and 6,000-output-token ceiling. No new provider setting is added.

The trusted host still owes its wall-clock limit and explicit spending authority.
This function does not install a process alarm, claim a monetary cap, or confer
hard enforcement by relabeling a soft budget. Unsupported `HARD_RUNTIME`
claims and shapes fail before spending. Preparation/Git I/O are distinct from
formal model-stage events; the receipt does not claim a global tool journal.

An existing launch marker or any retained execution/admission/result/failure record
prevents execution, including older executors that did not write launch.json. Concurrent create failure or uncertain mutation stops; no overwrite,
rollback, timeout reset, different-key escape or automatic retry. Missing/malformed
reserved bytes are not an empty history. Source/preflight failures stay NOT_EXECUTED;
provider execution failure retains the original EXECUTION_GAP, never a completed
WAIT or manufactured Funnel. Failure to retain the host receipt is separately
RETENTION_INCOMPLETE. Raw partial local outputs remain available to the host.

## Deliberately not deployed in this slice

There is **no CLI or workflow hook**, no enabled request, and no new scheduled task.
Import/merge/CI cannot call a model. A trusted authorized host must explicitly invoke
the function. The old Suken workflow/request/launch markers remain exactly as before.

This does not close the complete P0 loop. Still required:

- Source/input preparation for a genuinely new lawful question and an explicit
  daily source/spend policy before any unattended execution is enabled.
- A P0-5B retained-candidate publication binding into the existing current-state
  reader, preserving execution identity and raw result. Displaying an unreviewed
  candidate is not semantic acceptance or registered DEEPEN attention. Empty
  `additional_registered_handoffs` is not itself a bug to fix by auto-promotion.
- P0-6B exact Human permission / prior result / new discriminating input binding.
  This adapter does not reset an old reserved key to simulate continuation.
- An actual run, exact remote readback, semantic review, natural Brief delivery,
  a genuine Human response and the prescribed real trading-day observations.

## Verification scope

Forty-eight new synthetic cases call the **original** admission, identity, packet,
Pre/Quick, Funnel and Retainer code with fake GitHub/model I/O and denied sockets.
They cover three issuer identities, all terminal routes, no Quick after Pre WAIT,
input/context/seed/egress mismatches, future Discovery, unsupported budgets,
original admission rejection, conflicts, main movement/expiry after marker,
concurrent launches, uncertain writes/readback, preserved historical bytes and
private permission refs excluded from model context.

Regression-first review found that historical results without launch.json also
needed to block spending: all eight new legacy-record cases failed before that
correction. Local related suites after the correction: 193 passed, 1 skipped. Pydantic matches the repository pin;
pytest/requests/pypdf differ, and the official SDK is absent locally, so its existing
SDK transport test is skipped. This **does not replace exact-head full repository
CI**. These are engineering tests, not a new company Research result or proof of
unattended operation. No live source, market or model request is part of this slice.
