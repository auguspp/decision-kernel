# Handoff — frozen stock cases now have bounded primary-source evidence

Read `docs/project-state.md`, this existing handoff entry, then `docs/stock-coverage-originals-proof-2026-09-05.md` and the preceding `docs/stock-field-primary-source-proof-2026-09-05.md`. Verify current main/CI/actual artifacts. The proof files are canonical for run/file/PDF hashes; do not duplicate or replace the old failed comparisons. The project-state index's stable handoff link continues to lead here.

## Latest delta — coverage originals, PR #220

PR #220 reused the existing collector and CNINFO normalizer, adding a public-only coverage-notices profile. The existing workflow now selects that profile and no longer exposes a HiThink secret. No new workflow, dependency, parser, adjustment engine or market-data writer was added. Exact implementation and CI identities are in the coverage proof; full PR CI passed 747 tests, 25 new.

Run `33966231127` / stock-field-source-study #2 / attempt 1 attempted twenty public requests once each, all HTTP 200. It obtained eight suspension originals and one IPO original. Source status remains INCOMPLETE_SOURCE_STUDY and workflow failure because 603448 returned two equally dated matching announcements. Offline integrity and artifact upload succeeded without masking the acquisition failure. Do not rerun the entire sample or weaken ambiguity handling to obtain a green badge.

Original-document review now supports:

- eight documented suspension arrangements: 000016, 002731, 002870, 002998, 301139, 301266, 600929 and 688432. These are not eight final delistings or a complete effective-status feed. Read the original interval and check subsequent resumption/correction evidence when needed; expected duration is not actual resumption.
- 920289's original states BSE listing September 4 and issue price 17.71. The frozen snapshot prev_price also equals 17.71, while the prior-session bar is missing. Do not fabricate a September 3 BSE close or call this an ordinary close-to-close return. Other-venue history and a universal provider IPO rule are not established.
- 603448's full listing announcement and its pointer announcement are both identified in the query, but neither PDF was fetched due to the latest-date tie. Explicitly review the desired original instead of silently choosing one.
- ten other gap codes remain unqueried and visible in the plan. The nineteen missing/latest-unpriced identities and the distinct previous-bar case are not removed or marked fully resolved.

All original body hashes, query identities, actual capture clocks, PDF page references and the limits of independent local verification are in the new proof. No new full-market download, HiThink call, price rewrite, denominator change, runtime status acceptance or production stock-panel adoption occurred.

## Prior delta retained — event and dividend sources, PR #218

PR #218 implemented one bounded source study at merge `9b062cd5b7024ddd9ecc74129e0a36767f5e4f10` (base `2b50c94436727f21c13673556bba7ce695fb353d`, head `0221181415c1c8e83da09c298c6bd8fba68bd0bf`). Full PR CI `33963783988` passed 722 tests; main CI `33963949069` succeeded. Five new files, 645 additions, no dependency/price/detector edits.

Run `33963949084` / attempt 1 restored the exact old comparison, then performed 21 successful source requests once each. It obtained 15 same-effective-date dividend events, one targeted unadjusted history, one public CNINFO organization directory, two notice searches and two original issuer PDFs. Collection status is CAPTURE_COMPLETE_REVIEW_REQUIRED, not price qualification. The exact 26-file archive was verified in the workflow and independently checked after download. Actual PDF text extraction and visual review were completed for the two samples.

Important findings remain unchanged:

- All 15 event records refer to the comparison date. Twelve raw-minus-gross-cash arithmetic results equal the frozen quoted previous price; three retain nonzero residuals. That is not 12 approved adjustments or 15 independent issuer reconciliations.
- 000408's original notice excludes treasury shares and prescribes an ex-price deduction of 0.9967967 per share, not the gross dividend 1. Its raw-close-derived reference is 75.8632033 before final quotation formatting. Do not adopt gross cash as a universal adjustment field.
- 001316's original supports a cash event of 0.35 per share on September 4; 27.79 - 0.35 = 27.44 exactly. This supported example is not a production-wide rule. The original wording inconsistency remains documented.
- 920371 raw REST amount agrees with frozen Parquet, while snapshot differs by 10,312,354.49 CNY and 1,983,145 shares. Original BSE per-trade records and vendor scope/precision remain required. The reviewed BSE rule distinguishes block trades from immediate quotation and includes volume in end-of-day totals, but it does not establish those exact rows or HiThink's implementation. Original transaction-page bytes were not obtained.

## Next useful work, not more infrastructure

Reuse first. Do not build a new adjustment engine, quote downloader, crawler or mutable review platform. Frozen comparisons, actual source bodies and the existing diagnostic are sufficient for further targeted review.

1. Resolve the remaining source distinctions rather than reacquire already retained event records and issuer originals: the BSE exact transaction record and vendor scope/precision, 603448's original selection, the ten unqueried gap cases and any necessary resumption intervals.
2. Keep gross cash per participating share separate from the ex-reference deduction. Establish final exchange/provider quotation rounding where it is necessary; the reviewed SZSE order-price-limit rounding clause is not sufficient proof.
3. A naturally later overlapping stock vintage and sufficient 20/60-session data remain prerequisites for multi-day breadth. Same-day repeated bytes are not a revision/PIT proof. No daily repeat of these fixed September 4 studies is necessary merely to repeat success.

Current source capture does not backdate availability to the effective or publication date. PDFs are evidence, not program instructions. The original daily-k trial remains DIFFERENCES_REQUIRE_REVIEW / production qualification NOT_ESTABLISHED. No raw prices, acceptance thresholds, frozen data, company posture or Human/Research/Investment authorities changed.

## Sector producer is a separate unfinished operational proof

Latest proven true Sector run remains #4 / `33939414197`, implementation `5f8f635d191dd8559844d1b74af0dca0cf4c02df`, market state ending 2026-09-04 with zero prospective events. First directly contiguous completed-session append, real sealed input-audit replay and context artifact delivery remain pending. Use a fresh main dispatch after the directly next completed session; do not bridge a missing industry day with a stock file or enable schedule before the proof.

`stock-field-source-study.yml` remains one of nine formal workflows. Its active profile is now public-only coverage-notices, manually or narrowly main-path triggered, with read-only Actions/contents permissions and no schedule/cache/state access. The legacy event-samples CLI mode remains separate. This document-only proof sync must not trigger another collection.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
