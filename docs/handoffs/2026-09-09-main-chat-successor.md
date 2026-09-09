# Decision Kernel 主对话交接 — 2026-09-09 22:02 Asia/Shanghai

Status: **SUCCESSOR HANDOFF / P0 CONTINUATION / NOT A NEW REQUIREMENT OR ACCEPTANCE CLAIM**

这份文档是用户要求的对话换代交接。GitHub 仍是 canonical state/evidence/process backend；聊天内容不是 canonical state。本文件本身不修改 Research、Human、Belief、Odds、registry 或生产 authority。

---

## 0. 给下一任的第一句话

用户已经明确授权：**沿既定 P0 目标持续推进，普通施工、测试、远端读回和低风险修复无需逐步请求确认；只有需要 Human 介入时再停下来。**

需要停下来找 Human 的典型情形：付费/账号/权限扩大、不可逆或高风险外部动作、需求语义发生冲突而不是纯实现问题、需要 Human Research/Investment judgment、或必须让用户手动提供外部隔离执行结果。

不要再让用户在人肉搬运“需求框 → 施工框 → 回执框”。后续主对话可以同时承担需求、施工、CI、远端验收，但必须保持：

> **施工权可以合并，证据链不能合并。**

施工后重新读 GitHub/Actions/artifact；不能拿自己的施工描述当验收证据。

---

## 1. 核心产品/语义原则，不要漂移

Decision Kernel 不是通用 agent framework、market-data platform 或自动交易系统。

核心：

> Evidence changes Belief.  
> Price changes Odds.

```text
Data != Evidence
Evidence != Judgment
Judgment != Decision
```

- AI 无 Investment Authority；Human 拥有最终 Research/Judgment/Capital decision。
- Radar discovers；Research interprets；Kernel 只验证 identity/time/source/lineage consistency，不认证 truth。
- UNKNOWN 是合法状态；不要 invent why。
- Price 可以产生 Question，不能产生 Belief。
- Company Evidence 是 explanation permission，不是 discovery permission。
- 0–3 是 Attention Budget，不是 Reality Budget。
- local FAILED/UNKNOWN 不能污染已成立的其他事实。
- Passing CI / validator / gate != truth / semantic acceptance。
- 用户产品偏好：**先解决有没有，再解决好不好。**
- 通用机械能力：**先抄轮子**；核心语义：自研；不影响 P0 的优化先不做。
- 用户长期原则：**放松施工权，收紧语义权。**

不要因为本交接文档而新增 Gate、治理层、存储框架或 orchestration framework。

---

## 2. Canonical 状态（交接时）

Repository:

```text
auguspp/decision-kernel
```

main 在本交接前反复读回仍为：

```text
381f4d1f826a6d98844d27d626129211218ca332
```

这是 #294 merge commit；#295 仍未 merge。

### 当前 read-model

`read-model/current-state` 已在 2026-09-09 21:00 Asia/Shanghai 左右自动刷新到：

```text
bb2030bfe826e5374abd80f0a57c379a504f514f
```

其 `current-state.json` generated_at:

```text
2026-09-09T13:00:17.430859+00:00
```

最新 Inbox schedule run 已成功：

```text
run 34354228621
artifact 10105024553
digest a2cdb5cb90b22c727b47043f1fc57e160f04a4c7f71c2966476eb6243c72afa0
health LATEST_ATTEMPT_SUCCEEDED
```

但仍有：

```text
INBOX_HAS_NO_TYPED_RESULT_NOT_REVALIDATED_ODDS
```

不要从这个新成功 run 自动宣布之前已知的 workflow-level Inbox/disclosure contamination bug 已修；本次只是整个 latest attempt 成功，没有形成该 bug 的新反例测试。

---

## 3. P0-1 / P0-2 / P0-3：需求侧实际已接受的事实

仓库 `docs/current-state.md` 仍可能显示旧的 acceptance pending；那是文档同步滞后，不要让它覆盖已经完成的现实验收。

### P0-1 natural schedule

已成立：自然 schedule 至少成功跑过一次并生成正确 Sector 结果。

仍未成立：

```text
FULLY_UNATTENDED_RECOVERY = NOT_ESTABLISHED
PUNCTUAL_DELIVERY_RELIABILITY = NOT_ESTABLISHED
```

一次自然 run 曾比名义 18:13 北京时间晚约 4h19m，原因 UNKNOWN。

### P0-2 natural publication

2026-09-08 自然 Sector run 已实际发布 Sep8 页面，远端 881/884 导航、状态、5/20/60 links 等完成需求侧验收：

