# Sanhua Core Valuation Underwriting — 2026-09-03

Status: **RESEARCH SUPPORT REPAIR / BOUNDED CHALLENGER RANGE / NO TOTAL-COMPANY ODDS**  
Security: **三花智控 / 002050.SZ / 02050.HK**  
Source Research: `research_cases/002050-sanhua-deep-research-v1.json`  
Prior audit: `docs/dogfood/sanhua-valuation-multiple-audit-2026-09-03.md`  
Publication anchor supplied by Human: **CNY36.3/share**  
Investment Authority: **NONE**

## Executive verdict

The prior multiple audit established that Sanhua Full Research v1's `24/25/28/30/35x` terminal P/E schedule was not independently underwritten.

This repair does **not** replace it with another guessed point multiple.

Instead it rebuilds the valuation stack in four layers:

```text
normalized core earnings
→ core quality / duration
→ bounded core valuation surface
→ residual price paid for durability + optionality + market expression
```

Current best bounded conclusion:

```text
2027 normalized core earning power: ~CNY4.7-5.1bn
Defensible core P/E challenger band: ~16-22x
Central challenger band: ~18-20x
Core equity value: ~CNY75-112bn
Central core equity value: ~CNY85-102bn
```

At the Human-supplied CNY36.3 anchor and roughly 4.1955bn shares, total equity value is about **CNY152.3bn / 1,523亿元**.

Therefore the current price contains a residual of roughly:

```text
CNY40-77bn / 401-771亿元
```

above the bounded core surface.

Under the central `CNY4.9bn × 18-20x` challenger, the residual is roughly **CNY54-64bn / 543-641亿元**, or about **CNY12.9-15.3/share**.

That residual is **not robot value**.

It can contain:

```text
premium core quality / duration
+ future core growth above the normalized anchor
+ liquid-cooling economics
+ robot economics
+ A-share market-expression premium
```

The important correction is:

> CNY36.3 should not be described as “a cheap mature core with robot/liquid-cooling for free.” A material part of today's price is already payment for future duration and optionality.

## 1. Why the sell-side CNY5.4-5.8bn 2027 range is not a clean core-earnings anchor

The frozen Research correctly reconstructed post-H1 2027 forecasts around CNY5.26-5.77bn, with a center around CNY5.45bn.

But this is **total-company sell-side expectation context**, not pure core earnings.

The reports themselves make that clear.

Examples:

- CICC cut 2027 net profit to CNY5.422bn because automotive growth slowed, while still framing data-center liquid cooling and robot actuators as growth curves.
- Soochow / 东吴 projects about CNY5.774bn in 2027 and explicitly titles the H1 note around robot actuator mass-production acceleration; the report describes liquid cooling as incremental space.
- Galaxy / 银河 projects roughly CNY5.48bn in 2027 and explicitly says growth is expected from computing liquid cooling and robot components.
- Guosheng and other post-H1 notes likewise discuss liquid cooling and humanoid-robot industrialization as contributors to the 2027-28 growth path.

Sources:
- https://finance.sina.com.cn/jjxw/2026-08-28/doc-inipwhrr4500381.shtml
- https://www.sdyanbao.com/detail/988150
- https://stock.finance.sina.com.cn/stock/go.php/vReport_Show/kind/search/rptid/841328520366/index.phtml
- https://basic.10jqka.com.cn/144/002050/worth.html

Therefore:

```text
2027 sell-side total-company NP
!=
2027 normalized mature-core NP
```

Using CNY5.45bn as “core” and then adding robot/liquid-cooling optionality again would risk double counting.

## 2. Rebuild normalized 2027 core earning power

### 2.1 Observed base

2025 actual:

- revenue CNY31.01bn;
- deducted net profit CNY3.958bn;
- reported parent net profit CNY4.063bn;
- operating cash flow CNY5.091bn;
- weighted ROE 15.80%.

2025 segment economics:

- refrigeration revenue CNY18.585bn, +12.22%, gross margin 28.77%;
- automotive revenue CNY12.427bn, +9.14%, gross margin 28.79%.

2026H1:

- revenue CNY16.90bn, +3.92%;
- deducted net profit CNY2.147bn, +6.82%;
- OCF roughly CNY2.50bn;
- refrigeration revenue CNY10.445bn, +0.54%, gross margin about 28.37%;
- automotive revenue CNY6.455bn, +9.89%, gross margin about 27.56%.

