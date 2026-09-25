# CI mainline / CI 施工接续入口

Updated: 2026-09-25. Engineering only; Investment Authority = NONE.

## 目标、授权与当前接点

Human授权本CI线程按最终目标连续推进，不逐PR索批。目标是减少正常施工等待、永久验证义务和维护面，不是保持测试数只增不减，也不是再造CI管理平台。当前main、活动PR与未验事项先读[#354](https://github.com/auguspp/decision-kernel/issues/354)最新入口；不要仅凭本文历史样本重复已完成施工。

v2-first与职责接替授权：5818204474、5818729891；成熟组件审计：5817811217；分片/安装实证：[#557/5823086442](https://github.com/auguspp/decision-kernel/issues/557#issuecomment-5823086442)；后继合同收敛范围：[#354/5824416309](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5824416309)。这些不扩大产品、Research、来源/模型、生产日程或投资权限。

#558已完成正式PR、合并、独立main、正常publisher和精确读回，见[完整回执5823677513](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5823677513)。实际PR/main从首job到最终门禁分别193/169秒，旧#556对应381/356秒；这是前后样本，不保证每次固定时间。三个同5900项的实验另行支持4×2选择；不把实验单片时间当正式全流程。

#559已完成测试合同收敛并正常合并。一次真实有用修改中，同head Draft反馈36076516487为56秒，转Ready后全量36076645736为183秒/6146项；main36077213704为36秒，精确复用后者的完整证据并实跑87项smoke，没有再次启动研究组或四片。原24个参考反例的累计case时间21.267→0.621秒；这是用例层前后样本，不是整条CI等比例提速。实际原件与后续发布/读回状态见#559和#354，不把一次绿色当长期接受。

## 一个正式骨架，四种明确验证范围

```text
kernel-tests / ci.yml
    prepare：范围、实际安装、必要时完整collection与只读时长提示
       ├─ contracts-v2：现役研究连续性合同，较小依赖
       └─ remaining-v2：pytest-split，4 runner × 2 xdist workers
    test：原生needs之后的稳定最终门禁
        → 现有独立publisher，只消费合格main结果
```

根入口负责原事件、并发、路由和最终门禁；准备/执行用本地workflow_call，共同安装用薄composite。复用固定setup-python、setup-uv/uv0.12.17和pytest-split0.11.0；不自建selector、scheduler、影响图或注册表。持久pip/uv缓存当前DISABLED，每次实际安装；原base-only独立pip冷安装检查保留。

| 范围 | 必须成立的条件与实际执行 | 不能声称 |
|---|---|---|
| content | 原allowlist或新增研究Markdown；精确base有可信最新successful main CI；raw/NUL差异/status/mode合格；原内容检查实际通过，不安装工程环境 | 不是全量测试或研究质量认证 |
| draft_feedback | 合格owned Draft；固定smoke、直接修改的测试文件及语法反馈；研究组/四片不额外运行 | 不是全部affected tests；merge_eligible=false |
| full | 当前完整collection；研究组与四片分开执行；原生needs与实际ZIP/集合校验通过 | 单组、最快单片、旧绿灯均不等于全量 |
| merge_reuse | 干净main两父merge与owned PR同tree；真实安装环境匹配；最新合格PR full产物验证；原main smoke实际通过 | 是明确复用，不是main重新执行全量 |

正常多轮修改优先放在同一Draft；准备合并再转Ready。即使SHA未变，ready_for_review也必须产生新的正式验证，不能复用先前草稿绿灯。CI/依赖/全局配置/未知变更不靠Draft免检，不为失败把Ready降Draft。不要转换他人的Research草稿。

## 完整性、身份与失败边界

研究组基线为7模块/240项，覆盖进度保存追加恢复、Research-only冻结与UNKNOWN风险、固定读取包/登记/档案及索引恢复；清单是pytest原生参数文件。未裁定的Market/Odds/准入/来源/发布责任仍在剩余集合，不能因为尚未迁移就跳过。CI不认证经济真理、真实托管跨会话恢复或Human接受。

full先收集当前全部测试。已迁移文件通过原生--ignore仅从剩余执行分开，不从总义务移除；pytest-split负责分配，不决定哪些测试可以不跑。显式`-c pyproject.toml`固定rootdir。新增未知时长测试仍执行；时长缺失/过期/读取失败回默认权重，绝不是成功结果缓存。最多读取精确成功base及其明确复用的一个PR的时长，不扫描历史或自动写时长commit。

prepare的真实包库存形成同run约束。每片核相同代码/run/attempt、Python/镜像/架构/包版本和同一时长快照；研究小环境只允许省包，不允许共享版本漂移。每片collection=JUnit、片间互斥、并集=剩余集合，再加研究组=完整集合。保留原始ZIP、collection/JUnit、环境和日志；聚合JUnit不冒充单一pytest进程。

最终`always()`仅保证检查执行，不把取消、失败、缺片或意外skipped算成成功。content/Draft/reuse/full分别核适用前置结果。无continue-on-error、worker重试或失败后补跑换绿；保留pipefail、worker crash传播与60秒stall诊断。

合并核非Draft、精确head和整个最新workflow，以及实际适用的内容或完整产物；工程PR必须有正式full。main复用还核owned PR关系、最新attempt1/full非继承结果、完整实际环境、唯一ZIP大小/SHA256/CRC及内层分组证据；策略变化、未知环境或不确定回full，smoke失败保持失败。POLICY里的实际策略/布局文件不能自证免检。

只读contents/actions/pull-requests权限不变；GH_TOKEN只给范围/产物只读步骤，不给测试或来源文字。无业务secrets、持久checkout凭证或ZIP代码执行；诊断always保留30天。同PR过期head可由原生concurrency替代，独立main不互相取消。CI通过、发布、读回、研究接受和投资决定分别验收。

## 按合同降低重复成本，不按年代删保护

#559是明确示例：参考字段错误由原`_qualify_references`承担，23种字段反例直接执行它，每个反例先确认fresh正样本可通过；跨股票extra_identity仍归真实observer，另保留真实正常→参考不连续整链传播。没有缓存validator结果或mock掉失败；退出的是每个字段反例重复构建整链的义务，不是身份/时间/数值合同。测试数量不是成本替代指标。

慢Stock/Woton组继续逐责任KEEP / CONSOLIDATE / RETIRE / DEFER，核真实消费者。Woton当前已先校验manifest/repair身份再重解析PDF，且有共享completed_snapshot；不能只因耗时或旧one-shot名称删除必要reader。没有业务退役授权时，不为CI擅自关闭能力。

每次ADD/CHANGE/CONSOLIDATE/RETIRE同PR处置runtime/workflow、专属tests/fixtures、参数/缓存/布局例外与引用。共享现役合同保留，旧成果需读时优先保留reader而非旧executor。#556时序partition/assemble执行入口已由#558原生needs替代，历史single/partition reader继续；#557实验已关闭未合并，不恢复无限shadow。新matrix、安装组件和本轮fixture也有同样退出责任。

结构孤儿用Git搜索、pytest原生collection和成熟静态工具；引用已删除模块必须显式失败。语义孤儿由实际能力审查裁定，零引用不自动删除手动入口或历史兼容，不建逐测试registry，不设一加一删配额。

## 验收指标与协作

分别记录test/subtest数、安装、独立collection、worker内部收集与执行、job及触发到完成、runner数、sum(job秒)/60、cache状态、PR/main和新增维护量。累计case不是wall或CPU；缩减重复义务、同集合执行提速、main结果复用必须分别记账。没有受控重复样本，不声称稳定百分比或漏选率。

后续优先减少真实慢合同的重复准备与编排，而非增加更多快速旁路。actionlint/offline zizmor已有首次扫描但有发现，不是安全PASS；接入时用实测低成本，不为消告警改生产权限/触发。testmon仅有界shadow候选；dorny不替代可信baseline/mode，fkirc同树成功不替代full证据资格。

CI仅锁依赖结果的合并/采用边界；继续独立授权工作，不短轮询、不假忙、不承诺后台。先发现实际工具、核目标和本次授权；未发现不是无权限。明确拒绝停止对应动作，不绕过；不确定写入先读回，不重复写，旧#297安全拦截不重试。

回滚走正常PR，不直写main/force-push、不删除历史Evidence/run。旧方案、失败和#544以来成果留在Git/Issue，不覆写为成功。#354保持OPEN；分片上线与分支实跑不等于全域义务审查或长期体验目标已经完成。
