# Decision Kernel 交接书 — 2026-09-13 Stock Business 来源预检

> 本文给下一位 ChatGPT / Codex / 人类维护者。它记录本轮结束时的精确现场与禁止事项，不授予新的 Investment Authority，也不替代 #297 最新需求排序。

## 0. 先读这里：本轮结束时的精确现场

Repository: `auguspp/decision-kernel`

本轮结束前最后实际读回：

- `main = 99ad4e9391231be86b0bff27f2776a3966215fe8`
- `read-model/current-state = d0b02f8d2d92c99aad1f4a63ea246beda399a4fd`
- `research-work/stock-business-v0 = dc75bd59a06fa7b6da30c855fe232348270db089`
- P0 canonical roadmap / receipt thread: Issue `#297`
- latest source-only run: `34765190284`
- latest identified Research execution remains: `34751517820`

新聊天必须重新读取可变 refs；上面 SHA 是交接时快照，不是永久常量。

Human 本轮最后明确要求：结束当前聊天，由下一聊天接手。因此本文之后不要在本聊天继续施工、Research 或重跑。

## 1. 不可破坏的项目规则

- **Evidence changes Belief. Price changes Odds.**
- `Data != Evidence != Judgment != Decision`。
- Radar 只分配注意力；价格强势不能自动证明业务受益。
- Kernel 验证 identity / time / source consistency，不认证 truth。
- UNKNOWN 合法；不要补造 WHY。
- AI 没有 Investment Authority；Human 保留研究接受、判断和资本决定权。
- GitHub 是 canonical state/evidence/process backend；ChatGPT 是 research/decision interaction layer。
- Reuse First。局部缺口优先配置、组合或 THIN_ADAPTER；不要新造 Agent/DAG/provider/scheduler framework。
- Requirements Management 定义和排序需求；Main Construction 负责 repo 实现。

公司 Research / 估值 / Odds / 第一笔仍先读当前 `AGENTS.md`、`docs/RESEARCH-ENTRY.md` 及其链接案例。

## 2. 本轮已经完成的工程，不要重做

### #352 — 来源预检能力

PR `#352` 已合并。它在原 CNINFO / PDF / PDFium 路径上增加：

- source-only / preparation-only 诊断；
- 一次枚举全部缺失视觉页，而不是碰到第一页就停止；
- 只有全部必需正文可读时才保留完整 `prepared-context.json`；
- 完整输入超限时仍留存精确字节/hash，不裁正文；
- 和顺原法律意见书 `1225530957` 第25页绑定的视觉读取。

完整 PR CI `34758642578`：2993 passed；合并后主干 CI `34759544297`：2993 passed。正常读取发布 `34760157437` 成功。

### #353 — 来源专用生产接线

PR `#353` 已合并到当前 main `99ad4e...`。

它把来源预检接进**原** `stock-business-research` workflow：

- 手动参数 `prepare-sources=true`；
- `recover-sources=false`；
- job `prepare-stock-sources` 只有 contents/actions/issues READ；
- 不提供 Sub2API secret；
- 原 Research/model job 在 source-only 模式跳过；
- source-only 分支在 `run_item` / Retainer / admission / model 之前返回；
- 不写 `research-work/stock-business-v0`；
- fixed reader 区分 latest workflow invocation、latest Research execution、latest source preparation attempt，不能把预检当成 Pre/Quick。

完整 PR CI `34763198724`：3044 passed，无 pytest skip；AI construction review `5191063198`。合并后主干 CI `34764064026`：3044 passed；正常 publisher `34764691738` 成功；固定读取 `5ce32bde...` 已读回。

工程发布回执：#297 comment `5654117605`。

## 3. 刚刚已经真实执行的 source-only run：不要重复 dispatch

Human 已在原 Actions MCP 会话启动唯一一次来源专用预检：

- workflow: `stock-business-research`
- run: **`34765190284`**
- event: `workflow_dispatch`
- run_attempt: `1`
- head: `99ad4e9391231be86b0bff27f2776a3966215fe8`
- source Stock run: `34673882756`
- mode: `prepare-sources=true`, `recover-sources=false`
- job `prepare-stock-sources`: failure
- job `research-stock-business`: skipped
- batch status: `SOURCE_PREPARATION_INCOMPLETE`
- `model_calls = 0`
- `research_work_writes = 0`
- `formal_research_started = false`
- `research_execution_allowed = false`
- `unattempted_issuers = []`

因此 workflow conclusion `failure` 是**来源预检未全通过**，不是 Research failure、不是 WAIT、不是模型失败。

不要 Re-run `34765190284`，不要再次用完全相同材料 dispatch source-only run；任何下一次执行必须先有真实新增读取或完整输入处理材料。

