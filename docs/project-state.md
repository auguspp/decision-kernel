# Decision Kernel — Current Project State

Status: **MUTABLE CURRENT-STATE INDEX / NOT AUTHORITATIVE OVER FROZEN LINEAGE / NO NEW SCHEMA**  
Updated: **2026-09-04**  
Repository: `auguspp/decision-kernel`

## Operating rule

This file is the default cross-conversation current-state entry. Frozen Research / Human Decision / Action / Outcome artifacts remain authoritative over this mutable index.

```text
New conversation: 读状态，继续。
End of conversation: 同步状态。
```

`同步状态` updates only real state deltas; no ceremonial edits.

---

## 1. Current phase

```text
TRUSTWORTHY COGNITION CORE = STABLE ENOUGH TO STOP EXPANDING WITHOUT FAILURE
RESEARCH METHOD = DE-PRIORITIZED FOR METHOD-LED EXPANSION
ATTENTION ACQUISITION = ACTIVE HIGHEST PRIORITY
HUMAN ATTENTION SURFACE = ACCEPTED / MERGED / ACTIVE
HETEROGENEOUS PROSPECTIVE CASES = RADAR-ASSISTED, EVENT-DRIVEN
ODDS / CONSTITUTION REDESIGN = FROZEN PENDING OUTCOME-BACKED EVIDENCE
```

Current product objective:

> **后台足够复杂，前台足够简洁。Human first view should answer: 看哪只股票 / 为什么值得看 / 现在研究到哪一步；其余信息按需钻取。**

Human attention budget is intentionally scarce. Background discovery may be broad and noisy; the Human front door should normally show only 0–3 genuinely attention-worthy tickers, or explicitly say nothing requires attention.

Do not add frameworks, schemas, enums, routers, category-filling cases, or composite opportunity scores for completeness.

---

## 2. Architecture / doctrine

Decision Kernel is a **Decision Hygiene layer, not a Truth Machine**.

```text
Reality
→ Evidence / Claims
→ Discovery / Radar
→ Research Funnel
→ Attention Inbox
→ Research
→ frozen ResearchSnapshot
→ Observed Market
→ Odds
→ Decision Rehearsal
→ Human Surface
→ Human decides
```

Two Human-attention lanes share one front door without merging authority:

```text
Research Funnel
→ DEEPEN_REQUIRED
→ Research-attention card

Decision Spine
→ HumanResearchSurface.attention_eligible == true
→ Decision-review card
```

Semantics:

```text
DEEPEN_REQUIRED = spend Research budget
DEEPEN_REQUIRED != BUY signal
DEEPEN_REQUIRED != canonical Decision wake

HumanResearchSurface.attention_eligible = canonical Decision-review wake
```

Core doctrine remains:

```text
Evidence changes Belief.
Price changes Odds.

Research complete != Probability established != Odds ready.
Research explains reality.
Kernel enforces mechanical invariants.
Human owns the investment decision.
Investment Authority = NONE.
Frozen lineage is authoritative.
```

```text
CONSTITUTION CHANGE = NOT AUTHORIZED
SCHEMA CHANGE = NOT AUTHORIZED
NEW PROBABILITY STATE MACHINE = NOT AUTHORIZED
SECOND HUMAN WAKE GATE = NOT AUTHORIZED
LIVE ODDS POLICY REPLACEMENT = NOT AUTHORIZED
```

---

## 3. Attention system — accepted current state

### Human Attention Surface

PR #139 `feat: compress Human Attention surface` is **HUMAN ACCEPTED / MERGED / AUTHORITATIVE PRODUCT BEHAVIOR**.

Merge commit: `258ec766d1c611eeed1cf1f0bd3cc76e773734da`.

Front surface is ticker-first and drill-down oriented:

```text
company / ticker / price
→ 为什么值得看
→ current Research / Odds state
→ 深入查看 only on demand
```

Quiet researched cases remain collapsed; empty state explicitly says no Human attention is required while background monitoring continues.

### Cold-start Research attention

PR #140 `feat: add Research attention to ticker-centric Inbox` is **HUMAN ACCEPTED / MERGED / AUTHORITATIVE HARNESS BEHAVIOR**.

Merge commit: `dc7973bfb16e368017128d8c3ba0bce8f8558160`.

Accepted behavior:

