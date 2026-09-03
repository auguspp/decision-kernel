# 山东黄金 — Resource / pure-commodity underwriting stress test

Status: **ZERO-SCHEMA DOGFOOD / UNDERWRITING-LANGUAGE STRESS TEST / NO NEW RESEARCH SCHEMA / NO CARDINAL PROBABILITY / NO ODDS / NO HUMAN DECISION**

Date: 2026-09-03  
Security: `600547.SH` 山东黄金

## Question

This case is not an attempt to create a `COMMODITY` Economic Species enum or a routing template.

It asks one narrower question:

> **When the external commodity price can dominate reported earnings, what analytic language best separates price luck, mine operating quality, depletion, and owner economics?**

China Shenhua is already present in the repository, but it is not a clean control for this question. Its existing thesis explicitly depends on the integrated coal / rail / port / power system buffering commodity-price weakness.

Shandong Gold is a better stress test because the load-bearing chain is much closer to the mine economics themselves:

```text
gold price
× mine-produced volume
- mine operating cost
→ mine margin / operating cash generation
-
sustaining capital
-
growth / development capital
+
reserve replacement / mine-life extension
→ normalized owner cash through the cycle
```

The purpose of this note is to test that language against a real 2026 H1 record, not to freeze a new valuation or trade view.

---

# 1. Source boundary

The Shanghai Stock Exchange lists Shandong Gold's 2026 half-year report and summary as disclosures dated 2026-08-29.

For this stress test, detailed report text and financial-note tables were inspected through public reproductions of that filing. These materials are sufficient to identify the correct underwriting frame, but this note does **not** create new checked-in `EvidenceArtifact` objects or a formal `ResearchSnapshot`.

Therefore:

> **This is a method / frame dogfood, not a new authoritative Research freeze.**

Any future formal Shandong Gold Research must reacquire and qualify the exact official filing Evidence under the normal PIT / Claim Audit discipline.

Particularly important: exact mine-level unit cash cost / AISC and sustaining-capex data are **not** mechanically established by this note. Public sell-side calculations may help define what to investigate, but they are not substituted for primary realized Evidence here.

---

# 2. Why consolidated revenue is a bad first-order mining KPI

## 2026 H1 reported group result

The company reported:

- revenue: **RMB53.588bn**, down **5.60%** YoY;
- profit before tax: **RMB8.156bn**, up **48.74%**;
- attributable net profit: **RMB3.543bn**, up **26.17%**;
- weighted ROE: **10.15%**, up 0.34 percentage points;
- operating cash flow: **RMB7.771bn**, down **26.01%**.

If the analysis starts from consolidated revenue, the first impression is “business contracted.”

The filing itself says the revenue decline was mainly caused by lower **purchased-gold revenue**, and the cost decline was mainly caused by lower **purchased-gold cost**.

The product split makes the distortion explicit:

| 2026 H1 product | Revenue | Cost | Approx. gross margin |
|---|---:|---:|---:|
| self-produced gold | RMB20.558bn | RMB8.979bn | 56.32% |
| purchased gold | RMB17.498bn | RMB17.414bn | 0.48% |
| small gold bars | RMB8.743bn | RMB8.631bn | 1.28% |
| trading | RMB4.524bn | RMB4.551bn | -0.61% |
| other | RMB2.264bn | RMB0.919bn | 59.43% |

The implication is strong:

```text
large portions of consolidated revenue
= low-margin gold pass-through / trading activity
```

while:

```text
self-produced mine gold
= the economically load-bearing margin pool
```

So this case provides a clean negative control against the generic shortcut:

```text
revenue growth
→ operating strength
```

For Shandong Gold, that shortcut can point in the wrong direction.

---

# 3. Load-bearing uncertainty

The central uncertainty is not simply:

> Will the gold price remain high?

That is important, but it is an external state variable, not a complete underwriting question.

The more useful question is:

> **Can the company convert a favorable gold-price environment into durable per-share owner cash while restoring mine volume, controlling the cost curve, funding major development, and replacing depleted resources?**

That requires separating at least five nodes:

1. commodity price;
2. mine-produced volume / grade / recovery / downtime;
3. unit operating economics;
4. sustaining versus growth / development capital;
5. reserve replacement and future mine life.

