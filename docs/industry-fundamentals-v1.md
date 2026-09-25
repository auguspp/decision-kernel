# 产业雷达：真实经济变量日常观察 v1

Human 2026-09-25：“真正的把产业雷达也做起来”。#297/5833876816定义本轮范围。

## 实际职责

公开统计与报价观察，不自动判定产业拐点。需求/新订单、生产、库存与资金占用、利润、汽车产批零出口、生产资料价格、物流/运价及存储器公开现货分别保留来源原口径。原HiThink期现基差与easy-stock市场背景仍存在，但不再冒充全部产业观察。

## Reuse 与来源

复用 requests/BeautifulSoup、原GitHub run/artifact/同R publisher和公开来源协议；未引入新依赖、数据平台或证券映射框架。
审阅 AKShare MIT @0191689d57c667b7c7a198fd0cf97316837ef311：economic/macro_china.py、economic/macro_china_nbs.py、other/other_car_cpca.py；仅复用审阅后的协议/列定义，不下载执行上游代码，不使用其禁用TLS例子。

- NBS：从最新发布及两个分页发现精确官方统计标题，读取月度工业/能源产量、PMI构成、工业财务及旬度50类生产资料报价。目录内未找到明确保留缺口，不查询无限历史、使用搜索片段或把旧地址写死成最新。
- CPCA：公开charttype=1狭义/广义乘用车月度产量、批发、零售、出口；保留原year/month，量为万辆（已审阅AKShare官方接口文档）。该源HTTP未加密，单独披露，不宣称TLS完整性。
- Eastmoney：已真实取得的PPI、物流业景气与BDTI数据镜像；同统计期同值重复去重，冲突拒绝。REPORT_DATE是统计期/序列日期，不是原始公告发布日期，不能以镜像替代独立官方认证。
- DRAMeXchange：仅公开可见DRAM/NAND现货报价表，保留每张表自己的Last Update。报价不是合同或成交价格；未在原表确认币种时明确UNKNOWN，禁止跨源金额比较，不进入会员历史/付费内容。

## 时间、增量与计算

月度量、YTD累计流量、期末余额、扩散指数、旬度均价与某时段现货平均不可混排。源已披露同比/环比/百分点分字段；PMI旧值若由当期减披露变化推得，明确是计算值，不冒称独立取得的上月数据。CPCA同比只用同口径同月上一年，零/缺分母不算。原数、单位和来源统计期保留；获取日不能替代观察期。

对照上一份精确Git读取包：FIRST_SEEN基线、NEW_STATISTICAL_PERIOD、SAME_PERIOD_REVISION、UNCHANGED及SOURCE_PERIOD_REGRESSED分开。消失的旧序列列入missing，不写成产业下降。首轮捕获旧公开资料不算当天新事件。首轮可用已披露变化及源自带历史，不伪造多日验证。

## 日常运行和失败隔离

复用radar-industry-breadth原Sector完成事件时钟（不要求Sector成功）及原手工入口，新industrial-fundamentals job不读取市场凭据、不占HiThink Key、不依赖商品兄弟job成功。每轮最多16个请求，240秒开始预算，单体4MiB，不递归链接，不重试/绕鉴权；只允许固定服务和NBS固定路径。

所有实际响应、请求/取得时钟、失败种类、manifest/hash及规范化结果留存原生GitHub artifact。capture后无网络重建。单源不可用仍形成部分结果，不以workﬂow绿灯声称全部覆盖；核心完整性/身份损坏拒绝。

原normal publisher沿include-industry-breadth接入research.industry_fundamentals及details/radar/industry-fundamentals.md/json。按精确first-attempt industrial job验收，不以全workflow成功排除兄弟失败后的有效公开数据。当前取不到时展示精确前版观察并标旧资料；不抹掉当前失败。

## 明确不承诺

未全覆盖每个行业、海外库存、半导体fab利用率/合同价、全量SCFI/CCFI或公司订单；不以BDTI或集运期货冒充集装箱现货运价。没有来源就UNKNOWN，不用新闻推算产量/库存。状态回补、报告读回与自然连续可用率分别验收；不建日期永远对齐的假快照。

Quick可以消费全部指标、原始来源及增量，选择解释与公司验证；不要求先有Question/Pre或通过Stock Price Gate。不自动Research/Full/Odds/Watch/交易。AI Investment Authority=NONE。
