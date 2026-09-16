# Odds Book v0｜研究过、算过的对象从这里找

Version: odds-book-v0 / 2026-09-16。**NAVIGATION_ONLY / DECLARED_COVERAGE_BACKFILL / NO_AUTOMATION**。

这不是持仓表、实时行情、第二套 Odds 状态或买卖清单。下面保留的是本次找到的实际输出、方法更正和 Human 记录。**保留 ≠ 当前有效 ≠ Human 接受 ≠ 投资决定 ≠ 成交。**

**先看：** 恒瑞、内蒙一机、兴业科技有范围不同的 Human 接受记录；北大荒 9/16 provisional Odds 已进一步做了**利润主导的估值解释修订**，仍未获得 Human 接受，3年10%仍只是工作敏感性；光电旧估值桥受挑战，不能继续用旧梯度；三花、兆易有单独的条件投资决定，不能用旧 Inbox 的模型门槛替代。所有自动 watch 在本表均为**未启用**；除北大荒本次明确记录的9/15 public context外，本表没有重新核验当前价格，不计算距离或宣称触界。

## 1. 总表：最后登记的解释，不按文件时间裁定唯一“最新有效”

价格均为对应结果当时的参考价，**非本日价格**；不自动代表本日行情。没有明确取代关系的模型与 Human 条件并存；接受范围、方法资格和行动分栏。A股用 `.SH/.SZ` 统一导航，原件的 `.SS` 等标识不回写。

| 对象 | 最后找到的 Odds / 方法状态 | 原价格与来源资格 | Human 接受 / 决定 | 下一复核条件及当前处置 | 原件 / 历史 |
|---|---|---|---|---|---|
| 恒瑞医药 **600276.SH** | provisional / ordinal；原风险收益 MIXED；canonical 数值未建立 | 42.93元，9/10；Human supplied、CONTEXT_ONLY | 9/12接受条件价格分布用于决策准备；不是实际购入决定 | 39.6附近重审假设，37–38为条件首笔讨论；仍须核查产品现金、授权完整成本及净现金；**条件留存，watch未启用** | [临时Odds][HR-O] / [接受范围][HR-H] / H1–H3 |
| 内蒙一机 **600967.SH** | 已接受的 provisional / ordinal 为 WEAK / FRAGILE；首笔 NOT METHOD-READY | 14.98元，9/11；public CONTEXT_ONLY | 9/13接受 Research 与该 Odds；明确无投资决定 | 利润质量、现金可分配性和订单兑现需有新证据；没有可激活价格区间；**证据待核验，watch未启用** | [接受与条件计算记录][NM-H] / N1 |
| 兴业科技 **002674.SZ** | 修订后 provisional first-entry review；不把相近价格当旧模型被验证 | 18.61元，9/11；public CONTEXT_ONLY | 9/14接受修订研究及临时条件卡；无投资决定 | 15–17重审、13–13.5条件首笔复核；须核验旧业务衰减、InP规模经济及披露风险；**条件留存，watch未启用** | [修订研究][XY-R] / [接受范围][XY-H] / X1–X2 |
| 北大荒 **600598.SH** | 利润主导的 provisional / ordinal reverse-underwriting 修订：核心 terminal PE 收敛为21–23x，24x仅较好市场表达；当前9.6–10.6亿元正常化利润带无增长证据，12.33主要预付未证明的利润增长 | 12.33元，9/15完成交易日；PUBLIC_MULTI_SOURCE_CONTEXT_ONLY，非canonical market state；本次修订未刷新价格 | **NOT ESTABLISHED**；未记录Human接受、投资决定或仓位 | 11.0–11.3重审；9.8–10.3条件首笔复核；9.3–9.6为更优Odds复核；3年10%仅工作敏感性；**watch未启用** | [修订Odds][BD-R] / [前版Odds][BD-O] / BA1–BA2 |
| 光电股份 **600184.SH** | 原 UNFAVORABLE 是旧条件输出；研究/估值桥 CHALLENGED，旧梯度 NOT ACTION-READY | 19.98元，9/11；PUBLIC_NON_QUALIFIED_CONTEXT_ONLY | 原JSON为NOT_RECORDED；随后Human要求保留，当前NOT_ACCEPTED_YET，不是REJECTED | 先修经营/估值桥与单位、期限和完整下行；**旧梯度不激活，watch未启用** | [旧JSON][GD-O] / [方法勘误][GD-C] / [Human反馈][GD-H] / G1–G3 |
| 三花智控 **002050.SZ** | 9/11保存Inbox为 INSUFFICIENT_ODDS；Human core-first条件另存 | 34.87元，9/11；保存HTML/Markdown，**本次未typed复验** | 9/3已有约30元条件首笔决定；不等于接受旧总公司概率 | 约30元且核心经营/现金/资本回报未坏；原模型≤29.56不是Human首笔；**条件留存，watch未启用** | [保存输出][INBOX] / [Human条件][SH-H] / P1、P2 |
| 兆易创新 **603986.SH** | 9/11保存Inbox为 INSUFFICIENT_ODDS；Human duration-thesis条件并存 | 371.32元，9/11；保存输出，**本次未typed复验** | 9/3已有320–335条件首笔决定；原cardinal分布NON-DRIVING | 约350先重审期限、毛利/现金与常态盈利，再判断320–335；模型≤330.69不能替代；**条件留存，watch未启用** | [保存输出][INBOX] / [Human条件][GY-H] / P1、P2 |
| 贵州茅台 **600519.SH** | 9/3报告INSUFFICIENT，9/11保存Inbox为ACCEPTABLE；变化原因未独立建立 | 1275.16元，9/11；保存输出，**本次未typed复验** | 本次所查范围未定位独立的Human概率接受或投资决定 | 先取得原typed结果与精确研究/行情关系再作当前数值使用；不把旧关注标签当今日请求；**资格待复核，watch未启用** | [9/3记录][HISTORY] / [9/11输出][INBOX] / P1、P2 |
| 中国神华 **601088.SH** | 9/3、9/11保存标签均为INSUFFICIENT；不是已验证收益结论 | 47.51元，9/11；保存输出，**本次未typed复验** | 本次所查范围未定位独立Human接受/决定 | 原模型≤35.37仅作历史阈值；须先验typed结果、期限和适用性，不生成第一笔；**资格待复核，watch未启用** | [9/3记录][HISTORY] / [9/11输出][INBOX] / P1、P2 |
| 宁德时代 **300750.SZ** | 9/3旧ACCEPTABLE留存；9/4后通用数值资格退出，numerical Odds withheld | 349.5元，9/3历史运行语境；不是当前价格 | 本次所查范围无投资决定；资格退出不等于否定公司业务 | 按利润/现金/资本回报证据重审；不激活旧通用价格门槛；**历史/证据入口，watch未启用** | [原运行报告][HISTORY] / [资格退出][CATL] / C1–C2 |
| 招商银行 **600036.SH** | 旧通用场景曾错误重获Inbox资格；后来明确退出当前数值入口 | 9/1@40.86线索尚未定位完整原执行包，不补造 | 本次所查范围未定位独立Human接受/投资决定 | 旧场景/时间方法只供历史复核；新公告Pre不自动修复旧Odds；**历史/待定位，watch未启用** | [原治理失败及修复报告][HISTORY] / B1–B2 |

