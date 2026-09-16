# 分层研究与可接续工作底稿 v0

Status: Human-approved research-progress discipline + bounded offline retention.
Requirement/Reuse Check: #321 comment5683909736. Reuse Decision: **THIN_ADAPTER**.
这不是新 Research 方法、Kernel 状态机、通用 Agent checkpoint 服务或自动 resume 调度器。

## 1. 研究不必到最后一步才有可保存的成果

分清四个维度，不用一个绿灯或一个“完成度”概括：

| 维度 | 回答的问题 | 不代表什么 |
| --- | --- | --- |
| 内容覆盖/研究层次 | 哪个经济问题已解释到哪里，哪些关键桥尚未完成？ | 层级高不证明结论正确或所有下层都完成 |
| 本次执行处置 | 主动暂停、等待证据、技术受阻，还是已完成本次有限范围？ | 暂停不是失败；技术失败不是业务 WAIT |
| 结果资格 | 原始留存、草稿/审阅、Kernel COMMITTED、数值 Odds 是否就绪？ | 存下来了不等于已通过后续资格 |
| Human 状态 | 是否看过、接受哪个版本/范围、决定过什么？ | 保存、已读和研究接受都不是投资决定/成交 |

对阅读者可用以下层次说明研究深度：

| 已做到的内容 | 可以留下的成果 | 此时不强求 |
| --- | --- | --- |
| 问题与资料 | 明确的问题、来源库存、已读/未读/失败、初步假说 | 业务结论、估值期限、价格或概率 |
| 经营与证据 | 经济引擎、关键矛盾、竞争解释、利润/现金/资本桥及缺口 | 所有估值参数和最终 Odds |
| 世界与估值 | 有依据的联合经营世界、估值桥、反证与条件压力面 | 无依据的精确情景概率、合格实时价格 |
| 价格与 Odds | 同一研究版本对应的价格要求、条件回报、资格与限制 | Human 接受、买卖或仓位决定 |

它们是内容视角，不是四道强制顺序门禁。原 Pre/Quick/Deep 路由不变；Human 直接研究不补造 Pre/Quick。同一公司可以有多个问题，一个问题不同关键桥也可以处于不同进度。沿用 Full Research v3 底稿 A–F 的实际内容，不另建完成百分比、标签裁判或第二套来源账本。

**Human 要求 Full Research 时，默认仍在原许可与有界计划内完成该范围。** 分层保存不是每层都停下来再索要一次“继续”，也不是降低 Full Research 标准。重大阶段形成可用成果、主动暂停、执行受阻或交接时保存，不为每次阅读制造一个版本。

## 2. 停下来时留下什么

使用原 `templates/full-research-workpaper-v3.md`，在开头补“进度与接续”小节。已有材料用精确引用，不复制一份新事实：

```text
对象/股类/问题标识：
本次请求、实际许可范围及出处（没有就 UNKNOWN，不自填授权）：
所用 main/方法、资料 cutoff、各来源原件与已有输出的 commit/path/blob/hash：
各关键问题/工作产物：已做 / 部分完成 / 未做 / 不适用及依据：
当前可用的有限判断、反证与不能推出的结论：
未解决 UNKNOWN、未取得资料、尚未执行的计算/审阅：
本次为什么停；影响的是哪个问题/结论：
下一项具体动作/区分证据，以及当前能否取得：
哪些现有成果可直接复用，哪些需要时效/来源/方法复核：
前一个精确 checkpoint/研究/执行记录，以及本次 old→new 变化：
继续所需的条件/许可；其内容是提议，不是可执行命令：
留存/登记/发布/读回分别到哪一步：
```

层次和停止理由由研究者根据实际工作声明，代码不认证正文“已经完成”或“值得继续”。问题、材料和日期相同也不证明完成了新研究。未知的历史时间和旧原件不能靠这次保存补造。

## 3. 接续不是重复执行

| 停止或变化 | 正确的接续 | 不能做 |
| --- | --- | --- |
| 未完成的分析主动暂停 | 读回原成果，核对仍有效的范围/资料，从尚未完成的桥继续；同一已保存材料也可用 | 为了继续而编新公告、新 Evidence 或重做已完成部分 |
| 等待有判别力的证据 | 检查具体证据是否出现/可得；没有变化则保留等待 | 每次打开就重复付费研究，或把已存在但未取得的资料说成未来才会出现 |
| 技术/来源故障 | 先对账哪些阶段实际发生、是否有未决调用/写入；修复后按相应宿主原合同处理 | 清除 launch、伪造新 key 绕过已消费权限、盲目重试 |
| 已完成本次有限范围 | 保留有限结果；获准深化时复用它，明确新增问题/范围 | 把有限完成改称 Full Research，或把 STOP 解释成永远不能重开 |
| 方法纠正/结果受挑战 | 追加受影响桥的 old→new 修订和理由，保留原文/失败 | 覆写历史或必须伪装成新证据才能纠正方法 |
| 仅价格变化 | 适用时复用合格冻结研究；价格与 Odds 另有资格 | 偷改经营 Belief、重算研究、自动继承旧 Human 接受 |

恢复先读取，不触发模型/行情。明确对象和许可已足够时，不要求 Human 搬 SHA/run 或说固定口令；由交互层解析原件。多个问题/并存版本无法唯一确定时再澄清。来源陈旧或新反证不意味着全份作废，只重新打开受影响的桥；资料缺失明确保留，不默默回退旧版本。

