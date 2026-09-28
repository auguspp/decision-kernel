# Frozen stock-field source study — execution retired

Status: **RETIRED_EXECUTION / HISTORICAL_SOURCE_EVIDENCE_RETAINED** under #626,
2026-09-28. These fixed September 5 collection plans are not current source
acquisition instructions or a production recovery path.

## Retired responsibility and surviving consumer

The three fixed stock-field profiles and the single Muyuan H1 collection have
already produced their bounded original attempts. Their workflow, capture code
and dedicated simulation tests are retired together. This also removes the
old path-filtered main-push trigger that could reacquire the fixed Muyuan filing
when the shared source-study module changed. No source request or rerun is
part of retirement.

`stock_field_source_study.notice_query` remains at its existing import path,
with its exact organization checks and query form unchanged, because
`cninfo_announcement_probe` still consumes it as a legacy-form comparison.
That probe, its seven current tests, production CNINFO transport and shared
source/price/PIT validators are unchanged. The module has no collector or
usable capture CLI; an old CLI invocation exits before acquisition/output.
The existing shared retired-surface guard covers this boundary without a new
test identity.

## Retained original attempts

| Historical scope | Original run / artifact | Original result and retained bodies |
| --- | --- | --- |
| Event samples / #218 | 33963949084 / 9968826124 | CAPTURE_COMPLETE_REVIEW_REQUIRED; 21 bodies, including two PDFs |
| Coverage notices / #220 | 33966231127 / 9969513998 | INCOMPLETE_SOURCE_STUDY; 20 bodies, nine PDFs; 603448 latest-date ambiguity |
| Remaining listings / #222 | 33967897334 / 9970021334 | INCOMPLETE_SOURCE_STUDY; 21 bodies, nine PDFs; 601091/920298 missing |
| Muyuan H1 / #235 | 33999968354 / 9979191964 | ORIGINAL_CAPTURED_REVIEW_REQUIRED; three bodies including the exact full report |

The retirement review downloaded all four original ZIPs, checked their metadata
size/SHA256, ZIP CRC, report hashes and every manifested body's bytes/hash.
The two failed/incomplete source runs remain failures. The field plans remain
bound historically to frozen run 33959190974 and report hash
`668073931733d725abecb39a579495ebaad18a21b91f9b558be6a32fb366d5ce`.

Existing interpretation and limits remain in the original proof documents:
[event source proof](stock-field-primary-source-proof-2026-09-05.md),
[coverage originals](stock-coverage-originals-proof-2026-09-05.md),
[remaining listings](stock-remaining-listings-proof-2026-09-05.md), and
[Muyuan source/economic review](muyuan-livestock-evidence-2026-09-06.md).
Retirement does not re-perform the financial review or promote collected bodies
to accepted prices, historical availability, trading-status intervals or truth.

## Exact history recovery

Use the original run's own code commit for its original semantics. The final
pre-retirement implementations and instructions are also recoverable at
`4bfa59d014c6e84dce53c6d44b0e013f7c0cc080`:

- [Stock collector and offline verifier](https://github.com/auguspp/decision-kernel/blob/4bfa59d014c6e84dce53c6d44b0e013f7c0cc080/src/decision_kernel/runtime/stock_field_source_study.py)
- [Muyuan collector and offline verifier](https://github.com/auguspp/decision-kernel/blob/4bfa59d014c6e84dce53c6d44b0e013f7c0cc080/.github/scripts/capture-muyuan-filing.py)
- [Original workflow](https://github.com/auguspp/decision-kernel/blob/4bfa59d014c6e84dce53c6d44b0e013f7c0cc080/.github/workflows/stock-field-source-study.yml)
- [Original study instructions](https://github.com/auguspp/decision-kernel/blob/4bfa59d014c6e84dce53c6d44b0e013f7c0cc080/docs/stock-field-source-study.md)

Raw Actions artifacts retain their existing retention periods; this change
neither deletes them nor promises permanent artifact storage. Historical source
questions/UNKNOWNs remain recorded. A genuinely new acquisition need requires
its own current scope and source qualification, not revival by editing this
old launcher. The current production Stock path and its readers are not retired.

Research / Human Attention / Investment Authority remain NONE for these studies.
