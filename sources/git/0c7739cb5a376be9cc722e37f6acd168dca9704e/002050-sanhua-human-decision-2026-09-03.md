# Sanhua Human Investment Decision Checkpoint — 2026-09-03

Status: **FROZEN PROSPECTIVE HUMAN DECISION / CONDITIONAL BUY / ACTION NOT YET EXECUTED**  
Security: **三花智控 / Sanhua Intelligent Controls / 002050.SZ**  
Decision timestamp: **2026-09-03 07:04 +08:00**  
Capture protocol: `docs/prospective-decision-outcome-capture-protocol-2026-09-03.md`

## 1. Human decision — preserve the actual wording

Human statement:

> “我的决定是在 30 左右开始买入第一笔，目前的市场结构下，我还是对赔率和安全边际要求更高。”

Decision interpretation, limited to what the statement actually authorizes:

```text
DECISION = CONDITIONAL BUY
SECURITY = 002050.SZ / 三花智控
INITIAL ENTRY CONDITION = around CNY30/share
POSITION STEP = first tranche
ACTION = NOT YET EXECUTED
RATIONALE = current market structure requires higher Odds / margin of safety
```

This record does **not** infer:

- that a trade has already occurred;
- a target position size;
- a second or later tranche price;
- a stop-loss rule;
- an exit target;
- a personal evaluation horizon not explicitly stated by the Human;
- that the old numerical scenario probabilities are accepted as decision-grade probabilities.

## 2. Research context frozen at the decision PIT

Primary current Research lineage:

- Full Research package: `research_cases/002050-sanhua-deep-research-v1.json`
- ResearchSnapshot id: `1d890f85-1bf1-5ca8-b54b-dedf338783ff`
- Research information bundle hash: `3099d4e2b72595d52111b0e88e0ba84f36d4ef1b0ac3296563e414c3f6187145`
- Research valuation horizon: `2027-09-02`
- Decision Hygiene dogfood: `docs/dogfood/sanhua-decision-hygiene-zero-schema-2026-09-03.md`

The Decision Hygiene dogfood, rather than the old forced total-company probability distribution, is the main methodological context for this Human decision.

Current Research interpretation:

> **Qualified thermal-management industrial franchise with a relatively stable, auditable core earnings engine and genuine but economically unproven liquid-cooling / humanoid-robot call options.**

Probability read:

```text
CORE ECONOMIC RANGE = comparatively well constrained
CORE ORDINAL PROBABILITY KNOWLEDGE = meaningful
OPTIONALITY PROBABILITY = not established
TOTAL-COMPANY CARDINAL PROBABILITY MEASURE = not established
NUMERICAL ODDS FROM THE ZERO-SCHEMA DOGFOOD = withheld
```

The historical Sanhua v1 `15/25/35/20/5` distribution and CNY37.5435 weighted terminal value remain auditable prior artifacts. They are **not recorded here as the Human's accepted probability measure and are not the driving basis of this decision**.

## 3. What the CNY30 entry condition economically means

This is a reverse-underwriting aid, not a new Odds calculation.

Using the H1 issued-share count embedded in the Research package, approximately `4.19554bn` shares:

```text
CNY30/share
→ equity value ~CNY125.87bn
```

At illustrative 2027 core parent-profit states:

| 2027 core parent NP | Implied P/E at CNY30 |
| ---: | ---: |
| CNY4.7bn | ~26.8x |
| CNY5.0bn | ~25.2x |
| CNY5.25bn | ~24.0x |
| CNY5.5bn | ~22.9x |
| CNY5.7bn | ~22.1x |

Interpretation:

> The Human is not choosing to pay the current ~27–30x central-core multiple merely because the business is high quality. The first-entry condition requires a materially lower price so that the core franchise carries more of the underwriting and unproven optionality is less necessary to justify acceptable return.

This is consistent with the Human's stated preference for a higher margin of safety under the current market structure.

## 4. What world the first tranche is intended to buy

The first tranche is best understood as exposure to the **core-first world**, not a robot-right-tail bet.

Required thesis at entry:

```text
refrigeration core remains economically resilient
+ automotive thermal-management economics remain intact
+ core segment margins remain broadly consistent with the established historical band
+ cash conversion remains healthy
+ capital allocation does not materially impair core ROIC
→ core owner economics remain adequate to support the entry price
```

Liquid cooling and robot actuators may add upside, but they are not required to justify the initial-entry thesis.

Therefore:

> **If the first tranche only works because robot or liquid-cooling economics must already be large, the original decision rationale has been violated.**

## 5. Price condition is not an automatic execution command

