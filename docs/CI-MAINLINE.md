# CI mainline / CI 施工接续入口

Updated: 2026-09-24. Engineering only; Investment Authority = NONE.

## 当前目标与接手

Human已授权本会话接手CI优化，范围与Reuse Check见[#354/5816705697](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5816705697)。以缩短正常施工的同步等待、减少无效执行和永久维护义务为目标，不以测试数量只增不减为目标。产品范围仍按AGENTS/最新#297；不扩大来源、模型、生产日程或状态中心。

当前基线为#552后的main `b4fe1953fe301e5ffd09df57e98f29b7dd5d9dae`：6125项，不是旧6137。最新适用范围CI/发布事实读#354及精确PR/run；本文不预填下一PR的通过结果。旧入口全文保存在该精确Git前驱，旧请求、来源、成果、失败、消费记录与Human原话不重写。

## 施工纪律：等待只锁依赖边界

CI `queued/in_progress`只阻塞依赖其结果的合并、采用和后继操作，不冻结当前授权内的独立工作。可继续读调用关系、检查测试/fixture、准备隔离patch、做不依赖该结果的本地验证；不得修改正在验收的head而沿用旧结果。尽量完成一个有意义的切片再提交PR，不为每个机械文件改动启动一次全量。

不要反复短间隔轮询CI、为显得忙碌扩展无关审计，或把无意义只读工作当吞吐收益。真正没有独立工作时，交代已完成事项、待验精确run/head和停止边界；不承诺本轮结束后继续工作。本规则不降低合并门禁，也不自动授权叠PR、取消运行、Re-run或生产操作。

写入先发现当前实际工具、读目标并检查本次授权，然后执行所需真实动作。工具已列出不等于远端必有权限；未发现/未调用也不等于无权限。分别报告工具不可用、需审批、明确拒绝、参数或SHA/资源冲突、网络失败、结果不确定及成功。具体能力按file/comment/PR/dispatch和当前会话分别判断，不沿用另一个对话框的印象。不要制造探针写入验证权限；已授权正常写入足够。明确安全/权限拒绝停止对应动作，不换工具/包装绕过；结果不确定先只读对账，禁止重复写入。只有真实缺少所需能力或需Human批准时才要求转运。

## 生命周期：流程退役必须同时处置专属CI

**CI保护当前合同与必要历史读回，不永久保护每一代施工步骤。** 对每次ADD/CHANGE/CONSOLIDATE/RETIRE，在同一PR按能力或契约组检查runtime/workflow、专属tests/fixtures、部署断言和CI例外、共享守卫及历史reader。复用现有PR说明，不新增registry或逐条测试元数据平台。

- 专属执行对象已退役：对应测试、专属fixture和CI例外同时退役；未处置则退役尚未完成。
- 共享行为仍有现役调用：保留或合并对应保护，不能随旧入口整组删除。
- 旧成果仍须读取：保留最小必要格式/身份/重建兼容验证；仅在reader足以保护实际兼容责任时，才退役旧executor模拟。

新增测试说明其当前合同、现有覆盖缺口及随何种能力变化可退役；不要求机械一加一删。真实历史事故是风险证据，不因年代或名字含replay/tamper就删除。UNKNOWN保持待审，不自动判定无用。任何integration数量仅是按风险设计的起点，不能用“每条链三项”的配额取代关键失败覆盖。

继续使用原collection/JUnit/durations观察数量、模块、job墙钟和累计testcase时间。累计时间不等于并行墙钟；少跑准备不等于少测断言。明显增长要解释当前收益，异常增长提示审查，不为变绿跳过测试。

## 当前放行规则不变：一个稳定检查

`kernel-tests` / `test`名称不变，PR/main均产生实际检查，不用顶层paths-ignore。

**文字路径（#545/#546）**：仅根README/AGENTS、本文、RESEARCH-ENTRY、research-outcome-contract-v1及新增`docs/readings/**/*.md`。完整Git base→head raw/NUL差异，普通非执行文件新增/修改；精确base必须有本仓库main/push/attempt1成功CI，较新失败/进行中/未知不能由旧绿灯覆盖。混合、删除、改名、特殊mode及未知回full。无工程安装/全库collection/全量pytest，实际stdlib回归和UTF-8/非空/NUL/冲突检查，明确`NOT_RUN_CONTENT_ONLY`。不认证链接、计算、研究真理或Human接受；消费者改变时重新审范围。

**工程PR**：执行当前有效完整集合。src/tests/fixtures/workflow/依赖/registry/JSON/计算/既有研究原件及未审路径，不按扩展名免检；`full-research-method-v3.md`仍有消费者。完整集合可以随获准退役减少，不等于旧测试永久存在。

**干净main merge**：先真实安装，再限定单一两父merge、push.before=第一父、merge tree=本次owned PR head。核最新PR CI/attempt1/success、精确commit原生关联的已合并PR、唯一未过期artifact及SHA256/CRC、完整collection=JUnit逐项身份、无失败/跳过、实际Python/runner镜像/架构/安装包。参数名转换复用pytest JUnit writer；ZIP只作数据，不执行。读后再查最新PR，较新失败或不确定回full。

文字成功/其他继承结果不能当PR full证明。CI工作流、分流/复用器及其测试、pyproject变更时main必须full；首次部署不能自证免检。squash/rebase/多提交push、不同tree、脏tracked文件、环境变化/缺失、旧格式/坏产物均回full。复用时main另跑真实smoke；smoke失败直接失败，不补跑full换绿。明确`scope=merge_reuse`、`FULL_SUITE=REUSED_NOT_RERUN`，绑定原PR/run/artifact/tree/数量，当前执行单存`main-smoke.xml`，不伪造本SHA全量JUnit。

## 完整执行、诊断与权限

```sh
python -m pip install -e '.[dev]'
python -m pytest -q -n 4 --dist=loadfile --max-worker-restart=0 \
  -o faulthandler_timeout=60 -o faulthandler_exit_on_timeout=true \
  --durations=100 --durations-min=1.0 --junitxml=pytest.xml
```

本地默认串行；无skip/xfail/continue-on-error、worker重启或为变绿重跑。pipefail传播失败；60秒仅作CI stall诊断。缓存只复用下载，每次真实安装。base-only isolated/no-cache安装及真实pass/fail/worker-crash回归继续。PIT、来源/证券身份、权限、create-only/写入不确定、现役历史读回及有效Odds计算继续覆盖。

CI仅contents/actions/pull-requests read，不用业务secrets，不保留checkout credentials。GH_TOKEN仅给只读基线/PR核验，不进测试/内容。`commits/{merge}/pulls`而非可能清空的run.pull_requests；空/歧义/单页满/不匹配回full，不猜PR号。三个官方Action固定commit；仅同PR旧head可被替换，main每run独立。

原`kernel-ci-<run>-<attempt>` diagnostics继续always/30天。身份、环境、执行范围分开记录；早期失败缺完整产物仍是失败。下游success表示本次适用范围验证成功，不等于每个SHA全量重测、来源/模型接受或研究质量。

## Reuse First与当前切片

不先建设第二套CI或自行维护复杂选择器。[testmon正式说明](https://www.testmon.org/)明确不跟踪静态文件和外部服务；本仓库有JSON/YAML/PDF/子进程义务，不能直接把Python覆盖率当完整影响图。testmon可作后续有界观察候选，但首轮追踪成本、真实失败漏选、静态资产/环境处理与退出条件未验前，不接管放行。不能以若干次全绿证明无漏检。

优先复用[pytest现有fixture生命周期](https://docs.pytest.org/en/stable/how-to/fixtures.html)和原helper参数传递，消除重复准备；[xdist正式调度说明](https://pytest-xdist.readthedocs.io/en/stable/distribution.html)已提供loadfile/worksteal。当前保留loadfile以维持同文件fixture复用；是否换调度以真实测量为准，不先加Pants/外部服务或自建证明框架。Reuse Decision: REUSE。

本切片只让`prepared`/`contract_provider`接收调用者观察时钟，日历`inputs`从三次plan构造减为一次；原provider响应时钟仍保留、原builder/observer/capture/replayer照常执行。每次plan/关联副本/provider状态独立，不缓存被测plan。旧业务断言不变；一项新回归检查调用次数、时钟传递与响应隔离。预期6125+1，实际数量/用时以PR artifact为准，不预填通过或端到端提速。

CI v2若继续评估，应从当前Kernel一致性/权限、现役适配器、留存/读取/发布和必要历史兼容推导合同，复用已有有效测试；不以旧数量等价为目标，也不跳过尚未处置的现役风险。先证明成本低于继续清理，再讨论有退出期限的旁路；本切片不改变required checks。

## 已完成与历史定位

| 切片 | 已落实范围与原件 |
|---|---|
| #544–546 | PR过期运行/pip下载/Stock共享输入去重，固定Suken launcher退出；文字PR/main真实job 7/11秒。历史[31-workflow审计](https://github.com/auguspp/decision-kernel/blob/b3a3546560010f3683b02ec931f372ab714f2687/docs/CI-MAINLINE.md)。 |
| #547–550 | 精确PR→main复用；#548关联失败与另有镜像差异保留，#549薄修。#550首个真实命中：PR job310秒、main job54秒，不含排队/发布，非同机固定收益。旧Sector及intake launcher退出，现有workflow 28；单改旧intake请求不再自动搬材料，无替代触发，恢复须授权。 |
| #551 | [5815714318](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5815714318)：6225→6137、净减88项/1167行。Sector脚本/32专属模拟及三个PDF探索模式/57项退出，新增1边界测试。原PDF eval/verifier不变，metadata/Woton共享守卫保留；Sector旧代码在`fdb9104c1722fe250f44742e5129665b36c2889b`。run34566950303失败且已消耗，不授权重跑。 |
| #552 | [5816589940](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5816589940)：固定Suken executor退出共享模块，13旧测试换1真实CLI检查，6137→6125、净减371行；shared model/SDK/Retainer save/native/local继续，原请求/失败不变。旧executor在`026a7195f4d0ad3ccac121c9de92fbe18e5bd4b5`。最终PR pytest204.28秒/job250秒，main复用job40秒、正常发布读回；40秒不归因删12测试。 |

#354继续OPEN。剩余Stock/PDF重复准备、旧API固定部署义务、publisher重建、registry/计算按消费者验证仍待审。非默认API不等于全部获准关闭；现役Stock/Question共享宿主不整组退役。回滚走正常PR，不直写main/force-push、不删原证据/run，不改生产日程。CI、发布、Research质量、Human接受及投资决定分别验收。
