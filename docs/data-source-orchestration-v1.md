# Data Source Orchestration v1｜来源职责而不是全局主备表

日期：2026-09-26。Authority：#297/5845050149。Human要求把已购第三方 Tushare Relay 接入并重新梳理现有数据源。本文是工程编排合同，不是第二需求库、数据真伪评分或自动 provider router。Evidence changes Belief；Price changes Odds；Data != Evidence != Judgment != Decision。

**部署与验收：本文是已授权并实现的来源职责及运行合同；实际PR、main、发布、来源和消费状态分别以#593最新回执为准。下文“正式补充/生产接点”本身不是上线或全市场完整性证明。**

## 1. 三层必须分开

**原始/官方发布者**拥有其公开原件与字段：CNINFO/交易所/公司披露、NBS、HKEX、CFFEX、CPCA、DRAMeXchange 等。它们的原文、统计期间和修订时钟不能因为下游 API 更方便而消失。

**结构化取得与中转层**负责把公开数据变得可消费：HiThink、FTShare、Eastmoney 公开接口、TDX/eltdx、Tushare Relay、NewsNow。这里的“primary/secondary”只表示某个 Kernel 消费用哪条已验合同作为默认取得路径，不是“更真/更聪明”的排名。

**实现轮子/本地基础设施**不自动成为独立来源：AKShare 与 EasyStock 提供可复用的公开协议/字段实现；CNEquity 提供本地 Parquet/PIT/query/revision 能力；MinerU/Woton 等只处理文档表示。它们不能因为换了库名就把同一上游变成第二份独立 Evidence。

禁止全局 waterfall：来源语义不同就并存，不能遇到失败便静默换另一来源并把结果当同一字段。允许的 fallback 必须是消费者已经定义的**同语义连续性路径**，并保留实际来源、时点和差异。

## 2. 当前来源职责图

| 用途 | 默认/主体取得 | 二线/补缺/交叉检查 | 原件/解释边界 |
|---|---|---|---|
| A股交易日、价格、Stock/Sector market expression | HiThink Financial-API | FTShare已验 market inputs；Tushare Relay daily/daily_basic/adj_factor/trade_cal 只在逐接口验收后补缺/比对 | 价格变化只改 Odds/Market Expression，不自动改 Belief |
| Sector / Concept | HiThink Sector；TDX/eltdx source-native Concept | Eastmoney 概念二线；Relay 的 index_classify/index_member_all/ths_index/ths_daily/dc_* 作为补充候选 | TDX、Eastmoney BK、HiThink taxonomy 不互译成同一个身份 |
| 公司公告、财报原件 | CNINFO/交易所/公司公开原件 | FTShare announcement discovery、finance context；Relay income/balancesheet/cashflow/fina_indicator/disclosure_date 作为结构化上下文 | 结构化表不替代原PDF；版本、报告期、披露日分开 |
| Smart Money / 公开资本行为 | HiThink hot_money/org；FTShare原始席位/北向/高管；Eastmoney持股/调研/增减持/回购/定增/研报；HKEX季度北向持股 | **Tushare Relay 正式补充**：hm_list/hm_detail/report_rc/top_list/top_inst；stk_surv/research_report 按需研究 | Relay游资标签/营业部不是自然人认证；北向成交额不是净买；报告期持股不是交易日 |
| 产业/宏观 | NBS官方发布/RSS；CPCA；DRAMeXchange；现役工业统计与镜像 | Relay shibor/index_global/hk_daily/us_daily/fut_wsr 等逐接口验收后进入 B1；EasyStock审阅过的腾讯/Eastmoney/CFFEX合同继续现役 | 镜像不冒充官方发布日期；不同商品单位/期限不拼总量 |
| News / narrative discovery | NewsNow七个固定窗口；NBS native RSS | Relay news/major_news/anns_d/irm_qa_* 只有逐接口资格后才能进生产 | 聚合器保留具体来源；新闻是发现输入，不自动成为公司 Evidence |
| 本地历史/PIT存储 | GitHub retained originals；CNEquity 可选本地 lake/query | 无 | 存储层不是新数据来源；原 source identity 不改名 |

## 3. Tushare Relay 的正式定位

当前服务合同来自 Human 提供的 Tushare Relay 0.5.61 说明。正式根地址：

https://pcd.mobcvb.cn/tushare/pro

认证：repository Actions secret TUSHARE_PROXY_API_KEY → HTTP header X-API-Key。不把 Key 放 URL、Git、日志、浏览器或Research文本。正常 TLS 校验、禁自动 redirect、禁环境代理/凭据继承。旧 tl.kaixin8.top 试验地址和明文备用服务器不作为生产 fallback。

