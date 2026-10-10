# Kernel 2.0 — P3 目标设计与迁移包 v1

日期：2026-10-10（Asia/Singapore）。设计 ID：`K2-DESIGN-20261010-v1`。归属 [#508][OWNER]；主计划 [KERNEL-2.0-PLAN-20261010-v1.0][PLAN] 不变。前驱为 [P2交付回执04][PREV]；本轮 [P3开始记录][START]。

**状态：PROPOSED / 设计交付不等于设计采纳。** 本文中的 ADR-01…05 和 S1…S4 是待整体采纳的具体建议；没有改变现役代码、格式、CI、registry、任务或权限。P3文档保存、PR合并、设计采纳、P4实施和P5验收分别成立。实际进度只在 #508 最新交接与对应PR，不在本文复制实时阶段表。

## 1. 本次要定下来的方案

**推荐：同仓、原目录为主、保留现有领域与研究边界；先解决档案恢复的真实限制，再收敛重复发布实现，核选定数值链，统一局部依赖固定方式。** 不创建新Kernel、不搬全部历史、不装通用框架、不预设删测数量。

| 决定 | 推荐方案 | 直接收益 / 保留代价 |
|---|---|---|
| ADR-01 边界与归属 | 保留现役路径和CLI；明确领域、组合、读取、发布各自责任；ADR只放本文件 | 避免新门面/新目录的兼容负担；长文件名与部分历史布局继续存在 |
| ADR-02 身份与文件名 | 机器ID保持原ASCII；原始文件名不改写；仅显式登记的原文件档案启用有版本的Unicode规则 | 新材料可按中文原名恢复；增加一条小型、明确的历史读取兼容分支 |
| ADR-03 合同、血缘与失败 | 复用现有字节/来源/算法绑定，补到最终消费者；保留各自时钟与失败状态 | 不建第二血缘库；不能凭hash保证单位、经济解释或历史可得性 |
| ADR-04 验证与供应链 | 保持四种CI范围；先退出重复责任；首轮不增加Import Linter门禁；publisher两项Action改为同版本精确SHA | 不增加开发依赖；仍须做逐切片验证与后续有界更新 |
| ADR-05 迁移与发布 | 采纳后按S1→S2→S3→S4，一次一个主要切片；分别验证、可停可回退 | 不用一次大合并赌全项目；不自动发布v2.0.0或签收原C/D |

这五项不是只有标题的方向讨论：下文固定推荐选项、备选、读写者、兼容规则、实际改动边界及停止条件。存在明确UNKNOWN的地方不提前签字，也不把它们扩成无限全仓审计。

## 2. 输入与本轮新证据

代码基线 **M=`488d0a02a831c9033603062cbc3674bfd01a9043`**。已重新读取AGENTS、NEXT/#297、#508、主计划P3/P4门槛及04回执；开放main PR为空，精确树中只有P1/P2两份2.0文件。[P1][P2][PROTOCOL]

P1文档blob=`3f2b91bbf37999a5542d476fbc0c9aaf7b61873b`，P2文档blob=`18b4ef2b0dccd743d45ffa5453663c00cbbc3bf4`，与本M相同。直接复用其责任盘点、六组成本样本及先例，不重新研究全部上游。P2的REUSE/ADAPT不是已安装或已采纳。

### E1：中文档案有两个校验入口，且牵涉旧索引重算

`research_archive_index.project()`既验证record ID，也用`archive.NAME`验证入口文件名；`research_archive._tree_files()`又用同一正则验证目录内每个文件。只改一个入口不能解决全目录恢复。[INDEX][ARCHIVE]

更关键的是，`read_entries()`从同R的registry字节重新执行`split()`，再将结果与原`entry_count`及索引描述精确比较。**全局放宽默认规则可能令旧R中原来被拒绝的记录突然进入索引，改变历史投影。** 这是从现役代码得出的兼容风险，不是本轮发现了一个已发生的生产故障。

本地仅执行了原文件中未修改的纯函数`registry_index()`：合成旧集合为空时`entry_count=0`，假设新默认规则纳入一项时为1，两份描述不相等。未执行完整reader，未拿某个真实旧R伪造故障；这项反例说明为什么S1不能只替换正则。

[#782保留的恢复映射][CMES]明确列出`交付回执.md`、`价格反推表.csv`、`条件Odds表.csv`、`研究报告.md`。本轮从原源码提取NAME正则测试，四个名称均不匹配；保留registry的107个record ID全部匹配原规则。这是有界静态检查，不是107份档案正文已恢复。

### E2：发布机制已有唯一实现，重复在两条入口的外围步骤

基础`current_state_delivery.main()`与扩展入口都解析旧reading ref、读回/验证previous、逐文件导出本地结果；两者最终使用同一个`base.publish()`。后者已做候选读回、fast-forward更新与未知响应不重试。[BASE][COMPOSITION]

因此不新建publisher，也不合并来源资格与workflow预筛。可收敛的是重复的“读取前一版本”和“导出文件”实现；两条CLI的触发筛选、可选reader、错误诊断和摘要语义仍各自保留。

### E3：选定的价格结构链已有大量可复用证据

本轮完整读取`d_price_structure_reading.py`（blob `4a1fedfc8c848cfaca6c589c2637a1fe4a49d3f9`）、`d_price_structure.py`（`52b0cc5aa1ac41c6319146163bebe4bf54ba167b`）和对应reading测试（`53f38125965eb6789ff3d96decd8540a60c6c461`）。[STRUCTURE-READ][STRUCTURE][STRUCTURE-TEST]

已看到：LIVE_HITHINK audit、原history/calendar响应hash、请求范围与采集时钟、原收盘adapter对账、Decimal字符串到native float的逐字段绑定、CZSC版本/参数、原输入及结果hash、回放前缀日与实际观察时间分开。测试明确覆盖真实native worker、同源复用、可选失败保全价格/Research，以及不向worker传凭证；本轮只是读测试源码，没有运行它们。

这不证明所有单位或源修订历史完整。该链是**基准指数**，不是个股成员/股票复权链；不能把其`source_adjust=None`推广为所有股票不需要复权。S3先沿这一确切链做最终消费端对账，不重新写CZSC或猜测已经混源。

### E4：先例与工具选择

继续消费P2的Airflow/OTel/HA/dbt/Temporal/Rust/LEAN/Qlib/MADR及已保留#508/#511局部审阅；对应能力和用途未变，不重做上游大全。新增有界官方对照为Python3.12 `unicodedata`/`pathlib`、pathvalidate文件名验证/清理接口。[UNICODE][PATHLIB][PATHVALIDATE]

Python标准库提供规范化和纯路径原语；pathvalidate是可评估的现成验证候选，但自动sanitize会改变原名，不能用于恢复原件。其纯validate用途保留候选，不称“没有合适轮子”；本轮未审其发行包/全部依赖许可，不采用为依赖。S1是在原有档案校验上薄适配标准库，不自建通用文件名或Unicode算法。

本地公共API读请求返回DNS不可用，Python3.12和Import Linter未安装。当前本地Python3.13.5/UCD15.1.0的结果不是目标3.12的运行证明；官方3.12文档声明的UCD为15.0.0。没有为此造代理workflow、装生产依赖或请求Human搬运。GitHub/MCP读取、分支与文档写入仍可用。

## 3. ADR-01：责任优先，保持现役拓扑与公共入口

**状态：PROPOSED。** 对应CONS-01/04/09/10，P1-A/B/C/H/J，P2 PA-01/02/04/08/10。

**备选：** A保持路径并明确责任；B批量搬到core/application/infrastructure新树；C增加统一SDK、plugin registry或独立仓库。**推荐A。** P1已确认独立研究提交和live组合的边界；没有证据证明B/C的迁移、路径兼容和永久工具成本值得。

目标责任与依赖方向：

| 责任 | 现役拥有者 | 可依赖 / 不承担 |
|---|---|---|
| 身份、PIT、Research/Market/Odds领域合同 | `src/decision_kernel/`中相应领域模块 | 领域/纯值原语；不应由领域提交反向调用来源网络、runtime任务或UI |
| 可替换研究方法 | 现有method文件与RESEARCH-ENTRY路由 | 提供研究结果；不把固定思考步骤变成领域真理 |
| 默认live组合 | `live.py`及现有CLI | 可知道HiThink映射并接入显式fetch能力；不是纯领域层，不新增调度/状态服务 |
| 来源获取与资格 | 各adapter/producer及其原workflow | 维持来源特有请求/单位/日期/权限；不通过统一fallback洗掉差异 |
| 保存结果组合 | 扩展Collector及静态attach顺序 | 使用基础Collector预算和已获准字节；不执行source/model任务 |
| Git读取、导出与发布 | `current_state_delivery.py` | 基础读取/发布的唯一实现；扩展方不另建发布栈 |
| 人读面 | Workbench原读接口 | 固定R、所选文件校验与独立Issue时钟；不宣称重算整个canonical reading_hash |

首轮明确保留的兼容面是现有研究提交/保管合同、两个已文档化CLI及其参数、固定R读取协议、档案格式和原失败语义。**不把所有内部Python路径宣布成永久公共API，也不据此立即删除现有路径。** 新的稳定门面和Import Linter全仓层级图均暂缓。

S2最多在基础模块中增加两个私有小函数，供现有两条入口调用：读取/验证previous；create-only导出文件。它们没有新schema、状态、调度或动态回调注册。旧CLI继续存在并直接使用同一实现，不创建另一个`*_v2`入口。`collect()`静态顺序、Radar索引提前收口、共享预算及可选失败边界保持；文件名与真实范围的偏差先通过准确docstring/责任说明纠正。

**后果与确认：** 目录不会立刻变漂亮，但避免几百引用迁移。已有断言继续保护领域提交/无来源调用；S2用相同输入、时钟、前驱、成功和失败样本对比原入口与新入口。不能仅比较成功JSON而漏掉文件库存、API调用顺序、失败阶段或未知写结果。

## 4. ADR-02：机器ID不变，Unicode原名须显式、版本化启用

**状态：PROPOSED。** 对应CONS-08/09/10，P1-D/E，P2 PA-03/04及E1。

**备选：** A永远沿用英文同blob映射；B全局放宽NAME；C在现有档案登记中显式启用新文件名规则，保留旧解释。**推荐C，A保留为历史恢复路径；拒绝B。** 不让修文件名同时改变record/question/dependency ID和旧R投影。

### 4.1 四种身份

- 逻辑record/question/source ID继续按各自现役合同；`NAME`的ID语法不放宽。
- 原始Git路径是定位信息：保持原字符串，不做NFC重命名、拼音替换或自动sanitize。
- Git blob/SHA256/bytes识别精确内容，名称相同不代表字节相同，名称规范化相同也不意味着应合并。
- display/title用于人读，可中文化；不能覆盖原路径或成为机器ID。证券、交易所、供应商代码仍沿原adapter合同转换。

### 4.2 选择的最小兼容扩展

推荐在**现有registry**的原文件档案上允许下列精确形状，不创建新registry：

```json
{"format":"RETAINED_FILES","filename_policy":"UNICODE_FLAT_V1"}
```

此字段只适用于显式ON_DEMAND的`RETAINED_FILES`。`RESEARCH_PROGRESS`、`RESEARCH_COMMIT`、`ODDS_RESULT`首轮不扩展文件名合同。旧`{"format":"RETAINED_FILES"}`继续使用原ASCII规则；未知policy、任意附加字段、把policy放到ID上均拒绝。

**仅有record字段还不够：旧R的解释必须由其自身固定证据选择。** 新reading使用现有`on_demand_archive_index`描述，在需要新规则时增加唯一版本标记`filename_policy_version: 1`（精确整数，不接受bool/未知值）。旧索引没有标记、以及旧内嵌`on_demand_archives`，继续完整使用旧投影规则；即使旧registry曾含当时非法的新形状，也不得在旧R中追认。新标记允许按每条archive的显式policy解释，**不使未opt-in的档案自动放宽**。

标记属于原reading_hash绑定的解释版本，不是来源文字声明的权限。Writer、`project/validate/split/read_entries/registry_index`、导航以及`recover_archive`必须使用同一显式模式；`_record`的再次投影和`_tree_files`不能各取不同默认值。没有新policy记录时writer保持旧索引形状，减少不必要的旧读者不兼容。

| 输入 | 新reader应如何读 | 旧reader边界 |
|---|---|---|
| 旧R / 无标记 / 原ASCII记录 | 原规则、原entry_count、原拒绝和字节；不得追认新规则 | 原行为不变 |
| 新R / 无opt-in档案 | 默认仍生成旧形状；历史记录原样处理 | 不因2.0标签强制升级 |
| 新R / 明确标记 / 某原文件档案opt-in | 新规则只作用于该档案；仍查完整库存/原件/用途 | 旧reader应明确拒绝不支持的描述，不承诺旧reader读新格式 |
| 未知标记、record/索引模式不一致、伪造用途或hash | 拒绝；不得eager fallback、忽略字段或改写历史 | 不允许通过回退降低验证 |

这里确实新增了一个小型格式解释分支，**不是“完全没有schema影响”**。但不改顶层Research schema、方法版本或所有旧registry记录。P4应先交付兼容reader及合成正反例，再启用一个真实opt-in档案；不能先改生产登记、再让旧reader猜。

### 4.3 UNICODE_FLAT_V1 的推荐边界

只处理原允许根下的单层regular data files；保留16文件、单文件/总字节、Git树完整性、精确ref、无symlink/可执行mode/子模块/子目录、create-only输出及原请求预算。

新policy的basename要求：非空，最多128个Unicode码点且UTF-8最多255字节；不接受`.`/`..`、前导点、首尾空白或末尾点；拒绝路径分隔符、`<>:"|?*%#`、Unicode控制/格式/代理码位（Cc/Cf/Cs），并用Python3.12纯Windows路径规则拒绝保留名。比较键采用`NFC(casefold(NFC(name)))`，**仅用于整档案碰撞检查**；不同原名发生冲突时拒绝整次物化，即使同blob也不自动合并。原名和原字节始终保持，目录全体名称资格在下载bundle正文前验证。

这是本项目明确的安全恢复子集，不声称支持所有Unicode字符组合或所有文件系统。标准库规则与目标Python版本共同接受测试；不要升级本地Python后静默改变合同。旧ASCII档案保留旧解释，不把新policy的更严限制追溯施加给旧R。真实不安全/不支持原名保留在原Git及原映射，不能覆盖或循环重试来换绿。

**消费者与代价：** 直接涉及archive/index、扩展Collector、Radar公司投影、Research reentry、Stock disposition、D horizon及其实际调用者；搜索提供定位，不是全部消费者已审计。`entry_url`继续按路径分段安全编码/人读转义。S1应更新涉及精确shape的消费者测试；不要求一次迁移全部资料或把工程文档登记成Research。

## 5. ADR-03：沿现有合同追到用途端，失败和时钟不合并

**状态：PROPOSED。** 对应CONS-04/05/06，P1-C/D/I/J，P2 PA-02/05/06/09。

**备选：** A一个万能source对象/数据库；B复用现有描述并明确每个消费链的资格；C只保留hash、让人猜数据意义。**推荐B。** 原件、registry、运行回执、派生读包和Human接受不是同一种状态。

S3的首条核查链固定为：

```text
Sector所选已保存archive
 -> input-audit请求/原history与calendar响应
 -> normalize_archive与既有HiThink adapter
 -> 保存的normalized input
 -> CZSC指定版本/参数与native数值绑定
 -> price-structure结果/回放及观察时钟
 -> 原Collector的descriptor、固定R与实际读取端
```

| 要素 | 现役证据位置 / 后继要求 |
|---|---|
| provider/channel与请求 | audit.provenance、requests.path/params/error_type/captured_at；archive的run/head/字节身份一并核，不只取展示标签 |
| 证券/用途 | subject及BENCHMARK_INDEX_NOT_STOCK_COHORT；不能把指数示例解释成个股资格 |
| 日期与可得性 | source_date_ms/session、calendar、source_captured_at、computed_at、checked_at、replay_session、first_observed_at分别核；历史公开可得性仍允许NOT_ESTABLISHED |
| 单位/复权/修订 | 原OHLC字段、source_volume/turnover、source_adjust/requested_adjust/geometry及来源合同分别说明；单位不明不得推导新金额/流动性含义，不靠缺省填已知 |
| 算法与数值 | ALGORITHM版本/source_commit、PARAMETERS、source_decimal/native repr/hex、input_hash/native_input_hash及逐bar绑定；源码commit标签不替代实际安装版本证明 |
| 最终读包 | normalized_input_file、report_hash、descriptor的bytes/SHA256/blob及同R路径；所选文件校验不等于验证全部R或经济正确 |

实际查询仅取一份明确的保存输入及必要前驱；禁止为了填表重新采集市场数据、拼多个R或把不同供应商同ticker数据静默互换。多输入本身不违法，但用途、单位、窗口和来源必须显式可对账。发现真实缺字段时，只为该消费者补最小元数据或拒绝，不把全仓迁入新血缘schema。其余价格/因子/Outcome链保持现役保护并留在后继审查范围，**这一首轮不签全源血缘完成**。

失败仍分未执行、真实执行失败、效果未知、结果已读回，以及最后合格历史结果/最近尝试/新鲜度。共享helper不得把拒绝变空列表、把UNKNOWN变0或让一次成功覆盖旧缺交付。部分扩展失败可以保全基础读取，但API已用预算不能回滚，未知远端写先对账而非重试。[BASE][COMPOSITION][STRUCTURE-READ]

## 6. ADR-04：验证按责任，首轮不增加架构工具门禁

**状态：PROPOSED。** 对应CONS-02/03/04/11，P1-F/G，P2 PA-07/08/10。

**备选：** A保留现役pytest/原生CI、逐切片消除重复；B现在装Import Linter并增加全仓门禁；C自建AST依赖图/selector。**推荐A，B暂缓，C不建。** 尚无完整目标依赖合同、实测扫描成本或必须由新工具弥补的缺口；现有架构/网络禁止反例可先用于本轮具体改动。不是宣称Import Linter不适用，也不是因为本地网络失败就决定自建。将来出现反复的真实反依赖，再按P2已核2.15候选做正例/反例/成本试验。

保持`content / draft_feedback / full / merge_reuse`，当前工程完整证据、分片互斥/并集、实际环境与独立main要求不变。[CI] 本文路径不在content白名单，不移动到readings或改白名单省验证。

永久保护按现役义务保留：身份/PIT/权限、真实消费者失败传播、旧档案读取、来源到最终结果绑定。S2若两个入口共用同一helper，其内部字段反例可在helper层集中，**但两个CLI各自的接线/错误传播仍要验证**。S1新增兼容保护是新增成本，不冒称瘦身。测试identity退出、重复fixture构造减少、wall time和累计作业秒分别记账；不把参数用例塞循环制造“减少测试”的数字。

本轮没有可批准的全仓死代码或测试删除清单。已退役的#354/#626及业务one-shot不重开；没有直接import、文件旧或名字含trial不是删除依据。S2明确退出重复外围实现，不退出它保护的语义。其他可疑writer/fixture只有在原owner、CLI/workflow/手工恢复消费者均核清后才能另列有界后继，不自动扩大S1…S4。

供应链首轮只处理publisher中的`actions/checkout@v7`、`actions/setup-python@v7`：S4将届时实际核验的同版本官方提交固定为完整SHA，并保留可读版本注释。不要把“改为SHA”顺便变成升级版本、增加权限、把CI开发环境用于publisher，或重设CodeQL/Dependabot。已有原生依赖更新和独立安全扫描继续；未读告警不叫零漏洞。[PUBLISHER][NATIVE]

## 7. ADR-05：同仓小批，范围采纳后才实施

**状态：PROPOSED。** 对应CONS-01/06与全体切片。选择同仓有界替换，而不是新仓、长期双runtime或一次大迁移。软件2.0是整合称呼，不把包schema、研究方法、算法、研究修订或历史接受统一改成2。

本文件同时作为首轮ADR容器；不新建架构数据库，不把ADR塞入已承载Human决定的`docs/decisions/`。将来拆分ADR需有真实检索负担，再由本入口路由；不预先创建空目录和成批空Issue。

### 7.1 目标对象存放与生命周期

下表是本轮目标placement，不是把当前仓库重新誊写一遍。**除本设计文件外，首轮没有必要新增顶层路径。** 代码helper尽量留在现役owning module；历史资料保持原位置。I=固定commit/字节不可变，A=后继追加，M=经授权前向修改；Git历史不改写。

| 对象 | canonical owner/path | 可变性 | producer | consumers | retention | publication/read contract | 迁移/退役 |
|---|---|---|---|---|---|---|---|
| 领域与方法代码 | `src/decision_kernel/`各合同 | M/I | 已授权PR | 现有CLI/方法/验证 | Git版本 | 精确M，不继承方法接受 | KEEP；不批量搬目录 |
| 来源与任务声明 | 现有`decision_inputs/`、`radar_inputs/`、`provider_requests/`、workflow | M/I | 原任务owner授权PR | 对应producer/Collector | 原版本保留 | 配置不是已执行结果 | KEEP；S4只两项Action ref |
| 用途登记 | `current_state/registry.json` | M/I | 经授权登记 | index/archive/阅读端 | 每个M/R保留原字节 | 同R绑定的用途定位，不是全量状态 | S1仅明确opt-in及一个真实案例，不换全体ID |
| 结构化研究包 | 原`research_cases/`、显式archive | I/A | 获准研究/commit操作 | 既有typed reader/spine | 原schema/hash | COMMITTED不是Human接受 | KEEP；不转换旧概率/方法 |
| 研究底稿与来源文件 | 原`docs/readings/`或`research_runs/`精确ref/path | I/A | 原研究/保管操作 | 被明确登记的reader | 原件及后继分别保管 | 原名/bytes/blob，不跟随任意链接执行 | S1允许原名恢复，不改#782映射/旧原件 |
| Human决定 | 原`docs/decisions/` | I/A | Human原决定的授权保管 | 原研究/Watch/展示 | 保留原话与时点 | 接受/条件/Watch/交易分开 | KEEP；不放工程ADR |
| source/run artifact | 原Actions run/attempt/artifact；已有Git保管 | I、到期另列 | 原producer | 资格reader/恢复者 | 原平台期限与Git副本分开 | 过期副本不恢复当前源资格 | 不借2.0清空历史或保证永久保管 |
| 综合阅读 | `read-model/current-state`及sources/details | ref M；R I | 唯一base.publish | 固定R消费者 | 原Git历史 | metadata/原件/派生各自绑定 | S2共享外围helper；S1新解释显式标记 |
| News缓存/Issue观察 | 原news-live、#575/#581/#601等 | M、各自时钟 | 原任务 | 独立UI/研究入口 | 原用途规则 | 不是综合R的隐式组成 | KEEP；不因整合改时钟 |
| 测试/fixture/evaluation | 原`tests/`、Workbench tests/browser、eval/dogfood | M/I | 实施PR | 对应验证 | 现役保护和必要历史 | 合成与真实、工程与研究效果分开 | S1增必要兼容保护；S2集中重复内部证明 |
| 设计与进度 | 本文件；#508计划/最新回执；#297路由 | 设计I/A；导航M | 已授权工程/RM | 下次施工和Human | 保留采纳/替代理由 | 精确版本、PROPOSED与ACCEPTED分开 | 一处ADR容器、一处接续；不建第二进度表 |

### 7.2 首轮迁移包

**建议顺序S1→S2→S3→S4。** 原因：S1有真实原名恢复限制且可独立验证；S2只改已有重复实现；S3验证一条明确链而不改算法；S4独立收敛版本固定。S1和S2不捆绑一张PR，避免格式变化掩盖行为等价问题。

#### S1 — 有版本的原名档案恢复

- **范围/处置：** CONS-08/09，ADAPT原archive/index；KEEP逻辑ID、typed格式和旧R。改动仅archive/index、必要直接消费者/测试及两份现有档案说明。新registry opt-in作为兼容代码验证后的真实应用，不先行写入。
- **旧→新：** 无policy继续原规则；新索引标记下的原文件档案按`UNICODE_FLAT_V1`读取。helper只实现已选policy与碰撞检查，不建通用路径框架。
- **真实样本：** #782原件commit `a3f905d41146e29106f8ff4de71fbafbc0c081d8` 的`docs/readings/cmes-full-odds-2026-10-07-original/`，先核完整树/文件数/bytes，再显式登记原件入口。旧英文恢复目录 `d1177a0f76d2680157df4a27e741a048454f356b`继续保留，不替换旧接受或运行附带脚本。
- **验收：** V1–V5全部成立；新旧索引的同R投影、中文入口和中文非入口文件、所有原blob、URL转义均验证。复用`test_research_archive`/`test_research_archive_index`现成合成Git transport，不把stub称为真实网络。
- **代价/回退：** 一条持久解释分支及必要反例；不能承诺删测试。若新reader或实际恢复不合格，不启用opt-in。已发布新policy后回退应停止新登记/新格式写入，并保留能读已发布新旧记录的reader；不能直接回到不认识新格式的旧代码。原数据/ref不得倒退或force。
- **停止：** 原树不完整、碰撞、超额、旧R结果变化、模式不一致或任何内容/用途绑定丢失；保留失败和partial output，不覆盖、不自动重试。

#### S2 — 收敛两条发布入口的重复外围实现

- **范围/处置：** CONS-04/02，CONSOLIDATE两条main的previous读取与本地导出，KEEP唯一base.publish、两个CLI、静态attach链和各自诊断。建议在基础模块内放私有helper，不新增目录/框架。
- **旧→新：** 两套重复代码由同一内部实现承担；扩展trigger qualification仍先于读取/写入；refresh身份、API预算、输出与失败语义不得丢失。不同目的的workflow预筛/Python资格校验不合并。
- **验收：** V6/V7；固定合成输入/时钟的payload、文件库存/原字节、调用顺序与次数、返回码/失败阶段等价。两CLI均保留真实入口接线证据；共享helper反例可集中，但旧调用者传播不能删。
- **代价/回退：** 退出重复实现，不宣称永久test identity净减少；依据前后实际diff计账。正常revert代码即可回退，不回滚数据ref。完整CI与正常发布/固定R正文分别核。
- **停止：** helper需引入动态插件、第二状态owner、改变预算/源选择/异常含义，或差异无法解释；保留原实现而不为“统一”继续扩大范围。

#### S3 — 选定指数价格结构链的最终血缘与恢复对账

- **范围/处置：** CONS-05/06，KEEP现有adapter/CZSC/reader；按第5节核一份保存源及必要前驱。不是新增采集、全市场审计或新评价算法。
- **旧→新：** 从“来源字段存在”推进到“来源→实际数值→最终文件可逐项对账”。字段和拒绝已足够时不改代码；发现明确缺口才在原消费者中做最小修复并列明旧→新语义，实质超出本链则回#508处置。
- **验收：** V8/V9；原calendar/history与规范化输入、native binding、算法版本/参数、结果hash、同R文件读回和失败传播一致。单位或历史可得性不足保留UNKNOWN，不把结构线当公司研究/机会。
- **代价/回退：** 一次有界核查和必要局部保护，不建常驻血缘平台、不复制大fixture。单链结果不签其他价格/因子/Outcome链；无依据的部分明确留后继owner。
- **停止：** 保存原件不可取、来源/口径/窗口不相容、旧结果与原输入无法重建；不补采、不混源、不覆盖原失败。

#### S4 — publisher两项第三方Action精确固定

- **范围/处置：** P1-G，REUSE官方已有Action，将两项版本tag固定到同版本、届时重新核验的完整SHA；保留版本注释和现有原生更新途径。
- **旧→新：** 只减少可变tag歧义，不顺手升级Action/Python/业务依赖，不动permissions、任务cron、源任务或安全扫描配置。
- **验收：** V10；核精确commit/官方来源及实际workflow差异，原actionlint/full、独立main与正常publisher分别验证。只读tag解析不是相应代码已部署。
- **代价/回退：** 两处引用及必要文档/测试；后续升级仍走有界PR。回退通过正常PR恢复此前已验证的精确版本，不force发布ref，不修改凭证。
- **停止：** 无法证明tag对应版本/官方commit、必须新增权限或升级才能通过；不靠关闭检查继续。

### 7.3 验收矩阵：各项分别证明

| 编号 | 正例 / 负例 | 证据与完成条件 |
|---|---|---|
| V1 旧解释 | 旧eager、旧内嵌索引、旧registry投影；旧非法中文/附加字段仍按旧规则处置 | 新reader消费旧R时输出/entry_count/拒绝一致；原字节/hash不变 |
| V2 新policy | 新标记+显式raw opt-in；缺标记/未知标记/typed滥用拒绝 | ID语法不变，索引与完整目录恢复共同成立；不是仅入口可链接 |
| V3 文件安全 | 原四个中文文件名；NFC/NFD与大小写碰撞、控制字、保留名、穿越、symlink、超界拒绝 | bundle正文写入前查全库存；create-only、原16/字节/调用边界保持 |
| V4 原件恢复 | #782原名目录和原英文映射各自恢复 | 精确source ref/path/blob/bytes；不运行文件中的Python或改manifest |
| V5 消费者 | archive/index→导航/公司reentry/D等实际直接消费者 | 同一解释模式、同R、无eager fallback；UI只对实际改变部分补原测试，不重启Sites |
| V6 入口等价 | 两CLI的成功、无publish、诊断skip、前驱缺失/损坏、导出失败 | 固定输入/时钟；payload/files/API轨迹及错误语义不丢 |
| V7 发布边界 | 候选读回失败、并发ref冲突、写响应未知、可选reader失败 | 不force/重试/误报成功；原基础内容、历史失败和已用预算保留 |
| V8 数值链 | 保存源→原adapter→规范化→native→报告→所选同R字节 | provider/channel、用途、日期/单位/调整/算法可追溯；UNKNOWN有明确影响范围 |
| V9 时钟/差异 | 同输入、追加日、历史修订、窗口变更、观察中断 | 不把回放几何日期当首次获知、不把窗口变化当新信号 |
| V10 工程交付 | 精确PR/full、独立main、publisher与适用消费者 | 原ZIP与集合/环境/身份分别核；只文档时不冒称生产正文或独立会话验收 |

所有切片先读当前M、对应采纳记录及在途PR/run；仅确有保存结果消费时固定R。正式失败原样保留，不能rerun换绿；允许的后继修复必须有真实改动及原失败定位。

## 8. 本轮不做的事与P5边界

不改变C固定2026-10-08/09/12/13/14自然窗或D冻结/成熟结果；不复活旧source试验、分钟STOP或新城暂缓；不新增采集、模型调用、任务时钟、通知、费用、凭证或隐私外发。Sites与Codex原暂停/禁用边界保持。Investment Authority=NONE。

本轮不迁移全部`runtime/`、不清空旧`dogfood/`、不重写Human决定；不安装Import Linter/pathvalidate/新provider框架，不建数据库/遥测/Memory/DAG，不把所有P2候选变成依赖。**延后不是无合适工具，也不授权自建替代。**

P5按实际已实施范围对账：历史恢复与拒绝、受影响发布/正文/消费者、永久责任/测试identity/实际成本、独立新上下文接手、剩余DEFER及owner。P1样本不是本轮提速；成本比较需说明同一范围/环境/代码差异。S1增加的保护与S2减少的重复分别报告。是否发布v2.0.0另按稳定接口/兼容影响裁定；不为版本名称修改历史方法/schema。

## 9. 采纳记录与唯一下一步

**待采纳的范围就是本文ADR-01…05及首轮S1…S4，含上述兼容与停止边界。** 推荐接受该有界范围，而不是批准任意2.0重构。采纳后普通实现细节/PR不逐文件索批；新增来源、费用、权限、重要语义或超出四切片的删除仍单独处置。

本轮先完成设计文档正常交付和#508导航读回。此后P3仍保持IN_PROGRESS，直到#508记录Human/适用owner对精确设计版本及实施范围的采纳；P4 NOT_STARTED。文档PR的merge只是留存PROPOSED设计，不能拿它当采纳证据。

采纳后的下一最小动作：恢复S1，先实现新旧解释分离及合成正反例，验证兼容reader，再接一个#782真实原名档案；不从搬目录开始，不重做P1/P2。发生中断先核同一branch/head/PR和原操作，不能重新造设计。最终交接记录应分别列文档交付、设计采纳、P4、在途/不确定操作与唯一下一步。

## 10. 来源与检查范围

以下仓库源码链接固定本M；历史案例固定其原ref。本轮读了archive/index、两条main及选定价格结构代码/所列测试；相关消费者搜索用于定位，未冒称全仓调用图。测试源码读取、纯函数反例、正式CI、生产正文和独立会话是不同证明。

[OWNER]: https://github.com/auguspp/decision-kernel/issues/508
[PLAN]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6094482452
[PREV]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6095301019
[START]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6095423577
[P1]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/docs/kernel-2.0-architecture-map.md
[P2]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/docs/kernel-2.0-prior-art.md
[PROTOCOL]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/WORKING-PROTOCOLS.md
[INDEX]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/src/decision_kernel/runtime/research_archive_index.py
[ARCHIVE]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/src/decision_kernel/runtime/research_archive.py
[ARCHIVE-TEST]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/tests/test_research_archive.py
[INDEX-TEST]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/tests/test_research_archive_index.py
[CMES]: https://github.com/auguspp/decision-kernel/blob/d1177a0f76d2680157df4a27e741a048454f356b/docs/readings/cmes-full-odds-2026-10-07-recovery/README.md
[BASE]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/src/decision_kernel/runtime/current_state_delivery.py
[COMPOSITION]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/src/decision_kernel/runtime/current_state_delivery_with_odds_watch.py
[STRUCTURE-READ]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/src/decision_kernel/runtime/d_price_structure_reading.py
[STRUCTURE]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/src/decision_kernel/runtime/d_price_structure.py
[STRUCTURE-TEST]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/tests/test_d_price_structure_reading.py
[CI]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/docs/CI-MAINLINE.md
[PUBLISHER]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/.github/workflows/current-state-read-entry.yml
[NATIVE]: https://github.com/auguspp/decision-kernel/blob/488d0a02a831c9033603062cbc3674bfd01a9043/docs/github-native-operations.md
[UNICODE]: https://docs.python.org/3.12/library/unicodedata.html
[PATHLIB]: https://docs.python.org/3.12/library/pathlib.html
[PATHVALIDATE]: https://pathvalidate.readthedocs.io/en/latest/pages/reference/function.html
