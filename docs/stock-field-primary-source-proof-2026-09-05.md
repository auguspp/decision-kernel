# Stock-field primary sources: actual capture and remaining distinctions

Evidence date: 2026-09-05. Status: 15 EFFECTIVE-DATE EVENT RECORDS / TWO ORIGINAL ISSUER NOTICES / TARGETED RAW HISTORY OBTAINED / NO PRODUCTION STOCK PANEL.

## Implementation and actual operation

PR #218 base `2b50c94436727f21c13673556bba7ce695fb353d`, head `0221181415c1c8e83da09c298c6bd8fba68bd0bf`, merge/executed implementation `9b062cd5b7024ddd9ecc74129e0a36767f5e4f10`.

Exact five new files (645 additions, no deletions):

```text
.github/workflows/stock-field-source-study.yml
src/decision_kernel/runtime/stock_field_source_study.py
tests/test_stock_field_source_study.py
tests/test_stock_field_source_study_workflow.py
docs/stock-field-source-study.md
```

Full PR CI `33963783988` / job `101300150219`: 722 passed in 10.07s, 25 new cases. Main kernel CI `33963949069`: success. Local pre-PR validation was syntax compilation, not a full local repository run.

One narrowly triggered main-push run `33963949084` / stock-field-source-study #1 / attempt 1 completed successfully. Its source result is `CAPTURE_COMPLETE_REVIEW_REQUIRED`, not a green price-qualification result. The exact prior comparison artifact was restored through Actions; the old report, its nested inspection and four original input hashes were checked before acquisition. No whole-market file or stock snapshot was downloaded again.

Actual collection bounds:

```text
started_at   = 2026-09-05T11:40:26.964763Z
completed_at = 2026-09-05T11:41:04.616491Z
requests     = 21, all once, all HTTP 200
retained original bodies = 21
HiThink = 15 same-date event queries + 1 two-day unadjusted history query
CNINFO  = 1 public organization directory + 2 announcement queries + 2 original PDFs
problems = 0
causes automatically accepted = 0
market-state writes / events created = 0 / 0
```

The source plan is tied to frozen comparison session 2026-09-04. The collection clocks are actual September 5 acquisition times, not backdated availability. Current event responses do not contain historical publication/PIT clocks. Original providers' dates, numeric values and raw JSON bytes were not normalized in place or overwritten.

## 1. All fifteen discrepancies have a corresponding same-date event record

Every returned event stream contained exactly one event with exact requested identity, `ex_date_ms=1788451200000` (2026-09-04 Shanghai midnight), and `per_share_bonus=0`. These are provider-reported event facts, not fifteen independently reviewed issuer implementation notices. The endpoint does not establish all rights/treasury-share/rounding conventions.

The arithmetic below is only a diagnostic subtraction of the reported gross cash amount, not an adopted exchange ex-price formula or adjusted-price series:

| Code | Frozen raw previous close | Frozen snapshot prev_price | Provider dividend per share | Raw minus gross cash | Snapshot minus that subtraction |
| --- | ---: | ---: | ---: | ---: | ---: |
| 000408.SZ | 76.86 | 75.86 | 1 | 75.86 | 0 |
| 001316.SZ | 27.79 | 27.44 | 0.35 | 27.44 | 0 |
| 002027.SZ | 4.82 | 4.77 | 0.05 | 4.77 | 0 |
| 002293.SZ | 11.41 | 11.13 | 0.28 | 11.13 | 0 |
| 002653.SZ | 68.01 | 67.48 | 0.526 | 67.484 | -0.004 |
| 002907.SZ | 14.71 | 14.68 | 0.035 | 14.675 | 0.005 |
| 002997.SZ | 28.78 | 28.63 | 0.15 | 28.63 | 0 |
| 300664.SZ | 4.73 | 4.68 | 0.05 | 4.68 | 0 |
| 300677.SZ | 55.92 | 55.82 | 0.1 | 55.82 | 0 |
| 300946.SZ | 37.53 | 37.41 | 0.12 | 37.41 | 0 |
| 301511.SZ | 89.61 | 89.51 | 0.1 | 89.51 | 0 |
| 301608.SZ | 45.2 | 44.86 | 0.33938 | 44.86062 | -0.00062 |
| 603182.SH | 13.63 | 13.43 | 0.2 | 13.43 | 0 |
| 603259.SH | 156.63 | 156.12 | 0.51 | 156.12 | 0 |
| 920879.BJ | 13.38 | 13.3 | 0.08 | 13.30 | 0 |

