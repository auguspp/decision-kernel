# 恒瑞医药（600276）Research → Provisional Odds 归档

归档日：2026-09-11（UTC+08:00）  
对象：恒瑞医药 A 股 600276  
性质：Research / Decision reading archive，不构成投资指令、仓位建议或自动交易授权。  
Investment authority：**NONE / HUMAN ONLY**。

## 1. 权限与时点边界

本归档保存三轮研究、冻结 Belief、Human 提供的暂定价格上下文、provisional Odds、算术记录及原生行情资格失败回执。

- `HUMAN_SUPPLIED_PROVISIONAL_PRICE = 42.93 CNY`
- price context date：2026-09-10 A 股收盘价，由 Human 提供
- `price_authority = CONTEXT_ONLY`
- `qualified_market_observation = false`
- `canonical_odds = NOT_ESTABLISHED`
- `provisional_odds_type = PARTIAL / ORDINAL_ONLY`
- `cardinal_probability = NOT_ESTABLISHED`
- 原生行情资格失败：GitHub Actions run `34556401563`, attempt 1，checkout `7ea9e819ba703c3f3b748e4651d2a21712286eb0`，错误 `raw A-share history extends beyond the latest completed session`，exit code 2

失败记录不能解释为 quiet、无变化、买卖信号或正式 Odds。本归档不修改生产 workflow、schedule、Research registry 或 Action authority。

## 2. Frozen Belief

> **恒瑞已经证明创新研发能够形成产品和交易价值，但尚未证明这些价值在承担持续研发、资本投入和授权履约成本后，可以稳定转化为足以支持当前价格要求的每股可支配现金。**

Research 在第三轮明确 STOP。仍保留四个决定性 UNKNOWN：

1. 非肿瘤核心产品的净价、持续用药与增量现金贡献；
2. License-out 组合的完整研发、共享成本与税费；
3. BMS 首付款实际到账后的履约预算和可留存现金；
4. 价格日期初净现金、2029 净现金及 NewCo 净权益。

## 3. 三轮 Research 收敛

### Round 1 — 研究骨架

建立创新药转型、研发平台、License-out、利润/现金与估值框架。已确认 2026H1 收入约154.56亿元、归母约44.65亿元、扣非约37.30亿元、经营现金流约19.87亿元；药品销售约139.5亿元，创新药同比+16.38%，非肿瘤创新药同比+73.97%。同时保留 BMS、FDA CRL 等交易/监管边界，不把 headline deal value、公司对 CRL 的描述或临床进展自动升级成股东价值。

原生 `run-research` 实际调用在行情资格校验处失败，因此没有产生 canonical Odds。

### Round 2 — 收入桥、利润桥、现金桥

完整半年报将收入桥闭合：药品销售增加约2.554亿元，但药品以外收入减少约5.610亿元，公司总收入减少约3.056亿元。药品内部，肿瘤创新药约62.65亿元，同比+2.58%；非肿瘤创新药约25.45亿元，同比+73.97%；仿制药约51.39亿元，同比-16.07%。创新增量主要来自非肿瘤，而仿制药与部分成熟创新药继续承压。

归母→扣非差额主要来自金融资产公允价值等非经常损益，Kailera 股权公允价值增加是主要项目之一。利润→现金桥显示，GSK 首款存在“上期收现、本期履约确认收入”的明确跨期机制；现金转换下降不能粗糙归结为应收账款恶化，也不能全部解释成纯时点问题。

License-out 被拆为已收现金、确认收入、完整成本税后利润和条件性权益四层。2025全年+2026H1许可确认收入约48.15亿元，但持续研发、共享成本、履约和税费无法逐交易完整分配，因此账面毛利不能直接视为正常化股东利润。

### Round 3 — 从利润到股东可支配现金

停止横向扩面，只研究：非肿瘤增长持续性、License-out 全成本经济利润、利润到股东现金。

关键收敛包括：

- 若下一可比期肿瘤创新药仍+2.58%、仿制药仍-16.07%，非肿瘤创新药约需+26.10%才刚好维持药品收入不降；若再做净价-10%的纯压力测试，患者数×持续用药量约需+40.11%。这是条件计算，不是预测。
- IDEAYA 新核实额外200万美元里程碑及一项联合试验费用承担边界，但仍不足以识别 License-out 组合的正常化税后利润。
- 经营现金流含约7.104亿元银行存款利息收现；不能把经营现金减长期资产投入全部称作药品/授权业务现金，同时又把整笔现金本金及其利息收益重复加值。
- 费用化研发、资本化开发支出、固定/其他长期投入必须分开；已进利润/CFO的费用不能重复扣，资本化开发仍是真实现金流出。
- NewCo 股权、公允价值收益、royalty、授权利润、现金本金和利息之间必须防止重复计价。

