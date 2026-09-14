# Research / Odds / First Entry — 统一执行入口

Version: research-decision-handoff-v1.1 · 2026-09-14  
Status: HUMAN-APPROVED PROCESS DISCIPLINE / NO KERNEL SCHEMA OR RUNTIME CHANGE  
Scope: ChatGPT、外部研究者与仓库会话中的公司研究、估值、Odds、第一笔讨论及其质疑复核。Investment authority = NONE。

## 0. 新聊天先恢复什么

Repository: `auguspp/decision-kernel`。每次新研究或接续先解析 `main` 一次，固定为 M；本文件、方法和当前案例更正说明均按 M 读取。旧研究按其明确记录的历史 commit/path/blob 读取，不混成同一时点。保留本次 M 与读取结果。

先看本文。凡进入 decision-use Full Research、世界构造、估值、Price-Implied Worlds 或第一笔工作，先读 [Economic Architecture & Causal State Space](full-research-economic-architecture-and-causal-state-space-v1.md)，再按任务使用原有 [Full Research Review Gate](full-research-review-gate-v1.md)、[Price-Implied Economics Closure](full-research-price-implied-economics-closure-v1.md)、[Decision Hygiene](decision-hygiene-method-note-2026-09-03.md)。准备记录 Human 决定时读 [决策/结果协议](prospective-decision-outcome-capture-protocol-2026-09-03.md)。不是每次全文复述给用户。

只有需要声称生产/监控/待办状态时，再按 [current-state 消费协议](current-state.md) 独立解析 `read-model/current-state` 为 R，整包保持同一 R；M 不是 R。档案存在不等于已登记、持续观察、Human 接受或交易发生。读取失败就报告读取缺口，不从聊天猜测状态。

案例复核入口（在新 M 中检查是否有明确 successor）：

| 对象 | 当前方法处置 | 必读 |
| --- | --- | --- |
| 光电股份 600184 | 旧 first-entry 梯度为历史、不可直接作行动边界；经营/估值桥受挑战，未记录 Human 接受 | [600184 复核与单位勘误](readings/600184-research-method-review-2026-09-13.md) |
| 恒瑞医药 600276 | 保留原 Human 接受记录，不擅自改价；条件收益可复算，未验证的经营假设和风险约束仍需显式保留 | [原 Human 记录](decisions/600276-hengrui-human-first-entry-2026-09-12.md) 与 [两例回放](dogfood/research-handoff-replay-2026-09-13.md) |
| 和顺石油 603353 / 广哈通信 300711 | run34807883332 已实际完成 Pre／必要 Quick；旧 WAIT／DROP 终局理由混淆历史失败与本轮状态，未通过本次语义复核，不作业务终局依据 | [终局理由复核与纠错边界](readings/stock-successor-terminal-review-2026-09-14.md) |

本入口不能自动注入所有未读取仓库的聊天。可复用启动句：**按 auguspp/decision-kernel 的 docs/RESEARCH-ENTRY.md 恢复后再做研究或投资判断。** 消费端没有读取入口，就不能声称已采用本协议。

## 0.1 算过的 Odds 从哪里恢复；新结果怎样不再丢失

先打开 [Odds Book v0](ODDS-BOOK.md)，并按其中精确版本查原输出、方法更正、Human接受及下一复核条件。它是有声明覆盖的导航，不是持仓、当前行情或全历史穷尽；未被Human接受的临时/受挑战结果仍须保留。固定读取中的 `odds-book` 及相关purpose引用提供同R原件副本，不中途拼接新的main。

每次真实决策相关Odds计算或重大方法修订，交付的一部分就是按原留存协议保留结果、在既有用途索引登记精确path/ref/blob、追加old→new历史并读回。不能只给一个聊天答案后等待Human再问是否记录。原件、登记或发布未完成时明确报告 `NOT_SAVED / REGISTRATION_INCOMPLETE / PUBLICATION_PENDING` 的实际阶段；先核对已存在结果，不为补登记重新运行研究。无原件的历史线索保留UNKNOWN，不能补造过去的调用、时钟或结果。

接受、条件投资决定与Action单独引用；新版本不继承旧Human接受，受挑战旧梯度不激活。此处复用交互保存与现有publisher，不声明全仓自动发现/全入口自动捕获已经实现，不创建监控或第二Odds引擎。

## 1. 先确定在回答哪种问题

区分多年经营价值/现金回报与短期催化/预期交易；两者可并列，不互相代替。先保存以下 decision-use context：证券与股类、Research cutoff、价格日期/来源/authority、估值终点、持有期、绝对或相对回报门槛、分红/税费、股本及单位、允许承担的损失约束。

