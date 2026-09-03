# Sanhua Robot Operating-Economics Challenger — 2026-09-03

Status: **RESEARCH CHALLENGER / INDEPENDENT OPERATING-ECONOMICS REBUILD / NO CARDINAL SUCCESS PROBABILITY / NO RECOMMENDATION**  
Security: **三花智控 / 002050.SZ / 02050.HK**  
Prepared from main: `d13458072535b22cbb82958560fdfa852119e9ec`  
Parent Research: `docs/dogfood/sanhua-optionality-reverse-underwriting-2026-09-03.md`  
Investment Authority: **NONE**

## 0. Scope and boundary

This challenger does **not** reopen the accepted Xiaohongshu article and does **not** redo the already-closed base valuation / residual / price-implied optionality arithmetic.

It addresses the remaining Research gap:

> Can we independently reconstruct the industrial economics required for Sanhua's robot business to earn the sell-side CNY3.5bn / 35亿元 success-state profit, and can we identify how much capital would be required to earn it?

The sell-side reference arithmetic remains:

```text
1.0m annual robot units
× CNY50,000 actuator value / robot
× 70% Sanhua share
× 10% net margin
= CNY3.5bn / 35亿元 profit
```

This challenger treats that expression as a set of claims to underwrite, not as a Research conclusion.

No numerical robot success probability is introduced.

No Kernel schema is changed.

No BUY / HOLD / SELL engine is introduced.

No Human portfolio state, private trigger, action, or participation rule is inferred or published.

---

## 1. Epistemic labels used here

```text
FACT
= directly supported by issuer / exchange / competitor disclosure or similarly strong primary evidence

MARKET_CONTEXT
= useful public market / sell-side / industry framing that is not accepted as issuer truth

INFERENCE
= a conclusion drawn from multiple supported observations; not itself directly disclosed

ASSUMPTION
= an input used for a scenario or diagnostic without sufficient independent evidence

DERIVATION
= arithmetic or transformation from explicitly stated inputs

NOT ESTABLISHED
= current public evidence is insufficient to support the claim
```

---

## 2. Executive challenger

The evidence supports a materially narrower statement than the 35亿元 sell-side success case.

### 2.1 Commercialization is real, but the proof ladder is still early

**FACT** — In the 2026H1 investor-relations record, Sanhua says bionic-robot actuator core products are moving through **batch delivery** and **production-line ramp**.

That establishes productization beyond pure R&D.

It does **not** establish mass-production volume, durable customer allocation, long-run share, mature ASP, mature margin, or capital return.

### 2.2 The product is not economically equivalent to a single fully internal component

**FACT** — Sanhua's own exchange-query response describes a robot actuator as integrating transmission, drive, sensing, and control, plus brake / bearing content. The company says it combines supplier co-development with self-developed components; it has internal motor capability, while high-precision transmission adds manufacturing difficulty beyond existing pump products.

**INFERENCE** — The billable value of the actuator assembly is therefore not automatically equal to Sanhua's internally manufactured value added. Purchased content, partner economics, and subsystem boundaries matter for gross margin and invested capital.

### 2.3 CNY50k is a mature sell-side price assumption, not a disclosed current ASP

**MARKET_CONTEXT** — Dongwu's earlier deep-dive frames actuator-system value at **CNY200k+ per robot in the early ramp**, falling to roughly **CNY50k per robot at large-scale production**.

**DERIVATION** — Moving from CNY200k to CNY50k is a **75% price decline**; because the starting point is stated as CNY200k+, the implied decline is at least 75%.

**INFERENCE** — A CNY50k mature value-content case requires substantial cost-down, design simplification, purchasing leverage, automation, yield improvement, or content reduction to prevent economics from compressing with ASP.

### 2.4 The famous 70% share is not a clean long-run assumption even inside the same sell-side work

**MARKET_CONTEXT** — The same Dongwu deep-dive that discusses roughly 70% Sanhua share also says that after large-scale production the share **may gradually decline to around 50%**.

Therefore the familiar expression:

