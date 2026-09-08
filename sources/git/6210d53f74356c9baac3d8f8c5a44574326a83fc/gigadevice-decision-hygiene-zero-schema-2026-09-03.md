# GigaDevice Decision Hygiene Dogfood — Zero-Schema / Partial Probability Qualification

Status: **FROZEN DOGFOOD / RESEARCH METHOD EXPERIMENT / NO KERNEL OR ODDS POLICY CHANGE**  
Security: **兆易创新 / GigaDevice / 603986.SH**  
Method note: `docs/decision-hygiene-method-note-2026-09-03.md`  
Public evidence cutoff: **2026-09-02 close / sources available by 2026-09-02**  
Recorded: **2026-09-03**

## Purpose

This is the second zero-schema Decision Hygiene dogfood after YTO.

The experiment deliberately asks a different question from the existing GigaDevice Full Research v2:

> Can Research be complete enough to stop at the current PIT while supporting only an ordinal / partial probability judgment rather than a decision-grade cardinal probability measure?

It does **not**:

- change Kernel Constitution;
- add schema, enums, state machines, or probability-readiness fields;
- change `ResearchSnapshot`, Kernel `Scenario`, live Odds, or production policy;
- rewrite or delete GigaDevice Full Research v2;
- remove GigaDevice from the current production Inbox;
- treat public price as a Fundamental Belief input;
- issue a Recommendation or Human investment decision.

The existing GigaDevice v2 remains a frozen counterfactual baseline. Its `10/20/30/30/10` probability distribution, scenario values and any downstream deterministic Odds remain historically auditable. This dogfood asks whether the exact probability measure is methodologically qualified, not whether its arithmetic is correct.

---

## 1. Method verdict first

Current-PIT verdict:

```text
REFERENCE FRAME = HYBRID / PARTIALLY RESOLVED
CAUSAL WORLD COVERAGE = SUFFICIENT FOR CURRENT PUBLIC PIT
DECISION-CRITICAL UNCERTAINTIES = IDENTIFIED
PUBLISHED EXPECTATION RECONSTRUCTION = MATERIAL / MATCHED PANEL AVAILABLE
PRICE-IMPLIED WORLD SURFACE = CONSTRUCTED AS CHALLENGER ONLY
RESEARCH COMPLETENESS = COMPLETE ENOUGH TO STOP CURRENT PUBLIC-DILIGENCE LOOP
PROBABILITY QUALIFICATION = PARTIALLY ESTABLISHED
CARDINAL PROBABILITY MEASURE = NOT ESTABLISHED
NUMERICAL ODDS = NOT METHOD-READY IN THIS DOGFOOD
HUMAN ATTENTION VALUE = YES
INVESTMENT AUTHORITY = NONE
```

The key result is therefore different from YTO:

> **Research can establish useful ordinal probability constraints without establishing a full numerical probability measure suitable for deterministic Odds.**

This is still only a second dogfood result. It is not sufficient evidence to amend Kernel Constitution.

---

## 2. Existing frozen baseline — do not rewrite it

Current repository Full Research v2 is intentionally preserved.

It uses five Kernel `Scenario` objects:

| Existing v2 scenario | Probability | Terminal equity value / share |
| --- | ---: | ---: |
| `rapid_normalization` | 10% | CNY203.06 |
| `partial_normalization` | 20% | CNY310.08 |
| `research_low_core` | 30% | CNY427.79 |
| `research_high_core` | 30% | CNY538.65 |
| `right_tail` | 10% | CNY642.68 |

The frozen probability-weighted terminal value is **CNY436.5220/share**.

Full Research v2 also reconstructed a fresh post-H1 2027 sell-side expectation sample around:

```text
min     CNY13.977bn
median  CNY16.868bn
max     CNY17.872bn
```

That was a meaningful improvement over v1, whose earnings-state space had been too narrow.

This dogfood does not dispute those facts. It changes the research question:

> Did the evidence justify the exact `10/20/30/30/10` probability measure, or did the Kernel requirement to probabilize and value every scenario encourage more precision than the PIT information supports?

---

## 3. PIT-bound record — what is actually observed

The following are reported records / observations, not claims about sustainable economics.

### 2026H1 company record

The formal H1 filing reports:

