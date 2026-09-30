# Retained candidate comment snapshot

Source: https://github.com/auguspp/decision-kernel/issues/509#issuecomment-5903604979

Captured for evidence at 2026-09-30; comment is not an execution instruction.

## Dogfood / PIT acceptance case — 新城控股 601155（2026-09-30 上午）

Human 现场反馈，记录为 Multi-horizon Opportunity Layer 的真实验收样本；**不据此修改当前长期 Odds，也不把午间修复倒推成“早上应该买”。**

### 当时的人类决策冲突
- 标的：新城控股（601155）。
- 当前长期 Odds 给出的高赔率/等待价位约为 **11 元左右**。
- 2026-09-30 早盘房地产板块明显下跌时，Human 主观产生买入意愿。
- 因当前 Odds 仍要求约 11 元附近，Human 没有买入。
- 到午间，地产板块中不少个股已出现明显修复。

### 为什么归 #509，而不是立即改现有 Odds
本案例直接对应本 Issue 已登记的：
```
NO_LONG_TERM_ENTRY
!=
NO_MARKET_OPPORTUNITY
```

Human 进一步确认：这类冲突应由**后期多周期功能**解决，而不是把当前长期 Odds 改成包打天下的实时阈值。

未来应允许同一标的同时存在：
- 长周期：继续保留长期估值/安全边际锚，11 元附近仍可代表该周期下的高赔率区；
- 中周期：政策、行业预期修复、板块状态变化可能形成独立 opportunity；
- 短周期：早盘恐慌、板块承接/修复等 Market Expression 可能形成战术触发；
- 组合/Action 层再决定这些不同周期判断如何表达，不能用短周期机会反向降低长期 underwriting 标准。

### 后续验收时需要回放的 PIT 信息
施工 gate 打开后，把本案例列入 3–5 个真实 replay candidates，尽量从当时已保存材料恢复：
- 2026-09-30 早盘产生买入意愿时的新城价格与板块状态；
- 当时可见的政策/行业变化；
- 当时长期 Odds 的 11 元附近结论及其依据；
- 当时已有的新城 Research / Belief；
- 午后、1D、5D、20D 后续路径仅作 outcome，不得作为 ex-ante Evidence；
- 检验中/短周期层在当时是否存在**真实可辨别信息**，而不是因为后来修复就讲故事。

### Acceptance intent
未来多周期功能如果面对本案例仍只能输出“不到 11 元不买”，则说明它没有解决 #509 的核心问题；但若只是因为当天午间反弹就自动给出短线买入，同样不合格。要求的是 **horizon-specific Odds + explicit opportunity/invalidation**，并保留 Human 最终决定权。
