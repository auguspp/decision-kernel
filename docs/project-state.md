# Decision Kernel — Current Project State

Status: **MUTABLE CURRENT-STATE INDEX / NOT AUTHORITATIVE OVER FROZEN LINEAGE / NO NEW KERNEL SCHEMA**  
Updated: **2026-09-07 — conversation closeout; stock implementation merged, real acceptance incomplete**  
Repository: `auguspp/decision-kernel`

## Read first

Latest handoff: [2026-09-07-stock-p0-next-conversation.md](handoffs/2026-09-07-stock-p0-next-conversation.md).

Read this index and that handoff, then independently verify current main, open PRs/issues, workflows, exact CI and live-run evidence. The implementation baseline below is **before this documentation-only sync**; obtain the sync PR, merge SHA and its CI from GitHub. Do not treat an old handoff or chat as current repository truth.

The superseded index is preserved byte-for-byte at `docs/handoffs/archive/2026-09-07-project-state-before-live-stock-closeout.md` (original Git blob `919fd3d32285f118b7a449bfc1c3e703ebfee513`). The earlier 2026-09-06 handoff and archive remain unchanged historical records. In particular, their “#259 draft” and separate-patch reconciliation tasks are no longer current instructions.

**Product priority: finish a bounded real stock-first Radar reading, not another infrastructure expansion.** The first screen should expose 0–3 distinct stocks, their direction origins, own price paths, business evidence, risks and next questions within declared qualified coverage. “Worth opening” is not “worth buying.” Stock-first is not stock-only: observers need not invent a ticker to be useful.

## Verified implementation baseline and parallel work

| Item | Verified state before this documentation-only sync |
|---|---|
| Main / last implementation merge | `3529f4651e884abfd1dc48cc881d0dc360e5335f` / PR #265 |
| Main full CI | `34073063774`, success; test `101593895184`: **1708 passed in 406.80s** |
| #265 reviewed head / PR CI | `2e0eeeef383ba15b0eda393dbda6128fa9f73713`; `34072673845` / test `101592788995`: **1708 passed in 265.26s** |
| Stock implementation | **#259 MERGED**, followed by #262, #264 and #265; one selector, existing HiThink source |
| Open implementation PR | **#263 DRAFT / NOT MERGED**; `test/disclosure-source-instruction-isolation` |
| #263 exact head / its own CI | `fa4d9e48189ec421b7e17405a57070ae12db4ee0`; `34045118986`: **1699 passed** against its recorded base, not current main acceptance |
| Open non-PR Issues | **0**; #263 appears in the issues API because GitHub includes PRs there |
| Qualified real stock output | **NOT ESTABLISHED**; no successful real stock selection or qualified zero-match result |
| Latest real stock attempt | `34070171908`: incomplete input qualification; individual-stock requests not reached |
| Latest prerequisite attempts | Sector `34073613843` and `34073665086`: HTTP 429, no new authoritative state bundle |

The main CI also published its existing Judgment Timeline attachment. That is **not** a stock-reading artifact or stock acceptance. Test counts belong to exact commits/runs; do not add counts from different implementations.

## What changed during this conversation

| Merge | Result and boundary |
|---|---|
| #259 — `81ce648e140acdd35cc8249d796aecd842edde5b` | Reconciled remote A and local B into one stock reader. Normal capture uses HiThink own 61 completed raw bars, explicit current quote and reported corporate actions. Tushare is not a prerequisite; its unconnected checker/tests were removed from the release tree, with history retained. |
| #262 — `c73f4dcc929a8cd3181bdb48875f584d9fcd5966` | Missing/invalid `stock-market-run-id` now has explicit diagnostics; unstarted acquisition is not followed by misleading rebuild/upload errors. |
| #264 — `71807a85ca658af74ed6c2e3c7d0010b7ae53ef5` | Stock manual attempts reach the real calendar instead of being rejected by Theme's weekday heuristic. The actual calendar must confirm the exact latest completed saved session. |
| #265 — `3529f4651e884abfd1dc48cc881d0dc360e5335f` | Stock-only, receipt-bound premarket index carry strictly before 09:15, with expiry during reading; shared Sector/Theme index policy is unchanged. Five added regressions are synthetic, not a post-fix real stock run. |

#260 documentation, #261 independent voice-pass work, frozen Research/Decision/Action records and prior source proofs remain intact. #263 was not merged or modified by the stock fixes.

## Current stock-reading contract

Entry points are `src/decision_kernel/runtime/stock_radar_reading.py`, `src/decision_kernel/runtime/hithink_stock_reading.py`, `.github/scripts/capture-stock-reading.py` and the `stock-reading` job in `.github/workflows/hithink-stock-dump-trial.yml`. Current reader identity is `stock-first-reviewed-scope-raw-path-v4`.

