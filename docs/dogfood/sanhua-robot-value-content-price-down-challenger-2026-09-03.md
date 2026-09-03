# Sanhua Robot Value Content + Price-Down Challenger — 2026-09-03

Status: **RESEARCH CHALLENGER SUPPORT / CASE-SPECIFIC / UNIT-VALUE REBUILD / NO CARDINAL SUCCESS PROBABILITY**  
Security: **三花智控 / 002050.SZ / 02050.HK**  
Parent challenger: `docs/dogfood/sanhua-robot-operating-economics-challenger-2026-09-03.md`  
Sibling proof table: `docs/dogfood/sanhua-robot-35bn-proof-table-2026-09-03.md`  
Prepared against main: `9fb517c9592d4c5969907bdb7b7219f78097cdb5`  
Investment Authority: **NONE**

## 0. Question

The 35亿元 sell-side state depends on:

```text
CNY50,000 actuator value / robot
```

The Research question is not whether CNY50k is arithmetically convenient.

It is:

> What product architecture and component prices would have to exist at mature scale for a humanoid robot's relevant actuator systems to bill around CNY50k, and can those prices coexist with durable supplier margins?

This note does not replace the CNY50k assumption with another guessed point estimate.

---

## 1. What the sell-side CNY50k actually contains

### 1.1 Dongwu's own component bridge

**MARKET_CONTEXT** — Dongwu's 2025 Sanhua deep-dive describes a reference humanoid architecture with:

```text
body:
14 rotary actuators
14 linear actuators

hand:
12 hollow-cup motor modules
```

It says the hand architecture was not yet fixed.

For the body actuator value bridge, Dongwu assumes at large scale:

```text
rotary actuator:
~CNY1,500 / unit
× 14
≈ CNY20k / robot

linear actuator:
8 roller-screw actuators × ~CNY3,000
+ 6 T-screw actuators × ~CNY1,500
≈ CNY30k / robot
```

**DERIVATION** — using the stated unit inputs literally:

```text
14 × CNY1,500 = CNY21,000
8 × CNY3,000 + 6 × CNY1,500 = CNY33,000
combined = CNY54,000
```

Therefore the familiar `CNY50k` headline is already a rounded mature-state summary, not an independently disclosed customer quotation.

### 1.2 The billable system contains materially more than one transmission component

**MARKET_CONTEXT** — Dongwu describes a rotary actuator as:

```text
frameless servo motor
+ harmonic reducer
+ motor driver
+ clutch
+ force sensor
+ encoder
```

and a linear actuator as a motor + screw transmission system with sensing / control content.

**FACT — Sanhua architecture disclosure** — Sanhua's own exchange response similarly describes electromechanical actuators around transmission, drive, sensing and control, with brake / bearing content and a mix of supplier co-development and self-developed parts.

**INFERENCE** — A mature CNY1,500 rotary actuator is not a CNY1,500 reducer assumption. It is a system-level billable-price assumption after allocating economics across multiple purchased / internally produced components.

---

## 2. Independent harmonic-reducer price evidence

The rotary part of the CNY50k bridge can be challenged with realized public-company pricing.

### 2.1 Fengli Intelligent: realized new-entrant pricing and negative ramp margin

**FACT** — Fengli Intelligent's 2026 exchange inquiry response discloses realized harmonic-reducer economics:

```text
                     2023      2024      2025 1-9M
average ASP          CNY708    CNY701    CNY605
unit cost            CNY3,195  CNY1,040  CNY750
gross margin         -351%     -48%      -24%
```

2025 1-9M main-model selling prices were approximately CNY400-1,300 per unit, with average ASP CNY605.18.

The issuer explicitly says it was still in market-development mode and using a more aggressive pricing strategy.

**FACT** — Over the same ramp, manufacturing-expense share of harmonic-reducer unit cost fell from roughly:

```text
79.94%
→ 64.14%
→ 43.12%
```

as output rose, process improved and production efficiency increased.

Yet gross margin remained negative because fixed-asset absorption was still high.

### 2.2 Leaderdrive / Green Harmonic: higher incumbent price reference

**FACT / CROSS-CHECK** — Fengli's regulatory response cites Leaderdrive's 2024 annual-report harmonic-reducer average selling price at roughly **CNY1,320/unit**.

Separately, Leaderdrive's 2023 financing inquiry modeled its new-generation harmonic reducer at:

```text
first-year ASP = CNY1,400
third-year trial-production ASP = CNY1,317.26
annual modeled price-down = 3%
```

This was a management project model, not a realized humanoid-robot quotation.

**HISTORICAL FACT** — Leaderdrive's IPO-era disclosure also shows harmonic-reducer average ASP falling from approximately CNY1,923 in 2017 to CNY1,632 in 2019, driven by both product mix and direct price changes.

### 2.3 What this says about Dongwu's CNY500-800 mature reducer assumption

Dongwu assumes that at humanoid-robot mass scale a harmonic reducer may fall to roughly **CNY500-800/unit**.

Current public evidence does not disprove that possibility.

But it places it in context:

```text
CNY500-800
≈ around the low-price end already seen at an aggressive new entrant
< established supplier / broader-product average around CNY1.3k in recent public references
```

**INFERENCE** — The CNY500-800 assumption should be treated as a mature, high-volume cost-down state. It is not yet a broadly observed industry clearing price with demonstrated mature margins.

---

## 3. A budget-consistency test for the CNY1,500 rotary actuator

Dongwu's mature rotary-actuator budget is approximately:

```text
CNY1,500 per complete actuator
```

For 14 rotary joints:

```text
complete rotary-actuator bill
= 14 × CNY1,500
= CNY21,000
```

Now compare that system budget with observed reducer prices.

### 3.1 Using Fengli's 2025 1-9M average reducer ASP

**DERIVATION / DIAGNOSTIC ONLY**:

```text
14 × CNY605.18
≈ CNY8,473 reducer bill
```

That consumes roughly 40% of the CNY21,000 complete rotary-actuator budget.

The remaining budget is about:

```text
CNY12,527 total
≈ CNY895 per joint
```

for everything else combined:

```text
motor
+ driver
+ clutch
+ force sensor
+ encoder
+ bearings / structure
+ assembly / test
+ supplier gross margin
```

### 3.2 Using the ~CNY1,320 incumbent average reference

**DERIVATION / DIAGNOSTIC ONLY**:

```text
14 × CNY1,320
= CNY18,480 reducer bill
```

That consumes 88% of the CNY21,000 complete rotary-actuator budget.

Only:

```text
CNY2,520 total
= CNY180 per joint
```

would remain for all other actuator content and margin.

### 3.3 Research implication

This is **not** evidence that CNY1,500 is impossible.

It shows what must happen for CNY1,500 to become economically coherent:

```text
reducer price must move toward the low end
+
motor / sensing / electronics must also undergo large cost-down
+
integration / assembly costs must fall
+
yield and utilization must mature
+
supplier margin must survive the above
```

A mature reducer price alone does not close the rotary-actuator economics.

Therefore:

```text
CNY1,500 MATURE ROTARY ACTUATOR = ASSUMPTION
COST-DOWN BRIDGE TO CNY1,500 = NOT ESTABLISHED
```

---

## 4. Linear actuator: the larger unresolved value bucket

Dongwu's mature bridge allocates approximately CNY33k of the literal CNY54k body-actuator sum to linear actuators:

```text
8 roller-screw actuators × CNY3,000 = CNY24,000
6 T-screw actuators × CNY1,500 = CNY9,000
```

The report separately assumes a mature roller-screw price around CNY2,000/unit.

### 4.1 Public primary evidence validates industrial difficulty, not the CNY2,000 price

**FACT** — Beite Technology's 2025 prospectus describes planetary roller screws as a new product for which it had achieved initial validation / small-batch delivery, while explicitly warning that large-scale production must meet yield-economics requirements.

Its Thailand phase-I project plans:

```text
annual rated capacity = 800k roller-screw sets
total investment = CNY349.26m
building = CNY51.20m
equipment = CNY206.65m
other construction = CNY69.75m
initial working capital = CNY18.38m
```

The company warns that delayed capacity absorption, failure to achieve expected selling prices / volumes, raw-material / labor / manufacturing-cost pressure and incremental depreciation can impair economics.

**NOT ESTABLISHED** — This public prospectus does not provide a clean realized mass-production humanoid-robot roller-screw ASP that independently validates Dongwu's CNY2,000 mature assumption.

Therefore:

```text
CNY2,000 MATURE ROLLER-SCREW ASP = NOT INDEPENDENTLY ESTABLISHED
CNY3,000 COMPLETE ROLLER-SCREW ACTUATOR = NOT INDEPENDENTLY ESTABLISHED
```

### 4.2 Capital is already visible before price is visible

The Beite reference is useful precisely because it shows an industrial asymmetry:

```text
rated capacity + equipment + working capital
can be disclosed
before mature price / yield economics are observable
```

That is the same Research danger present in Sanhua: production-line ramp or capacity construction cannot be translated directly into mature unit economics.

---

## 5. Price-down is not one mechanism

The CNY200k+ early value → ~CNY50k mature value path should not be modeled as a single generic `75% price cut`.

At least four economically different mechanisms can create lower unit value.

### A. Same architecture, supplier price-down

Examples:

```text
harmonic reducer ASP falls
motor price falls
sensor / encoder price falls
customer annual price-down
```

This primarily pressures supplier revenue per unit and requires manufacturing cost-down to defend margin.

### B. Manufacturing learning / utilization / yield

Fengli provides a realized example:

```text
unit cost CNY3,195
→ CNY1,040
→ CNY750
```

while manufacturing-expense absorption falls materially as volume / efficiency improve.

This can offset selling-price decline without changing architecture.

### C. Vertical integration / purchased-content substitution

Sanhua has internal motor capability and describes partial self-development plus supplier co-development.

If previously purchased content moves in-house, customer billable value may fall while Sanhua value added or margin is preserved — but only if internal production economics are superior.

The exact in-house / purchased split remains `NOT ESTABLISHED`.

### D. Architecture simplification / content removal

This is economically different from manufacturing cost-down.

**FACT — adjacent robot architecture evidence** — Zhaowei Electromechanical's 2026 interim report explicitly offers both:

```text
high-DoF fully driven dexterous hand
vs
lower-DoF linkage underactuated hand
```

and says the underactuated route uses fewer drive units to reduce system complexity and hardware cost.

**ENGINEERING CONTEXT** — Published humanoid / biped actuator research likewise shows that actuator count and mechanism choice need not map one-for-one to nominal degrees of freedom; paired linear actuators and hybrid architectures can change component count and load sharing.

**INFERENCE** — Part of humanoid unit-value decline may come from deleting / consolidating actuators or changing actuator architecture, not merely producing the same bill of materials more cheaply.

That matters for Sanhua because:

```text
manufacturing cost-down
can preserve supplier content

architecture content-down
can permanently remove supplier revenue opportunity
```

These two paths should not be treated as economically equivalent.

---

## 6. Outside-view lesson: lower price and higher volume do not automatically create margin

Fengli is a particularly useful realized reference class:

```text
harmonic-reducer volume rises
+
ASP falls modestly
+
unit cost falls dramatically
+
manufacturing-overhead absorption improves
```

but gross margin can still remain negative during a multi-year ramp.

Leaderdrive's own financing model separately assumes ongoing annual price-down even after industrialization.

Therefore the correct mature-margin bridge is:

```text
customer price-down
vs
material cost-down
+ purchased-content localization
+ yield
+ labor productivity
+ automation
+ utilization
+ architecture change
```

not:

```text
volume ↑
→ margin automatically stable
```

---

## 7. What can now be said about CNY50k

### Supported

**MARKET_CONTEXT** — The sell-side CNY50k number has a concrete component architecture behind it rather than being a pure market-size placeholder.

**FACT / OUTSIDE VIEW** — Harmonic reducers already trade at public-company realized prices spanning roughly the high hundreds to low thousands of yuan depending on supplier / mix / ramp stage, and substantial cost-down with volume is demonstrably possible.

**FACT / OUTSIDE VIEW** — Cost-down and price-down occur simultaneously, while fixed-cost absorption can keep margins weak for years.

**FACT / OUTSIDE VIEW** — Architecture simplification can reduce the number of drive units and therefore reduce billable content, not just manufacturing cost.

### Not supported yet

```text
CNY50k = Sanhua disclosed mature ASP                   NOT ESTABLISHED
CNY1.5k complete rotary actuator is realized          NOT ESTABLISHED
CNY2k mature roller screw is realized at scale        NOT ESTABLISHED
CNY3k complete linear actuator is realized at scale   NOT ESTABLISHED
same BOM survives from early ramp to mature scale      NOT ESTABLISHED
Sanhua captures the whole CNY50k billable content     NOT ESTABLISHED
mature CNY50k can coexist with 10% Sanhua net margin  NOT ESTABLISHED
```

