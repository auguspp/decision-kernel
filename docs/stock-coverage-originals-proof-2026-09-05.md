# Frozen stock coverage: nine original notices, one unresolved selection

Evidence date: 2026-09-05. Status: ORIGINAL COVERAGE SOURCES PARTLY OBTAINED / INCOMPLETE_SOURCE_STUDY RETAINED / NO PRODUCTION ELIGIBILITY CHANGE.

## Implementation and actual run

PR #220 reused the existing source collector, Requests and the project's CNINFO announcement-page normalizer. No new workflow, dependency, PDF parser, adjustment engine or market-data loader was added. Its existing workflow switched to the public-only coverage-notices profile and removed the HiThink secret. The old event-samples CLI profile and its recorded evidence remain available, but were not rerun.

```text
base = bf2ffa9329ff30567ba502c4ab085ac047405498
head = 95a938378fb669878274daed7fbab032b1b374c5
merge / executed implementation = 3b1593a5290feeaf958cd4cedab109875c879d7a
PR CI = 33966005359 / job 101306138788 / 747 passed in 9.87s
main kernel CI = 33966231152 / success
new test cases = 25
```

Exact code PR scope: stock_field_source_study.py (+84/-6), its existing workflow (+6/-4), new test_stock_coverage_notice_samples.py (+187), existing workflow tests (+6/-5), and stock-coverage-notice-study.md (+54). Total +337/-15. The tests cover fixed-gap intersection, unqueried identities, legacy-plan compatibility, exact code/org/date validation, incomplete queries, duplicate IDs, latest-date ties, public-only request limits and rejection of altered plans. Full repository tests ran in CI; no full local checkout test is claimed.

One changed-profile main-push run executed:

```text
run = 33966231127 / stock-field-source-study #2 / attempt 1
started_at = 2026-09-05T12:30:48.316322Z
completed_at = 2026-09-05T12:31:15.921366Z
public requests = 20, once each, all HTTP 200
retained bodies = 20
organization directory = 1
exact-code notice queries = 10
original PDFs = 9
HiThink requests = 0
workflow result = failure
source status = INCOMPLETE_SOURCE_STUDY
problem = one ambiguous latest document selection for 603448.SH
```

HTTP success is not the same as complete source selection. The collector did not choose between two equally dated originals and did not retry, widen the query or quietly discard the unresolved case. The offline plan/file integrity step and artifact upload still succeeded independently of the failed acquisition step.

## 1. Eight originals document suspension arrangements

The table records what the retained issuer originals say, not a new automatic effective-status database. Page numbers are physical PDF pages, starting at 1. All eight codes belonged to the original missing-latest/unpriced intersection. Query metadata, original body bytes and actual capture clocks are preserved.

| Code | Issuer | Original notice | Reviewed pages | Documented arrangement relevant to the comparison window |
| --- | --- | --- | --- | --- |
| 000016.SZ | 康佳集团 / *ST康佳A | 2026-69, CNINFO 1225545707 | 1 | Suspension from 2026-09-04 for proposed shareholder-resolution voluntary delisting. The September 14 meeting and conditional resumption arrangement are still future/conditional; this is not evidence of a completed delisting on September 4. |
| 002731.SZ | 萃华股份 / *ST萃华 | 2026-107, CNINFO 1225539050 | 1 | Suspension from 2026-09-01 because the interim report could not be disclosed by the deadline; also describes continuing suspension and termination risks. Not a completed delisting receipt. |
| 002870.SZ | 香山股份 | 2026-068, CNINFO 1225538772 | 1 | Suspension from 2026-09-01 while planning a share/cash asset purchase, with a stated expected maximum of ten trading days. The notice does not confirm completion of the proposed acquisition. |
| 002998.SZ | 优彩资源 | 2026-049, CNINFO 1225547328 | 1 | Suspension from 2026-09-04 while a possible control change is negotiated, expected not to exceed two trading days. The agreement is not yet signed in this notice. |
| 301139.SZ | 元道通信 / *ST元道 | 2026-089, CNINFO 1225533921 | 1-2 text, page 1 visually checked | Suspension from 2026-08-31 following a disclosed administrative-penalty decision and potential mandatory-delisting process. A proposed/process state must not be relabelled as final exchange removal. |
| 301266.SZ | 宇邦新材 | 2026-056, CNINFO 1225542264 | 1-2 | Initially suspended August 31; continues from September 2, expected not to exceed three trading days, while a control change is pursued. This provides a more specific continuation notice rather than only the initial announcement. |
| 600929.SH | 雪天盐业 | 2026-032, CNINFO 1225527870 | 1-2 | Suspension from 2026-08-31 for a proposed share/cash acquisition and related fundraising, expected not to exceed ten trading days. |
| 688432.SH | 有研硅 | 2026-037, CNINFO 1225532846 | 1-2 | Suspension from 2026-08-31 for proposed share/cash acquisitions, expected not to exceed five trading days. The original suspension table leaves end/resumption dates blank. |

