# Research Method External Benchmark — 2026-09-03

Status: **EXTERNAL BENCHMARK / GAP AUDIT / DOCS ONLY / NO SCHEMA CHANGE**  
Repository: `auguspp/decision-kernel`  
Investment Authority: **NONE**

## Purpose

Decision Kernel is already relatively strong at **Research hygiene**:

- PIT-bounded evidence and immutable snapshots;
- claim-level source admissibility;
- explicit separation of record / interpretation / expectation;
- pre-expectation underwriting before consensus reconstruction;
- visible uncertainty and probability withholding;
- price-implied reverse underwriting;
- Human investment authority preserved outside the Kernel.

The Sanhua dogfood nevertheless exposed an important distinction:

> **Research hygiene can be strong while research penetration is still mediocre.**

This benchmark asks what capabilities are still missing if the goal is not merely an auditable report, but a materially better understanding of owner economics and the future requirements embedded in price.

This note compares current practice with:

1. public academic / practitioner research on forecasting, valuation and base rates;
2. public sell-side Sanhua research;
3. open-source financial-research systems on GitHub.

It is a gap audit, not a request to copy their architectures.

---

## 1. Existing strengths that should not be replaced

### 1.1 Research Method already separates inside view, expectation and price

Current method already has the right epistemic sequence:

```text
Observed / Reported Record
→ causal underwriting
→ pre-expectation view
→ published-expectation reconstruction
→ anchoring / gap audit
→ post-expectation belief
→ price-implied worlds
```

This is stronger for Decision Hygiene than simply asking an agent to produce a report or a target price.

### 1.2 Economic uncertainty is routed by economic species

The current playbook already distinguishes:

- model-class uncertainty;
- duration / normalization uncertainty;
- continuous reinvestment / owner-return uncertainty;
- network / economic-ownership uncertainty;
- qualified core + immature optionality;
- resource / commodity frame risk.

The problem is therefore **not** that ROIC, owner cash, duration or base rates are absent from the vocabulary.

The problem is that several of them are not yet **measured and calibrated consistently enough** to constrain the answer.

### 1.3 Sanhua fixed a real valuation failure

The current Full Research gate now requires:

```text
observable earnings scope
→ independently underwritten valuation bridge
→ no profit/multiple double reward
→ fundamental vs market-expression separation
→ visible uncertainty
→ reverse current price
```

The Gate 6 extension further requires:

```text
base
→ residual
→ required future economics
→ operating bridge
→ discounted value
→ observed-price closure
```

This should remain.

---

## 2. External benchmark — what mature research frameworks emphasize

## 2.1 Base rates before heroic inside-view forecasts

Michael Mauboussin and Dan Callahan's 2026 `Bayes and Base Rates` work argues that forecasting should start with the outcome distribution of a suitable reference class and then update with case-specific evidence. Their examples use long historical datasets of public-company growth and project completion rather than allowing a compelling company narrative to define the prior.

Sources:
- https://www.morganstanley.com/im/en-sg/institutional-investor/insights/consilient-observer/bayes-and-base-rates.html
- https://www.morganstanley.com/im/publication/insights/articles/article_bayesandbaserates2_ltr.pdf

**Gap exposed:** Decision Kernel names `base rate` and often correctly says `INSUFFICIENT`, but it does not yet maintain reusable reference-class evidence for common underwriting questions.

Examples we currently lack as reusable outside-view challengers:

- revenue-growth persistence by company size / maturity / industry economics;
- margin and ROIC fade after unusually strong periods;
- new-product / new-factory ramp time and miss distributions;
- market-share persistence after technology transitions;
- large-cap industrial adjacency success rates;
- project completion / capex timing slippage.

Without this layer, our scenario ranges remain more inside-view than they appear.

---

## 2.2 Growth must be financed by reinvestment and earned at a return

Damodaran's fundamental growth identity is:

```text
Expected operating-income growth
≈ reinvestment rate × return on capital on future investment
```

He distinguishes average return on capital from the **marginal return on new capital** and ties stable growth to the reinvestment necessary to create it. Terminal growth cannot be increased for free: higher growth also consumes more cash unless excess returns remain attractive.

Sources:
- https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/growth.htm
- https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/terminalvalue.htm

McKinsey reaches the same economic point from a value-creation lens: economic profit and ROIC are more directly linked to value creation than EPS alone, and 2026 investor-survey results again emphasize capital-allocation / ROIC discipline.

Sources:
- https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/which-metrics-really-drive-total-returns-to-shareholders
- https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/what-matters-most-to-investors-in-2026-and-what-it-means-for-companies

**Gap exposed:** current Research often mentions capex, OCF, owner cash and ROIC, but many forecasts still travel mechanically through:

```text
revenue
→ margin
→ net profit
→ P/E
```

rather than consistently through:

```text
volume / revenue
→ NOPAT
→ incremental invested capital
→ marginal ROIC
→ reinvestment required for the growth
→ owner cash / economic profit
→ value
```

For capital-intensive industrial adjacencies, this is a major missing bridge.

---

## 2.3 Duration should be modeled as competitive-advantage fade, not only a higher multiple

Mauboussin / Callahan's 2026 `Competitive Advantage Period` work frames value creation through three things:

```text
ROIC spread over cost of capital
× amount of capital that can be reinvested
× duration of the positive spread
```

It also emphasizes regression toward the mean, business life cycle, and **market-implied competitive advantage period**.

Source:
- https://www.morganstanley.com/im/en-sg/institutional-investor/insights/consilient-observer/the-neglected-value-driver.html

**Gap exposed:** Decision Kernel already talks about `duration`, but duration is often expressed qualitatively or indirectly through a terminal P/E.

A stronger Research surface would sometimes ask explicitly:

```text
current / incremental ROIC
→ fade path toward reference-class economics
→ how long excess returns persist
→ market-implied duration at the observed price
```

This is especially useful when debating `18x vs 28x`: the question becomes what **duration of excess economics** justifies the difference, rather than which P/E looks familiar.

---

## 2.4 Mean reversion and growth persistence need to be default challengers

Fama and French document strong mean reversion in profitability in historical U.S. data. Their exact historical coefficient should **not** be transplanted to China or used as a universal constant, but the empirical lesson is important: extraordinary profitability should face a mean-reversion challenger by default.

Source:
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=40660

Chan, Karceski and Lakonishok find that very high long-term growth does occur but is rare, long-term growth persistence is weak in their historical sample, and I/B/E/S long-term growth forecasts are overly optimistic with low predictive power.

Source:
- https://www.nber.org/papers/w8282

**Gap exposed:** our research can build a well-reasoned five-year growth path without forcing itself to answer:

> How unusual is this path in the relevant reference class, and what rate of fade should be the default challenger before company-specific evidence earns an exception?

The correct fix is not to copy U.S. historical coefficients. It is to build the outside-view question into the research process and collect suitable data where possible.

---

## 2.5 Sell-side consensus needs a statistical challenger, not only a source-role audit

Decision Kernel already treats sell-side research mainly as Market Belief / hypothesis / information map. That is good, but it does not eliminate forecast bias.

Academic evidence provides several useful warnings:

- Dechow, Hutton and Sloan document systematic optimism in sell-side long-term growth forecasts in an equity-offering setting.
- Hou, van Dijk and Zhang show that cross-sectional earnings models can reduce forecast bias and improve coverage relative to analyst forecasts in their historical U.S. sample.
- Azevedo, Bielstein and Gerhart show that combining analyst estimates with a cross-sectional model can improve the bias/accuracy trade-off versus either source alone.
- Ham, Kaplan and Lemayian show that forecast incentives and inefficiency differ across forecast horizons; longer-horizon forecasts face different optimism/accuracy incentives.

Sources:
- https://onlinelibrary.wiley.com/doi/10.1111/j.1911-3846.2000.tb00908.x
- https://ideas.repec.org/a/eee/jaecon/v53y2012i3p504-526.html
- https://link.springer.com/article/10.1007/s11156-020-00902-z
- https://link.springer.com/article/10.1007/s11142-021-09622-8

**Gap exposed:** we currently reconstruct consensus carefully but do not usually put next to it a disciplined independent challenger such as:

```text
sell-side consensus
vs
simple historical / persistence baseline
vs
reference-class / cross-sectional baseline
vs
our causal driver model
vs
price-implied requirement
```

That makes us less anchored than before, but not yet genuinely de-biased.

---

## 3. Public Sanhua sell-side research — where it is deeper than our current desk research

Recent public Sanhua reports are not automatically more correct than our Research. They are useful because they expose the **granularity** professional analysts attempt to model.

Examples:

- Dongwu explicitly turns a robot success case into `industry units × actuator value/robot × Sanhua share × margin`.
- Zheshang publishes product-market-share and business-segment assumptions and pushes into AIDC liquid cooling and robot component value chains.
- CITIC Construction treats liquid cooling as already contributing incremental economics rather than as a wholly separate untouched option.

Public references:
- Dongwu H1 commentary: https://stock.finance.sina.com.cn/stock/go.php/vReport_Show/kind/search/rptid/841165869756/index.phtml
- Zheshang deep report summary: https://stock.finance.sina.com.cn/stock/go.php/vReport_Show/kind/lastest/rptid/835208520214/index.phtml
- CITIC Construction H1 commentary: https://stock.finance.sina.com.cn/stock/go.php/vReport_Show/kind/search/rptid/841477655686/index.phtml
- Company 2026H1 filing: https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12550185&stockid=002050
- Company investor Q&A: https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12563691&stockid=002050

