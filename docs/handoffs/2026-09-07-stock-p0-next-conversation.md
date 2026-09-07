# 接手通知 — 股票实现已合并，真实 P0 未完成；在一个对话内闭环

日期：2026-09-07。状态快照：本轮最后真实尝试发生于北京时间 09:37–09:38。本文用于结束旧对话并接手，不是新的运行证明、定时任务或 authority 扩张。

## 1. 接手第一屏

先读 `docs/project-state.md` 与本文件，再独立查询当前 main、开放 PR/Issue、最新主干完整 CI、工作流及最新真实运行。不要重新从旧 #259 草稿或本地 ZIP 开始实施。上一份 `2026-09-06-stock-output-next-conversation.md` 保留为历史，当前指令以本文及实际仓库为准。

本次文档同步前：

```text
repository = auguspp/decision-kernel
last implementation main = 3529f4651e884abfd1dc48cc881d0dc360e5335f
last implementation PR = #265 / MERGED
main CI = 34073063774 / completed / success
test job = 101593895184 / 1708 passed in 406.80s
only open implementation PR = #263 / DRAFT / NOT MERGED
#263 head = fa4d9e48189ec421b7e17405a57070ae12db4ee0
#263 branch = test/disclosure-source-instruction-isolation
open non-PR Issues = 0
real qualified stock output = NOT_ESTABLISHED
```

这次 docs-only closeout 会产生更晚的 commit/PR/main CI。不要把上面实现基线误称为永远的最新 main；找到修改本文件的同步 PR，并读取其中最终核验回执。CI 测试数量归属于各自精确版本，不相加。

## 2. 用户的目的与工作方式

项目服务于投资注意力分配、可追溯判断和现实检验，不是追求更多框架或测试数。当前 P0 是打开 Radar 能得到范围明确、最多 0–3 只值得进一步查看的股票：方向来源、个股自身表现、业务依据、风险和下一问题。值得看不等于值得买；每天不必有股票，但必须完成声称完成的检查。

用户已认可的语义约束：

- Evidence/Price 是相应判断的合格输入，不是自动修订 Belief/Odds 的触发器；价格观察不偷换成企业基本面证据。
- stock-first 不等于 stock-only。Sector/Economic/Theme/Disclosure 等可以停留在观察或问题，不强造 ticker，也不自动进入正式 Research。
- 覆盖范围事前声明并保留。范围外、计划内数据不足、条件不满足、合格但未展示不能混淆；不能事后缩小范围美化结果。
- Outcome 可以审计 Method，但不能自动改 Method。正式方法/判断接受仍由 Human 决定，不以后见之明重写旧记录。

下一项施工使用 GOAL / HARD INVARIANTS / ALLOWED SIDE EFFECTS / FORBIDDEN AUTHORITY CHANGES / ACCEPTANCE EVIDENCE / STOP CONDITIONS / DELIVERABLE 即可；不为此新建平台。实现路径可选择，验收标准与权限不能自行改写。

## 3. 同一新对话必须实际拥有两组工具

用户不希望再在“能改代码”和“能启动任务”的两个对话之间搬通知。新对话请同时启用现有 **GitHub** 和已配置的 **GitHub Actions MCP**，或功能等价的连接。

| 能力 | 接手时实际发现并试读，不能只看“已连接” |
|---|---|
| 代码与评审 | 仓库文件读取、main/branch/commit、PR/Issue 查询；有界 branch/commit/PR 写入及明确授权后的 merge |
| Actions | 查询 run/job/log/artifact；指定 workflow/ref/inputs 创建 fresh workflow_dispatch；下载实际 artifact |

上一旧线程的 Developer MCP 曾返回 `This conversation does not support developer MCPs`；新 Actions 对话已实际创建过运行，因此 OAuth 配置不是本次未完成项。不要重新要求配置 Tushare，也不要以缺少某一工具推断 GitHub 账户权限或 HiThink 密钥失效。若只加载 Actions，不代表没有另一个已连接的 repository 工具；先发现现有连接。真缺能力时，只指出具体缺的操作，不编造提交/运行，不反复让用户搬代码。