Human 已明确的条件直接复用并引用原话。跨公司沿用三年/10%等条件须标为沿用假设，不能冒充该公司的已接受要求。尚未给出风险约束，不妨碍条件计算，但不能声称求出了唯一最优第一笔。小仓位减少金额暴露，不自动改善标的的百分比收益或估值。

没有合格行情时，可做明确标注的 CONTEXT_ONLY provisional analysis；不伪造 ObservedMarket、canonical Odds、Pre/Quick、Kernel COMMIT 或 validator PASS。#321 仍是另行安排的执行能力需求，本文不是其已实现证明。

## 2. 有限轮次研究，不让 Human 反复充当研究主管

先建立 Economic Architecture，再定义经济模型与关键矛盾：识别足以改变 owner outcomes 的经济引擎，说明各引擎的收入/利润/现金/资本回报，画出替代、共享固定成本、交叉补贴、资本迁移、营运资金和融资等重大关系，再识别能够独立变化的 load-bearing causal axes。**不要先写 Bear/Base/Bull 再往里填数字。**

在此基础上闭合收入→经营利润→归母/扣非→经营现金→再投资→股东现金，并把引擎级状态重新勾稽到集团 owner cash / ROIC。只深挖会改变判断的 3–5 个变量。对每个 UNKNOWN 保存重要性、下一项可区分证据、现在能否缩小、处置与 STOP 理由。

可以在一次用户请求内做 bounded passes；不用为格式造多轮，也不默认写完背景就算 Full Research。公开信息只能等待未来验证时 STOP，继续交付条件分析。资料取得失败与公开信息确实不足分开，不把前者称作穷尽公开证据。

公司披露证明其实际报告/表述了什么，不自动证明可持续经济利润。行业研究、周期、竞争与价值链对照应服务于 load-bearing variables：谁有议价权、什么会改变利用率/价格/成本/份额、同行如何反应、哪些现象是周期而非结构。不要以管线数量、主题标签、TAM 或成交上涨代替收入、资本回报和现金。

## 3. 独立经营研究 → 市场对照 → 显式修订

保留一次主动市场预期对照前的经营假设，再读卖方/价格隐含条件，最后形成对照后的判断。不是假装完全没看过股价，而是使锚定可追溯。

Market Expectation 表至少区分：机构、报告日、目标财年、利润定义、当时股本、模型驱动、有效覆盖数。只有同机构/同目标年/同口径或可比固定样本才能称作预测修订；跨机构差异叫横截面分歧。2027预测搬到2029必须另有过渡假设。

研报可提供模型、意见和待验证假说，不是默认的公司经济事实。来源权限复用 `source_policy_v2.py`，不得因同一段有一条引用就让其他重要数字免于来源或算术检查。

历史高低点、成交、技术支撑是市场行为观察。记录日期、周期、复权、股本/除权、收盘或盘中等口径。两次低点不证明价值地板；高点不揭示唯一隐含利润或概率。不要为价差发明平台/稀缺/注入原因。

模型与长期价格区间背离，应挑战模型、期限、市场表达或遗漏价值；结果也可以是暂不能识别、等不到或不参与。不能为了得到现实可买的价格上调经营世界，也不能因 Excel 输出就宣判市场错误。

## 4. 经营与估值分别论证，再做联合压力测试

世界必须来自已建立的 Economic Architecture 与独立 causal axes。每个世界说明各经济引擎的量价、产品组合、产能利用率、成本/费用、资本投入、营运资金如何共同形成集团利润和 owner cash；盈利区间不是独立建模完成的证明。经济上可行时必须主动检查反对角世界，例如旧业务变差+新业务成功、收入增长+利润率下降、利润增长+现金变差、新业务成功+ROIC仍差，而不是只保留整家公司 low/medium/high 同方向变化。

倍数、折现率和增长持续期复用原 Gate 2 的独立论证要求；条件敏感性中可以测试未验证参数，但不能标为合理公允估值或默认第一笔。至少检查业绩改善但估值收缩，以及一般业绩而溢价延续，不只保留低利润×低PE、高利润×高PE的对角线。

没有概率的表可称 stress surface，不假装互斥穷尽的概率分布；漏掉亏损或其他尾部要明示。不得只展示下行世界好端。并列累计资本损失、年化回报与期间回撤 UNKNOWN，期末损失不是最大回撤。

## 5. 价格要求与真实预期分开

价格反推回答在给定期限、回报要求和估值下需要什么成立；它通常不能唯一识别市场实际信念。先声明公式及每个输入的单位和来源，再算结果。

