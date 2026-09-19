# Radar 来源资格与 Research Question Layer 合同 v0

日期：2026-09-19。范围：Radar-r3 最小产品合同补充。
依据：#297/5740953811；本轮明确施工通知；施工前 Reuse Check #297/5741271436。
**Reuse Decision: REUSE。文档/语义与最小回归；runtime、schema、源资格算法及自动路由不变。**

## 1. 不同来路，不同资格

保留现有 Sector / Concept → discovery pool → Stock price gate 的市场表达产品路线，统称 `MARKET_EXPRESSION`；保留已实现的 Sector 路径、概念当前成员/补查阅读和各自未接通范围。不借这张目标图宣称全部概念成员已跑 Stock，也不把旧 pool 的未接线 batch planner 宣称为新增执行器。

| 来路 | 本路线的资格含义 | 不足以证明 |
| --- | --- | --- |
| Sector / Concept：MARKET_EXPRESSION | 按原来源政策验证指数/价格路径、时间、覆盖及成员身份；进入 Stock 检查的对象沿用其原 price/relative-strength gate | 公司业务受益、行业经济拐点、机构动机或 Research 准入 |
| Smart Money：OBSERVATION_QUALIFICATION | 保留自身观察的身份、来源、时间窗、字段口径和缺口；当前具体实现为机构席位窗口，不代表全部聪明钱 | 买入动机、投资正确性；不要求先通过 Sector/Stock Price Gate |
| Industry Inflection：ECONOMIC_EXPOSURE / MATERIALITY / VALUE_CHAIN | 未来核对行业变量与公司实际经济暴露、影响重要性及价值链方向；还需可回答问题与反证 | 仅行业变化或概念成员就完成公司筛选；股价已涨或未涨都不是经济暴露成立的裁判 |

上述大写名称是本合同的语义词汇，不是新增枚举/JSON字段。未知来路不得默认归入市场表达或机构观察。来源标签本身不是资格证明，资格必须可追溯至其原始合格结果、验证范围及失败记录。

成员表可读不等于指数历史合格，更不等于该股票通过价格检查。PARTIAL 来源必须逐项保留已取得范围和缺口，不把整个来源一次性标成研究合格。当前公司视图允许保留未通过/未检查价格的对象；这与市场表达路线保留自己的 Stock gate 不矛盾。

## 2. 现有字段够表达什么

本轮固定 M=`00830c83a03858d93d717200b7c52f9c9d3e487c`、R=`b623f3eec938c2b53f9b49b3b6361c71e49d875f`，审阅 `radar_stock_candidates`、`radar_company_reading`、concept v2/v3 与原回归。采用以下已有位置，不添加重复的 radar_kind / qualification_kind / qualification_reason。

| 信息 | 已有位置与读取语义 |
| --- | --- |
| company/security | 公司行 `thscode`、`source_names`、`name_status`；只按完整证券身份汇合，名称冲突仍可见 |
| origin kind | `origins[].kind`：`SECTOR_LEADER`、`CONCEPT_CURRENT_MEMBER`、`INSTITUTIONAL_WINDOWS`；补查沿用 concept kind，并保留 `acquisition_kind` |
| 原因与资格依据 | Sector 的 `group_key`、方向/driver、`retained_leader`、`source_result_hash`及原 Sector source；Concept 的成员/请求身份、`projection_hash`、`concept_context`或`concept_detail_context`内路径/缺口；Institution 的 `observations`、`window_aggregation`、原 source/projection；结合顶层 `source_status`读原验证，不造统一总分 |
| 价格结果 | `stock.status`、`stock.dispositions`、`stock.market_session`、`stock.lane_health`与同R来源；保留原status/reason，不提升为其他origin的全局资格 |
| 来源与时间 | `source`同R引用、`source_observed_at`、各自`market_session`及取得/成员时钟；publication UNKNOWN仍UNKNOWN，不拼成统一首次知晓时点 |
| 既有研究关系 | `research.references`、`stock_business_states`及其root/child、`on_demand_archives`；档案定位不等于已读正文或Human接受 |
| 当前问题资格 | `questions`只是通用阅读提示；`question_status=OBSERVATION_QUESTIONS_NOT_PRE_OR_QUICK_RESULTS`、`automatic_admission=false`、`new_research_execution=NOT_EXECUTED` |
| 去重/版本基础 | 公司层按thscode保留各origin；原pool/result/projection hash、精确source/reading commit及原研究问题/版本可供后续复用，不冒称已有问题语义去重器 |

