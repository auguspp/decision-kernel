# First real bounded theme capture — 2026-09-06

Status: COMPLETE_BOUNDED_THEME_CAPTURE / ORIGINAL RESPONSES REBUILT / NOT DAILY THEME PRODUCTION.

## Exact implementation and execution

PR #240 adds the real-source shell around the existing PR #239 offline theme probe. Base `9f25e5dd044447f626700db20c9b6de969e13bb1`, PR head `2cf029f136a0ba3bf04ca1198d931290ba59beba`, merge `fe5bbb46cc61b35f23b2321c13cf1db26628b6ee`. The full PR CI `34004032947` / test job `101407893092` passed 1147 tests in 35.43s. The merged main CI `34004111534` / test job `101408099109` passed 1147 in 37.83s; its pre-existing Judgment Timeline delivery also succeeded, but is unrelated to theme capture proof. This PR added 24 tests over 1123 and its first CI passed.

Exact scope, six files +628/-6:

- `.github/scripts/capture-theme-probe.py`: +290.
- `.github/workflows/hithink-stock-dump-trial.yml`: +80/-2.
- `docs/theme-radar-capture-v0.md`: +41.
- `radar_inputs/theme-probe-sample-v0.json`: +13.
- `tests/test_hithink_dump_trial_workflow.py`: +10/-4.
- `tests/test_theme_capture_trial.py`: +194.

One main-push compatibility trial ran at that exact merge: `hithink-stock-dump-trial` #6, run `34004111618`, attempt 1, theme job `101408099484`. Capture, offline reconstruction, upload and Summary all succeeded. The original stock-dump job `101408100015` was skipped: this was NOT another all-stock Parquet download. No second trial or retry was issued.

Artifact `theme-probe-trial-34004111618-1`, ID `9980435687`, ZIP bytes `615263`, SHA-256 `4314cf0f02fb001c976dfb09722893664d7f51ec6bd484e17f81107915fe2b02`. Created `2026-09-06T01:34:51Z`, expires `2026-12-05T01:31:20Z` under the existing 90-day retention. It has 19 files. Open `capture/index.html` after downloading/extracting, retaining the other files for verification. No hosted website or public release was created.

## Selection and actual request budget

The exact-name criteria 机器人概念 and 人形机器人 were committed before quotes were collected, with fixed 881 probes 通用设备 / 汽车零部件 / 自动化设备. The real catalog contained 390 concept identities and 320 industry identities (the unchanged 90/230 industry split). It uniquely resolved:

| Exact captured name | Resolved concept identity |
| --- | --- |
| 机器人概念 | 885517.TI |
| 人形机器人 | 886069.TI |

No returned gain, ranking or membership size selected these samples. Concept names/codes were not replaced when inconvenient; both original criteria matched. This is an implementer-declared engineering sample, not an independent prediction or Human approval.

Ten requests were attempted exactly once, all HTTP 200: two catalogs, one explicit snapshot for CSI300 and the two concepts, two histories, and five current-member requests. Twenty-second pauses preceded every request after the first. No all-market stock snapshot, individual-stock history, full-industry member scan, alternate source, API retry or company disclosure fetch occurred.

Capture started `2026-09-06T01:31:36.362329Z`; the two catalogs had arrived by `01:31:58.984284Z`; plan was frozen at `01:31:58.987868Z` before the first snapshot request at `01:32:19.369029Z`. Final member response arrived at `01:34:47.330267Z`; input cutoff `01:34:47.336834Z`; page generated `01:34:47.355185Z`. All are September 6 UTC, not September 4 market observations.

## Historical path is not a prospective discovery

The comparison uses the manifest-validated committed September 4 state only as a frozen study input. Both concept histories contain exactly its 127 completed sessions, `2026-03-05` through `2026-09-04`, no initial/intermediate/latest gap. Existing math reads its last 126 observations, beginning March 6. The snapshot benchmark latest and previous closes match the saved benchmark; both theme latest/previous close and latest volume/turnover match their date-keyed histories exactly, without rounding tolerance.

Percentages below are display-rounded; complete Decimal values and dated raw responses are retained. Excess is the arithmetic difference in return, reported here in percentage points, not a compounded trade return.

| Concept | 5d index / excess | 20d index / excess | 60d index / excess |
| --- | --- | --- | --- |
| 机器人概念 | -0.0182% / +1.3081 pp | +0.1278% / +3.2462 pp | -4.0943% / -0.4021 pp |
| 人形机器人 | -0.3728% / +0.9535 pp | -1.4456% / +1.6728 pp | -7.9536% / -4.2614 pp |

CSI300 returns are -1.3263%, -3.1184%, -3.6922% over those respective windows. This illustrates why positive excess must not be presented as positive absolute return. Positive 20d excess persisted 20 computable sessions from August 10 for robotics, and 19 from August 11 for humanoid robotics; neither run is left-censored in the supplied window. These are computed path start dates, NOT when this system first noticed the concepts. Five-session changes in 20d excess are -4.0971 and -5.5748 percentage points, respectively. Turnover pulse is approximately 0.8393 and 0.7916. No gate, ranking, price forecast or recommendation is inferred.