```text
CNY50k mature ASP
× 70% share
```

combines a mature-price state with a higher / earlier share state unless an additional argument is supplied for why share remains 70% after scale-up.

**DERIVATION — state-consistency check, not forecast:**

```text
1.0m units
× CNY50k
× 50% share
× 10% net margin
= CNY2.5bn profit
```

That is **28.6% below** the CNY3.5bn success-state profit.

To recover CNY3.5bn under a 50% mature share, one of the other inputs would need to compensate:

```text
1.4m units × CNY50k × 50% × 10% = CNY3.5bn
```

or

```text
1.0m units × CNY70k × 50% × 10% = CNY3.5bn
```

or

```text
1.0m units × CNY50k × 50% × 14% = CNY3.5bn
```

These are **DERIVATIONS**, not forecasts.

### 2.5 Competition is already observable; durable 70% allocation is not

**FACT** — Tuopu has created a dedicated robot-actuator business unit and discloses linear / rotary actuator products. Its public reporting shows robot-actuator revenue already exists, and later disclosures describe small-batch delivery / production readiness.

**FACT** — Sanhua and Leaderdrive / 绿的谐波 disclosed a strategic framework involving harmonic reducers, with the contemplated Mexico joint venture controlled by Leaderdrive. The framework itself was non-binding and implementation remained uncertain at disclosure.

**INFERENCE** — Key transmission economics can involve specialist suppliers / partners rather than being entirely captive inside Sanhua.

**NOT ESTABLISHED** — Current public primary evidence does not establish the final customer sourcing map, mandatory second-source policy, supplier allocation, or Sanhua's long-run economic share.

### 2.6 A 10% mature net margin is possible as a scenario, but currently unproven

**FACT** — Tuopu's robot-actuator gross margin was about **28.25% in 2025**. Its 2026H1 robot-actuator gross margin was about **27%** in public interim reporting while the business remained early in commercialization.

**FACT** — Leaderdrive reported a roughly **34.9% gross margin** for its industrial and embodied-intelligence robot-parts category in 2025, while explicitly warning that selling-price declines and higher depreciation during capacity ramp can pressure gross margin.

**INFERENCE** — There is enough gross-margin headroom in adjacent precision-component businesses for a 10% net margin to be conceivable after maturity, but current evidence does not prove Sanhua can retain it after price-down, purchased-content burden, ramp depreciation, R&D, SG&A, warranty / scrap / rework, tax, and financing effects.

**ASSUMPTION** — `10% net margin` remains a sell-side scenario input, not independently established Sanhua robot economics.

### 2.7 Capital intensity is the largest remaining missing denominator

**FACT** — Sanhua's disclosed CNY3.8bn future-industry investment is a **mixed robot-actuator + domain-controller** project.

**FACT** — The later CNY700m intelligent-drive future-industry-center project is also a **mixed new-energy thermal-management + bionic-robot-component** project.

Neither amount can be assigned wholly to robot invested capital.

**NOT ESTABLISHED** — Robot-specific fixed assets, capacity, yield, utilization, working capital, development capital, maintenance capex, and incremental invested capital are not publicly closed.

Therefore:

```text
SANHUA ROBOT INCREMENTAL ROIC = NOT ESTABLISHED
SANHUA ROBOT OWNER ECONOMICS = NOT ESTABLISHED
```

---

## 3. Product / component architecture

### 3.1 What Sanhua itself establishes

**FACT** — Sanhua describes the actuator system around four core functional blocks:

```text
transmission
+ drive
+ sensing
+ control
```

with brake / bearing content also involved.

**FACT** — The company describes integration across motor drive, transmission components, encoders, controllers and related elements through a mix of supplier co-development and self-developed components.

**FACT** — Sanhua says it has self-developed / self-manufactured multiple motor products.

**FACT** — Relevant production processes overlap with existing electronic-pump manufacturing — stamping, injection molding, machining, welding, surface treatment, motor winding, PCBA SMT and assembly — but robot products add precision machining for high-tolerance reduction mechanisms and have higher manufacturing difficulty.