- consume existing validated `ResearchFunnelResult`;
- only `DEEPEN_REQUIRED` reaches the Human front surface;
- `WAIT_FOR_TRIGGER` / `DROP_FOR_NOW` remain background dispositions;
- multiple Research questions for one ticker may be grouped into one front card;
- if the ticker already has frozen Research / live Odds, join that display state without mutating frozen Research;
- true cold-start cases explicitly show:

```text
尚未建立 frozen Research
Odds 未生成
```

No new Radar score, Research route, wake gate, Belief authority, probability state, recommendation, or investment authority was added.

### Scheduled production composition

PR #144 `feat: wire scheduled Research attention inbox` is **MERGED / ACTIVE HARNESS WIRING**.

Merge commit: `91990649692cfeacd2c73bdaf05c3936a6761426`.

The weekday `decision-inbox` workflow now runs `python -m decision_kernel.runtime.attention_inbox` and maintains two separate explicit lists:

```text
decision_packages
research_attention_handoffs
```

`decision_packages` remains curated for current live Odds. `research_attention_handoffs` may contain only exact, unresolved, validated `ResearchFunnelResult` files that currently retain `DEEPEN_REQUIRED`.

Current scheduled Research-attention list:

```text
EMPTY — no unresolved DEEPEN_REQUIRED handoff exists at this PIT
```

Tinavi's frozen cold-start handoff remains audit lineage, but Full Research and the Human WATCH / NO_ACTION disposition have resolved that attention request. It must not recur as a stale daily cold-start card.

Operating rule:

```text
new unresolved DEEPEN_REQUIRED -> add exact path
Full Research / Human disposition resolves request -> remove exact path
frozen handoff remains auditable
file presence alone never restores current Human-facing eligibility
```

No new score, route, wake gate, schema, recommendation, or investment authority was added.

### Disclosure scan / receipt-memory health

The 2026-09-03 scheduled disclosure artifact (`33757562673`) contained exactly nine packet identities: eight CATL batches and one Sanhua batch. Existing Research Funnel semantics resolved them as:

```text
DROP_FOR_NOW = 5
WAIT_FOR_TRIGGER = 4
DEEPEN_REQUIRED = 0
```

PR #147 recovered those nine exact quiet identities into the default-branch best-effort Actions cache. PR #148 removed the one-time recovery workflow and script after the cache save and audit artifact succeeded.

The 2026-09-04 current scan then restored that cache and correctly suppressed all nine previously reviewed identities. It surfaced exactly two genuinely new packet identities:

- China Shenhua `1225546775 + 1225546779` — meeting notice/materials repeat the interim-dividend proposal already disclosed before the frozen Research cutoff and add only voting procedure/timing. Disposition: **DROP_FOR_NOW**.
- GigaDevice `1225546905` — visual review of the H-share next-day securities return confirms a 2026-09-03 A-share repurchase of 135,000 shares (0.02%) at RMB380.27–385.00 for RMB51,852,403, intended for cancellation; issued A shares remained 670,718,327. This is real post-H-share capital-allocation evidence, but not enough to establish a material per-share owner-economics change. Disposition: **WAIT_FOR_TRIGGER**.

Current new-packet result:

```text
DROP_FOR_NOW = 1
WAIT_FOR_TRIGGER = 1
DEEPEN_REQUIRED = 0
```

PR #153 validated the exact packet/content hashes, replayed both assessments through the existing Research Funnel, asserted that no Human Research attention was earned, and saved both quiet receipts to default-branch cache. PR #154 then removed the temporary recovery workflow and helper script; no recovery-only product code remains.

Receipt memory remains only a Harness attention optimization:

```text
cache hit -> suppress this exact already-reviewed quiet identity
cache loss -> reassess rather than silently suppress
receipt != Research truth
receipt != Human wake
```

No current disclosure packet earned Human Research attention. The scheduled `research_attention_handoffs` list remains empty.

### HiThink live acquisition health

PR #149 `fix: reduce HiThink batch pressure without fallback` is **MERGED / ACTIVE HARNESS BEHAVIOR**.

Merge commit: `e4bac4eb6e4aed37d0b86e638c67415b26d2bbc1`.

The live acquisition path reuses only the exact trading-calendar response within one process for the same credential, Shanghai date and timeout. Price-history requests remain independent and uncached. A new Shanghai date cannot inherit the prior date's calendar.

Real operations probes established the fail-closed boundary before the first successful post-close proof:

```text
probe 1 -> TLS handshake timeout at calendar request
probe 2 -> HTTP 429 at first history request
post-#149 intraday probe -> calendar + history transport succeeded
               -> provider returned unfinished current-session row
               -> adapter rejected it before Research / Odds / Human surface
```

