# Micron SCA Floor-Economics Underwriting — 2026-09-03

Status: **FROZEN DECISION-USE RESEARCH SUPPLEMENT / US EQUITY / NO HUMAN DECISION / NO NUMERICAL ODDS / NO KERNEL CHANGE**  
Security: **Micron Technology / MU / NASDAQ**  
Parent research: `docs/dogfood/micron-decision-hygiene-zero-schema-2026-09-03.md`  
Public evidence cutoff: **2026-09-03 12:08 +08:00**  
Last completed U.S. market session used only as MARKET_CONTEXT: **2026-09-02**  
Public price context: **approximately USD956/share**  

---

## 0. Research question

The first Micron dogfood concluded that the apparent ~6x FY2027E P/E is not the correct investment question.

The load-bearing question is:

> **Do Micron's Strategic Customer Agreements (SCAs), HBM / AI-memory product mix, and capital structure materially raise post-cycle normalized owner earnings and free cash flow, or do they merely make an exceptional 2026-27 peak look safer than it is?**

This supplement attempts to finish that question as far as current public evidence allows.

It does not create:

- a Human investment decision;
- a complete cardinal probability distribution;
- production `ObservedMarket` for a U.S. equity;
- production Numerical Odds;
- a provider abstraction or fallback market-data path;
- a target price or automatic entry band;
- a Kernel schema change.

---

## 1. What is actually proven about SCA structure

### 1.1 SEC filing facts — PRIMARY REALIZED / PRIMARY DISCLOSURE

Micron's fiscal Q3 2026 Form 10-Q states that the new strategic customer agreements:

- contain **binding commitments for specific volumes** over multi-year terms;
- are structured as **take-or-pay** agreements;
- generally use either fixed pricing or **minimum / maximum pricing bands**;
- have largest agreements with a price ceiling for existing products near calendar-Q2 2026 market prices and a floor price through the term;
- include a minority of agreements with no fixed price or price band and therefore market-based pricing;
- create legally enforceable volume commitments, but can still create litigation / customer-relationship risk if customers fail to perform and Micron must enforce contractual rights.

The 10-Q therefore supports a stronger statement than historical memory LTAs:

> **The volume commitment is legally structured, not merely a handshake planning arrangement.**

But it does **not** prove frictionless economic realization in a severe downturn.

A customer default, renegotiation attempt, dispute, bankruptcy, technology change or enforcement action can still turn contractual entitlement into a different economic outcome.

### 1.2 Contract coverage announced at Q3

At the June 24 earnings call Micron said it had signed **16 SCAs**:

```text
Typical large / medium SCA term: calendar 2026 through end-2030 (~5 years)
Automotive SCA term: generally ~3 years
Signed SCA coverage: ~20% of DRAM volume
Signed SCA coverage: ~1/3 of NAND volume
Management's Q&A translation: roughly ~25% of company revenue over the term
Large customers: 4
Medium customers: 3
Other signed SCAs: smaller automotive customers
```

Micron said the target state is approximately **half or more of company revenue** under SCAs.

Among planned SCAs, agreements with fixed pricing or price ceilings near the signing-date market level are expected to represent roughly **40% of company revenue**.

This distinction is crucial:

```text
SCA coverage != price-protected revenue coverage
signed coverage today != eventual target coverage
SCA floor gross margin != consolidated company floor gross margin
```

### 1.3 Price floors and ceilings

Micron's prepared remarks and 10-Q state that, for SCAs with price bands:

> the floor price is designed to produce Micron gross margin **well above the peak quarterly gross margin in any prior cycle**.

The historical pre-2026 peak is observable:

```text
FQ4 FY2018 GAAP gross margin ≈ 61.0%
FQ4 FY2018 non-GAAP gross margin ≈ 61.4%
```

Therefore management's statement implies a **greater-than-low-60s gross-margin floor on the revenue sold under price-banded SCAs**, not on total corporate revenue.