Sources:
- https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12012988&stockid=002050
- https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12550185&stockid=002050

The observable core is therefore still a good business, but it is not currently hypergrowth.

### 2.2 2026 normalized bridge

CICC's post-H1 reported-profit estimate is about CNY4.397bn for 2026.

H1 also contained a CNY0.293bn FX loss and investment-market losses. Those items make headline net profit a noisy measure of operating earning power, but they should not simply be added back one-for-one as permanent earnings.

The safer underwriting interpretation is:

```text
2026 normalized core earning power ≈ CNY4.4-4.6bn
```

This is a bounded inference, not a reported fact.

It is supported by:

- H1 deducted profit annualizing to roughly CNY4.3bn before any H2 growth;
- stable ~28% gross margins;
- positive but moderate core segment growth;
- strong cash conversion;
- no evidence that a large robot/liquid-cooling profit contribution is already separately material.

### 2.3 2027 core growth bridge

A core-only 2027 growth rate should be driven by the two observable businesses, not by the total-company sell-side headline.

A useful bounded driver surface is:

```text
refrigeration: low-single-digit growth
+ automotive: high-single / low-double-digit growth
+ broadly stable gross margin
+ modest operating leverage / mix
```

At H1 mix, that implies roughly mid-single-digit core revenue growth, with core earnings growth somewhat higher if mix and efficiency remain favorable.

The resulting 2027 normalized core earning-power range is:

```text
CNY4.7-5.1bn
```

Interpretation:

- below CNY4.7bn would imply a meaningful core slowdown / margin deterioration;
- CNY4.7-5.1bn can be explained by the currently observable refrigeration + automotive franchise and modest operating improvement;
- materially above CNY5.1bn increasingly needs stronger-than-current core acceleration and/or measurable contribution from liquid cooling / robots.

This range is deliberately lower than the CNY5.4-5.8bn total-company sell-side range because the latter explicitly includes emerging growth curves.

## 3. Core quality deserves a premium, but quality is not the same thing as 28x

Sanhua has several real quality attributes:

- stable segment gross margins around 27-29%;
- diversified global customer base;
- qualification / reliability barriers;
- strong 2025 OCF relative to net income;
- meaningful automotive thermal-management growth;
- long operating history and global manufacturing footprint.

But the capital profile matters too.

In 2025:

- OCF was about CNY5.09bn;
- cash paid for fixed assets / intangible assets / other long-term assets was about CNY3.15bn;
- fixed-asset depreciation was about CNY1.06bn, plus roughly CNY0.10bn right-of-use depreciation;
- R&D expense was about CNY1.37bn.

Source:
- https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12012988&stockid=002050

Some 2025 capex clearly supports future/new businesses and H-share-funded expansion, so it should not all be assigned to mature core maintenance.

Still, the business is not capital-light. A premium multiple must be earned through durable growth and returns on incremental capital, not just gross-margin stability.

## 4. Comparable-company lens

No peer is exact. The point is to bound the distribution, not to copy one ticker's P/E.

### 4.1 Direct / mature manufacturing anchors

**DunAn Environment / 盾安环境**

- direct refrigeration / thermal-control manufacturing exposure;
- current TTM P/E is around the low teens;
- Huatai's recent target framework used about 15x 2026E P/E.

Sources:
- https://caibaobang.cn/sanpk/mh-zbs?code=002050&tag=pe
- https://stock.10jqka.com.cn/20260827/c679353429.shtml

**DENSO**

- global, qualified automotive-parts manufacturer;
- forward P/E around 11.7x on 2026-09-03.

Source:
- https://stockanalysis.com/quote/tyo/6902/

These companies are not equivalent to Sanhua's exact growth / margin profile. They establish that “global qualified manufacturing” alone does not justify 25-30x.

### 4.2 Premium industrial / thermal anchors

**Modine**

- thermal-management company with strong data-center exposure;
- forward P/E roughly 22x;
- 2027 consensus revenue growth around 28%;
- 2027 consensus EPS growth around 50%.

Sources:
- https://stockanalysis.com/stocks/mod/
- https://stockanalysis.com/stocks/mod/forecast/

**Parker-Hannifin**

- forward P/E roughly 27x;
- ROIC around 16%;
- FY2027 organic sales guidance roughly 5.5-8.5%;
- adjusted segment operating margin guidance around 27.5-27.9%.

