# Kernel 2.0 — P2 成熟工程先例对照 v1

日期：2026-10-10（Asia/Singapore）。归属 [#508][OWNER]；有效计划 [KERNEL-2.0-PLAN-20261010-v1.0][PLAN]；前驱 [P1 交付回执][P1-DONE]，本轮 [P2 开始记录][START]。

**状态解释：本文件是 P2 设计输入与复用建议，不是 P3 架构决策已采纳、P4 开工授权或上游工具已安装。** 文件/PR/CI/合并/发布的实际结果在 #508 最新回执与本文件 PR 中，不在这里维护第二张实时进度表。

## 1. 范围与结论

Kernel 读取基线 M=`97a4b14e287b04600841c1cc157c38a3cad0a781`（#801 合并）。本轮已恢复当前 AGENTS、NEXT-PHASE-CONSTRUCTION、#297、#508 主计划/03 回执、CONS-11、#508 治理先例与 #511 全部11条已有评论；开放 main PR 查询为空，docs 目录未有本 P2 文件。P1 的主要责任图、成本样本与 UNKNOWN 直接复用，不重新宣称全仓审计。[P1][PROTOCOL][CONS11]

**建议方向：保留现有领域与研究边界，把外围责任和兼容范围写清；优先使用现成检查工具及原生 GitHub 能力，而不是新建平台。** 现有代码不缺另一个统一状态库、调度器或“万能来源对象”。当前证据支持对已有职责作少量设计决策，不支持为了 2.0 把目录、schema、方法版本和运行系统一起翻新。

P2 的主要增量是：明确稳定接口不等于内部实现永久冻结；逻辑身份、原始路径与显示名称分别处理；配置、执行回执、数据原件、派生阅读和接受记录分别保管；失败恢复先对账；测试退役按消费者与义务，而不是按年龄或数量；架构检查可优先评估 Import Linter，ADR 可借鉴 MADR，但不能照搬其默认目录覆盖本仓 Human 决定。

### 证据与裁定口径

- **FRESH-CODE**：本轮固定上游 commit，实际读取下文列明的代码区间；不等于审阅完整项目或运行其测试。
- **FRESH-CONTRACT**：实际读取版本化 schema/规范或固定 commit 文档。滚动网页另记读取日期；不把网页最新版本当 Kernel 已采用版本。
- **RETAINED-AUDIT**：恢复已有精确审阅记录；仅复用其已覆盖的局部模式，不冒称重新读过所有上游源码。
- **REUSE / ADAPT / REJECT / DEFER** 是本轮对具体机制的建议。REJECT 只针对说明的用途，不是封杀整个项目；DEFER 不是无合适工具的证明。需要薄接合层时记 THIN_ADAPTER 候选；本轮没有 NEW_BUILD_JUSTIFIED 的运行子系统。

## 2. 十二类工程责任覆盖

| CONS-11 责任 | Kernel 问题与消费者 | 实际先例及机制 | P2 建议与 P3 必答项 |
|---|---|---|---|
| 01 架构/边界/接口 | P1-A/B：领域提交与外围读取组合的边界 | Airflow 明确 SDK 公共出口；OTel 区分组件生命周期与功能；Import Linter 检查依赖链 | REUSE 明确接口、ADAPT 组合归属；列出真实支持的入口/行为，不把所有 Python 导入路径都宣布稳定 |
| 02 身份/命名/拓扑/ownership | P1-D/E/H：机器 ID、文件名、显示名混用；同类材料位置不一 | Home Assistant 的 domain/name 与必要/可选依赖分离；Kubernetes staging 单一维护源；Python Unicode 规范化 | ADAPT 身份/展示/原始路径分离；决定逻辑对象、writer、reader、当前位置和生命周期，目录结果后置 |
| 03 数据/状态/产物/血缘 | P1-D/I：registry、原件、R 和数值来历不能合并 | dbt manifest v12/run-results v6 分离声明图与执行结果；SLSA 分离构建输入与执行来历 | REUSE 分层描述；精确字节不能代替单位/期间/修订/来源资格，P3选一条价格→派生结果链作验证方案 |
| 04 执行/失败/恢复 | P1-C：未知写结果、重复触发与业务拒绝 | Temporal 说明未确认的 Activity 可重执行；OTel 明确启动/退出义务；已有 LangGraph 审阅提供重复执行反例 | REUSE 对账和局部失败边界；DEFER 新执行框架，不引入自动重试。区分未执行、已失败、结果未知、已确认成功 |
| 05 配置/schema/兼容 | P1-A/D/E：软件2.0不等于包schema2或方法版本 | dbt独立schema版本；Airflow SDK与发行版版本不同；Kubernetes版本化API行为保护 | ADAPT 明确读/写兼容矩阵；旧字节与旧哈希保留，新字段缺失不可填成已知事实 |
| 06 测试/CI | P1-F：已有四scope，重复collection也承担集合证明 | Rust区分包测试、格式、发布包和性能验证；Import Linter有实际CLI失败/配置反例；Kernel现成pytest分片与证据reader | REUSE 现役工具；先按责任退役再减少重复构建。新增架构lint先有界试验，不替代完整CI或消费者测试 |
| 07 发布/弃用/迁移 | P1-A/E/H：避免长期双实现和旧writer永续 | SemVer先定义公共API；Kubernetes API版本与退役不同于软件发版；OTel要求弃用说明及迁移路径 | ADAPT 小批迁移、兼容窗口与退出条件；REJECT照搬企业发布节奏/任意删旧字段，不在P2签发2.0 release |
| 08 诊断/可运维 | P1-B/C/F/J：成功、丢弃、拒绝、过期与未知需分开 | OTel内部诊断区分输入/输出/拒绝及自身/下游错误；dbt逐结果status/timing；原Actions时钟/诊断 | REUSE 现有run与安全摘要；缺哪项诊断补哪项，不新建遥测服务，不由缺结果推断quiet |
| 09 安全/依赖/供应链 | P1-G：SHA与tag固定策略；artifact作为数据 | GitHub官方least-privilege、完整SHA与workflow_run安全；SLSA v1.2构建来源；Qlib拒绝静默退回不受限pickle | REUSE 原生Actions/attestation；按真实风险设计固定版本与更新过程。未扫告警不等于无漏洞，不新增权限服务 |
| 10 文档/ADR | P1-H/J及换会话需求：旧入口、重复状态、Human记录污染风险 | MADR4.0.0的选项/后果/Confirmation；既有Spec Kit/BMAD/patch-first审阅 | REUSE 少量决策记录及可达后继；架构ADR不得直接落入本仓已有Human `docs/decisions/`用途；P3决定最小存放方案 |
| 11 扩展/provider策略 | P1-B/C/I：共享技术能力与来源特有资格混淆 | HA必需/可选依赖；OTel Factory与组件责任；LEAN的数据/映射/因子/结果处理分离 | ADAPT 清晰能力参数和静态组合；REJECT自动插件发现/隐式fallback，现有适用薄adapter继续使用，不造统一路由平台 |
| 12 研究系统分工 | P1-A/D/I/J：研究、模型、实验、评价与决定 | Qlib Recorder分别保存参数/指标/产物；LEAN数据与交易/结果接口；旧Quantifact/TradingAgents/PIT反例 | REUSE 实验身份与反例；REJECT收益自动推导研究正确或Human接受。保持Research/Odds/Action与不成熟Outcome分别成立 |

这张表覆盖工程责任，不是安装12套工具。每类下方都有具体来源与裁定；没有把“看过README”升级为生产依赖验收。

## 3. 固定版本的机制审阅

### PA-01 Airflow：公共边界优于冻结全部内部路径

**实际读取：** Apache Airflow **3.1.6** 对应 commit `d6a009b6dfa1802930f514a2429cc56f5b4c2f12`；`task-sdk/src/airflow/sdk/__init__.py` 全文，及同版本公共接口文档。SDK 文件本身版本是 **1.1.6**，不能与 Airflow 发行版混称。[AIRFLOW-CODE][AIRFLOW-DOC]

该入口通过明确的 `__all__` 与受控 lazy-import 映射暴露能力，未知名称抛错；文档把面向DAG作者的接口与内部模型/数据库结构区分开。这里值得学习的是“什么行为可依赖”，不是给每个内部类承诺永久兼容。

**Kernel 建议：ADAPT。** P3先明确研究提交、固定R读取、归档恢复等现役消费者真正依赖哪些输入/输出和错误语义，再决定有无必要新增稳定导入门面。`live.py`已是有明确目的的组合根，不应因它知道默认行情映射而误判领域层受污染。

**不复制与成本：** 不安装Airflow、调度器、数据库、插件体系或把所有模块包装成SDK。已读代码含Apache-2.0许可头；本轮不复制代码。新门面会有导入兼容和旧入口退役成本，只有真实消费者需要时才加；直接保留原入口是有效备选。未运行Airflow测试，也未证明Kernel整个import闭包无反依赖。

### PA-02 OpenTelemetry Collector：组件责任、稳定性、诊断分别定义

**实际读取：** commit `e85aabce57ebef50de20837dca46fb6f4a483f04`；`component/component.go`全文；`docs/component-stability.md`前175行及官方当前文档的诊断条款（2026-10-10读取）。[OTEL-CODE][OTEL-STABILITY]

组件合同明确创建、启动、运行和退出；启动失败向上返回，退出必须处理未启动或重复退出的情况。稳定性可按组件所处理的信号与配置分别说明，并要求可理解的迁移说明。诊断关心接收、输出、拒绝和错误归属，不只是“整个进程绿灯”。

**Kernel 建议：REUSE责任描述、ADAPT局部组合。** 对共享Collector预算、reader扩展、publisher写入和可选模块失败隔离明确唯一owner。workflow廉价预筛与Python资格检查不自动合并；P3须说明哪层建立事实、哪层只是减少无用工作。重要的错误传播必须留在真实消费者路径。

**不复制与成本：** 不安装OTel Collector、Go组件Factory或新观测后台；不照搬覆盖率阈值、组件晋级委员会、固定弃用月份。Apache-2.0由已读源码SPDX声明。额外诊断有字段与维护成本，只补实际缺口；日志不应携带供应商秘密或私有原文。未运行上游生命周期测试；不声称本仓每一reader都满足这些性质。

### PA-03 Home Assistant：稳定机器名、显示名称与可选依赖

**实际读取：** `home-assistant/developers.home-assistant@883072b5555988737f681e91a8b2f0d2cf27af70`，`docs/creating_integration_manifest.md`前135行。[HA-MANIFEST]

manifest区分稳定唯一domain和供人识别的name，并分开必须先成功的dependencies与可选after_dependencies。它同时说明依赖安装和加载行为；“可选顺序”并不等于没有依赖安装成本。

**Kernel 建议：ADAPT，不引入manifest注册平台。** 机器record/question/source身份不能由可变中文标题替代；原始路径应保留来历，显示名称允许改善。领域依赖、启动顺序、展示顺序和可选扩展是四个不同问题，不靠统一目录层级或字符串前缀表达全部关系。

**不复制与成本：** 不复制HA domain=目录的强约束、自动安装requirements、配置向导或集成注册库。该条仅转述固定文档的设计模式；未审HA运行时代码或整仓许可，不能据此批准代码/模板复制。P3的说明应复用既有对象与输入合同，不为了有owner就给每个文件新增schema。

### PA-04 Kubernetes：一份维护源与明确兼容义务

**实际读取：** Kubernetes **v1.34.0** commit `f28b4c9efbca5c5c0af716d9f2d5702667ee8a45` 的`staging/README.md`前150行；另读官方Deprecation Policy当前页面（2026-10-10），不称v1.34.0为最新版本。[K8S-STAGING][K8S-POLICY]

staging文档明确内部目录是维护源，外部仓库由其发布，使用方通过workspace/replace解析；发布副本不接受独立代码修改。弃用政策将已发布API组版本的行为保护与软件版本/内部提交分开，并要求考虑既有存储数据的转换。

**Kernel 建议：REUSE单一writer，ADAPT兼容矩阵。** 本仓已经区分生产配置、原研究原件、registry索引、派生R和News缓存；未来目录变化必须指出唯一维护源与派生者，不能建立另一套能独立改写的2.0状态。归档旧读格式与已退役写入器应分开，不要求旧executor永久可运行。

**不复制与成本：** 不拆出发布子仓，不搭集群/etcd/controller，不复制SIG审批或Kubernetes固定支持年限。P3为实际消费者确定保留/迁移/拒绝规则；原件不可逆转换须保留旧字节，不能把未知值补成“向后兼容”。本轮只读文档，不复制Kubernetes代码；许可与部署不作采用裁定。

### PA-05 dbt：对象定义、运行结果与版本不是同一个东西

**实际读取：** 官方`manifest/v12.json`的metadata/节点身份及checksum定义，`run-results/v6.json`完整结构，及artifact说明。固定的是**schema版本**；其中`dbt_version`字段的默认示例不是Kernel或整个平台的版本证明。[DBT-MANIFEST][DBT-RESULT][DBT-ARTIFACT]

manifest描述对象及关系；run-results按`unique_id`记录status、timing、execution_time和adapter_response。schema版本、软件版本、生成时点和invocation身份分别表达，一些元数据允许null，不能根据字段存在推断完整运行证据。逻辑`unique_id`也不等于内容checksum。

**Kernel 建议：REUSE区分，保持现有数据格式。** registry用途登记不是全量业务状态，固定R不是源原件的当前资格；来源/方法/schema/代码/执行/阅读版本分别保留。若未来简化descriptor，必须核每个现役reader所需信息，不直接套dbt的字段或把一个invocation ID当完整血缘。

**不复制与成本：** 不引入dbt、SQL编译器、warehouse、manifest仓库或第二结果库。当前只对照正式schema，未执行dbt或证明其数据来源PIT。P3先评估原字段足够与否；只有实证无法表达的缺口才讨论格式改变。任何新增schema都带旧reader和迁移成本。

### PA-06 Temporal：外部效果与确认分离，恢复不是盲重跑

**实际读取：** `temporalio/documentation@724a4e4ee7361ed6f04fb48fabc8fe22986c48ee`，Activity Definition前210行，特别是idempotency条款。[TEMPORAL]

Activity的完成只有报告到服务端后才进入已确认历史；效果已发生但未确认时仍可能重执行。把“查数据—调用服务—写文件”放在同一Activity，最后一步失败会使前面步骤再次执行；更细粒度有利于隔离重复效果，但增加历史与交接成本。

**Kernel 建议：REUSE失败分析，不采用自动恢复策略。** 将“未执行”“确定失败”“效果未知”“已读回确认”分开；未知Git写响应先查精确ref/PR/原对象，不换通道重复创建。只读重建不能自动获得producer、Research续作或投资权限；原源拒绝也不能转成成功WAIT/quiet。

**不复制与成本：** 不安装Temporal服务/Worker/event history，不把上游默认重试带入本仓，也不为每一步永久建状态机。已有GitHub操作回执与固定commit常已足够。更细边界需要逐条证明价值，不能无限拆分。SDK、部署许可和容量均未试验；本条只是明确的官方语义合同，不是执行器采用。

### PA-07 Rust：不同测试各自证明什么；保留有用反例

**实际读取：** `rust-lang/rustc-dev-guide@aa181c58c5ad008b67fa8df22b3e610cb9c81dc8`，`src/tests/intro.md`全文。[RUST-TEST]

指南分别说明compiler测试、包单元/集成/文档测试、tidy/格式、文档链接、distcheck和性能测试。发布包解包后构建并测试，与源码工作区测试是不同证明；工具格式检查也不证明编译器行为。部分Rust工具的允许失败规则属于它自身项目选择。

**Kernel 建议：REUSE证明分工，KEEP原四scope。** 现有完整collection/分片并集检查、消费者失败传播、历史reader与独立browser证据分别有用。退役旧writer及仅为它服务的fixture时，应保留仍保护共享语义的测试；不要把便宜字段反例升级为重复昂贵整链，也不要把多用例压进循环来伪装减少义务。[CI]

**不复制与成本：** 不引入Rust bootstrap/tidy/Crater、compiler目录或允许失败规则，不把所有PR都加browser/distcheck。明确现役保护后才设计变化范围；测试代码量与P1成本只是调查信号。上游工具未运行，真实Kernel fixture退役清单仍须逐切片核实。

### PA-08 Import Linter：可以直接评估的架构检查CLI

**实际读取：** `seddonym/import-linter@31927f1457e3df673912cb5efb0afa6dbc37585f`（2.15）：`src/importlinter/contracts/forbidden.py`前200行、`tests/functional/test_lint_imports.py`前155行、`tests/functional/test_cli_without_ui_dependencies.py`、`pyproject.toml`、`LICENSE`，以及官方合同说明。[IL-FORBID][IL-TEST][IL-UI][IL-PKG][IL-LICENSE]

Forbidden合同默认检查间接依赖，忽略项失配默认报错；实现使用Grimp图寻找链并保留行号。重叠source/forbidden模块对会被跳过，因此不能随便用涵盖自身的通配符就声称全部隔离。功能测试包含坏配置、违规依赖、namespace和TYPE_CHECKING情形；另有CLI与可选UI依赖分离的测试。这里是**读到了测试源码**，不是本轮执行通过。

**Kernel 建议：REUSE现成CLI候选，采用待P3裁定。** 先在P3明确少量禁止方向，再用已固定的工具做开发环境有界试验，比较“不新增工具，仅保留现有明确断言”。不自建通用import图、规则DSL、Web面板或动态影响分析。验证输入中必须同时有合法路径和刻意引入的反依赖；输出应可定位真实链，而非只报分数。

成本与退出明确：BSD-2-Clause；Python>=3.10；运行依赖包括Click、Grimp、Rich、typing-extensions及条件Tomli，可选UI另需FastAPI/Uvicorn。Kernel现有Python环境与依赖兼容、实际扫描时间、动态import/文件路径/workflow耦合覆盖仍**NOT_RUN/UNKNOWN**。静态导入图不证明完整运行时调用图、权限或数据血缘。若入CI，只作开发工具及少量配置，退出删除对应配置/依赖；不把业务数据编码进lint。不因工具名成熟就自动新增长期门禁。

### PA-09 LEAN 与 Qlib：职责分离有用，交易与评价语义不继承

**实际读取：** LEAN commit `80e7843f645673bcbeaab963049f76f20f6785e1` 的`Engine/LeanEngineAlgorithmHandlers.cs`前160行；Qlib commit `54355232463878d2eebb91fe0ee5fa7fa1f5976c` 的`qlib/workflow/recorder.py`前225行。[LEAN][QLIB]

LEAN把数据feed、symbol映射、因子、数据provider/cache、结果和交易handler分开，组合根注入具体能力。接口分开是机制证据，不证明每个来源或跨币种处理都正确。Qlib Recorder为单次运行分开身份/状态、params、metrics和artifacts；所读接口明确`trusted=False`，受限对象加载失败不能静默换不受限pickle。当前代码已不同于旧指南的无trusted参数版本，不能只沿旧API摘要推断安全行为。

**Kernel 建议：ADAPT边界，REUSE已有研究反例。** 把provider/channel、原数据期间/单位/复权与派生算法来历传到真正消费端；不以“同ticker”或“同hash字段名”代替同口径。运行完成、模型产物生成、Research资格、Human接受与Outcome成熟分别成立。Qlib的实验身份模式可参考，但当前GitHub原件与回执已有承担者，不需要MLflow成为新权威库。

**不复制与成本：** LEAN所读文件为Apache-2.0，Qlib为MIT许可头；本轮不复制/运行代码。拒绝本范围引入订单handler、交易终态、模型训练栈、自动收益评分或pickle档案消费。Qlib变更标题不等于全项目已安全；未执行其安全/模型测试。已有#511 Quantifact/TradingAgents/bar-by-bar审阅按下一节的局部范围复用，不能将“框架PIT”当源修订与intraday知识时钟的保证。

### PA-10 MADR、SemVer 与原生供应链：少量可核决策，不建治理引擎

**实际读取：** MADR **4.0.0** commit `2475fe1973f66a12aaf58a91d8fa7b42c0f5ea3d`的`template/adr-template.md`与LICENSE；SemVer **2.0.0**；SLSA **v1.2** Build Provenance；GitHub Actions Secure use reference（2026-10-10）。[MADR][MADR-LICENSE][SEMVER][SLSA][GH-SECURITY]

MADR把问题、可选方案、决定及后果分开，并提供Confirmation说明实施如何验证；元数据允许裁剪。**其默认建议`docs/decisions`不能直接复制：Kernel这个位置已有Human决定checkpoint。** P3可在设计文件中保留少量ADR或选独立架构位置，但不可无意改变Human记录的用途/读者。[P1]

SemVer依赖先声明公共API；已发布版本不可原地改写。它不能代替schema和研究方法的独立版本。SLSA记录构建输入/执行来历，builder身份影响可信解释；签名不证明研究正确或Human采纳。GitHub建议最小job权限、完整SHA固定，并避免特权workflow_run执行不可信产物/代码。

**Kernel 建议：REUSE简明ADR结构和现有原生签名/CI，ADAPT版本/固定策略。** 不安装MADR工具链、不改仓库license、不承诺SLSA等级、不新造密码学验证器或审批服务。MADR许可声明MIT OR CC0-1.0；本文件仅转述，不复制模板全文。P1-G的tag差异需要P3明确一致性与更新成本，不在本PR顺手升级Actions。既有Dependabot/CodeQL/attestation能力和#619权限边界继续，不因本轮阅读重新设置。

## 4. 旧先例的实际消费与剩余缺口

| 原记录 | 本次实际使用 | 没有借旧记录扩大成的结论 |
|---|---|---|
| #508/5854935905：Spec Kit、BMAD、Decision Lab等 | 复用原则变化影响传播、入口可达性、少仪式与patch-first；已有治理条款不重复建平台 | 未重新审阅这些项目完整当前源码；不把新AI建议静默升级成Human规则，不搬agent角色或第二状态库 |
| #511/5909055503：Quantifact `0beb506…` | 真实失败→候选改变→同样本/回归→可审阅patch；检查例外本身是否可信 | 本轮未运行teach；其patch-ready不是接受，expected-refusal任意异常通过的规则不移植 |
| 同记录：bar-by-bar `9c645bb…`、TradingAgents `8b22d43…` | 可见时间窗口、请求前知识日期拒绝以及真实消费者接线的负控制 | 不继承交易簿/投资权限；bar窗口不是安全沙箱，按日知识日期不是日内PIT |
| #511/5943375601：Qlib dated members | 保留“历史成员证据≠今日成员回填”的既有来源对照 | PA-09本次读的是Recorder不同责任，不声称重验旧CSI来源或得到THS/TDX历史数据 |
| #511/5854938235：LangGraph | 与Temporal一起作恢复前代码可能重复执行的反例 | 保持runtime候选DEFER，不采用其checkpoint后端或恢复执行授权 |
| #511/5946621157、5948481135 | 保留report-cli/IMA已有有界adapter和私有数据边界 | 不重建已交付采集；不从私有报告能力推断可以公开正文；不新增provider请求 |

原记录在 [#508治理审阅][GOV] 与 [#511候选池][POOL] 可恢复。这里只解释本任务怎样消费，不重复给候选池新增全部卡片。旧记录中按“GPL不适合未来商业化”一刀切的措辞不覆盖当前AGENTS的个人用途评估要求；本轮不据假想商业场景拒绝工具。[PROTOCOL]

**新搜索范围：** 围绕public-interface、component stability/lifecycle、integration manifest、artifact schemas、idempotent recovery、compiler test types、Python import architecture contracts、deprecation、ADR及provenance进行公开搜索；对上述候选取得精确代码/合同，另核官方网站。不是全互联网或全部许可证审计。Dagster本轮未取得可独立定案的深读证据，保留候选而不写“不如现有方案”；当前数据/执行责任已由dbt/Temporal/OTel提供对照，P3若考虑资产编排才补其适用机制。此缺口不支持NEW_BUILD_JUSTIFIED。

读取中的局部失败已处置：本地公开API网络尝试DNS不可用；部分Web raw链接cache miss由原生GitHub固定版本读取补齐；Rust旧master、LEAN旧猜测文件名、MADR根模板路径不存在，按实际仓库目录/默认分支定位到上文原件。它们不是项目能力缺失、安全拒绝或许可失败，不用失败检索宣布“没有可复用工具”。

## 5. 四个会直接影响2.0设计的对照结论

### 5.1 不把“名称”当“身份”，也不原地规范化历史

Home Assistant给出逻辑身份与显示名称分离的先例；Python标准库已有Unicode规范化原语，无需自写Unicode算法。[HA-MANIFEST][UNICODE]

本轮仅做本地标准库字符串演示：Python **3.13.5**、UCD **15.1.0** 下，`caf\u00e9.md`与`cafe\u0301.md`原字符串不同、UTF-8字节SHA256不同，但NFC结果相同。**这不是Kernel目标3.12的实际validator测试，也不是文件系统/Windows/macOS安全认证。** 它证明“规范化后相同”不能使两份原来不同的路径/字节自动合并。

P3应区分逻辑ID、原始文件名、用于显示/比较的名称与精确blob身份；讨论碰撞、路径穿越、控制字符、平台保留名、长度、编码与symlink拒绝。不预先采纳一个允许任意Unicode的正则，也不重命名旧Git路径或改hash。真正的新规则要有旧ASCII读取和中文原件案例的正反测试，错误时不覆盖文件。当前CONS-08限制仍未改。

### 5.2 不把“组件化”当“更多框架”

可采用显式函数/对象参数、静态组合根和既有CLI；需要共用的只是有同一语义owner的行为。网络取回、源资格、纯转换、数值计算、读面拼装、最后指针更新的责任可被解释清楚，却不意味着每一层都要独立服务。Airflow/OTel/LEAN的规模不是Kernel的目标规模。[AIRFLOW-CODE][OTEL-CODE][LEAN]

P3先核 attach 顺序与预算有无真实约束，保留有界失败隔离；共享helper抽取必须说明减少了哪些维护责任，不能把不同来源资格压成相同接口后丢掉时间/单位语义。最终目录树仍未决定。

### 5.3 不把“统一测试”当“抹平证明差异”

优先KEEP现有pytest/pytest-split/xdist、原生needs、严格证据reader；Import Linter仅作为少量架构边界的候选补充。目标不是再加一层永久门禁，也不是依赖一张静态图安全跳过测试。退役判断需涵盖writer/reader、CLI/workflow、手工恢复用途、fixture与索引消费者。[IL-FORBID][CI]

P1成本样本是现状，不是P2后的收益。Import Linter实际耗时、CI总开销改善、零消费者清单、全源血缘和可运行恢复仍UNKNOWN，不能用文档合并签字。

### 5.4 不把“存得完整”当“研究正确”

manifest、run receipt、哈希、签名、Reader PASS和Research判断分别有用，但不能互相替代。新方法或新模型的候选结果不继承旧Human接受，归档恢复不触发自动Research/Odds；Outcome没成熟不能变成零收益或方法无效。[DBT-RESULT][SLSA][QLIB][PROTOCOL]

## 6. 给 P3 的有限设计议题

这是下一阶段输入，不是本文件已经作出的正式ADR。默认在`docs/kernel-2.0-design.md`形成少量决定，复用现有说明；确需分文件再选择不会污染Human决定的架构位置。

| 议题 | 必须比较的备选与实证 | 接受/停止条件 |
|---|---|---|
| A 边界与组合 | 保留原入口并补清责任；少量稳定门面；有界组合根收敛。用P1-A/B/C与PA-01/02/08核依赖 | 列明现役公共行为、内部实现、失败owner和真实调用者；没有消费者收益就不增加新层 |
| B 身份与placement | 不移动旧材料；对未来写入分离显示名；必要时有可逆定位/迁移。用PA-03/04及Unicode反例 | 覆盖旧路径/原blob/中文和碰撞拒绝、writer/reader/归属；没有读回证明不宣布迁移完 |
| C 格式与血缘 | 保留现schema并补说明；确有缺口才加字段/新格式；不自动重写旧payload | software/method/schema与源revision区分；选定链的provider/channel/units/period/调整/算法可对账，未知不填充 |
| D 验证/退役/安全 | 先退出已无执行责任的writer及专属测试；共享保护保留；Import Linter与不用新工具的方案比较 | 现役消费者和历史reader不丢；正反样本验证、精确CI scope与实际成本可核；无新授权不改变任务/权限 |
| E 迁移/恢复/发布 | 小批同仓替换、过渡入口有限保留、明确回退；MADR式确认与原GitHub交接 | 每批定义输入、范围、产物、兼容窗口、验证、恢复与退出条件；P3范围采纳后才P4，不以2.0名称预授权 |

**P2完成条件：** 十二类有机制级覆盖、真实源码/合同和保留审阅的等级明确、可复用与不复制项及成本/未知已写清；本文件按现行工程合同完成交付。**不是**所有候选实跑、全仓诊断通过、最终依赖选择、设计采纳或独立新会话验收。

## 7. 本轮验证与交付约束

本轮未安装/执行任何上游框架、CLI或模型，没有修改本仓代码、测试、workflow、registry、研究/Human记录或定时任务；只有公开工程资料读取、本地字符串例子和文档完整性检查。P2建议本身不构成新生产运行。

文档路径不在现行content allowlist，正式Ready PR按原full验证，不为文档扩白名单或挪到readings。当前完整CI、合并、独立main和正常publisher分别验；P2不需要新增Research用途登记或把工程文档塞进生产R。真正独立上下文恢复、浏览器/Sites、C/D自然窗口与投资效果继续由原owner持有。若阶段交付受阻，最新#508回执记录同一文件/PR停点，不重建计划或重复研究。

## 来源与可复查范围

所有上游代码链接固定上文commit；规范固定明确版本。滚动网页仅支持2026-10-10的实际读取，不保证未来内容不变。未复制第三方实现/模板全文；工具采用前仍须核准确发行包、传递依赖许可、数据使用权与实际部署边界。

[OWNER]: https://github.com/auguspp/decision-kernel/issues/508
[PLAN]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6094482452
[P1-DONE]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6094954709
[START]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6095086577
[P1]: https://github.com/auguspp/decision-kernel/blob/97a4b14e287b04600841c1cc157c38a3cad0a781/docs/kernel-2.0-architecture-map.md
[PROTOCOL]: https://github.com/auguspp/decision-kernel/blob/97a4b14e287b04600841c1cc157c38a3cad0a781/WORKING-PROTOCOLS.md
[CI]: https://github.com/auguspp/decision-kernel/blob/97a4b14e287b04600841c1cc157c38a3cad0a781/docs/CI-MAINLINE.md
[CONS11]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-6037621707
[GOV]: https://github.com/auguspp/decision-kernel/issues/508#issuecomment-5854935905
[POOL]: https://github.com/auguspp/decision-kernel/issues/511
[AIRFLOW-CODE]: https://github.com/apache/airflow/blob/d6a009b6dfa1802930f514a2429cc56f5b4c2f12/task-sdk/src/airflow/sdk/__init__.py
[AIRFLOW-DOC]: https://airflow.apache.org/docs/apache-airflow/3.1.6/public-airflow-interface.html
[OTEL-CODE]: https://github.com/open-telemetry/opentelemetry-collector/blob/e85aabce57ebef50de20837dca46fb6f4a483f04/component/component.go
[OTEL-STABILITY]: https://github.com/open-telemetry/opentelemetry-collector/blob/e85aabce57ebef50de20837dca46fb6f4a483f04/docs/component-stability.md
[HA-MANIFEST]: https://github.com/home-assistant/developers.home-assistant/blob/883072b5555988737f681e91a8b2f0d2cf27af70/docs/creating_integration_manifest.md
[K8S-STAGING]: https://github.com/kubernetes/kubernetes/blob/f28b4c9efbca5c5c0af716d9f2d5702667ee8a45/staging/README.md
[K8S-POLICY]: https://kubernetes.io/docs/reference/deprecation-policy/
[DBT-MANIFEST]: https://schemas.getdbt.com/dbt/manifest/v12.json
[DBT-RESULT]: https://schemas.getdbt.com/dbt/run-results/v6.json
[DBT-ARTIFACT]: https://docs.getdbt.com/reference/artifacts/dbt-artifacts
[TEMPORAL]: https://github.com/temporalio/documentation/blob/724a4e4ee7361ed6f04fb48fabc8fe22986c48ee/docs/encyclopedia/activities/activity-definition.mdx
[RUST-TEST]: https://github.com/rust-lang/rustc-dev-guide/blob/aa181c58c5ad008b67fa8df22b3e610cb9c81dc8/src/tests/intro.md
[IL-FORBID]: https://github.com/seddonym/import-linter/blob/31927f1457e3df673912cb5efb0afa6dbc37585f/src/importlinter/contracts/forbidden.py
[IL-TEST]: https://github.com/seddonym/import-linter/blob/31927f1457e3df673912cb5efb0afa6dbc37585f/tests/functional/test_lint_imports.py
[IL-UI]: https://github.com/seddonym/import-linter/blob/31927f1457e3df673912cb5efb0afa6dbc37585f/tests/functional/test_cli_without_ui_dependencies.py
[IL-PKG]: https://github.com/seddonym/import-linter/blob/31927f1457e3df673912cb5efb0afa6dbc37585f/pyproject.toml
[IL-LICENSE]: https://github.com/seddonym/import-linter/blob/31927f1457e3df673912cb5efb0afa6dbc37585f/LICENSE
[LEAN]: https://github.com/QuantConnect/Lean/blob/80e7843f645673bcbeaab963049f76f20f6785e1/Engine/LeanEngineAlgorithmHandlers.cs
[QLIB]: https://github.com/microsoft/qlib/blob/54355232463878d2eebb91fe0ee5fa7fa1f5976c/qlib/workflow/recorder.py
[MADR]: https://github.com/adr/madr/blob/2475fe1973f66a12aaf58a91d8fa7b42c0f5ea3d/template/adr-template.md
[MADR-LICENSE]: https://github.com/adr/madr/blob/2475fe1973f66a12aaf58a91d8fa7b42c0f5ea3d/LICENSE
[SEMVER]: https://semver.org/spec/v2.0.0.html
[SLSA]: https://slsa.dev/spec/v1.2/build-provenance
[GH-SECURITY]: https://docs.github.com/en/actions/reference/security/secure-use
[UNICODE]: https://docs.python.org/3.12/library/unicodedata.html