`around CNY30` is a price condition inside the Human decision, not a mechanical order instruction.

Before an actual purchase, Research must reopen if new company-specific evidence materially changes the core underwriting.

In particular, reaching CNY30 should **not** automatically produce an Action if, before execution:

- refrigeration and automotive weaken together with margin / cash-conversion deterioration;
- 2027 company-specific earnings evidence falls materially below the current core range;
- core cash conversion or global-capex ROIC deteriorates materially;
- a material new balance-sheet / governance / customer-concentration risk appears;
- the Reference Frame changes enough that the existing core-first valuation is no longer appropriate.

Rule:

> **Price can satisfy the entry condition; only unchanged-or-improved admissible evidence preserves the decision thesis.**

This prevents a falling price caused by thesis deterioration from being mistaken for automatically improved Odds.

## 6. Action state

Current Action state:

```text
ACTION = NOT YET EXECUTED
EXECUTION PRICE = NONE
EXECUTION SIZE = NONE
EXECUTION TIMESTAMP = NONE
BROKER / ORDER RECEIPT = NONE
```

If execution later occurs, create a separate Action checkpoint rather than editing this decision record.

That Action checkpoint should freeze:

- actual execution timestamp;
- actual price and size supplied / confirmed by the Human;
- the exact latest Research lineage used at execution;
- production `ObservedMarket` from HiThink where applicable;
- any material difference between the original CNY30 condition and actual execution;
- whether the Human decision changed before the trade.

Do not infer Action merely because market price later trades near or below CNY30.

## 7. Evaluation horizon — deliberately unresolved

The Research package has a valuation horizon of:

```text
2027-09-02
```

The Human did **not** explicitly state a personal investment / decision-evaluation horizon in the decision message.

Therefore:

```text
HUMAN EVALUATION HORIZON = NOT YET SPECIFIED
```

The Research valuation horizon must not be silently promoted into the Human's personal horizon.

Before any later outcome adjudication labels the decision `good`, `bad`, `right`, `wrong`, `missed`, or `successful`, the Human evaluation horizon must be explicitly frozen prospectively.

Until then, later share-price performance cannot by itself adjudicate the quality of this decision.

## 8. Predeclared decision-quality tests

Even before the Human evaluation horizon is specified, several process-quality tests can be frozen now.

### The decision is supported if, at execution and subsequent evidence checkpoints:

- the core franchise remains intact;
- core segment margins and cash conversion remain broadly resilient;
- the first tranche does not require unquantified robot / liquid-cooling profit to justify the entry economics;
- CNY30 materially lowers the economic assumptions required versus the ~CNY35.5 public-PIT context used in the dogfood;
- no material adverse evidence has invalidated the Reference Frame before Action.

### The decision rationale is weakened or invalidated if:

- core earnings quality deteriorates before price reaches the entry condition;
- the Human buys merely because price has fallen despite weaker Fundamental Belief;
- optionality is silently promoted into the base case to defend the entry;
- a later higher price is used as proof that the original causal thesis was correct;
- a later lower price is used as proof that the thesis was wrong without examining fundamental / valuation / execution layers separately.

## 9. What this checkpoint does not authorize

This document does not create:

- a recommendation;
- an automatic order;
- a position-sizing rule;
- an execution workflow;
- a stop-loss or target-price rule;
- a new Kernel `HumanDecision` schema;
- a new Outcome entity;
- a second Human wake gate;
- a new probability distribution;
- numerical Odds from unqualified probability;
- a change to live Odds policy;
- any system investment authority.

Investment Authority remains:

```text
NONE
```

The Human has made the investment decision recorded above. The system has only preserved it and its contemporaneous research context.

## 10. Frozen synthesis

```text
HUMAN DECISION = CONDITIONAL BUY
FIRST ENTRY = around CNY30/share
RATIONALE = higher required Odds / margin of safety under current market structure
THESIS BOUGHT = core-first thermal-management franchise
OPTIONALITY = upside only; not required for first-tranche thesis
ACTION = NOT YET EXECUTED
PRICE TRIGGER != AUTOMATIC EXECUTION
RESEARCH MUST REOPEN IF CORE EVIDENCE DETERIORATES BEFORE ENTRY
HUMAN EVALUATION HORIZON = NOT YET SPECIFIED
NUMERICAL ODDS = not newly asserted
INVESTMENT AUTHORITY = NONE
```

The key discipline is:

> **The decision is not “buy Sanhua because CNY30 is cheap.” It is “if the core thesis remains intact, CNY30 is the first price at which the Human currently chooses to begin accepting the remaining uncertainty.”**
