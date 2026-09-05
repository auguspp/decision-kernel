# Public economic-node pilots — 2026-09-05

Status: TWO BOUNDED SOURCE STUDIES / REVIEWED OFFICIAL EXCERPTS / NO AUTOMATED FEED / NO FUNDAMENTAL STATE MIGRATION / NO INVESTMENT AUTHORITY.

## Deliverable and limits

This is the first small implementation of the approved independent economic-observation path. It does not wait for a sector price candidate, and it does not use market strength as economic evidence. It covers only two explicitly selected nodes, with two reviewed releases each. The selection reflects the original livestock discovery pressure case and the earlier express-unit-economics node; it is not an industry-wide coverage claim.

`runtime/economic_node_study.py` normalizes narrowly defined, manually reviewed official text excerpts, preserves period/publication/capture identity and emits content-hashed study observations. A comparison is descriptive only. No source crawler, recurring schedule, alert gate, company mapping, Kernel enum, Research route or prospective market event is added.

## Source observations actually reviewed

The four original official web pages were opened and their relevant statements reviewed on 2026-09-05. The selected text and review capture clock are committed in:

```text
radar_inputs/economic-node-study-2026-09-05.json
```

The capture method is `REVIEWED_OFFICIAL_WEB_EXCERPT`. Each record contains selected, non-contiguous source lines, not the whole article or original HTTP/HTML bytes. Its excerpt hash proves the saved extraction's integrity, not origin authentication, completeness or the original historical publication vintage. The common review clock is 2026-09-05T04:51:30.793710+00:00. The pages had been retrieved by then; this clock identifies the research capture, not an automated provider request.

### Livestock price/feed node

Original sources:

- https://xmsyj.moa.gov.cn/jcyj/202608/t20260825_6486995.htm — published 2026-08-25, observations collected 2026-08-20.
- https://xmsyj.moa.gov.cn/jcyj/202609/t20260901_6487189.htm — published 2026-09-01, observations collected 2026-08-27.

Scope: the Ministry of Agriculture and Rural Affairs' monitoring of 500 county markets and collection points. Units are CNY/kg.

| Metric | 2026-08-20 | 2026-08-27 |
| --- | ---: | ---: |
| National live-hog average price | 11.52 | 11.55 |
| National corn average price | 2.46 | 2.46 |
| Fattening-pig compound-feed average price | 3.35 | 3.35 |

The difference from the reported rounded hog-price levels is +0.03 CNY/kg, about +0.2604%. The published weekly percentage is rounded to +0.3%; these are not conflicting facts and the computed ratio must not be passed off as the publisher's unrounded underlying statistic.

The two unchanged feed observations are not evidence of unchanged farm costs. Feed consumption, productivity, piglet costs, other costs, company procurement and reporting lags are not established here. No farm or company profit is calculated.

### Express-unit-economics node

Original sources:

- https://www.spb.gov.cn/gjyzj/c100015/c100016/202607/a31abbec99be4e0d80188b1a25fe1fe6.shtml — published 2026-07-17, includes June monthly data.
- https://www.spb.gov.cn/gjyzj/c100015/c100016/202608/b38ba608fef440bb89db1e7c3a9fddbf.shtml — published 2026-08-14, includes July monthly data.

Use only the explicit monthly express-business paragraphs, not cumulative Jan–June/Jan–July and not total postal activity.

| Metric | June 2026 | July 2026 |
| --- | ---: | ---: |
| Express revenue, CNY100 million | 1360.4 | 1303.7 |
| Express volume, 100 million parcels | 175.1 | 170.8 |
| Revenue per parcel proxy, CNY/parcel | 7.7693 | 7.6329 |

The ratio is revenue/volume because the two 100-million unit factors cancel. Computed with Decimal precision 28, its descriptive month-to-month change is about -1.7553%. That does not prove like-for-like delivery prices fell: geographic/product/customer mix, seasonality, scope and rounded totals remain relevant. It also says nothing directly about a particular courier's revenue, cost or profit. No seasonal adjustment is claimed.

These observations suggest a question for later research, not a finding about an industry cycle: which part of an aggregate change reflects business mix, comparable unit revenue, and company-level costs?

## Time and version discipline

The record separates:

1. collection date or calendar reporting month;
2. publisher's date-only release label;
3. the system's actual review capture time.

A date-only release never receives a guessed 09:00 or market-close timestamp. Current retrieval of an older web page is not proof of the page's first historical vintage. System-PIT eligibility starts at the actual capture, not at the older publication date. A comparison requested before capture is rejected.

Same-period changed observations are labeled `REVISION_NOT_NEW_PERIOD`. Content-addressed persistence is append-only and idempotent for the exact same record; it cannot overwrite an earlier version. A hash recomputed over a forged derived value is insufficient: the implementation reconstructs the observation from the saved source text and rejects disagreement.

No next-release due date has been qualified, so `next_release_due` is null and freshness is `NEXT_RELEASE_SCHEDULE_NOT_QUALIFIED`. A weekly/monthly label is not used to guess an overdue date or infer weakening from lack of an update. Cross-year or unsupported templates stop for review instead of guessing.

## Use and verification

Extract one source record from the committed array, then run:

```bash
python -m decision_kernel.runtime.economic_node_study \
  /research/one-reviewed-source-record.json --output /research/new-study-directory
```

The command has no network or market-state API. Its output is one hash-named study file, never `candidate-events.json`. The comparison function returns a separate hash-linked result with no authority.

Tests cover exact reviewed values, monthly versus cumulative/total-postal distinctions, units, all three clocks, source-path restrictions, missing/ambiguous statements, publication mismatch, no invented freshness, no rehashed numeric substitution, append-only revisions, no retrospective system-PIT use, no synthetic/public mixing, and no network access.

## Still required for a continuing economic feed

- A bounded official-page discovery/capture adapter, full retained source bytes and reviewed extraction across naturally occurring template changes.
- Several additional releases per node and revision/expected-release evidence; two periods do not establish a continuous series.
- Comparable prior-year/seasonal context rather than interpreting any month-to-month move as a structural signal.
- A read-only evidence card linked to the market context without merging source authority.
- Any company-economic exposure mapping must cite current company filings; board membership alone is insufficient.

This pilot does not modify market Radar thresholds, historical membership rules, the append-only market event ledger, workflow definitions or Human/Research/Investment authority. No HiThink market call was made for these public-source studies.
