# 接手通知 — 股票输出优先；两份未合并实现必须先核对

日期：2026-09-06。此文为本轮收口通知，不是运行或投资授权的扩张。

## 1. 先核验，不从上一轮聊天直接继续

连接 `auguspp/decision-kernel`，先读 `docs/project-state.md` 和本文件。重新查询 main、开放 PR/Issue、工作流目录、最新主干 CI，并重点检查 **PR #259** 的实际 head、diff、CI 和是否仍为 draft。工具权限可能随对话不同，必须实际发现并调用；不要直接继承“上一轮只读/可写”的说法。

收口前已核实：

```text
last merged code main = cfd2b4510a16a953f2bddcbb763e0a27f5fedf79
last code PR = #258
main CI = 34022916206 / success / 1511 passed in 101.62s
open implementation PR = #259 / draft / not merged
PR #259 head = 966ff79e39ba310705922b2cd3fd186df62efb69
PR #259 CI = 34027180578 / failure
PR #259 test job = 101470124388
result = 2 failed, 1569 passed in 231.34s
open non-PR Issue = 0
```

本轮状态同步会产生后续的文档提交；准确同步 PR、merge SHA 和主干 CI 以对应 PR/Actions 及最终收口回执为准，不把上面代码基线冒充未来 main。此次只同步文档，**不修复或合并 #259、不套用本地补丁、不启动采集**。

旧 `project-state.md` 已按原 Git blob `67a655859afdd64588cd043c73d908cb5cec4097` 原样归档到 `docs/handoffs/archive/2026-09-06-project-state-before-stock-output-sync.md`。旧全文是历史记录，不是当前进度。冻结 Research/Decision/Action、来源证明和旧 stock-primary-sources handoff 均保留不改。

## 2. 用户真正要的产品

用户明确要求：不要总是继续搭基建；打开雷达应直接看见 **0–3 只值得进一步查看的股票**，而不是看完320个行业后自己找公司。已经同意实现股票输出层。

第一屏应清楚显示：股票名/代码、来源方向、个股自己的表现、为什么值得看、公司业务依据、关键风险/缺口和下一核验问题。完整不通过/未展示清单在展开层。值得看不等于值得买，不能用 BUY/SELL 或新 canonical wake 偷换需求。

所谓“核心基建基本到位”只表示有界验收的部件足够，不表示股票输出已发布、长期无人值守已上线或发现效果已得到验证。当前 P0 是**收敛并验收股票输出实现**，不是再做一套回执、队列、存储或前端平台。

## 3. 两份未合并工作：不可当成同一份

### A. 远端草稿 PR #259 — 接手先看它

```text
branch = feat/stock-first-radar-reading
head = 966ff79e39ba310705922b2cd3fd186df62efb69
base = cfd2b4510a16a953f2bddcbb763e0a27f5fedf79
scope = 6 files, +1125 / -3 at the checked head
```

文件：

```text
.github/scripts/capture-stock-reading.py
.github/workflows/hithink-stock-dump-trial.yml
src/decision_kernel/runtime/stock_radar_reading.py
tests/test_stock_radar_capture.py
tests/test_stock_radar_reading.py
tests/test_theme_capture_trial.py
```

这份草稿包含纯股票阅读模块、复用现有适配器的有界采集/重建脚本，以及既有工作流中的手动 `stock-reading` 入口。它按活跃经济节点里的已审阅公司做范围受限的筛选，不是盲扫全A。现有公司依据主要为牧原/圆通，不能把有限证据覆盖包装成全市场最优股票。其声明采用节点轮询与明确的原始超额收益字典序；须检查实际代码，不把它与本地包的成交额排序视为同一规则。

**这份 PR 已存在但仍失败。** 最新核验日志中的失败为：

```text
tests/test_hithink_dump_trial_workflow.py::
  test_secret_is_only_in_acquisition_step_and_optional_libraries_are_installed
  -> 原测试按 theme-probe 前的整个文本段计数，实际计数 2，断言 1

tests/test_theme_source_capture.py::
  test_workflow_keeps_fixed_name_and_dump_manual_and_current_source_push_bounded
  -> 仍要求四项旧 options 精确字符串
```

这是日志中实际观察到的两项断言失配，不是本轮发现了真实凭据泄漏。下一轮先核对新增 job 的 secrets、只读权限、触发范围与离线步骤，再修正不适用的结构性测试；保留原有安全断言，不能删测试换绿色。此次没有检查所有新增语义漏洞，也没有证明修两项断言就足够上线。