Balance-sheet funding sits across all five.

---

# 4. Node A — Gold price is an external economic input, not evidence of operating quality

The 2026 H1 result occurred in a high-gold-price environment.

That environment can increase the revenue and margin of every ounce produced without management improving the physical mine system at all.

Therefore the causal chain must keep two statements separate:

```text
gold price higher
→ each produced unit is economically more valuable
```

and:

```text
mine operating system improved
→ more / cheaper / higher-recovery gold can be produced sustainably
```

The first can improve profit even while the second deteriorates.

This is exactly what makes commodity underwriting vulnerable to false confidence from current earnings.

A higher spot price can hide:

- lower production;
- worse grade;
- higher unit cost;
- temporary regulatory downtime;
- underinvestment in sustaining capital;
- reserve depletion;
- poor acquisition economics.

Therefore current-period earnings must not be treated as normalized earnings merely because their accounting provenance is clean.

---

# 5. Node B — H1 volume fell sharply, and the cause matters

## Realized record

2026 H1:

- mine-produced gold production: **19.10 tonnes**, down **22.70%** YoY;
- mine-produced gold sales: **19.96 tonnes**, down **15.42%**;
- overseas mine gold production: **6.69 tonnes**, up **18.03%**.

The company said Namdini improved mining volume, ore supply, processing throughput and recovery, with production growth above 50%.

Domestic operations faced a different problem. The company was simultaneously responding to upgraded safety regulation and accelerating major resource-integration projects in the Yantai region. It explicitly said that coordinating construction and production reduced production working faces and was expected to affect 2026 mine-gold production and operating targets, with the exact impact still uncertain.

## Underwriting implication

A 22.7% production decline is not one homogeneous signal.

It may contain:

```text
regulatory / safety normalization
+
construction interference
+
asset-specific operating performance
+
grade / recovery / mine-sequencing effects
```

These have very different terminal meanings.

The temptation to label the decline “one-off” should be resisted until evidence shows:

- affected working faces return;
- construction milestones are actually delivered;
- production recovers without degrading safety or cost;
- grade and recovery remain economically acceptable.

Likewise, higher overseas production is encouraging but cannot simply be netted against domestic shortfall without understanding mine-level economics.

---

# 6. Node C — Mine unit cost is load-bearing, and it is currently an evidence gap

A miner cannot be underwritten from price and volume alone.

The causal relationship is closer to:

```text
realized gold price
- mine unit operating cost
= unit mine margin
```

and then:

```text
unit mine margin
× sustainable mine volume
- sustaining capital
= pre-financing owner cash
```

The current H1 public record clearly shows strong self-produced-gold gross economics at the product level. However, this note has **not** frozen an exact primary-source mine-level unit cash-cost or AISC series with sufficient scope consistency for deterministic replay.

That distinction matters.

A sell-side analyst can estimate a unit cost by dividing selected reported cost lines by ounces or grams. The arithmetic may be deterministic, but the result is still an `ANALYST_MODEL` unless the cost scope is proven to match the production denominator.

Possible hidden scope differences include:

- mining versus processing cost;
- royalties / resource taxes;
- site G&A;
- stripping treatment;
- by-product credits;
- sustaining capital;
- inventory movement;
- domestic versus overseas mine mix.

Therefore:

> **No formal cost-curve conclusion is authorized by this stress test.**

This is a useful failure mode in itself: the frame tells us exactly what evidence is missing.

---

# 7. Node D — Capital spending must be split by economic purpose

## Realized H1 cash record

The group reported:

- operating cash flow: **RMB7.771bn**;
- investing cash flow: **-RMB8.676bn**;
- cash paid to acquire / construct fixed assets, intangible assets and other long-term assets: **RMB5.870bn**.

The company also disclosed substantial construction activity across major mine-development projects.

Examples include:

- Jiaojia integrated gold-resource development;
- Xincheng integrated development;
- Sanshandao expansion / development;
- Namibia Twin Hills development.

The 2026 annual planning statement had already indicated a very large investment program, including construction and intangible-asset investment.

## Underwriting implication

