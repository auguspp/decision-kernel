# D1｜真实日线窗口：三例路径核对完成，深市日历缺口保留

2026-10-07；归属 [D #509](https://github.com/auguspp/decision-kernel/issues/509)，续接 [#786具名预期](https://github.com/auguspp/decision-kernel/issues/509#issuecomment-6036417653)及[#787有限窗口](https://github.com/auguspp/decision-kernel/pull/787)。这是既有五名历史案例的来源与价格边界核验，不是新Full、策略回测、Human接受或投资指令。

## 一次实际运行，不抹掉失败

精确代码M=`9ceb3f24a25302314a762bdc47a50f558029e555`；工作流`research-price-window.yml`，run `37623034998/1`，job `112797786276`。用户已授权D接续，按原五名完整分母显式调用一次：恒瑞600276.SH、兴业002674.SZ、北大荒600598.SH、三花002050.SZ、兆易603986.SH，20260916–20260930。未重跑日常价格、旧试点或#745分钟路线。

来源为既有 **THIRD_PARTY_TUSHARE_RELAY**，不是官方Tushare直连。12个逻辑请求、各1次真实尝试，无重试；实际收到125行：SSE日历15行、SZSE日历10行、五证券日价与因子各10行。收据开始`2026-10-07T12:43:27.823581+00:00`，结束`2026-10-07T12:43:58.651200+00:00`；每次请求、接收及响应hash均在原receipt中。后取得历史资料不变成9月当时已采，更不改原9月17日06:18:10知识界线。

**原运行结论为failure，报告为PARTIAL_OR_UNAVAILABLE，二者保留。** capture和verify退出码2来自真实部分覆盖；原件上传成功。SSE日历覆盖完整15自然日，其中10个开市日；SZSE只返回10个开市日期，缺9月19、20、25、26、27五行，触发`CALENDAR_COVERAGE`。不将SSE日历偷换给SZSE、不把未返回日期填0，也不重试同请求直到变绿。12个HTTP/业务成功不等于12个来源都合格。

| 证券 | 日价/因子 | 日历及窗口资格 | 本次用途 |
|---|---|---|---|
| 恒瑞 | 10/10行 | COMPLETE_PROVIDER_DAILY_WINDOW | 使用固定界线后9个实际开市日的描述性路径 |
| 兴业 | 10/10行 | WINDOW_GAPS：SZSE闭市日期缺失 | 保留原件，完整窗口判断不签收 |
| 北大荒 | 10/10行 | COMPLETE_PROVIDER_DAILY_WINDOW | 同上，核税制案例原价格条件 |
| 三花 | 10/10行 | WINDOW_GAPS：SZSE闭市日期缺失 | 保留原件及分红相关因子变化，不计算完整窗口回报 |
| 兆易 | 10/10行 | COMPLETE_PROVIDER_DAILY_WINDOW | 同上，核原350元复核边界及不同端点含义 |

提供者返回的`history_complete`等文字只是来源声明；独立的日期、身份、OHLC、因子和覆盖检查另行执行。合格也不排除历史修订、未列公司行动、交易摩擦或来源系统性错误。

## 三条完整提供者路径的实际增量

9月16日只作前收背景，不能作9月17日清晨取得原观察之后的可执行入场。以下从9月17日开盘价到9月30日收盘价作同一固定窗口描述；开盘价不是本项目成交价。期间三只股票的所取因子各自不变，原始价格比与提供者因子价格比相同；逐相邻开市日的前收与前日收盘差均为0。没有认证完整总回报或计算手续费后的投资收益。

| 案例 | 9/17开盘→9/30收盘（元） | 价格比变化 | 窗口最低/最高价（元） | 原复核边界 | 在所取完整窗口内 |
|---|---:|---:|---:|---:|---|
| 恒瑞 | 43.33→47.20 | +8.9315% | 43.10 / 47.39 | 39.60 | 日低价未触及 |
| 北大荒 | 12.42→12.63 | +1.6908% | 11.99 / 13.42 | 11.30 | 日低价未触及 |
| 兆易 | 370.06→353.90 | −4.3669% | 351.28 / 413.43 | 350.00 | 日低价未触及 |

这些边界继承[五例原研究/Human审阅](https://github.com/auguspp/decision-kernel/blob/80fc78d49888e00ea7174ead387d4d2acd53f0b2/docs/readings/d1-five-case-economic-review-2026-10-07/README.md)。没有新建Watch事件、回写旧Watch状态或据价格宣称Belief始终不变。窗口最低价在期初开盘以下的幅度分别约0.53%、3.46%、5.07%；它们是已经观察到的路径位置，不是事前风险预算或最优买点。

**恒瑞：** 已有具名盈利下修及临床/回购资料不等于可交易的短期负向意外。现在实际价格窗口上涨，但这也不证明盈利预测后来兑现、现金问题解决或原研究提前预测了反弹。既有产品收入、许可确认与净现金的区分继续，原39.6复核及37–38条件讨论不改。结论是指定价格条件未出现；短期机会的事前区分力仍未建立，不是“无机会”或一次预测成功。

**北大荒：** 补税、近似预亏和已知中报的[前驱核对](https://github.com/auguspp/decision-kernel/blob/a4a1263d7fbb6c1c5eaeb03744c30fad211af01d/docs/readings/d1-beidahuang-disclosure-expectation-2026-10-07/README.md)保持。窗口曾到13.42，后来最低11.99，最终仅比起点开盘高1.69%；挑高点会掩盖路径反转。一次性补税不重复仍不等于持续税后能力增长，价格未到11.3也不等于永远不值得研究。没有因后来的涨跌改变BA2或Human条件。

**兆易：** 9月22日最高413.43而9月30日收盘353.90，若只截取上升段会得出不同印象；整个固定窗口价格比为负。最低351.28仍高于350，原假设复核/320–335首笔条件并未由该路径满足。价格变化不验证成本后毛利、营运资本或现金传导。尤其继续遵守[结果稿晚于A股收盘的时间边界](https://github.com/auguspp/decision-kernel/blob/b2eb323a9947e303b6509731c0fb2138fdcd3979/docs/readings/d1-information-boundaries-2026-10-06/README.md)：选定美光结果稿为10月1日04:01北京时间，不能用它解释9月30日盘内对这份稿件的反应；不能排除此前已公开指引或其他信息。

**深市两例不是丢弃样本。** 兴业、三花的返回行保留，但本次不使用另一交易所日历来把它们认证为完整路径。三花9月29/30因子15.533→15.5855，35.65×15.533/15.5855≈35.529912元，与所报前收35.53的差约0.000088元；这只是提供者数据之间的有限数值相容，不取代此前0.12元持有人毛红利与0.1195545除息参考调整的区别，也不修复日历缺口。

本件已完成“三条完整提供者路径＋两项明确缺口＋原条件核对”的有界工作，不再把这三例写成只有9月16/23/30几个端点。它仍是固定知识截点后的观察窗，不是每份公告首发附近的事件研究；分析者已知后继价格，不能冒充盲测、完整PIT策略或三个成立机会。未解决的事前经济区分证据、两例完整日历资格和原D伴随功能继续分别保留，不能把局部来源缺口扩大为整个D停工理由。

## 精确保管与不联网复核

本目录保存12份原始UTF-8响应与原`receipt.json`，内容字节不变，仅将原`raw/NN-1.json`一一放成平面的`NN-1.json`以便现有Git档案读取。receipt保留原路径，读取时显式映射，不修改原件。这里不是原ZIP字节的永久副本，也没有把原report/summary宣称已逐文件迁入Git；二者可从本目录输入确定性重建并核对下方原输出hash。原完整Actions包仍可用至其声明到期日2027-01-05，之后原响应和收据仍由Git保留。

- 原run：[37623034998](https://github.com/auguspp/decision-kernel/actions/runs/37623034998)，artifact11483171256，9843bytes，ZIP SHA256 `683488b0852894cea53d94248316b43ce82f788ded86bf38f50b998bb43f5308`。
- 原receipt：10348bytes，Git blob `3a2d59e8c6d312d76221b14134ad28a187c61dbc`，SHA256 `5681a46d9bb78d649640e593383231d637d6f1059741576895ce2c23561ae4ae`。
- 原report：9706bytes，SHA256 `3a1491df28043df32f31b9af59251af7dfca8f95f4b5f0f60e408cab73faccb0`；原summary：762bytes，SHA256 `f4877d981ba4ca0d7a82e4952e2666bf458497fb29f3e0b0484b88f49ba1e528`。

使用上述精确M的已审阅代码；以下只读本地数据，不运行来源请求，也不将缺口改为通过：

```python
from pathlib import Path
from hashlib import sha256
from decimal import Decimal as D
import json
from decision_kernel.runtime import research_price_window as w
here = Path('docs/readings/d1-window-evidence-2026-10-07')
r = json.loads((here/'receipt.json').read_bytes(), object_pairs_hook=w.unique)
assert sha256((here/'receipt.json').read_bytes()).hexdigest() == '5681a46d9bb78d649640e593383231d637d6f1059741576895ce2c23561ae4ae'
bodies = {name: (here/Path(name).name).read_bytes() for name in r['files']}
for name, raw in bodies.items():
    assert r['files'][name] == {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
p = w.build(r, bodies)
assert p['status'] == 'PARTIAL_OR_UNAVAILABLE'
assert sha256(w.dumps(p)).hexdigest() == '3a1491df28043df32f31b9af59251af7dfca8f95f4b5f0f60e408cab73faccb0'
assert sha256(w.render(p).encode()).hexdigest() == 'f4877d981ba4ca0d7a82e4952e2666bf458497fb29f3e0b0484b88f49ba1e528'
for s in p['securities']:
    if s['status'] != 'COMPLETE_PROVIDER_DAILY_WINDOW':
        print(s['ts_code'], s['status']); continue
    dates = [d for d in s['sessions'] if d >= '20260917']
    assert len(dates) == 9 and dates[-1] == '20260930'
    prices, factors = s['prices'], s['factors']
    o = D(prices['20260917']['open']); c = D(prices['20260930']['close'])
    assert len({x['adj_factor'] for x in factors.values()}) == 1
    for a, b in zip(s['sessions'], s['sessions'][1:]):
        assert D(prices[a]['close']) == D(prices[b]['pre_close'])
    print(s['ts_code'], c/o-1, min(D(prices[d]['low']) for d in dates), max(D(prices[d]['high']) for d in dates))
```

实际完整原ZIP已下载并核大小/hash/CRC、安全路径，原`verify`离线重建通过并仍返回PARTIAL；上述恢复代码亦核原输出hash。后续Git逐文件身份、PR/main、发布和入口回执另记#509/#787，不由本文件自证。此资料/工程验收目录通过原任务与能力文档导航，不是新增COMMITTED Research、ON_DEMAND用途登记、当前价格包或自然Quick消费。

本次自然使用验收已另写[#509/6037541224](https://github.com/auguspp/decision-kernel/issues/509#issuecomment-6037541224)：10月7日Quick和晚报确实采用普源/圆通/北大荒三项前向声明；六格不是六次预测。美光金额纠错场景未出现，晨报正文未恢复。该验收不因本次日线档案而扩大。原MU10/4及后三例10/7冻结、S0/5/20/T+1、11/30分析者复核、C10/8/9/12/13/14自然窗，Sites暂停、禁Codex、新城暂缓、旧任务/通知/费用/隐私权限均不变。D仍IN_PROGRESS；Investment Authority=NONE。
