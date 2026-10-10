# Kernel 2.0 — 全局目标架构与渐进重构方案 v2.1

日期：2026-10-10（Asia/Singapore）。设计 ID：`K2-DESIGN-20261010-v2.1`。唯一计划与跨会话接续入口：[#508][OWNER]。有效计划为[v1.2 架构级 Reuse First][PLAN12]、[v1.1 全面目标纠偏][PLAN11]和[v1.0][PLAN10]未被替代条款。

**状态：P3 GLOBAL DESIGN PROPOSAL / 待审。** Human已同意继续全面规划与架构复用比较；本稿不是全仓审计完成、具体架构采纳、依赖安装或P4施工授权。保存、CI、合并、采纳、实施、生产与产品验收分别成立。实时进度只在#508最新回执，不在本文另设进度表。

**版本关系：** 本稿整合[原v2][V2]与[架构复用证据附录v1][REUSE]的设计影响，继续在同一PR #804、同一路径评审，不增加第三份设计队列。原v2与附录的精确版本、来源和未运行声明保留；附录是证据输入，不与本文竞争当前目标。原[v1/#803][OLD]作为历史候选保留，其“原拓扑为主”和默认S1→S4已不再是当前推荐。P1/#801、P2/#802交付事实不撤销、不重做，其有界KEEP不构成全域免审。

## 1. 目标、差距与本版变化

Kernel 2.0是覆盖整个工程体系的架构审查、必要的目标重新设计与渐进式全面重构。全面指审查和决策范围，不要求所有代码重写；渐进指施工方式，不允许最后只交付几个局部修补。成功必须表现为整体维护、扩展、验证、恢复和接手成本下降，同时保护经过证明有价值的领域语义、研究成果与Human权限。[PLAN11]

| 原P3偏差 | 校准后的要求 | 继续保留的成果 |
|---|---|---|
| 四个可施工问题替代全局目标 | 所有重要工程域进入同一处置矩阵，迁移从目标责任和消费者推导 | S1–S4作为可重排、拆分、替换的候选 |
| 把保护领域语义等同于保留原拓扑 | 同台比较保持现状、有限整合、结构调整和外部架构采用 | 原PIT、身份、数值、权限与有效历史 |
| placement主要复述旧位置 | 明确目标边界、依赖、公共接口、状态归属、运行与恢复 | 旧路径作为迁移输入，不作为当然终点 |
| 局部血缘和CI绿灯代替整体证明 | 覆盖不同来源与产品链族；同口径比较未来变更成本 | 原工程、原件、发布证据不被抹去 |
| 只借外部原则，没有充分比较实际采用 | 在重大决定前检查可用组件、CLI、子系统、配置、薄适配与有限fork | P2仍适用的固定版本研究直接消费 |

固定边界：GitHub仍为正式代码/证据/状态后端；PIT、UNKNOWN、Evidence/Research/Odds/Human区分；历史和原话保留；AI Investment Authority=NONE。开放事项：代码拓扑、实现归属、内部接口、配置位置、读包与运行状态表示、兼容维护方式、测试组织、CI具体实现和依赖管理。现役规则在替代方案获准并完成适用验证前不变。

本版新增的不是更多施工承诺，而是六项有代码依据的设计约束：区分事件机会与合格数据依赖；识别#581的报告记忆；保留已有有界恢复而非统一重试策略；揭示工作流文本的配置消费者；把旧执行入口与现役共享实现分开；明确外部数据集复制与共享预算的适配问题。它们具体影响M04/M06/M08–M15/M19/M21/M23及W2/W3/W5/W6/W7/W8，详见下文。

## 2. 证据基线与实际覆盖

代码M=`4e9da1d037d6cefce0a7735ee74349666430a9bf`；本次文档编辑前的PR头H=`9d94d0e0f01cd32b1c9895d2297a8c2d61a2526a`。已重新恢复AGENTS、NEXT、#297、#508及07回执，核#804仍开放且仅两份工程文档在途。未读取生产R，未调用source/model/producer/publisher或安装候选依赖。

P1的责任/对象/成本样本、P2的十二类工程先例和复用附录的内部接点/外部候选直接复用。保留的结论只在原读取范围内有效；不能将树存在、搜索命中、旧文档或成功run标签当成全源码已审、现役性或零消费者证明。[P1][P2][REUSE]

### 2.1 本次增量读取与静态核对

| 输入 | 实际读取范围 | 本地核对对象 |
|---|---|---|
| `.github/`树 | M下72项元数据，返回未截断；包括工作流、脚本与输入 | 元数据用于覆盖导航，不代表全部正文已审 |
| `stock-reading-after-sector.yml` | 全文476行，五个job及事件/权限/命令/产物 | blob `8d5686c541665653d5c881c23e2a65388d9367f5` |
| `decision-inbox.yml` | 全文273行，输入数组、Watch、shadow和可选disclosures | blob `d97ea5aa1a6b4c8d074119a809648c41d2df46d6` |
| `stock-business-research.yml` | 全文379行，issues/dispatch、来源准备、方法调用与兼容探针 | blob `97eba671083b114fc7b5d4664f28a80fbc9f2360` |
| `saved-disclosure-research.yml` | 全文100行，三类触发及原生请求/保管接线 | blob `eb5da06270ffb20b37cb749db6f6e481241fa44d` |
| `sector_radar_persistence.py` | 全文892行，解析、关系校验、写入、bootstrap和恢复选择 | blob `d21b965e91e57c3c0b9e0de59754fce57da65ad3` |
| `reconcile-radar-delivery.py` | 全文395行，choose/collect/dispatch/retain_unresolved/report | blob `3198a1cb20f38fb534ed044aa3d6e7a4cd8aabfd` |
| `saved_research_once.py` | 全文566行，共享Retainer、模型请求/返回保管和方法执行 | blob `4819ec4cf257881c41f0752fa8420643694d7fb6` |
| Kedro `memory_dataset.py` | 固定候选版本全文153行 | blob `f4482e75addb0fe9393cf5d80f1f16efbfe76d5c` |

以上八份正文重新计算Git blob相符；Python只做标准库AST解析，YAML使用BaseLoader保留`on`键。未导入或执行这些源码。另读Sector workflow的生产/恢复/保管主要区间、`stock_research_intake.py:1–130`、`incremental_disclosure_intake.py:1–150`及Kedro内存数据集测试前190行。复核已保留base/扩展Collector、D reader/算法/测试、档案/索引及Workbench读取接口。`WORK_REF`等有界搜索只提供正例，未穷尽全仓引用。[SECTOR-WF][STOCK-INTAKE][DISC-INTAKE][K-MEM-TEST]

本地公开archive请求因DNS失败未得到完整checkout；连接器和MCP读取成功。这限制全仓自动扫描结论，不证明GitHub无权限，也不能成为自建工具或代理工作流的理由。没有把局部静态分析变成永久扫描器、CI门禁或新的执行平台。

### 2.2 当前代码能证明的主链，及其不能证明的运行事实

| 责任链 | 输入与执行接点 | 原件/状态/直接消费者 | 对设计的约束 |
|---|---|---|---|
| Sector生产与恢复 | 原dispatch的produce或具名历史恢复operation；producer及原恢复脚本 | run audit、state bundle、同字节cache；Sector自身和保存结果reader | 运行恢复须合格state，不从综合R取得权限；历史operation未因此获准再次执行 |
| 日常股票输入 | 原cron/manual或Sector完成事件；`stock-market-input-gate.py`→`stock_market_inputs` | dated source/skip artifact；现役股票/D读面 | 此分支不要求Sector成功或成员资格；日期去重与来源资格仍独立 |
| TDX接续 | Sector成功后核origin、result-bearing、新完成session和current main | 一次既有TDX dispatch；TDX自行核main CI、源日期、回放与保管 | 不能因收到完成事件就放行；Sector NOOP/恢复不等价于新输入 |
| 有界交付对账 | reconciler读取原run、artifact、活动工作和已上传intent | intent/report artifact；#581报告记忆；显式限定Sector/Stock后继 | 已知未发出、接受待结果、效果未知分开；不得自动重复未知dispatch |
| Inbox/Watch与可选公告 | workflow中的不同输入数组；Attention/Watch和独立disclosures job | HTML/Markdown、typed Watch、shadow、scan/PDF artifact；base与Watch reader | 研究请求、日常包、shadow和扫描对象不是一套“公司清单”；兄弟job失败不抹去已验证交付 |
| 已保存公告研究 | 显式request-only push/manual；另有要求旧scheduled Inbox的历史workflow_run分支 | intake packet与`research-work/disclosures-v0`；原host/admission/reader | reservation不是研究完成；当前不可达的自动边要单独处置，不能扩大成自动研究 |
| 股票/问题研究及资料准备 | `stock-business-research.yml`的issues/manual目的；相应host调用共享Retainer/执行器 | `research-work/stock-business-v0`及run-output；research reading/历史恢复 | 来源准备、兼容探针、模型执行、技术续作有不同权限；不能依据work文件存在启动下一阶段 |
| 综合阅读与派生发布 | base Collector＋显式扩展顺序→候选文件→原publish | `read-model/current-state`；Workbench、研究接续与归档reader | API消耗、候选文件、旧合格结果、最近失败不同；News快缓存/Issue观察不能假装同R |

本表是源码接线证据，不是本轮重新验证这些生产链成功、任务已启用或每日完整交付。News、D和Research领域链的原局部证据继续沿P1/P2/附录使用，未在本轮重新采集。

### 2.3 六项具体结构发现与处置

**E21：事件、数据、权限是三种边。** `stock-reading-after-sector`同一workflow包含五个job。daily-market-inputs接收Sector完成而不要求结论success；TDX接续则要求success及具体result资格。reconcile-deliveries还可能在已批准范围内发起有限后继；竞价两个目的另有手工入口。建议W3按用例拆清owner/接口，可复用原生steps或外部执行组件，但不能把全部转换成“上游成功才运行”的单一DAG。不因文件名含reading而把整个workflow认定只读。[STOCK-WF]

**E22：存在可精确定位的历史自动边。** 当前`decision-inbox`只声明workflow_dispatch；`saved-disclosure-research`的workflow_run job却要求其上游event=schedule。因此当前M下新发起的原生Inbox不能满足这条旧自动分支。该事实支持G4核查这一条边是否已失去执行责任，不证明整个公告研究workflow无消费者：它仍有manual和request-only push。更不能把条件改为接受manual Inbox从而新增自动研究。旧scheduled run及必要reader保留，删除或改接先核原owner/历史意图。[INBOX-WF][DISC-WF]

**E23：#581不只是可以丢弃的展示缓存。** `report_issue()`读取Issue正文中`radar-continuity-status-v1`的原JSON，调用`retain_unresolved()`后写回。原未交付身份按lane/target保留，非同一目标的后来成功不能清除它。它实际承担报告连续性记忆；迁移必须保留或证明可从原件完整重建。它仍不是dispatch准入权威，也不是Human判断数据库，不能由报告字段授予重试权限。原v2对“机器健康投影”的宽泛理解应据此收紧。[RECONCILE]

**E24：必要恢复不能被统一成零重试或默认重试。** reconciler已有最多3次每周期source attempt、活动检查、精确诊断类别、冷却、main CI、旧intent核对等有限规则。未知dispatch保持UNRECONCILED/DISPATCH_UNCERTAIN；明确定义的未发出与已接受待结果分别记录。模型调用和create-only写入又有自己的不重试边界。W3应保留已有获准语义，通用库的retry/resume不能替代；本稿也不扩大原有限source recovery。[RECONCILE][ONCE]

**E25：工作流文本还是配置接口。** base `Collector.research()`读取同M的Inbox workflow，从具名literal arrays提取decision_packages和research_attention_handoffs。当前两组为空，而shadow和显式公告扫描另有六公司样本；重复证券不等于同一生产意图。把数组搬进新配置/catalog需要同时迁移writer、reader、测试和旧版本解释；不能只改YAML再认为reader仍正确。用途registry不能变成新授权清单。[INBOX-WF][BASE]

**E26：旧名称不等于无用实现。** `saved_research_once.py`已退出Suken固定launcher，`__main__`明确拒绝运行，但现役hosts复用其Retainer和模型循环。按once/旧日期删整个文件会误退共享责任。应分别审查保管机械步骤、模型适配、方法选择和历史codec的归属；旧执行责任已退不重做，仍有消费者的实现允许CONSOLIDATE，不因复杂就继续全体KEEP。[ONCE][STOCK-INTAKE][STOCK-RESEARCH-WF]

## 3. 架构备选与架构级复用

### 3.1 两个独立比较轴

A/B/C回答改动幅度；实现从哪里来是另一个轴。每项重大选择都以同一真实消费者和约束比较，不能先决定自建目标树再找外部项目背书。[PLAN12][PROTOCOL]

| 改动方案 | 可能收益 | 必须承担的代价/可推翻条件 |
|---|---|---|
| A 维持现状、修具体问题 | 最少迁移；已有内聚能力可能已足够 | 仍要审当前重复、错误依赖、配置与历史责任；运行正常不是结构最佳证明 |
| B 有限整合 | 收敛重复技术实现与局部职责，兼容面较小 | 不能预设为全仓上限；若主干耦合仍在，应考虑C |
| C 同仓模块化结构调整 | 调整领域、方法、用例、I/O、产品与历史合同归属，降低跨用途变化传播 | 必须有消费者/状态/历史支持；只增加转发层、配置或维护负担的拆分应撤回 |

每种幅度同时比较：现有实现直接保留/配置；采用外部组织模式；直接使用成熟库、CLI或子系统；薄适配；有范围的fork/patch；确有证据才自建。先核不可违反的语义/权限/隐私，再比现用途长期净成本，不用加权总分抵消资格失败。不同语言、小型个人项目、独立进程、非100%贴合均不是自动排除理由。按实际个人用途核许可、外发、安装/升级和退出，既不加假想商业化负担，也不把个人使用当许可豁免。

**当前推荐仍是可推翻的组合候选：按责任作必要结构调整，逐域决定内部实现或外部采用。** 不是先批准自有七层，再允许外部库填缝；Kedro更完整项目组织等也可以参与总体结构比较。没有实证前不宣布某个框架全面胜出，不为“全面”新增微服务、数据库、调度平台或第二状态后端。需要改变现有约束的方案可以分析为有条件备选，实际改变仍须相应采纳。

### 3.2 目标责任与依赖方向

| 目标责任 | 所有的能力/接口 | 禁止的职责渗透 |
|---|---|---|
| domain | 身份/PIT、Evidence、Research、Market、Odds、估值与必要确定性计算 | 不依赖网络、GitHub、工作流、UI或具体研究方法 |
| methods | 可替换研究方法、输入/输出解释与版本；旧方法历史codec另辨 | 方法不取得Human接受或投资权限；不能要求所有研究者走旧Funnel |
| observations | Sector/Stock/News/Industry/economic/D等纯观察转换与输入计算族 | 不为了拿check/hash/预算反向导入宽publisher；解释不假装经济真值 |
| application | capture、研究交付、reading、恢复等具体用例；显式输入/结果/可选失败 | 不直接从具体HTTP模块拿全局凭证，不把事件机会当授权 |
| contracts | 实际跨边界数据和错误合同，按对象族归属 | 不建万能source/state对象；内部领域值和Git存储细节不全部公共化 |
| infrastructure | GitHub/HTTP/文件/格式读写与必要技术资源 | 实现调用但不决定Research接受、PIT补签或恢复权限 |
| interfaces / composition | CLI、host及产品读写入口，显式连接具体实现 | browser不持有写token；展示/请求/接受/执行分开 |

这描述责任而非强制层数。领域内部值留领域；infrastructure实现相关边界；组合根可以同时知道application和具体I/O。测试可组合各层，业务不依赖tests。不为每函数建Interface/Factory，不把各业务族复制成七套空目录。

物理候选为`src/decision_kernel/{domain,methods,observations,application,contracts,infrastructure,interfaces}`和原`workbench/`。仍须与外部成熟项目的组织方式、局部保持现状比较；没有本轮目录创建或移动清单。现有内聚模块可整体移入而不重写算法；`research.py`不能被同名新package静默遮蔽。安装后CLI、资源JSON、导入解析、旧序列化和实际消费者都要验证。历史资料按原commit/path/blob恢复，不为代码整理批量搬原件。[V2][P2]

### 3.3 外部实现的具体候选与尚未替代的责任

| 候选 | 已核可用边界 | 实际替代前必须回答 |
|---|---|---|
| 现有原生GitHub与显式函数链 | 当前触发、并发、artifact、Git对象、pytest等已有实现 | 哪些重复责任可退出，哪些显式性比新引擎更便宜；不是当然永久KEEP |
| OTel/LEAN/Airflow/dbt等组织模式 | P2固定版本的生命周期、handler/组合根、公共出口、声明与结果分离 | 只借模式不等于已采用运行实现，更不证明自建执行器合理 |
| Kedro选定组件 | 已读Pipeline/SequentialRunner/catalog可在已有进程内接入的合同与实现 | 数据与资源身份、失败范围、最小适配、插件/遥测、环境和字节恢复代价 |
| 更完整Kedro项目组织 | 架构文档允许project/framework与组件级方案分别使用 | conf/settings/registry/session能否实际减少维护，是否产生第二配置权威；完整迁移成本仍UNKNOWN |
| Apache Hamilton纯转换 | 已读默认内存执行器、局部tests与依赖；请求最终变量、可不采用动态执行/UI | 函数/名称合同、异常/循环、轻环境、包装规模及旧实现真正退出 |

Kedro固定`2e4375bd90e0ed09e179563c2ef9e29f4a2eb22f`；Hamilton固定`bed5a272904bd7d68bc03167978f663e1906738c`。此前具体阅读区间、版本标签差异和许可/依赖边界保留在附录。本轮不以README或发行标签作生产采用证明。未安装/运行两候选；没有测得节省比例。Dagster此前仅文档定位，证据不足，不作优劣判定。适用P2直接使用，新能力仍做有界新检索，候选集不是封闭白名单。[REUSE]

**本轮新增：Kedro的数据复制合同必须纳入适配。** 固定版本MemoryDataset的load/save采用显式copy_mode或按类型推断；普通对象通常deepcopy，亦可配置assign保留同一引用。已读对应测试的同对象/浅拷贝/深拷贝反例，未执行。因此将带凭证、API已用次数、memo和候选文件的Collector当普通dataset传递，可能复制资源计数或产生错误共享；这是代码支持的集成风险，不是已复现的Kernel故障。assign是可比较的解决方式，不能凭此直接否决Kedro，也不能未经测试认定assign安全。[K-MEM][K-MEM-TEST][K-MEM-DOC]

建议优先比较“已验证普通数据/字节＋纯计算”进入外部组件，resource budget、不可重复效果和最终发布留给明确owner；或通过显式共享资源适配而不复制live client。若适配仍把整个Collector藏进万能节点、原复杂度一项未退，只增加外层图，不算复用收益。反过来，不为展示图而制造大量无消费者小节点。

## 4. 公共接口、数据与状态权威

### 4.1 六组公共合同

| 合同 | 输入/结果及必要约束 |
|---|---|
| 研究交付 | 方法无关包、精确Evidence及独立方法版本→原commit资格/信息身份；COMMITTED不等于Full质量、Human接受或当前Odds可用 |
| 来源采集 | 显式获准请求、provider/channel/资产/期间/参数→原字节、捕获时钟、真实错误；不静默fallback/补采/填0 |
| 保存结果读取 | 精确run/attempt或Git定位及用途→验证过的字节/资格/缺口；不触发producer、研究或新行情，不提升缓存权威 |
| 生产恢复 | producer、合格状态、精确前驱和授权→限定恢复或拒绝；不从综合R/历史报告推导续跑权限 |
| 派生发布 | 代码/输入绑定的候选文件及预期前驱→候选读回、指定ref更新；并发不force，未知写先对账 |
| 产品请求与Human决定 | 只读展示、显式请求、原接受/决定分别保管；服务端限定授权写入，不把点击或模型建议当接受/Watch/交易 |

实际Python签名以真实消费者为准，尽量沿现有受支持接口，不凭本表给所有内部import永久兼容承诺。历史格式、公共行为和内部路径不同；旧转发层有使用者清单和退出证据，不能永续双轨。

### 4.2 对象存放、写入与恢复

| 对象 | 当前已核/目标owner | 保管和迁移边界 |
|---|---|---|
| 代码/工程协议/研究方法 | 原main PR及各自语义owner | 固定M；软件、schema、算法、研究方法版本独立，不统一改2 |
| 生产配置/意图 | 用途唯一显式声明；包括被reader消费的workflow数组 | 迁移同时核写入和读取；不能因内容有相同证券就合并不同集合 |
| 来源原件与提取表示 | 原capture/保管操作及其权利/隐私范围 | 精确字节与表示转换分开；文本不是PDF原件，不自动全部永久公开 |
| 研究工作reservation/阶段结果 | 原`research-work/disclosures-v0`与`research-work/stock-business-v0`等原host/Retainer | create-only、精确前驱/用途、读回；已占用、已执行和已接受不同；不由一个新catalog替代 |
| Research档案/进度/提交/Odds | 原研究交付与历史reader | 后继追加，保留旧字节/哈希/解释；恢复不重新研究，不继承旧接受 |
| Human决定 | 原Human授权路径/Issue | 原话、对象和时点；不放工程ADR、不由重构推断新判断 |
| Sector生产状态 | 当前最新成功合格state artifact；cache只同字节加速 | 90日原策略；缺失/过期/损坏/冲突停普通恢复，bootstrap仅首次；改变长期保管另作G3决定 |
| News历史输入 | 原News合格前驱和recovery回执 | 历史失败可以保留缺口且不阻止独立当次采集；不能套用Sector强依赖，也不能消除前驱缺口 |
| 有界后继intent/结果 | 原Actions run/attempt与先于dispatch上传的intent/report | 已知未发送、已接受待结果、效果未知分开；未发现child不是肯定未发送 |
| 未解决交付的报告记忆 | 原#581正文机器段由reconciler读改写 | 是报告连续性状态，不是授权；迁移/重建须保留lane/target身份及未交付历史 |
| 综合R/News派生缓存 | 各自原publish owner | 综合固定快照、News独立低频/高频用途；独立Issue观察另有时钟，不拼成一包 |
| fixture/evaluation | 原测试/研究评价owner | 合成、真实历史、业务原件区分；退出执行器不当然退出历史读取验证 |
| 工程设计/进度 | 本文件、原证据附录、#508计划/回执、#297路由 | 只有#508持有当前进度；不再建registry、数据库或另一审批看板 |

同一GitHub后端不意味着对象同义；每个逻辑对象有清楚写入owner，原生前驱/条件写控制并发，不假设物理上只能一个进程。[P1][REUSE][PERSIST][RECONCILE][ONCE]

### 4.3 三类恢复与分层失败

档案恢复：只读原字节、原用途和原合同，不执行其中代码或指令。运行恢复：按各producer自己的合格checkpoint/前驱与授权继续；Sector严格state依赖、News可选history不是同一策略。发布恢复：核原候选/指针是否已成功再决定动作，不因丢响应重复写。三者不能由一个默认resume串联。

短生命周期用例按实际需要完成意图/资格、获准I/O、验证/计算、留存失败/结果、读回和显式发布。共享机械实现不意味着共享一套总状态机。必要的source有限恢复、模型不重试、Git效果未知先对账分别守原合同。可选reader失败保全基础结果，已花API调用不可随候选files回滚；失败说明自身也须满足根/总容量。

最新尝试、最后合格结果、来源日/窗口、观察/检查/生成时钟分别保留；旧合格值可与新失败并列，不把“失败保全”说成当前成功。外部引擎返回成功、dataset.exists、cache命中或函数输出非空不建立来源/PIT/恢复/接受资格。

### 4.4 血缘与历史兼容范围

验收覆盖链族，而非只一个指数：Research/Evidence→commit→各Odds；行情/日历/复权→股票/成员比较；Sector状态/事件→原件→reader；行业/财务/公司行动→解释输入；News→滚动history/快缓存→产品；档案/进度→重入；D期限/结构/Outcome；Human决定→产品/Watch。每族覆盖代表成功与关键拒绝，机制差异另列，不以一条通过签全域。

核provider/channel、逻辑资产与供应商代码、窗口/币种/单位/复权、来源修订、可得/捕获时钟、算法/方法/schema、原字节及最终数值。哈希不是经济正确证明；多来源可用但必须显式对账，不能仅同ticker混用。未知历史可得性保留UNKNOWN，明确限制哪个结论。

中文档案仍比较现有同blob映射、路径合同解耦、显式版本policy；旧S1字段未自动采纳。旧R会据自身保存registry重新投影，因此不能全局放宽规则后追认过去拒绝项；旧索引数量、拒绝和哈希须按旧解释恢复。机器ID、原路径/原字节、显示名和规范化碰撞分别设计；不能直接重命名原件。新writer最后启用；发布新格式后，回退必须保留读取已发布格式的能力。[OLD][V2][REUSE]

## 5. 全局模块与永久责任处置矩阵

处置为KEEP / CONSOLIDATE / REPLACE / RETIRE / DEFER，全部是待采纳建议，不是已执行清单。CODE表示已读所列区间，RETAINED表示复用原证据，LOCATOR只定位，UNKNOWN为证据缺口而非处置。KEEP必须有依据，DEFER不能隐藏未审的大域。保留语义不冻结类、文件、目录或工程机制。

### 5.1 问题、消费者与推荐归属

| ID / 工程域 | 当前问题与实际消费者/证据 | 推荐处置及目标 |
|---|---|---|
| M01 身份/PIT/权限原语 | identity/primitives/authority与reader工具归属交叉；领域、reader、source、历史codec消费；RETAINED | KEEP已证语义；CONSOLIDATE同义纯原语，不统一不同编码/哈希用途 |
| M02 领域/Research/Market/Odds/数值 | 通用commit闭包已核，全部内部规则仍待G1；spine、provisional/conditional和恢复者消费 | KEEP不变量；CONSOLIDATE必要领域组织，审policy与law而非冻结原结构 |
| M03 方法/旧合同/模型适配 | 方法执行与历史Funnel合同共置；hosts、live、旧包reader消费；RETAINED＋E26 | REPLACE错位组织；KEEP必要旧codec；共享SDK/方法循环分别审复用，不更改研究接受 |
| M04 CLI/live/application | 多用途命令和组合、workflow入口；CODE/RETAINED | REPLACE过宽编排为明确用例/薄CLI；与Kedro组件/项目组织比较，旧支持入口有限过渡 |
| M05 provider transport/adapter | 网络与来源特有资格分布多处；capture、回放与reader；部分UNKNOWN | CONSOLIDATE同义传输；KEEP来源特有单位/日期/权限；按实际组件与进程边界评估复用 |
| M06 capture/producer | 来源获取、控制、保管混居；原workflows及下游消费；主链CODE，全族未闭合 | CONSOLIDATE机械步骤、REPLACE错位边界；不能让通用runner继承新采集/重试权限 |
| M07 纯观察/计算 | D及各Sector/Stock/News等纯函数与I/O同域；producer、研究准备和UI消费 | REPLACE错误依赖/组织；比较直接函数、Hamilton等实际转换组件；原算法尽量复用 |
| M08 workflows/事件/资格 | E21五job多目的，E22旧自动边，事件机会不等于data依赖 | CONSOLIDATE原生steps；REPLACE过宽目的入口为候选；RETIRE仅已证失去责任的具体边，禁止自动改接 |
| M09 producer状态/恢复 | Sector artifact强依赖、News history可选；原producer/恢复者消费；CODE＋RETAINED | KEEP必要差异；CONSOLIDATE机械读写；长期状态后端替换需G3证据与裁定，不能从R冒领权威 |
| M10 执行/失败/报告记忆 | E23 #581读改写、E24有限恢复/未知intent；reconciler/运维/恢复者消费 | CONSOLIDATE同义诊断；KEEP报告记忆与准入分离；REPLACE冗余实现须先证明原件可重建 |
| M11 档案/历史codec | registry/index/raw/progress/commit/Odds耦合；archive、D、reentry、人工恢复消费 | CONSOLIDATE保管责任；比较路径/版本策略；新policy与历史分支成本纳入，不自动采用S1 |
| M12 配置/registry/生产意图 | E25 reader解析workflow数组；intake/Watch/Collector消费，不同集合不同意图 | REPLACE确实重复的维护源；KEEP用途/接受/声明区分；外部catalog只在单一权威成立时采用 |
| M13 读包合同/通用工具 | current_state同时持有hash/path/ZIP与读面业务；多族纯计算与reader依赖 | REPLACE归属，分纯原语、codec和读面规则；输出原字节/哈希不能因迁址变化 |
| M14 Collector/预算/候选文件 | 多族借机构Radar reserve、共享可变files/API；Kedro复制影响资源身份 | CONSOLIDATE资源owner；REPLACE跨业务私有依赖；与外部组件数据/资源分离方案同台比较 |
| M15 Git发布/综合R/News | 原publisher与Retainer不同写合同；综合/News/研究/产品消费 | CONSOLIDATE同义Git机械操作；KEEP ref用途/create-only/前驱差异；不能统一为任意save/overwrite |
| M16 研究→产品/重入/时间线 | registry、work refs、Quick/Brief/Inbox各路径；RETAINED/LOCATOR | CONSOLIDATE已保存资产与请求消费；KEEP原Human和时钟；完整更正/接续闭环由G5补齐 |
| M17 Workbench client | 已读reading，app/product/业务页未完整审；浏览器与重入用户消费 | CONSOLIDATE读取/视图模型，必要REPLACE；同台比较现有与成熟组件，不预定前端框架 |
| M18 Workbench server/host | owner、同源请求、读ref/News刷新/Quick handler；完整关系UNKNOWN | KEEP读写隔离；CONSOLIDATE明确host合同；部署/Sites授权另立，暂停不免工程审查 |
| M19 tests/fixtures/evaluation | 真实入口、原字节、合成transport与跨test import；full/恢复/产品消费 | CONSOLIDATE共享fixture/重复证明；RETIRE无义务专属测试须消费者证据；研究质量评价不由CI代替 |
| M20 CI/工程自动化 | 四scope/分片/环境严格复用已有成本；PR、main、publisher消费 | CONSOLIDATE冗余执行/证据实现；比较更简单完整执行等替代，现役合同不提前放宽 |
| M21 依赖/打包/供应链 | 轻core与extras/dev重复声明，tag/SHA差异；轻reader、生产、native、dev消费 | CONSOLIDATE维护源；比较pip/constraints/lock/uv与所选外部库环境，精确Action策略全域审查 |
| M22 文档/治理/跨会话 | 旧NEXT、候选和现行协议易混；研究者/不同模型/维护者消费 | CONSOLIDATE任务触发→当前合同→原证据；RETIRE过时当前指针，不删历史、不加规则数据库 |
| M23 one-shot/兼容/退役 | E26旧launcher已退但共享实现现役；人工/CLI/workflow/fixture/历史reader仍需核 | RETIRE精确失去执行责任的入口；KEEP历史读取；CONSOLIDATE仍有消费者的实现，拒绝按名称批删 |
| M24 旁支/third_party/资源 | 小红书harness依赖研究包，样式/包资源与人工消费待核 | CONSOLIDATE为外围能力或必要历史组件；DEFER新功能启用而非免审；无使用证据不推导可删 |

### 5.2 收益、兼容成本、风险与必要验证

| ID | 预期净收益 | 必须计入的风险/兼容成本和验证 |
|---|---|---|
| M01 | 纯能力不再从业务模块借用 | 原字节/异常/时区/用途反例，不能把同名不同义函数误并；G1/G3 |
| M02 | 领域规则改动不牵连I/O/方法 | 算术、概率、PIT/Human漂移；闭包与旧模型重建，单位和UNKNOWN反例；G1/G3 |
| M03 | 更换交付者不维护旧执行链 | 旧包解码、信息身份/接受不继承；两种方法走同一commit，旧Funnel反例；G1/G3 |
| M04 | 每个用例少一个错误改动入口 | CLI参数/退出码、import/资源兼容；真实CLI合成正反例和安装包入口；G1/G6 |
| M05 | 传输/脱敏修复不逐provider复制 | 凭证、redirect、重试、源单位日期；实际endpoint和失败测试；G2 |
| M06 | 机械编排集中、来源族局部演进 | 请求预算、执行身份、原件与partial失败；逐族输入→run→reader回放；G2/G3 |
| M07 | 算法离线可复用、无需宽运行环境 | 函数图包装/名称耦合、方法语义变化；原确定性样本/拒绝及无网络边界；G1/G6 |
| M08 | 少维护目的分支和重复YAML | 外部触发、job名/title/path被消费者依赖；分清不可达旧边与现役manual/push；G2/G4 |
| M09 | 恢复入口和保管期限可解释 | 过期被追认、错误bootstrap、旧状态不可读；三类恢复演练，迁移权威先采纳；G3 |
| M10 | 错误定位清楚，旧未交付不被洗掉 | 未知效果压平、报告历史丢失、无限重试；精确target、intent和未发送反例；G2/G3 |
| M11 | 当前写入和旧读取解耦 | 旧R重投影、新旧policy/碰撞/原件库存；raw/progress/commit/Odds回放；G3 |
| M12 | 同一声明只改一处 | 数组用途误并、双配置、reader仍解析旧YAML；writer/reader/旧版本等价；G2/G3 |
| M13 | 纯模块不拖入整个读包层 | codec和根hash改变；同旧R/同bytes回放，选定文件≠全根认证；G1/G3 |
| M14 | 新reader少复制预算和回退 | dataset复制计数器、别名共享、已用预算被撤销；T3资源身份、容量与可选失败；G2/G6 |
| M15 | Git技术责任清楚且可复用 | create-only与覆盖误并、不同ref retention丢失；T5候选读回/并发/响应丢失；G3/G6 |
| M16 | 保存结果可发现、可更正、可接续 | 发现=接受/持仓、补充遗漏；跨入口同资料和更正/请求状态；真实消费原owner验；G5 |
| M17 | 新视图少复制读取和权限判断 | 只多Facade、页面回归；全client依赖/负例、适用真实browser/手机；G5 |
| M18 | host可更换且权限边界可测 | owner/同源/CSP/intent被放宽；原正反例及真实host，未部署不宣称上线；G5 |
| M19 | fixture和同义验证维护成本下降 | 删除相同断言却不同消费者的保护；义务→消费者→最小证明映射；G4/G6 |
| M20 | 反馈快且永久CI机制更简单 | 选测遗漏/环境漂移/证据不完整；full/main/发布资格与同范围时钟；G6 |
| M21 | 一处更新环境约束 | 新框架依赖、资源丢包、dev进入生产；轻core/dev/native/发行安装矩阵，许可/退出；G6 |
| M22 | 不同上下文找对当前版本 | 同会话复述替代独立接手、历史被覆盖；G7实际新上下文证据 |
| M23 | 旧执行/兼容永久责任真正退出 | 无import不等于无手工消费者；逐入口/历史/fixture/owner对账，不能删活跃Retainer；G4 |
| M24 | 旁支不污染领域与核心安装 | 漏人工用途/资源/许可证；命令/打包/历史恢复和third_party证据；G1/G4/G6 |

矩阵覆盖不是矩阵通过。本轮没有证明任何整块目录或全部历史测试可以删除；E22只识别一条当前不可由新Inbox满足的自动分支，最终RETIRE仍需历史/owner和消费者对账。

## 6. T3/T5：最小适配差异与变更成本设计

本节把复用从“可能有用”推进到实际接口假设；结果仍为CODE_READ / DESIGN_ESTIMATE / TRIAL_NOT_RUN，不是性能或采用验收。沿原T1–T7，没有新基准平台。

### 6.1 T3：既有保存来源增加读面用途

以原D reader的archive→normalize→无凭证native worker→比较/观察→候选文件→容量核验→保留为一组固定样本，News的可选历史失败为另一机制反例。不能把指数用途推广为全部股票复权或全部source链。[DREAD][DTEST][REUSE]

| 接点 | 保持现状/责任归位 | Kedro选定组件候选 | Hamilton纯函数候选 |
|---|---|---|---|
| 来源与前驱资格 | 复用原archive/previous读取与验证，拆清owner | 向节点供应已验证数据，不以catalog存在代替资格 | 向Driver提供已验证输入，不凭最终变量存在推断资格 |
| normalize/compare/render | 保持原纯函数，收敛错误依赖 | 适配Node输入输出；原函数尽量不重写 | 显式函数/参数依赖；不能让新函数名成为隐形永久公共ID |
| native计算 | 原受限子进程/超时/无凭证与固定CZSC | 不把模型/仓库client交给dataset；worker边界独立 | 图不是安全沙箱；纯转换可在worker外组织，隔离合同不弱化 |
| API预算和files | 一个真实资源owner，已用calls单调增加 | 不默认deepcopy live Collector；比较外置资源或assign＋身份/别名验证 | 内存结果不等价于资源预算；外部效果仍有明确owner |
| 可选失败与提交 | 原candidate检查完成才写入；失败保全基础结果 | 失败必须以原有显式gap表示，不能单靠全pipeline异常终止无关输入 | 只包纯函数不能假装已替代失败/容量逻辑；下游接线另验 |
| 增加第二用途的成本 | 数修改owner、跨模块规则和重复fixture | 数Node/catalog配置、适配代码、copy控制、测试与升级责任 | 数函数接线/命名依赖、包装、错误测试与环境成本 |

共同验收：相同输入/时钟产生相同原格式字节及资格；同输入复用不重装/重算；native/archive/quota/capacity失败保全价格和Research；已用API不回滚；错误说明不溢出根；无凭证worker；News历史缺口保留而独立当前采集不被误阻。沿原测试复用，不只做框架hello-world。

最小试验先核所选完整入口与必要依赖/插件/遥测/许可控制，使用合成I/O和已获准样本。安装或执行候选工具仍需原授权边界；未获准时交付试验设计，不擅自安装。不得把原复杂度藏进一个巨大节点来声称外部架构改善。

### 6.2 T5：未知效果与恢复

| 同一情形 | 必须保护的原行为 | 外部替代/内部整合的实际剩余责任 |
|---|---|---|
| dispatch后响应丢失/未看到child | 先前已上传intent仍有效；未见child不是未执行；不重复发出 | 精确lane/target/recovery-key/run对账，不能靠内存图状态恢复 |
| dispatch前main或活动状态变化 | 原明确NOT_DISPATCHED且occurred=false，区别于未知 | 外部runner异常类不能单独证明是否发出；保留效果边界 |
| create-only研究文件写后读回失败 | Retainer冻结后继写；保留原locator/部分结果，不overwrite/retry | 通用save或checkpoint的覆盖语义不直接适用 |
| 综合publish候选读回失败/并发冲突 | 不更新指针或不force，未知pointer结果先核原对象 | 复用Git机械实现仍要守预期前驱和指定ref合同 |
| Sector state缺失/过期/冲突 | 不能拿孤立cache、旧R或旧bootstrap续跑 | store.exists/cache命中不建立恢复资格；保管替代须G3 |
| #581旧未交付＋另一日期成功 | 按原目标保留报告记忆，不清空旧gap | 输出可重建必须有证据；不能把Issue当可随时覆盖的无状态视图 |

这里不预定由新引擎接管所有恢复。若库只提供纯计算执行，它不因此失败；应按其实际接管范围计收益与剩余成本。若完整项目采用要接管这些责任，必须给出同一失败集的适配/恢复证据，而不是用“支持checkpoint”替代。

## 7. 测试、CI、依赖与文档体系

永久验证按领域语义、边界格式/来源资格、真实调用者失败传播、历史恢复、产品/host安全、打包环境和独立接手分工。纯规则的字段反例不重复昂贵整链；共享helper通过也不能删除各CLI/产品的接线证明。跨test import和昂贵fixture先盘清，再讨论pytest布局/导入模式；原node身份的迁移逐条对应，不用把参数塞循环制造测试数减少。[P2][V2]

CI同台比较当前四scope＋严格merge reuse、更简单完整执行、以及保留证明目的但减少重复安装/collection/聚合的方案。现役content/draft_feedback/full/merge_reuse在替代合同采纳前不变。当前设计路径不在prose白名单，仍按未修改Ready完整验证；不移动到readings或扩白名单省CI。比较prepare/collection/execute/finalize/artifact/main/publisher，保留实际环境和失败传播。原生workflow_call、composite、actionlint、pytest split/xdist先复用，不自建影响分析或DAG来强制复用原则。

工具候选：P2固定审阅的Import Linter及明确禁止方向的正反试验；现有pip/setuptools＋constraints/锁定/uv；原生依赖提案与安全扫描；现有Git/codec和P2 MADR的选项/后果/Confirmation。工具真实依赖、安装、许可、动态调用盲区、成本与退出必须分别核；没有安装或运行证明不得写通过。任何新框架的轻core/完整dev/生产/可选native/打包资源矩阵都计入成本，不只看业务代码少了多少。

Action固定策略进入全域供应链审查：精确SHA与更新方式、可读版本、最小权限和用途证据一起决定；旧S4只是一个切片。不能顺手升级版本、改任务时钟、增权或把未读安全告警写成零漏洞。既有安全维护和主业务CI的独立责任保留，未审部分在G6。

文档维持AGENTS→NEXT/#297→#508有效计划/最新回执→精确设计/PR/证据。工程ADR不混入`docs/decisions`的Human决定。仅保留必要决策和当前入口，旧NEXT/候选的来源继续可达；不为每文件建规则schema、评分器或新registry。改入口须实际读回，独立新上下文接手不是同会话换角色或复述。

## 8. 完整分批迁移路线

P3内部继续R1取证与R2设计互相修正，R3正式采纳；不重开P0/P1/P2。下面W1–W8仍是待采纳的完整目标路线，可拆多PR，非八张固定PR，更非已授权施工队列。每个实际切片必须映射M行、接口及A验收，测试/文档/兼容跟随，不等最后补。

| 批次 | 覆盖与目标变化 | 前置、独立验证和退出 |
|---|---|---|
| W1 公共合同和保护样本 | M01–04/11/13/16/19；区分支持行为、旧格式与内部实现 | P3采纳后冻结原成功/拒绝/历史/CLI样本；不切生产格式，复用现有fixture |
| W2 共享原语与技术资源归位 | M01/05/10/13/14/15；同义hash/path/transport、预算/候选文件owner | W1＋真实消费者；比较原生/外部组件，验证同bytes/预算/错误，退出旧重复实现与转发 |
| W3 应用、producer、配置和恢复边界 | M04/06/08–10/12；事件、data、authority三种边与报告记忆 | W1/W2＋G2/G3；不更改原时钟/请求，保留有限恢复与未知intent；目标writer唯一 |
| W4 观察/来源各族结构重组 | M05–07；Sector/Stock/News/Industry/economic/D及财务输入 | W1/W2及受影响W3；按族垂直迁移，比较直接函数与外部执行，核来源→最终消费者，不重采 |
| W5 研究方法、档案和历史合同 | M02/03/11/12/16/24；方法执行/模型适配与旧codec、原件/接受分开 | G1/G3及W1/W2；两种研究交付与旧R/中文恢复；新writer最后启用，回退仍读已发布新格式 |
| W6 读包、发布和Workbench | M13–18；缩小Collector过宽组合、明确client/host和产品重入 | 相关W3/W4/W5；综合R/News/Issue独立；T3/T5及原CLI/host测试；Sites不自动部署 |
| W7 测试、CI、依赖和文档整合 | M19–22；fixture、义务归属、环境维护源和供应链 | 从W1开始量化、结构稳定部分先做；同保护集合/环境/失败和成本；新工具先授权试验/采纳 |
| W8 历史执行与过渡层退出 | M03/08/11/19/22/23/24；具体旧writer/事件边/兼容入口/专属fixture | 相应消费者已迁出、G4闭合；保留原件与必要reader；不按旧名称删共享实现，不force历史 |

W4/W5可依状态和消费者调整顺序；W7贯穿但不并行多批生产迁移。每次重排保留理由与目标映射，不能把难域悄悄删出范围。旧S1属于W5档案候选；S2扩大为W2/W6真实责任收敛而不局限两个helper；S3是W4/W6链族样本之一；S4是W7供应链一部分，均可拆分/替换/重排。

每个实际切片记录目标M/合同、精确旧→新、所有直接消费者和已证下游、复用选择/拒绝理由、实际文件/命令/格式、必须保留行为和另获准的语义变化、正反测试、成本、恢复、生产切换前置、回退及旧实现退出。范围已采纳后的普通工程不逐文件索批；新依赖/来源/费用/权限/重要语义不隐含获准。

## 9. 整体完工、成本与剩余风险

### 9.1 P5必须同时成立的八个维度

| 验收 | 完成条件 | 不能作为替代证明 |
|---|---|---|
| A1 全域审查与处置 | 所有重要工程域及发现旁支都有基于消费者的决定，核心UNKNOWN闭合 | 树清单、矩阵行数或复述P1/P2 |
| A2 目标结构达成 | 采纳的责任、禁止依赖、公共入口在代码/CLI/workflow/资源/产品实际成立，例外有依据 | 搬目录、加Facade或多套永久转发 |
| A3 语义与历史兼容 | PIT/单位/时钟/来源、Research/Odds/Human和旧包旧R恢复受保护；变化另获准 | hash存在、CI绿、版本号2.0 |
| A4 运行/恢复/发布 | 档案/运行/发布分别通过；有限恢复、未知效果、报告记忆及适用真实消费都有证据 | 一个ZIP恢复或publisher成功 |
| A5 永久复杂度下降 | 采纳整合/替换/退役的旧责任真实退出；代表变更成本呈系统性改善 | 文件/行/测试数或外部依赖数量变化 |
| A6 工程反馈和环境 | 同范围/可解释环境下CI、安装、collection、fixture和证据维护达采纳目标 | content对full、单次快跑或忽略外部升级成本 |
| A7 产品与独立接手 | 新上下文仅从入口恢复并完成代表理解/变更/恢复任务；产品可用且边界正确 | 同会话换角色、未部署页面、Human搬运摘要 |
| A8 收口与剩余归属 | 全部采纳目标完成或范围变更获准，过渡层退出，DEFER有owner/风险/触发，Human裁定发布范围 | 未审大域全部DEFER或无限等零缺陷 |

### 9.2 施工前冻结的T1–T7成本比较

T1修改一个领域资格；T2更换研究方法交付者；T3已有保存源增加读取用途；T4档案格式演进保持旧R；T5未知效果恢复；T6Workbench视图/host接口；T7依赖/验证规则。每项记录要理解/修改的责任点、跨接口传播、重复同规则的位置、兼容分支、人工恢复、fixture和CI成本。代码/文档推演标DESIGN_ESTIMATE，真正执行对照才MEASURED；模型思考时长/token不可当已测生产成本。

P1既有#799 full累计613作业秒、独立main 34秒、publisher 138秒只作为历史起点，非本轮新测量或收益承诺；不能跨不同代码、集合、content/full用途直接算提速。目标阈值在G6基线完成、P4前采纳，当前不编造百分比。[P1]

结构成功要跨代表任务看到维护责任/改动传播的系统性下降，不只一个例子变好。外部适配/fork/许可/升级、新增保护和迁移成本均计入；明显恶化要解释并裁定。若架构基线证明净收益不足，应修改目标，不降低P5标准。只把成本“解释过”不能让系统没有改善也算完工。

主要风险：遗漏动态/手工消费者；误合不同配置用途；丢失#581历史报告记忆；让cache替代state或让恢复自动重试未知效果；外部资源复制/别名共享导致预算/隔离错误；旧R格式追认；新增依赖/转发层反而增加长期负担；产品消费/独立接手被工程绿灯代签。这些都有对应M/G/T，不新建风险平台。

## 10. 取证缺口、明确下一范围与采纳事项

### 10.1 G1–G7的剩余证据，不以本版签收

| 门 | 本版增量 | 仍需补证及阻塞范围 |
|---|---|---|
| G1 全局依赖/公共消费者 | 主链workflow事件/命令、配置文本消费、共享Retainer与预算接点 | 全source import闭包、动态import/CLI/包资源、全部人工/外部消费者；阻塞精确拓扑和旧路径退出 |
| G2 producer/配置/资格链 | 四份完整workflow、Sector主要接线、reconciler与Research保管；E21/E25 | 其余source/经济/B2/行业/Concept/全Stock多目的的输入→run→原件→reader及预算/失败owner；不宣称全族已审 |
| G3 状态/档案/恢复 | 完整Sector persistence、#581报告记忆、原Retainer与intake片段 | 代表真实历史格式/原件与容量/期限、全部work-ref写者/读者、恢复演练；新格式/状态权威替换须先闭合 |
| G4 生命周期/退役 | E22具体旧自动边、E26共享实现不可按旧名删除 | 原owner/历史意图、manual/push/CLI/fixture和旧R消费者；无此证据不删边或模块 |
| G5 Workbench/研究产品 | 复用原reading及Quick/Inbox独立时钟合同 | 全client/server/host及更正、真实Quick→Brief消费；Sites暂停不免审，线上证明另立 |
| G6 变更成本/测试/候选 | T3/T5接口差异与共同失败集；Kedro复制合同/测试源码 | T1–T7实际基线、全fixture义务、环境与必要候选隔离试验；未安装未测成本保持UNKNOWN |
| G7 独立接手 | 通过原#508回执恢复本任务，但仍为本会话连续工作 | 真正新上下文/维护者的独立任务证据；本轮不能自签 |

### 10.2 下一取证包的有限边界

不再重讲Kedro/Hamilton介绍或重复News/D已有源码。下一包优先补**尚未读全的source家族与其消费者**：`hithink-stock-dump-trial.yml`多目的、`radar-smart-money.yml`、`radar-global-public.yml`、`radar-global-market.yml`、`radar-industry-breadth.yml`、Concept三类/TDX，以及`economic-release-discovery.yml`、`economic-source-capture.yml`、`b2-disclosure-appointments.yml`。从已取得树的精确入口沿命令走到写入物、直接reader与实际失败owner；不能只看workflow标题。

交付到同一设计的覆盖表：每条已读入口/输入/执行效果/保管对象/消费者/重复责任/复用候选；未读明确列出。源调用不执行，不开生产恢复；阅读metadata不是再采来源。然后对G1域/方法闭包与G3/G4/G5/G6分别补齐，不把剩余大域永久移为DEFER。各有限包在同一矩阵累积，最终全域必须交账。

工具/本地缺口仅阻塞相关证明；能够只读核实的继续，不让Human搬文件或重复授权。拟采用的新工具确需安装/执行时，带最小目的/环境/数据/费用/退出说明一次提交，不用任意依赖先装再解释。

### 10.3 Human尚需裁定，而不是现在重新确认目标

已经明确：全面审查与必要结构重构、架构级Reuse贯穿、P1/P2复用、历史保留、原语义/权限约束。待证据齐备再整体裁定：各域目标拓扑及外部实现接管范围；公共接口/旧reader支持与具体RETIRE清单；producer长期恢复权威或保管变更；成本与CI量化目标；候选隔离试验/依赖采用；分批迁移和产品部署/最终发布范围。

目前没有批准新字段filename_policy_version、批量删除、代码迁移、生产数据切换、新来源/模型调用、新费用/隐私外发/权限/任务时钟或v2.0.0发行。C固定2026-10-08/09/12/13/14自然窗、D冻结/成熟结果与#351/#621/#581等原责任独立保留。Sites暂停、禁Codex、#745分钟STOP、新城暂缓以及AI Investment Authority=NONE不变。设计/文档CI不取消这些责任，也不补签它们。

## 11. 来源与可复核定位

源码引用固定M；外部源码固定候选commit。P1/P2及附录仅按实际读取范围使用；未执行上游测试或新候选，未复制第三方实现。滚动官方文档是合同补充，不替代固定代码。当前PR/head/CI/合并和唯一下一步以#508最新回执为准。

[OWNER]: https://github.com/auguspp/decision-kernel/issues/508
[PLAN12]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6096068040
[PLAN11]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6095772144
[PLAN10]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6094482452
[V2]: https://github.com/auguspp/decision-kernel/blob/43c1284a05ed94b16230cea50252deca06bb355c/docs/kernel-2.0-design.md
[REUSE]: https://github.com/auguspp/decision-kernel/blob/9d94d0e0f01cd32b1c9895d2297a8c2d61a2526a/docs/kernel-2.0-architecture-reuse.md
[OLD]: https://github.com/auguspp/decision-kernel/blob/9290df46052f823a96069932321ae50b016af65c/docs/kernel-2.0-design.md
[P1]: https://github.com/auguspp/decision-kernel/blob/97a4b14e287b04600841c1cc157c38a3cad0a781/docs/kernel-2.0-architecture-map.md
[P2]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/docs/kernel-2.0-prior-art.md
[PROTOCOL]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/WORKING-PROTOCOLS.md
[STOCK-WF]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/stock-reading-after-sector.yml
[SECTOR-WF]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/sector-radar-shadow.yml
[INBOX-WF]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/decision-inbox.yml
[DISC-WF]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/saved-disclosure-research.yml
[STOCK-RESEARCH-WF]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/stock-business-research.yml
[RECONCILE]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/scripts/reconcile-radar-delivery.py#L59-L346
[PERSIST]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/sector_radar_persistence.py
[ONCE]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/saved_research_once.py
[STOCK-INTAKE]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/stock_research_intake.py#L1-L130
[DISC-INTAKE]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/incremental_disclosure_intake.py#L1-L150
[BASE]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/current_state_delivery.py
[DREAD]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/d_price_structure_reading.py
[DTEST]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/tests/test_d_price_structure_reading.py
[K-MEM]: https://github.com/kedro-org/kedro/blob/2e4375bd90e0ed09e179563c2ef9e29f4a2eb22f/kedro/io/memory_dataset.py
[K-MEM-TEST]: https://github.com/kedro-org/kedro/blob/2e4375bd90e0ed09e179563c2ef9e29f4a2eb22f/tests/io/test_memory_dataset.py#L1-L190
[K-MEM-DOC]: https://docs.kedro.org/en/stable/api/io/kedro.io.MemoryDataset/
