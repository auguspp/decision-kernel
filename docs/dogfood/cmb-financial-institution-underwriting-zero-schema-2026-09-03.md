# 招商银行 — Financial-institution underwriting stress test

Status: **ZERO-SCHEMA DOGFOOD / UNDERWRITING-LANGUAGE STRESS TEST / NO NEW RESEARCH SCHEMA / NO PROBABILITY / NO ODDS / NO HUMAN DECISION**

Date: 2026-09-03  
Security: `600036.SH` 招商银行  
Current checked-in baseline: `dogfood/600036-cmb.json`

## Question

This case is not asking whether a bank belongs to a new Economic Species enum.

It asks a narrower methodological question:

> **What is the load-bearing uncertainty for a bank, and what analytic language produces the least false precision?**

The existing generic CMB dogfood is useful as a frozen factual baseline, but its illustrative forward-book-value / P/B scenarios and `25/50/25` probability distribution predate the current Decision Hygiene method. This note does **not** treat those probabilities, terminal multiples, or resulting Odds as newly qualified.

## Source boundary

### Already frozen official Evidence in the repository

`dogfood/600036-cmb.json` contains one official 2026 H1 filing EvidenceArtifact:

- EvidenceArtifact: `fb496d1d-df31-5fd1-94db-a93e7a378809`
- source type: `OFFICIAL_FILING`
- source identifier: `SSE:600036:2026-H1:94TO`
- source locator: `https://static.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-08-29/600036_20260829_94TO.pdf`
- published / available: `2026-08-28T16:00:00Z`
- retained structured values include revenue, attributable profit, EPS, ROAE, total assets, loans, customer deposits, NPL balance / ratio, provision coverage, and net interest income.

The retained official values are sufficient to prove the broad balance-sheet baseline but **not** every detailed line item needed below.

### Current public retrieval used for this stress test

The Shanghai Stock Exchange and CMB Investor Relations currently list the 2026 half-year report, summary, and Pillar 3 report as official disclosures. Detailed report text was also inspected through public report reproductions / retrieval mirrors because the current repository EvidenceArtifact retains only a subset of structured values.

Those additional details are useful for selecting the underwriting language, but they are **not yet promoted into new checked-in EvidenceArtifacts** by this note.

Therefore:

> **This is a method / frame dogfood, not a new formal Research freeze.**

No claim below that depends on non-retained detailed H1 lines should silently become authoritative Kernel Research until exact source qualification and lineage are performed.

---

# 1. The industrial-company language is the wrong starting point

For a normal industrial company, a common causal chain is roughly:

```text
revenue
→ margin
→ operating cash flow
→ reinvestment / ROIC
→ owner cash
```

That is not the least-false-precision language for a deposit-taking bank.

In particular:

- customer deposits are an operating funding franchise, not ordinary trade financing;
- conventional operating cash flow is not a useful analogue of industrial free cash flow;
- regulatory capital and risk-weighted assets constrain growth and distributions;
- credit losses can transform apparently attractive spread income into poor owner economics with a lag;
- book value is economically meaningful only if its quality, capital intensity, and future ROE are understood.

The more useful causal chain is:

```text
funding franchise / deposit mix
        ↓
liability cost
        +
asset mix / asset yield
        ↓
NIM / net interest income
        +
fee franchises / AUM economics
        -
credit migration / credit cost
        -
operating cost
        ↓
profit attributable to common equity
        ↓
CET1 generation vs RWA consumption vs distributions
        ↓
per-share book-value compounding + cash distributions
```

`P/B` can be a terminal valuation translation **after** this chain is underwritten. It should not substitute for the chain.

---

# 2. Load-bearing uncertainty

The central uncertainty is not simply “can earnings grow?”

It is:

> **Can CMB's low-cost funding franchise and fee-income recovery offset continued asset-yield compression and retail-credit normalization strongly enough to preserve high-quality, capital-efficient per-share book-value compounding?**

This breaks into five load-bearing nodes.

---

# 3. Node A — Funding franchise vs asset-yield compression

## Realized record

The existing frozen package records 2026 H1 net interest income of RMB112.022bn, +5.60% YoY.

The detailed H1 report shows the underlying mechanics more clearly:

| Metric | 2026 H1 | 2025 H1 | Change |
|---|---:|---:|---:|
| interest-earning asset yield | 2.82% | 3.14% | -32bp |
| interest-bearing liability cost | 1.05% | 1.35% | -30bp |
| net interest spread | 1.77% | 1.79% | -2bp |
| NIM | 1.83% | 1.88% | -5bp |
| customer-deposit cost | 0.97% | 1.26% | -29bp |

