# Decision Kernel — Current Project State

Status: **MUTABLE CURRENT-STATE INDEX / NOT AUTHORITATIVE OVER FROZEN LINEAGE / NO NEW SCHEMA**  
Updated: **2026-09-04**  
Repository: `auguspp/decision-kernel`

## Operating rule

This file is the **single default cross-conversation current-state entry**.

It describes only what is true **now**. It is not a chat summary, changelog, Research store, Decision ledger, or second Constitution.

If this file conflicts with a frozen Research / Human Decision / Action / Outcome artifact, the **frozen artifact wins** and this file must be corrected.

Historical `docs/handoffs/*` remain lineage only and are **not** part of the default context-recovery path.

Cross-conversation protocol:

```text
New conversation: 读状态，继续。
End of conversation: 同步状态。
```

`同步状态` means: update only real project-state changes from the conversation. If there is no state delta, do not modify this file for ceremony.

---

## 1. Current phase

```text
TRUSTWORTHY COGNITION CORE = STABLE ENOUGH TO STOP EXPANDING WITHOUT FAILURE
RESEARCH METHOD = DE-PRIORITIZED FOR METHOD-LED EXPANSION
ATTENTION ACQUISITION = ACTIVE HIGHEST PRIORITY
HETEROGENEOUS PROSPECTIVE CASES = RADAR-ASSISTED, EVENT-DRIVEN
ODDS / CONSTITUTION REDESIGN = FROZEN PENDING OUTCOME-BACKED EVIDENCE
```

Current priority:

```text
Attention Radar
+ Radar-assisted heterogeneous prospective cases
+ real prospective events
+ longitudinal Decision / Action / Outcome evidence
```

Do not keep adding Research Method frameworks, schemas, enums, routers, or category-filling cases for completeness. A real disclosure, commitment resolution, surprise, Human Decision / Action, or Outcome has higher priority than new conceptual machinery.

---

## 2. Current architecture / doctrine

Decision Kernel is a **Decision Hygiene layer, not a Truth Machine**.

```text
Reality
→ Evidence / Claims
→ Radar / Attention Allocation
→ Research
→ frozen ResearchSnapshot
→ Observed Market
→ Odds
→ Decision Rehearsal
→ Human Surface
→ Human decides
```

Current doctrine:

```text
Evidence changes Belief.
Price changes Odds.

Research complete
!= Probability established
!= Odds ready

Research explains reality.
Kernel enforces mechanical invariants.
Human owns the investment decision.

Investment Authority = NONE.
Frozen lineage is authoritative.
```

Radar, Research, Odds, and Human Surface do not acquire investment authority by producing a more complete analysis.

---

## 3. Current unresolved architecture questions

These are active questions, **not authorization to change Constitution or schema**.

- **Research freeze vs cardinal probability qualification** — current evidence repeatedly shows Research can be mature enough to freeze before a full cardinal distribution is qualified.
- **Human Surface currently depends on Odds** — whether that remains the right long-run dependency when Research is complete but Odds are not method-ready remains unresolved.
- **Odds v0 validity / horizon normalization** — the semantic and horizon problem is real; replacement policy remains unproven without heterogeneous outcome-backed evidence.
- **Decision → Action → Outcome → Attribution** — prospective longitudinal evidence is still too thin to calibrate Research / Odds / Human Decision failure modes cleanly.

Current disposition:

```text
CONSTITUTION CHANGE = NOT AUTHORIZED
SCHEMA CHANGE = NOT AUTHORIZED
NEW PROBABILITY STATE MACHINE = NOT AUTHORIZED
SECOND HUMAN WAKE GATE = NOT AUTHORIZED
LIVE ODDS POLICY REPLACEMENT = NOT AUTHORIZED
```

---

## 4. Current live cases

Frozen artifacts own the details. This table is navigation only.

