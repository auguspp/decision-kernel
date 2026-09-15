# Research commit-only: retain and freeze Research independently

Status: bounded offline ingress, now accepting explicit Research-only schema v2; not complete Direct Deep adoption.
Contract separation / Reuse Decision **REUSE**: [#321 comment5689340004](https://github.com/auguspp/decision-kernel/issues/321#issuecomment-5689340004).
The original ingress remains a thin adapter; the versioned core separation is described below.
Authority and Reuse Check: [#321 comment5683100225](https://github.com/auguspp/decision-kernel/issues/321#issuecomment-5683100225).
Original ingress Reuse Decision: **THIN_ADAPTER**. No new Kernel entity, commit validator, Research
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
The existing `run-research` still composes Market/Decision Spine, not retention.
It now rejects missing numerical/context prerequisites before requesting Market.
Use this offline command first when independent Research retention is required.

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

The existing generic package, exact Evidence/PIT/bundle/chronology checks and
commit function are reused. Versioned readiness, not source truth, changes below. The complete supplied JSON, including Evidence metadata, open
questions, assumptions and method fields already present, is retained verbatim.
The typed committed snapshot differs only as the original commit function permits.

**This is not a Markdown-to-Kernel converter.** Legacy schema v1 retains its
numerical scenarios, probability sum, valuation horizon, market-expectations text
and rehearsal framing prerequisites. Explicit schema v2 provides Research-only
freeze without inventing those fields. Raw or unfinished work still belongs in
[save-progress/read-progress](research-progress-v0.md), not an automatic COMMIT.

## Research-only schema v2

This is a versioned **Kernel contract** change, not Full Research Method v3 or a
new ResearchStatus. Both snapshot and package default to schema v1; the caller
must explicitly prepare the appropriate v2 package. Do not relabel saved v1
failures, dates, Research or Human acceptance to make old results pass.

| Boundary | Required / permitted |
| --- | --- |
| Snapshot v2 COMMIT | REVIEW, explicit nonblank thesis and model-risk notes, nonempty invalidation, exact information bundle, original source/identity/PIT/child/chronology consistency. |
| Not required for v2 Research-only freeze | Numerical scenarios, valuation horizon, market-expectations narrative; package v2 may omit rehearsal framing. |
| Supplied numerical state | Existing Scenario remains numerical. If supplied, the original complete probability distribution is required. Valuation bases/scenarios require a consistent horizon. Absence is not replaced with dummy numbers. |
| Numerical calculation | COMMITTED plus the original supported horizon/distribution/currency/Market/chronology inputs. Missing inputs yield typed NO_CALCULATION, not zero or quiet Odds. |
| Live Decision Spine | Original numerical/accountability prerequisites plus actual rehearsal framing; checked before Market I/O. Framing is context, not investment authority. |

Ordinal business worlds and conditions may remain in the exact original
workpaper and existing thesis/risk/open-question narrative. Do not mislabel a
stress surface as a Scenario probability distribution. This change adds no
ordinal Odds engine, calibrated probabilities or free-text-to-package converter.
Only the exact snapshot/Evidence content in the package is frozen by its
information hash; an unbound external workpaper is not automatically part of that
bundle. Original workpapers/PDF bytes and their provenance still need retention.

Package v2 can wrap an unchanged legacy snapshot v1 without framing. That removes
run context, not the snapshot's original prerequisites; its Research information
hash stays the same while the package hash changes. Package v1 cannot wrap
snapshot v2. Unknown versions fail closed. The existing Method-v1 Funnel/Deep
path retains snapshot schema v1 and cannot silently adopt Research-only freeze.

Existing v1 serialized fields, default values and hashes remain unchanged. The
same information-hash function includes the snapshot's version and supplied
content. No migration rewrites or alternate hash/commit validator are introduced.

A later numerical research revision must use the existing new snapshot identity,
version and predecessor relationship, retaining the previous frozen snapshot.
Adding valuation assumptions/probabilities is a research/model revision, NOT a
price-only change. Merely refreshing a price does not authorize either revision
or repeat Research. Version/lineage consistency does not authenticate an absent
predecessor archive or certify the economic interpretation of a revision.

The same offline `commit` / `verify` commands above process v2 and keep the
original retention format. A successful commit does not certify that a Full
Research request was completed, that every UNKNOWN was reduced, or that Human
accepted the work. No state advances just because a saved progress file exists.

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
Research result: COMMITTED (declared version of the generic Kernel contract)
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
separate acceptance steps. The v2 regressions additionally exercise Research-only
commit and the unchanged offline CLI, refusal before Market, typed NO_CALCULATION,
legacy hash compatibility, version isolation, and explicit numerical succession.
Synthetic continuation/calculation is not a real company or calibration sample.
An automatic remote archive/registration host, #321-B price-only Odds and #349
Watch remain outside this slice. It does not close #321 or count P0 live-use days.
