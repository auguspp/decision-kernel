# 日常个股输入：去掉试验日期、固定股票名单和行业前置

2026-10-03。承接 #297 与 Human 本轮要求：把现有数据源变成当前系统可用输入，排查写死的日期、字段、样本和流程依赖。Reuse Decision：THIN_ADAPTER，复用现役 Tushare Relay 客户端、原 daily/trade_cal/adj_factor 接口、现有日常时钟和 current-state Collector。不引入新供应商、订阅、HTTP 客户端、数据库或研究/投资执行器。

## 实际入口

原 `stock-reading-after-sector.yml` 第一条日常时钟（10:35 UTC）增加无 needs 的 `daily-market-inputs` job。它不依赖 Sector 或 reconcile 成功，也不读取行业名单。显式 `workflow_dispatch mode=market-inputs` 走同一代码；不是重跑 #713、FTShare 一次性试点或旧 #727。

执行仍先核精确 main 与独立 main CI。原派发/TDX/Inbox 路径不变。该新 job 仅拿原 `TUSHARE_PROXY_API_KEY`，不拿 GitHub 写凭证。原正常 publisher 消费完成后名为 `stock-market-inputs` 的运行；`INCLUDE_CURRENT_STOCK_INPUTS=1` 在现役发布步骤启用新读取，不改变历史离线消费者默认行为。

## 按用途取得数据

一次 `trade_cal` 取得当前日期范围的来源日历，15:30 前不取当日收盘。按日历自动得到最近完成交易日及5/20/60交易日前的端点；没有固定2026-09-30，也没有固定三只、16只股票或旧 reading SHA。

对每个必要日期，各取一次 `daily` 和 `adj_factor` 日期横截面，最多9个逻辑请求、18次原客户端 HTTP 尝试。选择范围是本次末日返回的所有有效证券身份，不先按行业或已有历史筛选。6000是所用接口的有界请求值，不是已证明的全市场证券总数；满页、源端 total/has_more、重复和错日记录保留，榜单只称本次可比子集。

区间只使用两个收盘价和两个对应日期因子。无需另一个供应商逐字段相等，也无需中间逐日成交量、OHLC、因子全部齐全。日期或价格有问题仍拒绝相应用途；缺60日端点不影响5/20日，短历史证券不从末日分母删除，不假设其上市/停牌原因。

只读价格表不替代现役 HiThink canonical Stock/Market、FTShare其他公司/产业来源或 CNEquity 原生存储。它们无需被统一改成同一上游；已有来源职责继续保持。单一来源已足以满足某用途时，不强制双供应商或先建本地 lake。FTShare固定试点与CNEquity未部署的采集能力，不再作为本日常价格通道的前置条件；它们各自的未完工程也不冒称完成。

## 系统消费与缺口

原 exact response、请求、来源日历、实际取得时间和重试状态进入 `stock-market-inputs-<run>-1` artifact。`report.json` 为紧凑完整证券表，`summary.md` 展示各期限可比数与上下端样本。小数变化按12位序列化；精确源值在原响应中。无中间历史填补，无公司行动详情、总回报、因果领先、PIT、自动Research、Odds或投资授权。

正常读取入口将新结果放在 `details/stock/daily-market-inputs.json`，从现役 `details/stock/independent-observations.json` 和 README 引入。发布端从原响应重新计算并核报告字节；保存时间不是市场日。最新失败/待完成/过期保留为输入缺口，不搜旧成功冒充新结果。

旧16名、旧区间解释、旧失败和一次性授权记录继续保留。此次解除的是日常用途不必要的门槛，不回写旧报告或关闭尚未验收的研究责任。真实源运行、正常发布及实际正文读取以本PR/#297回执为准；测试和接线不是自然Quick/Brief采用证明。

## 发布前审查修正

正常表中的收盘价按相同 Decimal 数值输出，不保留无意义的末尾零；原响应字节、原字段与精度仍在原件中。合成6000名、带12位末尾零的合法价格曾触发整表字节上限，修正后仍在原512 KiB预算内完成全表保存和回放，不删证券、不降低计算精度，也不加来源门槛。

同一准确末日的证券若返回冲突报价，该证券仍计入分母，价格和依赖它的区间明确不可比；重复原行和来源处置保留。不从冲突报价中任选一个，也不通过删除证券使通过比例变好。这些是合成反例验证，不是新增真实行情或生产验收。

## 实际网关故障后的合同修正

2026-10-03真实运行37116525057的trade_cal返回HTTP502和零字节响应。原客户端先解JSON，误将已有临时网关状态归为格式错误；原capture保存了空响应，verify却以原件必须非空拒绝它。后继修正只让非JSON的502/503/504沿原HTTP状态执行原有最多两次、间隔30秒的有限重试；401/403/429仍不重试，HTTP200坏JSON/空体仍不合格，有效JSON内的来源禁用等业务状态保持原优先级。不会因无法解析响应就推断成功，也不改变连接错误的重试范围。

失败原件允许精确零字节并核哈希/库存，SUCCESS仍必须有非空HTTP200成功响应且通过实际字段/日期检查。原502、尝试及历史失败继续保留；修正不伪造已拿到日历或价格。复用现有Requests客户端和HTTP状态合同，不引入新客户端/依赖；[Requests官方说明](https://requests.readthedocs.io/en/stable/user/quickstart/#json-response-content)明确JSON可解析性与HTTP成功是两件事。源运行、原件回放、正常发布与实际分析使用仍分别验收。

## 复用依据与退出

已核内部 `tushare_relay.py`、`tushare_c2_price_check.py`、`independent_stock_reading.py`、`hithink_independent_capture.py`、FTShare历史比较与CNEquity桥接。同步检查CNEquity官方仓库/文档：其增量/Parquet/PIT功能可复用，但本用途不需要先部署整套lake。接口字段参照Tushare官方文档26（trade_cal）、27（daily）、28（adj_factor）；实际服务仍明确是第三方Relay，不用官方文档替代实际返回资格。

退出时移除本日常job、publisher触发/环境开关和专属reader/测试；原行业/Stock/Inbox及原来源客户端不受影响。已保管的源包和研究引用保留。没有第二个常驻状态库或自动provider waterfall。