| Case | Current state | Human Decision / Action | Next hinge | Authoritative pointer |
| --- | --- | --- | --- | --- |
| **GigaDevice / 603986.SH** | Cycle-amplified fabless platform; longer specialty-memory duration + higher post-cycle earnings floor remain the live thesis. Probability knowledge is partial / ordinal; full cardinal distribution not established. | **CONDITIONAL BUY**: ~CNY350 re-underwrite; CNY320–335 first-entry band only if thesis survives. **Action: NOT EXECUTED.** | Duration, supply, storage GM, foundry / procurement economics, inventory / OCF, MCU / custom memory, 2030 earnings floor. | `docs/decisions/603986-gigadevice-human-decision-2026-09-03.md` |
| **Sanhua / 002050.SZ** | Observable thermal-management base remains auditable. Robot operating-economics challenger in PR #136 has reached a **reasonable public-evidence boundary / stop state**. `FACT`: batch delivery + production-line ramp; Thailand BOI **THB1.8bn humanoid-actuator planned capital** at a 100%-consolidated listed-company subsidiary; current-stage external harmonic-reducer validation / small-batch supply into Sanhua; the specific market rumor of a **large robot order was formally denied**. Group-level hollow-cup-motor JV capability is not listed Sanhua equity. Robot revenue / GM, rated capacity, realized robot-only capital, mature allocation, mature make-buy, incremental ROIC and owner cash remain `NOT ESTABLISHED`. | **CONDITIONAL BUY**: first tranche around CNY30. **Action: NOT EXECUTED.** | **STOP by default. REOPEN only** on real new evidence in five buckets: (1) named customer / allocation / second source / realized volume; (2) mature robot architecture / module quotation / price-down; (3) robot-specific rated capacity / shipments / yield / utilization; (4) listed-company make-buy / related-party product identity / transfer-pricing economics; (5) robot-specific revenue / margin / PP&E / tooling / working capital / maintenance capex. | `docs/decisions/002050-sanhua-human-decision-2026-09-03.md` |
| **YTO / 600233.SH** | Research complete enough to stop current loop; franchise / network economics and reinvestment remain load-bearing. Cardinal probability not established; price remains `QUIET` for Fundamental Belief. | **No Human investment decision. Action: NONE.** | Frozen `QUIET / REOPEN / FRAME CHANGE` evidence triggers; reopen only on discriminating operating / network / owner-cash evidence. | `docs/dogfood/yto-evidence-trigger-design-2026-09-03.md` |
| **Micron / MU** | SCA / AI-memory may improve cycle economics; company-wide structural rebase remains unproven. | **WAIT / DO NOT BUY FOR NOW** under current Human U.S.-equity constraint. **Action: NO_ACTION.** | **2026-09-30 FY2026/FQ4 earnings**: SCA floor, HBM, FY27 GM, capex / depreciation, normalized FCF, incremental ROIC. | `docs/decisions/MU-micron-human-wait-validation-2026-09-03.md` |
| **Midea / 000333.SZ** | Mature high-ROE global consumer-industrial franchise; owner-return model is better expressed through retention × incremental ROIC than narrative-frame proliferation. | **No Human investment decision. Action: NONE.** | Smart Home durability, overseas OBM economics, B2B incremental ROIC, normalized owner cash, true net share shrinkage. | `docs/dogfood/midea-compounder-decision-hygiene-zero-schema-2026-09-03.md` |
| **Xiamen Tungsten / 600549.SH** | Historical Reference-Frame failure negative control; corrected resource / integrated-cycle frame remains the process guard. | **Not a current action candidate. Action: NONE.** | Reopen only if new evidence can map tungsten price + self-sufficiency + ownership / quota / capex into attributable through-cycle owner cash. | `docs/dogfood/xiamen-tungsten-research-error-negative-control-2026-09-03.md` |

For broader live-case navigation, use `docs/live-decision-book.md`; do not copy its full content here.

Sanhua's current mutable Research is in **PR #136** on branch `research/sanhua-robot-operating-economics-challenger`. The current pass is stopped at the public-evidence boundary. It is **not authoritative over frozen lineage until accepted / merged**. The branch has been re-read and reconciled to the latest mutable `docs/project-state.md`; `kernel-tests` passed; the PR is **mergeable and ready for review**. No Research conclusion changed during reconciliation. Do not add more Sanhua Research unless one of the five explicit reopen evidence buckets materially changes.

---

## 5. Current Radar direction

### Commitment Radar

Purpose: allocate attention to **previously frozen commitments** that can now be resolved or falsified.

Direction:

```text
frozen falsifiers
+ resolution paths
+ Human conditions where explicitly frozen
→ candidate new Evidence
```