Twelve diagnostic subtractions equal the observed two-decimal snapshot value exactly; three do not. This does not mean twelve complete cause reconciliations. In particular, the first original issuer notice below is a counterexample to treating gross cash as the exact ex-price deduction even when the displayed two-decimal subtraction agrees.

## 2. Original issuer PDFs strengthen and constrain interpretation

CNINFO's exact-code organization lookup produced a unique notice per query, with `hasMore=false` and one returned announcement. The returned original PDF URLs were then fetched once from the fixed official document host. Both are four-page PDFs. pypdf extracted their text locally, and rendered pages 1 and 2 of both documents were independently inspected visually; no OCR was used.

### 000408.SZ / 藏格矿业 / notice 2026-061

Original: https://static.cninfo.com.cn/finalpage/2026-08-28/1225521733.PDF

```text
retained file = capture/response-19.pdf
bytes = 124010
SHA256 = a714b0ac5300c5dae61a0730a6060dfde57da7eb61a7410035387b326086c91a
request_start = 2026-09-05T11:40:58.390760Z
processing_complete = 2026-09-05T11:41:02.985910Z
```

The original notice, dated August 28, states total shares of 1,568,914,754, excluded treasury shares of 5,025,600, participating shares of 1,563,889,154, cash of CNY10 per ten participating shares and total cash CNY1,563,889,154.00. Page 2 states record date September 3 and ex-date September 4, matching the queried event date.

Crucially, page 1 explicitly prescribes a different ex-price deduction: CNY9.967967 per ten total shares, truncated to six decimals, then CNY0.9967967 per share. Applying the issuer's stated deduction to frozen raw close 76.86 gives 75.8632033 before any final quotation formatting. Naively subtracting the provider's gross dividend 1 gives 75.86. These are not the same underlying price formula. A two-decimal display can conceal that distinction; final exchange/provider rounding and quotation semantics are not established just because 75.86 looks consistent.

Conclusion: the cash event and treasury-share exception now have retained original issuer evidence. Do not use the gross event field as a universal adjustment multiplier, and do not mark this stock automatically reconciled by the gross-cash identity.

### 001316.SZ / 润贝航科 / notice 2026-059

Original: https://static.cninfo.com.cn/finalpage/2026-08-28/1225519927.pdf

```text
retained file = capture/response-21.pdf
bytes = 114438
SHA256 = c1780013797d3223cdbba0a48b991adbf677d7d16257db184b908adfbc76ff20
request_start = 2026-09-05T11:41:04.084969Z
processing_complete = 2026-09-05T11:41:04.616483Z
```

Pages 1–2 state a distribution base of 161,161,588 shares, CNY3.50 per ten shares, no bonus or capital-reserve conversion, total cash CNY56,406,555.80, record date September 3 and ex-date September 4. The arithmetic `27.79 - 0.35 = 27.44` agrees exactly with the frozen snapshot reference. This sample now has original notice support for the event and a consistent cash-only arithmetic explanation. It does not authorize a production adjustment rule for other stocks.

The title calls this the 2026 interim distribution, while one sentence on page 2 says 2026 annual distribution. That source wording discrepancy is retained; the text was not silently rewritten. The actual notice identity, dates, amounts and documented decision context are preserved. CNINFO's date-only announcement metadata is not proof of the first public-release time or earlier system ingestion.

## 3. The large turnover outlier remains a scope question

The newly captured targeted raw REST history (`capture/response-16.json`) returns the September 4 turnover for 920371.BJ as **49,573,155.51**, equal to the frozen Parquet amount reported by the prior exact inspector. Close 7.73 also equals the frozen reference. The targeted history volume is **6,491,251 shares**, while the frozen snapshot contains **8,474,396 shares** and amount **59,885,510**.

```text
snapshot minus targeted/raw amount = 10,312,354.49 CNY
snapshot minus targeted/raw volume = 1,983,145 shares
```

