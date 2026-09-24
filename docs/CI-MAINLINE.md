# CI mainline / CI 施工接续入口

Updated: 2026-09-25. Engineering only; Investment Authority = NONE.

## 当前方向与接点

Human授权按最终目标连续推进，不逐PR索批。v2-first授权[#354/5818204474](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5818204474)；成熟组件审计[5817811217](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5817811217)；本次正式责任接替[5818729891](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5818729891)。先确定现役合同，再复用成熟执行组件；不要把减少等待变成新增管理平台。当前main、实际PR/run/产物和未完成验收以#354最新入口为准，本文不预填通过或提速。

前驱#555首次把7个现役研究模块（240项）独立运行，PR域job25秒/pytest4.81秒，完整6138项job386秒/pytest335.27秒；两个job合计411秒。其main完整6138项与240项已实物核验；正常publisher36031490641成功，读取ref f326e2cbad1b0f307e308df5c526c766a2fe537a的code_commit绑定065382ca300a73cf65e1bcfadd46a98bbb5150e6。不要把这些历史基线当本次提速。本地clone不可用不等于连接器没有写权限。

## 首组正式接替：不再重复执行240项

| 当前责任 | 正式承担者 | 范围边界 |
|---|---|---|
| 进度保存、追加、恢复，不自动commit/续跑 | v2 `test_research_progress.py` | 不认证真实托管跨会话恢复 |
| Research-only冻结/读回及UNKNOWN风险 | v2 `test_research_commit_only.py`、`test_research_only_commit_v2.py`、`test_research_model_risk_unknown_v2.py`、`test_generic_research_commit.py` | 不把缺概率/估值升级为Odds或Human接受 |
| 固定读取包、登记、档案和索引恢复 | v2 `test_research_archive.py`、`test_research_archive_index.py` | 原件、身份、完整性和权限；非研究质量 |
| 其余现役或尚未裁定的责任 | 原执行job的剩余集合 | Market/Odds/准入/来源/发布等继续保护，不因未迁移就跳过 |
| 整体集合完整且失败真实传播 | 原共享collection/JUnit与ZIP校验 | 两组并集等于完整集合、互斥、同一次运行 |

`.github/ci-v2-research.txt`仍是pytest原生参数文件，不是动态selector。v2单组继续明确`NOT_RUN_DOMAIN_ONLY / merge_eligible=false`：它只承担自己的责任，单独绿色不能合并。

正式full先收集当前全部测试，再用该文件生成pytest原生`--ignore`参数：这些测试由同run的v2执行，而非从完整责任中排除。删除/改名模块或空模块未同步更新参数文件会失败，不静默缩小集合。剩余job保留xdist4、worker-crash和非零退出传播，不重跑v2来覆盖其失败。

剩余执行保存`remaining.xml`。`--operation assemble`使用原gh/ZIP读取器取得同run/attempt的唯一v2实物ZIP，核代码/event/run/attempt、实际Python/镜像/架构，以及小安装环境所有包必须与完整环境同版本。两组分别通过原集合校验，再验证并集完整、互斥。缺件、异身份、环境漂移、失败或重复都不能产生full成功。

合格结果标`EXECUTED_PARTITIONED_V2`。`pytest.xml`明确是两份原始testsuite的聚合，不虚构单个pytest进程；原用例身份与实测suite时间保留。`remaining.xml`、`domain-source.zip`和`partition.json`保留原证据。main复用reader重新验证内层ZIP和两组组成，而非只相信聚合绿灯。历史单执行器full格式仍可读取，不能把分组scope/缺manifest伪装成旧格式。

两个job继续并行，没有新增调度job、轮询服务或生产触发。当前低耗时v2产物须已可读取；缺少它就失败，不无限等待。即使test job已绿，合并也必须等整个最新workflow成功；v2的后处理失败/取消仍会否决。后续若执行布局需要原生needs聚合，应直接迁移并退役本次同run装配适配，不无限叠层。

## 正式资格保持不变

- 合并核当前非Draft、精确head、最新完整workflow及实际full产物；不拿较早成功、单组绿灯或草稿反馈放行。CI成功、发布、研究接受和投资决定分开。
- 原可信内容路径保留：allowlist及新增研究Markdown，精确base须有最新本仓库main/push/attempt1成功CI。完整raw/NUL差异、status/mode和旧原件编辑处置不变，缺证回full。
- 原Draft反馈暂保留，不宣称全部受影响测试；Ready即使同SHA也产生新的正式验证。CI/依赖/全局配置/未知/删除/特殊模式仍full，不因失败降为Draft求绿。
- 干净main复用仍先真实安装，核两父merge、精确owned PR同tree、最新attempt1/full/非继承成功、完整环境及有效ZIP的大小/SHA256/CRC和collection=JUnit。复用后main实跑smoke；失败不补跑换绿。
- 策略文件、参数文件和专属测试仍属于POLICY失效范围；本次策略改动PR/main都完整执行，不能自证免检。独立main运行不能互相取消；同PR过期head按原生concurrency处理。
- 只读contents/actions/pull-requests权限；GH_TOKEN仅用于范围/身份/同run产物读取，不给测试或内容。不执行下载的ZIP；无业务secrets或持久checkout凭证。原产物30天/always留存，失败不因上传而转成功。

正式剩余执行使用`python -m pytest -q -n 4 --dist=loadfile --max-worker-restart=0 @remaining-args.txt`，保留60秒stall诊断、durations、JUnit和pipefail。本地默认串行；原base-only真实冷安装不变。没有xfail、continue-on-error、测试结果缓存或转移到夜间的未裁定义务。

## 后续按目标推进，不恢复无限shadow

首组已经承担正式执行，不新增第二套同职责测试。继续按现役能力审查其余组的KEEP / CONSOLIDATE / RETIRE / DEFER；不得为CI擅自关闭业务能力，也不按年代、名称或测试数量判死刑。共享身份/时间/来源/权限和必要历史reader继续保护。

执行优化复用成熟组件：pytest-split先对代表性同集合比较1×4、4×1、2×4、4×2；uv只benchmark安装层；testmon只做有界shadow；actionlint和offline zizmor先实扫。dorny不能代替可信baseline/mode，fkirc同树成功不能代替full资格。尚未实跑的实验标NOT_RUN，不把组变小算成执行器提速。

至少记录tests/subtests、安装/收集/执行、job及触发到完成、runner数量和sum(job秒)/60、cache、PR/main、新增维护量。不同runner的快慢不是因果证据；累计testcase时间不是wall或CPU。首组迁移不等于总等待目标完成，后续必须减少正式临界路径而非只展示快旁路。

## 生命周期、协作和回滚

每次ADD/CHANGE/CONSOLIDATE/RETIRE同PR处置runtime/workflow、专属tests/fixtures、参数/缓存引用、布局断言/CI例外、共享守卫及历史reader。流程退役而专属CI未处置，退役未完成。不设一加一删配额，不建逐测试registry。

结构孤儿使用Git搜索、pytest原生收集与成熟静态工具；语义孤儿按实际消费者裁定，零引用不自动删除手动入口/历史reader。本次分组执行退出时，同步退出其装配分支、原生参数转换、专属接线测试；有其他消费者的共享ZIP/完整性逻辑保留。

CI只锁依赖结果的采用/合并边界；独立授权工作继续，不短轮询、不制造假忙。工具先发现、核目标和授权，未发现不是没权限；明确安全/权限拒绝停止对应动作，不换工具绕过；不确定写入先只读对账，不重复写。旧#297安全拦截不重试。

回滚正常PR，不直写main/force-push、不删历史证据/运行、不改生产日程。前驱说明与#544–555成果均保留在Git/Issue。#354保持OPEN，未裁定风险和总体等待改进不得冒充完成。