The group had RMB10.162tn of customer deposits at 2026-06-30. H1 average demand deposits represented 49.60% of average customer deposits. Retail demand-deposit share improved while company demand-deposit share softened slightly.

## Underwriting implication

The important observation is not merely “NIM fell only 5bp.”

The causal observation is:

```text
asset yield compression = severe
funding cost compression = nearly as severe
→ spread compression remained modest
```

That is direct evidence that the liability franchise is economically load-bearing.

But it also creates an asymmetric question for the future: a deposit base already costing below 1% has less nominal room to reprice downward than a loan book has room to reprice downward. This is an **inference**, not a realized outcome.

Therefore future NIM underwriting must separate:

1. asset-yield repricing;
2. deposit-mix migration;
3. deposit pricing;
4. balance-sheet mix / volume;
5. non-deposit wholesale funding.

A single top-line NIM extrapolation would hide the mechanism.

---

# 4. Node B — Static asset quality is strong; retail risk generation is the live pressure

## Realized record

The existing frozen package records:

- total NPL ratio: **0.94%**;
- NPL balance: RMB70.251bn;
- provision coverage: **385.10%**.

The detailed H1 record adds an important composition split:

- company-loan NPL ratio: **0.78%**, down from 0.89% at 2025 year-end;
- retail-loan NPL ratio: **1.16%**, up from 1.06%;
- retail NPL balance: RMB42.832bn, up RMB3.248bn from year-end;
- annualized credit cost: **0.69%**, up from 0.67% in 2025 H1;
- provision coverage: 385.10%, down 6.69 percentage points from 2025 year-end.

## Underwriting implication

The headline `0.94% NPL` is not enough.

The decision-useful state is closer to:

```text
corporate credit quality improving
+
retail credit quality deteriorating from a still-low absolute base
+
very large reserve cushion, but declining at the margin
```

For a bank whose retail franchise is central to its valuation premium, the relevant failure mode is not necessarily an immediate jump in the total NPL ratio. It is sustained retail risk generation that consumes more credit cost and capital than fee / funding advantages can offset.

Therefore the next discriminating evidence is migration, not just stock:

- new retail NPL generation;
- overdue / special-mention migration;
- card / consumer / small-business product split;
- write-offs and recoveries;
- credit cost through a full retail normalization cycle.

---

# 5. Node C — Wealth-management recovery is real, but it is not the same as retail-profit recovery

## Realized record

The H1 disclosures show:

- retail customer AUM: **RMB18.44tn**, +7.96% from year-end;
- retail wealth-management fee and commission income: **RMB14.069bn**, +24.81% YoY;
- retail financial business revenue: RMB96.820bn, +0.65% YoY;
- retail non-interest income: RMB28.366bn, +11.43% YoY;
- retail financial business pre-tax profit: **RMB42.888bn, -17.58% YoY**.

## Underwriting implication

This is an important negative control against narrative shortcutting.

The tempting story is:

```text
AUM up
+ wealth-management fees up
→ retail franchise fully recovered
```

The realized segment economics do not support that conclusion.

A better statement is:

> The fee franchise is recovering strongly, while the retail business's total pre-tax economics remain under pressure.

The gap between these two observations is precisely where credit cost, asset mix, spread pressure, and other segment costs matter.

Therefore `wealth-management recovery` should remain one driver in the chain, not a substitute for the chain.

---

# 6. Node D — Capital adequacy is an economic constraint, not a compliance footnote

## Realized record

At 2026-06-30, the group reported under the advanced approach:

- CET1 capital: RMB1.115tn, +4.47% from year-end;
- RWA after capital-floor requirement: RMB7.929tn, +5.16%;
- CET1 ratio: **14.07%**, down 9bp from year-end;
- Tier 1 ratio: 16.59%;
- total capital ratio: 18.33%.

The existing H1 summary also shows common BVPS increasing from RMB43.43 at 2025 year-end to **RMB45.40**, +4.54%.

## Underwriting implication

The right question is not merely “is 14.07% above the regulatory minimum?”

It is:

> How much owner value can be compounded after funding asset growth, absorbing credit losses, satisfying capital constraints, and making distributions?

In H1:

```text
CET1 capital growth 4.47%
< RWA growth 5.16%
→ CET1 ratio edged down
```

That is not an alarm; the absolute ratio remains high. But it shows why bank growth must always be read together with capital consumption.

A future “earnings growth” case that requires much faster RWA growth without durable ROE would not automatically improve owner economics.

---

# 7. Node E — ROE and book-value compounding are the most compact owner-economics outputs

## Realized record

