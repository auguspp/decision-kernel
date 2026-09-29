# 当前施工入口：B2后端先行，Sites后续集中接入

2026-09-29。Human最新指令是先完成B2后端与可读取内容，之后在原Site编辑对话直接提出界面要求并集中接入。原话与范围对账见[#297/5888866896](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5888866896)。**当前执行顺序以[#297](https://github.com/auguspp/decision-kernel/issues/297)与对应任务的最新有效回执为准。** 本页只作导航，不维护第二份进度表。

## 当前顺序与任务归属

**主施工继续[#620 B2](https://github.com/auguspp/decision-kernel/issues/620)**：可靠公司事件及财报预约、明确对象依据、原研究复核条件、可恢复保存和稳定读取。优先现有原件、用途索引与发布链，缺口来自实际使用才补代码；“后端先行”不意味着新增数据库、provider、调度或日历框架。

#644的近期清单已正常合并、独立main、自然publisher及固定R原件／消费者读回，见[原交付](https://github.com/auguspp/decision-kernel/pull/644#issuecomment-5883938448)。旧分支、容量失败、安装超时与核读时钟保留，不把旧“未合并”恢复为当前任务。B2已有接口从[research-calendar-v1](research-calendar-v1.md)恢复；唯一`research-agenda`用途引用可显式切换到新保存稿，原BLS及旧稿不覆盖。实际登记／发布／来源资格以#620最新回执为准。

**[#621 Sites](https://github.com/auguspp/decision-kernel/issues/621)暂缓主施工投入，交由原Site对话后续集中采用。** 不再为此反复搬通知、源码、验签或安装浏览器。已保存v18、现网v17及预览能力缺口的最后原生回执留在该Issue；没有新工具核查就不声称部署状态已刷新。Human可直接向原Site对话提出要求，不需要主施工批准或中转。暂缓不是取消其已有宿主／权限／回退与发布前页面检查。

[#645 Brief Human-first / Concept Radar v2](https://github.com/auguspp/decision-kernel/issues/645)保留独立未验项。#646–#650已交付的Brief指令、概念总览／成员／比较／多周期读取不重建；真实长历史、自然Brief效果、未覆盖来源及实际使用仍分别验收，不作为B2前置。现用完整指令从[BRIEF-R5-v1.6](readings/2026-09-28-brief-human-first-instructions.md)恢复；不改任务、时钟与通知，不为验收手工补采。

先读同M的[AGENTS](../AGENTS.md)，从#297恢复当前任务，按需取回适用协议、原件与代码；涉及保存结果才独立固定R。旧摘要不证明功能不存在，新SHA不授予新范围。代码、来源、读取发布、Site部署及Human使用分别成立，后端完成不补签整项产品验收。

[#625 AI-native](https://github.com/auguspp/decision-kernel/issues/625)与[#626 AN-CI](https://github.com/auguspp/decision-kernel/issues/626)保留已收口前驱，不恢复旧“先支线再B2”。其原生管理403、外部身份／实机与长期观察的有界缺口继续原归属，不扩大为已通过，也不因此无限扩支线。

## 产品主线如何接续

B1 六族有限采集、原件保存/固定 R、Markets 代码的已交付范围，恢复 [B1 交接](handoffs/2026-09-27-b1-closeout-b2-next.md) 与 [#616 实际读回回执](https://github.com/auguspp/decision-kernel/pull/616#issuecomment-5857101690)。历史快照不是今日行情或生产采用证明，不重建 #610/#612/#614/#615/#616，也不重开 owner/bootstrap。

[#620 B2](https://github.com/auguspp/decision-kernel/issues/620) 与 [#621 六族 Markets 原站采用](https://github.com/auguspp/decision-kernel/issues/621) 继续归 #351，原范围、原件、未验项和授权保留；两者分别交付，不人为设置技术 blocking。Markets 沿原宿主授权集中采用，不从 repo 合并推断线上已部署。具体施工先后按当前任务和资源恢复，不再次索批已授予的“回主线”。

B2 日期必须有来源，计划/实际、时区、报告期与查询/发布时间分开；不猜财报日，不把研究过的公司当持仓，不把日历事件变成投资触发或 Human 待办。真实来源、保存、固定版本阅读、页面使用分开验收；首切片不提前替公司事件、原站或完整日历签收。

## 不变边界

保留 0→A→B→C→D、P01–P10 与横向 Learning Loop L 的原 Issue/PR 归属。H1–H5 从 #297 的明确 accepted successors 恢复；不把旧 pending-choice 当新阻塞。

规则或方法变化按 [治理生命周期](../AGENTS.md#governance-lifecycle)，前提变化按 [Reconcile](../AGENTS.md#reconcile-before-continuing--premise-change-impact-review) 同步受影响消费者。复用从 #508/#511 已留存候选与反证开始，不因改了导航而再次全量研究框架。

GitHub 是 canonical 状态/证据/过程后端；Research 解释、Kernel 核一致性不核经济真理；Evidence changes Belief，Price changes Odds；AI Investment Authority=NONE。保留原研究、失败、Human 原话与接受边界。文档/CI/保存/发布/实际使用分别验收。

不新增日常采集、Quick/Full/Odds/Watch/交易，不停原 Brief 或获准任务，不自动合并依赖提案，不改 Sites PAT/隐私/持续费用。不以本导航创建 Memory、provider、Agent/DAG、CI 或审批框架。

## 历史计划，不作为当前待建清单

- [本次后端优先前的Brief／Concept入口](https://github.com/auguspp/decision-kernel/blob/e1bf4146d73b4aa2dbd0d6bc3882bed4a9b0a48f/docs/NEXT-PHASE-CONSTRUCTION.md)：保留先前顺序与#644旧停点，当前由#297/5888866896取代。

- [本次重排前B2入口](https://github.com/auguspp/decision-kernel/blob/d8fedb169eaeaf825b45afb3602fe0c4d4390aa4/docs/NEXT-PHASE-CONSTRUCTION.md)：原范围与失败保留；其中当时的Brief优先顺序已由本页上方后继指令取代。

- [AI-native 支线导航](https://github.com/auguspp/decision-kernel/blob/1ef57be901243f683cb0cc15cedd3ed159fdd02e/docs/NEXT-PHASE-CONSTRUCTION.md)：保留原 AN1→AN-CI→AN2→AN3 顺序；收口以 #625 / #626 后继回执为准。
- [支线前 v4 完整计划](https://github.com/auguspp/decision-kernel/blob/3843e13ae20941c0a20241d509eb02bf9f293ea0/docs/NEXT-PHASE-CONSTRUCTION.md)：保留 B1 第一切片及其阶段限制；已交付项不得重新列为 NEXT。
- [v3 人本工作台 / Quick Inbox / News](https://github.com/auguspp/decision-kernel/blob/86c1d2075d3679ef1b92788e49674f7eaf4f77b2/docs/NEXT-PHASE-CONSTRUCTION.md)
- [v1 A3–A5 / B1–B2 原范围](https://github.com/auguspp/decision-kernel/blob/bceb4b55488a10ba800b22f5798515bc42731635/docs/NEXT-PHASE-CONSTRUCTION.md)

旧授权、限制、失败和退出理由留在精确原件；本次只更新当前入口，不追认历史成功。