This is September 6's acquisition of historical paths, not an original September 4 prospective signal or a tradable entry at that close. The ordinary Sector producer was not dispatched and its future direct-next-session acceptance remains pending.

## Membership and cross-industry results

These are the provider's returned CURRENT membership sets at this capture, not independently certified economic exposure, all actively trading shares, historic index constituents or index weights.

| Set / intersection | 机器人概念 | 人形机器人 |
| --- | ---: | ---: |
| Total returned unique members | 1227 | 466 |
| 通用设备 881117.TI (253 members in queried industry) | 110 | 54 |
| 汽车零部件 881126.TI (275) | 126 | 76 |
| 自动化设备 881171.TI (99) | 67 | 34 |
| Unassigned within these three queried industries | 924 | 302 |
| Ambiguous multiple-industry matches | 0 | 0 |

Both have exclusive observed members in all three supplied industry sets, so the existing narrow status is `OBSERVED_ACROSS_PROBED_INDUSTRIES`. This does not establish complete industry coverage. Unassigned means outside this three-probe intersection, not industry-less; the 1227-member label is not a concentrated or economically homogeneous portfolio. Membership-only denominator must not become a priced-stock breadth denominator. No per-stock quote, suspension/listing eligibility or company-business verification was acquired here.

The concepts share 403 members. Their union is 1290, summed memberships 1693, Jaccard 403/1290 = 0.3124031007751937984496124031. Of the smaller set, 403/466 = 86.4807% overlaps, but 63 humanoid-robotics members are outside robotics; 824 robotics members are outside humanoid robotics. Neither set contains the other. These are NOT a parent-child taxonomy or two independent forecast samples. No automatic merge, forced industry assignment, historical overlap or causal explanation was created.

## Reproducibility checks actually executed

The Actions verification invoked the existing full probe from original raw JSON responses: it re-resolved exact catalog names, reconstructed the frozen request plan and normalized inputs, recalculated the entire report, and compared JSON and HTML. Result `ORIGINAL_RESPONSES_PLAN_AND_PAGE_REBUILT`, no network calls or production writes. The underlying offline probe retains its `SUPPLIED_HITHINK_RECORDS_NOT_LIVE_CERTIFIED` label; the separate live-capture receipt and actual workflow establish where the input was acquired. Neither layer is a signature or an independent truth guarantee.

Downloaded archive was independently checked locally for exact ZIP digest, all 19 file names, all 16 inventoried input/output hashes (2,678,999 bytes), run/attempt/commit, request/receive clocks and spacing, raw catalog identities, all 127 dated bars per theme, snapshot/reference agreement, all 5/20/60 returns, and membership intersections/union/denominators. No binary-float normalization or replacement market values were used. Full project tests and exact module reconstruction occurred in Actions; local inspection is independent archive/JSON/Decimal validation, not a full local repository test run.

The exact archived HTML was also loaded into local Chromium memory with external requests blocked. At 1440px and 390px widths there was no document horizontal overflow; both native details controls existed and expansion worked; the page initiated zero network requests. A desktop screenshot was visually checked. This is not Safari/physical-phone/file-URL navigation or hosted deployment validation.

Important identities (all raw bytes remain necessary):

```
market state 2963d7fa62757a56e7296b3d9855a7d6d067d59816738078361f86c51d1f41d7
plan a4de27cb38989ce9f690c99027dbd7f952af5041cf14b198f4b8e38468032454
capture 45a2846a6ae850972e1427e47af04bb20ad34e987b105aecccc6e6be0959e572
projection 2123a93cf4253a4b8debda7dda92c23f8e9db9261796c09ec3a5c000d98c2edf
concept catalog eb20585a394ca5aa24cab883d3607fbd7e9e74ef7a971e577ef9022d57ae06df
industry catalog 367d64660f5ef1f715ae0ef1d832a180d075ec7d6fc0a915797cbfafbd33f360
```

## Boundary and next substantive gap

The real bounded capture and its remote page/data delivery are now proven for this single sample/window. This does NOT establish all-theme discovery, a daily producer, candidate corpus, stock-price breadth, independently calibrated quality, economic profit transmission or T+5/T+20 outcomes. No new genuine event, company stance, threshold, Human Decision/Action, Research route, canonical wake, normal market-state/cache/ledger write or schedule occurred. Human / Research / Investment / signal-transition authorities remain NONE.

The fixed bootstrap trial will refuse a later weekday rather than silently extend stale state. After artifact expiry, exact saved bytes must be preserved separately; hashes alone cannot restore them. Repeating the same fixed sample is not the next proof. Theme discovery input/selection and qualified current participation remain substantive gaps; any future automatic scan needs explicit universe, request budget and eligibility semantics before being promoted into the normal Radar.
