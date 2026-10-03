# 独立个股观察：当前日常价格输入与历史观察分开读取

2026-10-02。范围与Human本轮授权见[#297/5953022959](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5953022959)，接续5952434025。当前C2四项验收和固定五日窗仍由[c2-five-session-inputs](c2-five-session-inputs.md)持有。本文件不自签实现、main、发布、自然使用或投资效果。

## 2026-10-03 当前日常价格输入后继

[#730](https://github.com/auguspp/decision-kernel/pull/730)已将现有Tushare Relay的日历和日期横截面接入原日常时钟、正常publisher及本独立读取入口。当前采集合同见[current-stock-market-inputs](current-stock-market-inputs.md)，实际来源成功/失败与固定R仍按#297最新回执核定。下文的Sector取得方式、16名样本及“无新flag/额外GitHub读取”是历史观察支路的说明，不再描述新增的当前价格支路；历史原件和用途不变。

同一R先按根`research.independent_stock_observations`描述符核bytes/SHA256/git_blob取得独立详情。若`preferred_current_input=daily_market_inputs`，优先核`daily_market_inputs.status/latest_attempt/market_session`，沿其`file.read_path`在同R读取`details/stock/daily-market-inputs.json`并核描述符。缺file、pending或reading gap保持具体缺口，不能改读旧16名表冒充本次扫描。

当前价格表的`columns/rows`定义证券、末日原始收盘价、5/20/60区间变化和各自状态码；`status_codes`解释不可比原因。只使用对应期限状态为COMPARABLE的值；变化为小数比例，展示百分比时乘100。分母来自`cohort_denominator`，各期限可比数来自`qualified_windows`，与完整rows自行对账；摘要上下端样本不是全部分母。缺历史证券仍保留，60日不可比不阻止合格5/20日使用；不以中间逐日OHLCV、另一供应商逐字段相等或CNEquity部署作前提。

先核`source_row_coverage`中实际返回数、截断提示、重复身份、错日/拒绝行及来源失败。末日daily取得失败时，报告分母0表示身份集尚未建立，不能解释为市场证券数0或quiet。所有端点时钟、来源身份和缺因子保持原记录，不补零、不默认因子为1、不推断停牌或上市原因。即使有有效rows，来源覆盖仍不自动等于全部上市证券。

这张表可直接用于按证券查询最近完成交易日价格、合格区间表现及本次返回证券中的横向比较。它不是完整逐日走势、最大回撤、总回报或因果领先证明，也不提供公司经营/估值结论。需要业务解释时继续消费现有HiThink/FTShare等合格公司/产业材料；价格缺口只限制依赖它的比较，不否定独立有效的公司证据，也不要求所有来源先统一完美。

旧`observations/price_comparison`和`historical_sample_status/acquisition`按原市场日保留，作为历史观察使用；不能将其固定股票范围、日期或资格自动施加到当前全表。正常当前采集不依赖Sector成功。Quick/Brief消费按[原handoff入口](quick-brief-handoff-v2.md#新独立读取面)接续，不能把文档/配置同步冒充已发生的自然采用。

## 实际接点

原`current_state_delivery_with_odds_watch.Collector`在原来源组装后，调用`independent_stock_reading.attach`。原工作流、时钟、权限与来源客户端不变。没有新flag、另一读ref、定时器、数据库或自动研究。该接点只消费本轮Collector已经验证并保管的原ZIP，不发起额外GitHub读取或市场/公告请求。

同一固定R的`research.independent_stock_observations`为一个紧凑文件描述符。按其`read_path`读取`details/stock/independent-observations.json`，核SHA256、bytes、git_blob；README提供同R导航。先读status、summary、gaps及observations.coverage/selected_observations，按需读完整inventory，不把16名样本当全市场多周期覆盖。未发布时该入口改为显式容量缺口状态，没有沿用旧descriptor掩盖问题。

## 复用与身份

选择沿原Sector lane已经解析的来源：最新失败尝试已经保管的明确原件优先，否则沿现有last_qualified_result；同市场日NOOP仍由原既有选择器保留result-bearing原件。这里不另查运行、不倒找旧成功。来源ref、市场日、latest attempt与原lane gaps全部在详情保留；旧原件重新派生不是新采集或今日行情。

外ZIP先匹配本次真实archive_cache、现有retained原字节、SHA256/bytes/git_blob与到期时点，重用原`unpack_archive`验证完整库存。临时文件只恢复原清单绑定数据，不执行其中代码。原独立消费者的expected_audit_hash来自这份已被外层固定的manifest，不从新输出自取一个hash认证自己。

原`independent_stock_observations.build`、16名绝对带符号报价变动样本规则及全部证券分母不改。先形成独立样本，再用同市场日已保存Stock输入补充原价格检查；历史缺失、不同日或坏原件不能改变入样对象。可选Stock补充失败保留原全市场报价样本及明确缺口。Sector整体失败也不自动否定其已保存且独立资格合格的全市场输入。

## 不能因此签收的部分

现役Sector仍只在部分准备状态下取得全市场页；本批没有移动采集位置、请求新历史或增加quiet-day请求。因此`SECTOR_OWNED_NOT_UNCONDITIONAL_DAILY_INDEPENDENT_CAPTURE`始终明确展示。没有全市场页是INPUT_UNAVAILABLE_NOT_QUIET，而非空扫描。多数新样本可能没有原Stock历史，报价样本不等于5/20/60资格、Surprise或独立研究成果。

这两项仍是C2实际输入责任，不能都改成可选、不能只等五日窗。后续先评估既有日常输入的共享及源调用合同，再按实际授权接齐；不复活已退役#713、旧46笔预算或任何被拒操作。原K3手动采集与历史研究继续保留，但本接点不隐式运行它。

## 容量和退出

根继续192KiB，详情沿512KiB有界报告，保管与API预算沿原publisher。不会删除旧语义字段或扩大根上限。详情/预算不够时保留小型明确缺口入口和README说明；原根连小型缺口也容不下时仍按原发布失败保留上次完整R，不截断伪造成功。

退出时一起移除本接点、专属测试与导航说明；保留原源ZIP、独立消费者和历史R，不删除研究。Quick/Brief实际采用和重复/遗漏检查沿原任务及#351，不增设审计任务。

## Reuse及验证

Reuse Decision：REUSE + THIN_ADAPTER。复用原Collector/cache/ZIP/库存、独立消费者和原价格数学，不复制选择算法。外部实读actions/download-artifact@v5.0.0的src/download-artifact.ts，blob`6f2d7825ff056aaba75b85bd2003c0f64a6752c3`：它复用artifactClient的ID/名称下载和digest检查，但多ID缺失及digestMismatch为warning；不能替代本项目的严格源资格，也无需为已经保存的数据再装下载器。官方artifact元数据合同见[GitHub文档](https://docs.github.com/en/rest/actions/artifacts)。不引入第三方代码/依赖、许可变更或额外费用。

专属测试用合成源包调用真实原消费者，覆盖完整分母、负向/未定价样本、先入样后历史、错误日/坏历史隔离、缺原件/静默缺页非quiet、失败Sector不作选择门禁、正常publisher实际调用、原索引容量。合成测试不是新真实市场输入。正式PR full、独立main、正常发布、固定R真实原件恢复和后继使用分别以#297/本PR回执为准。