That is economically significant.

It is also still a **management forward statement**, not an outcome-tested fact.

### 1.4 New-product pricing is not simply frozen forever at 2026 prices

Q3 prepared remarks state that product transitions such as LP5→LP6, DDR5→DDR6 and newer HBM generations have rising bit costs, and that SCAs provide for **appropriate price premiums for new products to be negotiated in the future**.

This matters because a naive reading of the ceiling could otherwise imply that Micron has permanently sold next-generation products at 2026 price caps.

The available disclosure instead supports:

```text
existing-product price bands = bounded
new-product generations = future premium negotiation remains relevant
```

Exact mechanics are not publicly disclosed.

---

## 2. The RPO number is real but easy to misuse

### 2.1 Filed RPO at May 28

As of May 28, 2026, the 10-Q reported approximately:

```text
remaining performance obligations (RPO) = USD5bn
contract liabilities recognized = USD422m
~1/3 of then-existing RPO expected as revenue over next 12 months
```

Those numbers reflect agreements executed by the quarter-end cutoff.

### 2.2 Subsequent signed agreements

At the June 24 call, including agreements executed after May 28, management said:

```text
14 of 16 signed SCAs had cumulative minimum-price revenue ≈ USD100bn
cash deposits + related financial commitments ≈ USD22bn
cash component ≈ USD18bn
other financial commitments / letters of credit ≈ USD4bn
```

The company expects future revenue under these agreements to exceed the minimum-price RPO because the RPO uses minimum committed volume × minimum price and excludes agreements without price bands.

### 2.3 What the USD100bn does and does not mean

A crude even-year average over ~4.5 years is around USD22bn per year.

That average is **not** a forecast because contract timing is uneven.

It is useful only for scale intuition:

- USD100bn minimum contracted revenue is economically large;
- but it is not enough by itself to support Micron's current ~USD1.1tn equity value;
- it protects a meaningful slice of business economics, not the entire enterprise.

If one only uses the historical ~61% prior peak as a conservative lower reference for the company's phrase "well above prior peak" and applies it to an even USD22bn annualized minimum-revenue intuition, that would imply more than roughly USD13bn annual gross profit from that subset before company-wide operating expenses, tax and capital reinvestment.

This is an **illustration, not contractual timing or guaranteed annual profit**.

The implication is still useful:

> **SCA can materially cushion a downturn, but the initial signed contracts alone do not mathematically guarantee a USD50-100 normalized EPS floor.**

---

## 3. Customer deposits are commitment evidence, not free equity value

Micron said approximately USD18bn of the USD22bn financial commitments will be cash deposits.

The accounting / economic treatment is important:

```text
cash deposit != revenue prepayment
cash deposit != free cash flow
cash deposit != permanent owner cash
```

Management said:

- deposits are financing cash flows;
- they are unrestricted while held;
- they are returned to customers over time, heavily weighted toward the latter half of the agreements;
- the deposit demonstrates commitment and supports Micron's confidence when making large capital investments.

Therefore the correct owner-economics treatment is:

> **The deposits reduce financing / commitment risk and improve liquidity, but should not be capitalized as if they were permanent shareholder cash.**

They are economically closer to customer-backed funding / performance security than free owner capital.

This also prevents a subtle double count:

```text
SCA deposit
+ SCA future gross profit
```

cannot both be treated as unencumbered incremental equity value when the deposit is expected to be returned.

---

## 4. Are these contracts really harder than old memory LTAs?

### 4.1 Historical objection

Investors correctly remember that memory-industry LTAs have often failed to prevent boom-bust outcomes.

The strongest current objection is:

> even legally written long-term agreements can become economically renegotiated when an industry moves into severe oversupply.

Reuters explicitly highlighted this risk after Q3: analysts cautioned that the stability of new AI-linked contracts still depends on sustained end demand and that renegotiation risk could reintroduce volatility.

