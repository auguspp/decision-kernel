# Woton H1: retained-byte representation repair

Scope: #297/5754250159, after the approved source-only custody slice #481.
Reuse Decision: **THIN_ADAPTER**. No source/market/model request or new research
question is authorized by this repair. Reuse the exact saved PDF, original parser,
permission/main check, native Retainer and existing isolated Stock source job.

## Actual first attempt, not erased by the repair

Run35550930725/job106185415174 on main
aedf5160c344204b3595687c152c750af9cba0a3 was `failure` at
FULL_PDF_REPRESENTATION / REPORT_PRINTED_IDENTITY. Its single ordinary source GET
returned HTTP200 and the original bytes were successfully written and read back
before that failure. Artifact10618043542 is1155223bytes, SHA256
1a6176f57dd30c511183a0bf01911a8a1af2a379c434ff4b0737e860c7897d07.

The actual133-page PDF's cover has the issuer name and period, but no stock code.
Code000920 is in the company-profile table on p6. Both pages were rendered and
visually checked. The initial implementation and synthetic test assumed the code
was on the cover; this was our validation/test defect, not a source outage or a
wrong PDF. Preserve the failed run and its exact record.

The printed identity check now reads the cover's period/title and a code within
the first six pages. The exact original1262185-byte SHA256 check,133-page complete
parse, every-page text safety and all existing byte budgets are unchanged. The
same original PDF Git blob is reused as an offline regression fixture, not a new
source download, new observation, duplicate binary upload or economic acceptance.

## Zero-source-I/O repair

The same source-only job additionally accepts one fixed label,
`woton-h1-representation-ready`, on issue297 from auguspp. All original Research
jobs remain dispatch-only. Python routes ONLY that exact issues label to
`woton_report_representation.run`; the original acquisition path and no-retry
behavior stay separate. The source scope, original permission and expiry are
checked again on trusted main before and after the create-only repair marker.

The repair accepts only the exact original prepare/failure/PDF refs below and an
otherwise unmodified three-file source directory. It verifies both the fixed
history and the current directory's matching bytes, then saves a new
`representation-repair.json`. Existing repair markers block repeat work. It
writes only the new marker, extraction and manifest; it never rewrites the
original prepare, failure or PDF. An additional technical failure uses a separate
`representation-failure.json`. Uncertain mutations stop subsequent writes.
The existing small source adapter admits only those two additional metadata
filenames; the shared Research Retainer's OUTPUT_NAMES contract is not changed.

The final manifest's source_requests=1 refers to the ORIGINAL acquisition and its
original requested/received timestamps. Its representation_repair section and
new host receipt explicitly record zero new source requests and bind the retained
failure plus repair marker. The normal recover function verifies those bindings
and rebuilds the complete representation from the exact original bytes.

No artifact-supplied code, LLM, source HTTP, fallback, producer rerun or scheduler
is used. The new source job still has no model/market credential. The original
publisher event guard is unchanged; issues-triggered work is not falsely counted
as a normal publication.

## Exact original custody for recovery

Repository: auguspp/decision-kernel. Existing work ref:
research-work/stock-business-v0. Prefix:
research_runs/sources/public-reports/27c74e31c8aaf5a38d27b688f0841d81797816420b591647bfb6763e485b7728/.

| Original file | Exact commit | Git blob |
|---|---|---|
| source.pdf | 7ec7eee11ac61aecdf05940904631a47cc07436a | 87b56650d5ec01935e94e97d9e60ad986cb378d1 |
| prepare.json | 14d2efc0fd2f741bf6496721823a42028b40eae2 | 1ff1968388e4393cbb4c2a5f6591376533105780 |
| failure.json | 75f3b7e88037d1eb8c2558b9a981ccb25d4dd17a | f45c0d6d004cc67145218df27dc43de11169c4b0 |

PDF SHA256:
27c74e31c8aaf5a38d27b688f0841d81797816420b591647bfb6763e485b7728.
Failure831bytes/SHA2562e29dfe9c00f591dec9231197b07fac204ad9fa4fab188d8ed605fb3fa01ebff.
Prepare1231bytes/SHA256890156d755d07bea8e8c75f465b7c0d76f9263a953bc795001f9ab63947adca4.
The mirror is an issuer report; equality with CNINFO1225486931 is not established.
No DataSinking service fulltext is included or redistributed.

This document is also the lightweight raw-source locator. Its GitHub publication
does not materialize the PDF in current-state.json, mark the original failed run
successful, or imply that representation repair has executed. The source PDF can
already be read at its exact original ref with commit/path/size/blob/SHA256 checks.
When reading later repair results, resolve the work ref once, inspect the
create-only source.json at that fixed commit, and use the existing checked
recover function; the manifest may not exist before repair acceptance. Exact
repair-run/manifest/readback evidence belongs in the #297 appended close-out.

## Test and release evidence

The actual saved PDF and original prepare/failure are included as fixed offline
fixtures. New tests cover the real p1/p6 layout, unchanged hash, complete133pages,
original/future ref bindings, zero-GET repair and recovery, no original-file
mutation, duplicate repair/acquisition suppression, missing/tampered predecessors,
permission/expiry, lost writes and exact CLI event routing. All original tests and
original acquisition assertions remain. Local relevant suite123passed/25.39s;
this is the documented historical checkout with exact relevant current files,
Python3.13.5/pytest9.0.2/pypdf5.9.0, not full local main or CI. Initial local repair
regressions exposed the shared Retainer's fixed-name guard (3failed/112passed);
the small existing source adapter now handles only the two explicit source
metadata names, without widening the shared Retainer or deleting tests.

Full exact-head CI, clearly labelled same-model review, independent mainCI and
normal publication must pass before the one explicit zero-GET repair event.
Actual source Git readback and repair success are not predeclared. The original
Woton financial question, r1/r2 progress and other failures are preserved.
Daily NEW_DISTINCT/STATIC/CNINFO and model-egress boundaries remain unchanged.
This is neither Pre/Quick, COMMITTED/Full Research, Human acceptance, Odds/Watch,
nor completion of the P0 daily Research/Brief/response loop.
