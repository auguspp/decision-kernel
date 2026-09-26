# Data Source Orchestration v1｜来源职责而不是全局主备表

日期：2026-09-26。Authority：#297/5845050149。Human要求把已购第三方 Tushare Relay 接入并重新梳理现有数据源。本文是工程编排合同，不是第二需求库、数据真伪评分或自动 provider router。Evidence changes Belief；Price changes Odds；Data != Evidence != Judgment != Decision。

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

radar-smart-money 保留现有主采不变，在同一合格 capture run 后追加一个**独立可失败的 Relay supplement artifact**。它只消费主采已确认的最近完成交易日，不自己猜交易日。

初始固定接口：
- hm_list：正式名录，__probe=0；
- hm_detail：该完成交易日的游资明细；
- report_rc：该日公开结构化预测修订；
- top_list / top_inst：龙虎榜交叉检查。

每个接口单独保存原响应和请求/排队回执；一个接口排队不吞其他接口。Relay supplement 不写进现有 137k canonical Smart Money history，不重命名原来源，不成为综合“聪明钱分数”。正常 publisher 把 supplement 的结构化结果和原 artifact locator 放进同一 research.smart_money details，Hosted Quick 可按需读取。

stk_surv 与 research_report 暂不做全市场定时扫描：它们更适合 Hosted Quick / C1 对具体公司或机构做有界追查。B1 的全球行情/宏观候选也沿同一 client 复用，但按各自接口资格另接消费者，不反向扩 Smart Money workflow。

## 6. 退出与替换

Relay 关闭或质量下降时，删除其 caller、secret引用、专属 tests 与 supplement reader；现有 HiThink/FTShare/Eastmoney/HKEX/NBS/TDX 等不受影响。已保存 relay 原件、历史 read-model 与研究引用保留，不改写为从未存在。

没有新增持续订阅费用（Human已自行取得该服务）；没有新增数据库、provider registry、scheduler、评分、自动Full/Odds/交易。