### 4.2 What is materially different this time

At Micron's August 10 KeyBanc appearance, Chief Business Officer Sumit Sadana said the old LTAs were mostly 12-month planning arrangements without binding terms, while the new SCAs have:

- annual customer-specific volume commitments;
- take-or-pay economics;
- **no contractual outs** according to management;
- substantial cash / letter-of-credit commitments;
- predominantly five-year duration through calendar 2030;
- evergreen structure that can add years to the back end;
- deeper R&D / product-roadmap collaboration.

Micron also said it had signed **additional SCAs after the June earnings call**.

This improves the quality of the business-model-change hypothesis.

It still does not eliminate counterparty / enforcement risk.

The 10-Q itself acknowledges that if customers fail to meet commitments, Micron may need to enforce contractual rights, potentially creating litigation or disputes.

So the Decision Hygiene classification is:

```text
contract hardness = materially stronger than old LTA structure
contract economic realization through a real downturn = not yet outcome-tested
```

---

## 5. The hidden shareholder trade: SCA floors are bought partly with SCA ceilings

The largest price-banded agreements generally have ceilings near market prices prevailing when signed.

That means SCAs are not a one-way free option for Micron shareholders.

They transform payoff shape:

```text
OLD MEMORY MODEL
very high peak pricing
+ very low / negative trough economics

SCA MODEL
some peak upside capped on covered revenue
+ materially stronger price / volume floor on covered revenue
```

This is exactly what a lower-volatility business model should look like.

If successful, shareholders may rationally accept somewhat less extreme peak capture in exchange for:

- lower trough loss;
- higher visibility;
- better capex planning;
- better financing efficiency;
- potentially higher valuation multiple on normalized earnings.

This is a **business-model volatility exchange**, not simply a bullish revenue contract.

---

## 6. SCA coverage mathematics — why company-wide gross margin is still uncertain

The most important modeling correction is to separate protected and unprotected revenue.

For illustration only, suppose the eventual price-protected / fixed-price portion is 40% of company revenue and the SCA price-banded gross margin floor is approximated at 62% merely to represent "above the historical ~61% peak."

Then consolidated gross margin still depends heavily on the other 60% of revenue.

Illustrative blend:

| Protected revenue share | Protected GM | Non-protected GM | Blended GM |
|---:|---:|---:|---:|
| 40% | 62% | 0% | 24.8% |
| 40% | 62% | 10% | 30.8% |
| 40% | 62% | 20% | 36.8% |
| 40% | 62% | 30% | 42.8% |

This table is not a forecast.

Its purpose is to show:

> **A very strong SCA gross-margin floor can dramatically reduce corporate downside without creating a 60%+ consolidated floor.**

Under the earlier signed coverage level of roughly 25% of revenue, the corporate cushion is smaller.

This is why current valuation cannot be justified by repeating the phrase "floor margins above past peaks" without doing the protected / unprotected mix decomposition.

---

## 7. Capital intensity remains the second load-bearing variable

Micron is not a fabless platform.

The same SCAs that make revenue more visible also give management confidence to fund enormous capacity expansion.

Current realized / guided context:

```text
FY2026 net capex guidance ≈ USD27bn
FQ4 FY2026 capex guidance ≈ USD10bn
FY2027 quarterly capex expected above FQ4 levels
more than half of FY2027 YoY capex increase expected from construction capex
Idaho ID1 first wafer output expected mid-calendar 2027
Idaho ID2 first wafer output expected late-calendar 2028
additional Taiwan / Singapore / Japan / New York expansion underway
```

Nine-month FY2026:

```text
OCF ≈ USD45.7bn
PP&E cash expenditures ≈ USD19.6bn
D&A ≈ USD6.86bn
net PP&E ≈ USD56.4bn vs ~USD46.6bn at FY2025 year-end
construction in progress ≈ USD10.9bn vs ~USD5.5bn
```

