# Xiaohongshu Hengrui Human-Accepted Draft — 2026-09-11

Status: **HUMAN_ACCEPTED_DRAFT / STRUCTURE+VOICE CALIBRATION / PUBLICATION OUTCOME NOT YET OBSERVED**  
Security: **恒瑞医药 / 600276.SH**  
Accepted by Human: **2026-09-11**  
Investment Authority: **NONE**

## Why this record exists

This dogfood run was unusually expensive in Human editing time even though the underlying Research was already strong.

The failure was not mainly factual. It was a publication-sequencing failure: the draft repeatedly compressed a multi-round Deep Research package into a shorter research report instead of building one price-driven argument that a reader could follow without knowing the internal model.

The Human accepted the final version below as an **initial draft**, not as final publication copy and not as evidence of publication performance.

The purpose of this record is to reduce repeat failures for future models / agents.

## Accepted title

> **创新药还有机会吗，42元的恒瑞医药贵不贵？**

## The writing sequence that finally worked

For a price-led public-equity note, use this sequence unless the Research clearly requires another structure:

```text
current price
→ what expectations the current price already implies
→ what the company has actually proved today
→ quantify the gap between implied expectations and observed reality
→ identify which operating paths could close that gap
→ ask whether those paths have Evidence or are still assumptions
→ only then add a required-return hurdle / future observation point
→ state the extra conditions required for that return
→ check whether those extra conditions have Evidence
→ return directly to the quoted price
```

This is more specific than generic `price -> base -> residual -> future economics -> price`.

The key lesson from Hengrui is that **current implied expectations come before the author's internal base case**. A reader should not be handed an unexplained model answer and then asked to trust the rest of the article.

## Human feedback sequence and what it taught

### Failure 1 — Research process narration leaked into the article

Early drafts opened with things like:

- `我停更小红书挺久了`
- `最近刚好把自己折腾了几个月的投研系统真正用起来`
- `我一开始以为...`

This violated the existing voice calibration. The company and price should appear immediately. Research process belongs in trace, not publication.

### Failure 2 — Research-report order replaced the price argument

The early structure was roughly:

```text
innovation drugs
→ License-out
→ cash flow
→ valuation
```

This is a research memo order. The Human reported losing interest around the first third and only reconnecting in the final third, when the article finally returned to the question `42.93元到底要求什么`.

Reader-dropout signal:

> If the headline asks whether a price is expensive, but the first third can be read without remembering the price, the note is probably drifting into a research report.

### Failure 3 — Causal bridges were compressed away

Rejected examples included:

> `先要看这16%的创新药增长，最后能不能长成126亿元利润。`

This jumps directly from one business-line revenue growth rate to total-company future profit. It silently skips old-product decline, mix, pricing, margin, R&D, License-out, and cash conversion.

Another rejected phrase was:

> `高基数以后还能剩多少。`

`剩多少` has no defined object. Does it mean growth rate, revenue, patient count, price, profit, or cash?

Rule:

> Compression may remove words. It may not remove the causal bridge.

When shortening, keep the economic object explicit.

### Failure 4 — Jargon sounded like an analyst memo rather than normal speech

Rejected heading:

> `License-out已经赚到真钱，但还不能当成年金`

`年金` is technically interpretable but unnatural in this article's voice and mismatched with `赚到真钱`.

Preferred move:

> `海外授权已经证明能收钱，问题是最后能留下多少。`

The sentence should sound like a person examining a stock, not a memo translating finance vocabulary into slogans.

### Failure 5 — Internal model outputs appeared before the reader had seen the model

Rejected early sentence:

> `而我目前这套基准假设里，2029年利润大约只有104.7亿元。`

The reader had not yet seen the assumptions that produced CNY104.7bn. The number arrived like an answer taken from a hidden spreadsheet.

Rule:

> A model output cannot become an article premise before its inputs have been introduced.

If a number comes from an internal model, either:

1. derive it after the reader has seen the relevant assumptions, or
2. omit it.

### Failure 6 — Valuation parameters were smuggled in as defaults

The draft initially said:

> `假设2029年市场给恒瑞30倍PE...`

Human immediately asked: **为什么是30倍？**

Then the draft used a three-year holding period. Human asked: **为什么是三年？**

These are the same class of error.

PE, holding period, required return, discount rate, terminal date, and probability are **model parameters**, not facts.

Rule:

> Never let a model parameter appear as if the company itself supplied it.

Before using a parameter, do one of three things:

- justify it with Research;
- show a bounded range rather than one unexplained point;
- explicitly introduce it later as a diagnostic / required-return test after the current price and current reality are already clear.

For Hengrui, the accepted structure first used a PE range to show the earnings currently implied by CNY42.93. The 10% return hurdle and 2029 observation point only appeared later as a second-stage question.

### Failure 7 — Too much good Research was forced into the article

The Hengrui Deep contained many valuable findings: revenue bridge, product-level growth, GSK contract-liability mechanics, interest income in OCF, IDEAYA milestone details, capitalized development cash, cash/NewCo double-counting checks, and more.