- revenue **CNY11.566bn / 115.66亿元**, +178.67% YoY;
- parent net profit **CNY6.857bn / 68.57亿元**, +1,091.50%;
- deducted parent net profit **CNY4.883bn / 48.83亿元**, +796.90%;
- operating cash flow **~CNY6.048bn / 60.48亿元**;
- storage revenue **CNY9.827bn / 98.27亿元**, +245.44%;
- storage gross margin **67.57%**;
- MCU revenue **CNY1.430bn / 14.30亿元**, +49.07%;
- MCU gross margin **38.49%**;
- analog revenue **~CNY0.191bn / 1.91亿元**, gross margin ~40.50%;
- sensors revenue **~CNY0.100bn / 1.00亿元**, down materially YoY, gross margin ~19.60%.

Q2 alone reported revenue around **CNY7.378bn / 73.78亿元**, parent NP around **CNY5.396bn / 53.96亿元**, deducted NP around **CNY3.473bn / 34.73亿元**, and group gross margin **66.57%**.

The difference between H1 reported and deducted parent profit was about **CNY1.974bn**, and the filing identifies material financial-asset fair-value / disposal gains. These gains are observed earnings but are not treated as recurring operating economics.

### Headline H1 earnings were substantially preannounced

On 2026-07-09 after market close, the company preannounced approximately:

```text
H1 revenue          ~CNY11.5bn / 115亿元
parent NP           ~CNY6.9bn / 69亿元
deducted parent NP  ~CNY4.85bn / 48.5亿元
```

The formal H1 print therefore did **not** newly reveal the +1,091% headline profit growth. It mainly added detailed business mix, margins, cash-flow composition and operating disclosures.

### The company itself preserves the cycle warning

The 2026-06-30 company risk warning states that:

- the memory industry has historically shown significant cyclicality;
- product prices were already at historical highs;
- continued large price increases are not sustainable indefinitely;
- supply and demand ultimately move toward rebalance;
- niche-memory downstream demand is relatively stable and can be suppressed by rapid price increases;
- later marginal capacity additions can produce significant price declines;
- as a fabless company, GigaDevice also faces upstream wafer-capacity availability risk.

This is important because it prevents Research from silently converting a supply-shortage observation into a permanent high-margin model class.

### Independent industry context confirms both scarcity and a normalization path

TrendForce independently reported in June/July 2026 that:

- NOR Flash and SLC NAND contract prices had risen more than 100% in 1H26;
- mature-node capacity was being squeezed as large memory vendors prioritized HBM and advanced NAND;
- SLC NAND shortages were severe and 2H26 price increases could remain very large;
- long-lifecycle industrial/automotive qualification reduces customers' substitution flexibility.

But the independent picture is not a single permanent shortage world:

- price momentum already showed product-level divergence and buyer resistance;
- lower-density NOR could stabilize as Chinese capacity enters;
- TrendForce expects overall NAND supply constraints to begin easing in **2H27** as bit-supply growth catches up;
- DRAM and NAND supply-demand paths may diverge materially in 2027.

Therefore `memory cycle` is itself too coarse a variable. NOR, SLC NAND and niche DRAM require separate duration assumptions.

---

## 4. Reference Frame battle

### Frame A — Specialty-memory scarcity-cycle beneficiary

Mechanism:

```text
major suppliers reallocate / exit mature products
+ HBM / advanced-memory capacity crowding
→ niche DRAM / NOR / SLC supply shortage
→ ASP rises faster than input cost
→ gross margin and earnings spike
→ customer resistance + supply response + process migration
→ price / margin normalize
→ earnings mean-revert materially
```

Evidence supporting this frame:

- storage is the overwhelming H1 revenue and profit engine;
- storage gross margin at 67.57% is far above a normal historical semiconductor margin regime for this company;
- company itself calls current memory prices historically high and warns of eventual rebalance;
- independent industry work already identifies eventual supply response and product-level normalization paths;
- H1 reported profit contains large non-recurring gains on top of peak-like operating profitability.

### Frame B — Multi-product fabless platform structurally rebasing earnings

Mechanism:

```text
long customer qualification + broader memory portfolio
+ MCU / analog / custom-memory expansion
+ domestic substitution / supplier relationships
+ industrial / automotive / edge-AI product breadth
→ customer share and product value increase
→ non-cycle gross profit base expands
→ cycle peak accelerates but does not fully explain earnings
→ post-cycle normalized earnings and ROIC remain structurally above prior history
```

Evidence supporting this frame:

