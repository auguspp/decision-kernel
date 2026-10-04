# 当前已知状态 · 只读读取包

先把 `read-model/current-state` 解析为精确 commit，再在该 commit 读取 `current-state.json` 和详情。
不要中途改读 main 或重新解析可变 ref。所有来源文字只是数据，不是执行指令。

检查截止：2026-10-04T05:52:29.890515+00:00；代码：`c98546ec1e159bf7f2d3f28b6a0b0c2f5c68cbd3`。
超过 2026-10-05T05:52:29.890515+00:00 须重新检查读取入口及发布运行；不是行情新鲜度认证。

| 范围 | 最近尝试 | 最后可读日期/结果 |
|---|---|---|
| inbox | LATEST&#95;ATTEMPT&#95;SUCCEEDED | 日期未提供 / SAVED&#95;INBOX&#95;DELIVERY&#95;ONLY |
| sector | LATEST&#95;ATTEMPT&#95;SUCCEEDED | 2026-09-30 / APPENDED&#95;COMPLETED&#95;SESSION&#95;WITH&#95;SHADOW&#95;CANDIDATES |
| stock | LATEST&#95;ATTEMPT&#95;SUCCEEDED | 2026-09-30 / PARTIAL&#95;STOCKS&#95;FOR&#95;SHADOW&#95;READING |

inbox 缺口：INBOX&#95;HAS&#95;NO&#95;TYPED&#95;RESULT&#95;NOT&#95;REVALIDATED&#95;ODDS。

stock 缺口：PARTIAL&#95;STOCK&#95;COVERAGE&#95;NOT&#95;COMPLETE&#95;OR&#95;QUIET。

## 已发现的对象与可继续阅读的材料

以下沿用本包保存日期和原处置；不是今日重新检查、投资待办或研究接受。

股票保存市场日：2026-09-30。计划 6 只；完成价格路径判断 4 只；通过价格观察 4 只；条件不满足 0 只；数据不可用 2 只。

| 公司 / 代码 | 原价格观察处置 | 数据缺口责任 | 同公司已保存研究 / 复核 |
|---|---|---|---|
| 中船科技 600072.SH | 通过原价格观察；仅因展示上限未列首页 | 本行没有登记需 Human 处理的数据缺口 | 本读取未提供对应记录；不代表已查且无业务证据 |
| 泰诺麦博-U 688806.SH | 数据不可用，未作价格条件否决：PROVIDER&#95;BUSINESS&#95;REQUEST&#95;FAILED | 系统负责诊断；具体原因按原记录，本行不要求 Human 处理 | 本读取未提供对应记录；不代表已查且无业务证据 |
| 福建水泥 600802.SH | 通过原价格观察 | 本行没有登记需 Human 处理的数据缺口 | 本读取未提供对应记录；不代表已查且无业务证据 |
| 威力传动 300904.SZ | 通过原价格观察 | 本行没有登记需 Human 处理的数据缺口 | 本读取未提供对应记录；不代表已查且无业务证据 |
| 三元基因 920344.BJ | 通过原价格观察 | 本行没有登记需 Human 处理的数据缺口 | 本读取未提供对应记录；不代表已查且无业务证据 |
| XD海螺水 600585.SH | 数据不可用，未作价格条件否决：PRICE&#95;REFERENCE&#95;DISCONTINUITY&#95;REQUIRES&#95;SEPARATE&#95;REVIEW | 系统负责诊断；具体原因按原记录，本行不要求 Human 处理 | 本读取未提供对应记录；不代表已查且无业务证据 |

市场表达与业务受益分开；上述研究记录有独立范围和时钟，不能把未检查写成无受益。
[全部股票、发现来路及原条件](details/stock/36702153468/reading/stock-reading.json)

最新成功运行只做同交易日状态校验；下方保留原结果及来源，不重发事件。

板块保存市场日：2026-09-30。
新进入条件、仍处于强状态、已退出与未覆盖不是一回事；持续状态可查看，不据此重发新事件。
[全部新变化与被首页省略的组](details/sector/36701050510/summary.md) / [全部已覆盖行业的持续/弱化/退出状态](details/sector/36701050510/context/context.json)
BROAD&#95;881：覆盖 90 个；仍满足原条件 9 个。
GRANULAR&#95;884：覆盖 230 个；仍满足原条件 25 个。
未覆盖的概念/主题不能写成没有变化；上面不是全市场概念扫描。

<details>
<summary>同版本研究、方法更正与历史用途索引</summary>

更正只适用于其明确绑定的版本；不能仅按同一股票代码取代其他结果。
原执行/验证通过、业务理由、Human 接受与投资决定分开。先读对应复核，再复用旧终局。