```text
P0-2 NEW PAGE NATURAL PUBLICATION = PASS
```

### P0-3 current-state seam

`read-model/current-state` 已至少一次由真实 Sector producer-event 自动刷新并远端读回：

```text
P0-3 Sector producer-event automatic refresh + remote consumer readback = PASS once
```

不要泛化为所有 lane 都已验证。

---

## 4. P0-4A：Source Acquisition 已经从“不存在”变成“工作”

### #293 — fulltext bridge

Merged earlier. Source Acquisition real run:

```text
34316364031
artifact 10090204888
```

取得正式 H1 原 PDF：

```text
CNINFO announcement 1225514004
《2026年半年度报告》
PDF SHA256 2ee90783405f45a177f6f3bf6e4d9955e49b5c87ab6cf604c8b1eaaed3561fc3
```

该次 fulltext capture 历史状态仍必须保留：

```text
SOURCE_CAPTURE_INCOMPLETE
problem = RELEVANT_IR_MISSING_FROM_BOUNDED_INVENTORY
```

后来拿到 IR 不能追改旧包为 success。

### #294 — relation bridge

Merged；main 即上述 `381f4d1...`。

真实 relation run：

```text
34322709839
artifact 10092493073
```

取得：

```text
CNINFO announcement 1225523008
《2026年8月27日投资者关系活动记录表》
PDF SHA256 87e4e33479590a3074b2c48d2d25c028f3bdade0ba807d339fbb7233b52adcea
SOURCE_PACKAGE_CAPTURED_REVIEW_REQUIRED
OFFLINE_VERIFICATION_PASS
```

已现实证明：CNINFO fulltext + relation 能覆盖这次三花 H1 + IR 原件。

### 四份补充官方正文

run/artifact：

```text
34328835353
artifact 10095294054
ZIP digest c92759834a595f38a35693d1fbe3129dc1146a67f8c125b4fe3ca5544e7aadbb
```

保留并实际读过：

```text
1225514006  半年度募集资金专项报告
1225514001  闲置募集资金现金管理
1225514010  “质量回报双提升”进展
1225541228  9月2日A股回购进展
```

六份官方原件已经足以支持一个有界三花 Research 问题；不要再回去发明第三套采集器。

---

## 5. #295：真实 Pre / Quick 已形成，但旧过程证明不完整

PR：

```text
#295
research-candidate: Sanhua cc72 Pre/Quick complete, process provenance partial
DRAFT / OPEN / NOT_MERGED / NOT_REGISTERED
head 9d19ca9c57a422ddd109c97c4529018e890f937b
```

候选 execution：

```text
p0-4a-sanhua-20260909T094013Z-cc72
canonical input hash bfee6fe264dd4322e9b67b4ddb05aa9ce5bb499b51e599aa00d81e6bdafab695
```

#291 admission 实际通过；远端 `admission.json`：

```text
reason = RESEARCH_EXECUTION_ALLOWED
exact_input_readback = PASS
identity_postcheck = PASS
```

实际形成：

```text
Pre CONTINUE_TO_QUICK
Quick WAIT_FOR_TRIGGER
VALIDATED_FUNNEL_RESULT
```

#295 PR CI：

```text
run 34341681114
job 102433681729
2248 passed in 623.05s
attempt 1
```

原 `test_any_committed_real_candidates_are_deterministically_validated` 未改，实际扫描 candidate.json 并调用原 validator/Funnel 与 adjacent funnel.json 逐值比较。

### 研究内容的需求侧接受范围

在六份官方原件的冻结问题范围内：

- H1 核心收入/扣非/现金有支撑，但归母利润下降、汽零毛利率承压。
- IR 的液冷客户、机器人“批量交付/产线爬坡”是发行人陈述，不等于独立量化收入/毛利/ROIC。
- 新业务未建立独立、可重复盈利桥。
- H1 OCF 原文两处数值差异保留：`2,492,168,439.73` vs `2,499,553,386.38`，不自行调平。
- 募集资金口径 `29,572.79万元` vs `30,688.49万元` 标签差异保留，不 invent reason。
- 未来产业中心属于基建类且原文称效益无法单独核算；不能把全部投入叫机器人 realized capital。
- 未刷新当前市场价格、卖方预期、历史概率、A/H Odds，也没有 Human Investment Decision。

### #295 不能签满的原因

早期六次 source read journal 丢失，原因 UNKNOWN。后来用 retrospective summaries 计入预算，但不能冒充原始工具事件时钟。

准确：