仅改变报价、没有新经营证据时，经营模型不应静默改变。合法重新解释可以改变模型，但须按第7节记录，不能称作单纯 Odds refresh。

现金、新业务、股权/royalty 必须回答是否已在利润或现金流中；不清楚就不重复加值。费用化研发不二扣，资本化研发仍扣现金；新增融资不是自由现金。分红与期末余额相互勾稽。A价×A+H股数可作每股条件计算，不能冒称实际A/H合计市值。

无法合理约束 Economic Architecture、owner-economics 或估值桥，仍可交付 BOUNDED CONDITIONAL REQUIREMENTS，但默认第一笔保持 NOT METHOD-READY。UNKNOWN 不阻断所有分析，也不授权虚构完整价格梯度。

## 6. 第一笔使用条件卡，不强制五档价格

对候选价只写：哪些世界达到门槛；哪些仍亏损及完整下沿；需要支付哪些未验证预期；哪些新证据使卡失效。RE-UNDERWRITE、FIRST-ENTRY REVIEW、HIGH-MOS 是不同用途，不是同一容忍度的固定阶梯。

无可校准概率时 `CARDINAL PROBABILITY = NOT_ESTABLISHED`。允许 provisional/ordinal 判断并解释稳健性、脆弱条件；不从好看右尾直接推出 FAVORABLE 或真实上涨概率。

有望得到第一笔区间就给；只能观察就观察；不参与是合法结果。研究接受、价格梯度接受、投资决定、下单/成交必须分别记录。Human 接受不是模型真值证明。

## 7. 每次改变判断或价格边界，都留下修订桥

保存 old→new、原因、证据/公式、影响范围、尚未关闭的问题、未来区分新旧解释的观察。原因可为新证据、重新解释、经营模型修正、估值参数、期限滚动、Human偏好、算术/单位修正。

质疑和K线触发复核，不自动产生向上或向下修订。安全边际偏好不得偷渡成经营前景；历史模型也不得因冻结而免于纠错。旧版本保留，新增明确更正/失效说明，不擦掉历史。

## 8. 发布前与交接时

重要数字逐项核对输入→公式→输出→文字/JSON。1亿元=100000000元=0.1bn CNY；用真实复算，不能凭表格看起来合理就通过。受挑战的行动边界暂停复用，不能把 Kernel 身份校验当经济真相验证。

简短交付至少包含：Economic Architecture/关键引擎和关系；Belief；Price-Implied条件；联合经营/估值世界及完整下行；Odds/第一笔的资格和条件；关键敏感性；Reopen条件。底稿保存以上过程，不把正文写成流水账。

交接最小记录（Markdown足够，不新增schema）：

```text
M / Research版本与源文件身份 / 方法版本
cutoff / 证券与股类 / 价格日期、来源、authority
期限、回报、损失与分红假设 / 哪些为Human明确、哪些待确认
Economic Architecture / 独立causal axes / 关键关系与替代Reference Frame
经营假设前后变化 / 市场对照可比性 / owner-economics与估值桥 / 重复计价
算术实际执行回执 / 模型挑战处置 / 决定性UNKNOWN与STOP
当前结果：条件分析、provisional、canonical分别是否成立
Human原话及接受范围 / 决定与成交是否有记录
写入分支或main / 精确commit / 读回 / 监控登记是否真的存在
```

没有真正验证或写入就写 NOT RUN / NOT SAVED；不能用文件名或PR创建冒称main已完成。新聊天先读取当前更正状态，再决定是否可复用旧判断。

## 9. 验收与边界

[两例回放](dogfood/research-handoff-replay-2026-09-13.md)区分实际算术检查、人工语义复核、尚未完成的新聊天消费端测试及事后收益检验。不能互相替代。

Full Research 的一个长期质量信号是：**Human 仍需亲自发现多少个 Research 本应主动提出的 load-bearing questions。** Human 与模型判断不同很正常；Human 反复发现“这么关键的问题你根本没问”则应进入 Research postmortem，并先区分 METHOD GAP / EXECUTION GAP / SOURCE GAP / JUDGMENT GAP，不要把每次 execution miss 都机械增加成 checklist。

本协议是已有9月3日方法、Economic Architecture 方法与Review Gate的执行组合，不修改Kernel宪法/概率/行情/唤醒/仓位语义。要求定义与优先级仍由Requirements Management负责，runtime实现仍由Main Construction负责。#321只承接方法验收材料，不因本文自动开工。用户未要求的任务、行情重跑、研究循环和监控均不启动。