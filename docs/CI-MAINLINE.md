# CI mainline / CI 施工接续入口

Updated: 2026-09-24. Engineering only; Investment Authority = NONE.

## 当前目标与接手

Human已授权本会话接手CI优化；接手[5816705697](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5816705697)，#553收口[5817104078](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5817104078)，本轮继续与Reuse Check[5817228684](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5817228684)。目标是缩短正常施工的同步等待、减少无效执行和永久维护义务，不是保持测试数只增不减。

本轮实施前基线main `3306e75cb1dcc200abf8a14938d50011acf0e271`：#553全量6126项、pytest336.23秒/job379秒；main原精确复用后job48秒。日历辅助函数3次准备减1次没有证明全量提速，不能继续把小型去重当等待问题的主要终点。原入口全文及旧方案留在该精确Git前驱。实际新PR/main/发布结果读#354与对应PR，不在本文预填通过或性能。

产品范围仍按AGENTS/最新#297；不扩大来源、模型、生产日程、状态中心或投资权限。CI不认证经济真理、研究质量或Human接受。

## 施工纪律：等待只锁依赖边界

CI queued/in_progress只阻塞依赖其结果的合并、采用和后继操作，不冻结已授权的独立工作。可以读调用关系、检查测试/fixture、准备隔离patch、做不依赖当前结果的验证；不得修改正在验收的head而沿用旧结果。尽量完成一个有意义的切片再提交，不为每个机械文件修改启动一次full。

多轮工程编辑优先保持同一Draft PR：先得到反馈继续编辑，准备审查合并时转Ready。不要为逃避已有失败把Ready转Draft并宣称通过，也不要反复切换阶段制造运行。已经完整准备好的小切片可直接开正式PR。不要转换别人的PR或Research草稿。

不要短间隔轮询、扩展无关审计或制造假忙。真正没有独立工作时，说明已完成项、待验精确run/head与停止边界；不承诺本轮结束后继续。不自动授权叠PR、取消运行、Re-run或生产操作。

写入先发现当前实际工具、读目标并检查本次授权，再执行必要动作。工具存在不等于远端必有权限；未发现/未调用不等于无权限。按当前会话和file/comment/PR/dispatch分别区分不可用、需审批、明确拒绝、参数/SHA冲突、网络失败、不确定和成功。不要探针写入；用已授权正常写入与读回验证。明确安全/权限拒绝停止对应动作，不换工具/包装绕过；不确定先对账，不重复写。只有确实缺能力或需Human批准才要求转运。

## 生命周期：流程退役必须同时处置专属CI

**CI保护当前合同与必要历史读回，不永久保护每一代施工步骤。** 每次ADD/CHANGE/CONSOLIDATE/RETIRE在同一PR按能力/合同组检查runtime/workflow、专属tests/fixtures、部署断言和CI例外、共享守卫及历史reader。复用现有PR说明，不新增registry或逐测试元数据平台。

- 专属执行对象退役：对应测试、专属fixture和CI例外同时退役；未处置则退役未完成。
- 共享行为有现役调用：保留或合并保护，不随旧入口整组删除。
- 旧成果仍须读取：保留最小必要格式/身份/重建兼容；只有reader足以保护实际责任时才退役旧executor模拟。

新增测试说明当前合同、覆盖缺口和退出条件；不要求一加一删。真实历史事故是风险证据，不因年代或名称含replay/tamper就删除。UNKNOWN继续待审，不能按“每条链三项”等配额砍关键失败覆盖。继续用现有collection/JUnit/durations观察数量、模块、job墙钟和累计case时间；累计时间不等于并行墙钟。

## 验证按阶段分开，正式合并仍有完整证据

保留唯一workflow `kernel-tests` / job `test`，不新增第二工作流、触发服务或测试结果缓存，不用顶层paths-ignore。pull_request显式订阅opened、synchronize、reopened、ready_for_review和converted_to_draft；push仍只main。GitHub默认不包含Ready事件，所以不能省略该订阅。

### 已有文字路径

