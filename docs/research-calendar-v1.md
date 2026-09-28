# B2 首切片：有来源的有限宏观研究日历

归属与完整验收：[工作台 #351](https://github.com/auguspp/decision-kernel/issues/351) / [B2 #620](https://github.com/auguspp/decision-kernel/issues/620)；执行顺序仍以 [#297](https://github.com/auguspp/decision-kernel/issues/297) 为准。本文件描述工程接口，不维护第二份进度表。

## 可使用的结果与未包含的工作

`decision_kernel.runtime.research_calendar` 将**已经核读并保留的 BLS 月度日历文本摘录**转换为有限近期列表，保存后重新解析原字节并核 JSON、Markdown 和可选外部 hash。第一切片只处理 Employment Situation、Consumer Price Index、Producer Price Index，原日历外的日期不推演，未公布或未读到的日期不补造。

这是离线的 B2 第一切片，不是新的采集器、通用日历框架或第二份 canonical 状态库。没有网络客户端、生产 workflow、定时任务、Secret、Google Calendar、Human 待办、Quick/Full/Odds 或交易执行。不会因为研究过一家公司就生成关注/持有身份。

公司财报预约、里程碑/复核窗口、明确身份、完整改期/取消链和原站真实使用仍归 #620 后继；不关闭 B2。已有日历的固定 R 与工作台消费接口见下节；代码存在不证明正常 publisher、页面或 Sites 已实际采用，实际版本与验收读 #620 回执。

## 实际保存样本，不冒充原 HTTP 捕获

[2026-09-28 核读样本](readings/2026-09-28-b2-bls-calendar/calendar.md)及同目录的 `source.txt`、`request.json`、`calendar.json` 可以直接读和重放。样本来自实际查看的 [BLS 2026 年 10 月列表](https://www.bls.gov/schedule/2026/10_sched_list.htm)中的三行、月标题和时区/最后修改说明；保存的是 web 工具解析文本的**选取摘录**，换行是保存时的文本表示，不是服务器原响应。该会话容器取得原 HTML 的尝试失败，未将失败升级为自动采集成功。

`reviewed_at` 是核读留存时记录的时钟；HTTP `retrieved_at` 与来源首发 `published_at` 均为 UNKNOWN。页面的 Last Modified Date 单独保留，既不是 HTTP 抓取时间，也不证明这是首次发布日程的时刻。Git 精确提交/路径可固定这次摘录，不能恢复当时未取得的 HTTP 头或原 HTML。样本是真实核读数据，单测中的派生/改坏样本则明确为 `SYNTHETIC_TEST_ONLY`。

## 运行与读回

在已安装本项目的正常 Python 环境中：

```sh
python -m decision_kernel.runtime.research_calendar build \
  docs/readings/2026-09-28-b2-bls-calendar/source.txt /tmp/b2-reviewed-copy \
  --source-url https://www.bls.gov/schedule/2026/10_sched_list.htm \
  --reviewed-at 2026-09-28T05:06:04.658134+00:00 \
  --as-of 2026-09-28T05:06:04.658134+00:00 \
  --window-start 2026-09-28 --window-end 2026-10-25 \
  --local-timezone Asia/Singapore

python -m decision_kernel.runtime.research_calendar verify \
  docs/readings/2026-09-28-b2-bls-calendar
```

这是原留存样本的重放，不能把命令中的旧 `reviewed_at` 复制到新来源上当新查询。新来源须记录自己的实际核读时刻和有限日期范围；测试输入加 `--synthetic`。缺少 IANA 时区数据库时明确失败，不退回硬编码 UTC 偏移，也不自动安装依赖。复用本项目现有 Python/时区环境。

`build` 输出目录必须不存在，保存四个固定文件后立即读回；失败不覆盖旧目录，部分 I/O 写入保留为不完整目录而非成功。`verify` 不联网、不更新日期、不写文件；它重建结果并逐字节比较两个派生输出。需要外部定位时，传入由精确 Git/原回执独立取得的 `--expected-hash`。仅在同目录自报的 hash 不能证明整个目录未被协同替换，也不能认证来源内容的真实性。

## 日期、来源与阅读语义

输入必须有匹配官方 URL 的月份标题、BLS Eastern Time 说明，以及三系列中至少一行完整的英文日期/报告期。支持每行带 `hh:mm AM/PM` 或明确省略时间的日期行；`TBD`、未知格式、无法核对的整行不得转换为午夜。只接受固定月列表 URL，不跟随 URL、不解析来源文字为命令；裸页面导航不是这个摘录接口的输入。

原事件日期、星期、URL 月份与报告期分别检查。日历预约使用 `America/New_York`，本地时间由标准 `zoneinfo` 转换，夏令时不使用固定 12/13 小时时差。歧义/不存在的本地时刻拒绝；未知时刻保持 DATE_ONLY / UNKNOWN，不能建立唯一的本地日期。1–42 天范围按**原时区的来源日期**筛选，本地时间只负责展示，跨日本地日期不会反改筛选身份。

报告期是 `YYYY-MM`，不当发布日期。预约过去仍是 SCHEDULED；实际发布、已取得发布材料、分析与 Human 回应各自保持未检查/未运行/未记录，不能由时钟或保存日历推断。无事件只表示已读摘录中的所选系列在该窗口没有记录，不表示全世界 quiet 或完整日历无事件。

事件身份采用 BLS + 系列 + 报告期，不采用预约日期；改期能够保留同一事件身份、形成不同内容 hash。每个保存目录只增不改，旧日期不会被新调用覆盖。同一摘录重复/冲突身份拒绝而非选最新；**跨快照的只读显式前驱比对见下节；取消来源和正式修订登记尚未实现**，不要把稳定 event_id 或比较报告当成已经验收的完整改期链。

## 显式前驱比对：双端重放，不推断官方修订链

`compare` 在原模块内消费调用者明确选定的两份四文件原件。两个外部 `calendar_hash` 均必填，必须由精确 Git/原回执独立取得，不能在读取时把同目录自报 hash 当作外部证明。两端均走原 `read_calendar`：重新解析摘录、核请求与 JSON/Markdown 字节，再核各自外部 hash。任一端不完整、损坏或不符即拒绝；同 hash 自前驱、反向核读/截止时钟、真实核读与合成来源混用也拒绝。

```sh
python -m decision_kernel.runtime.research_calendar compare \
  /tmp/b2-before /tmp/b2-after \
  --predecessor-hash "$PREDECESSOR_CALENDAR_HASH" \
  --successor-hash "$SUCCESSOR_CALENDAR_HASH"
```

输出完整 canonical JSON，包含两端 hash、来源 URL/摘录 hash/核读时钟、窗口、报告期和原事件来源行，以及可复算的 `comparison_hash`。文件系统路径不参与身份，搬移原件后同一输入仍给同一报告。仅按既有 BLS＋系列＋报告期匹配，不用相似标题、最近日期或 mtime 猜前驱；允许同一报告期跨官方月份移动。

匹配事件的 `SOURCE_SCHEDULE_CHANGED` 只表示两次已保存摘录中的原预约日期/时刻不同，保留前后值；同日 DATE_ONLY/MINUTE 切换为 `TIME_PRECISION_CHANGED`，UNKNOWN 不当午夜，也不把补齐时刻说成确定改期。本地展示时区、来源行号或 Last Modified Date 变化不单独构成预约变更。两端窗口和展示时区是否相同另列，不能把窗口变化隐藏成同覆盖比较。

`PREDECESSOR_ONLY` 仅表示后端所选摘录/窗口里未见，**不是取消、已发布或已完成**；`SUCCESSOR_ONLY` 只是在本对首次见到，**不是首次公告**。两个来源的行与 hash 各自保留；输出不认证源站真实性，不因本次比较改变原预约/材料/研究/Human 状态，四项 authority 仍为 NONE。明确的取消来源、官方修订次序和完整多版本登记仍是后继，不从缺行或调用顺序推断。

此 CLI 是离线、只读的派生比较，自身不新增 bundle、数据库、自动挑最新、网络、publisher/registry 更新或页面历史面板。后续可选登记的发布端消费见下节。stdout 本身不是 create-only 归档；需要交接时，在原 Issue/PR 中保留报告和两份原件各自的精确 Git commit/path/hash。不同保存版本不得覆写，不能把比较哈希替代两端原件。原四文件格式、历史 hash 与 build/verify 输出合同不变。

本增量复用上方已存 #508/#511/#638 的有限事件/历史审计，以及原 stable event_id、read_calendar 和 canonical_json/hash；官方增量核读 [Schema.org previousStartDate](https://schema.org/previousStartDate) 与 [EventStatusType](https://schema.org/EventStatusType)，采用前后日期保留和独立状态证据，不引入其格式/解析器。**THIN_ADAPTER**，无新增依赖、权限或持续费用。退出仅移除 compare 函数/CLI、对应增量测试和本入口；原 build/verify、四文件保存及现有 Workbench 消费保留。代码/测试交付与实际来源改期验用、固定 R/页面采用仍分别成立。

## 复用、成本与退出

内部精确检查基线 M=`1ef57be901243f683cb0cc15cedd3ed159fdd02e`：`identity.py` 的 canonical_json/hash 直接复用；`economic_source_capture.py` / `economic_release_discovery.py` 的来源/时钟/原件边界作为兼容先例，不修改其 MOA/SPB 白名单。`ftshare_company_events.py` 是已披露合同/股东信息，不可替代财报预约；原交易日历也不提供事件日期。该前驱切片未改现役 Research、Markets、News、工作台、publisher；下方后继仅追加已保存原件的读取消费者。

复用检索先消费 #508/5773258951 和 #511 已存 PIT/供应商候选与否定边界，再检查残余缺口。`anthropics/financial-services` 当前审阅版本 `574ed3624aebd0418c7e96cd101262f30210ab26` 的 `plugins/vertical-plugins/equity-research/skills/catalyst-calendar/SKILL.md`（blob `af2ccb6bf1733c9a6d8df01e05a2b5805ed35000`）提供有限覆盖、核实变更与保存过去事件的产品先例；LICENSE 实读 Apache-2.0。本切片没有复制其文件或代码，不采用其仓位建议、自动填充、邮件或 Google Calendar 路线，也不引入它的框架。原 #511 的回测/持仓/SEC 数值候选不提供这个来源的未来日程。

官方复用是 [BLS 月列表](https://www.bls.gov/schedule/2026/10_sched_list.htm)和 [Python zoneinfo](https://docs.python.org/3/library/zoneinfo.html)。BLS 还提供 ICS 订阅，但本切片不读取 ICS、不写 RFC 5545 解析器；以后若确需自动采集，应先审其正式接口及成熟解析器，而非扩展这个摘录 parser。

**Reuse Decision：THIN_ADAPTER。** 新代码只负责所选官方文本与 Kernel 可恢复阅读的薄接点，不引入依赖、服务、持续费用或生产日程。测试直接覆盖新边界；并未删除/弱化现役完整 CI 或用小集合代表全仓。退出时可删除本模块、其专属测试及活入口，保留已存真实样本与历史回执；没有新数据库或运行任务需要迁移。

## 第二切片：同一原件进入固定 R 与市场观察

`current_state/registry.json` 的可选 `research_calendar` 登记当前完整四文件目录，并可显式追加一个同格式 `predecessor`（见下节）：精确源 commit、目录、四个 Git blob 和独立 calendar hash。首份绑定 #638 的 `74691f486beb6e9f2e011bb8ce9af7d14f146a30`，不读新的 main 来替换旧摘录，也不把来源 M 当发布 R。后续新快照须另行保留、核读并在正常变更中显式更新登记；没有自动按时间挑最新或补造改期关系。

`research_calendar_reading.read_registered` 复用现役 `Collector.source` 的 Git 读取、字节保管和来源额度，再调用原 `read_calendar` 重建/核对四文件与外部 hash。来源 ref/path/blob/bytes/SHA 和返回的同 R 描述符分别绑定。合成来源不能发布为可用观察；缺件、错误 hash、反向时钟或读取失败只产生本模块缺口，撤回本次未完成的派生保管，不删除 Git 历史、不改其他资料、不倒找旧成功。无新来源请求、权限、费用、定时任务或 CI 旁路。

原 publisher 的 `research.calendar` 保存 `SAVED_REVIEWED_CALENDAR` 或明确缺口、原核读截止、另列的读取检查时刻及四份 `files` 定位。原 JSON/Markdown/摘录/请求字节通过既有 `sources/git/<blob>/<name>` 留在同一发布 R，不重新写一套事件正文。根 README 增加同 R 日历 Markdown 链接；四项 authority 仍为 NONE。登记、代码合并、publisher 成功、准确 R 正文读回、原 Sites 采用分别成立。

工作台“市场观察”中的研究日历面板使用原 `Reading.readFile` 完成准确 R、已登记路径、字节数与原生 SHA-256 检查，显示有限窗口、原时区/本地时刻、报告期和未核实发布状态。完整来源解析仍归 Python 原重放；JS 仅核展示身份/形状，不重新认证源站或 canonical reading_hash。来源文字只进入既有文本节点，不当 HTML 执行。可从面板阅读同 R 的摘录和 Markdown；外部 BLS 链接明确是源站当前页，不能替代已固定原件。

没有登记的旧 R 显示“尚未接入”，读取错误不变成零事件，过期窗口明确标为历史。页面读取/换页不更新来源；迟到的旧 R 响应不能覆盖新的选择；时钟经过不把预约变成实际发布、已取得、已分析或 Human 已回应。公司事件、关注/持有身份与完整改期链不从现有 Research 或页面点击推导。

复用依据延续上方 #508/#511 与 #638 的原审计；消费者直接沿现役 Collector/Reading 和 #630 浏览器 harness，未发现需更换上游实现的新证据。官方接口复核：[DOM textContent](https://developer.mozilla.org/en-US/docs/Web/API/Node/textContent)、[Playwright 请求拦截](https://playwright.dev/python/docs/network)。不新建视图框架、状态库、解析器或 provider。实际新浏览器场景与原失败按 #620/关联 PR 留存，隔离测试不是原 Sites/真实身份/实机验收。

退出时同批移除本登记键、publisher 消费/导航接点、页面 import/面板、新专属测试与浏览器日历场景；保留原四文件档案和历史回执。CLI 与原日历的历史重放是独立能力，未获退役时不一并删除。新入口可缺失，不阻断原市场、研究或新闻阅读。

## 可选前驱：同 R 原件保管与比较导航

原 `research_calendar` 四字段（`ref`、`directory`、`calendar_hash`、`blobs`）仍表示当前选定快照；唯一新增可选键 `predecessor` 使用相同四字段，不能再嵌套前驱、列表或任意查询。两端分别绑定精确来源 commit、目录、完整四个 blob 和独立 calendar hash。没有默认从上一 R、mtime、最新提交或相似日期挑前驱；最多两份显式快照，不扫描完整历史。

`read_registered` 先按原接点核当前快照。当前失败时不读取前驱替代；当前成功、但前驱缺件/坏字节/错误 hash、合成类别、反向来源时钟、自前驱或比较保管失败时，保留当前日历及原件，只将 `comparison.status` 标为 `UNAVAILABLE_OR_REJECTED`。字段未提供则为 `NOT_CONFIGURED`；显式 `null` 不是未配置。失败不等于没有改期或取消，不倒找较旧成功，不泄露外部异常正文，不回退实际 API 计数。

双端成功后，直接调用原 `compare_calendars`；原 JSON 输出不加字段或改 hash，保存为 `details/research/calendar-comparison.json`，薄展示为同目录 `calendar-comparison.md`。原根 `research.calendar.comparison` 只登记 `SAVED_EXPLICIT_PREDECESSOR_COMPARISON`、独立检查时刻、比较 hash、当前 hash、前驱来源/四文件定位、分类计数与两个派生文件描述符，不将全部事件复制进根索引。当前日历的来源/核读时钟与四文件合同不变。

所有八份输入（相同 blob 可共用原保管路径）和两份派生输出都通过现有 Collector 保管在同一 R。根 README 导航直接进入比较 Markdown/JSON，比较文档再用同 R 相对路径到两端原件；不是链接到新 main 或源站当前内容。读取仍应先固定 R、核根 hash，再核描述符 bytes/SHA256；复核比较时用两端独立 hash 重放原四文件。单个比较 hash 不能替代原件或证明官网真值。

容量继续复用 #640 的四文件隔离，每次读取结束还原基线 source cache。读取前驱之前为其四次最多 GET、两份派生文件、当前已保管文件、根及发布元数据预留额度；原 60 来源/180 API 与总保管字节上限不增加。前驱或第二份派生写失败撤回本次可选保管，不删除已有当前文件、历史 Git 或其他模块材料。未改变原 publisher workflow/权限，也未新增状态所有者或自动采集。

这建立的是**可选双快照登记与同 R 阅读**，不是官方修订/取消链、完整多版本目录、Workbench 历史面板、Sites 或 Human 使用证明。现役 registry 不因工程测试自动追加前驱；真实后继须有自己的来源原件/实际核读时刻，并经正常变更显式登记。测试中的假设日期和核读标签只验证机械合同，不充当官方变化证据或生产样本。

复用当前文档已保留的 #508/#511、#638–#641 审计；内部为原 source/retain、read_calendar/compare_calendars 和 publisher 调用/导航。官方合同补核 [GitHub Contents 精确 ref](https://docs.github.com/en/rest/repos/contents#get-repository-content)及上方 previousStartDate，无新库/日期算法/网络客户端或持续费用。退出时删除可选 predecessor 登记、比较接点/专属测试与说明；原当前快照、CLI 历史重放、来源原件与失败记录保留。完整 B2 验收仍归 #620。
