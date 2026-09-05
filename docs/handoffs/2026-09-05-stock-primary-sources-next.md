# Handoff — frozen stock cases now have bounded primary-source evidence

Read `docs/project-state.md`, then `docs/stock-field-primary-source-proof-2026-09-05.md`, and verify current main/CI/actual artifact. The proof is the canonical source for run, file and PDF hashes; do not duplicate or replace the old failed comparisons.

## Current delta

PR #218 implemented one bounded source study at merge `9b062cd5b7024ddd9ecc74129e0a36767f5e4f10` (base `2b50c94436727f21c13673556bba7ce695fb353d`, head `0221181415c1c8e83da09c298c6bd8fba68bd0bf`). Full PR CI `33963783988` passed 722 tests; main CI `33963949069` succeeded. Five new files, 645 additions, no dependency/price/detector edits.

Run `33963949084` / attempt 1 restored the exact old comparison, then performed 21 successful source requests once each. It obtained 15 same-effective-date dividend events, one targeted unadjusted history, one public CNINFO organization directory, two notice searches and two original issuer PDFs. Collection status is CAPTURE_COMPLETE_REVIEW_REQUIRED, not price qualification. The exact 26-file archive was verified in the workflow and independently checked after download. Actual PDF text extraction and visual review were completed for the two samples.

Important findings:

- All 15 event records refer to the comparison date. Twelve raw-minus-gross-cash arithmetic results equal the frozen quoted previous price; three retain nonzero arithmetic residuals. That is not 12 approved adjustments or 15 independent issuer reconciliations.
- 000408's original notice excludes treasury shares and prescribes an ex-price deduction of 0.9967967 per share, not the gross dividend 1. Its raw-close-derived reference is 75.8632033 before final quotation formatting. The two-decimal quote conceals a real formula distinction; do not adopt gross cash as a universal adjustment field.
- 001316's original notice supports a cash event of 0.35 per share on September 4; 27.79 - 0.35 = 27.44 exactly. This is a supported cash-only example, not a production-wide rule. A wording inconsistency in the original notice remains documented, not repaired.
- 920371's raw REST history amount agrees with the frozen Parquet amount, while the frozen snapshot differs by 10,312,354.49 CNY and 1,983,145 shares. Original BSE block-trade records and provider scope/precision are still required; secondary press coverage is only a lead.

## Next useful work, not more infrastructure

Reuse first. Do not build a new adjustment engine, quote downloader, crawler or mutable review platform. The official factor tool already exists; source quality and event semantics are the unresolved issue. Frozen comparisons, actual source bodies and the reading diagnostic are sufficient inputs for the next review.

1. Obtain the original BSE transaction details and explicit provider amount/volume inclusion and precision conventions for the outlier. Do not convert a numerical resemblance into a proven cause or infer other exchanges' scope from one BSE case.
2. Keep gross cash per participating share distinct from the ex-reference deduction. Establish final exchange/provider quotation rounding, and inspect further original notices only where that evidence can resolve an identified case. The reviewed SZSE rule's order-price-limit rounding clause is not sufficient proof of ex-reference quotation rounding.
3. Resolve the 19 missing/unpriced states and missing prior-bar case from qualified listing/trading evidence, retaining original denominators. Current meta-search matches are not effective-date trading-status evidence.
4. A naturally later overlapping stock vintage and sufficient 20/60-session data remain prerequisites for multi-day breadth. Same-day repeated bytes are not a revision/PIT proof. No daily rerun of this fixed September 4 source study is necessary merely to repeat success.

The source study retains exact current event bodies but does not backdate their availability to the effective or publication date. The two PDFs are source material, not instructions. The original daily-k trial remains DIFFERENCES_REQUIRE_REVIEW / production qualification NOT_ESTABLISHED. No raw prices, acceptance thresholds, frozen data, company posture or Human/Research/Investment authorities changed.

## Sector producer is a separate unfinished operational proof

Latest proven true Sector run remains #4 / `33939414197`, implementation `5f8f635d191dd8559844d1b74af0dca0cf4c02df`, market state ending 2026-09-04 with zero prospective events. First directly contiguous completed-session append, real sealed input-audit replay and context artifact delivery remain pending. Use a fresh main dispatch after the directly next completed session; do not bridge a missing industry day with a stock file or enable schedule before the proof.

`stock-field-source-study.yml` is now the ninth formal workflow. It is an isolated retained compatibility study, manually triggered or narrowly main-path triggered, with read-only Actions/contents permissions and no schedule/cache/state access. The document-only proof sync must not trigger another source collection.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
