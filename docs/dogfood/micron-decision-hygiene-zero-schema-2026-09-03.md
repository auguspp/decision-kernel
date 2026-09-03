# Micron Decision Hygiene Zero-Schema Dogfood — 2026-09-03

Status: **FROZEN DECISION-USE DOGFOOD / US EQUITY / NO HUMAN DECISION / NO NUMERICAL ODDS / NO KERNEL CHANGE**  
Security: **Micron Technology / MU / NASDAQ**  
Public evidence cutoff: **2026-09-03 09:34 +08:00**  
Last completed U.S. session used for public market context: **2026-09-02**  
Repository lineage search: **NO PRIOR MICRON CASE FOUND in `decision-kernel` or `decision-os`**

---

## 0. Purpose and runtime boundary

This is the first Micron zero-schema Decision Hygiene dogfood in the repository.

It asks a narrower investment question than a conventional initiation report:

> **At the current public market price, what post-cycle earnings floor must Micron retain for the equity to be attractive, and what evidence would justify believing that the historical memory-cycle floor has structurally changed?**

This note deliberately separates:

```text
2026–27 scarcity earnings
from
post-scarcity normalized owner economics
```

It does **not** create a Human investment decision.

It also preserves the current production market-data boundary:

```text
PUBLIC U.S. MARKET PRICE = MARKET_CONTEXT ONLY
PRODUCTION OBSERVEDMARKET = NOT AVAILABLE FOR U.S. EQUITIES
PRODUCTION LIVE ODDS = NOT AVAILABLE
```

The current HiThink runtime is A-share specific. Public U.S. price data is therefore used only for reverse underwriting and must not be mislabeled as a production `ObservedMarket`.

No provider abstraction or fallback is introduced.

---

## 1. Prior lineage

Repository search across:

- `auguspp/decision-kernel`
- `auguspp/decision-os`

for Micron / MU / 美光 found no prior case lineage.

Therefore this note is a **new zero-schema lineage**. It does not inherit any prior ResearchSnapshot identity, probability distribution, scenario weights or valuation conclusion.

---

## 2. Source / epistemic discipline

### PRIMARY REALIZED

Micron fiscal Q3 2026 earnings release and Form 10-Q own realized company economics.

Quarter ended 2026-05-28:

```text
revenue                         ~USD 41.456bn
GAAP net income                 ~USD 28.243bn
GAAP diluted EPS                ~USD 24.67
non-GAAP net income             ~USD 28.857bn
non-GAAP diluted EPS            ~USD 25.11
GAAP gross margin               ~84.6%
operating cash flow             ~USD 25.39bn
net capex                       ~USD 7.1bn
adjusted free cash flow         ~USD 18.3bn
cash + marketable/restricted    ~USD 30.2bn
```

Business-unit Q3 gross margins were extraordinary:

```text
Cloud Memory                    ~83%
Core Data Center                ~87%
Mobile and Client               ~87%
Automotive and Embedded         ~79%
```

The realized result proves exceptional scarcity economics and cash generation at the current PIT.

It does **not** prove that an 80%+ gross-margin regime is permanent.

### PRIMARY STATEMENT

Micron's prepared remarks own management statements, not future truth.

Management states:

- DRAM and NAND demand significantly exceed supply;
- tight conditions are expected beyond calendar 2027;
- industry supply should improve gradually in 2028, but management says it has no line of sight to when supply catches demand;
- HBM4 is in high-volume shipment for a lead customer and HBM4E volume is expected in calendar 2027;
- new DRAM/NAND nodes are expected to begin volume production in 2H calendar 2027;
- fiscal Q4 2026 guidance is revenue `USD 50bn ±1bn`, gross margin around `86%`, non-GAAP EPS `USD 31 ±1`;
- the Q4 gross-margin outlook already reflects a meaningful moderation in the **rate** of price increases.

These statements are future expectations, not realized outcomes.

### INDUSTRY CONTEXT

TrendForce is used as independent industry context.

Current independent evidence supports a product-level divergence:

```text
2027 DRAM / HBM tightness = strongly supported
2028 meaningful DRAM supply response = increasingly relevant
2H27 NAND easing = serious contradiction to an all-memory-shortage thesis
```

TrendForce expects new DRAM capacity to begin contributing during 2027, with more substantial output in 2028. HBM continues to consume disproportionately high wafer input and is expected to retain pricing power in 2027.

NAND is different: TrendForce expects looser supply conditions in 2H27 as capacity rises and consumer demand remains weak.

