# News / Industry：保存观察的薄适配 v1

范围：纯转换、原件重建、公司上下文和声明式 Question 来路。不是生产采集、自动研究、行业拐点认证或投资判断。

需求与复用依据：#297 comments5741827146、5747204482、5747298151、5747407302、5747545412。开工main为9933d61ee70018b1d8e54e187392a5c62362ca46。复用已有canonical identity、company-reading validator、Question声明和原admission，不新增依赖、workflow、provider、crawler、registry或scheduler。

## 1. 可调用接口

`decision_kernel.runtime.external_radar_observations`：

- `news(body, receipt, cutoff=...)`：一份NewsNow原响应与原capture receipt → 一源观察投影。
- `news_context(captures, cutoff=..., company_reading=None)`：最多10份`(原字节, 原receipt)`，每份重建后按内容版本去重、形成精确标题待核对组；可选消费原有公司阅读投影。
- `industry(variety, captures, price_start=..., recent_start=..., period_end=..., cutoff=...)`：LC/CU/RB固定资料口径，捕获键为identity/prices/basis/warehouse，可选positions；每项也是`(原字节, 原receipt)`。
- `verify_news`、`verify_industry`：必须提供原件与参数并重新执行原转换，再比较整个保存结果，不能靠自己重算hash冒称原件核验。

这些函数没有文件、网络、模型或Git写入。调用方继续负责原件归档、精确Git/Artifact来源身份、只读load和结果保存；自报receipt加自报hash不证明真实HTTP执行。接口检查的是输入内身份、时钟、数值口径一致性。

News沿用实测attempts.json的bytes/sha256/requested_at/received_at/label/url/http_status/status；HiThink沿用requests.json的response_bytes/response_sha256/path/params/representation及对应时钟。HiThink保存的是解码后JSON表示，不冒称wire bytes。调用方不要把旧探针normalized output当作原响应，也不要对来源错误填零。

## 2. 新闻语义

只适配已经实测的七个NewsNow来源；每源最多30条，保留上游滚动窗口限制，不截断超额输入。验证请求source ID、响应ID、发行站点HTTPS域名、原文长度和原件hash。

`pubDate`、`extra.date`各自保留raw/parsed/status；缺失、无时区、无法解析、未来声明保留明确状态。数字时钟仅按已检查的毫秒口径，不猜秒/毫秒。解析通过也只是`PARSED_CLAIM_NOT_PUBLISHER_VERIFIED`。格隆汇来源的相对时间派生另标。服务updatedTime和success/cache分别保留，不充当文章发布时间或内容新鲜度。

article/version身份只依赖来源ID、URL、标题及原始时间声明；后来再次取得或对同一时间声明重新判断，不产生新内容版本。相同版本保留所供captures中最早收到的出现，其他来源窗口仍完整保留；不宣称提供了系统全历史first-seen。

标题分组仅折叠空白后精确相同，不抹掉数字、否定词、标点和货币。输出仍是UNVERIFIED待核对组，不合并原文、不宣称独立事件或独立证据。与实验版模糊标题聚类不是同一算法，计数不能直接作准确率比较。

可选company_reading先通过现有`radar_company_reading.render`检查，再在其source_names中做字面匹配，保留原thscode与research上下文。原阅读投影不改写；匹配不到不等于无相关公司，同名多个证券不静默裁决。输出只有CONTEXT_ONLY、NOT_FORMED和business_linkage=NOT_ESTABLISHED，不因评级、标题、标签数或价格自动进入Pre。

## 3. 行业语义

LCZL.GFE、CUZL.SHF、RBZL.SHF明确是供应商主连，不是固定到期主力合约。公开基差快照必须存在唯一默认spot ID；全部同品种备选仍留存。历史请求未显式传spot ID时只标`UPSTREAM_DEFAULT_HISTORY_NOT_CONFIRMED`，不能把今天的默认口径回填为全历史一致。

价格请求start/end和声明范围精确相同；时间戳不许越窗、重复或倒序。period_end的自然日已结束不等于完整交易所日历认证，输出保留calendar/historical-PIT/roll-composition缺口。收益按5/20个已保存观察间隔计算，不伪称交易日；区间存在缺值则该收益为空，不删掉缺失行缩短时间。

