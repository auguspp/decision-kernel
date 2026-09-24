# CI mainline / CI 施工接续入口

Updated: 2026-09-24. Engineering only; Investment Authority = NONE.

## 当前职责

Human 已授权按新架构拆、删、优化 CI；[当前同树减负范围](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5813511726)。产品仍按 AGENTS / 最新 #297，不新增模型调用、生产日程、治理平台或状态中心。

**CI 保护当前有效行为与历史兼容性，不永久保护每一代施工步骤。** 保留历史不等于永远重跑全部历史脚手架。改动、PR、CI、合并、发布、研究接受是不同事实；实际完成状态读 #354 最新回执。

## 一个稳定检查，按实际范围验证

`kernel-tests` / `test` 名称不变，PR与main都产生实际检查，不使用顶层 paths-ignore。

**文字路径（#545/#546）**：仅根 README/AGENTS、本文、RESEARCH-ENTRY、research-outcome-contract-v1，以及新增 `docs/readings/**/*.md`。普通非执行文件的新增/修改才可进入；完整 Git base→head raw/NUL 差异，不靠最后一个commit或平台300文件子集。要求精确base存在本仓库main/push/attempt1成功CI，不能藏掉同SHA更新的失败/进行中记录。未知、混合、删除、改名、特殊mode回full。文字路径不安装工程环境、不收集全库、不执行全量pytest；真实stdlib回归与提交文字UTF-8/非空/NUL/冲突检查，明确 `NOT_RUN_CONTENT_ONLY`。不认证链接、事实、计算、研究质量或Human接受。新增代码消费者依赖这些文字入口时须同步审查范围。

**工程 PR**：始终保留完整验证。src、tests/fixtures、workflow、依赖、registry/JSON、研究计算、既有研究原件修改及未审查路径，不因扩展名像文档就免检。`full-research-method-v3.md`仍有真实回放消费者。

**干净主干合并**：重新安装真实工程环境后，只有一个两父merge且push的before精确等于第一父、merge tree精确等于本次owned PR head，才尝试复用该PR全量。核对实际最新PR CI的身份/attempt1/success、精确merge commit原生关联的本次已合并PR、唯一未过期artifact的SHA256/CRC、完整collection与JUnit逐项一致/无失败或跳过、精确Python/runner镜像与架构/实际安装包集合。参数名转换复用当前pytest JUnit writer，不把参数里的`::`当层级。下载产物只作数据，不解包执行。读后再核最新PR，较新失败或读取不确定回full。

不接受文字成功或其他复用结果作为PR full证明；不扫历史找一个绿灯。CI工作流、分流/复用器及其测试、pyproject本次改变时主干必须full，所以此机制首次部署也不得自证免检。squash、rebase、多commit push、不同merge tree、脏tracked文件、环境改变/缺失、旧artifact格式/损坏均回full。当前仅支持证据最直接的普通merge，不伪装覆盖所有合并方式。

复用成功的main仍运行真实CI失败传播与Research身份/准入小型回归；任何失败直接失败，不再补跑全量换绿。产物明确 `scope=merge_reuse` / `FULL_SUITE=REUSED_NOT_RERUN`，保留精确PR/run/artifact/tree/测试数量，当前执行结果为独立 `main-smoke.xml`，不伪造当前全量JUnit。主干安装兼容性仍实际验证，PR的base-only测试仍保留；不是当前main再次运行每项测试的声明。

## 完整路径与权限不变

```sh
python -m pip install -e '.[dev]'
python -m pytest -q -n 4 --dist=loadfile --max-worker-restart=0 \
  -o faulthandler_timeout=60 -o faulthandler_exit_on_timeout=true \
  --durations=100 --durations-min=1.0 --junitxml=pytest.xml
```

原full Test shell不变，本地默认串行。无skip/xfail/continue-on-error或worker重启；pipefail保证失败，60秒只作CI stall诊断。完整路径真实安装，即使pip缓存命中；base-only isolated/no-cache安装及真实pass/fail/worker-crash回归保留。PIT、身份/来源、权限、create-only/不确定写入、旧格式读回、有效Odds计算继续覆盖。

CI仅contents/actions/pull-requests read，无业务secrets，不保留checkout credentials；GH_TOKEN只进入只读基线/PR核验步骤，不进入测试或内容。run.pull_requests合并后可能为空，改用commits/{merge}/pulls的精确关联并读回PR；关联列表为空、歧义、达到单页上限或不匹配仍full，不猜PR号。固定原已验收三个官方Action的commit，避免浮动Action版本被当相同执行环境。原并发不变：同PR过期head可替换，main每run独立。

保留原 `kernel-ci-<run>-<attempt>` diagnostics，always/30天，当前身份、环境和实际范围分开。早期失败可能没有完整产物，仍是失败。发布器/源准入收到的成功含义为“本次范围验证成功”：full、可信main基线上的文字检查，或精确PR full加实际main检查；不能声称后两者是本SHA全量重测。生产触发/保存产物验证/显式source-model权限均不改变。

## 进度、复用、回滚

[#544](https://github.com/auguspp/decision-kernel/pull/544)已完成PR并发/pip缓存/四个Stock输入准备去重与固定Suken旧启动器退役；原请求/失败/成果/共享runtime保留。[#545](https://github.com/auguspp/decision-kernel/pull/545)/[#546](https://github.com/auguspp/decision-kernel/pull/546)真实文字PR/main为7/11秒job，不含排队/发布，也不是完整引擎提速。更早[31-workflow初审](https://github.com/auguspp/decision-kernel/blob/b3a3546560010f3683b02ec931f372ab714f2687/docs/CI-MAINLINE.md)与失败/慢样本继续保留。

本次同树路径已由[#547](https://github.com/auguspp/decision-kernel/pull/547)合并；真实适用范围CI和发布验收读该PR及#354最新回执，不预填后继复用成功。#548首次实际main回退PR_MERGE_ASSOCIATION，另有镜像差异；这暴露了对run内PR字段的错误依赖，关联读取修正不放松环境门禁，也不重跑原样本。用途registry/计算专门消费者、其他旧执行义务、publisher/intake空转仍待后续处理。

固定旧 Sector recovery 启动器按[#354/5813736504](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5813736504)退役：删除 `sector-recovery-once.yml` 及其专属启动shell测试，收紧pacing的现役workflow检查。9月11日run34566950303是已消费且失败的历史尝试，不称恢复成功；原tag、请求、失败run、capture-sector-recovery.py与全部回放/时钟/数据校验保留。正常Sector日程/128请求预算/20秒节奏不变。原30个workflow文件变29个，不删除Actions历史记录。


Reuse Decision: REUSE + THIN_ADAPTER。原生Git/gh/Actions/pytest/stdlib；[官方artifact](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts)、[Git diff](https://git-scm.com/docs/git-diff)及已实读[fkirc@v5.3.2同树实现](https://github.com/fkirc/skip-duplicate-actions/blob/v5.3.2/src/main.ts)。其直接按旧tree/success跳过不含本次PR/full/env资格，因此只复用同树思想，不接入通用扫描/取消/skip策略。无新依赖/workflow/service；详细比选在原#354。

回滚走普通PR，不直写main/force-push，不删除历史证据/run，不动生产日程。写入不确定先对账；CI成功不是经济真理或投资授权。