此前聊天的“没有远端股票 PR”不能覆盖这次查到的 #259。不要为保持聊天一致而关闭、重置或覆盖它。

### B. 本地交付包 — 用于比较，不可盲目套用

```text
filename = stock-attention-projection-v0-local.zip
bytes = 536888
sha256 = 91aeb6f3ec637262cbb49b6b95d4611e3d5221fc4d71c8eb586a12af3937f21f
base_commit = cfd2b4510a16a953f2bddcbb763e0a27f5fedf79
stock-attention.patch sha256 = 214df5d87c578a4af194d1b1f63f6f1382134ace148b913ee3533702dafd071a
```

包内五个新增文件：

```text
src/decision_kernel/runtime/stock_attention_projection.py
src/decision_kernel/runtime/stock_attention_bridge.py
tests/test_stock_attention_projection.py
tests/test_stock_attention_bridge.py
docs/stock-attention-projection-v0.md
```

还有 `validation.json`、实际测试输出、普通 patch、相同内容的 `overlay/`、ready/incomplete 合成页面和浏览器记录。其原验证记录是 **78 passed**：66项核心/CLI/重建测试，12项模拟原 serializer/source-builder/provider-identity 边界的转换测试；**不是完整仓库集成**。原主干1511项不能算此包已通过，#259的测试也不能借给它。

收口时重新计算 ZIP、patch 与全部五个 overlay 文件的哈希，均匹配；校验记录与单独交付的 `stock-attention-validation.json` 相同。此次没有重跑那78项。原浏览器验证是 Chromium 用实际生成 HTML 的内存加载，1440/390像素；不是实际 file URL、手机、Safari或网站验收。

本地版先冻结全部所供成员与有业务依据的明细计划，再检查个股路径，使用原上游组顺序/当日成交额压缩为最多3只。它要求61个交易日、精确参考价连续性，计划缺件不凑前三；32是明细股票数量上限，不是全链路请求预算。原README里的直接 `git apply` 步骤现在已不是自动可用指令：**已有 #259，必须先比较合并策略**。

该 ZIP 未作为股票生产代码进入仓库。新对话不能假设本对话 sandbox 自动继承；需要从用户随接手通知提供的交接包中取得。缺附件时先读远端 #259，不臆造或从聊天重新抄一份实现。

## 4. 不能跨过的产品/数据边界

**两个草稿需要收敛为一个实现，不要同时引入两套 selector。** 对照方向来源（新进入 vs 仍强势阅读）、个股确认条件、业务覆盖、输出排序、时间与公司行为口径、真实采集和失败行为；复用已有模块并迁移有价值的反例测试。

个股5/20/60日必须来自个股自己的合格数据，至少61个明确完成交易日。旧10日 dump、行业收益、snapshot 的 data-ready 时钟都不能代替。原股票 dump 仍 `DIFFERENCES_REQUIRE_REVIEW / NOT_ESTABLISHED`；停牌、上市、分红和前收参考口径问题分别保留，不自写复权引擎、不添加经验容差、不用昨日价格补缺口。

公司材料、当前成员身份与受益归因分开。无所供业务证据是覆盖缺口，不等于公司无价值；如果首版只能核对牧原/圆通，就明确写“两家已审阅公司范围”，不能称“全A筛选”。不能为凑名单把海大/隆平的媒体报道自动接受成公司依据。

当前成员不能倒灌历史；881和884不能混排；主题目录标签不是永久 taxonomy 或纯业务暴露。所有计划内资料先完成核验再压缩首屏，超预算或缺件要保留完整原因。分红前后的原始价格变化不是含分红总回报，涨幅也不是判断质量。

股票优先的 shadow 页面可以有股票，不因此自动获得第三条 canonical Human wake。正式 Research 与 Decision 仍走既有两条路线；不自动插入 Inbox，不生成 Recommendation/Action。

## 5. 已合并能力和真实运行证明

到 #258：Sector独立881/884计算、127日状态、单日producer、事件账本、当前宽度、候选时parent复核、audit/replay和发布检查均已实现。经济发布接受/组装、产业—行业—公司联合阅读、T+5/T+20客观评估、主题探针/来源扫描、RSS去重/分批/精确执行/历史恢复及手动接线也已合并。

它们不等于真实闭环全部通过：