Therefore:

> **Micron cannot be underwritten as one homogeneous “memory shortage” factor. DRAM/HBM and NAND need separate duration assumptions.**

### MARKET EXPECTATION

Sell-side and public consensus are used only as Market Belief / expectation context.

Current public FY2027 EPS aggregations vary materially by vendor and update time, but a serious envelope clusters roughly around:

```text
FY2027 EPS ~USD 140 to 170
```

Visible current examples include approximately:

- BofA: FY2027 EPS ~USD 140;
- broader public consensus: ~USD 150–160;
- Morgan Stanley: ~USD 169.

The exact point estimate is less important than the fact that the market already understands FY2027 is an extraordinary earnings year.

The investment debate is therefore not:

> “Will FY2027 EPS be high?”

It is:

> **“What earnings / FCF survive after scarcity normalizes?”**

---

## 3. Historical base rate — Micron has been brutally cyclical

The 2025 10-K is a necessary base-rate anchor.

```text
Fiscal year          2023          2024          2025
Revenue              15.54bn       25.11bn       37.38bn
Gross margin         -9%           22.4%         39.8%
Net income           -5.83bn       0.78bn        8.54bn
Diluted EPS          -5.34         0.70          7.59
```

Fiscal 2023 also included material inventory NRV write-down effects as DRAM and NAND ASPs declined.

Compare that history with fiscal Q3 2026:

```text
Q3 2026 gross margin ~84.6%
```

The correct inference is not:

> “Micron has become an 85% gross-margin business.”

The correct inference is:

> **The current regime is historically extreme. Any structural-rebase thesis must explain why the next normalization trough is materially better than prior cycles.**

This historical base rate is the strongest antidote to `peak EPS × premium multiple`.

---

## 4. The genuinely new evidence: Strategic Customer Agreements

The strongest evidence that Micron's economic species may be changing is not current spot pricing. It is the SCA contract architecture.

As of the fiscal Q3 call, Micron had signed 16 SCAs.

Management disclosed:

```text
typical duration                2026 through end-2030
signed SCA DRAM volume          ~20% of DRAM volume over term
signed SCA NAND volume          ~1/3 of NAND volume over term
expected eventual coverage      ~half or more of company revenue
contract structure              take-or-pay / binding volume commitments
14 of 16 signed SCA minimum-revenue RPO  ~USD 100bn
projected deposits/commitments   ~USD 22bn
```

For large agreements, management says pricing commonly includes a ceiling near CQ2-2026 market pricing plus a floor through the agreement term. When all planned SCAs are complete, agreements with fixed pricing or ceilings near CQ2 pricing are expected to represent about 40% of company revenue.

Most importantly, management states that for price-band SCAs:

> the floor price enables gross margin **well above peak quarterly margins in any past cycle**.

This is a load-bearing statement.

It is **not yet a realized downturn outcome** because the industry has not gone through a normalization cycle under these contracts.

Therefore SCA evidence has two epistemic layers:

```text
FACT:
contracts / take-or-pay structure / term / minimum-price RPO exist

NOT YET PROVEN:
the disclosed price floors will produce the claimed high gross-margin floor in a real future normalization regime
```

This is the central future calibration event for the Micron thesis.

---

## 5. Why HBM matters beyond one cycle

HBM changes both demand and supply geometry.

Current evidence supports:

```text
AI accelerator demand
+ rising HBM capacity per accelerator / ASIC
+ increasing HBM wafer trade ratio
-> HBM consumes disproportionately more DRAM wafer capacity
-> conventional DRAM capacity is crowded out
-> memory hierarchy becomes more differentiated
```

TrendForce expects HBM bit shipments to grow about 50–60% YoY in 2027 and still fail to keep pace with demand, supporting supplier pricing power through 2027.

Micron reports HBM4 in high-volume shipment for a lead customer and HBM4E expected in 2027.

However, HBM does **not** eliminate competitive risk:

- SK hynix remains a major HBM leader;
- Samsung is actively recovering HBM share / qualification;
- customer qualification and generation transitions can shift share;
- advanced packaging and yield execution matter as much as end-demand growth.

Therefore the HBM thesis is not:

> “AI grows, therefore Micron wins.”

It is:

> **AI increases memory value and constrains wafer supply, while Micron must continue earning an economically meaningful share of differentiated HBM / server-memory value.**

---

## 6. Capital intensity — scarcity profit is not automatically owner profit

Micron is an integrated manufacturer. This is economically different from GigaDevice.

