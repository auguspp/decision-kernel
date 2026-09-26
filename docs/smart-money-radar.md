# 聪明钱雷达：公开参与者行为，而不是聪明钱评分

当前目标来自 #351/5841579235（Human：把原完整目标做完），承接 #351/5681995870、5696059286、5722424809。不能把 #426 一次机构席位样本或 #504 一次研报消费当成全部交付。Radar 发现、Hosted Quick 解释、Human 决定研究接受、Full 与资本动作。

本文件是实现合同，不是生产验收回执。实际 exact-head CI、合并、源执行、发布、读回和研究消费分别在原 Issue/PR 中记录；自然日常恢复率和投资有效性不能由工程测试证明。

## 1. 完整目标与本次观察面

| 目标 | 现有实现入口与范围 | 不应宣称的东西 |
|---|---|---|
| 游资公开轨迹 | HiThink hot_money 原标签、公司、日期、1/3日窗口和净额；FTShare 原始营业部买卖明细独立保存；初始最近5个实际交易日，后继补已知缺日 | 供应商标签不是本人身份；不同源同金额不是营业部到个人的认证；1/3日重叠不相加；不上榜不证明仍持有或已退出 |
| 机构席位 | 同日 org 原始行及买卖机构数量；不经过 Sector/Stock 强势门槛 | 机构席位不等于某个可识别基金的完整交易或仓位 |
| 北向 | 互联互通成交额/笔数分渠道；HKEX 公布的季度 CCASS 持股，最新公开表与前一已结束季度 | 成交额不是净买；不制造每日个股净买或实时北向持股；CCASS是合计，不是一家外资机构 |
| 具名个人/牛散、基金及其他机构 | 最新两个已结束报告期的前十大流通股东明细，分页核总数；按证券/股类/来源持有人身份对比数量；公司和参与者双向查询 | 不是所有账户、前十外持股或当前仓位；同名只作检索关联，不擅自认证同一自然人；榜单消失不等于清仓；没有名人标签不删除具名自然人 |
| 机构调研 | 最近90日披露窗口，保留实际活动日；先按公司、披露文件和活动日期区间分组，再列参与者与明确机构代码 | 同一活动100参与行不是100场活动；泛称“投资者”不算已识别独立机构；姓名文本不用于编造人数 |
| 研报/预期 | 最近90日全市场列表分页、报告ID与版本；EPS原槽位保留；有界取得原PDF，对正文明确同一指标/目标年的新旧值给出“本报告声明的修订” | 不从列表年度表头或取得时间猜历史目标年；不把不同券商差异当同一预测修订；原文引用旧值不等于旧原模型独立验证；不冒称完整共识 |
| 内部人/股东/公司资本动作 | 高管实际变动、股东披露增减持区间、回购方案ID/计划区间/累计已实施/用途；新旧累计不重复相加 | 计划不等于执行；未核单位字段保留原值不换算；回购不必然等于注销；实际披露不证明动机 |
| 锁定资本 | 定增发行记录、数量价格、披露募集额、认购对象、价格原则、锁定文本 | 发行股份购买资产不等于现金到位；披露募集额不等于独立核验银行收款；没有条款时继续 UNKNOWN |

每一面分别显示 source complete / partial / unavailable / deferred-with-age；同一期还要区别新取得、同ID修订、未变与冲突。完整范围未取得时保留缺口，不能用一个HTTP200、一个工作流绿灯或记录数量代替产品覆盖。

## 2. 实际复用与来源定位

内部复用：现有 HiThink/FTShare 身份、交易日、isolated Requests session、canonical JSON/hash、GitHub Actions、原 current-state publisher、按 Git blob 身份读取与原 Research/Quick 日志。不创建第二个正式状态库、不改 Stock 价格条件、不安装交易框架。

外部协议复用：AKShare 的东方财富股东、股东增减持、机构调研、回购与增发接口字段；现有 institutional-context 的 Eastmoney report/list；HiThink-Tech/Financial-API 的 dragon-tiger-list，FTShare 已批准 gateway 数据接口。使用直接薄适配以保留原始分页响应与来源时钟，不把 DataFrame、营销说明或旧字段目录视为当日实证。Reuse Decision: REUSE + THIN_ADAPTER。

本次已在独立工作分支取得原件的准备运行：36205967276（原源）、36206174933（字段补核）、36207379104（HKEX表和研报PDF）。四份原档案包括历史机构 source35296479748，在36210892160中经实际下载逐包核digest/字节/CRC；原件没有重抓替换。该准备的测试失败仍保留，源协议样本成功不等于生产全市场分页成功。最终源/工程结果见后继实际回执。

固定协议族：

- `fuyao.aicubes.cn/api/a-share/calendar/trading-days` 与 `special-data/dragon-tiger-list`；凭据只发该既有host。
- `market.ft.tech/gateway/api/v1/market/data/abnormal-trading-details`、`northbound`、`holder/stock-ggmx`；FTShare key只发该既有host。
- `datacenter-web.eastmoney.com/api/data/v1/get`；`RPT_F10_EH_FREEHOLDERS`、`RPT_ORG_SURVEY`、`RPT_SHARE_HOLDER_INCREASE`、`RPTA_WEB_GETHGLIST_NEW`、`RPT_SEO_DETAIL`。
- `reportapi.eastmoney.com/report/list`；正文仅 `pdf.dfcfw.com/pdf/H3_<已取得报告ID>_1.pdf`。
- `www3.hkexnews.hk/sdw/search/mutualmarket.aspx?t=sh|sz`；历史查询只提交原公共页面的固定表单和请求季度，不绕鉴权、不换代理。

当前披露规则一手依据（2026-09-26重读）：

