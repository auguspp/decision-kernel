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
