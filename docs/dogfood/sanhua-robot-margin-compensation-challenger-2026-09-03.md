# Sanhua Robot Margin-Compensation Challenger — 2026-09-03

Status: **RESEARCH CHALLENGER SUPPORT / STATE-CONSISTENCY TEST / NO FORECAST / NO RECOMMENDATION**  
Security: **三花智控 / 002050.SZ / 02050.HK**  
Parent challenger: `docs/dogfood/sanhua-robot-operating-economics-challenger-2026-09-03.md`  
Prepared against main: `9fb517c9592d4c5969907bdb7b7219f78097cdb5`  
Investment Authority: **NONE**

## 0. Question

The familiar sell-side success state is:

```text
1.0m robots
× CNY50k Sanhua billable value / robot
× 70% share
× 10% net margin
= CNY3.5bn net profit
```

Earlier challenger work independently found that both mature value content and mature share are less stable than the headline state implies.

This note asks:

> If mature share and / or mature value content are lower, what net margin would be required to preserve the same CNY3.5bn profit target?

This is pure reverse arithmetic.

It is **not** a forecast of Sanhua robot margin.

---

## 1. Required-margin map for the same CNY3.5bn profit

Formula:

```text
required net margin
=
CNY3.5bn target profit
/
(1.0m robot units × mature value content × Sanhua share)
```

### Case A — headline sell-side state

```text
CNY50k value
× 70% share
→ CNY35.0bn Sanhua robot revenue

required net margin = 10.0%
```

This simply reproduces the headline arithmetic.

### Case B — mature share falls to 50%

```text
CNY50k
× 50%
→ CNY25.0bn revenue

required net margin = 14.0%
```

### Case C — alternative Dongwu mature value, share remains 70%

Sibling research identified a separate Dongwu robot-industry mature-state bridge of approximately:

```text
CNY38,975 actuator value / robot
≈ CNY39k
```

At 70% share:

```text
CNY38,975
× 70%
× 1.0m
→ CNY27.2825bn revenue

required net margin ≈ 12.83%
```

### Case D — lower mature value and 50% mature share

```text
CNY38,975
× 50%
× 1.0m
→ CNY19.4875bn revenue

required net margin ≈ 17.96%
```

### Case E — CNY42k mechanical screw-price sensitivity, 70% share

The sibling value-content challenger showed a narrow mechanical sensitivity in which lower roller-screw pricing could reduce the literal CNY54k body-actuator bridge to roughly CNY42k if all other content stayed unchanged.

At 70% share:

```text
CNY42k × 70% × 1.0m
= CNY29.4bn revenue

required net margin ≈ 11.90%
```

At 50% share:

```text
CNY42k × 50% × 1.0m
= CNY21.0bn revenue

required net margin ≈ 16.67%
```

All cases above are `DERIVATION` only.

---

## 2. The compensation problem

The headline success state looks like four independent assumptions:

```text
units
× value
× share
× margin
```

But once the target profit is held fixed, the variables become compensating requirements.

If:

```text
mature billable value falls
and / or
mature share falls
```

then:

```text
required unit volume must rise
or
required net margin must rise
```

The combined mature-state challenge is therefore stronger than examining each assumption one at a time.

Example:

```text
CNY50k / 70% / 10%
```

can become:

```text
CNY39k / 50% / ~18%
```

if unit volume is held at 1m and profit is still forced to CNY3.5bn.

That ~18% number is **not** a forecast or fair-margin estimate.

It is the margin the arithmetic would require to rescue the same profit state under the alternative mature value / share assumptions.

---

## 3. Compare the required margin with observable Sanhua economics — carefully

### 3.1 Current company economics

**FACT — Sanhua 2026H1**:

```text
total company revenue      ≈ CNY16.90bn
company gross margin       ≈ 28.06%
company attributable NP    ≈ CNY2.044bn
attributable net margin    ≈ 12.1%
```

Automotive components:

```text
revenue                     ≈ CNY6.455bn
gross margin                ≈ 27.56%
```

These are mature / scaled company economics and include businesses with long operating histories.

They are **not** robot margins.

### 3.2 What can and cannot be inferred

The original 10% robot net-margin assumption is not obviously impossible merely because robot products are new.

Sanhua as a company is capable of producing low-teens net margins on roughly high-20s gross margins at scale.

But that does not establish the robot business can do the same after:

```text
customer price-down
purchased reducer / screw / sensor content
precision-manufacturing depreciation
ramp underutilization
scrap / rework / warranty
robot-specific R&D
new production facilities
```

More importantly, once the other mature assumptions weaken, the profit state can require **14-18%** robot net margins rather than 10%.

Those higher required margins are materially more demanding than the original scenario.

---

## 4. Adjacent reference classes constrain the margin story

### 4.1 Tuopu — realized early-ramp actuator GM

**FACT — 2025**:

```text
robot actuator revenue = CNY13.591m
gross margin = 28.25%
```