**FACT** — The company specifically identifies planetary roller-screw process / productization for linear actuators and higher-power-density motor development for rotary actuators as R&D directions.

### 3.2 What is still missing

**NOT ESTABLISHED**:

- exact product mix between linear and rotary actuators at batch-delivery stage;
- exact number of actuators / modules billed per robot;
- component-level ASP or value split;
- what content is customer-supplied versus Sanhua-purchased versus Sanhua-manufactured;
- purchased transmission-component share of BOM;
- current yield / scrap / rework by precision part;
- warranty reserve / field-failure economics;
- final architecture after customers redesign for mass production.

### 3.3 Research implication

**INFERENCE** — `CNY50k value per robot` cannot be treated as `CNY50k of Sanhua manufacturing value added`.

The economic bridge must eventually distinguish:

```text
customer billable assembly value
- externally purchased precision content
- externally purchased electronics / sensors
- direct materials
- direct labor
- depreciation / manufacturing overhead
- scrap / rework / warranty
= gross profit
```

before applying corporate opex and tax.

---

## 4. Unit value and price-down path

### 4.1 What is actually supported

**NOT ESTABLISHED** — Sanhua does not publicly disclose a robot-specific current ASP in the primary evidence reviewed here.

**MARKET_CONTEXT** — Dongwu uses an early-ramp actuator-system value of CNY200k+ per robot and a large-scale value of about CNY50k per robot.

**DERIVATION** — The sell-side framework therefore embeds at least ~75% value-content / price compression from early ramp to scale.

### 4.2 Why the price path matters more than the point estimate

A successful volume ramp can still produce weak owner economics if:

```text
ASP falls faster than conversion cost
or
purchased-content cost does not fall with ASP
or
new capacity arrives ahead of demand
or
yield improvement lags price-down
or
customer redesign removes supplier content
```

**INFERENCE** — The critical underwriting variable is not simply whether CNY50k is plausible in 2030. It is whether Sanhua's **cost per delivered actuator system falls fast enough relative to the price path** while customer content and supplier allocation remain durable.

### 4.3 Required future evidence

Highest-value evidence would be:

- actual quotation / order-value evolution from prototype → sample → batch → mass production;
- customer-owned versus supplier-owned BOM changes;
- cost-down clauses or annual price-down conventions;
- actuator count and value by robot architecture generation;
- gross-margin progression through the same stages.

Until then:

```text
CURRENT SANHUA ROBOT ASP = NOT ESTABLISHED
MATURE CNY50k VALUE = ASSUMPTION / MARKET_CONTEXT
PRICE-DOWN CAPTURE BY COST-DOWN = NOT ESTABLISHED
```

---

## 5. Competition, second sourcing, and long-run share

### 5.1 Tuopu is a real competing production route

**FACT** — Tuopu discloses linear and rotary robot actuators and an independent robot-actuator business unit.

**FACT** — Tuopu's 2025 robot-actuator revenue was about CNY13.6m, with gross margin about 28.25%.

**FACT** — Public 2026H1 reporting shows robot-actuator revenue of about CNY14.0m and gross margin about 27%, with the business still in early commercialization.

**FACT** — Tuopu previously announced a robot-core-component production-base project with planned investment of CNY5bn and roughly CNY3bn fixed-asset investment, while explicitly warning that robot orders and project profitability were uncertain.

**INFERENCE** — This is direct evidence that competing actuator capacity can be built before mature demand / economics are proven.

### 5.2 Specialist transmission suppliers matter

**FACT** — Leaderdrive is a scaled precision-transmission specialist with meaningful harmonic-reducer production and disclosed humanoid / industrial robot component economics.

**FACT** — Sanhua and Leaderdrive signed a strategic framework contemplating a Mexico harmonic-reducer joint venture controlled by Leaderdrive.

**NOT ESTABLISHED** — This challenger has not established the current operating status or economics of that contemplated JV after the original framework disclosure.

