# Kernel 2.0 — 全局目标架构与渐进重构方案 v2.8

日期：2026-10-11（Asia/Singapore）。设计ID：`K2-DESIGN-20261011-v2.8`。唯一计划、技术采纳与接续入口：[ #508 ][OWNER]。有效计划为[v1.3][PLAN13]与[v1.2][PLAN12]、[v1.1][PLAN11]、[v1.0][PLAN10]未替代条款；长期原则只从[统一项目原则][PRINCIPLES]读取。

**P3 GLOBAL DESIGN PROPOSAL / 待审。C/N/T和具体迁移均PROPOSED；P4/P5未启动。** 本版交付不代表整体架构采纳、runtime缺陷修复、生产恢复或投资权限。普通设计文档与证据交付可正常PR/验证/合并，工程结果与技术采纳分别记录。

## 0. 版本关系与阅读方式

本版承接[#808合并的v2.7精确前驱][V27]及[16交接][HANDOFF16]；本轮[开始17][START17]、[实际结果][RESULT17]与[完整原件附件][EVIDENCE17]可直接恢复。代码基线M=`7e770c6704cd3cfdcf496e276bb0bbceb98b106e`。已实时恢复main、AGENTS、适用统一原则、NEXT/#297、#508，开始时开放main PR为空；写入前main再次相符。

**本版把当前主文收敛为决策包，不再逐轮复制全部审计叙述。v2.7的完整细节按下表明确并入本版，只有本文写明的新增证据、处置建议和下一步替代相应旧条款。** 这不是把前驱降格为失效历史：原9类命名、14类永久对象归属、17项迁移样本、24M、W1–W8、A1–A8、T1–T7、G1–G7及全部未验责任继续有效。任何实施切片仍须打开其精确附件，不能只读本页摘要就开工。没有新计划、状态库或第二审批平台。

| 持续有效的精确材料 | 本版继续消费的完整内容 |
|---|---|
| [v2.7 §1.1、§8.5][V27] | Human长期演进L1–L5、七项准备R1–R7、Level A/B及其防止无限普查的边界 |
| [v2.7 §2][V27]及其v2.3–v2.6前驱 | E21–E62、F01–F12、原源码范围/来历、原件恢复与拒绝、13项接缝检查；未查部分不因本轮变成已查 |
| [v2.7 §3–5][V27] | C/N/T全部候选与反例、能力定义/提供者/消费者、状态owner、4类退出、恢复4项合同、9命名/14对象体系 |
| [v2.7 §6–8][V27] | 24M完整问题与消费者、17项旧→新映射、W1–W8、A1–A8、T1–T7及原成本/验证边界 |
| [P1][P1]、[P2][P2]、[架构Reuse附录][REUSE] | 已有固定成本、上游审阅和候选；只复用实际已覆盖范围，不重新宣布完整采用或审计 |

**本轮改变的实质：** E60已从“只测一个原AST函数，待补完整阶段影响”推进为“原Smart采集/磁盘重放/实际读取阶段及另一个Global消费者在有界离线输入下已复现、隔离与保管边界已查明”。缺陷仍NOT_FIXED；不再将同一接缝反复排查作为唯一下一步。后续转向Level A架构实现来源、历史支持/净成本取舍与首切片准备。

## 1. 目标与当前推荐

全面是审查、设计和处置范围，渐进是实施方式；不预设当前拓扑正确，不要求全部重写，也不能用少数局部修补替代整体长期改善。目标是降低维护、扩展、兼容、验证、恢复与接手总成本，同时保护已证明必要的语义和历史。[PLAN11]

| 决策 | 当前推荐，仍PROPOSED | 仍须裁定的关键问题 |
|---|---|---|
| K2-ADR-C 能力与组合 | 用例明确必需/可选能力；定义随语义owner，提供者在显式组合点连接；来源取得、解释、用途资格、执行/消费记忆分开 | 原生显式组合、成熟组件及可行完整架构按同样任务和退出成本比较；不能以现有目录反向排除外部接管 |
| K2-ADR-N Naming & Identity | 机器ID、原Unicode名、显示名、路径、schema/方法/软件版本与不同业务时钟分开；规则向前统一 | 公共路径/资源、碰撞、旧格式和新writer回退的支持范围；不批改旧ID/hash/原件 |
| K2-ADR-T Topology & Ownership | 单仓单主要Python发行单元，6类代码责任域；application内按能力组织，无全局万能contracts桶 | 具体实现来源可能改变组织；不先建空目录或多层Facade，再补收益论证 |

```text
src/decision_kernel/
  domain/          身份、PIT、必要值对象、确定性算术与权限不变量
  methods/         可替换研究方法、质量/source-role政策和旧方法合同
  observations/    来源族纯转换、模板、codec与计算
  application/     研究交付、来源、消费、reading、publication等用例
  infrastructure/  受约束的HTTP、GitHub、本地文件和环境技术实现
  interfaces/      CLI、宿主入口与显式composition
workbench/         原产品前后端边界
.github/           原生workflow/action与薄工程入口
```

domain不反依其他域；methods/observations依必要domain，不借publisher。application依语义和窄端口；infrastructure不反依含执行的用例；interfaces负责组合。旧public import、CLI和package resources有有限兼容/退出方案，不要求所有私有接口永久冻结。具体路径尚未创建或迁移。[V27]

### 长期演进要求不变

Human“希望没有3.0”落实为可重复的小范围改变，而非架构永不改变或提前实现全部未来能力。L1能力可扩展组合；L2关键实现可渐进替换；L3历史连续可解释；L4旧责任真正退出；L5全生命周期净成本受控。继续映射原ADR、A/T验收，不增加第三套原则或评分平台。[LONG][V27]

P5须证明代表任务的局部演进可重复，而不只是一次演示。模型、方法或来源更新不继承旧Human接受；旧writer退出不自动删除历史reader；临时适配必须有实际消费者、owner、支持范围和退出条件。原1.0的研究记忆、判断校准和方法演进愿景不是本轮新启用授权。[LONG]

## 2. Naming、永久对象与状态责任

完整规则保留在[v2.7 §4–5][V27]。以下是采纳时必须一起读的主张，不以短表替代原反例。

| 对象类别 | 向前规则与保留边界 |
|---|---|
| 分发/导入/命令 | 保持decision-kernel / decision_kernel / 原console入口；架构2.0不等于包v2.0.0 |
| Python | 新模块snake_case、类CapWords；不为统一风格批改序列化字段或旧状态token |
| JS/workflow/文档 | 依语言原生惯例；job/step/title/path可被真实消费者引用或触发外部效果 |
| 机器身份 | 保各对象原UUID/hash/证券/source规则；标题和路径不自动成为永久身份 |
| 原名/显示/路径 | 原Unicode与bytes保留；新机器目录默认ASCII，显示可中文；不静默规范化或合并碰撞 |
| 来源/资产名 | logical security、provider code、工具/传输与经济证据出处分开 |
| 版本 | schema、方法、算法、研究revision、软件独立；受支持v1不是应被一键删除的旧物 |
| 时间 | session、发布、可得、取得、接受、计算、显示分开；重放不刷新原资格或执行期限 |
| 格式内部文件 | 原固定库存与raw/semantic hash分别保留；同名JSON不等于同一种完成记录 |

14类永久对象的完整owner/位置/可变性继续：[v2.7 §5.2][V27]。核心代码、当前配置、执行请求/消费记忆、方法文档、人读研究、typed档案、来源原件、producer状态、Human记录、派生读包/缓存、健康/进度、tests/fixture/eval、工程指南/ADR、第三方资源不能因文件后缀相同合成一个全局桶。配置不装运行registry；原件、索引、来源声明和用途接受不互相代签。

**状态边界继续保护：** Sector强恢复状态不由综合R代替；Smart专用进度经reading交付control，不使整个R成为通用恢复权威。RSS初见/版本registry、scope扫描、限时market execution分账；quiet可以仍带旧失败plan。公告prepare attempt与quiet semantic receipt分开，DEEPEN不写quiet回执。economic source-review保recorded/eligible_from和原INCOMPLETE，声明reviewer不是身份认证。[V27]

**恢复四项责任：** 原件库存/存放、受信任历史reader、兼容运行环境、后继可执行动作分别确认。v2.6一项真实四原件重放通过，另一旧Python环境仍被原验证器拒绝；原code/hash相等不足以声称全域可恢复。原环境保管、经验证具体兼容reader、降低可执行恢复承诺是不同选项，后者不能未经采纳成为默认。[V27]

## 3. E63–E65：完整本地阶段带来的新证据

### 3.1 输入、方法与可复现原件

固定上述M，21份原文件均核Git blob、UTF-8与AST。16份目标/基础模块整文件导入；5份旁路依赖只抽取8个未修改定义/常量，源码区间及片段hash保留。空namespace initializer与未调用的Research导入sentinel明确记账。不是21份全新未知文件、所有分支覆盖或全仓真实import闭包。[EVIDENCE17]

原primary capture/磁盘replay、原Relay client/采集/磁盘replay、原Smart native/read_run、Collector ZIP验证/存取、history/state、可选补充、展示生成及canonical JSON实际运行；另运行Global Shibor capture/replay。只替换外部transport与GitHub API输入为合成对象，没有替换目标validator、ZIP完整性、实际Collector或共享预算函数。网络/socket和子进程禁止，尝试0；sleep记录而非等待。[EVIDENCE17]

预装Python3.13.5、Requests2.32.5、BeautifulSoup4.14.3、pydantic2.13.5，无安装。未执行默认live HTTP、Collector.collect、CLI/workflow进程、remote publish、浏览器JS、PDF解析、真实生产档案或候选框架。合成run/date/key不作为真实GitHub运行、交易日或线上事故证据。

| 组别 | 最终检查数 | 实际含义 |
|---|---:|---|
| 原primary capture与磁盘重放 | 1 | 19次合成请求、20分区；两条北向成交观察可读，18个其他分区缺口显式保留 |
| Relay正常计划v1/v2/v3及reports-only | 4 | 分别5/5/11/7次合成请求；原采集/磁盘重放可读，不把单页合格说成全市场覆盖 |
| Smart当前失败回执 | 6 | timeout、connection、request_error、timeout_then_success、nonJSON403、nonJSON429复现未修复矛盾 |
| 旧形状失败回执 | 1 | 合成副本去除诊断字段并重算自身hash后仍是UNAVAILABLE_NOT_QUIET；不是恢复了真实旧run |
| 原Smart实际读取与隔离 | 11 | 无补充、正常补充、六故障、不同日期/run的前驱、历史恢复、坏ZIP摘要；主源与其他资料保留 |
| 原Global正常/故障接线 | 4 | 正常AVAILABLE；三种原client故障变成显式未知回执 |

**合计27：18项现有行为符合预期，9个案例复现两类未修复协议不兼容，不是27项来源成功或9个独立缺陷。** 最终脚本在两个新目录运行、结果bytes相同，不称54项独立测试。它们不是本次正式CI新增的永久用例，也不是新架构净收益实测。[RESULT17][EVIDENCE17]

完整脚本27627 bytes，SHA256=`57aac3b3ac0d5e074a36dc5e407661ab59c2e0f255650ccd08ad1010fa0ea058`；完整输出24042 bytes，SHA256=`76b21fae69616587fef2f45e387756734d22c101cd0baa7b399ff849f19dfcac`。附件使用标准gzip/base64的固定文本分块，只保管三份文本，不被runtime或CI自动执行；decoder须先验hash/大小/固定文件集合。Issue简短复现摘录不是这份完整脚本，不能混用hash。

### 3.2 新证据与架构含义

| ID | 实际结果 | 具体设计影响/限制 |
|---|---|---|
| E63 Smart循环结束不是可消费完成 | 原capture保存capture.json、已有raw，并标execution_complete=true；随后原replay拒绝新增诊断字段或非JSON拒绝，summary未生成。**首次超时但重试成功**也被第一个attempt的额外字段阻断 | transport成功、取得保管、循环完成、可重放解释、对外交付分开。不能删失败attempt来让最终成功过关；E60不再仅是单函数猜测，仍NOT_FIXED |
| E64 原可选读取隔离有效但有明确保管界限 | 六类坏补充均标CURRENT_RELAY_READING_GAP，主source/state hash、非空无关lane、研究和sentinel保留。合成Git调用5→6，回退不退计数。坏补充ZIP从新读取包撤回，producer本地capture/raw仍在 | 保持独立主源提交和窄可选回退；“保住主源”不等于“坏补充原件已全部进入新R”。实际生产artifact可获取/期限另验；不据本地fixture宣称线上原件永存 |
| E64的历史反例 | 前一天run16001的正常primary/Relay由原链产生并读取；当前run17001坏补充仍可沿旧locator恢复，旧cutoff和主历史first_seen保原日期，当前gap继续显示 | 旧READY只能作为旧补充状态，不升级为当前成功；旧接受/日期不刷新。不能用同一个合成run改状态冒充前驱连续性 |
| E65 相同client还有另一个受影响consumer | Global Shibor对超时后成功、连接错误、非JSON403，在保存前的自身严格边界转为REQUEST_RECEIPT_UNAVAILABLE、attempts=[]、次数null，无raw文件；正常对照AVAILABLE | 不能只修Smart就宣布共享回执全面兼容。Global的“可读未知失败”不同于Smart的“已保存但解释拒绝”；新reader不能恢复旧记录里从未保存的细节或补造次数。未验证所有族/Stock/Auction或线上发生率 |

**本轮停止条件已达到：** E60在上述明确本地阶段的影响与隔离已查明，可形成修复/迁移裁定输入。此后只有真实diff、相关实施验证或新矛盾才重开相同排查。真实生产影响、其他消费者、CLI/workflow和权限仍未代签，不为结束有界取证而隐去它们。

## 4. 回执兼容的具体处置建议

这是ADR-C/M05/M10的实现准备，**PROPOSED / NOT_IMPLEMENTED**。比较三种办法：回退client并删诊断；全局忽略未知字段/宽松JSON；先在实际consumer中明确有限兼容。推荐第三种：前两种分别丢掉真实失败信息或降低现有保护；不需要因此替换整个HTTP栈或新建provider框架。

| 处置 | 建议范围 | 必须保持的拒绝与退出条件 |
|---|---|---|
| 诊断扩展 | Smart与Global按原client实际产生的有限transport_error_type枚举建立读取支持；无该字段的旧回执仍按旧解释；新增值与classification/http_status/body缺席的关系一并核对 | 不接受任意未知字段/诊断字符串，不从异常prose复制凭证；不通过删除旧attempt、重算历史manifest或扩大SUCCESS范围“修好” |
| 非JSON失败回执 | 对原client已经支持的有限HTTP拒绝/临时失败，核原bytes/hash/时钟/安全元数据和确实发生的解码失败，再验证原分类；作为失败可读，不作为数据成功 | 403/429仍停止且不重试；502等仍只按原该用途重试；未知HTTP/分类矛盾仍拒绝。正常JSON继续原严格业务/字段/日期/覆盖资格 |
| 原件与解释完成 | 保留source capture和用途解释各自完成条件；Smart现有checkpoint/主补隔离不拆掉；Global未来需要保留哪些已获原生回执，由其owner明确 | 不能以本次方案追填旧Global未保存的attempt/body；保存的失败也不授权重新执行、清消费记忆或退预算 |
| 共享定义与版本 | 先以受支持reader范围明确合同，逐consumer接替；固定可扩展字段、失败表示、原版本、适配位置、退出条件 | 请求计划revision与回执解释支持不是同一个版本；旧writer/旧reader分开退出。所有实际consumer相符前不宣布共享能力无缝替换 |

**拟最小代码范围**是原Smart读取校验和Global取得/读取边界及对应现役测试，不是改研究、市场数值、source taxonomy、任务时钟、凭证、权限或整个transport router。共享client不需要为了让旧reader过关而回退诊断。实际改动前仍核Stock/Auction等受影响接点、旧raw正反例、native workflow行为和各自预算；当前只确认Smart及Global Shibor的上述结果。

复用原Requests、JSON、原capture/replay、GitHub/Collector和现役测试工具，保持来源语义自有而机械实现可替换。前驱dlt等候选仍按其实际可接管层次比较；本条没有评估或采用新的依赖，也不等于G6完整架构取舍已完成。[V27][REUSE]

若独立缺陷修复需先于重构，由#508/#297按原权限对账为单独受控动作；本轮“继续规划”不自动授予runtime修复。E60只约束相关回执替换/修复的完成声明，不阻止无关的命名、历史支持和首切片准备。

## 5. 全域处置索引：不以局部接缝替代整体

下面保持M01–M24与原处置建议，完整问题、消费者、风险及证据仍由[v2.7 §6][V27]并入。KEEP/CONSOLIDATE/REPLACE/RETIRE/DEFER是建议，不是本轮已操作；重要UNKNOWN不得统一标DEFER来签完工。

| ID | 责任与建议 | 关键保护/本版增量 |
|---|---|---|
| M01 | 身份/PIT/权限：KEEP必要语义，CONSOLIDATE同义原语 | 原hash/bytes/时钟与拒绝不变 |
| M02 | Market/Odds/算术：KEEP各资格，CONSOLIDATE合理算术 | canonical/provisional/conditional不得静默互转 |
| M03 | 方法/旧合同/模型：REPLACE错位组织，KEEP必要codec | v2→v1、旧Deep、执行pair、接受与预算 |
| M04 | CLI/live：REPLACE宽入口为用例组合 | 原参数/退出码/输出/资源，无权不调用 |
| M05 | adapter/transport：CONSOLIDATE同义机械I/O，KEEP来源语义 | E63/E65有限失败回执兼容，非全局宽松解释 |
| M06 | capture/producer：REPLACE责任边界 | 枚举、循环完成、保管、可重放、交付不合并 |
| M07 | 纯观察/计算：REPLACE错向依赖 | 原算法/模板范围、无网络、适配成本 |
| M08 | workflow/资格：CONSOLIDATE原生接线，精确RETIRE | job/step/title/path-push和外部clock有消费者 |
| M09 | 状态/恢复：KEEP差异，REPLACE错位owner | Sector/Smart/RSS三账，失败/前驱不能清空 |
| M10 | 失败/健康记忆：CONSOLIDATE同义诊断 | E63/E65：已保存但解释失败≠无回执；未知次数不写0 |
| M11 | 档案/历史codec：CONSOLIDATE保管，审过宽闭包 | reader/环境/原件分别验，旧Unicode和失败 |
| M12 | 配置/registry：REPLACE重复维护，KEEP权威区别 | 不按JSON后缀迁config，原review资格/旧R |
| M13 | 读包/通用工具：REPLACE错位归属 | 固定R、单文件与根hash、显示与记录版本 |
| M14 | Collector/预算：CONSOLIDATE资源owner | calls不可回退，共享client不deepcopy；E64已做有界正例 |
| M15 | Git/本地发布：CONSOLIDATE机械I/O，KEEP完成差异 | E64主源独立保管，坏补充撤出新读包仍记缺口 |
| M16 | 研究→产品/重入：CONSOLIDATE资产/请求导航 | 保存≠研究完成/接受/持仓，Quick→Brief与更正 |
| M17 | Workbench client：CONSOLIDATE读取/展示 | 迟到/跨R/坏原文、浏览器/手机另验 |
| M18 | server/host：KEEP读写隔离，CONSOLIDATE窄合同 | 可信身份边缘、无旁路、凭证轮换；不擅部署 |
| M19 | tests/fixture/eval：CONSOLIDATE责任，精确RETIRE | E63–65跨consumer反例应随实际修复落到owner，不永久堆取证平台 |
| M20 | CI/自动化：CONSOLIDATE重复成本 | 四scope与同范围实测，原full/reuse不放宽 |
| M21 | 依赖/打包/供应链：CONSOLIDATE维护源 | 资源/wheel/sdist/仓库外启动，旧环境、许可/升级退出 |
| M22 | 文档/治理/接手：CONSOLIDATE唯一入口 | 本页当前决定、精确前驱细节、#508接续；不伪造独立评审 |
| M23 | one-shot/兼容/退出：RETIRE无义务入口 | 原manual/动态/历史consumer与4类退出分别核 |
| M24 | XHS/third_party：CONSOLIDATE外围authoring | 旧Deep/voice/style资源、选定声明/OMIT与原许可；新增启用DEFER不免审 |

## 6. Level A/B、首切片建议与迁移顺序

### 6.1 两级准备继续生效

**Level A整体采纳前：** 重要工程域有目标处置，影响根本owner/权限/公共合同/不可逆迁移的UNKNOWN闭合；C/N/T与成熟实现取舍、历史支持/回退、W1–W8/A/T、首切片充分映射和保护样本明确，并由Human对精确架构与实施范围正式采纳。无需现在穷尽晚期私有helper和全部fixture。[READY][V27]

**Level B每批改码前：** 精确base/必要R、原件与正负样本、直接/已知间接及动态/手工/外部consumer、路径/job/step/配置触发、原→新合同、预算/失败/可选缺席、CI/正常交付、未知写对账、兼容reader、回退、适配寿命及旧义务退出明确。一批一个受控主切片，不先搬文件后靠CI猜依赖。

| 本轮证据或剩余问题 | 当前归属 | 对进入下一步的影响 |
|---|---|---|
| E60本地采集/读取影响和隔离 | 有界取证完成，NOT_FIXED | 不再是重复普查任务；相关修复/替换的Level B必验输入 |
| 能力组合与完整外部架构取舍 | Level A / G6仍不足 | 影响C/T方向，不能拖到代码搬迁后再选 |
| 长期reader/原环境/兼容支持和成本 | Level A定支持策略；Level B验具体格式 | 不因一项恢复成功宣称全部可恢复，也不把无关切片全部锁死 |
| 精确调用尾部、晚期资源/fixture/host迁移 | 相关Level B；重大owner/权限部分仍在Level A | 不把所有晚期细节变成P3无限阻塞，也不隐藏重大未知 |
| 真实产品/新上下文/长期净收益 | A5–A8/P5，部分需事先定验收口径 | 同助手本地fixture和CI不能提前签收 |

### 6.2 拟首切片：先证明一个有实际消费者的轻合同能独立归属

**当前推荐候选为原§7的framing叶子类型拆分，归W1/M01–04；不是已开工或默认重构只做这一个类型。** 与之相比，先切producer状态/全面传输/Workbench部署具有更多不可逆效果和历史支持前提；E60修复可另行对账，不必冒充整个2.0架构。[V27]

原`NonAuthoritativeRehearsalFraming`定义位于`rehearsal.py`，`research_commit.py`、`workflow.py`、`live.py`、`research_workflow_v1.py`及相应用例tests有实际引用。当前M的有界反向搜索确认这些正例，不证明外部consumer穷尽。[FRAMING][COMMIT][LIVE][METHOD]

| 开工包项目 | 建议/仍须补齐 |
|---|---|
| 目的与目标owner | 将轻型非权威framing合同与Odds/Rehearsal重实现依赖分开；候选`domain/rehearsal_context.py`，路径以ADR-T采纳为前提 |
| 稳定公共面 | 旧public import有限重导出，保持同一类型身份；字段、默认值、JSON、schema/错误行为和原hash须实际比较，不据“只是搬类”宣布不变 |
| consumer次序 | 先支持新owner和旧入口，再迁已证caller；方法与研究提交不因此产生Market调用或新接受；无consumer时才退专属转发 |
| 原件/回退 | 不改历史数据或方法版本；旧/新包和仓库外安装可读；仅代码回退即可时也须验证，没有永久双轨许可 |
| 变更成本 | 记录实际import传播、需理解的owner、兼容残留、测试/安装/恢复成本；当前只有DESIGN_ESTIMATE，没有after实测或虚构降幅 |
| Level B尚缺 | 该批完整已知caller/动态public面、源触发影响、保护样本/正式CI、resource/package-data、临时shim退出与接受目标；不得凭本表启动 |

这是一个结构与变化传播样本，不用于绕开全域Level A。成功之后仍须覆盖W2–W8；失败或净成本变差时改候选，不降低历史/语义保护。领域特有值合同保留自有语义，不据此宣布全部外围基础设施应自建。

### 6.3 全局路线不变

| 批次 | 范围 | 首要前提与退出 |
|---|---|---|
| W1 | 公共合同/保护样本 | C/N/T采纳；首切片充分映射；不切生产数据 |
| W2 | 共享原语/资源/机械I/O | 各真实consumer同义性、Reuse、失败/预算；E60有限兼容在相关切片验证 |
| W3 | 用例/producer/恢复 | G2/G3、Smart反馈/RSS分账；不清旧状态、双写或刷新执行资格 |
| W4 | 来源/观察各族 | 逐族原件→最终consumer，旧指纹/解释与来源效果保全 |
| W5 | 方法/档案/历史 | 先旧reader与环境，再新writer；新格式可回退，失败原件保留 |
| W6 | 读包/发布/Workbench | 主/可选隔离、3类效果、host与产品证据；Sites不自动部署 |
| W7 | tests/CI/依赖/文档 | W1起贯穿，同保护范围与真实环境成本，退出不再需要的专属义务 |
| W8 | 旧执行/过渡退出 | runtime停用、provider替换、旧入口、历史reader四类退出分别成立 |

W4/W5可按真实依赖调序，W7贯穿，W8不能留成永久空头承诺。原17个迁移样本完整保留在[v2.7 §7][V27]：framing、方法质量、文件/保管、三类Odds、CLI/公告、package资源、XHS、配置声明、Smart进度、Global codec、economic HTTP、RSS三账、disclosure分组/assessment、economic review、历史环境、Relay回执、CNINFO获取。它们仍DESIGN_ESTIMATE/NOT_MIGRATED，不是一份已完成清单。

## 7. 验收、成本与剩余责任

| 整体验收 | 必须成立，沿原A1–A8 |
|---|---|
| A1 全域处置 | 重要模块/永久责任有consumer和决定，关键UNKNOWN闭合；行数与全域DEFER不算 |
| A2 目标结构 | 采纳能力/依赖/名称/owner/公共面在代码、安装、产品成立；不只是6目录 |
| A3 语义与历史 | PIT/单位/时钟/Research/Odds/Human、旧R/包及新格式回退可恢复 |
| A4 执行与恢复 | 原件、失败、未知效果、实际消费、兼容环境分别证明；ZIP存在/环境安装不足 |
| A5 永久复杂度 | 旧义务/临时兼容真正退出，代表改变可重复，系统性长期净改善 |
| A6 工程反馈 | 同保护集合/环境下安装、collection、fixture、CI、升级与恢复成本达采纳目标 |
| A7 产品与接手 | 真新上下文完成代表任务，真实产品边界/使用成立；同助手换角色不算 |
| A8 收口 | 目标完成或范围修订获准，DEFER具owner/风险/触发；Human裁定发行 |

T1领域资格、T2研究方法、T3同源新用途/reader、T4档案/命名、T5未知效果/恢复、T6视图/host/可选停用、T7依赖/CI/资源仍为共同变更样本。原全部正反例从[v2.7 §8.4][V27]继续；本轮仅给T3/T5/T6提供特定本地输入，不给整个样本或全域G3签收。

现役content/draft_feedback/full/merge_reuse继续。本文及证据不属于既有prose白名单，Ready PR正常完整验证；不为文档或本地27项取证增设CI豁免。正式精确head full、原件复验、普通合并、独立main及正常publisher分别确认；main严格reuse不是重新跑一遍full，publisher成功不代业务/Research/产品验收。[CI]

**没有本轮架构成本下降MEASURED。** 本地结果、CI测试数、gzip文件大小或文档变短不是净收益；比较仍须算迁移、适配、reader/旧环境、上游升级、永久验证义务和接手。需要的新组件先比较直接用/配置/薄适配/有限patch，再裁定自建；未独立核验的完整架构不能被悄悄排除。[PRINCIPLES][REUSE]

| 门 | 本版状态与下一责任 |
|---|---|
| G1 依赖/公共面 | 已证原顶层/前后端及本轮目标模块、framing直接引用；非全仓动态/手工/外部闭包。按重大owner和相关切片补齐，不普查所有helper |
| G2 producer/配置/资格 | E63–65本地完整阶段已查明；E60仍NOT_FIXED。Stock其他purpose、disclosure attempt_history/pdf_capture/hithink_http、theme尾部及其他consumer继续；实际workflow/CLI未代签 |
| G3 档案/状态/恢复 | 原真实四原件正例、旧环境拒绝、本轮合成前驱连续性继续；旧Python/RSS云端、全部work-ref/容量期限、旧R/新writer回退与生产恢复未完成 |
| G4 退出 | 4类退出和真实旧consumer反例明确；各owner意图、manual/动态/外部触发、专属fixture/config和支持期仍需该批证据 |
| G5 产品/host | 原19生产mjs及已审tests复用；余12份test.mjs、browser/手机、真实host身份边缘/无旁路、Quick→Brief/更正未签；Sites暂停不免审也不授权部署 |
| G6 成本/Reuse/供应链 | 原Kedro/Hamilton/dlt/pluggy局部固定审阅与本轮失败成本证据保留；完整架构取舍、DeepSeek Harness/Cordis未审重要部分、候选试验/许可依赖、全fixture义务与实际变更成本仍不足 |
| G7 独立接手 | 当前精确入口/原件可定位；本轮仍同一助手。真正新上下文/维护者完成任务未签，不以同会话自换角色代替 |

## 8. 唯一下一步与停止条件

**转向G6/Level A决策准备：在已有P1/P2/Reuse与v2.7证据上，完成能力组合实现来源的实质比较，给出C/T的明确取舍建议、剩余历史支持/净成本边界，以及W1首切片开工包的不足。** 比较要回答谁真正接管哪些责任、谁仍维护适配/兼容/状态/权限、正常改变如何传播、失败/退出怎样证明；不是再收集一轮README或机械增加已读文件数。

只补能改变整体选择或首切片可行性的证据；晚期局部细节留相关Level B，重大权限/公共合同/不可逆未知不能推迟到改码后。E60的本地阶段不再重复；具体修复获准后再用原件和实际consumer验证修改。既有候选同用途固定审阅直接复用；需新上游信息时取得当前原实现/合同并明确版本，不将未装/未跑写成通过。

本轮普通PR、精确head/原始CI、合并/main/正常发布、原件读回、在途/未知写与下一步归#508最终17回执；后继从当时main开新普通PR，不向已合并前驱追加。不重做P1/P2，不另建进度表。

Human无需重批全面审查、统一原则、Reuse/Modularity或普通文档。具体架构/外部接管、支持/RETIRE、长期原件/环境保管、成本目标、候选试验/依赖采用、P4批次、部署与发行仍按原范围裁定。C的2026-10-08/09/12/13/14自然窗、D冻结/成熟结果及原#351/#621/#581等owner不改；Sites暂停、禁Codex、分钟STOP、新城暂缓，Research/Human/Odds/Watch、来源/模型/通知/时钟/费用/隐私/权限边界与AI Investment Authority=NONE保持。

## 9. 精确来源

[OWNER]: https://github.com/auguspp/decision-kernel/issues/508
[PLAN13]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6097686457
[PLAN12]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6096068040
[PLAN11]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6095772144
[PLAN10]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6094482452
[PRINCIPLES]: https://github.com/auguspp/decision-kernel/blob/7e770c6704cd3cfdcf496e276bb0bbceb98b106e/WORKING-PROTOCOLS.md#project-principles
[V27]: https://github.com/auguspp/decision-kernel/blob/7e770c6704cd3cfdcf496e276bb0bbceb98b106e/docs/kernel-2.0-design.md
[HANDOFF16]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6100064100
[START17]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6102864183
[RESULT17]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6102969194
[EVIDENCE17]: kernel-2.0-evidence/p3-17/README.md
[LONG]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6099704536
[READY]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6098048638
[P1]: https://github.com/auguspp/decision-kernel/blob/97a4b14e287b04600841c1cc157c38a3cad0a781/docs/kernel-2.0-architecture-map.md
[P2]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/docs/kernel-2.0-prior-art.md
[REUSE]: https://github.com/auguspp/decision-kernel/blob/6125dc681602e86926dd5cd4dadb74e9457970e2/docs/kernel-2.0-architecture-reuse.md
[FRAMING]: https://github.com/auguspp/decision-kernel/blob/7e770c6704cd3cfdcf496e276bb0bbceb98b106e/src/decision_kernel/rehearsal.py#L33-L45
[COMMIT]: https://github.com/auguspp/decision-kernel/blob/7e770c6704cd3cfdcf496e276bb0bbceb98b106e/src/decision_kernel/research_commit.py
[LIVE]: https://github.com/auguspp/decision-kernel/blob/7e770c6704cd3cfdcf496e276bb0bbceb98b106e/src/decision_kernel/live.py
[METHOD]: https://github.com/auguspp/decision-kernel/blob/7e770c6704cd3cfdcf496e276bb0bbceb98b106e/src/decision_kernel/research_workflow_v1.py
[CI]: https://github.com/auguspp/decision-kernel/blob/7e770c6704cd3cfdcf496e276bb0bbceb98b106e/docs/CI-MAINLINE.md
