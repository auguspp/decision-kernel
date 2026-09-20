# News / Industry Radar — 2026-09-20 retained-probe readback

Status: REUSE FEASIBILITY DEMONSTRATED / QUALITY GAPS RETAINED / NOT PRODUCTION ADOPTION.

This report supersedes the early-capture-only view in #297/5747325258 with the later captures already registered in #297/5747298151. Main remains `9933d61ee70018b1d8e54e187392a5c62362ca46`. The temporary experiment branch is not main, a production feed, an accepted Research result or an investment decision.

## Exact inputs actually downloaded and inspected in this continuation

| Source | Run / artifact | ZIP bytes | SHA256 |
|---|---|---:|---|
| NewsNow + saved company-name matching | 35486102537 / 10597975192 | 53446 | 8fdf2884e86f0b47c4a268345715d07471cdf14d7a5ac524f347ca9dc153fbe0 |
| HiThink completed-window industry probe | 35486156318 / 10597645925 | 127752 | 8aa291e84d4b9577c903e702c43c9c8263871bd9371e8ed641a1118d0b312502 |

Both ZIP digests and CRCs were checked. All listed raw responses were checked against the byte counts and SHA256 values in their original capture receipts. The offline review used no network/model calls and did not modify the original captures. This is an additional arithmetic/identity review, not a substitute for Kernel validators or full CI.

## News: reuse works; publication/meaning still require qualification

The retained sample contains 180 observations, 180 unique URLs and 21 possible title-based event groups. Source counts: CLS30, Wallstreetcn30, FastBull30, Jin1030 is NOT the count: Jin10 has25; MKTNews30, Gelonghui15 and Thepaper20. Seven NewsNow feeds succeeded; the two public RSSHub feeds failed403. Public-instance failure does not imply that the publisher or reusable project is unavailable.

The deployed Docker identity is `ghcr.io/ourongxing/newsnow@sha256:98b62bd971d308040937fdfde5263a00715b357894936e88b3ce3c0d8adbf55a`. The inspected source commit `newsnext/newsnow@0f95b2c998dffbfd2ddbc51b47b5809887dc6b97` is not proven to be the deployed image's source commit; that linkage stays UNKNOWN.

There are160 parseable publication claims and20 missing ones; none of those parsed claims is later than the recorded client fetch. The old summary key `observations_with_qualified_publish_clock` overstates this result: parsing is not timestamp qualification. Some source adapters derive time from relative text; service updatedTime may describe cache handling rather than article publication. Do not promote either to an independently verified publisher clock. Likewise, 21 possible groups are not21 verified independent economic events. Title matching can miss differently worded reports about the same event.

The frozen903-company-name reading yielded4 title matches across3 company identifiers. This continuation reviewed those4 matched headlines only, not the economic meaning of all180 observations:

| Company text candidate | Saved headline observation | Interaction-layer draft disposition |
|---|---|---|
| 中国移动600941.SH | CLS2488035 and Wallstreetcn3167768:6G prototype/interconnection testing with Qualcomm | One bounded question draft: does this represent a new commercial timetable, capital commitment or economic increment, or progress within an existing R&D plan? The two differently worded headlines may refer to the same event; primary-source identity must resolve that. |
| 国科微300672.SZ | Gelonghui5314996: broker maintains a buy rating | Analyst opinion retained. No new issuer operating evidence established; do not use the rating as automatic Pre admission. |
| 亿纬锂能300014.SZ | Gelonghui5314987: broker maintains a buy rating and discusses storage/cylindrical batteries | Analyst opinion retained. The title does not establish new orders, margins or materiality; no automatic Pre. |

These are company-name candidates, not proof of the relevant share class, issuer economic exposure or investment merit. For the 中国移动 draft, required next material is the original issuer/partner technical release and existing research context, with counterchecks for previously disclosed work and lack of commercial commitment. No source body was acquired here, no formal question declaration/admission was created, and qualified Pre candidates remain0. Other176 headlines are NOT_REVIEWED, not rejected as useless.

## Industry: final history exists, but no inflection truth claim

The final capture contains12 successful HiThink response envelopes and3 series. Each has118 price observations from2026-04-01 through2026-09-18; basis and warehouse windows each contain35 observations from2026-08-03 through2026-09-18. Actual price timestamps were checked against the declared window and for duplicates. This does not certify a complete exchange calendar or historical point-in-time availability.

