# CI mainline / CI 施工接续入口

Updated: 2026-09-25. Engineering only; Investment Authority = NONE.

## 当前方向与证据

Human授权按最终目标连续推进，不逐PR索批。v2-first与正式职责接替仍见#354/5818204474、5818729891；成熟组件审计5817811217。先确定当前合同，再复用成熟组件减少正式等待与维护面，不建立CI管理平台。当前main、PR、实际运行和验收缺口以#354最新入口为准，不在本文预填成功。

#555把7个当前研究模块独立运行；#556已让240项研究连续性由v2正式承担，其余5900项与之互斥，总6140项，原80子测试另计。#556的main/正常publisher/读回已在#354收口。此基础不把其余测试宣布永远必要，也不因未迁移就跳过。

本次布局采用#557真实实验结论，详见[5823086442](https://github.com/auguspp/decision-kernel/issues/557#issuecomment-5823086442)：同一5900项三次单机xdist4执行345.04/348.37/345.79秒，四机各xdist2执行111.31/106.16/112.61秒；集合、环境和时长快照均实物对账。另有一次4×4筛选，不足以替代已重复验证的4×2选择。实验harness不合main，保留分支和失败/成功样本后关闭。

uv0.12.17已完成同包、全新venv的三组冷暖缓存对照，并实际通过240域测试；setup-uv固定commit。本次只换安装器，不迁移整个项目管理或业务依赖，不改原base-only pip冷安装验证。正式流水线暂不恢复/保存pip或uv缓存：安装每次真实发生，跨job缓存净收益尚未验收，不叠加缓存平台。

## 当前合同与原生执行图

```text
kernel-tests / ci.yml
    prepare（范围、真实安装、完整收集、可选时长提示）
       ├─ contracts-v2：原7研究模块，240项基线，较小依赖
       └─ remaining-v2：pytest-split，4 runner × 2 xdist workers
    test（needs全部前置，稳定的最终门禁与完整产物）
        → 原有独立publisher，仅消费合格main结果
```

根ci.yml只保留原事件、并发、范围路由和最终门禁。准备与完整执行使用本地workflow_call；共同安装是一个薄composite action，使用现成setup-python、setup-uv。无新schedule/dispatch、外部调度服务、动态依赖图或状态库。

研究组继续保护进度保存/追加/恢复、Research-only冻结/UNKNOWN风险、固定读取包/登记/档案和索引恢复。`.github/ci-v2-research.txt`为pytest原生参数文件，原有效测试不重写。其他Market/Odds/准入/来源/发布与未裁定责任仍在剩余集合。工程CI不认证真实跨会话恢复、研究真理或Human接受。

正式full完整收集全部测试；已迁移文件通过pytest原生--ignore从剩余执行中分开，不从总义务删除。pytest-split只分配剩余集合：新增未知时长测试照常运行。使用显式`-c pyproject.toml`固定rootdir，避免外部参数路径改变nodeid。保留worker crash、非零退出、60秒stall诊断和pipefail；无continue-on-error、worker重试或失败后补跑换绿。

准备job产生实际包版本约束；各shard真实安装并逐项核同一Python、镜像、架构和包版本，研究小环境允许省略包、不允许改变共享版本。pip仍随setup-python保留用于inventory和原冷安装测试。分片每次保持同一只读时长提示，不在同轮边跑边改分配。

## 时长只是提示，结果才是证据

优先读取精确成功base的正常CI产物时长；历史格式可从真实JUnit转换，最多追溯一次该base已明确复用的PR。缺失/过期/读取失败使用pytest-split自身默认权重，不改变任何测试的必跑义务。不写自动更新commit，不把时长文件当结果缓存。

原run/head/attempt、scope、真实环境、原始collection/JUnit和日志分别保留。plan、domain、四个shard各有独立artifact；稳定test门禁在原生needs全部结束后核适用范围，下载同run/attempt的唯一产物，用原有有界ZIP摘要/CRC读取器仅解析数据、不执行ZIP。

