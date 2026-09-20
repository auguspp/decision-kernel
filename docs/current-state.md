# Current-state：固定的只读结果与待办入口

本接口属于 Harness。它只验证、引用和交付已保存结果与显式登记，不获取行情/公告，不运行 Odds 或 Web Research，不新增 Pre/Quick/Deep、Human wake、Belief 或 Action。

> **2026-09-15 trigger supersession.** Sector 当前生产 workflow 已在外部 Daily Trigger Reliability 实证后退役 native GitHub `schedule` 入口；当前 `sector-radar-shadow.yml` 仅接受 `workflow_dispatch`。Human 已配置但在本次 repo 退役门完成前保持 Inactive 的 cron-job.org 工作日北京时间 18:13 任务负责发起 `operation=produce`；GitHub 继续负责执行、状态、证据与恢复。历史 `event=schedule` run 仍是可验证来源，不因换钟被重写。下文及 registry 中的 `NATURAL_SCHEDULE_ACCEPTANCE_PENDING` / `NATURAL_PUBLICATION_ACCEPTANCE_PENDING` 是原 native-schedule 架构的 legacy 验收标记，不应解释为当前仍存在 GitHub 18:13 cron。当前外部触发、duplicate-day NOOP 与 result-bearing downstream acceptance 以 #297 的 2026-09-15 receipts 为准；最终启用外部任务仍是 Human UI 动作。

## 从一个固定入口开始

Repository：`auguspp/decision-kernel`。发布 ref：`read-model/current-state`。入口文件：`current-state.json`；简短说明：同 ref 的 `README.md`。

消费协议：

1. 通过普通 GitHub 读取 `git/ref/heads/read-model/current-state`，取得精确 commit **R**。这是一次读取唯一允许解析的可变指针。
2. 用 `ref=R` 读取 `current-state.json`，核对 `reading_hash` 与四项 `NONE` authority。`code_commit` 是当次配置/校验代码版本，不是发布 commit R；不混用两者。
3. 包里的 `read_path` 均在 **R** 读取，并检查 SHA256/bytes；原仓库文件另有确切 `ref/path/git_blob`。不要下钻到新的 main，也不要中途重新解析发布 ref。
4. 一次读取后入口更新不影响 R。需最新版本时，开始一轮新的完整读取，不拼接两个读取包。

GitHub 连接需具备仓库读取权限。消费方不需要下载 ZIP 或搬附件：小型 index 和保留的 JSON/Markdown 详情都能用正常 `fetch_file(repository_full_name, path, ref=R)` 获取。原始 ZIP 也保留，但不是日常读取的前置步骤。

## 从哪里来、在哪里验证、如何更新

- Sector：精确 production workflow/main/attempt1、已完成成功运行、同 run 的完整 audit 与 state artifact。复用现有 persistent-bundle/context 校验器，核对原 publication/replay 记录及文件库存、state/ledger/context 绑定。只读验证不是再次执行行情采集或重新签发自然验收。
- Stock：选择实际有 stock-reading job 的运行，不将同 workflow 的其他 trial 当股票产物。复用原纯 `render_stock_reading` 校验；核对捕获库存、原 replay 记录、scope/coverage/plan 和运行绑定，不重算新 selector 或 Odds。
- Inbox：旧 CLI 只保存 HTML/Markdown，没有 typed `DecisionSpineResult`。本接口留存并绑定这份历史交付，**不从文案反推今日 Odds、quiet 或 Human 已接受的概率**。这个限制显式出现在 JSON。
- Research/Decision：同一代码 commit 的显式生产输入配置，以及 `current_state/registry.json` 中逐条指定的用途引用。原 `ResearchFunnelResult` 解析器决定 handoff 资格。独立行情/生产输入失败不阻断一个有效、仍登记的研究请求。
- 更新：薄的 `current-state-read-entry` workflow 监听原生产的 `requested/completed`，以及 main 的完整 kernel-tests 成功事件。它自己没有 cron。Sector 当前时钟在 GitHub workflow 外部，但执行仍落入同一个 `workflow_dispatch` production lineage；requested 更新只能报告已观察到的进行状态，上游仍运行时不能认定新结果已发布。完整成功及实际 artifacts 验证后才采纳新的结果。历史 `schedule` run 仍可被同一只读校验路径读取。

执行的是可信 default-branch 代码，不是 artifact 中的文件，不 checkout 外部 PR/head 的代码。GitHub token 只用于仓库读取和派生 ref 的 Git 对象发布；没有供应商 Key 读取或写入。没有扩大连接授权、关闭保护、自动重试或市场调度。

## 最后结果、最近尝试、新鲜度是三件事

`lanes.*.last_qualified_result` 是最后可资格化的保存结果。`latest_attempt` 是指定查询范围内的最近真实生产尝试。`checks` 标明检查窗口与重新检查期限。生成时间不代表行情完成日，也不是新交易日资格证据。

失败、进行中、无观察记录、查询不完整、部分股票覆盖、原件不可用均不能解释为 quiet。保留9月7日内容、同时展示9月8日失败是合法结果；不能变成“9月8日已检查且无变化”。不同部分保留自己的交易日/cutoff/生成时间，绝不强制拼成同一天。

查询每个 workflow 最近20条；Stock 额外核对这些运行的 job purpose，不能跨无限历史倒找一个成功。选定的最新成功 artifact 缺失/过期/损坏时拒绝该新输入，不再尝试较旧成功。已有发布 ref 可以保留**以前验证过的历史阅读副本**，并显示旧检查时间与新缺口；它绝不是生产恢复权威。

