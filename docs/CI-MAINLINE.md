# CI mainline / CI 施工接续入口

Updated: 2026-09-24. Engineering only; Investment Authority = NONE.

## 当前原则

Human 已明确授权按新架构全面审阅 CI，能拆则拆、能删则删、该优化就优化。复用 [#354](https://github.com/auguspp/decision-kernel/issues/354) 管有界整顿；产品架构仍读 AGENTS / 最新 #297。不新增治理平台、生产调度或模型调用。

**CI 保护仍有效的产品行为与历史兼容性，不永久保护每一代施工步骤。** 旧“全部历史测试永远 blocking”是可修订工程策略，不是不可修改原则；但架构变化也不证明旧 reader 已无人使用。拆分须按实际依赖、当前成果合同与失败传播作判断，不能凭测试数或文件名删除。

当前实施见 [#544](https://github.com/auguspp/decision-kernel/pull/544)；PR/测试/合并/发布状态必须从实际 run 读取。本页不是预填的验收结果。后续有界 CI 优化无需 Human 为每个文件重复授权；扩大运行、删除历史数据或外部付费权限另论。

## 已实现的改动范围

- 原生 concurrency：只有同一 PR 的过期 head 相互替换；main 使用每 run 唯一组，避免连 pending main 也被新 run 挤掉。未改生产 concurrency。
- 现有 setup-python 复用 pip 下载缓存，key 依赖 pyproject.toml；每次仍执行真实安装，不缓存虚拟环境或测试结果。base-only isolated/no-cache 安装保留。
- action-history 四个 tamper 复用一次真实、禁网络、验证过的 capture 准备；每例独立复制文件、解析 report、执行原 verify。正向/partial/fatal/transport 测试不改。复用 #443/#444，不建 fixture 框架。
- 删除固定旧试验入口 `.github/workflows/saved-research-once.yml`。原入口仅 manual、无日常调度，全历史两次运行 `34490271156`（失败，9/10）与 `34548590855`（成功，9/11）均已结束；原 v2 请求 blob `25ba54cfe5283feb30b2f2c0b3ff788aec2d826c` 不改。publisher 不订阅此入口；原请求、失败/成果、共享 runtime 和全部行为测试保留。原 prepared-disclosure 负向 workflow 断言随退役更新，不允许借退役激活裸旧 CLI。

这是资源去重与首个执行入口退役，不是全库 suite 分层完成。基线 31 个当前 workflow 文件，本切片删除 1 个后为 30；Actions 的 156 个历史登记不是 156 个现役文件。不得删除 run/log 美化库存。

## 当前执行与失败合同

**本切片仍执行完整 tests。** 本地默认串行；CI 明确使用：

```sh
python -m pip install -e '.[dev]'
python -m pytest -q -n 4 --dist=loadfile --max-worker-restart=0 \
  -o faulthandler_timeout=60 -o faulthandler_exit_on_timeout=true \
  --durations=100 --durations-min=1.0 --junitxml=pytest.xml
```

保留 PIT、身份/来源、权限、create-only/不确定写入、历史读回、Odds 算术等有效合同。PR checkout 实际 head、main checkout 本次 SHA，比较 git rev-parse HEAD；event SHA 单独保留。CI contents read-only、无 production secrets、不保留 checkout credentials。Test 使用 pipefail，不靠 skip/xfail/continue-on-error/retry 换绿，不重启崩溃 worker。60 秒是 CI stall 诊断边界，不是业务 SLA。

完整 collection、JUnit、pytest log、identity、环境保留在 `kernel-ci-<run>-<attempt>`，always 上传、30 天。早期失败可能没有完整 JUnit，仍是失败。原 synthetic pass/fail/worker-crash 继续真实执行 Test 脚本。静态资源检查不证明平台已发生取消或缓存命中。

第一切片保持 exact-head PR CI、正常审阅合并、独立 main CI、正常 publisher/readback 的过渡验收边界。后续按变更影响决定验收范围：改缓存不需要重新证明研究质量；改发布消费者则必须验发布。未知/混合变更先回全量，不能悄悄改变 downstream 对 kernel-tests 的成功定义。

## 接下来拆什么、保留什么

| 处置 | 对象与边界 |
| --- | --- |
| CONSOLIDATE 优先 | 内容与代码 CI 分流：纯文字、含计算脚本的研究档案、用途 registry、运行配置不能混为 docs。先明确内容/索引消费者和稳定 required check，unknown/mixed/code/fixture/workflow 回 full；不直接 paths-ignore 全 docs。 |
| RETIRE 逐项 | 已停用的 Pre→Quick 编排、冻结 ticker/日期的重复部署断言、一次性修复启动器。先核调用者、活动 run 与旧格式读回；删旧执行义务，不删原始证据或仍复用的 reader/validator。其他 API/source/recovery workflow 没有整体删除授权推论。 |
| CONSOLIDATE 接续 | intake 每次 main CI 成功启动再查 request diff 的空转；publisher 的代码重建/索引发布/观察更新触发。保留可信成功代码、显式请求与不确定写入边界，不在优化中关闭日常产品。 |
| KEEP | 当前 Radar/Stock 机械观察、当前成果合同、有效负向安全测试、独立 base-only 安装。最慢不等于最该删。Timeline 已退出普通 CI，不重复清理。 |
| DEFER | 无证据增加矩阵/worker、通用 selector/scheduler、自动性能治理。不得为瘦 CI 再造胖 CI。 |

## 测量、复用与历史

审计基线 main `0f644425dd3710551893625ab2eb3d9d2bc1d363`，CI `35984202408` / job `107582921346`，真实 artifact `10801701260` 已核对 SHA256/CRC/identity/JUnit：6189 唯一 tests、365 模块、0 failure/error/skip；pytest195.92s，job237s（install26s、collection8s、Test196s）。747.741 testcase-seconds / 4 CPU，理想均分约186.94s：继续调 scheduler 不是主要空间。并行 testcase 秒不能当作 wall-time 节省；冷缓存/热缓存与托管 runner 波动须区分，不预填提速。

Reuse Decision: REUSE / CONSOLIDATE。内部用原 CI/fixture 模式与失败回归；官方用 [GitHub concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)、[setup-python pip cache 实现](https://github.com/actions/setup-python/blob/main/src/cache-distributions/pip-cache.ts) 和 [使用说明](https://github.com/actions/setup-python/blob/main/docs/advanced-usage.md)。无新依赖；pytest-xdist/loadfile 的公共实现审查复用 #354 历史记录。路径拆分须遵守 [required-check/过滤语义](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)。

[31-workflow/耗时初审原件](https://github.com/auguspp/decision-kernel/blob/b3a3546560010f3683b02ec931f372ab714f2687/docs/CI-MAINLINE.md) 中 saved-research-once 的暂缓处置已被本次后续实读与退役替代；其他未实测对象仍不得冒充已签收。[旧 CI 入口](https://github.com/auguspp/decision-kernel/blob/0f644425dd3710551893625ab2eb3d9d2bc1d363/docs/CI-MAINLINE.md) 与 #354 保存更早基线/失败/清理记录，不因策略修订而改写。

回滚走普通 PR，不直接写 main、不 force-push、不动旧请求/证据/生产日程。远端写入不确定时先读回对账，不重发求绿。保留历史，不把 CI 成功解释为经济真理或投资权限。