Relay 是**第三方 multi-upstream compatibility layer**，不是“官方 Tushare 数据”等价声明。接口名相同也可能由官方兼容池、本地 ClickHouse、本地聚合或外部适配提供。每次消费者必须保留：relay host、api_name、请求参数、取得时间、HTTP/code、X-Request-ID/X-Cache，以及响应中实际可见的 provider/source 字段。

### 已验可用方向

- hm_list：正式 __probe=0 可返回游资名录；不能把 vendor mapping 认证成真人。
- report_rc：出现过排队后恢复；可用于结构化同机构预测期比较，空结果不证明无研报。
- stk_surv：实际返回机构名称；参与人员字段是否完整另验。
- research_report：实际返回历史券商报告/PDF locator，适合按需恢复同券商前后报告；其外部适配曾忽略通用 limit，不能套统一分页假设。
- top_list/top_inst：可作为龙虎榜冗余/对照；“机构专用”仍不是具体基金。
- 财务三表、Shibor、申万行业等已取得小样本；只有进入真实消费者后才算对应生产能力。

### 临时容量与失败

upstream_pool_exhausted 以及 HTTP 200 / code=1,msg=timeout 按供应商说明和实际复测视为**临时排队/容量状态**。生产薄适配只允许：

第一次请求 → 30 秒 → 再试一次 → 仍失败则 TEMPORARY_QUEUE_GAP

不无限等待、不短轮询、不后台自旋。data_source_unavailable、401/403、参数错误不按队列重试；429保留 Retry-After 并停止本轮，不通过旧host/备用host绕过。502/503/504只有在没有更明确不可重试语义时进入同一单次30秒重试。

## 4. 为什么不把 Relay 设成全局 primary

1. 现役 HiThink/FTShare/Eastmoney/HKEX/NBS 已有长期身份、历史、恢复和消费者合同，切换 primary 会制造迁移风险而没有对应收益。
2. Relay 本身是多上游中转，同名接口可能来自不同 provider；它最适合**补缺、冗余、扩展和按需研究**。
3. 对公告、财报、统计发布，官方原件仍承担最高的“原文/版本/时点”解释责任；Relay 的结构化字段只是 Data。
4. Smart Money 当前真实缺口恰好与 Relay 的专长重合，所以第一生产接点放在这里，收益最高且不需要改现有 canonical history。

## 5. 第一生产接点

radar-smart-money 保留现有主采不变，在同一合格 capture run 后追加一个**独立可失败的 Relay supplement artifact**。它只消费主采已确认的最近完成交易日，不自己猜交易日。显式`relay-only`维护沿第8节复用精确已保存主采原件，不为新增补充重复请求原12类来源。

初始固定接口：
- hm_list：正式名录，__probe=0；
- hm_detail：该完成交易日的游资明细；
- report_rc：本次实际取得日及此前6个日历日的结构化预测记录；报告日与目标季度分别保留，不把记录自动命名为修订；
- top_list / top_inst：龙虎榜交叉检查。

每个接口单独保存原响应和请求/排队回执；一个接口排队不吞其他接口。Relay supplement 不写进现有 137k canonical Smart Money history，不重命名原来源，不成为综合“聪明钱分数”。正常 publisher 把 supplement 的结构化结果和原 artifact locator 放进同一 research.smart_money details，Hosted Quick 可按需读取。

stk_surv 与 research_report 暂不做全市场定时扫描：它们更适合 Hosted Quick / C1 对具体公司或机构做有界追查。B1 的全球行情/宏观候选也沿同一 client 复用，但按各自接口资格另接消费者，不反向扩 Smart Money workflow。

## 6. 退出与替换

Relay 关闭或质量下降时，删除其 caller、secret引用、专属 tests 与 supplement reader；现有 HiThink/FTShare/Eastmoney/HKEX/NBS/TDX 等不受影响。已保存 relay 原件、历史 read-model 与研究引用保留，不改写为从未存在。

没有新增持续订阅费用（Human已自行取得该服务）；没有新增数据库、provider registry、scheduler、评分、自动Full/Odds/交易。


## 7. 已保存原件的解释合同（2026-09-26增量）

补充表格的取得状态、可解析行、日期/证券身份合格行和覆盖缺口分别保留。既有请求客户端及原始capture hash不改写；新的`interpretation_revision`只表示同一原件的后继解释，不是新采集。小数复用原有Decimal/canonical表示，原JSON字节不变；新增列和envelope/data/row各层实际source/provider声明不丢弃，不把中转名冒充独立上游。

