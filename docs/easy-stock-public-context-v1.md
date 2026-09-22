# EasyStock public market / positioning context — P1-4

Authority: #297/5773421011 (EasyStock requirement), 5773922748 and 5774606781 (preceding checks), 5774970966 (this implementation restart); Main Construction 5771409745; RM-20260922-r2/5771323230. Human explicitly asked to continue P1 with this reuse check before continuing Industry and before #504.

Kernel start: `5027b3e122ff070b9ddabd069421995fa714c3bf`; pinned reading `5fe960af772b94c1654691188fb816a6b245b9c8`. EasyStock current main was re-resolved to `0470c34b2d77a18c8389c6e9e0bcf324611c2b3a`, not assumed from the reference notice. This is an implementation audit of relevant source paths and prior full-tree review, not a claim every upstream line was independently audited or its data economically verified.

## Exact inspected upstream / attribution

All paths below are at that exact EasyStock commit:

| Path | Git blob / inspected use |
|---|---|
| backend/internal/providers/eastmoney/market_overview.go | 1be6a4b11d9532e04f066e9de301af9552f654ba; full implementation, industry/fund-flow/report requests, field mapping, numeric/time helpers and fallback |
| backend/internal/providers/futuresposition/client.go | ce6626d77b80489a37fee4444df8abf7ddf91e9d; full implementation, exact-date exchange CSV, top20 completeness, signed changes and fallback behavior |
| backend/internal/providers/marketoverview/provider.go | f5f3eaa564799478d69494a4df365bec17b860f9; full composition, Tencent industry / Sina flow providers and Eastmoney fallbacks |
| backend/internal/foundation/types.go | 0cc980f2dbaf9d3411dc5780eb3af660afe527f1; SourceMeta and relevant quote/board/financial primitives, lines1–200 |
| backend/internal/foundation/market_overview.go | 3c77709e0c50c13f36c301b26826df48f83c9e09; full market, flow and report response types |
| backend/internal/providers/tencent/industry.go | 20751a40caf0bfb70f809caaa910773d6a05ca8d; full rank request and explicit1/5/20 fields; score excluded |
| backend/internal/providers/tencent/client.go | 1aabe677449942f1aa6d12f19aadd1a2ee11b3e6; fixed origins/options, lines1–100 |
| backend/internal/providers/eastmoney/client.go | 3deb6d44d24234f1256cb4ed8419c00643ca9915; fixed origins/options, lines1–165 |
| LICENSE | 7c72335fe468d763f7c805a211e7a68147054e53; full license and Required Notice |

`easy_stock_context.py` is a Python adaptation of the specific endpoint/field/CSV logic above. It is not relicensed MIT. Its header carries the source commit, modified behavior and this license notice. The thin capture/reader compose existing Kernel owners rather than importing EasyStock's application, database or scheduler.

PolyForm Noncommercial 1.0.0: https://polyformproject.org/licenses/noncommercial/1.0.0

Required Notice: Copyright (c) 2026 jundizhou. Commercial use of easy-stock requires prior written permission from the copyright holder.

Data sources and other third-party dependencies retain their own terms. No commercial-use permission or upstream data redistribution entitlement is inferred from this audit.

## Reuse decision

**THIN_ADAPTER** for Tencent/Eastmoney request contracts, CFFEX CSV arithmetic, explicit field availability and provenance ideas. Internal reuse: existing requests Session (no netrc/env proxy), bounded HTTP response checks, canonical Decimal/hash, original Industry workflow identity/trigger, GitHub artifact/ZIP validators, Collector budgets/retention and normal publisher. Official source: the exchange dated CSV path and public Tencent/Eastmoney endpoints as identified by the exact implementation; a successful current live body/field check remains a separate acceptance event, not inferred from code or synthetic tests.

**REJECT_SEMANTIC_MISMATCH** for fusion scores/fixed weights, upstream numeric missing-to-zero behavior, default past-date searches and cached carry-forward as current observations, four-variety lot totals as risk exposure, automatic buy/sell/add/reduce, Hermes/Electron, another canonical DB, scheduler or provider framework. No NEW_BUILD_JUSTIFIED commodity framework is needed. Existing #510 LC/CU/RB calculations, broader HiThink snapshot and their historical custody remain unchanged.

## Finite acquisition / source isolation

One additional `public-context` job in the original `radar-industry-breadth.yml`, using its existing first-attempt main trigger and exact independent main-CI guard. No cron, push launcher, duplicate scheduled task or new workflow. The job has no source credentials; the GitHub token is scoped only to the preceding CI check, not public acquisition. It has its own `easy-stock-context-<run>-1` artifact, separate from the original HiThink job.

Eight fixed GETs at most: Tencent industry rank150; Eastmoney industry/theme/stock first page200 each; exact-date IF/IH/IC/IM CSV. No source text controls URLs, arguments or execution. No per-stock/per-contract request fan-out, paging, automatic retry, date fallback or alternate host. HTTP429 stops the remaining requests for that same provider; unrelated providers retain their own outcomes. Per-response4MiB, finite180-second start budget, five-minute job. Requests streams with no redirects or inherited credentials. The CFFEX upstream path uses plain HTTP: the receipt explicitly marks transport unauthenticated; no secrets are sent and byte hashing does not authenticate exchange truth.

