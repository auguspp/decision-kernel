# 2026-09-27 本轮交接：B1 六族保存读取已交付，下一主工程 B2

## 0. 本轮到此结束

Human 本次明确要求：**“本轮结束，同步一下状态，写一个交接文档存档到 github。”**

本文件是工程状态与下一会话的恢复入口，不是新研究、方法变更、B2 开工或 Sites 部署授权。本轮只完成交接文件、必要导航同步及其既有 CI/合并/发布流程；不再调用市场来源，不启动 B2、Quick、Full、Odds、Watch 或交易。

**交接结论：B1 六个有限来源家族的采集实现、原件保管、正常固定 R 读取和 Markets 代码已经交付。Sites 对本批 Markets 的生产采用、手机新面板、自然持续运行及全市场覆盖没有因此验收。下一主工程仍按原批准顺序接 B2 有限近期研究日历。**

执行导航由 [#297](https://github.com/auguspp/decision-kernel/issues/297) 持有，工作台产品范围由 [#351](https://github.com/auguspp/decision-kernel/issues/351) 持有。本文是一次固定快照；以后先读当时最新入口，不把本文的版本永久当作最新版本。

## 1. 冻结本次交接所依据的现场

| 项目 | 固定值及含义 |
|---|---|
| Repository | `auguspp/decision-kernel` |
| 写交接前 main / M0 | `38a68e4b558fefea855190330af5e41f200a0ef7`；#616 合并版本 |
| 写交接前读取版本 / R0 | `f299f08c3dcb101ff721d507cc4e4123f64d9a48` |
| R0 的代码绑定 | `code_commit = M0` |
| R0 的普通 publisher | `36327067044 / attempt 1 / success` |
| 其触发 main CI | `36327022256 / attempt 1 / success` |
| R0 检查截止 | `2026-09-27T14:47:13.092329+00:00`；不是行情时间 |
| 本次归档开始前 open PR | 返回空列表；不外推为以后没有并行施工 |
| 交付证据主入口 | [#616 回执 5857101690](https://github.com/auguspp/decision-kernel/pull/616#issuecomment-5857101690) |

本次状态同步重新读取了实际 main/ref、read-model/ref、M0 的 AGENTS/NEXT-PHASE、#297 当前入口和 #616 交付回执。下文测试和原件核验范围按该回执保留，不把“本次再次读到回执”说成又运行了一轮全部测试或源采集。

交接文件合并会产生新的文档 commit，正常 publisher 也可能推进 R。那属于**归档文档的后继版本**，不改变上述 B1 验收基线，也不是新的市场捕获。归档 PR 和 #297 后继评论记录其实际 commit、CI 与读回结果，不在本文预写成功。

## 2. 已完成什么，哪些工作不得重建

| 增量 | 已有事实 | 接续方式 |
|---|---|---|
| #610 | 国际指数与 Shibor 两个有限手动来源家族，沿原 Tushare Relay | 保留来源合同、原凭证和失败记录 |
| #612 | 两族原件接入正常固定 R，增加 Markets 阅读入口 | 后继六族实现向前兼容，不重做第一版 |
| #614 | Treasury、ECB、Yahoo 期货、Coinbase 四族公开来源及真实捕获 | 复用已有 codec、原 ZIP 和 run，不再另造同功能采集器 |
| #615 | 四族并入原 Collector / 固定 R / Markets，保留旧两族 | 集成已合并，但其首个实际发布存在下述 TypeError，不把总 publisher 成功当模块成功 |
| #616 | 用原 codec 的精确 JSON 表示修复汇总序列化；首次与 prior-R 恢复一起覆盖 | 已合并、实际发布读回完成，不再保留“#616 修复中”为当前 NEXT |
| #611 / #613 | 适用的复用检索顺序和治理生命周期接续 | 沿当前 AGENTS 消费，不新增治理工程阶段 |

内部实现恢复重点：`src/decision_kernel/runtime/global_market_context.py`、`global_public_context.py`、`global_market_reading.py`；来源工作流为 `radar-global-market.yml` 与 `radar-global-public.yml`；阅读与兼容说明见 [global-market-reading-v1.md](../global-market-reading-v1.md)（正文已描述六族 reading v2）。正式变更范围、测试和原件以各 PR/回执为准。

原 A 股、新闻、Quick Inbox、Research/Odds 与历史用途记录保持原职责。没有建设新数据库、通用 provider/队列、通用 GitHub proxy 或投资执行器。

## 3. R0 中的实际市场覆盖

| 来源族 | 真实捕获 run | 可读范围 | 原数据日期与不能外推的边界 |
|---|---:|---|---|
| 国际指数 | 36308774368 | HKTECH、N225、GDAXI；3/6 | 恒生科技 9/24，日经/DAX 9/25；SPX、IXIC、HSI 仍 `TEMPORARY_QUEUE`，不填零、不猜失败原因 |
| Shibor | 36309047326 | 8 个期限 | 9/24；人民币同业年化利率，变化用 bp，不代替美债 |
| 美国国债 | 36317799016 | 1个月至30年中选取的8期限 | 9/25；Treasury par yield、年化百分数与 bp，不是债券总回报 |
| 外汇 | 36317890212 | USD、CNY、JPY、GBP 四项 | 9/25；ECB 每1欧元参考价，不自动重基准到 USD，不是可交易即时报价 |
| 黄金与原油 | 36317970476 | GC=F、CL=F、BZ=F | 9/25；Yahoo 供应商期货序列，不冒充现货或结算价；换月连续性 UNKNOWN，不计算跨日收益 |
| 加密资产 | 36318059164 | BTC-USD、ETH-USD | 9/26；Coinbase 单一场所日线，不是全市场统一报价 |

**28 个可读值 / 31 个配置序列，六族有限背景，不是全市场覆盖。** 各自的来源日期、请求/收到时刻、抓取截止、单位和两次实际返回日期分开保存；不把全部结果包装为同一时刻的“今日实时”。来源文本只是数据；原因与公司经济映射交给 Research，价格不自动改变 Belief。

最近尝试与最后可读批次分开；后继查询、采集或读取失败不能删除已经保管的旧原件，也不能用旧值冒充本次成功。原发布时间、交易日历和未建立的连续性保持 UNKNOWN。两个来源工作流仍为手动运行；可手动执行不等于自然定时已开通或已验收。

## 4. 已发布定位及核验边界

在 R0 中：`research.global_market.status = SAVED_CONTEXT`，`version = global-market-reading-v2`，`complete_global_coverage = false`。Research / Investment authority 均不由此产生。

| 已登记正文 | bytes | SHA-256 | Git blob |
|---|---:|---|---|
| `details/markets/global-market.json` | 143758 | `e1db3dee7f2458c3a11f143768de38799c9580f5b0c61dc2f7e5208c4aee5bd4` | `72eeed75dc2faac51fc4ab3897acb17d0d1cd2d0` |
| `details/markets/global-market.md` | 9038 | `074073b06af8dcb85fe99c66ca797c9bb3319bb69c2632758932cb6fbfea1822` | `5d43e5e3d9173584bb6bd96665d6169f919b7abd` |

六份 ZIP 在**同一个 R0** 的 `sources/artifacts/<SHA256>.zip`，不只保存在会到期的 Actions 附件中：

| family | ZIP bytes | SHA-256 / 文件名主体 |
|---|---:|---|
| indices | 7130 | `e20a2768b45571cbc42d52415e725c81675de3963831f504e1ee600939fa9e6e` |
| shibor | 3451 | `907a92aa39c3aec4350c97bc7d731eea7a0072fc1ddf43074b71e2531d7daed5` |
| treasury | 5066 | `fe37f402329742729280e1bdce05ed45056f4df9febd62e142b50d6b12ce4624` |
| fx | 11573 | `65f957dd995b5282cdaa3507920807ab18d2af2d89bc6e7d4902ed78c80d0d77` |
| commodities | 7133 | `91b475ef30d4016e29dbb3d9b09dab76b29e79065a5bf749b272982b12324ffc` |
| crypto | 4236 | `cdf51b49d6adf0b1550e4942456f7dfe459d0fe83a9f84b2e7b3aebb1a86fac7` |

#616 回执区分了以下证据，不得在交接时升级：六 ZIP 完整字节/CRC/SHA256、19 份原 HTTP 正文及 capture/run/code/family/时钟已核；与同 R 实际 Git blob 一致；从六份原 summary 独立拼装的 Markdown 与发布正文长度/SHA256/blob 相同。**JSON 当轮核的是实际 path/blob/size 与登记，不是本地另存完整 JSON 后再次重算其 digest。** 原生 replay 由既有 publisher 和正式回归覆盖；这些不认证市场真理。

### 工程验证记录

- #616 PR full：`36326660080 / attempt 1`，6625 unique testcase＋既有80子测试，0 failure/error/skip。原 aggregate artifact `10934088222`，1912320 bytes，SHA256 `529ec18c5cbd6b658880035cb010989ad71de3424a670e077467b399c5469572`；outer 与5个inner ZIP、身份、scope、collection/JUnit 已按原回执核验。
- main CI：`36327022256 / attempt 1`；精确 merge-reuse 该 full，另跑87测试＋44子测试。artifact `10934232520`，222763 bytes，SHA256 `645232280deef0524290b171d7aa7c6192c67cee39b0e274a7c7d0f7c268b560`。
- 普通 publisher：`36327067044 / attempt 1`；R0 已实际检查模块登记和正文，不能只看总体 success。

## 5. 必须保留的失败与已退出路线

**#615 的真实失败不能擦掉。** publisher `36325766299` 总体 success，但其 R=`fdc40947928ca4927fcb4e244b2d133af07548d9` 的 `global_market` 为 `UNAVAILABLE_OR_REJECTED / TypeError`。原因是 Yahoo 元数据的小数被原 decoder 保留为 Decimal，汇总直接交给标准 JSON encoder 导致失败；旧合成样本未包含这类小数。

#616 在完成原件 replay、summary 和 render 核验后，经原 codec 的 canonical encoded 表示跨接口，不转 float、不丢字段、不改原 ZIP，首次汇总和 prior-R 恢复均覆盖。详见 [#615 失败回执 5856774909](https://github.com/auguspp/decision-kernel/pull/615#issuecomment-5856774909)、[#616](https://github.com/auguspp/decision-kernel/pull/616)。

开工时因旧 #297 顶部停在 #612，曾漏读 #614 而形成重复官方源草稿；已在 [5856024596](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5856024596) 对账退出。不要恢复 `global_market_official` 重复采集、额外 USD/CNY 重基准或重复 source dispatch。旧 owner fingerprint/bootstrap、外部探针1010和首次部署停点也不是当前 NEXT。

## 6. 未验范围与下一步

### 下一主工程：B2 有限近期研究日历（本轮未实现、未启动）

接手后先恢复 [v4 计划](../NEXT-PHASE-CONSTRUCTION.md)、[原完整 B2 范围](https://github.com/auguspp/decision-kernel/blob/bceb4b55488a10ba800b22f5798515bc42731635/docs/NEXT-PHASE-CONSTRUCTION.md) 和 #297 最新回执。沿既有日期/事件/明确关注身份复用，先消费 #508 High-Relevance Living Prior Art，再消费 #511 候选与负面证据，最后补未覆盖检索；不能把本交接视作已经完成新的复用检查。

事件日期要有可定位来源，计划/实际、时区和未知分开；不猜财报日，不把研究过的公司当持仓，不把日历事件变成投资指令或新的审批系统。具体实现仍受原范围、预算和验收约束，不由本文新增方案。

### 待采用：原 Sites 一次集中接入六族 Markets

#612/#615 尚未采用的前端增量集中交给**原站**，不拆成逐来源部署。先核实际部署/source，再按当前 `docs/global-market-reading-v1.md` 和原 PR 差异合入，保留宿主适配、同源 R 指针、News/Quick Inbox、根入口/旧链接、owner-only、CSP、现有 PAT 与回退。

本轮没有读取生产宿主配置，也没有新部署，故**不在此推断最新 Sites 版本号或六族页面已上线**。实际页面与手机需由原站采用后验；不得用 repo merge、CI 或早期部署回执替代。展示验收只读已保存资料，不为凑验收重抓新闻、重跑六族或造 Inbox 记录。

### 保留的真实缺口

SPX/IXIC/HSI 来源缺口；原发布时间/交易日历/期货连续性未建立；自然持续运行与长期使用质量未验。需要时按既有授权有界处理受影响范围，不循环重跑整批、不从失败猜原因、不静默切源或建设新 provider/队列。

## 7. 不被本轮覆盖的研究与产品事实

#609 的真实 Quick Inbox 样本仍通过 #601 result `5853963333` 关联请求 `5853796032`、`5853804680`、`5853810250`。一个独立新会话已从 GitHub 入口与精确 locator 恢复正文、处置和 UNKNOWN，证明有范围的 continuity；**不是对全部 P1/R5-5 自然日使用、研究质量、遗漏/误报的总验收，更不是 Human 接受那份研究。** 恢复实际研究时仍须重新读当前 RESEARCH-ENTRY、#601 和原正文，不能把本文件当研究正文。

A2 自然 Human 回应及原版本绑定、明确关注/持有身份，C/D 跨期 Evidence/Prediction 与多期限 Opportunity，L/Reuse Radar 和旧 P2/P3 继续原归属，不因本轮略写而删除或抢跑。#595 聪明钱 v1.1、既有来源编排与 CI 优化不重新展开。

## 8. 权限、归属与下一会话起手

GitHub 是 canonical 状态/证据/过程后端，ChatGPT 是研究交互层。Radar discovers，Research interprets，Kernel 核 identity/time/source 一致性而非真理。Evidence changes Belief；Price changes Odds。AI Investment Authority=NONE，Human 拥有最终研究接受、判断和资本决定。

本次无新增费用、账户、PAT 权限、Secret、自然定时、模型或交易动作。原 Sites PAT 仍限单仓、仅 hosted Secret；原 Issues:write / Actions:write / Contents:read 范围不扩为 Contents:write。此处记录的是原站约束，不是本轮独立检查了 Secret 或实际授权。已有 Brief/日程不变，既有正常分支/PR/CI/独立main/普通发布门禁不减。

RM 持有范围、排序和验收；Main Construction 负责实现和执行证据。本交接不新设规则或第二状态库；后继有真实新授权/新证据时，在原入口留下前后关系，不回写旧研究、旧失败或 Human 原话。

**下一会话可直接从这里起手：**

> 继续 auguspp/decision-kernel。先固定当时 main 与 read-model/current-state，读取同 M 的 AGENTS.md、docs/NEXT-PHASE-CONSTRUCTION.md、本文以及 #297 最新回执。B1 六族来源、固定 R 与 Markets 代码已交付，不重建 #610/#612/#614/#615/#616；下一主工程按已批准范围接 B2 有限近期研究日历。Sites 六族 Markets 待原站集中采用，保留当前真实部署与回退。先消费 #508/#511 适用留存；无新密钥/费用/自然任务，无自动 Full/Odds/Watch/交易。发现并行后继时先对账再写，不要求 Human 重贴旧报告。

本轮停止于状态归档；归档的确切 commit、CI、正常发布与同步入口结果，见本文件所属 PR 和 #297 后继回执。
