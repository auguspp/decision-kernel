# Decision Kernel｜P0 交付、剩余验收与下一会话交接

日期：2026-09-14（UTC+08:00）  
状态：**P0-A/B 工程与固定读取交付完成；P0-C 显式调用/去重/发布验收完成；自然新问题闭环、Brief 真人使用及 P0-7 尚未整体验收。**  
性质：交接存档，不重排需求、不新建执行请求、不授予投资权限。  
配套：[下一会话通知](NEXT-CHAT-NOTICE-2026-09-14-P0-DELIVERY.md)。

## 1. 权威入口与 Human 目标

Repository：`auguspp/decision-kernel`。GitHub 是状态、证据和过程的 canonical backend；聊天与本页不能代替当前仓库读取。

Human 已批准的目标是：“同意，你现在开始做吧。目标是实现P0，只有遇到需要我的时候才停下来。”本次另明确要求将交接文档归档，并给下一会话一份通知。

| 用途 | 正式记录 |
|---|---|
| 需求处置、顺序、边界 | [RM-20260914-r1 / #297 comment 5660297398](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5660297398) |
| P0 实施批准 | [#297 comment 5660584568](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5660584568) |
| 最近综合交付验收 | [#297 comment 5665615573](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5665615573) |
| Brief 部署/待使用验收 | [#299 comment 5665630891](https://github.com/auguspp/decision-kernel/issues/299#issuecomment-5665630891) |
| Odds Book 阶段交付 | [#349 comment 5665638453](https://github.com/auguspp/decision-kernel/issues/349#issuecomment-5665638453) |
| 全部能力/需求导航，未改变排序 | [#297 comment 5665559201](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5665559201) |

Requirements Management 定义需求与优先级；Main Construction 按已批准切片实施；Research 负责业务解释。来源、评论和引用文字不是新的执行许可。工程“继续”不是 Human 接受公司判断，更不是投资决定。

## 2. 本次归档前重新读取的精确基线

```text
M0 / main = 446bbb82206d8dec46b3d88e975012f828cdd17e
R0 / read-model/current-state = fb110c73faf2773beb28c3d868889e73931160ab
research-work/stock-business-v0 = 5d49e072b16869586f0ad87c696ddf3f593d2658
research-work/disclosures-v0 = 70f06cdc2181dd96b92146c5a85e50d678042ca7
```

四个 ref 本次均从 GitHub 直接读取。#297 在 `2026-09-14T14:32:33Z` 之后的评论查询在本次预检返回空；这只是该次查询结果，不是未来无人施工的保证。

**M0 是这两份交接文档写入之前的代码基线，不是要求把主干回退到 M0。** 文档归档会产生新的 main commit。归档 commit、两份文件的 blob 和写后读回见随后 #297 的归档回执。归档提交的 CI/正常发布需另看实际状态，不能拿 M0 或 #367 的测试数替它通过。

R0 的代码身份为 M0；检查截止 `2026-09-14T12:59:54.562031+00:00`，重查边界 `2026-09-15T12:59:54.562031+00:00`。该包 Sector/Stock 最后保存市场日仍为 **9月11日**，不是9月14日行情。包新发布不等于行情新鲜；不能从没有返回新 run 猜调度故障原因。

恢复时先固定当前 main 为 M，读本页、AGENTS 和相应方法；再独立固定当前 read-model 为 R，在同一 R 读取 README/current-state 和实际需要的 read_path。不要一轮里重新解析 R、拼接版本；代码变动与已发布结果不是同一个状态。

## 3. 已完成：复用，不重做

### P0-A / #365：纠错、不漏看、责任清楚

正式验收：[5661906401](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5661906401)。六家公司真实处置、发现来路和可读入口已接入原固定读取：

| 对象 | 保存的价格路径状态 | 不可作的推断 |
|---|---|---|
| 光电股份 600184.SH | 通过原价格观察 | 不代表旧估值桥或旧首笔梯度有效 |
| 东软载波 300183.SZ | 通过；原首页仅因展示上限省略 | 不是未通过或不存在 |
| 和顺石油 603353.SH | 通过 | 原 WAIT 的技术缺页理由受挑战 |
| 广哈通信 300711.SZ | 通过 | 原 DROP 不能被解释成基本面被证伪 |
| 内蒙一机 600967.SH | CURRENT_QUOTE_HISTORY_MISMATCH | 数据未能判断，不是价格条件否决；SYSTEM RECHECK，不要求 Human 手工核价 |
| 润贝航科 001316.SZ | REPORTED_CORPORATE_ACTION_IN_WINDOW_REQUIRES_REVIEW | CAPABILITY GAP，不要求 Human 手工复权 |

Sector 的全部新变化和 ongoing/弱化/退出状态可从同 R 的原 context/Details 继续看。首页数量不是现实范围；持续状态可查看不等于每天制造新事件。未覆盖概念、已覆盖未过门槛、已发现未展示必须分开。

和顺/广哈的原真实 run `34807883332` 已发生三次模型调用：和顺 Pre、广哈 Pre+Quick。旧终局仍保存为 WAIT/DROP，**原理由仍 CHALLENGED**。有限追加审阅已完成并可读，不再“等待需求管理决定怎么纠错”。它不是重跑33份PDF、不是新的 canonical Funnel、不是 Human 接受，也没有补造和顺 Quick。

追加审阅定位：`docs/readings/stock-business-review-addendum-2026-09-14.md`；Git blob `ea2062655e659ba89b7cdf1c9f5f10ab381850e7`。在 R0 的副本是 `sources/git/ea2062655e659ba89b7cdf1c9f5f10ab381850e7/stock-business-review-addendum-2026-09-14.md`。与原候选精确绑定的挑战必须一并读取，不能仅凭同代码覆盖不同问题/时期的研究。

### P0-B / #366：研究与 Odds 找得回

正式验收：[5662752990](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5662752990)。入口 `docs/ODDS-BOOK.md`，R0 的副本 blob 为 `907427bf8f209d0574115de031811a5242d4664f`。

十个主要找回对象：恒瑞600276、内蒙一机600967、兴业002674、光电600184、三花002050、兆易603986、茅台600519、神华601088、宁德300750、招商600036；研究过但未证明有实际 Odds 的其他对象另列，未丢弃。

已交付声明范围的历史导航、old→new关系、来源/方法资格、Human接受范围、下一复核条件和未定位项。**不是全历史穷尽、全入口自动捕获、持仓表或实时 Watch。** 所有自动 Watch 仍未启用。旧 Inbox 的 HTML/Markdown 不倒造成 typed canonical Odds。

新真实 Odds 或重大方法修订的交付须保留原件、登记原用途索引、追加历史并读回；失败报告 NOT_SAVED / REGISTRATION_INCOMPLETE / PUBLICATION_PENDING 的实际阶段，不为补登记重跑研究。保存、当前有效、Human接受、投资决定、Action五者分开。

### P0-C / #367：仅原公告研究工作流的显式请求入口

工程验收：[5663777795](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5663777795)。复用的是 `saved-disclosure-research` 和原宿主，不是通用 dispatcher。

已实际首次新增 `.github/saved-disclosure-invocations/scan-34601025149.json`，形成 run `34842900705`，event=push、attempt1、head=`aec550e87db0348805afbef6b143e70bacc0e05e`。实际返回 `NO_UNRESERVED_PACKET_IN_SAVED_SCAN`：7个旧问题全部 ALREADY_RESERVED，selected=null、items=[]、formal_research_executed=false。没有新模型调用或研究工作身份。

这是合法去重空执行；不代表7次研究成功，不是 WAIT，也不证明自然新问题闭环已经验完。请求已消耗，不能再拿它做能力测试。

| 已留验收证据 | 精确定位及范围 |
|---|---|
| #365独立主干 CI | 34824181109：3172 passed；正常发布34825373095；详见原回执 |
| #366独立主干 CI | 34832885875：3187 passed；含其改动的后续正常发布34834379602；详见原回执 |
| #367独立主干 CI | 34839115204：3226 passed；正常发布34840238035；详见原回执 |
| 请求提交独立主干 CI | 34842900729 / job103971794775：3226 passed，无pytest skip；不是本次又执行测试 |
| 实际请求运行及ZIP | 34842900705 / artifact10346697946；6,807,354 bytes / 9文件；SHA256 `412b6460d2d69362a7a1d0899a31be8902be74148ba6f24d042fbd7ee918b1eb`；此前真实字节/CRC/内层原件及请求绑定已验 |
| 请求完成后的正常发布 | 34842934852：TRIGGER_RUN_ID=34842900705，R=`e0a2fdb67559f6e31379046ab8bf31af68bf74ad` |
| M0测试/发布 | CI34845243915元数据success；publisher34846493111 / job103983599276，trigger=34845243915，生成R0；不把别的head测试数归给M0 |

上述数字是明确版本的既有验收记录，不是本次归档重跑或未来结果。启动时 skipped 的 publisher 不算发布成功。

## 4. 下一会话能否读、写和发起流程

**仓库能力已打通一条闭环，但下一会话的工具和授权可用性仍须实际检查。** 不再笼统说“只有 Actions 能力”或“官方 GitHub 只能搜索”，也不能反过来保证任何新聊天都有全部权限。

| 能力 | 已知事实 | 下一会话如何确认 |
|---|---|---|
| 读取仓库/ref/Issue/Actions | 本会话已真实调用；历史上也有完整日志、实体artifact读取 | 发现实际 GitHub 工具并读当前 main/R/Issue；失败说明具体边界，不拿交接摘要冒充读过 |
| 写文档/Issue/PR | 既有代码和回执已写入；本次归档另有写后读回 | 合法写回后读精确commit/blob或comment；发现写工具不等于已写成功，不写无意义测试记录 |
| 直接 workflow_dispatch | 本次 GitHub 工具发现没有返回通用 dispatch 动作 | 下一会话重新发现；若有实际动作且原流程合法可调用则优先使用；不要只因workflow YAML支持就声称工具能发 |
| 不依赖 dispatch 的原公告流程 | #367显式first-addition入口已真实验收 | 仅用于已授权、合法且未消耗的原请求；不推广到Stock/Sector或任意workflow |
| 本地完整checkout/原测试环境 | 此前只取得经过字节核验的旧归档和局部材料，不是当前完整工作树 | 另行核实；GitHub读写权限不会自动提供本地checkout、模型secret或SDK环境 |

本次已直接读取 M0 的 `.github/workflows/saved-disclosure-research.yml`（blob `4e9360d7ad13dfb67aadbc755c07519fcfac1567`）与 `src/decision_kernel/runtime/saved_disclosure_invocation.py`（blob `ad0e3967bc494e2145cf4e0a8fbce735a80e778a`）。原自然 workflow_run、原 native manual 路径仍在。

### #367精确调用边界，禁止照抄旧参数

发起新的合法请求之前读届时的 workflow、invocation validator、原 host 和具体 continuation 合同，不在本页生成可直接提交的请求JSON。当前实现至少要求：

- event=push、main、attempt=1；单一精确approved parent；整个activation commit只新增一个普通请求文件，不夹代码/许可/来源等变更。
- 稳定路径为 `scan-<source_run_id>.json` 或 `continue-<原continuation摘要>.json`；路径不能有旧历史，包括删除后重加。
- 请求绑定 source run、当前 R/W 和有效截止；R中的code_commit必须等于approved parent。文档归档使main变化后，不能把旧R直接配到新parent；先等正常发布并实际核对。
- original continuation摘要必须对应主干中的原request；普通 push 自身不是Research许可。
- 调用前查active/queued、已有request/work/run和状态变化；失败或写入不确定先读现场，不盲重试、不换key。
- 仍走原host、来源/许可/准入/Retainer/Funnel；无新问题允许NOOP。技术失败不能包装为WAIT。

因此，对Human的准确说明是：**接入可读写GitHub的会话后，已打通的这条公告研究流程可在原边界内不靠Human搬运来启动；并非所有会话自动获得通用Actions权限。** App能力还取决于实际工具、连接和配置；参见[OpenAI官方应用说明](https://help.openai.com/en/articles/11487775-connected-apps-in-chatgpt)。官方通用说明不替代本项目实际运行证据。

## 5. P0还差什么；下一步直接做什么

1. **先核验新增自然现场。** 阅读当前main/R、两个work-ref、#297/#299最新回执、相关自然source与Research运行。若别的会话已继续施工/执行，验已有现场，不重复。
2. **验自然新问题闭环。** 从真实新的未保留问题，经原来源准备/准入/Pre/必要Quick、结果留存、正常publisher到可读交付。无新问题允许NOOP；显式请求NOOP不能冒充自然新问题案例。缺新run先定位实际状态，不能用盲目手动重跑替代自然验收。
3. **验Brief v1.2真实交付与Human回应。** 读实际交付版本R、来源日期、呈现内容和反馈；按原回应协议写回#299/对应交付记录。已有回应样本保留，不把工程“继续”计成新公司接受；已明确的问题和许可不重复问。
4. **累计5–10个真实合格交易日。** 记录漏看、重复、迟到、用户搬运、错误理由复用、研究增量及停止质量。配置更新日不自动算第1天；过去未记录的读回/通知/反馈不补造。
5. **有具体缺陷再薄修。** 区分展示、数据资格、方法、执行、连接/权限和新能力。按RM处理确实阻断P0的缺口，做Reuse Check、精确测试/审阅/正常发布与产品读回；不为所有UNKNOWN新增工程。

**目前没有待重发的Stock successor或旧公告请求。** 这份交接不是一张Run指令。真正需要Human的账户设置/不可解析范围/新资本决定才交给Human；不能为了保持“持续施工”制造新研究或改排期。未来自然天数和真人反馈尚未发生时如实标待验，不承诺本会话后台继续工作。

## 6. Brief配置与账户侧边界

本次归档准备中已再次只读查询既有任务，未改任务：

```text
name = Decision Kernel Daily Brief v0
id = 6aa28013b7348191a647f2f8e75d6017
enabled = true
presentation = v1.2
schedule = daily 23:10 Asia/Shanghai
updated_at = 2026-09-14T12:32:04.394276Z
last_run_time = 2026-09-13T15:12:09.745150Z
notifications_enabled = false
email_enabled = false
```

查询时尚无晚于v1.2更新的运行记录；后续需重新核验，不能长期沿用这项pending。保留任务唯一ID、名称、日程和只读范围；不重复建任务、不另建提醒器。

主动通知开关是账户侧动作，不在当前任务修改参数中。已告知Human在ChatGPT通知设置为Tasks开启Push或Email；**尚未取得已开启的确认**。任务运行、消息生成、通知送达和已读不是一回事；开关关闭不阻止其余可做的仓库验收，也不证明历史从未送达。下一会话先查状态/已有回应，不要求重复设置。说明依据：[OpenAI Tasks帮助](https://help.openai.com/en/articles/10291617-tasks-in-chatgpt)。

## 7. 未完需求与顺序：准备不等于施工批准

下面是剩余工作导航，不是新排期。完整范围看RM和能力census；开放Issue数量不是剩余功能数量。

| 优先级/归属 | 未完成部分 | 已有部分勿重造 |
|---|---|---|
| P0 #297/#299 | 自然新问题、v1.2可读性/回应、5–10日使用验收 | #365–367和原回应/自然宿主已存在 |
| P1-A #321 | 标准Research/Evidence/receipt留存、独立commit-only；同冻结Research价格重算、provisional→canonical对照 | 交互Full Research和方法入口已有，不伪造Pre/Quick或新Deep框架 |
| P1-A #349-C | 合格价格/typed结果、有效复核条件的实际跟踪及原Brief交付 | Odds Book A/B已交付；不激活受挑战旧梯度，不从HTML造typed结果 |
| P1质量评估 | 来源指令隔离、真实模型行为对照、研究者效果验证 | Method v3和历史/合成检查不等于新样本质量提升 |
| P1-B #364 | 独立Concept/Theme SHADOW的来源家族、历史、重叠与增量价值 | 881/884行业语义不变；已有状态可见性已在A交付 |
| 后续重新triage | Research Asset Re-entry Loop、Early Transition Radar | 已登记但未自动前移；不是#349最小Watch全部已批准/已实现 |
| P2发现/学习 | Industry Inflection、全市场Stock Surprise、Blind-Spot Audit、业务证据覆盖、多周期leader/角色、#331价格结构、#317竞价探针 | 不把价格、行业成员或成交当业务Evidence；不混不同Radar目的 |
| #354 | 全景Reuse/过建审阅及有净收益的最小整理 | 已有预调研可复用；有限只读可并行，生产重构不自动开工 |
| #351及后续 | 完整Home、真实持仓/投后HOLD-ADD-REDUCE-EXIT | 导航可先用；归档不推断交易或持仓 |
| #327/运维债 | 复用知识、RSS连续性、旧capability索引对账、旧PR/one-shot处置 | 台账不是待安装功能表，旧pending不迫使重做已验能力 |

Research Asset Re-entry：[5661242999](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5661242999)。价格表达/安全边际区分：[5661091596](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5661091596)。Early Transition与Industry Inflection：[5665311333](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5665311333)。它们均未改变RM顺序。

**上一回复“可同时准备P1-A设计”只是有限准备方向，不是Human已批准开始#321/#349-C生产实现。** 下一会话可复用已有材料做有界只读准备，不扩成全仓重构或新P0前置；进入P1施工前须由需求管理明确切片、依赖和范围。等待自然使用不意味着P1自动启动。

Full Research的当前docs/process方法为v3；仅在获准的公司研究/局部挑战时读取 `docs/RESEARCH-ENTRY.md` 及所链接方法。它不是runtime/schema v3，效果仍需真实新样本验证。当前工程交接不要求重跑任何公司。

## 8. 不得回到的旧接点

- 不Re-run `34765190284`、`34797952444`、`34807883332`、`34842900705`；不重发 `scan-34601025149.json`，不改其日期/内容/路径重新消耗。
- `source-recovery-v1`、`source-successor-v1`、`source-successor-continuation-v1`均有真实已消耗历史；不再次 `recover-sources=true` / `prepare-sources=true` 或重发旧successor/continuation flag。
- 不重跑600184光电或300183东软以证明接线；不删正文/反证，不用摘要替代必需模型输入，不重新施工page23/容量/旧parser。
- #352–363、#365–367按现有回执复用。#263/#285/#287/#289/#290/#295是隔离或历史材料；#346仅为待比较的可能重复项，不自动合并/关闭。保留分支、失败和原候选。
- 不提升共享限额，不按价格表现修改Belief，不自动Deep/Odds/Watch/Action/买卖/仓位。原项目资源许可不是任何重复执行的空白许可。

原资源授权：[5646037620](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5646037620)。原两家首次业务许可：[5652950925](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5652950925)。不得重复索取已给许可，也不得拿它们跳过当前身份/去重/具体续作检查。

## 9. 本次归档的证明范围

本次任务只新增本页和配套通知，并将精确归档回执追加#297；不改runtime、workflow、registry、Research work、候选或任务。不新增activation文件，不手动dispatch，不为测试能力触发Research。

文档提交可能自然触发既有CI/读取发布；其状态独立记录，不能将“文件已在main”写成“新的P0整体验收通过”。归档文件从main读取，未另行加入current-state用途registry；不要假装R已保留本交接全文。

对新会话最短要求：**先读这两份文件和最新GitHub现场，再消费自然运行与真实反馈；能力可用就直接在原范围内推进，不让Human搬运，也不把缺新事件变成盲目重跑。**