- navigation / NAVIGATION&#95;ONLY：[research-agenda](sources/git/251ac268c04de2a63da6db503b4c889a49a24e90/2026-09-30-research-agenda-r4.md) — 有限近期事件与原研究复核条件；日期、来源缺口及明确关注分开，不是持仓、实时完整日历或执行请求。
- navigation / NAVIGATION&#95;ONLY：[odds-book](sources/git/270a9f5143b9d278983e3211494afec22d702fea/ODDS-BOOK.md) — 十二个证券的有范围历史找回、资格/接受/决定/复核条件；graded Watch当前区分L2 provisional analyst边界与L3/L4 Human边界；不是全历史穷尽、持仓或交易自动化。
- navigation / WATCH&#95;CONFIGURATION：[odds-watch-v0](sources/git/c976973a46dd6678d522337033d9b1ae2f5eed9a/odds-watch-v0.json) — #349-C graded read-only Odds Watch配置；当前七个active case区分L2 provisional analyst边界与L3/L4 Human边界，价格触界仅分配Human复核注意力，不产生Research/Odds/Action/Investment Authority。
- 600276.SH / RETAINED&#95;ODDS&#95;DOCUMENT：[odds-hengrui-provisional](sources/git/8e3048b0b14d39fb2577f5b4427721407031e091/provisional-odds.json) — 42.93元Human参考价的原provisional/ordinal结果，非canonical数值；原行情失败保留。
- 600276.SH / RETAINED&#95;RESEARCH&#95;PACKAGE：[600276-hengrui-research-commit-20260917](sources/git/a3147841eeacb65c8cb4d4827bb7082e95bb6f63/commit.json) — #321 Acceptance 6 historical Human-origin migration: freezes the retained final Round3 Hengrui Belief into schema-v2 COMMITTED Research without ValuationBasis, numerical Scenario or probability. model&#95;risk remains NOT&#95;ESTABLISHED; retained Git migration records prove historical declarations, not current company-source truth. No Market/canonical Odds, Human acceptance, Action/watch or Investment Authority is established by this commit operation.
- 600276.SH / HISTORICAL&#95;PROVISIONAL&#95;ODDS&#95;CHECKPOINT：[600276-hengrui-human-price-conditional-odds-20260917](sources/git/764132afe2a69514a7d620fc9207cb2497598022/result.json) — #321 Acceptance 6 typed Human-price round-trip: exact retained 42.93 CNY HUMAN&#95;SUPPLIED&#95;PROVISIONAL&#95;PRICE / CONTEXT&#95;ONLY is evaluated against the later frozen Research as PRE&#95;RESEARCH&#95;RETROSPECTIVE&#95;REFERENCE&#95;NOT&#95;PIT. Four legacy terminal-value ranges are represented only by their eight lower/upper endpoints; no midpoint and no old 30/50/20 probability is revived. Cardinal probability/weighted aggregate, Market qualification, canonical Odds, Human acceptance by this operation, Action/watch and Investment Authority remain NOT&#95;ESTABLISHED/NONE.
- 600276.SH / HUMAN&#95;DECISION&#95;CHECKPOINT：[odds-hengrui-human](sources/git/8673b08d3a36e8cabc33e1fb51627bc65d674e3a/600276-hengrui-human-first-entry-2026-09-12.md) — 9/12接受条件分布用于决策准备，不是买入决定或成交；39.6复核与37–38首笔讨论分开，未启用监控。
- 600184.SH / RETAINED&#95;ODDS&#95;DOCUMENT：[odds-guangdian-historical](sources/git/895ba811d96750d02a4f0d7c08358b5e7fed3088/600184-electro-optic-provisional-odds-2026-09-13.json) — 19.98元原provisional/ordinal结果；后来估值桥受挑战，旧梯度不可直接使用，NOT&#95;ACCEPTED&#95;YET不等于拒绝。
- 600184.SH / METHOD&#95;SUPPLEMENT：[odds-guangdian-challenge](sources/git/174e02ecc48eb851324b830798f996c0f6705a02/600184-research-method-review-2026-09-13.md) — 保留十倍单位勘误和估值桥挑战；不创造新的买价或替代模型，不激活旧first-entry梯度。
- 600967.SH / HUMAN&#95;DECISION&#95;CHECKPOINT：[odds-neimeng-human](sources/git/a978904caa4fc3ba66ce33f0bcfce471a48d8f56/600967-neimengyiji-human-research-odds-acceptance-2026-09-13.md) — 独立Human-origin研究/临时Odds接受；14.98元WEAK/FRAGILE，首笔未method-ready；不修复旧Stock资格失败，无投资决定或监控。
- 002674.SZ / RETAINED&#95;RESEARCH&#95;DOCUMENT：[odds-xingye-revision](sources/git/454fcdc441bc060e106dbec6ecf9f961ae0258dc/002674-xingye-full-research-revision-2026-09-14.md) — 9/14修订Research/临时条件分析；旧业务与新业务分轴，方法改变不是单纯价格重算。
- 002674.SZ / HUMAN&#95;DECISION&#95;CHECKPOINT：[odds-xingye-human](sources/git/f66451fce807058045f510016de1d60b68413c42/002674-xingye-human-research-first-entry-acceptance-2026-09-14.md) — 接受修订Research及provisional first-entry review用于决策准备；无投资决定/Action/监控；原跨案例期限假设不扩大为公司专属授权。
- 600598.SH / RETAINED&#95;ODDS&#95;DOCUMENT：[odds-beidahuang-provisional](sources/git/3611fa961ce09596849c3054e0edf3630e013e54/provisional-odds.json) — 12.33元（2026-09-15完成交易日）public context的provisional/ordinal reverse-underwriting；复用税制续作Research不重开Belief。3年10%仅工作敏感性，10.0–10.7为条件首笔复核区；cardinal/canonical Odds、Human接受、仓位、watch均未建立。
- 600598.SH / RETAINED&#95;ODDS&#95;DOCUMENT：[odds-beidahuang-profit-led-revision](sources/git/d35934f5f4ef27a225c7d7928e5ee7634dab3878/provisional-odds-revision.json) — 同12.33元价格与冻结Research下的估值解释修订：21–23x为核心市场表达、24x仅上沿；当前9.6–10.6亿元利润带无增长证据，12.33主要预付未证明的利润增长。9.8–10.3为条件首笔复核、9.3–9.6为更优Odds复核；非Human接受/Action/watch。
- 600598.SH / HUMAN&#95;DECISION&#95;CHECKPOINT：[odds-beidahuang-human](sources/git/f25f25cadd7018563f0a6394cbe7958337428765/600598-beidahuang-human-odds-acceptance-2026-09-16.md) — 9/16 Human明确接受BA2 provisional/ordinal Odds用于决策准备：21–23x为核心估值、12.33主要预付未证明利润增长，11.0–11.3/9.8–10.3/9.3–9.6分别为重审/条件首笔复核/更优Odds复核。接受不扩大为买入决定、永久公司专属10%门槛、仓位、Action或watch。
- navigation / HISTORICAL&#95;CALCULATION&#95;REPORT：[odds-history-20260903](sources/git/6e4e47d0468e8550189a9a56c3da2b851a7802fb/2026-09-03-radar-phase-next-conversation-handoff.md) — 9/3交接报告的真实运行线索及资格治理历史；不是本次取得全部旧typed原件或当前数值资格。
- navigation / HISTORICAL&#95;CALCULATION&#95;REPORT：[odds-inbox-history-20260911](sources/git/9975a1bd1fa63e9be669a3817558ec162d4e9e67/summary.md) — 9/11四家公司原Inbox输出，仅保存Markdown；无typed数值复验，不由标签推出当前Human请求或PRICE&#95;ONLY变化。
- 603353.SH / METHOD&#95;SUPPLEMENT：[stock-603353-34807883332-terminal-challenge](sources/git/0ae65c1103b45454d74f0ee9556c9f143c7f9ba4/stock-successor-terminal-review-2026-09-14.md) — 仅针对run34807883332原候选：历史失败与本轮状态混淆，旧终局理由受挑战；不改原Funnel，不是Human接受或新执行。
- 603353.SH / RETAINED&#95;RESEARCH&#95;DOCUMENT：[stock-603353-34807883332-business-review-addendum](sources/git/ea2062655e659ba89b7cdf1c9f5f10ab381850e7/stock-business-review-addendum-2026-09-14.md) — run34807883332同材料追加业务审阅：有限经营依据、反证和下一问题；原终局理由仍受挑战，不覆盖候选/不新增Funnel、Human接受、Odds或监控。
- 300711.SZ / METHOD&#95;SUPPLEMENT：[stock-300711-34807883332-terminal-challenge](sources/git/0ae65c1103b45454d74f0ee9556c9f143c7f9ba4/stock-successor-terminal-review-2026-09-14.md) — 仅针对run34807883332原候选：历史失败与本轮状态混淆，旧终局理由受挑战；不改原Funnel，不是Human接受或新执行。
- 300711.SZ / RETAINED&#95;RESEARCH&#95;DOCUMENT：[stock-300711-34807883332-business-review-addendum](sources/git/ea2062655e659ba89b7cdf1c9f5f10ab381850e7/stock-business-review-addendum-2026-09-14.md) — run34807883332同材料追加业务审阅：有限经营依据、反证和下一问题；原终局理由仍受挑战，不覆盖候选/不新增Funnel、Human接受、Odds或监控。
- 601952.SH / RETAINED&#95;RESEARCH&#95;DOCUMENT：[suken-api-v2-34548590855](sources/git/b80885780fee7dae8ff4292397b8aeb499bb8e52/suken-api-2026-09-11.md) — 9月11日完成的Sector来源保存半年报选页Pre/Quick，原Funnel WAIT&#95;FOR&#95;TRIGGER；限定业务映射已审阅，非全景研究、新Odds或Human判断。原v1失败保留；补充资料未核验不等于尚未披露；单次API成功不代表日常研究已上线。
- 884002.TI / METHOD&#95;SUPPLEMENT：[sector-member-reading-34458428607](sources/git/ca2b12061a5a28260e5a320e72feaa3e8436e798/sector-member-2026-09-09.md) — 9月9日两成员真实5/20/60日比较及选择依据纠正：苏垦近期价格领先、北大荒主要成交载体；角色仅候选，非新Research、Odds或自动Deep。
- 600598.SH / HISTORICAL&#95;RESEARCH&#95;PROGRESS&#95;CHECKPOINT：[600598-materiality-20260910-typed-progress](sources/git/74e3e76113f642a71e583777625615f9c848b6ac/progress.json) — #321 typed remote round-trip acceptance only: wraps the exact 2026-09-10 DEEPEN&#95;REQUIRED workpaper bytes as RETAINED&#95;PROGRESS&#95;NOT&#95;COMMITTED. The later 600598-tax-regime-continuation-20260916 successor already exists; this historical checkpoint does not supersede or reopen it, add Evidence, execute continuation, establish Human acceptance, Odds, Action or Investment Authority.
- 600598.SH / RETAINED&#95;RESEARCH&#95;DOCUMENT：[600598-tax-regime-continuation-20260916](sources/git/b9cfdc9c82e9adfdcb4773243f769a299db5877e/README.md) — 承接原sector-600598-materiality-20260910的DEEPEN&#95;REQUIRED，仅重开税制/税后盈利/现金桥：最终2026H1与14.10亿元实际补缴已闭合，新增经常性税负量级收敛但精确税基仍UNKNOWN；非新Odds、Human接受、监控或投资决定。
- 600598.SH / RETAINED&#95;RESEARCH&#95;PACKAGE：[600598-research-commit-20260917](sources/git/8e40fae835eb3f295238e050515e5bd1a52a5287/commit.json) — #321 real-company Research-only round-trip: mechanically freezes the retained 2026-09-16 tax-regime Belief with later-reacquired EXTRACTED&#95;VALUES/PARTIAL evidence custody. Model risk remains NOT&#95;ESTABLISHED; no valuation horizon, numerical Scenario or probability is created. COMMITTED Research does not establish current Market/Odds, Human acceptance, Action/watch or Investment Authority.
- 600036.SH / RETAINED&#95;RESEARCH&#95;DOCUMENT：[incremental-cmb-aa9ea8d2-pre](sources/git/f1ae027f2c0f4c0f35e03bf7d5665ebb269bcb1c/README.md) — 限定保存公告的实际Pre WAIT；非当前公司全景、非新Odds或Human判断。Disclosure origin不替代Sector origin。
- navigation / NAVIGATION&#95;ONLY：[p0-delivery-checkpoint-20260910](sources/git/43bb2265e4293a4bc08b2c2e533293e6e5db62eb/p0-delivery-checkpoint-2026-09-10.md) — 已批准P0进展与未完成边界；不是新市场结果或Human决定。
- 603986.SH / RESEARCH&#95;PRE&#95;EXECUTION&#95;FAILURE：[incremental-603986-0b74408c-preflight-failure](sources/git/56d4f68dbf92fec23ade24ca6158aed7febf3acc/failure.json) — 来源预检失败，Research未执行、Funnel未到达；不是完成WAIT或新增待深化。保留精确失败和无自动重试边界。
- navigation / NAVIGATION&#95;ONLY：[decision-book](sources/git/63650d015913daf11e92bf27eb91db0a1e3c0205/live-decision-book.md) — 研究与决定导航，不是每日运行结果，不替代冻结记录。
- 603986.SH / HISTORICAL&#95;CALCULATION&#95;BASELINE：[gigadevice-baseline](sources/git/b809dfb062232dee9b77db6184a9948a83b13fc7/603986-gigadevice-deep-research-v2.json) — 原完整数值基线；是否仍为生产输入另外从 workflow 的显式配置读取，不表示 Human 接受其概率。
- 603986.SH / METHOD&#95;SUPPLEMENT：[gigadevice-method](sources/git/6210d53f74356c9baac3d8f8c5a44574326a83fc/gigadevice-decision-hygiene-zero-schema-2026-09-03.md) — 方法实验没有授权移除生产 Inbox；不改写原概率或 Odds。
- 603986.SH / HUMAN&#95;DECISION&#95;CHECKPOINT：[gigadevice-human](sources/git/f803dc551dba69f0f39291b98353bc4e406a7710/603986-gigadevice-human-decision-2026-09-03.md) — 冻结的条件决定；历史分布 NON-DRIVING。Action 未执行状态只属于该 checkpoint，不能推断后续成交。
- 002050.SZ / HISTORICAL&#95;CALCULATION&#95;BASELINE：[sanhua-baseline](sources/git/925f9875b6f8d814f95537af61214068188beb11/002050-sanhua-deep-research-v1.json) — 原计算基线；与 Human 使用的核心业务方法背景分开。
- 002050.SZ / METHOD&#95;SUPPLEMENT：[sanhua-method](sources/git/41d6effe2c45fd1f17133f0ad38d844d82c134d9/sanhua-decision-hygiene-zero-schema-2026-09-03.md) — 零 schema 方法补充，不是自动替代生产输入的授权。
- 002050.SZ / HUMAN&#95;DECISION&#95;CHECKPOINT：[sanhua-human](sources/git/0c7739cb5a376be9cc722e37f6acd168dca9704e/002050-sanhua-human-decision-2026-09-03.md) — 条件首笔约30元，非机械订单；旧总公司概率不是该决定的驱动依据。
- 002050.SZ / HUMAN&#95;METHOD&#95;SUPPLEMENT：[sanhua-horizon](sources/git/ccc66895c2aaf29b78630208b95e0ca11655362f/002050-sanhua-human-horizon-supplement-2026-09-03.md) — 后续 Human 时间范围补充，不能回写此前 checkpoint 或冒充已执行 Action。
- 300750.SZ / EXPLICIT&#95;QUALIFICATION&#95;EXIT&#95;REFERENCE：[catl-qualified-exit](sources/git/597ca0310acbf5eee371aae2d3b9dc8b0f188e56/catl-full-research-reunderwrite-2026-09-04.md) — 宁德旧通用数值资格退出的具体依据；不机械推广到兆易或三花。
- 300750.SZ / HISTORICAL&#95;MECHANICS&#95;NOT&#95;CURRENT&#95;NUMERICAL&#95;INPUT：[catl-historical](sources/git/514fdb991504abdd23e814dc77fdcbd6f0e2e22c/300750-catl.json) — 保留历史机械/采集用途；生产配置另行读取，不能因本文件存在恢复资格。
- 300750.SZ / HISTORICAL&#95;RESEARCH&#95;COMMIT&#95;CHECKPOINT：[300750-catl-real-research-commit-roundtrip-20260916](sources/git/c75e6007f3a503baeec139b7640d22d8a3ac9fcb/commit.json) — #321 typed remote round-trip acceptance only: replays the exact historical dogfood/300750-catl.json ResearchCommitPackage through the existing commit-only retainer and archives the exact COMMITTED output. This validates commit/archive identity only; the existing CATL qualification-exit remains in force, historical illustrative scenario probabilities are not calibrated/current, and this does not establish current Research truth/Belief, Human acceptance, Market/Odds/Action/watch or Investment Authority.
- 600233.SH / RETAINED&#95;RESEARCH&#95;PACKAGE：[yto-research](sources/git/ae9bfce4dd3cfbedddb4be84075238d867f58529/600233-yto-deep-research-v2.json) — 既有完整研究包，非本次新研究或新的 Human 采用判断。
- 600233.SH / METHOD&#95;SUPPLEMENT：[yto-method](sources/git/2b58294ace63f3fe682c70f889a457f4b518c1a2/yto-decision-hygiene-zero-schema-2026-09-03.md) — 现有方法补充；不自动取得新 Odds 或投资权限。
- MU / HUMAN&#95;DECISION&#95;CHECKPOINT：[micron-human](sources/git/590453f3ad36e70cc11b8bae196aad377f082854/MU-micron-human-wait-validation-2026-09-03.md) — 冻结 Human WAIT/NO&#95;ACTION 及其原因；事件日期只是所读 checkpoint 的记录，未重新核验安排。
- 000333.SZ / METHOD&#95;SUPPLEMENT：[midea-method](sources/git/68e24d4db265517e2b4d75fdc24353621e566c59/midea-analysis-divergence-v0-2026-09-03.md) — 方法对照的用途独立保留，不是新概率或投资决定。
- 600549.SH / METHOD&#95;NEGATIVE&#95;CONTROL：[xiamen-negative-control](sources/git/d9acd593cf4a07c3a811282ec9b646a535b21840/xiamen-tungsten-research-error-negative-control-2026-09-03.md) — 研究方法负对照，不将其登记成当前投资待办。
- 688277.SH / RETAINED&#95;RESEARCH&#95;DOCUMENT：[tinavi-research](sources/git/9b7248d5b34a7a0eb89805abdff0e64da9a485ec/tinavi-full-research-zero-schema-2026-09-04.md) — 已完成 public-diligence 的保留记录，不重新运行旧 Quick。
- 688277.SH / HUMAN&#95;DECISION&#95;CHECKPOINT：[tinavi-human](sources/git/04655814a52d28b50d4d0e3dcbdac666c22b71df/688277-tinavi-human-watch-2026-09-04.md) — WATCH/NO&#95;ACTION 冻结记录，非本次投资指令。
- 002281.SZ / RETAINED&#95;RESEARCH&#95;DOCUMENT：[002281-accelink-full-research-20260917-v1](sources/git/50982ed0c0f1c5f06941ec8252dc1c5ffcb64d64/README.md) — User-requested, AI-drafted Full Research v3 as of 2026-09-17: business and financial evidence, frozen pre-expectation Builder, actual Challenger/reconciliation, and bounded profit/cash/price arithmetic. First-entry case NOT METHOD-READY; quoted price CONTEXT&#95;ONLY; no calibrated probability, canonical Odds, Kernel COMMITTED, Human acceptance, Action/watch, or Investment Authority. Full original-source custody remains PARTIAL.
- 300183.SZ / RETAINED&#95;RESEARCH&#95;DOCUMENT：[radar-300183-eastsoft-progress-20260919](sources/git/e2ae22709d858e242c97ad816e9a28b57a1a92a2/workpaper.md) — 2026-09-19 bounded interactive review of the retained 2026-09-13 Pre/Quick: restores the original WAIT and adds gross-profit, working-capital cash and goodwill-headroom arithmetic on saved filings. Current trigger refresh remains incomplete. Not new Pre/Quick, Full Research, COMMITTED, Human acceptance, Odds, Action or Watch.
- 601155.SH / METHOD&#95;SUPPLEMENT：[601155-unit-correction-notice-20260930](sources/git/270a9f5143b9d278983e3211494afec22d702fea/ODDS-BOOK.md) — 先看Odds Book中新城601155单位勘误摘要，再按精确链接恢复四文件后继；这份共用导航正文不是完整纠错档案已读取。金额/股数同时归一，不改每股结果和原接受边界。
- 002436.SZ / NAVIGATION&#95;ONLY：[odds-xingsen-provisional-20260930](sources/git/270a9f5143b9d278983e3211494afec22d702fea/ODDS-BOOK.md) — 2026-09-30 兴森 probability-free provisional Odds 的 registry-visible 导航；精确原件为 docs/readings/002436-xingsen-odds-2026-09-30/odds.md@d244c3427d112ad3c8623ab71aeb94408f202920（blob c49222d763654ed8f4e8978bb9ff1e9074f95af2）。40.93公共价格背景、3y/10%与30/35/40x均为 analyst sensitivity；35.73/26.80/20.16为 ANALYST&#95;DERIVED Watch复核层级，非Human接受、canonical Odds或Action。此记录复用共享 Odds Book 读取源，不新增独立 eager source request。