For mining, simply subtracting all investment cash flow from OCF and calling the residual “normalized FCF” is too crude.

The capital needs to be separated into at least:

```text
A. sustaining / safety / replacement capex
   required to preserve current productive capacity

B. development / growth capex
   intended to create future capacity or extend mine life

C. resource / mineral-right acquisition
   intended to replace or enlarge the depleting resource base

D. non-operating financial investment
   economically different from mine reinvestment
```

The H1 report provides enough evidence to see that major development is occurring, but it does not give this stress test a clean, mechanically complete sustaining-versus-growth split.

Therefore current OCF minus total investing cash flow is **not** accepted as normalized owner cash.

---

# 8. Node E — Reserve replacement is maintenance economics, not optional storytelling

A mine is a depleting asset.

Even if current production and margin are excellent:

```text
ore extracted today
→ resource base is consumed
```

So reserve / resource replacement is economically closer to maintenance of future earning power than a generic “optionality” story.

In 2026 H1 the company reported:

- exploration spending of roughly **RMB300m**;
- approximately **290,000 metres** of exploration work;
- approximately **20 tonnes** of newly added gold metal from exploration work.

The company was also acquiring / advancing mineral rights and large integrated development projects.

This means the owner-economics chain has to include:

```text
current ounces produced
vs
new economically recoverable ounces added
vs
capital required to discover / acquire / develop them
```

A company can report excellent spot-cycle earnings while destroying long-run owner value if replacement ounces become much more capital-intensive.

Conversely, development spending can temporarily depress cash flow while improving future mine life and productive capacity.

That is why resource replacement must not be collapsed into either:

- “capex bad”; or
- “resources good.”

The economic question is replacement quality per unit of owner capital.

---

# 9. Expansion is real; future production should not be treated as already realized

The report lists large projects and feasibility-study production expectations, including major capacity from Jiaojia, Xincheng and Twin Hills.

Those figures are useful as project commitments / planning inputs.

They are **not realized production**.

The correct chain is:

```text
project approved / under construction
→ construction progress
→ commissioning
→ ramp
→ achieved throughput
→ achieved grade / recovery
→ achieved unit economics
```

Skipping directly from project design capacity to terminal production is exactly the sort of inference compression Decision Hygiene is supposed to prevent.

This is especially important because current domestic production has already been affected by construction / safety coordination.

The same development program can therefore create both:

```text
near-term production headwind
AND
possible future capacity / mine-life benefit
```

without contradiction.

---

# 10. Balance sheet matters because the resource base is capital hungry

At 2026 H1 the reported asset-liability ratio was approximately **61.90%**, versus 62.21% at 2025 year-end.

The absolute level alone does not determine whether leverage is excessive.

The more decision-useful question is:

> **Can mine cash generation fund safety, sustaining needs, reserve replacement and the major project pipeline without making owner value increasingly dependent on high gold prices and external financing?**

That means future monitoring should connect:

```text
gold-price sensitivity
+
unit mine margin
+
project capex schedule
+
debt / interest burden
+
future production ramp
```

rather than treating leverage as an isolated ratio.

---

# 11. The H1 record is a negative control against two common errors

## Error A — consolidated revenue as operating truth

H1 gives:

```text
total revenue -5.6%
```

while:

```text
attributable profit +26.2%
self-produced-gold revenue +20.9%
```

because low-margin purchased-gold activity contracted sharply.

Therefore consolidated revenue growth is not a clean signal of mine economic growth.

## Error B — profit growth as proof of better normalized economics

At the same time:

```text
mine-produced gold volume -22.7%
```

while high gold prices supported strong self-produced-gold economics.

Therefore profit growth is also not sufficient proof that normalized mine economics improved.

Both errors can be true simultaneously:

```text
revenue can look weak for the wrong reason
AND
profit can look strong for an incomplete reason
```

That is exactly why the causal frame matters before probability or valuation.

---

# 12. What normalized earnings would actually require

A credible normalized-earnings estimate would need explicit assumptions for at least:

1. normalized gold-price state or price distribution;
2. sustainable mine-produced volume by major asset;
3. grade / recovery / operating downtime;
4. comparable unit mine cost;
5. sustaining capital;
6. development capex and ramp schedule;
7. reserve replacement economics;
8. financing / debt burden;
9. tax / royalty regime;
10. minority interests where relevant.

