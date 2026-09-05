# Economic Radar — shared source inputs and next-scan baseline

Status: HARNESS INPUT ASSEMBLY / EXPLICIT SOURCE REVIEW ONLY / NO NEW KERNEL OBJECT.

## What changes for the operator

Use one frozen seed file and one directory of existing accepted release bundles. The same inputs now feed both the existing directory scanner and the existing economic/market page, without listing each observation or review on every command. Nothing is automatically accepted or rewritten.

Defaults:

```text
radar_inputs/economic-node-study-2026-09-05.json  # original reviewed seed, unchanged
radar_inputs/economic-reviewed-releases/        # immediate children are accepted bundles
```

The committed review directory is genuinely empty except for an empty `.gitkeep`. It is not evidence of any natural new release, source acceptance or Human review. Register a new complete `economic_release_review apply` output by preserving its exact bundle as one immediate subdirectory. For the checked-out workflow inputs, registration requires an explicit repository change; local callers may instead pass a separately retained directory. Do not commit synthetic fixtures as real reviews. Preparing a draft does not register it, and this assembler never applies a review.

Every child is reverified with the existing review/discovery verifier. Missing directories, loose observation JSON, pending drafts, symlinks, unexpected files, future receipts and public/synthetic mixing fail; none are silently skipped. Duplicate acceptance identities collapse only after verification. The combined seed/physical-child count is at most 64; no top-N truncation. The seed byte budget is 256 KiB and all existing nested archive limits remain active.

## Two consumers, unchanged domain calculations

```bash
python -m decision_kernel.runtime.economic_release_inputs scan \
  --output ../release-input-run

python -m decision_kernel.runtime.economic_release_inputs verify \
  ../release-input-run

python -m decision_kernel.runtime.economic_release_inputs context \
  --bundle ./saved-sector-state \
  --parent-hints ./radar_inputs/sector-parent-hints-2026-09-05.json \
  --as-of 2026-09-06T12:00:00+00:00 \
  --output ../economic-market-reading
```

The date/path examples are not claims of a live run. `--seed` and `--reviews-dir` override the defaults for all three commands. `context` also accepts the existing `--links` input. It expands validated seed observations and review bundles into the existing association CLI, which retains its own strict market bundle, catalog, PIT, review and authority checks. Temporary seed-observation files are removed; original capture clocks are not refreshed. It writes the existing HTML/JSON plus `input-set.json`. It does not fetch market data or create candidates.

`scan` validates source-review eligibility at the actual run input cutoff before calling the existing scanner. It saves `input-set.json`, `report.json`, `summary.md` and the unchanged original scanner archive under `scan/`. Prepare later source reviews against that inner `scan/` directory. The original scanner module and its implementation hash are not changed by this feature.

## Baseline is a derived view, not new source authority

The scan's known-URL set is the union of seed URLs and explicitly accepted URLs. Its source entries retain their original capture times. Source acquisition, review declaration and first accepted recording remain different clocks; a review recorded after the requested cutoff cannot contribute merely because its article was acquired earlier.

Same-URL title/date conflicts produce `BASELINE_IDENTITY_REVIEW_REQUIRED` before any source request. There is no implicit latest-version choice. Identical metadata with differing accepted body/excerpt versions may share one scan identity while ALL review bundles remain available to the reading page: this does not resolve the page's economic-version conflicts. The scan only checks known URLs' visible directory metadata and does not re-fetch their body. `known_url_body_revisions_checked = false` remains explicit. Detecting unannounced same-URL body revisions is not claimed complete.

The existing scanner uses the newest known publication date per family. Advancing that cutoff can leave a still-unreviewed article in `OLDER_UNREVIEWED_BACKLOG_NOT_FETCHED`. This wrapper also retains the ORIGINAL seed cutoff and flags every visible such article at/after it. The result is `UNREVIEWED_BASELINE_GAP`, with every affected row retained and exit code 2, even when the underlying directory scan completed. This prevents a moved cutoff from quietly reporting a resolved window. It does not auto-fetch the backlog or create acceptance; resolve it using retained packets or a separately reviewed bounded recovery, never by repeatedly moving the seed. Older-than-original-seed backlog remains outside this selected operating window.

`INCOMPLETE_SCAN` preserves original transport, parsing and budget failures. `COMPLETE_BOUNDED_INPUT_SCAN` means this supplied input set and visible scan were processed, not complete publisher coverage or absence of updates. New identity-qualified packets still require explicit review. No scope is expanded to arbitrary crawling, no gate/score is added, and the original request budget remains two directory requests plus at most four planned detail requests.

## Reproduction, storage and provenance

`input-set.json` binds exact seed bytes, seed identity, accepted bundle hashes, first acceptance eligibility and derived baseline identity at an explicit cutoff. It is not a signed attestation, an authenticated Human reading record, a new economic observation, a new restore authority or a global record of everything known elsewhere.

`verify` revalidates the original seed and ALL original registered review bundles, reconstructs the input-set receipt, uses the existing scanner's offline verifier and compares the actual saved baseline, input time, report and summary. A newer or modified input directory cannot silently replay an older run. Restore the precise Git revision for repository inputs, or the exact external seed/review directory snapshot for local inputs. The scan archive does not redundantly copy all earlier review archives. Keep those originals; hashes alone cannot recover missing bytes.

Review/discovery verification still requires the original implementation and parser runtime. An old archive requiring a different version must not be silently upgraded. Workflow artifact retention remains finite; no new cloud database, automatic checkpoint policy or remote approval storage is introduced. The assembler assumes a single writer/frozen inputs during a run; it rejects changed receipts rather than offering concurrent queue semantics.

## Acceptance and limits

Tests reuse the real existing discovery runner, review application/verifier, source binder and association CLI; full context tests also reuse the actual audited synthetic Sector producer. Fixtures exercise both public-labelled production branches with blocked/mock transport and explicitly synthetic branches. All such fixtures are synthetic pytest data, never actual public capture or authenticated Human review. No validators or candidate selectors are replaced with canned success results.

Acceptance covers empty/invalid registries, distinct review versions, deduplication, cutoff eligibility, source identities, former-window backlog visibility, partial scans, rehashed corruption, exact replay and unchanged market/events. Existing source parser, canonical identity, source-review format, market calculation, archive formats, thresholds and all authority rules remain unchanged.

This feature makes accepted releases reusable as ordinary inputs. It does not establish a first natural new-release acceptance, ongoing full publisher coverage, reviewed company exposure, automatic schedule, Sector's next-session live append or real T+5/T+20 results. Human/Research/Investment authority remains NONE.