### 5.3 Customer allocation remains opaque

**NOT ESTABLISHED**:

- customer identity from Sanhua primary disclosure;
- number of qualified suppliers per actuator type;
- whether second sourcing is mandatory;
- share split between prototype / qualified / mass-production suppliers;
- customer-owned tooling versus supplier-owned tooling;
- allocation rules after price renegotiation;
- long-run Sanhua share.

### 5.4 Share proof ladder

Do not collapse these states:

```text
early design-in share
→ qualified-supplier share
→ batch-delivery share
→ mass-production allocation share
→ long-run economic share after price-down and second sourcing
```

**MARKET_CONTEXT** — Dongwu's own framing moves from about 70% toward about 50% at large scale.

**INFERENCE** — `70% long-run share` is therefore not currently a defensible Research conclusion.

---

## 6. Capacity, yield, and utilization

### 6.1 Sanhua-specific capacity is not closed

**FACT** — Sanhua has disclosed meaningful future-industry-center investment tied partly to robot components.

But the disclosed projects have mixed business scope:

```text
CNY3.8bn+ = robot actuators + domain controllers
CNY700m = bionic robot components + NEV thermal-management components
```

**NOT ESTABLISHED**:

- robot-only invested capital;
- robot-only design capacity;
- units / year by actuator type;
- current installed capacity;
- line utilization;
- yield;
- cycle time;
- automation level;
- precision-machining bottleneck capacity.

### 6.2 Manufacturing adjacency is useful but not sufficient

**FACT** — In an older cooling-control project, Sanhua demonstrated real process and automation improvements: the company reported higher production efficiency and lower unit-capacity spending through automation / process optimization and domestic equipment substitution.

**INFERENCE** — Sanhua has a credible manufacturing-engineering capability that may help the robot ramp.

But:

**NOT ESTABLISHED** — The same capex efficiency has not been demonstrated for high-precision robot transmission / actuator manufacturing.

### 6.3 Outside-view warning from mature precision transmission

**MARKET_CONTEXT / FACT FROM PEER DISCLOSURE** — Nabtesco, a mature precision-reducer leader, disclosed materially different utilization across plants during demand recovery even with a large installed position and substantial market share.

**MARKET_CONTEXT / FACT FROM PEER DISCLOSURE** — Harmonic Drive Systems explicitly warns that demand below expectations can leave production capacity underutilized and extend or prevent recovery of invested capital.

**INFERENCE** — Capacity installation is not evidence of economic capacity utilization. Utilization needs to be observed independently.

---

## 7. Margin bridge

### 7.1 Evidence from adjacent direct competitors

**FACT — Tuopu 2025:**

```text
robot-actuator revenue ≈ CNY13.6m
gross margin ≈ 28.25%
```

**FACT — Tuopu 2026H1 public reporting:**

```text
robot-actuator revenue ≈ CNY14.0m
gross margin ≈ 27%
```

This is early-stage, low-revenue evidence — useful for manufacturing reality, not a mature-margin forecast.

**FACT — Leaderdrive 2025:**

```text
industrial and embodied-intelligence robot-parts revenue ≈ CNY422.5m
gross margin ≈ 34.88%
```

Its disclosed cost mix for the category includes substantial material, labor, manufacturing-overhead and outsourced-processing burdens.

Leaderdrive also explicitly warns that selling-price declines and higher depreciation during capacity ramp can reduce gross margin.

### 7.2 What 10% net margin would have to survive

A proper bridge is:

```text
volume
× billable ASP / value content
= revenue

revenue
- purchased transmission / electronics / sensors
- direct materials
- direct labor
- depreciation / manufacturing overhead
- scrap / rework / warranty
= gross profit

- robot-specific R&D
- sales / application engineering
- corporate / segment SG&A burden
- tax / finance effects
= net profit / NOPAT
```

**NOT ESTABLISHED** — Sanhua has not disclosed enough robot-specific information to populate this bridge.

Therefore:

```text
10% ROBOT NET MARGIN = ASSUMPTION
```