The drafts became verbose because they implicitly followed this rule:

> `辛苦查出来的东西最好都写进去。`

That rule is wrong.

Publication should keep only facts / derivations that advance the reader's single price question.

Research depth is valuable even when most of it remains invisible.

### Failure 8 — Repeating epistemic boundaries became its own kind of verbosity

Once the structure improved, the draft still repeated variants of:

- `已经证明A，但还没证明B`
- `这不是事实，只是假设`
- `不能全部算进去`

These distinctions matter, but repeating the full boundary after the reader already understands it makes the article feel defensive.

Rule:

> State each important boundary at the point where it changes the valuation logic. Do not keep re-proving that the author has epistemic discipline.

## Human-supplied core writing rule

The Human eventually stated the article's desired main line explicitly:

> **现在的价格是多少，现在的隐含预期是什么情况，实际是什么情况，这中间差了多少，有没有高估或者低估，缺口有没有机会实现。假设回报要多少，还需要什么条件，这个条件目前有没有证据。**

This is the primary Hengrui calibration lesson.

For future agents, translate it operationally as:

1. **Current price** — start with the quoted per-share price.
2. **Current implied expectation** — work backward from current price using bounded valuation cases. Do not pick one unexplained PE.
3. **Actual state** — show only the business Evidence needed to evaluate those implied expectations.
4. **Gap** — quantify how much earnings / cash / operating progress separates current reality from the priced expectation.
5. **Can the gap close?** — identify the few operating paths that can close it.
6. **Evidence status** — for each path, state what is proved and what remains unproved.
7. **Return hurdle** — only after the current price is understood, ask what conditions are needed for a desired future return.
8. **Evidence for the hurdle** — do not turn desired-return math into a forecast. Ask whether the extra conditions already have evidence.
9. **Price closure** — return to the quoted price and answer it directly.

## Number sequencing rule

A strong note should feel like each number creates the next question.

Good sequence:

```text
42.93元
→ 2025 actual profit / EPS
→ current price implies different profit levels at 36x / 30x / 24x
→ compare those implied levels with actual business progress
→ quantify the profit gap
→ ask whether innovation / licensing / margin / cash can close it
→ later, add a 10% return hurdle and show the extra profit / valuation condition
→ return to 42.93元
```

Bad sequence:

```text
42.93元
→ 3 years
→ 10% required return
→ 30x PE
→ CNY126bn profit
→ innovation sales growth
```

The bad sequence introduces three unearned model parameters before the reader even knows what today's price is already expecting.

## Voice calibration earned here

Prefer:

- concrete objects (`利润`, `现金`, `患者`, `净价`, `收入`)
- direct questions (`这部分利润从哪里来？`)
- ordinary words (`能收钱`, `能留下多少`)
- one number followed by what that number changes

Avoid:

- undefined shorthand (`还能剩多少`)
- finance-jargon slogans (`不能当成年金`)
- narrator scaffolding (`我重新算了一遍`)
- research-process narration
- unexplained model parameters
- compressing revenue growth directly into total-company profit
- showing research volume for its own sake

## Planning check before drafting

Before writing prose, the planner should be able to answer all of these in plain language:

1. What is the current quoted price?
2. What does that price already require at several bounded valuation levels?
3. What has the company actually proved today?
4. What is the numeric gap between the implied expectation and current reality?
5. Which 2–4 business mechanisms can close that gap?
6. What Evidence supports each mechanism?
7. Which model parameters are merely diagnostics, and have they been introduced / justified before use?
8. If a required return is introduced, what additional conditions does it require beyond today's implied expectations?
9. Does the conclusion return to the same per-share price as the title?

If any answer is missing, **do not draft yet**. The missing bridge is either a planning defect or a Research Challenge.

## Human-accepted initial draft

### 创新药还有机会吗，42元的恒瑞医药贵不贵？

42.93元。

2025年，恒瑞医药归母净利润77.11亿元，EPS 1.19元。

按这个利润算，42.93元对应大约36倍PE。

2026年上半年，公司归母净利润44.65亿元。即使简单翻倍，也只有89亿元左右，而且半年利润里还有授权收入、公允价值变动等因素，不能直接当成年化盈利。

所以42.93元买的，不只是恒瑞现在已经赚到的钱。

市场已经提前买了一部分未来利润。

这部分未来，主要来自创新药。

#### 1、42.93元现在隐含了多少利润？

先不争恒瑞到底该值多少倍。

直接倒过来看。

按目前约66.37亿股计算：

36倍PE，对应大约79亿元利润。

30倍，对应大约95亿元。

24倍，对应大约119亿元。

2025年实际利润是77.11亿元。

所以如果市场长期愿意给恒瑞36倍左右的估值，现在的利润已经能解释大部分股价。

但如果以后估值回到30倍，利润就要从77亿元涨到95亿元左右。

如果只给24倍，则要接近120亿元。

这就是42.93元现在包含的预期：

**恒瑞未来的利润还得继续往上走。**