`HITHINK_FINANCE_API_KEY` 已配置于 GitHub Secrets，由 runner 注入。当前聊天没有该环境变量不是故障。所有 token、OAuth secret、含凭据 URL 留在安全配置，禁止写入聊天/PR/日志。不要改 push/schedule 或借 Re-run 绕过显式手动意图。没有设置未来提醒或自动任务。

## 4. 已经完成的实现，不要重做

| PR / merge | 内容 |
|---|---|
| #259 / `81ce648e140acdd35cc8249d796aecd842edde5b` | A/B 收敛为一套股票 reader；HiThink 历史/快照/公司行为实际接线；完整 PR 与 main CI 各 1670 项通过。 |
| #262 / `c73f4dcc929a8cd3181bdb48875f584d9fcd5966` | 修缺失/非法 Sector run 输入诊断及未开始采集后的连带重建/上传错误；完整 PR 与 main CI 各 1689 项通过。 |
| #264 / `71807a85ca658af74ed6c2e3c7d0010b7ae53ef5` | 股票入口不再用“周一一律拒绝”代替真实日历资格；完整主干 CI `34067144150`：1703 项通过。 |
| #265 / `3529f4651e884abfd1dc48cc881d0dc360e5335f` | 盘前指数误拒绝修复，review head `2e0eeeef383ba15b0eda393dbda6128fa9f73713`；PR CI `34072673845`：1708 项通过；main CI `34073063774`：1708 项通过。 |

#265 仅改 `src/decision_kernel/runtime/stock_radar_reading.py` 和 `tests/test_stock_premarket_index_snapshot.py`，+210/-4。reader v4；共享 `adapters/hithink_index.py` 未变。stock wrapper 只对共享 adapter 的特定 later-trading-session 拒绝开放窄例外：ready <= 该 snapshot 自身 receipt <= qualification，真实 calendar 确认 latest completed session，且三时钟同日、均严格早于09:15。例外有 `snapshot_valid_until`，后续 `at()` 复检。不要把它描述成全天使用昨日行情的许可。

#265 的5项新增测试是 synthetic/network-prohibited。旧真实附件的独立人工/脚本核对，与仓库 CI 回归不是一件事；没有 post-#265 成功真实 stock run。旧运行仍为失败。不要只凭摘要宣称生产已经核对所有 benchmark OHLC/volume 和321项turnover：旧附件核对做过这些比较，当前 reader/共享 adapter 的实际断言范围须读源码。

正常股票计划仍按活跃方向 + 已接入公司依据 + 当前成员产生。当前依据覆盖牧原/圆通；旧失败计划只有牧原，最多能产生一张而非三张保证卡片。不得人工增补“海大/隆平”等公司来凑名单。

个股必须有自己的61个完成交易日，算5/20/60日未复权收盘价比值；60日仅背景。保留实际 quote/prev close/量额精确匹配、公司行为窗口、日期/身份/凭据/哈希、26-call预算及30分钟寿命。不用旧10日dump/行业收益替代，不填prev_price、不自动复权、不加经验容差。未报告公司行为不是穷尽排除证明，raw return不是total/adjusted return。Tushare checker已从发布树移除；历史记录不是当前运行依赖。

相关实现说明：`docs/stock-reading-hithink-path-2026-09-06.md`。更早 reconciliation/source-check 文档保留演变记录，不能把其中已撤销的执行前提当作现行要求。

## 5. 真实执行链与可重新下载的附件

### 5.1 首次手动缺参

`34043329828`：trial-purpose正确，但stock-market-run-id为空，初始化停止；未取得行情、无股票artifact。#262修复诊断，不把它改成成功。

### 5.2 盘前指数资格失败——不是零匹配

```text
run = 34070171908
head = 71807a85ca658af74ed6c2e3c7d0010b7ae53ef5
workflow = hithink-stock-dump-trial.yml
trial-purpose = stock-reading
stock-market-run-id = 33939414197
artifact = stock-reading-34070171908-1
artifact id = 10000211354
bytes = 963490
sha256 = 0cd89b70719f6e55eaffd2ba116dc20320142bbc6486d22364dea1992a611b06
result = DATA_QUALIFICATION_FAILED / INPUT_CLOCK_IDENTITY_OR_SCHEMA_REJECTED
replay = RETAINED_INCOMPLETE_ATTEMPT_NOT_STOCK_SELECTION
```

