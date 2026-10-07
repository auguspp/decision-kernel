# D1｜9月23日的真实保留状态：五名完整基线与两项价格反例

2026-10-07；归属[#509/6029302696][TASK]。代码基线 `dfb0d2984c44868cf2fc8df08212fa24fbbede56`。这是已有历史的有界研究续接，不是新Full、历史买卖建议或D总验收。原六份JSON字节、来源关系与计算保留在本目录；投资权限NONE。

## 1. 这次从“无法证明当时知道”推进到了哪里

**本次取回的9月23日Watch和影子价格原件，确实由当日GitHub运行保存，早于9月30日结果。** 这比10月补读一个9月文件多一层真实的系统保管时钟：可以恢复所选截点当时的价格条件、原Human引用和已保存历史价格。它没有证明全部公司证据、新闻、市场预期或所有工具都在当时完整可得。[W23、H23]

9月23日原Watch有5名活跃证券、6名inactive；本件全部保留，不按后来的涨跌删选。9月30日选用当日第一个已找到的收盘后Inbox运行，不用后来加入兴森/新城的新配置替换。两个Watch的config_hash相同，registry_hash不同；五名各自的source引用、prerequisite和下一条件ID逐项相同，不能因此宣称整份注册表未变。[W23、W30]

**选窗是本次回看选择，且此前已见过9月30日价格，不是盲选、随机样本或独立前向实验。** 没有回填一份9月23日AI短期机会判断。原物料日期与这份10月解释分开，不能用本件训练知识或后见结果证明无未来信息泄漏。

## 2. 五名完整分母：未触原条件，不等于所有期限无机会

表内为原Watch声明的人民币未复权收盘；比例只算 `9月30日收盘/9月23日收盘−1`，不是含分红/公司行动/交易费用的收益。没有取得这五名完整公司行动检查，不能将比例升级为总回报或可执行策略成绩。

| 原活跃证券 | 9月23日 | 9月30日 | 指定日期原始收盘变化 | 原下一复核条件上沿 | 两个截点 |
|---|---:|---:|---:|---:|---|
| 恒瑞 600276 | 45.58 | 47.20 | +3.554190% | 39.60 | 均未触及 |
| 兴业科技 002674 | 20.25 | 19.82 | −2.123457% | 17.00 | 均未触及 |
| 北大荒 600598 | 12.76 | 12.63 | −1.018809% | 11.30 | 均未触及 |
| 三花 002050 | 35.99 | 35.71 | −0.777994% | 30.00 | 均未触及 |
| 兆易 603986 | 398.72 | 353.90 | −11.240971% | 350.00 | 均未触及 |

“上沿”中只有三花30元对应原条件首笔，其他分别是重审/假设复核，并非统一买价。**未触条件只描述两个已读截点；没有检查五名所有中间日或盘中价格，也不证明期间无人交易。** 原6项inactive的资格/失败原文保留，不把空价格填0。[原两份watch.json]

恒瑞后来上涨这一项必须保留，不能以其余四名收盘更低便宣布“等待策略80%正确”。原Watch根本没有作这五名同一短期涨跌预测，也没有统一持有期、执行、基准或机会集；五条不是五次独立预测。

## 3. 两项可回读反例：原先已反弹，后续仍可能下跌

原9月23日影子路径保存了截至当日的原始收盘。三花9月16日33.73至9月23日35.99为+6.700267%，兆易373.14至398.72为+6.855336%。两项原研究仍受各自Human边界约束；因此“长期首笔不满足”和“过去一段价格反弹”可以同时为真。[H23、S、G]

原9月30日另一次保存路径给出以下后续四行；两份历史重叠的已保存价格逐点一致，各自最后价格也与同run Watch吻合。这里是同一供应商的两种用途核对，不是两个独立市场证据样本。[H30]

| 原路径日期 | 三花 | 兆易 |
|---|---:|---:|
| 9月24日 | 36.08 | 383.77 |
| 9月28日 | 35.44 | 358.51 |
| 9月29日 | 35.65 | 367.57 |
| 9月30日 | 35.71 | 353.90 |

一个值得保留的期限陷阱：**9月23日至30日跨一周，却不是五个后继交易日。** 沪深交易所9月17日公告均安排9月25–27日休市、28日恢复；这与四行原路径相符。本件从官方索引核对该安排，未取得完整原网页字节，不把缺一日自行解释为休市，更不把一周比值改名为5日结果。[CAL-SH、CAL-SZ]

这两个例子反驳的是“近期反弹本身足以证明下一窗口机会”的推断，不是统计检验后宣布动量无效，也不是证明当时应该做空。所选9月16日旧价格在本件可证的系统捕获时点为9月23日，不能倒填成9月16日已经完成了该影子采样。收盘后才记录的观察也不能假定按记录当日收盘可成交。

## 4. 五个不同的经济判断入口，不能统一成一个价格规则

以下恢复9月23日实际run代码 `bc9882efb415912d46da28c21f53753903b23d9d` 所含原Human材料；源blob均与Watch引用相符。原记录中当时的判断不代表本次重新核验公司全景。

**恒瑞：研发/授权价值与每股现金分开。** 原接受的是条件价格分布，不是买入决定。非肿瘤净价与持续用药、授权履约/研发/税费、BMS首付款可留存现金及NewCo避免重复计价仍是原关键问题。45.58高于39.6复核条件，后来47.20不证明这些问题已解决，更不能因上涨而判原等待错误。有限事件机会须有公司层面的新支付/临床/授权兑现、对应事前预期及价格时点，本件没有补造。[H]

**兴业：新业务放量不能遮住旧业务衰退与融资。** 原接受的框架是旧业务经济价值衰退、资本再配置、早期InP转型和治理不确定性；4英寸规模商业化、重复大单与高ROIC尚未建立。20.25与19.82均高于17元，价格更低不能代替良率、ASP、现金、订单与融资证据。短期产业主题可以形成问题，但不能据此取消这些经济变量或恢复已被推翻的旧模型。[X]

**北大荒：补税后的报表恢复不能当持续盈利增长。** 原BA2接受的利润带约9.6–10.6亿元，核心21–23倍解释，以及增长证据未建立仍保留。12.76至12.63没有触及11.0–11.3重审区；这点跌幅不能证明税制现金研究正确或错误。短期机会要有租金、税后盈利、现金分配或定价预期的新依据，不能把一次性比较基数恢复直接当增长催化。原三年/10%是该计算框架，不新造永久门槛。[B]

**三花：核心经营与机器人/液冷期权分开。** 原Human首笔约30元，以核心经济支撑而非必须实现机器人右尾。此前6.70%原始收盘反弹没有建立期权收入、利润或资本回报，之后−0.78%也没有证伪长期核心。若讨论更短机会，应另给可观察的订单、价格/预期修订与终止条件，而非把2027估值压缩到一周。原3–6个月只在Human实际买到后起算，不能从本次回放9月23日启动持有期。[S、SH]

**兆易：全球存储上涨与本公司的成本后经济分开。** 原Human假设是较长利基存储紧张期加更高的周期后盈利底；代工成本、毛利捕获、库存与现金、MCU/定制产品是不可省略的桥。398.72至353.90虽明显下行，9月30日仍未触原350复核点，350也不是买价；没有恢复原320–335以外的新首笔。不能用之后公布的MU业绩或10月补读的采购解释倒填9月23日机会判断，也不能从这次下行宣布原长期假设已死。[G]

对五名共同的处置是：**原条件不触发不等于无战术机会；原始价格上涨或下跌也不等于战术机会已经建立。** 本件建立的是有真实历史保管的基线与反例。尚未形成可验证的独立短期信息集、预期差与机会合同，因此不能宣布原3–5完整PIT机会验收通过。

## 5. 本批收口与真正剩余

本批可收：原五名状态/引用完整恢复、四份历史价格输入保管、原始价格算术、日期与交易期区别、两项反例及五种经济核查入口。它收窄了“没有历史原件”的笼统说法：本窗口这些原件已有，后继不应再重复索取或从今天价格回填。

未收的是：五名在该窗口的完整事件/预期与调整价格资格、独立短期期限判断及真实采用；本件没有排除所有信号，因此不能把缺资料写成已经证明没有机会。后继应优先补具体经济变量或前向实际输出，不重新运行这些影子采样、扩建回测平台或再造状态总览。原10月4日MU→兆易S0/5/20与这里的9月历史窗口不同，不重置原冻结；C自然窗、竞价T+1及#745 STOP保持。

## 6. 保管与复算范围

`source-notes.json`保留四个原Actions ZIP的ID/原run/大小/SHA256、所选六个JSON成员的原字节及Git blob；两个Watch原JSON还在仓库既有Git对象中实际查到，直接复用对象。完整原ZIP没有写入本Git档案，也未保存供应商HTTP原始应答；六JSON是项目当时输出，不声称交易所签名或无法删除的证明。保存字节不改变原SHADOW用途，也不继承其旧数值概率。

本轮实际核外ZIP大小/SHA256/CRC、两Watch payload哈希、五名原引用/条件一致性、十个价格距离和比例，以及两项重叠路径和末端价格。Decimal/Fraction核算一致。没有重跑旧宿主/市场资格预检、完整source replay或全市场事件审计；因此本件不升级生产ObservedMarket身份。

在本目录显式运行以下离线复算；只读JSON，无网络、Git或模型调用，不自动进入档案reader：

```python
from pathlib import Path
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from hashlib import sha256
import json
root = Path('.')
notes = json.loads((root/'source-notes.json').read_bytes())
for item in notes['files']:
    raw = (root/item['file']).read_bytes()
    assert len(raw) == item['bytes'] and sha256(raw).hexdigest() == item['sha256']
reports = [json.loads((root/f'watch-{day}.json').read_bytes()) for day in ('20260923','20260930')]
for report in reports:
    raw = json.dumps(report['watch'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    assert sha256(raw).hexdigest() == report['watch_hash']
a,b = [report['watch'] for report in reports]
assert len(a['active_cases']) == len(b['active_cases']) == 5
assert a['inactive_cases'] == b['inactive_cases']
expected = json.loads((root/'result.json').read_bytes())['rows']
with localcontext() as ctx:
    ctx.prec = 50
    for old,new,saved in zip(a['active_cases'],b['active_cases'],expected,strict=True):
        assert old['ticker'] == new['ticker'] == saved['ticker']
        assert old['source'] == new['source'] and old['prerequisite'] == new['prerequisite']
        x,y = D(old['price']),D(new['price'])
        ratio = y/x-1
        fraction = F(new['price'])/F(old['price'])-1
        assert abs(ratio-D(fraction.numerator)/D(fraction.denominator)) < D('1e-48')
        assert format(ratio*100,'.6f') == saved['raw_close_change_pct']
        print(old['ticker'],saved['raw_close_change_pct'])
print('FIVE_DATED_RAW_CLOSE_PAIRS_MATCH_NOT_STRATEGY_RETURNS')
```

代码块仅复算所列字段，不冒充全部原机校验。原件修改、漏掉成员、同名证券替换的本地负例须拒绝；正式PR/CI/main、正常发布及精确导航读回另留回执，不能由本文预签。旧Human接受/Action、任务/通知/费用/隐私不变；Investment Authority=NONE。

[TASK]: https://github.com/auguspp/decision-kernel/issues/509#issuecomment-6029302696
[W23]: https://github.com/auguspp/decision-kernel/actions/runs/35836556981/artifacts/10739870546
[H23]: https://github.com/auguspp/decision-kernel/actions/runs/35836556981/artifacts/10739622325
[W30]: https://github.com/auguspp/decision-kernel/actions/runs/36689087147/artifacts/11084604574
[H30]: https://github.com/auguspp/decision-kernel/actions/runs/36689087147/artifacts/11084464642
[H]: https://github.com/auguspp/decision-kernel/blob/bc9882efb415912d46da28c21f53753903b23d9d/docs/decisions/600276-hengrui-human-first-entry-2026-09-12.md
[X]: https://github.com/auguspp/decision-kernel/blob/bc9882efb415912d46da28c21f53753903b23d9d/docs/decisions/002674-xingye-human-research-first-entry-acceptance-2026-09-14.md
[B]: https://github.com/auguspp/decision-kernel/blob/bc9882efb415912d46da28c21f53753903b23d9d/docs/decisions/600598-beidahuang-human-odds-acceptance-2026-09-16.md
[S]: https://github.com/auguspp/decision-kernel/blob/bc9882efb415912d46da28c21f53753903b23d9d/docs/decisions/002050-sanhua-human-decision-2026-09-03.md
[SH]: https://github.com/auguspp/decision-kernel/blob/bc9882efb415912d46da28c21f53753903b23d9d/docs/decisions/002050-sanhua-human-horizon-supplement-2026-09-03.md
[G]: https://github.com/auguspp/decision-kernel/blob/bc9882efb415912d46da28c21f53753903b23d9d/docs/decisions/603986-gigadevice-human-decision-2026-09-03.md
[CAL-SH]: https://www.sse.com.cn/disclosure/announcement/general/c/c_20260915_10832273.shtml
[CAL-SZ]: https://investor.szse.cn/disclosure/notice/general/t20260917_622911.html