完整结果要求：四片同身份/环境/时长快照，各片collection=JUnit，片间互斥，四片并集=剩余集合；再加研究组并集=完整集合。缺片、重复、测试失败、worker crash、环境漂移或取消均不能变绿。`always()`只让最终校验能够执行，不把skipped当success；content/draft/reuse与full的前置结果分别核对。

合格正式结果标`EXECUTED_MATRIX_V2`，保留四片ZIP、研究ZIP、remaining.xml、partition.json和聚合pytest.xml；聚合保留实际用例身份/时间，不虚构单进程完整运行。主干复用reader重新核内层证据。旧单执行器full与#556分区格式仍可读；保留reader兼容，不继续保留旧运行器。

本次同步退役#556的`--operation partition/assemble`执行入口及“短域应先完成”的时序假设，使用原生needs而非轮询/重试。旧单job命令和pip缓存布局断言改为当前失败/身份/完整性合同；共享历史reader测试继续。

## 保留的放行资格

- 合并检查当前非Draft、精确head、最新整个workflow成功与实际完整产物。单组绿灯、旧head、旧成功或草稿反馈均不能放行。
- 原内容allowlist、精确可信successful main baseline、raw/NUL差异与mode规则不变。content只做原内容检查，不安装工程环境；内容完整不等于研究正确。
- Draft只作显式有限反馈；Ready即使同SHA仍新跑正式验证。CI/依赖/全局配置或未知变更不走免检；不得把失败Ready降Draft求绿。
- 干净main精确复用先真实安装，再核两父merge、对应owned PR同tree、最新attempt1/full非继承结果、实际环境与完整有效ZIP。策略变化或不确定回full；复用后原main smoke实际失败即失败。
- 内容、Draft与精确main复用在prepare完成；不再额外双跑研究组或四片。最终门禁核明确模式与预期skipped/success，保留scope区别。
- 原只读contents/actions/pull-requests权限与同PR并发替换保持；独立main不互相取消。GH_TOKEN仅在范围和产物只读步骤，不交给测试，无业务secrets或持久checkout凭证。原30天诊断和always留存继续。

## 验收与后续

完整正式流水线时间必须实测，不能直接把实验111秒说成正式CI时间；同时记录准备、安装、收集、每片执行、聚合、排队、job总墙钟、sum(job秒)/60、runner数、缓存状态、PR/main和维护变化。累计case时间不是wall或CPU；少量样本只报告实值和范围。缩减义务与同集合执行加速分开计算。

继续按当前能力审查KEEP / CONSOLIDATE / RETIRE / DEFER，不为减少CI擅自关闭业务。分片解决必要执行的等待，不替代旧义务审查。actionlint/offline zizmor已做首次扫描，发现仍须按实际权限与范围裁定；不为清告警改生产触发。testmon仅有界shadow，dorny不代替可信baseline/mode，fkirc同树绿灯不代替完整证据资格。不再无限叠旁路组。

## 生命周期、协作与回滚

ADD/CHANGE/CONSOLIDATE/RETIRE同PR处置workflow、专属tests/fixtures、参数/缓存/布局例外和引用，保留共享合同及必要历史reader；流程退役但专属CI未处置即未完成。结构孤儿用Git/pytest/成熟静态工具，语义孤儿核实际消费者，不用零引用自动删除手动入口或历史兼容。不建逐测试registry或扫描服务。新matrix/安装组件被替代时，其专属接线测试同步退出。

CI仅阻塞依赖结果的合并/采用边界；独立授权工作继续，不短轮询、不假忙、不承诺后台。先发现实际工具并核目标/授权，未发现不是无权限；明确拒绝停止，不绕过；不确定写入先读回，不重复写。旧#297安全拦截不重试。

回滚走正常PR，不直写main/force-push、不删除历史证据/run、不改来源/模型/生产日程、Research/Odds/Watch/Action或投资权限。#544–557旧成果留在Git/Issue。#354保持OPEN，总体义务审查与长周期体验未冒充完成。
