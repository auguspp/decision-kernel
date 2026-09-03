# Xiaohongshu Price Closure v1

Status: **PUBLICATION REVIEW RULE / DOGFOOD-DERIVED / NO NEW RESEARCH AUTHORITY**  
Applies when a note's headline asks whether a quoted per-share price is expensive / cheap / justified.  
Investment Authority: **NONE**

## Why this exists

Sanhua dogfood exposed a publication failure even after the Research had correctly isolated a CNY400-700bn residual above normalized core value.

The draft still felt unfinished because it stopped at market-cap language:

```text
current market cap
→ core value
→ hundreds of billions of residual
```

The reader's actual question was stated in **yuan per share**.

A price article should therefore close the loop in the same unit as its headline.

## Core rule

If the headline is `X元贵不贵`, the valuation argument should return to `X元` before the conclusion.

Preferred chain:

```text
current price/share
→ observable core value/share
→ residual price/share
→ future economics required by that residual
→ future economics converted back into today's value/share
→ direct answer to the headline price
```

Do not make the reader convert a CNY50bn residual into per-share value mentally.

## Research boundary

Publishing may only perform this closure when all arithmetic is already declared as Research-safe / publication-safe `DERIVATION` inputs.

If the draft needs a new discount rate, terminal multiple, future profit number, probability, or timing assumption that is not present in the brief, stop.

That is a Research Challenge, not a writing problem.

Never:

```text
headline asks 36.3元贵不贵
→ draft discovers 600亿元 residual
→ drafter invents a robot profit / discount rate
→ returns a neat price target
```

Instead:

```text
headline asks 36.3元贵不贵
→ residual exposed
→ missing option-economics bridge exposed
→ Research re-underwrites the bridge
→ declared derivations return to Publishing
→ draft translates the bridge into price/share
```

## Useful price closure forms

Depending on the case, any of these may be appropriate if supported by Research:

### Implied earnings

```text
current price
→ current market cap
→ earnings required at 15x / 20x / 25x
→ compare with supported earning power
```

### Core + optionality

```text
core value/share
+ discounted future optionality value/share
= implied current price/share
```

### SOTP

```text
listed asset/share
+ operating business/share
+ residual/share
= current price/share
```

### Cyclical normalization

```text
normalized profit
× bounded valuation
÷ shares
= normalized value/share
```

No method is canonical. The unit closure is the rule.

## Sanhua earned example

Current Research challenger:

```text
core midpoint ≈ CNY22.2/share
```

Under a declared publication diagnostic of end-2030 optionality economics, 25x mature P/E and 9% discount rate:

```text
10亿元 durable 2030 optionality profit ≈ +CNY4.1/share today
20亿元 ≈ price CNY30.4
30亿元 ≈ price CNY34.5
35亿元 ≈ price CNY36.6
```

This is clearer than stopping at `~CNY54-64bn residual` because it answers the same question the title asked.

The numbers above are Sanhua-specific Research derivations. They are **not** reusable valuation constants.

## Review question

Before publication, ask:

> If the title contains a share price, does the final valuation logic come back to a share price using only declared derivations?

If no, the draft is not closed yet.

## Stop rule

Do not turn price closure into a target-price generator.

The purpose is to expose what the observed price requires, not to issue a recommendation or Human action.