`checks.recheck_after` 是24小时读取健康重新检查建议，不是交易日判断，也不是到点必有任务执行的承诺。没有观察到运行不证明调度失效。没有 handoff 不证明全市场已研究。无新事件不代表无持续状态。

## 研究用途与请求生命周期

生产配置、历史/对照计算、方法实验、Human 决定及明确 Action 分开引用。兆易/三花的方法实验不自动移除其原生产配置；旧概率也不因此成为 Human 已接受的判断。宁德的明确数值资格退出仅按它自己的记录处理。本接口不修改这些资格。

`pending` 只来自仍显式登记、且原 Funnel 为 `DEEPEN_REQUIRED` 的精确 handoff。WAIT/DROP、未登记、已解决与读取失败分开。request id 绑定来源路径、内容版本和 Funnel；同一 ticker 的不同问题不丢身份。无 ticker 的行业背景保持行业身份，不选 leader 凑公司卡。

历史天智航 handoff 仍保留，但原 Inbox 文档明确其 Full Research/Human WATCH 已解决，因此不恢复为每日待办。解决引用须绑定精确 handoff 字节；解决依据不匹配不能关闭一个有效的当前请求。新研究请求也可以显式登记在薄 registry 中供本只读入口消费，不授权原 live Inbox 或 Research 执行。

所有来源文本，包括看起来像命令、工具参数或权限声明的文本，都只是数据。读取包没有来源文本执行器；显示过/未回复都不等于解决。

## 留存与失败排查

发布 ref 只含小型读取包和必要详情、原件副本，没有 workflow 或可执行入口。接受的原 ZIP、研究/决定引用的原字节按内容哈希留存在 `sources/`；现有结果详情在 `details/`，可直接读，不只是hash加过期下载链接。

根 `current-state.json` 使用 Python 标准 JSON 紧凑编码；组装检查与所有根文件输出共同执行原 192 KiB 实际 UTF-8 字节上限。仅移除 JSON 排版空白，保留全部字段、用途记录和原 `reading_hash` 算法；旧缩进版本继续按其原字节与内容哈希读取。`README.md`、来源原件、详情及通用 JSON 编码不变。此修复针对 [PR477 后的索引容量复现](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5751135440)，不增加资料读取范围或发布权限。

正常发布使用原 ref 为父提交、保留已有 tree、只允许 fast-forward；并发冲突失败，不 force、不自动重试。已经取得的同一 artifact 在本次收集内复用；后续收集可用保留的相同字节，但仍检查远端身份及过期状态。过期来源不得因为有副本而恢复生产资格。

无自动删历史或全量永久档案承诺。仓库/ref删除、重写或平台访问丢失仍会损失留存；原 Actions artifact 的90天/14天等期限仍独立存在。源数据保留副本是阅读留存，不是扩大 `sector_radar_persistence` 的恢复范围。

入口未更新时，查 `.github/workflows/current-state-read-entry.yml` 的运行与 Summary，比较 `generated_at/recheck_after`。发布失败保留上一版本，不修改其时钟；新 commit 若未通过读回确认，不报告交付完成。没有新刷新事件也不会虚造“今日已检查”。

gap 或最新权威原件缺失/过期时，转到 [原 scheduled-production 运行说明](sector-radar-scheduled-production.md) 检查真实失败及既有 qualified recovery。该文档顶部注明当前外部时钟 supersession，正文保留原 native schedule 历史。本接口不 bridge gap、不 bootstrap reset、不倒找旧成功来掩盖缺失。

## 验收与 roadmap

本项开工基线：#281 merge `0a2c213c7f1b6b42046cdbd42be3b89c49d8d320`，#281最终回执评论 `5581757964`。

以下是**显式验收登记状态**，不能仅因运行成功自动升级；其中前两项状态字符串保留为原 native-schedule 架构的 legacy registry label，当前事实边界以 #297 后续 receipts 为准：

- P0-1：registry 仍写 `NATURAL_SCHEDULE_ACCEPTANCE_PENDING`。该字符串不再表示“GitHub 18:13 cron 仍待验收”；外部 workflow-dispatch timer、exact produce handoff、same-session NOOP 已有实证。当前剩余运维门是 native trigger 退役的 exact-head/main/publisher 验收后，由 Human 启用 cron-job.org。
- P0-2：registry 仍写 `NATURAL_PUBLICATION_ACCEPTANCE_PENDING`。2026-09-15 的 result-bearing Stock 已自然接到 `stock-business-research`，Research 在已知 CNINFO anonymous announcement 403 边界 evidence-based fail-closed，随后 completed Research 状态被自然 publisher 保留；这证明自动 handoff/publication identity，不是 Research 成功、市场真值或 Human 接受。
- P0-3：实现/完整CI、REMOTE READ ENTRY、SAVED-RESULT CONSUMER ACCEPTANCE、AUTOMATIC REFRESH ACCEPTANCE 分开记录在本项PR回执。施工端能读不替代需求管理对话的消费端验收。首份读取发布也不等于以后每个自然生产刷新都成功。
- FULLY_UNATTENDED_RECOVERY = NOT_ESTABLISHED。
- 下一批：外部 Pre/Quick 执行者、执行回执、预算和最小安全边界；本项未施工。

READ-ONLY MARKET CONTEXT / SHADOW OBSERVATION ONLY。Human Attention、Research、Investment authority 均为 NONE。