Sources:
- https://stockanalysis.com/stocks/ph/financials/ratios/
- https://www.sec.gov/Archives/edgar/data/76334/000007633426000082/exhibit991q4fy26.htm

**Trane Technologies**

- forward P/E about 26-27x;
- ROIC around 26.6%;
- 2027 consensus revenue growth about 9%;
- 2027 EPS growth about 15%.

Sources:
- https://stockanalysis.com/stocks/tt/financials/ratios/
- https://stockanalysis.com/stocks/tt/forecast/

**Eaton**

- forward P/E around 26x;
- supported by strong recent electrification / data-center growth and high margins.

Sources:
- https://stockanalysis.com/stocks/etn/financials/ratios/
- https://stockanalysis.com/stocks/etn/forecast/

The peer conclusion is not “Sanhua should trade at DENSO's 12x” or “Sanhua should trade at Trane's 27x.”

It is:

```text
low/mid teens = mature qualified manufacturing anchor
low 20s = strong thermal / industrial growth franchise
mid/high 20s = premium-compounder territory that needs stronger duration / return proof
```

Sanhua's mature core deserves to sit above the first bucket, but current evidence does not support treating the premium-compounder bucket as the default core valuation.

## 5. Same-company A/H lens

CICC's post-H1 note used the same 2027 earnings estimate of about CNY5.422bn for one consolidated company, while the two market expressions traded at roughly:

- A share: 28x 2027E;
- H share: 17x 2027E.

Source:
- https://finance.sina.com.cn/jjxw/2026-08-28/doc-inipwhrr4500381.shtml

This is powerful because it removes the business from the comparison.

The earnings, products, robot program, liquid-cooling program and cash flows are the same.

The market multiple is not.

Therefore a material portion of the A-share multiple is market expression / investor-base / liquidity / risk-appetite premium rather than pure business value.

The H-share 17x should not be treated as automatic fair value either. It is a lower market-expression anchor.

But this A/H spread makes it difficult to defend 28x as a neutral “core business multiple.”

## 6. Fundamental multiple sanity check

A justified-forward-P/E identity is useful only as a sensitivity check:

```text
justified P/E ≈ (1 - g / ROE) / (cost of equity - g)
```

Using round ROE of 16%:

| Cost of equity | g=4% | g=5% | g=6% |
| ---: | ---: | ---: | ---: |
| 8% | 18.8x | 22.9x | 31.3x |
| 8.5% | 16.7x | 19.6x | 25.0x |
| 9% | 15.0x | 17.2x | 20.8x |
| 9.5% | 13.6x | 15.3x | 17.9x |
| 10% | 12.5x | 13.8x | 15.6x |

This is not a canonical DDM.

Its diagnostic message is simple:

- ~16-20x can be supported by moderate long-run growth under non-aggressive return assumptions;
- >22x increasingly requires either a low required return or durable ~5%+ long-run growth;
- ~28x requires a strong long-duration growth / return combination and should not be the default for a mature core.

Market references around the date:

- China's 10-year government bond yield was below ~1.7%;
- Damodaran's latest country-risk datasets place China's total equity risk premium around the mid-5% range depending on method/update;
- Sanhua's measured historical beta is around 0.8 on common market-data services.

Sources:
- https://www.reuters.com/commentary/reuters-open-interest/china-escapes-global-bond-rout-wrong-reasons-mcgeever-2026-09-02/
- https://pages.stern.nyu.edu/adamodar/New_Home_Page/datafile/ctrprem.htm
- https://stockanalysis.com/quote/she/002050/

Those inputs are themselves model-sensitive, so this note intentionally does not derive one canonical cost of equity from CAPM.

## 7. Bounded core P/E range

Triangulating the three lenses:

```text
direct manufacturing anchors: ~12-15x
same-company H expression: ~17x total-company 2027E
premium thermal / industrial franchises: ~22-27x
fundamental sensitivity: high teens / low 20s under moderate assumptions
```

A defensible **core-only challenger band** is therefore:

```text
16-22x
```

with a central challenger of:

```text
18-20x
```

Interpretation:

- **16x**: still gives Sanhua a quality premium over several mature direct manufacturers;
- **18-20x**: pays for durable qualification barriers, stable margins and reasonable core compounding;
- **22x**: upper core boundary that requires stronger duration / reinvestment confidence;
- **25x+**: should no longer be treated as a clean mature-core multiple; it likely includes optionality / premium-duration / market-expression value;
- **28x+**: belongs in a total-company upside expression only after new-business economics or premium-compounder quality are demonstrated.