Rejecting the unfinished intraday row was intended PIT protection, not a production defect. Do not force a future `observed_at`, silently filter a provider contract violation, accept an intraday row as a completed close, substitute stale prices, or add a fallback market provider.

PR #156 was a same-repository operations probe and was **CLOSED WITHOUT MERGE** after preserving its proof artifact. Workflow run `33848495590` then established the first full post-#149, post-close Human composition proof using the exact current five-package production set and the real HiThink credential:

```text
completed market session = 2026-09-04 15:00 +08:00
Research attention = 0
canonical Decision wake = 1
Research handoffs = 0
researched cases = 5

CATL / 300750 = CNY351.00 / ACCEPTABLE_ODDS / Human review
Sanhua / Moutai / China Shenhua / GigaDevice = quiet / INSUFFICIENT_ODDS
stale Tinavi cold-start attention = absent
Investment Authority = NONE
```

This proves the normal post-close acquisition and Human rendering path. It does not validate every future provider response, create a retry/fallback policy, or change frozen Research, Odds thresholds, Human Decisions, Actions or authority.

### Operating constraint from legacy Web Radar

The old Codex Radar GitHub mirror no longer exists; references to reading that mirror are legacy OS-era assumptions.

Current Web-based radars produce too much Human-visible output and have become an attention-fragmentation source: Human consumption is effectively `有时间就看 / 没时间就不看`.

Accepted direction:

```text
Web / GitHub background discovery may remain complex
→ durable PIT artifacts / Research Funnel
→ ticker-centric Attention Inbox
→ Human sees only what deserves attention
→ drill down on demand
```

Do not rebuild another broad dashboard. Migration of existing Web scanners into durable GitHub-backed producers is future plumbing, not a new cognition framework.

---

## 4. Current live cases

### GigaDevice / 603986.SH
- Thesis: cycle-amplified fabless platform; longer specialty-memory duration + higher post-cycle earnings floor remain live.
- Probability: partial / ordinal; full cardinal distribution not established.
- Human Decision: **CONDITIONAL BUY** — ~CNY350 re-underwrite; CNY320–335 first-entry band only if thesis survives.
- Action: **NOT EXECUTED**.
- 2026-09-03 repurchase execution: 135,000 A shares / 0.02% / RMB51.85m / intended cancellation; Research Funnel disposition **WAIT_FOR_TRIGGER**. This does not reopen Full Research or change the frozen Human Decision.
- Pointer: `docs/decisions/603986-gigadevice-human-decision-2026-09-03.md`.

### Sanhua / 002050.SZ
- Core thermal-management economics remain auditable.
- Robot operating-economics challenger: **HUMAN ACCEPTED / MERGED / AUTHORITATIVE** via PR #136.
- Research: **STOP / REOPEN** at a reasonable public-evidence boundary.
- Human Decision: **CONDITIONAL BUY** — first tranche around CNY30.
- Action: **NOT EXECUTED**.
- CNY3.5bn robot success state: **not disproven / not independently established**.
- Pointer: `docs/decisions/002050-sanhua-human-decision-2026-09-03.md`.

### Tinavi / 天智航 / 688277.SH

This is the first accepted real cold-start Attention Inbox case.

PR #141 `dogfood: surface Tinavi DRG/DIP payment change` is **HUMAN ACCEPTED / MERGED**; merge commit `9d020f2b121e7253ef91756fb3deb8ebc8bf1cc6`.

It proved the real chain:

```text
policy / industry change
→ listed-company mapping
→ contradiction
→ Research Funnel
→ DEEPEN_REQUIRED
→ ticker-centric Human attention
```

without creating Odds, a recommendation, or a second wake gate.

PR #142 `research: underwrite Tinavi reversal candidate` is **HUMAN ACCEPTED / MERGED / AUTHORITATIVE RESEARCH LINEAGE**; merge commit `207b1d57b4282de0f5435ece6e12ecdef48aa219`.

Accepted Research state:

```text
CLINICAL UTILIZATION = REAL / GROWING
PAYMENT-FRICTION REDUCTION = PLAUSIBLE / PARTIALLY ESTABLISHED
RECURRING MONETIZATION REVERSAL = NOT ESTABLISHED
OWNER-CASH REVERSAL = NOT ESTABLISHED
PROPOSED M&A STRATEGIC FIT = PLAUSIBLE
PROPOSED M&A PER-SHARE ECONOMICS = NOT ESTABLISHED
PRICE DRAWDOWN = FACT
CHEAPNESS = NOT ESTABLISHED
CARDINAL PROBABILITY = NOT ESTABLISHED
NUMERICAL ODDS = NOT METHOD-READY
```

