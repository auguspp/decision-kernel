# HOME-14 趋势雷达｜真实保存样稿与 pre-0.2 范围

整理日：2026-09-18（UTC+08:00）。状态：**FIRST SAMPLE / REQUIREMENTS & REUSE REVIEW；不是每日产品已部署**。这只是 #351 HOME-14 中 Trend Radar 的局部迭代，不把整个 Decision Home pre-0.1 升级为已批准实施。

## 1. Human 批准与排期纠正

Human 指出：“但是实际上我更想要 351 里面提到的那个趋势雷达”，随后批准：“同意，做吧”。本轮范围和正式优先级已登记于 [#351/5721629641](https://github.com/auguspp/decision-kernel/issues/351#issuecomment-5721629641)，并同步 [#297/5721637350](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5721637350)。

**下一主产品方向是连续趋势阅读，不是先扩概念池，也不是先做完整 Home。** #364 以后补覆盖；#297 必要主线修复及 P0-7 观察并行。全部报错清零、全仓整理、积满全部观察天数，不是本产品的共同前置。

本轮交付：真实保存数据的阅读样稿、多方案横向对照、字段/来源地图、可复用能力及剩余缺口、下一最小切片。没有市场抓取、workflow dispatch/Re-run、模型研究、Odds、提醒启用或交易；Investment Authority = NONE。

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

实际输入复用本会话已有 Stock archive `stock-reading-35210443356-1.zip` 内的同 Sector 保存副本。逐文件计算 Git blob hash，与本轮从固定 R 读取的上述两个 blob 一致；日期、基准、`context.market_state_hash == result.output_market_state_hash` 一致。不是因为 Stock zip 的存在就推导 Stock 资格。

本轮独立检查的是原件字节身份、绑定、完整集合与显示算术；**未执行原 canonical validator，未独立重算整个 reading_hash，未重新认证上游行情真伪**。样稿消费的是已保存 Sector 产物，不替换其资格判断。Stock lane 已有 `stock reading identity or authority differs` 仍明示，不升级为本轮合格个股路径。

原件：[完整context](https://github.com/auguspp/decision-kernel/blob/ac23c61446d7a7001c3ceb82d345d30a31fa5c84/details/sector/35209312183/context/context.json) · [同日result/宽度](https://github.com/auguspp/decision-kernel/blob/ac23c61446d7a7001c3ceb82d345d30a31fa5c84/details/sector/35209312183/result.json) · [原新事件摘要](https://github.com/auguspp/decision-kernel/blob/ac23c61446d7a7001c3ceb82d345d30a31fa5c84/details/sector/35209312183/summary.md)。这里的链接已经固定版本，不使用 latest。

## 3. 样稿：现在什么状态，而不是只看今天新触发

**9/17 的保存市场结构：元件/印制电路板处于各自层级20日相对领先位置；种植业与林业仍满足条件但近期弱化；被动元件进入加速条件，却不是当日普涨。** 这些是市场表达，不是受益原因或买入判断。

| 分层范围 | 已覆盖节点 | 当前条件有效 | 其中当天无新事件 | 近期弱化 | 任一原条件退出 | 有效且弱化 |
|---|---:|---:|---:|---:|---:|---:|
| 宽行业881 | 90 | 9 | **7** | 41 | 3 | 1 |
| 细分行业884 | 230 | 25 | **16** | 106 | 8 | 2 |

这些是重叠阅读维度，不是互斥市场阶段。不能把9+41+3当成不同对象数。881/884是重叠的分类层级，不混排，不加权汇成全A市场强度。

原事件层是 **11个新事件、10个变化组**。状态层中，宽行业7个、细分行业16个当前有效节点没有当天新事件；这说明只看新增事件不能替代趋势总览。

### 六个阅读验收例子（人工选例，不是新增top6筛选）

所有超额与其变化单位为**个百分点**；“5日变化”是滚动20日超额与5个交易日前的差，不是未来加速预测。

| 方向 | 5日超额 | 20日超额 | 20日行业自身收益 | 20日超额的5日变化 | 正20日超额连续期 | 应怎样读 |
|---|---:|---:|---:|---:|---:|---|
| 元件 `881270.TI` | +9.30 | +22.18 | +19.29% | +9.36 | 27交易日 | 20日宽行业第1；条件持续、当天无新事件；成员宽度未采集 |
| 印制电路板 `884092.TI` | +10.53 | +27.22 | +24.34% | +9.99 | 25交易日 | 20日细分第1；条件仍有效，同时另一个原条件退出；当天无新事件 |
| 种植业与林业 `881101.TI` | -4.46 | +12.21 | +9.32% | -18.06 | 41交易日 | 仍满足条件，同时近期弱化；不是趋势已结束或基本面恶化 |
| 被动元件 `884093.TI` | +5.73 | +8.34 | +5.45% | +7.69 | 6交易日 | 新入加速；当日指数-2.06%、上涨仅1/16；不等于当日普涨 |
| 其他酒类 `884119.TI` | +4.83 | +12.00 | +9.11% | +3.77 | 46交易日 | 新入加速；当日7/9上涨，对当日参与有支持，不证明历史扩散 |
| 乘用车 `884099.TI` | +4.36 | +4.69 | +1.80% | +4.07 | 8交易日 | 新入加速；上涨7/已定价9、全部成员10，缺失1，不冒充完整7/9覆盖 |

保存沪深300的5/20/60日自身收益分别约-1.94%/-2.89%/-11.15%。因此页面必须并列绝对收益与超额；正超额不必然是绝对上涨。连续正20日超额也不等于连续上涨。

### 首版发现的真实数据缺口

只有**11/320行业节点**有同日宽度记录，恰为原事件候选；其他309个节点本轮未提供宽度。当前有效的34个节点中，23个没有同日宽度（宽行业7、细分16）。这是节点覆盖计数，不是去重证券覆盖或市场广度。

所以，把趋势全部展示出来之后，最重要的新增数据问题是：**如何对持续关注、但没有新事件的方向保留有界的成员宽度与领导结构覆盖？** 不是再添加一个强弱综合分。

首版只展示已有同日上涨/下跌/平盘、已定价/全部成员、缺失数和当日突出成员。不用当前成员倒灌历史；不把当日涨幅leader称为多日龙头；没有成员权重和历史归因时不使用“指数由某三只贡献”或“资金在撤离”的结论。

### 连接已有业务解释，不补写原因

[会稽山601579.SH](https://github.com/auguspp/decision-kernel/blob/ac23c61446d7a7001c3ceb82d345d30a31fa5c84/sources/git/46aeb73b396295952fedcd37dd74b4583aefc885/failure.json) 与 [艾华集团603989.SH](https://github.com/auguspp/decision-kernel/blob/ac23c61446d7a7001c3ceb82d345d30a31fa5c84/sources/git/48bfffbbead593c76cf260cb2c7409cbda34b5bf/failure.json) 的9/17业务基线都停在SOURCE_PREPARATION，Pre/Quick未执行。本页连接精确旧失败，不称新研究，也不因旧失败否定行业市场观察。

## 4. 横向比较：取可用原则，不复制终端

查阅日2026-09-18。本轮是公开官方文档/接口说明与当前仓库能力比较，未登录外部付费产品、实测接口、进行完整代码/许可证审计或验证投资增量；不宣称完成整个HOME-14的超短/龙虎榜/Smart Money调研。

| 样本与已核实事实 | 本轮处置 | 对本项目的具体含义 |
|---|---|---|
| StockCharts官方RRG：用相对强度与其动量、历史尾迹组织多证券阅读，并明确不是交易系统。[E1] | ADOPT PRINCIPLE；实际算法作为CHALLENGER | 借“水平与变化分开”及轨迹表达；不把本项目收益差/变化直接命名为JdK RS-Ratio/Momentum或冒充RRG，不预设必然顺时针轮动 |
| FINVIZ Groups：提供多窗口可排序表现表和组别sparkline。[E2] | ADOPT PRINCIPLE | 完整层内窗口浏览、少量历史展开；保留全量入口，不只留当天前三个；不把表现表当买入榜 |
| TradingView官方Heatmap：允许选择分组、色值、面积参数及等大单元模式。[E3] | ADOPT PRINCIPLE；不嵌外部行情作canonical数据 | 热图必须解释颜色/面积/窗口；市值大不等于广度大。首版先把字段与覆盖说清，不以一个日涨幅色块代表趋势 |
| Koyfin官方相对表现说明区分价格比值A/B与收益差%A-%B。[E4] | ADOPT PRINCIPLE | 保留本项目已定义的行业收益减基准收益；百分比与百分点不能混写，换表达法必须声明，不能偷换原指标 |
| OpenBB官方groups接口有group/metric/provider/warnings，文档明确US-listed stocks与FINVIZ provider。[E5] | REUSE CANDIDATE（接口形状）；当前不采用依赖 | 可借透明分组与警告共存；不把美股行业数据接口当作已有881/884替代源，不引入其整个平台 |
| AKShare官方文档列出东方财富行业快照、成分、历史接口，分别含上涨家数、当前成分与adjust参数。[E6] | REUSE CANDIDATE（未来来源缺口） | 公共库可做字段比较，不直接混同BK与TI分类身份；当前快照不证明历史成员、PIT或本环境实际可用。首版不切换HiThink、不请求该接口 |
| EasyStock原讨论样本 | 本轮身份待定位，保留待复查 | 当前HOME-14记录只给出项目名，本轮仓库代码搜索及公共检索未定位到可确认的原项目URL/commit；不拿同名库存软件或其他股票项目替代，不虚构已审代码/许可证 |

本轮结论：优先采用**多窗口并列、状态与事件分离、水平与变化分离、同对象展开、覆盖率同屏**。不引入外部综合分、买卖阶段模型、provider框架或第二状态库。

[E1]: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-types/relative-rotation-graphs-rrg-charts
[E2]: https://finviz.com/knowledge-base/market-data-research/maps-groups/group-views-performance
[E3]: https://www.tradingview.com/widget-docs/widgets/heatmaps/stock-heatmap/
[E4]: https://www.koyfin.com/help/relative-performance-relative-strength/
[E5]: https://docs.openbb.co/odp/python/reference/equity/compare/groups
[E6]: https://akshare.akfamily.xyz/data/stock/stock.html

## 5. 现有能力与字段地图

现有 [sector-radar-read-only-context.md](https://github.com/auguspp/decision-kernel/blob/480fd447c02f091967ae2cebb64a354a960a4f9c/docs/sector-radar-read-only-context.md) 已定义完整状态与分窗口浏览，已有renderer和回归。**不能把这些重新列为待建设的趋势引擎。**

| 问题 / 字段 | 当前可复用 | 尚缺 / 使用边界 |
|---|---|---|
| 现在谁领先 | context各层5/20/60日行业/基准/超额及rank | 窗口、基准、单位同屏；不混两层rank |
| 强势是否仍在 | persistent/acceleration的previous/current、currently_gate_active | 当前有效不等于趋势从今天开始，也不等于已持续买入信号 |
| 最近增强还是减弱 | 20日超额的5日变化、20日rank的5日变化、原recent_weakening | recent_weakening是原两个负变化的合取，不能将单一负超额变化偷偷升级为相同flag |
| 持续多久 | 正20日超额及前四分位持续期、left-censor | 有左截断用“至少”；账本首次事件、系统首次观察与趋势起点分开 |
| 当日参与宽不宽 | 同日同state result.breadth_observations | 当前11节点有记录；其余缺失。历史扩散需要当时成员与连续观测 |
| 谁在带动 | 同日leaders/laggards、成交额集中度等原字段 | 当日表现排序不是多日龙头或贡献归因；缺全成员合格多日历史，不造角色分数 |
| 为什么值得研究 | 既有Stock/Research按公司和问题绑定的原记录 | 本R Stock读取拒绝；不得升级。业务解释缺失就是UNKNOWN |
| 趋势阶段/轮动轨迹 | 当前/前一日gate及既有变化字段 | “形成/扩散/分化/退潮”尚无获准可检验定义；阶段分类和多日历史产品未完成 |
| 机构关注与资本行为 | HOME-14后续需求已登记 | 本样稿NOT COLLECTED，不是假零、不合成聪明钱总分 |

## 6. pre-0.2最小产品定义

第一屏回答：当前持续关注哪些方向、最近怎样变化、参与是否广、有哪些可继续看的公司及业务解释缺口。先A股盘后、既有881/884、同R只读；概念/主题以后独立扩覆盖。

T-01 连续可见：无新事件的方向仍能按完整层内窗口榜或状态找到；默认阅读不创建事件。

T-02 分开水平与变化：20日超额及其5日变化并列，同时保留行业自身收益；不新增综合分或把相对领先叫便宜。

T-03 状态可重叠：当前有效、近期弱化、某条件退出分别显示原谓词；阶段解释不随意填入。

T-04 宽度有分母：上涨/已定价/全部成员/缺失同屏；宽度只来自同日同源合格结果；未观测不显示0。

T-05 领导结构不偷换：首版只展示当日突出成员及已有独立合格的多日路径；全行业多日龙头、接力、权重贡献尚缺则明示。

T-06 时间可追溯：市场日、观察/生成时钟、首次事件和持续期各自保留；比较不同日期需按当时版本和分类身份，不以后见历史冒充当时已告警。

T-07 连接研究而不制造研究：精确公司/问题/版本链接，区分未执行、已研究WAIT、需新证据和数据失败；价格观察不改变Belief。

T-08 可替换阅读层：复用既有context renderer、result与fixed reading。缺Stock/Research不应让独立合格Sector状态消失；失败必须可见。不要再造采集器、调度器、canonical registry或状态机。

## 7. 下一最小实施切片与后续边界

**Reuse Decision: REUSE + THIN PRESENTATION COMPOSITION。** 这次新生成器仅是本地一次性样稿，不进入runtime、workflow或日常发布，不能固化成第二renderer。下一生产实现应扩展现有 `sector_radar_context.py`/既有读取渲染接点，而不是照搬样稿另立系统。

建议下一切片：在已验证context上组合经同run/交易日/state身份验证的已有breadth结果，增加紧凑总览与方向详情内的覆盖/成员/研究连接，并在现有交付入口可发现。保留原计算、原事件集合、原输入hash及失败语义。施工前确认最小函数接点，明确哪些新回归必要；已有回归不重写。

数据补充独立评审：持续方向的有界breadth覆盖、历史成员保留、多日个股领导结构。先量化现有预算和来源成本，比较复用既有采集与少量明确关注对象，不默认每天全行业全成员补抓。历史样本可作回看但不得补造前瞻事件。机构调研/Smart Money、超短、竞价、龙虎榜同属后续HOME-14调研，不作为首版阻塞；#364以后扩独立概念宇宙。

阶段算法CHALLENGER只做标注/回放研究，考察稳定性、翻转率、是否提供超出现有5/20/60数据的增量信息与Human可读性；不得为几个已知样本调整门槛并宣布有效，也不默认研究收益率或自动交易。

## 8. 实际验收与剩余工作

本地样稿为可离线阅读HTML：包含320个节点、881/884切换、5/20/60保存排名切换、名称/代码搜索、重叠状态筛选、方向详情、同日已有breadth、精确原件链接。输入是上文两个不变原件；没有新市场算法。

已完成本地17项呈现检查：确定性输出、320行完整性、两层分离、默认90行、原20日rank1、5/20/60切换、重叠状态1/2、名称搜索/空搜索、1/16宽度、309未观测、跨层详情跳转、1280px/390px页面无横向溢出、脚本错误0、自动网络请求0。浏览器为本地Chromium+Playwright set_content；不是GitHub已登录下载路径或用户设备兼容性认证，也不是全仓CI或canonical validation。

原样稿HTML SHA256：`cfd9b4b1bf54e96d1d97ec062f48e734d4105fa768a3c2dacef47e750dc63194`。完整HTML、生成器、输入副本、QA和manifest随聊天交付；本文件及固定R原件是GitHub中的需求/样稿证据。**这里只记录本地HTML指纹，不声称HTML原字节已作为Git blob归档。**

用户阅读验收仍PENDING：能否在30–60秒分辨持续强势与新事件、强中弱化、相对抗跌与绝对上涨、当日宽度与历史扩散、当日突出成员与多日龙头，并无需读日志找到值得继续问的问题。程序检查不能替代这一验收。

完成第一份样稿和范围定义，不等于完成整个HOME-14或每日趋势雷达。现有源/读取故障另留原责任；不以样稿覆盖失败、不宣称系统全面健康。
