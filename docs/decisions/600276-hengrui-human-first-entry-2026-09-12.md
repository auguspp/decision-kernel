# 恒瑞医药（600276）Human-accepted conditional first-entry distribution — 2026-09-12

Status: **HUMAN_ACCEPTED_DECISION_REHEARSAL / NOT EXECUTED**  
Security: 恒瑞医药 / 600276.SS  
Research archive: `docs/readings/hengrui-600276-research-odds-2026-09-11/`  
Recorded date: 2026-09-12 (UTC+08:00)

## 1. Human acceptance

Human explicitly accepted the conditional first-entry price distribution described below.

This record is a Human decision-preparation record. It is **not** an automated trade instruction, standing order, position-size mandate, or execution authorization.

Investment authority remains Human-only.

## 2. Frozen Belief reused without reopening Research

> **恒瑞已经证明创新研发能够形成产品和交易价值，但尚未证明这些价值在承担持续研发、资本投入和授权履约成本后，可以稳定转化为足以支持当前价格要求的每股可支配现金。**

Research remains frozen. This decision record does not reopen company Research and does not manufacture new cardinal probabilities.

The decisive UNKNOWN set remains:

1. 非肿瘤核心产品的净价、持续用药与增量现金贡献；
2. License-out 组合的完整研发、共享成本与税费；
3. BMS 首付款实际到账后的履约预算和可留存现金；
4. 价格日期初净现金、2029 净现金及 NewCo 净权益。

## 3. Price authority boundary

The prior Human-supplied price remains:

- `2026-09-10 A-share close = CNY42.93`
- source: `HUMAN_SUPPLIED_PROVISIONAL_PRICE`
- authority: `CONTEXT_ONLY`
- qualified market observation: `false`
- canonical market state: `false`

A later public close around CNY42.67 was observed only as additional non-qualified context and does not overwrite the frozen Human-supplied 42.93 input.

The prior HiThink qualification failure remains retained:

- run `34556401563`, attempt 1
- error: `raw A-share history extends beyond the latest completed session`
- no canonical Odds was produced

## 4. Odds method boundary

Current Kernel `decision-os-live-odds-v0.1` requires cardinal positive-return probability and supports a 180–730 day holding period. This Hengrui decision framing uses a three-year horizon and still has no calibrated cardinal probability.

Therefore:

- `CANONICAL_NUMERICAL_ODDS = NOT_ESTABLISHED`
- `DECISION_USE_ODDS = ORDINAL / REVERSE_UNDERWRITING`
- `CARDINAL_PROBABILITY = NOT_ESTABLISHED`
- no Bull/Base/Bear probability weights are asserted

This record follows the same decision-use discipline as prior first-entry reverse-underwriting records: price changes Odds; it does not change Belief.

## 5. Human-accepted conditional first-entry distribution

### Above CNY39.6

`WAIT`

Reason: even the low end of the current core-thesis value world is not sufficient to robustly clear the Human's three-year 10% annualized-return requirement.

### Around CNY39.6

`RE_UNDERWRITE / ASSUMPTION_RECHECK`

This is not a first-entry trigger. It is the mechanical area where the low end of the core-thesis world begins to meet the 10% annualized-return requirement.

### CNY37–38

`CONDITIONAL_FIRST_ENTRY_REVIEW`

This is the Human-accepted first-entry discussion region, conditional on the frozen Belief remaining intact.

At approximately CNY38 under the retained stress worlds:

- operating undershoot world: roughly -15.9% to -5.1% annualized over three years;
- growth but average cash-conversion world: roughly +1.0% to +9.4% annualized;
- core thesis mostly realized: roughly +11.5% to +19.7% annualized;
- material outperformance: roughly +22.5% to +31.7% annualized.

These are conditional world returns, not probability-weighted expected returns.

### Around CNY35

`SECOND_REVIEW / MATERIALLY_BETTER_ODDS`

If Belief is unchanged, the price geometry becomes materially more favorable. This is not an automatic averaging-down instruction.

### CNY32–32.5

`HIGH_MARGIN_OF_SAFETY_REVIEW`

At this region, the upper end of the current downside world approaches nominal capital preservation while ordinary-growth and core-thesis worlds produce materially stronger return geometry.

This remains a review zone, not a standing buy order.

### Around CNY29.45 and below

`DEEP_RE_UNDERWRITE`

At roughly CNY29.45, even the low end of the retained `growth but average cash conversion` world begins to satisfy approximately a 10% three-year annualized return.

However, a fall to this level may itself contain new negative information. The Human must first determine whether Belief has changed before treating the lower price as improved Odds.

## 6. Anti-mechanical rule

**No price level in this record is self-executing.**

Before any Human first-entry decision, re-check whether new Evidence has changed the frozen Belief, especially:

- non-oncology product volume / net pricing / persistence;
- license-out full-cost economics;
- BMS receipt / obligation / retained-cash evidence;
- cash, NewCo and royalty double-counting;
- any new regulatory, clinical, reimbursement or operating evidence that materially changes the Research state.

If new Evidence weakens or invalidates the thesis, the price distribution is stale and must not be mechanically reused.

## 7. Human decision state

```text
RESEARCH = FROZEN
CANONICAL ODDS = NOT_ESTABLISHED
ORDINAL / REVERSE-UNDERWRITING ODDS = ACCEPTED FOR DECISION USE
FIRST-ENTRY DISTRIBUTION = HUMAN ACCEPTED
FIRST ENTRY EXECUTED = NO
POSITION SIZE = NOT RECORDED
STANDING ORDER = NONE
AUTOMATIC EXECUTION AUTHORITY = NONE
FINAL INVESTMENT AUTHORITY = HUMAN
```

This record captures acceptance of the price distribution only. It does not record an actual purchase or capital allocation.