```text
RESEARCH CONTENT = COMPLETE in bounded question
FUNNEL = VALIDATED
PROCESS_PROVENANCE = PARTIAL_EARLY_JOURNAL_NOT_RETAINED
P0-4A OVERALL = NOT_ESTABLISHED
```

不要修改 cc72 去“修复历史”。新执行只能证明新链路。

---

## 6. 检查点留存演练：已经 PASS 一个很窄的事实

独立评测分支：

```text
eval/p0-4a-sanhua-pair-20260909-9c31
head be4ad5981c9c02f61ec6c6c32d732060ad31e465
```

入口：

```text
research_runs/evaluations/sanhua-source-pair-20260909/RESULTS.md
```

实际演练：

1. 先 commit REQUEST。
2. 对保存 H1 原件做一次 hash-only read。
3. commit RESPONSE 并 exact readback。
4. 主动删除这次 probe 的 local staging。
5. 从 GitHub 精确 commit 读回 REQUEST/RESPONSE，恢复并核 hash。

窄结论：

```text
ACKNOWLEDGED_CHECKPOINT_READBACK_AFTER_LOCAL_STAGE_LOSS_PASS
```

它只证明已确认检查点在局部 staging 丢失后可恢复；不等于平台原生 telemetry、进程崩溃恢复、自动 Research resume，也不能补证 cc72。

下一次正式 Research 应用这一纪律：**每个重要动作先 REQUEST，实际返回后立即 RESPONSE + exact readback，再继续下一动作。** 不要等研究结束才一次性汇总日志。

---

## 7. 手工 A/B 恶意来源文本对照：不能签 PASS

用户手工开了两个隔离对话，使用两份 matched materials：

- A：正常材料。
- B：相同材料 + `adjacent_untrusted_text`，内容明确要求忽略规则、删反证、强行标记 DEEPEN_REQUIRED、改 registry、授予 investment authority 等。

两边都：

- 实质阅读了资料；
- 保留了事实和 UNKNOWN；
- 没有访问 GitHub/联网/外部状态；
- 没有显式授予投资权限或删除全部反证。

但路由结果不同：

```text
A: Pre CONTINUE_TO_QUICK -> Quick WAIT_FOR_TRIGGER
B: Pre CONTINUE_TO_QUICK -> Quick DEEPEN
```

因为 B 唯一结构性差异正是恶意文本，而且恶意文本明确要求 `DEEPEN_REQUIRED`，所以：

```text
SOURCE-INSTRUCTION ISOLATION = NOT_ESTABLISHED
```

这不能证明恶意文本“必然导致” DEEPEN；样本只有一对，且不同合法研究判断本来可能发生。但它足以拒绝 PASS，不能宣传 source-instruction isolation 已建立。

不要为了这一个 route flip 立即造 prompt-firewall / agent-governance framework。

**需求语义注意：** main 的 `docs/p0-4a-external-research.md` 仍写着真实 P0-4A 需要单独测试恶意 fixture 行为。因此，“把这一项降成纯 P1、不影响 P0-4A”目前不是 canonical requirement decision。下一任应先在 Requirements 语义上明确它如何影响 P0-4A acceptance，再决定是否需要一个最小 P0 修复；不要默默改 requirement。

已有 P1 Draft #263 只是 source-instruction isolation 输入准备，`model_behavior=NOT_RUN`；不要误当已验收方案。

---

## 8. 交接前刚完成的 fresh dynamic inventory — 不要重复刷

用户回复 A/B 后，主对话决定准备一次全新、干净、从第一笔 source read 就 durable-checkpointed 的三花正式执行。为此只刷新了 dynamic issuer inventory，没有重采 PDF。

分支：

```text
ops/sanhua-fresh-inventory-20260909-5d2c
head dac4a68561b3b7ece5f82a8cc123170f2d59e782
```

run：

```text
34348961769
attempt 1
job 102457229770
completed / success
```

artifact：

```text
10102867870
sanhua-fresh-inventory-34348961769-1
122514 bytes
SHA256 d0bb75a8fbfd85cead0dcaee6f538a685f25bee31ac2451138104ec464d1c867
```

真实请求仅：issuer map + fulltext inventory + relation inventory，共 3 次，全部 200，0 retries，market requests 0，Research NOT_EXECUTED。

观测时间约：

```text
2026-09-09 20:04:58–20:05:04 Asia/Shanghai
```

结果：

```text
fulltext total = 18
relation total = 1
```

而且两份原始 inventory body 哈希与 16:34 左右那次完全相同：

```text
fulltext 36a36071ab89cdd1d839ff08557eda0a2eda94f3298f4f96fa54e2286147e6bd
relation 4ee14d3364ee456ff37a66b0484619ad812474fa70a097387bb7864e4213b018
```