Sector绑定/下载已通过；四份响应是calendar、catalog、index snapshot、benchmark history。保存/latest completed为2026-09-04。2026-09-07北京时间：开始08:33:42.770201，snapshot ready08:34:26.000，实际receipt08:34:26.800222，benchmark receipt08:34:48.182318。不是未来数据：ready早于该响应receipt，而不是必须早于整次运行开始。

旧附件中沪深300 last/prev与已完成历史一致，人工核对OHLC/volume/turnover及321项last/prev/turnover也一致。共享adapter把后续交易日期的ready一律拒绝，#265因此修正stock-only盘前路径。没有发出牧原61日历史请求，故其5/20/60表现未知，不能补0、用行业收益填充或作为已选股票。

附件中的牧原 `002714.SZ` 只是 `NOT_COMPLETED_NO_SELECTION_CLAIM`。方向养殖业 `881102.TI` / 生猪养殖 `884275.TI` 是仍强势阅读，不是新事件；公司资料为留存摘录，未重读原始披露。旧来源内容不因本次交接变成最新经营事实。

### 5.3 两次 Sector HTTP 429——股票 workflow 未创建

| run / producer job | 北京时间、失败点 | 失败审计artifact |
|---|---|---|
| `34073613843` / `101595435840` | 2026-09-07 09:37；`/api/a-share-index/catalog/ths-index-list` HTTP429 | `sector-radar-run-34073613843` / `10001289545` / 460149 bytes |
| `34073665086` / `101595581994` | 2026-09-07 09:38；`/api/a-share/calendar/trading-days` HTTP429 | `sector-radar-run-34073665086` / `10001306616` / 458139 bytes |

```text
artifact 10001289545 sha256 = 747ccbc690a561cb6776141d733f6a7d2beafb94f16fa6173ba86dd77e2dac25
artifact 10001306616 sha256 = 8707b88cab0b58d7e4614842557ba5cac9aaa8ea8dbbe6df95d06bd3dfd69ae9
```

均为main `3529f465...`、fresh dispatch/attempt1；恢复旧state后请求失败。两次 `Upload authoritative state bundle` 和cache save均skipped，只上传失败audit。本次收口复读两次日志/元数据，没有声称重新下载并重放两份429audit。其归类是前置Sector请求失败，不是stock结果枚举，不是条件不满足或零匹配。

两次仅相隔约一分钟，**fresh run不等于已经退避**。不要继续同样短间隔重试。429无法单凭状态码断言限流窗口、额度耗尽或密钥失效，也不能排除现有客户端请求节奏问题。优先读取保留失败证据及可核实的provider说明；没有Retry-After证据就不杜撰等待秒数。不能据此自动改供应商、改门槛或加通用重试平台。

上述两次均发生在上午，不是收盘后验收。旧对话“15:10–15:20再观察”只是建议，既没有实际排程，也不保证到点数据或额度可用。

### 5.4 仍可定位的最后成功 Sector 输入

```text
run = 33939414197 / success
code = 5f8f635d191dd8559844d1b74af0dca0cf4c02df
market session = 2026-09-04
artifact = sector-radar-state-bundle
artifact id = 9961284050
bytes = 431180
sha256 = 3c8c3bec756932abed10de450666f5814aec3c82938acf79cbe7c27487f95539
prospective candidate ledger = empty
```

它是有身份的历史输入，不是永久可用默认值；早于新版sealed audit，不可为它制造新审计。canonical bootstrap身份仍只以 `radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json` 和原parser为准，不因恢复失败静默重置。

所有artifact收口查询时未过期；仍按90天保留，不保证永久可取。新对话从GitHub按上述run/artifact重新下载，并自行核对实际bytes/digest；不要依赖旧聊天sandbox链接或假设本地文件自动继承。

## 6. 下一次只做一个有界真实闭环

**先确定当前能合法说到哪里，再决定缺口是否确实需要代码。** 不要因本交接再造一次检查平台，也不要把“代码绿”当成产品交付。

