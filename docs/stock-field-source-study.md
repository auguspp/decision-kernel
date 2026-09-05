# Frozen stock-field source study

Status: IMPLEMENTED SOURCE COLLECTION / LIVE RESULT MUST BE VERIFIED SEPARATELY / NO PRICE ACCEPTANCE.

## Purpose

The frozen run 33959190974 already provides the complete ten-session stock-file comparison. Do not download it again to make the result green. Use its exact offline report and four original input hashes to identify specific unanswered questions, then collect only relevant source evidence.

The first reviewed plan requests the 15 prior-close cases' event streams for 2026-09-04 and the largest turnover outlier's two-day unadjusted REST history. It also attempts two issuer implementation-notice samples, 000408.SZ and 001316.SZ, from CNINFO's public directory, search and original-PDF hosts. These samples distinguish ordinary cash from treasury-share exclusions; they are not all-company eligibility coverage. A gross cash dividend is not automatically the exchange ex-price deduction.

No signing endpoint, full stock snapshot, new Parquet download, current membership or sector-state endpoint is called. The 19 unpriced/missing stocks are not discarded or assigned a cause by this study. BSE's original block-trade records and the provider's turnover inclusion/precision contract remain separate evidence requirements; a REST history comparison alone cannot prove them.

## Reuse decision and primary contracts

- HiThink's exact event/history endpoint specification: https://github.com/HiThink-Tech/Financial-API/blob/765513c2616030803ad80915ed65b205f425a942/docs/api/endpoints-prices.md ; blob c8d9cc7d636dbb944404328f0e254387afb80585.
- Official factor implementation already reviewed, not reimplemented: https://github.com/HiThink-Tech/Financial-API/blob/765513c2616030803ad80915ed65b205f425a942/python/marketdb/calculations/adjustment.py ; blob df9e5d60ada6953b14452aff94f4c4c14137aa2f. It requires event inputs and does not establish original publication times.
- CNINFO query contract was checked against the maintained AKShare adapter: https://github.com/akfamily/akshare/blob/8e95744b79ae22326308ccd2b4e62650c5b53c55/akshare/stock_feature/stock_disclosure_cninfo.py ; blob 2b964689cef6e72dae93beeaf86019a81586082d.

The adapter exists. Its HTTP transport, repeated first-page request, all-page collection and DataFrame projection are not imported as an unbounded crawler. This fixed study uses Requests plus the same documented organization lookup and query fields, but HTTPS, one query per selected issuer, no pagination and original response retention. Reuse existing project safe-JSON, canonical identity, file-hash and Requests-session/response helpers. There is no new dependency, PDF parser, adjustment engine, scraping framework or review queue. PDF content review uses the already available pypdf tooling outside price acceptance.

## Source and output boundaries

The CLI pins offline report hash `668073931733d725abecb39a579495ebaad18a21b91f9b558be6a32fb366d5ce` and verifies its nested inspection plus all four original file hashes. Output must be a new directory outside `decision-state`. Prior artifacts and prices are never overwritten. Example:

```bash
python -m decision_kernel.runtime.stock_field_source_study \
  --frozen /downloaded/run-33959190974 \
  --output /new/stock-field-source-study
```

The operation records the exact source plan, original successful HTTP body bytes, public request parameters, request-start and processing-completion clocks, numeric HTTP status, file hashes and a hashed report. Completion clocks are actual capture bounds, not fabricated provider publication timestamps. No HTTP authorization, cookies, signing response, error body or usable signed URL is retained. A failing operation retains only safe exception class/status; response-shaped JSON provider errors can be retained as failed evidence, never as valid events. Requests are sequential, attempted once, have explicit timeouts, and disable redirects, environment credentials and proxy settings through the reused fresh-session helper.

Budgets: at most 24 requests, 8 MiB per body, 32 MiB retained bodies. A complete current plan is at most 21 requests: 15 events, one targeted history, one public organization directory, two notice queries and at most two PDF downloads. Provider credentials go only to the fixed HiThink origin. CNINFO originals must be unambiguous exact-code notices and use a returned, validated `finalpage/date/numeric-id.PDF` path on the fixed public PDF origin. Empty/ambiguous/incomplete notice queries remain failures; no mirror or guessed PDF is substituted.

`CAPTURE_COMPLETE_REVIEW_REQUIRED` means the bounded requests returned structurally usable source bodies, not that all event dates/values or prices have been reconciled. An empty valid event response is retained, not treated as proof no event occurred. `INCOMPLETE_SOURCE_STUDY` remains nonzero. Both keep the original `DIFFERENCES_REQUIRE_REVIEW` and unconditional production qualification `NOT_ESTABLISHED`. Current event queries do not provide historical publication/availability evidence. The study does not alter acceptance, prices, denominators or detector thresholds.

Injected transport must carry `SYNTHETIC_TEST_ONLY`. Synthetic PDF fixtures only test bounded container capture; they are not original notices or PDF extraction tests. Full repository tests run in CI; no live requests occur in those tests.

## Workflow

The separate `stock-field-source-study.yml` is a retained isolated study, not a daily producer or temporary repair workflow. It runs on fresh manual main dispatch or narrowly filtered main changes to this module/workflow. The original run's named artifact is downloaded using the maintained Actions downloader and is refused if the report/file hashes do not match. The HiThink secret exists only in the explicit source-collection step. Original input and output hashes are checked offline before evidence upload. Artifacts last 90 days. No cache, production state, canonical Inbox, schedule, code-writing job or retry action is present. A documentation-only state sync does not trigger another collection.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