- MCU revenue grew ~49% YoY in H1 rather than merely following storage ASP;
- NOR/DRAM/SLC product breadth and industrial/auto qualification have real strategic value;
- management reports custom-memory project progress in AI phone, AI PC and robotics;
- analog is becoming a broader supporting product line;
- product / customer qualification can make mature-node specialty memory less interchangeable than commodity memory headlines imply.

But the key weakness is scale:

> H1 storage revenue of ~CNY9.83bn is still almost seven times MCU revenue of ~CNY1.43bn.

The platform thesis is therefore plausible, but current reported mix does not yet prove that non-cycle businesses can carry group earnings after storage profitability normalizes.

### Current frame disposition

Retain the hybrid frame:

> **Cycle-amplified fabless platform: 2026–27 earnings are dominated by an exceptional specialty-memory scarcity regime, while a real multi-product platform is developing underneath it; the post-cycle normalized earnings level and terminal model class are not yet proven.**

This frame is intentionally less flattering than `structural compounder` and less reductive than `memory cyclical`.

### Retrospective fit

The hybrid frame explains simultaneously:

- a genuine product-platform expansion;
- extraordinary H1 storage margin;
- strong MCU growth from a much smaller base;
- enormous 2026 earnings acceleration;
- company warnings that peak memory pricing is not indefinitely sustainable;
- independent evidence of structural shortage **and** later supply rebalancing;
- sell-side willingness to keep high earnings forecasts while cutting valuation multiples.

### Prospective discrimination

The two main frames make different future predictions.

If the platform frame is increasingly correct:

- MCU/custom-memory/analog gross profit should grow materially even after storage price growth slows;
- customer qualification and product breadth should preserve higher normalized margins / earnings;
- cash conversion and post-H-share capital returns should remain strong;
- earnings should not collapse when niche-memory ASPs plateau or fall.

If scarcity-cycle economics dominate:

- storage gross margin should decline materially as product-specific supply balances normalize;
- non-memory gross profit will not offset enough of that decline;
- inventory / working capital can worsen around cycle turns;
- the market should increasingly capitalize high near-term earnings at a lower multiple.

---

## 5. Five decision-critical variables

| Variable | Decision use | Uncertainty representation | Main uncertainty origin | Current read | Resolution path |
| --- | --- | --- | --- | --- | --- |
| **Product-specific scarcity duration** | VARIABLE | Scenario-linked | Future-state + structural | 2H26 tightness is strongly evidenced; 2027 differs materially across niche DRAM, NOR and SLC NAND | TrendForce/product pricing, foundry capacity, quarterly storage mix and gross margin |
| **ASP-to-owner-margin capture / upstream supply economics** | VARIABLE | Scenario-linked | Structural + estimation | Fabless model benefits from price but remains dependent on wafer/capacity economics; peak ASP does not mechanically equal permanent owner margin | storage GM, procurement/capacity disclosures, gross-profit conversion as pricing slows |
| **Non-cycle recurring profit base** | VARIABLE | Range / scenario-linked | Future-state + measurement | MCU growth is real; custom-memory is promising but forward-looking; current scale remains far below storage | MCU/custom-memory/analog revenue, margin, realized customer production volumes |
| **Cash conversion / capital-base quality** | VARIABLE | Scenario-linked | Future-state + estimation | H1 OCF is strong, but H-share issuance changes the per-share capital base and future ROE/ROIC denominator | inventory, receivables, OCF, capital allocation, post-H-share cash deployment |
| **Post-cycle model class / normalized ROIC** | VARIABLE | Scenario-linked | Model / Reference Frame | The central unresolved question: cyclical rent capture or durable platform rebase? | earnings after storage-margin deceleration, non-storage gross-profit scale, normalized FCF/ROIC |

The most important uncertainty is therefore not simply `2027 net profit`.

It is:

> **What fraction of 2027 earnings is scarcity rent, and what fraction represents economically retained platform capability that survives a memory normalization?**

---

## 6. Causal Worlds — deliberately no assigned probabilities

These are broad Research Worlds, not current Kernel `Scenario` objects. They carry no assigned probability and no terminal value.

The earnings bands below are stress anchors for causal coherence. They are not forecasts, targets, or probability buckets.

### World A — Fast normalization

Illustrative recurring 2027 earnings anchor: **~CNY8–10bn**.

```text
niche-memory supply responds faster than current management view
+ customer price resistance grows
→ storage ASP growth stalls / reverses
→ storage GM falls materially from H1 peak
→ MCU / analog / custom-memory grow, but from too small a base
→ group recurring profit normalizes sharply
```

