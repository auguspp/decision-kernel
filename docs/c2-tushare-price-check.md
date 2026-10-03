# C2：现役 Tushare Relay 日线／复权因子有界核验

范围：[Human要求与本批接点](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5964411868)。这是现时C2补价的逐接口资格检查，不是已启用日常Tushare扫描。#713退役、#725试点消费及其403不改变；不调用FTShare受限路由、不升级套餐。完整C及固定自然使用窗继续由#297持有。

## 同一批对象，不因数据可得性换选

复用固定R `5b116c5741b4e813bc9e9f8b145750448d1236ec` 的 `details/stock/independent-observations.json`，SHA256 `2d4cd81c19e5723af1d785e0a6a2407eecbd1ae5be700bb4d27a0bfb28ebe854`。原16名选择和61个保存交易日保持，终点为2026-09-30；这不是10月3日行情，也不是9月30日当时可得信息。

已有股票输入workflow新增一个独立manual choice `tushare-c2-price-check`；其他参数为空，closure为none。仅main/attempt1，当前main CI成功且原生运行记录未消费该唯一标题后才能访问原secret。每股一份daily、一份adj_factor，另一份终点日期daily，最多33个逻辑调用、66次HTTP；每响应沿原4MiB，原body总量16MiB。没有新定时、自动下一批或重复整次试验；主干更新不复位一次性范围。原生下游发布与日常恢复均排除本独立来源检查，Python读者也按实际运行身份/目的隔离。

复用`tushare_relay.py`，host、header凭据、TLS/redirect/proxy和30秒一次临时排队重试均不变。401/403/429、明确source failure、格式或范围错误停止剩余调用；传输/保管状态不明不重试。HTTP成功、失败、未请求、字段完整、每窗可比各自保留。

## 能建立什么

每个5/20/60窗口分别要求6/21/61个原日历交易日的有效日线和正因子，证券/日期唯一、OHLC合理、正成交量额、终点close同时匹配该Relay的终点日线及原保存HiThink报价。缺日不填充，不从缺失猜停牌或上市原因。原16名分母不删，未请求不等于不满足条件。

按同一Relay股票及日期一对一接合日线/因子，价格变动为 `end_close*end_factor/(base_close*base_factor)-1`；原始价格和因子均保留。它是供应商复权价格表达，不是总回报、分红明细恢复或无公司行动证明。因子字段存在并不证明供应商算法/全量事件完全可靠，实际样本还须对照已有合格路径；单次实测不认证长期稳定或日常准入。

全日daily只表示实际返回的交易日线证券，不是上市证券全宇宙。停牌/未上市分母和quiet-day独立发现需要另有合格输入，本批不补签。`pre_close`是除权参考，不强行等于前日原始close。vol是手、amount是千元；盘后字段单独保留，未证明跨供应商量额口径一致，不将其相加或静默抹去。

原件包包含固定reference、请求与真实运行身份/HTTP/时钟/安全headers、原body和逐窗报告。离线verify检查原body摘要/完整库存、请求顺序、停止及原重试边界，再重新计算报告；调用方另以实际run/head/attempt和artifact摘要固定外层身份，不能由包内自报来源认证自己。verify只读；来源数据失败可以被诚实保留并成功重放，但不等于数据资格通过。

## Reuse与退出

REUSE + THIN_ADAPTER：原Relay、canonical、官方日线/因子合同和固定现有观察。实际审查 `waditu/tushare@093856995af0811d3ebbe8c179b8febf4ae706f0` 的 `tushare/pro/client.py`（blob `d8803117d8182edc209071b20b568fe544bbf055`）：直接HTTP POST/token/DataFrame边界不匹配已购HTTPS GET/header Relay，因此不安装/复制SDK、不新增依赖。官方说明：[daily](https://tushare.pro/document/2?doc_id=27)、[adj_factor](https://tushare.pro/document/2?doc_id=28)。第三方Relay与官方直连身份分开，官方积分要求不替代本账号权限证明。

本核验不新建排名器、数据库、provider router或自动研究。退出时去掉独立choice/job、caller及其专属测试/说明，历史来源原件和必要只读解释保持；不要为退出删除原共享Relay或日常来源。工程、正式CI/main、来源实际取得、日常采用、自然使用及Human接受分别以PR/#297回执为准。