not Research fact.

---

## 8. Capital, working capital, incremental ROIC, and owner economics

### 8.1 Sanhua's denominator cannot yet be isolated

The main missing variable in the 35亿元 scenario is not another income-statement line. It is **incremental invested capital**.

A proper bridge is:

```text
incremental robot revenue
→ incremental gross profit
→ incremental NOPAT

plus required:
working capital
+ robot-specific fixed assets
+ tooling / automation
+ precision-machining equipment
+ capitalized / expensed development burden where economically relevant
+ maintenance capex
= incremental invested capital / reinvestment burden

incremental ROIC
= incremental NOPAT / incremental invested capital
```

**NOT ESTABLISHED** — Current public evidence does not permit a clean Sanhua robot-only denominator.

### 8.2 Why mixed project announcements cannot close the answer

Do **not** write:

```text
robot invested capital = CNY3.8bn
```

because the CNY3.8bn project includes robot actuators **and domain controllers**.

Do **not** write:

```text
robot invested capital += CNY700m
```

because the CNY700m project includes bionic robot components **and NEV thermal-management components**.

Adding both would create false precision and likely double-count / misallocate mixed-use capacity.

### 8.3 Outside-view capital evidence

**FACT — Leaderdrive 2025:**

- revenue about CNY570.7m;
- cash paid to acquire / construct long-term assets about CNY99.7m;
- a new-generation precision-transmission intelligent-manufacturing project had budget of about CNY2.03bn and was still early in cumulative investment at year-end;
- receivables and inventory were both material relative to the revenue base.

**DERIVATION — whole-company reference only, not robot-specific:**

```text
2025 cash fixed-asset capex / revenue
≈ 99.7 / 570.7
≈ 17.5%
```

A deliberately narrow working-capital proxy gives:

```text
AR + inventory - AP
≈ 194.5 + 285.0 - 112.3
≈ CNY367.3m
≈ 64% of annual revenue
```

This is **not** a normalized working-capital requirement for Sanhua. It is a warning that precision-component growth can carry meaningful inventory / receivable capital.

**FACT / MARKET_CONTEXT — Nabtesco:** its 2024 company-level ROIC was low during a period when precision-reducer demand and utilization were weak despite its mature competitive position.

**FACT / MARKET_CONTEXT — Nidec E-Axle:** Nidec committed heavily to anticipatory E-Axle capacity, later recorded large automotive losses / restructuring and shifted strategy toward profitability, localization, cost reduction, and more selective component-level participation amid intense EV price competition.

**INFERENCE** — Volume growth and high system value content do not guarantee attractive owner economics when capacity is built ahead of demand or price-down outpaces cost-down.

### 8.4 Current owner-economics verdict

```text
ROBOT-SPECIFIC NOPAT = NOT ESTABLISHED
ROBOT-SPECIFIC WORKING CAPITAL = NOT ESTABLISHED
ROBOT-SPECIFIC GROWTH CAPEX = NOT ESTABLISHED
ROBOT-SPECIFIC MAINTENANCE CAPEX = NOT ESTABLISHED
ROBOT INCREMENTAL INVESTED CAPITAL = NOT ESTABLISHED
ROBOT INCREMENTAL ROIC = NOT ESTABLISHED
ROBOT OWNER CASH / OWNER ECONOMICS = NOT ESTABLISHED
```

This is not a model failure to be patched with guessed numbers.

It is the current Research truth.

---

## 9. Small outside-view / reference class

This is intentionally a **small human-readable reference class**, not a probability engine.

The companies are not identical to Sanhua. Their use is to identify recurring industrialization failure modes that the Sanhua case must explicitly survive.