**FACT — 2026H1**:

```text
robot actuator revenue = CNY14.048m
gross margin ≈ 27.0%
```

This is a real actuator-business gross-margin reference, but public volume / allocation remains undisclosed.

It does not provide robot-segment net margin.

### 4.2 Zhongda Leader — integrated robot-component project model

**MARKET_CONTEXT / MANAGEMENT PROJECT MODEL** — at maturity:

```text
gross margin = 25.84%
net margin   = 7.31%
post-tax IRR ≈ 12.21%
```

This demonstrates that an integrated robot-component success-case model can lose a large part of gross margin through operating expenses, depreciation and tax before reaching net profit.

### 4.3 Green Harmonic / Leaderdrive

**FACT** — its industrial + embodied-intelligence robot-parts category reported gross margin in the mid-30s in 2025, while the company also highlighted price pressure and ramp depreciation as margin risks.

Again, this is not Sanhua net-margin evidence.

---

## 5. Gross-margin headroom test

Without guessing Sanhua robot opex, the Research can still pose a simple accounting constraint.

If mature robot gross margin were somewhere around observable adjacent references of roughly high-20s to mid-30s, then a required net margin of:

```text
10%
```

leaves meaningful gross-profit headroom for:

```text
R&D
SG&A
warranty
other operating costs
tax
```

A required net margin approaching:

```text
18%
```

leaves much less headroom.

This does **not** prove 18% is impossible.

It means the burden of proof becomes much higher: the business would need unusually strong operating leverage / vertical integration / pricing / cost execution while mature value content and share are simultaneously lower.

That compensation mechanism is currently `NOT ESTABLISHED`.

---

## 6. Capital makes margin compensation even harder to treat as owner economics

Even if accounting net margin rises enough to preserve CNY3.5bn profit, that does not close owner economics.

A higher-margin outcome achieved through more vertical integration can require:

```text
more grinding / machining equipment
more metrology / test equipment
more tooling
more working capital
more development capital
```

So:

```text
higher captured margin
```

can coexist with:

```text
higher invested capital
```

The correct owner-economics question is therefore not:

> Can net margin reach 14% or 18%?

It is:

> If margin rises because Sanhua internalizes more value, what incremental capital is required to produce that margin, and what ROIC / owner cash results?

That denominator remains `NOT ESTABLISHED`.

---

## 7. State-consistent profit table

Assuming 1.0m downstream robot units:

| Mature Sanhua billable value / robot | Mature share | Sanhua revenue | Net margin needed for CNY3.5bn profit |
| ---: | ---: | ---: | ---: |
| CNY50,000 | 70% | CNY35.0bn | **10.0%** |
| CNY50,000 | 50% | CNY25.0bn | **14.0%** |
| CNY42,000 | 70% | CNY29.4bn | **11.9%** |
| CNY42,000 | 50% | CNY21.0bn | **16.7%** |
| CNY38,975 | 70% | CNY27.28bn | **12.8%** |
| CNY38,975 | 50% | CNY19.49bn | **18.0%** |

The table is a `DERIVATION` matrix, not a forecast matrix.

It makes the success-state compensation requirement visible.

---

## 8. Current margin verdict

The strongest conclusion is **not**:

```text
10% robot net margin is wrong
```

Public evidence is not sufficient to make that claim.

The stronger and more defensible conclusion is:

```text
10% is only sufficient if the high value-content / high-share state also survives.
```

If mature value content and mature allocation are both lower, preserving CNY3.5bn profit requires a much more demanding margin state.

Therefore:

```text
10% SANHUA ROBOT NET MARGIN = ASSUMPTION
14-18% COMPENSATING NET MARGIN STATES = DERIVATION
EVIDENCE THAT MARGIN WILL COMPENSATE FOR LOWER SHARE / ASP = NOT ESTABLISHED
```

---

## 9. Source register

### Sanhua primary

- 2026H1 report — company revenue, profit and segment gross margins:  
  https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12550185&stockid=002050

### Tuopu primary

- 2025 annual report — robot-actuator revenue / cost / GM:  
  https://static.cninfo.com.cn/finalpage/2026-03-24/1225026446.PDF
- 2026H1 report — robot-actuator revenue / cost:  
  https://stock.stockstar.com/notice/SN2026082700051918.shtml

### Other reference-class sources

- Zhongda Leader / Leaderdrive sources are registered in `docs/dogfood/sanhua-robot-industrial-ramp-outside-view-challenger-2026-09-03.md`.

### Sell-side scenario context

- Dongwu value-content states are registered in `docs/dogfood/sanhua-robot-linear-actuator-value-capture-challenger-2026-09-03.md`.

---

## 10. Current challenger

The CNY3.5bn success state now has a clear combined-state test:

```text
if share falls
and value content falls
then margin must rise materially
or units must rise materially
```

No public evidence currently establishes that such compensation will occur.

That is a more useful Research statement than accepting or rejecting any one sell-side variable in isolation.