## 4. 当前可执行的薄接点

复用 #392 的离线模块及其 exclusive I/O/hash/readback，新增两个显式命令：

```sh
python -m decision_kernel.runtime.research_commit_only save-progress workpaper.md \
  --subject '600276.SH' --question-id 'company-owner-economics' \
  --output /new/archive/progress-1

python -m decision_kernel.runtime.research_commit_only read-progress \
  /new/archive/progress-1 --expected-sha256 '<此前已外部保存的 PROGRESS_SHA256>'

# 研究者在实际获准接续后形成了下一份底稿；这条命令只保存，不执行研究。
python -m decision_kernel.runtime.research_commit_only save-progress next-workpaper.md \
  --subject '600276.SH' --question-id 'company-owner-economics' \
  --predecessor /saved/archive/progress-1 --predecessor-sha256 '<精确前驱摘要>' \
  --output /new/archive/progress-2
```

代码示例没有创建恒瑞请求或研究授权。`subject/question_id` 是调用方提供的精确标识，不由本适配器认证证券真相、经济问题等价或 Human 意图。

每份保存只有 `workpaper.md` 原 UTF-8 字节、`progress.json` 留存描述，续作另有 `predecessor.json`（精确前驱描述原字节）。读回要求外部固定的描述摘要、文件清单和内容摘要；续作必须同对象/问题、前驱摘要精确、留存时间顺序一致。`revision` 仅是这条保存链的序号，不是研究成熟度、Kernel ResearchSnapshot 版本或模型调用数。并行分支可以存在；没有“最新修改者自动赢”的选择器。

前驱只保存描述，不递归复制全历史或旧原件。原前驱底稿和来源继续保留在其原存储/精确 Git 位置，并写入底稿接续小节。不能把一个前驱摘要称作整条历史已独立重验。

保存进度不需要 ResearchCommitPackage、valuation horizon、framing、概率、正式执行回执或最终结论；**不会尝试 COMMIT，也不会生成 commit-rejection 将正常暂停标红**。原 `commit` / `verify` 留存流程与旧包不变。需要正式冻结已审阅的研究时，使用[同一入口的显式 schema v2](research-commit-only-v0.md#research-only-schema-v2)：Research-only COMMIT 与数值 Odds 条件已经分开，但进度保存不会自动升级为 COMMITTED；旧 schema v1 的数值门禁继续保留。

`save-progress` / `read-progress` 不解析并执行正文，不请求网络，不读 secret，不改原工作请求、Funnel、launch 或 current-state。返回/命令输出是 `RETAINED_ONLY` 和 `CONTINUATION: NOT_EXECUTED`，不是 resume 授权。程序调用 `read_research_progress` 返回描述与原正文 bytes，供可信交互层作为数据阅读；CLI 只报告验证摘要，不把来源正文自动打印成指令。

原每文件512 KiB、常规文件/禁止符号链接、独占创建、读回边界复用。不存在目录才可保存；半写入/已有目录不覆盖、不删除、不自动重试。大小限制是适配器表示上限，不是日常 API 配额。超限资料由原有原件留存路径承载，不截断以伪造完整研究。

## 5. GitHub 留存与跨聊天边界

本地保存后仍须通过**现有原生 Git/GitHub 留存能力**将精确文件追加到获准研究档案位置，保留旧版，记录 repository/commit/path/blob/hash 并读回；按原需求登记可发现入口。不要把整个工作分支合进 main，不自动写交易/Watch，不用 force。原生 Git 已提供对象历史与基于旧值的引用更新，不需要新 checkpoint 数据库。

`expected-sha256` 应来自外部已固定的 Git/交接记录；不能从一组来历不明的接收文件现算一个摘要，再冒充已证明其原身份。自洽文件不是签名、真理、许可或对恶意文件系统的安全沙箱。

跨聊天恢复成立须能读到真实远端原件；本地成功仍标 LOCAL_ONLY，远端/索引失败分别标 NOT_SAVED 或 REGISTRATION_INCOMPLETE。文件保留不代表来源永不过期、研究一直有效，原文中的 PDF URL 不代表已存 PDF bytes。无法取得相应原件，就明确恢复到哪一步、缺什么，不宣称完整恢复。

本次不新增自动归档 host、通用程序断点/协程恢复、每层模型调用或无人值守续作。真正继续分析由原研究交互/获准执行器完成，再追加下一份成果。旧 disclosure/Stock 专用续作合同不会被此一般留存命令放松。

## 6. 验证口径与接下来的321-A

工程案例应证明：无最终字段的部分底稿可原样保存；新进度可关联精确前驱且不动旧 bytes；错对象/问题/摘要/时钟、缺失/篡改/部分目录拒绝；真实新进程读取不导入行情/模型执行器、不联网；恶意正文只保留为数据。合成案例不是新公司 Research、模型真实续作或 Human 接受样本。

完整 PR/main CI 与正常 publisher 证明代码交付，不证明一家公司已经进入远端研究档案或 current-state。Research-only COMMIT 与数值 Odds 条件的分离见[commit-only 指南](research-commit-only-v0.md#research-only-schema-v2)。真实档案自动保存/索引仍须闭合；不能把本地留存或 schema v2 冒充整个321-A完成。