- SSE《调整沪港通交易信息披露机制》：https://www.sse.com.cn/lawandrules/sselawsrules2025/global/hkexsc/c/c_20250613_10781806.shtml 。2024-08-19生效的北向成交/持股字段频率分开；现行列示不支持旧每日买卖差假设。
- HKEX Northbound Shareholding Search：https://www3.hkexnews.hk/sdw/mutualmarket/SH.htm 。按公开说明显示季度持股及发布日期规则，不能把页面隐藏日期或今日请求日期当持股日。

以上URL是 source identity，不是 Kernel 对外部经济事实的认证；规则后续变更须按新实际证据处理。

## 3. 取得、资格、历史与安全

`smart_money_sources`负责固定请求与分家族口径；`smart_money_capture`负责有限请求、逐页原件、检查点与无网络重放；`smart_money_view`负责现有Git历史上的分块阅读、可比变化与公司/参与者检索；`smart_money_reading`只将已保存原件接入正常publisher。模块边界是代码职责，不是四个Agent或四个正式状态中心。

初始范围是最近5个完成交易日、90日披露和两个结束季度。源总数、已取页、原始行、去重记录、错误行分别保存。最多300个计划请求、每页最多4MiB、总原件80MiB、20分钟开始预算；失败逐来源隔离。128页是物理上限，不足时标明未取得页，不声称全市场穷尽。HTTP401/403/429及redirect等政策停止不在同轮换host/重试；已记录同日政策停止不借下一轮绕过。

HiThink间隔复用保守20秒，其他来源有有限间隔。每次请求后保存原JSON/PDF/HTML和manifest检查点，进程后续失败仍可保留此前已收到材料；失败工作流的材料明确为partial，不签整条执行成功。所有文字/正文只作数据，不执行来源代码或指令。

日期至少区分交易/活动日、报告期、披露日、取得截止、当前阅读检查。数值变化不替代披露可得时间；当年新取得旧材料不能放回过去当时知道的事实。首次基线不是当天发生的全部事件。

同ID同版本去重保留原件定位；同ID不同内容保存版本，冲突不偷偷选一个。当前阅读保留100日事件及两个报告期，之前的固定Git读取commit与原ZIP不删除。季度全表成功后最多六天复用并显示原取得日；缺期不复用为完成。原Actions附件有30天期限，正式publisher保存的精确ZIP另由Git历史留存，二者不混。

Gzip分块是普通JSON数据；两向浏览器不联网，不执行原始HTML或脚本，用textContent呈现来源文字。不在浏览器放token。大块/损坏/预算不足导致聪明钱阅读失败时，只保留该面缺口及旧历史定位，不吞其他Sector、Watch和Research交付。

旧 institutional_radar 的七文件实现指纹仅因 #579 unused Sector代码变更而不匹配。`institutional_radar_compat`只接纳实际审阅的完整旧/新映射；私有调用绑定不改原manifest或模块全局。36210892160对33家公司旧原件重放成功，网络调用0；旧失败不改写，历史结果不冒称新扫描。

## 4. 日常运行与自动补齐

`radar-smart-money`使用独立的工作日17:20及20:10北京时间时钟；第一轮尽量供18:50 Hosted Quick，第二轮核晚披露或已分类的临时缺口。这是已有Actions能力，不依赖Sector成功。并发group不取消进行中的采集。现有17:20启动不等于所有来源已发布，实际日期/覆盖始终保留。

控制步骤只用GitHub读取检查exactmain CI、固定R里的原进度、同日执行和共享源活动。已交付且不需晚确认时不重复采；最多三次同日调用，遇到未知数据资格/认证/额度错误不盲重试。共享HiThink被占用或无法核对时跳过该源，独立公开披露照常取得。当前进度不明确则停止相关重复采集并保留缺口。

下次以真实交易日历恢复已知缺日，不只读“最近一天”。一次最多20个交易日，超过的日期留待后继；仍不可取得的旧日期继续显示，不能被新一天成功盖掉。披露旧缺窗在一年有界范围内扩大查询，超范围仍保留待处理。历史覆盖不能由本轮空返回直接变成全市场无行为。

生产原件由既有 `current-state-read-entry` 自动发布到 `research.smart_money`，正常入口 `details/radar/smart-money.md`，完整两向读取 `details/radar/smart-money/browse.html`；manifest/state/overview保留实际时点及来源。不做第二份Health数据库，Brief/Quick读取该面真实coverage及pending状态。定时器成功、源交付、阅读成功、研究消费和Human已读分别验收。

## 5. 研究用途、剩余证据与验收

先回答“谁在哪些公开材料里出现了什么行为、相对哪个版本变了什么”；再由Hosted Quick查公司业务/产业/旧Research，判断实际研究价值。参与者名称、机构数量、资金净额均不自动成为研究真相、概率、推荐排序或投资决定。

新实现完成后必须做：精确head完整CI及原结果包审阅；正常merge/main CI/publisher；一次新正式capture并检查每个family的实际分页/错误/原件；固定R摘要、完整公司/参与者检索及旧档案读回；至少一次真实Quick消费。自然运行和故障恢复是后续真实样本，不用回放或合成fixture签收。

特别未被实现保证的事实：牛散真实身份与能力、游资实际账户所有人、未公开北向日内/每日净买、所有前十外持仓、原研报完整模型和全部可比历史、各回购实际注销、所有定增现金收款及穿透股权。能取得字段据实读，不能取得字段明确标记；这些不是把已有公开可做目标取消的理由。

退役时移除本caller、专属来源依赖/配置/测试与normalpublisher触发，保留已保存公共原件、历史索引及仍被消费的reader。临时probe/preparation不进入主干。无新付费订阅，无交易或自动Full/Odds/Watch。