三花/兆易原checkpoint写“尚未执行”，恒瑞/内蒙/兴业的接受记录没有交易；北大荒两个9/16 Odds版本均明确 Human acceptance NOT ESTABLISHED。这些陈述只覆盖对应checkpoint/结果。本次没有重新检查券商或完整Action历史，**不得推断后来一直没有成交，更不得推断持仓**。

## 2. 变迁：先有原件，再解释 old → new

下列ID是本登记簿的导航行号，不是新execution_id、模型运行或Kernel状态。一次运行可包含多只证券；接受、勘误、留存和模型计算不是同一种事件，不能把本表行数当调用次数。

| 行号 | 原时间 / 对象 | 找到的历史及后续关系 | 变化性质 / 未验证项 |
|---|---|---|---|
| P1 | 9/3，三花/茅台/神华/兆易 | 原手动验证run33743787675的已保存交接记录列出36.3/1298.88/47.78/383.2元，均INSUFFICIENT | **原运行报告文字**；不是本次下载该run的typed输出或重算 |
| P2 | 9/11，同四家公司 | run34601025149实际保存summary：34.87/1275.16/47.51/371.32元；茅台ACCEPTABLE，其余INSUFFICIENT | **保存输出**；未证明两次Research/方法/期限完全相同，所以不把标签变化归因PRICE_ONLY |
| C1 | 9/3，宁德 | 同run33743787675报告349.5元、ACCEPTABLE | 历史机械输出，不能倒推现在有数值资格 |
| C2 | 9/4，宁德 | 后续Full Research明确旧generic numerical资格退出，保留行业/公告用途 | **DEQUALIFICATION / METHOD_REVIEW**；不是新买卖决定 |
| B1 | 9/1、9/3，招商 | 9/1@40.86是需求台账给出的执行线索；9/3交接报告记录旧场景被错误重新放入Inbox | 9/1完整原件尚未定位；9/3是保留的失败说明，不能复活为当前结果 |
| B2 | 9/3，招商 | #120改为显式生产名单，原验证run33743787675确认CMB不在Human Inbox | **ELIGIBILITY_CORRECTION**；旧fixture继续保留，不修改历史输出 |
| H1 | 9/11归档，恒瑞 | 原provisional-odds.json冻结42.93参考价、三年条件世界及ordinal判断，保留行情失败 | **PROVISIONAL / ORDINAL**，不是canonical数值结果；整套研究材料见原归档入口 |
| H2 | 9/12，恒瑞 | 新Human记录接受条件分布，39.6复核和37–38首笔讨论用途分开 | **HUMAN_ACCEPTANCE_CHANGE**；没有证据说明此事件生成新Research或成交 |
| H3 | 9/13，恒瑞方法回放 | 后续研究入口要求完整下行、风险与经营/估值假设保持可见 | **METHOD_REVIEW**；不撤回或扩大H2的实际接受范围，不把算术回放当新投资结果 |
| G1 | 9/13，光电 | 原工作分支JSON留存UNFAVORABLE与提议价格梯度，原human_acceptance=NOT_RECORDED | **PROVISIONAL / ORDINAL**；原分支与JSON字节不改 |
| G2 | 9/13，光电 | 主干勘误指出亿元/bn十倍单位错误及估值桥受挑战，旧首笔梯度暂停复用 | **METHOD_CORRECTION / CHALLENGE**；并未产生替代的新合理价 |
| G3 | 9/13，光电 | Human要求未接受的Odds也须保留，NOT_ACCEPTED_YET | **HUMAN_RESPONSE / RETENTION**；不是拒绝公司或接受旧梯度 |
| N1 | 9/13，内蒙一机 | 接受记录保留Research与14.98元WEAK/FRAGILE ordinal结论、条件要求及不采用数值Odds的理由 | **ACCEPTANCE_CHECKPOINT**；完整原Research输入/计算包尚未在本次盘点定位，不由此补造 |
| X1 | 9/14，兴业科技 | 修订稿保留“可修复旧业务+期权”的旧解释被挑战，改为旧业务衰减×新业务独立成长 | **REINTERPRETATION / METHOD_CORRECTION**；原早期草稿完整包未定位，相近13元讨论不等于同一模型 |
| X2 | 9/14，兴业科技 | Human接受修订研究及临时条件卡；原记录18.61参考价、13–13.5条件首笔复核 | **HUMAN_ACCEPTANCE_CHANGE**；公司专属三年10%门槛仍非单独Human确认，无投资决定或Action |
| BA1 | 9/16，北大荒 | 复用已保存税制/税后现金续作，不重跑Pre/Quick；以9/15完成交易日12.33 public context做provisional reverse-underwriting并保存 | **PRICE_ONLY / PROVISIONAL / ORDINAL**；3年10%为工作敏感性而非Human专属要求；cardinal/canonical Odds、Human接受、仓位与watch均未建立 |
| BA2 | 9/16，北大荒 | 同一12.33价格与冻结Research下，复核历史估值后把21–23x收敛为核心市场表达，24x降为较好上沿；同时将“9.6–10.6亿元利润带尚无增长证据”提升为主要Odds轴 | **VALUATION_INTERPRETATION / ODDS_REVISION / NOT_PRICE_ONLY**；12.33改判为主要预付未证明利润增长；9.8–10.3为条件首笔复核、9.3–9.6为更优Odds复核；Human接受仍未建立 |

