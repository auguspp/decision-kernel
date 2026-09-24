# CI mainline / CI 施工接续入口

Updated: 2026-09-24. Engineering only; Investment Authority = NONE.

## 当前职责

Human 已授权按新架构拆、删、优化 CI；继续授权与本轮范围见 [#354/5812645340](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5812645340)。产品仍按 AGENTS / 最新 #297，不新增模型调用、治理平台或生产调度。

**CI 保护当前有效行为与历史兼容性，不永久保护每一代施工步骤。** 保留历史不等于永远重跑所有历史脚手架。改动、PR、CI、合并、发布、研究接受是不同事实；本页描述执行合同，不预填验收成功。

## 两条验证路径，一个稳定检查

`kernel-tests` / `test` 名称不变，PR与main都产生实际检查，不使用顶层 paths-ignore。

- **文字路径**：仅根 README/AGENTS、本文、RESEARCH-ENTRY、research-outcome-contract-v1，以及新增 `docs/readings/**/*.md`。只接受普通非执行文件的新增/修改；既有研究原件修改、删除、改名或特殊mode仍走完整路径。
- **完整路径**：src、tests/fixtures、workflow、依赖、registry/JSON、研究计算脚本、其他未审查路径及混合改动。`full-research-method-v3.md`有实际历史回放测试消费者，不因扩展名为md就进入文字路径。文字路径不代表所有研究保存都已加速。

分流使用完整 Git base→head raw/NUL差异，关闭rename折叠，不受平台300文件path过滤上限影响。PR比较event base/head；push比较event before→sha，不能只看最后一个commit。checkout必须等于本次代码SHA。差异/基线读取失败或范围不明回full，不能生成内容成功。

文字路径还要求**精确base SHA存在本仓库main/push/attempt1成功CI**，且同SHA较新的失败/进行中运行不能被旧绿灯掩盖。使用原生gh只读查询；它不是未验证代码的免检通道。成功的文字CI维持未变代码的可信基线，后续文字提交可依次继承；不是在新环境重跑全套的声明。新增代码消费者依赖这些文字入口时须同步审查此范围。

文字路径不安装工程依赖、不收集全库、不执行全量pytest；运行本分流的stdlib回归，并检查实际commit中的UTF-8、非空、无NUL/未解冲突。源码不执行，来源链接不联网；不认证链接有效、事实、计算、研究方法质量或Human接受。保存scope.json、content-check.json和真实日志，明确 `FULL_SUITE=NOT_RUN_CONTENT_ONLY`，不伪造全量JUnit。

## 完整路径保持的合同

```sh
python -m pip install -e '.[dev]'
python -m pytest -q -n 4 --dist=loadfile --max-worker-restart=0 \
  -o faulthandler_timeout=60 -o faulthandler_exit_on_timeout=true \
  --durations=100 --durations-min=1.0 --junitxml=pytest.xml
```

原Test脚本不变；本地默认串行。无skip/xfail/continue-on-error或失败worker重启，pipefail保证真实失败；60秒只是CI stall诊断。每次完整路径都真实安装，即使pip缓存命中；独立base-only isolated/no-cache安装和真实pass/fail/worker-crash回归保留。PIT、身份/来源、权限、create-only/不确定写入、旧格式读回、有效Odds计算继续验证。

CI仅contents/actions read，无业务secrets，不保留checkout credentials。actions read仅用于核对base CI；GH_TOKEN不进入内容文件。完整路径保持原collection、JUnit、pytest日志和环境；两条路径均有code/event/run身份和scope，上传到原 `kernel-ci-<run>-<attempt>`，always/30天。早期失败可能没有完整产物，仍是失败。

原并发不变：同PR过期head可替换，main每run独立组。现有发布器/来源准入收到的成功含义是“本次范围验证成功”：full，或可信main基线上的代码不变加内容检查；不能把后者描述为本SHA全量重测。publisher仍验证保存产物，来源/模型仍须原显式权限；没有改变其触发/写入/研究权限。

## 进度与接续

[#544](https://github.com/auguspp/decision-kernel/pull/544)已经完成资源去重与固定Suken旧启动器退役：同PR并发、pip下载缓存、四个action-history输入准备共享；原请求、失败/成果、共享runtime与行为测试保留。30个现役workflow文件不是156个历史Actions登记。真实基线和慢样本见 [首切片回执](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5812515561)，没有显著端到端提速结论。

本轮分流已由 [#545](https://github.com/auguspp/decision-kernel/pull/545) 正常合并。工程验收、实际文字路径与正常发布读回分别记录在该PR和#354最新回执；不得用一类通过替代另一类。后续纯文字改动按上方范围执行，不再人为要求全库pytest；混合或未知变更仍full。

下一重点仍是用途registry/计算档案各自的消费者验证、代码同树PR/main双份全量、已消费旧编排义务及publisher/intake空转。它们没有在本次被自动退役；不为快通道再造通用selector、scheduler或新状态中心。

Reuse Decision: REUSE + THIN_ADAPTER。使用原Git/gh/Actions与stdlib；[Git raw/-z](https://git-scm.com/docs/git-diff)、[Actions条件和过滤限制](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)、实读[dorny/paths-filter@v3 git实现](https://github.com/dorny/paths-filter/blob/v3/src/git.ts)提供差异与失败模式经验，不新增Node Action/依赖/深历史扫描。完整审计沿用[初审原件](https://github.com/auguspp/decision-kernel/blob/b3a3546560010f3683b02ec931f372ab714f2687/docs/CI-MAINLINE.md)和#354。

回滚走普通PR，不直接写main/force-push，不删除历史证据/运行记录，不动生产日程。无论路径如何，CI成功都不是经济真理或投资授权。
