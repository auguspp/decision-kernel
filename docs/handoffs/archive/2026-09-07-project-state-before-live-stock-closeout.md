# Decision Kernel — Current Project State

Status: **MUTABLE CURRENT-STATE INDEX / NOT AUTHORITATIVE OVER FROZEN LINEAGE / NO NEW KERNEL SCHEMA**  
Updated: **2026-09-06 — conversation closeout**  
Repository: `auguspp/decision-kernel`

## Read first

Latest handoff: `docs/handoffs/2026-09-06-stock-output-next-conversation.md`.

Read this index and that handoff, then independently verify current main, open PRs/issues, workflows and exact CI. Do not continue from a chat summary alone. The previous index is preserved byte-for-byte in `docs/handoffs/archive/2026-09-06-project-state-before-stock-output-sync.md` (original Git blob `67a655859afdd64588cd043c73d908cb5cec4097`). It is historical context, not today's operating status. Existing frozen proofs, decisions and the prior stock-source handoff are unchanged.

**User priority: produce a usable stock-first Radar view, not more generic infrastructure.** The desired first screen is 0–3 distinct stocks with reasons, their own price paths, business evidence and explicit gaps. “Worth opening” is not “worth buying.” Reuse mature libraries and existing project modules; do not create a second signal authority or indefinite infrastructure roadmap.

## Verified baseline and unmerged work

| Item | Verified status before this documentation-only sync |
|---|---|
| Main / last code merge | `cfd2b4510a16a953f2bddcbb763e0a27f5fedf79` / PR #258 |
| Main full CI | `34022916206`, success, **1511 passed in 101.62s** |
| Open implementation PR | **#259, DRAFT, NOT MERGED**; `feat/stock-first-radar-reading` |
| #259 exact head | `966ff79e39ba310705922b2cd3fd186df62efb69` |
| #259 latest checked CI | `34027180578`, failure: **2 failed, 1569 passed in 231.34s** |
| Open non-PR Issues | **0**; GitHub's issues endpoint also lists PR #259, which is not a second Issue |
| Separate local stock-output patch | Exists as conversation ZIP; **not applied to main**, not identical to #259 |
| Automatic real-stock output | **NOT RELEASED / NOT PROVEN LIVE** |

The documentation sync commit will be later than the code baseline above; obtain its exact head/merge/main-CI from the sync PR rather than interpreting the baseline as a permanently current ref. Do not merge, reset, close or overwrite #259 during status synchronization.

The two failing #259 assertions are `test_secret_is_only_in_acquisition_step_and_optional_libraries_are_installed` in `tests/test_hithink_dump_trial_workflow.py` and `test_workflow_keeps_fixed_name_and_dump_manual_and_current_source_push_bounded` in `tests/test_theme_source_capture.py`. The log shows a job-boundary secret-count assumption and the old exact workflow option list. This is not evidence of a live secret leak, and it does not authorize deleting security guards to turn CI green. Review actual credential scope and intended triggers before correcting tests.

## Implementation is not the same as live qualification

| Capability | Merged implementation / preserved evidence | Not yet established |
|---|---|---|
| Sector 881/884 | Independent 5/20/60 strength, persistence, acceleration, turnover; current breadth; candidate-time containment; one-day producer and exact state/event persistence | New completed-session append and current sealed-audit/combined-page live publication |
| Sector operations | Input audit/replay and prepublication checks; manual workflow; bootstrap and same-session artifact/cache restoration proven | Schedule, populated prospective corpus, gap-bridging recovery qualification |
| Objective outcomes | PR #230 T+5/T+20 sector/benchmark/excess returns, close-path extrema and rank/state persistence | Real matured prospective outcomes and routine original-state collection |
| Economic/company reading | Reviewed livestock/express inputs, release acceptance and shared input assembly; Muyuan/YTO retained evidence; joint page wired in #238 | Continuous accepted economic facts, complete company coverage, causal benefit or live joint-page proof |
| Theme observation | Bounded probe, source-label discovery and exact-plan execution; real small-sample proofs #240–#244 | Autonomous all-market theme discovery or proof that a label/member is a beneficiary |
| Native RSS | feedparser intake, version retention, real 1000-entry initial baseline and unchanged successor | Qualified natural new NBS versions; unzoned publication strings remain unresolved |
| Feed consumption | #253–#258 batching, exact execution, safe response/time checks, history registration/restore and opt-in manual remote-history wiring | Actual cloud consumer-history continuation and fully autonomous service |
| Human Surface | Existing canonical ticker-first Inbox; read-only Judgment Timeline and CI attachment; exposure-capture supplement | Stock Radar promotion into canonical Inbox; genuine new Human exposure/decision/outcome records |
| Stock-first Radar | **Draft PR #259 plus a separate local patch only** | Chosen/reconciled implementation, passing full CI, qualified live individual-stock inputs and real delivery |

“Core infrastructure broadly ready” means enough exists for bounded acceptance, not that stock screening, continuous operations or investment value has been proven. Stop generic expansion; resolve the stock-output drafts and qualify the smallest useful real run.

## Real data and proof boundaries

