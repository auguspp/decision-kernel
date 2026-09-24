# CI mainline / CI 施工接续入口

Version: ci-mainline-v2 / 2026-09-24. Engineering only; Investment Authority = NONE.

## 当前授权与方向

Human 2026-09-24 明确要求：思路调整后全面分析 CI，哪些可拆、可删，该优化就优化。复用 [#354](https://github.com/auguspp/decision-kernel/issues/354) 管这次有界整顿，不另建治理平台。当前产品架构仍以 AGENTS / 最新 #297 的 R5.1 为准；本页不启动 Radar、模型实验、Full 或任何新定时。

**CI 保护当前仍需承担的行为与兼容性，不永久保护每一代施工步骤。** 旧的“每次改动必须重跑全部历史测试”是可以随依赖证据修订的工程策略，不是 Kernel 的不可修改原则。反过来，R5.1 也不意味着旧数据不再需要读回、API 模块已无人调用，或可以凭文件名删除安全检查。

本轮先实施低风险资源优化；测试分层、默认路径退役仍按下面的对象与证据推进。没有实施并验证前，**实际 blocking 命令仍运行完整 tests**，不得把路线图写成已缩减覆盖。后续已获准的有界 CI 优化不需要 Human 为每个文件重复授权；扩大运行/数据删除/外部费用权限另论。

## 恢复与真实验收

固定 current main，读取本页、`.github/workflows/ci.yml`、`pyproject.toml` 和 #354 最新回执。PR、exact-head CI、正常合并、独立 main CI、正常 publisher/readback 是不同事实；只有修改会影响发布边界时，才把发布语义作为该变更的验收对象，不把 CI 当研究质量或 Human 接受的证明。当前已有 publisher 会由成功 main CI 自然触发，本切片未删除它。

第一切片的验收保留旧的 exact-head PR、独立 main CI 与正常 publisher/readback 边界，不能由本页预填完成。保留首次失败，不以 rerun/skip/xfail/continue-on-error 换绿。后续若拆 suite，须先确定稳定 required-check 和 downstream 消费者合同，再改变触发语义。

## 精确审计基线

代码 `0f644425dd3710551893625ab2eb3d9d2bc1d363`；main CI `35984202408` / job `107582921346`；artifact `10801701260`。

真实下载 ZIP 301380 bytes，SHA256 `41bca64455f449ab76a3b1a98ea5c66fae340075f1c86015808e6e4149319c2f`。CRC、identity、JUnit 已核对：6189 个唯一 testcase，365 个模块，0 failure/error/skip。pytest 195.92 秒；JUnit 累计 747.741 testcase-seconds；runner 4 CPU。四 worker 的理想均分下界约 186.94 秒，进一步调 scheduler 的空间不是主要问题。

Job 实测 237 秒：安装 26 秒，独立 collection 8 秒，Test 196 秒，其余约 7 秒。单一托管样本，不是 SLA，也不是改动后的提速证据。

| 测试模块 | cases | 累计 testcase 秒 |
| --- | ---: | ---: |
| stock_reading_calendar | 17 | 51.438 |
| stock_discovery_page | 28 | 50.606 |
| stock_action_history_capture | 10 | 50.597 |
| woton_report_representation | 25 | 46.932 |
| stock_reading_reconciliation | 34 | 42.218 |
| stock_radar_capture | 29 | 38.990 |
| stock_company_coverage_v2 | 13 | 35.087 |
| stock_issuer_isolation | 29 | 31.669 |
| stock_radar_reading | 32 | 29.870 |
| stock_sector_raw_retention | 7 | 26.926 |

前十共 404.333 testcase-seconds；并行时间不能逐项相加成 wall-time 节省。Stock 抓取/回放仍在使用，不能为追求少测试而删掉。`saved_research_once` 的 45 个测试在该样本仅约 2.9 秒：旧测试的维护负担和耗时负担必须分开判断。

## KEEP / CONSOLIDATE / RETIRE / DEFER

| 对象 | 当前处置 | 具体边界与接续 |
| --- | --- | --- |
| PIT、来源/证券身份、权限、历史读回、create-only/不确定写入、Odds 算术 | KEEP | 属于持续有效产品合同；保留真实失败传播和反例，不靠日志齐全替代。 |
| 同一 PR 已被新 head 取代的 CI | CONSOLIDATE | 原生 concurrency，只取消同一 PR 的旧运行；main 采用每 run 唯一组，不丢独立或 pending main。 |
| 每次开发安装的重复下载 | CONSOLIDATE | 原生 setup-python pip cache，key 依赖 pyproject；每次仍真实安装，不缓存环境/测试结果；base-only isolated/no-cache 安装不变。冷/热命中收益分别实测。 |
| action-history 四个 tamper 的相同上游 capture | CONSOLIDATE | 复用 #443/#444 的不可变输入模式；每例独立文件、report 和真实 verify，正向/partial/fatal/transport 测试不改。 |
| 文档/研究档案/索引变动一律全工程验收 | CONSOLIDATE，下一结构切片 | 分开纯文字、含计算代码的研究材料、用途 registry、运行配置。先审消费者与对应内容/索引校验；unknown/mixed/code/fixture/workflow 改动回 full。不得直接 paths-ignore 全 docs。 |
| 已退役 Pre→Quick 编排、冻结试验和一次性修复的重复部署断言 | RETIRE 候选，尚未删除 | 先证明入口已停用、调用者已迁移、旧格式读回仍有覆盖。删旧执行义务/重复 literal，不删原始证据、失败、冻结输入和仍被复用的 reader/validator。 |
| main CI 成功后无条件启动 intake | CONSOLIDATE，待触发合同审阅 | 现有 job 已按 request diff 限制实际工作，但仍每次启动 runner。后继应保留可信成功代码与显式请求变动绑定，不能变成任意 push 执行。 |
| current-state publisher 与 kernel-tests 的绑定 | CONSOLIDATE，待消费者审阅 | 区分代码重建、索引发布、观察更新；不在本切片断开 publisher，也不取消 requested 可见性或把失败当无变化。 |
| 判断研究推理是否严格走固定角色/轮次/Pre | RETIRE 默认工程义务 | R5.1 按成果/证据/交接验收研究；旧序列化格式的兼容测试仍须留在适当层。CI 不认证经济真理。 |
| base-only 安装、full collection/JUnit、失败日志、4-worker loadfile | KEEP 当前实现 | collection 仅 8 秒，尚不足以承担另建身份采集机制的成本。缓存不替代任何执行结果。 |
| 任意增加矩阵/worker、通用选择器/调度框架、自动性能报警 | DEFER | 不为精简 CI 另造一套胖 CI；没有当前收益证据不建设。 |

### Workflow 盘点范围

精确 main 的 `.github/workflows` 是 **31 个文件**，不是 Actions API 返回的 156 个历史登记。历史登记中存在当前 tree 已没有的临时施工入口；不能把它们全部算作现役，也不删历史 run/log 来美容。

下表覆盖 31 个当前文件的去向；未逐项核验实时使用的对象保留 DEFER，不把库存盘点冒充全部运行验收。

| 当前文件（省略 .yml） | 处置 |
| --- | --- |
| ci | KEEP；本切片优化资源，不改执行覆盖。 |
| current-state-read-entry；incremental-disclosure-intake | CONSOLIDATE 候选；已读完整触发/步骤，CI fan-out 如上。 |
| stock-business-research；saved-disclosure-research；saved-research-once；sub2api-codex-validator-smoke | DEFER 删除、优先审退休 API 执行入口。stock-business 包含来源保管/修复与多种旧研究模式，不能整个删；saved-research-once 仍被一个 prepared-disclosure 测试直接读 workflow。 |
| sector-radar-shadow；hithink-stock-dump-trial；stock-reading-after-sector；sector-member-reading；radar-concept-source；radar-concept-detail；radar-industry-breadth；radar-institutional-source；radar-newsnow-daily；vibe-concept-snapshot | DEFER 配置改动；在用或正在验收的机械观察/读取层不能因 hosted Quick 更强而整体删除。各真实运行/调度合同仍以对应入口为准。 |
| decision-inbox；apply-disclosure-assessment | DEFER；用户交付/写入边界需独立检查，不能当 CI 杂项删除。 |
| judgment-timeline | KEEP 手动阅读面；先前清理已让它退出普通 CI，不重复施工。 |
| cninfo-announcement-source-probe；economic-release-discovery；economic-source-capture；mineru-pdf-capability-probe；sanhua-relation-acquisition；sanhua-source-acquisition；sector-public-history-probe；sector-radar-historical-study；sector-recovery-once；stock-field-source-study；live-dogfood | DEFER 逐个退役审阅；区分可复用获取/诊断和已消费一次性执行。旧公司名、once/probe 字样本身不是删除证据。 |

## 当前执行合同

本地 `python -m pytest -q` 默认仍串行；CI 明确使用：

```sh
python -m pip install -e '.[dev]'
python -m pytest -q -n 4 --dist=loadfile --max-worker-restart=0 \
  -o faulthandler_timeout=60 -o faulthandler_exit_on_timeout=true \
  --durations=100 --durations-min=1.0 --junitxml=pytest.xml
```

PR checkout 实际 head，main checkout 本次 SHA，并比较 `git rev-parse HEAD`；event SHA 单独保留。contents read-only，不给 CI production secrets，不保留 checkout credentials。Test 使用 pipefail，卡死在 60 秒先留栈后失败，不重启 worker。60 秒是 CI deadlock 诊断边界，不是业务 SLA；真实合法慢项必须依据实测审阅。

`kernel-ci-<run>-<attempt>` 30 天保留 identity、环境、full collection、JUnit 和 pytest log，always 上传。早期安装失败或 stall 可能没有完整 JUnit，仍是失败。原 synthetic pass/fail/worker-crash 测试继续真实执行工作流 Test 脚本；缓存和资源策略的静态回归不是平台实测取消/命中证明。

## Reuse Check 与回滚

Reuse Decision: **REUSE / CONSOLIDATE**。内部复用原 ci.yml、test_ci_contract、#443/#444 fixture 模式；官方复用 GitHub concurrency 和现有 setup-python 的 pip cache；公共实现检查 actions/setup-python 的 `src/cache-distributions/pip-cache.ts` 及 `docs/advanced-usage.md`，历史 pytest-xdist/loadfile 审阅复用 #354 已保留记录。没有新依赖、选择器、scheduler 或生产 cache。

来源：
- [GitHub concurrency：包括 pending 替换与条件取消](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
- [setup-python cache 实现](https://github.com/actions/setup-python/blob/main/src/cache-distributions/pip-cache.ts)
- [setup-python usage](https://github.com/actions/setup-python/blob/main/docs/advanced-usage.md)
- [路径过滤与 required-check 语义](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)

回滚通过普通 PR 撤销本切片 workflow/fixture/资源回归，不直接写 main，不 force-push，不动旧请求/证据或生产日程。发生不确定远端写入先读回对账；保留失败，不通过新入口绕过权限。不得把缓存命中、测试数减少或一次更快的 runner 当成产品验收。

## 历史入口保留

2026-09-15 至 09-20 的完整旧说明、基线和 #378/#381/#383/#385/#387/#442–444/Timeline 清理记录见 [本页前驱版本](https://github.com/auguspp/decision-kernel/blob/0f644425dd3710551893625ab2eb3d9d2bc1d363/docs/CI-MAINLINE.md) 和 #354。它们是已发生的证据，不因当前策略修订而失效；不再把旧 DEFER 或“永不拆 suite”措辞当成本次新授权的否决条件。
