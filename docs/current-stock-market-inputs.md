# 日常个股输入：去掉试验日期、固定股票名单和行业前置

2026-10-03。承接 #297 与 Human 本轮要求：把现有数据源变成当前系统可用输入，排查写死的日期、字段、样本和流程依赖。Reuse Decision：THIN_ADAPTER，复用现役 Tushare Relay 客户端、原 daily/trade_cal/adj_factor 接口、现有日常时钟和 current-state Collector。不引入新供应商、订阅、HTTP 客户端、数据库或研究/投资执行器。

## 实际入口

原 `stock-reading-after-sector.yml` 第一条日常时钟（10:35 UTC）增加无 needs 的 `daily-market-inputs` job。它不依赖 Sector 或 reconcile 成功，也不读取行业名单。显式 `workflow_dispatch mode=market-inputs` 走同一代码；不是重跑 #713、FTShare 一次性试点或旧 #727。

执行仍先核精确 main 与独立 main CI。原派发/TDX/Inbox 路径不变。该新 job 仅拿原 `TUSHARE_PROXY_API_KEY`，不拿 GitHub 写凭证。原正常 publisher 消费完成后名为 `stock-market-inputs` 的运行；`INCLUDE_CURRENT_STOCK_INPUTS=1` 在现役发布步骤启用新读取，不改变历史离线消费者默认行为。

## 按用途取得数据

一次 `trade_cal` 取得当前日期范围的来源日历，15:30 前不取当日收盘。按日历自动得到最近完成交易日及5/20/60交易日前的端点；没有固定2026-09-30，也没有固定三只、16只股票或旧 reading SHA。

对每个必要日期，各取一次 `daily` 和 `adj_factor` 日期横截面，最多9个逻辑请求、27次原客户端 HTTP 尝试。选择范围是本次末日返回的所有有效证券身份，不先按行业或已有历史筛选。6000是所用接口的有界请求值，不是已证明的全市场证券总数；满页、源端 total/has_more、重复和错日记录保留，榜单只称本次可比子集。

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

## 流式读取超时的现役客户端修正

