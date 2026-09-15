# MU 单次执行失败记录：输入被拒绝，必要较晚来源未齐

**DRAFT / NOT MERGED / NOT ACCEPTED RESEARCH。没有完成的 Quick，也没有原 Funnel 结果。**

本页是这次尝试的结束回执；初始 README 和 preflight 保留其输入准备时的原貌，不表示后来通过验收。需求侧要的完整案例本次未交付。

## 冻结身份与实际执行

- execution_id：`p0-4a-MU-20260909-sca-7c9e2b41`
- 输入先行 commit：`affca344836b57769bed39c1563e8bad598246e2`
- 原始 input blob：`7b14f49fb8a592d9dc0003b9207fc92bd26dabc9`
- 原始 input 文件 SHA256：`5322243ce8b6b626aee0a1b97a09098c955979ee4b8734682c5c39481ea458ad`
- 代码：`29f98409dddd0032259e05a4bdad7ebad60b8a76`；已有阅读快照：`18f093c8c9c51a03c238233c143ad45d8901c9a5`
- cutoff：`2026-09-08T21:36:01.998742Z`，北京时间 2026-09-09 05:36:01.998742。
- 单次研究起始：`2026-09-08T21:42:35.297607Z`；最后来源动作记录：`21:53:01.827180Z`；停止处置本地时钟：`21:59:04.267952Z`。
- 原预算：48 原子动作 / 12 查询字符串 / 36 成功读取事件 / 1 技术重试 / 35 分钟，均为 SOFT_EXECUTOR。
- 已记录：46 动作 / 11 查询 / 31 成功读取事件 / 4 失败读取 / 1 重试；起始至停止向上取整 17 分钟。31 次读取包含重复、目录、标题片段和 PDF 页面，绝不是31份一手报告。

来源是仓库已保存的 Micron SCA 研究观察，不是新 Radar 或价格观察。执行者已见旧研究，因此不是盲测或独立新自然样本。原 Human WAIT / NO_ACTION 及旧研究均不改写。

## 两个必须分开的失败

### 1. 输入准备错误：原 schema 在 Funnel 之前拒绝

首轮正常 PR CI：`34282031752`；test job：`102248818094`。已读取完整 checkout/install/pytest/cleanup 日志。checkout 为 `d6ca95fd73cca97cf494c5aefb64c9c03575ebc3`，绑定初始 head 与既有 main。真实结果：**1 failed, 2094 passed in 639.89s**。

新测试在 `ExternalResearchInputPacket.model_validate_json(raw)` 处失败：`seed_evidence_artifacts.0.published_at` 是 `null`，而原 Evidence schema 要求有效 datetime；连带 seed tuple 校验失败。

这是执行者准备输入的错误，不是原 schema 或 #288 的缺陷。没有得到原模型 canonical input hash，没有进入 candidate/Funnel 校验。**文件 SHA256 不是 canonical model hash；不能填一个原始 JSON 哈希冒充。**

原 `input.json`、cutoff、seed、preflight 和测试不修补；不补造发布日期，不删改断言，不用另一个同名输入把失败变绿。本次收口只增加失败资料，不修改 runtime、Kernel、Funnel、#288 guard 或历史测试。

### 2. 必要较晚来源未取得：不能完成 Quick

| 冻结必读来源类 | 实际阅读及边界 |
|---|---|
| FORMAL_PERIOD_ACTUALS | 正式10-Q和业绩正文已读；区分报告期、单位和实际数。 |
| SCA_CONTRACT_COVERAGE | 已读10-Q及准备稿中的已签量价约束、目标覆盖、履约风险；六月口径不是九月当前值。 |
| CASH_CAPITAL_ECONOMICS | 已读现金/融资分类、资本计划及七月资本和供应商正文；RPO不等于利润或永久 owner cash。 |
| INDEPENDENT_INDUSTRY_CONTEXT | 已读 SK hynix、Samsung 一手发布正文；行业管理层叙述不是独立认证，不能把DS利润当存储利润。 |
| SUBSEQUENT_ISSUER_UPDATE_CHECK | **未齐**。专项搜索发现8月10日活动可能包含财报后SCA变化；官方活动页只有日期和链接，官方链接的 webcast 返回404，无一手等价正文。 |

上述已读内容只是实际动作和有限历史观察，不是这份无效 input 下已验证的 Evidence/Funnel。七月 Ford、GM 和汽车协议正文说明其属于原16份协议，不能据此补上八月增量。二手 transcript 只作发现线索，不采用其中的合同数量或变化为 FACT。

官方活动地址和失败 webcast、查询字符串、返回引用及记录时钟见 `action-ledger.json`。另有八月26日业绩日期公告及现代季报索引 Internal Error，均保留；没有把这些失败说成公告不存在。唯一技术重试用于同一八月26日地址，未再重试 webcast。

**原 accessibility preflight 取得了核心正文，但并未证明所有必要较晚来源可得。先行冻结后又在输入尚未通过安装模型时启动研究，没有达到本次任务要求的完整前置门槛。** 本记录保留这个执行错误，不把它解释为市场的未来 WAIT trigger。

## 留存内容及可验证程度

`pre-research.unbound.json` 保留在进一步来源检查前写出的 Pre 内容，仍为 CONTINUE_TO_QUICK，没有事后改成 WAIT/STOP。其文件 SHA256 与当时本地记录完全相同：`4bb3c6b0c992f6b5e2046b66585bb7b1dd4a2aadbc89acb6ee19dab739c8722a`。两个 Evidence UUID 仅是当时对 FILING / REMARKS 的预分配引用；本次不提供已验证 Evidence 包。

当前容器中原临时 journal 已不可用。`action-ledger.json` 是依据保留的动作记录恢复的序列、URL、查询、返回引用和本地时钟，不宣称是原 journal 字节、原 HTTP 回放或平台原生遥测。共享时钟与31-33动作的延后记录明确标注。未记录私有思考过程。

`failure-record.json` 是描述性失败回执，**不是** `ExternalResearchValidationResult` 或 `ResearchExecutionReceipt` 的有效实例。这里的来源缺口不能冒充原校验器输出的 EXECUTION_GAP。实际状态是：输入 REJECTED；Research 完整性 INCOMPLETE_SOURCE；Funnel NOT_REACHED；Quick/Funnel 结果均无。

## 结束边界

没有第二次 MU 执行，没有神农追加尝试，没有补预算、Re-run、手动 dispatch、Research/handoff/current-state 登记、Deep/Odds、Human 写回或投资权限。#285/#287/#263 和 #288 已合并代码不改。

本 Draft 留在失败状态供过程审阅；**不合并，不作为完整 Research 交需求侧签收，也不把2094个其他测试通过说成本次输入通过。**