What must be observed:

- faster-than-expected product price normalization;
- storage GM compression;
- inventory / working-capital deterioration;
- non-memory profit contribution insufficient to offset memory normalization.

### World B — Extended scarcity, then normalization

Illustrative recurring 2027 earnings anchor: **~CNY11–14bn**.

```text
2H26 and part of 2027 remain tight
→ niche-memory ASP / GM stay above old-cycle levels for a useful period
+ MCU / NOR volume continue growing
but
→ later 2027 supply / buyer resistance begins to normalize economics
→ earnings remain far above old history but are not permanent peak economics
```

This world is compatible with a better business and a favorable cycle without requiring a new permanent model class.

### World C — Long scarcity + platform contribution

Illustrative recurring 2027 earnings anchor: **~CNY15–18bn**.

```text
niche DRAM / SLC remain tight through most or all of 2027
+ NOR stays supported
+ MCU and custom-memory scale economically
→ storage margin normalizes only partially
→ non-memory gross profit becomes meaningfully larger
→ recurring earnings remain in the high-teens neighborhood
```

This world resembles the center of fresh post-H1 sell-side expectations, but the fact that analysts model it does not make it true.

### World D — Durable platform rebase / right tail

Illustrative recurring earnings anchor: **>CNY18bn** on a durable basis, not merely one peak year.

```text
cycle shortage creates customer / product-share gains
+ GigaDevice converts those gains into durable qualification positions
+ custom memory / MCU / analog become material profit engines
+ post-cycle storage economics settle far above prior regime
+ cash deployment preserves attractive ROIC
→ high earnings survive even after ASP normalization
```

This world requires evidence of retained economics **after** the scarcity regime begins to normalize.

It cannot be proven by 2026H1 peak margins alone.

### World coverage assessment

These four worlds appear sufficient for the current public-PIT research question.

The issue is no longer scenario invention. The issue is whether current evidence can support a cardinal probability measure across them.

---

## 7. Reconstructed pre-expectation underwriting

This reconstruction uses company records plus independent industry evidence while deliberately excluding sell-side forecasts and current share price from Fundamental Belief formation.

It does not claim psychological market-blindness; the purpose is auditability of the deliberate expectation-reconstruction pass.

Pre-expectation view:

1. **The 2026 recurring earnings inflection is real.** H1 deducted profit of ~CNY4.88bn and OCF of ~CNY6.05bn are too large to dismiss as only securities gains.
2. **The H1 margin regime is exceptional.** Storage GM of 67.57% is a cycle-state observation, not a demonstrated steady-state margin.
3. **Near-term scarcity is independently supported.** External industry data corroborates mature-node supply compression and strong 2H26 pricing.
4. **Scarcity is product-specific, not one permanent memory state.** 2027 DRAM/NAND/NOR paths can diverge, and broader NAND supply may loosen in 2H27.
5. **Platform improvement is real but not yet dominant in group economics.** MCU grew strongly, but storage still overwhelms the revenue/margin mix; custom-memory expectations remain forward-looking until realized.
6. **The fabless model creates both leverage and dependency.** Scarce product prices can generate high gross margins, but supply access / wafer economics / customer willingness matter to retained owner economics.
7. **Post-cycle capital returns matter.** H-share issuance and the enlarged cash/capital base mean absolute profit growth is not enough; per-share owner returns and ROIC must be tested after capital deployment.

Therefore:

> A high 2027 earnings world is economically plausible, but the duration and terminal model class are materially less established than the near-term shortage itself.

No cardinal probability is generated at this stage.

---

## 8. Published Expectations — use a matched panel where possible

### H1 headline was already known before the formal report

The 2026-07-09 preannouncement already gave the market approximately 115亿元 revenue, 69亿元 parent NP and 48.5亿元 deducted NP.

So the formal H1 report on 2026-08-19 should not be interpreted as a fresh `+1,091% earnings surprise`.

### Clean matched example: BOCI / 交银国际

**2026-07-17 — after H1 preannouncement, before formal H1 details**

BOCI initiated coverage with approximately:

```text
2026 revenue     CNY25.56bn
2027 revenue     CNY33.98bn
2026 gross margin 65.3%
2027 gross margin 65.8%
2026 parent NP   CNY13.97bn
2027 parent NP   CNY16.58bn
A-share target   CNY798
valuation        32x 2027E PE
```

This is a published expectation world, not fundamental truth.

**2026-08-20/21 — after formal H1 details**

