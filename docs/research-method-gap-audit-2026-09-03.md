# Research Method Gap Audit — 2026-09-03

Status: **EXTERNAL-BENCHMARK AUDIT / METHOD RESEARCH / NO NEW KERNEL SCHEMA**  
Repository: `auguspp/decision-kernel`  
Investment Authority: **NONE**

## Executive verdict

Decision Kernel is already unusually strong on **epistemic hygiene**:

- PIT discipline;
- evidence / claim separation;
- Research / Odds / Human authority boundaries;
- explicit uncertainty and withholding;
- reference-frame correction;
- valuation-input underwriting;
- price-implied economics closure;
- prospective outcome capture.

The main remaining weakness is not another missing governance layer.

It is that the system still has more **discipline around research** than **empirical machinery inside research**.

External comparison suggests seven material gaps, ranked by expected value.

```text
1. outside-view / base-rate calibration
2. operating-driver + competitive-strategy underwriting
3. incremental ROIC / reinvestment accounting
4. systematic earnings-quality / accounting-signal analysis
5. forecast-error calibration and longitudinal learning
6. longitudinal disclosure / transcript / competitor-diff infrastructure
7. expectation-revision / catalyst mechanics
```

The first four are Research-quality gaps. The last three are evidence-acquisition / learning-system gaps.

---

## 1. Highest-priority gap — no systematic outside-view / reference-class calibration

### Current strength

Kernel is careful about model uncertainty and avoids guessed cardinal probabilities.

### Missing layer

For many variables we still rely on case-specific inside-view reasoning:

- how fast a new business ramps;
- how long elevated growth persists;
- how often high market share survives scale-up;
- margin fade after capacity expansion;
- probability of a sell-side success state;
- long-horizon analyst forecast error;
- ROIC fade after entering a new category.

What is missing is a reusable **empirical reference class**.

McKinsey's outside-view work explicitly argues that detailed bottom-up forecasts are commonly overoptimistic and that a reference class of comparable real-world outcomes is a core debiasing tool. Academic work on analyst forecasts also documents optimism that generally increases with forecast horizon.

Sources:
- https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/bias-busters-taking-the-outside-view
- https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/the-strategy-analytics-revolution
- https://academic.oup.com/rfs/article/36/6/2361/6782974
- https://link.springer.com/article/10.1007/s11142-021-09622-8

### Sanhua example

We can reverse CNY36.3 into a robot success-state scale, but we still cannot answer empirically:

> Among industrial suppliers at `batch delivery / line ramp`, how often does a new category reach the implied revenue, share, margin and ROIC within 3-5 years?

That is the missing outside view.

### Minimum useful next step

Do not create a probability engine.

Build small human-readable reference-class tables for repeated real cases:

```text
new-business commercialization
cycle-duration persistence
margin normalization
analyst 2Y / 3Y forecast error
incremental ROIC fade
```

Record medians / ranges / failure modes, not fake priors.

---

## 2. Competitive-strategy and operating-driver underwriting is still too shallow

### Current strength

Kernel now converts a price residual into future profit and, where possible, into volume / share / ASP / margin.

### Missing layer

The bridge often uses external scenario assumptions without independently underwriting each operating variable.

Expectations Investing explicitly treats competitive strategy as central because expectations revisions ultimately come through sales, cost, investment and competitive dynamics. Public equity-research skill sets also explicitly require market structure, share trends, how firms compete, disruption risk, and competitive-positioning maps.

Sources:
- https://www.jstor.org/stable/10.7312/maub20304.9
- https://www.jstor.org/stable/10.7312/maub20304.10
- https://github.com/anthropics/financial-services/blob/main/plugins/vertical-plugins/equity-research/skills/sector-overview/SKILL.md

### Sanhua example

The current robot bridge uses a sell-side success-state:

```text
1m units
x CNY50k value / robot
x 70% Sanhua share
x 10% net margin
= CNY3.5bn profit
```

We have correctly labelled this as a scenario, but we have **not independently underwritten**:

- why CNY50k remains the right mature value content;
- which actuator components Sanhua actually owns versus sources;
- whether price erosion changes that value content;
- why 70% share is sustainable after second-sourcing / localization;
- what manufacturing yield / utilization is needed for 10% net margin;
- who the serious competing suppliers are by component;
- customer bargaining power at scale;
- how much capex is required for 1m-unit economics.

Company disclosure confirms batch delivery / production-line ramp but does not provide those mature operating economics.

Sources:
- https://paper.cnstock.com/html/2026-08/27/content_2260681.htm
- https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12563691&stockid=002050

