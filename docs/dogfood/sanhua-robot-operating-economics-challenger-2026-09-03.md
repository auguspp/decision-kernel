# Sanhua Robot Operating-Economics Challenger — 2026-09-03

Status: **RESEARCH CHALLENGER / INDEPENDENT OPERATING-ECONOMICS REBUILD / NO CARDINAL SUCCESS PROBABILITY / NO RECOMMENDATION**  
Security: **三花智控 / 002050.SZ / 02050.HK**  
Prepared against main: `9fb517c9592d4c5969907bdb7b7219f78097cdb5`  
Parent Research: `docs/dogfood/sanhua-optionality-reverse-underwriting-2026-09-03.md`  
Investment Authority: **NONE**

## 0. Scope

This challenger does not reopen the Human-accepted Xiaohongshu article and does not redo the already-closed observable-base valuation / residual / price-implied optionality arithmetic.

It addresses the remaining Research question:

> Can we independently explain why Sanhua's robot business might or might not earn the sell-side CNY3.5bn / 35亿元 success-state profit, and how much capital would have to be committed to earn it?

The familiar sell-side arithmetic remains only a reference state:

```text
1.0m annual robot units
× CNY50,000 actuator value / robot
× 70% Sanhua share
× 10% net margin
= CNY3.5bn / 35亿元 profit
```

This file is now the synthesis entry for the supporting case-specific challengers created on this branch.

No numerical success probability is introduced.
No Kernel schema is changed.
No BUY / HOLD / SELL engine is introduced.
No Human portfolio state, private trigger, action or participation rule is inferred or published.

---

## 1. Current executive verdict

The sell-side CNY3.5bn state is **not disproven**, but it is not independently established.

The strongest current Research conclusion is:

> The 35亿元 state requires several commercialization assumptions to remain simultaneously favorable across different stages — realized robot volume, mature actuator architecture / billable content, durable customer allocation, mature margin, make-or-buy mix, utilization and capital intensity. Public evidence currently proves commercialization progress, but not that those mature-state conditions all coexist.

The largest case-specific failure found so far is **cross-state assumption mixing**:

```text
mature low ASP / value content
×
higher early / headline share
```

The same sell-side work that uses roughly CNY50k mature value also discusses share potentially declining toward roughly 50% after mass production.

Pure state-consistency arithmetic:

```text
1.0m × CNY50k × 50% × 10%
= CNY2.5bn
```

not CNY3.5bn.

To preserve CNY3.5bn at 50% share, one of the other inputs must compensate. Holding 1m units and CNY50k value constant:

```text
required net margin = 14%
```

If mature billable value is also lower, required margin can move into the mid/high teens. These are `DERIVATION`, not forecasts.

---

## 2. Product / component architecture

### Supported

**FACT** — Sanhua describes robot electromechanical actuators as integrating:

```text
transmission
+ drive
+ sensing
+ control
+ brake / bearing auxiliary content
```

**FACT** — The company says the system integrates motor drive, transmission components, encoders and controllers through supplier co-development plus partial component self-development.

**FACT** — R&D targets include planetary-roller-screw process / productization for linear actuators and higher-power-density motors for rotary actuators.

**FACT** — Robot production overlaps with existing stamping, injection molding, machining, welding, surface treatment, motor winding, PCBA SMT and assembly capabilities, while adding higher-precision transmission machining requirements.

### Not established

```text
exact rotary / linear product mix at batch-delivery stage
exact actuator count per robot at mature scale
component-level customer quotation
customer-supplied vs Sanhua-purchased vs Sanhua-manufactured content
mature BOM by component
mature yield / scrap / rework / warranty economics
```

### Implication

```text
customer billable content
!=
Sanhua internally manufactured value added
```

The difference matters for both margin and capital intensity.

---

## 3. CNY50k value content: now decomposed, still not a Research fact

Dongwu's mature-state reference contains a concrete architecture rather than a pure TAM placeholder.

Literal body-actuator bridge:

```text
14 rotary actuators × CNY1,500 = CNY21,000
8 roller-screw linear actuators × CNY3,000 = CNY24,000
6 T-screw linear actuators × CNY1,500 = CNY9,000
--------------------------------------------------
literal total ≈ CNY54,000
```

The headline `CNY50k` is therefore a rounded mature-state assumption, not a disclosed Sanhua ASP.

### Rotary challenge

Public-company harmonic-reducer pricing shows that a complete CNY1,500 rotary actuator requires much more than reducer cost-down.

A complete rotary actuator still has to contain:

```text
motor
+ reducer
+ driver
+ clutch / brake
+ force sensing
+ encoder
+ bearing / structure
+ assembly / test
+ supplier margin
```

