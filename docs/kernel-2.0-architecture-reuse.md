# Kernel 2.0 — 架构级复用对照与增量证据

日期：2026-10-10（Asia/Singapore）。证据版本：`K2-REUSE-COMPARISON-20261010-v1`。归属 [#508][OWNER]，与[整体设计 v2][DESIGN]同在 PR #804 中评审。本文是设计的证据附录，不是第二份主计划、进度表或实施队列。

**Human已采纳的原则：架构级 Reuse First 贯穿重构。具体外部实现、目标目录、迁移和依赖采用仍待验证/采纳，P4未启动。** 有效计划为[v1.2架构复用增补][PLAN12]、[v1.1全面纠偏][PLAN11]及原v1.0未替代条款。Human本轮同意继续的是全面规划及其增量取证；不能用这句同意补签尚未完成的G1–G6。

**与v2的关系：** v2正文及24组责任、W1–W8、A1–A8、G1–G7继续作为整体审阅基线。本文补充v2 §3.1、§5、§6.3、§7.4、§8.2的比较方法和实际证据：A/B/C是改动幅度，不是完整的实现来源备选；其中C及七类物理组织不能优先于可行外部架构。v2中的“不引入”保留当前未授权采用的边界，不解释成永不评估成熟实现。没有声称本轮改写了v2正文或已经解决其全部缺口。当前版本/下一步仍只从#508最新回执恢复。

## 1. 重构决策同时回答两个问题

第一轴：现状保留、有限整合、结构性调整。第二轴：实现与架构从哪里来。每个重大选择都应比较以下实际可行方式，而不是先画自有目录树再找外部项目背书。

| 实现来源 | 可能减少的自有责任 | 必须说明的剩余成本 |
|---|---|---|
| 现有实现直接保留或配置 | 无新增迁移与外部依赖；可能已经足够 | 当前重复、错误依赖、历史兼容是否值得继续承担 |
| 采用成熟项目的架构模式 | 复用职责划分、组合方式、接口与失败设计 | 实现仍由Kernel维护，不能宣传成已经采用外部执行器 |
| 直接采用成熟库、CLI或子系统 | 把确定的技术责任交给维护中的上游 | 适用合同、安装/升级、许可/安全、可观察行为及退出 |
| 薄适配既有实现 | 用小边界保留Kernel特定语义，同时复用核心能力 | 适配是否真的薄，是否暗中复制一个完整状态/调度系统 |
| 有限fork/patch | 避免因可修复缺口重写全部组件 | 补丁范围、上游合并可能、长期同步和独立维护责任 |
| 有证据支持的自建 | 只承担尚无更低成本可行替代的独特责任 | 已检查的替代、具体阻断、为什么配置/适配不能解决 |

成熟项目不是必须整套搬入；不同语言、独立进程或小型个人项目也不因此失去评估资格。现有方案和外部方案都必须以同一真实消费者、语义与成本口径接受反证。保留现有能力是合法结论，但熟悉、自主可控、已经投入很多或“只差20%”不是充分理由。[PROTOCOL]

**比较顺序：先核不能违反的语义/权限/隐私条件，再比较当前用途的长期净成本。** 不用一个加权总分抵消PIT或权限失败；可改变但尚未获准的约束作为有条件方案另列，不能偷偷移除。按个人现用途核实际许可义务，不加假想商业化门槛，也不把个人使用当许可豁免。没有证据的成本保持UNKNOWN，不填主观百分比。

## 2. 本轮内部增量证据：复用判断所需的真实接点

代码基线M=`4e9da1d037d6cefce0a7735ee74349666430a9bf`。文档前驱H=`43c1284a05ed94b16230cea50252deca06bb355c`。本轮读取#508、#297、AGENTS、现行Reuse First和#804状态；未解析生产R，未运行来源、模型、生产恢复或发布。

| 证据 | 实际看到的依赖/行为 | 对目标设计的影响 |
|---|---|---|
| I1 共享资源预算 | `institutional_radar_reading._reserve`同时依赖`stock_research_reading.call_limit`和`read_blob_reuse.pending_blob_writes`，把已用API调用、待写blob、新文件和固定发布预留一起检查 | 它不只是通用限速器；不能用某库的并行数限制替代。共享资源owner应按实际语义确定，不因目前放在机构Radar就保持该归属。[RESERVE] |
| I2 跨业务消费者 | 对`institutional_radar_reading`的有界代码搜索返回Concept、EasyStock、TDX、News、Global Market、Industry、D和Outcome等明确引用；多处直接借`_reserve`/`ERRORS`或`_run` | 支持审查跨业务共享边界，而非仅提取两个CLI helper；搜索只证明这些正例，不证明所有消费者已列全、所有引用同义或可删除。[CONSUMERS] |
| I3 D可选计算链 | D reader沿原history/calendar adapter规范化，调用CZSC子进程，构造固定文件与descriptor；失败时恢复本轮候选文件，已发生的API调用不能视为撤销 | 任何外部runner须分别表达纯计算、文件候选、已消耗预算与可选失败。函数图可替代部分编排，但不能凭图执行成功替代最终文件资格。[DREAD][DCORE] |
| I4 已有实际外部实现复用 | News workflow调用固定digest的NewsNow容器，经本地端口使用服务，未向该容器传入仓库凭证；CZSC代码直接使用现成算法 | 当前系统已经有“外部进程/库+Kernel边界”的具体实现方式；2.0应审查是否恰当，而不是重新实现它们或假定只有同语言SDK才可复用。这里核的是代码接线，不是本轮生产成功。[NEWS-WF][DCORE] |
| I5 News历史与当次采集分离 | `news_history_recovery.recover`选择有界前驱，保留最近尝试及更晚不可用尝试；损坏后输出RECOVERY_REJECTED，不再换档案。CLI保留缺口但返回0，允许本轮独立新闻采集继续 | “历史不完整”与“当次采集失败”是不同结果；统一成任何异常都终止或吞掉所有错误都不等价。旧历史恢复与外部runner自身重试/缓存必须分开。[NEWS-RECOVERY] |
| I6 真实调用入口已有反例 | `test_news_history_input_edges.py`从capture和CLI输入构造缺失/空/超界历史，检查七个窗口仍被采集、PREDECESSOR_GAP保留；D reader测试保护价格/Research及无凭证worker | 直接复用这些正反例设计确认样本，不新造一套只测外部库能跑的演示；本轮只读测试，未执行。[NEWS-TEST][DTEST] |

I2实际搜索范围为默认分支plain-keyword `institutional_radar_reading`、返回上限20；结果定位均在本M。正例包括`concept_radar_reading.py`、`easy_stock_reading.py`、`d_auction_minute_reading.py`、`d_horizon_follow_up.py`、`operating_outcome_reading.py`、`tdx_concept_reading.py`、`news_daily_reading.py`、`global_market_reading.py`、`industry_breadth_reading.py`、`concept_detail_reading.py`。这是可追溯的局部依赖扇出，不是完整静态/动态调用图，更不是零消费者证明。

八份保留源码（research_commit、live、base/扩展delivery、D core/reader、archive/index）在本地重新计算Git blob，与原精确对象匹配，再用标准库AST读取；没有导入或执行业务代码。这种临时分析不成为自建永久依赖扫描器或CI门禁。全仓源码、动态import、workflow/CLI、资源和人工恢复用途仍需G1/G2补齐。

## 3. 实际外部备选：不是只列项目名称

### 3.1 Kedro：完整项目架构与组件级使用分别比较

本轮读取官方架构总览。它明确区分采用完整project/framework/starter与在已有代码中选择DataCatalog、配置加载器、pipeline/runner。项目结构包括conf、pipelines、settings和registry；库把配置、图描述、执行与I/O拆成各自单元。**因此“采用Kedro必须整体迁入模板或另建常驻调度平台”不是本轮可成立的假设。**[K-ARCH]

实际代码固定为Kedro **1.7.0**、commit `2e4375bd90e0ed09e179563c2ef9e29f4a2eb22f`。读取`sequential_runner.py`全文、`runner.py:40–215`、`tests/runner/test_sequential_runner.py:1–165`和`pyproject.toml:1–130`。这不是全项目源码或全部依赖审计。[K-SEQ][K-RUN][K-TEST][K-PKG]

代码可见：SequentialRunner在本进程按拓扑顺序执行；默认is_async=False；catalog在执行前提供输入并检查缺失输入；可不传plugin manager；执行结果返回dataset对象，调用方需要`.load()`取得值。`only_missing_outputs=False`是默认值，按现存输出跳过节点是另行启用的能力。不能用“文件存在”替代Kernel的时钟、来源、权限与当前资格。

**候选边界：** 比较直接用Pipeline/Node、SequentialRunner与内存catalog，或受限CatalogProtocol适配，在现有获准Actions/进程内消费已验证输入；GitHub原件、状态权威、发布前驱/读回与Human边界仍由明确owner承担。另一候选是更完整采用Kedro的项目组织/配置框架，而不是一开始就将其排除；但其实际改动和兼容范围需与组件级方案分开估算。

**可能收益：** 不再自建图执行、节点输入输出关系及通用I/O编排；复用明确的项目/库分离方式。**真实代价：** 需要改变哪些现有函数和调用者、dataset/metadata怎样绑定、失败是否仍原样可见、配置与插件入口是否增加负担，均需实证。项目元数据声明了包括cookiecutter、OmegaConf、fsspec、GitPython、pluggy、kedro-telemetry等依赖；server依赖单列可选。依赖存在不是该候选一定外发数据的证明，但试验前须核遥测/插件加载控制及许可和最小环境；当前未安装。[K-PKG]

阶段结论：**THIN_ADAPTER候选；完整项目采用保留对照；未试验、未定胜负。** 没有因不完全等同Kernel或属于框架而拒绝，也没有因成熟而直接采纳。若边界适配接近复制当前Collector全部责任、又不能退出旧实现，组件采用不具净收益；若实际减少自有编排且保护成本合理，应优先复用。

### 3.2 Apache Hamilton：纯函数数据流与默认内存执行

本轮按GitHub返回的release精确定位：tag **`apache-hamilton-v1.90.0-incubating-RC0`**，commit **`bed5a272904bd7d68bc03167978f663e1906738c`**。标签含RC0而release元数据prerelease=false，两者原样保留，不据此保证发行成熟度。读取`hamilton/driver.py:1–240`、`pyproject.toml:1–150`、实际目录定位后的`tests/test_hamilton_driver.py:1–185`，并参考官方Driver合同。[H-DRIVER][H-PKG][H-TEST][H-DOC]

代码可见：DefaultGraphExecutor用内存dict保存本次计算，按请求的最终变量返回值；任务分组/动态执行是另一执行器。缓存、UI、外部执行等能力不能混称默认必需。当前发行包名称为`apache-hamilton`，不是从旧教程推断的包名；核心依赖声明包含numpy、pandas和类型工具，Driver本身导入pandas。[H-DRIVER][H-PKG]

**候选边界：** 对已验证输入后的纯观察转换，比较函数图/Driver取代部分手写连接；在边界输出原格式而不重新定义Research、概率或状态权威。它不是文件/来源安全沙箱，任意节点仍可能含副作用；必须核实际纳入的函数和禁网/无凭证边界，而不是依赖框架名称。

**可能收益：** 函数依赖和所需输出更显式，减少自有执行关系维护。**真实代价：** 现有函数参数和全局状态是否需要大量包装、名称成为依赖合同后的重命名成本、导入numpy/pandas对轻环境的影响、错误传播及结果字节是否相同，均未测。已读测试同时含`.has_cycles()`检查与执行循环时期待RecursionError的例子，不能宣称所有非法图都在运行前安全拒绝。[H-TEST]

阶段结论：**纯转换域的THIN_ADAPTER候选，暂不把整个producer/恢复/发布改成函数图；不是永久拒绝扩展采用。** 对含外部效果的路线，需要证明它实际减少责任且不继承未经授权的重试/缓存；缺口未清时不新建自己的等价DAG引擎，也不先安装Hamilton。

### 3.3 P2架构模式直接消费，但不冒称实现已经替换

复用P2实际审阅的OpenTelemetry Collector组件生命周期/可选失败边界、LEAN组合根与data/result handler分离、Airflow受支持接口出口、dbt声明与运行结果分开。它们分别用于审查共享资源owner、纯计算与I/O依赖、公共接口与历史格式，而不是用来论证必须保留原拓扑。[P2]

模式级借鉴与采用外部运行实现是不同备选。即使决定不运行整套OTel/LEAN，也仍应比较其内聚组件组织与v2分层组织；不能仅提炼一句原则后假定内部结构最优。使用外部实现时也无须继承交易handler、研究接受规则或新的状态后端。

本轮Dagster仅取得官方执行API页面作为后续候选定位，未取得足够源代码/依赖/测试证据，不作优劣判定；不以此宣布没有其他可复用方案。此次新检索以Kedro/Hamilton的可嵌入架构与执行能力为主，未覆盖全部工程领域的所有外部备选。

## 4. 同一需求下的当前比较结论

| 方案 | 架构与实现接管范围 | 对Kernel需保留的边界 | 本轮裁定与下一验证 |
|---|---|---|---|
| 现有显式函数/Collector链 | 不新增引擎，保留已用库和原生GitHub | 现有预算、状态、失败、原件和发布规则全部保留 | KEEP作为基线；不是全面架构最终结论；测跨业务依赖和T3改动传播 |
| 复用OTel/LEAN等组织模式，调整内部归属 | 结构模式复用，自有实现仍需维护 | 精确序列化与当前业务资格不变 | ADAPT模式候选；不能当成运行库复用或自建引擎合理性的证明 |
| 采用Kedro选定组件 | 通用pipeline/runner/catalog实现可能退出自有维护 | 来源/原件/预算/最终发布仍显式；默认关闭基于现存输出的跳过 | THIN_ADAPTER候选；先核适配规模、插件/遥测、内存与字节合同 |
| 更完整采用Kedro项目组织 | settings/conf/registry/session等可能接管更多工程结构 | 原用途索引不能变成第二真源；历史定位/Human/权限不丢 | 保留结构性对照；未审完整配置/插件/迁移范围，不提前签REPLACE |
| 采用Hamilton纯函数执行 | 纯转换的图与执行关系可能由上游维护 | 执行授权、来源校验、失败记忆和发布不从图推断 | THIN_ADAPTER候选；核函数重接、循环/异常、轻环境与可退出接口 |

**目前没有证据支持宣布某个外部方案全面胜出，也没有证据支持跳过它们而自建通用执行/状态平台。** 已有被证明有用的NewsNow/CZSC等实现继续作为复用基线接受审查，不把重构等同于替换所有外部组件。本轮的实质结论是：外部组件级采用确实有可检查入口，应与内部结构调整竞争；C方案尚未因七类目录写得更完整而获准。

## 5. 对全局处置矩阵的直接回写含义

这张表是v2矩阵的证据增补，不是覆盖全部24行的新矩阵。各行最终处置仍须G1–G6证据和适用采纳。

| v2行/批次 | 原建议需要增加的比较 | 当前可据证推进 / 尚未证明 |
|---|---|---|
| M04/M06/M08，W3 | 自有用例/工作流收敛，对比Kedro组件执行、完整项目组织及原生Actions边界 | 已有真实嵌入式runner入口；尚无所有producer/触发/配置转换表 |
| M07，W4 | 自有observations分组，对比Hamilton函数图及现有纯函数直接调用 | D纯计算边界和上游executor已读；全族算法与函数适配代价未知 |
| M09/M10，W3 | 各状态权威/失败owner，对比外部runner结果、生命周期及恢复语义 | News恢复失败不阻止当前采集的反例已核；其他producer恢复不能由News推广 |
| M13/M14/M15，W2/W6 | current_state通用能力与跨业务预算归属，对比组件资源接口/库式catalog，而非再建万能Collector | 多族真实引用已发现；全消费者清单、共享预算的最小合同和并发语义尚未闭合 |
| M19/M21，W7 | 采用外部实现减少哪些自有证明，同时新增哪些环境/适配/升级义务 | 已读Kedro/Hamilton元数据和局部测试；无新增安装、性能或依赖兼容试验 |
| 其余M行 | 继续沿其实际问题比较内部与外部方案，不用本组研究签收 | P2适用证据继续使用；未审字段保持原UNKNOWN，不隐藏为DEFER |

## 6. 下一比较的统一样本与通过条件

沿v2已有T1–T7，不新建基准系统。本组先固定T3（增加既有保存输入的读面用途）与T5（恢复/发布效果未知）的以下保护口径，作为待执行的比较说明，不是已经运行的benchmark。

| 样本 | 各候选必须处理的同一情形 | 证据与失败条件 |
|---|---|---|
| T3-成功 | 相同保存源/时钟、现有规范化与CZSC结果进入同一读包用途 | 原文件字节、元数据和资格逐项对应；计算方法变化须另立语义差异，不能借框架迁移隐藏 |
| T3-可选失败 | 已用预算不撤销，D失败仍保留原价格/Research；不足容量不能只写一半候选 | 复用D测试的真实reader接线；不能只证明纯节点单测成功 |
| T3-历史缺口 | News前驱缺失/超界/坏格式，本轮独立采集可继续但PREDECESSOR_GAP必须保留 | 复用已有capture/CLI反例；既不抹掉失败，也不使无关来源被统一阻塞 |
| T5-未知写结果 | 外部效果可能成功但响应丢失；先读原locator判断实际结果 | 不自动重试、force或重复发布；外部引擎resume/cache不可自行产生执行权限 |
| T5-坏原件/错误用途 | hash、ref、source身份或预算不符合已选用途 | 拒绝相应操作并保留失败；不以缓存存在、catalog.exists或成功run标签替代资格 |
| 成本与退出 | 完成上述同一用途并做一次后继修改 | 比较修改责任点、适配函数/配置、重复实现、兼容分支、安装/测试/维护与退出步骤；不能只数代码行 |

先从完整源码与已有证据确定最小适配差异，再按原权限边界提出必要的隔离试验；外部库尚未获准安装时只提交可执行的试验设计，不自动执行。将纯模块包装成巨大万能节点虽然能让库运行，但若原复杂性全部留在节点内，不算架构改善。反过来，为展示框架优点而拆成大量无消费者小节点也不算降低成本。

结果分开记录CODE_READ、CONTRACT_READ、DESIGN_ESTIMATE、TRIAL_NOT_RUN和实际MEASURED。没有实测的成本保持UNKNOWN；本轮未评定T3/T5完成，也未签G6。

## 7. 贯穿P3、P4、P5的使用规则

P3在作重大归属/接口/实现决定前完成同口径比较，原矩阵记录外部接管和Kernel剩余责任；P4每批引用仍适用的决定，出现重要新能力/成本/许可/语义变化才补局部检索，不逐文件重做P2；P5核旧责任实际退出及新增适配/fork/升级负担是否抵消收益。没有新代码通常也是有效KEEP结论。

同一套现有ADR/设计、#508回执和实施PR保存比较依据，不建复用评分引擎、候选数量配额、常驻审计、第二registry或平行进度。普通已授权设计工作不逐文件索批；具体生产改变、新依赖/费用/来源/权限及重要语义仍按原边界处理。

## 8. 实际范围、局部失败与后继证据

本轮只读外部代码、合同、元数据及所列内部源码/测试；本地仅原文件hash/AST静态检查。没有安装Kedro/Hamilton/Import Linter，没有运行上游或Kernel业务测试，没有执行source/model/生产任务，没有读生产R。不能从本附录或文档CI推断真实采集/发布成功。

公开archive本地下载因DNS失败未取得完整checkout；原生GitHub连接读取成功。一次误用repo/search路径被参数校验拒绝，随后正确代码搜索成功；Hamilton旧猜测test_driver.py为404，通过实际目录定位到test_hamilton_driver.py；Kedro猜测文档地址不可读后沿官方导航恢复。以上是取回/定位差异，不是项目能力不存在或绕过权限拒绝。保留具体读取范围，不用失败搜索证明NEW_BUILD_JUSTIFIED。

G1/G2仅有本文列明的增量正例，尚未全域闭合；G3–G6及真正独立接手仍按整体设计继续。当前工作是把真实消费者/状态owner及同口径外部替代补齐，再形成精确架构采纳包，而不是默认启用旧S1或安装某框架。C/D原自然窗、其他owner、Sites暂停、分钟STOP、新城暂缓及AI Investment Authority=NONE保持。

## 来源

仓库源码固定M；外部源码固定所列commit。滚动官方文档只支持本轮读取到的合同，不代替固定发行代码或实际采用。源码许可头/项目元数据的读取不等于所有依赖许可审计；未复制第三方实现。

[OWNER]: https://github.com/auguspp/decision-kernel/issues/508
[PLAN12]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6096068040
[PLAN11]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6095772144
[DESIGN]: https://github.com/auguspp/decision-kernel/blob/43c1284a05ed94b16230cea50252deca06bb355c/docs/kernel-2.0-design.md
[PROTOCOL]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/WORKING-PROTOCOLS.md#reuse-first--required-external-prior-art-check
[P2]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/docs/kernel-2.0-prior-art.md
[RESERVE]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/institutional_radar_reading.py#L1-L60
[CONSUMERS]: https://github.com/auguspp/decision-kernel/tree/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime
[DREAD]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/d_price_structure_reading.py
[DCORE]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/d_price_structure.py
[DTEST]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/tests/test_d_price_structure_reading.py
[NEWS-WF]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/radar-newsnow-daily.yml
[NEWS-RECOVERY]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/news_history_recovery.py
[NEWS-TEST]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/tests/test_news_history_input_edges.py
[K-ARCH]: https://docs.kedro.org/en/stable/getting-started/architecture_overview/
[K-SEQ]: https://github.com/kedro-org/kedro/blob/2e4375bd90e0ed09e179563c2ef9e29f4a2eb22f/kedro/runner/sequential_runner.py
[K-RUN]: https://github.com/kedro-org/kedro/blob/2e4375bd90e0ed09e179563c2ef9e29f4a2eb22f/kedro/runner/runner.py#L40-L215
[K-TEST]: https://github.com/kedro-org/kedro/blob/2e4375bd90e0ed09e179563c2ef9e29f4a2eb22f/tests/runner/test_sequential_runner.py#L1-L165
[K-PKG]: https://github.com/kedro-org/kedro/blob/2e4375bd90e0ed09e179563c2ef9e29f4a2eb22f/pyproject.toml#L1-L130
[H-DRIVER]: https://github.com/apache/hamilton/blob/bed5a272904bd7d68bc03167978f663e1906738c/hamilton/driver.py#L1-L240
[H-PKG]: https://github.com/apache/hamilton/blob/bed5a272904bd7d68bc03167978f663e1906738c/pyproject.toml#L1-L150
[H-TEST]: https://github.com/apache/hamilton/blob/bed5a272904bd7d68bc03167978f663e1906738c/tests/test_hamilton_driver.py#L1-L185
[H-DOC]: https://hamilton.apache.org/reference/drivers/Driver/
