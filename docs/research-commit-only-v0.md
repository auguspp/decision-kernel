# 321-A first slice: retain and commit an existing Research package offline

Status: bounded Harness ingress; not complete Direct Deep adoption.
Authority and Reuse Check: [#321 comment5683100225](https://github.com/auguspp/decision-kernel/issues/321#issuecomment-5683100225).
Reuse Decision: **THIN_ADAPTER**. No new Kernel entity, commit validator, Research
executor, dependency, workflow, provider, registry or scheduler.

## What this actually closes

`research_commit.commit_research_package()` already commits independently of
Market. The existing `run-research` CLI composes that commit with live Market and
Decision Spine; a later Market exception prevents that composition from returning
the in-memory commit result. It is not a reliable Research-retention boundary.

Use the new explicit offline module for an **already prepared, eligible** generic
`ResearchCommitPackage`. It saves the original package first, applies the original
Kernel commit checks, saves the typed `ResearchCommitResult`, then reads it back.
No `live`, `workflow`, market client, source downloader or model client is invoked.
The existing `run-research` behavior is unchanged, not silently redirected.

```sh
python -m decision_kernel.runtime.research_commit_only commit \
  /path/to/reviewed-package.json --output /path/to/new-retention-directory \
  --execution-receipt /path/to/original-research-execution-receipt

python -m decision_kernel.runtime.research_commit_only verify \
  /path/to/new-retention-directory
```

`--execution-receipt` is optional. It copies only an explicitly supplied original
file, verbatim, as `RETAINED_UNVALIDATED`. Absence stays absent. Neither an opaque
file nor this commit operation is proof of a prior research execution, a valid
external Pre/Quick receipt, source completeness, independent review or consent.
The caller must preserve the original receipt's source/identity when publishing.

## Supported input, without inventing missing Research

The original generic package and all original Evidence/PIT/bundle/commit checks
are unchanged. The complete supplied JSON, including Evidence metadata, open
questions, assumptions and method fields already present, is retained verbatim.
The typed committed snapshot differs only as the original commit function permits.

**This is not a Markdown-to-Kernel converter.** The current legacy snapshot commit
contract still requires the existing scenarios and probabilities summing to one;
the generic package also requires its existing rehearsal framing. Do not invent
probabilities, framing, Evidence, timestamps, Human acceptance or fake Pre/Quick
lineage to fit an ordinal-only Full Research into that contract. Such a package
remains retained/rejected, not COMMITTED. Supporting research-only readiness
separately from numerical Odds readiness is a remaining #321 semantic boundary,
not something this adapter or a green CI silently changes.

Evidence URLs and original-document locators remain pointers. This command does
not download, re-review or separately retain their PDF bodies. Preserve existing
exact original-document archives and their bindings using the existing retention
process. A package hash does not certify the source's economic truth.

## Exact files and failure stages

| File | Meaning |
| --- | --- |
| `input.json` | Exact input bytes, saved before original commit validation. |
| `research-execution-receipt.bin` | Optional original receipt bytes; unvalidated, not executable. |
| `retention.json` | Byte counts/SHA256 and actual retention-operation clock. |
| `research-commit.json` | Original typed Kernel commit result, if checks succeed. |
| `commit.json` | Commit-operation receipt, written last; not a research-execution or Human receipt. |
| `commit-rejection.json` | A rejected input's safe error class and retained-input binding; no successful commit. |

Each input/output file is bounded to 512 KiB for this ingress. This is a local
representation bound, not a new daily API quota. Oversized/missing/nonregular
inputs are not saved by this adapter; they are not truncated or reconstructed.
Malformed JSON within the bound is saved unchanged before rejection. Duplicate
JSON keys and non-finite numeric constants are rejected. The optional receipt is
not parsed as JSON or instructions, regardless of what its bytes say.

The output directory must not exist, even if empty or left by a failed attempt.
Native `mkdir(exist_ok=False)` reserves that path; all files use exclusive `xb`,
flush/fsync and exact readback. Existing files and partial failures are not erased,
overwritten, resumed or automatically retried. Symlinked inputs/outputs/parents
are refused. An I/O failure can leave a partial directory; it is not a verified
commit. The read-only `verify` operation is not a new research attempt.

Successful verification requires the exact inventory, input/receipt/result byte
bindings, fixed authority fields and equality with the result of the **original**
commit function on the retained input. Rehashing a changed result alone does not
make it valid. A later separate Market failure cannot erase this retained result.

This is create-only per local output path, not a repository-global uniqueness
service, atomic whole-directory transaction, signature or adversarial-filesystem
sandbox. A caller controlling all files can construct a different internally
consistent bundle; external immutable Git/source identity remains necessary.

## Clocks, authority and GitHub publication remain separate

The original package's `proposed_committed_at` is not rewritten. It must satisfy
the original chronological checks and cannot follow this actual retention
operation. Applying the deterministic commit function to a historical package
now does **not** prove it was executed at its proposed historical timestamp.
`retained_at` records this operation separately; verification never refreshes it.

A successful local operation reports:

```text
Research result: COMMITTED (original generic Kernel contract)
Market: NOT_REQUESTED
Odds: NOT_COMPUTED
Human acceptance: NOT_ESTABLISHED_BY_THIS_OPERATION
Investment authority: NONE
Publication: LOCAL_ONLY_NOT_GITHUB_PUBLICATION
```

Local retention is not GitHub retention, registration or publication. The
interaction layer still owes the existing create-only Git write of the exact
files to an authorized archive path/ref, its exact code/source provenance,
readback, and any separately authorized purpose registration/publication. Until
that happens, report the actual local-only / NOT_SAVED / PUBLICATION_PENDING
stage; do not say the company is in current-state or monitored. Do not merge a
research work tree into main just to publish these files.

The verifier cannot authenticate the execution environment, a historical clock,
semantic eligibility or Human approval from these self-contained files. Do not
promote old/challenged snapshots as current simply because byte checks pass.

## Verification and remaining work

Synthetic regressions reuse the original generic-package fixtures and commit
validator. They cover original rejection behavior, missing receipts, unchanged
UNKNOWNs, false authority, malformed/tampered bytes, no-future time, exclusive
creation, symlinks, size/I/O failure and original-result recomputation. An isolated
Python process runs the real module entrypoint with sockets and optional
model/document/market imports denied. The existing CMB illustrative dogfood
package checks compatibility only, without fetching sources or changing its
historic scenarios. It is not a new Full Research or probability calibration.

A first import-isolation regression exposed that the existing private external
Research JSON helper imports the unrelated Funnel/Decision Spine. This adapter
uses standard-library JSON hooks directly rather than weakening that regression
or refactoring the external executor. Existing case-specific Retainer guards stay.

Full exact-head PR CI, independent main CI and ordinary publisher/readback remain
separate acceptance steps. This slice does not implement ordinal-only Kernel
commit readiness, an automatic remote archive/registration host, #321-B price-only
Odds consumption or #349 Watch. It does not close #321 or count P0 live-use days.
