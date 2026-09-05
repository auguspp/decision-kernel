# Next handoff — context delivery and official-page capture

Date: 2026-09-05. Repository: `auguspp/decision-kernel`.
Authority: SHADOW OBSERVATION ONLY / HUMAN ATTENTION NONE / RESEARCH NONE / INVESTMENT NONE.

## Read and verify first

Read `docs/project-state.md`, this handoff and both independent proof records:

- `docs/sector-radar-live-bootstrap-restore-proof-2026-09-05.md` — last real market-state validation/restore;
- `docs/economic-source-raw-capture-proof-2026-09-05.md` — first public-page capture, explicitly incomplete.

Verify current main, open PRs/issues, workflow directory and kernel-tests. Do not equate a green kernel test run with all live source workflows being green. Current implementation baseline before this state-only synchronization is `1c19360e5b400933339f452ba159117d5a8408e2`; its kernel CI `33947395988` succeeded, but economic source run `33947395994` failed.

## Merged in this round

### PR #198 — deliver read-only context

```text
base = 31c6df90ab91a24c23ed253cb38adda49dfe3d39
head = a98865680095e1f3a00e4785b8b832fbc2d43872
merge = a01267e9377b11b9303d95850b606b5d4079a795
PR CI = 33946611323 / success / 468 passed
main CI = 33946763758 / success
```

Exact files:

```text
.github/workflows/sector-radar-shadow.yml
tests/test_sector_radar_context_artifact.py
docs/sector-radar-read-only-context.md
```

The existing manual workflow now renders saved state after producer calculation, before remote state/cache publication. `context/index.html` and `context/context.json` join the existing complete run artifact. Summary links only a successful render plus actual uploaded artifact URL. No public website, schedule, new alert or provider request. Rendering failure blocks remote publication without pretending the already-calculated local bundle was remotely committed. The projection is outside the sealed calculation replay inventory.

Actual live Sector context publication has not occurred yet.

### PR #199 — original public-body capture and offline verification

```text
base = a01267e9377b11b9303d95850b606b5d4079a795
head = bc4c3c460e1f2a25d88ca29a411ee4296412b64d
merge = 43305d60e3f4b73fe5831dbd1664f9dca5de70e9
PR CI = 33947099486 / success / 502 passed
main CI = 33947259762 / success
```

Exact files:

```text
src/decision_kernel/runtime/economic_source_capture.py
tests/test_economic_source_capture.py
tests/test_economic_source_capture_transport.py
docs/economic-source-raw-capture.md
```

Bounded exact official URLs only, four pages maximum, one request each, 2 MiB/body and 20 MiB/archive. No credentials, cookies, redirects, proxy credentials, retries or fallback. Original response bytes, safe metadata and actual clocks are retained. Reconcile existing reviewed excerpts and rebuild study observations; do not interpret this as automatic new-release discovery. Successful and rejected bindings are independently reproducible; original snippets and market events are never rewritten.

### PR #200 — independent public compatibility workflow

```text
base = 43305d60e3f4b73fe5831dbd1664f9dca5de70e9
head = 8c9310c472718438131b8ef64f8489ca94808d1b
merge = 1c19360e5b400933339f452ba159117d5a8408e2
PR CI = 33947331766 / success / 506 passed
main kernel CI = 33947395988 / success
```

Exact files:

```text
.github/workflows/economic-source-capture.yml
tests/test_economic_source_capture_workflow.py
docs/economic-source-compatibility-operations.md
```

Maintained probe runs by manual main dispatch or narrowly path-filtered main pushes affecting capture code, study parser, reviewed source list or workflow. No clock schedule and no pull-request trigger. It is not a self-modifying temporary repair. It uses no repository secret, market cache, state or candidate ledger. Attempt-specific proof artifacts retain failures as well as successes for 90 days.

## Real proof result — do not erase the failure

```text
run = 33947395994 / economic-source-capture #1 / attempt 1
source requests = 4, each once
SPB accepted original pages = 2
MOA original pages = 0; both requests HTTPError
aggregate = INCOMPLETE
workflow conclusion = failure
artifact = 9963755766
capture integrity = VERIFIED, still INCOMPLETE
```

The ZIP, inventory/file hashes, source/provenance clocks, original body text and selected-fragment offsets were checked after download. Recorded workflow verification reconstructed the study outputs. Numeric HTTP status was not preserved for the MOA failures: do not guess 403/404/5xx, revision, access control or permanent unavailability. Next diagnosis should add safe numeric status evidence, not repeated favourable-result fishing or source fallback. Old raw evidence and reviewed excerpts remain untouched.

The proof is for two previously reviewed SPB pages, not continuous economic monitoring, historical first-vintage authenticity or company profitability.

## Unchanged live market state and next P0

The last real Sector run remains #4 / `33939414197` on `5f8f635d191dd8559844d1b74af0dca0cf4c02df`. Market state still ends 2026-09-04; prospective candidate ledger is empty. Neither public-source workflow nor these code merges creates a new market session.

Bootstrap identity remains canonical only in `radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json`; do not duplicate an independently maintained hash here.

Next market proof is a fresh main Sector dispatch after the next completed session, targeted for 2026-09-07 and independently established by the provider calendar/prices. Require exactly one-session append, all cached-close/prev-price matches, complete audit, exact state/event persistence and real read-context attachment. Download the input audit and replay at its recorded implementation. Zero candidates is legitimate. More than one missing completed session requires separate qualified recovery, not a daily-producer bridge.

Do not request another same-session run merely to repeat the old proof. No Sector schedule before this new-session verification. Adding a future schedule must also update previous-success lookup, which currently filters workflow_dispatch.

## Still pending beyond that proof

Real HiThink stock dump entitlement/download/Parquet execution, overlapping vintages and corporate-action qualification; multi-day breadth; benchmark sensitivity; new economic-release discovery and continuous capture; company economic exposure mapping; objective T+5/T+20 records and separate Human annotations; long-term checkpoints. Do not call these complete because their precursor tools exist.

Company decisions, Research reopen conditions and canonical Human attention lanes remain as in project-state.md. No market-price-to-fundamental-belief shortcut, no Recommendation/Action and no new investment authority.
