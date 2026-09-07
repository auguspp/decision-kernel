# Bounded real company coverage expansion — 2026-09-07

Status: implementation/evidence change; **not live stock selection or P0 acceptance**.

## Product purpose and selection boundary

The user authorized adding real company coverage after #270 isolated issuer-local
failures. The last live stock plan contained only Muyuan. Isolating its failure
cannot manufacture other usable stocks. Add three disclosed business baselines
from the previously captured active livestock/pig member sets, without selecting
on their price performance or promising any will pass the stock data checks.

New identities: **300498.SZ 温氏股份, 603477.SH 巨星农牧, 605296.SH 神农集团**.
The existing Muyuan and YTO definitions and source containers are unchanged.
The new v2 manifest has four livestock companies and one express company. It is
still curated coverage, not all 11 pig members, all 36 livestock members or all
A-shares. The earlier membership snapshots are routing evidence only; the next
live attempt must fetch and validate current membership again.

These three were selected for direct disclosed pig operations and distinguishable
business boundaries: pig/chicken operations; pig/feed plus leather; and the
feed/farming/slaughter/food chain. There was no new HiThink request, stock-return
comparison, action-query preselection, or substitution of unreviewed tickers.
The fixed 26-request limit is unchanged. Even if all five companies enter and the
existing six-direction limit is reached, 4 + 6 + 3*5 = **25** requests. With only
the two retained active livestock directions and four companies, the plan ceiling
is **18**. These are upper-bound arithmetic/planning, not successful requests.

## Primary disclosure review and honest retention

All three new records retain limited **2025 annual-report business narratives**,
not 2026 H1 earnings or refreshed current operating facts. Public search results
mentioning newer reports were not substituted for unread primary documents.

| Issuer | Actually inspected primary source | Retained scope |
|---|---|---|
| 温氏股份 | [Issuer-hosted 2025 annual report](https://www.wens.com.cn/uploadfiles/2026/04/20260422104344852.pdf), linked by the issuer IR page; PDF/printed p.6 and pp.10–11 were visually inspected | Exact company/A-share identity; pigs and chickens, product/sales boundaries and company-plus-farmer operating model |
| 巨星农牧 | [Company disclosure in Shanghai Securities News](https://paper.cnstock.com/html/2026-04/23/content_2203880.htm), embedded **2025 annual-report summary**, identity and second-section business/products, production and purchasing passages | Pigs/feed and separate leather business; product/customer distinctions; own/cooperative production and feed supply |
| 神农集团 | [2025 annual-report summary disclosure](https://paper.cnstock.com/html/2026-04/25/content_2206266.htm), identity and second-section business, purchasing and sales passages | Feed/farming/slaughter/food chain; internal/external sales and customer-owned slaughter-service stock; procurement boundaries |

The Juxing page's overall heading mentions 2026 Q1, but the selected passage is
explicitly the embedded 2025 annual-report summary, not Q1 performance. No absent
image/table was treated as a read financial statement. New values are TEXT and
use PRIMARY_STATEMENT / ATTRIBUTED_STATEMENT. Revenue/cost mechanisms remain
hypotheses; current capacity, cash generation, weights, benefit direction,
valuation and Odds remain unestablished.

New records' conservative available_at/retrieved_at are
`2026-09-07T12:44:18.367059+00:00`; mapping prepared_at is
`2026-09-07T12:46:20.919933+00:00`. Publication dates are day-level midnight
representations, not independently verified intraday availability. No acquisition
clock is backdated into the earlier stock run or old September 6 tests.

Original complete PDF/HTTP bytes were not materialized into the repository.
Retention is EXTRACTED_VALUES / PARTIAL with no raw_storage_ref. `content_hash`
binds canonical JSON of source_locator, source_location and the retained fields;
it is **not** a raw-PDF hash or source-authenticity proof. Exact source-file Git
blobs are bound in v2. Its source_commit `4a06ed9c13636f4f8aa59601dc09ab17a287914a`
contains the three new records plus unchanged earlier inputs.

## Production integration, not a stand-alone display

The existing `capture-stock-reading.py capture` CLI explicitly selects
`radar_inputs/economic-company-links-livestock-v2.json`. No new workflow input,
trigger, platform, provider or selector is introduced. `capture()` and
`load_inputs()` take an explicit manifest, keeping their historical v1 library
default for existing retrospective fixtures. Normal live CLI routing is tested
separately; the v2 work is not limited to a synthetic fixture or optional demo.

The recorder copies the selected manifest and **all** five company sources using
the existing bounded source packager, binds `company_manifest` into the capture,
and feeds that exact path to the existing plan builder. Its v5 verifier uses the
captured path and original bytes, not whatever profile is currently newest. An
unknown path, missing v2 file, future mapping, changed evidence or rehashed v2→v1
label cannot silently reduce the plan. Old failed captures require their original
captured implementation and are not rewritten or upgraded.

The shared Sector page packager retains its original v1 default. Only its source
copy helper gains an explicit optional manifest parameter; no Sector producer,
market state, ledger, cache, thresholds or frozen Research records are modified.

## Acceptance to run

No-network tests use actual new company evidence through production
plan/capture/replay, with explicitly synthetic market responses and a synthetic
holiday calendar so the old frozen test state can be used after the real evidence
acquisition. They do not change actual calendar rules or claim real selections.
They must cover the four-company plan / 18-request ceiling, isolation of one
issuer with three surviving test paths, full evidence copying, exact replay,
backdating rejection, missing/changed evidence, capture relabeling, retained old
company definitions and normal live CLI routing.

Full PR CI, exact patch review, merge identity and main CI still require actual
receipts. A subsequent fresh stock workflow must bind a Sector state that passes
its actual current-calendar qualification. On the same qualified Sept 7 window,
`34107253263` is the established candidate input, not an evergreen default. Do not
rerun old workflows or restart Sector just because the company manifest changed.

## Remaining real data constraints

The prior Muyuan `3002/data:null` is not transformed into successful no-events.
The 43.20 turnover discrepancy has no invented precision tolerance. Additional
stocks may also report actions or lack required data; they are isolated under
#270, still count in the denominator, and are never labelled conditions-not-met.
HTTP429/business4001, authentication, shared-state/clock/safety/unknown failures
remain batch-fatal. A green process or CI is not P0 acceptance or complete coverage.

#263 stays independent and untouched. SHADOW OBSERVATION ONLY.
HUMAN ATTENTION / RESEARCH / INVESTMENT AUTHORITY = NONE.