These are original-source explanations consistent with the observed gaps, not proof of a complete status interval. The keyword query is not a full search for every resumption, correction or exchange decision. In particular, an expected suspension duration is not a guaranteed actual resumption date. Do not infer perpetual suspension, remove a code from the original denominator, or fill a missing price with a previous close.

Document date and query publication date may differ: for example, 002731's signed document ends August 31 while CNINFO's publication metadata is September 1. Both are preserved. Acquisition occurred September 5; no historical system availability was backfilled.

## 2. 920289.BJ: the previous-bar gap now has an IPO-specific explanation

The 67-page original listing announcement, CNINFO 1225544616, states on physical PDF page 40 (printed page 39): exchange = Beijing Stock Exchange, listing date = 2026-09-04, name = 华汇智能, code = 920289. Physical page 60 (printed page 59) states an issue price of CNY17.71.

The frozen September 4 snapshot had last_price 37.5 and prev_price 17.71, while the existing inspector recorded no previous-session bar. Thus the quoted prev_price equals the documented issue price; it is not evidence that a September 3 BSE close existed. Do not manufacture such a bar, compute an ordinary close-to-close return across the IPO boundary, or assign zero return. This is a concrete example of why quote-reference prices and historical prior closes require separate semantics.

This observation does not establish a universal HiThink first-day-price contract or prove the absence of older trading history on another venue. It supports the identified BSE first-session case only. The original inspector output remains unchanged and the stock panel is not adopted.

## 3. 603448.SH remains an explicit unresolved original-document selection

The exact query returned a complete two-record page, both dated September 4:

- CNINFO 1225547191: 天博智能首次公开发行股票主板上市公告书.
- CNINFO 1225547199: 天博智能首次公开发行股票主板上市公告书提示性公告.

Both matched the fixed search family and had the same latest timestamp. The collector therefore kept the original query but fetched neither PDF. This is the single reason the run is INCOMPLETE_SOURCE_STUDY. It is not an HTTP outage, an empty query, or proof that there is no listing announcement. The full announcement versus pointer announcement can be explicitly reviewed later; do not weaken same-time ambiguity handling or rerun the entire sample just to get a green badge.

The previous SSE indexed listing-date lead is not upgraded by this query alone. No new accepted effective date is assigned for this code in the machine result.

## 4. Ten gap identities were not queried in this bounded sample

```text
301686.SZ 301689.SZ 301699.SZ 601091.SH 688801.SH
688837.SH 920201.BJ 920268.BJ 920269.BJ 920298.BJ
```

These remain explicit in plan.unqueried_gap_codes. The frozen coverage problem is nineteen latest-bar/unpriced identities plus the distinct missing-previous-bar code 920289.BJ. The selected ten are eight suspension leads, one unresolved listing-original selection and one obtained IPO original. Nine obtained PDFs do not mean all twenty cases are closed. No identity or missing diagnostic was removed.

## 5. Turnover remains a different, unresolved question

The BSE 2026 trading-rule publication at https://www.bse.cn/jygl_list/200028217.html was reviewed through primary-domain indexed text. Section 3.6.8 excludes block trades from immediate quotes/index calculation and includes their volume in the security's daily total after block trading. That is relevant scope context, not the exact September 4 transaction rows or the vendor's turnover/volume precision contract.

Browser/local transport attempts did not obtain original BSE transaction-page bytes in this round; local attempts recorded connection/DNS failure, not a claimed exchange rejection or absent trades. Do not attribute 920371's exact 10,312,354.49 CNY difference to a cause on that basis. No third-party price source, empirical tolerance or generalized exchange-scope rule was adopted. The previous gross-dividend/ex-reference distinctions also remain unchanged.

## Evidence inventory and independent verification

