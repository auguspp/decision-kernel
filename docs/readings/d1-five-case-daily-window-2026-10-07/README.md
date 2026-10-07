# D1｜五案例逐日日线与有界机会复盘

2026-10-07；归属[#509本轮施工][TASK]。代码基线M=`9ceb3f24a25302314a762bdc47a50f558029e555`；本轮读取R=`ffe09874ffdf5ec345cd43caf595d57497e5d226`。性质：**指定历史窗口的研究性复盘与完整源文件留存，不是当时运行的策略、可执行收益或Human接受。Investment Authority=NONE。**

## 1. 本轮完成与终局

原[五例经济审查][PRE]只有9月16/23/30三个收盘截点；[同期公司行动][ACTION]及[具名预期][FORECAST]已完成的核对继续继承。本件用#787的唯一真实取证，把指定窗口推进为逐日OHLC/因子、盘前知识截点之后的开盘参考、全窗条件是否触及和已知公司行动影响的具体比较。没有再查同一预告、复制旧静态估值表或选择新的赢家。

**指定9月17–30日复盘在以下来源与研究边界内完成，下一轮不重做该窗口。** 五例均不足以据本组材料确认当时可执行的战术机会；这是有根据的“未建立”，不是证明全市场无机会，更不是五个成功预测。原价位条件回答长期/条件投资问题，不能由其未触及推出全部短期限无机会。事后见到上涨也不能补造事前识别。完整D总验收、方法效果和未发生的前向结果不由本件代签。

## 2. 原始来源与正确保留的失败

唯一源run=`37623034998`，attempt=1，job=`112797786276`，code=M；[原运行][RUN]在2026-10-07T12:43:13Z发起，receipt实际取得窗口为12:43:27.823581Z–12:43:58.651200Z。12个计划请求均首试SUCCESS；来源是既有第三方Tushare Relay，不冒称交易所原生行情或当时已采。无新主机、key、付费服务、重试dispatch或日常任务重跑。

[原ZIP][ZIP]为artifact `11483171256`，9843bytes，SHA256 `683488b0852894cea53d94248316b43ce82f788ded86bf38f50b998bb43f5308`。15个文件全数取回，外ZIP大小/hash/CRC、安全路径和唯一文件名已核。下面保存的是其**全部原文件内容**，不是原ZIP容器字节的Git副本；原ZIP仍有Actions保管期限。所有raw及receipt/report/summary逐字节保持，含失败状态，不截断、不修订旧资格。

两份日历表现不同：SSE覆盖9/16–30全部15自然日；SZSE只给10个开市日，缺9/19、20、25、26、27的闭市行。五只股票各有10行日价和10行因子，不能将两只SZ的日历失败说成价格没取到。原`qualified`正确抛`CALENDAR_COVERAGE`；原报告仍为`PARTIAL_OR_UNAVAILABLE`，3个SH为`COMPLETE_PROVIDER_DAILY_WINDOW`，兴业/三花为`WINDOW_GAPS`。capture与verify均exit2，附件保存成功，不以成功HTTP覆盖运行失败。

研究日历另与2025-12-22的[上交所年度休市通知][SSE]及[深交所年度休市通知][SZSE]作有限对照：中秋9/25–27休市，9/28恢复。SSE正文成功打开；SZSE仅取得官方域名搜索索引文字，直接正文请求超时，未取得原HTML字节。结合原SZSE明确给出的开市行，下文对两只SZ作**带外部日历限制的研究性比较**，不把SSE日历冒充SZSE，不填原漏行或将原报告改成PASS。原提供者是否历史修订、全部公司行动及实际可成交资格仍未认证。

## 3. 时点、分母和计数先固定

原五名保管与经济审查的历史知识界线是`2026-09-16T22:18:10Z`（9月17日06:18:10，UTC+8）。9/16收盘早于这个界线，只作前收背景；下文从**9/17开盘参考**开始，而不是假定能按9/16收盘买入。晚取的日线只证明此次提供者给出的历史值，不证明当时系统已持有这些值。分析者已知道后继涨跌，全部规则和本次复盘属于事后研究，不称盲测、样本外验证或策略上线。

研究窗口开市日为9/17、18、21、22、23、24、28、29、30，共9日。计入9/17的第5日是9/23；若说“9/17收盘之后的5个后继交易日”，则是9/24，二者不混用。这不是10月四案例前向S0/5/20的定义变更。保留五名完整分母，三份原生完整与两份日历限定并列，不删不利样本。

## 4. 新的日线路径比较

人民币元；变化为所选开盘参考到指定收盘的未复权价格比例，非实际持仓收益、总回报或模型预期。阈值沿原五份Human记录，不重新设定。

| 案例 | 9/17开盘参考 | 9/23收盘 | 含起始日5日变化 | 9/30收盘 | 全窗变化 | 全窗最低价 / 原相关条件 | 原生来源资格 |
|---|---:|---:|---:|---:|---:|---|---|
| 恒瑞600276 | 43.33 | 45.58 | +5.192707% | 47.20 | +8.931456% | 43.10 / 39.60复核；未触及 | SH完整 |
| 兴业002674 | 19.55 | 20.25 | +3.580563% | 19.82 | +1.381074% | 19.00 / 17.00复核上沿；未触及 | SZ日历限定 |
| 北大荒600598 | 12.42 | 12.76 | +2.737520% | 12.63 | +1.690821% | 11.99 / 11.30复核上沿；未触及 | SH完整 |
| 三花002050 | 33.50 | 35.99 | +7.432836% | 35.71 | +6.597015% | 33.45 / 约30.00条件首笔；未触及 | SZ日历限定 |
| 兆易603986 | 370.06 | 398.72 | +7.744690% | 353.90 | -4.366859% | 351.28 / 350.00假设复核；未触及 | SH完整 |

此前三个截点的“未触界”现在推进为**所取得9个交易日日低的有界检查**。不是全历史/全部盘口认证，不证明Human没有另外成交。这里的开盘价也不是承诺成交价，没有订单、成交量/流动性、滑点、税费或停复牌交易资格检查。

**路径反例，不挑最高价作收益。** 兆易9/22最高413.43，较9/17开盘参考高11.719721%，但到9/30收盘反为-4.366859%；九个日收盘的峰值至后继收盘最大回撤约-11.987068%。最高价不是既定退出，也不代表能同时选对低点和高点。恒瑞同窗收盘向上，不能将一个共同“全部上涨”的故事套在五家公司上。

**跟随上涨的另一时间检验。** 五名到9/23都高于9/17开盘参考。若仅用这一事实在9/23收盘后形成追涨想法，应至少从下一开盘参考9/24而非已知的9/23收盘观察。9/24开盘至9/30收盘未复权变化分别为恒瑞+4.010577%、兴业-1.393035%、北大荒-1.096319%、三花-0.390516%、兆易-9.949109%。这只是固定全分母的后见反例；没有随机/样本外比较、基准、择时模型或成本，不计算策略胜率、alpha或否定所有动量方法。

## 5. 三花的公司行动不能藏在回报小数里

三花9/29收盘35.65，9/30的`pre_close`为35.53；同日因子由15.533变为15.5855，是本组唯一前收参考断点和因子变化。其他四股所取窗口未发现该类断点，不由此证明不存在全部公司行动。

继承[ACTION]已核的每股合格持有人毛红利0.12元与除息参考调整0.1195545元的区别，原持有人登记/实际支付/税费资格不扩大。9/17开盘至9/30收盘：未复权+6.597015%；按此次提供者两端因子换算的价格背景为+6.957302%；假定全程持有、取得0.12元毛红利且忽略税费，端点现金对照为+6.955224%。后两者略有差别，不能把因子显示精度或参考价调整机械当成真实现金收益，更不能在因子调整之后再加同一分红而重复计数。

9/24开盘的追涨端点若另按同一毛红利条件加入现金，三花由原价格-0.390516%变为约-0.055788%，仍非实际投资回报。该处理是新逐日窗口中的断点核对，不改#785原9/23起点的历史计算。

## 6. 五个经济判断的终局与重开理由

| 案例 | 将新路径与已完成研究配对后的本轮裁定 | 什么新事实才值得重开，而非重查本窗 |
|---|---|---|
| 恒瑞 | 价格上涨存在，但原复核条件未触及；[FORECAST]已识别旧下修重报，不能用转载日期制造中报新冲击。上涨未证明授权全成本净现金或产品持续性改善，有限战术机会未建立 | 可区分的产品净价/销量、许可净收款及履约支出，或有清楚日期和口径的真实预期变化；不是同一旧目标价被重发 |
| 兴业 | 已返回的日线显示先涨后回吐；既有交易付款/交接和合同义务不回退未知，但也不是规模化订单、良率、ROIC兑现。SZ日历限定不隐藏，原两种业务和治理风险保持 | 真实重复订单、良率/单位经济、增量现金投入及融资/调查资料；不因InP标签或后来涨幅重写旧模型 |
| 北大荒 | 有价格反弹但未到原复核区，税务和7月亏损预告在中报前已存在。一次性补税不重复不能被这个反弹认证为持续税后盈利增长 | 新合同/税负或可归属现金使正常化盈利/风险折价有可区分变化；旧亏损报道或相同利润倍数网格不是新证据 |
| 三花 | 价格涨幅、分红、国信盈利调整与华泰倍数变化分别解释；核心热管理与未证实可选业务不能混作必要利润。原约30元附条件决定和实际执行后3–6个月评价不动 | 可验证的核心收入/利润率、现金资本回报或新业务重要经济量；不是把外部目标价下降当盈利同比下降 |
| 兆易 | 窗内上冲后全窗转负，350只是复核不是买点；行业紧缺、跨机构预测差及短暂上涨均不足以证明成本后利润/现金。原高于跨周期盈利底的定价风险保持，不能拿峰值包装已识别机会 | 与公司相关产品的实现价/销量/成本、库存现金及有日期可比预期；不借MU后到披露倒填9/17信息或把跨机构61/140.69当单模型上修 |

原长期条件、Human接受层级与下注决定都未改变。以上是有限研究的结论与证据触发，不是新增Watch、自动退出、概率或买卖授权。信息集未穷尽不等于公司永久排除；后继只在上述新材料或具体反证出现时有界重开，不为了收口继续查同一价格窗口。

## 7. 16文件原件映射与复验

本目录恰有16个普通文本文件：本README，原`receipt.json`、`report.json`、`summary.md`，以及12份raw。同名三文件保持原名；`raw-NN-1.json`与原ZIP的`raw/NN-1.json`一一对应，NN=01…12。只是可逆平面文件名适配原档案合同，原receipt内部路径与每一份内容未改变。不是删文件、拆分超限档案或改变验证器。

| 原同名文件 | bytes | SHA256 |
|---|---:|---|
| receipt.json | 10348 | 5681a46d9bb78d649640e593383231d637d6f1059741576895ce2c23561ae4ae |
| report.json | 9706 | 3a1491df28043df32f31b9af59251af7dfca8f95f4b5f0f60e408cab73faccb0 |
| summary.md | 762 | f4877d981ba4ca0d7a82e4952e2666bf458497fb29f3e0b0484b88f49ba1e528 |

每份raw的bytes/SHA256、请求、原文件名和实际时钟全部在未改的receipt中；不由哈希认证经济真理或提供者未修订历史。先按登记的精确commit取齐整个目录，再由人工审阅后在临时目录恢复`raw/`。归档读取器本身不得执行README代码；以下是明确的离线复验范例，不联网也不重新捕获来源：

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
from decimal import Decimal as D, getcontext
from fractions import Fraction as F
import json
from decision_kernel.runtime.research_price_window import verify

# Use reviewed code at 9ceb3f24a25302314a762bdc47a50f558029e555.
root = Path('.')  # recovered flat archive, not a live mutable branch
getcontext().prec = 45
receipt = json.loads((root/'receipt.json').read_bytes())
expected = {
 'GITHUB_REPOSITORY':'auguspp/decision-kernel',
 'GITHUB_REF':'refs/heads/main', 'GITHUB_EVENT_NAME':'workflow_dispatch',
 'GITHUB_RUN_ATTEMPT':'1', 'GITHUB_JOB':'capture',
 'GITHUB_WORKFLOW_REF':'auguspp/decision-kernel/.github/workflows/research-price-window.yml@refs/heads/main',
 'GITHUB_SHA':'9ceb3f24a25302314a762bdc47a50f558029e555',
 'GITHUB_RUN_ID':'37623034998'}
assert receipt['workflow'] == expected
assert len(list(root.iterdir())) == 16
with TemporaryDirectory() as tmp:
    out = Path(tmp); (out/'raw').mkdir()
    for name in ('receipt.json','report.json','summary.md'):
        (out/name).write_bytes((root/name).read_bytes())
    for name, meta in receipt['files'].items():
        data = (root/name.replace('raw/','raw-')).read_bytes()
        assert len(data) == meta['bytes']
        assert sha256(data).hexdigest() == meta['sha256']
        (out/name).write_bytes(data)
    report = verify(out, expected_workflow=expected)
assert report['status'] == 'PARTIAL_OR_UNAVAILABLE'
assert sum(s['calendar_available'] for s in report['securities']) == 3
thresholds = ['39.6','17','11.3','30','350']
for s, threshold in zip(report['securities'], thresholds, strict=True):
    p = s['prices']; days = sorted(d for d in p if d >= '20260917')
    assert len(days) == 9 and days[4] == '20260923' and days[5] == '20260924'
    assert set(p) == set(s['factors'])
    first, last = D(p[days[0]]['open']), D(p[days[-1]]['close'])
    pct = (last/first-1)*100
    exact = (F(last)/F(first)-1)*100
    assert abs(pct-D(exact.numerator)/D(exact.denominator)) < D('1e-40')
    assert min(D(p[d]['low']) for d in days) > D(threshold)
    print(s['ts_code'], s['status'], pct.quantize(D('0.000001')))
```

实际本地在两个精确原模块的隔离导入环境调用原verify，原report及summary字节重建一致且返回PARTIAL；直接对SZSE原回复确认CALENDAR_COVERAGE。另以Decimal/Fraction独立核本件端点、全分母、最低/最高、因子/前收断点和日期计数。它不是完整安装/远端CLI、正式CI、独立研究者审阅或自然任务采用；精确代码的工程证明继承#787双full8327，本件新增档案的CI/main/发布与固定读取由后继PR实际回执分别成立。

## 8. 与D总单及自然使用的准确关系

[#509/6037541224][USE]已经验证10月7日三份前向声明进入Quick和晚报，连同10月5/6日为三日实际采用，不再说尚未首次使用。本件不是新自然Quick，也不补写原#575被拒正文；Library内容、原任务和通知保持。Oct7两份正文未重述MU四项现金，不能将未出现该场景签成#783纠错已被正确采用；晨报原文仍未恢复，不推定没有运行。

原MU10/4和后三案例10/7前向冻结、原11/30分析者复核、S0/5/20、竞价T+1、C的10/8/9/12/13/14固定自然窗不重置或补签。九个9月历史日不能填成10月前向成绩；公司指引误差不是AI预测误差。D整体仍IN_PROGRESS，公开叙事、盘中/盘前及时性及成熟效果各自原责任保留。此有限研究不要求再建平台、重复源请求或放宽旧验证；Sites暂停、禁Codex、#745 STOP、新城暂缓、费用/隐私/权限边界均不变。

[TASK]: https://github.com/auguspp/decision-kernel/issues/509#issuecomment-6038960827
[RUN]: https://github.com/auguspp/decision-kernel/actions/runs/37623034998
[ZIP]: https://github.com/auguspp/decision-kernel/actions/runs/37623034998/artifacts/11483171256
[PRE]: https://github.com/auguspp/decision-kernel/blob/80fc78d49888e00ea7174ead387d4d2acd53f0b2/docs/readings/d1-five-case-economic-review-2026-10-07/README.md
[ACTION]: https://github.com/auguspp/decision-kernel/blob/cc6d7830ba9b6e7c535b7554580a89517413446b/docs/readings/d1-three-case-pit-sources-2026-10-07/README.md
[FORECAST]: https://github.com/auguspp/decision-kernel/blob/64c74ce4e71a535401941b17932a3616f2f75ba6/docs/readings/d1-dated-expectation-controls-2026-10-07/README.md
[SSE]: https://www.sse.com.cn/disclosure/dealinstruc/closed/c/c_20251222_10802510.shtml
[SZSE]: https://investor.szse.cn/disclosure/notice/general/t20251222_618087.html
[USE]: https://github.com/auguspp/decision-kernel/issues/509#issuecomment-6037541224
