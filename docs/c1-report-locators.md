# C1：两份光迅长江研报的原件定位

本次Human明确授权从成熟接口取得原件。只查002281.SZ、长江证券的2026-04-30和2026-09-10两份目标报告。原#680不可比输入及历史不改；下载地址不是PDF已取得，更不是完整预测模型合格。

Reuse：沿docs/data-source-orchestration-v1.md现有research_report按需职责，直接复用原tushare_relay客户端、固定HTTPS源、已有Actions secret和原临时队列一次30秒重试。不复制AKShare爬虫，也不采用响应级currentYear给历史模型定年。官方字段/限额依据为 https://tushare.pro/document/2?doc_id=415 。第三方Relay不冒称官方独立来源。

`.github/workflows/c1-report-locators.yml`仅main、owner、attempt1，要求对应独立main CI成功；单次authorization为c1-accelink-two-reports-20261002。两笔逻辑查询最多四次HTTP；不分页、扩股、购权限。权限/限流/业务及目录资格失败停止。限额可能被上游忽略，故实核保存行数、count及每行日期/证券/机构，不凭请求参数认定过滤成功。

原响应、请求/取得时钟与摘要保存到本次Actions artifact，30天，不是永久Git原件。来源URL可能带临时参数，不打印到公开job日志；本程序不下载任何返回URL。目录完成后由原C1研究逐一核实际URL与目的地后取目标PDF，保留原作者、日期、版本、口径和来源限制，不自动翻译成forecast资格。

`capture --root <新目录>`执行固定两查询；`verify --root <已有目录>`无凭据调用原响应验证并重建summary，逐字节核对。两者均由原GitHub运行身份绑定。进程中断可能只有部分原响应，不能冒称完整回放。本地/合成测试、正式PR/main、来源成功、PDF取得、模型资格和自然使用分别验收。

这是原C1一次性薄载体，不接生产时钟、不新增provider/registry/数据库/模型/Watch，不承担C2来源执行，也不解除#713的历史平台安全拒绝。取得结果后沿#680/#297收口；若由正式按需消费者接管，退役本专属载体并保留原件。Sites暂停，D未启动。
