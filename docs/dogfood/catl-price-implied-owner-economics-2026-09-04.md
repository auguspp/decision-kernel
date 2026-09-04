# CATL / 300750.SZ — price-implied owner-economics closure at CNY351

Status: **BOUNDED REVERSE-UNDERWRITING / NO TARGET PRICE / NO CARDINAL PROBABILITY / NO NUMERICAL ODDS**  
Observation: **CNY351.00, completed 2026-09-04 A-share close**  
Research cut-off: **2026-09-04 16:55 +08:00**  
Investment Authority: **NONE**

## Purpose

This note answers one question:

> **What owner economics must be true for CNY351 to deliver an acceptable long-term return?**

It does not answer:

```text
what the stock will trade at
what probability each scenario has
whether the Human should buy
```

The old generic dogfood used three EPS values, three terminal P/E values and a `25% / 50% / 25%` probability distribution. Those inputs were illustrative mechanics fixtures. This note replaces that false precision with explicit requirement surfaces.

---

## 1. Observation-unit closure

Inputs:

```text
price = CNY351.00/share
total shares ≈ 4.626654919bn
market cap ≈ CNY1,623.96bn
H1 attributable equity ≈ CNY379.35bn
book value/share ≈ CNY81.99
P/B ≈ 4.28x
```

Historical / current earnings anchors:

```text
2025 parent profit = CNY72.20bn
2025 adjusted parent profit = CNY64.51bn
2026 H1 parent profit = CNY43.28bn
2026 H1 adjusted parent profit = CNY39.01bn
```

Mechanical ratios:

```text
2025 reported P/E ≈ 22.5x
2025 adjusted P/E ≈ 25.2x
H1 reported annualisation P/E ≈ 18.8x
H1 adjusted annualisation P/E ≈ 20.8x
```

The H1 annualisations are sensitivities, not forecasts.

---

## 2. 2028 earnings required for a 10% return

Equation:

```text
required 2028 EPS
= current price × (1 + required return)^2 / terminal P/E
```

No explicit dividend or excess-cash credit is included.

| Terminal P/E | Required 2028 EPS | Required 2028 profit | 2025–2028 profit CAGR |
| ---: | ---: | ---: | ---: |
| 12x | CNY35.39 | CNY163.75bn | ~31.4% |
| 15x | CNY28.31 | CNY131.00bn | ~22.0% |
| 18x | CNY23.60 | CNY109.17bn | ~14.8% |
| 20x | CNY21.24 | CNY98.25bn | ~10.8% |
| 24x | CNY17.70 | CNY81.87bn | ~4.3% |

Interpretation:

- 24x terminal valuation requires little profit growth but asks the market to preserve a premium multiple for a capital-intensive manufacturer.
- 15x–20x requires roughly CNY98bn–131bn 2028 parent profit.
- 12x demands a much more aggressive earnings outcome.

Dividends and genuinely excess cash lower the required earnings. Capital consumption, dilution, lower terminal multiples or weaker cash conversion raise them.

---

## 3. P/B and sustainable ROE

Simplified identity:

```text
P/B ≈ (ROE - g) / (r - g)
therefore
ROE ≈ P/B × (r - g) + g
```

At P/B ≈ 4.28x:

| Cost of equity `r` | Perpetual growth `g` | Implied sustainable ROE |
| ---: | ---: | ---: |
| 10% | 4% | ~29.7% |
| 10% | 5% | ~26.4% |
| 10% | 7% | ~19.8% |
| 11% | 4% | ~34.0% |
| 11% | 5% | ~30.7% |
| 11% | 7% | ~24.1% |

This assumes a stable steady state and does not separately value excess cash. It is not a target-price model.

The key result is:

> **CNY351 requires CATL to remain an unusually high-ROE industrial manufacturer for a long time, or to retain high growth long enough that today's premium book multiple is not eroded.**

---

## 4. Cash-yield surface

Raw cash sensitivity:

```text
2025 OCF ≈ CNY133.22bn
2025 fixed/intangible/other long-term asset cash purchases ≈ CNY42.35bn
2025 raw FCF ≈ CNY90.88bn
2025 raw FCF yield at CNY351 ≈ 5.6%

2026 H1 OCF ≈ CNY60.22bn
2026 H1 cash asset purchases ≈ CNY25.07bn
H1 raw FCF ≈ CNY35.14bn
H1 annualised raw FCF yield ≈ 4.3%
```

But H1 owner-cash quality must be adjusted conceptually for:

```text
inventory build
+ receivable build
- payable funding
- supplier financing
- growth capex
- warranty / quality obligations
- global expansion commitments
```

Therefore a raw FCF yield is not a sufficient buy signal.

---

## 5. Capital-allocation sensitivities

### A-share cancellation buyback

Approved:

```text
CNY20bn–40bn
price cap CNY573
not started as of 2026-08-31
```

At a purely mechanical CNY351 execution price:

| Gross spend | Shares retired | Current-share reduction | Gross EPS lift |
| ---: | ---: | ---: | ---: |
| CNY20bn | ~57.0m | ~1.23% | ~1.25% |
| CNY40bn | ~114.0m | ~2.46% | ~2.53% |

This excludes financing cost, lost interest, taxes and opportunity cost.

### Financial liquidity

A rough H1 sensitivity:

```text
cash + wealth-management assets ≈ CNY440.21bn
borrowings + bonds + leases ≈ CNY127.02bn
rough net financial liquidity ≈ CNY313.19bn
≈ CNY67.69/share
```

Do not automatically deduct CNY67.69 from price. A material part of liquidity is operating / strategic capital, including unused H-share proceeds and planned global / zero-carbon deployment.

---

## 6. Evidence burden by valuation world

### Lower-multiple world — 12x–15x

Requires:

```text
2028 profit ≈ CNY131bn–164bn
```

Evidence needed:

- sustained high battery volume;
- stable or recovering EV / ESS margin;
- large overseas profit contribution;
- working-capital discipline;
- capex productivity;
- no large policy-driven market loss.

### Middle world — 18x–20x

Requires:

```text
2028 profit ≈ CNY98bn–109bn
```

This is less demanding operationally but still requires a quality premium, because terminal valuation remains above a commodity-manufacturer multiple.

Evidence needed:

- high-teens-ish profit growth or equivalent dividends / buybacks;
- durable share leadership;
- acceptable incremental ROIC;
- owner cash keeping pace with profit.

### Premium-duration world — 24x

Requires:

```text
2028 profit ≈ CNY82bn
```

The earnings requirement is modest, but the valuation burden shifts to duration:

- CATL must remain structurally different from cyclical battery manufacturers;
- technology / customer / service moats must preserve high returns;
- new businesses must extend duration without destroying capital efficiency;
- policy fragmentation must remain manageable.

---

## 7. Closure

```text
PRICE REQUIREMENT = BOUNDED / EXPLICIT
CHEAPNESS = NOT ESTABLISHED
EXPENSIVENESS = NOT ESTABLISHED
CARDINAL PROBABILITY = NOT ESTABLISHED
NUMERICAL ODDS = WITHHELD
```

At CNY351:

> **The market is not demanding an impossible earnings number, but it is demanding either sustained double-digit profit growth into 2028 or a durable premium multiple, while also assuming that global capex, working capital and new-business investment will not dilute long-run owner returns.**

The existing public evidence supports scale, share and demand. It does not yet support a probability-weighted answer to the full simultaneous requirement set.

---

## Source / lineage pointers

- `docs/dogfood/catl-full-research-reunderwrite-2026-09-04.md`
- `dogfood/300750-catl.json` — superseded for current numerical Decision authority, retained for audit.
- `docs/full-research-review-gate-v1.md`
- `docs/full-research-price-implied-economics-closure-v1.md`