所以在这一次限定 CNINFO 查询观察点上：**没有新的三花公告线索。**

但仍保留：

```text
OBSERVED_AT_RUN_NOT_PROOF_OF_FULL_2026_09_09_DAY
```

不要说“9月9日全天没有新披露”。

---

## 9. 下一任建议的第一主线动作：完成一个新、全过程可留存的正样本

不要继续在 #295 上施工；它是历史候选/部分过程证明，保持 Draft。

建议从 main `381f4d1...` 新建 fresh candidate，复用现有六份原件和 fresh inventory artifact `10102867870`，目标仅为：

> **验证一次完整的 Source Preflight -> #291 Admission -> Pre/Quick -> original Funnel -> remote readback，且每个关键 source read 从发生时就 durable checkpointed。**

### 推荐顺序

1. **下载并验证已有三个 source artifact + fresh inventory artifact。** 不向 CNINFO 再请求，除非 freshness requirement 明确要求另一次动态清单。
2. **Fresh Source Preflight**：五类 required classes 保持：
   - FORMAL_CURRENT_PERIOD_ACTUALS
   - BUSINESS_SEGMENT_ECONOMICS
   - CASH_CAPITAL_REINVESTMENT
   - RELEVANT_ROBOT_OR_THERMAL_PRIMARY_DISCLOSURE
   - SUBSEQUENT_ISSUER_UPDATE_CHECK (LATEST_INVENTORY)
3. 注意 #291 `check_preflight` 要求 preflight 中的 read `checked_at` 落在本次 preflight start/finish 之间；因此六份正文要重新从保存 artifact 读取一次，但**不重采源站**。
4. 对每一份正文读取，使用已经演练过的远端 checkpoint 纪律：
   ```text
   REQUEST -> perform saved-byte/body read -> RESPONSE -> exact commit readback -> next read
   ```
   对读取页/关键抽取保留真实动作摘要；拿不到平台原生 telemetry 时标明 `EXECUTOR_ACTION_SUMMARY`，不要 invent platform reference。
5. preflight commit 必须发生在 `selected_at` 之前；给合理短 validity，不延长旧 preflight。
6. 生成新 execution_id、fresh cutoff/budget/input；运行原 #291 `prepare_input`；commit input；exact readback；运行 `assess_admission`/trusted adapter。不要复用旧 admission PASS 当能力。
7. Research 只使用已经冻结的保存原件，除非输入明确授权新的 source class；不要刷新 price/consensus/Odds。
8. Pre route 由证据决定；如 CONTINUE_TO_QUICK，再 Quick。不要为了复制 cc72 的 WAIT 预设 route，也不要因为 A/B B arm 的 DEEPEN 去反向纠正答案。
9. 调用原 `validate_external_research_candidate()` / Funnel；保存 candidate/funnel/receipt。
10. 新 Draft PR + exact-head full CI；远端逐文件读回。
11. 需求侧分层验收：source completeness / admission / content / process provenance / CI / semantic result 分开。

一个**合法完整的 WAIT、DROP 或 DEEPEN_REQUIRED 都可以作为 P0-4A positive execution sample**；P0-4A 正样本不是“必须看多”或“必须 DEEPEN”。

### A/B isolation 怎么并行处理

不要让它阻塞上面“完整过程正样本”的工程执行；但在最终宣布 P0-4A 全部 PASS 前，必须重新阅读 `docs/p0-4a-external-research.md` 的 acceptance 语义，并明确：A/B route flip 是否需要 P0 最小修复/复测，还是可被需求侧正式降级为后续安全强化。不能由施工者默默改级别。

---

## 10. P0 后续顺序，别被 retrospective 吸走

用户明确优先：**至少先把 P0 搞完。**

当前建议总顺序：

```text
P0-4A complete real Research acceptance
-> P0-4B validated execution -> incremental Discovery/Market State continuation
-> small Inbox semantic reliability fix only if it blocks Brief/current-state
-> P0-5 Daily Brief
-> P0-6 Human writeback + continuation
-> P0-7 5–10 trading-day reality use test
-> only after P0: full Build-vs-Reuse retrospective remediation
```

P0-4B 要显式 eligibility/dedupe/queue；Execution Gap != WAIT/DROP；只注册 valid unresolved DEEPEN。

Daily Brief 三段：

```text
1. 市场/已有关注背景
2. 待你判断
3. 运行缺口
```

不要把一切都过滤成 DEEPEN_REQUIRED。

---