Current references place harmonic reducers from aggressive new-entrant pricing in the high hundreds of yuan to broader incumbent averages around the low thousands. Therefore a CNY1,500 complete actuator requires coordinated cost-down across the whole subsystem.

### Linear challenge

Dongwu's mature roller-screw assumption is roughly CNY2,000 per screw.

An exchange-reviewed Five Continents Spring project model uses:

```text
planetary roller screw ASP = CNY500
unit cost = CNY318.77
GM = 36.25%
```

and assumes 14 roller screws per humanoid robot.

This does **not** prove CNY500 is the future clearing price; specifications and architecture can differ.

It does prove:

```text
CNY2,000 mature roller-screw ASP
!= unique publicly supported mature endpoint
```

Architecture also differs across references, so value-per-robot is partly a component-count / mechanism choice, not just price-down.

### Current status

```text
CNY50k mature customer billable content = STRUCTURED SELL-SIDE ASSUMPTION
SAME BOM SURVIVES TO MATURITY = NOT ESTABLISHED
CNY1.5k COMPLETE ROTARY ACTUATOR = NOT ESTABLISHED
CNY2k MATURE ROLLER SCREW = NOT ESTABLISHED
CNY3k COMPLETE ROLLER-SCREW ACTUATOR = NOT ESTABLISHED
```

---

## 4. Price-down has two economically different forms

The early `CNY200k+ → ~CNY50k` path cannot be treated as one generic 75% price cut.

### Manufacturing / sourcing cost-down

```text
same / similar content
+ yield improvement
+ automation
+ utilization
+ supplier price-down
+ localization / vertical integration
→ lower customer price
```

This can preserve supplier value added if costs fall fast enough.

### Architecture / content-down

```text
customer redesign
+ fewer drive units
+ simpler mechanism
+ integrated functions
+ lower actuator count / specification
→ lower customer bill because content disappears
```

This can permanently reduce supplier revenue opportunity even if manufacturing is efficient.

Current public robot architecture evidence shows both fully driven and underactuated approaches exist in adjacent applications.

Therefore mature value content must be underwritten as:

```text
component count
× component type
× specification
× mature price
```

not simply `early value × price-down percentage`.

---

## 5. Competition / allocation: commercialization is FACT, durable 70% is not

Sanhua's proof ladder has advanced materially:

```text
2024: R&D project / no designated customer disclosed
→ key-customer co-development
→ trial production / iteration / sampling
→ 2026H1 batch delivery + production-line ramp
```

This is genuine commercialization progress.

But reviewed primary materials do not disclose:

```text
customer name
contracted volume
allocation percentage
rotary-vs-linear allocation
supplier-of-record status by robot generation
long-term purchase commitment
```

Therefore:

```text
COMMERCIALIZATION PROGRESS = FACT
CUSTOMER-SPECIFIC ECONOMIC ALLOCATION = NOT ESTABLISHED
70% LONG-RUN MASS-PRODUCTION SHARE = ASSUMPTION
```

Tuopu has separately disclosed robot-actuator revenue, proving competing actuator commercialization exists.

Tesla's public procurement policy is useful outside-view context: it qualifies multiple suppliers for key components where sensible, continuously seeks supplier cost reductions, can source cheaper alternatives and redesign parts. This is not Optimus-specific allocation evidence and is not used to identify Sanhua's customer.

Long-run share can be diluted by:

```text
second source
customer redesign
customer vertical integration
new robot generation
component-level directed sourcing
```

not only by a conventional direct competitor.

---

## 6. Make-or-buy is now a load-bearing state variable

Sanhua primary evidence supports supplier co-development plus partial self-development.

It does not support full mature vertical integration across all core components.

Therefore the owner-economics bridge must split:

```text
customer billable content
=
internally manufactured content
+
purchased content
```

### More purchased content

```text
lower internal PP&E / tooling burden
but lower internal value capture
and supplier margin appears inside purchased BOM
```

### More internal content

```text
higher potential value capture
but higher development / equipment / working-capital burden
and direct utilization / yield / depreciation risk
```

The relevant test is:

```text
incremental NOPAT gained by internalization
/
incremental invested capital required
```

not whether a component is simply labelled `self-produced`.

### Linear component capital reference

Five Continents Spring discloses roughly CNY223.15m of major production equipment for 980k sets/year planetary-roller-screw capacity.

Outside-view equipment-only intensity:

```text
~CNY228 equipment capital
per one unit of annual roller-screw capacity
```

If an actuator integrator used 8 roller screws / robot for 1m robots and internalized all 8m screws at similar manufacturing intensity, the reference-class diagnostic is roughly:

```text
~CNY1.82bn equipment capital
```

before buildings, land, common utilities, development capital and working capital.

This is not a Sanhua capex forecast. It shows why make-or-buy belongs inside the ROIC denominator.

---

## 7. Margin: 10% is conceivable, but not independently underwritten

Peer evidence does not validate a direct `high-20s / low-30s GM → 10% net margin` shortcut.

### Realized Tuopu actuator economics

2025:

```text
robot-actuator revenue ≈ CNY13.6m
GM = 28.25%
GM change = -22.65ppt YoY
```

Material, labor and manufacturing expense all matter.

### Integrated execution-unit project reference

Zhongda Leader management project model:

```text
mature GM = 25.84%
mature net margin = 7.31%
construction = 2 years
first operating year utilization = 80%
100% utilization from following year in model
```

This is management underwriting, not realized Sanhua economics.

It demonstrates that even an integrated execution-unit project can lose most of its gross margin after period costs, depreciation and tax.

### Compensation problem

If mature share falls to 50% while value remains CNY50k:

```text
required net margin to preserve CNY3.5bn profit = 14%
```

If mature value also falls toward ~CNY39k and share is 50%:

```text
required net margin ≈ 18%
```

Again: pure reverse arithmetic, not forecasts.

This makes the combined mature-state requirement materially harder than examining `10% margin` in isolation.

---

## 8. Capital: real deployment is visible, robot-only denominator still is not

### Dedicated development layer

A historical GDR plan budgeted a CNY201.8m robot electromechanical-actuator R&D project and explicitly said it would not add production capacity. The GDR plan was later terminated, so the amount is evidence of planned development-capital scope, not realized investment.

### CNY3.8bn future-industry project

This is a mixed:

```text
robot actuator
+
domain controller
```

R&D / production-base project.

It cannot be assigned wholly to robot capital.

### CNY700m intelligent-drive future-industry center

This is also mixed:

```text
new-energy thermal-management components
+
bionic-robot components
```

but its capital stack is disclosed:

```text
land                 CNY70.89m
buildings            CNY421.60m
equipment            CNY115.74m
contingency          CNY26.35m
initial working cap  CNY65.42m
--------------------------------
total                CNY700.00m
```

Realized mixed-project capital is now visible:

```text
2025 additions to CIP ≈ CNY138.97m
2025 year-end CIP     ≈ CNY138.97m
investment / budget   ≈ 19.85%
reported progress     ≈ 25%
```

2026 disclosures show continued financing / physical progress and a delay in expected usable status to December 2026.

This proves:

```text
MIXED PHYSICAL CAPACITY BUILD-OUT = FACT
```

but does not reveal robot-specific building area, equipment, capacity or working capital.

Therefore:

```text
ROBOT-SPECIFIC REALIZED CAPITAL = NOT ESTABLISHED
```

---

## 9. Outside view: what actually happens during industrial ramp

The current small reference class deliberately avoids formal probability statistics.

### Tuopu actuator

Realized early commercialization can show positive high-20s GM while revenue remains immaterial and cost grows faster than revenue.

### Zhongda Leader integrated execution unit

Management model uses mid-20s GM but only ~7% mature net margin after full cost burden.

### Five Continents precision component project

Management model combines mid-30s planetary-roller-screw GM with only:

```text
12.27% post-tax project IRR
6.60-year payback incl. construction
```

once the broader capital system is included.

### Leaderdrive / Green Harmonic

The new precision-transmission project originally modeled:

```text
35.02% post-tax IRR
5.66-year payback
```

but realized harmonic-reducer utilization was:

```text
2023 51.59%
2024 42.67%
2025 67.76%
```

and the new project was later delayed from end-2026 to end-2028 to absorb existing capacity first.

### Repeated outside-view mechanics

```text
validation
→ small batch
→ line ramp
→ capacity absorption
→ stable utilization
→ mature margin
→ mature owner return
```

are distinct stages.

Also:

```text
attractive project-model IRR
!= realized demand timing
!= realized utilization path
```

and:

```text
30% GM
!= known ROIC
```

---

## 10. Owner-economics bridge that still must close

A complete mature-state bridge should be:

```text
terminal robot units
× customer allocation
× mature actuator architecture / billable content
= Sanhua robot customer revenue

split revenue economics into:

internally manufactured content
+
purchased content

then:

revenue
- purchased content
- direct materials
- labor
- manufacturing depreciation / overhead
- scrap / rework / warranty
= gross profit

- robot-attributable R&D
- SG&A / logistics / customer support
- cash tax
= incremental NOPAT

and denominator:

robot-attributable PP&E / tooling
+ robot working capital
+ development capital not already expensed
+ allocated shared infrastructure where economically required
= incremental invested capital

incremental NOPAT
/
incremental invested capital
= incremental ROIC

incremental NOPAT
- growth capex
- maintenance capex
- change in working capital
= owner cash
```