H3的方法回放：[原回放与证明范围][REPLAY]。G3和B1的需求线索：[Odds Book需求补充][GD-H]。北大荒前版：[前版Odds][BD-O]；利润主导修订：[修订Odds][BD-R]。后来的主张必须指向其实际版本，不向过去回填。

## 3. 本轮找回范围与仍未找到的材料

读取基线：原A交付 M=`49b7fc999953977832afef67420fd693797e451d`、R=`49089753bdeb9a8660d2d74f4747dc749ce7a313`；施工前发现主干新增兴业档案，另固定 M2=`8e045ef755ade568aaad33d50a5a36aae04b19ed`。M→M2只有AGENTS及三份兴业/转型方法文档，不把它们伪装成原R已有内容。此书在 9/16 追加北大荒 BA1 与 BA2；各原件由正常publisher在新的同R中按显式purpose留存。

原找回盘点覆盖十家公司；9/16 新增的是**实际新计算并留存的北大荒 Odds及其修订**，因此当前总表仍为十一家公司。这仍不是全仓白名单或全历史穷尽。不为凑满总表重算历史。

| 覆盖层 | 已找到什么 | 尚未证明 / 后续处置 |
|---|---|---|
| 原结果/方法原件 | 恒瑞provisional JSON；光电精确旧分支JSON及勘误；兴业修订文档；北大荒9/16前版Odds与利润主导revision | 不认证其经济真值，不把归档内容全部升级为Kernel Research；北大荒仍非canonical/cardinal Odds |
| Human原文/checkpoint | 恒瑞、内蒙、兴业、三花、兆易 | 接受范围不同；北大荒两版Human接受均未建立；内蒙完整原Research/计算包、兴业更早草稿仍未定位；后续Action未全查 |
| 已保存运行输出 | 原R中9/11 Inbox Markdown/HTML | 原运行未保存typed numeric result；不能从文案重建一个声称通过原validator的数值结果 |
| 原运行报告 | 9/3交接中run33742568111/33743787675及资格治理历史 | 本轮未逐个下载这些旧run原始artifact；精确原输出/usage缺口继续保留 |
| 待定位执行线索 | 招商9/1@40.86；光电未落分支的其他旧梯度 | 线索不变成新snapshot；找到原件后追加，不以今天重算补过去 |