BOCI's accessible post-H1 summary shows:

```text
2026 revenue     ~CNY25.6bn
2027 revenue     ~CNY33.7bn
2026 gross margin ~65.4%
2027 gross margin ~65.3%
overall profit forecasts broadly unchanged
A-share target   CNY687
valuation        28x 2027E PE
```

The stated reasons for the lower target include:

- memory price growth may decelerate at the margin;
- later specialty-memory capacity release creates cycle-downside risk;
- domestic storage investment opportunities may become more dispersed.

### Matched-panel conclusion

This is a particularly useful expectation observation:

> **The same sell-side house kept the earnings framework broadly intact while cutting the valuation multiple from 32x to 28x.**

That is direct evidence that `earnings level` and `duration / valuation regime` are different expectation dimensions.

It does **not** prove that the market sold the stock for exactly the same reason.

### Broader post-H1 expectation envelope

Current Full Research v2 already preserved a fresh 2027 sample around **CNY13.977–17.872bn**, median **CNY16.868bn**.

Other houses also made very large upward revisions from spring/Q1 assumptions into the post-H1 regime.

The important interpretation is:

> Sell-side expectations had already moved into a fundamentally different 2027 earnings regime before / around formal H1 disclosure. The remaining investment disagreement is heavily about duration, normalization and terminal model class rather than only one-year EPS.

---

## 9. Formal-report event reaction — attention evidence, not fundamental proof

Observed A-share closes:

```text
2026-08-18  CNY436.74
2026-08-19  CNY403.71  (-7.56%, 66.28m shares)
2026-08-20  CNY403.50
2026-09-02  CNY388.86
```

From the pre-formal-report close on 2026-08-18 to 2026-09-02, the share price declined about **10.96%**.

But the broader price path was already extremely volatile before formal H1:

```text
2026-07-09  CNY663.49
2026-07-10  CNY612.00
2026-07-17  CNY463.15
2026-07-21  CNY475.53
2026-08-03  CNY340.74
2026-08-18  CNY436.74
```

Therefore the H1 event study should not be converted into a single-cause story.

The defensible conclusion is narrow:

> **The market materially repriced the stock even though headline H1 earnings were already preannounced and at least one matched sell-side house kept its earnings framework broadly unchanged. This raises a valid duration / valuation / positioning research question; price action itself does not answer it.**

---

## 10. Price-Implied Worlds — challenger only

The price surface is deliberately kept outside Fundamental Belief.

Using the H1 issued-share count of approximately **701.75m shares** as a simple public-PIT bridge:

```text
CNY436.74/share → equity value ~CNY306.48bn
CNY403.71/share → equity value ~CNY283.30bn
CNY388.86/share → equity value ~CNY272.88bn
```

A simple 2027 earnings / implied-P/E surface is:

| 2027 parent NP world | At 436.74 | At 403.71 | At 388.86 |
| ---: | ---: | ---: | ---: |
| CNY8bn | 38.31x | 35.41x | 34.11x |
| CNY10bn | 30.65x | 28.33x | 27.29x |
| CNY12bn | 25.54x | 23.61x | 22.74x |
| CNY14bn | 21.89x | 20.24x | 19.49x |
| CNY16bn | 19.16x | 17.71x | 17.06x |
| CNY18bn | 17.03x | 15.74x | 15.16x |
| CNY20.5bn | 14.95x | 13.82x | 13.31x |

This table does **not** say the market uniquely believes one row.

It shows the many-to-one mapping problem:

> The same current price can be compatible with lower earnings / high duration, higher earnings / low terminal multiple, or different combinations of risk premium, reinvestment and terminal economics.

Therefore no single `implied EPS` or `expectation-gap score` is produced.

### Our World Surface vs Market-Compatible World Surface

The material dimensions are currently:

- 2027 recurring earnings level;
- product-specific scarcity duration;
- storage gross-margin normalization;
- MCU/custom-memory/analog profit contribution;
- supply / wafer economics and retained margin;
- capital deployment and post-cycle ROIC;
- terminal model class;
- valuation multiple / risk premium.

The research question is:

> **Which of the causal/economic conditions required by market-compatible worlds do we have the strongest reason to reject?**

Price can force that question. It does not answer it.

---

## 11. Anchoring audit — did published expectations improperly pull Fundamental Belief?

Published forecasts create a real anchoring risk because Full Research v2 was explicitly reopened after discovering that v1's scenario envelope sat below the fresh sell-side center.