Human Decision is frozen:

```text
DECISION = WATCH / CONTINUE FOLLOWING
ACTION = NO_ACTION
RESEARCH = STOP CURRENT PUBLIC-DILIGENCE LOOP / REOPEN ON DISCRIMINATING EVIDENCE
FOLLOWED = YES
```

Central question:

> Can improved hospital payment treatment make already-real procedure growth convert into recurring revenue, gross profit and owner cash, and can the proposed Shanghai MicroPort Orthopedics transaction improve rather than dilute per-share owner economics?

Reopen buckets:
1. local DRG/DIP payment implementation / hospital economics;
2. procedure monetization — utilization, consumables/service revenue per procedure, attach rate, recurring mix, margin;
3. owner-cash conversion — revenue reacceleration, loss narrowing, OCF, working capital;
4. transaction economics — final consideration, purchase-share dilution, financing dilution, audited target economics, goodwill, pro-forma balance sheet / cash flow;
5. Reference-Frame evidence — robot + implant + overseas-channel economics versus simple combination of loss-making / capital-intensive businesses.

Pointers:
- `docs/dogfood/tinavi-full-research-zero-schema-2026-09-04.md`
- `docs/dogfood/tinavi-reversal-proof-table-2026-09-04.md`
- `docs/decisions/688277-tinavi-human-watch-2026-09-04.md`

### YTO / 600233.SH
- Research complete enough to stop; franchise/network economics and reinvestment remain load-bearing.
- Cardinal probability not established; price remains QUIET for Fundamental Belief.
- No Human investment decision; Action NONE.
- Pointer: `docs/dogfood/yto-evidence-trigger-design-2026-09-03.md`.

### Micron / MU
- SCA/AI-memory may improve cycle economics; company-wide structural rebase unproven.
- Human Decision: **WAIT / DO NOT BUY FOR NOW** under current U.S.-equity constraint.
- Action: NO_ACTION.
- Next hinge: **2026-09-30 FY2026/FQ4 earnings**.
- Pointer: `docs/decisions/MU-micron-human-wait-validation-2026-09-03.md`.

### Midea / 000333.SZ
- Mature high-ROE global consumer-industrial franchise; owner-return better expressed through retention × incremental ROIC.
- No Human decision; Action NONE.

### Xiamen Tungsten / 600549.SH
- Historical Reference-Frame failure negative control.
- Not a current action candidate; Action NONE.

---

## 5. Radar state

### Commitment Radar
Purpose: allocate attention to frozen commitments that can now be resolved or falsified.

Current v0 proves exact Research / commitment / Evidence lineage; semantic relevance remains cognition. CATL buyback-progress is still the same capital-allocation theme, not a genuinely different second promotion case.

### Surprise Radar
Purpose: discover **post-Research price anomalies** in already-researched cases so Human can allocate attention.

Eligibility:

```text
ResearchSnapshot.created_at exists before candidate anomaly
+ anomaly occurs after Research creation
```

`ResearchSnapshot.as_of_datetime` is PIT cutoff only, not Research-existence proof.

Accepted reviewed baseline remains:

```text
eligible post-Research daily observations = 10
securities represented = 6
largest absolute eligible daily move = 2.74% / CATL / 2026-09-02
qualified price-anomaly label = NOT YET EARNED
false-negative candidate = NOT YET EARNED
anomaly detector = NOT YET PROMOTED
```

Do not turn 2.74% into a threshold.

The 2026-09-04 post-close proof exposed a separate Harness input failure: `dogfood/*.json` had become invalid because the directory now contains Research package objects, Evidence arrays and Research-attention handoffs. The Human Inbox still rendered, but the independent shadow failed closed on a non-object package input.

PR #157 `fix: curate Surprise Radar shadow package inputs` is **MERGED / ACTIVE HARNESS BEHAVIOR**.

Merge commit: `ca512c07ce7c7c229f369e9b6606bcb46fb96d8e`.

The scheduled shadow now uses an exact, explicit six-package list rather than a heterogeneous directory wildcard. Real proof run `33848953117` produced and validated:

```text
qualified windows = 6
tickers = 600519 / 300750 / 600036 / 601088 / 603986 / 002050
response session = 2026-09-04
Radar semantics = SHADOW_OBSERVATION_ONLY
Human attention authority = NONE
Investment Authority = NONE
```

These short-lived windows prove acquisition and batch integrity only. They have not been reviewed into a new anomaly corpus, do not change the accepted 10-observation baseline above, and do not authorize a detector, threshold or automatic Research route.

Human alert policy remains:

```text
PRE-EXISTING RESEARCH = YES
CASE REMAINS FOLLOWED = YES
QUALIFIED PRICE ANOMALY = YES
→ MAY ALERT BY DEFAULT
```

Alert = attention only. It does not automatically reopen Research, change Belief or Odds, recommend, act, or create investment authority.

Cold-start Attention Discovery and Surprise Radar remain distinct products:

```text
Cold-start Discovery = what deserves first Research attention?
Surprise Radar = what already-researched case deserves renewed attention?
```

Do not merge their semantics merely because both feed the same Human Inbox.

---

## 6. Research-method lessons currently live

Reusable discipline:

```text
industry success
!= company revenue
!= listed-company profit
!= owner cash
```

Tinavi adds a heterogeneous confirmation:

```text
procedure / usage growth
!= recurring monetization
!= gross-profit conversion
!= owner cash
```

A large drawdown may justify attention but does not establish cheapness.

A policy change may improve an economic friction point but must still be traced through:

```text
policy
→ customer / hospital economics
→ operating behavior
→ listed-company revenue / margin
→ capital / cash conversion
→ per-share owner economics
```

A proposed acquisition that can change business mix / capital structure must be treated as a possible Reference-Frame change, not free optionality. Standalone and pro-forma worlds must not borrow economics from one another before transaction terms are established.

Pointers:
- `docs/full-research-review-gate-v1.md`
- `docs/full-research-price-implied-economics-closure-v1.md`

---

## 7. Next work

Priority order:

1. **Use, do not expand.** Let real policy, industry, disclosure, price/path and open-discovery events generate candidates.
2. When a real unresolved `DEEPEN_REQUIRED` handoff appears, add its exact path to the scheduled `research_attention_handoffs` list; remove it promptly when Full Research or a Human disposition resolves the attention request.
3. Keep exact quiet disclosure receipts as lossy Harness memory only; cache loss must cause reassessment, not silent suppression.
4. Human front surface should remain 0–3 tickers or `nothing requires attention`.
5. Run Full Research only on cases that earn `DEEPEN_REQUIRED`; leave WAIT/DROP in background.
6. Tinavi remains WATCH / NO_ACTION until one of its five reopen buckets changes.
7. Sanhua remains STOP / REOPEN until its frozen evidence buckets change.
8. Continue natural Surprise Radar observation through the explicit curated shadow package list; review real windows before promoting any detector or threshold.
9. Continue Commitment Radar without promoting a second attention authority.
10. Treat MU 2026-09-30 earnings as a natural prospective replay hinge if no more important event arrives first.
11. Freeze real Human Decision / Action / Outcome / falsifier / resolution lineage promptly when events occur.

---

## 8. Do not do

```text
no new probability enum
no EconomicSpecies schema / router
no second investment-decision wake gate
no probability generator
no generic provider framework
no broker / portfolio ledger inside Kernel
no heuristic Decision ↔ Action linking
no price → Fundamental Belief shortcut
no forced cardinal probabilities
no conceptual framework without real case pressure
no composite opportunity score as attention authority
no broad Human-facing dashboard that exposes background noise
no Surprise Radar threshold tuned to one historical example
no pre-Research price window promoted as current Radar evidence
no as_of_datetime used as Research-existence timestamp
no per-anomaly Human alert permission loop for actively followed researched cases
no Sanhua- or Tinavi-specific numbers promoted into generic constants
no intraday row used as completed-close Odds input
no fallback or stale-price substitution when HiThink fails
```

Also:
- do not infer historical Human intent from trades or price paths;
- do not use market movement alone as Outcome attribution;
- do not infer “no longer followed” without an explicit Human statement;
- do not equate capacity / project investment / policy support / procedure growth with realized owner return;
- do not let presentation-friendly wording mutate canonical frozen state.

---

## 9. Authoritative entry pointers