The returned identifiers are `LCZL.GFE`, `CUZL.SHF`, `RBZL.SHF`: provider main-continuous series, NOT fixed-expiry main contracts. The early evaluator expected ticker CU/LC/RB while the basis snapshot returned cu9999/lc9999/rb9999. The original main_contract_thscode label therefore needs explicit continuous-series semantics. Multiple spot_indicator_id rows exist per variety and cannot be silently collapsed.

Actual price returns and first-to-last changes were recomputed from retained raw records:

| Variety | 5-observation return | 20-observation return | Reported basis-rate change, percentage points | Warehouse amount change, raw source unit |
|---|---:|---:|---:|---:|
| LC | -5.68165% | -19.86388% | +3.90 | +14553 |
| CU | +0.57803% | +1.73550% | +0.58 | +1517 |
| RB | -0.38610% | +1.87562% | +1.06 | +24018 |

Units and direction matter. The actual snapshot/history uses close_basis = converted_spot_price - close_price. Reported close_basis_rate values such as5.6 represent percentage points, not a unitless5.6; normalization gives0.056. The original unqualified +3.90 delta must not be presented as+390%. The amount unit for warehouse data was not established from this capture and is not relabeled as tonnes or lots.

All105 recent basis amounts reconcile to spot-minus-futures. Of the105 reported basis rates,103 reconcile within0.005 percentage points, the declared two-decimal nearest-rounding check. Two LC rows do NOT:

| Date | Spot | Futures close | Basis | Reported rate % | Recomputed rate % | Reported minus recomputed, percentage points |
|---|---:|---:|---:|---:|---:|---:|
| 2026-09-11 | 145100 | 134820 | 10280 | 7.09 | 7.0847691247 | +0.0052308753 |
| 2026-09-15 | 137500 | 129120 | 8380 | 6.10 | 6.0945454545 | +0.0054545455 |

The reason is UNKNOWN. Do not silently widen the tolerance, fix the source bytes, or call this an economic contradiction. The field-level discrepancy does not invalidate unrelated verified price arithmetic. A later adapter can retain reported and explicitly calculated rates separately; it cannot call the two values identical.

The archived PELT results remain retrospective shadow annotations; this continuation did not rerun ruptures and does not certify predictive value. Main-continuous roll composition, warehouse unit, fully comparable spot-indicator history and issuer materiality remain unestablished. Price decline plus increased warehouse receipts can motivate a supply/demand/registration question, but does not itself prove a fundamental downturn or identify a beneficiary. Qualified company exposure candidates remain0.

## Reuse decision and next bounded implementation seam

- News: reuse self-hosted NewsNow; do not build a crawler or deploy the full TrendRadar stack merely for collection. Preserve original observations, cache/publication-clock distinctions and candidate-only entity/event mappings.
- Industry: reuse existing HiThink transport. No additional AKShare price provider is needed for this sample. Bind actual continuous identifiers and spot IDs; preserve units, nulls, window and field-level discrepancies. Do not manufacture calendar completeness or rolling-contract economics.
- ruptures remains EVAL_ONLY, not a production gate. AKShare company mappings remain optional discovery claims, never DIRECT_EXPOSURE/MATERIALITY authority.
- The next runtime slice is a pure conversion/validation adapter feeding the existing company-first / Question layer. It is NOT implemented by this report. No new provider registry, scheduler, automatic Pre, Deep, Odds or Action is authorized by the observations.

## Continuation incident and cleanup

The continuation initially missed the later03:23 receipt and repeated news sampling. Two new branch writes triggered three additional completed push runs:35486730093,35486754205,35486754288. They are retained, not hidden, and are not used to inflate the canonical sample counts above. They are not Research runs or Re-runs. No new HiThink or model call was added by this continuation.

Both NewsNow-specific push workflow files were removed atomically in branch commit `e856cb9c776cd5a3ffdf49eb7b2b41e143530fe5`, preserving their old commits and artifacts. Do not push new live experiments to the obsolete probe branches. No experiment workflow, new dependency or runtime adapter was merged into main; no main-CI or production-acceptance claim is made.

AI Investment Authority = NONE.
