# Kernel 2.0 — P1 当前架构责任图与 CI 成本基线 v1

日期：2026-10-10（Asia/Singapore）。计划：[KERNEL-2.0-PLAN-20261010-v1.0][PLAN]；归属 [#508][OWNER]。本文件是固定时点的工程盘点，不是第二份实时进度表、最终目录设计或迁移授权。实际交付/验证及下一步以 #508 顶部的最新交接回执和本文件 PR 为准。

## 1. 阅读基线、结论与证据等级

代码 M=`88f5a11eeefe79c0748b77f16e5bd13063249e76`，tree=`7fe5653945086031e01e7684f8c6af35fd61bc3b`，即 #800 合并后的 main。写入本文件前重新检查 main 未变。本轮没有解析生产 R，没有运行行情、Research、Odds、来源试验或 publisher；历史 CI 查询不等于当前生产读取。

**结论：现有 core / method / live composition / saved-reading 边界值得保留；2.0 的主要盘点问题在外围责任、名称与实际用途的偏离、配置/原件/索引/副本的区分，以及验证与交付成本的归属。现在没有证据支持推倒重写、统一万能 source 对象或按测试配额删测。**

本轮实际读取根目录、docs、src、.github 和 Workbench 的相关目录/树、任务入口以及下列关键文件；对取得的 Python 文件做静态 AST/导入检查，对 registry 做 JSON 计数，对六个已选 Actions run 的完整 job 列表和必要日志做时间摘录与本地复算。不是完整 checkout、全仓调用图、全部测试/fixture 审计或所有数据源的端到端血缘认证。

证据等级：**CODE** 为本轮实际源码/配置；**CONTRACT** 为本轮读取的现有说明/工作协议；**HISTORY** 为原 Issue/PR 的历史结果，未在本轮重新验收；**UNKNOWN** 为未检查或证据不足。下文 owner 表示语义/写入责任，不是新增 GitHub 团队、审批角色或权限。

## 2. 当前责任与消费者地图

| 责任 | 当前归属与可核入口 | 写入者 / 直接消费者 | 生命周期与处置 |
|---|---|---|---|
| 领域身份、PIT、Evidence、Research、Market、Odds、Human surface | `src/decision_kernel/` 领域类型；实际读取 `research_commit.py`、`workflow.py` [S1][S2] | Research 方法提供输入；commit 与 spine 检查使用；不由 provider/UI 获得决定权 | CODE：KEEP 不变量；未对所有领域模块作闭包依赖扫描 |
| 研究方法与质量政策 | README 的 method/constitution 分离、AGENTS 研究路由；`research_workflow_v1.py` 等方法文件 [S0][S3] | 研究者/方法产生 review；核心接收 method-agnostic 包 | CONTRACT + live import：KEEP 可替换性；各方法完整实现本轮未逐一重读 |
| 通用研究提交 | `ResearchCommitPackage` → `commit_research_package()` [S1] | 精确 REVIEW snapshot + Evidence 输入；产生 COMMITTED snapshot；供离线保管或 live 使用 | CODE：schema 1/2 分开；framing 不进入 information identity；COMMITTED 不代表当前价格资格或 Human 接受 |
| 默认 live 组合与 CLI | `live.py`、`cli.py`，pyproject 的 `decision-kernel` entry point [S3][S4] | CLI 注入 fetch capability；live 串接提交、明确行情获取、policy 与 spine | CODE：组合层可认识 HiThink 映射，不把它当纯领域层；不新增调度/重试/永久状态 |
| 来源采集与产生器 | `.github/workflows/` 的 source/radar/stock/industry 等入口，`runtime/` 对应产生器 [S5][S6] | 获准 workflow/CLI 写各自 run artifact；Collector 按 run/attempt/head/purpose 读取 | CODE/CONTRACT：每类源的完整请求、单位、因子和采集副作用未逐一审计，保留 UNKNOWN；文件存在不是已启用或已授权 |
| 生产声明与读取用途索引 | `decision_inputs/` 等显式输入；`current_state/registry.json`；base Collector 的配置读取 [S5][S7] | 经授权修改的配置/登记；Inbox、Watch、Collector 分别消费 | CODE：registry 是用途索引，不是全量状态或接受数据库；生产 packages 另由同 code commit 的 workflow 声明读取 |
| 研究进展、提交与结果保管 | `docs/readings/`、`research_runs/` 的显式 archive；`runtime/research_archive.py` [S7][S8] | 原研究/保管操作写精确版本；archive reader 只读并验证所选档案 | CODE：保存/登记/恢复与执行分离；旧引用与失败 KEEP；不能只按目录判定所有对象格式 |
| Human 决定与方法补充 | registry 中 `HUMAN_DECISION_CHECKPOINT` / `HUMAN_METHOD_SUPPLEMENT` 指向 `docs/decisions/` [S7] | Human 原决定经授权留存；展示、Watch 或研究接续按精确用途消费 | CODE/CONTRACT：不从文件存在推断持仓、交易或继承接受；本轮不重新评价这些决定 |
| 基础读包收集与发布 | `runtime/current_state_delivery.py` 的 `GitHubAPI`、`Collector`、`publish` [S5] | 读取既有来源和配置；写派生 Git tree/commit/ref；不得执行 source artifact | CODE：唯一基础发布机制；保留预算、失败分类、旧结果日期、fast-forward 与不确定写入处理 |
| 读面扩展与 D 接点 | `current_state_delivery_with_odds_watch.py` 的 subclass/attach 链 [S9] | 各 reader 使用同 Collector/payload/files；联合送到综合阅读输出 | CODE：实际责任已覆盖 Radar、Industry、News、Research、D，而不只是 Odds Watch；候选责任收敛点，尚非缺陷或拆框架决定 |
| 人读 UI 与独立状态观察 | `workbench/reading.mjs`、同目录消费者和测试 [S10] | `openPinnedReading` 固定 R、读已登记详情；Quick/Health/Inbox 另读 Issue 且保留独立时钟 | CODE：shape/selected-file hash 校验不等于重算 canonical reading_hash；Sites 实际部署和浏览器结果本轮 NOT_RUN |
| CI、维护与供应链 | `.github/workflows/ci*.yml`、`.github/scripts/ci-*`；GitHub 原生维护说明 [S11][S12][S13] | 原生事件启动适用验证，final gate 汇合；正式 PR/main 证据分别消费 | CODE/CONTRACT：四 scope KEEP；CodeQL/依赖提案与业务 CI 分开；本轮未读取全部安全告警或重新定安全政策 |
| 回归、fixture 与 evaluation | `tests/`、Workbench `*.test.mjs` / browser、`eval/` 与 dogfood；CI 的显式 collection/分组 [S11] | 开发者维护保护；CI 执行；历史 evaluation 不自动成为 runtime 输入 | CONTRACT/目录：永久 test identity、fixture 成本及逐项可退役清单尚 UNKNOWN；不因一次性文件名直接删除 |
| 计划、架构与运行进度 | AGENTS → NEXT/#297 → #508 当前计划/回执；#351 产品、#621 Sites、#581 运行健康 [S0][S13] | Human/RM 管范围；实施者写证据；新会话从入口恢复 | KEEP 原 owner；Issue OPEN 不等于工程未做，Closed 不等于当前运行健康；不建立第二进度平台 |

### 2.1 两条已从代码核到的路径

```text
方法/外部研究 -> REVIEW ResearchCommitPackage + exact Evidence
             -> research_commit.validate / commit_snapshot
             -> COMMITTED ResearchSnapshot
             -> (满足 spine 条件 + framing，才在 live 中调用 fetch_market)
             -> workflow.run_decision_spine
             -> Odds -> Rehearsal -> Human surface
```

`research_commit.py` 的本地导入为 evidence/identity/primitives/rehearsal/research，不依赖 runtime/provider。`live.py` 则明确允许默认映射、方法包装和注入的市场读取；不能把两者的不同依赖集合误判成应全部一样。[S1][S2][S3]

```text
显式生产输入 + 原 workflow/run/attempt/head
 -> 保存来源 artifact / 明确 Git 原件
 -> base Collector（资格、时钟、字节、预算、历史/新失败）
 -> 扩展 reader/attach 链 + registry 的 eager/on-demand 投影
 -> base publish（Git 对象、候选读回、fast-forward ref）
 -> read-model/current-state 的 R
 -> Workbench 固定 R 详情读取 / 其他获准消费者
```

这是一条静态接口链，不是本轮重新运行的生产闭环。Quick/Health/Inbox 的独立 Issue 观察和 `read-model/news-live` 派生缓存不能冒充综合 R 的组成字节；本轮没有读取这些在线结果。[S5][S6][S9][S10]

## 3. 当前 placement inventory：对象不是文件后缀

| 对象 | 当前默认位置 / 权威归属 | 可变性 / 读取与保留规则 | 迁移时不能丢的区别 |
|---|---|---|---|
| 领域/方法代码 | `src/decision_kernel/`，各 owning contract | main 可演进，固定 commit 不变；依赖方向由责任而非目录名决定 | 核心 law 与方法 policy；公开稳定接口范围待 P3 决定 |
| 当前输入声明 | `decision_inputs/`、`radar_inputs/`、`provider_requests/`、`ui_inputs/` 及 workflow literal inputs | 经授权前向修改；每类应以实际消费入口判断现役性 | 声明不是源输出；目录存在不是 active inventory 完整证明 |
| 用途登记 | `current_state/registry.json` | 随代码版本演进，旧 M/R 保留旧登记；不由 reader 修改 | registry 定位、生产配置和 Human 接受分别成立 |
| 结构化研究包 | `research_cases/`、部分 `dogfood/` 和显式 archive | 旧包身份、方法与 schema 按原合同；新版本不继承原接受 | 文件名 v2 不能等同软件 2.0 |
| 研究底稿与原件 | `docs/readings/`、`research_runs/` 的特定 ref/path；大型原件可能另有 Git/Actions 保管 | exact commit/blob/bytes，后继修订保留原文；是否完整原件逐档判断 | Markdown 摘录、来源 PDF 字节和可恢复定位不是同一件事 |
| Human checkpoint | `docs/decisions/` 的显式用途引用 | 原 Human 文字/时点保留，后继决定独立留存 | 接受 Research、价格条件、Watch、实际交易不合并 |
| source/run artifact | 原 Actions run/attempt/artifact 或经验证的 Git 保管 | 原平台到期与 Git 副本的资格规则分开 | 有 hash/URL 不等于已永久保管；旧字节不恢复当前源资格 |
| 综合 read model | `read-model/current-state` 的 `current-state.json`、README、sources/details | 可变 ref 每轮解析一次成 R，随后固定；生产器之外的派生副本 | M、R、source ref、market time、generated time 分开 |
| News 快速缓存 | `read-model/news-live` | 独立 latest-only 派生缓存，按现有新闻消费合同 | 不是第二 canonical state；不和综合 R 隐式拼包 |
| 测试和实验材料 | `tests/`、Workbench tests/browser、`eval/`、dogfood 类材料 | regression / fixture / evaluation / 历史恢复用途逐项区分 | fixture 非生产数据；历史 reader 可仍现役；退役 executor 不必永续 |
| 工程说明与状态 | `docs/` 说明、少量后继 ADR；Issue/PR/run 为执行证据 | 固定文档版本与当前回执分开；新决定 supersede 而非抹历史 | 不为当前状态移动几百文件，不从旧 NEXT 重开已完成工作 |

**registry 的实际静态数值：** 取得文件为 76,385 bytes，blob `4e83e7a44ecebe26ccfa0e39cb4499dab959a59f`；JSON 解析 `references` 共 **107** 条，其中显式 `ON_DEMAND_ARCHIVE` **56** 条、未带该 read_policy 的原 eager 路径 **51** 条。它们是引用条数，不是公司数、不同原件数、源请求数或完整历史数。部分引用共享同一源文件；不能用 107 推算每日 107 次读取。登记还含独立 research_calendar、historical_handoffs、research_work_read 和 capability_gaps，计数没有把这些当 references。[S7]

archive reader 当前仅接受 `research_runs/` 或 `docs/readings/` 的有界深度、flat regular files；`NAME` ASCII 正则同时用于 record/dependency ID 与相对文件名。CONS-08 的问题在本 M 仍可由源码确认。不能只改一个 Unicode 正则：路径安全、规范化碰撞、历史 same-blob 恢复、hash 与现有消费者都要由 P2/P3 决定。[S8]

## 4. CI 成本：六个事先选定的样本

选样登记：[本轮 P1 开始与样本表][START]。#799 是近期已交付工程 full/main reuse，#637 是历史 content PR/main，#670 是历史 main 因环境变化回 full，#799 publisher 是独立发布成本。目的为覆盖路径，不按快慢挑样；均 attempt 1。GitHub jobs 使用 `filter=all, per_page=100`，返回总数分别 7/4/4/4/7/1，均一页完整；其中三个 4-job 响应各含两个 skipped wrapper，表中不算作实际 runner 占用。

### 4.1 口径

- **作业跨度**：`max(active job completed_at) - min(active job started_at)`。不声称覆盖提交、run 创建前排队或最后用户通知的全过程。
- **累计作业秒 / 分钟**：各 active job 的 `completed_at-started_at` 求和，再除 60；包含 job overhead，不是 CPU 时间、实际账单或平台计费舍入。
- **创建后等待总秒**：各 active job 的 `started_at-created_at` 求和；这是原 job 创建后的间隔，不能推断全部队列/依赖延迟或平台根因。
- step 时钟是秒级；Test 步骤可包含 worker collection/进程启动，不全等于纯断言执行。未取得可独立分离的 worker collection 成本，保持 UNKNOWN。
- 时间摘录在附录逐 job 给出并用 Python datetime/Decimal 复算；摘录不是原 REST JSON 字节保管，也不是完整 CI ZIP、JUnit 或环境等价性的再认证。

| 用途 / 原 run | active jobs | 作业跨度（秒） | 累计作业秒 | 累计作业分钟 | 创建后等待总秒 |
|---|---:|---:|---:|---:|---:|
| #799 PR full [37862015470][R1] | 7 | 217 | 613 | 10.2167 | 14 |
| #799 main reuse [37862646073][R2] | 2 | 71 | 34 | 0.5667 | 39 |
| #637 content PR [36374091305][R3] | 2 | 22 | 19 | 0.3167 | 4 |
| #637 content main [36374500857][R4] | 2 | 17 | 15 | 0.2500 | 3 |
| #670 main fallback full [36693704611][R5] | 7 | 198 | 565 | 9.4167 | 17 |
| #799 normal publisher [37862757783][R6] | 1 | 138 | 138 | 2.3000 | 1 |

#799 full 的 prepare/research/shard4/shard3/shard2/shard1/gate 作业秒分别为 **31/19/121/128/132/168/14，总计613**。本地首次人工期望和为713，算术断言拒绝后按原时钟重算并更正；没有改变源时钟或重跑CI。独立 main 为29+5=34秒，其中最终 gate 从00:02:28创建到00:03:05开始的 **37秒**不是测试执行。两个 scope 成本不同，不是本次整合带来的提速。

### 4.2 可见 step 成本与限制

#799 full：七处安装步骤累计 **43秒**；prepare 全 collection **15秒**，research collection **2秒**，四分片独立 collection **17/18/18/18秒**，合计 **88秒**；research 与四分片 Test 步骤合计 **418秒**；上传步骤累计 **8秒**。剩余为 checkout、环境、校验、其它步骤与 job 边界开销，不能把重复 collection 全部直接删掉，因为它还承担身份集合对账。[R1][S11]

#799 main：安装 **6秒**、reuse 检查 **6秒**、main smoke **8秒**；full collection 与下游 full workers 实际 skipped。保留独立 main 的实际环境安装与门禁，不说“main 又跑了一次全量”。原回执中的8544 full /87 smoke为历史完整性记录，本轮没有重新下载其 collection/JUnit/ZIP 来认证全部测试身份。[R2][H1]

#670 main：prepare 日志 `109816575432` 的2026-09-30T09:04:28.9802722Z明确为 `CI_MERGE_REUSE=false REASON=FULL_REQUIRED_ENVIRONMENT_CHANGED`；随后 full collection/worker jobs 实际运行。该日志证明回 full 的已报告类别，不证明具体哪个环境字段改变；不得把它强行归因于 Python patch 或网络。[R5]

publisher：基础安装 **5秒**、可选 saved-price engine 安装步骤 **20秒**、合并的校验/收集/发布步骤 **107秒**。该步骤无法据 job 时钟再拆成网络与计算；可选安装脚本自行处理失败，step success 本身不证明依赖实际安装成功。未在本轮读取固定 R 正文，不能由这个绿色 job 预签内容质量。[R6][S6]

### 4.3 现役范围与不能提前作出的结论

现有 CI 已实现 content / draft_feedback / full / merge_reuse；不是准备新建四层CI。`ci-content-scope.py` 的 prose 白名单仅根 README/AGENTS、CI-MAINLINE、RESEARCH-ENTRY、research-outcome-contract，另有符合严格新增条件的 `docs/readings/*.md`。**本文件的预定路径不在 content 范围；按原 Ready full 执行，不移动到 readings 或扩白名单来省验证。** Draft feedback 也不能作为正式合并证据。[S11][S12]

四分片降低关键路径，但不消除累计 runner 占用；上述样本没有证明 CI 失控或稳定耗时分布。安装/执行/上传、当前 fixture/test 维护量、过时 head 成本、长期 reuse 命中率、失败比例、真实计费和自然 publisher 触发总量仍需按实际决策补局部证据，不新建遥测平台。#637、#670 与 #799 的代码、集合、日期不同，不能据耗时差宣布回归或改善百分比。

## 5. P2/P3 应解答的具体问题，不是已采纳重构

| 编号 | 已观察证据 / 未证明部分 | 本轮处置 | 给后继的有界问题 |
|---|---|---|---|
| P1-A | commit 与 spine 的独立方法接口已存在；live 刻意承担默认连接 | KEEP [S1–S4] | 明确 public/stable 与 internal 的接口边界，避免为目录一致而引入 core→runtime 反依赖 |
| P1-B | with_odds_watch 的 collect 串接多家 reader，共享 payload/files/budget；名称小于实际职责 | CONSOLIDATE 候选，未认定功能故障 [S5][S9] | 组合根、通用读取基础能力与业务 reader 的 owning contract 怎样明确；不要先造 plugin/event bus |
| P1-C | publisher workflow 按源 path/title/event 有例外，Python 又核 exact native attempt | KEEP 安全语义，检查责任重复 [S6][S9] | 哪些只是便宜预筛、哪些是唯一资格 owner；不能见两层检查就删除真正的拒绝传播 |
| P1-D | registry、workflow配置、档案、R、News缓存、独立Issue各有不同职责 | KEEP 区分，placement 待定 [S7][S10] | 如何用少量规则说明 source-of-truth/writer/reader，避免把全部对象压成一个“状态” |
| P1-E | ASCII NAME 同时校验逻辑ID与显示文件名 | CONS-08/09 实例，设计未冻结 [S8] | Unicode安全/碰撞/旧路径恢复与机器ID分离；#782原ASCII映射历史继续可读 |
| P1-F | full/main/content/发布成本可分别量化；独立 collection 有非执行目的 | KEEP 四scope；退役清单 UNKNOWN [S11][S12][R1–R6] | 先退出过期 executor/writer 责任，再合并重复证明；不能把多个测试塞进循环伪装删测 |
| P1-G | CI checkout/upload 为精确SHA，publisher checkout/setup为版本tag | 有限源码观察，不是漏洞或增权结论 [S6][S11] | P2供应链对照时核适用固定版本策略与更新成本，不能顺手升级依赖/Actions |
| P1-H | runtime同处容纳纯验证、Git读取、外部产生器及CLI组合；docs/dogfood与顶层dogfood并存 | 分类需按实际消费者，非全部迁移 [S5][S8][S9] | P3 placement应区分行为责任和历史保管；全仓死代码/手动用途仍需逐切片证明 |
| P1-I | read面绑定来源不自动证明派生数值全程同口径 | CONS-05完整审计未完成 | 对选定价格/因子/结构/Outcome链绑定实际provider、channel、period、units、revision与算法；不推断已混源，也不推断绝无混源 |
| P1-J | Workbench明确shape/所选文件校验，不重算canonical reading_hash；Issue观察独立于R | KEEP 诚实验证标签 [S10] | 兼容与显示改动不能扩大成端到端验证/部署证明；实际浏览器及独立会话另外验 |

#354/#626 已完成的有界 CI/retirement 前驱保持 HISTORY，不因为本盘点再开旧专项。一次性脚本文件存在、无直接 import、旧日期都不足以 RETIRE。CONS-07能源/航运传感器是另有范围的补盲候选，不进入本轮；C/D自然窗口、失败、成熟结果与Sites暂停仍由原任务持有。

## 6. 盘点交付边界与下一步

本 v1 提供当前主要责任图、placement inventory、六个有界成本样本、已证边界及带明确 UNKNOWN 的后继问题。它足以作为 P2 先例对照的输入，但不是全仓架构正确性证明、最终 ADR、全链 lineage 或批准的删除清单。

文件保存、正式 PR 适用 CI、main 合并、独立 main、普通 publisher 与必要读回仍分开成立，不由文档存在预签。未完成的交付步骤记录在本 PR/#508；先恢复同一文件/PR，不重新盘点或复制另一主计划。交付后沿 CONS-11 按 P1-A…J 的实际问题对照成熟模式，再形成 P3设计；不直接从P1跳到Unicode修复或删测。

本轮未改 production/schema/registry/workflow、任务时钟/通知、供应商请求、隐私/费用/权限或投资能力。相应文档PR的原生验证不冒称来源/模型任务；本地只有文件静态解析、计数和时钟算术，没有执行仓库业务入口。

## 附录 A：原 job 时钟摘录与重算方法

所有时钟为UTC，日期分别在小标题注明。每行：`job_id / purpose / created / started / completed`。零时长 skipped wrapper 不在下列active列表。原件入口为各run页面及 `actions/runs/{id}/jobs?filter=all&per_page=100`；这些摘录不是完整API响应备份。

### 37862015470 / 2026-10-08 / head f90e71e3e048b8e65039002397bc9368d973349c

```text
113599725444 prepare 23:54:44 23:54:46 23:55:17
113599886682 research 23:55:17 23:55:19 23:55:38
113599886718 shard4 23:55:17 23:55:19 23:57:20
113599886757 shard3 23:55:17 23:55:19 23:57:27
113599886792 shard2 23:55:17 23:55:19 23:57:31
113599886825 shard1 23:55:17 23:55:19 23:58:07
113600676661 gate 23:58:07 23:58:09 23:58:23
```

### 37862646073 / 2026-10-09 / head f763790ced6f605f690e58ca54a1f3c546ffcfe3

```text
113601777255 prepare 00:01:57 00:01:59 00:02:28
113601930581 gate 00:02:28 00:03:05 00:03:10
```

### 36374091305 / 2026-09-28 / head 8b8dca56ccc5c678740144d3adb11c5898471baf

```text
108776259679 prepare 03:32:06 03:32:08 03:32:20
108776305740 gate 03:32:21 03:32:23 03:32:30
```

### 36374500857 / 2026-09-28 / head 1ef57be901243f683cb0cc15cedd3ed159fdd02e

```text
108777443954 prepare 03:38:20 03:38:22 03:38:30
108777476592 gate 03:38:31 03:38:32 03:38:39
```

### 36693704611 / 2026-09-30 / head 0af68fa6afe205846776b070fc942bcf16d8058b

```text
109816575432 prepare 09:04:10 09:04:12 09:04:48
109816801308 shard1 09:04:48 09:04:50 09:07:09
109816801314 shard2 09:04:48 09:04:50 09:06:34
109816801343 shard3 09:04:48 09:04:51 09:06:40
109816801361 research 09:04:48 09:04:51 09:05:11
109816801616 shard4 09:04:48 09:04:51 09:07:14
109817647835 gate 09:07:14 09:07:16 09:07:30
```

### 37862757783 / 2026-10-09 / head f763790ced6f605f690e58ca54a1f3c546ffcfe3

```text
113602155243 publisher 00:03:14 00:03:15 00:05:33
```

重算每个小标题的行：将对应日期和各时间解析成带 `+00:00` 的 datetime；逐行求 `(completed-started).total_seconds()` 和 `(started-created).total_seconds()`；前者求和/60为作业分钟，`max(completed)-min(started)`为跨度。本轮六组实际复算的累计秒为613/34/19/15/565/138，跨度217/71/22/17/198/138。无永久计量runtime或新增计数测试。

## 附录 B：精确源码与历史依据

所有 S 链接固定本 M；只对上文说明的读取范围作证。各自原合同/历史后继仍按原入口读取，不因本文件统一改写。

[S0]: https://github.com/auguspp/decision-kernel/blob/88f5a11eeefe79c0748b77f16e5bd13063249e76/AGENTS.md
[S1]: https://github.com/auguspp/decision-kernel/blob/88f5a11eeefe79c0748b77f16e5bd13063249e76/src/decision_kernel/research_commit.py
[S2]: https://github.com/auguspp/decision-kernel/blob/88f5a11eeefe79c0748b77f16e5bd13063249e76/src/decision_kernel/workflow.py
[S3]: https://github.com/auguspp/decision-kernel/blob/88f5a11eeefe79c0748b77f16e5bd13063249e76/src/decision_kernel/live.py
[S4]: https://github.com/auguspp/decision-kernel/blob/88f5a11eeefe79c0748b77f16e5bd13063249e76/pyproject.toml
[S5]: https://github.com/auguspp/decision-kernel/blob/88f5a11eeefe79c0748b77f16e5bd13063249e76/src/decision_kernel/runtime/current_state_delivery.py
[S6]: https://github.com/auguspp/decision-kernel/blob/88f5a11eeefe79c0748b77f16e5bd13063249e76/.github/workflows/current-state-read-entry.yml
[S7]: https://github.com/auguspp/decision-kernel/blob/88f5a11eeefe79c0748b77f16e5bd13063249e76/current_state/registry.json
[S8]: https://github.com/auguspp/decision-kernel/blob/88f5a11eeefe79c0748b77f16e5bd13063249e76/src/decision_kernel/runtime/research_archive.py
[S9]: https://github.com/auguspp/decision-kernel/blob/88f5a11eeefe79c0748b77f16e5bd13063249e76/src/decision_kernel/runtime/current_state_delivery_with_odds_watch.py
[S10]: https://github.com/auguspp/decision-kernel/blob/88f5a11eeefe79c0748b77f16e5bd13063249e76/workbench/reading.mjs
[S11]: https://github.com/auguspp/decision-kernel/blob/88f5a11eeefe79c0748b77f16e5bd13063249e76/docs/CI-MAINLINE.md
[S12]: https://github.com/auguspp/decision-kernel/blob/88f5a11eeefe79c0748b77f16e5bd13063249e76/.github/scripts/ci-content-scope.py
[S13]: https://github.com/auguspp/decision-kernel/blob/88f5a11eeefe79c0748b77f16e5bd13063249e76/docs/github-native-operations.md
[PLAN]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6094482452
[OWNER]: https://github.com/auguspp/decision-kernel/issues/508
[START]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6094731990
[H1]: https://github.com/auguspp/decision-kernel/issues/297#issuecomment-6071512908
[R1]: https://github.com/auguspp/decision-kernel/actions/runs/37862015470
[R2]: https://github.com/auguspp/decision-kernel/actions/runs/37862646073
[R3]: https://github.com/auguspp/decision-kernel/actions/runs/36374091305
[R4]: https://github.com/auguspp/decision-kernel/actions/runs/36374500857
[R5]: https://github.com/auguspp/decision-kernel/actions/runs/36693704611
[R6]: https://github.com/auguspp/decision-kernel/actions/runs/37862757783
