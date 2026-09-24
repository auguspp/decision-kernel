# CI mainline / CI 施工接续入口

Updated: 2026-09-24. Engineering only; Investment Authority = NONE.

## 当前职责与审查标准

Human 已授权拆、删、优化CI，并明确要求审查测试本身是否仍有用；当前测试减负见[#354/5815419873](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5815419873)。产品仍按AGENTS/最新#297。不增加来源/模型调用、日程或状态中心。

**CI保护当前有效行为与必要的历史读回，不永久保护每一代施工步骤。保留历史不等于保留全部历史执行器。** 测试数量不设只增不减的目标，也不按“过半过时”设删除配额。按实际用途区分：现役行为、历史格式/身份兼容、已退役执行实验、仍待审查。删除执行测试须同时核对它的真实调用者和现役入口；共享函数仍在使用时保留相应测试。旧代码/测试可以在精确Git历史中保留，不要求每次改动重新模拟当年的完整施工。不要用skip、ignore列表、另一套夜间回归或动态依赖框架掩盖没有作出的退役判断。

## 一个稳定检查，按实际范围验证

`kernel-tests` / `test`名称不变，PR/main都产生实际检查，不使用顶层paths-ignore。

**文字路径（#545/#546）**：仅根README/AGENTS、本文、RESEARCH-ENTRY、research-outcome-contract-v1，以及新增`docs/readings/**/*.md`。普通非执行文件新增/修改；完整Git base→head raw/NUL差异，不靠最后一次提交或平台300文件子集。精确base须有本仓库main/push/attempt1成功CI，较新失败/进行中/未知不能被旧绿灯掩盖。混合、删除、改名、特殊mode及未知回full。此路径不安装工程环境、不收集全库、不执行全量pytest，实际执行stdlib回归和文字UTF-8/非空/NUL/冲突检查，明确`NOT_RUN_CONTENT_ONLY`。不认证链接、事实、计算、研究质量或Human接受。新增消费者依赖这些文件时同步审查分流范围。

**工程PR**：执行当前有效的完整测试集合。src、tests/fixtures、workflow、依赖、registry/JSON、计算、既有研究原件修改及未审路径不按扩展名免检。完整不等于已退役测试永不减少；`full-research-method-v3.md`等仍有实际消费者。

**干净主干合并**：真实安装工程环境后，只有单一两父merge、push.before=第一父、merge tree=本次owned PR head才尝试复用该PR全量。检查最新PR CI/attempt1/success、精确commit原生关联的已合并PR、唯一未过期artifact的SHA256/CRC、完整collection与JUnit逐项相符且无失败/跳过、精确Python/runner镜像/架构/实际安装包。参数名转换复用pytest JUnit writer。下载ZIP只作数据，不解包执行；读后再核最新PR，较新失败或不确定回full。

文字成功或其他继承结果不能充当PR full证明。CI工作流、分流/复用器及其测试、pyproject改变时main必须full；首次部署不能自证免检。squash、rebase、多提交push、不同tree、脏tracked文件、环境变化/缺失、旧格式或坏产物均回full。复用main仍实跑小型回归；失败直接失败，不补跑全量换绿。产物明确`scope=merge_reuse`、`FULL_SUITE=REUSED_NOT_RERUN`，绑定精确PR/run/artifact/tree/数量；当前执行单存`main-smoke.xml`，不伪造本SHA全量JUnit。

## 完整路径与权限

```sh
python -m pip install -e '.[dev]'
python -m pytest -q -n 4 --dist=loadfile --max-worker-restart=0 \
  -o faulthandler_timeout=60 -o faulthandler_exit_on_timeout=true \
  --durations=100 --durations-min=1.0 --junitxml=pytest.xml
```

本地默认串行；无skip/xfail/continue-on-error、worker重启或为变绿重跑。pipefail传播失败；60秒仅用于CI stall诊断。缓存只复用下载，每次真实安装。base-only isolated/no-cache安装及真实pass/fail/worker-crash回归保留。PIT、来源/证券身份、权限、create-only/写入不确定、现役历史读回和有效Odds计算继续覆盖。

CI仅contents/actions/pull-requests read，不用业务secrets、不保留checkout credentials。GH_TOKEN仅进入只读基线/PR核验，不进测试/内容。用`commits/{merge}/pulls`而非可能清空的run.pull_requests；空/歧义/单页满/不匹配回full，不猜PR号。三个原已验官方Action固定commit；同PR旧head可替换，main每run独立。

原`kernel-ci-<run>-<attempt>` diagnostics继续always/30天，身份、环境、验证范围分开记录。早期失败没有完整产物仍是失败。下游成功含义为“本次范围验证成功”，不是声称每个SHA都全量重测；现役来源/模型权限和原件验证不由此改变。

## 已实施、退役与后续

[#544](https://github.com/auguspp/decision-kernel/pull/544)：PR过期运行/pip下载/Stock重复准备去重，固定Suken旧启动器退役。共享runtime及原件保留；没有完整引擎提速结论。

[#545/#546](https://github.com/auguspp/decision-kernel/pull/546)：真实文字PR/main job为7/11秒。[#547/#549](https://github.com/auguspp/decision-kernel/pull/549)实现并修正同树复用；#548因PR关联回退、另有镜像差异，原样本不重写。[#550](https://github.com/auguspp/decision-kernel/pull/550)已取得首个真实命中：PR全量6225项，job310秒；main另外实跑80项，job54秒。不含排队/发布，不是同机基准或固定省时承诺。停止扩展复用器，以正常使用核收益。

#548/#550已删Sector一次性和旧intake启动器，现有workflow文件为28。旧intake请求单独修改不再自动搬运材料，没有替代触发；共享入库模块/工作分支/原请求/失败保留。恢复旧操作须明确授权。#544的原始[31-workflow审计](https://github.com/auguspp/decision-kernel/blob/b3a3546560010f3683b02ec931f372ab714f2687/docs/CI-MAINLINE.md)留在历史。

#551按#354/5815419873进一步退役**执行义务**：

| 对象 | 当前处置 | 保留什么 |
|---|---|---|
| 已无现役调用的`capture-sector-recovery.py` | 脚本退出main；移除32项专属模拟测试 | 两项共享peer/正常预算检查、正常Sector/采用与读回模块、原请求/tag/失败；原代码/测试在下方精确历史 |
| 三种旧PDF探索模式`pdf-transport`、`pdf-download-endpoint`、`exchange-pdf-source` | 删除workflow选项、命令及57项专属实验测试；增加一项真实shell退役边界回归 | 所有原eval脚本/离线verifier字节不变；Woton使用的native_identity/session测试及原始结果/失败保留 |

Sector的历史脚本及原测试可从[退役前精确提交fdb9104c](https://github.com/auguspp/decision-kernel/tree/fdb9104c1722fe250f44742e5129665b36c2889b)恢复用于历史检查，不是重新调用源站的授权。9月11日run34566950303失败且已消耗，不能改称成功。

旧PDF试验按[#297/5740713728](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5740713728)不再建设；原`eval/`脚本仅保留为历史试验/离线核验资料，不再是这些模式的现役云端入口，也不承诺旧试验在每次新依赖环境中重跑。later Woton candidate和metadata模式、共享HTTP/PDF解析/留存守卫不变。不存在新的探针运行许可。

#551实际6225→6137，PR全量通过；main复用后实跑80项、job41秒，正常发布/读回完成，见[#354/5815714318](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5815714318)。这不是删除88项让全量引擎只需41秒；完整清单也不代表剩余测试已逐条证明必要。

当前按[#354/5816112755](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5816112755)完成固定苏垦任务的代码退役：`saved_research_once`去掉固定请求/前驱、`checked_request/acquire/run/main`及`Retainer.begin`，保留模块名与共享`model_call/research/Retainer.save/native/local`实现。旧`-m`入口明确非零退出，不建立替代worker。原`api-once-request.json`、候选分支、失败和消费记录不动；原执行器/测试可在[精确前驱026a7195](https://github.com/auguspp/decision-kernel/tree/026a7195f4d0ad3ccac121c9de92fbe18e5bd4b5)恢复作历史检查，不授权重新采集/研究。移除13项固定任务/旧手写时序断言，新增1项真实CLI退出检查；共享时钟、SDK与输出留存测试保留，通用prompt预算测试不再依赖旧任务。实际CI/合并/发布结果读#354及对应PR，不以本文预填。现役Stock/Question等共享宿主没有被整组宣布退役。

后续优先审旧API编排/固定部署和重复集成准备，保留真正必要的旧成果读回；publisher重建和registry/计算按消费者验证尚待处理。

Reuse Decision: REUSE原生Git历史、已有共享守卫与CI，不加依赖/工作流/选择器。既有官方Git/Actions及外部skip/filter比选见#354历史；删除已退役义务不需要另一套过滤平台。回滚走正常PR，不直写main/force-push，不删除原证据或运行，不改生产日程。写入不确定先对账；CI、发布、Research质量、Human接受和投资决策各自独立。
