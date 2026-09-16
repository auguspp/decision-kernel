# 北大荒 600598 — 税制续作后的 provisional Odds / first-entry reverse underwriting

Status: `PROVISIONAL_ORDINAL_ODDS / HUMAN_ACCEPTANCE_NOT_ESTABLISHED / NO_ACTION / WATCH_NOT_ENABLED`  
Research source: `fefff5b49ecfbe4f5cfb4aa62cf29f6f9f26aa03` / `docs/readings/600598-beidahuang-tax-regime-continuation-2026-09-16/README.md` / blob `b9cfdc9c82e9adfdcb4773243f769a299db5877e`  
Research cutoff: `2026-09-16T02:25:49Z`  
Investment Authority: `NONE`

## 1. 本轮只做 Price → Odds，不重开 Research

冻结 Belief 不变：北大荒的主要股东经济是国有耕地发包、统一管理与服务形成的准租赁/管理现金流。2026 年 14.10 亿元历史补税与滞纳金为一次性结算且已支付，不应年化；但非职工家庭农场对应土地承包收入不享受原优惠，使长期税后盈利/现金能力较旧口径永久下调。新增经常性所得税约 2 亿元量级仍是工作假设，精确税基保持 UNKNOWN。

本页没有重跑旧 Pre/Quick，没有追加经营 Evidence，没有把价格变化改写成 Belief 变化。

## 2. 价格资格：使用最后一个可交叉验证的完成交易日，不冒充 9/16 盘中 canonical 行情

本次价格锚：

- `2026-09-15 close = CNY12.33`
- authority: `PUBLIC_MULTI_SOURCE_CONTEXT_ONLY`
- qualified market observation: `false`
- canonical market state: `false`

12.33 可由 Yahoo、CFI 与华盛通等公开页面交叉对应到 9/15 完成交易日；另有一个公开延迟页面在 9/16 上午显示 12.47，但其日期/历史行与其他来源不一致，因此未把该盘中值升级为合格行情。当前计算是 decision-use provisional / reverse-underwriting，不是 Kernel canonical numerical Odds。

价格来源：

- https://tw.stock.yahoo.com/quote/600598.SS
- https://quotewh.cfi.cn/quote1305_600598.html
- https://www.hstong.com/quotes/30000-600598-SH

## 3. 先把“正常化盈利”范围说清，而不是直接套负 TTM PE

续作中的两个独立程度有限但有用的锚：

1. 2025 归母净利润 11.6618 亿元，扣除约 1.75–2.05 亿元新增经常性所得税敏感性，得到约 **9.61–9.91 亿元**；
2. 2026H1 加回公司明确的一次性税务影响后归母约 8.7339 亿元，再加 2025H2 实际归母约 1.8175 亿元，得到约 **10.5514 亿元**。这是季节性锚，不是 2026 年预测。

因此当前只把约 **9.6–10.6 亿元**视作正常化盈利工作带。按总股本 17.776799 亿股、12.33 元计算，市值约 **219.19 亿元**，对应正常化 PE 约 **20.8–22.8x**。

现金镜头更保守：续作保存的历史 `CFO - 购建固定/无形现金 - 新增税负` 仅约 **7.31–8.93 亿元**，折合约 **0.411–0.502 元/股**，在 12.33 元对应约 **3.33%–4.07%** 的现金收益率。这个指标不是经认证 Owner Earnings，因为维护/增长 capex、季节性和营运资金时点尚未拆清。

## 4. 倍数不从农业行业平均直接拿

农业板块包含大量与北大荒经济对象不同的种植、养殖、种业和周期公司，不直接用行业平均 PE 做主锚。

同公司历史估值只作为市场表达背景：理杏仁在 2026-09-11 的历史 PE 页面给出约 `21.34x / 22.90x / 24.51x` 的 20%/50%/80% 分位；亿牛网显示 2023/2024/2025 年平均 PE 约 `24.04x / 22.16x / 23.69x`。两家口径不完全相同，因此只用于说明“过去市场常给低到中 20x”，不把任何一个点当公允倍数。

本次使用的 terminal PE 是**独立敏感性轴**：

- `15x`：深度去评级 stress；
- `18x`：税制/分红/治理风险后的明显去评级；
- `21x`：接近历史下沿的普通表达；
- `24x`：接近历史上沿的较好市场表达。

盈利和倍数分轴，避免“盈利好所以倍数也自动变高”的双计数。

历史估值来源：

- https://www.lixinger.com/equity/company/detail/sh/600598/600598/fundamental/valuation/pe-ttm
- https://eniu.com/gu/sh600598/pe_ttm

## 5. 当前 12.33 元到底要求什么

本案尚无北大荒专属 Human 持有期/回报门槛。为了形成可比较的 decision-use surface，本次以 **3 年、10% 年化总回报**作为主要工作敏感性，并同时检查 8%/12%。这不是 Human 已接受的北大荒门槛。

分红只用税前/费用前累计敏感性：中值 3 年合计 `1.20 元/股`，范围 `0.75–1.50 元/股`；不假设 2025 年的 0.55 元可以机械维持。

在 12.33 元买入、3 年总回报要求 10%、累计股息 1.20 元的条件下，2029 期末“股价 + 累计股息”需约 **16.41 元/股**。换成 2029 归母净利润要求：

| 2029 terminal PE | 为达到 3 年 10% 总回报所需 2029 归母净利润 |
|---:|---:|
| 18x | 约 **15.02 亿元** |
| 21x | 约 **12.88 亿元** |
| 24x | 约 **11.27 亿元** |