同名重复列、错误API、矛盾count或业务错误不能变成有效表；日期或证券身份有问题的行保留原值及行号，不进入合格行。机构`side`空值保留为字段缺口，不猜买榜/卖榜，也不丢掉可用的金额和营业部资料。不同上榜原因、重叠窗口、机构专用与具名身份仍不合并。

官方hm_list单次1000、hm_detail单次2000、report_rc单次3000，top_list/top_inst单次10000；旧Relay请求limit=5000不证明它突破了上游限制。新计划分别使用1000/2000/3000，两个龙虎榜接口维持5000。解释采用请求limit与官方单次界限中较小者作为截断警告，不自行追加请求或宣称全量。返回count大于保存行数另报缺口；count相等也不是全市场完整证明。空页不是没有资本行为。

真实旧复测36230932993/artifact10901553881：44份原body的bytes/SHA256及外ZIP CRC已核。两个龙虎榜接口各5行是受限样本；top_inst这5行side均空，金额/身份/日期仍可读。该次hm_list/hm_detail/report_rc为排队失败，不用后来的复测成功改写它；这不是本轮新取数或完整生产验收。

官方接口合同：Tushare文档311、312、292、106、107。report_rc官方更新时钟为交易日21:15与次日09:15；旧Relay capability文本另称19—22点，二者是不同声明。现有17:20/20:10执行与预测更新时间并不等价。这一阶段仅交付离线解释。迟到窗口、服务级停止和免重复主采的补取由第8节后继实现；真正分页以及更广市场完整性仍未由单页返回建立。

此解释仅使用原件与标准库和既有canonical工具；不新增HTTP实现、凭证入口、provider路由、定时或费用。退出时随Relay消费者一并移除解释模块及专属回归，保留原件、旧解释和研究引用。


## 8. 原客户端保留与有界采集接续（计划revision 2）

**Reuse Decision: KEEP原有限HTTP客户端，THIN_ADAPTER既有capture/control/reader。** `tushare_relay.py`继续使用原blob `d2ee02a81648eafe7204a47e7f8e41b56c3c48fd`，不替换请求、地址、凭证、TLS或重试实现。上次平台拦截的新客户端没有重试或移到别处重建。旧“必须更换客户端才能继续”的前提由实际职责分离及测试撤销，不把一次被拦截的动作扩大成GitHub全仓没有写权限。

现有采集器在第一次请求前、每个接口后、完成时保存manifest检查点。401/403/429、明确鉴权/限流状态或无法取得安全请求回执时，停止本服务本轮后续接口；已取得原件保留，未调用项明确标记，异常消息和反射凭证不公开。无法取得请求回执时实际HTTP次数UNKNOWN，不填0。旧客户端的单次30秒临时队列重试不扩大为重复轮询。

新`plan_revision=2`只影响后继采集：report_rc查询实际取得日及此前6个日历日，交易榜单仍查询经主采确认的交易日。实际报告期、披露日、取得日和中转更新时间互不替代。manifest绑定精确主采identity/capture_hash/cutoff/trading_sessions；新补充属于当前执行身份，旧主采保持原运行/代码/截止。旧无revision的manifest及其单日请求按revision1原样重放，原hash不重命名。

维护输入`relay-only=true`必须是显式workflow_dispatch、给出当前已通过独立main CI的`code-sha`，有固定R内原state，并且不同时请求`repair-pending`。现有控制器只选该state明确登记的`last_source_run_id`，核其原件artifact唯一性、run/head/digest/大小/时间；原生download-artifact以精确artifact ID和run ID取得。Relay实际执行前再次离线重放原件；正常publisher再次核新旧身份、主采日历与补充manifest。不改原canonical history，不把旧价格或交易日标为新取得。

原主采每日三次调用上限不放宽。Relay-only额外按当天**实际已启动Relay job**计数，跨代码版本不归零，累计最多3次；未开始、skipped或仅主采控制的run不是已做Relay请求。库存/身份读取不完整时停止，而不是重置配额。原有两次工作日日程和并发隔离保持，不新增午夜/晨间任务。

正常采集使用同run主原件，显式维护使用上述唯一旧原件。源作业、正常发布、固定R读取与有用研究消费必须分别实测；fixture、成功退出或300余项相关回归不能代替这些。单页达到上限、返回日期/字段缺口、机构side未知、未公开身份与自然可靠性继续可见。关闭Relay时一起移除其caller、专属解释/reader/control分支、workflow接点与测试，保留旧原件、历史解释及研究引用；原12族继续运行。