## 4. source-only run 的真实结果

### 603353.SH 和顺石油

本次终于检查了全部计划正文范围：

- selected announcements: **20**
- checked bodies: **19**
- `all_planned_bodies_inspected = true`
- `unattempted_ids = []`
- `complete_context = null`
- status: `PREPARATION_INCOMPLETE`

新的唯一已知缺口不是旧第25页，而是：

- announcement id: **`1225530965`**
- PDF SHA256: **`cc3a234f7551ef02c401fae60452b891ca48ef0047aad7e26981e0f4ec7948fa`**
- page: **23**
- error: `required page visual review unavailable`
- original extracted text SHA256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`（空文本）
- render: RGB, width `1180`, height `1678`, scale `2`, rotation `0`, draw_annots `true`
- pixels SHA256: **`196d9e941525f37577039e27b81fed72354caa0f1afb2844f856940ef6177059`**

下一聊天第一项来源工作是从 artifact 中实际查看这页，写一个与原 PDF / page / pixels / engine 精确绑定的 `AI_VISUAL_READING`，明确 unknowns。不能认证签章、身份、签署日期或法律效力；如果页面内容与假设不同，就按实际内容记录，不要先猜它是签章页。

### 300711.SZ 广哈通信

本次 13/13 计划正文全部检查完成：

- selected IDs: **13**
- checked IDs: **13**
- missing page reviews: `[]`
- `all_planned_bodies_inspected = true`
- `unattempted_ids = []`
- status: `PREPARATION_INCOMPLETE`

完整上下文已经真实留存：

- path: `prepared-context.json`
- bytes: **636,462**
- SHA256: **`4cb6c5a18a18ef6ed8b011f315c7bac000a3ecaaf4b21b6cd72b476a3344cbf0`**
- current context limit: `458,752` bytes (448 KiB)
- checked source-reference limit: `524,288` bytes (512 KiB)
- `within_current_limit = false`
- `within_source_reference_limit = false`
- error: `full business context too large; no clipping`

这已经证明广哈不是缺材料。下一缺口是**完整输入的生产无损存储 / 解码 / model egress 合同**。

注意：此前本地原型曾证明同一完整 JSON 可以无损压缩到约 221 KiB，但这只证明 storage 可压缩，**不证明解码后的完整模型请求能满足 `STOCK_PROMPT_BYTES=512KiB`**。下一施工必须同时验证：

1. 持久化 identity / checked-source 合同；
2. 解码后 byte identity；
3. 最终 Pre/Quick request 的真实字节限制；
4. 不裁正文、不丢风险材料、不以摘要替代必需正文；
5. 不把压缩串直接交给模型；
6. 不为过测试而笼统放宽共享 512KiB 身份边界。

## 5. 本次 artifact 与正常 fixed-reading

来源预检 artifact 已成功上传：

- artifact id: **`10320565453`**
- name: `stock-source-preparation-34765190284-1`
- ZIP size: **12,563,240 bytes**
- ZIP digest: **`sha256:25cda8a1d4afb4783432320239cd6271fe193cfdc5ed6dc2095a5deb833dce9c`**
- file count in upload log: **91**
- expiry reported by GitHub: `2026-10-13T15:19:28Z`

本聊天没有把 ZIP 下载并逐文件解压验收。下一聊天应先下载一次、核对 digest、安全路径/CRC/文件数，再从里面读取和顺 `1225530965` 原 PDF 和广哈 `prepared-context.json`。不要用日志代替 artifact 字节审计。

source-only run 完成后普通 fixed-reader 又实际运行：

- publisher run: **`34765255273`**
- conclusion: success
- latest read ref: **`d0b02f8d2d92c99aad1f4a63ea246beda399a4fd`**
- code_commit: `99ad4e9391231be86b0bff27f2776a3966215fe8`
- checks.finished_at: `2026-09-13T15:20:07.389806+00:00`

固定读取现在正确显示：

- `latest_source_preparation_attempt = 34765190284`（failure，来源预检）
- `latest_execution_attempt = 34751517820`（旧 Research/source-recovery run）
- `latest_workflow_invocation = 34765190284`
- 原 Stock Research work ref 仍为 `dc75bd59...`
- 旧候选/失败字节未被 source-only run 改写。

## 6. 四股当前状态

| 公司 | 当前状态 | 下一含义 |
| --- | --- | --- |
| 光电股份 `600184.SH` | 已有真实 Pre/Quick candidate，`WAIT_FOR_TRIGGER` | 直接复用，不重跑；旧估值桥挑战仍独立存在 |
| 东软载波 `300183.SZ` | 已有真实 Pre/Quick candidate，`WAIT_FOR_TRIGGER` | 直接复用，不重跑 |
| 和顺石油 `603353.SH` | source-only preflight 只剩 `1225530965` page23 视觉读取缺口 | 先补精确页读取，再做完整来源复核；尚未 Pre/Quick |
| 广哈通信 `300711.SZ` | 13/13 来源齐全；完整 context 636,462 bytes 超 448/512KiB | 先实现无损 storage/decode/egress 合同；尚未 Pre/Quick |

原 `600967.SH`、`001316.SZ` 仍保持原 Stock 数据资格失败，不因本轮升为业务 Research 输入。

## 7. 下一聊天应怎样继续

### 第一阶段：只读验收 source-only artifact

1. 重新读取 `main`、`read-model/current-state`、`research-work/stock-business-v0`。
2. 确认没有新的对应施工/dispatch 已经发生；有则先验收，不重复。
3. 下载 artifact `10320565453` 一次并核对 digest。
4. 核对 `source-preparation-batch.json`、两家公司 `source-preparation.json`、原 PDFs、extraction/page-reading 记录和广哈 `prepared-context.json`。

### 第二阶段：修两个不同的 blocker

**和顺**：对 `1225530965` page23 做 same-PDF whole-page reading，并把可信 note 放到主干已有 `research_runs/source-readings/<pdf_sha>/page-23.json` 合同下；先做精确像素/引擎绑定和 unknowns。不要凭标题或页号猜内容。

**广哈**：使用这次真实 `prepared-context.json` 设计最小 THIN_ADAPTER，闭合完整 context 的 storage / checked-source / decode / egress / prompt-size。必须证明 decode 后与 `4cb6c5...` 原文一致，并证明最终模型输入合同，而不只是“压缩文件能存下”。

如果两个 blocker 的实现需要不同 PR，可以分开；不要为了“一次全部绿”造新框架。

### 第三阶段：合法 Research successor

旧 `source-recovery-v1` 已消耗，source-only run 也已经真实运行。后续不能：

- 重置或删除旧 marker；
- 重跑 `34751517820`；
- Re-run `34765190284`；
- 换许可编号、日期或 v2 key 绕过去重；
- 用 source-only success/failure 直接启动模型。

只有当新的页读取 / 完整输入适配形成真实新增材料后，才建立与：

- 原父失败；
- 已消耗的 `source-recovery-v1`；
- source-only run `34765190284`；
- fixed reading `d0b02f8d...`；
- Human permission / Reuse Check #297 comment `5652950925`

的合法 successor 绑定。

Research 范围仍只允许和顺、广哈原首次业务 **Pre / 必要 Quick**。Pre 可停止；Quick 只按原 Funnel 路由执行。没有自动 Deep、Odds、Action、买卖、仓位或监控注册权限。

### 第四阶段：发布与自然使用

真实 Research 完成后必须：

- 保留原 source-only artifact / old failures；
- 正常发布进 fixed reading；
- 明确 latest source preparation 与 latest Research execution；
- Brief 中区分 Market Expression / Business Benefit / System Gap；
- 四股首个闭环成立后再进入 5–10 个真实交易日的自然使用观察，不能补造历史样本。

## 8. 不要做的事

- 不要重新设计整个系统。
- 不要另建 provider / Agent / DAG / scheduler framework。
- 不要启动新的 Stock 行情扫描来解决这两个来源问题。
- 不要重跑光电或东软。
- 不要再次 `recover-sources=true`。
- 不要把和顺缺页解释成业务不受益。
- 不要把广哈容量失败解释成 WAIT。
- 不要把 workflow `failure` 冒充 Research failure。
- 不要裁剪广哈正文或只留“重要”材料。
- 不要要求 Human 手工找公告、查乱码或再次批准项目额度。
- 不要因为 user 在新聊天说“继续”就自动视作新的 Research/Investment Authority；先按本文精确接点恢复。

## 9. 关键 canonical refs / receipts

- 四股首次业务研究 Human 请求：#297 comment `5651083343`
- 三家来源恢复许可（历史）：#297 comment `5652047028`
- 两家剩余来源/输入修复 Human 同意 + Reuse Check：#297 comment `5652950925`
- run `34751517820` 验收与新 blocker 诊断：#297 comment `5652913153`
- #352 合并后继续 #353 的实施接点：#297 comment `5653558242`
- #353 工程/发布验收：#297 comment `5654117605`
- source-only run: `34765190284`
- source-only artifact: `10320565453`
- source-only publisher: `34765255273`
- latest fixed reading at handoff: `d0b02f8d2d92c99aad1f4a63ea246beda399a4fd`

本文是本轮结束的正式工程交接。下一聊天从 source-only artifact 的实际字节验收开始，不从 #352/#353 重来。