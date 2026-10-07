# D｜普源两期成本列报桥：数值差额收窄，现金与机会判断不补签

2026-10-07，Asia/Singapore。归属 [#509][TASK]；本批授权 [6027934572][START]。性质：**RETAINED_RESEARCH_CONTINUATION / NOT_FULL / NOT_NUMERICAL_ODDS / D_IN_PROGRESS**。

代码基线 M=`fbac318df6e65d1eecacadba0b13ce3695f3bcb3`；本次观察固定 R=`e466d73414c569fb986af358a7ae37dc35fdc7f0`。这两个版本与下方历史原件版本不混用。本件不修改原 ResearchSnapshot、Human 决定、价格条件、期限或自动任务。

## 1. 这次真正改变了什么

[前驱三例补证][PRE]已指出：普源 A 股与 H 股报告的毛利率同比方向不同，当期成本列报相差约1,108万元，尚未查明分类桥。**本次从精确保存的 A 股中报找出两项候选解释：税金及附加，以及存货跌价损失及合同履约成本减值损失。将这两项加到 A 股营业成本后，两期结果均与前驱保存的 H 股 cost of sales 相容至千元披露精度。**

这把原“成本差异未解释”收窄为“已有双期数值桥，官方具体重分类依据仍待核实”。它不是新经济事件，不是证明两份报告全部口径一致，也不是正式会计政策认证。不能因数值相等便宣布已读到港股附注的分类说明。本轮未重新取得原 PDF；H 股数值仍明确继承前驱实际读取记录。[S-A、S-H]

研究含义是：**不能把两个毛利率方向当作两套互相否定的经营事实，也不能只挑上升的一套讲改善。** 同一成本桥下，收入、成本负担和毛利额分别解释；库存/应收占用、现金与融资分母仍按原研究处理。原“经营改善但持续现金转换未建立”的限制未被这次数值对账解除。[CASH]

## 2. 两期金额如何勾稽

下表金额均为人民币元。A 股列来自原合并利润表及附注；资产减值按损失的正金额加入成本，不把信用减值混入。H 股比较值是前驱保存的231,887／170,651千元乘1,000，仍是披露精度值，不冒充精确到元的原始账目。

| 项目 | 2026H1 | 2025H1 |
|---|---:|---:|
| A 股营业收入 | 486,842,894.90 | 354,968,365.55 |
| A 股营业成本 | 220,805,439.15 | 158,352,858.95 |
| 税金及附加 | 5,052,180.01 | 5,638,071.13 |
| 存货跌价及合同履约成本减值损失，正金额 | 6,029,336.62 | 6,660,066.09 |
| **三项成本合计** | **231,886,955.78** | **170,650,996.17** |
| H 股 cost of sales，千元展示值换算 | 231,887,000 | 170,651,000 |
| **H 展示值减三项合计** | **44.22** | **3.83** |
| A 股收入减三项合计，分析毛利额 | 254,955,939.12 | 184,317,369.38 |

原件定位：A 股报告第84页为收入/营业成本，第85页为税金及附加、信用减值及资产减值；第166页核收入成本及税金总额，第170页核资产减值类别。H 股 cost of sales 来自前驱 S3 的第3页读取记录。本轮通过 GitHub 取回的是固定 context 的相应文本页段及前驱记录，没有重新计算整份435,146字节 context 或原PDF的摘要。[S-A、S-H]

两期差额均落在按最近千元展示的相容范围内；使用四舍五入只作分析兼容性检查，不声称已经取得发行人的舍入政策。双期同时吻合，比只拿本期差额配一个科目更有约束，但仍不足以替代官方分类说明。

### 毛利率方向为何可以不同

使用同一份 A 股精确收入作为分母，避免将人民币元和 H 股千元舍入分母混算：

| 比较 | 2026H1 | 2025H1 | 同比变化，百分点 |
|---|---:|---:|---:|
| A 股原营业成本口径毛利率 | 54.645443% | 55.389586% | −0.744143 |
| 两项额外成本负担／收入 | 2.276200% | 3.464573% | −1.188373 |
| 同一成本桥下的分析毛利率 | 52.369243% | 51.925013% | +0.444230 |

恒等关系为：`分析毛利率变化 = 原毛利率变化 − 额外成本负担率变化`。本例 `−0.744143 − (−1.188373) = +0.444230`（展示已舍入）。因此方向翻转可以由所选成本负担率变化解释，**不需要先假定产品竞争力发生两种相反变化**。这个分析值不是另造“标准化盈利”，税费与减值也没有从利润或现金中消失；后续分析不得重复扣减。[本次计算]

## 3. 反证、歧义与不得越过的结论

已做的数值反例：分别漏掉税金、漏掉存货/合同成本减值、把减值符号反转、额外加入信用减值，或把元误作千元；两期共10个变体均不能得到原 H 股千元成本。信用减值本期／上期为2,283,854.31／289,264.08元，属于单独检查项，不因都含“减值”二字并入候选桥。[S-A；本次计算]

原文本第170页分类行与第85页均将上期资产减值列为损失−6,660,066.09元，但第170页合计行提取文本少一个负号。本件据两个一致位置取损失金额，同时保留异常；**未取得页面图像，不能判断原报告、排版还是提取出了问题，也没有改写原文。**

本件没有完成 A/H 整套准则、税后利润、每股收益、现金流或资产负债对账。港股 non-IFRS adjusted profit 仍不等于 A 股扣非；收入/毛利变化也不证明超出事前市场预期。没有已核的事件前预期与适用价格链，不生成预期收益、上涨概率、目标价或新的首笔条件。[PRE]

## 4. D 模块接续：解决一项当前解释缺口，不把其他责任写成等待即可

**普源：** KEEP 原经营改善、现金占用和融资分母的研究；将“无法解释成本差异”更新为本件的双期数值候选桥。当前仍可继续核官方分类说明、可比历史账龄/期后回款、融资后每股口径及事件前预期。此前成本差异本身不再被当作经营恶化证据；不存在因本件而自动建立的短期机会或 Full 委托。[CASH、RIGOL]

**圆通：** 本轮恢复[已有成本与条件定价][YTO]，确认其中9.4分/票抵消量、总量增长与单位利润区别、股息/股数及联合下行已完成，不能再包装成新交付。前驱原公告确认量价但没有当月成本；H1成本不能代入8月、同业并表单价不能代入圆通。下一经济增量应来自实际可比成本、季度单位利润、现金或网络材料；新材料只支持原证据驱动 QUIET／REOPEN 判断，不新增价格触发。[PRE、YTO]

**兆易：** 本轮恢复[已有采购研究][GIGA]和固定R的经济接续。额度不等于采购、采购不等于成本、毛利率下降不必等于毛利额下降，这些均已完成，不重复计算凑成果。下一增量是审批结果或条款变化，以及相关产品成本后毛利额、存货/预付/应收与现金的实际兑现。10月20日14:30仍为原安排的审批窗口，11月30日为原分析者复核，不改成营收确认、自动任务或交易期限。原长期Human条件不动。[GIGA]

**期限及成熟结果：** 本次在固定R实际读到的联合文件仍将S0置null，5／20日状态为WAITING_FOR_COMPLETED_SESSION；原冻结为2026-10-04T01:03:53Z，长期期限2027-09-02、分析者复核2026-11-30未变。文件中的MU比较仍是一个公司指引事件、四指标，AI成绩/概率分数未建立。这是所读投影的状态，不是本件独立重验全部原ZIP、reading_hash或经济真值。[R-JOINT]

所以，本批能够交付的是一个有实质数值依据的口径解释修订及三例接续处置；**原3–5个完整PIT机会案例、期限特定机会定价、实际使用和成熟效果没有整体签收。** 剩余不仅是未来交易日，也有当前研究/来源缺口。C的10月8、9、12、13、14固定自然窗、竞价T+1、#745 STOP、Sites暂停、禁止Codex、新城暂缓及现有任务/通知继续按原责任，不补跑或挑选成功日。[START、R-JOINT]

## 5. 可重算材料与实际验证范围

以下是本件保留的离线计算说明；只有使用者显式执行才运行，档案reader不执行代码。标准库Decimal与Fraction分别核金额，10个反例和毛利率恒等关系已在本轮本地实际运行通过；不是全仓CI、独立研究审阅或来源认证。临时运行文件不进入生产runtime，不新增长期验证义务。

```python
from decimal import Decimal as D, getcontext, ROUND_HALF_UP
from fractions import Fraction as F
getcontext().prec = 40
# period: revenue, A cost, surcharges, inventory/contract impairment,
#         separate credit impairment, H cost displayed in RMB thousand
rows = {
    '2026H1': ('486842894.90', '220805439.15', '5052180.01',
               '6029336.62', '2283854.31', '231887'),
    '2025H1': ('354968365.55', '158352858.95', '5638071.13',
               '6660066.09', '289264.08', '170651'),
}
expected = {'2026H1': ('231886955.78', '44.22'),
            '2025H1': ('170650996.17', '3.83')}
margins = {}
round_thousand = lambda v: (v / 1000).quantize(D('1'), rounding=ROUND_HALF_UP)
for period, raw in rows.items():
    revenue, cost, tax, loss, ecl, h_thousand = map(D, raw)
    adjusted = cost + tax + loss
    assert F(adjusted) == F(raw[1]) + F(raw[2]) + F(raw[3])
    assert adjusted == D(expected[period][0])
    assert h_thousand * 1000 - adjusted == D(expected[period][1])
    assert round_thousand(adjusted) == h_thousand
    variants = (adjusted-tax, adjusted-loss, adjusted-2*loss,
                adjusted+ecl, adjusted*1000)
    assert all(round_thousand(v) != h_thousand for v in variants)
    a_margin = (revenue-cost)/revenue*100
    bridge_margin = (revenue-adjusted)/revenue*100
    burden = (tax+loss)/revenue*100
    margins[period] = (a_margin, bridge_margin, burden)
    print(period, adjusted, h_thousand*1000-adjusted, margins[period])
delta = tuple(a-b for a,b in zip(margins['2026H1'], margins['2025H1']))
assert abs(delta[1] - (delta[0]-delta[2])) < D('1e-35')
print('TWO_PERIOD_BRIDGE_AND_TEN_NEGATIVE_CONTROLS_PASS', delta)
```

### 来源与读取纪律

- **S-A：** [原205页中报context][S-A]，blob `62c24a0c3e5f76d09384439f0dcc6a8e459ed8b2`。本轮读取身份页及第83–86、166–171页所在文本段。原保管说明记录整包SHA256 `b27853cd4db25ad8f8830cb33c6e06dab958f2b82912c2d47a318501e85ae463`，本件仅继承该声明，未以分段读回冒称独立重验整包。[原保管说明][CUSTODY]
- **S-H：** [前驱source-ledger][S-H] S3，具体原PDF `2026082501757.pdf`、275,945字节、SHA256 `25ad355ddfb53347a952775643a04470c451b09362a59591bdbd239d30809a99`；前驱记录2026-10-06T15:55:42.130516Z取得。H成本数值取自前驱正文，未新取得PDF或H附注全文。
- **时间：** 前驱已分别保留该H文件8月25日20:55列表发布、A报告8月26日日期和CNINFO storageTime；本轮没有把日期00:00、系统存储时间或今日读回回填为历史公众最早可得时间。新解释也不回填为10月4日冻结时系统已经知道。
- **失败：** 本轮Web打开原A/H及兆易PDF未取得正文；00:13:30Z开始的三条原官方URL容器请求均返回DNS/NameResolutionError，最后一条接收记录为00:13:35.372406Z，未取得PDF字节或新hash。没有OCR、页面图像核验、重试、换凭据或新建源workflow。公开检索的索引线索没有升级为本件新增报表数字。
- **复用：** 原生Git create-only研究文件与原Decision Book导航；标准库离线算术。没有新架构/依赖/采集器，不为纯研究补证另造SDK或重复已有OSS审阅。新增导航停用可恢复旧视图，原档案/失败保留。

本件及计算先保存、精确读回，再按实际适用CI、正常合并、独立main与正常publisher分别验收。发布后导航可发现性不等于新ON_DEMAND_ARCHIVE登记或自动完整原件恢复；自然Quick/Brief采用与Human接受仍须真实证据。实际交付以原#509及本批PR回执为准。**Investment Authority=NONE。**

[TASK]: https://github.com/auguspp/decision-kernel/issues/509
[START]: https://github.com/auguspp/decision-kernel/issues/509#issuecomment-6027934572
[PRE]: https://github.com/auguspp/decision-kernel/blob/ac4813bd2242a0bcbfc7db2fcf6682e5c25fc328/docs/readings/d-source-time-and-expectations-2026-10-07/README.md
[S-H]: https://github.com/auguspp/decision-kernel/blob/ac4813bd2242a0bcbfc7db2fcf6682e5c25fc328/docs/readings/d-source-time-and-expectations-2026-10-07/source-ledger.json
[S-A]: https://github.com/auguspp/decision-kernel/blob/aecb004596d811a8d5a68bf17a271e744bddda33/research_runs/normal-question-preparation/688337-20260924/context.json
[CASH]: https://github.com/auguspp/decision-kernel/blob/fbac318df6e65d1eecacadba0b13ce3695f3bcb3/docs/readings/d-688337-cash-conversion-2026-10-06/README.md
[CUSTODY]: https://github.com/auguspp/decision-kernel/blob/fbac318df6e65d1eecacadba0b13ce3695f3bcb3/docs/readings/d-688337-cash-conversion-2026-10-06/source-notes.json
[RIGOL]: https://github.com/auguspp/decision-kernel/blob/b8840419cfc7accddbfb8a79fe0f3bb78b7727d7/docs/readings/d1-rigol-expectation-price-2026-10-06/README.md
[YTO]: https://github.com/auguspp/decision-kernel/blob/9a27c4ca47b088b17361c271c1621f94e53a576b/docs/readings/d1-yto-cost-pricing-2026-10-06/README.md
[GIGA]: https://github.com/auguspp/decision-kernel/blob/7e3ab436233711f0c2d44130ca855c6e2be345a8/docs/readings/d-gigadevice-cxmt-procurement-2026-10-06/README.md
[R-JOINT]: https://github.com/auguspp/decision-kernel/blob/e466d73414c569fb986af358a7ae37dc35fdc7f0/details/research/d-joint-reading.json