仅README/AGENTS、本文、RESEARCH-ENTRY、research-outcome-contract-v1及新增docs/readings/**/*.md。完整Git base→head raw/NUL差异；普通非执行文件新增/修改；精确base须有本仓库main/push/attempt1成功CI，较新失败/进行中/未知不能由旧绿灯覆盖。混合、删除、改名、特殊模式及未审路径不作为文字免检。

不安装工程环境、不全库collection或pytest；实际stdlib回归与UTF-8/非空/NUL/冲突检查，明确NOT_RUN_CONTENT_ONLY。不认证链接、计算或研究真理，消费者改变须重审范围。文字失败或基线缺口不会通过Draft降级成反馈成功。

### 草稿反馈：不是合并门禁、不是受影响测试全集

仅真实pull_request事件、draft严格为布尔true、本仓库head/base、base为main、head/base SHA与原完整Git差异相符时适用。Ready/正式PR/main、缺失或不匹配元数据、fork、空/未读差异、删除/改名/特殊模式仍按full处理。任何.github/、tests/test_ci_*、pyproject/依赖或全局pytest配置变化仍full；首次部署不能自证免检。

复用四个已有main smoke文件（CI实际失败/复用、external Research身份和准入）加上直接变动的现存test_*.py；对改变的src/**/*.py做非执行语法检查。使用pytest原生文件参数，不建依赖图、不猜传递影响。改动一个慢测试文件仍可能慢；此反馈也可能漏掉未选测试中的失败，明确没有覆盖非Python资源或间接依赖的全部影响。

产物scope=draft_feedback、FULL_SUITE=NOT_RUN_DRAFT_FEEDBACK，写draft-feedback.json/xml/log，不生成当前完整collection.txt/pytest.xml，merge_eligible=false。失败真实传播，不补跑/重试换绿。当前完整证据reader严格要求scope=full，因此草稿成功不能被主干复用当作完整PR成功。

### 正式工程PR

**转Ready必须触发新的当前head完整验证，即使SHA没有变化。** 非草稿opened/synchronize/reopened照常full。src/tests/fixtures/workflow/依赖/registry/JSON/计算/旧研究原件及未审路径，不按扩展名免检；full-research-method-v3.md仍有消费者。获准退役可以减少当前集合，不等于旧测试永久保留。

合并前确认当前PR不是draft、精确head及本次正式验证的实际scope、全量collection/JUnit、最新run和原审查。不能只看“有一个绿色test”，不能把草稿反馈、旧head或较早成功当放行。转换Ready不授予产品/Research/来源或投资权限。本仓库现有合并程序仍由这些证据约束，本轮不改branch protection/ruleset。

### 干净main merge

先真实安装，再限定单一两父merge、push.before=第一父、merge tree=本次owned PR head。核最新PR CI/attempt1/success、精确commit关联已合并PR、唯一未过期artifact的SHA256/CRC、完整collection=JUnit逐项身份、无失败/跳过、实际Python/runner镜像/架构/安装包。ZIP只作数据，不执行；读后再核最新PR。草稿、文字和继承结果均不是PR full证明。

CI工作流、分流/复用器及其测试、pyproject变化时main仍full。squash/rebase/多提交push、不同tree、脏tracked文件、环境变化/缺失、旧格式/坏产物或不确定均full。复用时main另跑真实smoke，失败即失败，不补跑full换绿。标记scope=merge_reuse、FULL_SUITE=REUSED_NOT_RERUN及原PR/run/artifact/tree/数量；当前执行单存main-smoke.xml，不伪造本SHA全量JUnit。

## 完整执行、诊断与权限

```sh
python -m pip install -e '.[dev]'
python -m pytest -q -n 4 --dist=loadfile --max-worker-restart=0 \
  -o faulthandler_timeout=60 -o faulthandler_exit_on_timeout=true \
  --durations=100 --durations-min=1.0 --junitxml=pytest.xml
```