Current v0 proves exact frozen Research / commitment / Evidence lineage; semantic relevance remains Research cognition. Human conditions remain subordinate to their frozen Decision artifacts and must not create a second wake gate.

The latest scheduled disclosure batch still does **not** supply the second promotion case. CATL's 2026-09-03 buyback-progress disclosure remains another CATL capital-allocation variant and should not be used to satisfy the requirement for a genuinely different naturally encountered commitment-resolution case.

### Surprise Radar

Purpose: discover **auditable post-Research blind-spot anomalies** that may justify reopening or deepening an already frozen Research case.

Current eligibility rule:

```text
frozen ResearchSnapshot must exist before candidate anomaly
+ candidate anomaly occurs after Research freeze
+ Human later labels whether Research triage was warranted
```

This is a load-bearing correction. Historical price bars that predate the ResearchSnapshot may remain useful descriptive context, but they **cannot** be promoted into the current Surprise Radar v0 control corpus.

Current state:

```text
qualified HiThink history input = available
short-lived shadow sampling = available
first real scheduled six-window batch = reviewed mechanically
valid positive control = NOT YET EARNED
valid negative control = NOT YET EARNED
valid false-negative candidate = NOT YET EARNED
anomaly detector = NOT YET PROMOTED
```

The first real scheduled shadow batch came from `decision-inbox` run `33757562673` and contained six qualified windows through 2026-09-03.

Mechanical review found GigaDevice to have the most distinct historical path, including a ~28% drawdown from 2026-07-21 to 2026-08-03. The Human later answered the counterfactual triage question with:

```text
A = worth alerting me; should trigger Research triage
```

However repository history shows the first GigaDevice Full Research package was committed only on **2026-09-02 09:37+08:00**, after that candidate anomaly. Therefore:

```text
603986 historical anomaly = COUNTERFACTUAL HUMAN TRIAGE ONLY
603986 valid Surprise Radar v0 positive control = NO / RETRACTED
```

The same eligibility issue rules out Sanhua's 2026-08-19 `-7.10%` move as a negative-control candidate: Sanhua's first Full Research package entered the repository only on **2026-09-02 20:24+08:00**.

PR #137 (`radar/first-real-shadow-review`) preserves the mechanical review and the correction. It should not claim a valid control until a post-Research anomaly is naturally observed and labeled.

Detector sophistication must wait for a minimally balanced **eligible** corpus:

1. one post-Research anomaly the Human judges worth Research triage;
2. one post-Research mechanically meaningful move the Human judges should remain `IGNORE`;
3. one post-Research quieter path where later decision-relevant evidence suggests a plausible false negative;
4. cross-case diversity / another naturally scheduled batch.

### Authority boundary

```text
Radar may prepare Evidence.

Radar may NOT create:
Fundamental Belief
Probability
Odds
Human Decision
Investment Authority
```

Default attention flow:

```text
Radar
→ Human triage
→ DEEPEN / WAIT / DROP
```

Decision Inbox attention is not the same thing as a Surprise Radar alert.

---

## 6. Next work

1. **Accumulate post-Research natural windows** — use each case's exact frozen ResearchSnapshot time as the left boundary for Surprise Radar control eligibility.
2. **Earn a valid positive control prospectively** — do not reuse pre-Research historical anomalies as if the Radar could have reopened Research that did not yet exist.
3. **Earn a valid negative control prospectively** — a mechanically meaningful post-Research move must be labeled `IGNORE` by the Human.
4. **Find a valid false-negative candidate** — a quieter post-Research path followed by genuinely decision-relevant evidence.
5. **Do not tune a detector yet** — the eligible control corpus is currently empty.
6. **Attention Radar** — continue Commitment Radar use and Surprise Radar observation without creating a second attention authority.
7. **Radar-assisted heterogeneous prospective cases** — let real surprises, commitment resolutions, and method mismatches select the next case; do not fill imagined company categories.
8. **Prefer prospective events to framework work** — real disclosure / resolution / price observation relevant to Odds / Human Decision / Action / Outcome outranks another conceptual framework.
9. **Freeze longitudinal evidence promptly** — when a Human Decision, confirmed Action, Outcome, falsifier, or resolution event occurs, preserve the appropriate immutable lineage before retrospective interpretation can rewrite it.
10. **Sanhua robot Research Challenger = STOP / REOPEN** — do not keep searching to make the report look complete. Reopen PR #136 only when primary evidence can change one of the five explicit evidence buckets above.