The correction itself was valid:

> Serious market worlds should not be silently omitted merely because the researcher initially normalized too aggressively.

But a second error would be:

```text
sell-side publishes 14–18bn
→ therefore our Fundamental Belief must center on 14–18bn
```

This dogfood avoids that step.

Published Expectations contribute in two ways only:

1. they prove that those worlds are live **market beliefs** worth underwriting;
2. their models can expose drivers or primary evidence that Research had missed.

They do not become Fundamental Evidence merely through repetition.

The post-expectation Fundamental Belief remains:

> High 2027 earnings are plausible because scarcity is real and platform breadth is improving, but the current public PIT does not establish how much scarcity rent converts into durable post-cycle owner economics.

---

## 12. Probability Qualification Review

### 12.1 What is sufficiently established to constrain probability qualitatively

Several ordinal statements are defensible:

**A. A simple immediate collapse of all specialty-memory economics in 2H26 is less consistent with current evidence than continued near-term tightness.**

Company records, management statements and independent industry data all support continued 2H26 scarcity.

**B. Permanent extrapolation of H1 peak margins is also weakly supported.**

The company itself warns that prices are historically high and eventual supply-demand rebalance is unavoidable; independent evidence already shows product-level divergence and future supply response.

**C. Middle worlds — extended scarcity with partial normalization — deserve serious attention.**

They are causally consistent with both the observed shortage and the eventual normalization path.

**D. A durable platform-rebase right tail cannot be dismissed, but it requires evidence not yet observed.**

It needs non-storage/custom-memory economics and post-cycle ROIC to remain strong after memory ASP growth decelerates.

Thus the evidence can perform useful **tail rejection / ordinal ranking**.

### 12.2 What is not established

The PIT evidence does not justify a stable numerical answer to:

```text
P(World A) = ?
P(World B) = ?
P(World C) = ?
P(World D) = ?
```

Reasons:

1. **No clean reference class.** Generic memory cycles are relevant but too coarse because GigaDevice's current product mix, supplier structure and customer qualification base are changing.
2. **Product-level supply paths diverge.** DRAM, NOR and SLC NAND cannot be represented by one scarcity probability.
3. **Profit sensitivity is nonlinear.** Small changes in ASP / wafer cost near peak margins can produce very large earnings changes.
4. **The platform contribution is still emerging.** Custom-memory future volumes and post-cycle MCU/analog economics are not yet realized at sufficient scale.
5. **Terminal model class is part of the uncertainty.** A cyclical semi and a durable multi-product platform deserve different valuation regimes even at identical 2027 EPS.
6. **Several decisive uncertainties are future-state uncertainty.** More reading today cannot reveal 2027 supply release, customer inventory behavior or post-normalization margins.

### 12.3 Current qualification verdict

```text
WORLD COVERAGE                = SUFFICIENT
TAIL / ORDINAL JUDGMENT        = PARTIALLY ESTABLISHED
CARDINAL WORLD PROBABILITIES   = NOT ESTABLISHED
PROBABILITY-WEIGHTED EV        = NOT METHOD-READY IN THIS DOGFOOD
NUMERICAL ODDS                 = WITHHELD
```

Therefore the existing v2 `10/20/30/30/10` should be described as:

> **a frozen historical probability proposal that enables deterministic arithmetic, not a probability measure this dogfood can independently qualify as decision-grade.**

That is a methodological qualification, not a retroactive deletion.

---

## 13. Research stop test

### Strongest unresolved contradiction

The strongest contradiction is:

> Independent evidence supports unusually durable niche-memory scarcity, yet both company risk disclosures and broader supply data make permanent peak economics implausible; current data cannot establish where high temporary earnings end and durable platform economics begin.

### Strongest current evidence for the opposite conclusion

Against a pure-cycle view:

- MCU volume growth is real;
- product breadth / qualification are real;
- specialty-memory supply changes partly reflect structural vendor exits and capacity reallocation rather than only a short demand spike.

Against a pure-platform rebase view:

- storage dominates current economics;
- H1 storage margin is extraordinary;
- management itself warns about eventual price normalization;
- custom-memory and post-cycle non-storage profit scale remain mostly future evidence.

### Is there current public evidence we have not yet gathered that would likely establish cardinal probability?

Current answer: **not enough to justify another broad diligence loop**.

The highest-value discriminants are now mostly future observations rather than missing present-day reading.

Therefore:

```text
CURRENT PUBLIC RESEARCH LOOP = STOP
NEXT STATE = WAIT FOR DISCRIMINATING EVIDENCE
```

Quiet / waiting is a valid Research output.

---

## 14. Resolution paths / reopen triggers

Research should reopen when one or more of the following become observable:

1. **Product-specific storage pricing / gross margin:** evidence that niche DRAM, NOR or SLC NAND is normalizing faster or slower than the current causal worlds.
2. **Supply response:** foundry / memory-supplier capacity additions, process migration or customer inventory correction that changes the 2027 scarcity path.
3. **MCU/custom-memory realized economics:** actual revenue, gross profit and production-volume evidence rather than project language.
4. **Inventory and cash conversion:** rising inventory / receivables or weakening OCF despite high earnings would be materially discriminating.
5. **Capital deployment / owner returns:** use of the enlarged H-share cash base and evidence of normalized ROIC / per-share return quality.
6. **Matched expectation revisions:** same-house earnings and valuation changes that alter the Market Belief map. These are expectation evidence, not automatic Fundamental Belief updates.

---

## 15. Human Surface if the system allowed Research-complete / partial-probability state

A useful Human-facing result would be:

> **Research is complete enough for the current PIT. The central question is no longer whether the 2026 specialty-memory upcycle is real; it is how much of 2027 earnings is temporary scarcity rent versus durable multi-product platform economics. Current evidence supports prolonged near-term tightness and rejects both immediate mean reversion and blind peak extrapolation as simple defaults, but it does not justify a stable cardinal probability distribution across the serious 2027 worlds. The next high-value evidence is product-specific margin normalization, non-storage/custom-memory realized profit and cash/ROIC after the expanded capital base. Numerical Odds are withheld until a probability measure is supportable.**

This is already decision-useful without an expected-value number.

---

## 16. Counterfactual comparison with existing Full Research v2

| Question | Existing Giga v2 | Decision Hygiene dogfood |
| --- | --- | --- |
| Expectation envelope | Corrected vs v1 | Retained; matched BOCI revision added |
| Reference Frame | Implicit specialty-memory + platform | Explicit hybrid frame, challenged |
| Causal worlds | Five probabilized / valued scenarios | Four broad causal Research Worlds first |
| Probability | 10/20/30/30/10 | Ordinal constraints only; cardinal measure not established |
| Weighted terminal value | CNY436.522 | Withheld in dogfood |
| Price role | Excluded from frozen Belief | Explicit challenger surface only |
| Research stop point | Commit-ready after probability | Complete enough to stop before cardinal probability |
| Main unresolved issue | cycle durability / valuation | scarcity rent vs durable platform economics / terminal model class |

The dogfood therefore does not prove that the old v2 conclusion was wrong.

It proves a narrower methodological point:

> **A complete causal-underwriting process can contain more epistemic information than a forced probability distribution, and partial probability knowledge does not have to be rounded into a full measure merely to unlock Odds.**

---

## 17. Failure-attribution lens for later review

If later outcomes contradict this dogfood, do not default to `memory cycle surprise`.

Inspect at least:

- **Evidence Failure:** were source records materially wrong?
- **Classification Failure:** did management outlook or sell-side forecasts get promoted beyond their epistemic role?
- **Reference Frame Failure:** did we incorrectly classify durable platform economics as cyclical rent, or vice versa?
- **Inference Failure:** did we correctly observe supply data but misunderstand transmission to GigaDevice margins?
- **Assumption Failure:** did a specific product supply/demand state fail to occur?
- **Probability Failure:** were the worlds reasonable but later evidence shows our ordinal/tail judgment was badly calibrated?
- **Valuation Failure:** were earnings broadly right but terminal model class / multiple wrong?
- **Odds Failure:** was Fundamental Belief reasonable but price paid economically unattractive?
- **Exogenous Surprise:** only after the above have been inspected.

This dogfood is especially useful for testing `Reference Frame Failure`, because both a cycle model and platform model can fit selected pieces of the same H1 record.

---

## 18. Cross-case learning after YTO + GigaDevice

Two cases now produce two different probability-readiness outcomes.

### YTO

```text
Research complete enough to stop
→ Probability NOT ESTABLISHED
→ Numerical Odds withheld
```

Main reason: franchise/network economics, competition duration and reinvestment require future observations before even ordinal world weights are reliable enough.

### GigaDevice