完整Test shell不变，本地默认串行；无skip/xfail/continue-on-error、worker重启或为变绿重跑。pipefail传播失败，60秒仅作stall诊断。缓存仅下载，每次真实安装。base-only isolated/no-cache安装和真实pass/fail/worker-crash继续。PIT、来源/证券身份、权限、create-only/写入不确定、必要历史读回、有效Odds计算继续覆盖。

CI仅contents/actions/pull-requests read，不用业务secrets或持久checkout credentials。GH_TOKEN仅进只读基线/PR核验，不进测试/内容。commits/{merge}/pulls空/歧义/满页/不匹配回full，不猜PR号。官方Action保持原固定commit；仅同PR运行可相互替换，main每run独立。

kernel-ci-<run>-<attempt> diagnostics继续always/30天，身份/环境/执行范围分开记录。早期失败无完整产物仍失败；success只说明该范围验证成功，不证明所有SHA全量重测、来源/模型接受或研究质量。

## Reuse选择、成本与退出

[GitHub原生PR事件](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request)和[Draft/Ready阶段](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/changing-the-stage-of-a-pull-request)已提供不可合并草稿与正式验证的分界；当前只加薄事件/反馈适配，复用Git差异、pytest显式路径与原full证据reader。沿用#354既有fkirc/path-filter审查，不再造一般选择框架。Reuse Decision: REUSE。

[testmon正式合同](https://www.testmon.org/)要求先建跟踪库，且不自动跟踪静态资产/外部服务；[Pants增量目标](https://www.pantsbuild.org/stable/docs/using-pants/advanced-target-selection)需要相应依赖建模。这两者不是永久否决，但本仓库JSON/YAML/PDF/子进程/动态导入及跟踪开销、漏选边界未完成实证，不能直接接管正式放行。数次全绿不是无漏检证明；不新增外部云服务或上传代码/覆盖数据。

本轮减少的是草稿编辑期间重复full的次数，不是让最终工程PR免full，也不声称整套CI v2重建完成。反馈路径复用四个核心文件，新增回归本身也有成本；使用真实草稿反馈耗时、Ready全量、一次切片实际同步等待与维护差异验收，不用测试数量代替收益。

若Draft反馈不被实际使用、持续接近全量成本，或后续更合适方案替代：同一PR退出draft范围分支、对应步骤、事件例外及专属测试，保留原正式full/文字/main复用和历史记录。禁止形成永久双轨CI。

## 已完成与历史定位

| 切片 | 已落实与历史定位 |
|---|---|
| #544–546 | PR旧运行/pip/Stock输入去重，Suken launcher退役；文字PR/main job7/11秒。原31-workflow审计在b3a3546560010f3683b02ec931f372ab714f2687的本文。 |
| #547–550 | 精确PR→main复用，#548关联失败与镜像差异保留、#549薄修；#550 PR310/main54秒，非同机固定收益。旧Sector/intake启动器退役，28个workflow；单改旧intake请求不再搬材料，恢复须授权。 |
| #551 | 6225→6137、净88测试/1167行；旧Sector脚本在fdb9104c1722fe250f44742e5129665b36c2889b。原PDF eval/verifier字节保留，metadata/Woton共享守卫保留；run34566950303失败且已消耗，不重跑。 |
| #552 | 固定Suken executor退出共享模块，6137→6125/净371行；shared model/SDK/Retainer继续，原请求/失败不变。旧代码在026a7195f4d0ad3ccac121c9de92fbe18e5bd4b5；PR204.28秒、main复用40秒，后者不归因删测试。 |
| #553 | 当前前驱3306e75；日历3次plan减1次，6126测试。三项协作纪律已落地；PR336.23秒/main复用48秒，未证明全量提速。 |

#354保持OPEN。Stock/PDF重复准备、旧API固定部署、publisher重建及registry/计算按消费者验证仍待审。非默认API不等于已获准整条关闭；现役Stock/Question共享宿主不整组退役。回滚走正常PR，不直写main/force-push、不删历史证据/run、不改生产日程。旧#297被拦截通知不重试。