This band is a **research-supported challenger surface**, not a Constitution rule and not a universal manufacturing P/E table.

## 8. Core value at CNY36.3

Human publication anchor:

```text
price = CNY36.3
shares ≈ 4.1955bn
market cap ≈ CNY152.3bn / 1,523亿元
```

Using `CNY4.7-5.1bn` normalized 2027 core earnings:

| Core earnings | 16x | 18x | 20x | 22x |
| ---: | ---: | ---: | ---: | ---: |
| CNY4.7bn | 752亿 | 846亿 | 940亿 | 1,034亿 |
| CNY4.9bn | 784亿 | 882亿 | 980亿 | 1,078亿 |
| CNY5.1bn | 816亿 | 918亿 | 1,020亿 | 1,122亿 |

Equivalent core value/share:

| Core earnings | 16x | 18x | 20x | 22x |
| ---: | ---: | ---: | ---: | ---: |
| CNY4.7bn | 17.9 | 20.2 | 22.4 | 24.6 |
| CNY4.9bn | 18.7 | 21.0 | 23.4 | 25.7 |
| CNY5.1bn | 19.4 | 21.9 | 24.3 | 26.7 |

Residual versus CNY1,523亿元 current equity value:

```text
bounded surface: ~401-771亿元
central 4.9bn × 18-20x: ~543-641亿元
```

Equivalent residual per share under the central challenger:

```text
~CNY12.9-15.3/share
```

That is roughly **36-42% of the CNY36.3 share price**.

Again, this is not “robot value.”

It is the bill for everything that sits above normalized observable core earnings at the chosen core multiple.

## 9. What must justify the residual

The residual can be justified by several things, but each requires evidence.

### Core duration premium

Need evidence that refrigeration + automotive can keep compounding materially above mature-industrial rates without margin / cash-return decay.

### Liquid cooling

Current evidence proves commercialization and some global customer supply.

Still missing:

```text
revenue
→ gross margin
→ operating profit
→ capital intensity
→ cash conversion
→ repeatable ROIC
```

### Robot actuators

Current evidence proves batch delivery and production-line ramp.

Still missing:

```text
allocation / customer scale
→ volume
→ ASP
→ revenue
→ margin
→ utilization
→ repeatable profit / ROIC
```

### A-share market-expression premium

The A/H spread proves this premium can be large.

It cannot be treated as permanent fundamental value.

## 10. Research correction to the old CNY30 participation trigger

The historical Human record remains:

```text
CONDITIONAL BUY
around CNY30 first tranche
NOT EXECUTED
```

This note does not rewrite that Human Decision.

But its Research support changes materially.

At CNY30, equity value would still be roughly CNY126bn using current shares.

Under the central core challenger (`CNY4.9bn × 18-20x`), that would still leave about CNY28-38bn of residual future / premium value.

Therefore CNY30 is **not** automatically “core value with optionality free” under the repaired valuation method.

The old participation trigger should remain historically recorded but be **re-underwritten before use**.

## 11. Current Research stance

```text
CORE BUSINESS QUALITY = GOOD / SUPPORTED
2027 NORMALIZED CORE EARNING POWER = ~CNY4.7-5.1bn CHALLENGER RANGE
CORE P/E = ~16-22x CHALLENGER RANGE
CENTRAL CORE P/E = ~18-20x
CNY36.3 TOTAL EQUITY VALUE = ~CNY152.3bn
RESIDUAL ABOVE CORE = MATERIAL (~CNY40-77bn)
ROBOT / LIQUID COOLING ECONOMICS = NOT YET QUANTIFIED
TOTAL-COMPANY CARDINAL PROBABILITY = NOT ESTABLISHED
TOTAL-COMPANY NUMERICAL ODDS = WITHHOLD
```

The next real evidence that should move this valuation is not another TAM estimate or customer-name headline.

It is measurable economics from liquid cooling / robot actuators, or a material change in the core growth / margin / cash-return path.

## 12. Publication consequence

The Xiaohongshu article should now be framed around:

> **CNY36.3 buys a real, high-quality core plus a material amount of prepaid future. The question is how much of the CNY400-700bn residual can eventually become durable earnings rather than remaining an A-share narrative / duration premium.**

Do not publish the private Human CNY30 trigger, position state or Decision/Action state.
