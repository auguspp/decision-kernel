# 公告按需与研究资料范围 v0

2026-09-19。需求：#297 / 5740713728；本切片授权与复用：5740780755。
Reuse Decision: THIN_ADAPTER。沿用 Full Research v3、原来源准入与进度留存；不是新 schema、抓取器或自动研究许可。

## 已经收敛的边界

公告是一手材料，不天然等于已经验证的 Evidence，更不是 Judgment。停止自研公告下载基础设施及端点/请求头实验；当前财报先恢复并复用仓库已有的实际获取、解析、完整输入和留存能力。新浪发行人 PDF 镜像与 DataSinking 财报正文均有历史及本轮成功记录，见[财报优先与历史复用](handoffs/2026-09-20-report-priority-and-reuse.md)。若将来恢复稳定公告供给需求，再按[#297原范围](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5740713728)评估 Tushare 的实际覆盖、权限、许可与原件取得能力；这不是当前默认安装或唯一通道。返回 PDF URL 不等于取得 PDF bytes，不预先承诺某个服务能修好网络问题；本轮不接入新的服务或解析器。

Radar 不要求公告扫描先成功。`decision-inbox.yml` 保留原独立 inbox/disclosures jobs；`scan-disclosures` 是原生 boolean，默认 false，只有明确 true 才执行保留的六公司扫描。默认运行的 Markdown/HTML 与原生摘要明确 `NOT_REQUESTED`，不写“今日没有公告”或“扫描成功”。显式启用后，旧扫描的输入、来源、预算、失败传播、原件及 handoff 合同保持；不是新增的任意公司按需 API。

历史失败继续保持原时间和原结果，默认关闭不会修复它们。工程 CI/publisher 成功不证明未来真实 Inbox run 的 job skip 或研究质量；首次自然或另行批准的运行需查实际 job/输入与产物。无需为了验收一个默认开关重跑行情、旧研究或公告。

## 当前财报范围与历史边界（2026-09-20）

Human 已明确“报表确实是关键信息，其他公告暂时不考虑”，[本轮范围记录](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5750493197)向前取代助手此前将公告窗口补齐列为下一必做阶段的安排。当前必要主材料为支持具体问题的财报；其他公告采集暂缓，不把全窗口公告正文作为项目、Radar或全部财报分析的前置条件。

财报可支撑的收入、利润、现金和附注分析继续。若某个必要主张确实只能由一份具体公告原文判断，应说明该文件、受影响的主张及替代材料为何不足；未解决的局部主张保持 UNKNOWN，不据此停止其他工作。暂缓公告不意味着没有后续事件、风险已经排除或 Full Research 已完成，也不排除已读财报中的不利信息。

Human 明确改变范围与下载失败后擅自降级必要来源不同。保留旧范围、失败和执行身份，记录 old→new 及依据，再按新范围准备后续材料；不倒填旧 run、不清除 launch、不凭改名制造新问题。以下一般规则继续约束声明范围内的必要材料。

Human 随后要求继续验证 GitHub 候选，新增一次[沃顿 2026H1 有界报告查询与 PDF 实测](cninfo-woton-h1-candidate-probe-v0.md)，范围记录为[#297 / 5750797689](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5750797689)。这一向前范围允许复用已审开源查询形状并使用现役只读探针；上文停止继续自研端点实验的旧切片边界不阻止这次具体授权。它不启用常态公告采集、不改生产来源资格，也不重跑旧研究请求。

## 取得材料前先写问题与资料范围

在原 Full Research 底稿“身份与范围”或“进度与接续”内记录即可，不新增登记库：

| 声明 | 最小内容 |
| --- | --- |
| 问题与边界 | 证券/股类、明确问题、cutoff、分析期间；来源计划保存版本与时点；继承哪个已保存问题/执行 |
| 必要材料 | 要支撑或推翻什么主张、所需主来源及期间/口径；已知相关修订、监管和反证材料不能因不利而排除 |
| 有界更新检查 | 公司、时间窗、官方渠道、要检查的披露类别及实际覆盖限制；必要最新核验不得以旧报告代替 |
| 可选背景 | 为什么不承载本次结论；未取得时具体不影响哪条已被必要证据支撑的论证 |
| 结果与缺口 | 每项已读/未读/获取失败、源定位/时间/哈希与表示方式；UNKNOWN影响范围与停止条件 |

先有范围声明，后有获取结果。不能先把现成文件当全部必要输入，再事后宣称覆盖充分；也不能因第一份 PDF 失败，就删掉对应必要类或将反证改为不相关。相关性是研究者可追责的判断，不是标题规则、价涨或某个模型 confidence 能认证的事实。

问题本身改变、材料发现要求扩展或原判断有误，应留下 old→new、依据和先前计划，重新遵守所用宿主的版本/准入/权限合同；不得覆盖旧失败、清除 launch，或换 key 重试同一已消费执行。

## 来源失败影响哪一层

必要财务数据缺失：相应利润、现金或估值桥保持 UNKNOWN，不得给已验证结论。必要最新披露检查失败：不能声称已经查清“没有新风险”。已发现相关反证的正文不可得：该论证仍未解决，不能由其他几份看好的材料冲淡。

与声明的问题无关、且不承载结论的背景来源不可得：保留 `SOURCE_UNAVAILABLE / UNKNOWN`，其他有依据的分析可继续。若原权威来源确有另一种可核验的官方正文表示，独立记录其身份、时点、哈希、范围及 custody 限制；不是悄悄当作丢失 PDF 的原字节，也不是新增独立来源。

Full Research 必须进行重要公告的有界核验；“尝试过”不等于“核验完成”。若关键范围仍缺失，可以交付并留存有限判断/条件分析，但必须明确哪些 Full Research 工作未完成，不把技术受阻叫作公开信息已经穷尽。印章真实性、实际签署时间及法律效力不由 OCR 或哈希认证。

## 复用现有执行与留存，不改写旧专用合同

`external_research_admission.check_preflight` 已核对声明的 `required_classes`；对于 `LATEST_INVENTORY`，检查计划中的实际查询及 `decision_relevant` leads 的主来源正文。`prepare_input/execute_after_admission` 还校验声明与固定原件、时钟、身份、权限；本切片不修改这些函数，不降低任何 gate。检查通过不是研究真值认证，也不是正式研究已经运行。

尚未进入正式准入或只完成部分分析的成果，沿用 `research_commit_only save-progress/read-progress` 与 `research_archive`，独立记录原件归档、索引、发布、读回。不能把普通工作底稿包装成 validated Pre/Quick、COMMITTED、Human接受或投资决定。

**旧 Stock `FIRST_BUSINESS_BASELINE` 仍绑定最新完整年报/半年报及其后的全部声明正文。** `stock_research_sources.choose/capture`、稳定问题key、旧失败/恢复合同与自动监听，本次均未改动。这一特定来源合同不提升为所有研究的全局前置要求；也不能靠“公告按需”偷偷改写旧执行的输入范围。

后续已交付 `reviewed_question_input`、`stock_question_host`、`stock_question_continuation` 及 `stock_daily_question`，不能继续笼统称为“按问题 Stock 接续未实现”。这些入口保留各自的来源、前驱、预算及保存绑定；当前 daily 请求默认关闭，当前沃顿的财报范围和新浪原件尚未通过该宿主的具体绑定。先用已取得的财报推进原问题并保存进度，真正运行时再落实该入口的输入合同；取得资料、有限分析、正式准入和默认自动运行分别验收。

## 验收与下一接点

本切片证明默认请求不执行六公司扫描、摘要不把未请求误称静默，以及原准入对可选/必要来源仍维持边界。新增回归是 synthetic 工程控制，不是公司研究或真实 source 可用性证据。

下一接点先恢复已有候选、来源与进度，交付一份有明确新信息/计算/裁定的研究接续；仅有恢复旧材料不能计为新的 Pre/Quick。旧 Stock 专用入口如何接入新问题范围另做薄改，不增加新的provider、scanner或通用调度框架。Research与Odds分离；Human保留最终资本决定。

外部复用依据：GitHub 官方 workflow_dispatch inputs 和 jobs.if 文档；boolean 使用 inputs context 保留类型。本轮不添加解析 YAML 的生产依赖。

## Radar 到问题的下一接点（2026-09-19）

遵守[Radar 来源资格与 Research Question Layer 合同](radar-research-question-contract-v0.md)：不同 Radar 各自验证 observation，不共用一种 Price Gate。先在 company-first context 形成具体、可证伪且可回答的问题，再沿本文声明必要证据、反证和缺口，最后进入既有 Pre admission。已声明问题的输入与显式执行已有实现，自动问题生成尚未实现。通用 `questions` 提示不等于合格 question candidate，标签/来源数量或涨幅不决定 Pre。

旧 `FIRST_BUSINESS_BASELINE` 的 stable key、失败及 lineage 不改；未来 THIN_ADAPTER 不能靠换问题名称或 key 重试已消费执行。Industry Inflection 尚未实现，公告收敛与必要来源失败的边界保持不变。