Round 3 的完整语义记录在 [`round3/`](round3/)；其中包括产品矩阵、授权经济账、现金/研发算术、STOP register、来源、失败回执、研究补充和可复算脚本。

原便利 XLSX 与 PNG preview 不作为 Evidence 或 Kernel state 写入 Git；其原字节 SHA-256 已记录在 `round3/README.md` 和顶层 `manifest.json`，全部经济输入/输出与 UNKNOWN 传播已保留为可读/可复算语义记录。

## 4. Provisional Odds @ 42.93

若从42.93元出发，持有三年并要求10%年化、不计期间分红，则2029年需约57.14元/股。沿用约66.37亿股的每股盈利分母，所需正常化利润约为：

| 2029 终值 PE | 所需正常化利润 |
| ---: | ---: |
| 24x | 158.02亿元 |
| 28x | 135.45亿元 |
| 30x | 126.41亿元 |
| 32x | 118.52亿元 |
| 36x | 105.35亿元 |

因此当前价格不允许“利润只做到原参考 Base（约104.67亿元）+ 终值回归30x”同时发生而仍满足10%回报。至少需要利润、终值倍数，或不重复计价的净现金/NewCo/royalty价值之一明显优于当前已证明水平。

机器可读记录见 [`provisional-odds.json`](provisional-odds.json)。其四个近似互斥世界为：

- `OPERATING_UNDERSHOOT`：约75–90亿元利润、20–24x；
- `GROWTH_BUT_AVERAGE_CASH_CONVERSION`：约100–110亿元、26–30x；
- `CORE_THESIS_MOSTLY_REALIZED`：约125–135亿元、28–32x，并需正自由现金留存得到证据；
- `MATERIAL_OUTPERFORMANCE`：约145–160亿元、32–36x，同时要求非肿瘤、授权现金经济性与资本效率明显超预期。

这些是 provisional Odds construction assumptions，不是目标价或真实概率。

## 5. Odds Judgment

- `CARDINAL PROBABILITY = NOT_ESTABLISHED`
- `ODDS TYPE = PARTIAL / ORDINAL_ONLY`
- `RISK_REWARD = MIXED`
- `UPSIDE_OPTIONALITY = meaningful`
- `DOWNSIDE_PROTECTION = incomplete`
- `DEPENDENCE_ON_OPTIMISTIC_EXECUTION = material`

现有 Evidence 最直接支持“创新药继续增长、现金兑现一般”的世界。核心赔率判断是：**下行世界不需要极端悲观假设；达到三年10%回报则至少需要一个关键经济变量明显优于当前已证明水平。**

## 6. Biggest Odds Sensitivities

1. 2029正常化利润能否由约105亿元向125–130亿元以上移动；
2. 正常化利润到股东自由现金的转换率；
3. License-out 扣完整研发/平台/共享成本与税费后的可重复税后经济利润；
4. 非肿瘤创新药首轮医保放量后的真实量价、持续用药和现金贡献。

## 7. Reopen Triggers

出现以下 Evidence 后再重开 Research/Odds：

- 非肿瘤创新药下一可比期的产品级或足够细分量价/收入；
- BMS 首付款实际到账及研发/共同开发预算或费用承担；
- 新财报更清晰连接 License-out 收入、履约成本、研发与现金；
- 经营自由现金连续改善，且不是主要来自存款利息、授权预收或一次性营运资金释放；
- NewCo 权益出现可验证估值、变现或 royalty 现金流，并能避免重复计价；
- HiThink 恢复 qualified market observation。届时只替换 market state，不改写 Frozen Research，重算 canonical Odds 并与本 provisional Odds 比较。

## 8. Archive payloads

- `round1-research-packet.zip.b64` — 第一轮原 ZIP 字节的 base64，可逆还原；哈希见 `manifest.json`
- `round2-research-packet.zip.b64` — 第二轮原 ZIP 字节的 base64，可逆还原；哈希见 `manifest.json`
- `round3/` — 第三轮全部 Research 语义、算术、UNKNOWN/STOP、来源与失败回执
- `provisional-odds.json` — 冻结价格边界与 ordinal Odds
- `manifest.json` — 来源 commit/run、authority、文件身份与二进制便利层哈希

Round 1/2 解码示例：`base64 -d round1-research-packet.zip.b64 > round1-research-packet.zip`。

GitHub 是本次归档的状态/过程后端；这些文件的存在不代表它们通过了 canonical market/Odds authority。Human 保留最终研究、判断与资本决策权。
