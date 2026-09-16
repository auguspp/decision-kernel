# 北大荒 600598 — 利润主导的 provisional Odds 修订

Status: `PROVISIONAL_ORDINAL_ODDS_REVISION / HUMAN_ACCEPTANCE_NOT_ESTABLISHED / NO_ACTION / WATCH_NOT_ENABLED`  
Revision type: `VALUATION_INTERPRETATION / NOT_PRICE_ONLY / NO_NEW_OPERATING_EVIDENCE`  
Previous Odds: `cc95a4fb42f332f8384dd2240647e61fa36fd49f` / `docs/readings/600598-beidahuang-odds-2026-09-16/provisional-odds.json` / blob `3611fa961ce09596849c3054e0edf3630e013e54`  
Frozen Research: `fefff5b49ecfbe4f5cfb4aa62cf29f6f9f26aa03` / `docs/readings/600598-beidahuang-tax-regime-continuation-2026-09-16/README.md` / blob `b9cfdc9c82e9adfdcb4773243f769a299db5877e`  
Investment Authority: `NONE`

## 1. 为什么要修订

前一版把 `24x` 放在 18/21/24x 的主要反推轴里。后续复核历史估值后，证据更适合这样解释：

- 理杏仁历史 PE 的 20%/50%/80% 分位约 `21.34x / 22.90x / 24.51x`，平均约 `22.83x`；
- 亿牛网 2023/2024/2025/2026 年均 PE 约 `24.04x / 22.16x / 23.69x / 23.57x`。

因此 `21–23x` 更适合作为当前**核心市场表达带**，`24x` 保留为较好市场表达，不再用于支撑基准判断。两家数据口径不同，只用于历史市场表达背景，不把某个精确倍数认证为公允价值。

本次没有新价格，也没有新经营 Evidence；仍固定使用前一版 `2026-09-15 close = CNY12.33 / PUBLIC_MULTI_SOURCE_CONTEXT_ONLY`。因此这不是 `PRICE_ONLY`，而是估值解释修订。

历史估值来源：

- https://www.lixinger.com/equity/company/detail/sh/600598/600598/fundamental/valuation/pe-ttm
- https://eniu.com/gu/sh600598/pe_ttm

## 2. 关键经营前提不变：目前只证明稳定，没有证明增长

冻结 Research 仍支持约 **9.6–10.6 亿元**的正常化归母利润工作带。核心土地发包/管理现金流具有韧性，但当前 Evidence 并未证明公司已经进入利润增长周期。

因此这一版不再让较高 terminal multiple 替尚未证明的利润增长兜底，而是直接问：

> 若市场估值大体稳定在 21–23x，12.33 元需要未来利润做到多少，才能满足三年 10% 的工作回报要求？

## 3. 12.33 元反推的利润要求

沿用三年累计税前股息 `1.20 元/股` 的中值敏感性，三年 10% 年化总回报要求对应：

| 2029 terminal PE | 所需 2029 归母净利润 |
|---:|---:|
| 21x | **12.88 亿元** |
| 22x | **12.29 亿元** |
| 23x | **11.76 亿元** |
| 24x | 11.27 亿元（较好市场表达，仅作上沿对照） |

相对当前 9.6–10.6 亿元正常化工作带，若三年后估值在核心 21–23x，利润需要约 **3.5%–10.3%/年**的复合增长；22x 中枢大致需要 **5.1%–8.6%/年**。

这不是极高增长要求，但关键在于：**目前没有 Evidence 证明这条利润增长轨迹已经开始。**

## 4. 如果利润不增长，12.33 的回报是多少

统一保留三年累计税前股息 `1.20 元/股`，以下为条件敏感性，不是概率世界：

| 2029归母净利润 | 21x | 22x | 23x |
|---:|---:|---:|---:|
| 9.6亿元 | +0.6%/年 | +2.0%/年 | +3.4%/年 |
| 10.0亿元 | +1.8%/年 | +3.3%/年 | +4.7%/年 |
| 10.6亿元 | +3.6%/年 | +5.1%/年 | +6.5%/年 |
| 11.5亿元 | +6.2%/年 | +7.8%/年 | +9.3%/年 |
| 12.0亿元 | +7.6%/年 | +9.2%/年 | +10.7%/年 |
| 12.5亿元 | +9.0%/年 | +10.6%/年 | +12.1%/年 |
| 13.0亿元 | +10.3%/年 | +11.9%/年 | +13.5%/年 |

