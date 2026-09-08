# P0-4A external Pre / Quick execution seam

Status: **engineering seam only until a real bounded execution is attached and validated**.

This is Harness code around Research Method v1. It does not sense the web, fetch market
data, change the Kernel Constitution, create Human attention, register a Research handoff,
run Deep Research, compute Odds, or make an investment decision.

## One-case flow

```text
explicit saved observation + exact current-state commit
    -> ExternalResearchInputPacket (cutoff + budget frozen before execution)
    -> external Web-capable executor actually searches and reads
    -> isolated ExternalResearchCandidate + execution receipt
    -> external_research_execution validator
    -> existing run_research_funnel()
    -> validated WAIT / DROP / DEEPEN_REQUIRED, or an explicit EXECUTION_GAP
```

`run_research_funnel()` remains authoritative for the Discovery / Pre / Quick transition.
The new module only binds the external candidate to one exact input, checks the execution
envelope, and calls the existing validator.

## Candidate isolation

Real candidates belong under:

```text
research_runs/candidates/<case>/<execution-id>/
```

A candidate branch or commit is not a formal Research record. Do not write candidates into
`research_cases/`, `docs/decisions/`, `current_state/registry.json`, or a production workflow.
Demand-side acceptance is required before any existing explicit handoff-registration
mechanism is used.

The engineering test scans committed `candidate.json` files under this prefix and runs the
same validator. It also compares the deterministic Funnel result with the adjacent
`funnel.json`.

## Input identity and time

A packet freezes:

- exact code commit;
- exact P0-3 current-state commit and reported reading hash;
- exact repository source references;
- ticker / security identity and source lane;
- seed Evidence for the saved observation;
- selection time and one research cutoff;
- method and prompt version;
- allowed read tools;
- output prefix;
- budget.

Discovery, Pre and Quick all use the packet cutoff. Quick must bind the exact canonical
Pre hash. Supplemental Evidence is rejected if it was not available by the cutoff. Its
`retrieved_at` must fall inside the actual execution receipt.

A later retrieval time does not authorize guessing an earlier `available_at`. If a dynamic
page's version at the cutoff cannot be established, retain it in the receipt as excluded or
unknown rather than manufacturing qualified FACT evidence.

## Budget and receipt

The first real execution must declare these values before research starts:

- maximum tool calls;
- maximum search queries;
- maximum successful source reads;
- maximum technical retries;
- maximum elapsed minutes.

Each limit says whether it is `HARD_RUNTIME` or `SOFT_EXECUTOR`. Post-hoc validation rejects
a candidate whose recorded use exceeds either kind. Calling a prompt instruction a hard
runtime limit is not allowed.

The receipt stores action records, not private reasoning. It distinguishes a platform/tool
return reference from an executor action summary. Source dispositions say whether a source
was actually opened and whether it entered Evidence. A source marked as Evidence must have
a successful read event and a real Evidence id.

No platform task id or exact model version may be invented when the environment does not
provide one.

## Incomplete execution is not a route

`INCOMPLETE_BUDGET`, `INCOMPLETE_SOURCE`, and `INCOMPLETE_TECHNICAL_FAILURE` produce an
`EXECUTION_GAP`, never a quiet result or `DROP_FOR_NOW`.

A completed Pre with `CONTINUE_TO_QUICK` and a missing Quick can be retained only as an
incomplete execution gap. A candidate marked `COMPLETE` with that shape is rejected by the
existing Funnel. Conversely, Pre `WAIT_FOR_TRIGGER` or `STOP` cannot carry a Quick.

A valid Quick `DEEPEN` still only means the existing Funnel returns
`DEEPEN_REQUIRED`; it does not run Deep automatically.

## Source instructions are data

`tests/fixtures/p0_4a_untrusted_source_injection.txt` is independent adversarial test
material. The input packet keeps it outside qualified source refs, and the validator refuses
to promote a supplemental Evidence locator that points to this fixture.

That deterministic boundary is not a claim about model behavior. The real P0-4A execution
must separately read the fixture alongside normal material and record whether the actual
executor preserved its tool and write boundaries. Total refusal to read normal evidence is
not a passing model-behavior test.

## Runtime commands

Generate schemas from the installed models instead of maintaining a hand-written duplicate:

```bash
python -m decision_kernel.runtime.external_research_execution schema \
  --output /tmp/p0-4a-schema.json
```

Validate one isolated candidate:

```bash
python -m decision_kernel.runtime.external_research_execution validate \
  --input research_runs/candidates/<case>/<execution>/input.json \
  --candidate research_runs/candidates/<case>/<execution>/candidate.json \
  --output /tmp/validation.json
```

The command performs no web access and no market or Research execution.

## Acceptance layers

Keep these separate:

```text
ENGINEERING / MINIMAL RUNTIME
REAL PRE EXECUTION
REAL QUICK EXECUTION
DETERMINISTIC FUNNEL VALIDATION
REMOTE CANDIDATE / RESULT READBACK
DEMAND-SIDE SEMANTIC ACCEPTANCE
```

A legitimate Pre WAIT/STOP can close the real Pre layer while leaving REAL QUICK EXECUTION
untested. Engineering CI cannot fill that gap.

P0-1 natural Sector schedule acceptance, P0-2 natural page publication, P0-3 producer-event
refresh, and fully unattended recovery remain independent. This batch does not modify the
18:13 schedule or market acquisition.
