# Xiaohongshu Price-Led Regression Gate — 2026-09-11

Status: **DOGFOOD-REGRESSION / PUBLICATION ONLY / NO RESEARCH OR INVESTMENT AUTHORITY**

This gate exists because the Hengrui draft required repeated Human correction even though the underlying Research was already strong.

The failure was not mainly factual. The writing system kept compressing a research report instead of reconstructing what the quoted share price already believed.

## Mandatory spine for price-led notes

When the headline asks whether `X元贵不贵 / 值不值 / 高估低估`, the plan should normally follow this sequence:

```text
current price
→ implied expectations already embedded in that price
→ observed business reality
→ quantified expectation gap
→ 2–4 operating paths that could close the gap
→ Evidence status for each path
→ only then introduce a required-return hurdle / future observation point
→ extra conditions required for that return
→ Evidence status for those extra conditions
→ return to the same quoted price
```

This is a planning rule, not a new valuation method.

## Regression failures to catch before drafting

Do not draft if the plan does any of the following:

1. **Research-report order**
   `业务A → 业务B → 现金流 → 最后估值` while the title asks about a price.
2. **Unexplained model parameters in the opening**
   `三年 / 10% / 30倍PE / 折现率 / 概率` appear before the current price and current implied expectations are established.
3. **Hidden-model answer arrives early**
   An internal base-case number such as `2029年104.7亿元利润` appears before the reader has seen the assumptions that produce it.
4. **Causal bridge compression**
   A business-line revenue growth rate is jumped directly into total-company future profit without preserving mix, old-business decline, pricing, margins, R&D, licensing and cash conversion where relevant.
5. **Undefined finance shorthand**
   Phrases such as `还能剩多少` do not name the economic object.
6. **Research-volume dumping**
   Findings are included because they were expensive to obtain, rather than because they move the price question forward.
7. **Epistemic over-explaining**
   The note keeps re-proving `这是事实/这是推断/不能证明` after the boundary is already clear and no longer changes the valuation logic.

## Human-accepted Hengrui lesson

The Human supplied the main line directly:

> 现在的价格是多少，现在的隐含预期是什么情况，实际是什么情况，这中间差了多少，有没有高估或者低估，缺口有没有机会实现。假设回报要多少，还需要什么条件，这个条件目前有没有证据。

Treat this as the primary calibration for future `IMPLIED_EARNINGS` price articles unless another Human-accepted case supersedes it.

## Regression assets

- Human-accepted initial draft and failure record:
  `docs/dogfood/xiaohongshu-hengrui-human-accepted-draft-2026-09-11.md`
- Structured regression fixture:
  `eval/xiaohongshu/hengrui-price-led-regression-v1.json`
- Regression tests:
  `tests/test_xiaohongshu_hengrui_regression.py`
- Style-bank sample:
  `hengrui-price-expectation-gap` in `xiaohongshu_style_sample_bank_v1.json`

## Test intent

The regression test does not certify that a future draft is good.

It certifies that future planner prompts still receive the Human-earned Hengrui lessons and negative examples. It is a guard against silently deleting the calibration during prompt/harness refactors.

A future model should still be judged semantically. If another real dogfood run repeats the same structural failure, promote the relevant item from soft calibration into a deterministic runtime validator rather than adding more prose instructions.

## Stop rule

Do not build a separate publishing framework for this gate.

Reuse the existing style sample bank, planner prompt, voice pass and tests. New machinery must be earned by a repeated observed failure after this regression is in place.
