# D：原竞价条件的有界来源与正常读取

本批接续 #509 / #317；施工范围与复用见 #509/5976340445。它不重做
#735 成员表或 #736 目录，不改长期 Research/Human 决定，不等 C 自然窗。

## 实际入口与范围

在现有 `stock-reading-after-sector.yml` 手动选择 `mode=auction-inputs`；
`auction-session` 可填准确 YYYY-MM-DD，留空取实际上海日期。没有新增 cron、
常驻采样、盘中轮询、通知、自动买卖或第三方数据库。原日常 `market-inputs`
和收盘流程不变，手动竞价模式不运行 reconciliation 或 Sector 后继。

沿同一现有 Tushare Relay 依次请求：

1. `trade_cal`：查询目标日前31日至目标日；只要求准确前开市日至目标日连续日历，
   不因更早缺行挡住本次用途，截断标记仍保留。目标休市不要求不存在的竞价。
2. `limit_list_d`：前交易日 U/D/Z 来源池；只取原条件实际所需的身份、名称、
   换手及独立连板背景。单次最多2500，达到上限或显式更多页标为截断。
3. `stk_auction`：目标日STK竞价成交价与同一行昨收，最多8000。只在前项确有
   静态候选时请求；使用已登记代码身份，不固定个股名单。

最多3个逻辑请求；原 Relay 仅对 TEMPORARY_QUEUE 按原30秒等待重试一次，
总运行有界。明确401/403、429、缺凭据或凭据反射停止后续请求，不改账号、
换入口绕过、不自动升级。读取的官方接口说明不等于当前 Relay 账号已获权益；
真实可得性以本批后继原运行/原响应为准，不因未验就称来源不可用。

原条件在命名 profile 内冻结，不是所有价格用途的数据门槛：
昨日 U 池 -> 沪深主板代码形态/昨日名称非ST -> **昨日换手10–30%（含端点）** ->
**本次竞价价/同一行pre_close - 1 为3–9%（含端点）**。
不要求当日换手、成交量、OHLC、60日历史、因子、另一个供应商或 Sector 成功。
官方竞价 `pre_close` 是本用途的比较基准，不拿原未复权昨日close硬替代或强制相等。

完整返回的昨日 U 身份保留在分母；重复冲突、日期错误、名称/换手缺失、排除的
板块与区间都给逐项理由。不能确定身份的U原行也保留一个未识别行及原行位置，
不把它扔掉提高通过率。相同证券重复不增加人数；不同数值不任选其一。
`columns` + `rows` 保存完整列式结果，原始返回另行保留，不靠截断名单省容量。
首页最多展示按证券代码的前20个匹配项，并显示省略数；这不是强弱排名，完整结果
始终在 `details/stock/auction-probe.json`。未匹配不等于公司不好，没有匹配也不是零机会。

## 时点、名称与温度的准确含义

当前官方 `stk_auction` 文档写明当日数据约09:26–09:29可取得（2026-10-04所读版本）。
本程序不把普通行情latest/close、`stk_auction_o`盘后结果或后来历史返回冒充09:25。
今日早于09:26或日历休市，只写对应状态，不发股票请求。历史/09:30之后取得的结果
可用于明确的历史字段比较，但标记 `HISTORICAL_OR_LATE_NOT_PREOPEN_DISCOVERY`。
`RECEIVED_BEFORE_CONTINUOUS_OPEN`只描述此响应的实际取得时段，不证明稳定及时性、
价格持续领先、已经在该时刻交付给Human或具有收益。发布时钟另行保留。

ST处理仅有**昨日来源名称**与来源自身“不含ST统计”的范围，不认证次日改名、
风险警示、停复牌或完整可交易资格。缺相应资料不杜撰；本输出无交易权限。

涨停/跌停/炸板数与最高连板来自**昨日返回池**，不是“今日情绪温度”。缺连板字段
只限制连板上下文，不取消合格的竞价比值。原始U/D/Z类型、冲突、截断、未识别行与
名称时点都可恢复，来源池不冒充独立交易所穷尽统计。今日温度、09:40持续/开板、
收盘/T+1结果与20–30自然样本尚需各自真实输入及评价，不由本切片预签。

## 来源保管与正常发布

原始各次响应按现有格式保管，记录请求/取得时间、HTTP/原重试分类、文件字节哈希；
不将任意源错误文案或凭据写入摘要。新目录create-only；原文件、失败与旧试点不改。
`--verify`不发源请求，重算查询序列、日历、分类、全部输出和摘要，拒绝改值、
异时/异源/跨证券、无HTTP却声称200、错误重试、停止后继续请求和多余文件。

正常 publisher 复用已配置的 `stock-reading-after-sector` workflow_run，但仅新增
本手动用途的完成触发。源读取在 publisher 中不执行；只恢复原生main/attempt1
的 `d-auction-inputs-<run>-1`，用当前代码从原件重算，保留失败运行状态。
描述符与有界摘要进入原独立个股详情及README，完整结果按原读取R保存。
最新输入失败不回搜“好看的”较早竞价结果，历史原件仍在Git/Actions各自位置；
错误只影响竞价派生项，不删除或取消原日常价格/研究成果。

## Reuse 与验证边界

Reuse Decision: REUSE + THIN_ADAPTER。复用现有 Relay 的请求、凭据和停止规则，
`stock_market_inputs` 的严格JSON/Decimal/安全路径，Collector 的原生Actions
档案、校验、字节保管与正常发布。没有复制第三方策略代码或引入依赖。