</details>


已登记且仍符合原 Funnel 的研究请求：0。这不是已研究全市场的计数。
研究资料按生产配置／历史计算基线／方法补充／Human 记录／明确 Action 分别引用，互不自动覆盖。

入口未更新：查 `.github/workflows/current-state-read-entry.yml` 的运行及失败日志；保留最后版本不代表持续新鲜。
缺日或源附件不可用：按 `docs/sector-radar-scheduled-production.md` 转入已有 qualified recovery；本读取 ref 绝不是恢复来源。

原 GitHub artifact 仍受保留期约束；本 ref 留存的精确阅读副本在 Git 历史中，无自动清理，但不是永久备份承诺。

SHADOW / READ-ONLY。Human Attention / Research / Investment authority = NONE。

## 多来源公司发现与研究上下文

读取状态：READ_OK。
保存公司线索 922 家：行业 45，机构 33，概念 860；证券去重，不是同日信号或已完成研究数量。
[打开全部公司、各自来路与保存研究状态](details/radar/index.html)
[读取结构化公司结果](details/radar/company-reading.json)
各来源日期和实际取得时间分开；无匹配研究记录不等于从未研究。本层没有执行新的Pre/Quick、Odds或Action；完整概念与其他聪明钱维度仍未覆盖。

## 概念趋势、重叠与未覆盖