### Minimum useful next step

For any load-bearing new business, require one case-specific competitive map before using a success-state economically:

```text
product / component architecture
→ competing suppliers
→ customer qualification / second-source structure
→ value content and price-down path
→ capacity / yield / utilization
→ share
→ margin
→ capital intensity
```

No new Kernel entity is needed.

---

## 3. Incremental ROIC and reinvestment are named, but not yet operationalized consistently

### Current strength

The repo repeatedly recognizes that growth is not enough and that owner economics depend on incremental ROIC, cash conversion and capital intensity.

### Missing layer

There is no consistent cross-case calculation discipline for:

- maintenance versus growth capex;
- working-capital investment;
- capitalized R&D / internally developed intangibles where relevant;
- acquisition capital;
- incremental invested capital by growth pool;
- incremental NOPAT / owner earnings generated by that capital;
- fade in return on incremental capital.

Damodaran explicitly derives fundamental growth from reinvestment rate × return on capital. McKinsey likewise emphasizes that growth creates value only when returns on invested capital justify it. Mauboussin's ROIC work stresses that positive earnings do not necessarily imply value creation.

Sources:
- https://pages.stern.nyu.edu/adamodar/New_Home_Page/invemgmt/assetsel.htm
- https://pages.stern.nyu.edu/~adamodar/New_Home_Page/Inv4ed.htm
- https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/balancing-roic-and-growth-to-build-value
- https://www.morganstanley.com/im/publication/insights/articles/article_returnoninvestedcapital.pdf

### Sanhua example

The company explicitly says future capital expenditure will fund domestic expansion, automation, overseas capacity, robotics and liquid cooling. Yet the robot success-state valuation currently focuses mainly on profit, with only a qualitative warning about required capital.

Source:
- https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?CompanyCode=10001452&gather=1&id=12433636

### Minimum useful next step

For any growth story that carries material price value, add a simple owner-economics bridge:

```text
incremental revenue
→ incremental operating profit / NOPAT
→ working capital
→ growth capex + capitalized development burden
→ incremental invested capital
→ incremental ROIC
→ owner cash
```

If capex allocation cannot be separated, say `NOT ESTABLISHED` rather than treating accounting profit as value creation.

---

## 4. Financial-statement analysis is not yet systematic enough

### Current strength

Individual cases inspect cash conversion, inventory, margins, FX, capex and accounting scope when they become visibly important.

### Missing layer

There is not yet a standard multi-year accounting-signal pass that asks whether the income statement is being confirmed or contradicted by the balance sheet and cash-flow statement.

Classic fundamental-analysis research links detailed signals such as inventory, receivables, gross margin, selling expense, capex, tax rate and labor productivity to future earnings and analyst revisions. Accrual-reliability research shows that less reliable accrual components are associated with lower earnings persistence.

Sources:
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=40740
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=105748
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=521062

Open-source research agents increasingly include five-year statement extraction, DuPont decomposition, ratio histories and rule-based earnings-quality red flags rather than relying only on narrative retrieval.

Sources:
- https://github.com/irenethebest/financial-statement-analysis-agent
- https://github.com/kherarudransh-oss/financial-research-agent

### Minimum useful next step

A Full Research pass should normally produce a compact 5-year / 8-quarter diagnostic for the variables that matter to the economic species:

```text
revenue / volume proxies
margin bridge
receivables
inventory
payables
contract liabilities where relevant
OCF / EBITDA / net income conversion
capex / depreciation
R&D
share count / dilution
net debt / cash
segment mix
```

Not all variables need to become Kernel state. The point is to make contradiction detection routine rather than case-triggered.

---

## 5. We have prospective outcome capture, but almost no forecast-error calibration history yet

### Current strength

The repository already has prospective decision / outcome capture discipline. That is the correct foundation.

### Missing layer

Because the system is young, there is not yet enough longitudinal data to answer:

- how optimistic our 2Y / 3Y earnings assumptions are;
- which economic species we systematically mis-model;
- whether sell-side consensus is more accurate than our independent model at different horizons;
- whether our chosen valuation ranges are too wide / narrow;
- which claimed falsifiers actually discriminate outcomes;
- whether Research challenges improve subsequent error.

This matters because analyst-forecast research repeatedly finds horizon-dependent bias and inefficiency. A research system should therefore learn from its own forecast errors, not just preserve the original reasoning.

Sources:
- https://academic.oup.com/rfs/article/36/6/2361/6782974
- https://link.springer.com/article/10.1007/s11142-021-09622-8
- https://link.springer.com/article/10.1007/s11156-020-00902-z