The frozen plan comes from active linked directions, retained company evidence and current membership, not user-nominated tickers. Company evidence currently covers **Muyuan and YTO**; the failed real plan contained **Muyuan only**, not two guaranteed candidates or a market-wide top three. Preserve coverage-outside, planned-but-incomplete, conditions-not-met and display-omitted distinctions.

Own 5/20/60-session changes use **61 individually dated completed stock sessions**, not industry returns or a ten-day dump. Explicit `adjust=none`; exact current quote/previous-close and activity checks; reported corporate actions in the window block the incomplete attempt. These are raw-close ratios, not adjusted or total returns. No reported action is not an exhaustive absence proof; historical daily independent reference qualification remains unestablished. No filled prices, invented `prev_price`, inferred adjustment or empirical tolerance.

The existing selector/gates, 881/884 separation and node-order presentation are unchanged. Full plan request ceiling remains **26**, lifetime **30 minutes**; no preselecting three companies to hide incomplete coverage. Credentials, real request/receipt clocks, state/identity hashes, safe retention and credential-free replay remain required. A failed attempt cannot publish partial stock cards as a completed selection.

#265 does **not** make yesterday's snapshot valid throughout today's trading hours. Its exception applies only when the real calendar still identifies the saved completed session and provider-ready, exact receipt and qualification are on the same later trading date, all strictly before 09:15. Read the exact implementation before changing this policy. Human handoff checks of retained benchmark OHLC/volume and all-index turnover are not proof that every such comparison exists as a production assertion.

## Real attempts and durable evidence

| Run | Actual result | Artifact |
|---|---|---|
| `34043329828` | `stock-market-run-id` empty; initialization stopped; no market request | No artifact; fixed subsequently by #262 |
| `34070171908` | `DATA_QUALIFICATION_FAILED / INPUT_CLOCK_IDENTITY_OR_SCHEMA_REJECTED`; replay `RETAINED_INCOMPLETE_ATTEMPT_NOT_STOCK_SELECTION` | `stock-reading-34070171908-1`, ID `10000211354` |
| `34073613843` | Sector producer catalog request HTTP 429 at 2026-09-07 09:37 +08:00 | Failure audit `sector-radar-run-34073613843`, ID `10001289545` |
| `34073665086` | Sector producer calendar request HTTP 429 at 2026-09-07 09:38 +08:00 | Failure audit `sector-radar-run-34073665086`, ID `10001306616` |

Artifact digests, exact clocks and retrieval instructions are in the latest handoff. Both Sector failures skipped authoritative state and cache publication. They did not initiate another stock workflow. **No selected stock and no zero-match conclusion exist from these attempts.** Old failed runs must not be relabelled as successes after code changes.

429 is observed transport rejection, not proof of an invalid secret, a particular quota window or the absence of a client-side pacing issue. Short-interval fresh dispatches are still retries against the provider; new run identity is not rate-limit relief. Do not launch repeated trials to diagnose it. This closeout performs no market/RSS/company/model request and installs no reminder or schedule.

## Next bounded execution

Use a new conversation with **both repository code/PR capability and Actions dispatch/log/artifact capability** actually available. Existing GitHub plus GitHub Actions MCP were complementary in this conversation; do not assume either alone has every operation. Discover actual tools before promising execution. HiThink remains in repository secret `HITHINK_FINANCE_API_KEY`; no token belongs in chat or documentation.

At the last live attempts it was the **morning of 2026-09-07**, not a post-close test. Re-check current Asia/Shanghai time, the actual calendar, pending runs and provider availability when resuming. The earlier 15:10 suggestion was a possible observation time, not a job already scheduled or a guarantee data would be ready.

After a genuinely completed trading session, first obtain a successful, qualified Sector state via **one** fresh `sector-radar-shadow.yml` dispatch on main (no inputs). For a direct next-session append use the ordinary producer; if intervening completed sessions are missing, qualify recovery first. Do not bootstrap-reset or bridge missing sessions. Only after the full producer and authoritative upload succeed, pass that exact run ID to a new `hithink-stock-dump-trial.yml` dispatch with `trial-purpose=stock-reading` and `stock-market-run-id=<qualified Sector run>`. Not `native-market-run-id`, not the stock run's own ID, not Re-run jobs.

An already successful Sector run may be reused when its exact state still passes current calendar/time qualification; a new run number by itself is not new market data. `33939414197` is a historical input reference, **not an evergreen default**. On any 429, stop that bounded acceptance and report the stage; no automatic loop or source substitution. Download the actual stock artifact, check its identity/digest, replay with the captured code version and inspect both HTML and JSON before reporting 0–3 cards or the precise failure/coverage state.

## Preserved capabilities and still separate proofs

