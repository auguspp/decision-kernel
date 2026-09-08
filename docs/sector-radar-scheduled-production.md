# Sector Radar P0-1：每日自动生产，不扩展判断权限

本项只为已有 `sector-radar-shadow.yml` 接入工作日收盘后定时。保留手动入口，两种触发都走同一 producer、原重放、阅读、权威状态发布与 cache 保存链路。#277 的全部 qualified changes 可发现与首页 0–3 不变。

**工程配置与真实验收分开：本文件不证明自然 schedule 已运行。** 首条用于本次时间修正验收的真实运行必须绑定采用 18:13 配置的 main SHA、GitHub `event=schedule` 和 attempt 1，记录在本项 PR 的回执中；没有这种证据时状态为 `NATURAL_SCHEDULE_ACCEPTANCE_PENDING`。不以 CI、手动 dispatch 或本地合成测试替代。`FULLY_UNATTENDED_RECOVERY = NOT_ESTABLISHED`。

## 时点与开工证据

Human 最终确认的名义时点：**每周一至周五北京时间 18:13，UTC cron `13 10 * * 1-5`**。优先 completed-session 稳定性与共享任务错峰，保留晚间消费窗口，不追求盘中或最早收盘后结果。不增盘中、小时轮询或节假日调度器。非交易日仍由原 provider calendar 与 completed-session qualification 判断，不能靠 weekday 或时钟制造新 session。

基线 `8ce373cbd9e9390bc7c94fd504d5d499cc520790`（#277）读回时，开放 PR 只有独立草稿 #263，非 PR Issue 为 0；全仓 in_progress/queued 均为 0。这只是开工时的观测，不是之后的活动或额度保证。

当前四个 workflow 引用同一 repository Key：Sector、本仓 `decision-inbox`、`hithink-stock-dump-trial`、`live-dogfood`。只有 Inbox 既有定时 `20 8 * * 1-5`（16:20），使用 Key 的 job 超时 8 分钟；stock-dump 有手动及两个限定路径的 main push，live-dogfood 为手动。此次不改另外三个工作流，也不碰 stock-dump 的 push 路径。

18:13 比 Inbox 名义时间晚 113 分钟，超过其名义超时窗口 105 分钟；Sector 自身保留 20 分钟 timeout，正常情况下晚间仍有阅读消费空间。已成功的 Sector run `34107253263` 在 2026-09-07 17:39–17:54 运行，是既有收盘后生产的历史观察，不是每日供应商就绪承诺。实际资格仍由运行时验证。

必须保留反例：Inbox 的自然 schedule run `34132068387` 实际到 **2026-09-07 22:16:34** 才启动，最终 failure；本项未分析其失败原因。名义 cron 错峰不保证无碰撞。[GitHub 官方 schedule 文档](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) 明确可能延迟，高负载时甚至丢弃排队任务；13 分也避开整点，但不提供准点或每日必达 SLA。

## 同一路径与最小改动

原 main-only 与 attempt 1 guard 保留；采集前的活动检查也只允许 `workflow_dispatch` / `schedule`。发布重放脚本与联合阅读脚本原来只允许手动事件，本项仅扩展这两个 event allowlist，仍要求 main、首次尝试、无市场凭据；原完整性、确切身份、原件字节、重放与阅读验证没有跳过。

`.github/scripts/check-sector-scheduled-activity.py` 在原采集前做一次 GitHub 元数据观察：逐个读取 in_progress / queued / waiting / pending / requested，各最多一页 100 个 run，共最多 5 个 GET；任何查询错误、重定向、超限、不完整或含非终态 peer run，均非零退出，不采集、不发布、不自动重试。使用现有 `actions: read`，不访问 HiThink、Key、quota，也不持久化 token 或原 HTTP 错误正文。[状态与分页依据](https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-repository)。

检查三个 peer 的所有潜在 Key 作业，可能保守阻止实际不消费 Key 的 peer 分支。Sector 自己由原 `sector-radar-prospective-state` concurrency 串行、`cancel-in-progress: false` 保证，不把其排队后继当 peer 导致自锁。**这个检查不是原子锁**：检查后新启动的 peer、外部机器和其他仓库消费者仍可能碰撞；它不证明额度可用。遇到 429 仍停止 bounded attempt，不 Re-run、不 fallback。

活动检查只写 Job Summary/日志，不往 sealed run inventory 偷塞新文件。原 producer 之前失败时，可能没有 operations.json 或 audit ZIP；该情况显示“未取得生产记录/检查失败”，不能伪装 quiet。原 producer 已开始后的失败继续保存现有失败审计与 operations。Invocation summary 增加 trigger / run / attempt / SHA / UTC 记录时钟和活动检查结果，不增加 Human wake。

## 定时状态必须接续同一条恢复链