### What we still have not underwritten deeply enough in Sanhua robot

The current `35亿元` robot case is useful for **price scale**, but it still depends on several large assumptions:

```text
robot industry / customer volume
× joint / actuator architecture
× Sanhua supplied content per robot
× ASP / price-down path
× sustainable customer share
× gross / operating / net margin
× utilization
× working capital
× capex / incremental invested capital
→ incremental ROIC / owner cash
```

Current Research has not independently established the robustness of `CNY50k`, `70% share` or `10% net margin` across a realistic scaled industry state.

That means:

> We have successfully reverse-underwritten what CNY36.3 requires, but we have **not yet done enough industry work to say how plausible the required robot economics are.**

This is the most important remaining Sanhua Research gap.

### Liquid cooling has the same problem

Current evidence proves commercial supply, and observable refrigeration economics may already contain some liquid-cooling contribution.

But a deep owner-economics model would still want:

```text
addressable deployment unit (rack / MW / CDU / loop)
× content value by product
× customer procurement / qualification path
× company share
× price-down
× margin
× capex + working capital
→ incremental owner economics
```

The current proof ladder is correct; the missing piece is quantitative industrial economics behind each rung.

---

## 4. GitHub benchmark — useful engineering ideas, but not investment authority

## 4.1 OpenBB

`OpenBB-finance/OpenBB` is primarily a broad data platform for analysts, quants and AI agents.

Repository:
- https://github.com/OpenBB-finance/OpenBB

Useful lesson:

> Research depth is constrained by standardized access to historical financial, market and economic data.

But provider breadth is not itself a research method and is not a current Decision Kernel priority.

## 4.2 FinRobot

`AI4Finance-Foundation/FinRobot` separates deterministic numerical computation from LLM narration and exposes explicit modules for forecasting, sensitivity analysis, peer comparison and valuation.

Repository:
- https://github.com/AI4Finance-Foundation/FinRobot

Useful lesson:

```text
numbers are calculated deterministically
narrative is LLM-assisted
numeric outputs retain provenance
```

Decision Kernel already has strong provenance semantics, but it lacks the same breadth of deterministic **financial-model operators** for recurring owner-economics calculations.

What should **not** be copied automatically:

- multi-agent debate for its own sake;
- automatic BUY / SELL style conclusions;
- Monte Carlo before probability calibration;
- generic DCF merely because a DCF engine exists.

## 4.3 ai-hedge-fund v2

`virattt/ai-hedge-fund` emphasizes point-in-time data during historical replay and uses the same cycle path for current runs and backtests. It also plans explicit backtest-overfitting validation.

Repository:
- https://github.com/virattt/ai-hedge-fund

Useful lesson for us is **not trading backtests**.

It is:

> A PIT research system should eventually be able to replay what its forecasts actually said at the time and compare them with later realizations.

Decision Kernel freezes snapshots and has a prospective Human Decision/Outcome protocol, but it does not yet have a simple longitudinal **Research Forecast Ledger** for the underlying driver forecasts themselves.

---

# 5. Gap ranking

## Tier 1 — highest-value missing capabilities

### Gap 1 — reusable reference classes / base rates

Current state:

```text
conceptually understood
case-by-case base-rate comments exist
reusable empirical reference classes = weak
```

Needed capability:

- select the appropriate outside-view reference class;
- show its historical distribution / range when data quality permits;
- then explain why company-specific evidence should move away from it.

This should be a **challenger**, not a prior that overrides causal company Research.

### Gap 2 — forecast calibration and PIT replay

We do not yet routinely preserve and later score:

- revenue forecasts;
- unit volumes;
- ASP;
- margin;
- market share;
- capex;
- cash conversion;
- marginal ROIC;
- valuation-duration assumptions.

A Research system that cannot later say **which driver it forecast badly** will improve slowly.

Needed first step is a docs-first ledger, not a backtesting platform.

Example:

| PIT | Case | Variable | Horizon | Forecast / range | Realized later | Error type |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-09-03 | Sanhua | robot annual volume | 2030 success-state reference | conditional only | pending | pending |
| 2026-09-03 | Sanhua | 2027 observable-base profit | 2027 | 47–51亿元 | pending | pending |

Only after enough observations exist should calibration machinery be considered.

### Gap 3 — quantified marginal-ROIC / reinvestment bridge

For every material growth pool, Research should be able to ask:

```text
What new capital must be invested?
What incremental NOPAT / owner cash does it produce?
What marginal ROIC does that imply?
How does ROIC change as scale rises and price falls?
```

