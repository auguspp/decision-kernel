# Stock fields: preserve the outlier, separate the unanswered questions

Review date: 2026-09-05. Status: READ-ONLY DIAGNOSTICS / SOURCE REMAINS DIFFERENCES_REQUIRE_REVIEW / NOT PRODUCTION QUALIFICATION.

## Scope and reproducibility

This review uses the already retained run `33959190974`, not a new market acquisition. Original evidence: artifact `9967375391`, ZIP SHA256 `ee7f5c1bdc955b0d4c86c898a2d035e632a93ba6429ab2bdcb2d75fb4273b812`. All 21 input file sizes/hashes and equality of the two saved inspection objects were rechecked locally. The original offline report hash is `668073931733d725abecb39a579495ebaad18a21b91f9b558be6a32fb366d5ce`; inspection hash is `823beb55ca45044a16e7e52172901a5bb60fd358c27030a85a6fb866326e523c`.

`runtime/hithink_dump_diagnostics.py` is a reading projection of that existing offline report. It does not load new quotes, decode Parquet again, infer corporate actions, add an epsilon or approve fields for production. It reuses the existing canonical identity functions and Python Decimal. No new dependency, workflow, network client, adjustment engine, scheduler or mutable review database is added.

```bash
python -m decision_kernel.runtime.hithink_dump_diagnostics \
  --report /trial/offline-inspection.json \
  --output /new/field-diagnostics.json
```

The command checks the saved report and inspection hashes, preserves source disposition and provenance hashes, and retains every original numeric discrepancy plus exact signed/absolute deltas. Field counts share the original checked denominator. Missing-bar records and missing/unpriced-set intersections are separate. Deterministic order is descending absolute difference, then exact code; quantiles use the nearest-rank definition, not interpolation. The largest-removed distribution is descriptive only: the largest item remains in `all_differences` and no identity is excluded. CLI exit 0 means the reading projection was written, not that the source data passed. Existing output and production `decision-state` output are refused.

Self-consistent hashes are not independent authenticity. This command does not rescan source files or prove original report generation; the preceding artifact/inventory review provides that association. The source's actual two Parquet scans occurred in Actions. Local work here executed the new diagnostic command, 17 focused tests, and hash/JSON arithmetic checks; it was not a full local repository test or new local PyArrow scan. Local copied `identity.py` and `primitives.py` had exact Git blob hashes `9f86067c4d51821ebc5c6cce56e390b795e90546` and `7d717854871eca5afabd4760f98d6c36a4ce8234` respectively. An initial local run rejected the existing previous-close `reason` field; the implementation/fixture were corrected against the retained shape before this PR. No provider input was edited.

Full diagnosis content hash: `2554cdbbb3bad9ba7e389b5850af606cafcec719792cb15bd2dd7ccb6fee16ab`.

## Actual numeric findings

| Field | Exact matches | Numeric differences | Missing comparison |
| --- | ---: | ---: | ---: |
| Latest close | 5548 | 0 | 19 current identities have no priced latest reference/bar, outside this checked denominator |
| Turnover | 894 | 4654 | same coverage boundary |
| Raw previous close | 5532 | 15 | 1 missing previous bar |

The 4670 diagnostic entries concern 4657 distinct identities; they are not disjoint stock counts. The 19 missing latest bars and 19 unpriced references are the same set, not 38 stocks.

Turnover absolute differences in original CNY units:

| Statistic | Amount |
| --- | ---: |
| Minimum | 0.01 |
| Median (nearest rank) | 0.59 |
| 95th percentile | 9.45 |
| 99th percentile | 43.33 |
| Largest | 10312354.49 |
| Largest among the other 4653 differences | 327.64 |
| Sum of absolute differences | 10326571.22 |
| Sum among the other 4653 differences | 14216.73 |

The largest is `920371.BJ`: raw dump turnover `49573155.51`, observed snapshot turnover `59885510`, delta `+10312354.49`, about 20.8023% of the dump value. It must be investigated separately from small precision-like differences. The next two largest are `000977.SZ` (327.64) and `300308.SZ` (194.35). These statistics do not establish any permitted rounding rule; no field is reclassified as accepted.

The inspected official dump and stock-snapshot specifications both identify turnover as original-currency amount, but no exact cross-endpoint quantization/precision guarantee was found in those specifications. A universal scale error or uniform rounding cannot simply be assumed. Primary specifications inspected: `HiThink-Tech/Financial-API` stock spec blob `c8d9cc7d636dbb944404328f0e254387afb80585` and dump spec blob `07e93d98ec02e33e6db6c1661c1d280a38a5fcb6`.

## Previous-close cases: preserve the evidence needed for event reconciliation

