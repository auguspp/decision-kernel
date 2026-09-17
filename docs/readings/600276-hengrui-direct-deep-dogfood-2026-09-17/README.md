# 恒瑞医药 fresh Human-origin Direct Deep dogfood — 2026-09-17

Status: **RETAINED FRESH DOGFOOD / RESEARCH-ONLY / MARKET NOT REQUESTED / ODDS NOT COMPUTED / HUMAN ACCEPTANCE NOT ESTABLISHED**

Repository code baseline: `67701b4debd3b82971b78aa9650541f3f91b584a` (PR #414 merged).

## Purpose

This directory is the fresh qualitative acceptance case for #321 after the Direct Deep loop mechanics landed on main. It tests the product behavior that one Human authorization can drive multiple bounded internal research passes without fake Discovery / Pre / Quick / DEEPEN state.

The Human message bound to this run was the project-level `继续`; it did **not** add a second/third-round research instruction such as “查现金” or “再查 license-out”. The executor itself selected and completed the evidence, cash-bridge, adversarial and STOP passes. This distinction is recorded because a generic project continuation is not evidence that the Human manually supervised each research round.

## Fixed clocks and authority

- Human request / Research cutoff: `2026-09-17T09:57:00Z` (`17:57 +08:00`).
- Research origin: `HUMAN_ORIGIN_DIRECT_DEEP_FRESH_DOGFOOD`.
- Predecessor frozen ResearchSnapshot: `ea9b4e56-c998-5dcd-b8fa-3f1539612762` from the retained 2026-09-11 Hengrui Research.
- Market: `NOT_REQUESTED`.
- Odds: `NOT_COMPUTED`.
- Investment authority: `NONE`.

The cutoff freezes what could change Belief. Retrieval after the cutoff is allowed only for material that was already available by the cutoff.

## Passes

1. **Evidence universe / economic question reset.** Re-read 2026H1 financials, BMS 10-Q, the 9/10 management-reply mirror and post-prior-cutoff company announcement scope.
2. **Profit → cash → necessary reinvestment.** Reconcile H1 attributable profit to CFO and long-term-asset/development cash.
3. **License-out / double-counting challenger.** Compare consolidated vs parent license-cost scopes and explicitly prevent duplicated cash, accounting income, equity fair-value and royalty value.
4. **UNKNOWN / STOP.** Stop when the remaining decisive questions require future product-level or Q3 periodic-report evidence rather than more public-background searching.

No price was used to change Research Belief.

## Fresh findings frozen in the Research package

- 2026H1 attributable net profit: CNY `4,465,439,428.10`.
- 2026H1 CFO: CNY `1,987,003,872.34`.
- Cash paid for fixed/intangible/other long-term assets: CNY `1,577,505,322.86`, including development expenditure CNY `1,148,782,134.14`.
- Diagnostic `CFO - long-term-asset cash`: CNY `409,498,549.48`. This is **not** automatically FCFE.
- H1 license revenue: CNY `1,422,301,939.04`; reported license cost differs sharply by consolidation scope (consolidated CNY `22,191,700.84`, parent CNY `399,955,124.72`). This is evidence against using headline accounting license margin as full-cycle economic profit.
- BMS primary 10-Q states the transaction closed in July 2026 and contractually calls for a USD `600m` upfront payment in 2026Q3.
- A secondary mirror of the 9/10 company management replies states that the USD `600m` was received in Q3 and recorded in contract liabilities. Because the official SSE answer bytes were not captured, the fresh Research treats this as **REDUCED but not formally CLOSED** until the Q3 periodic report.
- The captured company announcement scope after the prior Research contains additional clinical/regulatory progress but no new periodic financial filing that closes product-level net pricing, license full-cost economics or normalized shareholder cash.

## Remaining decisive UNKNOWNs

The final four open questions are preserved exactly in `research-package.json`. They concern product-level net economics, License-out full-cycle net cash, formal Q3 BMS accounting closure, and normalized shareholder cash after necessary reinvestment.

The separate double-counting question is **CLOSED as a method discipline**: the final Research does not add cash principal + interest, upfront cash + later accounting recognition, equity stock value + its fair-value gain, or future royalty twice.

## Retention and replay

- `source-captures.json` — exact extracted-value captures and source qualifications; `EXTRACTED_VALUES / PARTIAL`, not invented full-source retention.
- `request.json` — exact Direct Deep request and bounded budget.
- `pass-records.json` — ordered pass summaries, UNKNOWN transitions, receipts and exact evidence/package references without duplicating the package bytes.
- `research-package.json` — schema-v2 Research-only handoff.
- `commit-result.json` — expected generic Kernel commit result.
- `hashes.json` — request, result, information-bundle, package and source-capture identities.

`tests/test_hengrui_direct_deep_fresh_dogfood.py` rehydrates these files through the real current-main `run_direct_deep()` and `commit_research_package()` implementation. A replay test passing establishes identity/mechanics and that the retained fresh Research can commit independently of Market. It does not prove investment truth, Human thesis acceptance, or long-run research effectiveness.

## Acceptance interpretation

This case can support #321 Acceptance 1 only at the **interaction/execution-quality** level if review agrees that the fresh four-pass output reaches approximately the prior Hengrui Round-3 decision-useful boundary without substantive Human round-by-round instructions.

It does **not** establish:
- canonical Odds or Acceptance 9;
- cardinal probability;
- current fair value / buy price;
- Human acceptance, Decision, Action or Watch;
- that the source mirror is equivalent to exchange-original bytes;
- long-run calibration or investment performance.
