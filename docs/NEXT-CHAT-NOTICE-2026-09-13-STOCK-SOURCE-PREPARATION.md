# 下一聊天通知 — 2026-09-13 Stock Business 来源预检交接

继续 `auguspp/decision-kernel` 的 Decision Kernel #297 P0，但**不要重新设计系统，也不要重做 #352/#353**。

先完整阅读：

`docs/HANDOVER-2026-09-13-STOCK-SOURCE-PREPARATION.md`

然后重新读取可变 refs：

- `main`
- `read-model/current-state`
- `research-work/stock-business-v0`

交接时快照：

- main = `99ad4e9391231be86b0bff27f2776a3966215fe8`
- read-model/current-state = `d0b02f8d2d92c99aad1f4a63ea246beda399a4fd`
- research-work/stock-business-v0 = `dc75bd59a06fa7b6da30c855fe232348270db089`

这些 SHA 只是交接时快照，新聊天必须先重新读取，不能盲用。

## 当前真实停点

#352、#353 已完成、合并并通过完整 CI / 主干 CI / 正常 fixed-reading 发布。

Human 已经启动一次来源专用预检；它已经结束，不要再次 dispatch 同一批材料：

- workflow `stock-business-research`
- run **34765190284**
- head `99ad4e9391231be86b0bff27f2776a3966215fe8`
- attempt 1
- `prepare-sources=true`
- `recover-sources=false`
- conclusion `failure`
- source-only job `prepare-stock-sources` 实际运行
- Research/model job `research-stock-business` skipped
- `model_calls=0`
- `research_work_writes=0`
- `formal_research_started=false`
- batch=`SOURCE_PREPARATION_INCOMPLETE`

这是来源预检 failure，不是 Research failure、不是 WAIT。

artifact：

- id **10320565453**
- name `stock-source-preparation-34765190284-1`
- size 12,563,240 bytes
- digest `sha256:25cda8a1d4afb4783432320239cd6271fe193cfdc5ed6dc2095a5deb833dce9c`
- upload log 91 files

本交接聊天没有下载并逐文件解压该 ZIP。**下一聊天第一件事就是下载一次并核对 digest / 文件完整性；不要拿日志代替 artifact 字节验收。**

## 两家准确结果

### 603353.SH 和顺石油

20 个 selected announcements 已全部走到检查流程；19 个 body checked，`unattempted_ids=[]`。现在唯一已知缺口：

- announcement `1225530965`
- PDF sha256 `cc3a234f7551ef02c401fae60452b891ca48ef0047aad7e26981e0f4ec7948fa`
- page 23
- original extracted text empty
- render RGB 1180x1678, scale2, rotation0, draw_annots=true
- pixels sha256 `196d9e941525f37577039e27b81fed72354caa0f1afb2844f856940ef6177059`
- error `required page visual review unavailable`

先从 artifact 实际查看该页，再写与 PDF/page/render/engine 精确绑定的 `AI_VISUAL_READING`；UNKNOWNs 必须明确。不要预设它一定是什么页，也不要认证签章真实性、人员身份、签署日期或法律效力。

### 300711.SZ 广哈通信

13/13 selected bodies 全部 checked，missing page reviews 为空；真正 blocker 是完整输入容量：

- `prepared-context.json`
- bytes **636,462**
- sha256 `4cb6c5a18a18ef6ed8b011f315c7bac000a3ecaaf4b21b6cd72b476a3344cbf0`
- 448KiB context limit 不通过
- 512KiB checked-source/reference limit 也不通过
- error `full business context too large; no clipping`

不要删页、裁正文、只留支持证据或把摘要替代必需原文。此前本地“压缩后约221KiB”只证明 storage 原型，不证明 decode 后最终模型 prompt 能过 `STOCK_PROMPT_BYTES=512KiB`。下一施工必须把 storage / byte identity / checked-source / decode / final model egress / prompt-size 一起闭合。

## 四股当前状态

- 光电股份 `600184.SH`：已有真实 Pre/Quick candidate，`WAIT_FOR_TRIGGER`，直接复用。
- 东软载波 `300183.SZ`：已有真实 Pre/Quick candidate，`WAIT_FOR_TRIGGER`，直接复用。
- 和顺石油 `603353.SH`：尚未 Pre/Quick；只剩一个新的 page23 source gap。
- 广哈通信 `300711.SZ`：尚未 Pre/Quick；来源齐全但完整 context 超当前输入/引用限制。

`600967.SH`、`001316.SZ` 继续保留原 Stock 数据资格失败，不升为本轮业务 Research。

## 固定读取已经更新

source-only run 后正常 publisher：

- run `34765255273`
- success
- fixed reading `d0b02f8d2d92c99aad1f4a63ea246beda399a4fd`

读取入口现在应区分：

- latest source preparation attempt = `34765190284`
- latest Research execution attempt = `34751517820`
- old Research work commit 仍 `dc75bd59...`

source-only run 没有改写旧 candidate/failure，也没有新的 Human Action。

## 下一聊天的执行顺序

1. 重新读 main / fixed reading / work ref，检查是否已有别人继续施工或新增 run；有则先验收，绝不重复。
2. 下载 artifact 10320565453 并做字节级验收。
3. 查看和顺 `1225530965` page23，形成可信 same-PDF page reading；按 Reuse First / THIN_ADAPTER 落地主干并完整 CI。
4. 用广哈真实 `prepared-context.json` 设计最小无损完整输入桥，必须证明原文 round-trip identity 与最终 Pre/Quick request-size；不要盲目放宽全局限制。
5. 只有形成真实新增读取/输入处理材料后，才建立合法 successor，绑定旧父失败、已消耗 source-recovery-v1、source-only run34765190284、fixed reading、已有 Human comment5652950925。
6. 之后只完成和顺、广哈原首次业务 **Pre / 必要 Quick**。Pre 可停止；Quick 仅按原 Funnel 路由。没有自动 Deep/Odds/Action/买卖/仓位/监控权限。
7. 完成后正常发布 fixed reading，并在 Brief 中继续区分 Market Expression / Business Benefit / System Gap；四股闭环之后才开始真实 5–10 交易日观察。

## 明确禁止

- 不 Re-run `34765190284`。
- 不再次 `recover-sources=true`。
- 不重跑 `34751517820`、光电或东软。
- 不换许可号、日期或 key 绕去重。
- 不把来源 failure 写成 WAIT 或业务不受益。
- 不裁广哈完整正文。
- 不要求 Human 手工找报告/查乱码/重新批准额度。
- 不施工 #321 / #331 或新 Agent/DAG/provider/scheduler framework 来抢占当前精确接点。

关键 #297 回执：

- 5651083343：四股首次业务研究 Human 请求
- 5652047028：历史来源恢复许可
- 5652913153：run34751517820 验收/新 blocker
- 5652950925：和顺/广哈剩余来源和完整输入处理 Human 同意 + Reuse Check
- 5653558242：#352 后 #353 实施接点
- 5654117605：#353 工程/发布验收

如果 Human 在新聊天只说“继续”，就从**artifact10320565453 字节验收**开始，不从设计、行情扫描或旧恢复任务重来。