没有单个通用qualification reason字段不是本次runtime缺口：依据已经在原件和引用中。缺少某个具体依据就显示UNKNOWN，不能从kind、哈希自洽或读取成功推导其经济真相。现有字段足够本轮阅读合同，不表示已能执行完整Research Question Layer；未来真实宿主不能表达的内容，才举证作THIN_ADAPTER。

## 3. 汇合点与本轮未实施的下一层

目标合同：

`qualified observations -> company-first context -> Research Question Layer -> Pre`

这里的 qualified 指每项观察通过自己的用途/范围资格，不是公司视图里所有行都合格。company-first context可以保留更宽的未检查、部分、失败和历史背景；未解决的必需资格不会因汇合而消失。Pre前仍要完成原来源范围、执行权限、预算及身份/时间检查；问题形成不授予模型调用权限。

Research Question Layer 当前为 **TARGET_CONTRACT_ONLY / NOT_IMPLEMENTED**：不是新provider、Agent、DAG、队列、调度器或打分器。不要把现有 `_questions()` 的模板提示包装成具体可执行研究问题。下一明确接点是复用现有research progress/source scope/admission，把经审阅的具体问题薄接到原Pre入口；本轮只登记，不生成实际公司问题、不执行Research。

### 问题候选的最小留存合同

在原底稿的身份/范围与进度中记录即可，以下不是新增schema或待填运行对象：

| 内容 | 最小要求 |
| --- | --- |
| company/security | 证券、市场/股类、公司身份；不得按六位代码猜交易所 |
| origin(s) | 每个原观察的kind、资格依据/拒绝原因、原始source/hash/版本与时钟；重叠仍是多条来路 |
| question | 具体、可证伪、可回答；说明哪个经营变量/论证会因答案变化，以及什么证据可以推翻它 |
| why_now | 为什么此时值得花研究预算：新合格观察、明确旧问题未完成、有效方法挑战等；不是臆造涨跌原因 |
| required evidence classes | 在取数前声明支撑与推翻问题的必要主来源、期间/口径和有界更新范围；失败后不改叫可选 |
| known counterevidence | 已知反证、替代解释及未查范围；未找到不等于不存在，坏消息不能被标签分数抵销 |
| existing research relation | 原问题/版本/失败/终局/档案的精确引用；是继续未完成分析、查触发证据、另一个问题还是方法修订 |
| UNKNOWN | 区分未请求、未检查、不可得、来源失败和真实未决问题；注明受影响的结论和停止条件 |
| dedup/version identity | 复用证券+经济问题身份、既有来源/内容hash、保存版本和前驱关系；保留old→new依据与相关范围，不发明新的全局key规则 |

重复标签、重复source或同一公告的不同转载不能创建独立确认。同一经济问题仅增加另一条Radar来路，先与已有问题合并来路/记录版本关系，不重复Pre；有不同影响机制或分析范围时须明确区别。不得换key、重置launch或换版本逃过已消费执行权限。相同文字也不证明问题等价；新证据先核对影响范围，不机械重做全部研究。

进入Pre的原则是问题的决策相关性、可回答性、证据充分性与剩余认知预算；保留不进入的具体原因。没有composite score，不按标签数量、来源数量或涨幅排名直接决定进入Pre；少量是认知预算目标，不是每日配额，允许0个。问题候选、准入通过、实际执行、研究结果与Human决定是不同阶段。

合成说明（不登记真实公司）：“产品X在期间T的交付延后是否主要由验收推迟，而非份额流失？哪些同产品中标量/份额/价格、验收和收入/回款记录能区分？”比“为什么涨了、是否利好”可回答；这仍只是问题表达示例，不是已完成研究或来源已取得。

