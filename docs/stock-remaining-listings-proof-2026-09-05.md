# Remaining frozen stock gaps: nine new originals, two empty queries

Evidence capture date: 2026-09-05. Status: ORIGINAL DOCUMENTS PARTLY OBTAINED / INCOMPLETE_SOURCE_STUDY RETAINED / NO PRODUCTION ELIGIBILITY OR PRICE ACCEPTANCE.

## Implementation and one actual run

PR #222 base `a4c25b58ea6c79617d39c6d27921e5b8ea9e0dcf`, head `8579f43822b0c588fe9b61a811c224513c8db218`, merge/executed implementation `62d1a62772c116f3dfde2e9e2131c6c57eb1a994`.

Exact diff: stock_field_source_study.py +69/-17; its existing workflow +5/-5; new test_stock_remaining_listing_sources.py +209; existing workflow tests +3/-2; stock-remaining-listings-study.md +43. Five files, +329/-24. Full PR CI `33967816065`, job `101310925177`: **768 passed in 10.07s**, 21 new cases. Main kernel CI `33967897339` completed successfully. Full local repository tests were not run or claimed.

The implementation reuses the existing collector, Requests and CNINFO announcement normalizer. Old event-samples and coverage-notices plan shapes are retained. Only remaining-listings uses the reviewed full-original identity and full-document title suffix. The old 603448 same-date tie still fails in the old profile; unrelated ties, missing originals and identity drift remain failures. No new workflow, dependency, transport, parser, status service or adjustment engine was introduced.

```text
run = 33967897334 / stock-field-source-study #3 / attempt 1
started_at = 2026-09-05T13:05:56.399358Z
completed_at = 2026-09-05T13:06:39.524469Z
requests = 21, once each, all HTTP 200
retained original bodies = 21
organization directory = 1
exact-code queries = 11
original PDFs = 9
HiThink requests / market downloads = 0 / 0
workflow conclusion = failure
source status = INCOMPLETE_SOURCE_STUDY
unresolved selections = 601091.SH and 920298.BJ, each a complete zero-row keyword result
```

The separate offline plan/inventory verification and artifact upload succeeded. A successful transport is not a complete source selection, and a source collection is not stock-panel acceptance. The unchanged 24-request budget was not raised; at most 23 requests were planned. Earlier successful nine coverage originals were not requested again. A prior local direct attempt to obtain the known 603448 PDF failed to connect and retained no body; it is not claimed as a successful local acquisition.

## 1. 603448.SH now has an explicit pre-listing boundary

The full original CNINFO `1225547191` was already identified, alongside pointer notice `1225547199`, in the prior retained query. The new profile required that exact original ID, title, publication date and URL rather than choosing the first tied result. Its original bytes are now retained as `capture/response-10.pdf`.

The 76-page listing announcement states on physical PDF page 8 (printed page 7) that Shanghai Stock Exchange consent was given under 上证函〔2026〕2895号; 23,516,837 shares begin trading on **2026-09-07**, under code **603448**, and the listing-date field also gives September 7. This supports the concrete pre-listing explanation relative to the frozen September 4 comparison. It does not demonstrate an actually completed September 7 first trade, nor does it authorize backfilling a September 4 price or deleting the code from the original provider catalog.

The original code catalog can contain a security before its exchange listing date. Preserve the catalog denominator; distinguish it from a separately qualified as-of trading-eligibility denominator. No runtime eligibility projection was enabled in this PR.

## 2. Eight other originals describe issuance stages, not eight established listing dates

Page numbers below are physical PDF pages, starting at 1. Statements are limited to the reviewed original passages; planned dates remain plans and later corrections are not ruled out by a bounded keyword query.