```text
last independently verified successful Sector run = 33939414197
implementation = 5f8f635d191dd8559844d1b74af0dca0cf4c02df
market session = 2026-09-04
prospective candidate ledger = empty
new completed-session append = not yet proven live
new sealed-audit replay / combined-page remote delivery = not yet proven live
Sector schedule = absent
real matured T+5 / T+20 corpus = absent
```

bootstrap 身份唯一事实源是 `radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json`，不在此重复拷贝哈希。下一预计直接接续日9月7日必须由真实日历/收盘快照确认；错过中间完成交易日必须先建立 qualified recovery，不允许跨缺口或伪造运行时钟。用新的 dispatch 验收同日幂等，不用 Re-run jobs。

RSS原生基线 `34010252507` 保存1000条，续跑 `34012474393` 保留相同版本且没有新增。原始发布时间缺时区仍未资格确认。#258接入的是消费者历史，不是重新建RSS基线；`isolated`仍默认，initialize/continue明确选取，execute默认false。真实云端消费者历史上传/恢复和自然新增来源验收仍未建立。历史总量32MiB、有限对象数量、附件90天，不代表永久保存；丢失或过期不得静默重置。

读取相关说明：

```text
docs/sector-radar-prospective-producer-operations.md
docs/sector-radar-publication-check.md
docs/sector-radar-joint-reading-delivery.md
docs/sector-radar-objective-outcomes.md
docs/economic-company-context-v0.md
docs/native-feed-history-workflow-v1.md
docs/handoffs/2026-09-05-stock-primary-sources-next.md
```

聊天附件 `radar-readonly-results-2026-09-06.zip`（SHA256 `0d00ebb8e0584038d834d07bace20d4b08fbb10740302c0dd04bb5f1cf2fa133`）是保存9月4日市场的只读重算，不是本轮live producer或真实个股名单。牧原、海大、隆平是人工展开的阅读对象，不可倒填成系统当时发现的候选。合成ready页面也不是真实数据。

## 6. 下一轮实施顺序和验收

1. 先核对 #259 是否有新提交或并行修改；阅读当前失败日志、实际代码和本地补丁说明，选择单一实现路径，不覆盖别人的未完成工作。
2. 在明确范围内修正/补齐集成验收：真实 producer/company builder 边界、个股历史资格、所有计划内输入/失败、distinct ticker压缩、机密和时钟保护。试行筛选条件先冻结记录，不用本次样本立即调参。
3. 完整 PR CI 通过并审阅精确 diff 后才合并。纯绿色CI不能替代真实数据资格，也不允许为了绿而删关键断言。
4. 用明确授权的一次有界真实运行验证合格个股输入与实际附件；保留原文/响应、输入截止、计划、完整拒绝原因。先看0–3只真实合格股票或明确不足，不反复下载旧数据冒充前瞻进展。
5. 真实收盘后新日追加、同日幂等、云端历史接续各自验收；完成后才讨论 schedule 和正式通知渠道，不能因为页面生成就宣布自动推送上线。

每个PR/运行报告：编号、精确diff、head/merge SHA、完整CI、实际请求/输入日期、是否改workflow、是否真的上传/恢复、是否改Human/Research/Investment authority。区分未触发、条件不满足、数据不足、请求失败和显示截断，不统一叫“没机会”。

## 7. 权限和公司状态保持不变

```text
External Research Method can propose. Kernel commits. Human decides.
SHADOW OBSERVATION ONLY
HUMAN ATTENTION AUTHORITY = NONE
RESEARCH AUTHORITY = NONE
INVESTMENT AUTHORITY = NONE
```

False→true只由previous/current市场状态计算，事件/执行账本不是第二套触发依据。客观outcome与Human注释分开；未来反思不能改写原判断或自动进入方法记忆。

CATL继续跟踪、便宜/概率未建立、Odds withheld、无决定无动作；GigaDevice条件买入框架未执行；Sanhua约30元条件框架未执行；Tinavi WATCH/NO_ACTION；Micron WAIT/DO NOT BUY，9月30日为此前记录的待观察节点，不是本轮重新核验的日程。未解决DEEPEN_REQUIRED为0（既有记录）。Position/Holding仍按既有文件deferred。牧原/圆通证据页、海大/隆平聊天阅读，不产生新投资决定。

本轮到此结束。后续从当前仓库、#259和交接附件开始，不再以“基建已经完成”掩盖股票输出未合并、个股数据未资格确认和真实验收未完成。