接下来要看的，就是这部分增长有没有依据。

#### 2、创新药在增长，但老产品也在往下掉

2026年上半年，恒瑞创新药销售88.09亿元，同比增长16.38%，已经占药品销售六成以上。

但同期公司营业收入下降1.94%，扣非净利润下降12.71%。

拆开看就很清楚。

创新药大约增加了12.4亿元收入。

仿制药减少了约9.8亿元。

也就是说，新药带来的大部分增量，先填了老产品下滑留下来的缺口。

创新药内部也有明显分化。

肿瘤创新药收入62.65亿元，只增长2.58%。

真正快的是非肿瘤创新药，收入25.45亿元，同比增长73.97%。

这批产品已经开始放量，这是确定的。

但很多产品刚进入医保或者还在快速爬坡。

接下来要验证的，是首轮放量过去以后，患者还能不能继续增加，价格能守住多少，最后能不能把收入增长变成利润增长。

恒瑞现在需要的不只是继续出新药。

还要靠新药不断接住老产品的下降。

#### 3、海外授权也能补利润，但能补多少还不确定

恒瑞这几年做了不少海外授权。

GSK、MSD、IDEAYA、Braveheart等合作，都已经产生过实际收款。

所以研发成果能不能卖出去，这件事已经有答案了。

能卖，而且有人愿意付真钱。

2026年上半年，公司确认许可收入14.22亿元，直接营业成本只有约0.22亿元。

但不能因此把接近14亿元都当成稳定利润。

一款药成功授权之前，还有研发人员、临床、失败项目和持续开发。

这些成本不一定都挂在某一笔合同下面，但想继续做下一笔授权，就必须继续花。

之前的中间模型里，假设海外授权未来每年能贡献15亿元税后利润。

这个数字目前还没有被充分证明。

所以海外授权已经证明的是：

**恒瑞的研发平台有经济价值。**

还没证明的是：

**这套平台一年到底能稳定留下多少利润。**

#### 4、价格和现实之间，到底差多少？

目前看，恒瑞未来利润继续增长是有基础的。

非肿瘤创新药在放量。

海外授权已经能变现。

创新药占比也在继续提高。

但利润兑现还没有完全跟上。

2025年利润77亿元。

42.93元如果以后对应30倍PE，需要大约95亿元利润。

中间差不到20亿元。

这不是一个离谱的缺口。

问题在于，这20亿元不能只靠“创新药还会增长”一句话填上。

它需要更具体的东西：

非肿瘤新药高基数以后还能继续放量。

成熟产品下滑逐渐放缓。

License-out扣掉完整研发成本以后，确实能留下稳定利润。

利润最终还能转成现金，而不是继续被研发和资本投入吃掉大部分。

目前这些方向都有证据。

但还没有哪一条强到可以说，95亿元甚至更高的正常化利润已经基本确定。

#### 5、如果还要求10%左右的回报呢？

可以再往前看一步。

拿2029年做一个观察点，不是因为三年是什么标准持有期，而是现在这一批新药、医保放量和授权项目，到那时应该已经经历几个完整报告期。

42.93元如果三年年化10%，2029年需要到57.14元。

对应的利润要求是：

24倍PE：约158亿元。

30倍：约126亿元。

36倍：约105亿元。

此前做过一组中间测试：

创新药销售每年增长20%，其他药品每年下降6%，药品税后净利率23%，授权业务每年贡献15亿元税后利润。

算下来，2029年正常化利润大约105亿元。

如果届时还能给36倍PE，10%左右的回报可以实现。

如果只给30倍，利润则要做到126亿元。

又多了20多亿元。

而且105亿元这套假设本身已经不算保守，里面还包含目前尚未完全验证的15亿元授权税后利润。

所以如果对回报要求更高，42.93元对恒瑞未来的要求也会明显提高。

#### 42.93元贵不贵？

**不算离谱，但也看不出便宜。**

恒瑞的创新药转型已经有真实收入，海外授权也已经拿到真钱，所以市场给它成长溢价有依据。

但42.93元已经提前包含了一部分利润继续增长的预期。

如果未来创新药放量、授权利润和现金转化继续兑现，现在的价格可以成立。

如果只是创新药收入继续增长，但利润和现金没有明显抬升，那现在这部分成长溢价就会显得偏贵。

所以恒瑞现在最值得看的，不是又多了一条管线，也不是下一笔授权有多少亿美元。

是两件更普通的事：

**新药卖出去以后，到底能多赚多少钱。**

**这些利润最后又能留下多少现金。**

创新药还有机会。

42.93元的问题，是这个机会已经不是免费的了。

本文仅为个人研究记录，不构成投资建议。

## Calibration status

- `HUMAN_ACCEPTED_DRAFT`: yes
- `PUBLICATION_PERFORMANCE`: not observed
- `HIGH_READ`: do not assign yet
- `INVESTMENT_DECISION`: none
- `RESEARCH_AUTHORITY`: unchanged

Future publication outcome, if any, should be recorded separately.