The current stress test does not establish those inputs tightly enough for a cardinal terminal distribution.

Most importantly, it would be poor discipline to choose one “normalized gold price” simply because a valuation model requires a number.

Commodity-price normalization is itself a model assumption that needs an explicit basis and sensitivity structure.

---

# 13. Probability status

The 2026 H1 evidence is sufficient to establish several important facts:

- consolidated revenue is structurally contaminated by low-margin pass-through activity;
- mine-produced-gold economics are more load-bearing than consolidated revenue;
- production volume is currently under pressure;
- domestic safety / construction effects are material and unresolved;
- major mine development is consuming capital;
- resource replacement is economically necessary;
- exact normalized unit-cost / sustaining-capex evidence remains incomplete.

It is **not** sufficient to establish a trustworthy cardinal probability distribution over future owner value.

Therefore:

```text
RESOURCE / COMMODITY FRAME = ESTABLISHED
H1 REALIZED ECONOMIC TENSIONS = ESTABLISHED
NORMALIZED GOLD PRICE = NOT ESTABLISHED
NORMALIZED UNIT COST = NOT ESTABLISHED
SUSTAINING CAPEX = NOT ESTABLISHED
NORMALIZED OWNER CASH = NOT ESTABLISHED
CARDINAL PROBABILITY = NOT ESTABLISHED
FRESH NUMERICAL ODDS = WITHHELD
HUMAN DECISION = NONE
ACTION = NONE
```

---

# 14. Next discriminating evidence

A future formal Shandong Gold Research pass should prioritize evidence that completes the causal chain rather than collecting generic mining ratios.

## Price / realization

- exact realized mine-gold selling price by period if officially disclosed;
- hedging / price-protection effects and their scope;
- separation of spot-price benefit from operating changes.

## Physical operations

- mine-produced volume by major mine;
- ore grade;
- recovery rate;
- throughput;
- regulatory / safety downtime;
- working-face restoration after current construction interference.

## Unit economics

- exact comparable mine-level cash-cost definition;
- AISC or equivalent if officially disclosed with scope;
- royalty / resource-tax treatment;
- domestic / overseas cost split;
- strip / development accounting.

## Capital

- sustaining versus growth capex;
- project-by-project remaining capex;
- commissioning and ramp milestones;
- actual versus feasibility-study throughput and economics.

## Depletion / replacement

- reserves and resources under a consistent technical standard;
- depletion during production;
- exploration additions;
- acquisition additions;
- cost per replacement ounce;
- mine-life extension achieved per unit of owner capital.

## Owner economics

- OCF after tax normalization;
- sustaining cash requirement;
- debt and interest burden;
- distributions;
- per-share owner cash through different gold-price states.

---

# 15. Method disposition

```text
PURE-RESOURCE FRAME STRESS TEST = USEFUL
CONSOLIDATED REVENUE AS PRIMARY GROWTH SIGNAL = REJECTED
CURRENT PROFIT GROWTH AS NORMALIZED EARNINGS PROOF = REJECTED
PRIMARY LANGUAGE = PRICE × VOLUME × UNIT COST → CAPITAL → RESERVE REPLACEMENT → OWNER CASH
COMMODITY PRICE = EXTERNAL STATE, NOT MANAGEMENT QUALITY
RESERVE REPLACEMENT = LOAD-BEARING MAINTENANCE ECONOMICS
PROJECT DESIGN CAPACITY = NOT REALIZED PRODUCTION
SELL-SIDE UNIT-COST BACKSOLVE = ANALYST_MODEL, NOT PRIMARY REALIZED FACT
NEW COMMODITY ENUM / SPECIES ROUTER = NO
NEW KERNEL SCHEMA = NO
CARDINAL PROBABILITY = NOT ESTABLISHED
ODDS = WITHHELD
HUMAN DECISION / ACTION = NONE
```

The useful lesson is not “gold miners use a mining template.”

It is:

> **When reported accounting scale is dominated by commodity pass-through and spot-price effects, underwriting must move down to the physical economic chain before valuation becomes more detailed.**