The benefit is that Micron can capture more manufacturing scarcity rent.

The cost is enormous reinvestment.

Fiscal Q3 2026:

```text
OCF                    ~USD 25.4bn
net capex              ~USD 7.1bn
adjusted FCF           ~USD 18.3bn
```

But capex is accelerating materially.

Management guides:

```text
FQ4 2026 capex                  ~USD 10bn
FY2026 full-year capex          ~USD 27bn
FY2027 quarterly capex          above FQ4-26 levels
>50% of FY27 YoY capex increase from construction capex
```

ID1 Idaho first wafer is targeted for mid-2027, ID2 for late 2028, with additional capacity in Taiwan and other U.S. projects.

Therefore the owner-economics chain must be:

```text
scarcity pricing
-> gross margin
-> operating cash
-> massive fab / cleanroom / technology capex
-> government incentives + customer financing treatment
-> normalized FCF
-> incremental ROIC
-> per-share owner value
```

Do not count SCA customer deposits as free cash flow merely because cash arrives earlier.

Do not capitalize peak accounting earnings without charging the capital needed to defend / expand supply.

---

## 7. Reference Frame

Retained Reference Frame:

> **Capital-intensive memory oligopoly transitioning from a brutally cyclical commodity producer toward a strategically contracted AI-memory supplier; 2026–27 economics are scarcity-amplified and historically extraordinary, while SCAs, HBM differentiation and AI-driven memory hierarchy may permanently raise the post-cycle earnings and free-cash-flow floor, but that regime change is not yet outcome-proven.**

This is a hybrid frame.

It rejects two simplistic frames:

### Rejected: ordinary historical memory commodity only

This ignores real SCA contracts, HBM differentiation and AI-driven supply crowding.

### Rejected: permanent AI compounder already proven

This ignores:

- historical commodity cyclicality;
- 84–86% current gross margins being extreme;
- 2028 supply response;
- 2H27 NAND easing risk;
- very large forward capex;
- the fact that SCA floor economics have not yet been tested through a downturn.

---

## 8. Decision-critical variables

### 1. SCA downside economics

Load-bearing question:

> **What gross margin / EPS / FCF does Micron actually retain under SCA floor pricing when the open market normalizes?**

The contracts are real. The future realized floor is not yet proven.

### 2. DRAM / HBM shortage duration and share

Need to resolve:

- 2027 tightness durability;
- 2028 incremental supply timing;
- HBM4 / HBM4E qualification and share;
- wafer trade-ratio economics;
- conventional DRAM crowding-out.

### 3. NAND divergence

Do not allow DRAM strength to hide a weakening NAND cycle.

2H27 NAND easing is a serious competing world.

### 4. Owner cash / capital intensity

Need rolling evidence on:

- OCF;
- capex;
- customer deposits versus true owner cash;
- government incentives;
- depreciation / future capital consumption;
- incremental ROIC on new U.S. and Asian capacity.

### 5. Post-cycle normalized EPS / FCF floor

This is the single most important valuation variable.

FY2027 peak EPS is not the answer.

---

## 9. Research Worlds — no probabilities

These are causal Research Worlds, not Odds Scenarios. No cardinal probabilities are assigned.

### World A — Classic-cycle reversion

```text
DRAM capacity catches up after 2027
NAND eases earlier
SCA protection helps but does not transform total-company economics enough
HBM remains attractive but competitive
capex remains heavy
post-cycle normalized EPS ~USD 45–60
```

This world says the new regime mainly improves the peak / duration, not the fundamental trough economics.

### World B — Contract-cushioned normalization

```text
DRAM normalizes gradually
SCA floor pricing materially dampens ASP / margin collapse
HBM + server mix remain structurally richer
NAND cycles but is less important to total economics
capital spending converts to acceptable returns
post-cycle normalized EPS ~USD 70–90
```

This is the first world in which the SCA architecture creates a clearly higher economic floor.

### World C — Strategic-memory rebase

```text
AI memory hierarchy remains structurally supply-constrained
SCA coverage reaches ~half of revenue and performs as management describes
Micron holds strong HBM / advanced DRAM position
new capacity earns high incremental returns rather than recreating oversupply
post-cycle normalized EPS ~USD 100–125
```

This is a genuine business-model reclassification, not merely a long cycle.

### World D — Long AI-memory scarcity + durable platform

```text
2027 tightness persists materially longer
HBM / server DRAM / enterprise SSD value expands
contracts preserve unusually high margins through the period
owner cash accumulates despite capex
post-cycle floor also resets higher
```