基差以本次实测口径保留：金额=折算现货减期货收盘；百分比=该差额/折算现货×100。供应商报告比率、归一化fraction、按量价计算比率和残差分别存储。容差固定0.005个百分点。金额或比率不勾稽、缺失的行留在field_gaps，原因UNKNOWN；不修原值、不放宽容差，也不否定无关价格计算。

仓单amount只计算原始单位差值，单位UNKNOWN；不臆造吨、手或行业总库存。可选持仓必须绑定同一品种及声明日期，不跨区间相加。暂不引入ruptures、AKShare或经济拐点评分。

本转换需要所声明的完整捕获集合。缺少必需原响应或结构身份失败时应由宿主保留SOURCE_UNAVAILABLE/转换拒绝，不能冒称空成功。字段级缺值与勾稽差异按上述方式留存，不自动成为业务WAIT或经济反证。

## 4. 与原Question入口的连接

`reviewed_question_input.ORIGIN_KINDS`只追加：

- NEWS_EVENT_CANDIDATE
- INDUSTRY_VARIABLE_OBSERVATION

不是新增Funnel或执行器，不修改旧三类来路和旧输入序列化。INDUSTRY_INFLECTION这个未实现的资格标签仍不接受。

研究者形成明确问题后，仍须保存原reviewed-radar-question-v0声明，并以原SourceRef引用精确留存的来路和必要原件；必须有why_now、可证伪检查、counterevidence、UNKNOWN及既有研究关系。把候选标为QUALIFIED_FOR_DECLARED_SCOPE是独立、可追溯的研究者声明，不由本适配器产生，也不等于Kernel认证经济真实性。

原来源预检、声明冻结顺序、原件hash、重复问题、执行权限等检查完整保留。只有CONTEXT_ONLY来路不能通过原prepare；必要正文缺失仍拒绝。即使输入准备通过，research_execution_allowed仍为false，真实Pre另受原launch门禁限制。

行业经济暴露/实质性/价值链判断、新闻正文核验、自动问题形成以及正常company-first publisher接线，均不由这次纯接口冒称已完成。

## 5. 保存实测输入上的新适配器回放

没有重采、重新部署或模型调用。原件来自：

| 输入 | run/artifact | ZIP bytes | SHA256 |
|---|---|---:|---|
| News | 35486102537/10597975192 | 53446 | 8fdf2884e86f0b47c4a268345715d07471cdf14d7a5ac524f347ca9dc153fbe0 |
| Industry | 35486156318/10597645925 | 127752 | 8aa291e84d4b9577c903e702c43c9c8263871bd9371e8ed641a1118d0b312502 |

转换cutoff固定2026-09-20T04:00:00Z。News重建180条、7源、160条可解析声明，严格标题规则产生10个待核对组（旧实验模糊规则21个，保留旧记录）。本次本地重建未重新物化完整903公司阅读；真实公司名称命中的历史检查仍见5747407302，公司接点由独立synthetic integration regression验证。

Industry各重建118条价格及35条近期基差/仓单，价格窗口2026-04-01..09-18，近期窗口2026-08-01..09-18。LC的9/11、9/15两条比率差异仍保留，铜/螺纹对应比率无本次容差缺口；仓单单位依旧UNKNOWN。

该回放使用新模块blob1bd28db04eb2b135f1c7e7f3cec623d3d30e267f，SHA256eedb7b69c334824c34597e43cbf09f0b544291cda53755a47df7088b5720a55d。规范投影hash：News41ee2428edd9eee178f2961615c5b181b6e74a0539ee7f355cf7ad1f6a27ac70；LCb8f007c8e9014d3b3a8f581e192306da70e6a86b141210594d7c933aa3208bd5；CUe73d0d2861c8cba2287e4301aaf7485c25af7d2b33a4a108b4e35b89213d671d；RB13789fca3af3226504dd1c9ed05625ff3411e31d8e06768e8cd7e353d34cdd41。

本地37项定向测试使用部分源码目录，identity.py与primitives.py已与精确main blob核对；不是完整仓库checkout或全量CI。最终准入以PR exact-head完整CI、独立main CI和正常publisher/readback为准。没有新增市场、Research或投资执行。

AI Investment Authority = NONE。