This is more decision-useful than a generic `revenue CAGR + net margin` table.

### Gap 4 — competitive-advantage duration / fade

For premium valuation, we need more than `quality is good`.

Where material, Research should model a bounded challenger for:

- excess ROIC / margin fade;
- share durability;
- reinvestment runway;
- life-cycle maturity;
- price-implied duration of the excess economics.

This is the missing bridge between business quality and terminal multiple.

### Gap 5 — independent statistical challenger to consensus

Do not replace analysts with a regression model.

Instead triangulate:

```text
inside-view causal forecast
+ sell-side consensus
+ simple outside-view / statistical baseline
+ historical forecast error
+ price-implied requirement
```

A disagreement among these surfaces is Research attention, not an automatic thesis change.

---

## Tier 2 — important depth gaps, but more case-specific

### Gap 6 — industry / value-chain granularity

For a genuinely load-bearing new business, Research needs product-level economics rather than only TAM and customer names.

For Sanhua robot, the main current unresolved variables are:

- architecture / components actually supplied;
- per-unit content and future price-down;
- realistic dual-source / in-house risk;
- achievable long-run share;
- yield / utilization;
- manufacturing cost curve;
- capex throughput;
- working-capital burden;
- incremental ROIC.

### Gap 7 — accounting normalization and capital allocation are not uniformly first-class

Depending on the case, owner economics should explicitly reconcile:

- maintenance vs growth capex;
- R&D capitalization logic;
- leases;
- working capital;
- acquisitions / goodwill;
- minority economics;
- tax normalization;
- dilution / issuance / genuine share cancellation;
- cash trapped or economically unavailable to owners.

Some existing cases do this well. It is not yet consistent across Full Research.

### Gap 8 — management and analyst forecast track record

Claim-level source admissibility should remain authoritative.

Separately, it is useful context to know:

- how prior management targets realized;
- how a sell-side house's estimates moved over time;
- whether optimism / conservatism is persistent in the exact forecast type.

Do **not** convert this into one global source credibility score.

---

# 6. What to do next — smallest experiments

Do not implement eight new systems.

The highest-value next dogfood is three narrow experiments.

## Experiment A — Sanhua outside-view / base-rate challenger v0

Question:

> How unusual are the growth, share, profitability and ramp assumptions required by CNY36.3?

Possible reference classes:

- mature high-quality industrial component companies sustaining premium ROIC;
- industrial adjacency launches moving from qualification to material profit;
- large capacity ramps / manufacturing projects;
- suitable robotics component peers only where the economic comparability is real.

Output can remain ordinal / bounded if the reference class is weak.

No fake `robot success probability` is required.

## Experiment B — Research Forecast Ledger v0

Start manually with existing frozen cases:

- Sanhua;
- GigaDevice;
- Micron;
- YTO.

Freeze only a few load-bearing variables and their intended resolution horizons.

Do not score performance before outcomes exist.

## Experiment C — Sanhua incremental-owner-economics bridge

Take the existing robot success state and explicitly test:

```text
volume
× content / ASP
× share
→ revenue
→ gross / operating profit
→ NOPAT
→ working capital + fixed capital required
→ incremental ROIC
→ cash conversion
```

Repeat only as far as public evidence permits.

If capex, utilization, price-down or unit-cost evidence cannot be established, say so. That missing evidence is itself a more useful conclusion than another neat valuation table.

---

# 7. What not to build now

External projects contain attractive machinery that is not currently earned by Decision Kernel evidence.

Do not add merely because competitors have it:

- generic multi-agent bull/bear voting;
- an automatic DCF / Monte Carlo target-price engine;
- an AI BUY/SELL layer;
- a provider registry / failover platform for its own sake;
- historical trading backtests as a proxy for Research quality;
- a global analyst credibility score;
- forced numerical success probabilities.

The immediate research bottleneck is **economic understanding and calibration**, not orchestration.

---

# 8. Bottom line

The strongest current diagnosis is:

```text
Decision Hygiene = relatively strong
Research penetration = inconsistent
```

The next quality jump is unlikely to come from more stages or schemas.

It should come from three habits becoming empirically harder:

```text
OUTSIDE VIEW
reference class / base rate

OWNER ECONOMICS
marginal ROIC + reinvestment + cash conversion

CALIBRATION
freeze forecasts → observe outcomes → attribute errors
```

Then keep the current price discipline:

```text
business economics
→ future requirements
→ price-implied burden
```

A useful standard for future Full Research is therefore:

> **Can the Research explain the economic machine, challenge its inside view with a relevant outside view, and later tell exactly which forecast was wrong?**

Until all three improve, a more elaborate scenario table will mostly make the same Research look more professional rather than make it more accurate.
