# 2026-09-02 Web Conversation Handoff

Status: **working handoff for the next ChatGPT conversation**  
Repository: `auguspp/decision-kernel`  
Baseline main at handoff start: `539a0f3a03288566ffa8198ab371ba93672aa047`  
Historical prior-art repository: `auguspp/decision-os`

> If this handoff conflicts with current code or a newer merged Research artifact, current main wins. This file is operational context, not Kernel Constitution.

## 1. Product objective and authority boundary

The project is not `data -> AI score -> buy/sell`.

Canonical flow:

```text
Reality
  -> Harness claims/evidence
  -> Radar / Attention Allocation
  -> Research
  -> frozen ResearchSnapshot
  -> Observed Market
  -> Odds
  -> Decision Rehearsal
  -> Human Surface
  -> Human decides
```

Core semantics:

- `Kernel owns truth. Harness owns motion.`
- More precisely: Reality exists -> Harness gathers claims -> Kernel decides what is admissible.
- Kernel owns validated/admissible decision truth, not external-world truth.
- Radar allocates research attention; it is not a stock picker.
- Research != Recommendation.
- Odds != Recommendation.
- Human remains final Investment Decision Owner.
- `HumanResearchSurface.status + attention_eligible` remains the sole Human wake gate. Do not add another wake gate.
- Research Method is replaceable; Kernel Constitution is not.
- `Investment Authority = NONE` must remain explicit unless the Human changes it.

Quality bar:

> 少、真、静、可审计、不越权。

Engineering objective:

> 让现实进来，让垃圾消失，让真正改变决策上下文的东西留下来。

## 2. Non-negotiable implementation preferences

- Prefer direct action and small PR batches.
- Reuse > rebuild.
- Use Codex only when genuinely needed.
- Do not overstate maturity.
- Mature external tools should handle dirty mechanics; Web GPT/LLM handles semantic Research; Kernel guards admissibility/invariants; Human owns the investment decision.
- HiThink remains the sole production market-data source. Do not introduce provider/fallback abstraction.
- Never expose `HITHINK_FINANCE_API_KEY`.
- Do not add DB/repository/event-store/queue/provider frameworks unless forced by a real need.
- Do not create a second company-disclosure Radar/state machine.
- Temporary experiment PR/workflow is acceptable; close unmerged after reading the result.
- No automations unless the Human explicitly asks.

## 3. Research discipline recovered from Decision OS

This is now a hard Research preflight, especially after the GigaDevice correction:

1. Recover prior case lineage from `decision-kernel` and `decision-os` before inventing anything new.
2. Read current sell-side research / earnings forecasts **before scenario generation**.
3. Reconstruct the material expectation envelope, including serious bull and bear worlds.
4. Use official/company facts for historical economics and disclosure facts; sell-side is expectation context, not future truth.
5. Establish `driver -> transmission -> owner economics` before assigning probabilities.
6. Explicitly retain or reject material market worlds with evidence; never silently truncate them because preferred internal scenarios “feel reasonable.”
7. Every decision-relevant return claim needs an explicit horizon.
8. Valuation Map != numerical Odds without a supportable probability basis.
9. Evidence changes probability; price changes Odds.
10. If only price changes, freeze fundamental Belief and recompute price-dependent valuation/Odds only.
11. Avoid peak x peak constructions such as peak volume x peak ASP x peak margin x peak PE.
12. Good Research is allowed to lower conviction. It should make clear what must be true for capital to be committed.

Hard lesson from GigaDevice: **研报先行 is not optional.** Full Research v1 used an incomplete expectation envelope and repeated an error already documented in the old system.

## 4. Current production state

Current `decision-inbox.yml`:

- `workflow_dispatch`
- weekday cron `20 8 * * 1-5`
- timezone for disclosures: `Asia/Shanghai`
- production market data: HiThink only
- Node Actions already upgraded to current generations (`checkout@v7`, `setup-python@v7`, `upload-artifact@v7`, `cache@v6`)

Current Research-covered disclosure universe is six names:

- 贵州茅台 `600519`
- 宁德时代 `300750`
- 招商银行 `600036`
- 中国神华 `601088`
- 兆易创新 `603986`
- 三花智控 `002050`

Decision Inbox currently consumes `dogfood/*.json` plus the explicit current Full Research files:

- `research_cases/603986-gigadevice-deep-research-v2.json`
- `research_cases/002050-sanhua-deep-research-v1.json`

Disclosure Radar scans the same six-company Research-covered universe and remains a bounded sentry, not an all-A-share disclosure aggregator.

## 5. Disclosure receipt semantics

Production semantics id:

```text
research-funnel-v1
```

Receipt seen identity:

```text
(stock_code,
 exact announcement_ids,
 research_snapshot_id,
 research_as_of,
 assessment_semantics_id)
```

Meaning:

> The exact evidence batch + exact frozen Research context + exact assessment semantics has already been judged.

Important boundaries:

- model/provider/prompt provenance is NOT receipt identity;
- receipt memory is Harness attention memory, not epistemic truth;
- cache loss must cause reassessment/noise, never false silence;
- legacy unversioned receipts cannot suppress current semantics;
- scan does not itself save receipts;
- only the manual exact apply workflow can record a quiet receipt;
- `DEEPEN` remains unreceipted;
- disclosure assessment creates no Recommendation, Human wake, or investment authority.

## 6. Important merged work from this conversation

### PR #72 — quiet Odds explanation

Merged. Presentation-only change:

- quiet Inbox rows now explain why they are quiet;
- displays `ACCEPTABLE_ODDS` boundary;
- no Odds classification change;
- no wake-gate change;
- no recommendation logic.

Important semantic caution: `ACCEPTABLE_ODDS` must not automatically be called “first buy price.” Historical cases show it can correspond to a stronger zone.

### PR #73 — GigaDevice Full Research v2

Merged, `208 passed`.

File:

```text
research_cases/603986-gigadevice-deep-research-v2.json
```

v1 remains frozen and append-only; v2 supersedes it.

Core correction:

- fresh post-H1 sell-side 2027 estimates clustered roughly around CNY 14-18bn;
- v1's CNY 10bn base / CNY 13.5bn upside sat below much of the refreshed expectation cluster;
- this was an expectation-envelope error, not an arithmetic error.

Provisional/canonical v2 economics used in discussion:

- weighted terminal value about `CNY 436.52/share`;
- at the 2026-09-02 close `CNY 388.86`, expected undiscounted return about `+12.3%`;
- positive-return probability about `70%`;
- current live `VERY_HIGH` policy implies `ACCEPTABLE_ODDS` around `CNY 330.7`.

Human calibration from this conversation:

- at `CNY 388.86`, the Human would **not** buy a first position;
- market structure/regime was part of the reason, not a change in company Fundamental Belief;
- later, with the chart shown in chat, the Human said around the MA250/year-line region near `CNY 322` they would **consider** a first position because valuation Odds and long-cycle price structure overlap.

Crucial caveat: this is still a **hypothetical participation zone**. No actual buy has occurred. Do not overfit live policy to it.

### PR #76 — Sanhua Full Research v1

Merged, `211 passed`.

File:

```text
research_cases/002050-sanhua-deep-research-v1.json
```

Research framing:

- mature thermal-management core provides the economic floor;
- liquid cooling is commercially real but not yet separately material in disclosed economics;
- robot actuators moved into batch-delivery / production-ramp language, but unit economics remain unquantified;
- post-H1 2027 analyst forecasts cluster around roughly CNY 5.3-5.8bn;
- robot/liquid-cooling optionality is kept in explicit right-tail worlds, not Base.

Frozen 2027 scenario map:

| World | Probability | 2027 NP | Terminal PE | Terminal value/share |
| --- | ---: | ---: | ---: | ---: |
| Core slowdown | 15% | CNY 4.7bn | 24x | CNY 26.89 |
| Sell-side low | 25% | CNY 5.25bn | 25x | CNY 31.28 |
| Consensus core | 35% | CNY 5.5bn | 28x | CNY 36.71 |
| New-business success | 20% | CNY 6.5bn | 30x | CNY 46.48 |
| Robot right tail | 5% | CNY 8.5bn | 35x | CNY 70.91 |

Probability-weighted terminal value:

```text
CNY 37.5435/share
```

The downside multiple was deliberately revised from an overly harsh `20x` to `24x` so broad-market de-rating is not double-counted inside Fundamental Belief and again in participation context.

Historical/simple Web prior supplied by the Human:

- `30.5-32` first-participation consideration;
- `28-30` high-interest / higher-Odds zone;
- `<28` re-underwrite before considering heavier participation;
- A/H should be treated as one company Belief with separate market-expression Odds.

Again: these are **not revealed-preference trades**. The Human has not actually bought these levels yet.

## 7. Odds policy status — do not rush changes

Current live policy remains unchanged:

```text
expected-return thresholds: 20% / 35% / 55%
positive-return thresholds: 55% / 65% / 75%
model-risk add-ons: LOW 0, MEDIUM +3pp, HIGH +7pp, VERY_HIGH +12pp
OddsContext uncertainty add-ons: elevated +3pp, high +7pp
```

Current calculations are undiscounted nominal cumulative payoff, not annualized, even though valuation horizons can vary substantially.

Historical Decision OS evidence:

- old Dongshan operational proof used materially lower thresholds;
- Human-reviewed Dongshan participation bands were:
  - `165-170` first-participation candidate;
  - `150-160` attractive / high Odds;
  - `145-150` strong Odds with evidence re-check.
- its supplemental annualized hurdle map was roughly `10% -> 171`, `15% -> 161`, `20% -> 152`.

Experiments in this conversation:

- PR #74: live Odds calibration challenger — closed, unmerged.
- PR #75: GigaDevice market-regime Human calibration — closed, unmerged.
- PR #77: three-case Human participation challenger — closed, unmerged, `215 passed`.

What #77 established:

- a simple universal ~10% annualized hurdle does not reproduce all Human judgments;
- a simple 2:1 payoff-asymmetry rule is **not** universal;
- positive-return probability alone is not enough;
- current `ACCEPTABLE_ODDS` does not map consistently to exactly “first participation” or exactly “high Odds” across Dongshan, GigaDevice and Sanhua.

