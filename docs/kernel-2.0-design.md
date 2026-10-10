# Kernel 2.0 — 全局目标架构与渐进重构方案 v2.6

日期：2026-10-10（Asia/Singapore）。设计 ID：`K2-DESIGN-20261010-v2.6`。唯一计划、架构接续与实时状态入口：[#508][OWNER]。有效计划为[v1.3][PLAN13]、[v1.2][PLAN12]、[v1.1][PLAN11]及[v1.0][PLAN10]未替代条款；长期规则只从[统一项目原则][PRINCIPLES]读取。

**状态：P3 GLOBAL DESIGN PROPOSAL / 待审。** 普通设计文档交付和正常合并已获授权；具体能力、命名、拓扑、外部依赖、迁移和生产变更仍待相应采纳。K2-ADR-C/N/T均PROPOSED；P4/P5未启动。文档、CI、合并、技术采纳、实现、实际恢复与产品验收分别成立。

**版本关系：** 承接随#806合并的[v2.5精确前驱][V25]与[14交接][HANDOFF14]，本轮范围见[开始15][START15]。本版细化来源版本、scope扫描、限时执行、显式审阅和恢复环境的责任，并加入一项真实历史重放和一项真实拒绝。v2.5的E46–E51/18项控制函数证据、v2.4的E40–E45及v2.3的E21–E39/F01–F12完整代码证据与未验声明继续有效；其细节通过下表并入本设计，不因主文收敛而退役。M01–M24、W1–W8、A1–A8、T1–T7、G1–G7不改编号或全域范围。[P1][P1]、[P2][P2]与[Reuse附录][REUSE]不重做；[旧v1/#803][OLD]的默认S1→S4不复活。

| 精确前驱 | 本版继续消费的完整范围 |
|---|---|
| [v2.3][V23] | E21–E39、F01–F12、执行/状态与来源家族、Workbench声明图、原源码区间和未验消费者 |
| [v2.4][V24] | E40–E45、三类Odds、v2→v1/旧Deep与XHS、CLI/安装资源、原件保管和原子报告的区别、三ADR细节 |
| [v2.5][V25] | E46–E51、Smart发布→control反馈、Global各族合同、六行状态归属、原13个迁移样本、dlt状态层次比较及全部反例 |

## 1. 目标与当前推荐

Kernel 2.0覆盖整个工程体系的架构审查、必要目标重新设计与渐进式全面重构。“全面”是审查和决策范围，“渐进”是施工方式；不要求全部重写，也不能以四个局部补丁替代整体改善。最终降低维护、扩展、兼容、验证、恢复与接手的长期总成本。[PLAN11]

保护必要领域语义不等于保留现有拓扑。当前路径是迁移输入，不是当然终点；外部完整架构也须同台比较，不能先画自有目录再找背书。静态归属建议记DESIGN_ESTIMATE，真实执行证据只支持其实际范围，不把一次重放称为架构净收益MEASURED。

| 决策 | 当前明确推荐 | 推翻或采纳所需证据 |
|---|---|---|
| K2-ADR-C 能力与组合 | 用例声明必需/可选能力，合同跟随语义owner，实现在明确组合点提供；来源版本、扫描记忆、执行结果与接受分别建模 | 原生组合、成熟组件和完整外部架构按同一消费者/失败/退出成本比较；不是默认新建插件平台 |
| K2-ADR-N Naming & Identity | 按对象类别统一向前规则；机器身份、原Unicode名、显示名、存储路径、版本与时钟分开 | 公共合同/资源/历史原件与碰撞样本验证；不为整齐重算旧身份 |
| K2-ADR-T Topology & Ownership | 单仓单主要Python发行单元，六类代码责任域，应用内按能力组织；无全局万能contracts桶 | 全局采纳后才定施工路径；候选架构若实际接管更多责任且成本更低，可调整组织 |
| 恢复与迁移 | 原件存取、历史解释、兼容环境、生产续接分别确认；先旧reader可恢复，再切writer，最后退旧入口 | 不能用存在的ZIP、绿色任务或原版本号代签；已发布新格式必须有可行回退 |

固定边界：GitHub为正式代码/证据/过程后端；PIT、UNKNOWN、Evidence/Research/Odds/Human区分；保存失败、原件、方法版本和Human原话；AI Investment Authority=NONE。内部拓扑、接口、配置、状态表达、恢复实现、CI和依赖均可审查。现役合同在替代方案获准并验证前保持。

## 2. 本轮证据与设计影响

### 2.1 基线、实际读取和未执行范围

固定M=`986f70523ed9674e32db4f313bbd5a95ea39e3b0`，即#806合并；主设计前驱blob=`a82b8d6c039cba62e1872baed02d08fe597a71d3`。实时恢复AGENTS、NEXT/#297、#508顶部/14及相关统一原则，main开放PR查询为空。没有用旧聊天替代当前接点。本轮历史样本直接绑定其原run/commit/artifact，不消费生产综合R；如后续普通文档合并触发既有publisher，工程交付另列。

**新增完整审阅6份runtime源码，均完整UTF-8/Git blob核对及AST解析；不是全部下游闭包。**

| 文件 | 精确Git blob | 范围 |
|---|---|---|
| [radar_feed_intake.py][INTAKE] | `94e50d228d38c216e77d6a1ac96ee4c376080d12` | 33,511 bytes /516行；feed解析、版本推进、导出、捕获与重放 |
| [radar_feed_consumer.py][CONSUMER] | `bcdb4d01fda0fd41923e0346f1b65a1a65f67e8e` | 24,073 bytes /405行；scope回执、FIFO、执行历史和scan |
| [theme_plan_execution.py][PLAN-EXEC] | `f5f8dec8cd3d16db2c2a585ac9a1251ab3b7577e` | 14,259 bytes /237行；原计划期限、原件和执行重放 |
| [economic_release_discovery.py][DISCOVERY] | `5ff791f82a10833222c1518abaf87826d97ba97f` | 30,087 bytes /537行；目录、未审包、实现和运行环境绑定 |
| [economic_release_review.py][REVIEW] | `0defa63b347af8fc0db4591bca7b34949395a617` | 12,826 bytes /241行；精确包摘录接受、原时钟与重放 |
| [economic_node_study.py][NODE] | `0f6386118adedf77491f2078949a8b206e9addd0` | 13,172 bytes /233行；两个窄来源模板及描述性算术 |

新增局部读取[economic_market_context.py:75–231][ECON-CONTEXT]，blob=`d31093b7eecb222c5d4e4760c9b3ebe4dda461c1`：确认review验证、distinct period与原始取得时间、接受资格receipt进入实际产品消费者；不是全文件新审。反向搜索确认economic_release_inputs、economic_market_context及相应tests实际消费review；测试只读命中接点，没有称已完整阅读/运行这些tests。前驱economic_source_capture、identity、primitives及包初始化按相同blob复用，只为精确重放组装必要受信任源码。[RECOVERY15]

已读取[原native history工作流说明][HISTORY-DOC]、当前默认review目录及相关Actions历史。`radar_inputs/economic-reviewed-releases`在M只有空`.gitkeep`，仅表示该默认位置没有接受包，不表示全仓/其他ref从未接受。两个相关工作流查询分别返回10个和3个main run，并选下文两个精确样本；没有重跑旧任务。

本地Python3.13.5、pydantic2.13.5、BeautifulSoup4.14.3为预装环境。feedparser6.0.14本地未安装，因此RSS解析/完整consumer-history本轮没有执行，也未安装候选补齐。未运行source、model、生产恢复或候选状态框架。

### 2.2 新增E52–E57

| 证据 | 实际事实 | 对目标设计的影响与边界 |
|---|---|---|
| E52 intake完成不等于来源可被消费 | 两个完整RSS窗口共同推进append-only registry；初次只建baseline。所有post-baseline版本继续待处理，不限最新delta；模糊发布时间/当前多版本冲突仍阻导出。feedparser固定版本及source policy参与兼容 | 来源codec/版本账的owner必须独立于传输；换parser不是仅换HTTP。明确批次也不能绕过全局语义缺口；不从RSS补造时区或把description当全文。[INTAKE] |
| E53 扫描完成与市场执行是两件事 | consumer scope包括matcher/consumer版本、catalog、industries和source policy；仅同scope已验证scan抑制重复。FIFO在匹配前选前缀，大首项超预算不能跳过挑后项。只有成功执行才清对应旧plan，quiet scan可仍有outstanding plans | 一个processed标记或max cursor不足；作用域变更可合理重扫，但不能重置源初见时钟。独立receipt不认证提供了全部历史；多份完整原件复制计物理预算。[CONSUMER] |
| E54 恢复旧计划不刷新执行资格 | `theme_plan_execution`核原scan/plan，30分钟有效期在请求前校验；verify按原started_at和原raw重建，失败包不拥有成功结果 | 历史codec保留与现役producer退役分开；恢复结果不能获得“现在再执行一次”的权限。旧失败plan可保留为失败，不当新计划自动重试。[PLAN-EXEC] |
| E55 审阅资格晚于来源取得，且可局部成立 | review选择精确pending packet而不要求整个发现扫描成功；保留原source_scan_status。eligible_from取记录时间，reviewer为DECLARED_NOT_AUTHENTICATED。实际context验证接受截止并保管receipt，不把重新抓取同一期当新发布 | source-review是单独用例合同，不是来源真假或Human投资认证；可读原件、可用观察和已审用途资格分开。单项合法接受不能给全目录补签完整覆盖。[DISCOVERY][REVIEW][ECON-CONTEXT] |
| E56 原件完好仍可能无法在当前环境重放 | 正样本四份原件完整重建；负样本manifest/全文件/四份源码指纹相等，但Python3.12.14→3.13.5触发严格parser_runtime拒绝 | 把兼容环境供应与历史解释纳入恢复责任；不能只保存code commit或删版本检查后宣布可恢复。具体证据和方案见§2.3/§3.6。[RECOVERY15] |
| E57 依赖更新也是可能的来源执行面 | economic-source-capture的workflow路径在push触发器内；#624 Action更新合并实际触发36526584715，并取得下文原件 | CI/依赖/改名计划必须审diff→触发→外部效果；不是只关注runtime算法。此为历史事实，不授权现在再采集或顺手退役现役触发器。[CAPTURE-WF][ACTION-RUN] |

### 2.3 两个真实保存样本与拒绝反例

完整原脚本、实际JSON输出、受信任源码pin、ZIP检查方法和未验声明均已保存并读回[本轮恢复证据][RECOVERY15]。脚本8119 bytes，SHA256=`45b7c2c453ef92db12afd7ee70577db0a7edbc207b924a7ace3d6b4528495219`；输出4480 bytes，SHA256=`0e42583bb824f9ba5921ef133dc4121ff300d6fc2b198b615be714aeb93f218a`。网络/socket和子进程入口禁止，实际尝试0；ZIP只作为数据，未执行其内代码。

| 精确输入 | 实际检查结果 | 不代表什么 |
|---|---|---|
| [36526584715/1][ACTION-RUN]，原代码`18c09e6e1e8ca86636e04784916bcba5b3a700af`；artifact11014198805，67,711 bytes，SHA256=`58662259288dbab6dfc08a62bdeae768fc36503fa29346393f05872c2325edb1` | 服务器digest/size、CRC、路径/库存及workflow身份核对；28文件/253,470展开bytes。未修改的当前`economic_source_capture.verify_capture`完整重建四份原件的文本绑定/观察/summary，结果等于原verification.json；capture_hash=`a8c7f008e0ee457894985cb8df131578635e81e0aac922fd20a0b314ebb12217` | 一项真实历史离线重放，不是新source-review、今日数据、来源认证、全G3或生产恢复；原artifact expires_at=2026-12-28T05:31:40Z，不承诺永久可下载 |
| [33996480270/1][FAILED-RUN]，原代码`f0a667a4e569584b511bf16f151772a38492e700`；artifact9978205420，14,277 bytes，SHA256=`2900b96da465deda883ee123a0c9f61b021e08adff0c8e3181f97b3426e2d64f` | 13文件/48,517展开bytes，manifest与全部文件相符，四个implementation指纹与当前相等。原parser_runtime为BS4 4.14.3/html.parser/Python3.12.14，当前Python3.13.5；原验证器返回`archive identity/hash/implementation differs`，没有放宽 | 字节保管成立、当前环境完整语义重放未通过。原INCOMPLETE_SCAN和2026-09-05历史HTTP403/no-body仍保留；不是现在访问被拒或今日来源故障。expires_at=2026-12-04T22:38:12Z |

正样本五份独立临时副本分别改raw body、派生observation、summary、删除binding、增加文件，均由原验证器拒绝；随后原正样本再次通过。合计8项预期检查成立，**其中“负样本拒绝符合预期”不是负样本恢复成功**。没有执行原整套测试、RSS云端续接或经济review真实接受；没有成本降低实测。

### 2.4 前驱约束继续保护

事件机会≠合格数据：Sector完成只给某些日常入口机会，TDX仍需success/result-bearing；旧公告自动边要求scheduled Inbox而当前Inbox为manual。job/step/title、path push与runpy sibling有实际消费者。#581记忆不能因后一天成功删除旧未交付；未知dispatch先对账，已花API预算不随候选回退。[V23]

三类Odds资格不可互换；v2仍依赖v1，XHS/旧Deep/Retainer/历史脚本是真实消费者；原件先存后验与原子报告是不同失败合同。Concept和economic宽实现指纹影响历史解释。旧R按自己的registry/policy解释，不全局放宽后追认旧拒绝；Unicode原名/hash/库存不重写。[V24][V25]

Smart专用进度确实由R交付给control，但整个R不因此成为通用restore authority。Global公共族no-retry与Relay特许第二attempt不同；原精确token为`REQUEST_RECEIPT_UNAVAILABLE`，不能当0请求。Workbench的固定R、News live、Issue观察时钟，重读/#601追加/dispatch三类效果，迟到/跨R/坏原文拒绝、host身份边缘和useLabel参与记录hash均继续保护。[V23][V25]

## 3. K2-ADR-C：能力合同与组合

**PROPOSED。** 目标是变化只传播到该能力及合理组合点，而不是给每个函数新建接口或把旧复杂性包装进Facade。合同属于语义owner；状态、预算、外部效果和历史支持是合同的一部分。

### 3.1 实现来源同台比较

| 方案 | 可以接管 | 必须计入的剩余成本与证据 |
|---|---|---|
| 现有函数/构造注入＋GitHub原生组合 | 已证明确定性代码、workflow_call/composite、Git/pytest | 宽CLI/Collector与跨业务私有工具仍需收敛；熟悉或已投入不是胜出证据 |
| 六责任域内部重组 | 领域、方法、用例、机械I/O有明确owner | 实现继续自养，必须用T1–T7证明净收益；不能仅加空包/转发 |
| pluggy选定hook组件 | 固定1.6.0 register/add_hookspecs/unregister可承担真实1:N扩展点 | 前驱只审manager局部；注册先写映射后验hook，不假定事务式清理。顺序/失败/退出、完整测试/依赖许可与运行仍待核。[V24] |
| Kedro/Hamilton/dlt组件或完整架构 | 数据目录、纯函数图、REST分页及状态等已有真实入口 | 资源复制、原件/失败资格、Git完成权威、配置、升级退出需适配；不能以不同语言/包装或非100%贴合排除，也不据README采纳。[REUSE][V25] |
| DeepSeek Harness/Cordis等能力组装 | 原需求给出的能力定义/提供方/消费者/生命周期对照 | 完整实现与净成本尚未独立核验，不宣布只能借理念，也不宣告可替代全部Kernel；不阻无依赖的命名设计。[MOD-REQ] |

推荐以稳定合同和显式组合作为设计基线，具体实现逐能力裁定；真实动态启停/1:N需求才评估注册器。完整外部架构可以改变总体组织，六目录不是它的先验限制。非独特自建责任必须检查直接采用、配置、CLI/进程、薄适配与有限patch；本稿不宣告新插件/状态/调度平台NEW_BUILD_JUSTIFIED。

### 3.2 定义、提供者、消费者与缺席

| 能力/M归属 | 定义与提供/消费关系 | 必需/可选、owner与替换界限 |
|---|---|---|
| 研究提交 M01–03/11 | method-agnostic ResearchCommitPackage→commit→live/离线保管 | snapshot/Evidence精确绑定；仅离线schema2可无framing/数值准备；方法adapter在methods，不造Pre/Quick，不改旧hash/继承Human接受 |
| canonical Odds M02/04 | 原政策/概率/ObservedMarket→算术/Odds→spine | 合格数值研究与Market必需；context可选且原缺省不变；同证券/单位/复权/时钟/来源逐项对照，context price不冒充Market |
| provisional/conditional M02/11 | 独立结果合同→各原实现→Human分析/retention | HumanPriceContext必需；前者仍需分布，后者允许概率未知；可共用payoff/序列化，不用开关静默互转 |
| 来源捕获 M05–10 | 特定provider/channel/对象/窗口→transport/parser→producer/reader | 授权、预算、raw custody在具体用例；必需失败阻动作，可选缺席不抹基础结果；request/capture/qualify分离，同JSON不证明同资格 |
| 研究执行/pair M03/09/16 | 方法input/result/receipt→现役host→identity/admission/产品 | 当前执行与历史codec分开；预算/执行pair/消费记忆有owner；动态import也是消费者，旧结果不授权新执行 |
| 保管/恢复 M11/15/21 | raw/progress/commit/Odds→Git/local及版本化reader→历史/比较CLI | 精确pin/库存必需；原件先存后验、原子报告和环境兼容不同合同；共享机械I/O，不共用万能save/restore，见§3.6 |
| 保存读包/可选观察 M09/13–16 | 受支持descriptor→各reader/纯算法→publisher/研究/Workbench | calls预算及candidate files各唯一owner；D/补充失败保价格/研究；已花calls不rollback，不deepcopy client/secret/共享预算 |
| 展示/显式请求 M16–18/24 | fixed-R阅读、#601追加、News刷新、写作brief→Workbench/XHS→Human | host权限与请求独立；XHS仅选定声明、Human状态OMIT；换视图不改身份，停producer不删reader，不自动上线/发文/Watch |

缺必需能力只阻依赖动作；可选缺席、技术失败、资格失败、业务quiet/WAIT/STOP不能统一成空数组或成功。共享凭证不是一个可以自由卸载又隐含授权的插件。端口与含执行逻辑的实现分文件，避免application/infrastructure循环；不藏进全局service locator。

### 3.3 四类退出

| 退出 | 处置 | 证明与保留 |
|---|---|---|
| 运行时停用 | 停未来构造/注册/触发，标出缺席；先对账在途 | 无关功能可用，旧结果保原日期；停UI不等于停生产，反之亦然 |
| provider替换 | 组合点替换，逐项对照请求/数值/时钟/权限/失败及状态兼容 | 同合同正反例；旧记录不改来源或继承接受 |
| 旧执行入口退役 | 核manual/CLI/workflow/job/step/path-push/外部clock，退专属触发/权限/fixture | 共享义务和必要历史reader保留；不能按旧名删除Retainer/v1/XHS |
| 历史reader退役 | 等价恢复、支持期与适用采纳成立才退旧codec/别名 | 原bytes/失败/Human/方法解释可恢复；不要求旧producer永久活着 |

解绑hook不撤销HTTP/Git写入或预算，不授予自动cancel/retry。四种退出沿T2–T6/A2–A4/A7验证，不新建插件验收平台。

### 3.4 状态与发布反馈：具体owner

备选A继续把不同状态隐含放在view/control/reader；B统一迁入pipeline state；C先明确下表各owner和合同，机械存取可以复用外部实现。**当前推荐C，仍PROPOSED。** A继续隐藏消费者；B须实际证明资格、失败与Git权威等价后才采用；C的小端口/兼容成本同样计入G6，不预先排除B更省成本。

| 对象/实际链 | 建议owner与组合 | 不可混淆的迁移条件 |
|---|---|---|
| Smart交付进度：capture→view.state→reading→control | `application/smart_money/progress.py`纯推进；reading保管/定位，control经窄读取端口取精确state；首批继续原R/state路径 | 完成/未完成集合、枚举水位、日历缺口、source id分开；显示失败不清进度；停publisher影响control须验证，不能赋整个R恢复权威 |
| Smart准入/账户使用/待发布捕获 | 同能力control保原判定，workflow薄调用，activity查询借机械接口 | 调用机会≠Relay实际启动；换head/job名不清预算；未读入旧raw先对账，unknown历史/权限仍拒绝 |
| Global单次attempt与日期资格 | application执行/保管，observations拥有纯plan/codec/数值，HTTP助手归infrastructure | Relay第二attempt≠公共no-retry；无回执≠未请求；v1/v2参考日期、UTC日桶、期货换月原解释保持 |
| RSS版本registry/初见与appearance | 来源codec拥有版本/时间语义，`application/economic_feed/`组合；不是配置或下游已处理账 | 双窗口共同推进；baseline/successor互斥，post-baseline pending不局限最新delta；parser/source policy迁移须旧reader，模糊时区仍拒绝消费 |
| native-feed扫描与market execution历史 | `application/native_feed/`分scope扫描账、精确plan执行账；source/market/history各独立locator | 同scope才抑制已scan；FIFO在matching前；quiet可带旧失败plan。成功execution仅关闭自身，不替代source-delivery/Human接受；旧plan期限不刷新 |
| economic声明/seed/派生输入 | 声明与受审source原件仍归原owner；`application/economic_inputs/`组装，纯模板/比较归observations | 目录名不选最新接受；同URL冲突、max日期后旧未审backlog、原implementation指纹保留；不是把所有JSON移config |
| economic显式review及用途资格 | 同economic输入用例拥有review/acceptance合同；context必须连receipt消费，原件独立保管 | acquired/reviewed/recorded/eligible_from分开；局部接受不改整体INCOMPLETE，声明reviewer不升级为身份认证；不导出缺接受资格的“已审”裸观察 |

RSS scope中的catalog/matcher版本变化可能使扫描需重做，不能等同源数据重新出现；两catalog查询是原manual执行成本，不在本轮离线验证发生。复制原RSS到scan、execution、history的实际物理字节都受32MiB总量/64对象每类约束，不能仅按逻辑记录数估算可保存多久。容量/期限到达须明确归档迁移，不自动prune或重置。[CONSUMER][HISTORY-DOC]

### 3.5 Reuse：解析、传输和状态各按接管层次比较

本轮直接复用已采用的feedparser/BeautifulSoup及原GitHub/原离线验证器，不新写解析器或恢复框架。保持v2.5固定dlt1.31.0/`2360d229c77f7f64692acc31a4555f4cfcd50ed3`的RESTClient与自定义state比较：它可处理资源私有/来源共享字典和对象集合，不限max cursor；destination原子提交不能未经适配视作Kernel原件/执行/发布全部完成。[V25][REUSE]

| 接管范围 | 可比较的实现 | Kernel仍需保持和实测的责任 |
|---|---|---|
| RSS/HTML解释 | 当前feedparser6.0.14、BS4 4.14.3及其既有边界 | 原bytes、严格pubDate/链接、source-policy、旧parser/runtime与失败；不能采用宽松纠正后追认旧证据 |
| REST/分页/会话 | 当前Requests/urllib；固定dlt RESTClient＋显式session | no-redirect、每族retry与body权利/预算、null/空/缺列；不能继承默认429/5xx重试替换现役合同 |
| 分区/对象/消费state | 当前精确Git/artifact＋明确owner；dlt资源/自定义state | 未完成集合、初见时钟、scope扫描与执行区分、未发布raw、无回执、失败原件；init/refresh不清旧账或重放已耗calls |
| 工作流和机械接线 | 原生workflow_call/composite，可与上述组合 | job/step/title/runpy/path-push外部消费者；Action升级也可能触发source；全过程更新/退出成本一起计 |

共同反例继续T3/T5/T7：新日期成功但旧分区未完成；raw未读入；同日跨head已用Relay；null与空表；无回执；失败但可重放market执行；旧registry初见；只停视图而未停control。新增同scope/换scope扫描、超大FIFO首项、旧plan过期和实际runtime不符。lag可以用于有证明窗口，不能据有限回看宣称任意旧缺口已补全。

本版未新增外部候选能力或安装；复用前驱相同候选/用途/约束的固定审阅，不重做全上游。完整state采用仍需同输入隔离试验、许可/依赖、实际提交失败/退出和净成本；DeepSeek Harness/Cordis及其他可行完整架构未审部分仍列G6，不能因此默认自建胜出。

### 3.6 恢复能力：原件、reader、环境与续接四项合同

E56表明“代码没改＋原件完好”仍不是当前环境可重放的充分条件。**建议每个需长期恢复的格式明确：原始对象库存与合法存放位置；受信任历史解释实现及其依赖/环境；可支持时间和容量；验证结果可用于什么后继动作。** 这应写在格式owner/现有保管记录里，不新建全局环境注册库或自动下载执行历史代码。

| 方案 | 优点 | 代价/选择条件 |
|---|---|---|
| 保留原受信任reader及精确原运行环境 | 最直接保持现有严格解释；不先改语义 | 获取/保管/安全维护多个环境有成本，旧包仍可能失效；本轮没有取得Python3.12.14或完成该方案试验 |
| 经审查的版本化兼容reader | 有望减少长期环境数量和宽文件指纹耦合 | 必须用原成功/失败/原件/时钟样本证明等价，并明确仅覆盖的版本对；不能全局去掉runtime/hash检查 |
| 只保原件和已生成报告，停止可执行恢复承诺 | 维护成本可能更低 | 会降低当前恢复承诺，依赖它的producer/档案/接受用途不能继续使用；须明确范围变更和owner采纳，不能静默作为默认 |

当前推荐前两项按格式组合评估：必要的原reader/环境在等价兼容证据成立前保留，新reader最后才可替代；不要求所有历史永远安装同一套环境，也不预先承诺整个仓库跨Python重放。机械环境构建优先现成工具，具体依赖/环境安装另按授权；本轮只测预装环境，无新实现或许可结论。

旧原件的implementation/parser_runtime/hash保持原值；新格式可以考虑把兼容边界收敛到真实解释闭包，但须先取得闭包/历史反例与成本证据。失败重建仍失败，旧plan重放按旧时钟验证不使其今日可执行。库的安装成功或一次CI绿不证明所有原环境已可恢复。

正样本证明某一旧格式在当前环境可完整重放，负样本证明另一格式当前仍被拒绝。两者共同改变G3从“尚无本轮真实样本”到“有明确有界正反证”，不关闭全域G3，不给生产恢复或格式迁移授权。

## 4. K2-ADR-N：Naming & Identity

**PROPOSED。** 备选A保留全部混合惯例；B一律英文化/同一分隔符；C按对象统一向前规则并显式兼容。推荐C：A不降新增决策负担，B破坏真实公共/历史合同；C仍需原样本验证。完整背景、CONS-09/10、Python/Packaging正式惯例及Unicode要求由[v2.4][V24]与[v2.5][V25]§4并入，不重开已明确原则。

| 对象 | 新规则建议 | 禁止的误统一 |
|---|---|---|
| 分发包/导入/命令 | 保持`decision-kernel`分发/命令与`decision_kernel`导入 | Kernel2.0不自动变包2.0.0，不为同拼写破公共入口 |
| Python | 新模块snake_case、类CapWords、函数/字段snake_case，原稳定状态token保持 | 不批改序列化字段/enum；不让旧research.py与新同名包竞争 |
| JS/workflow/文档 | 现有ES模块kebab-case、出口camelCase；职责性workflow/文档名；约定README/AGENTS保留 | 不跨语言强统一；job/step/title/path可能是接口和触发面 |
| 机器身份 | 各对象保原UUID/hash/证券/source规则；新人工slug默认小写ASCII | 不拿title/公司名/路径当永久ID，不造全域正则追验所有旧对象 |
| 原名/显示/路径 | 原Unicode名称和bytes精确保留；新机器目录默认ASCII，显示可中文，URL逐段转义 | 不静默NFC/NFKC规范化或合并碰撞，不以新路径同sha代替原来历 |
| 来源/资产名 | logical security、provider code、transport/channel/tool和证据出处分开 | 工具不自动是经济证据源，TDX和其他概念同名不合并 |
| 版本 | schema/方法/算法/研究revision/软件独立；_v1可仍是受支持合同 | 不全改v2、不删v1表示升级，不重算历史information/package hash |
| 时间 | 日期YYYY-MM-DD，timestamp有时区；session/发布/可得/取得/接受/计算/显示分开 | 不补RSS时区，不拿运行/目录/重放时钟替代原日期或eligibility |
| 格式内文件 | result.json/retention.json按各格式固定库存；raw hash与语义hash分开 | 不因同名文件合并对象；外层归属变更不改内层原字节 |

路径安全拒绝越界/绝对路径/分隔符和实际危险控制字符；新writer检查目标文件系统的规范化、大小写及保留名碰撞，并保原名映射。具体策略随旧reader支持范围裁定，不伪装通用跨平台规则已实现。核机器ID/中文原名/显示、至少两组规范化碰撞、旧R数量/拒绝、CLI/资源、workflow身份；新schema先reader后writer。不得用全仓风格门禁替代这些证据。

## 5. K2-ADR-T：Topology & Ownership

**PROPOSED。** 比较当前顶层领域＋宽runtime、前稿七个全局分类桶、六责任域＋能力内owner。推荐后者作为待验证结构；仍可由更低成本的完整外部架构调整。路径表达责任，不是六层嵌套或每能力六套空目录。

### 5.1 代码目标与依赖

```text
src/decision_kernel/
  domain/          身份、PIT、研究/市场值、算术和权限不变量
  methods/         可替换研究方法、质量/source-role政策及旧方法合同
  observations/    各来源族纯转换、模板/codec与计算
  application/     按研究交付、来源、消费、reading、publication等用例组织
  infrastructure/  受约束的GitHub、HTTP、本地文件和环境技术实现
  interfaces/      CLI、宿主入口与显式composition
workbench/         原前后端产品边界
.github/           原生workflow/action、薄调用与工程辅助
```

domain不反依其他域；methods/observations依赖所需domain而不借publisher。application依赖领域/方法/观察和窄端口；infrastructure可依窄合同，不能反依包含执行的用例模块。interfaces连接应用和具体实现，tests可组合但业务不依赖tests。合同跟随语义owner，无独立万能contracts包；只有真实多owner稳定类型才共享。

旧public Python路径、console command和安装资源须有有限兼容方案和退出条件；不强制所有私有import永久稳定。没有消费者且历史恢复等价的转发要真正退出，不永久双轨。原native资源与entry-point机制优先复用，Import Linter等按P2实际候选和成本裁定，不提前加永久门禁。[V24][V25]

### 5.2 永久对象的默认归属

路径全为目标建议，未创建或迁移。每对象一个语义/写入owner；同一证券的不同用途不是一个“大公司文件夹”。

| 对象 | 默认位置/owner建议 | 可变性、消费者与迁移边界 |
|---|---|---|
| 核心代码/机械实现 | src责任域，各模块owner | 经PR演进，公共接口/历史解释另核；不为框架重写确定性算术 |
| 当前配置/声明 | `config/<owning-capability>/` | PR变更，producer/reader双端迁移；读用途例`config/reading/purposes.json`，旧R仍识别原registry路径 |
| 执行请求/消费记忆 | 原请求路径/work-ref为迁移输入，具体host/use-case定目标 | 请求≠完成；path push/external trigger先核；不一律搬config或再消费 |
| 方法/操作文档 | `docs/methods/`，RESEARCH-ENTRY导航 | 方法版本独立，原案例/Human/历史正文精确可达 |
| 人读研究/底稿 | 新同类`docs/readings/<record-id>/`，研究保管owner | create-only/追加或新revision；旧research_runs/docs不批迁，非typed COMMITTED |
| typed progress/Research/Odds | 新档案`research_runs/archives/<record-id>/<revision>/`，格式owner | 内层原文件/库存/bytes，三种对象分开；旧candidates/execution packet继续历史支持 |
| 来源原件/提取表示 | 原获准artifact/Git位置，source custody owner | raw/文本/metadata权利独立，不默认全部公开；期限/恢复环境见§3.6 |
| producer运行状态 | 原state bundle/work-ref及明确进度用例owner | Sector不由综合R替代；Smart专用state仍原R交付；RSS源/scan/execution分账，失败/前驱不清 |
| Human判断/接受 | 原`docs/decisions/`及具名Human记录 | AI草稿/工程ADR不混入，不继承接受或批改原话 |
| 派生读包/快缓存 | 原current-state/news-live等指定ref，原publisher | 展示和control进度分别标识；同ref不统一权威；ref时钟/force合同保留 |
| 健康/项目进度 | #581健康，#508本项目接续，#297路由 | 不同Issue owner，报告记忆不是无状态页面，不复制新状态库 |
| tests/fixture/eval | 逐批`tests/<owning-capability>/`，eval独立 | cross-test import、collection身份/分片先对账；旧fixture保解释义务，不能塞循环伪降数量 |
| 工程指南/ADR | AGENTS/README路由WORKING-PROTOCOLS，本文件三ADR | Git前驱保旧决定；不另建实时ADR审批系统或第三套原则 |
| 第三方代码/资源 | 原third_party/所属能力package resources | 原许可/NOTICE/来历和更新退出；Odds政策与写作样式虽同目录但不同owner；loader/package-data一起验 |

配置不装运行registry或原件；历史环境/reader支持写在格式owner已有记录，不借此建新的万能archive或environment平台。新配置默认位置和公共支持范围仍须全局采纳，不留到施工时随意决定。

## 6. 全域M01–M24处置矩阵

KEEP/CONSOLIDATE/REPLACE/RETIRE/DEFER均为建议，不是实际操作。UNKNOWN不等于没有消费者。完整先前问题/消费者/源码范围由[V23]–[V25]并入；以下保持每项责任、净收益假设和验证，不用缩写取消其旧义务。

| ID/责任 | 当前问题与消费者 | 建议/收益假设 | 兼容风险与必要验证 |
|---|---|---|---|
| M01 身份/PIT/权限 | 类型与读面工具混居；commit/方法/reader消费 | KEEP语义、CONSOLIDATE同义原语 | 不混hash/编码/时区；原bytes和拒绝，G1/G3 |
| M02 Market/Odds/算术 | 三类Odds资格不同；spine/Human/retention消费 | KEEP原义、CONSOLIDATE合理算术归属 | 分布/单位/context/UNKNOWN/时钟不可互换，G1/G3 |
| M03 方法/旧合同/模型 | v2依赖v1，Quick/Deep共享receipt；host/archive/XHS消费 | REPLACE错位组织、KEEP必要旧codec | 原方法hash/解释/预算/接受，T2/G1/G3 |
| M04 CLI/live | 五命令宽导入；console/workflow/shell消费 | REPLACE为薄CLI与用例，按命令构造依赖 | 参数/退出码/输出/仓库外资源，无权不执行，T1/T7 |
| M05 adapter/transport | Global借Smart/economic，RSS/HTML parser有版本资格 | CONSOLIDATE同义机械I/O，KEEP来源语义；比较成熟组件 | retry/redirect/credential/body/单位/时钟不可通用缺省覆盖，E48/E52/G2/G6 |
| M06 capture/producer | 枚举/完成分区、RSS窗口/registry和单次attempt不同 | REPLACE边界，CONSOLIDATE机械步骤 | 不把请求时间当覆盖，双窗口/全局语义gaps/无回执保留，G2/G3 |
| M07 纯观察/计算 | 纯函数反依宽runtime；producer/UI消费 | REPLACE错向依赖，比较既有/Hamilton等 | 原算法/失败、无网络、适配成本；node窄模板不是通用产业引擎，T3/G6 |
| M08 workflow/资格 | job/step/title/path/runpy及外部trigger有消费者 | CONSOLIDATE原生复用；RETIRE仅确无义务旧边 | Action升级也可取源；拆job不清预算/旧raw，E47/E57/G2/G4 |
| M09 状态/恢复 | Sector强state、Smart反馈、RSS源/scan/execution各异 | KEEP必要差异，REPLACE错位owner，CONSOLIDATE存取 | scope变更≠新source，quiet≠无旧plan；不能统一cursor/empty reset，E52–54/G3 |
| M10 失败/健康记忆 | #581旧gap、Smart待发布、未知receipt、失败执行 | CONSOLIDATE同义诊断，KEEP准入/保管/报告区别 | 未发送≠未知，失败保存≠成功消费；原日期/预算/前驱，T5/G3 |
| M11 档案/历史codec | 宽implementation/parser_runtime绑定，旧库存和Unicode | CONSOLIDATE保管，REPLACE过宽回放闭包 | 一项真实恢复通过不覆盖另一实际环境拒绝；reader/环境/原件分别保，E56/T4/G3 |
| M12 配置/registry | 声明、运行registry、review bundle含不同权威 | REPLACE重复维护，KEEP对象区别 | 不按JSON后缀搬config；source-review eligibility和旧R双端支持，E55 |
| M13 读包/通用工具 | current_state兼原语，文案参与身份；前后端消费 | REPLACE错位归属，窄合同 | 单文件认证≠根hash，显示/记录版本分开，G1/G3/G5 |
| M14 Collector/预算 | 跨业务reserve、共享client/files | CONSOLIDATE资源owner，REPLACE借私有模块 | deepcopy/assign、calls不可回滚、可选失败隔离，T3/G6 |
| M15 Git/本地发布 | 原件custody/原子报告/News/综合R不同，Smart反馈 | CONSOLIDATE机械I/O，KEEP各完成合同 | upload-ready≠上传，未发布不重采，显示失败不抹进度，T5/G3 |
| M16 研究→产品/重入 | registry/work-ref/#601/Brief多入口 | CONSOLIDATE资产/请求导航，可发现更正 | 保存≠研究完成/接受/持仓；真实Quick→Brief与原时钟，G5 |
| M17 Workbench client | 前驱14client已核，迟到/跨R/原文保全 | CONSOLIDATE读取/展示，外部框架仍比较 | 原生或等价机制，全tests/browser/手机/成本，G5/G6 |
| M18 server/host | 5server与共享依赖，owner/token/permit/固定ref | KEEP读写隔离，CONSOLIDATEhost窄合同 | 可信边缘/无旁路/凭证轮换；暂停不免审、不擅部署，G5 |
| M19 tests/fixture/eval | 重复与跨test import，历史/字段/消费者义务不同 | CONSOLIDATE必要fixture，RETIRE真正失去义务项 | 原collection/失败传播/历史环境反例；研究质量与CI分开，G4/G6 |
| M20 CI/自动化 | 四scope/分片/环境/证据已有成本 | CONSOLIDATE重复实现，比较简化完整执行 | 同范围实测，不先放宽现役full/reuse，G6 |
| M21 依赖/打包/供应链 | extras/dev约束、资源与历史runtime | CONSOLIDATE维护源，复用包装/环境工具 | 当前安装≠旧解释环境；环境保管/兼容/许可/升级退出成本，E56/T7/G6 |
| M22 文档/治理/接手 | 统一原则已交付，长证据与旧NEXT易混 | CONSOLIDATE当前决定/精确证据路由，RETIRE旧指针 | 不删失败/原话；真新上下文，不自换角色，G7 |
| M23 one-shot/兼容/退出 | 旧名仍有Retainer/CLI/手工/历史脚本消费者 | RETIRE精确无义务入口，KEEP必要reader | 无import/年久不证可删；原plan不能复活，配套fixture/config同处置，G4 |
| M24 XHS/third_party | 旧Deep、voice/harness与style资源被消费 | CONSOLIDATE外围authoring；DEFER新增启用而非审查 | 原选定声明/OMIT/旧输入与输出、人工用途/许可资源仍核，G1/G4/G6 |

没有证据允许立即删除整块目录或全部旧合同。KEEP也需依据；重要UNKNOWN不能全部转DEFER来签A1。E22旧自动边是候选，E41/E45/E53是保留真实消费者/历史义务的反例。

## 7. 旧→新映射与恢复顺序

全表为**DESIGN_ESTIMATE / NOT MIGRATED**。路径要以K2-ADR-T采纳为前提，完整直接/动态/手工/外部消费者、source-effect、测试和退出证据先于每个实际切片。保留v2.5原13个映射的完整限定，本版将新增证据直接并入相关行，再补独立review和环境责任。

| 当前责任→建议目标 | 实际消费者/改进目标 | 必需迁移、恢复、回退与停止条件 |
|---|---|---|
| rehearsal轻framing→domain/rehearsal_context.py | research_commit/live/workflow/方法；减少借类型拖入Odds | 类型/JSON/hash、旧public import保持；全部caller迁出再退代理，T1/T2 |
| research/claim v1/v2/source_policy→methods/quality | v2→v1、case tests、旧Deep | 不改assessment/schema/方法hash；domain不反依methods；旧序列化/命令可恢复 |
| research_commit_only文件原语→infrastructure/local_files；保管→application/research_delivery | Odds/比较/TDX/独立stock/历史replay脚本 | 原件先存后验≠两文件原子报告；旧脚本/格式/环境支持先定，不能仅全仓rename |
| 三类Odds→domain/odds分立实现 | spine/保管/Human同Research比较 | 共享payoff不混资格；概率/字段/context/时钟反例，各旧result重建，无自动互转 |
| cli/live→interfaces/cli＋application/live_decision及公告用例 | 五命令/console/workflow/shell | 参数/错误码/无权不调用，help/离线命令不构造市场fetch；余尾闭合前不施工 |
| Odds政策资源与style分别移所属application/policy_data | 两loader/setuptools/XHS voice | 原resource bytes、wheel/sdist及仓库外启动；editable成功不代完整安装 |
| XHS harness/voice→application/publication | 旧Deep claim catalogue/voice/人工稿件 | 先保旧adapter；选定声明/OMIT/无自动发文；草稿覆盖不冒充原件custody，G4 |
| registry/输入声明→config/<owner> | Collector/archive/index/B2/Watch/intake | 配置双端；旧R/packet仍原path/schema；execution-inputs另有owner，先核push/externaltrigger不回填历史 |
| smart_money_view.state/control→application/smart_money | capture/reading/control/workflow/tests | state/初次后继JSON相同，丢history不重置，原R与未发布raw等待保持；先迁两端再退view导出 |
| global纯plan/日期/codec→observations/global_market；capture→application | 两workflow/global reading/CLI | v1/v2、重试、partial/无回执/数值日期/旧summary与拒绝不变，不改原packet |
| economic PublicResponse/安全HTTP→infrastructure/http；业务绑定留economic | global_public_context/economic CLI/workflow | 仅共享同义机械合同；Global保HTTP错误body与economic不读取HTTPError body差异保留，旧implementation映射先定 |
| RSS registry与native消费历史→独立经济feed/native用例 | successor/acceptance及原多用途workflow | 保runpy sibling、三locator、init/continue、失败不变success；补同scope/FIFO/全局gap、原plan30分钟和物理32MiB预算；先有兼容reader再迁owner |
| disclosure分组→observations/disclosures；旧assessment→methods或公告用例 | CLI及原assessment | 跨Research截止保整批，精确Evidence集合/补充不覆盖/旧输出；assessment/receipts/HTTP尾部未全闭合不移动 |
| economic review→application/economic_inputs的单独review合同 | inputs/context/CLI/对应tests | eligible_from不能改为captured_at；保declared reviewer及原INCOMPLETE，裸观察不冒充已审；当前默认目录空不能捏造接受样本 |
| 历史解释环境→格式owner声明＋既有环境技术实现 | economic discovery/review及所有依赖其重放的用途 | §3.6先验证现环境/原环境/具体兼容版本对；源码指纹相等仍可拒绝，严禁删校验或改原manifest；无可行环境阻相应迁移不阻无关文档 |

切片必须再列精确base/head/old→new、采纳决定、外部实现取舍、直接及已证下游、正负历史样本、预计/实测成本、reader/writer次序、生产触发影响、恢复/回退和旧义务退出。不能将“整体设计先行”偷换成所有后期逐文件细节一次冻结，也不能反过来先搬文件后靠CI猜依赖。

## 8. 全局迁移与验收

### 8.1 W1–W8

| 批次 | 目标/M归属 | 前置与独立确认 |
|---|---|---|
| W1 公共合同/保护样本 | M01–04/11/13/16/19；能力、命名、owner与原正反例 | P3整体采纳；diff→trigger→source-effect包括Action更新；不切生产数据 |
| W2 共享原语/资源 | M01/05/10/13–15；窄类型、文件/传输、预算owner | 实际消费者/Reuse；same bytes/异常/预算；旧重复和转发真正退出 |
| W3 用例/producer/恢复 | M04/06/08–10/12；资格/进度/消费账/#581 | G2/G3，Smart反馈与RSS三种账；原plan不刷新；保持时钟/权限，不能双写或清账 |
| W4 来源/观察各族 | M05–07；Sector/Stock/News/Industry/economic/D和财务输入 | W1/W2/相关W3，逐族原件→最终消费者；无重采，旧指纹/解释保全，新闭包验证后收窄 |
| W5 方法/档案/历史 | M02/03/11/12/16/24；旧Funnel/generic/Quick/中文名 | G1/G3，原hash与失败保管；兼容环境先查，reader先writer后，回退能读已发布格式 |
| W6 读包/发布/Workbench | M13–18；可选组合、三类效果、时钟/重入 | 相关W3–W5，T3/T5、host/client/迟到跨R；Sites不自动部署 |
| W7 tests/CI/依赖/文档 | M19–22；fixture、资源、环境、供应链与入口 | W1起贯穿，同保护范围/环境成本；工具采用另核，不放宽现役门禁 |
| W8 旧执行/过渡退出 | M03/08/11/19/22–24；入口/别名/专属配置/测试 | G4及consumer迁出，四类退出分别签；原件和必要reader保留 |

W4/W5可按真实依赖调序，W7贯穿；不同时展开多批生产迁移。旧S1/W5、S2/W2-W6、S3/W4-W6、S4/W7只是子样本，不是全部范围或默认顺序。重排在#508解释，不另建队列。

### 8.2 工程验证与成本基线

现役CI保持content/draft_feedback/full/merge_reuse；本设计路径不在prose白名单，Ready PR正常完整验证。正式full、独立main、严格原件reuse、publisher、browser、产品使用和Human接受分别成立；不拿旧head/最快分片冒充新head完整结果。[CI]

比较原复用、简单完整执行、减少重复安装/collection/聚合的方案；优先原生workflow/actionlint/pytest split/xdist，不新建选择/调度平台。退tests依义务结束而非数量或年份；必要字段反例直接测owner，保实际消费者/拒绝传播。原ZIP当数据不执行，环境不符保留失败。没有取得告警不等于零漏洞。

依赖比较现pip/setuptools、constraints/lock/uv或候选环境及退出成本；原Action精确版本和source-effect全域核查，不顺手升级或改变任务。E57证明现役workflow维护也可能产生业务请求，P4逐批必须把此效果列入范围和授权检查。

文档沿AGENTS→NEXT/#297→#508→本设计/精确证据；原则正文只有WORKING-PROTOCOLS。每轮保head/PR、实际验证、在途/未知效果、缺口与唯一下一步。普通文档合并和架构采纳不互锁，但不能用合并签P3完工。

### 8.3 A1–A8整体完工标准

| 验收 | 必须成立 | 不足以替代它的证据 |
|---|---|---|
| A1 全域处置 | 重要模块/永久责任有消费者和决定，关键UNKNOWN闭合 | 目录树、矩阵行数、全域DEFER |
| A2 目标结构 | 采纳能力/依赖/名称/owner/公共面在代码、安装、产品成立 | 六目录、无环import、多层Facade |
| A3 语义与历史 | PIT/单位/时钟/Research/Odds/Human及旧R/包/新格式回退可恢复 | hash、CI绿、一份原件重放或版本2.0 |
| A4 执行与恢复 | 档案、运行、发布的原件/失败/未知效果/实际消费和兼容环境有证据 | 一次ZIP恢复、环境安装或publisher成功 |
| A5 永久复杂度 | 被替代的旧义务/兼容真正退出，代表任务系统性改善 | 行/文件/tests/依赖数下降 |
| A6 工程反馈 | 同范围可解释环境下安装/collection/fixture/CI/证据成本达采纳目标 | content对full、单次提速、漏计旧环境和上游升级 |
| A7 产品与接手 | 真新上下文从入口完成代表任务，实际产品边界/可用性成立 | 同会话换角色、未部署UI或要求Human搬材料 |
| A8 收口 | 目标完成或范围修订获准；DEFER有owner/风险/触发，Human裁定发行 | 无限等零缺陷或把难域删出范围 |

### 8.4 T1–T7共同变更样本

| 样本 | 同口径比较任务 | 本轮新增必要反例 |
|---|---|---|
| T1 领域资格 | 修改一项必要资格，统计真实owner/传播/重复规则 | 公告轻分组不能带来method/Market执行 |
| T2 研究方法 | 替换方法，保旧格式、共享执行pair、通用commit和接受边界 | source-review与Research方法/认证不混 |
| T3 保存源新增用途/换reader | 同原件、不同合法用途，比较接入/失败/资源隔离 | 同scope扫描抑制、换scope重扫、FIFO首项预算、全局source gap |
| T4 档案格式/命名 | 原bytes/中文名/原hash，先reader后writer与新格式回退 | 仅源码相等而Python环境不符仍拒绝；真实四原件正样本与五损坏副本 |
| T5 未知效果/恢复 | 原dispatch对账、失败记忆、预算/原件/发布进度 | quiet仍有旧plan、原30分钟窗口、HTTP403/no-body历史保持，不自动执行 |
| T6 视图/host/可选停用 | 页面/写入/刷新独立、迟到/跨R拒绝、可信host | 停Smart展示不能意外清control进度，停producer不删历史reader |
| T7 依赖/CI/资源 | 仓库外安装、同保护集合、升级/环境/退出负担 | Action-only变更的source-effect、旧运行环境的可获取与支持成本 |

原反例继续：News历史恢复失败不妨碍独立当前采集但保缺口；D候选回退不退API预算并保价格/Research；Sector过期不借cache/综合R续跑；#581非同target成功不擦gap；资料转存不自动研究；坏原文/迟到结果拒绝。候选只接管纯计算就按该范围计收益，完整恢复接管声明则须实证。[V23][REUSE]

本轮8检查不冒充完整T4/T5/T7或全单测；v2.5的18函数案例不扩大。P1的#799 full累计613作业秒、main34秒、publisher138秒仅历史样本，不是本轮收益。G6应取得代表任务同口径实际基线，P4前采纳量化目标；不编百分比，不计模型思考时长为生产成本。结构/外部适配若增总负担，要改设计而非降低完工标准。

## 9. G1–G7剩余证据与下一决策

| 门 | 已有证据 | 未完成/受限动作 |
|---|---|---|
| G1 依赖/公共面 | 前驱29顶层正文/33静态范围、4runtime接点、console/resource和19生产mjs；本轮选定来源尾部 | 不是全仓调用闭包；CLI/adapter、动态/手工/外部消费者继续，未知不能支持全局删除 |
| G2 producer/配置/资格 | E46–E51加本轮intake/consumer/exact-plan/discovery/review/node，review→context局部消费者；path-push实际正例 | Smart source parser/docs/Relay、stock其余purpose、公告assessment/receipts/HTTP，theme matcher/probe未审内部和外部调用仍明列；不重读无变化已审文件 |
| G3 档案/状态/恢复 | 真实四来源原件完整重放、五副本拒绝、实际历史runtime不兼容；精确原件/脚本/输出可定位 | 未完成旧Python环境重放、RSS云端scan/execution历史、所有work-ref/容量/期限、旧R/新writer/回退、生产恢复；一项正样本不关闭全域 |
| G4 退出 | v2→v1/XHS/历史脚本/runpy和四类退出明确；旧plan不获新资格 | 原owner意图、manual/CLI/external trigger、全部专属fixture/config和支持期；等价reader后才退 |
| G5 产品/host | 前驱生产声明/三份tests及身份/迟到证据，economic context局部consumer | 余12份test.mjs、browser/手机、真实host资产/身份边缘/无旁路、Quick→Brief/更正；Sites暂停不免审也不授权部署 |
| G6 成本/Reuse/供应链 | 原Kedro/Hamilton/dlt/pluggy局部固定审阅、T1–T7；本轮原parser复用与恢复环境成本问题 | 全fixture义务、实际变更基线、必要候选隔离试验/许可/依赖/副作用、DeepSeek Harness/Cordis及完整架构取舍；未安装/未跑不称通过 |
| G7 独立接手 | 唯一入口可恢复本轮版本与原证据 | 真新上下文/维护者完成代表任务；同会话不可自签 |

**下一步：继续G2中影响拆分/退出的Smart parser/Relay及公告CLI assessment/receipts/HTTP尾部，回写同一能力/迁移表；同时把E56转为各格式的环境支持与恢复取舍决策输入。** 对旧Python样本的完整重放需取得真实相符环境或正式验证的具体兼容方案，不能先改校验“解锁”；在该条件缺失时仅限制其恢复结论，不阻其他设计取证。原RSS云端历史、stock其余purpose、G4/G5/G6/G7未验责任不消失，不通过换域或DEFER隐藏。

不重复P1/P2、已核顶层/19生产mjs、v2.5十一文件和本轮六文件；有实际diff、矛盾或特定未验分支才重开。后继从当时main开普通PR，不向已合并前驱追加。全局目标/命名/拓扑和重大实现来源决定先于P4，每切片详细消费者/恢复/退出映射先于该切片施工。

Human无需重批全面审查、统一原则、Reuse/Modularity或普通文档。仍需正式裁定具体架构/外部实现接管、公共支持/精确RETIRE、长期原件和环境保管、成本/CI目标、候选试验/采用、P4批次、部署和发行；本稿不代签。

C的2026-10-08/09/12/13/14自然窗、D冻结/成熟结果、#351/#621/#581原owner和P01–P10/L保持。Sites暂停、禁Codex、分钟STOP、新城暂缓、原Research/Human/Odds/Watch、来源/模型、通知/时钟、费用/隐私/权限及AI Investment Authority=NONE不变。无新来源/模型请求、生产迁移、批量删除/重命名、候选依赖安装、交易或v2.0.0发行授权。

## 10. 精确来源与证据路由

新增代码固定M，历史原件固定其原run/commit；当前解释由受信任M提供，原档案中代码未执行。前驱完整引用与声明分别留在V23/V24/V25，不将引用压缩视为删除保护义务。PR/head、实际CI原件、正常合并/发布、未验事项和接续以#508最终回执为准；以下恢复材料不是另一份主计划。

[OWNER]: https://github.com/auguspp/decision-kernel/issues/508
[PLAN13]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6097686457
[PLAN12]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6096068040
[PLAN11]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6095772144
[PLAN10]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6094482452
[PRINCIPLES]: https://github.com/auguspp/decision-kernel/blob/986f70523ed9674e32db4f313bbd5a95ea39e3b0/WORKING-PROTOCOLS.md#project-principles
[V25]: https://github.com/auguspp/decision-kernel/blob/986f70523ed9674e32db4f313bbd5a95ea39e3b0/docs/kernel-2.0-design.md
[V24]: https://github.com/auguspp/decision-kernel/blob/6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc/docs/kernel-2.0-design.md
[V23]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/docs/kernel-2.0-design.md
[HANDOFF14]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6098990602
[START15]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6099118485
[RECOVERY15]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6099221201
[P1]: https://github.com/auguspp/decision-kernel/blob/97a4b14e287b04600841c1cc157c38a3cad0a781/docs/kernel-2.0-architecture-map.md
[P2]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/docs/kernel-2.0-prior-art.md
[REUSE]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/docs/kernel-2.0-architecture-reuse.md
[OLD]: https://github.com/auguspp/decision-kernel/blob/9290df46052f823a96069932321ae50b016af65c/docs/kernel-2.0-design.md
[MOD-REQ]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6097504982
[CI]: https://github.com/auguspp/decision-kernel/blob/986f70523ed9674e32db4f313bbd5a95ea39e3b0/docs/CI-MAINLINE.md
[INTAKE]: https://github.com/auguspp/decision-kernel/blob/986f70523ed9674e32db4f313bbd5a95ea39e3b0/src/decision_kernel/runtime/radar_feed_intake.py
[CONSUMER]: https://github.com/auguspp/decision-kernel/blob/986f70523ed9674e32db4f313bbd5a95ea39e3b0/src/decision_kernel/runtime/radar_feed_consumer.py
[PLAN-EXEC]: https://github.com/auguspp/decision-kernel/blob/986f70523ed9674e32db4f313bbd5a95ea39e3b0/src/decision_kernel/runtime/theme_plan_execution.py
[DISCOVERY]: https://github.com/auguspp/decision-kernel/blob/986f70523ed9674e32db4f313bbd5a95ea39e3b0/src/decision_kernel/runtime/economic_release_discovery.py
[REVIEW]: https://github.com/auguspp/decision-kernel/blob/986f70523ed9674e32db4f313bbd5a95ea39e3b0/src/decision_kernel/runtime/economic_release_review.py
[NODE]: https://github.com/auguspp/decision-kernel/blob/986f70523ed9674e32db4f313bbd5a95ea39e3b0/src/decision_kernel/runtime/economic_node_study.py
[ECON-CONTEXT]: https://github.com/auguspp/decision-kernel/blob/986f70523ed9674e32db4f313bbd5a95ea39e3b0/src/decision_kernel/runtime/economic_market_context.py#L75-L231
[HISTORY-DOC]: https://github.com/auguspp/decision-kernel/blob/986f70523ed9674e32db4f313bbd5a95ea39e3b0/docs/native-feed-history-workflow-v1.md
[CAPTURE-WF]: https://github.com/auguspp/decision-kernel/blob/986f70523ed9674e32db4f313bbd5a95ea39e3b0/.github/workflows/economic-source-capture.yml
[ACTION-RUN]: https://github.com/auguspp/decision-kernel/actions/runs/36526584715
[FAILED-RUN]: https://github.com/auguspp/decision-kernel/actions/runs/33996480270
