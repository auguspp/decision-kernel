# C2：现役价格输入、用途资格与历史核验

范围：[Human要求与本批接点](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5964411868)。这是现时C2补价的逐接口资格检查，不是已启用日常Tushare扫描。#713退役、#725试点消费及其403不改变；不调用FTShare受限路由、不升级套餐。完整C及固定自然使用窗继续由#297持有。


## 2026-10-03整改后继：区间表现不再被完整路径门槛挡住

[Human整改授权与范围](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5966565563)采纳“按实际用途检查”，不是降低全部数据要求。现役`independent_stock_reading`在原来源完整验证后，给出`interval_performance`（`c2-price-purpose-qualification-v2`），并将全样本区间表放入正常读取README和summary，而不只留下附件或一个合格计数。

| 使用什么结论 | 必须检查什么 | 不应附加的前提 |
|---|---|---|
| 5/20/60日区间复权价格表现 | 原合格日历的准确起终日、同一证券、同口径两端close与累计factor、有限正数、真实来源/版本；本固定样本保留既有终点报价核对 | 中间每天OHLC、成交量额、因子全部完整；完整历史成员/PIT |
| 逐日走势、回撤、波动、量价或持续性 | 该指标真正使用的逐日价格、因子及相应量额/日期 | 区间端点可用不能代签这类指标 |
| 历史当时能否提前发现、领先/跟随角色 | 该结论所需的当时信息与连续观察 | 当前成员回看区间涨幅不能代签 |

比值仍为`end_close*end_factor/(base_close*base_factor)-1`，不补任何中间值，不假定factor=1。供应商复权价格不是已认证总回报，也不代表已恢复公司行动明细。证券/日期/响应身份、失败和停点仍按原验证器检查；字段不属于某项指标不等于可以接受错证券、错日期或真实来源错误。没有进行跨来源价格/因子拼接。跨源比对是诊断工具，不是所有区间价格用途都必须拥有两家供应商的通用要求；本批保留的是原固定输入的明确绑定。

原采集、`report.json`、`verify`/`verify_gaps`及原`qualified_windows`逐字节语义不改；旧字段继续表示原完整逐日检查。新增`interval_performance.qualified_windows`只表示端点区间资格，两者同时显示。后继解释绑定原report摘要与实际source_stop，不因解释更新重写历史失败或重新取得行情。原完整16名保留；缺端点、值被拒和历史不足分别留处置，不要求新股具有不存在的60日历史；子集不是全成员排名。