Most important latest Human guidance:

> Do **not** rush volatility/path-risk calibration. The Human has not actually bought any of these three names at the discussed zones, so the zones are still hypothetical preferences, not revealed behavior.

Therefore:

- do not fit a new volatility premium now;
- do not invent `HIGH_VOL + X%` or `bear market + Y%` parameters;
- do not change live Odds policy just to fit hypothetical zones;
- let real future buy/no-buy decisions create stronger calibration evidence.

## 8. Market-regime semantics

The Human explicitly distinguishes company Belief from market regime:

- weak broad-market structure can justify demanding a higher participation hurdle;
- this should not automatically lower company Fundamental Belief;
- technical claims such as monthly MACD/death-cross behavior are hypotheses/context until historically validated, not Kernel truth.

Do not encode technical-analysis heuristics into Kernel policy without a real evidence program.

## 9. Next requested task: Full Research on 圆通速递

The next conversation should continue with **圆通速递 / YTO Express (`600233`)**.

Do not start with a Bear/Base/Bull guess.

### Required preflight

1. Search both repositories for prior YTO material.
2. `decision-os` contains legacy/demo YTO artifacts such as:
   - `backend/fixtures/yto_demo.json`
   - `backend/fixtures/yto_phase2a_expected.json`
   Treat these as prior art/demo until inspected; do not assume they are current or canonical Research.
3. Read current sell-side reports / forecast revisions first and reconstruct the expectation envelope.
4. Then gather official-company facts and industry structure.
5. Only after that assign scenario probabilities.

### Research questions that likely matter

Focus on owner economics, not narrative:

- parcel volume growth and market share;
- single-parcel revenue / pricing pressure;
- single-parcel transportation, sorting and franchise-network cost trends;
- cost reduction versus service-quality tradeoff;
- industry competitive intensity and price-war behavior;
- capital expenditure, automation, hubs, aircraft/aviation and international assets;
- working capital and operating cash conversion;
- franchisee economics / network health;
- dividends, buybacks and capital-allocation discipline;
- whether international/aviation optionality is economically material or mostly narrative;
- consensus 2026-2028 earnings range and revisions;
- valuation regime appropriate for a mature logistics compounder versus a price-war cyclical.

Production ObservedMarket must still come from HiThink only. Public Web Research can use company filings, investor relations, industry sources and sell-side context.

### Deliverable discipline for YTO

A Full Research artifact should, at minimum:

- preserve prior-art lineage;
- show research-report expectation envelope before probabilities;
- separate FACT / MARKET_CONTEXT / INFERENCE / ASSUMPTION;
- state explicit falsifiers;
- include at least one serious downside and one serious upside world;
- keep horizon explicit;
- avoid giving market weakness twice through both terminal PE and a later participation overlay;
- produce Research Contract + Claim Audit + regression tests;
- remain Research, not Recommendation;
- do not add YTO to the production Research-covered universe until the Full Research package is frozen and inclusion is intentionally chosen.

## 10. Useful current files

Production / policy:

```text
.github/workflows/decision-inbox.yml
.github/workflows/apply-disclosure-assessment.yml
src/decision_kernel/policy_data/live_odds_v0_1.json
```

Current Full Research:

```text
research_cases/603986-gigadevice-deep-research-v1.json   # frozen prior
research_cases/603986-gigadevice-deep-research-v2.json   # current
research_cases/002050-sanhua-deep-research-v1.json       # current
```

Historical knowledge worth consulting in `decision-os`:

```text
docs/product/active-learnings.json
docs/philosophy/investment-doctrine-v1.md
docs/philosophy/doctrine-mapping.md
docs/product/decision-underwriting-workflow-v0.md
docs/cases/xiamen-tungsten-research-retrospective.md
docs/audit/2026-08-22-zhongji-innolight-underwriting-retrospective.md
docs/cases/dongshan-precision-002384/
docs/adr/ADR-008-policy-champion-challenger-governance.md
```

## 11. What the next conversation should NOT do

- Do not reopen live Odds policy as the first task.
- Do not fit policy parameters to the hypothetical GigaDevice/Sanhua participation zones.
- Do not call `CNY 322` or `CNY 31` a proven buy price.
- Do not turn MA250/MACD/death-cross ideas into Kernel truth without validation.
- Do not overwrite GigaDevice v1; lineage is append-only.
- Do not create a second Radar/wake gate/provider abstraction.
- Do not let sell-side forecasts become facts.
- Do not skip sell-side expectation-envelope reconstruction before YTO scenario design.
- Do not produce Recommendation, sizing, order or execution authority from Research.

## 12. Suggested first message/action in the next conversation

When the Human asks to continue YTO Research:

```text
先从两个 repo 恢复圆通 prior art，尤其检查旧 Decision OS 的 YTO demo/计算样例到底是 demo 还是真实历史判断；然后先读最新研报重建 2026-2028 expectation envelope，再进入官方经营事实和单票经济模型。先不碰 live Odds policy。
```

That is the intended restart point.