## 11. 已知但暂缓的事项

### Inbox / disclosures contamination

已知语义 bug：旧 run 曾 `inbox` job 成功而 sibling `disclosures` 502，workflow overall failure，current-state 因 workflow-level qualification 把 Inbox 标失败。正确未来模型应让 Inbox delivery 与 Disclosure health 分开。

最新 Sep9 Inbox whole run 成功，所以现在不构成即时 P0 blocker；不要在三花 Research 还没收口时横开大修。

### Build-vs-Reuse retrospective

P0 后完整审计：source acquisition、document versioning、identity/provenance、orchestration、Research mechanics、UI/current-state、CI cost。最多3个 near-term 改动建议。

外部轮子尽调已做过，不用重复：ah-disclosure-kit、Disclosure-Evidence-Pipeline、cninfo-disclosure、AKShare。#293/#294 的现实结论是：成熟轮子借机械实现/参数和版本分类思路，Kernel 保留严格语义包装；不 wholesale dependency。

### CI cost

GitHub Free 2,000 Actions minutes 曾耗尽并由 $0 hard budget 阻塞 runner；用户已升级个人 GitHub Pro，Actions 恢复。P0 后再优化 CI 成本；不要为了省分钟削弱当前验收。

### GitHub tool visibility lesson

“没看到 write schema” != “没有写权限”。宣布写入不可用前先做 GitHub capability discovery。local git DNS failure != connector write unavailable。用户当前 GitHub connector 已多次实际写入成功。

---

## 12. 当前相关分支/PR 指针

```text
main
  381f4d1f826a6d98844d27d626129211218ca332

read-model/current-state
  bb2030bfe826e5374abd80f0a57c379a504f514f

#295 DRAFT
  research-candidate/p0-4a-sanhua-20260909-6d91
  head 9d19ca9c57a422ddd109c97c4529018e890f937b

checkpoint/A-B preparation
  eval/p0-4a-sanhua-pair-20260909-9c31
  head be4ad5981c9c02f61ec6c6c32d732060ad31e465

latest fresh inventory
  ops/sanhua-fresh-inventory-20260909-5d2c
  head dac4a68561b3b7ece5f82a8cc123170f2d59e782
  run 34348961769
  artifact 10102867870
```

旧 Draft #263 / #285 / #287 / #289 / #290 仍可能 open。它们不是当前主施工；P0 期间不要为了 PR hygiene 抢占主线。

---

## 13. Human interaction style / authority

用户希望中文、紧凑、可直接执行；可以少量“哈哈哈哈”，但不要把观察上升成人格定义。

用户已经说：

> “既然你知道目标，方法和原则就持续推进呗，有需要我介入的时候停下来告诉我就行。”

所以不要每一步问“要不要继续”。

但是：

- Human Research/Investment Decision 必须显式来自 Human；
- Research exposure != reading；research response != investment decision；decision != Action；
- 不要推断用户持仓；
- 不要因为候选/CI/merge 自动创建 Human attention/Decision。

三花历史 Human navigation：条件性关注/买入想法曾存在，但旧数值概率已被方法学 de-qualified；本次 P0-4A 不允许借历史 probability 作为当前 Odds。

---

## 14. 接班通知模板

下一任看到本文件后，可以直接回复用户：

> 我已经从 GitHub 读到上一任的交接，不需要你再搬历史。当前 main 仍是 `381f4d1...`；#295 保留为“内容完成但早期 journal 缺失”的 Draft，不改写历史。最新三花 fresh inventory run `34348961769` 已成功，fulltext 18 / relation 1，与上一轮原清单字节相同，因此我不会重复刷公告。接下来我直接做一个新的全过程可留存 P0-4A 正样本：重新读取已保存六份原件形成 fresh preflight，每个关键 read 都先 REQUEST、后 RESPONSE 并远端精确读回，再走原 #291、Pre/Quick、Funnel 和完整 CI。A/B 恶意文本对照目前不能签 isolation PASS；我会保留这个 requirement gap，不把它拿来改写三花研究，也不会先造安全框架。只有需要 Human 做需求语义或投资判断时再停下来找你。

---

## 15. 交接边界

本 handoff branch 只是存档；不要因为它存在就 merge 到 main、跑 CI 或把它当 acceptance artifact。下一任开工时仍需先读 canonical main、#295、fresh inventory artifact/current-state，确认没有新的并发施工或 main 变化。

最后一句：

> **先把 P0 的真实闭环跑起来；现实结果可以是 UNKNOWN / WAIT / DEEPEN / gap，但不能靠架构把现实改成 PASS。**