#278 合并后的代码读回发现一个遗漏：成功运行查询仍带 `event=workflow_dispatch`，会隐藏较新的 scheduled success，转而选择更旧的手动状态；两次连续定时运行因而可能错误缺日。这个代码缺口不能由 CI green 掩盖，本项以独立的小修复补齐，不声称它已经发生过自然定时失败。

修复仅移除同一 Sector workflow、main、success 查询的手动事件过滤，使最近成功记录不因触发类型而不可见。仍只检查最新 prior success 的精确 artifact：该包缺失或过期，返回不可用并 fail closed，绝不继续寻找旧手动包或旧定时包；不增请求、不改分页数量、cache/manifest 权威规则、状态机或恢复实现。

新增五项参数化回归的模拟 GitHub 响应真正遵守 URL event filter，覆盖“新定时/旧手动”“新手动/旧定时”“连续定时”，以及最新定时 artifact 缺失/过期时不回退。它们能暴露旧查询的错误，但不是自然 schedule 验收。

## 原状态机和恢复边界

| 条件 | 原生产语义 |
|---|---|
| 最新合格完成日等于 cached 日 | `VALIDATED_ALREADY_CURRENT_NO_PROSPECTIVE_EVENT`，candidate_count=0，不新建回顾性事件 |
| 最新合格完成日恰为 direct next | 只追加一次，`APPENDED_COMPLETED_SESSION_QUIET` 或 `APPENDED_COMPLETED_SESSION_WITH_SHADOW_CANDIDATES` |
| 有中间完成日缺口 | `FAILED_CLOSED`；明确 qualified recovery required，不跨日桥接 |
| 最新成功 state artifact 缺失/过期/完整性失败 | fail closed；不倒找更旧成功来掩盖缺失，不依赖 cache 单独恢复、不 bootstrap reset |
| provider/429/无效行情 | 失败不是 quiet；不重试。若随后形成 gap，则须显式 qualified recovery |

开工核到最近成功的 Sector 为 `34107253263`，state artifact `10013384600`（未过期），完成日 2026-09-07。下载 ZIP 为 438508 bytes，SHA256 `e154b1221fd8ecee699eca6f0390d8c9123e2624a28012a458b51a22444e3848`；三文件 CRC、manifest 的 state/ledger 文件摘要匹配。state hash `93a4e45222e085d5e06e75848c794546c3874c1c4f0316d96a64b78dda654841`，ledger hash `d37316b957117698c8e03d0b4064909fde81b90abdc77d80fe44b700b2d68b84`。这只是启用前基线，**没有把该 run 硬编码成永久 restore 来源**。

保留原 operations.json/md；新 session 的 result.json/summary.md；同日的 same-session-validation.json；complete run audit；authoritative state bundle；cache acceleration copy；context 与 economic/company reading；publication verification。REST 成功运行查询仅移除手动事件过滤，未改 state/ledger/operations schema、权威恢复及缺失包不回退规则、replay inventory、detector/rank/gate 或任何 HiThink 请求预算。这里只增加每天自动尝试的频率，不宣称累计请求总量不变。

## 确定性测试与自然验收

四个旧测试文件中的手动限定断言禁止 schedule，与本需求冲突：把这些断言迁移为双触发/精确 cron（发布入口的拒绝样本改为未授权 push），保留其余权限、串行、恢复、发布与阅读断言，并增加测试，而非绕过 YAML 检测或删掉整个测试。

新增测试检查双方主干/attempt guard、单一生产命令、允许事件在下游的闭合、活动/不完整查询非零停止、失败不打印凭据、元数据请求不重试。合成 provider 输入走原 adapters/detector/audit/replayer，分别检验同日、quiet、candidate、gap、provider failure 和429异常；原 #277 discoverability 测试继续执行。重放和失败审计均不得生成 live state。事件 admission 单测会隔离昂贵下游函数，原三种状态的完整 publication/context 集成测试也扩展至两种触发，reading checks 仍由既有集成测试覆盖；不把模拟事件名说成自然 schedule 验收。

首条自然运行核验：event=schedule；采用 18:13 配置的实际 main SHA / attempt 1 / 开始与完成时钟及相对名义时点的延迟；活动检查和真实共享任务时间；精确 restore run/artifact/manifest；calendar 与最新合格完成日/cached/direct next；provider 请求记录及429；operations 状态/candidate数/state与ledger hash；完整远端 artifacts；原离线重放与发布 gates；Job Summary。缺任何项如实记录。CI绿不预填这一回执。

第一次自然运行失败就保留原失败，调查真实原因；不 Re-run，不手动替代。未触发、触发延迟、失败和成功但未验收是不同状态。没有自动 gap recovery、补触发器或第二 provider。本项不承诺后台代查，也不要求用户搬运日志。

**SHADOW OBSERVATION ONLY；Human Attention / Research / Investment authority = NONE。** scheduled success 不等于市场结论正确；quiet 不等于市场没有重要变化。没有新 market-state reader、Research、Daily Brief、全市场 Stock Surprise 或其他平台。
