# B2 首切片：有来源的有限宏观研究日历

归属与完整验收：[工作台 #351](https://github.com/auguspp/decision-kernel/issues/351) / [B2 #620](https://github.com/auguspp/decision-kernel/issues/620)；执行顺序仍以 [#297](https://github.com/auguspp/decision-kernel/issues/297) 为准。本文件描述工程接口，不维护第二份进度表。

## 可使用的结果与未包含的工作

`decision_kernel.runtime.research_calendar` 将**已经核读并保留的 BLS 月度日历文本摘录**转换为有限近期列表，保存后重新解析原字节并核 JSON、Markdown 和可选外部 hash。第一切片只处理 Employment Situation、Consumer Price Index、Producer Price Index，原日历外的日期不推演，未公布或未读到的日期不补造。

这是离线的 B2 第一切片，不是新的采集器、通用日历框架或第二份 canonical 状态库。没有网络客户端、生产 workflow、定时任务、Secret、Google Calendar、Human 待办、Quick/Full/Odds 或交易执行。不会因为研究过一家公司就生成关注/持有身份。

公司财报预约、里程碑/复核窗口、明确身份接入、正常 publisher/固定 R 登记、工作台页面与原站真实使用仍由 #620 后继交付；本切片不替代这些验收，不关闭 B2。独立目录保存也不证明普通 publisher 或 GitHub `read-model/current-state` 已经消费。

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

事件身份采用 BLS + 系列 + 报告期，不采用预约日期；改期能够保留同一事件身份、形成不同内容 hash。每个保存目录只增不改，旧日期不会被新调用覆盖。同一摘录重复/冲突身份拒绝而非选最新；**跨快照的显式前驱/取消/修订登记尚未实现**，不要把稳定 event_id 当成已经验收的完整改期链。

## 复用、成本与退出

内部精确检查基线 M=`1ef57be901243f683cb0cc15cedd3ed159fdd02e`：`identity.py` 的 canonical_json/hash 直接复用；`economic_source_capture.py` / `economic_release_discovery.py` 的来源/时钟/原件边界作为兼容先例，不修改其 MOA/SPB 白名单。`ftshare_company_events.py` 是已披露合同/股东信息，不可替代财报预约；原交易日历也不提供事件日期。现役 Research、Markets、News、工作台、publisher 不改。

复用检索先消费 #508/5773258951 和 #511 已存 PIT/供应商候选与否定边界，再检查残余缺口。`anthropics/financial-services` 当前审阅版本 `574ed3624aebd0418c7e96cd101262f30210ab26` 的 `plugins/vertical-plugins/equity-research/skills/catalyst-calendar/SKILL.md`（blob `af2ccb6bf1733c9a6d8df01e05a2b5805ed35000`）提供有限覆盖、核实变更与保存过去事件的产品先例；LICENSE 实读 Apache-2.0。本切片没有复制其文件或代码，不采用其仓位建议、自动填充、邮件或 Google Calendar 路线，也不引入它的框架。原 #511 的回测/持仓/SEC 数值候选不提供这个来源的未来日程。

官方复用是 [BLS 月列表](https://www.bls.gov/schedule/2026/10_sched_list.htm)和 [Python zoneinfo](https://docs.python.org/3/library/zoneinfo.html)。BLS 还提供 ICS 订阅，但本切片不读取 ICS、不写 RFC 5545 解析器；以后若确需自动采集，应先审其正式接口及成熟解析器，而非扩展这个摘录 parser。

**Reuse Decision：THIN_ADAPTER。** 新代码只负责所选官方文本与 Kernel 可恢复阅读的薄接点，不引入依赖、服务、持续费用或生产日程。测试直接覆盖新边界；并未删除/弱化现役完整 CI 或用小集合代表全仓。退出时可删除本模块、其专属测试及活入口，保留已存真实样本与历史回执；没有新数据库或运行任务需要迁移。