所以，在“估值基本稳定”的假设下，**决定当前 Odds 的主要变量确实变成利润水平**。

当前 Evidence 支持的 9.6–10.6 亿如果只是横盘，12.33 元大多只能给出低到中个位数年化总回报；要稳定进入 10% 左右的工作回报区间，利润大致需要上到 **12–13 亿元**。

## 5. old → new 修订桥

前一版：

- `10.0–10.7` = conditional first-entry review；
- `8.8–9.5` = materially better Odds review；
- 12.33 = `WEAK_TO_MIXED_NOT_ROBUST`。

本次修订原因不是新价格，而是 `24x` 不再作为基准支撑，并且“利润增长尚未被 Evidence 证明”被提升为主要判断轴。

新的条件卡：

### 12 元以上（当前 12.33）

`WAIT / UNPROVEN_PROFIT_GROWTH_PREPAID`

在核心 21–23x 下，为达到三年 10% 工作回报，需要 2029 归母约 11.76–12.88 亿元。当前价明显在预付尚未证明的利润增长。

### 11.0–11.3 元

`RE_UNDERWRITE / UPPER_EVIDENCE + UPPER_CORE_VALUATION`

约 11.21 元时，`10.6亿元 / 23x / 三年股息1.20元` 才接近 10% 年化。它同时使用当前正常化利润带的上沿和核心估值带的上沿，因此只是重审区，不作为默认第一笔。

### 9.8–10.3 元

`CONDITIONAL_FIRST_ENTRY_REVIEW`

约 10.29 元时，`10.1亿元 / 22x / 三年股息1.20元` 接近三年 10% 年化。这个区域更接近“利润不增长、估值维持中枢”也能成立的第一笔讨论区。

### 9.3–9.6 元

`MATERIALLY_BETTER_ODDS_REVIEW`

约 9.42 元时，较低的 `9.6亿元 / 21x / 三年股息1.20元` 也接近三年 10% 年化。这意味着即使利润停在当前 Evidence 下沿、估值落在核心下沿，价格几何仍开始变得有吸引力。

### 约 7 元及以下

`DEEP_REUNDERWRITE`

继续沿用深 stress 用途，不形成机械加仓规则。

## 6. 修订后的 Odds

```text
RESEARCH = FROZEN / UNCHANGED
PRICE = 2026-09-15 CLOSE 12.33 / PUBLIC CONTEXT ONLY
REVISION = VALUATION_INTERPRETATION / PROFIT-LED
CORE TERMINAL PE = 21–23x
24x = UPPER / GOOD MARKET EXPRESSION, NOT BASE
CURRENT EVIDENCE-SUPPORTED NORMALIZED PROFIT = ~9.6–10.6bn CNY
EVIDENCE OF PROFIT GROWTH = NOT ESTABLISHED
CANONICAL NUMERICAL ODDS = NOT ESTABLISHED
CARDINAL PROBABILITY = NOT ESTABLISHED
PROVISIONAL ORDINAL ODDS @12.33 = WEAK / UNPROVEN_PROFIT_GROWTH_PREPAID
RE_UNDERWRITE = 11.0–11.3
CONDITIONAL FIRST-ENTRY REVIEW = 9.8–10.3
MATERIALLY BETTER ODDS REVIEW = 9.3–9.6
HUMAN ACCEPTANCE = NOT ESTABLISHED
POSITION SIZE = NOT METHOD-READY
WATCH = OFF
ACTION = NONE
INVESTMENT AUTHORITY = HUMAN ONLY
```

## 7. 什么 Evidence 会让 12.33 重新变得更合理

不是粮价本身，而是利润桥开始兑现：

- 土地承包费收入持续快于对应成本；
- 农业分公司利润从当前近似横盘转为持续同比增长；
- 新增所得税后的归母利润/股东现金同步增长；
- 分红能力没有被税制与母公司可分配利润明显削弱。

如果未来报告期能把正常化利润从约 10 亿推向 12 亿并留下可持续证据，12.33 的 Odds 会明显改善；在此之前，它主要是在支付尚未证明的利润增长。