Latest independently verified successful Sector run: `33939414197`, implementation `5f8f635d191dd8559844d1b74af0dca0cf4c02df`, ending **2026-09-04**, empty prospective event ledger. This predates the newer sealed input-audit format. Do not fabricate a modern audit for it. The closeout successful-manual-run listing still has this as the latest Sector success.

Frozen RSS baseline `34010252507` and successor `34012474393` are distinct from consumer-history snapshots. The latter preserved the same 1000 versions with no new version; neither proves natural new-source processing. Consumer-history wiring does not fix timezone qualification. The 32 MiB history budget, finite object counts and 90-day artifact retention remain; expiry or capacity exhaustion is not permission to reset or prune history.

The conversation's `radar-readonly-results-2026-09-06.zip` is a saved-September-4-state read-only calculation, **not a new live producer run**. Muyuan, Haid and Longping discussed in chat were manually expanded reading ideas, **not three programmatically qualified stock candidates or new company judgments**. Synthetic stock pages are not real stock selections.

The stock dump remains `DIFFERENCES_REQUIRE_REVIEW / production qualification NOT_ESTABLISHED`. A ten-session dump cannot become 61 stock observations. A page data-ready timestamp is not a per-stock last-trade date. Corporate-action/reference-price gaps cannot be repaired by stale substitution, inferred adjustment, arbitrary tolerance or copying yesterday's close into a missing provider field. See the unchanged `docs/handoffs/2026-09-05-stock-primary-sources-next.md` and its frozen proofs.

#### Rolling state and durable bootstrap

`radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json` is the **sole canonical source** for bootstrap identity, byte lengths/hashes, catalog and lineage. The parser and existing regression test remain authoritative over prose.

```text
latest completed session = 2026-09-04
rolling sessions = 127
series = 321
benchmark = 1
broad = 90
granular = 230
state hash = 2963d7fa62757a56e7296b3d9855a7d6d067d59816738078361f86c51d1f41d7
```

#### HiThink sector-breadth acquisition

Reuse current-member and same-session breadth adapters. Parent hints are current-PIT routing aids, not permanent taxonomy. Keep all planned candidates covered or fail explicitly; no daily 320-member-list fan-out and no silently enriching only the first three. False→true is decided only by previous/current market state; event history is audit/dedup/evaluation, not a second signal state.

The expected direct next session after September 4 is September 7, subject to actual qualified calendar and completed snapshot. If a later run has missed an intervening completed session, obtain a separately qualified recovery state; do not bridge the gap or change clocks to pass. A fresh same-session rerun must preserve event idempotence. Schedule remains disabled until actual operational acceptance.

## Workflows on the code baseline

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

No temporary repair workflow. Sector is manual-only. Native acceptance in `hithink-stock-dump-trial` is manual-only with `isolated` as default and explicit `initialize`/`continue` history modes; execution defaults false. Exact prior run/history hash is required for continuation. The stock-reading workflow option is in **draft #259**, not this code baseline. Existing non-Radar schedules must not be confused with an enabled Sector/RSS schedule. This sync changes no workflow and requests no live acquisition.

## Authority and unchanged company state

```text
External Research Method can propose. Kernel commits. Human decides.
Evidence changes Belief. Price changes Odds.
Research complete != probability established != Odds ready.
Sector/theme/stock Radar = SHADOW OBSERVATION ONLY.
HUMAN ATTENTION AUTHORITY = NONE
RESEARCH AUTHORITY = NONE
INVESTMENT AUTHORITY = NONE
```

Keep the two canonical routes only: unresolved `DEEPEN_REQUIRED` Research attention, and `HumanResearchSurface.attention_eligible` Decision review. No composite opportunity score, automatic Research, Recommendation, Action or third canonical wake. Objective market outcomes and Human review annotations remain separate; profit is not proof of good judgment. No Kernel/Odds/constitution redesign without outcome-backed failure evidence.

| Case | Unchanged recorded stance, not a new assessment |
|---|---|
| CATL | Continue following; cheapness/cardinal probability not established; numerical Odds withheld; no Human decision or Action |
| GigaDevice | Conditional buy framework; not executed |
| Sanhua | Around-CNY30 conditional framework; not executed; later horizon supplement must not rewrite the earlier decision |
| Tinavi | WATCH / NO_ACTION |
| Micron | WAIT / DO NOT BUY FOR NOW; September 30 earnings node is the previously recorded monitoring date, not reverified scheduling here |
| YTO / Muyuan / Haid / Longping | No new investment stance, probability, Odds, Human decision or execution from this work |

Unresolved `DEEPEN_REQUIRED` remains 0 in the retained curated state. The Position/Holding loop remains deferred in `docs/known-deferred-position-holding-loop-2026-09-05.md`.

## Next execution priority

First read #259's exact code and failed CI, then compare the separate local patch described in the handoff. Choose one implementation, port useful tests, and do not blindly apply both. Verify real Sector/company integration and individual-stock data qualification, then pass complete PR CI before merge. Only then perform an explicit bounded real run and inspect actual downloaded output. A short stock list must identify its coverage; zero qualified cards must distinguish missing inputs from no matching conditions. Notification transport must remain separate from semantic authority.