```text
artifact = stock-field-source-study-33966231127-1
artifact id = 9969513998
ZIP bytes = 2086166
ZIP SHA256 = 92d43485f91aef58363fee03cf862776c784dcdafeb5f8c34b2a2cf7b1676305
expires_at = 2026-12-04T12:30:28Z
source report hash = 668073931733d725abecb39a579495ebaad18a21b91f9b558be6a32fb366d5ce
plan hash = 325a999ad68762d5671f6ba612d5c68843b190ac54f1c477663367c408e9450e
study hash = bd26d79e4836f4ea999902b968e9858741832d8fc787e872a4566a01851e592f
workflow provenance hash = 030cd681d391040cb8c67209352976bcbed768bb6e8d8c69ba0b610cc5b3c1da
```

Original PDF inventory under capture/:

| Code | File | Bytes | SHA256 |
| --- | --- | ---: | --- |
| 000016.SZ | response-03.pdf | 177198 | 8da7586099fb06bdd0d6666d2bd100077a92b5e05c6e73e11d07403b3c5a7dce |
| 002731.SZ | response-05.pdf | 95846 | f9890ae00af1769880f17f60953257384ceb3b629cf1b46ba69d528ec880a608 |
| 002870.SZ | response-07.pdf | 148207 | feb71e43cf225f48508df3bc9718fd224a7d33bd544cacd5a39ff939c96bdb2e |
| 002998.SZ | response-09.pdf | 109386 | a82d02f81b2e1c71ff523d5ae30c6945ae0efeb5c9a784425758a159d1c9b3d9 |
| 301139.SZ | response-11.pdf | 91428 | eb93005104bd94d8896c4c4fcb27ecbd4478ba6d7c4b3a03b134a586aadc50d6 |
| 301266.SZ | response-13.pdf | 92294 | eef7c7108c5479b7140d4b9af643fc05d0363da68bbd562f01b8d8ae4eea1b26 |
| 600929.SH | response-15.pdf | 137563 | 817fab301617ac8140b64b49cb5022d4a4ca5f458c67ec0249633ea3e309833f |
| 688432.SH | response-18.pdf | 145570 | 35fc0c96e450f629b284e97c0b3298e4aa2a8b95199f69fe90269ea06256c09a |
| 920289.BJ | response-20.pdf | 1147962 | 49b38fa4629e8485894f3b41a1c072b6005eddf4c86db751e6a90d98a99dce6e |

The 25-file archive contains twenty original bodies, plan/report/summary, the unchanged frozen offline-inspection report and workflow provenance. Its workflow verifier rebuilt the coverage plan, checked all inventory/file hashes and retained the acquisition failure. After download, independent local checks reconciled ZIP/body hashes, original report/inspection hashes, exact file inventory, monotonically ordered capture clocks, current org-map identities, all query row codes/orgs/dates/IDs and selection of each of the nine downloaded PDFs. The source offline report is byte-identical to the preceding source-study copy. No credentials were used or retained in this public-only run.

Existing local pypdf 5.9.0 extracted the nine PDF texts; Poppler rendered the reviewed suspension pages and the IPO listing/issue-price pages. Visual checks covered the eight suspension originals' first pages, continuation/detail pages 2 for 301266/600929/688432, and IPO physical pages 40 and 60. This was targeted source review, not a complete read of all 67 IPO pages, new OCR, a full local repository test or another Parquet scan. Hashes establish integrity of retained bytes, not independent certification of every issuer claim or a complete legal status history.

## Next useful decisions, not repeated successful downloads

Keep the original DIFFERENCES_REQUIRE_REVIEW / NOT_ESTABLISHED result. A later explicit stock-history contract should distinguish no trade, not-yet-listed, first session, missing data and unexplained values without turning any into fabricated prices. It must preserve denominator and membership/PIT boundaries and should reuse existing qualified status/event sources rather than introduce another generic state machine.

For these exact samples, further work should resolve 603448's reviewed original selection, the ten unqueried cases, and any needed resumption/status intervals, not refetch the nine obtained originals. Separately obtain BSE transaction rows/vendor scope, final quotation semantics, a naturally later overlapping stock vintage and sufficient history before 20/60-session breadth. No schedule or price-only production adoption was earned.

The Sector producer still awaits its direct-next-completed-session proof, real input-audit replay and live context delivery. This public source run did not invoke that producer or write its market state/cache/event ledger. No detector threshold, company decision, Research route, Human/Research/Investment authority or canonical Inbox changed.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