Current public evidence still cannot fill this bridge with defensible Sanhua-specific mature numbers.

---

## 11. Current proof state

```text
DOWNSTREAM 1m REALIZED ANNUAL ROBOT OUTPUT = NOT ESTABLISHED
SANHUA BATCH DELIVERY / LINE RAMP = FACT
MATURE ACTUATOR ARCHITECTURE = NOT ESTABLISHED
CNY50k MATURE BILLABLE CONTENT = STRUCTURED SELL-SIDE ASSUMPTION
SANHUA VALUE-ADDED SHARE OF BILLABLE CONTENT = NOT ESTABLISHED
70% LONG-RUN ECONOMIC SHARE = ASSUMPTION
CUSTOMER-SPECIFIC SECOND-SOURCE / ALLOCATION = NOT ESTABLISHED
ROBOT MAKE-BUY MIX = NOT ESTABLISHED
ROBOT MATURE GROSS MARGIN = NOT ESTABLISHED
ROBOT 10% NET MARGIN = ASSUMPTION
ROBOT YIELD = NOT ESTABLISHED
ROBOT UTILIZATION = NOT ESTABLISHED
ROBOT-SPECIFIC INVESTED CAPITAL = NOT ESTABLISHED
ROBOT INCREMENTAL ROIC = NOT ESTABLISHED
ROBOT OWNER CASH = NOT ESTABLISHED
ROBOT CARDINAL SUCCESS PROBABILITY = NOT ESTABLISHED
```

---

## 12. What has changed versus the original 35亿元 framing

Before:

```text
1m × 50k × 70% × 10%
= 35亿元
```

Now:

```text
1m planned / reference downstream scale
!= 1m realized annual output

CNY50k customer billable content
!= CNY50k Sanhua value added

mature value content
= architecture × component count × specification × mature price

70% headline / early share
!= 70% durable mass-production allocation

10% net margin
must survive purchased content
+ price-down
+ depreciation
+ ramp underutilization
+ R&D / SG&A

more vertical integration
can raise value capture
but also raises capital intensity

35亿元 accounting profit
!= 35亿元 owner cash
```

The Research has therefore moved materially closer to the stated objective:

> We can now explain several concrete industrial mechanisms by which Sanhua might or might not earn CNY3.5bn, and why the amount of capital required is inseparable from the answer.

But the owner-economics closure is not yet complete because robot-specific realized allocation, mature BOM / pricing, make-buy mix and invested capital remain undisclosed.

---

## 13. Supporting challenger files

- `docs/dogfood/sanhua-robot-35bn-proof-table-2026-09-03.md`
- `docs/dogfood/sanhua-robot-allocation-durability-challenger-2026-09-03.md`
- `docs/dogfood/sanhua-robot-commercialization-capital-sequence-2026-09-03.md`
- `docs/dogfood/sanhua-robot-industrial-ramp-outside-view-challenger-2026-09-03.md`
- `docs/dogfood/sanhua-robot-linear-actuator-value-capture-challenger-2026-09-03.md`
- `docs/dogfood/sanhua-robot-make-buy-linear-capital-challenger-2026-09-03.md`
- `docs/dogfood/sanhua-robot-margin-compensation-challenger-2026-09-03.md`
- `docs/dogfood/sanhua-robot-outside-view-ramp-return-challenger-2026-09-03.md`
- `docs/dogfood/sanhua-robot-realized-capital-attribution-challenger-2026-09-03.md`
- `docs/dogfood/sanhua-robot-value-content-price-down-challenger-2026-09-03.md`

These remain case-specific Research support. None are promoted into generic Kernel method / schema.

---

## 14. Next evidence priority

The next upgrade should come from evidence, not additional framework.

Priority order:

1. **Customer / allocation evidence** — customer or supplier proof of actual allocation by actuator type / robot generation.
2. **Sanhua make-buy evidence** — which motor / screw / reducer / encoder / sensor / controller content is already self-produced at batch-delivery stage.
3. **Robot-specific manufacturing evidence** — line capacity, output, yield, utilization, equipment and working capital.
4. **Realized commercial price / margin** — complete actuator quotation / realized revenue and gross profit.
5. **Architecture change evidence** — whether mass-production design removes content versus merely lowering component costs.

Until one of these appears, tighter point estimates would mostly hide the remaining unknowns rather than reduce them.