This establishes an additional same-provider endpoint comparison: raw REST history agrees with the stored raw-file amount, while snapshot differs in both volume and amount. It is not independent exchange validation or proof of which trade types each field includes. The historical query occurred later than the frozen snapshot capture, and its current response is not a historical first-vintage receipt.

Secondary reports continue to point to three September 4 block trades at 5.2 CNY and approximately 1,031.24 ten-thousand CNY. Those reports are research leads, not retained original BSE transaction records. No exact block-trade rows, provider inclusion contract or turnover precision rule has been obtained in this study, so the turnover cause remains unaccepted. No large difference was discarded to allow the small differences to pass.

## 4. Rules reviewed without importing an unrelated rounding rule

The official SZSE 2026 trading-rule publication and PDF were consulted:

- https://www.szse.cn/lawrules/rule/trade/current/t20260424_620190.html
- https://docs.static.szse.cn/www/lawrules/rule/allrules/bussiness/W020260424690713155663.pdf

The publication identifies an effective date of July 6, 2026. Section 4.4.2 gives the ex-reference formula and allows issuer-specific approved changes; 4.4.3 uses the ex-reference price as the change-rate base. Section 3.3.19's nearest-tick rounding text concerns price limits and allowed order-price ranges. It must not be repurposed as sufficient documentation of the provider's final ex-reference-price rounding. This rule review used the browser's primary-source parsed PDF and a page-14 screenshot; it is not a raw rulebook included in this Actions archive. No rule-derived runtime behavior was changed.

## Evidence integrity and reproducibility

```text
artifact = stock-field-source-study-33963949084-1
artifact id = 9968826124
ZIP bytes = 429030
ZIP SHA256 = 4ddb0a01e08fd207bc26a19cbe2bbe41512158294d626369e739fe5351a97e81
expires_at = 2026-12-04T11:40:08Z
source report hash = 668073931733d725abecb39a579495ebaad18a21b91f9b558be6a32fb366d5ce
plan hash = 4374b4a2c3012e60b0fb59ed4c001ae903ab25cb254c4e9a2df79703713ef970
study hash = 482ccc3bb9af58803ee2abdbc4068dbd10ffc2865e45561bc206015ff9c43c40
workflow provenance hash = 9a36114e498a9016f8fe26c76eae124443db7bc0e73cb1cf7c1ab5ab6651a7ae
```

The 26-file archive comprises 21 original HTTP bodies, plan/report/summary, the byte-identical prior offline report and workflow provenance. The workflow's offline verification step actually completed: it rebuilt the plan from the frozen report, checked the study/plan hashes and exact retained-file inventory. Independent local review checked the ZIP, all 21 body sizes/hashes, both source report hashes, original four input hashes, sequential request clocks, exact event identities/ex-dates/values, targeted history, notice-query identities, PDF text and rendered sample pages. Decimal arithmetic produced the displayed comparisons. No network replay, new full Parquet scan or full local project test is claimed.

The archive lasts 90 days, not forever. The issuer URLs alone are not durable identities; keep the hashes and retained artifact. Original provider/issuer bytes are evidence, not automatically trustworthy instructions or permission to change the program.

## What changed and what did not

We now have retained source evidence for all 15 event dates, two original issuer distribution samples and a targeted raw-history comparison. The prior missing-evidence statement is narrowed for those exact items. The original stock-file inspection remains `DIFFERENCES_REQUIRE_REVIEW` and production qualification remains `NOT_ESTABLISHED`.

Still pending: original BSE transaction details and provider amount/volume scope; documented precision; the other issuer implementation conventions where required; final ex-reference rounding; the 19 missing/unpriced statuses and missing prior bar; naturally later overlapping-vintage behavior; longer history and historical/current-membership semantics. No automatic event-to-price transformation, exclusions, filling, tolerance or 20/60-session breadth was introduced.

Existing Requests, Actions artifact restore and project validators were reused. The maintained AKShare CNINFO adapter informed the exact organization/query protocol, but its package and unbounded paging were not installed/executed. Existing pypdf/Poppler read the actual notices; there is no new PDF parser or adjustment engine. This study added one retained isolated workflow, not a schedule. It did not invoke the Sector producer, write market state/cache/events, alter thresholds or company decisions, route Research or change Human/Research/Investment authority.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