直接复用原Relay、来源包/停止校验、既有消费者和Decimal算术，没有新取数程序、数据库、排名器或依赖。CNEquity现有query/版本/复权能力继续可复用，未启用其采集不是来源失败；为这四个已有数值建立另一个湖或导入新依赖没有必要。官方公式参见[Tushare复权说明](https://tushare.pro/document/2?doc_id=146)；第三方Relay身份不因此变成官方Tushare。

本节取代下方v1门槛作为“所有价格用途”的解释；下方继续持有原试点、采集预算、失败、保管和历史重放合同。新交易日日常输入与Quick/Brief实际采用仍由#297接续，不把离线用途整改当成日常采集或完整C验收。

## 同一批对象，不因数据可得性换选

复用固定R `5b116c5741b4e813bc9e9f8b145750448d1236ec` 的 `details/stock/independent-observations.json`，SHA256 `2d4cd81c19e5723af1d785e0a6a2407eecbd1ae5be700bb4d27a0bfb28ebe854`。原16名选择和61个保存交易日保持，终点为2026-09-30；这不是10月3日行情，也不是9月30日当时可得信息。

已有股票输入workflow新增一个独立manual choice `tushare-c2-price-check`；其他参数为空，closure为none。仅main/attempt1，当前main CI成功且原生运行记录未消费该唯一标题后才能访问原secret。每股一份daily、一份adj_factor，另一份终点日期daily，最多33个逻辑调用、66次HTTP；每响应沿原4MiB，原body总量16MiB。没有新定时、自动下一批或重复整次试验；主干更新不复位一次性范围。原生下游发布与日常恢复均排除本独立来源检查，Python读者也按实际运行身份/目的隔离。

复用`tushare_relay.py`，host、header凭据、TLS/redirect/proxy和30秒一次临时排队重试均不变。401/403/429、明确source failure、格式或范围错误停止剩余调用；传输/保管状态不明不重试。HTTP成功、失败、未请求、字段完整、每窗可比各自保留。

## 原v1完整逐日核验能建立什么

每个5/20/60窗口分别要求6/21/61个原日历交易日的有效日线和正因子，证券/日期唯一、OHLC合理、正成交量额、终点close同时匹配该Relay的终点日线及原保存HiThink报价。缺日不填充，不从缺失猜停牌或上市原因。原16名分母不删，未请求不等于不满足条件。

按同一Relay股票及日期一对一接合日线/因子，价格变动为 `end_close*end_factor/(base_close*base_factor)-1`；原始价格和因子均保留。它是供应商复权价格表达，不是总回报、分红明细恢复或无公司行动证明。因子字段存在并不证明供应商算法/全量事件完全可靠，实际样本还须对照已有合格路径；单次实测不认证长期稳定或日常准入。

全日daily只表示实际返回的交易日线证券，不是上市证券全宇宙。停牌/未上市分母和quiet-day独立发现需要另有合格输入，本批不补签。`pre_close`是除权参考，不强行等于前日原始close。vol是手、amount是千元；盘后字段单独保留，未证明跨供应商量额口径一致，不将其相加或静默抹去。

原件包包含固定reference、请求与真实运行身份/HTTP/时钟/安全headers、原body和逐窗报告。离线verify检查原body摘要/完整库存、请求顺序、停止及原重试边界，再重新计算报告；调用方另以实际run/head/attempt和artifact摘要固定外层身份，不能由包内自报来源认证自己。verify只读；来源数据失败可以被诚实保留并成功重放，但不等于数据资格通过。

## Reuse与退出

REUSE + THIN_ADAPTER：原Relay、canonical、官方日线/因子合同和固定现有观察。实际审查 `waditu/tushare@093856995af0811d3ebbe8c179b8febf4ae706f0` 的 `tushare/pro/client.py`（blob `d8803117d8182edc209071b20b568fe544bbf055`）：直接HTTP POST/token/DataFrame边界不匹配已购HTTPS GET/header Relay，因此不安装/复制SDK、不新增依赖。官方说明：[daily](https://tushare.pro/document/2?doc_id=27)、[adj_factor](https://tushare.pro/document/2?doc_id=28)。第三方Relay与官方直连身份分开，官方积分要求不替代本账号权限证明。

本核验不新建排名器、数据库、provider router或自动研究。退出时去掉独立choice/job、caller及其专属测试/说明，历史来源原件和必要只读解释保持；不要为退出删除原共享Relay或日常来源。工程、正式CI/main、来源实际取得、日常采用、自然使用及Human接受分别以PR/#297回执为准。

## 2026-10-03 后继：缺日差额与已保存比较接入

范围与Human“继续”见[#297/5965083214](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5965083214)。#726原33次来源核验已消费，保留原题目/预算/输出；不重新执行它。复用同一模块、原Relay及同一个股票输入job，新增明确choice `tushare-c2-factor-gaps`。先固定原run37091291428/artifact11261749659的外部身份和ZIP摘要，原始replay通过后才补取。

本差额只请求5张`adj_factor`日期表：9/30先核16名原终点因子完全一致，然后7/7、7/15、8/18、9/18；各limit6000、无分页，最多5逻辑/10HTTP。只将原来有daily而无factor的47个证券/日期键接入；没有价格的日期不补，不将表内其他股票纳入样本。数值/来源声明冲突、形状或权限等明确失败停止后续请求。缺行不前填，不生成假原始响应；原ZIP和新响应各自保留，原`evaluate`与差额共享同一价格资格/计算实现。只验证终点重叠一致性，不冒称完整历史版本、独立底层上游或公司行动明细已认证。没有新源主机、凭据、SDK、依赖、数据库或排名器。

既有`independent_stock_reading`可在相同9/30日历、16名顺序/selection_hash与终点报价全部匹配时，附上`price_comparison`及可读摘要。沿现役Collector验证原生run/artifact/实际ZIP、原始响应及逐窗复算，不覆盖`observations`里的HiThink原覆盖或失败。没有后继成功差额时明确显示原比较及最新差额尝试；后继成功原件损坏时拒绝，绝不倒找更早成功。读取范围限原工作流最近20条及明确固定前驱，保留原API/根/详情字节上限，不够时显示缺口。

这是**日常读取端采用已保存补充资料**，不是已启用日常Tushare采集。新交易日/不同样本不继承本批比较；无Sector活跃日的完整独立分母仍未由此建立。差额任务不触发日常自动补采；原普通publisher仅按已保存原件规则发布，源结果、发布/读回与自然Quick/Brief采用分开验收。原始试点的发布隔离保持。

复用#726已经核对的官方接口及SDK差异：本次重新核doc28的单日因子查询合同，不新增通信层或其他轮子。退出本差额时删除其choice、捕获分支和当前读取接点，保留原两个格式的必要replay、源失败和历史原件。具体工程/来源/发布结果以本批PR与#297后继回执为准，不由本文预签。
