**000920.SZ 沃顿科技：已有研究与问题关系审阅，2026-09-20**

本轮已完成下述明确范围内的关系检索，可关闭前一来源档案中“当前入口与已知分支关系尚未完成审阅”的待办。在这些入口中，没有发现另一份沃顿已执行、已完成或并行登记的正式问题。当前应接续 `062f9761224e3aecfa9e314222d5069e79a351be` 已保存的同一来源草稿；本次检索不创建新问题、研究执行或来源资格。

固定方法 main：`5d6db8e395c28d62318bc7476f8a405b6e8f0ad5`；固定阅读 R：`551b6d2a148ec798afae0e6f0139dd9a1087f14d`；reading_hash：`a04fafd28ca842e8b95e395fd610baeee50558ea21d0b4f38ac801a420b58ce7`；原 work：`88784c6b84dbd497489ebb181d89fffc26fedce8`。元数据查询是本轮实际可见讨论，时间范围另见随附证据，不冒充全部发生在 R 生成之前。

已读同 M 的 `AGENTS.md`、`docs/RESEARCH-ENTRY.md`、`docs/research-source-scope-v0.md`、`docs/radar-research-question-contract-v0.md`、`docs/reviewed-question-input-v0.md`，并核对原 `reviewed_question_input` 和 `stock_research_intake` 的关系与问题定义。原规范要求保留同证券经济问题身份及前驱，不允许以换 key、版本或来路重试旧执行；原 catalog 去重也不认证自然语言问题独立性。

| 已查入口 | 实际证据与关系 |
| --- | --- |
| 同 M registry 与同 R registry 副本 | 完整 56 条引用；R 引用的 registry blob 为 `e03b441dcbff47f6147b25a2b274001a65fe7616`，其返回正文与 M 原文件逐字相等。沃顿唯一专属登记为 `p0-000920-membrane-profit-cash-source-review-20260920`，是 ON_DEMAND 来源草稿。49 条已物化记录、9 条 incremental candidate 与其余档案没有另一个沃顿研究命中。 |
| 原 execution catalog | `research_runs/execution-inputs.json` 两条输入均为 `605296.SH`；已读取各自精确 input blob 的证券与问题，不是沃顿。其既有冲突保留，不用清空目录证明本题无重复。 |
| 完整 work tip 的旧沃顿根 | `research_runs/candidates/stock-business/66446c4257a92cd4576ee87ff1bd4ead51ca61a4292befc55cbde3d514b5542c/` 仅有 prepare、failure、host-receipt 三文件，均已完整读取；无 input、candidate、launch 或子执行。它是 `FIRST_BUSINESS_BASELINE` 的来源准备失败，formal_research_started=false、Funnel NOT_REACHED、automatic_retry=false。 |
| 同 work 的所有 stock-question roots 与同 R 结果 | 只有广哈通信 300711 的 `restricted-proceeds-internal-transfer-2026h1` 原根与固定 technical-continuation-v1。是同一问题的技术关系，不是沃顿研究，也不构成两个新日常问题。 |
| 已知沃顿来源档案 | 精确 `062f9761224e3aecfa9e314222d5069e79a351be` 下七文件身份/字节已核对；已审阅 README、批次处置、事前范围、question-review、workpaper。其问题正是本轮待续草稿，状态 DRAFT / NOT_ADMITTED / NOT_EXECUTED，NEW_DISTINCT_QUESTION 尚未赋予。 |
| 已取得本地 refs 的 tip 文本 | 对现有 529 个 heads/remotes/tags、523 个不同 tip 对 000920、沃顿、vontron、woton 做不区分大小写的扩展正则文本查询（原 git grep，排除二进制）；51 个 tip 命中，共 40 路径、43 个 path/blob 版本，0 读取错误。逐项归类为同一草稿、旧失败、市场观察、读取副本、工程诊断或测试；Fibocom 底稿中的沃顿仅是旧来源失败边界引用。没有额外沃顿问题原件命中。 |
| GitHub issue/PR 元数据 | 在本仓库标题、正文、评论中分别检索 000920、沃顿、vontron、woton，并补查膜/膜工程，共 12 次有效查询，均 incomplete_results=false。命中 issues #297/#351，PRs #447/#448/#449/#473/#474；前四别名中 vontron/woton 为 0。完整取得并关键词扫描 #297 的 361 条评论及 #351 的 28 条评论，重要命中读完整正文；五份 PR 正文与可见讨论均已检查。工程探测、reader 和 daily 接线不构成研究结果。 |

旧根的精确 blob：prepare `f0efbab42adde8af50977c7f51f75087e518a0df`，failure `531b5e21ed15928f2abf2550b0800dc666b47ffb`，host-receipt `8c134ee737a62820a8d8c04eb6048661c3028fe1`。[当前草稿事前范围](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5749522521)、[已保存的收窄结果](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5749800329)、[本轮继续同一草稿的记录](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5750079861)相互一致；不是发现了第二份新题。

**独立性裁定：目前不能仅凭本次去重认定 NEW_DISTINCT_QUESTION。** 旧基线原问句已经包含“主营业务与触发板块的真实联系，收入、利润和现金流如何暴露”。现在“2026H1 膜产品/膜工程收入毛利如何转化为集团利润和经营现金”确实提出更窄的分析范围，但与旧基线的未答暴露问题有实质重叠。加上期间、拆细变量或改名称都不是独立性的充分依据。未发现额外正式重复问题，可以结束这次关系检索；它不等于已证明新问题的经济独立性、可回答性或执行权限。此处是有界语义审阅，不是独立经济认证或 Human 接受。

接续保持同一草稿及旧根引用，继续原已经声明的资料与分析范围。不要为了适配新入口改问题或创建新 key。实际具体问题形成时，应说明利润/现金转换机制及反证边界与旧基线的关系，按原宿主的相应关系和权限处理；仍属同题就保留原接续关系。无需再次穷尽更多不可达历史后才继续当前资料工作。

来源资格仍未因去重改善：原档案中的 2026H1 官方主报告原文/原始 PDF、必要的 7/1–9/20 相关更新覆盖，以及需用的 2025 基线原件均保留各自缺口；本轮来源补充的实际状态以其独立回执为准。本去重任务未访问发行人来源。不得把必要动态更新降为 STATIC/可选，不把来源失败写作 WAIT/DROP、未来披露等待、公开信息穷尽或 Human 拒绝。当前无 formal question admission、Pre/Quick、日常 slot 消费、COMMITTED 或投资权限。

完整 refs、命中 path/blob、同 R 绑定及元数据查询证据在 `dedup-evidence.json`。本次范围是现有本地 refs 的 tip 文本、上述固定读取入口及可见 GitHub 讨论；没有逐个读取所有祖先版本，未枚举不可达/已删除 refs、未登记聊天、二进制正文或不含检索词的记录。词法索引可能遗漏表达不同的材料，因此只作本范围内的明确结论。本次无仓库改动、GitHub 写入、来源请求、workflow dispatch 或测试。