This is the right tail.

Do **not** value it as:

```text
peak FY27 EPS × premium compounder multiple
```

A long-scarcity world should be valued through cumulative owner cash plus post-cycle terminal economics.

---

## 10. Market-implied worlds at the current public price

Public price vendors show small discrepancies for the 2026-09-02 close. For arithmetic only, this note uses approximately:

```text
PUBLIC MARKET CONTEXT PRICE ~USD 956/share
```

This is **not** production `ObservedMarket`.

At ~USD 956, the stock trades at only about:

```text
FY27 EPS 140      -> ~6.8x
FY27 EPS 155      -> ~6.2x
FY27 EPS 169      -> ~5.7x
```

That apparent cheapness is deceptive if FY27 is a peak.

The more useful reverse-underwriting question is:

> **What normalized EPS does USD 956 imply at a justified post-cycle multiple?**

```text
8x normalized earnings   -> ~USD 120 EPS
10x                      -> ~USD 96 EPS
12x                      -> ~USD 80 EPS
15x                      -> ~USD 64 EPS
18x                      -> ~USD 53 EPS
20x                      -> ~USD 48 EPS
```

This surface is the central investment read-through.

It means the market price is roughly compatible with very different worlds depending on what multiple the post-cycle business deserves.

Examples:

### If Micron remains fundamentally a cyclical manufacturer

A normalized EPS floor around `USD 50–60` with a mid/high-teens multiple can approximately explain the current price.

In that world, `~6x FY27E` is **not** necessarily cheap.

### If SCAs / HBM raise the floor to ~USD 70–90

Current price starts to look materially more favorable, even without assuming FY27 peak earnings persist.

### If the floor becomes ~USD 100+

The current market price can be cheap despite the enormous recent share-price appreciation.

Therefore the decision hinge is not the FY27 consensus EPS debate.

It is:

> **Is post-cycle normalized EPS closer to USD 50, USD 80, or USD 100+?**

---

## 11. Valuation Map — stress anchors, not targets

Using deliberately simple normalized EPS × normalized P/E stress anchors:

```text
World A: classic-cycle reversion
EPS ~45–60 × 15–18x
compatibility range ~USD 675–1,080

World B: contract-cushioned normalization
EPS ~70–90 × 13–16x
compatibility range ~USD 910–1,440

World C: strategic-memory rebase
EPS ~100–125 × 14–17x
compatibility range ~USD 1,400–2,125
```

These are **not price targets** and carry **no probabilities**.

They exist to expose what must be true for the current market price to offer a margin of safety.

The range also shows why a single “forward P/E = 6x” statistic is analytically weak.

---

## 12. What is actually differentiated versus already priced

The market already knows:

- FY2026/FY2027 earnings are extraordinary;
- DRAM/HBM are tight;
- AI infrastructure is memory intensive;
- Micron has signed major SCAs;
- fiscal Q4 guidance is extremely strong.

Therefore a weak variant perception is:

> “2027 memory is still strong.”

A stronger variant perception is:

> **“SCAs + HBM + AI memory hierarchy permanently raise Micron's trough-normalized earnings / FCF floor materially above the roughly USD 50–60 world that a traditional-cycle framework would imply.”**

That proposition is economically important and still not fully outcome-proven.

---

## 13. What would falsify the bullish rebase thesis

Reopen / downgrade the Reference Frame if evidence shows:

1. SCA minimum-price economics fail to preserve materially better margins during normalization;
2. major customers renegotiate / reduce economically meaningful commitments or SCA enforceability proves weaker than described;
3. DRAM/HBM supply catches demand materially faster than current serious industry work suggests;
4. Micron loses material HBM4 / HBM4E share or qualification economics;
5. NAND normalization materially overwhelms DRAM/HBM strength;
6. FY27–29 capex rises faster than owner cash and normalized ROIC deteriorates;
7. new capacity recreates commodity oversupply before SCA / product differentiation raises the floor;
8. inventory rises sharply while ASP / gross margin deteriorate;
9. post-cycle EPS / FCF evidence starts converging back toward the old historical cycle baseline.

---

## 14. Near-term event bridge

Next hard company event:

```text
Micron fiscal Q4 2026 earnings
2026-09-30 after U.S. market close
```

The important questions are **not only** whether Micron beats the current `~USD 31` Q4 EPS guide.

At the next event, the Research should prioritize:

1. FY2027 revenue / gross-margin / EPS direction;
2. pricing moderation by DRAM versus NAND;
3. SCA signed coverage, RPO, deposit receipts and any newly disclosed floor economics;
4. HBM4 / HBM4E qualification, mix and share;
5. FY2027 capex magnitude and construction versus productive-tool split;
6. OCF / FCF after capex;
7. inventory and days;
8. evidence for or against the post-cycle normalized earnings floor.

A short-term beat without better evidence on the floor should not automatically raise Fundamental Belief.

---

## 15. Current operating risks

Current public context includes a labor dispute / threatened strike process involving Micron employees in Taiwan.

Taiwan is a material manufacturing base, so this deserves operational attention.

However, at the current PIT it is a **risk / monitoring item**, not enough by itself to reclassify the Reference Frame.

Other persistent risks include:

- geopolitical / trade restrictions;
- HBM qualification / customer concentration;
- Samsung / SK hynix competition;
- Chinese DRAM capacity expansion over a longer horizon;
- power / permitting / construction delays;
- capital-cycle overshoot.

---

## 16. Probability qualification

Current probability state:

```text
2027 DRAM / HBM tightness                      = STRONGLY SUPPORTED ordinally
SCA downside protection exists                = STRONGLY SUPPORTED structurally
2028 supply response                          = SERIOUS COMPETING WORLD
2H27 NAND easing                              = SERIOUS COMPETING WORLD
exact SCA trough gross-margin floor            = NOT ESTABLISHED
post-cycle normalized EPS / FCF floor          = NOT ESTABLISHED cardinally
complete total-company scenario probabilities  = NOT ESTABLISHED
```

Therefore:

```text
PROBABILITY QUALIFICATION = PARTIALLY ESTABLISHED
CARDINAL PROBABILITY MEASURE = NOT ESTABLISHED
NUMERICAL ODDS = WITHHELD
```

The lack of U.S. production `ObservedMarket` is an additional independent reason not to publish production live Odds.

No placeholder probabilities are introduced.

---

## 17. Research stop memo

At the current public PIT, the decision-critical disagreement is sufficiently localized.

More generic AI / memory articles are unlikely to improve the decision meaningfully before the next hard company event.

Current stop state:

```text
REFERENCE FRAME = PARTIALLY RESOLVED / HYBRID FRAME RETAINED
CAUSAL WORLD COVERAGE = SUFFICIENT FOR CURRENT PRE-FQ4 PUBLIC PIT
DECISION-CRITICAL UNCERTAINTIES = IDENTIFIED
MARKET-IMPLIED WORLD SURFACE = CONSTRUCTED
RESEARCH COMPLETENESS = COMPLETE ENOUGH TO STOP CURRENT PUBLIC-DILIGENCE LOOP
PROBABILITY QUALIFICATION = PARTIALLY ESTABLISHED
CARDINAL PROBABILITY = NOT ESTABLISHED
PRODUCTION OBSERVEDMARKET = NOT AVAILABLE FOR U.S. EQUITY
NUMERICAL ODDS = WITHHELD
HUMAN ATTENTION VALUE = YES
HUMAN DECISION = NONE
INVESTMENT AUTHORITY = NONE
```

The next mandatory Research reopen event is fiscal Q4 2026 results on 2026-09-30, or earlier if a material company-specific event changes SCA economics, HBM qualification, supply, labor / production continuity, or capital allocation.

---

## 18. Frozen synthesis

Micron is not analytically interesting because it trades at approximately six times peak FY2027 earnings.

It is interesting because the current price forces a more useful question:

> **Has Micron's post-cycle earnings floor changed enough that a traditional memory-cycle valuation is now the wrong Reference Frame?**

The strongest evidence for a higher floor is real:

- five-year take-or-pay SCAs;
- material minimum-price RPO;
- price-floor architecture;
- HBM / AI-memory differentiation;
- structural DRAM capacity crowding;
- extraordinary current owner cash generation.

But the decisive evidence is still missing:

> **How those contracts and product advantages perform when the next normalization actually arrives.**

At approximately USD 956, the reverse-underwriting surface says:

```text
normalized EPS ~USD 50–60  -> current price can be roughly fair
normalized EPS ~USD 70–90  -> current price starts to look attractive
normalized EPS ~USD 100+   -> current price can be materially cheap
```

No probability is assigned to those worlds.

The next Research job is not to predict one more quarter of peak EPS. It is to estimate the **post-cycle normalized owner-earnings floor** without using the current price to backsolve Belief.