- `docs/project-state.md` — mutable current-state index.
- `docs/decision-hygiene-constitution-review-checkpoint-2026-09-03.md` — Constitution / schema disposition.
- `docs/live-decision-book.md` — live-case navigation; subordinate to frozen case artifacts.
- `docs/decision-inbox.md` — accepted ticker-centric Attention Inbox behavior and scheduled composition rule.
- `src/decision_kernel/runtime/attention_inbox.py` — Research-attention + Decision-review Human front door.
- `.github/workflows/decision-inbox.yml` — scheduled explicit Decision, Research-attention and Surprise Radar shadow package lists.
- `src/decision_kernel/runtime/hithink_http.py` — fail-closed HiThink transport, completed-session qualification and process-local calendar reuse.
- `src/decision_kernel/runtime/disclosure_receipts.py` — exact quiet-disposition receipt semantics.
- `docs/full-research-review-gate-v1.md` — Full Research review discipline.
- `docs/full-research-price-implied-economics-closure-v1.md` — price-implied economics closure discipline.
- `docs/dogfood/sanhua-robot-operating-economics-challenger-2026-09-03.md` — accepted Sanhua challenger.
- `docs/dogfood/surprise-radar-v0-first-post-research-baseline-2026-09-04.md` — prospective Radar baseline.
- `docs/dogfood/surprise-radar-v0-human-alert-policy-2026-09-04.md` — Human alert policy.
- `docs/dogfood/tinavi-full-research-zero-schema-2026-09-04.md` — accepted Tinavi Full Research.
- `docs/decisions/688277-tinavi-human-watch-2026-09-04.md` — frozen Tinavi WATCH decision.
- `docs/prospective-decision-outcome-capture-protocol-2026-09-03.md` — longitudinal capture discipline.

---

## 10. Recent state delta

- **NEW — PR #149 merged.** HiThink trading-calendar acquisition is reused only within the same process / credential / Shanghai date / timeout; histories remain independent, and endpoint-specific failures remain visible without retry, fallback or stale-price substitution.
- **NEW — 2026-09-04 current disclosure review closed with 1 DROP / 1 WAIT / 0 DEEPEN after the recovered cache suppressed all nine previously reviewed identities.** China Shenhua meeting materials were dropped as repeated voting/timing disclosure; GigaDevice’s 135,000-share / 0.02% repurchase execution remains WAIT_FOR_TRIGGER. PR #153 saved both exact quiet receipts to default-branch cache; PR #154 removed all temporary recovery code.
- **NEW — first full post-#149 post-close production proof succeeded.** PR #156 was closed without merge after run `33848495590` accepted the completed 2026-09-04 session, rendered 1 canonical Decision wake / 4 quiet cases / 0 Research attention, excluded stale Tinavi attention and preserved Investment Authority NONE.
- **NEW — PR #157 merged after the same proof exposed a heterogeneous `dogfood/*.json` shadow-input failure.** The scheduled Surprise Radar shadow now uses six exact Research package objects; real run `33848953117` produced six qualified 2026-09-04 windows with no Human or investment authority.
- **NEW — PR #144 merged.** The weekday job now runs the ticker-centric Attention Inbox composition root with separate explicit Decision and Research-attention lists; the current Research-attention list is empty, and resolved handoffs do not regain eligibility from file presence.
- **NEW — PR #139 accepted / merged.** Human front surface is ticker-first, why-worth-looking-first, drill-down oriented.
- **NEW — PR #140 accepted / merged.** `DEEPEN_REQUIRED` Research attention and canonical Decision review now share one Human Inbox without merging authority.
- **NEW — legacy Codex Radar GitHub mirror is confirmed gone.** Existing Web Radar long outputs are recognized as an attention-fragmentation problem; future migration should hide background complexity rather than reproduce dashboards.
- **NEW — PR #141 accepted / merged.** Tinavi is the first real cold-start policy/industry discovery to pass Research Funnel and surface as a ticker-centric attention case.
- **NEW — PR #142 accepted / merged.** Tinavi Full Research is authoritative Research lineage; business reversal and cheapness remain unproven.
- **NEW — Tinavi Human Decision frozen as WATCH / CONTINUE FOLLOWING / NO_ACTION.** Research stops current public loop and reopens only on discriminating payment, monetization, owner-cash, transaction or Reference-Frame evidence.
- **UNCHANGED — Sanhua remains CONDITIONAL BUY around CNY30 / Action NOT EXECUTED.**
- **UNCHANGED — GigaDevice remains CONDITIONAL BUY / Action NOT EXECUTED.**
- **UNCHANGED — Surprise Radar detector / score / automatic Research route / schema / investment authority remain unpromoted.**