Target date is the capture's actual Asia/Shanghai calendar date, not a guessed last trading day. Weekend/pre-publication gaps remain gaps. No A-share calendar is borrowed as a futures publication calendar. Source/network failures, safety/decoding body rejection, retained bodies failing a semantic contract and genuine empty JSON windows are different states. Raw error text is not copied into status logs. Current retrieval cannot establish historical first-available PIT.

## Field and temporal meaning

Tencent's `bd_zdf/bd_zdf5/bd_zdf20` remain its declared1/5/20 percentage-point fields, not recalculated or independently live-verified. Its provider lacks the requested breadth/flow fields; absence stays absent. Eastmoney `f3/f109`, turnover `f8`, rising/falling `f104/f105`, leaders `f128/f136`, and three flow dimensions retain their source taxonomy and raw fields. **f24 is quarantined and never mapped to20-day change** while horizon interpretation is unresolved. All missing/non-numeric values become explicit unavailable fields, not zero. An actual zero remains zero. ST-name rows are retained rather than silently pruned. Up/down counts alone do not establish unchanged members, historical membership or full-market breadth.

Tencent and Eastmoney classifications do not merge with each other or the existing THS881/884 Sector universe. Both snapshots are provider-ranked first-page windows, not complete/unbiased stock universes. CNY-flow and percentage-point mappings are attributable upstream interpretations, not company Evidence. All outputs are CONTEXT_ONLY / MARKET_EXPRESSION; no market strength is promoted to company economics or eligibility for Research.

SourceMeta records available parsed fields, source/URL, received clock and raw digest. `trade_date` is populated only from validated dated CSV rows; non-dated market snapshot trade dates stay null. `stale`, `snapshot_id` and `next_refresh_at` stay unknown when not supplied. `carry_forward=false` means this adapter never substituted a prior body; it is not a guarantee that an upstream endpoint is uncached. A recent HTTP response is not proof of fresh source content. No fallback was executed, so no invented fallback_reason.

## CFFEX positioning

Each returned IF/IH/IC/IM contract must have all ranks1–20 exactly once and valid signed integer changes; dates and varieties may not be mixed. Preserve separate long-side and short-side member names, original cells and encoding (UTF8/GB18030). Sum only within the same variety over actually disclosed complete contracts. The exchange's full contract catalogue is not independently acquired: do not claim every listed contract was returned.

`net_long = long - short`; `net_short = short - long`; changes use the same signed convention. Published current-ranked-member changes are not a fixed-cohort time-series change. Four different index-future lots are not added into one exposure or directional score.

Only whitespace normalization is allowed for exact `中信期货(代客)`. No fuzzy match to other 中信 entities or brokerage proprietary positions. A missing ranked side stays UNKNOWN; aggregate CITIC net change is unavailable unless both sides are present in every returned contract. Not being in the top20 does not imply a zero position/change. These values are POSITIONING_CONTEXT, not company Evidence, market truth, forecasts or trade instructions.

## Reading and acceptance

The original publisher independently checks the newest native Industry run and its exact first-attempt `public-context` job, required guard/capture/upload steps, archive identity and original-byte replay. It does not read older success after latest failure, execute artifact code, or call public sources. A successful public job may remain readable while the sibling HiThink job fails; the whole-workflow failure is explicitly retained, not rewritten to success. A selected historical workflow with no public job is visibly NOT_PRESENT, not no activity.

Normal same-R Markdown links to full structured fields, raw-archive references and job proof. Existing Stock/Research/Watch/lane outcomes and navigation remain unchanged. The display's first10 rows are a reading cap, not a source truncation or attention quota. No score, company beneficiary, Research question, Pre/Quick, Odds, notification or investment authority is produced.

Full exact-head CI, unchanged5443 baseline test identities, expected-head merge, independent main CI and normal publication/readback are separate gates. Local parser checks use a partial retained older source checkout, not full current main. First real source-body verification, units/horizons/PIT review and economic Question/original Funnel adoption remain explicit product acceptance gaps until real evidence exists. Code or synthetic pass counts do not complete P1-4 or all P1.

## Later reuse retained, not implemented here

Before #504, re-resolve upstream current main and validate the then-current `/report/list` contract. Already inspected `MarketReports`: qType0/1, orgSName/researcher, rating/previous rating/ratingChange, indvAimPriceL/T, predictThisYearEps/Pe, publishDate, industry and security fields. Preserve exact report identity and prediction-year meaning; a current endpoint's forecast may be revised and must not be backdated. Ratings/targets/forecasts are Data/Expectation Context, not Evidence. Do not explore this API from scratch.

#508/#509 retain the prior full-tree audit inputs for author-level dedup/one author one vote, support/opposition/consensus, triggers/invalidations/checklists, A-share baseline to US transmission and opening verification, turning-point taxonomy and next-bar/backtest execution constraints. None of those scores, models, backtests or runtime frameworks is activated by this P1-4 change.