施工前实际核 FTShare-Lab/FTShare-skill
`d31ee34c86d68569a486feedec5dd8d5cc29db31` 的 auction-results handler/子Skill：
竞价接口确实存在；子Skill未带完整响应字段说明，未猜schema，也未判其不可用。
其 limit-up-pool 历史为曾涨停，不能直接改叫昨收封板池。Tushare 官方369/298
给出了本次使用的具体字段与时点；`waditu/tushare` 的 DataApi.query 只负责接口
请求/fields-items展开，当前系统已有Relay无需再装SDK。外部候选筛选器的Top3、
胜率、买卖推荐与事后改参不移植。本仓库只独立实现原#317公开条件，不取私有源码。

来源：
- https://tushare.pro/wctapi/documents/369.md
- https://tushare.pro/wctapi/documents/298.md
- https://github.com/waditu/tushare/blob/master/tushare/pro/client.py
- https://github.com/FTShare-Lab/FTShare-skill/tree/d31ee34c86d68569a486feedec5dd8d5cc29db31/ftshare-market-data/sub-skills/auction-results

本批测试用合成来源，不是实际行情。正式PR全量CI、独立main、正常发布、新R读回、
第一次真实数据源运行与自然盘中/竞价效果须看 #509/#297 后继回执，本文不预签。
可整体撤下本manual模式/专属两模块/测试和派生接点，原价格通道、Research、来源失败
及历史读取保持；不升级成第二个状态/任务框架。Investment Authority=NONE。

## 真实来源后的连板数适配（2026-10-04）

#737首次真实run `37181646810/1`的 `limit_times` 返回JSON数值 `2.0`、`1.0`。
原v1只接受Python int，错误地把57名U池成员的连板数全部标缺失。三源已成功、
57名分母/12名竞价可比/0匹配均不受此问题影响；这是本系统适配错误，不是数据源不足。

v2复用原精确数值解析，接受正且恰为整数的JSON数值、字符串或int，不对2.5取整，
不接受bool/非有限/缺失。不同写法的相同计数不制造冲突；真实不同计数仍单列缺口，
不影响相应证券可用的竞价比值。摘要中的涨跌停、最高已识别连板和梯队均标明昨日日期、
缺失数量及来源统计范围，不称今日温度。

v1的原receipt/report/summary仍按原版本逐字节重放。正常reader在验证成功后，
可从同一原响应追加 `prior_temperature_qualification`，保留旧 `prior_temperature`，
并绑定原报告及响应SHA256。新增解释不是改写历史输出、重新采集或新的发现时间。
新capture明确使用 `d-opening-auction-shadow-v2`；原观察profile、时钟和请求不变。
修复消费已有档案，不需再dispatch来源或扩大字段、预算、订阅、任务。

## 同日收盘结果接续（2026-10-04）

接续 #509/5977960431 的实际完整未匹配组计算，施工范围见 #509/5978086349。
正常 `stock_market_input_reading.read_current` 在原竞价/日常读取之后，调用薄派生
`d_auction_follow_through`，保存 `details/stock/auction-follow-through.json`，
摘要沿原独立个股详情进入 README。源报告不变；不另建候选/结果注册表或采集任务。

输入只取本次正常 reader 已验证、同一读取包中的竞价和**准确同一市场日**的
日常 `raw_close`；最新失败和既有 `last_qualified_result` 分开保存。选择只看
实际末日身份与收盘用途，不要求5/20/60任一期限通过、复权因子或完整分钟。
错误字节、不同来源/证券/日期不拼接；被选输入损坏不自动倒找旧成功。
当本次保留文件没有该市场日的收盘时，完整原名单仍在，逐项标未取得；
不会拿更晚收盘算成同日结果，不扫描所有历史、不暗中请求来源。

原条件匹配、竞价可比但未匹配、静态条件内但竞价未完成、静态排除、
静态未能判断五组分别保留分母、可比数和高于/低于/等于竞价价的数量。
`auction_to_close_change = same_session_close / auction_price - 1` 是小数比值；
摘要才转百分数。零匹配的中位变化为null，不编造零收益或推荐组合。
方向按原两端价格比较，不把显示精度下舍入为0的微小变化冒充价格相等。
原竞价行的名称、日期、筛选状态和匹配标记不因后续表现改写；同日缺close
仅影响该证券。不新增胜率、仓位、成交、盈亏、因果或策略有效性结论。

复用检查在编码前完成：检查了 [pandas的连接/唯一性合同](https://pandas.pydata.org/docs/reference/api/pandas.merge.html)
和 [Alphalens的因子/前瞻收益接口](https://quantopian.github.io/alphalens/alphalens.html)。
本用途是已有精确键的全分母左连接，不是因子清洗或投资组合回测；选择复用
原证券键、Decimal、标准库统计与Collector，不引入新的行情/分析依赖。
[Tushare日线官方字段](https://tushare.pro/document/2?doc_id=27)定义close为未复权
收盘价；本用途只比较同证券同日，不能直接推广为跨日复权表现。

派生读数失败只影响这个详情，不取消原竞价、价格、Research或失败信息。
沿原512KiB详情、总保留及发布预算；可独立删除本模块、原reader的接点、
专属测试和本说明，源捕获/v1-v2重放保持。每次正常Git发布仍保留自身版本，
不建立新的逐日历史扫描或结果状态机。09:40、日内高低区间、T+1、自然
盘前连续样本及完整D各自仍须验证；本批不新增日程或自动通知。