---

## 8. Implication for the 35亿元 success state

The headline state:

```text
1m × CNY50k × 70% × 10%
= CNY3.5bn
```

now has a more explicit hidden dependency:

```text
CNY50k must be achieved by cost-down
without losing so much content or margin
that Sanhua's economics collapse
```

This means `CNY50k` is not independently bullish or bearish.

There are at least two very different CNY50k worlds:

### World 1 — good supplier economics

```text
same / similar actuator content
+ aggressive manufacturing learning
+ high utilization / yield
+ localized purchased content
→ CNY50k customer bill
→ margin survives
```

### World 2 — weak supplier economics

```text
customer redesign
+ fewer / simpler actuators
+ second sourcing
+ component commoditization
→ CNY50k customer bill
→ Sanhua content / price / margin all decline
```

Both can produce the same headline CNY50k robot value.

Only the first supports a strong owner-economics state.

Which world Sanhua ultimately occupies is currently `NOT ESTABLISHED`.

---

## 9. Highest-value next evidence

The price / value-content bridge would materially improve with:

1. customer or supplier quotation evidence for complete rotary / linear modules;
2. realized planetary-roller-screw ASP and unit cost through a genuine mass-production ramp;
3. Sanhua disclosure of purchased vs internally produced transmission / motor / sensing content;
4. evidence of actuator-count / architecture changes between prototype and mass-production versions;
5. annual customer price-down / redesign requirements;
6. Sanhua robot-specific gross margin once line ramp moves into material revenue.

Until then, CNY50k should remain a **structured sell-side mature-state assumption**, not a Research fact.

---

## 10. Source register

### Sanhua primary

- September 2024 exchange inquiry response — actuator architecture / process overlap / higher precision requirements:  
  https://static.cninfo.com.cn/finalpage/2024-09-26/1221289654.PDF

### Sell-side scenario context — not accepted as issuer truth

- Dongwu Sanhua deep-dive reproduction — 14 rotary / 14 linear architecture; mature rotary and linear value assumptions:  
  https://www.vzkoo.com/read/20250225ed52d621d9ff8b8a93e04be6.html

### Fengli Intelligent primary / regulatory reply

- 2026 Shenzhen Stock Exchange inquiry response — realized harmonic-reducer ASP, unit cost, manufacturing-cost absorption, product price ranges:  
  https://disc.static.szse.cn/disc/disk03/finalpage/2026-04-20/334a322e-ff89-484e-9775-8382b07abf12.PDF

### Leaderdrive / Green Harmonic primary

- 2023 Shanghai Stock Exchange financing inquiry — CNY1,400 harmonic reducer / CNY20,000 high-end mechatronic project pricing, annual 3% / 5% price-down, equipment intensity:  
  https://static.sse.com.cn/stock/disclosure/announcement/c/202306/688017_20230616_ASHC.pdf
- IPO-era price history / product-sales-price risk:  
  https://static.sse.com.cn/stock/information/c/202006/6a4687316782455c89c5ed4b25354015.pdf

### Roller-screw outside view

- Beite Technology 2025 securities offering prospectus — 800k roller-screw project, investment composition, small-batch / yield / utilization / depreciation risks:  
  https://static.sse.com.cn/stock/disclosure/announcement/c/202512/603009_20251205_7ZC1.pdf

### Architecture cost-down outside view

- Zhaowei Electromechanical 2026 interim report — full-drive vs underactuated hand architectures and fewer drive units for hardware-cost reduction:  
  https://disc.static.szse.cn/download/disc/disk03/finalpage/2026-08-15/6b203b49-e54f-43bc-b49f-adc0799bfbb0.PDF

---

## 11. Current verdict

The research has moved from:

```text
CNY50k is a sell-side mature value assumption
```

to:

```text
we know the sell-side component arithmetic behind it
+
we can test part of the rotary budget against realized reducer prices
+
we can observe real price-down / cost-down / utilization behavior
+
we can distinguish manufacturing cost-down from architecture content-down
```

but we still cannot say:

```text
Sanhua will realize CNY50k mature revenue per robot
or
CNY50k will support 10% durable net margin
```

Those remain to be proven by commercial and manufacturing evidence.