### Minimum useful next step

Do not create a score leaderboard yet.

At each realized annual / quarterly checkpoint, preserve:

```text
forecast made at PIT
actual outcome
error magnitude
error source:
  frame / earnings scope / duration / margin / volume / share / capital / valuation
whether consensus was better or worse
whether a stated falsifier fired
```

After enough observations, then earn calibration statistics.

---

## 6. Evidence lineage is strong; longitudinal evidence acquisition is still manual and episodic

### Current strength

Kernel has excellent claim lineage and authority separation.

### Missing layer

External open-source systems increasingly automate:

- filing ingestion;
- section-aware retrieval;
- multi-period statement extraction;
- earnings-call / transcript ingestion;
- section-to-section disclosure changes;
- competitor mapping;
- supply-chain analysis;
- retrieval evaluation and re-retrieval when confidence is weak.

Examples:
- https://github.com/smadinen7/financial-research-agent
- https://github.com/twCarllin/10k-analysis
- https://github.com/lucasastorian/intellifin-agent
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces

The lesson is not to copy their multi-agent architecture. The useful part is **coverage completeness and longitudinal diffing**.

### China-specific implication

For A/H coverage, the analogous evidence surface should eventually include repeatable ingestion / diffing across:

```text
annual / interim reports
exchange announcements
IR activity records
earnings presentations
major peer disclosures
sell-side expectation revisions
```

This is an acquisition-layer improvement, not a new Fundamental Belief engine.

---

## 7. Price-implied expectations are now strong, but expectation-revision mechanics remain weak

### Current strength

Kernel now asks what the current price requires and closes residual value into business requirements.

### Missing layer

High-level equity research also asks:

> Which **specific evidence** is capable of changing those embedded expectations, and by how much?

Expectations Investing calls for identifying the value trigger with the greatest impact and then analyzing the competitive / operating developments that could cause an expectations revision. Institutional research workflows similarly maintain thesis trackers, model updates and catalyst calendars.

Sources:
- https://www.jstor.org/stable/10.7312/maub20304.8
- https://www.jstor.org/stable/10.7312/maub20304.10
- https://github.com/anthropics/financial-services

### Boundary

This does **not** mean turning Kernel into a trading signal engine.

A Research-safe version is simply:

```text
price-implied requirement
→ load-bearing uncertain variable
→ evidence event that can materially resolve that variable
→ expected Research update direction if observed
```

Sanhua already has the beginnings of this with robot volume / ASP / margin / utilization / capital intensity. The missing piece is consistently ranking which one or two disclosures would matter most to the valuation surface.

---

# What is *not* the main gap

External GitHub projects often emphasize multi-agent orchestration, sentiment agents, technical indicators, report generation and autonomous recommendations.

Those are **not** the highest-value missing pieces for Decision Kernel.

Kernel already has a stronger authority / evidence design than many public research-agent repositories. Adding more agents, a vector database, technical indicators or automatic BUY/HOLD/SELL output would increase machinery without fixing the main weakness.

The main weakness is empirical depth:

```text
company evidence
→ operating economics
→ competitive structure
→ reinvestment requirement
→ owner economics
→ outside-view calibration
→ price-implied requirements
→ realized forecast error
```

---

# Recommended order of work

Do not build seven systems at once.

The highest-return sequence is:

## Phase A — use Sanhua to deepen one real case

1. independently underwrite robot component architecture / value content / competitors / second sourcing;
2. underwrite the 70% share assumption rather than merely citing it;
3. build a capacity / capex / utilization / margin bridge for robot success states;
4. map liquid-cooling current embedded economics versus future incremental economics;
5. build 2-3 relevant industrial commercialization reference classes.

## Phase B — upgrade Full Research checklists only after the work earns them

Potential earned additions:

- outside-view / reference-class check;
- financial-statement contradiction panel;
- incremental-ROIC bridge;
- competitive-structure / operating-driver check.

Keep them docs/process-only until repeated cases prove a schema need.

## Phase C — learn longitudinally

Use realized outcomes to measure where Research was wrong.

No framework expansion should substitute for this evidence.

---

# Bottom line

Decision Kernel's next leap is not from `good framework` to `more framework`.

It is from:

> **auditable reasoning about public information**

to:

> **independently reconstructed business economics, calibrated against real base rates and later outcomes.**

The Sanhua case is currently strongest on valuation hygiene and weakest on independent underwriting of the robot / liquid-cooling operating economics that must justify the prepaid future.