[打开概念观察地图](details/radar/concept-observation-map.html)
保留各指数多日路径；按实际成员包含关系减少重复阅读。完整补查范围不是已执行批次，也不是研究优先级。

## 保存的新闻与行业观察

[查看带日期的观察、公司名称命中及来源缺口](details/radar/external/index.html)

这是明确保存的历史样本，不是今日重采、每日信号或待执行研究；重读不新增事件。

[行业广泛观察：日常批次与独立历史范围](details/radar/industry-breadth.md)；不是新增研究或受益判断。

[产业雷达：需求、生产、库存利润、价格与物流](details/radar/industry-fundamentals.md)；统计期与原始来源、增量及缺口分别保留。

[行业市场表达与期指持仓上下文](details/radar/easy-stock-context.md)；不是研究结论或买卖指令。

[TDX 概念市场横截面](details/radar/tdx-concept/summary.md)；completed-session 1/5/10 Market Expression，不是 Research/Odds/Decision。

[TDX 概念完整成员（同版本）](details/radar/tdx-concept/membership.json)；来源成员不是业务受益或持仓。

[概念5/20/60日相对走势与阶段](details/radar/tdx-concept/trend/summary.md)；同期基准、持续天数与缺口分别保留，不是投资信号。

[新闻：原日期、滚动索引与接续缺口](details/radar/news-daily.md)；不是新Research或自动提醒。

## 日常候选检查与具体问题研究

读取状态：READ&#95;OK。未审阅不等于没有问题；旧结果首次展示不算新研究。

**688337.SH / DEEPEN&#95;REQUIRED**：值得关注的是“真实盈利改善与现金兑现之间的距离”，而不是把负现金流等同于没有经营改善。仪器及解决方案是普源精电实际收入来源，解决方案收入已超过1亿元，增长与合并毛利额扩张有直接经济联系；但产品增长对应多少利润、占用多少资金，尚不能从收入增速直接推出。  现有数据已能排除两种过度简化：盈利并非全靠理财或削减研发，增长也尚未兑现为合并经营净现金流。尤其存货现金占用7064.93万元，明显超过本期扣非净利润，母公司现金为正而合并为负，使增长业务、集团内部交易与现金归属的核对具有实质意义。  现在可利用已有附注进一步检验利润增量、现金差额和业务归属，不必只等下一份财报。本次由2026年9月23日正常观察触发，是对8月已披露中报的新问题审阅，不解释当日价格变化。按所提供的固定W候选及当前R检查范围，未见688337正式研究；这一关系不外推到全部历史聊天或研究。

[查看本批完整处置、已执行问题的原结果及来源缺口](details/research/reviewed-questions.md)

本批路由处置：SAVED&#95;DISPOSITION&#95;FOR&#95;DIFFERENT&#95;BATCH&#95;NOT&#95;APPLIED；选择新执行数：未知。与经济问题审阅、Pre/Quick及Human接受分开；见上方同批详情。

[旧研究再进入：已有材料、原条件与保存观察](details/research/asset-reentry.md)；不是新研究或自动提醒。

[聪明钱：游资、北向、具名持股与资本行为](details/radar/smart-money.md)；独立观察与缺口，不是综合荐股分。

[全球市场：指数、利率、外汇、黄金原油与加密资产，含各自日期与缺口](details/markets/global-market.md)；不是实时行情。

## 按需恢复的已登记档案

下列仅有精确档案定位，正文未纳入本读取；不是已读研究、待判断请求或新Pre/Quick。
从本次固定R使用既有research_archive与record-id恢复，仍须核验完整目录、字节和进度。