以下已研究/方法对象也没有被悄悄丢掉，但本轮未取得足够依据把它们计成新的实际Odds计算；**北大荒不再属于这一组**：

| 对象 | 已有入口 / 当前登记处置 | 不作的推断 |
|---|---|---|
| Micron MU | 既有Decision Book与Human WAIT/NO_ACTION；保留方法/条件分析入口 | 不把美股暂不购买约束当公司看空；旧事件日期未重新核验；未建立生产美国数值Odds |
| 圆通速递600233.SH、美的000333.SZ、天智航688277.SH | 既有Research/方法及Human记录见[原Decision Book][BOOK]和同R用途索引 | 有研究或条件敏感性不等于已经实际完成一次合格Odds；不伪造概率/当前交易 |
| 苏垦601952.SH、和顺603353.SH、广哈300711.SZ、东软300183.SZ | 已有Pre/Quick/追加审阅等按各自原范围保留 | 不用Research完成计数补Odds计数；和顺/广哈错误终局与追加审阅同时保留 |
| 厦门钨业600549.SH及纯合成/方法回放 | audit/method区域可查，不进入默认有效Odds清单 | 不是当前portfolio或被Human采用的真实数值结果 |

其余分支、已过期artifact、未登记聊天和全部historical commits尚未穷尽；状态为**DECLARED_COVERAGE_BACKFILL**，不是“已找回所有历史”。后续发现真实用于Human研究/决定的旧输出，即使名为dogfood，也追加到相应历史，不能仅凭目录名排除。

## 4. 以后怎样登记，才不会又丢失

复用 `current_state/registry.json` 的既有purpose引用、原件文件及Git历史，不新增canonical Odds registry。**每次实际用于决策准备的Odds计算或重大方法修订，正常交付必须同时完成以下动作，不再等待Human追问是否记录：**

1. 先保留原输入/结果/执行或计算记录；沿既有留存协议绑定证券、Research/Belief版本、价格/日期/authority、方法、期限、剩余UNKNOWN和真实时钟。不改旧结果，不生成不存在的execution_id、原始日志或Human原话。
2. 在既有purpose索引登记精确原件路径/ref/blob，并追加本书的历史关系；并存、superseded、challenged、de-qualified分别说清。新接受事件只作用于被接受的精确版本，不自动继承给新结果。
3. 写入后按返回commit读回；正常fixed-reading发布再核对同R入口及原件。结果已经生成但写入/登记/发布未完成，就报告 **NOT_SAVED / REGISTRATION_INCOMPLETE / PUBLICATION_PENDING** 对应事实，不声称完整交付。先查现场，不能为补登记重跑研究。

这是本版的交互登记/交付合同，**不是已部署的全仓自动扫描器**。现有日常Inbox仍通过原运行→原件→fixed-reading历史保存；每份新R的该lane是实际最新已保存输出入口，不因本书的旧日期被隐藏。本书是交互维护的导航投影，未登记新对象的缺口必须明示；自动跨所有入口的完整捕获需各入口真实接入验收，不能仅凭本段称已建立。

