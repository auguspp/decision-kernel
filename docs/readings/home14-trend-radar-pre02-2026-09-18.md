# HOME-14 趋势雷达｜真实保存样稿与 pre-0.2 范围

整理日：2026-09-18（UTC+08:00）。状态：**FIRST SAMPLE / REQUIREMENTS & REUSE REVIEW；不是每日产品已部署**。这是 #351 HOME-14 中 Trend Radar 的局部迭代，不把整个 Decision Home pre-0.1 升级为已批准实施。

## 1. Human 批准与排期纠正

Human 指出：“但是实际上我更想要 351 里面提到的那个趋势雷达”，随后批准：“同意，做吧”。本轮范围和优先级登记于 [#351/5721629641](https://github.com/auguspp/decision-kernel/issues/351#issuecomment-5721629641)，同步于 [#297/5721637350](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5721637350)。

**下一主产品方向是连续趋势阅读，不是先扩概念池，也不是先做完整 Home。** #364 以后补覆盖；#297 必要主线修复及 P0-7 观察并行。全部报错清零、全仓整理、积满全部观察天数，不是本产品的共同前置。

本轮交付：真实保存数据样稿、多方案横向对照、字段/来源地图、复用能力与缺口、下一最小切片。没有新市场抓取、workflow dispatch/Re-run、模型研究、Odds、提醒启用或交易；Investment Authority = NONE。

## 2. 精确输入与证明范围

| 项目 | 固定身份 |
|---|---|
| main / M | `480fd447c02f091967ae2cebb64a354a960a4f9c` |
| read-model / R | `ac23c61446d7a7001c3ceb82d345d30a31fa5c84` |
| 市场交易日 | **2026-09-17**；不是9/18行情 |
| Sector producer | `35209312183`；origin code `67701b4debd3b82971b78aa9650541f3f91b584a` |
| context Git blob | `8d93faeb3b3bd5250b1e7be1c80a24e530587147` |
| result Git blob | `338896d623f46642bef68e9ef03a269772a054ed` |
| 保存状态 hash | `7b2c8d085bdba16dc128a1b9236bd481f4026bbbbbf43134209ff71c5084a218` |
| context SHA256 | `1d333c6c6a52b42d6bb53cf4d17cfff3f504fd99be6330944430d2306c8ff71b` |
| result SHA256 | `a40690837a9bc12e6e8447305a81b51dc2837ee80018118d76e26d294be51aa2` |

输入复用本会话已有 `stock-reading-35210443356-1.zip` 内的同 Sector 保存副本。逐文件计算 Git blob hash，与本轮从固定 R 读取的两个 blob 一致；日期、基准、`context.market_state_hash == result.output_market_state_hash` 一致。不是因为 Stock zip 存在就推导 Stock 资格。

本轮独立检查原件字节身份、绑定、完整集合与显示算术；**未执行原 canonical validator，未独立重算整个 reading_hash，未重新认证上游行情真伪**。样稿消费保存 Sector 产物，不替换其资格判断。Stock lane 的 `stock reading identity or authority differs` 仍明示，不升级为本轮合格个股路径。

原件：[完整context](https://github.com/auguspp/decision-kernel/blob/ac23c61446d7a7001c3ceb82d345d30a31fa5c84/details/sector/35209312183/context/context.json) · [同日result/宽度](https://github.com/auguspp/decision-kernel/blob/ac23c61446d7a7001c3ceb82d345d30a31fa5c84/details/sector/35209312183/result.json) · [原新事件摘要](https://github.com/auguspp/decision-kernel/blob/ac23c61446d7a7001c3ceb82d345d30a31fa5c84/details/sector/35209312183/summary.md)。均固定版本，不使用latest。

## 3. 样稿：现在什么状态，而不是只看今天新触发

**9/17保存结构：元件/印制电路板处于各自层级20日相对领先位置；种植业与林业仍满足条件但近期弱化；被动元件进入加速条件，却不是当日普涨。** 这些是市场表达，不是受益原因或买入判断。

| 分层范围 | 已覆盖节点 | 当前条件有效 | 其中当天无新事件 | 近期弱化 | 任一原条件退出 | 有效且弱化 |
|---|---:|---:|---:|---:|---:|---:|
| 宽行业881 | 90 | 9 | **7** | 41 | 3 | 1 |
| 细分行业884 | 230 | 25 | **16** | 106 | 8 | 2 |

这些是重叠阅读维度，不是互斥市场阶段。不能把9+41+3当成不同对象数。881/884是重叠分类层级，不混排，不加权汇成全A市场强度。

原事件层是 **11个新事件、10个变化组**。状态层中，宽行业7个、细分行业16个当前有效节点没有当天新事件；只看新增事件不能替代趋势总览。

### 六个阅读验收例子（人工选例，不是新增top6筛选）

超额与其变化单位为**个百分点**；“5日变化”是滚动20日超额与5个交易日前的差，不是未来加速预测。各数字分别从原始未舍入字段格式化，不用两个已舍入数字相减反推。

| 方向 | 5日超额 | 20日超额 | 20日行业自身收益 | 20日超额的5日变化 | 正20日超额连续期 | 应怎样读 |
|---|---:|---:|---:|---:|---:|---|
| 元件 `881270.TI` | +9.30 | +22.18 | +19.29% | +9.36 | 27交易日 | 20日宽行业第1；条件持续、当天无新事件；成员宽度未采集 |
| 印制电路板 `884092.TI` | +10.53 | +27.22 | +24.34% | +9.99 | 25交易日 | 20日细分第1；条件仍有效，同时另一个原条件退出；当天无新事件 |
| 种植业与林业 `881101.TI` | -4.46 | +12.21 | +9.32% | -18.06 | 41交易日 | 仍满足条件，同时近期弱化；不是趋势已结束或基本面恶化 |
| 被动元件 `884093.TI` | +5.73 | +8.34 | +5.46% | +7.69 | 6交易日 | 新入加速；当日指数-2.06%、上涨仅1/16；不等于当日普涨 |
| 其他酒类 `884119.TI` | +4.83 | +12.00 | +9.11% | +3.77 | 46交易日 | 新入加速；当日7/9上涨，对当日参与有支持，不证明历史扩散 |
| 乘用车 `884099.TI` | +4.36 | +4.69 | +1.81% | +4.07 | 8交易日 | 新入加速；上涨7/已定价9、全部成员10，缺失1，不冒充完整7/9覆盖 |

文档对账修订：首稿中被动元件/乘用车绝对20日收益的+5.45%/+1.80%是显示舍入反推错误，现按原 `sector_return` 修正为+5.46%/+1.81%。本地HTML一直从原字段直接格式化，原件、算法和HTML未改变。

保存沪深300的5/20/60日自身收益分别约-1.94%/-2.89%/-11.15%。因此必须并列绝对收益与超额；正超额不必然是绝对上涨。连续正20日超额也不等于连续上涨。

### 首版发现的真实数据缺口

只有**11/320行业节点**有同日宽度记录，恰为原事件候选；其他309个节点本轮未提供宽度。当前有效的34个节点中，23个没有同日宽度（宽行业7、细分16）。这是节点覆盖计数，不是去重证券覆盖或市场广度。

最重要的后续数据问题是：**怎样对持续关注、但没有新事件的方向保留有界成员宽度与领导结构覆盖？** 不是再加一个强弱综合分。

首版只展示已有同日上涨/下跌/平盘、已定价/全部成员、缺失数和当日突出成员。不用当前成员倒灌历史，不把当日涨幅leader称为多日龙头；缺成员权重和历史归因时不声称指数由某几只贡献或资金在撤离。

### 连接已有业务解释，不补写原因

[会稽山601579.SH](https://github.com/auguspp/decision-kernel/blob/ac23c61446d7a7001c3ceb82d345d30a31fa5c84/sources/git/46aeb73b396295952fedcd37dd74b4583aefc885/failure.json) 与 [艾华集团603989.SH](https://github.com/auguspp/decision-kernel/blob/ac23c61446d7a7001c3ceb82d345d30a31fa5c84/sources/git/48bfffbbead593c76cf260cb2c7409cbda34b5bf/failure.json) 的9/17业务基线停在SOURCE_PREPARATION，Pre/Quick未执行。本页连接精确旧失败，不称新研究，也不因此否定行业市场观察。

## 4. 横向比较：取可用原则，不复制终端

查阅日2026-09-18。公开官方文档/接口说明与仓库能力比较；未登录付费产品、实测接口、完整审计代码/许可证或验证投资增量。不宣称完成整个HOME-14的超短/龙虎榜/Smart Money调研。

| 样本与已核实事实 | 本轮处置 | 对本项目的具体含义 |
|---|---|---|
| StockCharts官方RRG用相对强度与其动量、历史尾迹组织阅读，并明确不是交易系统。[E1] | ADOPT PRINCIPLE；实际算法作为CHALLENGER | 借水平与变化分开及轨迹表达；本项目收益差/变化不冒充JdK RS-Ratio/Momentum或RRG，不预设必然顺时针轮动 |
| FINVIZ Groups提供多窗口可排序表现表和组别sparkline。[E2] | ADOPT PRINCIPLE | 完整层内窗口浏览与少量历史展开，保留全量入口，不只留当天前三个，不当买入榜 |
| TradingView官方Heatmap允许选择分组、色值、面积参数及等大单元模式。[E3] | ADOPT PRINCIPLE；不嵌外部行情作canonical数据 | 解释颜色/面积/窗口；市值大不等于广度大。首版不以单日日涨幅色块代表趋势 |
| Koyfin官方相对表现说明区分价格比值A/B与收益差%A-%B。[E4] | ADOPT PRINCIPLE | 沿用本项目行业收益减基准收益；百分比/百分点不混写，不偷换原指标 |
| OpenBB官方groups接口有group/metric/provider/warnings，并明确US-listed stocks与FINVIZ provider。[E5] | REUSE CANDIDATE（接口形状）；不采用依赖 | 可借分组与警告共存；不是881/884替代源，不引入整个平台 |
| AKShare文档列出东方财富行业快照、成分、历史接口，含上涨家数、当前成分与adjust参数。[E6] | REUSE CANDIDATE（未来来源缺口） | 比较字段，不混同BK与TI分类身份；快照不证明历史成员/PIT/实际可用。本轮不切换HiThink、不请求该接口 |
| EasyStock原讨论样本 | 本轮身份待定位，保留待复查 | HOME-14记录只给项目名，本轮仓库代码搜索及公共检索未定位可确认的原URL/commit；不同名替代，不虚构已审代码/许可证 |

结论：采用**多窗口并列、状态与事件分离、水平与变化分离、同对象展开、覆盖率同屏**。不引入综合分、买卖阶段模型、provider框架或第二状态库。

[E1]: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-types/relative-rotation-graphs-rrg-charts
[E2]: https://finviz.com/knowledge-base/market-data-research/maps-groups/group-views-performance
[E3]: https://www.tradingview.com/widget-docs/widgets/heatmaps/stock-heatmap/
[E4]: https://www.koyfin.com/help/relative-performance-relative-strength/
[E5]: https://docs.openbb.co/odp/python/reference/equity/compare/groups
[E6]: https://akshare.akfamily.xyz/data/stock/stock.html

## 5. 现有能力与字段地图

现有 [sector-radar-read-only-context.md](https://github.com/auguspp/decision-kernel/blob/480fd447c02f091967ae2cebb64a354a960a4f9c/docs/sector-radar-read-only-context.md) 已定义完整状态与分窗口浏览，已有renderer和回归。**这些不是待建设的新趋势引擎。**

| 问题 / 字段 | 当前可复用 | 尚缺 / 使用边界 |
|---|---|---|
| 谁领先 | context分层5/20/60日行业/基准/超额与rank | 窗口/基准/单位同屏；不混两层rank |
| 强势是否仍在 | persistent/acceleration的previous/current、currently_gate_active | 当前有效不等于今天起涨或买入信号 |
| 最近增强/减弱 | 20日超额及rank的5日变化、原recent_weakening | 原weakening为两个负变化合取，不能改成一个负变化 |
| 持续多久 | 正20日超额/前四分位持续期、left-censor | 左截断用至少；首次事件/首次观察/起点分开 |
| 当日参与宽度 | 同日同state result.breadth_observations | 11节点有记录；历史扩散需当时成员与连续观测 |
| 谁带动 | 同日leaders/laggards、原成交额集中度 | 单日排序不是多日龙头/权重贡献；全成员多日历史尚缺 |
| 为什么值得研究 | Stock/Research按公司/问题/版本的原记录 | 本R Stock读取拒绝；不得升级。业务解释缺失为UNKNOWN |
| 阶段与轮动 | 前后gate及已有变化字段 | 形成/扩散/分化/退潮尚无获准可检验定义；多日历史产品未完成 |
| 机构关注/资本行为 | HOME-14后续需求已登记 | 本样稿NOT COLLECTED，不是假零、不合成总分 |

## 6. pre-0.2最小产品定义

第一屏回答：持续关注哪些方向、最近怎样变化、参与是否广、哪些公司可继续看及业务解释缺口。先A股盘后、881/884、同R只读；概念/主题以后独立扩覆盖。

**T-01 连续可见。** 无新事件的方向仍可按完整层内窗口榜或状态找到；阅读不创建事件。

**T-02 水平与变化分离。** 20日超额及其5日变化并列，保留自身收益；无综合分，不把相对领先叫便宜。

**T-03 状态可重叠。** 当前有效、近期弱化、某条件退出显示原谓词；不随意贴阶段标签。

**T-04 宽度有分母。** 上涨/已定价/全部成员/缺失同屏；只消费同日同源合格结果，未观测不显示0。

**T-05 领导结构不偷换。** 首版当日突出成员与已有独立合格多日路径分别显示；全行业多日龙头/接力/权重贡献缺失则明示。

**T-06 时间可追溯。** 市场日、观察/生成时钟、首次事件与持续期分开；跨日比较按当时版本/分类，不以后见历史冒充当时已告警。

**T-07 连接研究。** 精确公司/问题/版本链接，区分未执行、研究WAIT、需新证据和数据失败；价格不改变Belief。

**T-08 可替换阅读层。** 复用既有context renderer、result及fixed reading。缺Stock/Research不让独立合格Sector状态消失；失败可见。无新采集器/调度器/canonical registry/状态机。

## 7. 下一最小实施切片

**Reuse Decision: REUSE + THIN PRESENTATION COMPOSITION。** 新生成器只是本地一次性样稿，不进入runtime/workflow/日常发布，不固化成第二renderer。下一生产实现应扩展现有 `sector_radar_context.py`/既有读取渲染接点。

建议切片：在已验证context上组合经同run/交易日/state身份验证的已有breadth结果，增加紧凑总览和方向详情内的覆盖/成员/研究连接，在现有交付入口可发现。保留原计算、事件集合、输入hash与失败语义；施工前确认最小函数接点及必要新回归，复用已有测试。

数据补充独立评审：持续方向的有界breadth、历史成员保留、多日个股领导结构。先核对现有预算/来源成本，比较已有采集复用与少量明确关注对象，不默认每天全行业全成员补抓。历史回看不补造前瞻事件。机构调研/Smart Money、超短/竞价/龙虎榜仍属后续同轨调研，不阻塞首版；#364以后扩独立概念宇宙。

阶段算法CHALLENGER仅做标注/回放研究：检验稳定性、翻转率、相对现有5/20/60的增量信息及Human可读性；不为已知样本调门槛，不默认自动交易。

## 8. 验收与剩余工作

本地离线HTML包含全部320节点、881/884切换、5/20/60保存排名切换、名称/代码搜索、重叠状态筛选、方向详情、同日已有breadth及精确原件链接。输入为两个不变原件，无新市场算法。

17项呈现检查已通过：确定性、320行完整、两层分离、默认90行、原20日rank1、窗口切换、重叠状态1/2、名称搜索/无匹配、1/16宽度、309未观测、跨层详情、1280px/390px无页面横向溢出、脚本错误0、自动网络请求0。使用本地Chromium+Playwright独立页面set_content；不是GitHub已登录下载或用户设备认证，不是全仓CI/canonical validation。中途QA装载方式的同页面重复const声明已改为独立页面，最终重新通过；HTML字节未变。

HTML SHA256：`cfd9b4b1bf54e96d1d97ec062f48e734d4105fa768a3c2dacef47e750dc63194`。完整HTML、生成器、输入副本、QA与manifest随聊天交付；本文件和固定R原件是GitHub中的需求/样稿证据。**这里只记录本地HTML指纹，不声称其原字节已成为Git blob。**

Human阅读验收PENDING：能否在30–60秒分辨持续强势/新事件、强中弱化、相对抗跌/绝对上涨、当日宽度/历史扩散、单日成员/多日龙头，并不用读日志就找到下一问题。程序检查不能替代此验收。

第一份样稿和范围定义完成，不等于整个HOME-14或每日趋势雷达完成。现有源/读取故障另留原责任，不以样稿覆盖失败，不宣称全面健康。