---

## 7. Do not do

```text
no new probability enum
no EconomicSpecies schema / router
no second Human wake gate
no probability generator
no generic provider framework
no broker / portfolio ledger inside Kernel
no heuristic Decision ↔ Action linking
no price → Fundamental Belief shortcut
no forced cardinal probabilities
no new conceptual framework without real case pressure
no Surprise Radar threshold tuned to one historical example
no pre-Research price window promoted as current Radar control
```

Also do not infer historical Human intent from trades or price paths, and do not use market movement alone as Outcome attribution.

For Sanhua specifically:

- do not upgrade unnamed-customer / exclusive-supply / allocation / volume claims from secondary supply-chain reporting when issuer, customer, exchange or supplier filings do not establish them;
- existing customer relationships in another product category do not prove robot-component supply;
- group-level manufacturing capability does not equal listed-company value capture when the relevant JV / entity sits outside listed Sanhua's equity perimeter;
- capacity ambition, project investment and factory readiness do not equal realized robot output, utilization or owner return.

---

## 8. Authoritative entry files

Use the smallest necessary set. Follow case-specific frozen pointers only when the current task requires them.

- `docs/project-state.md` — **default current-state entry; mutable index only**.
- `docs/decision-hygiene-constitution-review-checkpoint-2026-09-03.md` — current Constitution / schema-change disposition and architecture pressure.
- `docs/live-decision-book.md` — mutable live-case navigation; subordinate to frozen case artifacts.
- `docs/case-coverage-checkpoint-2026-09-03.md` — current phase, heterogeneous coverage, Attention Acquisition priority, longitudinal gaps.
- `docs/dogfood/commitment-radar-v0-2026-09-03.md` — Commitment Radar lineage boundary.
- `docs/dogfood/surprise-radar-v0-qualified-history-foundation-2026-09-03.md` and `docs/dogfood/surprise-radar-v0-shadow-sampling-2026-09-03.md` — Surprise Radar current input / observation foundation.
- PR #137 / `docs/dogfood/surprise-radar-v0-first-real-window-review-2026-09-04.md` — first real scheduled shadow-batch mechanical review + eligibility correction; **not authoritative until accepted / merged**.
- PR #137 / `docs/dogfood/surprise-radar-v0-gigadevice-positive-control-2026-09-04.md` — retained filename, now a corrected counterfactual Human-triage checkpoint; **not a valid positive control**.
- `docs/dogfood/odds-semantic-replay-cmb-v0-2026-09-03.md` — current Odds semantic / horizon pressure.
- `docs/prospective-decision-outcome-capture-protocol-2026-09-03.md` — prospective longitudinal capture discipline.

Historical handoffs remain available for lineage investigation only; they are not routine entry files.

---

## 9. Recent state delta

- **CORRECTED — Surprise Radar control eligibility requires pre-existing frozen Research.** A historical anomaly is not a valid current-v0 control when the relevant ResearchSnapshot was created only afterward.
- **RETRACTED — GigaDevice 2026-07-21 → 2026-08-03 is not a valid positive control.** First GigaDevice Full Research entered the repository on 2026-09-02 09:37+08:00. The Human's `A` response is preserved only as a counterfactual usefulness judgment.
- **REJECTED AS CANDIDATE — Sanhua 2026-08-19 `-7.10%` cannot be used as a current-v0 negative control.** First Sanhua Full Research entered the repository on 2026-09-02 20:24+08:00.
- **CHANGED — eligible Surprise Radar control corpus is currently empty.** Next evidence must come from naturally observed post-Research windows.
- **UNCHANGED — Commitment Radar promotion threshold remains unmet.** CATL's latest buyback-progress disclosure remains another CATL capital-allocation variant rather than a different natural case.
- **UNCHANGED — PR #136 Sanhua Research remains STOP / REOPEN at the current public-evidence boundary.**
- **UNCHANGED — project-level Attention Radar priority, frozen lineage authority, Human investment authority, Constitution / schema freeze, Evidence→Belief and Price→Odds doctrine remain intact.**
