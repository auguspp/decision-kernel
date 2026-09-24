# CI mainline / CI 施工接续入口

Updated: 2026-09-25. Engineering only; Investment Authority = NONE.

## 当前方向：先交付最小可运行 v2，不继续扩建 legacy

Human已同意先重建当前验证责任，再用成熟组件优化执行，并指示开工。当前授权/Reuse Check见[#354/5818204474](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5818204474)。前驱完整入口在`526ca0dc2827d6783b255019572614b35ea681f5`；成熟轮子审计见[#354/5817811217](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5817811217)。旧说明、失败、源件、成果与Human原话留在原Git/Issue，不重写历史。

先决定今天要保护什么，再决定怎样跑快。复用有效旧测试，不从零重写好测试；也不默认6133项都有永久进入v2的权利。产品范围/能力退役仍按AGENTS和最新#297，不为CI擅自关闭业务能力。CI不认证研究质量、经济真理、实际跨会话恢复或Human接受。

本切片实施前基线：#554 PR `36022927971`，6133+80subtests，337.61秒pytest/383秒job；同tree main `36023936003`，245.09秒/287秒；均pip缓存命中。不同运行的差异不是优化因果证据。最新结果看#354/精确PR产物，本文不预填PASS或节省秒数。

## 当前合同图与首个可运行组

| 当前责任 | 第一组覆盖与原测试复用 | 尚未迁移的责任 |
|---|---|---|
| 未完成研究可保存、追加和恢复，不自动commit或续跑 | `test_research_progress.py` | 真实托管会话交付/恢复不是CI能代证 |
| Research-only冻结与读回；缺概率/估值/模型风险不伪造成Odds或接受 | `test_research_commit_only.py`、`test_research_only_commit_v2.py`、`test_research_model_risk_unknown_v2.py`、`test_generic_research_commit.py` | 其他Odds/Market/Decision合同仍由legacy保护 |
| 按固定读取包与显式记录恢复原始档案；身份/字节/完整性/权限不漂移 | `test_research_archive.py`、`test_research_archive_index.py` | 其余publisher/来源/研究准入与传递消费仍待审 |
| CI实际执行集合完整且失败正确传播 | 复用原collection/JUnit校验函数；正式结果资格仍保留 | 后续分片的全组并集/互斥与最终聚合未实施 |

七个研究模块在#554实际collection中共240项。`.github/ci-v2-research.txt`是pytest原生参数文件，不是自建测试registry、动态selector或性能配额。只列当前模块；新增组先说明当前合同和覆盖缺口，不因名称/年代含replay、repair或tamper删除。

## v2执行与证据边界

原`ci.yml`只新增本地`workflow_call`调用；主体在`ci-contracts-v2.yml`，与legacy job并行，不等待legacy完成才反馈。它没有独立schedule/dispatch或发布入口，不使用业务secrets，不继承写入权限。原“只能一个workflow文件”是#554布局选择，不是永久Kernel语义。

复用现有内容资格判定；可信纯文字变更由原content gate负责，v2明确NOT_RUN_CONTENT_ONLY，不安装工程依赖。其他范围先运行本组，不声称已覆盖全部受影响测试。环境使用现有`feeds`加仅含既有pytest的`ci-contracts` extra；不安装整个dev，不引入新发行包，不提前迁移uv。

本地/CI同一命令：

```sh
python -m pip install -e '.[ci-contracts,feeds]'
python -m pytest -q @.github/ci-v2-research.txt
```

CI另保存实际环境、精确代码/run/attempt、独立collection、JUnit与执行日志。`passed_test_set`只核本次声明集合完整且无failure/error/skip，复用原full reader的同一逻辑；它不证明scope、来源或权限。v2产物命名`kernel-ci-v2-<run>-<attempt>`，结果明确`research-continuity-v2 / NOT_RUN_DOMAIN_ONLY / merge_eligible=false`，不生成伪全仓collection/pytest.xml。原full reader仍必须先验证PR/full/环境/ZIP资格，不能拿domain成功代替。

本轮是第一组迁移实证，**并行重复240项是临时成本，不是已删除5893项**。全库legacy暂时继续，不skip/ignore未裁定风险。首组实证后，下一切片须根据真实结果裁定接替对应反馈/正式合同范围，或退回/退出；不得以“继续观察”无限增加双轨组。迁移正式集合时，要使全部必要合同由明确执行组覆盖，不要求旧布局/旧命令字符串永远不变。

## 正式放行暂不改变

- 保留`kernel-tests` / `test`及原PR事件/同PR过期head替换；独立main run不互相取消。v2单组绿灯不授权merge；合并仍检查精确head的整个最新workflow与原正式完整产物，不能只看一个绿色job。
- 可信文字路径仍仅原allowlist及新增研究Markdown；精确base须为本仓库最新成功main/push/attempt1。完整base→head raw/NUL diff、status/mode、旧原件编辑处置不变；缺证回full，不按扩展名放行。
- 原Draft反馈暂保留，明确非全部影响集；Ready即使同SHA仍新跑正式完整验证。CI/依赖/全局配置/未知/删除/特殊模式仍full。不要转换别人的Research草稿，不因失败把Ready降为Draft求绿。
- 主干复用仍先真实安装，限定干净两父merge及精确owned PR同tree；核最新attempt1/full/非继承结果、唯一有效ZIP的大小/SHA256/CRC、collection=JUnit与实际Python/镜像/架构/安装包，读后再核最新PR。CI策略改变、环境缺失/变化或不确定回full；main实际smoke失败不能重跑换绿。
- 本组workflow/参数文件/专属CI测试加入原POLICY失效边界，首次部署及后续策略改动不能自证免检。正常publisher只消费原合格main结果；CI成功、发布、研究接受和投资决定分别验收。

原完整执行仍为`python -m pytest -q -n 4 --dist=loadfile --max-worker-restart=0`，带原60秒stall诊断、durations和JUnit。原Test shell、失败/worker-crash传播、本地默认串行及独立base-only冷安装继续；没有新skip/xfail、continue-on-error或结果缓存。

## 生命周期与孤儿检查

每次ADD/CHANGE/CONSOLIDATE/RETIRE在同PR按能力组检查runtime/workflow、专属tests/fixtures、部署断言/CI例外、缓存/参数文件引用、共享守卫及历史reader。专属执行对象退役而CI未处置，退役未完成；共享现役保护保留，历史责任能由reader承担时不永久重演旧executor。UNKNOWN保持待审，不用“一加一删”或每链固定测试数配额。

结构性孤儿先用现有引用搜索、pytest原生收集及成熟静态工具发现。参数文件引用已删模块应失败，不回退到更小集合；语义孤儿由能力生命周期审查裁定，不能仅凭零引用自动删除手动入口或历史reader。v2的workflow调用、参数文件、extra和专属wiring测试同生命周期；被替换/退出时同步删除，共享`passed_test_set`仍有full消费者则保留。不新建扫描服务或逐测试元数据平台。

## 成熟组件与后继

Reuse First三层已查：内部七组测试/原scope/full reader；[pytest原生参数文件](https://pytest.org/en/stable/how-to/usage.html)及[GitHub本地可复用工作流](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)；外部七轮子完整审计沿用5817811217。Reuse Decision: REUSE / 既有完整性原语薄拆分。

`pytest-split`是后续执行布局首选实验，待代表性v2集合确定后比较同集合1×4、4×1、2×4、4×2；不自写分片器。uv只对照安装层，testmon仅shadow；dorny不代替可信baseline/mode，fkirc同树绿灯不代替full资格。actionlint/zizmor用于普通静态能力，先实扫并量测；本PR不声称已部署这些组件。缩减验证集合与同集合执行提速分别记账。

至少记录tests/subtests、安装/收集/执行墙钟、job与事件到完成、runner数量、sum(job秒)/60、cache命中、PR/main及新增维护量。少量样本只报告实值和范围，不把累计testcase当wall/CPU，不拿快旧主干样本冒充新收益。

## 协作与历史接点

CI只阻塞依赖其结果的合并/采用边界；独立授权工作继续，不短轮询、不假忙、不为每个机械文件改动跑full，无独立工作时留精确run/head，不承诺后台。工具先实际发现与核本次授权，区分不可用/需批准/明确拒绝/冲突/不确定/成功；未发现不等于无权限，明确拒绝不绕过，不确定先读回，不做探针写入。

#544–550资源/文字分流/精确复用、#551–552净退役100测试/1538行、#553日历准备去重及纪律、#554草稿分层均在前驱入口和原PR留存。#554主干全量已核成功，但其正常publisher/完整读回及真实Draft收益仍须按实际回执分别确认。回滚走正常PR，不直写main/force-push、不删证据/run、不改生产日程；旧#297拦截不重试。#354保持OPEN；v2全域重建未完成。
