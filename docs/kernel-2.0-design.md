# Kernel 2.0 — 全局目标架构与渐进重构方案 v2

日期：2026-10-10（Asia/Singapore）。设计 ID：`K2-DESIGN-20261010-v2`。唯一计划/接续入口：[#508][OWNER]。有效计划为[v1.1 Human目标纠偏][PLAN11]及其未替代的[v1.0条款][PLAN10]。

**状态：GLOBAL DESIGN PROPOSAL / 待审，不是全仓审计完成、技术方案采纳或P4授权。** Human已明确本次全面审查/重新规划的目标，无须重新批准这个目标；具体架构、模块处置及实施范围仍需实证和正式采纳。本文交付差距分析、全局目标架构、主要责任处置矩阵、完整迁移路线、完工定义及风险。未完成的取证逐项列在第9节，不能用本文篇幅、PR、CI或矩阵覆盖替代。

**替代关系：** 本文作为P3当前整体审阅稿，替代[v1/#803][OLD]作为最终目标架构和默认施工路线的地位。旧五ADR、S1–S4及其工程证据按原精确版本保留，转为候选，不直接继承其“原拓扑为主”和S1优先结论。P1/P2文件及已交付事实不撤销、不重做；其中方向性KEEP仅是当时有界建议，不是全工程域的免审依据。实时进度仍只写#508最新回执，不在本文另设进度表。

## 1. 目标校准：全面的是决策范围，渐进的是实施方式

Human本次要求是“覆盖整个 Kernel 工程体系的架构审查、目标架构重新设计与渐进式全面重构”，而非四项修补或无依据重写。目标是使维护、扩展、验证、恢复和接手的总成本实质下降，同时保留有价值的研究成果、已证明必要的语义及Human权限边界。[PLAN11]

### 1.1 原方案与目标的差距

| 差距 | v1中的实际表现 | v2纠正 | 不因此抹去的成果 |
|---|---|---|---|
| 审查范围与实施粒度混淆 | 全工程学习最后只形成S1–S4默认路线 | 所有重要工程域先进入同一处置矩阵，实施批次从目标架构推导 | 四项仍可作候选和回归案例 |
| 现状偏好先于审查结论 | ADR-01推荐保留原拓扑，S2限定两个私有helper | 同台比较现状、有限整合、结构性模块重组；目录和接口都可调整 | 已证领域语义、既有公共消费者继续保护 |
| 缺少完整目标系统 | placement大多复述当前位置 | 明确目标责任、依赖、公共合同、状态owner、运行/恢复和产品交界 | 旧路径是迁移输入，不必是目标路径 |
| 历史成本没有全局处置 | 没有全局writer/reader/兼容/fixture退出表 | 区分当前执行、历史读取、研究原件、过渡接头；逐项处置 | 已完成退役不重做，旧原件不删除 |
| 单链核验替代系统性数据设计 | S3只核一条指数结构链 | 覆盖不同来源/资产/单位/时钟/复权/方法/结果链族 | S3保留为其中一项端到端样本 |
| 完工容易退化为PR清单完成 | 只对首轮已实施范围对账，缺整体改动成本门槛 | 目标矩阵、代表变更任务、兼容退出、跨模块恢复及独立接手共同验收 | CI/发布证据仍有效，但不代签架构价值 |

原计划本已要求责任、先例、ADR、placement、迁移和验收。需要纠正的是目标窄化及证据不足时的过早定案，不是丢弃原计划重新立项。[PLAN10][P1][P2][OLD]

### 1.2 本轮固定与开放的事项

固定：全工程域审查；GitHub仍为正式代码/证据/状态后端；PIT、UNKNOWN、Evidence/Research/Odds/Human区分；历史与原话保留；AI Investment Authority=NONE；逐批验证；实施前正式采纳。

开放：代码拓扑、模块组合、内部接口、配置存放、读包和运行状态表示、兼容维护方式、测试布局、CI具体实现及依赖管理工具。现有四scope、Collector继承、flat runtime、旧方法包装和tag固定方式都不是永久不可动的架构原则。**在替代方案获准并完成适用验证前，现役规则仍照常执行。**

本通知不授权大批删除、生产数据迁移、新来源、安装依赖、新费用、权限/时钟改变或重要经济语义修改。新设计也不借“重构”复活已暂停任务。

## 2. 证据基础与增量审查

本轮代码基线 **M=`4e9da1d037d6cefce0a7735ee74349666430a9bf`**（#803合并）。恢复当前AGENTS、NEXT、#297、#508、v1.0计划和前驱交接；创建本分支前读取开放main PR为空。未读取生产R，未执行source/model/业务入口或生产恢复。

P1/P2直接复用：责任图、两条主链、对象分类、六组CI历史成本、十二类工程先例。原blob分别为`3f2b91bbf37999a5542d476fbc0c9aaf7b61873b`、`18b4ef2b0dccd743d45ffa5453663c00cbbc3bf4`；旧设计blob为`c9b847f336010ed1f77c451bbadac2a5498acf7e`。本轮重新核对选定12份本地原文件与Git blob并做Python AST读取，未导入或执行源码。[P1][P2][OLD]

增量范围：完整读取根树及`src/decision_kernel/`、`.github/`、`workbench/`子树元数据（返回未截断）；读取下列代表性代码区间和pyproject。树清单只证明对象存在，不证明全源码已审、现役/无消费者或可删除。未对全部tests/fixture、全部历史分支和所有调用路径做全量分析。

| 证据 | 实际观察 | 可支持的判断 / 不能支持的判断 |
|---|---|---|
| E1 `[current_state.py:1–145]` | 同模块包含check/clock/json/hash/path/archive原语及读面workflow资格/选择 | 存在通用原语与读面合同共置；值得拆责任。不是每项检查都冗余。[CURRENT] |
| E2 `[institutional_radar_reading.py:1–112]`及D读取代码 | 通用发布预算`_reserve`归在机构Radar模块，D借用；reader为回放资格引用capture模块 | 共享预算owner和纯验证/副作用边界需重组；不能直接删除来源特有验证。[RESERVE][DREAD] |
| E3 原base/扩展Collector及AST | Git传输、artifact、配置、业务lane、导出、publish同在base；扩展静态串接多族reader且共享files/budget | 结构目标应超过抽两个helper；不能从继承或文件长度单独判故障。[BASE][COMPOSITION] |
| E4 `[sector_radar_persistence.py:1–120]` | producer恢复权威是合格artifact；cache只作同字节加速，过期须显式合格恢复 | 恢复策略是真实语义，不能用更容易取回的R替代；是否改长期保管需单独设计。[PERSIST] |
| E5 `[research_workflow_v1.py:1–115]`与通用commit | v1编排自称可替换method，仍含序列化Funnel合同；通用commit本身方法无关 | 方法执行、历史合同和领域不变量可分离；不能仅因旧v1就删除解析器。[METHOD][COMMIT] |
| E6 `pyproject.toml` | 单一包，core只声明Pydantic；optional extras与dev重复列多项依赖，setuptools配置src布局 | 当前已有轻core，环境声明仍有重复维护；未证明传递依赖完整锁定或改工具一定省成本。[PACKAGE] |
| E7 Workbench树及已保留reading代码 | client读面、product/app与server身份/请求handler并存；固定R和独立Issue观察分开 | UI读写权限与视图模型要全局纳入，不能只审reading.mjs；实际host/浏览器尚未重验。[UI][UI-TREE] |
| E8 `[xiaohongshu_harness.py:1–72]`与源码树 | 内容输出模块及样式数据位于主包，并依赖DeepResearch/ResearchClaim | 旁支能力也要处置，不能误当全部核心或无用文件；实际命令/人工消费者仍需核。[XHS][SRC-TREE] |

本地公开仓库archive取回因DNS失败而未获得完整checkout；授权GitHub/MCP读取成功。这是本轮证据边界，不是全局无权限或“无合适工具”。以下提出的是有依据的全局设计与明确取证门槛，不冒称已完成全仓动态调用图。

## 3. 架构备选与推荐

### 3.1 同一目标下比较三个方案

| 方案 | 结构和收益 | 永久代价/主要风险 | 建议 |
|---|---|---|---|
| A 维持现状，只做已知修补 | 迁移少、短期回归面小 | 不能有把握解决共享原语错位、runtime多重责任、方法/历史合同混放及跨用途改动传播 | 保留为对照；不是本次默认整体目标 |
| B 有限整合，保留大部分边界 | 集中少量重复helper与文档/依赖声明 | 可能留下核心共享owner和运行/恢复层耦合；适合局部已经内聚的模块 | 按矩阵逐域选择，不把它预定为全仓上限 |
| C 同仓模块化结构重构 | 按领域、方法、观察计算、用例、基础设施、公共合同与产品接口重新分配实现；旧入口有限过渡 | 需要调用者对账、导入/序列化兼容、过渡退出和测试重接；不能只多加包装层 | **推荐为总体候选，具体模块按证据选A/B/C，不要求每处重写** |

不推荐另建微服务、DAG平台、数据库、消息总线、通用provider框架或新状态后端：本轮没有证明这些成本能解决当前问题。同仓默认不是现有拓扑默认正确；结构性重组也不自动要求拆成多个发行包。

**可推翻条件：** 若关键调用图/变更对照表明某次拆分只增加转发层、依赖或兼容负担，则该域选择A/B，并记录原因；若当前存储确有无法在GitHub现有边界解决的容量/恢复需求，再提交独立替代论证和授权，不按“全面”推导新基础设施。

### 3.2 推荐目标责任与依赖

```text
Human / 可替换研究者 / Workbench
                 |
        受支持的命令与读写接口
                 |
       application：具体用途的编排
        /          |             
  methods      domain       observations
 研究方法    领域与数值      纯观察/解释输入计算
        \          |             /
        contracts：必要的边界数据合同
                 ^
 infrastructure：GitHub / HTTP / 文件 / 编码

composition root显式把具体基础设施交给用例；
上图表示责任，不意味着每个调用必须走过所有盒子。
```

更精确的依赖规则：domain不依赖method、GitHub、workflow、UI或网络；methods/observations可用领域纯类型，不导入发布器来拿通用工具；application依赖明确的领域/方法/观察能力及其边界合同，不从具体HTTP模块读取全局凭证；infrastructure实现所需I/O、受支持格式和必要纯数据合同，不决定Research接受或投资结论；CLI/host组合根可同时知道application和具体infrastructure，负责注入；Workbench只依赖已声明的读面/请求合同，browser中没有写token。测试可以组合各层，但业务模块不导入tests。

`contracts`表示公共边界的归属，不是强制新建万能schema。领域内部纯值留在domain；Git对象的存储细节留在GitHub基础设施；现有序列化字段只有证明需要时才改变。不能把所有失败、所有来源或所有状态装入一个总对象，也不为每个函数创建Interface/Factory。

### 3.3 建议物理组织及迁移原则

```text
src/decision_kernel/
  domain/          已核必要的身份、证据、研究、市场、Odds、估值与计算
  methods/         可替换研究方法；与旧方法历史读取分开
  observations/    sector / stock / news / industry / economic / D等纯计算族
  application/     capture / research / reading / recovery等具体用例
  contracts/       真实跨边界合同，按对象族分开，不是万能状态模型
  infrastructure/ github / http / files及格式读写
  interfaces/      CLI与受支持内容输出入口
workbench/         客户端视图和独立服务端host适配
```

这是待验证/采纳的目标组织，不是已创建目录或移动清单。需要移动的理由是降低错误依赖与共同变更成本，而不是统一英文名。已有内聚模块可整体迁入而不重写算法；不必每个业务族都复制七层空目录。现有`research.py`不能在过渡期被同名新package悄悄遮蔽；Python导入解析、CLI入口、包内JSON资源与安装后运行必须验证。[PACKAGE][PYTEST]

旧内部import可按实际消费者使用有限转发层，记录被谁使用以及退出证据；不能把每条旧路径永久公共化。过去档案按原commit/path/blob读取，不因代码整理批量移动。新的资料默认位置需按对象owner决定，不能把Human记录、工程ADR和研究底稿混为一类。

### 3.4 六组明确的外部合同

| 合同 | 输入/输出及owner | 迁移中不得隐含改变 |
|---|---|---|
| 研究交付 | 方法无关的Research包、精确Evidence、独立方法版本；领域commit返回原资格及信息身份 | COMMITTED不等于Full质量、Human接受或当前Odds可用；不强制旧研究流程给所有研究者 |
| 来源采集 | 显式获准的请求、provider/channel/资产/期间/参数；返回原字节、捕获时钟与真实错误 | 不能隐式fallback、补采或把源错误变UNKNOWN金额0 |
| 保存结果读取 | 指定run/attempt或Git定位和用途；输出验证过的文件及资格/缺口 | read不触发producer/Research/市场调用，不把缓存改为当前来源权威 |
| 生产恢复 | 指定producer状态与合格checkpoint、原前驱和授权 | 不从综合R/历史报告获取运行恢复权；不自动跨缺口续跑 |
| 派生发布 | 绑定代码/输入的候选文件集与预期前驱，读回后更新指定ref | 未知写结果先对账；并发冲突不force；不同ref的独立时钟不合并 |
| 产品请求与Human决定 | 只读展示、显式请求、接受/决定分别保管；服务端按原owner授权受限写入 | 点击/显示/文件存在/模型建议均不等于Human接受、Watch或交易 |

具体Python签名不在本轮凭空冻结；上述合同决定后，尽量沿用已支持接口，只有真实消费者收益才新增门面。

## 4. 数据、状态、运行与恢复的目标模型

### 4.1 权威归属与对象placement

同一个GitHub后端可以保存多种用途对象，不能因此把它们变成同一种状态。每种对象只有一个明确的逻辑写入owner；并发实例由原生前驱/条件写入控制，而非假设只能有一个进程。

| 对象 | 目标权威/写入者 | 保管与读合同 | 迁移/兼容决定 |
|---|---|---|---|
| 代码、研究方法与工程协议 | main的获准PR；方法/工程owner分别负责 | 固定M可复查；方法、schema、软件版本独立 | 可重组代码，不能重写旧方法/接受历史 |
| 生产意图/配置 | 每个用途唯一显式声明owner | 声明版本绑定执行；配置不是结果或授权的自我证明 | 对workflow literal arrays与外部输入比较一个维护源；派生副本禁止独立编辑 |
| 来源原件与提取表示 | 原capture/保管操作，精确源和字节身份 | 原字节、表示转换与权利/隐私范围分开 | 不自动全部永久公开；不以转换后文本假装PDF原件 |
| Research底稿/提交/结果 | 研究交付用例；旧资料在原ref保留 | 后继追加；原格式解码；恢复不重新研究 | 复审archive/index/typed reader，中文名方案也须比较新增兼容成本 |
| Human原决定 | 原Human授权留存路径/Issue | 原话、对象、时点及后继关系；接受与交易分开 | 不进工程ADR库，不由AI迁移推断新决定 |
| producer运行状态 | 原producer的已资格化状态来源 | 明确checkpoint、输入/方法/前驱、失败及可恢复范围 | Sector现行artifact恢复先保持；长期Git checkpoint只是待裁定方案，不自动升格R |
| 执行事实与未知效果 | 原Actions run/attempt/job/产物及必要回执 | 未执行、确定失败、效果未知、读回成功分开 | 复用原记录，避免第二运行数据库或逐步骤永久状态机 |
| 综合读包/News派生缓存 | 各自唯一派生发布owner | 综合R原子快照；News和Issue观察带各自时钟 | 共享机械传输可整合，不合并不同可见性/保留语义 |
| fixture/evaluation | 测试/评价owner | 合成、真实历史样本和业务原件分别标识 | 不把研究原件仅为测试方便改写；失去义务才退专属fixture |
| 工程设计与进度 | 本文件设计、#508计划/回执、#297路由 | 精确版本和替代链；只有#508持有当前2.0进度 | 不创建第二registry/看板/状态库 |

### 4.2 运行用例与恢复模式

推荐用明确输入和结果的短生命周期用例：核意图与资格→执行获准I/O→纯验证/计算→留存结果/失败→必要读回→显式发布。共享的是已有技术原语和真实重复代码，不是所有业务相同的状态机。保持现有触发机会、预算、拒绝边界和来源特有规则，直到对应改变获准。

恢复分三类：**档案恢复**只读原字节并验证原合同；**运行恢复**依原producer合格状态与授权继续；**发布恢复**核原候选/指针是否已成功后再决定动作。三者不能通过一个`resume()`默认串行触发。某步骤效果未知时先按原locator对账；不会因代码搬迁就重新消耗已使用的pilot或来源预算。[PERSIST][BASE]

可选reader失败保全基础结果，但已消耗的API预算不能回滚。最后合格结果、最近尝试、观察窗口、新鲜度、检查时钟分别保留；允许展示旧合格结果与当前失败，不把“失败保全”误写成当前成功。高频News与低频综合发布的分离维持原用途，不因整合改成每次采集都全量发布。

### 4.3 血缘验收覆盖链族，不止指数示例

必须覆盖：领域Research/Evidence→commit→不同Odds路径；行情/日历/复权→股价/成员比较；sector状态/事件→来源保存→读包；行业/财务/公司行动→解释输入；News原件/滚动历史/实时缓存→产品；档案/进度→重入；D多期限/价格结构/Outcome；Human决定→产品/Watch消费者。每族选代表路径与关键拒绝，并对未涵盖的不同机制另列例外。

共同核对provider/channel、逻辑资产及供应商代码、期间/窗口/币种/单位/复权、来源修订、可得与捕获时钟、算法/方法/schema、原字节和最后数值绑定。hash只证明对应内容，不证明经济含义正确。多输入不是禁令，但不能同ticker静默混源。未取得的源正文/历史可得性保留UNKNOWN，并明确限制哪个结果。

## 5. 全局主要模块与永久责任处置矩阵

**以下均为P3推荐，不是已执行的删除/迁移清单。** K=KEEP，C=CONSOLIDATE，P=REPLACE，T=RETIRE，D=DEFER仅在表内缩写；完整处置含义分别为保留、整合、替换实现、退出责任、明确暂缓。事实等级用CODE（已读代码）、RETAINED（P1/P2/历史证据）、LOCATOR（仅树/定位）、UNKNOWN。CODE只覆盖说明的区间，不表示全模块审计通过。

### 5.1 当前问题、消费者与目标处置

| ID / 重要工程域 | 当前问题与证据 | 现役/待核消费者 | 推荐处置与目标归属 |
|---|---|---|---|
| M01 身份/PIT/权限原语 | 原语在identity/primitives/authority及读面通用函数有不同归属；CODE/RETAINED | 所有领域、source/reader/历史合同 | KEEP语义，CONSOLIDATE必要纯原语；domain与中性边界明确，不能统一不同编码规则 |
| M02 领域研究/市场/Odds/估值/数值 | 方法无关commit已有证明；其他领域内部闭包/重复校验仍UNKNOWN | commit、spine、provisional/conditional、保管和显示 | KEEP已证不变量；CONSOLIDATE领域组织，逐项审查policy与law，不冻结所有类/目录 |
| M03 研究方法、v1/v2合同与模型接口 | method编排与历史Funnel模型共处；CODE；完整现役方法路由待核 | hosted研究、旧包reader、live兼容、Full/Quick说明 | REPLACE方法执行与历史codec共置的组织；KEEP必要旧读取；不替用户改变研究方法 |
| M04 CLI/live/应用编排 | 多用途命令和具体组合耦合；通用live已有方法独立接口；CODE/RETAINED | console script、workflow命令、手动工程使用 | REPLACE为按用例的application及薄CLI/composition root；旧入口按实际兼容窗口退出 |
| M05 provider transport/纯adapter | provider网络与不同资格散布adapters/runtime；全族内容UNKNOWN | 采集、市场资格、PDF/资料解析、源回放 | CONSOLIDATE同义技术传输；KEEP来源特有单位/日期/授权，按后端与纯adapter分离 |
| M06 capture/producer | 多源capture与运行控制同居runtime；具体生命周期需逐族核 | 原source workflows、后继reader及恢复者 | CONSOLIDATE可证重复编排/落盘；REPLACE错位边界，不新增来源或通用采集平台 |
| M07 纯观察/解释输入计算 | sector/stock/news/industry/economic/D等纯逻辑与I/O命令同目录；CODE/LOCATOR | producer、reader、研究准备、Workbench | REPLACE为内聚observations族；纯计算不反依赖publisher，复用原算法 |
| M08 workflows/触发/运行身份 | 当前入口含按path/title/purpose例外；多用途trial入口存在；CODE/LOCATOR | schedule/dispatch/workflow_run、资格reader | CONSOLIDATE原生重复steps；必要时REPLACE混合目的入口；先核现役用途/外部时钟，不按名称删 |
| M09 producer状态/恢复 | Sector持久化有专用恢复权威；其他状态全貌UNKNOWN | Sector/News等有状态producer、恢复者 | KEEP已证明恢复语义；CONSOLIDATE机械存取，存储替代DEFER至权威/容量证据明确 |
| M10 执行回执/失败/诊断 | 许多字段反映不同失败阶段，不能全变空列表；CODE/RETAINED | 调用方、运行健康、恢复和读面 | CONSOLIDATE同义回执/安全诊断；KEEP未知效果和部分失败；不建事件库 |
| M11 研究/来源档案与历史codec | index、raw/progress/commit/Odds恢复互依；中文policy v1有额外解释分支；CODE | archive、重入、D、产品、人工恢复 | CONSOLIDATE档案责任；比较保持映射、解耦路径、版本化policy，不默认采纳旧S1字段设计 |
| M12 配置/registry/生产意图 | workflow literal arrays、input dirs、registry用途各异；RETAINED | Inbox、Watch、Collector和生产器 | REPLACE重复维护的配置来源（如经核属重复）；KEEP意图/用途/接受区分，不造第二registry |
| M13 读包合同/通用工具 | current_state混合通用check/hash/path/ZIP与读面业务；CODE | 多类reader、纯D计算、归档、产品 | REPLACE归属：中性原语/格式codec/读面业务分开；旧序列化不因搬代码变hash |
| M14 Collector/共享预算/可选扩展 | 多族共享可变files和预算；机构Radar持有通用reserve；CODE | base/扩展reader、D、发布器 | CONSOLIDATE共享预算/文件集owner；REPLACE跨业务借私有helper和过宽组合责任 |
| M15 Git发布/综合R/News缓存 | 综合publish已有唯一实现；不同派生读面保留语义不同；CODE/RETAINED | current-state、News-live、UI、研究者 | CONSOLIDATE机械Git传输/前驱读回；KEEP各ref用途，REPLACE不必要重复入口实现 |
| M16 研究→产品接续/重入/时间线 | registry、reentry、Quick/Brief/Inbox有多个消费路径；RETAINED/LOCATOR | hosted研究、用户读取、Watch、#351产品 | CONSOLIDATE已保存资产/请求的消费接口；KEEP原Human决定和独立时钟；补真正闭环 |
| M17 Workbench client/视图模型 | app/product/reading和各业务页需全量依赖审查，不能只看reading；CODE/LOCATOR | 浏览器、资料重入、跨市场/新闻/公司页 | CONSOLIDATE共享读取/视图模型；必要REPLACE耦合实现；不默认引入前端框架 |
| M18 Workbench server/host与权限 | 原server有owner身份、读ref、News刷新、Quick请求handler；LOCATOR | 原host routes、owner交互、连接后端 | KEEP读写隔离；CONSOLIDATE受支持host合同，权限实现逐项核；Sites部署仍暂停 |
| M19 tests/fixtures/eval | 有真实入口/原字节/合成transport，也有跨test import；CODE/RETAINED；全义务表UNKNOWN | full CI、模块回归、旧档案重建、研究评价 | CONSOLIDATE共享fixture和重复证明；RETIRE无义务的专属测试仅限证据成立；研究评价独立 |
| M20 CI/证据/工程自动化 | 四scope、分片聚合、环境精确复用有实测成本；RETAINED | PR、main、发布资格、开发者 | CONSOLIDATE冗余执行/证据实现；比较现四scope与更简单完整执行方案，不能先宣告旧设计永续 |
| M21 依赖/打包/供应链 | extras/dev重复约束；core轻依赖已存在；tag/SHA策略不一；CODE | 工程、轻reader、native worker、生产及安全扫描 | CONSOLIDATE依赖维护源；比较锁定/constraints/现工具，精确Action固定纳入全域策略 |
| M22 文档/规则/接续 | #508有单入口，但文档建议/历史NEXT会误作现行范围；RETAINED | 工程会话、研究者、后续维护者 | CONSOLIDATE任务触发→当前合同→历史依据；RETIRE过时当前指针，不删除历史论证 |
| M23 one-shot/试验/兼容层 | 已退役与仅名字旧的对象混在历史中；RETAINED/LOCATOR；零消费者未证 | CLI/workflow/人工恢复/历史reader/fixture | RETIRE候选执行责任；KEEP必要历史读法；每条必须列调用者退出与回退，不批量按日期删除 |
| M24 旁支输出/third_party/样式资源 | 小红书harness依赖研究包，包资源配置有全局归属；CODE/LOCATOR | 内容命令/历史样本/分发使用仍需查 | CONSOLIDATE为外围受支持能力或有界历史组件；DEFER新功能激活；不能从主链之外推出可删 |

### 5.2 每项的收益、兼容成本、风险与验证

| ID | 预期收益 | 兼容成本/风险 | 必要验证及UNKNOWN处置 |
|---|---|---|---|
| M01 | 不再从业务reader借基础能力 | 不同hash/JSON用途被误并；旧引用失效 | 对照原字节/异常/时区反例；保留不同codec语义，G1/G3 |
| M02 | 领域变化不牵连运行/供应商/方法 | 算术、概率资格、PIT或Human边界漂移 | 域闭包、旧模型重建、单位与UNKNOWN负例；未审内部关系在G1补齐 |
| M03 | 更换模型/方法不需要保留旧执行链 | 旧包失去解码；新方法继承旧接受 | 现役路由/历史reader表、两个不同方法包进入同一commit、原Funnel反例；G1/G3 |
| M04 | 一个用例有一个编排入口 | import/CLI flags、exit code、资源读取改变 | 真实CLI合成成功/失败、安装包入口及调用顺序；G1/G6 |
| M05 | 修传输/脱敏不逐provider重复改 | 误加重试、凭证外发、来源资格被统一丢掉 | endpoint/redirect/token/单位/日期负例及原adapter正例；G2 |
| M06 | 相同机械步骤共享，族内变化局部 | 来源预算/运行身份/失败保管丢失 | 每种producer对应输入→run→原件→reader链；没有来源调用的合成回放，真实运行另授权；G2 |
| M07 | 纯算法可离线复用且依赖可理解 | 将研究判断误作确定性算法，代码搬迁改变结果 | 各族确定性样本与拒绝集合、无网络导入边界；G1/G2 |
| M08 | 减少多用途条件和重复workflow维护 | 外部触发目标/产物资格/必要预筛改变 | 逐入口事件/权限/命令/消费者对账；活跃与人工用途未知不得删；G2/G4 |
| M09 | 运行恢复可解释且不依赖读面猜测 | 删旧状态、过期被追认、无法回退 | 三类恢复演练、checkpoint原件/有效性和容量；储存权威改变需Human裁定；G3 |
| M10 | 少量一致诊断能定位真实失败owner | 多义状态被压平、敏感错误正文泄漏 | 确定失败/未知效果/部分成功反例；任何异常不能自动算expected拒绝；G2/G3 |
| M11 | 历史恢复与当前写入解耦，降低格式维护 | 新policy增加永久分支，旧R索引重算改变 | raw/progress/commit/Odds+中文+旧拒绝+碰撞/库存回放；比较S1备选；G3 |
| M12 | 同一生产声明只改一个维护源 | 将用途索引变成授权、双配置分歧 | writer/消费者一一表、旧/新声明等价及用途差异；G2/G3 |
| M13 | 纯模块不再导入宽读面 | 根hash/输出bytes与历史兼容改变 | 对旧R/codec的精确回放；共享的是实现不是统一意义；G1/G3 |
| M14 | 新增reader不复制预算与回退代码 | 隔离失效、已用预算被回滚、可选模块吞基础结果 | 原预算与partial rollback负例、共享owner的真实调用者接线；G2/G6 |
| M15 | 发布机械逻辑有清楚owner | 不同ref retention/时钟被合并；未知写误报成功 | 候选读回失败/并发冲突/响应丢失；综合/News分离、同R正文；G3/G6 |
| M16 | 研究结果能稳定被产品找到并接续 | 资料发现=接受/持仓、补充更正遗漏 | 相同资料跨入口发现/更正/请求/已解决状态回放，真实Quick/Brief由原owner验证；G5 |
| M17 | 新视图不复制读取和权限判断 | app拆分只加转发层；旧页面失效 | 全client依赖、视图负例、真实浏览器/手机另列；不借Sites暂停跳过工程审查；G5 |
| M18 | host可更换而不携带个人凭证逻辑 | 读接口变写权限、跨源请求或owner绕过 | 原owner/CSP/同源/显式intent正反测试；未重验host不称已部署；G5 |
| M19 | 降低昂贵重复fixture和实现细节绑定 | 删掉不同消费者的同形保护；测试藏循环 | 义务→真实消费者→最小证明映射；原node身份变更逐条对应；G4/G6 |
| M20 | 减少永久CI机制和反馈成本 | 选测漏覆盖、环境漂移、把反馈当合并证明 | 完整集合/故障传播、full/main/发布资格前后对账；同范围成本比较；G4/G6 |
| M21 | 一处更新约束，少装无关依赖 | lock改变业务库、发行包漏数据、生产安装dev | 轻安装/完整工程/可选native/打包资源矩阵；工具试验需授权，依赖和许可另核；G6 |
| M22 | 新会话找到一个有效计划和当前合同 | 只挪文字但入口不可达；历史被改写 | 独立会话定位与后继读取；版本保留、无并行状态；G7 |
| M23 | 真正退出过期writer与兼容负担 | 无import但有人手动恢复；历史无法复算 | 精确CLI/workflow/人工/旧R/fixture检索与owner确认；未证零消费者则暂缓该删除；G4 |
| M24 | 旁支不进入领域依赖/核心安装成本 | 漏掉真实用户用途、资源路径/许可证失效 | 命令、打包资源、tests、third_party许可与人工使用定位；G1/G4/G6 |

M23中没有任何具体文件在本轮被证明可立即删除。KEEP同样不是免审；DEFER也不能用来把未审的大域隐藏出2.0范围。若主链归属、历史恢复或不可逆迁移仍UNKNOWN，相关设计不得进入实施采纳。

## 6. 全域测试、CI、依赖和文档设计

### 6.1 验证责任先于测试数量

将永久义务分为领域语义、边界格式/来源资格、用例/真实调用者传播、历史恢复、产品/host安全、打包与运行环境、独立接手。单元测试集中纯规则，contract测试核边界，integration核真实接线，少量端到端核完整用途；不把每个字段反例都升级为昂贵全链，也不能因已有unit test就删下游异常传播。

合成transport和真实历史输入分别标识。fixture应按所服务责任归属，共享builder放在测试支持位置，不让一个业务测试文件成为整个suite的隐形公共库。迁移pytest布局/导入模式前先核现有跨test imports；官方对新项目的importlib建议不是现有项目可直接切换的证明。[PYTEST]

### 6.2 CI实现本身进入审查

比较：当前四scope+严格merge reuse；更简单的完整执行路线；保留四种证明目的但减少重复安装/collection/聚合实现的路线。**目标不是预定必须保留四scope，也不是减少scope数量本身。** 当前规则在替代合同获准前不变。

先量化维护成本和作业成本，区分准备、collection、执行、汇合、artifact校验、main、publisher。退役失去义务的测试、收敛昂贵fixture、复用原生workflow/step，应先于自建影响分析/selector。任何后继完整验证都须说明实际执行集合、失败传播、代码/环境和发布资格如何建立；不能静默靠路径猜测省略有效回归。原GitHub reusable workflow适合job复用，composite action适合step复用，两者不能任意互换。[CI][GH-REUSE]

### 6.3 工具候选不是安装清单

| 能力 | 复用/备选及当前证据 | 采用前条件与不采用代价 |
|---|---|---|
| 依赖方向检查 | P2固定审阅的Import Linter 2.15；本轮补读官方Layers合同；备选现有明确pytest检查 | 在真实目标图上测合法/违规/例外及成本；未安装未试验。不同container内规则不自动禁止跨container反依赖，须显式补合同。静态图不能替代workflow/文件依赖。[P2][IL] |
| 环境锁定与分组 | 当前pip/setuptools+精确直接依赖；比较constraints/锁文件和uv | 本轮只读uv锁定/同步合同，未审安装包/全部许可依赖或运行；`--locked`检一致性与`--frozen`忽略锁新鲜度不同。不得默认工具替换已获准。[UV] |
| 自动化去重复 | 现有GitHub workflow_call、composite、actionlint、pytest split/xdist | 保持目的/身份/失败；不新增编排平台，不改变来源任务时钟。[GH-REUSE][P2] |
| 原件保管/恢复 | 原Git对象、create-only I/O、现有codec与archive | 同时比较保留旧reader和有界历史版本恢复；不能为少量旧样本维护整套旧执行系统，也不能只有过期URL。[P1][OLD] |
| 文档/ADR | 复用P2 MADR选项/后果/Confirmation及原Reconcile | 少量实际架构决策与任务触发入口；不建每文件规则registry，不混Human决定。[P2][PROTOCOL] |

每个新增依赖、框架或公共边界都必须列收益、维护/恢复/许可/安全成本和退出路径。未运行的候选不得写“通过”；本地联网失败不得当成自建理由。

### 6.4 文档与跨会话

维持AGENTS→任务入口→#297/#508→有效计划/最新回执→精确设计/PR。设计描述目标及原因，回执描述实际做到哪里；旧文件标记为历史候选而不篡改当时状态。P1/P2知识按实际议题消费，不每轮重读全部史料。目标变化必须同步当前导航，而不只埋评论。

迁移中每批保留目标矩阵ID、旧→新责任、原/后继入口、未解决项和唯一下一步。角色切换不构成独立审查；不同模型能接手不是模型标签口号，需要真实新上下文任务证据。

## 7. 完整渐进迁移路线

**以下为待采纳路线，不是已授权P4队列。** W编号表示工程目标批次，可拆成多张小PR；不是必须八张PR，也不预建八个空Issue。一次只推进一个主要2.0切片；每个切片须引用M行、目标合同和验收项。测试/文档/兼容更新跟随每批，不等最后补。

### 7.1 设计阶段的前置门

P3-R0：目标纠偏及版本/导航；P3-R1：第9节关键证据、全局调用/消费者和变更成本基线；P3-R2：将本文候选裁成可采纳目标及精确迁移范围；P3-R3：Human/适用owner采纳。R1/R2可以增量互相修正，但不能跳过关键UNKNOWN直接把草案交给P4。

### 7.2 实施目标批次及依赖

| 批次 | 覆盖与旧→新 | 依赖/复用 | 独立验收、回退与退出 |
|---|---|---|---|
| W1 冻结公共合同与保护样本 | M01–04/11/13/16/19；把外部支持行为、旧数据格式、内部实现分开 | P3采纳；复用现有typed/archive/CLI/失败样本，不新造业务资料 | 建立原行为基线和明确例外；无生产格式切换，回退不碰数据 |
| W2 共享原语与技术基础设施归位 | M01/05/10/13/14；拆读面通用工具、共享预算与I/O机械步骤 | W1；复用标准库、原Git/HTTP/文件实现 | 真实调用者接线与相同bytes/失败/预算；旧实现退出后删除过渡接头，不留双owner |
| W3 应用、producer、运行/恢复边界 | M04/06/08/09/10/12；按用例组织，workflow只承担明确执行/触发，状态owner与发布分开 | W1/W2及G2/G3；原生GitHub而非新scheduler | 不改变原时钟/请求；合格恢复/效果未知/并发反例；回退保留新旧已写格式的读取能力 |
| W4 观察与来源各族结构重组 | M05–07及D/财务/行业/News；纯计算、源资格、capture、读面分离 | W1/W2，受影响状态接口先满足W3；按族垂直迁移 | 每族来源→数值→最后消费者及拒绝；算法保持或另声明语义修正；逐族停切而非重跑来源 |
| W5 研究方法、档案、配置与历史合同 | M02/03/11/12/16/24；方法执行与历史解析、原件/意图/用途/接受分开 | W1/W2及G1/G3；旧S1仅是备选之一 | method可替换、旧包/旧R/中文完整恢复；新格式writer最后启用；回退不能退掉已发布格式reader |
| W6 读包、发布及Workbench产品接口 | M13–18；缩小Collector组合责任、统一机械发布、显式client/host边界 | 相关W3/W4/W5；旧S2及S3分别归入结构和血缘验证 | 综合R/News/Issue分开，同R正文与产品重入；CLI兼容；Sites不自动部署。未部署明确留原owner而非签线上完成 |
| W7 测试/CI/依赖/工程文档整合 | M19–22；义务归属、fixture、验证结构、环境声明及供应链整体优化 | W1起就量化，结构稳定部分可先做；不必等待W6全部结束 | 完整保护/失败/环境证据和可比成本；旧S4归此。新工具需显式试验/采纳，不“顺手升级” |
| W8 历史执行与过渡层退出 | M03/08/11/19/22/23/24；只对消费者已迁出的旧writer/入口/专属fixture结束责任 | 各相关W完成及G4；保留历史字节与必要codec | 查workflow/CLI/人工/旧R/包资源消费者；无遗漏才退出；有恢复入口及正常PR回退，不force历史 |

优先级依据是结构收益、真实变更频率、失败影响、兼容成本和依赖，而不是S1已经写得最详细。W4/W5可按依赖调整先后；W7贯穿，但不并行多批生产迁移。每次重排保留目标映射及理由，不把难域静默移出范围。

### 7.3 旧S1–S4的新地位

S1归W5/M11，重新比较旧映射、路径合同解耦与显式版本policy，连同新增持久兼容分支成本定案；S2归W2/W6，不再人为限制为两个helper；S3归W4/W6的血缘链族样本，不代表全血缘；S4归W7的依赖/发布策略，不代表供应链全部。可以保留、拆分、替换或改变顺序，均未获得开工授权。

### 7.4 每个实际切片的最小内容

记录：目标矩阵行/合同；精确旧→新；writer与全部直接消费者及已证下游；复用理由；实际文件/命令/格式；必须保留的行为和显式语义修正；正反测试；CI/恢复/成本；生产切换前置；回退和旧入口退出；新权限/依赖/费用有无授权。不固定测试/文件数，不建额外执行平台。

## 8. P5整体完工定义：不能用四个PR替代系统升级

### 8.1 必须同时满足的验收维度

| 验收 | 完成条件 | 不能替代它的证据 |
|---|---|---|
| A1 全域覆盖与处置 | 全部重要工程域有基于代码/消费者/原owner的决策；发现的新旁支纳入，核心UNKNOWN闭合 | 树清单、矩阵行数或“已经读P1/P2” |
| A2 目标结构真正成立 | 已采纳责任归属、依赖方向及公共入口在代码、workflow、包资源和产品中落实；受控例外明确 | 只创建目录、画图或增加Facade |
| A3 语义与历史兼容 | PIT、单位/时钟/来源、Evidence/Research/Odds/Human与旧包/档案恢复成立；改变语义单独获准 | 所有文件hash存在、CI绿或版本号2.0 |
| A4 运行/恢复/发布 | 三类恢复分别验证，未知效果先对账，合格状态与派生读面不互代；适用真实生产消费有证据 | 一次publisher成功或只恢复某个ZIP |
| A5 永久复杂度下降 | 已采纳整合/替换/退役清单有实际退出；代表变更任务显示维护责任与改动传播下降，新增保护代价单列 | 文件数/行数/测试数减少或把成本转进新平台 |
| A6 工程反馈与环境 | 可比环境/范围下CI、安装、collection、fixture、证据维护成本达成采纳目标或有明确获准的例外 | 拿content与full比较、单次耗时或假造稳定提速 |
| A7 产品和独立接手 | 新上下文能仅靠入口恢复计划/目标/证据，并完成代表性变更或恢复；产品读者可用且边界正确 | 同会话复述、换角色、CI、未部署界面或Human搬运材料 |
| A8 收口和剩余归属 | 实施目标已完成，过渡层实际退出；DEFER有理由/owner/风险/触发；Human裁定发布范围 | 把重要未审域都标DEFER或无限等零缺陷 |

### 8.2 成本基线与可检验成功标准

在任何结构性代码施工前，P3-R1应冻结代表性变更任务及其比较口径，不等看到结果再挑样本：

T1修改一个领域资格规则；T2替换一个研究方法的交付者而不改领域；T3为既有已保存来源增加一个读面用途（不增采集）；T4读取/演进档案格式并保持旧R；T5处理效果未知的运行/发布恢复；T6修订一个Workbench视图/host接口；T7更新一组工程依赖/验证规则。

每项记录：需要理解/修改的责任owner、跨模块接口、重复编码同一规则的位置、应维护的兼容分支、人工恢复步骤、测试/fixture准备及CI成本。只用代码/文档推演的样本标DESIGN-ESTIMATE；实际有界工程对照标MEASURED，不把模型思考时长/token当已知生产成本。

建议采纳门槛：全局审查覆盖全部重要域；每项已采纳结构目标完成；关键依赖/恢复违规无未处置项；代表任务中可比较的维护责任/跨边界改动有系统性下降而非仅一例变好，出现明显恶化须说明并获准；真正冗余的writer/兼容/重复实现退出，而非单纯迁址；可比工程验证成本不出现无解释回退。

具体数值阈值在G6完成基线后、P4前由Human/适用owner采纳。当前没有证据可承诺节省某个百分比，也不能把“成本有解释”变成所有结构都没改善仍算完成。若基线证明本建议没有整体收益，必须修改目标架构，而不是降低P5标准。

P1已有#799 full 613累计作业秒、main 34秒和publisher 138秒等历史样本，仍是起点，不是本轮测量或未来收益保证。按同用途、相同保护范围与可解释环境差异比较，不靠测试重新编号伪造瘦身。[P1]

## 9. 关键UNKNOWN、补证方式与采纳阻塞

| 门 | 尚缺的证据 | 本阶段怎样补，不重做P1/P2 | 阻塞范围 |
|---|---|---|---|
| G1 全局依赖与公共消费者 | 全source import闭包、动态import/CLI/workflow/包资源、方法与旁支的真正现役性 | 固定M取得全树和源码，原生搜索/可用静态工具结合关键调用链人工核对；给每个拟移模块列消费者/支持接口 | 精确拓扑迁移与旧路径退出；不阻止当前目标校准留存 |
| G2 producer/配置/资格链 | 每族writer/trigger/请求预算/原件/下游/失败owner完整映射 | 按源码、workflow、已有原run取证，不dispatch或新采；区分共用技术和源特有语义 | 采集/运行/配置重组，不因此取消其他独立设计 |
| G3 状态/档案/恢复 | 各状态权威、代表历史格式、容量/期限与拟迁移旧R反例 | 固定代表ref及原件，先只读；分档案/运行/发布；需要执行的回放另核权限 | 新格式/写入切换、不可逆迁移、替代恢复权威 |
| G4 生命周期/可退役项 | 精确历史writer/fixture/手工用途及原owner后继 | 复用#354/#626等实际退役结果，只核剩余候选；查命令/工作流/文档/原件恢复消费者 | 每一项删除或关闭；UNKNOWN不准自动判无消费者 |
| G5 全Workbench与研究—产品链 | client/server完整依赖、host合同、真实Quick/Brief和更正接续 | 先读全相关源码/原测试；复用原#351/#621证据，必要浏览器/真实消费按既有约束 | 产品接口定案及线上声明；Sites暂停不免工程审查 |
| G6 变更成本/测试义务/工具 | T1–T7基线、全fixture义务、环境重建与候选工具真实收益 | 既有PR/CI/collection和代码静态对照；对现成工具只在获准隔离环境做必要试验；不新装生产依赖 | 定量收益目标、测试/CI替代合同、新工具采纳 |
| G7 独立接手 | 真正新上下文是否找对有效版本并做对下一步 | 后继实际会话从#508恢复目标、原操作与证据，不靠Human贴结果；保留结果 | P5独立接手，不阻止目前文档交付 |

G1–G6是全局设计采纳前需要解决或明确裁定的关键差异，不是事后“边做边决定”的授权。可按域分批取证，但全域审查不能靠将一大片未审内容标DEFER完成。个别非核心增强可DEFER；需说明它为何不影响主要架构/恢复/成本目标及谁承担剩余风险。

本轮未完成以上全部门，因此**不能宣称这份v2已成为可直接施工的最终架构**。它已纠正设计范围并提出可评审目标，下一步是按这些门补证和裁定，而不是重开P1/P2或照旧开始S1。

## 10. Human仍需裁定的事项与当前交付边界

已经明确、不再重复询问：全面审查及必要结构性重构的目标；P1/P2复用；#803保留为候选；P4暂不开工；原领域/Human/来源/隐私/费用/时钟边界。

后续提交采纳时，需要带证据一次性裁定：C方案及各域A/B例外的目标拓扑；公共接口支持和历史reader保留策略；是否改变任何producer长期恢复权威/保管范围；定量变更成本及CI目标；Import Linter/锁定工具等是否作隔离试验并进入开发环境；完整迁移批次与产品部署范围。新来源/新费用/权限/经济语义不打包成默认同意。

当前没有批准新的具体删除名单、新字段`filename_policy_version`、依赖安装、源码迁移、生产启用或发行v2.0.0。旧S1兼容风险和回退教训继续作为反例，不代表其具体字段设计已采纳。

本轮仅规划、只读增量审查和工程文档/Issue留存。C固定2026-10-08/09/12/13/14自然验收、D原冻结/成熟结果及#351/#621/#581等责任继续独立；Sites暂停、禁Codex、分钟STOP、新城暂缓及AI Investment Authority=NONE保持。不同问题各有阻塞范围，不能用自然等待阻塞所有设计，也不能以2.0补签产品或投资效果。

**当前唯一下一工作：P3-R1的G1/G2全局依赖—消费者—状态owner证据补齐，并回写本v2矩阵及架构备选；随后完成G3–G6、形成精确采纳包。** 不重写主计划，不把本稿当P4授权，不请求Human逐文件确认；实际文档PR/CI/合并和剩余操作以#508最新回执为准。

## 11. 来源与证据使用范围

仓库链接固定M；旧成果固定其原版本。公共资料只用于所述机制/合同，不称已安装或运行；本轮未重新审阅P2全部上游。以下记录是设计证据索引，不是第二份状态数据库。

[OWNER]: https://github.com/auguspp/decision-kernel/issues/508
[PLAN11]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6095772144
[PLAN10]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6094482452
[OLD]: https://github.com/auguspp/decision-kernel/blob/9290df46052f823a96069932321ae50b016af65c/docs/kernel-2.0-design.md
[P1]: https://github.com/auguspp/decision-kernel/blob/97a4b14e287b04600841c1cc157c38a3cad0a781/docs/kernel-2.0-architecture-map.md
[P2]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/docs/kernel-2.0-prior-art.md
[PROTOCOL]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/WORKING-PROTOCOLS.md
[CURRENT]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/current_state.py
[RESERVE]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/institutional_radar_reading.py
[BASE]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/current_state_delivery.py
[COMPOSITION]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/current_state_delivery_with_odds_watch.py
[DREAD]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/d_price_structure_reading.py
[PERSIST]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/runtime/sector_radar_persistence.py
[METHOD]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/research_workflow_v1.py
[COMMIT]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/research_commit.py
[PACKAGE]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/pyproject.toml
[UI]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench/reading.mjs
[UI-TREE]: https://github.com/auguspp/decision-kernel/tree/4e9da1d037d6cefce0a7735ee74349666430a9bf/workbench
[SRC-TREE]: https://github.com/auguspp/decision-kernel/tree/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel
[XHS]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/src/decision_kernel/xiaohongshu_harness.py
[CI]: https://github.com/auguspp/decision-kernel/blob/4e9da1d037d6cefce0a7735ee74349666430a9bf/docs/CI-MAINLINE.md
[PYTEST]: https://docs.pytest.org/en/stable/explanation/goodpractices.html
[GH-REUSE]: https://docs.github.com/en/actions/concepts/workflows-and-actions/reusing-workflow-configurations
[IL]: https://import-linter.readthedocs.io/en/latest/contract_types/layers/
[UV]: https://docs.astral.sh/uv/concepts/projects/sync/