| Code / issuer | CNINFO original | Reviewed relevant pages | What the original supports |
| --- | --- | --- | --- |
| 301686.SZ / 中塑股份 | 1225542290, September 2 | 14 | Initial inquiry September 4 and planned online/offline subscription September 10. This is an issuance timetable, not the actual listing date. |
| 301689.SZ / 电科思仪 | 1225544675, September 3 | 1-2 | Issuance-result report; subscription payment work ended September 1. Allocation/payment completion is not exchange-trading commencement. |
| 301699.SZ / 洛轴股份 | 1225537096, September 1 | 1-2 | Issuance-result report; subscription payment work ended August 28. No accepted listing-date value is inferred from it. |
| 688801.SH / 燧原科技 | 1225538497, September 1 | 4, 13-14 text; 4 and 13 visual | Subscription September 2 and subsequent payment/allocation schedule. Page 4 explicitly says listing arrangements will be separately announced. |
| 688837.SH / 信诺维 | 1225542462, September 2 | 4, 12-13 text; 4 and 12 visual | Subscription September 3 and subsequent payment/allocation schedule. Page 4 explicitly says listing arrangements will be separately announced. |
| 920201.BJ / 百瑞吉 | 1225547122, query metadata September 3 | 5, 9 | Planned subscription September 7; listing arrangements to be separately announced. The document timetable describes September 4 disclosure, which is kept distinct from the query's September 3 timestamp. |
| 920268.BJ / 百迈科 | 1225544140, September 2 | 1-2 | Issuance-result report; subscription payment ended August 31. This does not supply an actual BSE listing date. |
| 920269.BJ / 杰锋动力 | 1225526987, August 28 | 1-2 | Issuance-result report; subscription payment ended August 26. This does not supply an actual BSE listing date. |

These sources replace missing-document statements only for the exact originals acquired. They do not close every effective trading-status interval or establish the absence of other-venue history. CNINFO IPO-table blank listing cells are not enough to infer not-yet-listed status; source dates, document dates and actual capture time must remain separate.

## 3. Two exact queries remain empty, not negative listing evidence

`601091.SH` / 沈鼓集团 returned zero rows for 初步询价及推介公告; `920298.BJ` / 腾信精密 returned zero rows for 发行结果公告. Both exact-code/organization requests used the existing August 15–September 4 window. Their responses have `hasMore=false` and `totalAnnouncement=0`. The bodies are retained as `capture/response-08.json` and `capture/response-21.json`; neither produced a guessed PDF.

The result establishes only that those particular queries returned no document. It is not an HTTP error, proof no issuance/listing occurred, or a reason to classify a missing quote. Future investigation should use an explicitly reviewed alternative document identity/keyword or a qualified exchange listing record for those two cases, not repeat all eleven cases or quietly widen a search until a convenient answer appears.

## 4. Overall evidence coverage and permissible use

Across the previous coverage run and this run, eighteen of the twenty original gap cases now have at least one retained original document: eight suspension arrangements, the 920289 first-BSE-session original, the 603448 future listing date, and eight issuance-stage originals. The remaining two have empty selected queries. **Eighteen source packets is not eighteen fully resolved statuses.** The original problem remains nineteen latest-bar/unpriced identities plus the distinct 920289 missing-previous-bar case. No code, missing diagnostic or price was removed.

| Evidence or field | Permitted interpretation | Still not permitted |
| --- | --- | --- |
| Explicit future listing date | Identified pre-listing boundary relative to the frozen day | Fabricated bars, completed future trades, or whole-catalog rewriting |
| Subscription/allocation dates | The issuer's described issuance stage | Invented actual listing date or full no-trading interval |
| First-session issue-price reference | IPO comparison distinct from previous exchange close | Ordinary close-to-close return across a nonexistent prior bar |
| Suspension arrangement | Exact documented arrangement and source date | Guaranteed resumption, permanent suspension or final delisting without evidence |
| Latest-close equality | The compared field agrees for the inspected priced identities | All-field qualification, total-return correctness or cross-vintage stability |
| Turnover/volume discrepancy | Unresolved precision and transaction-scope question | Empirical tolerance, silent stock removal or claimed BSE trade attribution |

This is a documented use boundary, not a new eligibility state machine or activated acceptance gate. The original stock-file result stays **DIFFERENCES_REQUIRE_REVIEW**, with **production_qualification = NOT_ESTABLISHED**. The 920371 original BSE per-trade records/vendor scope, final ex-reference quotation conventions, needed status intervals, naturally later overlapping vintage and adequate 20/60-session history remain outstanding. The fixed ten-session file is not yet a production stock panel or multi-day breadth input.

## Original inventory and verification

```text
artifact = stock-field-source-study-33967897334-1
artifact id = 9970021334
ZIP bytes = 9205313
ZIP SHA256 = 7b504db1cf7ec0bf495dd0d7309f0148cbfec2ee9c9227f1c4e9742cad2c0978
expires_at = 2026-12-04T13:05:41Z
source report hash = 668073931733d725abecb39a579495ebaad18a21b91f9b558be6a32fb366d5ce
plan hash = 4003242d09b446b457ccec2e82704ae8df22c66f3dfd4d15e62894f59e45194a
study hash = cf0df5f5f312103c27221b91294356bbf21a6c495060a074081a5f1683abb8aa
workflow provenance hash = 189431bec27fd1e26548335e1cddfecb72ed0a9c119761c5826c573761d5db8d
```