```text
Research complete enough to stop
→ Probability PARTIALLY ESTABLISHED
→ ordinal / tail constraints are useful
→ full cardinal measure NOT ESTABLISHED
→ Numerical Odds withheld in this dogfood
```

Main reason: near-term scarcity and eventual normalization can both be evidenced, but product-level duration, profit sensitivity and terminal model class prevent precise cardinal weights.

This is early evidence that:

> **Probability readiness is not identical to Research completeness and may itself have meaningful degrees without requiring a new production enum.**

Do not encode this observation yet.

---

## 19. Current methodological verdict

For GigaDevice at the current public PIT:

```text
RESEARCH COMPLETE ENOUGH = YES
MORE CURRENT BROAD READING = LOW MARGINAL VALUE
CAUSAL WORLDS = SUFFICIENT
REFERENCE FRAME = HYBRID / STILL CHALLENGEABLE
TAIL / ORDINAL PROBABILITY KNOWLEDGE = YES
CARDINAL PROBABILITY DISTRIBUTION = NO
VALUATION MAP = POSSIBLE
PROBABILITY-WEIGHTED EV = WITHHELD IN THIS DOGFOOD
NUMERICAL ODDS = WITHHELD IN THIS DOGFOOD
SYSTEM RECOMMENDATION = NONE
HUMAN DECISION = NONE
INVESTMENT AUTHORITY = NONE
```

The current production GigaDevice Full Research v2 remains untouched and auditable.

This dogfood is evidence about Research Method maturity, not an instruction to alter current production state.

---

## 20. Source register

### Repository baselines

- `research_cases/603986-gigadevice-deep-research-v2.json`
- `research_cases/603986-gigadevice-research-contract-v2.json`
- `research_cases/603986-gigadevice-claim-audit-v2.json`
- `tests/test_gigadevice_full_research_v2.py`
- `docs/decision-hygiene-method-note-2026-09-03.md`

### Company / primary-record sources

- GigaDevice 2026H1 report, CNINFO: `https://static.cninfo.com.cn/finalpage/2026-08-19/1225480384.PDF`
- Company 2026-06-30 trading-risk warning reproduced in Shanghai Securities News: `https://paper.cnstock.com/html/2026-06/30/content_2237061.htm`
- Company 2026H1 preannouncement reported from the official announcement: `https://finance.eastmoney.com/a/202607093800142153.html`
- Company 2026-08-24 investor-relations record mirror: `https://m.10jqka.com.cn/sn/20260824/59422697.shtml`

### Independent industry context

- TrendForce, 2026-06-16, NOR / SLC structural shortage: `https://www.trendforce.com/presscenter/news/20260616-13102.html`
- TrendForce, 2026-07-13, SLC NAND price / structural-demand update: `https://www.trendforce.com/presscenter/news/20260713-13142.html`
- TrendForce, 2026-07-21, NAND supply growth / 2H27 easing: `https://www.trendforce.com/presscenter/news/20260721-13148.html`
- TrendForce, 2026-08-31, niche NAND price-momentum moderation: `https://www.trendforce.com/research/download/RP260831EM`

### Published Expectations

- BOCI / 交银国际 2026-07-17 first coverage summary: `https://stock.10jqka.com.cn/hks/20260717/c678258044.shtml`
- BOCI / 交银国际 post-H1 target / valuation revision summary: `https://caifuhao.eastmoney.com/news/20260820121837352623130`
- Current 10jqka sell-side forecast page: `https://basic.10jqka.com.cn/603986/worth.html`

### Market-context price observations

- Investing historical prices: `https://cn.investing.com/equities/gigadevice-semiconductor-beijing-historical-data`
- 2026-09-02 public market close context: `https://mc.baidu.com/from%3D1020712e/ssid%3D0/pu%3Dsz%401320_1001/s?word=%E5%85%86%E6%98%93%E5%88%9B%E6%96%B0%E8%82%A1%E7%A5%A8`

---

## 21. What this does not authorize

This dogfood does not authorize:

- a `PROBABILITY_PARTIALLY_ESTABLISHED` enum;
- a Research-complete state in Kernel;
- a new Research World schema;
- removal of probabilities from `ResearchSnapshot`;
- changes to production GigaDevice Research or Inbox;
- a new probability engine;
- a new price-implied-expectation engine;
- new Human wake semantics;
- any investment authority.

Next step remains **dogfood before schema**.

The next case should preferably have a different economic species again, so we can test whether probability qualification becomes easier when the business has a more stable causal/terminal model.