- 603986.SH / [d-mu-gigadevice-horizons-20261004](https://github.com/auguspp/decision-kernel/blob/9ec1a0a4f22d70d9fdf71cedf57a719aaa8cb830/docs/readings/d-mu-gigadevice-horizons-2026-10-04/README.md) — MU→兆易的产品／成本／现金传导、独立期限及反证；沿#509/5975228575原2026-10-04T01:03:53Z冻结。不是新行情、Full、数值Odds、成交或成熟结果。；状态：正文按需恢复，未在本包物化。
- 600598.SH / [sector-600598-materiality-20260910](https://github.com/auguspp/decision-kernel/blob/822c5c725df2d1e5d66768b3b06bc9ddfef93a2e/research_runs/candidates/sector-origin/600598-materiality-20260910/README.md) — Human许可后Sector来源的有限Pre/Quick，税后盈利问题待深化；最终H1仍有正文核验缺口，非全景研究/新Odds/自动Deep或Human决定。；状态：正文按需恢复，未在本包物化。
- 300638.SZ / [radar-300638-fibocom-progress-20260919](https://github.com/auguspp/decision-kernel/blob/250efdc82567f9988d43cadae0a5b715e50d85da/docs/readings/radar-question-review-2026-09-19/300638/workpaper.md) — 2026-09-19 bounded interactive question/source checkpoint: issuer business identity and a profit-to-cash question; 2026H1 primary financial PDF not acquired and conflicting secondary cash-flow units not adopted. Not completed Pre/Quick, business WAIT/DROP, Full Research, COMMITTED, Human acceptance, Odds, Action or Watch. Body is explicitly ON&#95;DEMAND&#95;ARCHIVE: locator only in daily reading; use the existing same-R archive reader before claiming body recovery.；状态：正文按需恢复，未在本包物化。
- 300638.SZ / [radar-300638-fibocom-progress2-20260919](https://github.com/auguspp/decision-kernel/blob/f75ed7c5c338aa8497b042380d2c53bd6df6f495/docs/readings/radar-fibocom-profit-cash-progress-2-2026-09-19/workpaper.md) — Revision2 of module-profit-cash-source-review, linked to retained revision1. Bounded interactive analysis of historical June29 acquisition and March18 accounting announcements read through the official web viewer: control versus economic ownership, cash/capital allocation and conditional profit undertaking. Current closing/payment, 2026H1 financial body and binary source PDF retention remain unverified/not acquired. Not automatic Pre/Quick, Full Research, COMMITTED, Human acceptance, Odds, Watch or investment authority. ON&#95;DEMAND&#95;ARCHIVE locator only; recover this explicit revision before reuse.；状态：正文按需恢复，未在本包物化。
- 300638.SZ / [radar-300638-fibocom-progress3-20260919](https://github.com/auguspp/decision-kernel/blob/04eb44d37680195caa0de4635f0df02415c975ca/docs/readings/radar-fibocom-profit-cash-progress-3-2026-09-19/workpaper.md) — Revision3 of the same retained profit-to-cash question, linked to revision2. Bounded interactive review of the official 2026Q1 financial key table and April23 temporary idle-proceeds announcement; distinguishes operating cash conversion, internal fund use and conditional acquisition capital allocation. Q1 does not substitute for unacquired H1; issuer explanation is not verified cause and the RMB500m limit is not actual drawdown. Raw source PDF custody, current closing/payment, Full Research, automatic Pre/Quick, COMMITTED, Human acceptance, Odds and Watch are not established. ON&#95;DEMAND&#95;ARCHIVE locator only; recover this exact revision before reuse.；状态：正文按需恢复，未在本包物化。
- 300183.SZ / [radar-300183-eastsoft-review2-20260919](https://github.com/auguspp/decision-kernel/blob/41dc250b63ce87950d11560d304cc3f3a8fa14d3/docs/readings/radar-eastsoft-delivery-cash-review-2-2026-09-19/workpaper.md) — Same-question interactive continuation of the retained Eastsoft delivery-profit-cash review: new H1 fee-coverage sensitivity, contract-asset impairment/cash counterevidence and remaining-obligation recognition limits. Conditions are not forecasts; latest customer and complete disclosure updates remain unavailable. Not new Pre/Quick, Full Research, COMMITTED, Human acceptance, Odds, Action or Watch. RETAINED&#95;FILES with exact predecessor in workpaper; body recovered on demand.；状态：正文按需恢复，未在本包物化。
- 002460.SZ / [radar-002460-lc-spread-inventory-question-20260920](https://github.com/auguspp/decision-kernel/blob/51365aae52e13cdec153ecb0cb4ab79de7d96836/docs/readings/lc-exposure-questions-2026-09-20/workpaper.md) — Bounded interactive lithium case: 2025 issuer segment disclosures support a draft question about selling-price/input-cost/inventory mismatch after the saved LC observation. Current 2026H1 primary bodies and updates through2026-09-20 remain unacquired; no current materiality qualification, formal Question admission, Pre/Quick/Deep, COMMITTED, Human acceptance, Odds, Action or Watch. Raw PDF custody incomplete. Shared four-file comparative archive; on-demand locator only.；状态：正文按需恢复，未在本包物化。
- 300014.SZ / [radar-300014-lc-cost-pass-through-question-20260920](https://github.com/auguspp/decision-kernel/blob/51365aae52e13cdec153ecb0cb4ab79de7d96836/docs/readings/lc-exposure-questions-2026-09-20/workpaper.md) — Same bounded lithium comparative archive: 2025 issuer disclosures support a draft question about cost savings retained versus passed to customers, inventory timing and cash conversion. All-material cost share is not lithium-specific exposure. Current 2026H1 primary bodies, relevant updates and PDF custody remain incomplete; no formal admission/Pre/Quick/Deep, current benefit acceptance, COMMITTED, Human acceptance, Odds, Action or Watch. On-demand locator only.；状态：正文按需恢复，未在本包物化。
- 000920.SZ / [p0-000920-membrane-profit-cash-source-review-20260920](https://github.com/auguspp/decision-kernel/blob/062f9761224e3aecfa9e314222d5069e79a351be/docs/readings/000920-question-review-2026-09-20/workpaper.md) — 2026-09-20 bounded source/question review of the saved six-row Stock batch. Official historical 2025 revenue and July contract text narrow the membrane profit/cash question; necessary 2026H1 official body/raw PDF and current issuer-update coverage remain incomplete. DRAFT / NOT&#95;ADMITTED / NOT&#95;EXECUTED; not Pre/Quick, business WAIT/DROP, COMMITTED, Human acceptance, Odds, Action or Watch. Seven retained files include exact source status, inventory, scope and all six candidate dispositions. ON&#95;DEMAND&#95;ARCHIVE locator only; recover this exact archive before claiming its body was read.；状态：正文按需恢复，未在本包物化。
- 000920.SZ / [p0-000920-source-access-and-dedup-20260920](https://github.com/auguspp/decision-kernel/blob/02a8f8f2c1aadca8287c1f68ebbb6be2f7d8ac7e/docs/readings/000920-source-review-continuation-2026-09-20/README.md) — Follow-up to the 2026-09-20 Woton source/question draft. Normal browser checks still acquired no official PDF or complete current disclosure inventory; issuer report directories were outdated. Bounded relation review of retained inputs, 529 local refs and visible GitHub discussions found no additional formal Woton question, while substantive overlap with the failed baseline remains. Continue the same draft; NEW&#95;DISTINCT&#95;QUESTION is not assigned. Seven files retain access observations, exact dedup scope and pending interface reuse. NOT&#95;ADMITTED / NOT&#95;EXECUTED; no Pre/Quick, business WAIT/DROP, Human acceptance or automatic supersession. Recover this exact archive before citing its body.；状态：正文按需恢复，未在本包物化。
- 000920.SZ / [p0-000920-reports-only-profit-cash-20260920](https://github.com/auguspp/decision-kernel/blob/7e992b3ce83993897930076f64da0eb9cf2035f6/docs/readings/000920-reports-only-progress-2026-09-20/workpaper.md) — Human scope 5750493197 prioritizes financial reports and pauses other announcement acquisition. Bounded continuation of the original Woton root using the acquired 2026H1 Sina issuer-report PDF: p104 profit-to-operating-cash reconciliation and p16 membrane product/engineering facts; volume/price/mix and segment cash attribution remain unresolved. First typed progress checkpoint, not a new distinct question or formal Pre/Quick, COMMITTED Research, Full Research, Human acceptance, Odds, Action or Watch. ON&#95;DEMAND&#95;ARCHIVE locator only; exact body recovery is separate. Source PDFs/service full text are not included in the two-file progress directory.；状态：正文按需恢复，未在本包物化。
- 000920.SZ / [p0-000920-reports-only-working-capital-20260920](https://github.com/auguspp/decision-kernel/blob/3ba635649edadafcd7715ab0e469e1a751dfe5cd/docs/readings/000920-working-capital-progress-2026-09-20/workpaper.md) — Second typed progress checkpoint on the original Woton question using the already-retained 2026H1 Sina PDF. Six inventory categories reconcile exactly to the operating-cash inventory adjustment; receivable/bill balances explain the direction difference but do not establish cash receipts. Endorsed-bill asset/liability changes are kept together; detailed operating-receivable cash reconciliation and segment attribution remain UNKNOWN. This is separate financial work, not a result of the concurrent CNINFO source probe, formal Pre/Quick, COMMITTED Research, Full Research, Human acceptance or Odds. Three-file archive contains the workpaper and current/predecessor progress descriptors, not source PDFs. Recover the exact body separately.；状态：正文按需恢复，未在本包物化。
- 000920.SZ / [p0-000920-h1-original-pdf-custody-20260921](https://github.com/auguspp/decision-kernel/blob/e9d116bd4f20f6f9a3ed6f2e299fe2a97f9c577b/docs/readings/woton-original-source-custody-20260921/README.md) — Retained source-preparation working note for the original Woton financial question: exact original Sina H1 PDF, source attempt35550930725 and preserved representation failure. This one-file on-demand note locates raw PDF/prepare/failure bytes; it does not materialize them in the daily reading or declare repair success, CNINFO byte equivalence, new Question, Pre/Quick, financial Research completion, Human acceptance or model-egress permission. Representation repair is a separate zero-source-GET operation; old question/r2/failures remain.；状态：正文按需恢复，未在本包物化。
- 000920.SZ / [p0-000920-reports-only-profit-bridge-20260921](https://github.com/auguspp/decision-kernel/blob/69305a766eb2cc4b09a6b1a6d4008625e54b8a3d/docs/readings/000920-profit-bridge-progress-2026-09-21/workpaper.md) — Third same-question typed progress checkpoint using the retained 2026H1 issuer PDF: six-product gross profit and both H1 group gross-profit-to-parent-net-profit bridges reconcile exactly. Parent profit growth includes a minority-allocation effect; the tax-adjustment note has an unallocated551260.96-yuan discrepancy. Per-product expenses/tax/cash and prior receivable-cash attribution remain UNKNOWN. Interactive financial work, not new Pre/Quick, Full Research, COMMITTED, Human acceptance, model-egress permission or investment authority. Three-file progress archive only; raw PDF has separate native custody. Recover this exact revision on demand.；状态：正文按需恢复，未在本包物化。
- 000920.SZ / [p0-000920-continuation-failure-review-20260921](https://github.com/auguspp/decision-kernel/blob/2a3c429aabca6f0b398b973df66fe94bb235de94/docs/readings/000920-continuation-review-2026-09-21/README.md) — One approved same-question Pre call returned text but failed APPLICATION&#95;VALIDATION; original EXECUTION&#95;GAP and raw output remain unchanged, no Quick or retry. Separate source-page review corrects blank engineering assets/liabilities and distinguishes over-time revenue disclosure from unallocated working capital; product and report-segment engineering costs differ by19735430.65CNY. Not validated Pre/WAIT, Full Research, COMMITTED, Human acceptance or investment authority. Eight-file on-demand archive; original PDF/context remain at precise prior Git refs.；状态：正文按需恢复，未在本包物化。
- 603507.SH / [stock-603507-financial-question-review-20260921](https://github.com/auguspp/decision-kernel/blob/a1f73741d4223c058364a6e1446dc8fda908b350/docs/readings/stock-financial-question-review-2026-09-21/workpaper.md) — September21 six-row batch preliminary financial-question review. Shared four-file archive; original H1 PDFs were not acquired at this checkpoint. Historical conditional inputs and explicit source gaps remain; not formal Question admission, Pre/Quick, Human acceptance or Odds. Recover exact body on demand.；状态：正文按需恢复，未在本包物化。
- 002285.SZ / [stock-002285-financial-question-review-20260921](https://github.com/auguspp/decision-kernel/blob/a1f73741d4223c058364a6e1446dc8fda908b350/docs/readings/stock-financial-question-review-2026-09-21/workpaper.md) — September21 six-row batch preliminary financial-question review. Shared four-file archive; original H1 PDFs were not acquired at this checkpoint. Historical conditional inputs and explicit source gaps remain; not formal Question admission, Pre/Quick, Human acceptance or Odds. Recover exact body on demand.；状态：正文按需恢复，未在本包物化。
- 000560.SZ / [stock-000560-financial-question-review-20260921](https://github.com/auguspp/decision-kernel/blob/a1f73741d4223c058364a6e1446dc8fda908b350/docs/readings/stock-financial-question-review-2026-09-21/workpaper.md) — September21 six-row batch preliminary financial-question review. Shared four-file archive; original H1 PDFs were not acquired at this checkpoint. Historical conditional inputs and explicit source gaps remain; not formal Question admission, Pre/Quick, Human acceptance or Odds. Recover exact body on demand.；状态：正文按需恢复，未在本包物化。
- 002792.SZ / [stock-002792-financial-question-review-20260921](https://github.com/auguspp/decision-kernel/blob/a1f73741d4223c058364a6e1446dc8fda908b350/docs/readings/stock-financial-question-review-2026-09-21/workpaper.md) — September21 six-row batch preliminary financial-question review. Shared four-file archive; original H1 PDFs were not acquired at this checkpoint. Historical conditional inputs and explicit source gaps remain; not formal Question admission, Pre/Quick, Human acceptance or Odds. Recover exact body on demand.；状态：正文按需恢复，未在本包物化。
- 603507.SH / [stock-603507-profit-hedging-cash-20260921](https://github.com/auguspp/decision-kernel/blob/6eacd1fe5963514948cbcf0a516a13098286fe14/docs/readings/603507-profit-hedging-cash-2026-09-21/workpaper.md) — Same-question primary-page continuation: FTShare discovery led to retained CNINFO 215-page H1 PDF. Two-period profit and cash bridges reconcile; hedge disclosure inconsistency and sustainability remain unresolved. Two-file workpaper/calculation archive; large original PDF has separate exact Git custody. Not Pre/Quick, formal admission, Human acceptance or Odds.；状态：正文按需恢复，未在本包物化。
- 002436.SZ / [002436-xingsen-full-r2-20260924](https://github.com/auguspp/decision-kernel/blob/649f2820b3139cef9c1dd6fa08f2fe6ee079f187/docs/readings/002436-xingsen-full-2026-09-24-r2/README.md) — Human-direct兴森Full R2，精确前驱为#536/a4cb0c0b44970ef3b96f0f570107093e7a1eb7ae；本条登记#538/649f2820b3139cef9c1dd6fa08f2fe6ee079f187的六文件原档案，不合并研究草稿或重做Research。按需恢复README、report、reconciliation及原计算；同时读https://github.com/auguspp/decision-kernel/pull/538#pullrequestreview-5300822964：报告“同比扭亏”应按同比改善理解；名义面积×利用率的单位要求未证明合格可售率，暂不用于已实现单位盈利判断。经营/现金/资本研究有界推进与算术复验已留证，完整估值、最终合同覆盖、全部原文独立核验、Human接受仍未建立。原README/retention中的未审阅/未登记是保存时状态，由后继实际回执补充，不回写旧文件。ON&#95;DEMAND&#95;ARCHIVE只登记定位，不声明正文已被本次读取或全部PDF字节已保管；非typed COMMITTED、Odds、Watch、Action或Investment Authority。；状态：正文按需恢复，未在本包物化。
- 002436.SZ / [002436-institutional-context-20260925-36089933785](https://github.com/auguspp/decision-kernel/blob/9330742c8b48f9c778d0518f11d397cbae0d49a3/docs/readings/institutional-context-2026-09-25-36089933785/README.md) — #504 source-only context from fresh run36089933785/attempt1: 002436.SZ publication window2026-08-11..2026-09-24. Two actual report-list rows &#40;two institutions&#41; and exact raw forecast slots retained; not report PDFs or comparable forecast revisions. Activity source returned HTTP200/success=false/code9201; event/institution/person counts remain UNKNOWN, not zero. Six-file native archive preserves two raw bodies, capture identity, original derived context/summary and an explanatory README. Not completed Quick/Full, economic truth, Research acceptance, Odds, Watch or investment authority. ON&#95;DEMAND&#95;ARCHIVE locator only; recover the exact files before claiming body consumption.；状态：正文按需恢复，未在本包物化。
- 002436.SZ / [002436-institutional-quick-consumption-20260925](https://github.com/auguspp/decision-kernel/blob/1671640800739650922805c6c62e178dcfc39f2e/docs/readings/002436-institutional-quick-consumption-2026-09-25/README.md) — Bounded Hosted Quick consumption of retained #504 context. Reuses Xingsen R2 and review5300822964; both broker forecasts already existed in R1. Preserves provider/report date ambiguity, additional indexed-report leads outside the two saved rows, UNKNOWN activity counts and unverified comparable revisions. Conditional H2 profit burden is arithmetic on retained inputs, not a forecast, new Full, Odds or Human acceptance. Four-file archive; recover before claiming body consumption.；状态：正文按需恢复，未在本包物化。
- NEWS-BATCH-20260927 / [quick-inbox-news-batch-20260927](https://github.com/auguspp/decision-kernel/blob/a15a124725f9bd728828786a19c7c0b410de8a52/docs/readings/quick-inbox-news-batch-2026-09-27/README.md) — Bounded Hosted Quick consumption of #601 requests 5853796032, 5853804680 and 5853810250 from fixed R 7894a95cb43e6cb6131cb4b5a7bb2111b0aff139. Separates one commercial-space WAIT&#95;FOR&#95;TRIGGER, one Zhejiang marine-clean-energy Full candidate recommendation and one Hutuo River STOP; preserves source limits/UNKNOWN and does not execute Full, recalculate Odds, transfer Human acceptance, create Watch/holdings or authorize trading. Two-file native archive; recover exact body before reuse.；状态：正文按需恢复，未在本包物化。
- 601155.SH / [601155-xincheng-policy-full-20260930](https://github.com/auguspp/decision-kernel/blob/fcf09133cc5f7b5ce90e8017d85be5ba3acd3c67/docs/readings/601155-xincheng-policy-full-20260930/README.md) — Human-direct Full continuation around the 2026-09-29 property policy and Xincheng equity-value bridge. Corrects Wuyue/debt/development scope, retains sources/calculations/stop conditions and does not claim typed COMMITTED Research, Human acceptance, canonical Odds, Watch, Action or Investment Authority.；状态：正文按需恢复，未在本包物化。
- 601155.SH / [b2-appointments-36658570687-1-601155-SH](https://github.com/auguspp/decision-kernel/blob/6b9f1b4624cf0bab09cf3ea11b545d658da58e46/docs/readings/b2-appointments-36658570687-1/601155.SH/summary.md) — 财报预约来源资料（2026-09-30）；原资料引用601155-xincheng-policy-full-20260930。仅作来源导航，不是研究、关注、持仓、Watch或投资接受。；状态：正文按需恢复，未在本包物化。
- 601155.SH / [b2-announcements-36671452199-1-601155-SH](https://github.com/auguspp/decision-kernel/blob/6e8d82ddd59e6354311541e590aae17f7d9fe939/docs/readings/b2-announcements-36671452199-1/601155.SH/summary.md) — 公告目录来源资料（2026-09-24至2026-09-30）；原资料引用601155-xincheng-policy-full-20260930。仅作来源导航，不是研究、关注、持仓、Watch或投资接受。；状态：正文按需恢复，未在本包物化。
- 601155.SH / [b2-announcements-36675839340-1-601155-SH](https://github.com/auguspp/decision-kernel/blob/d13143a92b4c25bb38c9a46fc836309dba2af367/docs/readings/b2-announcements-36675839340-1/601155.SH/summary.md) — 公告目录来源资料（2026-08-26至2026-08-27）；原资料引用601155-xincheng-policy-full-20260930。仅作来源导航，不是研究、关注、持仓、Watch或投资接受。；状态：正文按需恢复，未在本包物化。
- 601155.SH / [b2-pdf-36685884532-1-601155-SH](https://github.com/auguspp/decision-kernel/blob/e382453d09e54572ead47f23f553a5da87764d9f/docs/readings/b2-pdf-36685884532-1/601155.SH/summary.md) — 公告原文来源资料（1225512314）；原资料引用b2-announcements-36675839340-1-601155-SH。仅作来源导航，不是研究、关注、持仓、Watch或投资接受。；状态：正文按需恢复，未在本包物化。
- 002281.SZ / [c-synopsis-comparison-002281-20260930](https://github.com/auguspp/decision-kernel/blob/2a264469fbd0017b46dffe52ceeb6e4b3587bf53/docs/readings/c-synopsis-comparison-002281-2026-09-30/README.md) — Bounded C consumer proof using two public synopses attributed to Changjiang: same-year total-profit arithmetic, changing analyst combinations, missing explicit currency/share-model/PIT qualification. Not original broker PDFs, qualified complete-model revision, new Full, Human acceptance, Watch or investment action. Preserves the prior 20260917 archive.；状态：正文按需恢复，未在本包物化。
- navigation / [d-pit-eligibility-controls-20260930](https://github.com/auguspp/decision-kernel/blob/0378c878d40af7c2d14d4095e5eb8c4ae05c89b5/docs/readings/d-pit-eligibility-2026-09-30/README.md) — Bounded D retained-record and PIT eligibility proof: two candidates plus three horizon/mandate/correction controls. Preserves missing contemporaneous inputs, frozen Research horizons, unknown current execution and immature outcomes. Not five qualified opportunities, calibration success, Human acceptance, a new method or investment action.；状态：正文按需恢复，未在本包物化。
- 601155.SH / [601155-unit-correction-20260930](https://github.com/auguspp/decision-kernel/blob/f54c017c3d06fd46cf2a5da4949c0e461e5789e0/docs/readings/601155-unit-correction-2026-09-30/README.md) — 先读原601155条件估值的十倍单位标签勘误：统一归一金额与股数，保留每股/回报/门槛及原舍入精度；不是经济假设复核、完整来源证明、Human接受或投资行动。原档案不覆盖。；状态：正文按需恢复，未在本包物化。
- 002281.SZ / [c-longitudinal-accelink-20260930](https://github.com/auguspp/decision-kernel/blob/83a40bfb408090015678d98bd192489db9226c3a/docs/readings/c-longitudinal-accelink-2026-09-30/README.md) — Reviewed longitudinal cash/capital comparison: exact retained sources, period/unit/scope checks, explicit economic interpretation and unknowns. Actual generic offline consumer output, not new Full, original issuer PDF custody, typed COMMITTED Research, Human acceptance or complete C.；状态：正文按需恢复，未在本包物化。
- 002436.SZ / [c-longitudinal-xingsen-20260930](https://github.com/auguspp/decision-kernel/blob/83a40bfb408090015678d98bd192489db9226c3a/docs/readings/c-longitudinal-xingsen-2026-09-30/README.md) — Reviewed longitudinal cash/capital comparison: exact retained sources, period/unit/scope checks, explicit economic interpretation and unknowns. Actual generic offline consumer output, not new Full, original issuer PDF custody, typed COMMITTED Research, Human acceptance or complete C.；状态：正文按需恢复，未在本包物化。
- navigation / [c2-blindspot-audit-20260930](https://github.com/auguspp/decision-kernel/blob/79f7921811f905a0e58ba7690c957180d1ba7eca/docs/readings/c2-blindspot-audit-2026-09-30/README.md) — One-time complete-denominator audit of retained #375 historical study: coverage/gate/delivery distinctions, all396census cells and7x66purposive pressure histories. Lossy derived report, original31MBstudy remains Actions artifact with expiry; not permanent original custody, new detector, threshold change, historical catalog proof or complete C2.；状态：正文按需恢复，未在本包物化。
- 002281.SZ / [c-cash-bridge-semantic-002281-20260930](https://github.com/auguspp/decision-kernel/blob/eef5b196cfd62ea8e7db4aa45a1a2285e36fe543/docs/readings/c-cash-bridge-semantic-review-2026-09-30/README.md) — Two-case semantic successor to the retained C1 comparisons; select this issuer input after reading semantic-review.md. Original source bytes and all inherited result fields unchanged. Distinguishes genuine new evidence from inherited AT&amp;S/BGA caveats; no new Full, original PDF custody, Human acceptance or complete C1.；状态：正文按需恢复，未在本包物化。
- 002436.SZ / [c-cash-bridge-semantic-002436-20260930](https://github.com/auguspp/decision-kernel/blob/eef5b196cfd62ea8e7db4aa45a1a2285e36fe543/docs/readings/c-cash-bridge-semantic-review-2026-09-30/README.md) — Two-case semantic successor to the retained C1 comparisons; select this issuer input after reading semantic-review.md. Original source bytes and all inherited result fields unchanged. Distinguishes genuine new evidence from inherited AT&amp;S/BGA caveats; no new Full, original PDF custody, Human acceptance or complete C1.；状态：正文按需恢复，未在本包物化。
- 002281.SZ / [c-reviewed-forecast-002281-20260930](https://github.com/auguspp/decision-kernel/blob/4255a42e26ecd71476c19ac99d93ea9298396471/docs/readings/c-reviewed-forecast-boundaries-2026-09-30/README.md) — Reviewed forecast identity/basis boundary cases using exact retained source bytes. Select the issuer input after README. Real cases classify distinct provider records or cross-institution attribution but refuse numeric comparison for missing qualifications; synthetic positives are engineering tests only. No original broker model, historical availability, Human acceptance or full C completion.；状态：正文按需恢复，未在本包物化。
- 002436.SZ / [c-reviewed-forecast-002436-20260930](https://github.com/auguspp/decision-kernel/blob/4255a42e26ecd71476c19ac99d93ea9298396471/docs/readings/c-reviewed-forecast-boundaries-2026-09-30/README.md) — Reviewed forecast identity/basis boundary cases using exact retained source bytes. Select the issuer input after README. Real cases classify distinct provider records or cross-institution attribution but refuse numeric comparison for missing qualifications; synthetic positives are engineering tests only. No original broker model, historical availability, Human acceptance or full C completion.；状态：正文按需恢复，未在本包物化。
- 002436.SZ / [c-reviewed-activity-002436-20260930](https://github.com/auguspp/decision-kernel/blob/4f7c1f09d0785775084ab122fe0560c266f78609/docs/readings/c-reviewed-activity-boundaries-2026-09-30/README.md) — Reviewed activity census boundary archive: failed provider response remains UNKNOWN, and one retained corrected IR event has no roster or issuer-window total. Exact original capture/reconciliation bytes, two inputs and deterministic reports; synthetic positive populations are engineering tests only. No source/model call, original disclosure custody, Human acceptance or full C completion.；状态：正文按需恢复，未在本包物化。
- 002436.SZ / [c-activity-positive-002436-20260930](https://github.com/auguspp/decision-kernel/blob/0ff4f1384c205f6ab7d9ca7f90774a7d55052d17/docs/readings/c1-activity-positive-2026-09-30/README.md) — Official historical named-roster selected-event positive use: one event, two visiting institutions, eight visitors/eight attendances, three issuer hosts excluded. Original PDF and extraction/review mapping retained separately; derived input is RETAINED&#95;RESEARCH, not original issuer bytes or global identity proof. No issuer-window total, current signal, full C or Human acceptance.；状态：正文按需恢复，未在本包物化。
- navigation / [c2-independent-observations-20260930](https://github.com/auguspp/decision-kernel/blob/096fddf5da1066a1f4793ae19a32f79000feae7d/docs/readings/c2-independent-stock-observations-2026-09-30/README.txt) — Lossy offline independent all-market observation replay:5578identities/12pages and an unvalidated bounded quote-change sample, selected before available-history intersection; explicit source failures and missing history. Original ZIP is separately body-verified in fixed read-model Git R=e2d5074e70acd65277e760ac9c825f51f003d8ec; its Actions copy has separate expiry. This two-file derived archive is not the original source bundle or a permanent-storage guarantee. No quiet-day live acquisition, Surprise, Research admission, economic value or full C2 acceptance.；状态：正文按需恢复，未在本包物化。
- 002916.SZ / [c-shennan-transmission-20261001](https://github.com/auguspp/decision-kernel/blob/5b93bfd6a0b3f3594445afd3c889321f9929a05c/docs/readings/c-shennan-transmission-2026-10-01/README.md) — Source-bound Shennan H1 industry/company/profit/cash-capital transmission case: reviewed extraction, exact comparison replay and explicit peer/consolidation limits. Not issuer PDF custody, typed COMMITTED Research, Human acceptance or full C.；状态：正文按需恢复，未在本包物化。
- navigation / [c2-baseline-episodes-20261001](https://github.com/auguspp/decision-kernel/blob/e5d061dbb6a089906f1a96035108b9ccfca580ce/docs/readings/c2-baseline-episodes-2026-10-01/README.md) — Complete frozen-cohort baseline episodes: 21120 sector-session rows become 449 observed onsets plus 32 left-censored runs; same-run lead and mature/pending noise controls. Post-hoc diagnostics, not new detector, observed Human attention, historical catalog qualification, stock roles or full C acceptance. Original large source remains separately expiring Actions custody.；状态：正文按需恢复，未在本包物化。
- 002436.SZ / [c1-peer-commitment-002436-20261001](https://github.com/auguspp/decision-kernel/blob/382c68bc94f81e986c9237620524e2f761e9a4f0/docs/readings/c1-capital-realization-2026-10-01/README.md) — Explicit successor to PR700: all seven prior-funding destinations and two quantified benefit cases; reallocation, changed project scale and N/A retained. Funds exhausted and annual pre-tax benefit are not owner return. Original peer archive remains linked; no forecast, Full or Human acceptance.；状态：正文按需恢复，未在本包物化。
- navigation / [c2-k3-research-use-20261001](https://github.com/auguspp/decision-kernel/blob/991d2b5ec0c72acb7ff18983fef726597ebf6e7d/docs/readings/c2-shanshui-transmission-2026-10-01/README.md) — K3 successor: original five-file route retained; Shanshui product/cash transmission and qualified industry context added. Not historical roles, causal inflection, new Full, Human acceptance or complete C.；状态：正文按需恢复，未在本包物化。
- 002436.SZ / [c1-incentive-capital-002436-20261001](https://github.com/auguspp/decision-kernel/blob/e1eb810e7b7d5bb7bbe072d140714094aa485294/docs/readings/c1-incentive-capital-2026-10-01/README.md) — Incentive revenue conditions are not forecasts; cumulative alternatives, retained R2 H2 burden and hypothetical compensation/cash distinctions. Partial primary-text access, no actual grant/transfer, original broker-model qualification or Human acceptance.；状态：正文按需恢复，未在本包物化。

[研究日历：已保存的有限 BLS 预约](sources/git/ec0c4cd941fe19ef804393c387e7548579c8019a/calendar.md)；原核读时刻保留，不是实时日历、实际发布确认或研究待办。

未登记显式前驱；未作版本比较，不表示没有改期。


# 日常个股输入

市场日：2026-09-30。本次覆盖 0 个有效证券身份；不是全部上市证券清单。
5／20／60交易日区间可比：0／0／0（各分母 0）。
来源：现有第三方 Tushare Relay。仅比较准确日期的两端价格与因子；中间逐日数据不作前提。
缺历史或缺因子只影响对应期限；不补零、不推断停牌或上市日，不替代经营研究或投资决定。

来源覆盖缺口：daily:20260930、daily:20260922、daily:20260707、adj_factor:20260707。完整范围与行级处置见正文数据表。

## 5日区间两端变化（本次可比子集）

| 证券 | 区间变化 |
|---|---:|
| 暂无可比输入，不是没有变化 | — |

## 20日区间两端变化（本次可比子集）

| 证券 | 区间变化 |
|---|---:|
| 暂无可比输入，不是没有变化 | — |

## 60日区间两端变化（本次可比子集）

| 证券 | 区间变化 |
|---|---:|
| 暂无可比输入，不是没有变化 | — |


[本次完整证券表、逐期限缺口与来源](details/stock/daily-market-inputs.json)。


## 最近已验证可用输入（保留原日期）

最新尝试状态：PRICE_INPUT_UNAVAILABLE_NOT_QUIET。以下来自较早采集，不表示最新尝试成功。
原采集完成：2026-10-03T13:18:26.649057+00:00；[原运行](https://github.com/auguspp/decision-kernel/actions/runs/37125677265)。按原市场日使用，不能当作更新交易日的行情。

### 已保存的日常个股输入

市场日：2026-09-30。本次覆盖 5561 个有效证券身份；不是全部上市证券清单。
5／20／60交易日区间可比：5550／5536／5502（各分母 5561）。
来源：现有第三方 Tushare Relay。仅比较准确日期的两端价格与因子；中间逐日数据不作前提。
缺历史或缺因子只影响对应期限；不补零、不推断停牌或上市日，不替代经营研究或投资决定。

## 5日区间两端变化（本次可比子集）

| 证券 | 区间变化 |
|---|---:|
| 301190.SZ | +75.61% |
| 600825.SH | +61.21% |
| 301560.SZ | +53.90% |
| 301218.SZ | +45.95% |
| 000678.SZ | +44.99% |
| 920229.BJ | -65.07% |
| 301686.SZ | -61.70% |
| 601091.SH | -39.05% |
| 002717.SZ | -32.61% |
| 600857.SH | -28.96% |

## 20日区间两端变化（本次可比子集）

| 证券 | 区间变化 |
|---|---:|
| 688137.SH | +121.26% |
| 600825.SH | +95.28% |
| 605058.SH | +93.72% |
| 601811.SH | +85.43% |
| 601579.SH | +80.19% |
| 301030.SZ | -45.71% |
| 688121.SH | -43.65% |
| 002717.SZ | -38.61% |
| 000017.SZ | -37.02% |
| 601123.SH | -35.69% |

## 60日区间两端变化（本次可比子集）

| 证券 | 区间变化 |
|---|---:|
| 688137.SH | +320.53% |
| 301234.SZ | +298.97% |
| 301080.SZ | +189.08% |
| 002827.SZ | +150.96% |
| 601579.SH | +150.17% |
| 688121.SH | -80.31% |
| 301139.SZ | -73.08% |
| 600363.SH | -63.08% |
| 001309.SZ | -57.88% |
| 688525.SH | -54.65% |


[最近可用完整证券表及缺口](details/stock/last-qualified-market-inputs.json)。


## D：已保存名单的多期限市场表达（只读）

价格市场日：2026-09-30；6个主节点，192次成员关系。名单日期分别保留，不冒称历史当时成员。
以下为可比成员等权中位数，不是行业指数收益；不同期限的强势个体不自动成为跨周期龙头。

| 主节点 | 成员 | 5日可比／中位数 | 20日可比／中位数 | 60日可比／中位数 |
|---|---:|---:|---:|---:|
| 风电设备 | 32 | 32/32；+2.86% | 31/32；+6.37% | 31/32；+2.57% |
| 其他生物制品 | 35 | 35/35；+0.65% | 34/35；+3.91% | 33/35；+0.91% |
| 水泥 | 21 | 21/21；+0.86% | 21/21；-0.59% | 21/21；+6.09% |
| 汽车整车 | 23 | 22/23；-0.02% | 23/23；-2.31% | 23/23；+2.56% |
| 美容护理 | 34 | 34/34；-1.02% | 34/34；-0.40% | 32/34；+6.08% |
| 饮料制造 | 47 | 47/47；-0.18% | 47/47；-2.56% | 47/47；+8.26% |

| 主节点指数 | 结构市场日 | 前5／20／60日收盘区间位置 | 最近局部转折：发生→确认 |
|---|---|---|---|
| 881280.TI | 2026-09-30 | 高于区间／高于区间／高于区间 | 收盘局部低点 2026-09-23→2026-09-24 |
| 884240.TI | 2026-09-30 | 高于区间／高于区间／区间内 | 收盘局部低点 2026-09-28→2026-09-29 |
| 884060.TI | 2026-09-30 | 高于区间／区间内／区间内 | 收盘局部低点 2026-09-28→2026-09-29 |
| 881125.TI | 2026-09-30 | 高于区间／高于区间／区间内 | 收盘局部低点 2026-09-24→2026-09-28 |
| 881182.TI | 2026-09-30 | 区间内／区间内／区间内 | 收盘局部低点 2026-09-28→2026-09-29 |
| 881133.TI | 2026-09-30 | 高于区间／区间内／区间内 | 收盘局部低点 2026-09-28→2026-09-29 |

价格结构仅为收盘区间／局部转折的简单基线，不是缠论认证、盘中领先、短线买卖点或预期收益。
完整成员、逐期限强弱／缺口、结构日期及来源见 [details/stock/market-expression.json](details/stock/market-expression.json)。


## 历史样本（保留原日期）


## 独立个股观察（已保存输入）

[完整分母、独立样本与输入缺口](details/stock/independent-observations.json)。先读 status、summary、coverage 和 selected_observations；输入仍有自己的市场日。样本选择不依赖行业入选，不代表已建立每日独立采集、全市场多周期或研究受益。

截至2026-09-30的供应商口径区间表现：5/20/60日分别14/12/0只可比（各分母16）。
原完整逐日检查分别14/0/0只通过；缺中间数据不否定已核实的两端涨跌幅，但不能据此描述完整走势、回撤或领先角色。

| 证券 | 5日 | 20日 | 60日 |
|---|---:|---:|---:|
| 001246.SZ | 不可比 | 不可比 | 不可比 |
| 920202.BJ | 不可比 | 不可比 | 不可比 |
| 301190.SZ | +75.61% | +73.83% | 不可比 |
| 688185.SH | +28.72% | +35.41% | 不可比 |
| 688806.SH | +20.09% | +31.01% | 不可比 |
| 300893.SZ | +7.46% | +2.93% | 不可比 |
| 688265.SH | +24.96% | +56.96% | 不可比 |
| 301030.SZ | -27.18% | -45.71% | 不可比 |
| 301218.SZ | +45.95% | +25.43% | 不可比 |
| 920344.BJ | +13.89% | +12.21% | 不可比 |
| 301080.SZ | +18.75% | +77.25% | 不可比 |
| 301686.SZ | -61.70% | 不可比 | 不可比 |
| 688137.SH | +28.83% | +121.26% | 不可比 |
| 300981.SZ | +7.98% | +25.77% | 不可比 |
| 688837.SH | -6.58% | 不可比 | 不可比 |
| 688026.SH | +2.15% | +53.90% | 不可比 |

不可比项保留在分母中，具体缺端点或数值问题见 interval_performance；原逐日缺口和来源失败见原 price_comparison。不是总回报、当前行情或新增采集。
