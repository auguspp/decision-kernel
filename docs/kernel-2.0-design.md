# Kernel 2.0 — 全局目标架构与渐进重构方案 v2.5

日期：2026-10-10（Asia/Singapore）。设计 ID：`K2-DESIGN-20261010-v2.5`。唯一计划与跨会话接续入口：[#508][OWNER]。有效计划为[v1.3][PLAN13]与[v1.2][PLAN12]、[v1.1][PLAN11]、[v1.0][PLAN10]未被替代条款；长期规则从已合并的[统一项目原则][PRINCIPLES]读取。

**状态：P3 GLOBAL DESIGN PROPOSAL / 待审。** 本稿提出具体能力边界、命名与拓扑决定，不表示这些技术决定已经采纳。文档获准交付和正常合并不依赖P4批准；具体架构、依赖、迁移与生产效果仍分别取得相应采纳和证据。P4/P5未启动；实时进度只在#508最新回执。

**版本关系：** 承接已随#805合并的[v2.4精确前驱][V24]与[13交接][HANDOFF13]，本轮范围见[开始记录14][START14]。本版补来源控制/状态反馈、Global codec、native RSS消费历史、经济输入和两条CLI尾部的证据，并据此修订同一能力合同、状态归属与迁移映射。K2-ADR-C/N/T继续PROPOSED；v2.4的E40–E45与三项决策、v2.3的E21–E39/F01–F12完整证据和未验声明保留。原M01–M24/W1–W8/A1–A8/T1–T7/G1–G7编号不变，不建立第二份计划；[P1][P1]、[P2][P2]和[Reuse附录][REUSE]不重做，[旧v1/#803][OLD]默认S1→S4不复活。
## 1. 目标、差距与本次推荐

Kernel 2.0覆盖整个工程体系的架构审查、必要目标重新设计与渐进式全面重构。“全面”是审查和决策范围，“渐进”是施工方式；不要求所有代码重写，也不能以四项局部修补替代系统改善。最终必须降低长期维护、扩展、兼容、验证、恢复和接手的总成本。[PLAN11]

原P3把保护领域语义扩大成保留原拓扑、把有界切片收窄成全部目标，并以局部血缘和工程交付代替整体设计。本版仍以实际消费者、可替换边界、状态归属与净收益纠正，不撤销历史分析与真实交付。

| 决策条目 | 本次明确推荐 | 仍可推翻的条件 |
|---|---|---|
| K2-ADR-C 能力与组合 | 按具体用例声明必需/可选能力，合同由语义owner维护，具体实现由组合入口提供；先比较原生显式组合、成熟组件与完整框架 | 真实适配/升级/退出证据显示外部完整架构净成本更低时调整；不预先选定自有框架 |
| K2-ADR-N 命名与身份 | 不同对象各有一致规则；机器身份、原始文件名、显示名、版本与时钟分开；旧身份/原字节不重算 | 具体生态或历史公共合同需要例外时在其owner处登记，不为整齐破坏兼容 |
| K2-ADR-T 拓扑与归属 | 同仓六类代码责任域，应用内部按能力组织；无独立万能contracts包；配置按owner集中，历史档案不批量搬迁 | 全部关键消费者及Reuse净成本补齐后正式采纳；六个目录名不是现在已冻结的施工命令 |
| 迁移与验收 | 全局决定先于P4；每批旧→新和消费者映射先于实际移动；四类退出分别验证 | 新语义、费用、权限、来源、任务时钟或生产迁移不由文档合并隐含批准 |

固定边界：GitHub是正式代码/证据/过程后端；PIT、UNKNOWN、Evidence/Research/Odds/Human区分；保留原件、失败、方法版本和Human原话；AI Investment Authority=NONE。开放审查：内部拓扑、接口、配置、状态表示、保管与恢复实现、测试/CI和依赖。现役合同在替代方案获准及验证完成前继续适用。

## 2. 证据基线与新增判断

### 2.1 本轮实际做了什么

固定M=`6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc`，即#805合并。实时恢复main、AGENTS、NEXT/#297、#508/13与已合并#805，开放main PR查询为空。前驱设计blob=`51039778eced9c4e7c6aff152ac15377de8dc3f4`。取证期间没有解析生产R或调用来源、模型、producer、publisher；如随后正常文档合并触发原发布，工程证据单独登记，不混为取证或业务验收。

**新增完整读取11份内部源码：** `.github/scripts/`中的smart-money-control、prepare-native-rss-successor、native-feed-acceptance；runtime中的smart_money_capture、global_market_context、global_public_context、radar_feed_history、economic_release_inputs、economic_source_capture、disclosure_radar、disclosure_research。完整UTF-8/Git blob核对及AST解析均通过；模块内部导入已列，未读完其所有下游，不能称完整依赖闭包。未执行这些来源入口。[SM-CONTROL][SM-CAPTURE][GLOBAL-RELAY][GLOBAL-PUBLIC][RSS-PREPARE][FEED-ACCEPT][FEED-HISTORY][ECON-INPUTS][ECON-CAPTURE][DISCLOSURE-BATCH][DISCLOSURE-METHOD]

局部新增读取`smart_money_view.py:1–95`，仅核state与history开头；复看已审CLI的1–58行和相同blob的`smart_money_reading.py:250–334`，用于闭合control→R专用state→publisher的实际反馈关系，不重复宣称整份新审。反向搜索在`tests/test_smart_money.py`和相关capture/relay tests找到真实脚本消费者；仅取得片段，未完整审阅或运行这些测试文件。直接路径`tests/test_smart_money_control.py`不存在不代表该责任没有测试。[SM-STATE][SM-READING][CLI][SM-TEST]

**有界本地验证：** 对上述精确control脚本以非`__main__`加载，直接调用原`choose`、`pending_publication`、`relay_started_count`；18个合成案例通过。socket连接与子进程创建被禁止，实际尝试0；无临时复制实现替代原函数。覆盖次数上限、完成/补确认/短暂失败/权限与未知失败、未发布原件被metadata skip遮挡、已接受前驱、在途/重复/缺失/不完整历史以及跨代码版本的Relay实际启动计数。属于原函数行为证据，不是workflow或真实历史恢复，不是原单测全套执行，也不是维护成本MEASURED；脚本/结果的确切保管在本轮交接。

外部复用：直接消费v2.3固定dlt1.31.0源码审阅，并新读同commit的advanced-state正式文档，以及官方滚动cursor、lag与REST session合同；滚动页的版本标记不替代固定源码版本。没有安装dlt、运行候选或核完其全部依赖/许可/状态实现，因此没有采用或性能结论。[DLT-STATE][DLT-CURSOR][DLT-LAG][DLT-REST]

### 2.2 新增源码判断 E46–E51

v2.4 E40–E45继续按[V24]§2.2消费：三类Odds不互换、v2依赖v1、CLI/资源公共面、三种文件写入责任、execution pair与XHS/历史脚本消费者均不因本版省写而退出。

| 证据 | 实际事实与消费者 | 对目标的影响／验证边界 |
|---|---|---|
| E46 发布包内确有专用控制进度 | `smart_money_view.state`生成completed/unresolved/calendar进度；reading调用它并保管state；下一次smart-money-control从固定R读取该state，决定是否采集、补确认或恢复 | “综合R不是通用恢复权威”不等于所有R字段均无控制消费者。将Smart进度推进与展示分责，原R只是其明确交付路径；不能只迁页面便删除state。全量state重建/真实恢复尚未演练。[SM-STATE][SM-READING][SM-CONTROL] |
| E47 不同进度与次数不能混成cursor | Smart计划区分最后枚举交易日、日历缺口、完整分区和未完成分区；新捕获前核上次原件是否已被读入，metadata跳过不掩盖未发布捕获；主用途按调用机会限制，Relay另数实际启动job | 保留未完成集合和前驱，不能以最大日期/最后run/head变化清账；提取control必须连同native job、runpy activity及reader处置。18案例只核三个函数，不覆盖全部计划/transport。[SM-CAPTURE][SM-CONTROL] |
| E48 Global同为采集但失败与日期合同不同 | Relay仅特定TEMPORARY_QUEUE允许第二次attempt；公共族一次GET无重试；REQUEST_IN_PROGRESS/RECEIPT_UNAVAILABLE不等于0请求。公共v1/v2日期门槛分派，并保参考利率、UTC日桶和期货换月限制 | 共用传输/原件写入的机械部分，不共用默认retry、PIT时钟或source成功。共享助手应脱离Smart/economic业务模块；旧codec和原packet仍按旧规则重放。[GLOBAL-RELAY][GLOBAL-PUBLIC][ECON-CAPTURE] |
| E49 来源registry与下游消费历史是两种状态 | RSS successor先核成功前驱原件/registry再取源；native acceptance显式区分isolated/initialize/continue，并分别绑定source、market、history。消费history允许记录失败但可重放的market执行，source前驱仍要求成功 | 不把“所有失败不能保存”或“有记录就是已消费成功”统一化。source版本/初见时钟与scan/execution记忆分开；停用source不等于退役消费reader。未读完整feed intake/consumer内部，保留G2。[RSS-PREPARE][FEED-ACCEPT][FEED-HISTORY] |
| E50 经济输入仍要保留前移日期后的缺口 | 输入组装核所有直接review bundle，按接受hash去重、不按目录最新选择；保留同URL元数据冲突与OLDER_UNREVIEWED_BACKLOG；capture将原件保管与摘录匹配分开，HTTP错误body不默认保管 | config/受审资料/派生输入分别归属；dlt回看窗口不自动替代未审集合或同URL正文修订核验。extractor替换也会触及旧implementation指纹及文本匹配，不能仅搬工具。[ECON-INPUTS][ECON-CAPTURE] |
| E51 CLI公告尾部含不同责任 | disclosure_radar按证券/发布时间分组，跨Research截止的整批仍保留；disclosure_research则校验具体旧方法assessment与原Evidence批次并调用旧Funnel | 将分组/新鲜度放纯观察，将旧方法assessment放方法/用例适配；不能把两者一起做成通用source policy或只因在runtime便都视为采集器。assessment/receipts/HTTP等余下尾部未闭合。[DISCLOSURE-BATCH][DISCLOSURE-METHOD][CLI] |

### 2.3 前驱重要约束继续生效

下表是现行设计约束摘要；完整原件、源码区间、F01–F12和原未验范围仍在[V23]，不是被本版压缩掉的验收责任。

| 范围 | 必须继续保护 |
|---|---|
| 事件与来源 | Sector完成只给某些日常输入执行机会，TDX另需success/result-bearing；旧公告自动边要求scheduled Inbox而当前Inbox为manual。不同用途不得误接；经济/股票特定path push可能真实采集，移动前核效果；job/step/title被reader消费 |
| 恢复与状态 | Sector合格state、News可选历史、Smart Money/Global前驱各有资格；#581保存未交付记忆，后一天成功不能清旧gap；未收到dispatch回复不等于未执行；cache、综合R和可见报告均不自动授予恢复权限 |
| 共享资源与兼容 | API已用预算不随候选文件rollback；Kedro deepcopy/assign不同；Concept宽指纹把无关改动带入兼容维护，旧映射保留、新回放边界可缩；B2共享Relay助手/锁/hash须核原义务，不自动解除 |
| 档案与研究 | 旧R按自身registry重投影，不全局放宽后追认旧拒绝；泛化提交与旧Deep信息hash不同；轻framing类型、旧方法enum和Retainer均有真实消费者；新格式发布后回退仍能读它 |
| Workbench与产品 | 综合R、News live、Issue观察时钟不同；重读、#601追加、受控dispatch是不同效果。host可信身份边缘/无旁路、token与指纹/permit协调、迟到响应/跨R隔离、原文损坏拒绝继续；useLabel参与新context hash不能当纯文案改动。真实host、browser、Quick→Brief不由CI代签 |

## 3. K2-ADR-C：能力合同与组合

**状态：PROPOSED。** 背景是过宽运行模块、跨业务借私有工具、方法/历史codec与展示相互牵连。目标是能力变化只触及自身与合理接入点，而不是把所有旧实现包装成一个插件后保持原复杂性。

### 3.1 同口径比较

| 方案 | 能接管的责任 | Kernel剩余责任与选择依据 |
|---|---|---|
| 现有显式函数/构造注入＋原生GitHub | 保留已运行的确定性函数、workflow_call/composite、Git和pytest；不新增runtime注册系统 | 当前跨私有模块借用、过宽CLI/Collector仍需收敛；熟悉或已经投入多不构成优越证明 |
| 六责任域＋能力内合同的内部重组 | 让类型/算术/方法/用例/机械I/O有明确owner，少复制和少错误依赖 | 实现仍自己维护；须在T1–T7中证明净收益，不能只加Facade/空包 |
| pluggy选定hook组件 | 固定1.6.0的register/add_hookspecs/unregister可承担1:N扩展点与hook解除 | 不负责Git事实、历史reader、预算或外部效果。已读manager局部代码：注册过程先写映射再核hook，不承诺事务式无残留注册；接入需测试部分失败、调用顺序和清理。未读完整测试/依赖许可、未运行，因此仅候选，不是采用结论。[PLUGGY] |
| Kedro/Hamilton/dlt选定组件或更完整架构 | 前驱已核：数据目录/流水线/纯函数图/REST分页有真实可用入口，不要求整套平台才有价值 | 资源复制、资格、错误与raw保管、配置权威、升级/退出都计入；不以“非Python/项目大/不是100%贴合”排除，亦不以README宣称胜出。[REUSE][V23] |
| DeepSeek Harness/Cordis等完整能力组装 | 原需求提出能力定义/提供者/消费者和生命周期的对照方向 | 本包未完成该实现的独立代码/成本核验，保留为待核，不先宣布只能借理念或全面替代；不因其待核阻塞不依赖该选择的命名规则。[MOD-REQ] |

**推荐：稳定合同与显式组合先作为设计基线，具体实现来源逐能力裁定。** 小型单次用例不强制注册器；真实1:N或动态停用需要出现时将成熟hook/生命周期组件纳入实际对照。更完整外部架构仍可改变总体组织，当前六责任域不是优先于外部方案的既成事实。任何非独特自建子系统必须有实际替代检查和具体阻断证据；本稿不宣告新插件/调度/状态平台NEW_BUILD_JUSTIFIED。

### 3.2 能力定义、提供者、消费者与缺席

合同放在拥有该用例/语义的模块，不统一放到一个全局`contracts`桶。下表是设计描述，不是新capability registry或自动执行授权。

| 能力及M归属 | 定义／现有提供者／消费者 | 必需、可选与状态owner | 组合与替换界限 |
|---|---|---|---|
| 研究提交 M01–03/11 | method-agnostic commit合同／现有ResearchCommitPackage＋commit／离线保管、live | 精确snapshot和Evidence必需；仅离线schema2可无framing/数值准备；Human接受另立 | 方法输出适配在methods；commit不依赖某方法；不伪造Pre/Quick或改旧hash |
| canonical Odds M02/04 | 原Odds政策/完整概率/ObservedMarket／原算术与Odds构造／spine、合格调用者 | 合格市场及数值Research必需；odds context可选但原缺省不变 | provider替换须另核同证券、单位/时钟/复权与来源；context price不能冒充Market |
| provisional与conditional M02/11 | 各自独立的结果合同／原纯实现／Human分析、结果保管 | HumanPriceContext必需；前者仍需原概率分布，后者允许概率未知；外部Research全hash绑定 | 可以复用payoff/序列化，不能让开关把一类静默变另一类；历史重算不是今日准入 |
| 来源捕获 M05–10 | 特定provider/channel/对象/窗口合同／具体transport+parser／producer和保存结果reader | 授权/预算/原件owner在各用例；必需源失败阻本动作，可选补充缺失不抹基础结果 | 按request→capture→qualify分离；同ticker/同JSON不是等价provider，事件只是机会 |
| 研究执行与历史pair M03/09/16 | 特定方法的input/result/receipt／现役host和方法实现／identity/admission、产品接续 | 预算、execution pair、前驱/消费记忆有明确owner；旧codec不因此授权新执行 | 当前执行、共享receipt、旧Funnel校验与读面projection分开；动态import也算消费者 |
| 档案/报告保管 M11/15 | raw/progress/commit/Odds各格式；create-only或原子报告／原Git+local I/O／归档reader、TDX/比较CLI、人工恢复 | 独立Research pin、完整库存/原字节必需；失败原件与不完整报告区别保存 | 机械I/O共享；操作合同不共用万能save；新writer最后切换 |
| 保存读包与可选观察 M09/13–16 | 受支持read descriptor／各reader和派生算法／原publisher、研究及Workbench | 共享API budget和候选files各唯一owner；D/补充reader失败保留无关价格/研究；已耗calls不回滚 | app composition明确启用能力及顺序；不让dataset复制client/凭证/预算 |
| 展示与显式请求 M16–18/24 | fixed-R阅读、#601追加、新闻刷新、写作brief各自合同／Workbench及XHS／Human | host权限和新请求独立于页面展示；XHS只用选定声明，原Human状态OMIT | 视图替换不得改变记录身份；停用producer不删历史reader；不自动上线/发文/Watch |

必需依赖缺失只阻塞依赖它的动作；可选缺席、技术失败、数据不合格、业务quiet/WAIT/STOP使用已有不同状态，不能统一成空数组、零或成功。共享账户/凭证本身不是可卸载的权限授权插件。

### 3.3 四类退出的确认条件

| 退出 | 必须处置 | 保留与验证 |
|---|---|---|
| 运行时停用 | 停未来构造/注册/触发，标明哪些消费者显示未启用；在途动作先对账 | 无关能力可用；旧结果保原日期；停用UI不是停止生产，反之亦然 |
| provider替换 | 在组合点接替，比较请求、输入输出、单位/时钟/权限/失败；明确新旧状态兼容 | 同一支持合同正反例；既有记录不改来源，不继承原Human接受 |
| 旧执行入口退役 | 核manual、CLI、workflow/job/step、path push、配置、外部时钟；移除专属触发/权限/测试 | 公共语义和共享实现留下；Retainer/XHS/v1合同有消费者，不能按旧名删除 |
| 历史reader退役 | 等价历史恢复和适用采纳成立后，才退出旧解码/别名/专属fixture | 原bytes/失败/Human/方法解释可恢复；保历史不意味着旧producer必须永远运行 |

解绑hook不撤销已经发出的HTTP、Git写入或已消耗预算；未知效果不自动取消/重试。静态设计不是已完成这些演示。验证沿T2–T6、A2–A4/A7，不另建插件测试平台。

### 3.4 来源进度、消费历史与发布反馈的具体归属

**这是K2-ADR-C/T的细化，仍PROPOSED，不新增状态schema或自动恢复器。** 现状A把不同状态隐含寄存在view/control/reader；备选B将所有状态迁入通用pipeline state；推荐C先按下表明确owner和读写合同，机械保存可复用外部实现。A继续制造隐藏消费者，B未经资格/预算/失败对照会改变含义；C仍有小端口成本，需要G3/G6证明。若B通过实际适配与退出验证更低成本，可替代C的实现，不替换必要语义。

| 对象／实际链 | 目标owner与组合 | 迁移必须保护的区别 |
|---|---|---|
| Smart交付进度：capture observation → view.state → reading保管state → control读取 | `application/smart_money/progress.py`拥有纯进度推进；reading负责保管与定位；control经窄读取端口取回精确进度。首批建议继续原R/state路径，不先建新state ref或库 | 完成分区、未完成集合、枚举水位、日历缺口、原source id分别保留；显示失败不清进度。停publisher可能阻后续源，此依赖必须明确测；所有R不因此成为通用restore authority |
| Smart准入与账户使用：原调用列表／实际Relay job／未发布捕获 | `application/smart_money/control.py`保存原判定；原workflow薄调用，共享activity查询只借窄基础设施 | 主用途调用机会和Relay实际启动不是同分母；新代码/改名不能重置原预算。先对账未被消费的原件，不能为了“恢复”重复采集；unknown权限/历史范围仍拒绝 |
| Global单次attempt＋专有日期资格 | `application/global_market/`执行、原件保管；`observations/global_market/`拥有纯plan/codec/版本与数值；通用HTTP助手由infrastructure实现 | Relay受控第二attempt≠公共no-retry；REQUEST_IN_PROGRESS/RECEIPT_UNAVAILABLE≠未请求；v1/v2日期与数值原解释，捕获时间不冒充发布时间 |
| RSS来源版本registry与初见/出现历史 | 原feed intake拥有版本/时钟推进；建议`application/economic_feed/`组合独立输入/保管和旧codec | explicit baseline与精确successor互斥；旧版本/初见时钟不可丢；声明请求文件可在config，运行registry不是config；失去旧源不能静默初始化 |
| native-feed消费scan＋market execution账 | `application/native_feed/`拥有消费与历史保管；source、market和history各经精确locator接口提供 | 失败但可重放execution可以保管，不能改success；格式损坏/blocked scan不获完成；branch history不是全局exactly-once；remote上传与本地ready各证明 |
| 经济seed、已核review与派生扫描输入 | 声明/受审source原件仍由各原owner维护；`application/economic_inputs/`组装，纯对应逻辑归observations | 目录名不选择“最新接受”；同URL冲突/未审旧条目不被max日期抹去；新目录必须兼容原review inventory、文本绑定与implementation指纹 |

收益假设是减少跨业务私有工具依赖、把控制进度从页面生成中剥离、明确不应更改的状态。**本版没有搬文件或新建这些目录，没有声称原件恢复已通过或新增层数必然更好。** 数据存放默认位置遵循§5.2；源/消费账的原精确Git/artifact引用继续作为迁移输入，不一律集中进`config/`或`archive/`。

### 3.5 Reuse：按接管层次比较，而不是接受默认增量/重试

固定候选仍为v2.3已审dlt1.31.0/`2360d229c77f7f64692acc31a4555f4cfcd50ed3`，不是新依赖。其同版高级state合同支持资源私有字典、source共享状态、已处理对象集合，与数据一起保存；滚动官方文档另说明lag窗口、cursor边界去重和自定义session。不能因为默认cursor不足就否定整个dlt，也不能将其destination原子保存直接等同Kernel的Git/artifact完成。[DLT-STATE][DLT-LAG][DLT-CURSOR][DLT-REST]

| 可行复用范围 | 可能实际接管 | Kernel仍承担／需同输入验证 |
|---|---|---|
| 现有Requests/urllib＋内部责任拆分 | 不增加运行依赖，沿用已核来源执行与codec | 当前controller/codec/保管重复及错误归属成本仍由自己维护，不能因“运行中”默认胜出 |
| dlt RESTClient配显式session与响应保管 | URL/分页接线、会话配置与响应访问；原件在转换前保管 | 逐族请求上限/禁止redirect、权利与body保管、null/空/缺列区别；公共no-retry和Relay特许重试不得被默认5xx/429策略覆盖；原client审阅可复用 |
| dlt资源＋自定义分区/对象state | 可比较完整/待处理集合、源状态的机械持久化和批次处理，不限max时间戳 | 必须设计与原Git/artifact权威及失败原件的接合；数据提交成功与来源真实调用/历史上传不同。取消/初始化/refresh不得重放已耗调用或清掉合法旧账；仅套壳不算减少自有责任 |
| 原生GitHub复用＋上述组件的混合 | workflow_call/composite复用安装/机械接线；domain和有界控制仍显式 | 旧job/step/run标题、runpy sibling和外部触发是消费者，迁移不能只更新一端；总体升级/退出成本一起计 |

共同反例沿T3/T5/T7：较新日期成功但旧分区仍未完成；有旧raw但尚未被发布读入；同日跨head的Relay已执行；正文null与空表；无回执的外部调用；保留的失败market执行；旧registry的初见时钟；只停用视图而不重置采集。dlt lag可用于有证明的数据窗口，但不能凭有限lookback宣称任意旧缺口已补全。选择全pipeline前要核版本化代码、真实state提交/失败和退出、许可证/依赖、相同案例隔离试验；当前只完成正式合同补充，未运行或宣布采用/净节省。

## 4. K2-ADR-N：Naming & Identity

**状态：PROPOSED，形成可审阅规则，尚非格式或代码切换。** 来源是[CONS-09/10][NAMING-REQ]及[架构先行纠正][NAMING-CORRECTION]；复用P2已核Home Assistant身份/展示与成熟项目owner模式，并核Python/Packaging官方惯例。PEP 8也明确不应仅为风格破坏兼容。[P2][PEP8]

备选：A维持全部历史混合惯例；B一律改成同一种英文/分隔符；C按对象类别统一规则、向前应用、旧合同显式兼容。推荐C：A不能降低新增对象的决策负担，B会改写原件、破坏资源/调用与历史含义；C有必要例外与迁移成本，但可验证。

| 对象 | 建议新规则与例子 | 不允许的误统一 |
|---|---|---|
| 分发包/导入/命令 | 保持`decision-kernel`分发名与命令、`decision_kernel`导入；它们是不同生态位置 | 不为同拼写改console command或PyPI/import身份，不将Kernel2.0直接写成包2.0.0 |
| Python代码 | 新包/模块用小写、必要snake_case；类CapWords；字段/函数snake_case；常量/状态按已有稳定token规则 | 不批量改已序列化字段/枚举；不以root名`research.py`与新同名目录并存制造遮蔽 |
| JS、工作流、工程文档 | 维持现有ES模块kebab-case文件与camelCase出口；新workflow/文档用职责性kebab-case；README/AGENTS等约定名保留 | 不把JS出口改Python风格；workflow/job/step/title可能被消费，改名按接口迁移 |
| 机器身份 | 保留UUID、内容hash、证券和来源原有稳定规则；新人工slug默认小写ASCII并有各对象自己的长度/唯一性约束 | 不把中文title、公司名、路径或内存对象id当永久identity；不新造统一全域ID正则来重验所有旧记录 |
| 原文件名/显示名/存储路径 | 原件记录精确Unicode名称和bytes；代码/新机器目录默认ASCII；显示名可正常中文；读取时按段转义URL | 不静默NFC/NFKC规范化原名或合并碰撞；不能用改名后sha匹配代替原路径来历 |
| 来源与资产名 | 分开logical security、provider原生code、transport/channel/tool和证据出处；沿现有明确字段表达 | HiThink/Relay/工具名不自动等于经济证据来源；TDX概念与其他分类不因同名合并 |
| 版本 | schema、方法、算法、研究revision、软件发布各独立；文件含`_v1`可表示仍受支持旧合同 | 不全改`v2`，不删v1来表示项目升级，不重算历史information/package hash |
| 时间 | 新日期用YYYY-MM-DD，timestamp带时区；market session、发布/可得/取得/研究截止/计算/显示时钟分别说明 | 不用目录日期代替来源可得时钟；不把UTC日桶当交易所交易日；未知保留UNKNOWN |
| 格式内文件 | `result.json`、`retention.json`等按具体格式固定；原始bytes和规范化语义hash分开 | 不能因为多个包同名文件就合并为一个对象；外层新归属不改变内层精确库存 |

Unicode安全分两层：路径读取拒绝越界、绝对路径、分隔符/控制字符等实际危险；新writer在目标文件系统上检查规范化/大小写/保留名碰撞并保留原名映射。具体策略与旧reader版本一起裁定，不在本稿伪装已实现通用跨平台规则。旧R用旧registry/policy解释；不能改全局正则使过去拒绝项突然进入旧索引。[ARCHIVE][ARCHIVE-INDEX]

**确认条件：** 对机器ID/中文原名/显示名、两组规范化碰撞、旧R数量与拒绝、schema/method版本区分、CLI/安装资源以及workflow标识分别验证；需要新schema时先reader、再writer。无碰撞样本/历史恢复证据的切片不得搬原件。少量必要检查可用原有测试或成熟工具，不建立全仓风格罚则/命名注册库。

## 5. K2-ADR-T：Repository Topology & Ownership

**状态：PROPOSED。** 决定的是责任和依赖，路径是其表达。比较A当前顶层领域＋宽runtime；B前稿七个全局分类目录；C按稳定责任分区、用例内部按能力组织、合同跟随owner。推荐C，保留`src`布局和单仓单主要Python发行单元；它仍须与能真实接管责任的外部架构比较。目标不是六层嵌套，更不是每个能力复制六套空目录。[P2][V23][PYPA-SRC]

### 5.1 代码目标

```text
src/decision_kernel/
  domain/          已证明的身份、PIT、研究/市场值、算术和权限不变量
  methods/         研究方法、质量/source-role政策、按原版本解释的旧方法合同
  observations/    sector/stock/news/industry/economic/D等纯转换与计算
  application/     按live_decision、research_delivery、reading、publication等用例组织
  infrastructure/  受约束的GitHub、HTTP、本地文件与其他技术实现
  interfaces/      CLI与宿主接入、显式composition；不拥有研究接受
workbench/         原ES模块/服务端/浏览器入口，仍为产品边界
.github/           原生workflow/action、薄调用与工程辅助
```

`contracts`不作为独立全局代码包：领域值留domain；研究方法格式留methods；跨来源/保管/读包的端口在拥有该用例的application模块，或已有合理owner处。只有已证跨多个owner使用、且不会拖入其执行逻辑的稳定类型才提取共享小模块。应用按能力细分是为控制变化传播，不是新capability runtime。

依赖方向：domain不导入methods/observations/application/infrastructure/interfaces；methods与纯observations依赖所需domain，不反向借publisher；application依赖领域/方法/观察和所需窄端口，不从transport获取全局secret；infrastructure实现技术边界，可以依赖窄合同，不能导入含业务执行的用例模块；interfaces/composition可以同时连接application和具体实现；tests可组合各层，业务不依赖tests。必要端口应与实现分文件避免application/infrastructure循环，不能用全局service locator隐藏依赖。

现役`research.py`、`cli.py`等旧公共路径只有在消费者迁移和有限兼容方案成立时才退出；不得与同名package竞争。不强制所有内部import永久兼容，已记录公共命令、格式、外部/历史使用则逐项处理。旧代理没有活跃消费者且历史读取已等价时要真正退出，不永久双轨。

### 5.2 永久对象的默认归属

以下路径是目标建议，不是已经创建的位置。每行只有一个语义/写入owner；同一证券可被多用途消费，但不能因此把不同对象混在一个“公司文件夹”里。

| 对象 | 目标默认位置／owner | 可变性、writer/consumer和保管/迁移 |
|---|---|---|
| 核心代码/机械实现 | 上述src责任域；各语义模块owner | 经PR演进；支持接口和历史数据解释独立；不重写确定性算法来适应框架 |
| 当前生产配置/声明 | `config/<owning-capability>/`；各应用用例owner | PR变更；producer/reader共同迁移。示例`config/reading/purposes.json`接替当前用途索引时，旧R仍识别原`current_state/registry.json`；它仍是用途声明，不是原件或接受真源 |
| 执行请求/消费记忆 | 当前显式request路径与原work-ref为迁移输入；由原host/消费合同owner定目标 | 请求≠执行完成；已有path push是执行面，需完整G2/G3后切换；不得把全部文件统一移动到config或自动再消费 |
| 方法/操作文档 | `docs/methods/`下按实际方法；任务入口仍从RESEARCH-ENTRY跳转 | 方法版本与格式版本独立；旧正文/案例/Human原话保留精确定位，搬入口须可达与原合同不变 |
| 人读研究/工作底稿 | 新同类材料默认`docs/readings/<record-id>/`；研究保管owner | create-only/追加或明确新revision；旧research_runs和docs原件不批迁；资料保存不等于typed COMMITTED |
| typed Research/progress/Odds档案 | 新档案默认`research_runs/archives/<record-id>/<revision>/`；对应格式owner | 内层文件名/库存/bytes按原格式；progress、commit、Odds三种对象不混；旧candidates路径及execution packet约束须显式历史支持 |
| 来源原件/提取表示 | 原获准artifact/Git保管位置；source custody owner | 原件、抽取文本和metadata权利不同；不建立默认全部公开的sources大目录。发布副本有独立定位，过期/隐私/许可仍按原范围 |
| producer运行状态 | 原producer的state bundle/work-ref；该producer或明确进度用例唯一owner | Sector恢复不由综合R替代；Smart的专用交付进度目前经固定R供control读取，按§3.4单独绑定而不赋整个R恢复权限；长期保管待G3，保失败/前驱 |
| Human判断/接受 | 保持`docs/decisions/`及既有具名记录的Human owner | AI草稿和工程ADR不混入；新增判断不继承旧接受，不批量改名、归并或删除 |
| 派生读包/快缓存 | 原`read-model/current-state`、`read-model/news-live`等各指定ref；原publisher | 展示投影和被control消费的专用progress必须分别标识；两者目前可同R提交，不因同仓同ref统一权威。不同ref时钟/force合同保留，reader不自动获执行权限 |
| 健康与项目进度 | #581保健康连续性，#508保2.0接续，#297只路由 | 原生Issue是不同owner对象；报告记忆不能当无状态展示删除；不复制新状态库 |
| 测试/fixture/eval | `tests/<owning-capability>/`作为逐批目标，eval仍独立 | cross-test import、pytest收集/节点身份/分片先对账；原历史fixture与研究质量evaluation不变runtime依赖，不为减少数量塞循环 |
| 工程指南与ADR | AGENTS/README路由WORKING-PROTOCOLS；本设计内具名ADR | 旧决定以精确Git前驱保留；不要另建实时ADR审批系统或复制计划 |
| 第三方代码/资源 | 原`third_party/`和所属能力包资源；各采用方owner | 原许可/NOTICE/来源与更新/退出证据；政策JSON与写作样式虽共目录并非同一语义，迁移连同package-data和loader验证 |

新配置位置不意味着要迁所有旧文件；原格式/权限/consumer尚未闭合时继续从原owner读取，目标方案保持待采纳。`config`是否按该具体路径落地由全局采纳确认，但对象归属不能留到写代码时随意决定。

### 5.3 结构确认而不是目录美化

采用前要证明：需要更改的模块有真实owner；支持接口与私有细节可区分；追加一种来源/换一种方法/停用可选能力有明确接入位置；新结构减少错误依赖而非仅把它藏进转发；安装包从仓库外启动仍读到正确资源。importlib.resources与console entry沿官方机制复用，不自建资源定位器或命令注册系统。[PY-RESOURCES][PYPA-ENTRY]

无关内部文件数不设武断门槛。少量禁止依赖/包资源/格式检查由最终ADR和原测试推导，Import Linter等仍按P2实际候选证据和试验成本裁定，不预建永久门禁。

## 6. 全局模块与永久责任处置矩阵

KEEP / CONSOLIDATE / REPLACE / RETIRE / DEFER均为推荐处置，非已执行。UNKNOWN是证据状态，不是“无消费者”。下表归并前驱两张矩阵的当前问题、已知消费者、收益、兼容风险与验证；前驱具体源码证据仍可达。[V23]

| ID / 责任 | 问题与实际消费者 | 推荐处置／预期收益 | 兼容成本、风险与必要验证 |
|---|---|---|---|
| M01 身份/PIT/权限原语 | 轻类型与读面工具混居；commit/方法/reader消费 | KEEP语义、CONSOLIDATE同义原语；避免借类型拖宽执行链 | 不混不同编码/hash/时区；旧bytes与错误反例，G1/G3 |
| M02 领域/Market/Odds/算术 | 三类Odds有不同资格和时钟；spine、Human分析、retention消费 | KEEP原语义，CONSOLIDATE领域组织/适合算术 | 概率、单位、context/Market、UNKNOWN不能互换；旧模型重建、G1/G3 |
| M03 方法/旧合同/模型适配 | v2调用v1，Single Quick/Direct Deep共享旧receipt；host/live/archive/XHS消费 | REPLACE错位组织、KEEP旧codec；方法切换不拖当前执行链 | 方法hash/历史解释/预算及接受不继承；T2、G1/G3 |
| M04 CLI/live/application | 五命令共享宽导入，政策资源固定；shell/工作流/用户消费 | REPLACE过宽入口为用例＋薄CLI；按命令构造依赖 | 参数/退出码/发布输出/安装后资源；CLI正反例，T1/T7 |
| M05 source adapter/transport | Global复用Smart/economic助手，来源族有不同重试/错误body规则 | CONSOLIDATE机械传输，KEEP单位/时钟/rights；比Requests/dlt等 | 逐族retry/redirect/credential/原件保管配置不能被通用缺省覆盖；E48/E50、G2/G6 |
| M06 capture/producer | Smart枚举/完成/待修分区与Global单次捕获不同；workflow/reader/control消费 | REPLACE边界，CONSOLIDATE机械步骤；来源族局部演进 | 不把请求时间当覆盖，未完成尾部与无回执保持；E46–50、G2/G3 |
| M07 纯观察/计算 | 部分纯函数反依宽runtime；producer、准备与UI消费 | REPLACE错向依赖；复用现有/Hamilton等实现 | 原算法/失败、无网络边界和外部包装成本，T3/G6 |
| M08 workflows/资格 | 原event/job/path及runpy有消费者；Smart主调用数与Relay实际启动数不同 | CONSOLIDATE原生复用；RETIRE须证实的旧边 | 拆job不能清预算/未发布原件；保旧身份、手工/外部trigger与source效果，E47、G2/G4 |
| M09 状态/恢复 | Sector强state、Smart发布反馈、RSS原始registry与消费history不同 | KEEP必要差异，REPLACE展示/进度混居，CONSOLIDATE机械存取 | §3.4逐对象绑定；不能统一max cursor/empty reset或删失败执行，E46/E49、G3 |
| M10 执行/失败/健康记忆 | #581旧未交付、Smart pending publication、Global未知receipt与RSS失败ledger | CONSOLIDATE同义诊断；KEEP准入/保管/报告分离 | 未发送≠未知，保存失败≠成功消费；原日期/预算/前驱，T5/G3 |
| M11 档案/历史codec | Concept及economic有实现指纹；RSS含scan/execution原库存/前驱 | CONSOLIDATE保管，REPLACE宽回放边界 | 旧R/Unicode/原hash；extractor/renderer改变也需旧解释与拒绝复验，T4/G3 |
| M12 配置/registry | 输入数组/请求声明、RSS已见registry与经济review bundle是不同对象 | REPLACE重复维护源，KEEP配置/原件/消费状态区分 | config只装声明，不把运行registry或已接受包按JSON后缀搬入；双端迁移、E49/E50 |
| M13 读包合同/通用工具 | current_state兼任原语，product文案参与身份；多reader/前后端消费 | REPLACE归属、窄合同；减少错向import | 单文件认证≠整根hash、显示与记录身份版本，G1/G3/G5 |
| M14 Collector/预算/files | 读族借机构reserve；共享client计数/候选；各reader消费 | CONSOLIDATE资源owner，REPLACE跨业务私有借用 | deepcopy/assign、原预算不可rollback、可选失败隔离，T3/G6 |
| M15 Git发布/本地输出 | 原子报告/原件custody/综合R/News不同；Smart control依赖已发布专用state | CONSOLIDATE机械I/O，KEEP各操作合同 | 发布未读入不能再花来源预算；显示失败不抹已核进度；no-replace/unknown pointer，E46、T5/G3 |
| M16 研究→产品/重入 | registry/work-ref/#601/Brief接续；研究者与Human消费 | CONSOLIDATE资产与请求入口；更正可发现 | 保存≠研究完成/接受/持仓；真实Quick→Brief、更正与原时钟，G5 |
| M17 Workbench client | 19生产模块中的14client已核；迟到/跨R/原文保全 | CONSOLIDATE读取/视图；候选框架仍比较 | 保原native机制或等价替代；全测试/browser/手机与成本，G5/G6 |
| M18 Workbench server/host | 5server与shared依赖，owner/token/permit/固定ref；原host消费 | KEEP读写隔离，CONSOLIDATE窄host合同 | 可信边缘/无旁路、凭证轮换，暂停不等免审；G5，未授权不部署 |
| M19 tests/fixtures/eval | 同义重复、跨test import和不同消费者保护 | CONSOLIDATE必要fixture；RETIRE真实失去义务的专属项 | collection身份/拒绝传播、研究质量与CI分开；G4/G6 |
| M20 CI/自动化 | 四scope/分片/环境/证据已有代价；PR/main/publisher消费 | CONSOLIDATE重复实现；对照更简单完整执行 | 原正式full及严格reuse不提前放宽，比较同范围实际时钟，G6 |
| M21 依赖/打包/供应链 | extras/dev重复约束、两个包资源owner；轻core/生产/native/dev消费 | CONSOLIDATE维护源，复用原生包装工具 | 安装后资源、隔离extras、许可/更新/退出，T7/G6 |
| M22 文档/治理/接手 | 已统一原则；旧NEXT和长证据易混 | CONSOLIDATE当前决策与精确证据路由，RETIRE过时指针 | 不删除失败/原话；真实独立上下文不是换角色，G7 |
| M23 one-shot/兼容/退出 | 旧名含现役Retainer，历史脚本/CLI/手工消费者 | RETIRE精确无职责入口；KEEP必要reader，CONSOLIDATE共享实现 | 无import或年久不证明可删；专属tests/config与consumer一同处置，G4 |
| M24 XHS/third_party/资源 | XHS消费旧Deep，voice消费harness，style resource随包 | CONSOLIDATE外围authoring；DEFER新增启用而非审查 | 保选定声明/OMIT、旧输入adapter与本地输出合同；人工用途/资源许可仍核，G1/G4/G6 |

当前无证据允许立即删除任何整块目录或所有旧版本合同。E22的旧自动边是明确退役候选；E41/E45则是不能删v1/旁支的正例。KEEP必须有依据；UNKNOWN的大域不可全部移入DEFER来签A1。

## 7. 有证据的旧→新迁移映射样本

以下给出实际名称和目标归属，状态均为**DESIGN_ESTIMATE / NOT MIGRATED**；不是宣称每项完整消费者已穷尽。每个实际切片在P4前还要补齐其完整测试、动态/手工调用、source-effect与退出证据。目标路径只是K2-ADR-T被采纳时的建议，不使旧路径立即失效。

| 现有责任／目标建议 | 已知消费者与净收益假设 | 迁移、恢复、回退与停止条件 |
|---|---|---|
| rehearsal中的轻framing类型 → `domain/rehearsal_context.py`；其它rehearsal仍独立 | research_commit、live、workflow和方法；减少仅借类型牵动Odds | 类型身份/JSON/hash和旧public import分别核；不动信息hash语义；完整caller迁出后才退旧代理，T1/T2 |
| research/claim合同v1/v2与source_policy → `methods/quality/`保留原版本模块名 | v2→v1、现有case测试和旧Deep消费 | 不改变assessment结果/schema容许范围；shared domain不反依methods；历史serialized读取与公开入口回退，E41 |
| research_commit_only的安全文件原语 → `infrastructure/local_files.py`；研究/结果保管 → `application/research_delivery/` | Odds、研究比较、TDX成员/价格、独立股票、历史replay脚本 | 精确保留原件先存后验、两文件原子报告两种合同；旧脚本不可静默改写。支持旧环境或有限旧import的选择待G3/G4，不能仅全仓rename |
| canonical/provisional/conditional → `domain/odds/`的分立实现；原qualified Market adapter仍外置 | spine、保管、Human分析及同Research比较 | 共享`_committed`/payoff须原字段/概率/时钟反例；每种旧result独立重建；不加自动互转或市场fallback |
| cli/live → `interfaces/cli.py`＋`application/live_decision/`和公告用例 | 原五命令、console script、workflow/shell | 保持旧命令/参数/错误码与无授权不执行；help与离线子命令不构造市场fetch；旧入口代理有退出条件，未核其runtime尾部前不施工 |
| policy_data的Odds政策 → `application/live_decision/policy_data/`；样式资源 → `application/publication/policy_data/` | 两个importlib.resources loader、setuptools package-data与XHS voice | 原资源bytes不改，显式新loader/package-data、wheel/sdist实物检查；从仓库外执行验证，不把editable成功当完整安装证明 |
| XHS harness/voice → `application/publication/`及独立CLI薄接入 | 旧Deep claim catalogue、voice、人工命令/草稿 | 先保旧Deep adapter再考虑方法无关输入；选定声明/OMIT/无自动发文不变；草稿覆盖不伪装原件custody，人工使用G4待核 |
| registry/输入数组 → `config/<owner>/`，读用途例`config/reading/purposes.json` | Collector、archive/index、B2、Watch、intake；execution-inputs另有owner | 一套新writer/consumer迁移，不把不同用途合并；旧R/旧packet继续按原path/schema；先查workflow数组与push/外部trigger，不回填消费历史 |

来源控制本批新增五个同表范围的映射，仍为DESIGN_ESTIMATE：

| 当前责任 → 目标建议 | 已知消费者／改进目标 | 不可跳过的迁移证据 |
|---|---|---|
| smart_money_view.state → `application/smart_money/progress.py`；原control → 同能力control | capture、reading、control、原工作流和测试；避免页面模块拥有未来采集进度 | 原state JSON/首次与后继结果相同，丢history不重置；保原R locator与未发布原件等待；先迁reader/control再退旧view导出 |
| global_*_context纯plan/日期/codec → `observations/global_market/`；capture → `application/global_market/` | 两工作流、global_market_reading、现有CLI；让重放不依赖网络执行实现 | v1/v2、不同attempt上限、partial/无回执/单位/日期反例；原saved summary与拒绝保持，不改历史源码原件 |
| economic capture的PublicResponse/安全HTTP助手 → `infrastructure/http/`窄实现；业务绑定仍归economic | global_public_context及economic捕获，CLI/workflow；解除借工具导入业务parser | 只共享同义机械合同；公共Global保管HTTP失败body与economic不读取HTTPError body的不同策略保留；旧implementation hash映射先设计，不能拔验证 |
| RSS源registry与native scan/execution历史 → 两个独立应用owner及各自codec | prepare-native-rss-successor、native-feed-acceptance、原源/股票多用途workflow | `runpy`相邻脚本调用、source/market/history三个locator、failure可保管不改success；init/continue边界、原上传封装及容量不自动清理 |
| disclosure_radar分组 → `observations/disclosures/`；disclosure_research旧method适配 → `methods/`或公告用例 | CLI及原assessment；减少轻分组依赖旧Funnel | Research cutoff跨批仍保整批；原Evidence集合、补充证据不覆盖、旧方法输出/旧命令保持；assessment/receipts/HTTP尾部闭合后才移动 |

一个可执行切片还须列：M与采纳决定、精确base/head及old→new、全部直接消费者及已证下游、外部实现选择、正/负/历史样本、预计与实测成本、格式reader/writer切换顺序、production影响、恢复、回退与旧责任退出。未审消费者阻该切片，不阻无关已获准文档工作。

## 8. 完整迁移、工程与验收

### 8.1 W1–W8保持全局目标

| 批次 | 全域目标与映射 | 前置与独立确认 |
|---|---|---|
| W1 公共合同/保护样本 | M01–04/11/13/16/19；把能力合同、命名/owner与原正反例固定 | P3整体采纳；实际diff→trigger→source effect对账；不切生产数据 |
| W2 共享原语/资源 | M01/05/10/13–15；窄类型、文件/传输、预算/files owner | 真实消费者与Reuse选择；same bytes/异常/预算；旧重复/转发真正退出 |
| W3 用例/producer/恢复 | M04/06/08–10/12；三种依赖边、job/step资格、#581记忆与§3.4进度/消费账 | G2/G3；先核Smart publisher反馈和RSS双历史；保持时钟/权限/有限恢复，不能同时双写或清账 |
| W4 来源/观察各族 | M05–07；Sector/Stock/News/Industry/economic/D及财务输入 | W1/W2及相关W3；逐族垂直迁移；原件→最终消费者，无重采；旧指纹保全、新回放闭包缩小 |
| W5 方法/档案/历史 | M02/03/11/12/16/24；旧Funnel、generic、Single Quick、存取/中文原名 | G1/G3；不同hash/格式与两类保存失败不混；reader先、writer后；回退仍读已发布格式 |
| W6 读包/发布/Workbench | M13–18；显式可选组合、三类效果、独立时钟与产品重入 | 相关W3–W5；T3/T5及原host/client、跨R/迟到拒绝；Sites不自动部署 |
| W7 测试/CI/依赖/文档 | M19–22；fixture/义务、安装资源/环境、供应链与可恢复入口 | 从W1量化且贯穿所有批次；同保护集合/环境，工具采用另核，不放宽现役门禁 |
| W8 旧执行/过渡退出 | M03/08/11/19/22–24；具体旧入口/别名/专属测试/配置 | G4及相应consumer迁出；旧原件与必要reader保留，四类退出分别签收 |

W4/W5可依实际依赖调序，W7贯穿，不同时展开多批生产迁移。重排需在#508说明原因和整体目标映射。旧S1属W5，S2属W2/W6，S3是W4/W6的一个样本，S4属W7；都不是全部范围或默认顺序。

### 8.2 保持现役验证，比较降低义务的替代

CI继续原content/draft_feedback/full/merge_reuse；当前设计路径不在内容白名单，正常Ready走完整验证。对照现行复用、较简单完整执行、保留证明但减少重复安装/collection/聚合三类方案，采纳前不改合同。full、独立main、publisher、浏览器、产品使用分别验证；不拿旧head或最快分片代替新head完整结果。复用原workflow_call/composite/actionlint/pytest split/xdist，不自建选择器或调度平台。[CI]

字段反例尽量直接测实际owner，保必要真实消费者/失败传播；测试退役依据义务结束而不是数量/年代。保持原byte/hash/库存/环境，ZIP当数据不执行。依赖管理比较现有pip/setuptools、constraints/lock/uv及候选框架实际环境；原Action精确版本与升级策略全域核查，不顺手增权/升级/改钟。未取得安全告警不能写成零漏洞。

文档沿AGENTS→NEXT/#297→#508→当前设计/原证据；原则正文只有WORKING-PROTOCOLS。每轮交接有精确head/PR/验证、在途或未知效果、下一步和停止条件。不要把文档合并与待审架构采纳互锁，也不因此把P3签收。

### 8.3 A1–A8整体完工

| 验收 | 必须成立 | 不能替代的证据 |
|---|---|---|
| A1 全域处置 | 重要模块/永久责任都有消费者证据与明确决定，关键UNKNOWN闭合 | 目录树、矩阵行数或全域DEFER |
| A2 目标结构 | 采纳的能力/依赖/名称/owner/公共面在真实代码与安装/产品成立 | 六目录存在、无环import或多层Facade |
| A3 语义与历史 | PIT/单位/时钟/Research/Odds/Human、旧包旧R与新格式回退可恢复 | hash存在、一次CI绿或版本号2.0 |
| A4 执行与恢复 | 档案、运行、发布分别有原件/失败/unknown效果/实际消费证据 | 一个ZIP恢复或publisher成功 |
| A5 永久复杂度 | 被接替的旧责任/兼容/专属维护真实退出，代表任务呈系统性改善 | 代码/文件/测试/依赖数下降 |
| A6 工程反馈 | 同范围和可解释环境下安装、collection、fixture、CI/证据成本达到采纳目标 | content对full、单次提速或漏计上游升级 |
| A7 产品与独立接手 | 真正新上下文从入口恢复并完成代表任务；产品边界及可用性成立 | 同会话换角色、未部署UI或Human搬材料 |
| A8 收口 | 采纳目标完成或范围变更获准；DEFER有owner/风险/触发，Human裁定发行范围 | 无限等零缺陷或把难域从范围删掉 |

### 8.4 T1–T7成本与模块化共同样本

T1改领域资格；T2换研究方法；T3已有保存源增加用途/替换具体reader；T4档案格式/命名演进；T5未知效果与恢复；T6视图/host及可选能力停用；T7依赖/验证与安装资源。相同需求比较实际修改owner、跨边界传播、重复规则/fixture、适配/旧reader、请求/恢复步骤、安装/CI/升级/退出成本。静态推演记DESIGN_ESTIMATE，真实受控执行才MEASURED，模型思考时长不作为生产成本。

共同反例继续：News历史恢复失败不妨碍独立当前采集但保缺口；D候选撤回不退API预算且保价格/研究；未知dispatch先对账；Sector过期不靠cache/综合R续跑；#581非同target成功不擦旧gap；资料转存不自动研究；原R/坏原文/迟到回包拒绝。候选只接管纯计算时按该范围计收益，不因不管理Git就宣判失败；完整采用若声称接管恢复则必须实际证明。[V23][REUSE]

本版E46–E51另要求将§3.5共同反例放入原T3/T5/T7；本轮18函数案例仅补控制行为正反例，不冒充这些跨模块验收已完成。通过完整CI也不能将“progress在R中被读取”扩大为全部生产状态已安全迁移。

P1的#799 full累计613作业秒、main34秒、publisher138秒仍是历史样本，不是本轮收益。最终量化阈值须在G6同口径基线取得、P4前采纳；现在不编造百分比。若新增结构/外部适配使总负担增加，应调整设计，而非降低完工标准。

## 9. G1–G7剩余证据与下一决策包

| 门 | 本版已补 | 尚未完成、验证方式与受限动作 |
|---|---|---|
| G1 依赖/公共消费者 | 29顶层正文与声明图、4个runtime执行/存取接点、console/package-data；前驱19生产mjs图保留 | CLI向runtime/adapter尾部、来源控制与动态/手工/外部消费者仍需追踪；不得称全源码闭包或据此全局删除 |
| G2 producer/配置/资格 | F02 control/capture反馈、F03/04两Global codec、F01 native acceptance/history、F10/11 capture/输入及两公告尾部；E46–51与具体迁移表 | feed intake/consumer内部、Smart各source parser/docs/Relay尾部、economic discovery/review、stock其余purpose与公告assessment/receipts/HTTP仍未全审；优先补影响状态替代和退出的实际调用，不重复本版11文件 |
| G3 状态/档案/恢复 | 原件先存后验、报告原子发布、Odds同Research恢复、execution pair与旧路径约束 | 真实历史原件/全部work-ref、容量/期限和恢复演练；验证旧R、新writer及回退，不从代码阅读签实际恢复 |
| G4 退出 | v2→v1/XHS/历史脚本及runpy/control为明确正例；四类退出与新增来源映射 | 原owner意图、manual/CLI/external trigger、全部专属fixture/配置；支持期/等价reader明确后才能退出 |
| G5 产品/host | 继承Workbench生产声明/三份测试源码和权限/迟到结果证据 | 余下12份test.mjs、browser、真实host可信边缘/资产/无旁路和Quick→Brief/更正；Sites暂停不免审、不擅自部署 |
| G6 成本/测试/候选 | 具体T1–T7、原pluggy/dlt源码审阅、dlt高级state合同及18项control函数行为检查；不是成本实测 | 全fixture义务、实际代表任务基线、必要候选隔离试验/许可/依赖/副作用、完整架构对比；试验不自动获准 |
| G7 独立接手 | 通过唯一入口恢复本轮并留下可定位后继 | 真正新上下文或维护者的独立任务证据；本会话不能自签 |

**下一包：优先闭合G2的feed intake/consumer与economic discovery/review，再对其可定位的保存样本补G3历史恢复证据；把结果回写§3.4状态归属和§7迁移表。** Smart parser/Relay、stock其余purpose及CLI assessment/receipts/HTTP尾部仍明列；按是否阻碍当前决策排序，不以换领域隐藏缺口。 不再重读已核29顶层正文、33文件静态范围和19生产mjs，不重做P1/P2；有新diff或真实矛盾才重开相关部分。G3/G4/G5/G6/G7保持未验，不藏到DEFER。

Human无需重批全面审查、Reuse/Modularity、统一原则或普通设计文档。最终仍需裁定：具体目标拓扑和外部实现接管范围、受支持公共/旧reader与精确RETIRE清单、长期恢复/保管变更、成本/CI门槛、候选试验/依赖采用、P4批次以及产品部署/发行。K2-ADR-N/T从“只有候选分类”推进到明确建议，不等于最终采纳或逐切片映射全部齐备。

C的2026-10-08/09/12/13/14自然窗、D冻结/成熟结果与#351/#621/#581等原责任继续。Sites暂停、禁Codex、分钟STOP、新城暂缓不变。本文不自动批准新来源/模型请求、依赖安装、生产迁移、批量删除/重命名、权限、持续费用、隐私外发、任务时钟、Watch/交易或v2.0.0发行。

## 10. 精确来源与证据入口

本版新增代码固定M=`6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc`；旧v2.4/v2.3证据保留原commit。官方滚动dlt页于2026-10-10读取，新advanced-state文档固定在原候选commit；旧pluggy局部审阅不扩大为完整采用。没有复制第三方实现或安装新包。实际PR/head、受控函数原始检查、完整CI、合并与正常发布以#508最终交接为准。

报告原语反向搜索还定位到以下实际调用者；本轮只消费其命中接点，不声称已完整重读每个调用者：

- [src/decision_kernel/runtime/research_comparison.py](https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/runtime/research_comparison.py)
- [src/decision_kernel/runtime/tdx_membership_comparison.py](https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/runtime/tdx_membership_comparison.py)
- [src/decision_kernel/runtime/tdx_member_price_join.py](https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/runtime/tdx_member_price_join.py)
- [src/decision_kernel/runtime/reviewed_activity_census.py](https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/runtime/reviewed_activity_census.py)
- [src/decision_kernel/runtime/independent_stock_observations.py](https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/runtime/independent_stock_observations.py)
- [tests/test_atomic_report_publication.py](https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/tests/test_atomic_report_publication.py)

[OWNER]: https://github.com/auguspp/decision-kernel/issues/508
[PLAN13]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6097686457
[PLAN12]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6096068040
[PLAN11]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6095772144
[PLAN10]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6094482452
[PRINCIPLES]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/WORKING-PROTOCOLS.md#project-principles
[V23]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/docs/kernel-2.0-design.md
[HANDOFF12]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6097955454
[START13]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6098096510
[P1]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/docs/kernel-2.0-architecture-map.md
[P2]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/docs/kernel-2.0-prior-art.md
[REUSE]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/docs/kernel-2.0-architecture-reuse.md
[OLD]: https://github.com/auguspp/decision-kernel/blob/9290df46052f823a96069932321ae50b016af65c/docs/kernel-2.0-design.md
[ROOT]: https://github.com/auguspp/decision-kernel/tree/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel
[RETENTION]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/runtime/research_commit_only.py
[ODDS-RETENTION]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/runtime/odds_retention.py
[EXECUTION]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/runtime/external_research_execution.py
[EXECUTION-ID]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/runtime/external_research_identity.py
[PROVISIONAL]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/provisional_odds.py
[CONDITIONAL]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/conditional_odds.py
[RC1]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/research_contract_v1.py
[RC2]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/research_contract_v2.py
[CA1]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/claim_audit_contract_v1.py
[CA2]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/claim_audit_contract_v2.py
[SOURCE-POLICY]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/source_policy_v2.py
[V2-TEST]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/tests/test_yto_full_research_v2.py
[CLI]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/cli.py
[LIVE]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/live.py
[POLICY]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/policy.py
[PACKAGE]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/pyproject.toml
[XHS]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/xiaohongshu_harness.py
[VOICE]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/xiaohongshu_voice_pass.py
[REPORT-USERS]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/docs/readings/c2-shanshui-transmission-2026-10-01/replay.py
[PLUGGY]: https://github.com/pytest-dev/pluggy/blob/fd08ab5f811a9b2fa9124ae8cbbd393221151e2c/src/pluggy/_manager.py#L122-L315
[MOD-REQ]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6097504982
[NAMING-REQ]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6036481124
[NAMING-CORRECTION]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6036531643
[PEP8]: https://peps.python.org/pep-0008/
[ARCHIVE]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/runtime/research_archive.py
[ARCHIVE-INDEX]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/src/decision_kernel/runtime/research_archive_index.py
[PYPA-SRC]: https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/
[PY-RESOURCES]: https://docs.python.org/3.12/library/importlib.resources.html
[PYPA-ENTRY]: https://packaging.python.org/en/latest/specifications/entry-points/
[CI]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/docs/CI-MAINLINE.md

[V24]: https://github.com/auguspp/decision-kernel/blob/6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc/docs/kernel-2.0-design.md
[HANDOFF13]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6098430990
[START14]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6098747928
[SM-CONTROL]: https://github.com/auguspp/decision-kernel/blob/6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc/.github/scripts/smart-money-control.py
[SM-CAPTURE]: https://github.com/auguspp/decision-kernel/blob/6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc/src/decision_kernel/runtime/smart_money_capture.py
[SM-STATE]: https://github.com/auguspp/decision-kernel/blob/6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc/src/decision_kernel/runtime/smart_money_view.py#L1-L95
[SM-READING]: https://github.com/auguspp/decision-kernel/blob/6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc/src/decision_kernel/runtime/smart_money_reading.py#L250-L334
[GLOBAL-RELAY]: https://github.com/auguspp/decision-kernel/blob/6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc/src/decision_kernel/runtime/global_market_context.py
[GLOBAL-PUBLIC]: https://github.com/auguspp/decision-kernel/blob/6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc/src/decision_kernel/runtime/global_public_context.py
[RSS-PREPARE]: https://github.com/auguspp/decision-kernel/blob/6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc/.github/scripts/prepare-native-rss-successor.py
[FEED-ACCEPT]: https://github.com/auguspp/decision-kernel/blob/6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc/.github/scripts/native-feed-acceptance.py
[FEED-HISTORY]: https://github.com/auguspp/decision-kernel/blob/6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc/src/decision_kernel/runtime/radar_feed_history.py
[ECON-INPUTS]: https://github.com/auguspp/decision-kernel/blob/6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc/src/decision_kernel/runtime/economic_release_inputs.py
[ECON-CAPTURE]: https://github.com/auguspp/decision-kernel/blob/6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc/src/decision_kernel/runtime/economic_source_capture.py
[DISCLOSURE-BATCH]: https://github.com/auguspp/decision-kernel/blob/6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc/src/decision_kernel/runtime/disclosure_radar.py
[DISCLOSURE-METHOD]: https://github.com/auguspp/decision-kernel/blob/6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc/src/decision_kernel/runtime/disclosure_research.py
[SM-TEST]: https://github.com/auguspp/decision-kernel/blob/6d8b7a4dd14560eb739a9984b4a9cc0b8d97bebc/tests/test_smart_money.py
[DLT-STATE]: https://github.com/dlt-hub/dlt/blob/2360d229c77f7f64692acc31a4555f4cfcd50ed3/docs/website/docs/general-usage/incremental/advanced-state.md
[DLT-CURSOR]: https://dlthub.com/docs/general-usage/incremental/cursor
[DLT-LAG]: https://dlthub.com/docs/general-usage/incremental/lag
[DLT-REST]: https://dlthub.com/docs/dlt-ecosystem/verified-sources/rest_api/advanced
