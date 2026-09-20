# 首例真实研究的执行接续

核对基线为 main `5d6db8e395c28d62318bc7476f8a405b6e8f0ad5`、reading `551b6d2a148ec798afae0e6f0139dd9a1087f14d`，以及 work `88784c6b84dbd497489ebb181d89fffc26fedce8`。本页保存本轮对现有实现和授权的只读审阅；没有实施下述第二版、形成可执行输入或发起模型调用。

## 已核实的执行条件

- 当前原 reader / `stock_daily_question.capacity()` 实际来源预算为 22/32；一份完整新问题最坏新增 10 个来源，首例容得下。问题执行组当前 2/8。无需先扩容或删除旧历史。
- 普通 Git SourceRef 的 512 KiB 上限不是 Human 的 PDF 总预算。日常政策原有上限为最多 4 份与已声明问题相关的完整公开 CNINFO 发行人 PDF、合计 32 MiB；完整 context 最多 448 KiB，prompt 最多 512 KiB。当前 daily 把原 PDF 再当普通 SourceRef 读取，形成首版工程限制。
- 原 `external_research_admission` 与 `reviewed_question_input` 已支持 `LATEST_INVENTORY`，原 `stock_research_host.run_item` 已有查询回执、保存 journal 和必要 PRIMARY BODY 的实际配方。日常首版的 STATIC 限制不允许把本问题必要更新改成静态或可选。
- 原 `.github/workflows/stock-business-research.yml` 的 source-only 绑定仍限旧 603353/300711 修复范围。不能将沃顿塞入旧修复配置或重开消费过的 `FIRST_BUSINESS_BASELINE`；旧 non-daily SUB2API 宿主也不作为当前 DeepSeek 政策的捷径。

## 取得真实材料之后的最小接续

先核验真实原件、发行人和公告身份、完整页文字、更新窗口与相关性，实测 PDF、保存 ZIP、context 和 prompt 字节数，再决定原接口的最小适配。问题须先正式保存，随后才有本次实际 preflight；此前来源审阅不能回填成后来预检的成功时钟。

关系检索已经完成；具体机制仍待真实材料确定。若最终仍属旧基线问题的实质接续，应保留旧根并按原接续关系与适用权限处理，不能以新 key 进入仅接新独立问题的 daily 宿主。以下只是现有来源接口的复用候选，没有预先裁定本草稿应执行为新问题。

可复用原 `GitHubAPI.archive` → `current_state.unpack_archive` → `stock_source_successor._saved_document`，从合格来源 artifact 取得实际 PDF 字节，再按已经批准的 PDF 总预算解析；普通 JSON / SourceRef 的 512 KiB 上限继续保留。现有 source run/artifact、inventory、journal、PDF 与 extraction 的绑定仍需成立，不能把任意本地 PDF 打成 ZIP 就称为原来源 workflow 的成功 artifact。浏览器或 Human 提供的原文件须如实记其取得方式，再审阅与原保管接口的实际适配，不伪造成功下载日志。

原 archive 还另有限制：完整 ZIP ≤32 MiB、展开后总量 ≤96 MiB、单 entry ≤32 MiB。它们与 PDF 合计 32 MiB 是独立检查。不能删必要正文、裁掉反证或截断 context 以通过边界；也不在取得真实材料前提高全局上限。

在既定沃顿问题和原必要来源范围内，复用原 `LATEST_INVENTORY` 与保存 PDF 接口属于本次工程接续。首版 STATIC 是原施工收窄，不是 Human 对后续版本的永久禁止；用户的“继续”承接来源模式匹配工作。任何第二版均须具体留存、普通 PR、完整 CI、独立 main CI 和正常发布后才可能启用。旧 v1 政策及其消费记录保留，slots/day/question 命名空间不重置，原 provider、输出及外发预算不变；仍最多消费 10 个已保存正常市场日、每市场日最多 1 次新问题尝试，最早市场日为 2026-09-18，最迟执行时间为 2026-10-20T00:00:00Z。

新来源接口并未实施；材料是否能在现有全部预算内回答问题尚未建立。若真实材料要求扩大经济问题、外发范围、文档/字节预算、次数日期或更换 provider，那才是需要 Human 决定的具体取舍。

## 本轮停止点与可交接材料

标准浏览器已读到 CNINFO 半年报和库存入口的明确阻断页面；发行人正常目录没有所需的当前报告。原始 PDF 取得数为 0，9/19–9/20 完整公告覆盖仍 UNKNOWN。独立去重审阅见本目录 `dedup-review.md`，它不替代材料准入或赋予新问题身份。

来源接续首先需要：

1. 沃顿科技 2026 年半年度报告原始 PDF，官方公告 `1225486931`、披露日 2026-08-21。
2. 2026-07-01 至 2026-09-20 的完整官方公告列表/导出记录，以及对膜业务利润和现金问题实际相关的原始公告文件。已知 7/8 膜分离工程合同公告 `1225413015`、9/17 投资者关系记录 `1225569161` 仍须审阅；其他已发现的交易、会计政策和资金事项不能因正文缺失就断言不相关。
3. 若半年报比较数据不足以建立必要基线，再使用已经披露的 2025 年报原件 `1225028676`。历史收入重要性不能替代 2026H1 的利润/现金判断。

可以由正常可访问的官方来源取得，也可以接收 Human 已下载的上述文件并如实保留其来路。文件提供本身不等于官方字节一致性、动态窗口完整性或 runtime admission 已通过；这些仍由后续实际核验完成。本轮没有提出模型调用或投资决定的追加许可请求。

当前仍为来源受限草稿，正式新问题数为 0；Pre、Quick、Deep、Odds、Watch 均未执行，没有消费日常 slot。P0-A 的真实 Pre 到 Brief 及 P0-B 的研究回应仍待实际发生，完整人机闭环天数保持 0。