| Capability | Existing implementation / retained evidence | Still not established by this conversation |
|---|---|---|
| Sector 881/884 | Independent strength, persistence, acceleration, turnover, current breadth, candidate-time containment and daily state/event persistence | Successful ordinary next-session append and new sealed-audit/combined-page live delivery |
| Sector operations | Manual producer, audit/replay and prepublication gates; historical bootstrap/same-session restore | New fresh-dispatch same-session idempotence under current code; qualified recovery for any actual gap; unattended schedule |
| Objective outcomes | #230 T+5/T+20 sector/benchmark/excess and path/rank/state measures | Matured prospective real outcomes and routine original-state collection |
| Economic/company | Reviewed livestock/express inputs, release assembly, retained company evidence and joint reading | Continuous accepted facts, broad company coverage, causal benefit and refreshed company originals |
| Theme | Bounded probe, source-label discovery, exact-plan execution and earlier small live samples | Autonomous market-wide discovery or member/label-to-beneficiary proof |
| Native RSS | Real 1000-version baseline `34010252507`, unchanged successor `34012474393` | Qualified natural new versions; timezone qualification is not fixed by history plumbing |
| Feed consumers | #253–#258 batching, exact execution and opt-in history registration/restore | Actual consumer-history cloud continuation and continuous service |
| Source instruction isolation | #263 draft, paired input preparation and deterministic boundary tests | Real-model behavior `NOT_RUN`; tool-capable behavior `NOT_TESTED` |
| Human Surface | Existing two canonical routes and read-only Judgment Timeline | Stock page promoted into canonical Inbox; new genuine Human decision/execution/outcome records |

Latest verified successful Sector run remains `33939414197`, code `5f8f635d191dd8559844d1b74af0dca0cf4c02df`, market session **2026-09-04**, empty prospective ledger. It predates the newer sealed audit; do not manufacture one for it. Canonical bootstrap identity and bytes remain in `radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json` (127 sessions, 321 series); the manifest/parser outrank prose.

The old dump remains `DIFFERENCES_REQUIRE_REVIEW / production qualification NOT_ESTABLISHED`; old saved-state calculations and synthetic pages are not live selections. See the unchanged `docs/handoffs/2026-09-05-stock-primary-sources-next.md`. Consumer history remains bounded at 32 MiB with finite objects; artifacts use 90-day retention, not permanent storage. Expiry/capacity never authorizes silent reset or pruning.

## Workflows on the implementation baseline

```text
apply-disclosure-assessment.yml
ci.yml
decision-inbox.yml
economic-release-discovery.yml
economic-source-capture.yml
hithink-stock-dump-trial.yml
live-dogfood.yml
sector-radar-shadow.yml
stock-field-source-study.yml
```

Sector and stock-reading remain manual. The shared trial workflow's existing theme-source push trigger does not make stock-reading automatic. Native acceptance defaults remain `isolated`, execute=false, with explicit initialize/continue and exact prior history binding. This sync changes no workflow, dependency, runtime, state, ledger, threshold or company judgment.

## Authority, project meaning and unchanged company state

```text
SHADOW OBSERVATION ONLY
HUMAN ATTENTION AUTHORITY = NONE
RESEARCH AUTHORITY = NONE
INVESTMENT AUTHORITY = NONE
```

Kernel owns PIT, lineage, frozen identity, exact Odds binding and Human accountability; research method is replaceable policy. Evidence is admissible input to Belief revision, not a compulsory state transition. Observed price is admissible input to Odds; market observations cannot silently become enterprise fundamental evidence. Research complete != probability established != Odds ready. Outcome may audit Method but cannot automatically amend it. External evidence has no instruction authority.

Keep the two canonical routes only: unresolved `DEEPEN_REQUIRED` Research attention and `HumanResearchSurface.attention_eligible` Decision review. No automatic Research, Recommendation, Action, composite opportunity score or third canonical wake. Do not rewrite frozen beliefs/decisions or infer investment authorization from implementation approval. Prefer outcome-first tasks with explicit invariants, side effects, acceptance evidence and stop conditions, not a new governance platform.

| Case | Unchanged previously recorded stance; not refreshed here |
|---|---|
| CATL | Continue following; cheapness/cardinal probability not established; numerical Odds withheld; no Human decision or Action |
| GigaDevice | Conditional buy framework; not executed |
| Sanhua | Around-CNY30 conditional framework; not executed; later horizon supplement must not rewrite the earlier decision |
| Tinavi | WATCH / NO_ACTION |
| Micron | WAIT / DO NOT BUY FOR NOW; September 30 is a previously recorded monitoring node, not a reverified schedule |
| YTO / Muyuan / Haid / Longping | No new investment stance, probability, Odds, Human decision or execution from this work |

Retained curated unresolved `DEEPEN_REQUIRED` remains 0, not a fresh all-source scan. The Position/Holding loop stays deferred in `docs/known-deferred-position-holding-loop-2026-09-05.md`.