| Code | Previous raw close | Snapshot prev_price | Raw minus snapshot |
| --- | ---: | ---: | ---: |
| 000408.SZ | 76.86 | 75.86 | 1.00 |
| 001316.SZ | 27.79 | 27.44 | 0.35 |
| 002027.SZ | 4.82 | 4.77 | 0.05 |
| 002293.SZ | 11.41 | 11.13 | 0.28 |
| 002653.SZ | 68.01 | 67.48 | 0.53 |
| 002907.SZ | 14.71 | 14.68 | 0.03 |
| 002997.SZ | 28.78 | 28.63 | 0.15 |
| 300664.SZ | 4.73 | 4.68 | 0.05 |
| 300677.SZ | 55.92 | 55.82 | 0.10 |
| 300946.SZ | 37.53 | 37.41 | 0.12 |
| 301511.SZ | 89.61 | 89.51 | 0.10 |
| 301608.SZ | 45.2 | 44.86 | 0.34 |
| 603182.SH | 13.63 | 13.43 | 0.20 |
| 603259.SH | 156.63 | 156.12 | 0.51 |
| 920879.BJ | 13.38 | 13.3 | 0.08 |

Missing previous bar: `920289.BJ`. A missing bar is not a zero return or an inferred IPO. A price difference is not by itself proof of a dividend.

Reuse assessment: the official upstream adjustment implementation exists at https://github.com/HiThink-Tech/Financial-API/blob/765513c2616030803ad80915ed65b205f425a942/python/marketdb/calculations/adjustment.py (blob `df9e5d60ada6953b14452aff94f4c4c14137aa2f`). It uses DuckDB and explicit cash/bonus/rights events with raw K-lines to rebuild forward/backward factors. It is not an event source or publication-time proof. We reviewed it rather than writing another adjustment engine, but have not installed or executed that database workflow, supplied qualified events, or adopted adjusted prices. Null-coalescing and effective-date mapping must not be mistaken for evidence that absent events were observed as zero.

## Coverage evidence and outstanding source review

The 19 original missing/unpriced identities remain in the denominator:

```
000016.SZ 002731.SZ 002870.SZ 002998.SZ 301139.SZ
301266.SZ 301686.SZ 301689.SZ 301699.SZ 600929.SH
601091.SH 603448.SH 688432.SH 688801.SH 688837.SH
920201.BJ 920268.BJ 920269.BJ 920298.BJ
```

A primary-domain search excerpt of SSE announcement [2026]28, published September 4, states that `603448` starts trading September 7:
https://www.sse.com.cn/disclosure/announcement/listing/ipo/c/c_20260904_10831265.shtml
This supports a specific not-yet-trading explanation for that code at the comparison date, not exclusion of all 19. Original HTML bytes could not be fetched by the available browsing/local transport in this review; this is a manually reviewed indexed excerpt, not a sealed raw-source observation or an automatic eligibility override. The machine diagnostic cause labels remain unestablished.

Further searches surfaced leads for block-trade inclusion in `920371`, issuer dividend disclosures for the previous-close cases, and a listing announcement for `920289`. Their original exchange/issuer bytes and full operational conventions have not been reconciled here. Secondary summaries are not accepted fact records; no root cause, gross-dividend adjustment or stock-status classification is committed on their authority. In particular, cash paid per participating share can differ from the cash amount used for the exchange ex-price when repurchased shares do not participate. Obtain the implementation notice, capital base, effective date and explicit exchange rounding convention before computing a claimed exact reconciliation.

## Next bounded tasks, not repeated whole-market trials

1. For turnover, obtain the provider's precision and trade-type inclusion contract separately. Prioritize `920371.BJ`; compare original regular/block/fixed-price trade records and volume/amount scope before attributing the large delta. Do not adopt an empirical epsilon for the other 4653 rows.
2. Obtain the 15 exact effective-date corporate-action records and relevant implementation notices, including nonparticipating capital/rights where applicable. Use the reviewed upstream tool only on an isolated qualified event dataset; preserve raw history and availability clocks.
3. Confirm the 19 per-code listing/trading statuses and the missing previous bar from primary records. New listing, suspension, delisting and missing data are different states; no blanket deletion or forward filling.
4. Only a naturally later overlapping market vintage can test corrections. Longer history and explicit membership semantics remain necessary before 20/60-day breadth. Checked latest closes are evidence of same-provider field agreement, not permission to activate a price-only production panel.

No live HiThink request, new file download, workflow/dependency edit, production writer, threshold, company posture or authority change occurred in this slice. The original trial remains failure / DIFFERENCES_REQUIRE_REVIEW. Sector's direct-next-session, real input-replay and context-publication proofs remain pending; its last real state still ends September 4, with zero prospective events. Do not add a schedule or bridge missing industry sessions with stock files.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