这说明当前价格不是单纯“税务利空后已经便宜”：

- 若未来市场只给 18x，必须出现远高于当前正常化带的利润增长才能达到 10%；
- 21x 时仍需要约 12.9 亿元，明显高于当前 9.6–10.6 亿元工作带；
- 24x 时只需约 11.3 亿元，经营要求并不极端，但同时要求公司在税制、分红和治理重估后仍保留接近历史上沿的市场表达。

换成 8% 门槛时，累计股息同为 1.20 元，所需 2029 净利润约为 14.15/12.13/10.62 亿元（18x/21x/24x）。因此 12.33 对 8% 目标是 **borderline**，对 10% 目标是 **not robust**。

## 6. 独立盈利 × 倍数压力面

以下统一用 3 年累计税前股息 1.20 元，只是 stress surface，不是概率世界：

| 2029 归母 | 18x | 21x | 24x |
|---:|---:|---:|---:|
| 8 亿元 | -9.0%/年 | -4.8%/年 | -0.9%/年 |
| 10 亿元 | -2.8%/年 | +1.8%/年 | +6.0%/年 |
| 12 亿元 | +2.7%/年 | +7.6%/年 | +12.2%/年 |
| 13 亿元 | +5.2%/年 | +10.3%/年 | +15.0%/年 |

完整深度 stress 再单列：若 2029 归母只有 8 亿元、terminal PE 15x、三年累计股息仅 0.75 元，则期末总价值约 **7.50 元/股**，从 12.33 元起算约 **-15.3% 年化**。这是条件下沿，不是概率预测，也不是最大回撤估计。

## 7. provisional Odds / first-entry 条件卡

`CARDINAL PROBABILITY = NOT_ESTABLISHED`。当前只做 ordinal / reverse-underwriting。

### 12 元以上（当前 12.33 在此）

`WAIT / WEAK_TO_MIXED UNDER 10% WORKING REQUIREMENT`

普通 10 亿元左右正常化盈利，即使 terminal PE 24x，三年总回报也只有约 6%；要达到 10%，需要更好的盈利和/或更高的市场表达一起成立。

### 约 11.2 元

`RE_UNDERWRITE / 8% SENSITIVITY ZONE`

约 11.27 元时，`10.5 亿元净利 / 22x / 三年股息1.20元` 的敏感性才接近 8% 年化。不是买点，也不是 Human 已接受回报要求。

### 10.0–10.7 元

`CONDITIONAL_FIRST_ENTRY_REVIEW`

约 10.66 元时，`10.5 亿元净利 / 22x / 三年股息1.20元` 的敏感性接近 10% 年化。这是目前较合理的**第一笔讨论区**，前提是冻结 Belief 没有被新税基、合同、成本、治理或分红 Evidence 破坏。

这个区间并不脱离市场现实：公开行情显示近一年低点约 10.40 元。历史价格能到达这里不证明它应当到这里，也不证明到达时 Belief 仍然成立。

### 8.8–9.5 元

`MATERIALLY_BETTER_ODDS_REVIEW`

约 8.82 元时，较低的 `9.5 亿元净利 / 20x / 三年股息1.05元` 敏感性也开始达到约 10% 年化。价格几何明显更好，但若股价真的跌到这里，必须先检查是不是出现了新的负面 Evidence，不能机械认为“越跌越便宜”。

### 约 7 元及以下

`DEEP_REUNDERWRITE`

已接近深度 stress 的价格区域。这里只允许重新研究，不形成自动加仓规则。

## 8. 第一笔“金额”现在不能伪造

价格条件可以算，但**具体第一笔金额仍 NOT METHOD-READY**。仓库里没有北大荒专属的最大仓位、第一笔可承受损失或组合风险预算。小仓位只减少暴露金额，不改变 12.33 元对应的百分比回报几何。

如果 Human 后续给出最大仓位或第一笔损失预算，可以用已选 stress value 做机械上限计算；在此之前不凭空写 1%、5 万元或四分之一仓等数字。

## 9. 当前 Decision state

```text
RESEARCH = RETAINED / FROZEN FOR THIS PRICE-ONLY ODDS PASS
PRICE = 2026-09-15 CLOSE 12.33 / PUBLIC CONTEXT ONLY
CANONICAL NUMERICAL ODDS = NOT ESTABLISHED
CARDINAL PROBABILITY = NOT ESTABLISHED
PROVISIONAL ORDINAL ODDS = WEAK_TO_MIXED AT 12.33 UNDER 10% WORKING HURDLE
CONDITIONAL FIRST-ENTRY REVIEW = 10.0–10.7
MATERIALLY BETTER ODDS REVIEW = 8.8–9.5
POSITION SIZE = NOT METHOD-READY
HUMAN ACCEPTANCE = NOT ESTABLISHED
WATCH = NOT ENABLED
ACTION / TRADE = NONE
INVESTMENT AUTHORITY = HUMAN ONLY
```

## 10. Reopen 条件

只有价格变化：复用这份冻结 Research 做 price-only refresh，不重写 Belief。

以下新 Evidence 到来时只重开受影响桥：

- 2026 年报所得税附注或公司披露显著改变经常性税基估计；
- 新年度土地承包合同/收费结构改变主引擎经济性；
- 土地承包成本与毛利趋势明显偏离当前 H1 桥；
- 分红方案/母公司可分配利润证据改变股东现金回报假设；
- 官方公告证明管理层留置背后存在更广治理/内控问题；
- 若要建立 Kernel canonical numerical Odds，则另取合格市场观察，不用本页 public context 冒充。

精确机器可读结果见 `provisional-odds.json`。
