# Economic release review v0 — from discovered original to reading input

Status: EXPLICIT LOCAL SOURCE REVIEW / NOT AUTOMATIC ACCEPTANCE / NO INVESTMENT AUTHORITY.

## Delivered path

The existing discovery produces identity-qualified `PENDING_HUMAN_SOURCE_REVIEW` packets, not economic observations. `runtime/economic_release_review.py` connects a selected packet to an explicit reviewed excerpt, and the existing economic/market reading CLI can now consume its verified acceptance bundle with `--reviewed-release`.

```text
existing original discovery archive
→ prepare one exact source packet (blank review + normalized source text)
→ an authorized operator explicitly reviews the original and writes an acceptance
→ existing archive verification + existing reviewed-excerpt binding + existing economic parser
→ a new immutable local acceptance bundle
→ existing association page, subject to the later acceptance cutoff
```

There is no new crawler, parser, database, approval service, event bus or workflow. A `prepare` success is only draft preparation. `apply` requires `ACCEPT_REVIEWED_EXCERPT`, explicit reviewer, timezone-aware review time, a source-review reason and the exact reviewed excerpt. PENDING, DEFER and REJECT cannot produce an acceptance. This v0 is not a general rejection/defer queue; retain those working notes separately without promoting the source.

## What acceptance does and does not establish

The exact archive hash, source packet ID and body hash must match. The existing discovery verifier rebuilds directory identity and article metadata from the original bytes, under its original implementation/parser runtime requirements. It does not accept a loose packet JSON, an arbitrary URL or a guessed latest article.

The existing `bind_reviewed_source` validates the supported source template, whitespace-normalized excerpt correspondence and original acquisition time. A changed value absent from the original, an unsupported new template, changed source identity or contradictory metadata is refused even when a review says accept. This matching is NOT exhaustive semantic verification of every claim on the page; reading the full retained context remains the operator's responsibility. A reviewer declaration and content hashes are not authentication, digital signatures, proof of actual Human reading, or proof that economic conclusions are true. Execution permissions and review governance remain outside this local helper. Do not wire an unattended LLM to fill the acceptance fields.

A scoped valid packet can be reviewed even if another directory in the same scan failed. The original INCOMPLETE scan status remains in the receipt and the original archive is never rewritten. A scan with zero identity-qualified detail packets cannot be converted into a source acceptance. Accepting an excerpt does not improve directory coverage or prove that no later release or body revision exists.

## Keep three system times, not one convenient date

- `source_record.captured_at` and the existing observation's `system_pit_eligible_from` remain the original article acquisition time. No recapture is invented.
- `reviewed_at` is the operator's explicit declaration, not an inferred reading event. It must be after acquisition and no later than recording.
- `recorded_at` is taken when this explicit acceptance is first applied; this reading channel's `eligible_from` equals that later recording time.

The association's `as_of` must include `eligible_from`, not merely the earlier article capture or public release date. A source acquired at 12:00, reviewed at 12:05 and recorded at 12:10 cannot be consumed as accepted at 12:09. Later report generation does not fix an earlier ineligible input cutoff. Market close, source publication date/precision, reporting period, mapping review time and page-generation time keep their existing meanings.

The original economic observation remains nested inside `acceptance.json`, with its original source-derived identity and binding. No standalone `observation.json` is exported that could accidentally lose review eligibility. A whole acceptance passed through the old `--observation` path fails the existing source-derived validator. The old path remains for explicitly pre-reviewed legacy study observations, not a mechanism to strip new review metadata or launder unattended source discovery. The supported new-release ingress is `--reviewed-release`.

## Local files, idempotence and revisions

An acceptance directory contains exactly:

```text
acceptance.json  # nested original observation, binding, reviewer/clock/identity receipt
review.json      # exact explicit review declaration
page.txt         # existing normalized source-text projection, not executable HTML
 discovery/     # exact copied original discovery archive, including raw article bytes
```

The embedded archive is verified again after copying. `verify` reconstructs the acceptance and page from that archive and review instead of trusting a hash alone. Synthetic discovery remains SYNTHETIC_TEST_ONLY through acceptance and the reading page; mixing synthetic and public economic records remains refused.

The local writer stages and verifies before publishing a new directory. Exact reapplication to the same complete output returns the first receipt without changing its recording time. A different review cannot overwrite that output; use another explicit directory. Failed writes clean the temporary bundle and leave inputs unchanged. Paths with symlinks, nesting inside the original archive, and market-state storage are refused. The writer is single-writer only, not a distributed/concurrent transaction service.

Changed source versions are separate archives and receipts. The existing association still shows VERSION_REVIEW_REQUIRED when conflicting values for the selected period are supplied. Neither a second review nor a repeat read is a new economic period, independent forecast or additional market event. This is not an automatic revision-resolution policy, and it does not update the discovery baseline.

Review JSON is bounded to 64 KiB; acceptance JSON to 256 KiB; the existing archive budgets remain in force. Association input count retains its 64-record operational limit across old observations and new review bundles. Raw archives and receipts are local outputs; remote retention, publication and automatic archive selection are NOT provided by this change. Preserve the whole bundle and its original runtime when retaining evidence; future code changes do not silently migrate old receipts.

## Usage

Use the existing package with the pinned discovery extra and the original archive's Python/parser runtime. These commands do not fetch any data. Inputs and outputs below are examples, not claims that a new live packet exists.

```bash
python -m decision_kernel.runtime.economic_release_review prepare ./inputs/discovery \
  --packet-id <exact-source-packet-id> --output ./draft
# Review the original source and fill draft/review.json explicitly; do not auto-approve.
python -m decision_kernel.runtime.economic_release_review apply ./inputs/discovery \
  --review ./draft/review.json --output ./accepted-release
python -m decision_kernel.runtime.economic_release_review verify ./accepted-release \
  --as-of <explicit-timezone-aware-cutoff>
python -m decision_kernel.runtime.economic_market_context \
  --bundle ./inputs/sector-state --parent-hints ./inputs/parent-hints.json \
  --reviewed-release ./accepted-release --as-of <explicit-timezone-aware-cutoff> \
  --output ./reading
```

Repeat `--reviewed-release` for explicitly selected accepted packets. Existing `--observation` inputs can remain alongside them when provenance is compatible. No recursive directory scan, latest-file guessing, network fallback, producer-cache write, automatic Research routing or new canonical wake occurs. With no review bundles, the existing projection and legacy behavior remain unchanged. With them, HTML and JSON retain separate source capture, declared review and actual recording times, with an explicit source-review-not-investment-decision label.

## Verification boundary

Tests reuse the actual existing synthetic discovery pipeline, archive verifier, source binder, economic parser and association builder. End-to-end CLI tests additionally use a real calculated synthetic Sector producer bundle; selectors/validators are not replaced with preselected results. Cases cover both source families, draft refusal, exact identity, unsupported templates, unsubstantiated values, missing/invalid clocks, future acceptance cutoffs, duplicate/revised inputs, tampering despite recomputed hashes, synthetic provenance, single-writer idempotence, interrupted storage, DOM escaping and unchanged original state/events.

No live source has been newly acquired or accepted by these tests. No real Human review, company judgment, investment Action, fundamental confirmation or prospective market event is manufactured. The previously saved discovery with zero new packets is not repurposed to claim a natural new-release proof. First natural application, operator access control, automatic baseline maintenance, remote review delivery and Sector's independent live next-session acceptance remain separate work.