Original PDF locations are the official CNINFO host `https://static.cninfo.com.cn/` plus the paths below. URLs are locators, not durable content identity.

| Code | Original relative path | Retained file | Bytes | SHA256 |
| --- | --- | --- | ---: | --- |
| 301686.SZ | finalpage/2026-09-02/1225542290.PDF | response-03.pdf | 774231 | 4c8b46988290c4d2d5fed2d782892daf1a2716c738184306a289a41fb237ee2f |
| 301689.SZ | finalpage/2026-09-03/1225544675.PDF | response-05.pdf | 437046 | 6fd2ca25b5db3e245764d36593ba5a21e6bb373fddb989cb6a7ce297e18cce27 |
| 301699.SZ | finalpage/2026-09-01/1225537096.PDF | response-07.pdf | 549641 | 9169b5049fd2f17bd39cd440b8b769446f191d2a8b16dd70d776b28c68077bd6 |
| 603448.SH | finalpage/2026-09-04/1225547191.PDF | response-10.pdf | 994934 | 18232683beead59f4ff4948254f45dcbfb745bd748795a3fc77cef2452a498b4 |
| 688801.SH | finalpage/2026-09-01/1225538497.PDF | response-12.pdf | 3399165 | de6063647c1e8df2d1745ff0fdb9a33bbc7149e3c32aae149664c00385d372f0 |
| 688837.SH | finalpage/2026-09-02/1225542462.PDF | response-14.pdf | 2734521 | 48a1527c4d3b91d10b24e2f00bdd1d1c5f902929a636b132a59bafef60044fbf |
| 920201.BJ | finalpage/2026-09-03/1225547122.PDF | response-16.pdf | 666873 | e2c3609ef6655495eb7e161881f827bf5b79eba68f9f40489472bf9ab79ff91a |
| 920268.BJ | finalpage/2026-09-02/1225544140.PDF | response-18.pdf | 326596 | 98b726c0289e5186fd7df380c39c35c98e4901e4d4403ae06e8d51a65b61cda9 |
| 920269.BJ | finalpage/2026-08-28/1225526987.PDF | response-20.pdf | 458803 | 4dc10e8ced12f5dff385f155d7308c4099c64d8841298b619fe950d76b83385a |

The actual workflow rebuilt the plan from the frozen report and checked the exact retained-file inventory and body hashes even though acquisition was incomplete. After download, independent local checks reconciled ZIP identity, all 26 files, all 21 original body sizes/hashes, source/report/inspection/plan/provenance hashes, monotonically ordered request clocks, exact code/org identities, all returned announcement dates/IDs, full-document selection and the two zero-row outcomes. The original offline report was compared byte-for-byte with the prior archive and is unchanged. The verifier used independent standard-library checks, not a claimed full local project replay or Parquet scan.

Existing local pypdf 5.9.0 extracted at most the first thirty pages of each PDF, and all pages of the shorter documents. PyMuPDF rendered cover sheets and twelve relevant pages for visual checking. The nine PDFs have 40, 7, 8, 76, 162, 578, 18, 6 and 7 pages respectively; the long investor annexes were not fully read. In particular, this is not a complete read of the 578-page document. No OCR, new PDF parser, credentials or source re-download was used during local review. Full document bodies, not just extracted text, are retained in the 90-day artifact.

No source date or issuance date was substituted for actual system availability: these bodies were acquired on September 5. A retained source is evidence to evaluate, not permission to change the program. Historical first-vintage availability is not proved.

## Next operational priority

Do not continue adding generic infrastructure or rerun successful fixed-date samples. The two empty source queries and remaining field contracts should be addressed only by identified evidence that can settle them. Fixed September 4 qualification work must not be mistaken for a continuous status feed or distract from the separate first-new-session Sector proof. The producer still needs its directly contiguous completed-session append, real sealed-input replay and context artifact publication; do not use stock files to bridge an industry-session gap or enable schedule before that proof.

No runtime acceptance, denominator, company posture, market state/cache/events, 881/884 detector, Research/Inbox route or Human/Research/Investment authority changed. SHADOW OBSERVATION ONLY.