后继真实run37119142775仍有末日daily和两个历史因子TRANSPORT_CONNECTION；原收据不足以判断这些旧失败的底层原因，不改写为超时或成功。检查现有Requests 2.34.2[官方源码](https://requests.readthedocs.io/en/latest/_modules/requests/models/)发现iter_content把urllib3 ReadTimeoutError包装成ConnectionError，原客户端漏掉了这个已知读取超时的有限重试。THIN_ADAPTER：在原_http_get流式读取处仅将已知包装还原为ReadTimeout，复用原最多两次/间隔30秒规则；普通连接、TLS、认证、限流或其他协议错误没有获得通用重试，超时参数和来源预算未改。

异常收据从调用开始记录时间，并只保留STREAM_READ_TIMEOUT、REQUEST_TIMEOUT、CONNECTION_ERROR或REQUEST_ERROR四个诊断码，不保存异常消息、主机或凭证。失败分块不冒充完整响应；原字节上限、长度、日期与成功体检查不变。capture/verify保留该可选诊断，旧收据保持可重建。验证直接使用Requests真实Response.iter_content和urllib3异常，另核普通连接不重试、诊断保存重建及私有文字不泄露。正式CI和真实来源验收沿本PR/#297回执；修正本身不证明旧连接失败全是超时或当前源已稳定。

## 固化成功路径与日常有限恢复（2026-10-03）

原始经验分别保留：#732/5969211086真实流式读取超时经原有限重试成功，仍有两个上游池耗尽缺口；#732/5969593381同一现役代码的新真实采集九次HTTP200成功，5561分母的5/20/60可比5550/5536/5502，正常publisher和固定R四入口已实际消费。不能把“两个失败后停止”或“后来一次全成功”当成来源永远稳定。

仅此日常通道在原Relay request显式选择最多三次尝试，临时队列/网关/读取超时仍按原TEMPORARY_QUEUE分类，间隔30秒后再90秒。只重试同一API与参数，保留三次原响应/类型/时钟；成功立即结束。普通连接、TLS、认证、限流、来源禁用、非法参数和HTTP200格式错误没有新重试。其他Relay调用默认仍最多两次/30秒，旧已消费试点不重新启动。复用现有Requests/urllib3，不配置自动HTTPAdapter重试丢掉中间原响应；参考[urllib3官方有限重试与backoff合同](https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html)，以现有收据owner作薄适配，不建retry平台。

一次capture共享17分钟请求准入预算；开始新请求或延后重试前必须还留等待时间和60秒请求余量，预算不足停止，空尝试明确REQUEST_BUDGET_EXHAUSTED而不伪造HTTP错误。carrier硬20分钟仍保持。已完成输入继续保存/发布，未请求端点保持NOT_REQUESTED_AFTER_SOURCE_STOP；失败不报废其他期限。该准入预算不能中断已在执行的stream，原10/30秒socket超时、响应字节上限和20分钟job超时仍承担执行边界。

新收据声明retry_waits=[30,90]，verify实际核每次前置TEMPORARY_QUEUE、间隔与最多三次，不只是允许第三个数组元素。没有该字段的旧收据仍按两次/30秒合同验证，旧失败不升级。无新增时钟、来源、数据库、provider waterfall、自动Research或投资权限。自然日常执行/消费仍单独验收；临时源故障可以发生，不能承诺以后每次成功。

## 最新失败与已验证可用结果并列（2026-10-03 后继）

真实run37128261519的末日daily三次超时，而此前run37125677265已取得相同市场日的合格输入。正常入口仅显示最新失败，使已保存的可用结果需要手动寻找旧R。现沿用current-state已有的latest_attempt/last_qualified_result分工：最新状态、原件和daily-market-inputs.json保持本次事实；本次没有任何可比期限、正在执行或读回失败时，在原有最近100条原生运行查询内，另选最近一个较早的completed/success日常run，只校验这一候选，不跨损坏/过期候选继续倒找。

原Collector核artifact身份/字节/hash/过期，原producer verify从原响应重建，并要求LIVE_TUSHARE_RELAY和至少一个可比期限。通过后在daily_market_inputs.last_qualified_result保存原运行、市场日、采集完成时间、分母、各期限数、原件与独立文件details/stock/last-qualified-market-inputs.json。README和独立个股summary直接显示链接与旧日期；最新失败仍保持，旧结果不能用于声称更新交易日已有行情。一次读取仍固定一个R，不能混合两次采集的端点、名单或因子。最新已有可用期限时不以旧数据改善通过率。

候选不合格时保留latest结果，记录last_qualified_reading_gap并回滚候选留存；有限查询完整性另记run_query_complete。保存副本是只读历史输入，不是生产恢复、自动Research或投资授权。自然后续运行/分析消费仍按C原责任验收；artifact过期后的历史阅读副本继续按原固定R读取，不升级当前来源资格。

Reuse Decision: THIN_ADAPTER。内部复用current-state.md既有最近尝试/最后合格结果语义、Collector.archive/retain与stock_market_inputs.verify。施工前检索并读[requests-cache 1.3.3 stale_if_error实现](https://requests-cache.readthedocs.io/en/stable/_modules/requests_cache/session.html)和[过期合同](https://requests-cache.readthedocs.io/en/stable/user_guide/expiration.html)，并核[GitHub artifact API](https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28)。HTTP缓存可提供旧响应，但本处输入是已保存的run/artifact，并须同时展示最新失败与完整旧报告身份；给来源客户端引入持久缓存会新增存储且不能替代现有原件回放。故不安装/复制外部代码、不新增许可/运行成本，薄适配既有读取消费者即可；退出时同改该reader、正文链接及专属反例，旧报告/失败保留。


## 2026-10-08 因子返回条数异常与同日历史资格连续性（有限消费者修复）

在R=ee173b793bcdedb1d9d6463b5735e05cdba2b3b8，9月30日输入的7月7日基期日线返回5517条，复权因子仅5条；60日可比5/5561。相同市场终点的旧合格保存批复权因子返回5536条、60日可比5502/5561。成功HTTP/成功原件验证不是足额证券因子覆盖证明；上游具体原因仍UNKNOWN。

复用原日常reader/Collector与一次候选恢复限制，不增加任何来源API调用或重试。当前已保存原报告的每个比较基期，若同日因子返回行数小于价格行数，新增只读source_coverage_attention；最新合格的5/20日继续有效。原有最近100条内仅审一个较早completed/success日常run，严格校验原artifact身份、原响应重建、日期/版本和有效期限；只有同一市场日、受影响期限的已验证可比数确实更高，才把旧批完整单独刊为last_qualified_result，同时保留两批run/cutoff/分母，不拼接端点、证券名单或因子。候选不改善则回滚它的留存，不为填补覆盖率向更早批次无限倒找；旧“最新没有任何可比期限”的原有回退资格不改。发布说明不得把此阅读连续性说成因子源已修好。

本后继属于数据资格可见性/消费者不静默失明的修复。**尚未补到10月8日市场日的整表多期限输入**，也未修复供应商7月7日真实因子覆盖；无新日程、源请求、费用、研究、Watch/Odds、交易。既有正常输入时钟下一自然运行与同R publisher/Brief实际使用分别验收，不提前签成功。


## 2026-10-08 纯只读三候选上限：跳过有效但资格较差的旧批，不跨受损原件

真实原保存批表明，9月30日同一市场终点的日常输入在10月5/6/7日陆续返回60日基期因子2/2/5行，10月3日保存批返回5536行。此前只核一份最近成功保存候选，遇到有效但同样覆盖退化的旧批就停止，未能单独发布已证明存在的较完整60日历史参照。

受影响期限已保存因子返回少于日期价格返回且最新其它期限仍有资格时，在原最近100条原生运行响应和同一个R中**最多核三份之前成功候选**；同一市场日、完整producer原响应重建/身份/过期/原件校验，不改善可继续检查下一份*有效*候选；受损/过期/错误身份/日期不同立即停止，绝不通过跳过坏原件换取看似较高覆盖。找到某受影响期限原合格数量真正更高才独立留存其完整last_qualified_result，最新输入全保留，不拼证券、因子或端点。最新所有期限都无资格时仍仅核最近一份成功原件。

这个调整不改变来源请求合同、Runner定时、通知或自动投资；不能从旧覆盖值推出最新上游已恢复。三个旧候选仍不足时留下明确边界，不无界翻历史、不反复重试数据源。测试包含连续两份有效但同样坏的候选之后的旧合格原件及中途损坏的严格停点。


## 2026-10-08原时钟缺交付：复用Sector完成事件的防重补充入口

在10月8日固定自然窗，原现役\`stock-market-inputs\`定时事件未提供当日结果（不能据此伪称没有执行的细分原因）；Sector完成后，现役\`stock-reading-after-sector\`已收到同日workflow_run事件。为防止GitHub cron延迟/缺投递造成真实市场日输入空白，本job增加**已有Sector工作流「完成」事件**作为另外一个收盘后时钟入口；**不依赖Sector运行成功、成员名单或行业价格资格**。原10:35 UTC工作流cron与手动mode=market-inputs均保留，不创建第二工作流或改变Quick/Brief/通知。

两时钟可能在同一天触发，为保护Tushare Relay原**每日一个、最多九次逻辑源请求**的预算，复用GitHub原生workflow runs/artifacts做不联网市场的日期闸门：同一上海本地15:30以后只在没有别的真实来源尝试时允许一次capture；若已有源artifact、并发或不确定原尝试则**fail closed**不再打源。跳过不冒充合格日频：该job保留限域、短TTL的显式\`stock-market-inputs-skip-<run>-1/skip.json\`（source_requests=0），正常read-model读取器按artifact身份和字段校验跳过来源0请求run，再采用真正有report原件的最近run。未取得skip证据、artifact身份不合格或无新源时保留GAP，不擅自倒找。正常源capture/原件重算、Publisher、来源费用、时间/状态/Research权限合同完全保留。

10月8日人工定向市场输入run37788705002本身**不是当天自然定时交付**，不得从中补签自然窗。该补充的真正效果只能由下一次按既有源运行节奏发生的工作流结束和R/Quick/Brief实际读回证实；不承诺以后不会有供应商或GitHub服务故障。