The correct causal chain is therefore:

```text
SCA / AI demand visibility
→ more committed capacity investment
→ future bit supply + product mix
→ realized gross margin
→ depreciation + capex burden
→ normalized FCF
→ incremental ROIC
```

A company can have a higher EPS floor and still produce disappointing owner returns if the capital required to sustain that floor rises too aggressively.

---

## 8. Historical negative control: what an old memory trough looked like

Fiscal 2023 provides a useful realized downside reference:

```text
FY2023 revenue ≈ USD15.54bn
GAAP gross margin ≈ -9.1%
GAAP operating loss ≈ USD5.75bn
GAAP net loss ≈ USD5.83bn
adjusted FCF ≈ -USD5.45bn
```

FQ3 FY2023 gross margin reached roughly **-17.8% GAAP**.

The SCA thesis does not need to prove that future downturns disappear.

It only needs to prove that the system can no longer fall anywhere close to this old economic floor on a comparable demand shock.

That is a much more testable claim.

---

## 9. Current peak economics are not the normalized base

FQ3 FY2026 realized:

```text
revenue ≈ USD41.46bn
GAAP gross margin ≈ 84.6%
GAAP operating margin ≈ 80.4%
GAAP net income ≈ USD28.24bn
GAAP diluted EPS ≈ USD24.67
OCF ≈ USD25.39bn
adjusted FCF ≈ USD18.3bn
```

FQ4 guidance:

```text
revenue ≈ USD50bn
GM ≈ 86%
non-GAAP EPS ≈ USD31
```

These are scarcity economics.

No decision-use valuation should capitalize 84-86% corporate gross margin as a permanent baseline.

---

## 10. Current market expectation is already extremely bullish on FY2027

Public market-context aggregation around 2026-09-02 shows approximately:

```text
FY2027 EPS consensus ≈ USD155-163
FY2027 estimate range ≈ roughly USD130-218 depending source / analyst set
FY2028 estimates remain very dispersed and use a much smaller analyst sample
```

At ~USD956/share, Micron therefore screens at only ~6x FY2027 consensus EPS.

This low multiple is not evidence that the market is asleep.

It is evidence that the market does **not trust FY2027 earnings as durable**.

The valuation debate is therefore correctly stated as:

> **What normalized EPS / FCF survives after scarcity pricing falls and new capacity arrives?**

---

## 11. Reverse underwriting from the current price

At approximately USD956/share, the normalized EPS required by alternative normalized P/E assumptions is:

| Normalized P/E | Required normalized EPS |
|---:|---:|
| 20x | ~USD48 |
| 18x | ~USD53 |
| 16x | ~USD60 |
| 15x | ~USD64 |
| 12x | ~USD80 |
| 10x | ~USD96 |

This is the cleanest current-price question.

The market is not merely pricing a 2027 peak.

At today's valuation, a serious long-term holder must be comfortable with some combination of:

- normalized EPS in the **USD55-80+** range;
- a materially higher normalized multiple than old commodity-memory valuation;
- or a longer scarcity duration that creates substantial owner cash before normalization.

---

## 12. A bottom-up normalized-earnings grid

The following grid is deliberately simple and probability-free.

Assumptions used only for mechanical illustration:

```text
normalized annual operating expense = USD10bn
normalized tax rate = 15%
diluted shares = 1.145bn
interest / below-operating items ≈ ignored for simplicity
```

Illustrative EPS by annual revenue / consolidated gross margin:

| Revenue | 35% GM | 45% GM | 55% GM | 65% GM |
|---:|---:|---:|---:|---:|
| USD100bn | ~18.6 | ~26.0 | ~33.4 | ~40.8 |
| USD130bn | ~26.4 | ~36.0 | ~45.7 | ~55.3 |
| USD160bn | ~34.1 | ~46.0 | ~57.9 | ~69.8 |
| USD190bn | ~41.9 | ~56.0 | ~70.2 | ~84.3 |

