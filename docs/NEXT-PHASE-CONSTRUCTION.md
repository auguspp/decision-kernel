# 当前主施工计划 v4：B1 全球市场状态

2026-09-27。Human 已在独立新会话恢复样本后明确“好，开始做”。当前主线切到 B1，随后 B2；不继续展开 Sites 身份、bootstrap、通用代理或 WebGPT 直连。

> **2026-09-27 本轮交接更新：** B1 六族有限来源、固定 R 保存读取与 Markets 代码已交付，下一主工程为原已批准的 B2 有限近期研究日历；Sites 六族 Markets 待原站集中采用。见 [本轮交接文档](handoffs/2026-09-27-b1-closeout-b2-next.md) 与 [#616 实际读回回执](https://github.com/auguspp/decision-kernel/pull/616#issuecomment-5857101690)。下文第一切片及“尚未覆盖”说明保留为 v4 开工时的分阶段范围，不再作为当前待建设清单；具体后继以 #297 为准。本轮结束，只同步和归档，不启动 B2 或新采集。

## 当前接点

Quick Inbox 的真实选择→网页版研究→GitHub正文→结果关联，以及一个独立新会话仅凭入口和定位恢复，已形成有范围的实证。这个样本不等于 Human 接受研究，也不替代 R5-5 的持续使用/质量观察及其他未验范围。

B1 的已批准完整目标：全球指数、利率/债市、黄金原油、外汇与加密资产的有限市场背景；分来源家族独立刷新。来源只报告观察、时点及覆盖，原因与公司经济映射交给 Research。价格变化不自动改 Belief，不执行 Full/Odds/Watch/交易。

## 治理接续（沿原批次，不新增工程阶段）

规则/方法/已接受经验的新增、实质修订及有据清理，按同 M 的 [AGENTS 治理生命周期](../AGENTS.md#governance-lifecycle)执行：在原 Issue/PR 说明原因、适用范围、消费者/取回触发、授权/生效与退出；变化同步检查实际消费者。普通已授权工程不逐项索批，候选 patch 不冒充 Human 接受。#508/#511 的适用留存及拒绝理由进入当前 Reuse Check，未读到不能写成没有候选；下一相关任务记录实际采用/未采用，不能用登记或 CI 代替效果证明。治理规则不在本计划复制第二份；交易 Effect、通用 Memory/审批平台继续后置。具体交付/未验停点始终读 #297 最新回执，不从本页第一切片说明重开已交付工作。

## 第一切片：先核真实来源，再接 Markets

复用现有 Tushare Relay 的 `index_global` / `shibor`，不替换原客户端、不引入新服务或凭证。详情见 [B1 source slice](global-market-context-v1.md)。

- 指数：SPX、IXIC、HSI、HKTECH、N225、GDAXI，有限近日线。
- 利率首块：人民币 Shibor 八期限；不冒充美债或全球债券收益率。
- 两族独立手动运行，保留原响应、请求/收到时刻、来源日期、单位、缺口及可离线复验的摘要。
- 未取得的市场状态/发布时钟保持 UNKNOWN；失败不清空旧结果，不推成没有变化。

首批交付是可运行采集与原件验证，**不是六大资产类别已齐、不是 Markets 已上线**。先按真实 API 字段和返回验证，再将本批保存结果及最新尝试缺口接入原 current-state/pinned-R/Markets；不要为来源尚未实测先写一屏伪行情，也不要将一个绿工作流当成来源完整覆盖。

其他 B1 来源族保留在本主线：美债/国际利率、黄金原油、汇率、加密资产。继续按“内部复用→官方接口→外部 prior art”选择最薄实现；**外部 prior art 先查 #508 High-Relevance Living Prior Art，再查 #511 Capability Radar / candidate pool，已有重叠候选先复核当前 upstream / delta，只有仍有缺口才做新的 GitHub 搜索。** 未完成这一步，不以 `NEW_BUILD_JUSTIFIED` 收口；不另造 provider framework。只在真实字段/权限缺口出现时调整受影响一族，不强制整组重跑。

## 之后的顺序

B1可用市场背景→B2有限近期研究日历；跨期Evidence/Prediction比较、多期限Opportunity与Reuse Radar继续为后续增强。日历日期需明确来源，事项/事件不自动成为 Human 待办或交易触发。

持续使用中的 News/Quick Inbox/手机问题保留修复，但不再因历史标题或旧入口重新启动身份指纹施工。未自然发生的 Human 回应、研究接受、Full委托和长期使用验收保持原资格，不补造。

## 保留历史与不变边界

本 v4 向前取代 v3 的“继续集中 Sites 采用”作为当前 NEXT；旧实现、失败、来源、回退及未验事项不删除。

- [v3 人本工作台 / Quick Inbox / News Refresh 计划](https://github.com/auguspp/decision-kernel/blob/86c1d2075d3679ef1b92788e49674f7eaf4f77b2/docs/NEXT-PHASE-CONSTRUCTION.md)
- [v1 A3–A5 / B1–B2 原范围](https://github.com/auguspp/decision-kernel/blob/bceb4b55488a10ba800b22f5798515bc42731635/docs/NEXT-PHASE-CONSTRUCTION.md)
- 主执行入口仍是 #297。不改现有 Research/Odds/Human authority、全部CI/合并门禁或其他来源日程。

本次没有新增自动任务、Sites部署、权限、数据库或收费订阅。后续源工作流只在精确main通过CI后按本授权有界运行；实际成功/失败、保存/发布/手机显示分开验。