`PRICE_ONLY`只用于确证同一冻结Research、方法、期限口径而仅合格价格变化的情况；否则写EVIDENCE/REINTERPRETATION/METHOD_CORRECTION/AUTHORITY_CHANGE/HORIZON_CHANGE/HUMAN_ACCEPTANCE_CHANGE或UNKNOWN/MIXED，不能从标签变化猜原因。

## 5. 跟踪处置与权限

v0记录边界和前提、方便找回，**WATCH_NOT_ENABLED**。没有后台新价格获取、距离计算、提醒投递、自动重算、Research重开、Deep或买卖/仓位动作。北大荒9/16两版只是本次交互的显式价格/Odds计算与解释修订，不是持续监控。条件留存不是监控登记，文件存在不是后台有人盯。

后续获准的watch复用既有渠道；有合格价格、可比且仍有效的边界才能比较。“接近”没有已保存定义时只展示事实距离，不自设统一5%/10%。价格触界只是复核机会，不证明业务前提仍在。受挑战/失效/不适用的旧梯度不能激活；ordinal条件不硬塞要求cardinal概率的数值函数。

本书不签署或撤回Human投资决定，不代表Kernel对研究真值作认证。未来新版本仍保留本版Git历史与全部原件引用；不删除历史来制造简洁。

## 原件索引（固定版本；同R用途索引另保留阅读副本）

[HR-O]: https://github.com/auguspp/decision-kernel/blob/49b7fc999953977832afef67420fd693797e451d/docs/readings/hengrui-600276-research-odds-2026-09-11/provisional-odds.json
[HR-H]: https://github.com/auguspp/decision-kernel/blob/49b7fc999953977832afef67420fd693797e451d/docs/decisions/600276-hengrui-human-first-entry-2026-09-12.md
[NM-H]: https://github.com/auguspp/decision-kernel/blob/49b7fc999953977832afef67420fd693797e451d/docs/decisions/600967-neimengyiji-human-research-odds-acceptance-2026-09-13.md
[GD-O]: https://github.com/auguspp/decision-kernel/blob/9cd072a8e8b5ec1b5fd88e7bfcf9e1d6ae2cd21a/docs/readings/600184-electro-optic-provisional-odds-2026-09-13.json
[GD-C]: https://github.com/auguspp/decision-kernel/blob/49b7fc999953977832afef67420fd693797e451d/docs/readings/600184-research-method-review-2026-09-13.md
[GD-H]: https://github.com/auguspp/decision-kernel/issues/349#issuecomment-5652172247
[XY-R]: https://github.com/auguspp/decision-kernel/blob/8e045ef755ade568aaad33d50a5a36aae04b19ed/docs/readings/002674-xingye-full-research-revision-2026-09-14.md
[XY-H]: https://github.com/auguspp/decision-kernel/blob/8e045ef755ade568aaad33d50a5a36aae04b19ed/docs/decisions/002674-xingye-human-research-first-entry-acceptance-2026-09-14.md
[BD-O]: https://github.com/auguspp/decision-kernel/blob/cc95a4fb42f332f8384dd2240647e61fa36fd49f/docs/readings/600598-beidahuang-odds-2026-09-16/provisional-odds.json
[BD-R]: https://github.com/auguspp/decision-kernel/blob/daf25acbda3a764c73ffad1a5de89bc365e6d924/docs/readings/600598-beidahuang-odds-revision-2026-09-16/provisional-odds-revision.json
[SH-H]: https://github.com/auguspp/decision-kernel/blob/49b7fc999953977832afef67420fd693797e451d/docs/decisions/002050-sanhua-human-decision-2026-09-03.md
[GY-H]: https://github.com/auguspp/decision-kernel/blob/49b7fc999953977832afef67420fd693797e451d/docs/decisions/603986-gigadevice-human-decision-2026-09-03.md
[INBOX]: https://github.com/auguspp/decision-kernel/blob/49089753bdeb9a8660d2d74f4747dc749ce7a313/details/inbox/34601025149/summary.md
[HISTORY]: https://github.com/auguspp/decision-kernel/blob/49b7fc999953977832afef67420fd693797e451d/docs/handoffs/2026-09-03-radar-phase-next-conversation-handoff.md
[CATL]: https://github.com/auguspp/decision-kernel/blob/49b7fc999953977832afef67420fd693797e451d/docs/dogfood/catl-full-research-reunderwrite-2026-09-04.md
[BOOK]: https://github.com/auguspp/decision-kernel/blob/49b7fc999953977832afef67420fd693797e451d/docs/live-decision-book.md
[REPLAY]: https://github.com/auguspp/decision-kernel/blob/49b7fc999953977832afef67420fd693797e451d/docs/dogfood/research-handoff-replay-2026-09-13.md