| Reference | Stage / evidence | Observed economics | What it challenges in Sanhua |
| --- | --- | --- | --- |
| **Tuopu robot actuators** | early revenue + small-batch / production-base build | ~27-28% early gross margin; large planned capex relative to current disclosed robot revenue | design-in / capacity build does not prove mature utilization or margin |
| **Leaderdrive / 绿的谐波** | scaled precision transmission + robot component demand growth | 2025 industrial / embodied-intelligence parts GM ~34.9%; high volume growth; explicit price-down + ramp-depreciation risk; meaningful capex / WC | volume can grow while price, depreciation and capital remain first-order |
| **Nabtesco precision reducers** | mature global leader | high mature share can coexist with uneven plant utilization and weak ROIC in demand downturns | durable share is possible, but installed-base moat does not eliminate utilization / cycle risk |
| **Harmonic Drive Systems** | mature precision drive supplier | explicitly warns of underutilization / unrecovered capex if demand misses; 2026 management says AI-robot real-world implementation pace diverged from prior planning assumptions | even category leaders can mis-time AI / robot adoption and capacity |
| **Nidec E-Axle** | adjacent high-value mechatronic system ramp | large anticipatory investment + sales growth did not prevent losses / restructuring under price competition; strategy shifted toward profitability / selective component participation | high content per end product is not equivalent to high owner return |

### 9.1 What this reference class does establish

**INFERENCE** — Across these cases, five recurring industrialization variables matter before owner economics can be trusted:

```text
1. real end-demand versus planned capacity
2. ASP / annual price-down versus cost-down
3. supplier allocation after second sourcing
4. yield / automation / utilization versus depreciation burden
5. working capital + capex required per unit of incremental NOPAT
```

### 9.2 What it does not establish

It does **not** establish:

- a robot success probability;
- a median Sanhua margin;
- a median Sanhua ROIC;
- a mechanically transferable price-down rate;
- a mechanically transferable capital / revenue ratio.

The sample is too small and heterogeneous for those claims.

---

## 10. Rebuild the 35亿元 success state as falsifiable operating requirements

The clean way to use the sell-side scenario is to convert each input into a proof obligation.

| Variable | Sell-side success-state input | Current Research status | What would upgrade it |
| --- | ---: | --- | --- |
| end-market annual volume | 1.0m robots | **ASSUMPTION / MARKET_CONTEXT** | customer / industry production evidence and realized shipments |
| billable actuator value | CNY50k / robot | **ASSUMPTION / MARKET_CONTEXT** | actual mass-production quotation / realized ASP / content map |
| Sanhua share | 70% | **NOT ESTABLISHED**; same sell-side work contemplates ~50% at scale | customer sourcing / supplier allocation evidence |
| net margin | 10% | **ASSUMPTION** | robot-specific realized GM, opex, yield, utilization and cost-down evidence |
| incremental invested capital | omitted from 35亿元 arithmetic | **NOT ESTABLISHED** | robot-specific capacity, fixed assets, WC, development and maintenance burden |
| incremental ROIC | omitted | **NOT ESTABLISHED** | NOPAT + invested-capital denominator |
| owner cash | omitted | **NOT ESTABLISHED** | NOPAT less sustaining / growth reinvestment and WC needs |

### 10.1 The scenario currently proves arithmetic, not economics

The original expression proves only:

```text
if
volume = 1.0m
and ASP = CNY50k
and share = 70%
and net margin = 10%
then profit = CNY3.5bn
```

It does not prove any antecedent.

### 10.2 The most important current inconsistency

The same sell-side body of work contains two states:

```text
early / high-share state ≈ 70%
large-scale share may decline toward ≈ 50%
```

while the CNY50k ASP is explicitly a large-scale price assumption.

**INFERENCE — case-specific failure exposed:**

> The 35亿元 headline arithmetic appears to combine assumptions from different commercialization states unless a separate durability argument is supplied for keeping 70% share after large-scale price-down.

This is a real Research Challenger, but it is **not yet promoted into a new generic Kernel method**.

One case is not enough.

---

## 11. Why 35亿元 may still be possible

This challenger does not conclude the success state is impossible.

A high-profit state can still emerge if some combination of the following is eventually evidenced:

```text
end-market volume materially exceeds 1.0m
or
mature billable value remains above CNY50k
or
Sanhua retains unusually high allocation despite second sourcing
or
net margin exceeds 10% through integration / automation / cost-down
or
higher-margin content offsets price compression
or
capital turns prove unusually efficient
```

But each of these remains an empirical claim to prove.

No cardinal probability is assigned.

---

## 12. Why 35亿元 may fail even if robot shipments scale

The outside view identifies several non-binary failure modes where commercialization succeeds but owner economics disappoints:

```text
volume grows
but ASP falls faster than cost

capacity is installed
but utilization remains low

supplier is qualified
but second-source allocation compresses share

gross margin looks acceptable
but working capital + capex absorb owner cash

system value is high
but purchased precision content captures much of the economics

end-market grows
but customer redesign reduces content / supplier bargaining power
```

This is the main reason the next Research layer must be operating economics rather than another TAM / order / capacity narrative.

---

## 13. Current Research Challenger verdict

```text
SANHUA ROBOT COMMERCIALIZATION = REAL / SUPPORTED AT BATCH-DELIVERY + LINE-RAMP STAGE

PRODUCT ARCHITECTURE = PARTIALLY RECONSTRUCTED
CURRENT / MATURE BILLABLE VALUE = NOT INDEPENDENTLY ESTABLISHED
PRICE-DOWN PATH = MATERIAL / SELL-SIDE CONTEXT, NOT YET REALIZED EVIDENCE
CUSTOMER SECOND-SOURCE / ALLOCATION = NOT ESTABLISHED
LONG-RUN SANHUA SHARE = NOT ESTABLISHED
ROBOT-SPECIFIC CAPACITY = NOT ESTABLISHED
YIELD = NOT ESTABLISHED
UTILIZATION = NOT ESTABLISHED
ROBOT GROSS MARGIN = NOT ESTABLISHED
ROBOT NET MARGIN = NOT ESTABLISHED
ROBOT-SPECIFIC CAPEX = NOT ESTABLISHED
ROBOT-SPECIFIC WORKING CAPITAL = NOT ESTABLISHED
INCREMENTAL ROIC = NOT ESTABLISHED
OWNER ECONOMICS = NOT ESTABLISHED

SELL-SIDE 35亿元 SUCCESS STATE = SCENARIO ARITHMETIC / NOT RESEARCH CONCLUSION
CARDINAL ROBOT SUCCESS PROBABILITY = NOT ESTABLISHED
TOTAL-COMPANY NUMERICAL ODDS = WITHHOLD
```

The strongest new challenger is not that CNY3.5bn is impossible.

It is:

> **The current 35亿元 headline combines a mature CNY50k price state with a 70% share assumption that the same sell-side work says may fall toward 50% at scale, while omitting the capital required to achieve the volume. Before 35亿元 can become an independent Research state, share durability, price/cost-down, mature margin, and invested-capital intensity must be demonstrated together.**

---

## 14. Highest-value next evidence

Do not broaden into generic framework work yet.

The next research should target evidence that can actually close the remaining bridge:

1. **Product billing scope** — assembly versus component content; actuator count per robot; customer-supplied versus Sanhua-supplied content.
2. **Realized price path** — prototype / sample / batch / mass-production quotation or ASP evidence; annual cost-down clauses.
3. **Customer allocation** — qualified suppliers, second-source structure, allocation after mass-production launch.
4. **Capacity denominator** — units / year by line, installed equipment, tooling, cycle time, precision bottlenecks.
5. **Yield and utilization** — ramp yield, scrap / rework, line utilization and depreciation absorption.
6. **Margin bridge** — purchased content, direct conversion cost, warranty, robot-specific R&D / SG&A and realized gross margin.
7. **Working capital** — receivables, inventory / WIP and payable terms tied to robot production.
8. **Incremental capex** — robot-only fixed assets and maintenance / growth capex, separated from domain controller and NEV thermal projects.
9. **Ownership boundary** — economics of any upstream supplier / JV relationship before assigning value to the listed company.
10. **Owner economics** — only after NOPAT and invested capital can be separated, calculate incremental ROIC and owner cash.