1. 重新核验main与对应完整CI、真实时间和现有运行。已有同目标运行时先检查它，避免重复dispatch。09:15之后至当日完成交易前，当前路径不支持把当日更新但仍代表旧完成日的snapshot当作合格盘前carry；不要改时钟或硬闯。收盘后仍以真实calendar/完整行情为准，不按墙钟预先宣称资格。
2. 使用真实当前资格决定是否需要新Sector输入，不是每次股票读取都机械强制再产一个run。对于本轮计划的下一个完成日，先fresh dispatch `sector-radar-shadow.yml` on main，inputs为空，最多一次；程序核验直接下一交易日。若已经漏过中间完成日，先取得separately qualified recovery，不跨日桥接。普通直接下一日追加不必误称为recovery。
3. Sector完整success、权威state bundle上传成功，并核对session/身份后，才fresh dispatch `hithink-stock-dump-trial.yml` on main，inputs为 `trial-purpose=stock-reading`、`stock-market-run-id=<精确合格Sector run>`。其余native选项默认；不能漏参、填native-market-run-id、填本次stock编号、用latest或Re-run jobs。已有成功输入若仍合格可以复用；新run_id不自动让旧行情变新。
4. 任何429或前置失败即停止这次闭环，不自动再开一个fresh run“验证瞬时限流”。保留错误/审计并区分失败阶段；需要再尝试时重新确认窗口、预算和provider条件。不能把失败audit当authoritative state。
5. 成功与失败都读完整stock日志；下载本次 `stock-reading-<run>-1`，核验repository/ref/commit/run/attempt、artifact digest与内部identity；用**该次捕获代码版本**执行离线重建，打开 `reading/index.html` 并读 `reading/stock-reading.json`（失败时该文件可能按设计不存在）。如需修bug，精确diff及完整PR CI后再merge，核验main CI，然后新运行；不可改写旧失败附件或合成未发生请求。

交付直接回答：是否有程序标的；每只的方向/自身5-20-60日raw变化/通过条件/业务依据/风险/下一问题。没有则分别说明无活跃方向、业务覆盖不足、完整输入但条件不符、数据不足、资格失败或请求失败。计划对象不是入选对象；零张卡不是一概quiet。run、artifact和校验回执作为支撑，而非取代产品内容。

## 7. 独立待办，不混入当前P0

#263 保持draft：head `fa4d9e48189ec421b7e17405a57070ae12db4ee0`，原base `c73f4dcc...`，3个新增文件+285/-0；CI `34045118986` / job `101518696734`，1699项通过。复用 `eval/disclosure_cognition/` 的两个冻结packet，clean/四类攻击/良性对照共12份输入，10项确定性回归。

```text
model_behavior = NOT_RUN
tool_capable_behavior = NOT_TESTED
```

不得用mock安全输出/JSON schema成功/一律拒绝，替代真实模型和正常任务完成的对抗评测；不扩大为Kernel schema、Prompt Firewall、Agent Manager或新memory平台。P0不因它暂停；未明确接手这条支线前不merge/rebase/覆盖它。

普通Sector下一完成交易日追加、当前版本fresh-dispatch同日幂等、RSS发布时间资格、消费者历史云端接续仍分别缺真实证明。RSS基线 `34010252507` 和相同1000版本的successor `34012474393` 不是新自然事件或消费者接续证明。既有32MiB/对象预算/90天限制保留，缺历史不静默reset。Position/Holding loop继续deferred。

## 8. 不变的语义与结束范围

```text
SHADOW OBSERVATION ONLY
HUMAN ATTENTION AUTHORITY = NONE
RESEARCH AUTHORITY = NONE
INVESTMENT AUTHORITY = NONE
```

不自动进入Research，不新增第三条canonical Human wake，不生成Recommendation/Action，不改写公司判断或冻结Research/Decision。原CATL/GigaDevice/Sanhua/Tinavi/Micron等立场只是旧记录，未由此轮重评。股票实现、工程授权、Human投资认可和真实执行是四件事。

此次收口只更新 `docs/project-state.md`、本文件，并原样归档旧索引；不改代码/测试/工作流/依赖，不动#263，不发起真实行情/RSS/公司原文/模型请求，不设置定时任务。后续真实动作由新对话在核验能力、时间和实际资格后完成。

核验入口：GitHub PR #259/#262/#264/#265；PR #263；Actions runs/artifacts如上。详细历史依据使用相应精确commit的文件和日志，不用本通知覆盖它们。