## 4. Industry Inflection 的未来完成定义

`行业变量变化 -> 价值链映射 -> 公司经济暴露 -> 少量候选 -> 具体 Research Question -> Pre`

五项必要审阅为 `DIRECT_EXPOSURE`、`ECONOMIC_MATERIALITY`、`VALUE_CHAIN_DIRECTION`、`QUESTION_ANSWERABLE`、`COUNTEREVIDENCE_DECLARED`。分别核对真实业务联系，收入/毛利/利润/现金/资本影响量级，价值链环节及方向，问题可核验性，以及长协、库存、转嫁能力、产能、竞争、客户集中等反证。方向不能建立或必要量级不明时保留UNKNOWN与未入选原因，不将全行业成分股或涨幅领先者全部送Pre。

行业变量下降也可构成风险研究问题，不预设只能找正向受益者。股价未明显上涨不能排除有经济依据的候选；大涨也不能证明受益。Price是后续market-expectation/Odds context，不替代经营证据。仅有行业变化列表不能算Industry Inflection完成；最终需要少量公司问题与各自进入/不进入原Pre的可追溯处置。

此处是后续/P2完成定义，**不是当前Industry Inflection provider、经济资格验证器或自动Pre已上线**。不抢占Radar-r3真实使用；真正开工前仍需具体需求及External Reuse Check，不因文档列出五项就造五个gate模块。

## 5. 保留的合同与验收边界

旧 `FIRST_BUSINESS_BASELINE`、stable key、已消费launch、全量正文合同、旧失败、root/child lineage及自动监听保持不变。未来question-scoped Research另作THIN_ADAPTER，不把本合同当作重试旧失败或修改历史的许可。

公告按#297/5740713728与#450收敛：默认scan-disclosures关闭，按需核验；`SOURCE_UNAVAILABLE / UNKNOWN`不是没有事件。不得重开CNINFO/SZSE/SSE下载实验。本轮不接Tushare/Jev/MinerU，不调用Research/Pre/Quick/Deep/Odds/Action，不改变投资权限。

本轮落地的是语义映射、下一层最小合同和对已有隔离行为的synthetic回归；没有改JSON、rendered HTML、source gate、price gate、排序、publisher或运行入口。工程CI/合并/正常publisher分别留回执，不把绿灯写成Radar→Research自动闭环。

## 6. 复用与关联入口

原[Radar company reading](radar-company-reading-v1.md)、[Concept v2](concept-company-reading-v2.md)、[Concept detail v3](concept-detail-reading-v3.md)继续承载现有读取；[研究资料范围](research-source-scope-v0.md)、[进度留存](research-progress-v0.md)、[原准入](../src/decision_kernel/runtime/external_research_admission.py)承载后续薄接点。

外部复用仅为既有pytest的fixtures/monkeypatch与GitHub原生Markdown/Git，不引入Radar框架。检查依据：pytest官方[fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html)与[monkeypatch](https://docs.pytest.org/en/stable/how-to/monkeypatch.html)，2026-09-19读取；原工具足够，不因无整包覆盖全部产品语义就自建整层。

Evidence changes Belief; Price changes Odds。Kernel校验身份/时间/来源一致性，不认证真理。AI Investment Authority = NONE；Human拥有最终研究、判断和资本决定。


## 2026-09-19 后续薄适配：显式问题输入准备

见[已声明问题输入准备 v0](reviewed-question-input-v0.md)。它将一份预先保存的有界问题声明通过原 source_refs 绑定至原 ExternalResearchInputPacket，再调用原 prepare_input；不改变本页原来源字段、Price Gate、Stock基线或Kernel schema。输出仅为 QUESTION_INPUT_PREPARED_NOT_EXECUTED，不是Pre admission或执行权限。

这是本页下一接点的一个有限实现，不是整个Research Question Layer上线：自动问题生成、语义审阅/去重/选择、company-first生产接线及真实Pre仍未实施。旧continuation/trigger/method宿主不因新的声明而被重开，必要来源失败仍拦住对应输入。
