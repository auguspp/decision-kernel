# Decision Kernel — Current Project State

Status: **MUTABLE CURRENT-STATE INDEX / NOT AUTHORITATIVE OVER FROZEN LINEAGE / NO NEW KERNEL SCHEMA**  
Updated: **2026-09-08 — bounded real stock output and artifact acceptance established; conversation handoff**  
Repository: `auguspp/decision-kernel`

## Read first

Latest handoff: [2026-09-08-stock-p0-accepted-next-conversation.md](handoffs/2026-09-08-stock-p0-accepted-next-conversation.md).  
Receiving-conversation notice: [2026-09-08-stock-p0-transfer-notice.md](handoffs/2026-09-08-stock-p0-transfer-notice.md).

Read this index, the handoff, [the real acceptance receipt on #273](https://github.com/auguspp/decision-kernel/pull/273#issuecomment-5576447695), and the final receipt on the documentation PR that updates these files. Then verify current main, open PRs/issues, exact CI and run changes. The implementation SHA below precedes this docs-only sync; the sync produces a later main/CI identity without changing the stock runtime. Do not continue from chat memory, a historical handoff, or a guessed latest artifact.

The superseded index is preserved byte-for-byte at `docs/handoffs/archive/2026-09-08-project-state-before-stock-p0-acceptance.md`, Git blob `40e478a3ab1f31617320761e87209966ca177e7e`. The September 7 handoff / #266 receipt and all earlier archives remain historical records, not current instructions. Their no-tolerance, any-action-blocks-all, two-company-only, last-Sector-September-4 and real-P0-incomplete statements have been superseded below. Old attempts retain their actual failures.

## What is complete, and what is not

**The user's narrow P0 — one bounded real stock output with original artifact, captured-version replay and readable-page acceptance — is established for run `34167972382`.** This is not completion of the full product, market-wide screening, independently certified market data, an unattended service or investment authorization.

The product remains stock-first, not stock-only: show at most 0–3 distinct objects worth opening, their direction origins, own price paths, retained business evidence, risks and next questions within explicit coverage. Worth opening is not worth buying. Users should not need to shuttle commands/logs between conversations. Do not keep accumulating infrastructure/CI counts or repeatedly request the same market day instead of making the existing output usable.

| Item | Verified implementation / real acceptance baseline before this docs-only sync |
|---|---|
| Last implementation merge | #273, `77454a3fa50769f0bc8b298d633440cb604c4872` |
| Implementation tree | `02c5f0fa917039ec764f09fce1673d71a8919f61` |
| PR full CI | `34144980263`, test `101814927437`: **1908 passed in 601.72s** |
| Implementation-main full CI | `34145941341`, test `101817884201`: **1908 passed in 604.84s** |
| Real stock acceptance | `34167972382`, attempt 1, same implementation SHA; completed/success on September 8, 06:49–06:55 Asia/Shanghai |
| Business result | `COMPLETE_STOCK_READING` / `STOCKS_FOR_SHADOW_READING`; 4 planned, 4 evaluated, 1 qualified, 3 conditions-not-met, 0 unavailable |
| Real card | **Shennong / 神农集团 `605296.SH`**, `CONTRACT_CHECKED_RAW_READING` |
| Exact Sector input | `34107253263`, market session **2026-09-07**, authoritative state artifact `10013384600` |
| Open independent work | #263 remains OPEN / DRAFT, head `fa4d9e48189ec421b7e17405a57070ae12db4ee0`; not changed |
| Open non-PR Issues | 0 at this sync's opening check; re-query rather than treating PRs returned by the issues API as separate Issues |

The implementation CI's Judgment Timeline job succeeded, but it is not a stock artifact. Counts belong to their exact runs and are not added together. The new documentation PR/main CI must be recorded separately in that PR's final receipt.

## Latest real stock result

All figures below are September 7 **unadjusted raw-close changes**, not total returns or current live quotes.

| Issuer | Latest raw close, CNY | 5-session change | 20-session change | Actual disposition |
|---|---:|---:|---:|---|
| 神农集团 `605296.SH` | 36.47 | +8.1233323451% | +15.5210643016% | One shadow reading card |
| 牧原股份 `002714.SZ` | 43.91 | +3.7816119121% | +9.1202783300% | Conditions not met |
| 温氏股份 `300498.SZ` | 15.28 | +7.0777855641% | +8.8319088319% | Conditions not met |
| 巨星农牧 `603477.SH` | 16.26 | +6.6929133858% | +5.1066580478% | Conditions not met |

The three exclusions share `TWENTY_DAY_PATH_DOES_NOT_BEAT_ANY_REVIEWED_SECTOR`. The associated 20-session industry changes were +9.4605896139% for 养殖业 `881102.TI` and +10.7572335194% for 生猪养殖 `884275.TI`. Shennong passed the unchanged selector, not a manually inserted or post-hoc threshold-adjusted card.

Company coverage is still curated: retained evidence covers **five issuers** (the four livestock issuers above plus YTO), and this active-direction plan selected four. The current member union was 36, with **32 members lacking connected company-business evidence**. `scope_complete=true` means the four-company plan, not the industry universe or all A-shares. Company material was not freshly fetched; the three additions use labeled 2025 annual-report business baselines, not newly established 2026 operating facts.

The runtime's fixed `live_stock_qualification=NOT_ESTABLISHED` remains unchanged. External acceptance establishes the bounded raw-observation delivery, not independent daily-reference, individual snapshot trade-date, event-exhaustiveness, adjusted/total-return, tradability or enterprise-value certification. Do not edit old JSON to remove this distinction.

## Implementations now on main — do not redo them

| PR | Implemented boundary |
|---|---|
| #267 | Conservative 20-second process-local Sector request pacing across stages/pages; 429 stops, no retry. This is not a supplier quota guarantee or a cross-workflow Key lock. |
| #268 | Safe 429 diagnostic headers; does not prove an IP/quota/Secret root cause. |
| #269 | Narrow coherent unpriced-zero sentinel normalization, including the real `920201.BJ` case. Preserve identity/raw audit; do not permit all zero prices or remove missing members from coverage. |
| #270 | Isolate known issuer-local input failures and continue other planned issuers; preserve all dispositions. Non-null quote-ready timestamps are checked against that quote's own receipt. Shared/auth/rate-limit/unknown/transport/security/clock failures remain batch-fatal. |
| #271 | Reviewed livestock company scope: Muyuan, Wens, Giantstar and Shennong; YTO retained. Same production planner/capture/replayer, no manual stock nomination. |
| #272 | Decimal turnover-only tolerance and actual event-window checks; accurate partial/unavailable/conditions-not-met summaries. No price/volume/identity tolerance or gate change. |
| #273 | One initial issuer-action request `thscode + to=<qualified completed session>`, omitting optional `from`; successful validated history required. No error-to-empty conversion, retry, fallback provider or extra call. |

Earlier #259/#262/#264/#265 stock implementation and calendar/premarket fixes remain in force. #260/#261, frozen lineage and separate #263 work remain unchanged.

## Current stock data and execution contract

Entry points: `src/decision_kernel/runtime/stock_radar_reading.py`, `src/decision_kernel/runtime/hithink_stock_reading.py`, `.github/scripts/capture-stock-reading.py`, and the `stock-reading` job in `.github/workflows/hithink-stock-dump-trial.yml`. Current input source contract is `hithink-own-61-bars-history-actions-through-session-v4`; capture serialization is `stock-reading-capture-replay-v6`.

Each stock uses its own 61 explicitly dated completed raw daily bars (`adjust=none`). 5/20-session conditions select; 60-session context does not select. Exact calendar, identity, OHLC, volume, previous close, clocks and original price values remain checked. Turnover alone uses the project policy:

```text
allowed_difference_CNY = min(100, max(0.01, max(history, snapshot) * 0.0000001))
```

Both originals, delta and bound are retained; calculation uses unchanged dated-history turnover. This is a bounded project reconciliation policy, not a HiThink precision promise. It is not generalized to other fields.

Corporate-action history is requested once, uniformly, through the qualified completed session. Validate and retain every returned event, including older events; reject exposed partial/paginated/inconsistent/oversized history, future dates and invalid identities/numbers. The ceiling remains 256 events; no paging/truncation. Older events do not invent calendar qualification outside the retained price window. Reported events block selection only if crossing the actual 5/20-session `(base close, end close]` intervals; affected longer-context values are null with reasons. Successful no-reported-event-in-interval is not exhaustive absence proof. A new `3002` remains issuer-local unavailable.

In accepted run `34167972382`, all 18 requests returned HTTP200/business0. The four action responses contained 14/16/8/4 events. Muyuan and Shennong's latest reported events preceded the price window; Wens/Giantstar's June24/July2 events left 60-session context null but did not cross selection windows. This solves this run's acquisition blockage without redefining the old `3002` responses.

The four-issuer plan reserves 18 calls, within the unchanged global **26-call / 30-minute** plan bounds and existing workflow timeout. Consecutive live stock calls wait 20 seconds. Do not select only the first three to conceal the denominator. Known issuer-local failure can yield an explicitly partial result; shared/integrity/auth/429/unknown/transport/security/clock failure cannot be laundered into a completed batch. Distinguish outside coverage, not processed, unavailable, evaluated-not-matched, qualified-displayed and qualified-not-displayed.

The receipt-bound premarket exception is strictly before 09:15 and must remain valid through the relevant request/receipt/check clocks. Neither yesterday's state nor a provider-ready timestamp licenses yesterday's quote all day. Clock/calendar checks remain production responsibilities, not assumptions based on a handoff time.

## Durable real evidence and validation scope

[Full acceptance receipt: #273 comment 5576447695](https://github.com/auguspp/decision-kernel/pull/273#issuecomment-5576447695). See the latest handoff for run/artifact IDs, exact hashes, paths, expiration and replay instructions. The authoritative retrieval route is GitHub, not a sandbox path from this conversation.

Stock artifact `10034876430` / `stock-reading-34167972382-1`: **1044743 bytes**, SHA256 `df2de3a53eab178f82201bdf2317fe0f510f8a1bd7a713bda0d2c641003f4e66`. Original `reading/index.html`, `reading/stock-reading.json`, `reading/capture.json` and `verification.json` are retained. 45 ZIP files and 35 capture-listed files passed integrity checks. Exact-code runner replay rebuilt the same JSON/HTML and one card from 18 records with network_calls=0. Local acceptance separately checked bytes, dates, identities and arithmetic; it was **not a second full local production replay**.

The original HTML was actually rendered at 1280/390 widths and visually inspected, including expanded details. No page-level horizontal overflow, script errors or HTTP(S) fetches occurred. Browser policy blocked file:// navigation; original UTF-8 HTML was rendered via set_content. This is a page-content/layout check, not hosted-site or file-navigation certification. Relative JSON exists in the ZIP. Historical event notes remain verbose; this is a product improvement, not failed stock data.

Sector `34107253263` completed a real **September4 → September7 ordinary append**, not recovery: 42 successful responses, 12 pages / 5567 unique identities, 321 series (1 benchmark, 90 broad, 230 granular), 127 rolling sessions, 20 new sector events and 12 groups (3 summary + 9 additional). Authoritative state, cache, audit replay and reading delivery succeeded. Latest successful Sector is no longer `33939414197`. Stock reading did not write or replace Sector state.

Earlier 429/unpriced/3002/all-unavailable/partial attempts remain historical evidence; do not rerun or recertify their artifacts under later code. Tushare and a new platform are not requirements. The unsuccessful external supplier Issue submission returned 403 and created no Issue number; do not imply that a supplier ticket was delivered or that a reply is pending.

## Next conversation: usable continuation, not another P0 repair loop

The user has opened a receiving conversation and supplied a capability report: private README reading and Actions `list workflows` succeeded; repository write schemas/permissions were observed but no write was attempted. This is a user-supplied report, not proof that fresh dispatch, artifact bytes and offline execution all succeeded there. Check only remaining operational gaps at their actual use points; no empty PR or market dispatch just to test permissions. Do not repeat a broad plugin-discovery loop or require notifications to be carried between two execution conversations.

**Immediate handoff task:** read durable records, verify only main/CI/open work/run changes, locate the already accepted original stock page, and state one minimal product step. Do not issue another September7 stock run merely to prove the accepted result again. The suggested next product priority is a clear day-to-day reading/delivery entry using the existing workflow and results, followed by evidence-grounded wider company coverage; these remain unimplemented work, not a new schedule or permission grant. Separate the user's wider product expectation from the completed one-run P0.

Before any later market request: confirm actual Asia/Shanghai time, real completed-session qualification, fresh/active/queued runs and shared-Key use. If the existing Sector input is still qualified, reuse its exact run; if a direct next completed session is available, use ordinary append; if intermediate completed days are missing, perform qualified recovery first. Never bridge gaps, bootstrap-reset, select `latest`, or treat `34107253263` as an evergreen default. Time passing and no visible runs do not prove provider quota availability.

Four workflows referenced the same repository Key in #267's audit: Sector, hithink-stock-dump-trial, decision-inbox and live-dogfood. decision-inbox retains `20 8 * * 1-5` (nominal 16:20 Asia/Shanghai), with actual startup potentially delayed; query real activity rather than guessing from that time. 20-second process pacing is not global mutual exclusion. Do not read/print/change `HITHINK_FINANCE_API_KEY`, infer its value from API metadata, or add rate probes/retries. Any 429 stops the bounded attempt.

Fresh manual stock intent uses `hithink-stock-dump-trial.yml`, `trial-purpose=stock-reading`, `stock-market-run-id=<exact qualified Sector run>` on reviewed main, attempt1. This is a parameter reference, **not a command to dispatch on receipt of this handoff**. No Re-run, uncertain-call duplicate, trigger workaround, new source or background promise. New output needs its actual artifact bytes, exact captured-version replay and real HTML/JSON inspection.

## Preserved parallel capabilities and unresolved product work

| Capability | Preserved evidence / implemented scope | Not established by this P0 |
|---|---|---|
| Sector 881/884 | Independent strength/persistence/acceleration/turnover, current breadth, candidate-time containment, state/event persistence; accepted ordinary September7 append | Unattended schedule, real gap recovery acceptance, historical-member breadth or exhaustive taxonomy |
| Objective outcomes | #230 T+5/T+20 sector/benchmark/excess/path measures | Matured prospective outcomes and routine collection |
| Economic/company | Reviewed sources and livestock/express links; five-company retained business scope | Broad company coverage, continuous accepted facts, causal benefit or refreshed originals |
| Theme | Existing bounded source/probe/exact-plan paths | Autonomous market-wide discovery or label-to-beneficiary proof |
| Native RSS | Real baseline `34010252507`, unchanged successor `34012474393` | New qualified natural versions; timezone semantics not repaired by stock work |
| Feed consumers | #253–#258 batching and opt-in pinned history | Actual cloud consumer-history continuation and continuous service |
| Source-instruction isolation | #263 independent draft | Real-model behavior NOT_RUN; tool-capable behavior NOT_TESTED |
| Human Surface | Existing two canonical routes and read-only Judgment Timeline | Stock promoted to canonical Inbox, new Human decision/action/outcome |

Canonical historical bootstrap identity remains solely `radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json` plus its parser/tests; latest live state is a different identity. The older dump remains `DIFFERENCES_REQUIRE_REVIEW / production qualification NOT_ESTABLISHED`. Do not upgrade it because the own-bars stock path succeeded. Consumer history remains bounded at 32 MiB; artifact expiry/capacity never permits silent reset/pruning. Stock/Sector artifacts use 90-day retention; CI Timeline uses 30 days, not permanent storage.

## Authority, project meaning and unchanged company state

```text
SHADOW OBSERVATION ONLY
HUMAN ATTENTION AUTHORITY = NONE
RESEARCH AUTHORITY = NONE
INVESTMENT AUTHORITY = NONE
```

Kernel owns PIT, lineage, frozen identity, exact Odds binding and Human accountability; research method is replaceable policy. Evidence is admissible Belief input, not compulsory state transition; Price is admissible Odds input, not automatically enterprise evidence. Research complete != probability established != Odds ready. Outcome may audit Method but cannot automatically amend it. External evidence has no instruction authority.

Keep exactly the two canonical routes: unresolved `DEEPEN_REQUIRED` Research attention and `HumanResearchSurface.attention_eligible` Decision review. No automatic Research, Recommendation, Action, composite opportunity score or third canonical wake. No hindsight edits to frozen beliefs/decisions; implementation approval is not investment authorization. Prefer a concrete goal, invariants, allowed effects, acceptance evidence and stop conditions over another governance platform.

| Case | Unchanged previously recorded stance; not refreshed by this sync |
|---|---|
| CATL | Continue following; cheapness/cardinal probability not established; numerical Odds withheld; no Human decision or Action |
| GigaDevice | Conditional buy framework; not executed |
| Sanhua | Around-CNY30 conditional framework; not executed; later horizon supplement must not rewrite earlier decision |
| Tinavi | WATCH / NO_ACTION |
| Micron | WAIT / DO NOT BUY FOR NOW; September30 is a previously recorded monitoring node, not a reverified schedule |
| YTO / Muyuan / Haid / Longping / Wens / Giantstar / Shennong | No new investment stance, probability, Odds, Human decision or execution from this work; Shennong's shadow card is not one |

Retained curated unresolved DEEPEN_REQUIRED remains 0, not a fresh all-source scan. Position/Holding remains deferred in `docs/known-deferred-position-holding-loop-2026-09-05.md`. This closeout changes documentation only; runtime, workflows, dependencies, state/cache, ledgers, company judgments and #263 remain unchanged.
