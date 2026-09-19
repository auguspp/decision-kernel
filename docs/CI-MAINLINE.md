# CI mainline / CI 施工接续入口

Version: ci-mainline-v1 / 2026-09-15. Engineering only; Investment Authority = NONE.

## 从这里恢复，而不是接着旧聊天猜

先重新固定 current main，读取本页、`.github/workflows/ci.yml`、`pyproject.toml`，再读 [#354 最新回执](https://github.com/auguspp/decision-kernel/issues/354)。代码进入 PR、合并、main CI 成功、正常 publisher 成功是不同阶段；本页不是某个未来 run 的成功证明。

Human 已将两个过长的施工会话交给当前 Main Construction，并明确要求先完成 CI，再接续后续项目。原话及范围在 [接手授权](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5678344365)；主线顺序记录在 [#297](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5678384813)。CI 收口不等于 #354 全仓架构审阅或 P0 使用验收完成。不要因为换聊天就重复已经合并的 #378/#381/#383/#385。

## 一套测试，两种执行方式

安装仍用 `python -m pip install -e '.[dev]'`。本地默认 `python -m pytest -q` 仍是串行；并行与 stalled-test fail-fast 只由 CI 的显式命令启用：

```sh
python -m pytest -q -n 4 --dist=loadfile --max-worker-restart=0 \
  -o faulthandler_timeout=60 -o faulthandler_exit_on_timeout=true \
  --durations=100 --durations-min=1.0 --junitxml=pytest.xml
```

所有 tests 都在同一 blocking `test` job 中，不按改动路径筛选，不用 `-k`/marker/ignore 排除慢测试，不增加 skip/xfail，不重启崩溃 worker，不设置 continue-on-error。`loadfile` 将同文件的测试交给同一 worker；现有 fixture 缓存是进程内的，mutable association 仍逐调用复制，plan 仍通过当时的真实 callable 重建。不能把缓存结果当成测试通过。

CI 额外复用 pytest 9.1 的内建 faulthandler：单项测试（含 fixture setup/teardown）超过 60 秒时先向 pytest log 输出线程栈，再退出该卡死进程。这个 60 秒只属于 CI deadlock 诊断/fail-fast；不改变本地默认 pytest，也不是业务 timeout、性能 SLA、skip 或自动重试。当前已接受 main 的慢项约为个位数秒，因此该边界用于识别异常 stall，而不是把正常慢测试切掉；若真实合法测试未来需要超过该值，应基于实测重新审阅，不能静默放宽或绕过。

新增依赖仅为 dev 中精确固定的 `pytest-xdist`；faulthandler 属于 pytest 内建能力，不新增依赖。不进入 base、Research、documents、feeds 或 production extras。真实 base-only 安装/CLI 检查继续运行，不降为 import-name grep，也不通过复用开发虚拟环境冒充 clean install。它自身保留 isolated/no-cache/no-retry 安装边界。

## 身份、失败与证据

PR 测试显式 checkout `github.event.pull_request.head.sha`，main push 使用 `github.sha`，并用 `git rev-parse HEAD` 实际比较；event SHA 单独留存，不与被测试代码 SHA 混为一谈。测试权限只读、不继承 production secrets、不保留 checkout credentials。

每个 CI run 的 `kernel-ci-<run>-<attempt>` artifact 保留 30 天，包含代码/event/run 身份、Python/包版本、CPU 数、pytest 完整 collection、JUnit XML 与 pytest 日志。这是 CI 诊断附件，不是 canonical Research/Radar/Market 状态，不进入 production restore 发现路径。上载使用 always；测试命令的 pipefail 保证 tee 不会吞掉失败。checkout/install 早期失败可能没有完整附件；stalled test 在 JUnit 最终写入前被 faulthandler 终止时也可能没有 `pytest.xml`，但 `pytest.log` 应保留触发时的线程栈。这仍是失败，不是 quiet success。

`tests/test_ci_contract.py` 既检查命令/依赖/权限边界，也在临时目录用工作流的实际 Test 脚本运行明确的 synthetic pass/fail/worker-crash 样本，验证退出码与 JUnit，禁止用模拟的全项目 PASS 代替它。既有 main-only Judgment timeline 继续依赖 `test` 成功，原 publisher 仍走正常路径。

## 已完成清理与保留理由

| 范围 | 处置 | 理由 / 边界 |
|---|---|---|
| PIT、身份、来源、权限、fail-closed、replay/retention 等 active contracts | KEEP blocking | 它们是持续有效的工程/认知边界，不能为速度删除或抽样。 |
| Stock 共享不可变测试准备 | CONSOLIDATE，复用 #381 | 减少重复准备，不缓存被测 plan，不共享可变测试结果。 |
| consumed direct successor 的历史 receipt 重复 literal | RETIRE 重复断言，复用 #383 | 保留 disabled/scope/hash 等结构契约；冻结 JSON、文档、Git 历史不改。 |
| consumed continuation 的历史 receipt 重复 literal | RETIRE 重复断言，复用 #385 | 保留 failed-work/predecessor/source binding 与现有 continuation 安全契约；不退役执行权限检查。 |
| base-only 安装与 isolated CLI 执行 | KEEP blocking | 基线约 6.69 秒，但它证明 dev extras 没有泄漏为基础依赖，不能只按耗时退役。 |
| 多核执行、JUnit、artifact 传输、stalled-test thread dump | REUSE | 使用 pytest-xdist、pytest 内建 faulthandler、GitHub 原生能力；不自建 scheduler/watchdog/registry/分片协议。 |
| pip cache、changed-file 筛选、fast/slow suite | DEFER | 安装不是当前主瓶颈；路径筛选/拆 suite 仍缺少净收益与隔离证据。无需靠减少 blocking coverage 换速度。 |
| 其他历史 one-shot 测试、production workflow 整理 | DEFER 至 #354 对应审阅 | 名称包含 once 或历史日期不等于可删除；仍在使用的 admission/recovery 合同继续有效。 |

## 复用依据与已知基线

[施工前 Reuse Check](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5678398231) 覆盖仓库内部、官方工具、公共 GitHub prior art。实际检查 pytest-xdist v3.8.0 的 [依赖/许可证](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/pyproject.toml)、[loadfile 实现](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadfile.py) 和 [运行/worker restart 说明](https://pytest-xdist.readthedocs.io/en/stable/distribution.html)，而非只看 star 数。官方 [setup-python pip cache](https://github.com/actions/setup-python#caching-packages-dependencies) 已比较，本切片未采用。2026-09-16 的真实 #384 双次 hang 进一步复用 pytest 9.1 内建 `faulthandler_timeout` / `faulthandler_exit_on_timeout`，不引入新的 timeout/watchdog plugin。

接手前精确基线：main `e6ab50663532745feb390978843072628a562845`；run `34952643776` / test job `104326855801`；实际 **3314 passed in 468.54s**，安装约 12 秒。早先 746.03、441.91、459.83 秒等不同 run 不能混成稳定 benchmark。新增 CI 回归预计增加 7 个测试；最终以 exact-head collection/JUnit 对账为准，不能只检查测试总数。

收口必须有：未删除既有测试的 diff、完整清单与执行结果、真实失败传播回归、exact-head PR CI、合并后的独立 main CI、正常 publisher 和结果读回。速度只按实际样本报告，托管 runner 波动不包装为保证；本页不会预填尚未完成的运行。

## 2026-09-19 第二轮实测：四 worker 与诊断体积修正

随着 Radar / Research / Odds 等新能力进入同一 blocking suite，main `eb64d63a164f50c4d4bcb4a9ff9821f49f409054` 已达到 4213 tests。run `35410366885` 的 pytest 为 **4213 passed / 344.79s**；安装约12秒、collection约9秒，pytest 再次成为主耗时。该 runner 报告4 CPU，而 #387 仍只使用2 workers，因此“更多 worker”从原 DEFER 条件重新进入有界实测，而不是凭 test 数量直接拆 suite。

PR #442 在保持完整 test identity、fail-closed、`loadfile` 与 `--max-worker-restart=0` 不变的前提下，保留三个独立 exact-head 样本：

| workers | run | pytest | 结果 |
| ---: | --- | ---: | --- |
| 2 | 35412336901 | 334.82s | 4213 passed；0 failure/error/skip |
| 3 | 35412499474 | 314.83s | 4213 passed；0 failure/error/skip |
| 4 | 35412508707 | 299.51s | 4213 passed；0 failure/error/skip |

三份实际 JUnit 各含4213个唯一 testcase，**testcase 集合完全相同**；执行顺序因 xdist 不同不作为身份差异。托管 runner 分别来自不同 Azure region，因此这些秒数是实际样本而非受控同机 benchmark；四 worker 的首个样本相对同轮二 worker 低约10.5%，且未出现 worker restart/crash。最终采用4 workers，仍由后续 exact-head 与独立 main CI 提供第二层实证；若实际 main 证明不稳定，按普通 reviewed PR 回滚，不通过 skip/retry 掩盖。

同一 PR 还修正两处 pytest 自动参数 ID：8MiB+ feed body 和512KiB+ Research progress body的**输入字节与断言完全不变**，只增加短语义 `ids`。实际诊断原件从 main run35410366885 的 `collection.txt` **9,386,728 bytes** / `pytest.xml` **9,555,747 bytes**，降到本轮 **473,881 / 约642.9KiB**；最长 collection 行从8,388,709字符降到16,485。ZIP因重复文本压缩本来很强，因此压缩包降幅较小；此改动的主要收益是 collection/JUnit/诊断可读性与传输解析负担，不冒充 pytest 主耗时优化。

这一轮仍不启用 changed-file selection、marker、skip/xfail、fast/slow suite、自建 sharding、test-result cache 或 continue-on-error。Stock capture/replay 的重复完整 synthetic preparation 仍是下一候选，只允许复用不可变 upstream/baseline；被测 validator、mutable plan 和结果不得缓存。

## 诊断与回滚

并行异常先读本 run 的失败/环境/collection/JUnit/pytest log，不自动重跑生产。若单项测试超过 60 秒，先使用 faulthandler 留下的线程栈定位 blocking call；不要用 Re-run 把首次 stall 擦掉。串行诊断使用同一精确代码、同一 extras，去掉 `-n 4 --dist=loadfile --max-worker-restart=0`，运行原完整 pytest 命令；保留身份和诊断附件。遇到失败不以添加 skip/xfail 或减少测试换绿灯。

需要代码回滚时，通过普通 reviewed PR 撤销这次 CI 配置及其专属回归/依赖改动；不改 #381/#383/#385、冻结 request、历史证据或任何 production workflow。回滚本身也必须通过真实 CI。不要直接在 main 写回旧文件，也不要 force-push。

CI 验收完成后，按届时最新 main、#297 与项目交接继续，不自动合并其他 open PR、不启动 CNINFO/Radar/Research 来证明 CI 成功。自然运行、真人使用和投资判断各自验收。