This table exposes the real burden of proof.

To justify a **USD60+ normalized EPS floor**, Micron broadly needs either:

- post-cycle revenue near / above ~USD160bn with consolidated GM around the mid-to-high 50s;
- or a larger revenue base with somewhat lower margins;
- or structurally lower opex / share count than this simple assumption.

SCA protection alone does not automatically create this result.

HBM / high-value mix, bit growth, differentiated products and post-cycle pricing power must also carry the thesis.

---

## 13. Four causal Research Worlds — no probabilities

### World A — Contracts help, commodity cycle still dominates

Causal chain:

```text
2027 peak pricing normalizes
+ non-SCA DRAM/NAND prices fall hard
+ SCA contracts protect only a minority / partial share
+ customers honor contracts but open-market economics weaken
+ capex / depreciation remain heavy
→ earnings floor improves from 2023 but remains far below current Street peak earnings
```

Illustrative normalized economics:

```text
revenue ~USD110bn
consolidated GM ~30%
opex ~USD10bn
normalized EPS ~USD17
```

At ~USD956, this world is extremely expensive.

### World B — Contract-cushioned normalization

Causal chain:

```text
SCA coverage grows toward target
+ price-band floors work as written
+ open-market pricing normalizes but does not collapse
+ HBM / server mix retains structural premium
+ capex remains high but productive
→ old negative-margin trough is eliminated
```

Illustrative normalized economics:

```text
revenue ~USD140bn
consolidated GM ~42%
opex ~USD10.5bn
normalized EPS ~USD36
```

At ~USD956, current price still implies ~27x this normalized EPS.

This world would prove the business improved materially but would not by itself make today's price obviously cheap.

### World C — Strategic-memory rebase

Causal chain:

```text
SCA floor / volume commitments work
+ HBM remains high-value and strategically differentiated
+ AI memory hierarchy sustains stronger DRAM / NAND mix
+ next-generation products receive negotiated price premiums
+ supply expansion does not destroy oligopoly discipline
+ owner cash exceeds growth reinvestment needs by a wide margin
→ normalized corporate margins rebase structurally higher
```

Illustrative normalized economics:

```text
revenue ~USD170bn
consolidated GM ~52%
opex ~USD11.5bn
normalized EPS ~USD57
```

At ~USD956, this is roughly **17x normalized EPS**.

This is close to the minimum world required for the current stock price to look like a reasonable long-duration owner price rather than merely a peak-cycle trade.

### World D — Long AI-memory scarcity + durable platform economics

Causal chain:

```text
memory shortage persists through / beyond 2028
+ SCA contracts extend / evergreen
+ HBM / server / SSD value density keeps rising
+ Micron sustains strong technology / power / product differentiation
+ capacity additions are absorbed by AI demand
+ post-cycle gross margin remains far above historical cycle norms
→ normalized EPS approaches high double / low triple digits
```

Illustrative normalized economics:

```text
revenue ~USD200bn
consolidated GM ~62%
opex ~USD12.5bn
normalized EPS ~USD83
```

At ~USD956, this is roughly **12x normalized EPS**.

This is the world in which today's price begins to look genuinely cheap without relying on a temporary FY2027 peak multiple.

---

## 14. Illustrative owner-cash bridge

EPS is not enough for a capital-intensive IDM.

A simple steady-state FCF stress can be used only to expose reinvestment burden.

Illustrative assumption:

```text
D&A ≈ 10% of revenue
capex ≈ 18% of revenue
net reinvestment ≈ 8% of revenue
```

This is **not** a forecast and should not be used as Numerical Odds.

Applying that bridge to the four illustrative worlds gives approximate FCF/share:

```text
World A: ~USD9/share
World B: ~USD26/share
World C: ~USD45/share
World D: ~USD69/share
```

At ~USD956 that corresponds to rough normalized FCF yields of:

```text
World A: ~1%
World B: ~3%
World C: ~5%
World D: ~7%
```

This reinforces the same conclusion as the EPS reverse underwriting:

> **Current valuation already requires a meaningful strategic rebase of post-cycle owner economics.**

The stock is not simply pricing an old memory company at a cheap peak multiple.

---

## 15. What evidence most increases confidence in World C/D

### 15.1 Full SCA RPO at the FY2026 10-K

The most immediate hard evidence will be the September 30 earnings / subsequent 10-K disclosure.

Important fields:

- total RPO after the large agreements signed in FQ4;
- next-12-month RPO recognition amount;
- total contract liabilities / deposits;
- updated number and coverage of SCAs;
- whether additional SCAs keep similar no-out / price-band economics;
- whether the eventual ~40% price-protected revenue target remains credible.

### 15.2 Gross-margin behavior as market prices moderate

The strongest eventual proof of SCA value is not another contract announcement.

It is:

```text
open-market memory ASP declines
while
Micron consolidated / protected gross margin remains materially above old-cycle behavior
```

Until that happens, the claimed floor is still prospective.

### 15.3 HBM and next-generation product economics

Need evidence that HBM value is durable rather than merely shortage rent:

- HBM4 / HBM4E qualification breadth;
- customer concentration / dual-source dynamics;
- pricing versus cost / yield / packaging burden;
- HBM trade ratio and effect on non-HBM supply;
- negotiated premium for new products inside SCAs;
- return on incremental HBM / advanced packaging capital.

### 15.4 Capex ROIC

Need to distinguish:

```text
high earnings because scarcity under-investment existed
from
high returns after the new capacity base is fully installed
```

Monitor:

- PP&E growth;
- construction-in-progress conversion;
- depreciation growth;
- bit output per invested dollar;
- normalized FCF after capex;
- excess-cash return versus permanent capital needs.

---

## 16. What evidence would falsify the business-model-transformation thesis

Material falsifiers include:

1. **SCA renegotiation / nonperformance becomes economically common.**
2. **RPO growth stalls far below targeted company-revenue coverage.**
3. **New SCAs move materially toward market-only pricing with weak floors.**
4. **Open-market downturn drives corporate GM back near old-cycle levels despite SCA coverage.**
5. **HBM / high-value product margins compress faster than cost / mix improvements.**
6. **New capacity materially overshoots demand after 2028.**
7. **Capex / depreciation consume most of the post-cycle earnings rebase.**
8. **Customer deposits / commitments prove weak protection in actual disputes.**
9. **China / competitor supply growth changes oligopoly economics faster than expected.**
10. **2030+ normalized revenue / margin cannot support at least a mid-50s EPS floor while current valuation remains near today's level.**

---

## 17. The current strongest and weakest statements

### Strongest supportable statement

> **Micron has created a materially stronger contractual business structure than its historical memory LTAs: multi-year take-or-pay volume commitments, substantial customer cash / LC commitments, and price bands whose disclosed floors are designed to produce very high gross margins on protected revenue. This should materially reduce the severity of a future memory downturn if customers perform and if protected revenue coverage reaches management's targeted scale.**

### Statement that is not yet supportable

> **Micron now has a company-wide 60%+ gross-margin floor or a proven USD70-100 normalized EPS floor.**

The evidence does not establish that.

### Most important inference

> **SCA is probably a real trough-cushion mechanism, but today's ~USD956 valuation already requires more than trough cushioning. It requires a structural post-cycle earnings rebase driven jointly by contracts, HBM / AI-memory mix, durable revenue scale and acceptable reinvestment economics.**

---

## 18. Probability qualification

Current state after this supplement:

```text
RESEARCH COMPLETENESS = complete enough to stop current public-diligence loop before FQ4
SCA CONTRACT HARDNESS = materially supported
SCA CORPORATE-FLOOR TRANSMISSION = partially established
SCA OUTCOME THROUGH REAL DOWNTURN = not observed
AI / HBM LONG-DURATION DEMAND = materially supported but not sufficient alone
POST-CYCLE NORMALIZED EPS FLOOR = bounded but not established as a single number
ORDINAL PROBABILITY KNOWLEDGE = useful
CARDINAL PROBABILITY MEASURE = NOT ESTABLISHED
NUMERICAL ODDS = WITHHELD
HUMAN DECISION = NONE
INVESTMENT AUTHORITY = NONE
```

Ordinally:

- a repeat of FY2023-style economics is less consistent with the current contract structure than it was historically;
- a simple claim that all cyclicality has disappeared is not supportable;
- World B and World C deserve serious weight in Human reasoning;
- World C is approximately the minimum normalized world that makes the current public price comfortable under ordinary long-duration multiples;
- World D is possible but still requires stronger evidence than current market-cycle enthusiasm.

No percentage probabilities are assigned.

---

## 19. Next hard checkpoint

Micron has confirmed fiscal Q4 / FY2026 results for **September 30, 2026 after market close**.

The event should reopen this research specifically for:

```text
full SCA RPO and next-12-month RPO
new SCA count / coverage
contract liabilities and deposits
FY2027 gross-margin trajectory
FY2027 capex and depreciation trajectory
HBM4 / HBM4E mix and economics
DRAM / NAND supply commentary for 2028
normalized FCF / ROIC implications
```

Do not judge the event primarily by whether EPS beats the current ~USD31 quarterly consensus.

The decision-critical question is:

> **Did new evidence raise or lower the credible post-cycle normalized EPS / FCF floor?**

---

## 20. Frozen synthesis

```text
MICRON ECONOMIC SPECIES
= capital-intensive memory oligopoly transitioning toward a strategically contracted AI-memory supplier

SCA CHANGE
= real and materially stronger than old LTAs

SCA MECHANICS
= multi-year take-or-pay + binding volume + deposits / LCs + mostly price bands

SCA FLOOR
= very high gross margin on protected revenue according to management
!= company-wide gross-margin floor

CURRENT SIGNED SCALE AT Q3 ANNOUNCEMENT
= ~20% DRAM volume / ~1/3 NAND volume / ~25% revenue over term

TARGET SCALE
= ~50%+ company revenue under SCA
~40% revenue expected under fixed or price-banded structure

USD100BN RPO
= minimum contracted revenue across 14 signed agreements at floor mechanics
!= forecast revenue
!= guaranteed annual profit

USD18BN CUSTOMER CASH DEPOSITS
= commitment / financing support
!= revenue
!= free cash flow
!= permanent owner cash

CURRENT ~USD956 PRICE
= not explained by "6x FY27 peak EPS" alone
requires belief in materially higher post-cycle owner economics

REVERSE-UNDERWRITING HINGE
= normalized EPS roughly USD55-80+ depending normalized multiple

WORLD A
= contracts cushion but commodity cycle dominates -> current price expensive

WORLD B
= contract-cushioned normalization -> business improved, current price still demanding

WORLD C
= strategic-memory rebase -> current price becomes broadly defensible

WORLD D
= durable AI-memory scarcity + platform economics -> current price can be cheap

PROBABILITY QUALIFICATION
= PARTIAL / ORDINAL

CARDINAL PROBABILITY
= NOT ESTABLISHED

NUMERICAL ODDS
= WITHHELD

HUMAN DECISION
= NONE

NEXT HARD REOPEN
= FQ4 / FY2026 results on 2026-09-30
```

The central investment sentence is:

> **Do not buy Micron because FY2027 EPS is huge and the P/E is six. Buy only if you believe the combination of SCA-protected economics, HBM / AI-memory differentiation and post-buildout ROIC can leave Micron with a post-cycle earnings floor high enough that today's valuation does not require permanent scarcity.**
