# Sanhua Human Decision Horizon Supplement — 2026-09-03

Status: **FROZEN PROSPECTIVE HUMAN DECISION SUPPLEMENT / NO ACTION CHANGE**  
Security: **三花智控 / Sanhua Intelligent Controls / 002050.SZ**  
Supplement timestamp: **2026-09-03 07:22 +08:00**  
Parent decision: `docs/decisions/002050-sanhua-human-decision-2026-09-03.md`  
Capture protocol: `docs/prospective-decision-outcome-capture-protocol-2026-09-03.md`

## 1. Human statement

> “如果我在30左右买到了三花，我的持有期限可能是3个月到6个月。”

This supplement freezes only the new information supplied by the Human. It does not rewrite the original decision or infer an execution.

## 2. Horizon interpretation

```text
DECISION = unchanged: CONDITIONAL BUY
FIRST ENTRY CONDITION = around CNY30/share
ACTION = NOT YET EXECUTED
INTENDED HOLDING / EVALUATION WINDOW = approximately 3 to 6 months after actual execution
3-MONTH CHECKPOINT = appropriate prospective review point
6-MONTH CHECKPOINT = appropriate prospective review point
AUTOMATIC EXIT AT 3 MONTHS = NO
AUTOMATIC EXIT AT 6 MONTHS = NO
```

The Human used “可能” and described a likely holding period, not a hard time-based liquidation rule.

Therefore the 3–6 month window should be used for prospective outcome evaluation without manufacturing a mandatory sell instruction.

## 3. What should be evaluated inside the window

Outcome review must separate:

1. **Fundamental outcome** — did the core thermal-management franchise remain economically intact?
2. **Expectation outcome** — did the market begin to require more or fewer assumptions than at entry?
3. **Price / valuation outcome** — did the entry margin of safety convert into a better market price or multiple?
4. **Optionality outcome** — did robot / liquid-cooling evidence become economically measurable, remain unresolved, or deteriorate?
5. **Execution outcome** — if Action occurred, was the actual price materially different from the CNY30 condition?

The intended 3–6 month horizon makes several near-term variables especially important:

- refrigeration and automotive revenue / margin evidence;
- cash conversion and capex / ROIC signals;
- 2027 earnings-estimate revisions and their reasons;
- robot and liquid-cooling evidence only when it advances from commercialization language to measurable economics;
- market multiple / expectation changes, kept separate from Fundamental Belief.

## 4. Predeclared adjudication discipline

A favorable 3–6 month share-price outcome does **not** by itself prove the decision was correct.

An unfavorable 3–6 month share-price outcome does **not** by itself prove the decision was wrong.

The decision should be judged against the original rationale:

> **At around CNY30, with the core thesis intact, the Human was willing to begin accepting the remaining uncertainty because the core franchise carried materially more of the underwriting and unproven optionality was less necessary to justify return.**

A later review should therefore ask:

- Was the core thesis still intact at execution?
- Did the core evidence improve, deteriorate, or remain stable over the holding window?
- Did the price outcome come from fundamental realization, expectation / multiple change, broad-market movement, or some combination?
- Was optionality wrongly promoted into the base case after the decision?
- Did a material thesis change occur before any Action?

## 5. Boundary with the Research valuation horizon

The frozen Sanhua Research package uses a valuation horizon of `2027-09-02`.

The Human's intended decision window is now separately frozen as approximately **3–6 months after execution**.

These are different objects:

```text
Research valuation horizon != Human intended holding / evaluation window
```

A 3–6 month Human decision can still be informed by longer-horizon owner economics, but outcome attribution must respect the Human's actual intended decision window rather than silently substituting the Research horizon.

## 6. Action state unchanged

```text
ACTION = NOT YET EXECUTED
EXECUTION PRICE = NONE
EXECUTION SIZE = NONE
EXECUTION TIMESTAMP = NONE
```

If the Human later confirms an actual purchase, create a separate Action checkpoint and anchor the 3-month and 6-month review dates to the actual execution timestamp.

## 7. Frozen synthesis

```text
SANHUA HUMAN DECISION = CONDITIONAL BUY around CNY30 / first tranche
ACTION = NOT YET EXECUTED
INTENDED HOLDING / EVALUATION WINDOW = ~3–6 months after execution
TIME-BASED AUTOMATIC EXIT = NONE
PRIMARY THESIS = core-first thermal-management franchise
OPTIONALITY = upside only unless realized economics become measurable
OUTCOME REVIEW = fundamental + expectation + valuation + optionality + execution attribution
INVESTMENT AUTHORITY = NONE
```

The key discipline is:

> **The 3–6 month window tells us when to judge the decision, not what price result we are allowed to call success.**
