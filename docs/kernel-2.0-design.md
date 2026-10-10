# Kernel 2.0 — 全局目标架构与渐进重构方案 v2.3

日期：2026-10-10（Asia/Singapore）。设计 ID：`K2-DESIGN-20261010-v2.3`。唯一计划与跨会话接续入口：[#508][OWNER]。有效计划为[v1.2 架构级 Reuse First][PLAN12]、[v1.1 全面目标纠偏][PLAN11]和[v1.0][PLAN10]未被替代条款。

**状态：P3 GLOBAL DESIGN PROPOSAL / 待审。** Human已同意继续全面规划与架构复用比较；本稿不是全仓审计完成、具体架构采纳、依赖安装或P4施工授权。保存、CI、合并、采纳、实施、生产与产品验收分别成立。实时进度只在#508最新回执，不在本文另设进度表。

**版本关系：** 本稿承接[v2.2来源链设计][V22]，补入领域／方法静态闭包和Workbench生产模块的完整声明图；v2.1及v2.2的执行／状态、来源与复用证据继续有效。继续整合[原v2][V2]与[架构复用证据附录v1][REUSE]的设计影响，继续在同一PR #804、同一路径评审，不增加第三份设计队列。原v2与附录的精确版本、来源和未运行声明保留；附录是证据输入，不与本文竞争当前目标。原[v1/#803][OLD]作为历史候选保留，其“原拓扑为主”和默认S1→S4已不再是当前推荐。P1/#801、P2/#802交付事实不撤销、不重做，其有界KEEP不构成全域免审。

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

v2.1已保留六项有代码依据的设计约束：区分事件机会与合格数据依赖；识别#581的报告记忆；保留已有有界恢复而非统一重试策略；揭示工作流文本的配置消费者；把旧执行入口与现役共享实现分开；明确外部数据集复制与共享预算的适配问题。它们具体影响M04/M06/M08–M15/M19/M21/M23及W2/W3/W5/W6/W7/W8，详见下文。v2.2新增F01–F12来源接线与E27–E32：代码push的source effect、job/step兼容、宽指纹的维护成本、B2跨来源耦合、不同前驱/增量状态及dlt采集适配。它们进入原M/W/G，不变成新的施工队列。v2.3新增E33–E39和T1/T2/T6接点：纯领域边界、类型借用造成的宽依赖、真实方法／历史格式差异、产品读写效果、宿主身份与凭证轮换、异步版本隔离及展示合同。未把静态图闭合说成全仓调用图、运行或安全验收。

## 2. 证据基线与实际覆盖

代码M=`4e9da1d037d6cefce0a7735ee74349666430a9bf`；本次文档编辑前的PR头H=`7eccad7d98d85003213c53fb54721c7af6aaf6aa`。已重新恢复AGENTS、NEXT、#297、#508及09回执，核#804仍开放且仅两份工程文档在途。未读取生产R，未调用source/model/producer/publisher或安装候选依赖。

P1的责任/对象/成本样本、P2的十二类工程先例和复用附录的内部接点/外部候选直接复用。保留的结论只在原读取范围内有效；不能将树存在、搜索命中、旧文档或成功run标签当成全源码已审、现役性或零消费者证明。[P1][P2][REUSE]

### 2.1 前驱v2.1读取与静态核对（作为已保存证据复用）

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

前驱已对以上八份正文重算Git blob并核对相符；Python只做标准库AST解析，YAML使用BaseLoader保留`on`键，未导入或执行这些源码。本轮复用其精确证据，不把这八份重新计为新增。前驱另读Sector workflow的生产/恢复/保管主要区间、`stock_research_intake.py:1–130`、`incremental_disclosure_intake.py:1–150`及Kedro内存数据集测试前190行。复核已保留base/扩展Collector、D reader/算法/测试、档案/索引及Workbench读取接口。`WORK_REF`等有界搜索只提供正例，未穷尽全仓引用。[SECTOR-WF][STOCK-INTAKE][DISC-INTAKE][K-MEM-TEST]

前驱及本轮公开archive取回均未得到完整checkout；本轮下载工具URL门与一次urllib DNS读取分别失败，连接器和MCP读取成功。这限制全仓自动扫描结论，不证明GitHub无权限，也不能成为自建工具或代理工作流的理由。没有把局部静态分析变成永久扫描器、CI门禁或新的执行平台。

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

**E23：#581不只是可以丢弃的展示缓存。** `report_issue()`读取Issue正文中`radar-continuity-status-v1`的原JSON，调用`retain_unresolved()`后写回。原未交付身份按lane/target保留，非同一目标的后来成功不能清除它。它实际承担报告连续性记忆；迁移必须保留或证明可从原件重建。它仍不是dispatch准入权威，也不是Human判断数据库，不能由报告字段授予重试权限。原v2对“机器健康投影”的宽泛理解应据此收紧。[RECONCILE]

**E24：必要恢复不能被统一成零重试或默认重试。** reconciler已有最多3次每周期source attempt、活动检查、精确诊断类别、冷却、main CI、旧intent核对等有限规则。未知dispatch保持UNRECONCILED/DISPATCH_UNCERTAIN；明确定义的未发出与已接受待结果分别记录。模型调用和create-only写入又有自己的不重试边界。W3应保留已有获准语义，通用库的retry/resume不能替代；本稿也不扩大原有限source recovery。[RECONCILE][ONCE]

**E25：工作流文本还是配置接口。** base `Collector.research()`读取同M的Inbox workflow，从具名literal arrays提取decision_packages和research_attention_handoffs。当前两组为空，而shadow和显式公告扫描另有六公司样本；重复证券不等于同一生产意图。把数组搬进新配置/catalog需要同时迁移writer、reader、测试和旧版本解释；不能只改YAML再认为reader仍正确。用途registry不能变成新授权清单。[INBOX-WF][BASE]

**E26：旧名称不等于无用实现。** `saved_research_once.py`已退出Suken固定launcher，`__main__`明确拒绝运行，但现役hosts复用其Retainer和模型循环。按once/旧日期删整个文件会误退共享责任。应分别审查保管机械步骤、模型适配、方法选择和历史codec的归属；旧执行责任已退不重做，仍有消费者的实现允许CONSOLIDATE，不因复杂就继续全体KEEP。[ONCE][STOCK-INTAKE][STOCK-RESEARCH-WF]

### 2.4 v2.2来源家族增量：已保存证据复用

v2.2批次固定同一M，完整读取12份workflow、10份runtime reader/compat和B2脚本，共23份内部文件；另完整读取固定dlt RESTClient。24份均重算Git blob与连接器元数据相符，Python仅AST解析、YAML用BaseLoader保留`on`；不导入或执行业务/上游代码。部分范围另读`tushare_relay.py:1–140`及dlt的retry、tests、pyproject，见§3.4。源请求数/字节上限来自代码合同，不是本轮真实请求或运行成本。

| 入口（均为完整workflow读取） | 已核输入、执行和保管 | 已核直接消费者／仍缺证据 | 处置和复用含义 |
|---|---|---|---|
| [F01][WF-STOCK] `hithink-stock-dump-trial.yml` | 八个手工purpose、六个job；Stock接精确Sector原件，independent/source-check/native-feed等独立；theme分支另有指定路径push；多种独立artifact | base Collector按实际stock-reading job选；independent读面已在组合根接线，细部本轮未读；native-feed脚本只定位，不能签全部purpose内部资格 | M06/08/23：REPLACE多用途接线候选；保留不同来源/研究权限及已消费pilot，不以trial名称判整份可退 |
| [F02][WF-SMART] `radar-smart-money.yml` | 两个原定时＋手工模式；control、主capture、Relay补充、FTShare诊断/试验分开，30日artifact；Relay依已核主源或精确旧源 | 完整`smart_money_reading`：排除诊断、核本attempt/job、最多一次control绑定前驱；保留history/state/gzip chunks与可选Relay。control/capture算法未读全 | M09/14/15：CONSOLIDATE机械读写，KEEP主/补充隔离、精确前驱和缺口；不得将旧源复用冒称新采集 |
| [F03][WF-GLOBAL-MARKET] `radar-global-market.yml` | indices/Shibor两用途、各自原cron与as-of；显式Relay凭证；精确代码/CI，分族artifact30日 | 完整`global_market_reading`按族重建，旧v1两族与v2六族分别解释；source codec仅由导入/调用定位 | M05/07/12：共享transport不统一资产/期间语义；保留来源各自日期与失败 |
| [F04][WF-GLOBAL-PUBLIC] `radar-global-public.yml` | Treasury/FX/commodity/crypto四用途及原cron；无业务凭证，原字节/失败/离线replay，分族artifact30日 | 同一完整reader的独立query和family状态；不用public失败抹Relay，失败run内可读原件亦须重建 | M06/15：CONSOLIDATE同义保管；成功判定不能统一为workflow绿灯，实际source parsers仍待核 |
| [F05][WF-IND] `radar-industry-breadth.yml` | Sector完成事件或手工；三个无needs的job：breadth/public-context/industrial-fundamentals，独立原件30日 | 完整三个reader：breadth要求全run成功，另两项核自己的job；历史external样本另列，fundamentals同capture不重复消费增量 | M08/10/14：审资格粒度与可选失败，而非简单合并成一个job；E28 |
| [F06][WF-CONCEPT] `radar-concept-source.yml` | 明确session/code；原capture/verify，最多15请求；payload和inert源码tar分开，artifact30日 | 完整`concept_radar_reading`以可信installed verifier和compat校验最新primary，供公司组合；不执行tar | M07/11/23：保留原字节回放，重组未来验证闭包；E29，不放宽旧来源资格 |
| [F07][WF-DETAIL] `radar-concept-detail.yml` | 明确primary run/code/offset，最多三项六请求；base.zip与独立补充，30日 | 完整`concept_detail_reading`核primary run/head/artifact/字节/日期；完整compat双端指纹对照；只一批而非累积全覆盖 | KEEP补充与主源绑定；CONSOLIDATE组合/保管；未来窄codec替代宽文件指纹的方案待验证 |
| [F08][WF-TDX] `tdx-concept-snapshot.yml` | 已使用eltdx 3.2.2，下载wheel并记hash；snapshot＋同host可选trend；源文件/请求身份/回放，30日 | 完整`tdx_concept_reading`[TDX-READ]：原snapshot和新版嵌套envelope、可选trend/member分开；full-run入口门仍在 | REUSE现成解析/协议能力，不另写TDX；对整套外部架构/组件与现有适配仍可比较；可信本地回放不等于执行源档代码 |
| [F09][WF-VIBE] `vibe-concept-snapshot.yml` | 仅明确手工code/mainCI，capture/replay，无key/no-retry，30日artifact | 手工replay是已知消费者；本轮原组合根和publisher未见Vibe专属入口，indexed search零命中不是全局无消费者证明；人工/历史仍UNKNOWN | M23：用途核查候选，不自行RETIRE整模块，也不自动接成新增每日源 |
| [F10][WF-ECON-DISC] `economic-release-discovery.yml` | directory与native RSS两用例；RSS bootstrap/精确predecessor显式分开；push只接声明的successor request；90日 | workflow内`economic_release_inputs verify`、RSS `prepare-native-rss-successor`/`radar_feed_intake verify`；capture/控制函数与研究产品下游未穷尽 | KEEP目录与正文/研究分离；补齐source生命周期，不把普通代码变动变成新RSS基线 |
| [F11][WF-ECON-CAP] `economic-source-capture.yml` | 手工＋四项代码/配置路径push；最多四个已审页面capture/verify，完整/失败proof90日 | 原离线verify为直接消费者；未证明完整产品下游或当前自动边已无用途 | E27：修改代码可能触发source effect，必须在实际迁移之前裁定触发处置，不擅自删除或触发 |
| [F12][WF-B2] `b2-disclosure-appointments.yml` | 三种手工source-kind、显式registry IDs/period/目录或PDF定位；不同源边界，30日原件 | 完整731行脚本：原件先保存、目录调用原CNINFO parser、PDF复用archive/getter/extractor；registration-proposal尚无有效ref，后续Git保管/登记/发布另行完成 | M01/05/08/12：已有复用保留并审过宽依赖；只借Relay六类助手却被全Relay hash/共享并发门耦合，E30 |

本表覆盖指定入口及所述直接消费者，**不是12族capture内部逻辑、全部测试、所有手工用途或真实生产链全通过**。`external_radar_reading`[EXTERNAL-READ]完整读取证明它消费明确的历史News/Industry样本，不能因名字external就认定它消费经济RSS/B2。F01/F10/F11的控制/捕获函数缺口继续留在G2，不藏入DEFER。

### 2.5 v2.2对目标架构的六项实质修正

**E27：代码迁移有隐含source effect。** F11的push路径包含自身workflow、`economic_source_capture.py`、`economic_node_study.py`和seed；F01的theme push还监听capture脚本和样本。与F10的显式request-only push不同，普通工程路径改动就有源调用接线。W1必须在移动/替换相关代码前核本次diff是否命中效果入口，确定获准的隔离/触发迁移方式；不是把它变成所有PR的新审批平台，也不能靠`skip ci`绕开验证。只改本设计路径不命中这些源入口。[WF-ECON-CAP][WF-STOCK][WF-ECON-DISC]

**E28：job/step/title/path已是部分reader的兼容接口。** F05三个job没有needs；breadth reader在读取artifact前要求全run成功，Easy Stock和industrial reader却分别核自己的job。Easy Stock还核三个精确step名。故原生workflow_call/composite、拆job或改显示名会影响证据解释，不只是YAML去重复。建议目标为与实际用途一致的qualification unit（run/job/step/原件），对独立可用数据避免无理由的兄弟失败传播；具体改变仍须查历史/测试并采纳，当前仅识别耦合，不宣称已发生生产故障或立即改成job级放行。[WF-IND][BREADTH-READ][EASY-READ][FUND-READ]

**E29：宽实现指纹把局部变化变成跨域兼容维护。** `concept_detail_compat.py`有九张主要实现映射；最初完整映射17个文件，primary子集13个。代码明确记录#530显示函数、#579/#728 Sector、#757/#769 Collector预算等不被该回放调用的变更，却需保存额外installed/historical配对。这是可定位的结构性成本，不只是文件长。比较A继续映射、B抽出原纯能力并约束未来回放闭包、C由合适外部组件承担通用部分且保留Kernel来源/格式合同。推荐优先验证B/C的窄边界：新产物精确绑定必要验证实现/版本与输入，而非每次指纹覆盖无关宽模块；旧映射/原件留到有替代恢复证据才退。不能删除指纹、用当前hash追认旧失败、执行archive里的tar，或把某框架cache key当资格证明。[CONCEPT-COMPAT][CONCEPT-READ][DETAIL-READ]

**E30：B2有明确的跨来源技术耦合。** 全脚本AST对`relay`的属性引用只有`RelayError/SECRET_ENV/_unique/decode/now/require`；已读这些定义，属于错误、JSON、时钟和凭证反射防护，不是Relay市场请求。实际公告用独立Requests/CNINFO。与此同时workflow核整个Relay blob，并共用Global market的`radar-global-market-relay`并发组。应比较中性原语归属与维持现状的净成本；锁的历史目的、其他外部竞争者尚UNKNOWN，不能据“不同端点”自动删锁或撤哈希门。对应M01/05/08/12与W2/W3。[B2-CODE][RELAY-HELPERS][WF-B2][WF-GLOBAL-MARKET]

**E31：不是一个通用latest-success或cache对象。** Global按六族保存最新尝试和最后可读批次；Smart Money用精确control-bound前驱及history/state，历史恢复失败不能清空重基线；industrial同capture再发布保留上次比较增量；Concept补充必须绑定primary。它们可共用传输/字节/存放实现，但状态角色、来源日/检查日和旧结果含义须分别保持。设计不默认制造一个总cursor/checkpoint；外部组件接管范围也按这些差异计成本。[GLOBAL-READ][SMART-READ][FUND-READ][DETAIL-READ]

**E32：采集组件的返回值可能压平Kernel必须保留的区别。** dlt RESTClient在提取数据时可把JSON null变成空列表，且其上游测试明确覆盖该行为；分页器可能已将`PageData.request`更新到下一页上下文，不能直接当已经发出的原请求记录。B2当前区分null/空表/缺列/未查询，并先保存原始页。因此可复用显式session/原始response/hook，但必须在转换前保管本次实际request/response及失败，显式页限、目的地和no-retry；若只能继续维护全套旧实现再套一层，就没有净收益。它是可验证适配条件，不是永久拒绝dlt。[DLT-CLIENT][DLT-TEST][B2-CODE]

### 2.6 v2.3领域／方法闭包与Workbench声明图

固定同一M，源码子树返回231项、Workbench子树返回42项，均未截断；这些数字包含目录，不能当作已读文件数。Workbench为40个文件：19个生产mjs、15个test.mjs、1个HTML、5个browser目录文件。本轮完成全部19个生产mjs及index.html正文；测试只完整读app、owner-identity、reading-ref三份，其余测试／browser仍只定位。宿主真实部署不在这张图内，不能把“19/19”写成前后端全部验收。[WB-CODE][WB-INDEX][WB-APP-TEST]

本轮本地核对42份完整正文：16个领域／旧方法模块及包初始化、single_quick_contract与direct_deep两个runtime模块、19个生产mjs、三份前端测试、index.html。每份重新计算Git blob与精确M处元数据相符；合计453,785字节／7,853行只描述读取范围，不是成本或优化收益。research_commit与reading.mjs复用前驱原字节再核hash，其余40份本轮取得。Python仅标准库AST；22份mjs用现有Node v22.16.0的`--check`做语法检查，不执行模块、测试、DOM或fetch。另读原host说明全文、News workflow第1–160行；不计入42份完整字节核对。[RC][DOMAIN-CODE][SINGLE-QUICK][DIRECT-DEEP][WB-REF-TEST][WB-OWNER-TEST][WB-HOST][NEWS-SITE-WF]

**闭包口径：** 下表为内部静态模块依赖，不是函数调用／执行效果图；所有函数体内import也纳入AST。三条根的模块总数包含根、不含无导入的包初始化，不计标准库与Pydantic内部。逐一取得被引用内部模块后，research_commit为11节点／28条唯一模块边，workflow为12／34，research_workflow_v1为15／51；三者并集16模块／56边，所列内部依赖均闭合。该集合只依赖标准库和Pydantic；未发现对runtime、adapter、网络或GitHub模块的导入。不能外推到条件／临时Odds、CLI、全部contracts或所有runtime。[RC][SPINE][METHOD-WORKFLOW]

| 根／边界 | 已核内部静态接线 | 含义与额外边界 |
|---|---|---|
| 通用Research提交 | research_commit → evidence、identity、primitives、rehearsal、research；research → valuation；rehearsal → odds → calculation | 研究保存不必执行数值计算，但一个framing类型扩大import闭包；E34 |
| 数值Decision Spine | workflow → Research、ObservedMarket、Odds、rehearsal、Human surface等明确纯能力 | 方法模块依赖spine，spine不反向导入旧研究方法；保留纯计算边界而不冻结文件位置 |
| 旧Research Method v1 | research_workflow_v1 → deep_research、research_funnel、workflow及共同领域值 | 旧方法哈希／路由仍有历史消费者，不移植为新方法的唯一准入 |
| 新single Quick | single_quick_contract → 共享Claim/Discovery、旧方法terminal enum、external_research_execution；读档函数再引用external_research_identity | 已完整读本文件，明确版本分派；外部execution／identity的全闭包本轮未完成 |
| Human-origin Direct Deep | direct_deep → 通用ResearchCommitPackage、Evidence及external_research_execution的预算／receipt | 受注入execute_pass驱动的方法循环；不是核心强制的研究步骤、模型或新的宿主 |
| 包初始化 | `src/decision_kernel/__init__.py`仅文档串和空__all__ | 未通过包初始化隐式加载整个系统；不把此处无副作用扩展为所有模块无副作用 |

**Workbench生产声明图：19节点、41条唯一静态模块边，全部相对模块目标均在本次正文中；未发现循环或生产动态import表达式。** 这是源码声明的有界结论，不包含测试中的动态import、HTML宿主接线、运行时函数回调、全局fetch/crypto/DOM或外部Sites消费者。app入口静态闭包14模块；server/routes闭包8模块；二者共享reading、product、quick-inbox三个模块，故不能把`workbench/`整体当浏览器专属代码。[WB-CODE][WB-ROUTES][WB-APP][WB-QUICK]

| 所有生产模块（省略workbench/前缀） | 直接内部模块依赖（省略.mjs） |
|---|---|
| app.mjs | quick-inbox-ui、news-markets、news-live、reading、presentation、product |
| reading.mjs / presentation.mjs / global-markets.mjs | 无静态内部import；reading仍定义网络操作，不能由“零import”推导无I/O |
| product.mjs | reading |
| quick-inbox.mjs / quick-inbox-ui.mjs | 前者：product、reading；后者：quick-inbox、reading、product |
| news-live.mjs / news-refresh.mjs / on-demand.mjs | 分别：reading；reading、product；reading、product、news-refresh |
| news-markets.mjs | concept-members、quick-inbox-ui、global-markets、research-calendar、reading、news-live、on-demand、product |
| concept-stock.mjs / concept-members.mjs / research-calendar.mjs | 分别：reading、product；reading、concept-stock、product；reading、product |
| server/routes.mjs | 同目录quick-inbox-handler、news-refresh-handler、owner-identity、reading-ref-handler |
| server/owner-identity.mjs | 无静态内部import；实际使用宿主crypto及环境 |
| server/news-refresh-handler.mjs / server/reading-ref-handler.mjs | reading |
| server/quick-inbox-handler.mjs | reading、quick-inbox |

### 2.7 E33–E39：由真实接口修正目标，而非按文件大小拆分

**E33：纯领域边界已有可保留的正证据。** 上述三个闭包将Evidence/PIT、Research、估值、数值Odds、演练和Human展示的数据关系留在进程内；源码内没有供应商／GitHub传输。目标不应把已内聚的确定性能力换成Agent、远程服务或为适配图而重写算法。仍可调整归属与公共出口，不能据本闭包给全M02免审。`ResearchSnapshot`的schema1数值提交、schema2 Research-only提交与`assert_decision_spine_ready`不同；不能让“保存研究成功”自动满足数值Odds资格。[RS][SPINE][RC]

**E34：借一个类型会拖入另一个执行域。** research_commit只为`NonAuthoritativeRehearsalFraming`导入rehearsal；该类型在33–45行，但其模块还导入odds，后者导入calculation。Single Quick又为共同terminal enum导入research_workflow_v1；Direct Deep借external_research_execution的预算／receipt。不能把宽import等同于已经发出网络或执行计算，但它扩大更换方法／轻量读取必须理解和保护的边界。比较A保持原状、B将真正共享的纯类型／结果值归到窄合同、C复用成熟组件的公共出口组织；当前推荐先验证B，复用P2公共接口先例，不新建万能协议库。需核真实公共使用者、模型schema、旧包哈希及有限兼容出口，不能只加一层转发后永久保留两套定义。[RC][REHEARSAL][SINGLE-QUICK][DIRECT-DEEP][P2]

**E35：统一交付不等于统一历史研究流程。** 通用提交哈希覆盖Research状态与精确Evidence，旧Deep哈希另外覆盖Discovery/Pre/Quick/Deep。Single Quick以明确method/schema组合选择原v1或v2解析器，混合版本拒绝而非fallback；FULL_CANDIDATE只产生无执行权限的委托定位。Direct Deep最终要求无framing的schema2 REVIEW包，原UNKNOWN与Evidence、预算和stop规则由这个方法实现负责。目标可共用保管、receipt和结果展示，但不能伪造Pre、把旧方法条件强塞新研究、将Direct Deep的passes限制升格为所有研究者必走流程，或用新规则追认旧包。对应M02/03/11、W5和T2；两个runtime模块的其余导入闭包仍是G1缺口。[RC][DEEP][SINGLE-QUICK][DIRECT-DEEP]

**E36：产品具有三类效果，不能只画成read-only前端。** app根刷新只重读保存R/独立Issue；Quick Inbox显式POST在#601追加add/remove，后续result另有原协议，保存材料不执行Quick；News显式prepare/submit/status中只有合格submit发出原workflow dispatch。Inbox精确读回才报告saved；并发相同请求允许实际产生多条评论，投影保留全部原ID。结果存在但原文未核验仍待处理。News的Map只是单isolate去重；跨实例保护还依赖原workflow中同一预期run_number/code/attempt的源前检查，不保证恰好一次dispatch或必成功。原source guard已在workflow第1–160行核到；来源／发布其余实际运行未验。目标分别复用现有reader、追加记录和有界dispatch，保持未知效果先对账，不把新UI框架cache/mutation重试当作权限与完成证明。[WB-APP][WB-QUICK][WB-INBOX-HANDLER][WB-NEWS-HANDLER][NEWS-SITE-WF]

**E37：宿主边界与凭证轮换是适配责任，不是已证安全漏洞。** routes将两个固定read-ref GET交给reading-ref-handler时，没有先经过ownerEnvironment；该handler本身核固定origin/intent/token，不作原owner比较。写路径另经ownerEnvironment及各handler核验。原设计依赖owner-only Sites边缘、可信身份头和无旁路Worker URL；本轮未读真实部署，不能宣称可绕过鉴权，也不能把这些route直接搬成独立公网服务。owner fingerprint使用现有GitHub token做HMAC；由实现可推导：只轮换token而不重建匹配fingerprint，会使指纹式owner校验失配；旧refresh permit也会失效，后者原说明已明确。应保留协调更新／原生GitHub对账与回退，不以独立新secret服务或放宽身份校验解决。单用户origin/owner常量是信任边界配置，不能与写死业务对象一概判冗余。[WB-ROUTES][WB-REF-HANDLER][WB-OWNER][WB-HOST]

**E38：异步版本隔离是产品合同，不是装饰代码。** app以reading对象、detail/render generation和News请求序号拒绝迟到回包；原件／预览按R、path、hash绑定，局部预览完成不清空已开的正文或搜索状态。News live使用独立ref，不冒称与综合R同版。app测试已经包含跨R、晚到失败、切页、目录失败、原文损坏及更正／历史回应反例；本轮完整读这些测试且仅语法检查，没有执行或伪装真实浏览器。目标可复用原生控制或候选框架，但必须保留这些效果；不能因为代码长先选全局store、自动polling或默认重试。两份owner/ref测试证明现有受控测试的范围，不证明实际边缘可信。[WB-APP][WB-LIVE][WB-APP-TEST][WB-OWNER-TEST][WB-REF-TEST]

**E39：展示规则也是受消费接口，但不应升级为研究真值。** product按精确Quick首标题、已登记use和窄JSON格式分类；多份正文不按更新时间选唯一结论，原文标题／段落摘录不是模型摘要。路径、版本、来源单位、时间和分母亦由各view核验；shape或声明hash相等不等于重算canonical reading_hash。前后端共享product.useLabel意味着“只改中文标签”还可能改变之后新Inbox context的title/hash与去重身份，原历史记录不应改写。此项由resolveSelection→contextValue→digest代码推导，未实测重复写入。显示与记录的稳定身份应拆清，比较保持原合同与下一版本有界解耦；不得静默改旧context哈希。对应M12/13/16/17，进一步说明不能只搬目录或统一字段名。[WB-PRODUCT][WB-QUICK][WB-INBOX-HANDLER][WB-READING]

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

**v2.1保留的适配发现：Kedro的数据复制合同。** 固定版本MemoryDataset的load/save采用显式copy_mode或按类型推断；普通对象通常deepcopy，亦可配置assign保留同一引用。已读对应测试的同对象/浅拷贝/深拷贝反例，未执行。因此将带凭证、API已用次数、memo和候选文件的Collector当普通dataset传递，可能复制资源计数或产生错误共享；这是代码支持的集成风险，不是已复现的Kernel故障。assign是可比较的解决方式，不能凭此直接否决Kedro，也不能未经测试认定assign安全。[K-MEM][K-MEM-TEST][K-MEM-DOC]

建议优先比较“已验证普通数据/字节＋纯计算”进入外部组件，resource budget、不可重复效果和最终发布留给明确owner；或通过显式共享资源适配而不复制live client。若适配仍把整个Collector藏进万能节点、原复杂度一项未退，只增加外层图，不算复用收益。反过来，不为展示图而制造大量无消费者小节点。

### 3.4 来源采集与原生工程复用：不只比较函数图

v2.2已审候选dlt固定为**1.31.0 / `2360d229c77f7f64692acc31a4555f4cfcd50ed3`**（Release/tag由原生GitHub核对）。完整读取`dlt/sources/helpers/rest_client/client.py`432行；局部读`requests/retry.py:1–250`、实际目录定位的`tests/sources/helpers/rest_client/test_client.py:1–180`、`pyproject.toml:1–150`及官方REST helpers合同。未安装、未执行任何测试或pipeline；未审全部依赖/许可/初始化外发。包元数据声明Apache-2.0不是整个依赖链合规结论；未复制上游实现。[DLT-CLIENT][DLT-RETRY][DLT-TEST][DLT-PKG][DLT-DOC]

| 同口径方案 | 能交给已有实现的责任 | Kernel仍负责什么／采用前验证 |
|---|---|---|
| 原Requests/stdlib＋现役source parser | 已有连接、响应、原始字节和具体来源映射，迁移最小；已有AKShare映射/eltdx/NewsNow/CZSC等按原证据复用 | 若保留仍要收敛重复错误/JSON/保管和宽依赖，不以熟悉现状作理由；新用途变更点和测试成本须与替代比 |
| GitHub原生composite／reusable workflow | 可复用已有安装、代码/CI核验和保管技术步骤，不新造scheduler | composite是原job内steps，reusable workflow提供job级复用，不能随意互换；现有reader消费精确job/step/title，迁移要双边证据；不得让共享steps扩大token、源权限或cron。[GH-REUSE] |
| dlt独立RESTClient＋明确session/分页/response hook | Requests客户端、分页及返回上下文有实际入口，可不使用destination/pipeline平台 | 默认session会加可配置重试，可传已约束Session；须明确timeout/redirect/trust_env/HTTP预算与原字节保管；不把自动selector/paginator、忽略404/null→[]当Kernel源语义 |
| dlt更完整声明式source/pipeline | 候选可接管更多资源关系、cursor、提取/加载，不能先假设必须新建服务器才可用 | 本轮只审独立客户端，不声称完整架构优劣已定；GitHub状态权威、历史append/create-only、PIT/部分失败与退出成本仍须比较。不将dltHub平台/Agent能力混成所选客户端的必需依赖 |
| 本项目自建统一抓取/状态平台 | 本轮未证明独特需求或相对净收益 | 不开建。已有组件配置或薄适配满足时优先复用，工具未安装/本地取回受限不是自建理由 |

dlt `_create_request`接受完整HTTP(S) URL，`_send_request`使用会话的环境设置，DEBUG日志可含请求参数/headers；这些是集成控制点，不是已经发生泄露。候选试验须固定可信目的地、无环境凭证/代理、日志策略和实际发送次数；用可信配置而非source文本控制hook。普通GET/POST可返回原Response，不能因为paginated数据有null归一化就否认其原件保管接点。默认重试可配，不能据默认行为排除；也不能仅配置项存在就宣称满足全部边界。

**当前设计选择：** W2/W3先比较原生已有机制的责任归位与dlt等组件薄适配；不采纳全局替换。对只有有限单页原件保管的用途，dlt可接管的执行责任可能少，属于待测假设；真正多页/多资源用途可能更有收益。G6以同一B2/Global受控样本比原件、失败、请求数、改动点、依赖安装/升级与退出成本，不预定任何胜者。Kedro/Hamilton继续在其真正适合的用例/纯计算域比较，不强迫一个框架承担全部Kernel。

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
| M01 身份/PIT/权限原语 | identity/primitives/authority与reader工具归属交叉；E33/34已核纯领域闭包与借类型的宽依赖；其他原证据RETAINED | KEEP已证语义；CONSOLIDATE同义纯原语，不统一不同编码/哈希用途 |
| M02 领域/Research/Market/Odds/数值 | E33三条根的16模块静态并集已闭合；schema1/2提交与数值资格分离；provisional/conditional等仍待G1 | KEEP不变量；CONSOLIDATE必要领域组织，审policy与law而非冻结原结构 |
| M03 方法/旧合同/模型适配 | E26/34/35：旧方法／通用提交／single Quick／Direct Deep已读到真实分歧；hosts/live/旧包reader消费，runtime全闭包未完 | REPLACE错位组织；KEEP必要旧codec；共享SDK/方法循环分别审复用，不更改研究接受 |
| M04 CLI/live/application | 多用途命令和组合、workflow入口；CODE/RETAINED | REPLACE过宽编排为明确用例/薄CLI；与Kedro组件/项目组织比较，旧支持入口有限过渡 |
| M05 provider transport/adapter | 网络与来源特有资格分布多处；F01–12/E30/E32补到入口及消费者，capture内部仍部分UNKNOWN | CONSOLIDATE同义传输；KEEP来源特有单位/日期/权限；按实际组件与进程边界评估复用，增加dlt独立客户端比较而不预装 |
| M06 capture/producer | 来源获取、控制、保管混居；原workflows及下游消费；主链＋12来源workflow及所列直接reader为CODE；各capture算法/控制未全闭合 | CONSOLIDATE机械步骤、REPLACE错位边界；不能让通用runner继承新采集/重试权限 |
| M07 纯观察/计算 | D及各Sector/Stock/News等纯函数与I/O同域；producer、研究准备和UI消费 | REPLACE错误依赖/组织；比较直接函数、Hamilton等实际转换组件；原算法尽量复用 |
| M08 workflows/事件/资格 | E21/E22及E27/E28：多purpose、旧自动边、push效果、job/step/title资格；事件不等于data或authority | CONSOLIDATE原生steps；REPLACE过宽目的入口为候选；RETIRE仅已证失去责任的具体边，禁止自动改接 |
| M09 producer状态/恢复 | Sector artifact强依赖、News history可选；原producer/恢复者消费；CODE＋RETAINED | KEEP必要差异；CONSOLIDATE机械读写；长期状态后端替换需G3证据与裁定，不能从R冒领权威 |
| M10 执行/失败/报告记忆 | E23/E24加E28/E31：#581、有限恢复/未知intent、不同job资格/源前驱；reconciler/reader消费 | CONSOLIDATE同义诊断；KEEP报告记忆与准入分离；REPLACE冗余实现须先证明原件可重建 |
| M11 档案/历史codec | 档案/codec及E29宽实现指纹；archive、Concept回放、D、reentry、人工恢复消费 | CONSOLIDATE保管责任；比较路径/版本及窄回放闭包；旧完整指纹配对保留至替代恢复证明，新policy不自动采用S1 |
| M12 配置/registry/生产意图 | E25数组与E30 B2显式registry选择；intake/Watch/Collector消费，不同集合不同意图 | REPLACE确实重复的维护源；KEEP用途/接受/声明区分；外部catalog只在单一权威成立时采用 |
| M13 读包合同/通用工具 | current_state混持原语／读面；E39前后端共享reading/product且展示文字参与新请求身份；不可只统一字段或复制校验 | REPLACE归属，分纯原语、codec和读面规则；输出原字节/哈希不能因迁址变化 |
| M14 Collector/预算/候选文件 | 多族借机构Radar reserve、共享files/API；E28/E31各族隔离和增量；Kedro复制影响资源身份 | CONSOLIDATE资源owner；REPLACE跨业务私有依赖；与外部组件数据/资源分离方案同台比较 |
| M15 Git发布/综合R/News | 原publisher与Retainer不同写合同；综合/News/研究/产品消费 | CONSOLIDATE同义Git机械操作；KEEP ref用途/create-only/前驱差异；不能统一为任意save/overwrite |
| M16 研究→产品/重入/时间线 | E35/36/39补Quick原版本读取、#601追加和结果字节资格；原registry/work refs/Brief接续尚有未核部分 | CONSOLIDATE已保存资产与请求消费；KEEP原Human和时钟；完整更正/接续闭环由G5补齐 |
| M17 Workbench client | E36/38/39：14个client生产mjs全部正文和静态边，HTML/app受控测试已读；真实浏览器、全部测试与前端替代成本未验 | CONSOLIDATE读取/视图模型，必要REPLACE；同台比较现有与成熟组件，不预定前端框架 |
| M18 Workbench server/host | E36/37：5个server模块全读，routes闭包8模块；read-ref依赖原宿主边缘、owner指纹／permit依赖token；真实部署UNKNOWN | KEEP读写隔离；CONSOLIDATE明确host合同；部署/Sites授权另立，暂停不免工程审查 |
| M19 tests/fixtures/evaluation | 真实入口、原字节、跨test import；新增完整app/owner/ref三份受控测试阅读，仅语法检查；15份WB测试与browser未全审 | CONSOLIDATE共享fixture/重复证明；RETIRE无义务专属测试须消费者证据；研究质量评价不由CI代替 |
| M20 CI/工程自动化 | 四scope/分片/环境严格复用已有成本；PR、main、publisher消费 | CONSOLIDATE冗余执行/证据实现；比较更简单完整执行等替代，现役合同不提前放宽 |
| M21 依赖/打包/供应链 | 轻core与extras/dev重复声明，tag/SHA差异；轻reader、生产、native、dev消费 | CONSOLIDATE维护源；比较pip/constraints/lock/uv与所选外部库环境，精确Action策略全域审查 |
| M22 文档/治理/跨会话 | 旧NEXT、候选和现行协议易混；研究者/不同模型/维护者消费 | CONSOLIDATE任务触发→当前合同→原证据；RETIRE过时当前指针，不删历史、不加规则数据库 |
| M23 one-shot/兼容/退役 | E26共享实现、E29旧回放映射、F09 Vibe手工用途；人工/CLI/workflow/fixture仍需核 | RETIRE精确失去执行责任的入口；KEEP历史读取；CONSOLIDATE仍有消费者的实现，拒绝按名称批删 |
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

### 6.3 T1/T2/T6：本批落实到真实责任点

以下是已读代码支持的变更设计，不是完整影响分析或MEASURED收益。正式保护仍优先复用原测试与成熟公共出口／组合方式，安装候选和改变语义不在本轮发生。

| 任务 | 已核责任点（不等于全局消费者已穷尽） | A/B/外部采用应如何同口径比较 |
|---|---|---|
| T1 改一条Research资格 | ResearchSnapshot的提交／spine-ready、ResearchCommitPackage的版本／PIT／证据精确集合、workflow数值使用；framing类型使无关Odds实现进入import边界 | A原规则与依赖不动；B窄共享类型及领域资格归位；外部组织模式不能替代资格。核v1冻结哈希、v2研究保存、数值拒绝及真实调用者，不能用11→更小的理论节点数当收益 |
| T2 更换研究交付者 | generic与旧Deep信息身份不同；single Quick的method/schema读取、委托来源；Direct Deep注入执行与最终通用包；共享Retainer仍有现役消费者 | 比较保留实现、抽共同纯结果值／保管、适用外部执行组件；原方法应可以退出执行但继续读取旧包。记录必须修改的writer/reader/fixture，不把旧方法整体塞入“兼容节点”宣称退出 |
| T6 修改产品视图或宿主接入 | 14模块app闭包、8模块route闭包共享3模块；useLabel参与新context身份；owner/token/permit、固定ref/源workflow pin、DOM generation均有消费者 | 先分清纯展示、记录协议、受限I/O与宿主合同，再比原生视图或成熟组件。任何替代须覆盖原app晚到／跨R／完整原文与owner/ref拒绝；真实host仍另验，不能只比较组件行数 |

当前建议是保留现成纯领域算法、原生ES模块与已证明必要的效果边界，优先试证窄共享合同及展示／记录身份解耦的净收益；这不等于永久否决外部架构或已批准新目录。前端框架及host替代尚无本轮固定实现比较，不作胜负判断。T1/T2/T6全部直接与间接消费者、所需fixture和安装／升级／退出成本仍按G1/G5/G6补齐。

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
| W1 公共合同和保护样本 | M01–04/11/13/16/19；区分支持行为、旧格式与内部实现 | P3采纳后冻结原成功/拒绝/历史/CLI样本；先核实际diff→触发→source effect，未裁定不移动效果路径；不切生产格式 |
| W2 共享原语与技术资源归位 | M01/05/10/13/14/15；同义hash/path/transport、预算/候选文件owner | W1＋真实消费者；比较原生/外部组件，验证同bytes/预算/错误，退出旧重复实现与转发 |
| W3 应用、producer、配置和恢复边界 | M04/06/08–10/12；事件、data、authority三种边、job/step资格与报告记忆；审E30共享锁而不自动取消 | W1/W2＋G2/G3；不更改原时钟/请求，保留有限恢复与未知intent；目标writer唯一 |
| W4 观察/来源各族结构重组 | M05–07；Sector/Stock/News/Industry/economic/D及财务输入 | W1/W2及受影响W3；按族垂直迁移，比较现有/dlt/纯函数执行与窄回放闭包；旧指纹恢复先保护，核来源→最终消费者，不重采 |
| W5 研究方法、档案和历史合同 | M02/03/11/12/16/24；方法执行/模型适配与旧codec、原件/接受分开；按E35保持真实method/schema/信息哈希差异，不造Pre | G1/G3及W1/W2；两种研究交付与旧R/中文恢复；新writer最后启用，回退仍读已发布新格式 |
| W6 读包、发布和Workbench | M13–18；缩小Collector过宽组合；按E36–39分清client/shared/host、三类效果、凭证轮换、异步版本隔离与产品重入 | 相关W3/W4/W5；综合R/News/Issue独立；T3/T5及原CLI/host测试；Sites不自动部署 |
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
| G1 全局依赖/公共消费者 | 主链/F01–12加E33–39；领域三根16模块并集、包初始化、两新方法接点、Workbench19节点41静态边 | 已闭合仅三条领域／旧方法根与19生产mjs；其余顶层12文件、runtime/adapter、动态CLI／资源及人工／外部消费者继续未闭合，阻塞全局拓扑及退出 |
| G2 producer/配置/资格链 | 前驱加本批12份完整source workflow、B2全脚本和10份reader/compat；E27–E32 | F01 native-feed/各purpose控制，F02 control/capture，F03/04 source codecs及F10/11 capture/lifecycle内部与其全部下游仍需补；本批不签完整G2 |
| G3 状态/档案/恢复 | Sector/#581/Retainer加Smart Money/Global/industrial/Concept明确前驱与增量角色 | 代表真实历史格式/原件与容量/期限、全部work-ref写者/读者、恢复演练；新格式/状态权威替换须先闭合 |
| G4 生命周期/退役 | E22旧自动边、E26共享实现、E27效果入口、E29兼容映射和F09手工Vibe用途 | 原owner/历史意图、manual/push/CLI/fixture和旧R消费者；无此证据不删边或模块 |
| G5 Workbench/研究产品 | 19生产mjs＋index全读；app及owner/ref三份测试读源码；独立时钟、追加/dispatch、宿主与token、迟到响应已定位 | 生产声明图已闭合，真实宿主/入口资产/可信头与旁路、其余12份test.mjs及browser、Quick→Brief实际消费/更正全链仍未验；不因Sites暂停免审 |
| G6 变更成本/测试/候选 | T1/T2/T6新增真实变更接点；T3/T5与既有候选证据复用；42文件/闭包/语法计数仅静态覆盖，不是维护或运行成本实测 | T1–T7实际基线、全fixture义务、环境与必要候选隔离试验；未安装未测成本保持UNKNOWN |
| G7 独立接手 | 通过原#508回执恢复本任务，但仍为本会话连续工作 | 真正新上下文/维护者的独立任务证据；本轮不能自签 |

### 10.2 下一取证包：剩余领域边界、方法存取与source控制，不重建本批图

本轮已完成三条选定领域／旧方法根的静态闭包与Workbench全部19生产mjs声明覆盖；不是29个顶层模块、231项源码子树、全部测试或真实宿主全通过。下一包优先收口**G1尚未进入本图的conditional/provisional Odds、research/claim contracts、source policy、CLI/live/包资源和方法存取接点**；外围xiaohongshu两个模块仍按M24核直接用途，不能只因旁支免审。已读direct_deep/single_quick需沿external_research_execution/identity、research_commit_only／odds_retention原writer/reader继续，不重复读已闭合16模块或19生产mjs。

同时按原G2逐项补F01多purpose控制、F02 control/capture、F03/04 source codec及F10/11生命周期的真正执行／消费者；按G3关联原state/work-ref/格式及恢复权威。G4具体退出、G5真实host和产品全链、G6全fixture与实际成本、G7独立接手均明确留存，不用大域DEFER收口，也不因本轮无已证故障就宣称架构无需调整。

结果继续回写原24M／W／G与本设计；#508只记录实际证据和下一步。只读分析和工程文档不逐文件索批；不执行源／模型／生产恢复、不安装或执行新候选工具、不部署Sites。代码目录、具体替代、迁移及旧路径退出仍须P3-R3正式采纳；没有完整checkout就按实际取得字节标覆盖，不造代理工作流或要求Human搬运。

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

[V21]: https://github.com/auguspp/decision-kernel/blob/a5da26a464e04d6c6b2ae3ad4c57d3101ad66354/docs/kernel-2.0-design.md
[WF-STOCK]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/hithink-stock-dump-trial.yml
[WF-SMART]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/radar-smart-money.yml
[WF-GLOBAL-MARKET]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/radar-global-market.yml
[WF-GLOBAL-PUBLIC]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/radar-global-public.yml
[WF-IND]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/radar-industry-breadth.yml
[WF-CONCEPT]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/radar-concept-source.yml
[WF-DETAIL]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/radar-concept-detail.yml
[WF-TDX]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/tdx-concept-snapshot.yml
[WF-VIBE]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/vibe-concept-snapshot.yml
[WF-ECON-DISC]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/economic-release-discovery.yml
[WF-ECON-CAP]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/economic-source-capture.yml
[WF-B2]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/b2-disclosure-appointments.yml
[GLOBAL-READ]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/global_market_reading.py
[SMART-READ]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/smart_money_reading.py
[BREADTH-READ]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/industry_breadth_reading.py
[EASY-READ]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/easy_stock_reading.py
[FUND-READ]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/industry_fundamentals_reading.py
[TDX-READ]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/tdx_concept_reading.py
[CONCEPT-READ]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/concept_radar_reading.py
[DETAIL-READ]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/concept_detail_reading.py
[CONCEPT-COMPAT]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/concept_detail_compat.py
[EXTERNAL-READ]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/external_radar_reading.py
[B2-CODE]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/scripts/b2-disclosure-appointments.py
[RELAY-HELPERS]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/tushare_relay.py#L1-L140
[DLT-CLIENT]: https://github.com/dlt-hub/dlt/blob/2360d229c77f7f64692acc31a4555f4cfcd50ed3/dlt/sources/helpers/rest_client/client.py
[DLT-RETRY]: https://github.com/dlt-hub/dlt/blob/2360d229c77f7f64692acc31a4555f4cfcd50ed3/dlt/sources/helpers/requests/retry.py#L1-L250
[DLT-TEST]: https://github.com/dlt-hub/dlt/blob/2360d229c77f7f64692acc31a4555f4cfcd50ed3/tests/sources/helpers/rest_client/test_client.py#L1-L180
[DLT-PKG]: https://github.com/dlt-hub/dlt/blob/2360d229c77f7f64692acc31a4555f4cfcd50ed3/pyproject.toml#L1-L150
[DLT-DOC]: https://dlthub.com/docs/dlt-ecosystem/verified-sources/rest_api/advanced
[GH-REUSE]: https://docs.github.com/en/actions/concepts/workflows-and-actions/reusing-workflow-configurations

[V22]: https://github.com/auguspp/decision-kernel/blob/7eccad7d98d85003213c53fb54721c7af6aaf6aa/docs/kernel-2.0-design.md
[DOMAIN-CODE]: https://github.com/auguspp/decision-kernel/tree/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel
[WB-CODE]: https://github.com/auguspp/decision-kernel/tree/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench
[RC]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/research_commit.py
[RS]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/research.py
[SPINE]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/workflow.py
[METHOD-WORKFLOW]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/research_workflow_v1.py
[REHEARSAL]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/rehearsal.py
[DEEP]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/deep_research.py
[SINGLE-QUICK]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/single_quick_contract.py
[DIRECT-DEEP]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/direct_deep.py
[WB-ROUTES]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench/server/routes.mjs
[WB-APP]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench/app.mjs
[WB-QUICK]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench/quick-inbox.mjs
[WB-INBOX-HANDLER]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench/server/quick-inbox-handler.mjs
[WB-NEWS-HANDLER]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench/server/news-refresh-handler.mjs
[WB-REF-HANDLER]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench/server/reading-ref-handler.mjs
[WB-OWNER]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench/server/owner-identity.mjs
[WB-PRODUCT]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench/product.mjs
[WB-LIVE]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench/news-live.mjs
[WB-READING]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench/reading.mjs
[WB-INDEX]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench/index.html
[WB-APP-TEST]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench/app.test.mjs
[WB-OWNER-TEST]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench/owner-identity.test.mjs
[WB-REF-TEST]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench/reading-ref.test.mjs
[WB-HOST]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/docs/workbench-news-refresh.md
[NEWS-SITE-WF]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/.github/workflows/radar-newsnow-daily.yml#L1-L160