2026 H1:

- attributable net profit: RMB76.445bn, +2.02% YoY;
- annualized ROAE: **13.42%**, down from 13.85% in 2025 H1;
- common BVPS: **RMB45.40**, +4.54% from 2025 year-end.

## Underwriting implication

For CMB, `ROE` is not a sufficient thesis by itself, but it is a better compressed output than industrial-company ROIC language because it naturally captures the equity capital base on which a regulated bank compounds.

The useful decomposition is:

```text
NIM economics
+ fee economics
- credit cost
- operating cost
→ common earnings

common earnings
- distributions
+ / - capital actions
→ retained common equity

retained common equity
vs RWA growth / capital requirement
→ sustainable future ROE
→ per-share book-value compounding
```

The current 13.42% ROAE remains economically strong in absolute terms, but the trend is downward. A high current ROE therefore cannot be assumed to be the terminal ROE.

---

# 8. What this case says about Reference Frame

The old generic CMB dogfood used illustrative forward BVPS and P/B scenarios. That was useful for exercising Kernel/Odds mechanics, but it is not enough for current underwriting.

This case demonstrates a stronger boundary:

> **For a bank, terminal P/B is an output translation of expected future ROE / growth / risk / capital economics; it is not the primary causal model.**

A model that starts with:

```text
2027 BVPS × chosen P/B
```

without first underwriting:

```text
funding cost
asset yield
credit migration
fee economics
capital consumption
```

can produce precise arithmetic on the wrong frame.

This is exactly the kind of heterogeneous case the project needs: not because “bank” is a category to route, but because the load-bearing uncertainty forces a different analytic language.

---

# 9. Probability status

The current evidence is enough to establish the causal frame and identify the live pressure points.

It is **not** enough to establish a trustworthy cardinal distribution over terminal CMB outcomes.

Reasons:

1. retail credit normalization has not resolved;
2. future asset-yield versus deposit-cost repricing remains path-dependent;
3. the durability of H1 wealth-management recovery versus market beta is not yet isolated;
4. normalized ROE after the current credit / rate cycle is not established;
5. this note has not yet re-frozen all detailed H1 inputs as exact EvidenceArtifacts under the current Claim Audit discipline.

Therefore:

```text
RESEARCH FRAME = ESTABLISHED
REALIZED H1 BASELINE = STRONG
NORMALIZED ROE = NOT ESTABLISHED
CARDINAL PROBABILITY = NOT ESTABLISHED
FRESH NUMERICAL ODDS = WITHHELD
HUMAN DECISION = NONE
ACTION = NONE
```

The old `25/50/25` probability distribution in `dogfood/600036-cmb.json` remains a historical mechanics fixture. This note does not ratify it.

---

# 10. Next discriminating evidence

The next CMB pass should not be “find more bank ratios.” It should specifically test the causal chain.

## Funding / NIM

- Q3/Q4 asset yield and loan repricing;
- customer-deposit average cost and demand-deposit share;
- whether liability repricing continues to offset asset-yield compression.

## Credit

- retail NPL generation and overdue migration;
- card / consumer / small-business risk split;
- write-offs, recoveries, and credit cost;
- whether total asset-quality stability survives continued retail normalization.

## Wealth / fees

- AUM composition and net new money;
- fund / insurance / wealth-management fee durability;
- whether fee recovery translates into improved total retail segment profit after credit costs.

## Capital / owner economics

- RWA growth versus CET1 generation;
- capital ratio after distributions and capital actions;
- common BVPS growth;
- normalized ROAE through the rate / credit cycle.

---

# 11. Method disposition

```text
FINANCIAL-INSTITUTION FRAME STRESS TEST = USEFUL
INDUSTRIAL REVENUE→MARGIN→FCF→ROIC LANGUAGE = REJECTED AS PRIMARY FRAME
BANK UNDERWRITING LANGUAGE = FUNDING + ASSET YIELD + CREDIT + FEES + CAPITAL → ROE/BVPS
P/B = TERMINAL TRANSLATION, NOT PRIMARY CAUSAL MODEL
OLD GENERIC CMB PROBABILITIES = NOT REQUALIFIED
NEW BANK ENUM / SPECIES ROUTER = NO
NEW KERNEL SCHEMA = NO
NEW RESEARCH STATE MACHINE = NO
CARDINAL PROBABILITY = NOT ESTABLISHED
ODDS = WITHHELD
HUMAN DECISION / ACTION = NONE
```

The useful lesson is not “banks require a special template.”

It is:

> **When the load-bearing uncertainty changes, the underwriting language must change before the arithmetic becomes more detailed.**
