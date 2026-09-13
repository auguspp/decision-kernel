# Next Chat Notice — 2026-09-11

## 2026-09-13 追加：公司研究与投资判断入口

涉及公司Research、估值、Odds、第一笔或历史结论质疑，先按当前main读取 [docs/RESEARCH-ENTRY.md](RESEARCH-ENTRY.md)，包括其中案例勘误。本文以下仍是9月11日工程交接快照，不得当作今天最新生产状态；#297实际优先级按最新明确回执恢复。研究方法补充不授权#321 runtime施工，不自动登记监控。

请先阅读：`docs/HANDOVER-2026-09-11.md`。

然后直接接当前 P0，不要重新设计整个系统。

## 当前第一优先级

当前主线是 **Sector 9/10 缺日恢复**，但必须从正确接点继续：

1. 先重新读取 `main` 和 `read-model/current-state`；本通知中的 SHA 只是交接时快照。
2. 读取 #297 最新三个关键回执：
   - comment `5630416664`：真实 one-shot recovery 在 HTTP429 `request limit exceeded` 失败；
   - comment `5630590808`：剩余211条 HiThink逐指数 historical 不再是首选；
   - comment `5631452967`：AKShare/10jqka 免费 public-history 5-code probe 的施工前 Reuse Check。
3. **不要 Re-run `sector-recovery-once` run34566950303，也不要继续剩余211条 HiThink history。**
4. Human 如果在新对话说“继续”，第一可执行任务是最小 **5-code AKShare/10jqka source-identity probe**：
   - codes: `881101.TI`, `881270.TI`, `884001.TI`, `884002.TI`, `884023.TI`
   - dates: `2026-09-09`, `2026-09-10`
   - compare: `close / volume / turnover`
   - against retained HiThink originals in artifact `10187281705`
   - public requests max=5
   - no HiThink/Sub2API secret
   - no retry loop
   - no state/cache/event/Research writes
   - retain raw THS `.js`, normalized comparison and hashes
   - any identity/field/value mismatch fails closed
5. **Probe 目前只有设计记录，没有代码、没有 workflow、没有真实请求。** 不得误报已运行。
6. 即使 5/5 exact match，也不能自动扩到321条或直接 promote Sector checkpoint；先审阅真实 probe evidence，再决定扩展。

## 当前 Sector 真实失败现场

`sector-recovery-once` run **34566950303** 已真实运行一次并失败：

- attempt 1；
- claim / authority checks 成功；
- 实际 HiThink 请求113次；
- 保存112个成功响应，其中 index history 110/321；
- 第111个 history attempt `884024.TI` 返回 HTTP429 / `request limit exceeded`；
- zero automatic retry 生效；
- production state writes = 0；
- events created = 0；
- restore authority = false；
- artifact **10187281705** 已保存，SHA256 `aedf5fc5507fa33c00f316be72c14b50962486961ba7199e097d2628205dc60b`。

最后合法 Sector session 仍是 **2026-09-09**。

## P0 其他未完成项不要丢

- Stock 当前 `CHECK_INCOMPLETE`，最后有效 2026-09-07；
- Daily Brief v1 仓库呈现规则已合并，但原生 Scheduled task 是否实际换成 v1 prompt 仍 UNKNOWN；
- Daily same-day Research → Brief 通用闭环未接通；
- Human continuation 有局部真实样本，但 general daily loop 未证明；
- P0-7 的 5–10 real trading days 不能提前开始计数。

## 已经证明的能力不要重做

- GitHub Actions + Sub2API 是可信执行宿主；
- Codex/validator smoke 已成功；
- 苏垦真实 bounded Research 已跑通并进入固定读取入口；
- 北大荒 Human continue → bounded continuation 已有真实案例；
- #318 HiThink failure diagnostics 已合并；
- #320 one-shot recovery capture 已合并，但真实 run 因429失败。

不要再测试“Web ChatGPT 能不能执行 validator”，不要重跑苏垦。

## #321 只登记，不施工

Issue **#321 Human-origin Direct Deep v2** 是新需求，但当前状态是：

`REQUIREMENT REGISTERED / NOT IMPLEMENTATION AUTHORITY`

核心需求包括：Direct Deep 不造 fake Funnel、Harness bounded 多轮 UNKNOWN compression、Research Commit 独立于 Market、Human-supplied price 只能生成 CONTEXT_ONLY Provisional Odds、无校准时不强迫 cardinal probability。

**#321 不抢占 #297 P0。**

## 必须保持

- Evidence changes Belief.
- Price changes Odds.
- Data != Evidence != Judgment != Decision.
- UNKNOWN allowed; do not invent why.
- AI has no Investment Authority.
- Human owns final research, judgment and capital decisions.
- GitHub is canonical state/evidence/process backend.
- Reuse First；局部缺口先 thin adapter，不新造 Agent/DAG/provider/scheduler framework。
- Brief 是 Attention Surface，不是 Audit Report。
- 缺口/失败不能冒充 quiet。

交接写入时的快照：

- `main` 在完整交接文档创建前为 `3a161eb2f7c3ee5c6ecf11413fa5ef161ec6a36d`
- `read-model/current-state = d98a88d7012ef650733dda3daa1e62f31468c809`

新对话必须重新读可变 ref，不能把以上 SHA 当永久最新值。