---

## 15. Method-promotion decision

**Do not change Full Research process docs yet.**

This case exposed a plausible new failure mode:

```text
cross-state assumption mixing
=
using an early-stage share assumption
with a mature-stage ASP / cost assumption
inside one apparently coherent success-state equation
```

That failure is worth preserving in this case record.

It is **not yet a generic method gate**.

Promote it only if another real case independently reproduces the same failure and the generic rule earns its keep.

---

## 16. Public evidence used

### Sanhua primary / issuer evidence

- 2026H1 investor-relations activity record — batch delivery / production-line ramp:  
  https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12563691&stockid=002050
- Exchange-query response on robot actuator project architecture, supplier co-development, self-developed motors, manufacturing process and R&D scope:  
  https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=10499411&stockid=002050
- Future-industry-center investment framework — robot actuator + domain controller mixed project:  
  https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=9763716&stockid=002050
- Intelligent-drive future-industry-center project — robot components + NEV thermal-management mixed scope:  
  https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=11214249&stockid=002050
- Project-delay notice:  
  https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12423757&stockid=002050
- Company clarification rejecting widely circulated undisclosed robot “large order” rumors:  
  https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=11513931
- Sanhua / Leaderdrive strategic framework on harmonic reducers:  
  https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=8990501

### Sell-side / market context

- Dongwu deep-dive carrying early CNY200k+ → large-scale CNY50k value-content path and ~70% → potentially ~50% share framing:  
  https://finance.sina.com.cn/roll/2025-02-20/doc-inemchxc3801346.shtml

### Direct competitor / precision-component evidence

- Tuopu 2025 annual report:  
  https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12012707
- Tuopu 2026H1 report:  
  https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12562168&stockid=601689
- Tuopu robot-core-component production-base investment disclosure:  
  https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=9765302
- Leaderdrive / 绿的谐波 2025 annual report:  
  https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12146041&stockid=688017

### Outside-view reference-class evidence

- Nabtesco business / precision-reducer share context:  
  https://www.nabtesco.com/en/about/ir/weare-nabtesco/
- Nabtesco FY2025 results briefing / precision-reducer utilization context:  
  https://www.nabtesco.com/cms/wp-content/uploads/Results_Briefing_Material_for_FY2025_e.pdf
- Nabtesco Value Report 2024 / ROIC and demand-utilization context:  
  https://www.nabtesco.com/cms/wp-content/uploads/value_report_2024_en.pdf
- Harmonic Drive Systems risk disclosure:  
  https://www.hds.co.jp/english/ir/management_policy/risk/
- Harmonic Drive Systems 2026 management message on AI-robot implementation pace versus prior assumptions:  
  https://www.hds.co.jp/english/ir/management_policy/top_message/
- Nidec risk disclosure on anticipatory capacity / utilization / investment-return risk:  
  https://www.nidec.com/en/ir/management/risk/
- Nidec Integrated Report 2024 / E-Axle profitability-first shift:  
  https://www.nidec.com/-/media/www-nidec-com/sustainability/integrated_report/IntegratedReport2024_en.pdf

---

## 17. Final handoff state from this challenger

```text
35亿元 IS NO LONGER TREATED AS A SINGLE ATOMIC ROBOT CONCLUSION.

It is decomposed into:
volume
× mature billable value
× durable allocation share
× mature margin
minus the missing reinvestment / capital burden required to sustain those economics.

Current strongest failure:
CNY50k mature price + 70% share is not state-consistent with the same sell-side work's own ~50% mature-share discussion unless additional share durability is proven.

Current biggest unknown:
robot-specific incremental invested capital and therefore incremental ROIC / owner economics.

NEXT ACTION:
seek primary evidence that closes customer allocation, realized ASP / cost-down, capacity / yield / utilization, and robot-specific capital.

NO METHOD PROMOTION YET.
NO CARDINAL SUCCESS PROBABILITY.
NO INVESTMENT RECOMMENDATION.
```
