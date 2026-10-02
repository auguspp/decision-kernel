# IMA 私有研报库：只读发现入口

Owner / scope: #297 的 Human-approved optional mature-wheel enhancement。用户已加入一个 IMA 共享/订阅研报知识库，并配置 IMA OpenAPI 凭证。这个入口只验证和使用 **私有搜索能力**；不会把付费/受限研报库复制进公开仓库。

## 边界

Decision Kernel 仓库是公开仓库。IMA 订阅库可能包含来源权利不明或不允许再分发的券商材料，因此本入口默认把 IMA 当作 `PRIVATE_SECONDARY_LIBRARY / PROVENANCE_NOT_VERIFIED`：可用于发现“有什么值得读”，不能仅凭 IMA 条目声称官方原件、公开授权、完整模型或研究接受。

默认搜索模式保持两次以内的手动 probe；下方2026-10-02后继另允许显式单篇检查：

1. `search_knowledge_base`：按明确名称片段定位共享/订阅知识库；
2. 可选 `search_knowledge`：在唯一定位的知识库中做一次首屏关键词搜索。

公开留存只含状态、首屏命中数量、分页布尔、HTTP/字节/hash/时钟及查询本身的哈希。**不留存**知识库名称/ID、标题、摘要、media_id、URL、原始 JSON、PDF 或凭据；因此也明确 `source_replay=NOT_AVAILABLE_WITHOUT_PRIVATE_BYTES`。这不是原件保管链。

## 凭据与执行

凭据只从 GitHub Actions Secrets `IMA_OPENAPI_CLIENTID` / `IMA_OPENAPI_APIKEY` 注入。不要把值写进 workflow input、Issue、PR、代码、artifact 或聊天。固定服务为 `https://ima.qq.com/openapi/wiki/v1/`，只允许 IMA 官方搜索及 `get_media_info` 端点；POST JSON、禁重定向、禁代理凭据、显式 timeout、512KiB 单响应上限、无自动重试/备用主机。

`.github/workflows/ima-private-probe.yml` 仅 `workflow_dispatch`，要求精确 main SHA 和该 main 的独立 CI success。它不是 schedule，也不接 Research/Full/Odds/Watch。workflow inputs 本身属于公开仓库运行元数据，所以只放非敏感搜索词，不放账号、凭据、私密公司判断或原文。

## Reuse

Reuse Decision: **THIN_ADAPTER**。

- 内部：KEEP #717 的公开研报发现与既有正文/Research通道；IMA 不替换它。
- 外部：复用 `xuewolai/ima-mcp-server@2eb49e017a5158fc4b6521005e9917d61250b503` 已核的 IMA OpenAPI endpoint/header/schema 映射，MIT；不安装其 Node/MCP runtime。
- IMA API/数据权利与开源代码许可分开。能读订阅知识库不等于获得批量再分发券商 PDF 的权利。

## 后继

probe 成功只证明：当前 Secrets 有效、目标订阅库可通过 OpenAPI 定位、给定关键词可执行搜索。它不证明全部历史覆盖，也不把搜索结果送入模型。

若后续要让 Hosted Quick/Full 消费 IMA 正文，需要单独裁定**私有内容如何在不公开泄漏的情况下进入 Research**；不得因为本 probe 成功就把标题/摘要/PDF 上传到公开 GitHub artifact。优先做按需、小批量、可撤销的私有消费，不做全库同步、批量下载器或数据库。

## 文档搜索省略分页字段（2026-10-02）

旧代码将文档搜索的 `is_end` 强制设为必填，导致[凭据修正后首个真实请求](https://github.com/auguspp/decision-kernel/pull/719#issuecomment-5949240932)在本地 `DOCUMENT_PAGINATION` 处失败。该次库搜索与文档搜索已通过 HTTP/业务码检查，但私有原响应未留存，不能恢复命中数，也不能证明本次具体缺失的是哪一个字段。

补充复用依据是第三方作者的[实测说明](https://github.com/daymade/claude-code-skills/blob/b8585e12650227cd8c5d5f66dc87caaa8d3bd652/ima-copilot/references/search_best_practices.md)及[真实实现](https://github.com/daymade/claude-code-skills/blob/b8585e12650227cd8c5d5f66dc87caaa8d3bd652/ima-copilot/scripts/search_fanout.py)：`search_knowledge` 可能同时不返回 `is_end` 与 `next_cursor`，高频查询可能只给100条。这不是腾讯官方保证，也不证明本账号覆盖范围。

薄适配只接受两个明确变体：两字段齐备时仍严格核布尔/字符串类型；两字段均缺失时输出 `pagination_reported=false`、`is_end=null`、`next_cursor_present=null`。只缺一个字段或提供错误类型仍拒绝，不以空字符串/true补全缺失值。两变体的 `coverage=UNKNOWN` 均不升级为整库或历史覆盖证明；摘要也明确缺分页时未知，不自动翻页、重试或全库扫描。

知识库目录校验、行/身份检查、原HTTP/业务失败、认证、隐私、请求预算与workflow均不变。原成功格式继续可读，原失败不重写为成功。离线合成测试不是实际研报命中，也不是对未保管原响应的回放；修补后的真实源验收另行确认，不由本次代码提交自动再执行已消费的探测。

## 单篇原件可用性检查（2026-10-02 Human批准后继）

接续[#297可行性审阅5950208330](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5950208330)及[Human“好，做吧”开工5950809043](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5950809043)。这只扩展原手动入口，不新建数据库、同步器或私有存储服务。A股证券知识库保持综合首选，公司研报知识库补充；两者已通过的检索不等于原件可读。

`report-title-terms` 默认空，保持原搜索行为。显式提供后，先在同次首批文档结果中按全部标题关键词筛选，选择原返回顺序的第一个不同media候选；不是“最新/最好”、不是去重后整库。名称必须实际匹配所请求知识库。无标题匹配就停止，不换关键词。至多增加一次 `get_media_info`；只有 `media_type=1` 且给出有效访问资料，才增加一次文件GET。每次最多3个API请求与1个文件GET，没有分页、重试、替代网页接口或更多候选尝试。

复用依据仍是 `Tencent/WeKnora@bccb4b151bae403508da77fbb174efc79dc47c1a` 中 IMA `client.go`、`connector.go`、`types.go` 的单篇访问合同；不复制其全库同步、重试或日志实现。PDF复用仓库既有 `documents` 依赖pypdf/pypdfium2，不套用Smart Money的预测抽取来冒称研报已读。第三方订阅库受限说明保留为反证，账户权限以实际响应为准。

文件阶段使用独立HTTPS客户端，原IMA长期凭据不传给文件服务器；只接受返回的腾讯域名访问地址，校验所有DNS地址为公网后固定一个地址连接，TLS仍校验证书域名。禁止重定向、用户信息、非443端口及任意Cookie/Host/header注入；只使用返回的受限访问头。不把未知下载域名或缺URL改成可用，不换IP重试。单PDF最多8MiB、80页；解析子进程有20秒墙钟/12秒CPU/1GiB地址空间上限，检查前3页文字和首张渲染。原生/解析器输出被抑制，防止源文字落入公开日志。

**私有处理位置是当前Actions runner的临时内存与隔离子进程。** 不保存原PDF、候选标题/ID、正文/摘要、访问URL/headers或凭据到Git、日志、summary、artifact或read-model。公开输出只有候选数、选择哈希、响应字节/哈希/时钟、media类型、访问/解析状态、页数/字数及明确语义限制；相同对象不会留下可供原件回放的字节。本检查不是持久私有交付，更不是Quick/Full消费。

- `BODY_UNAVAILABLE_NO_URL`：该次PDF媒体响应没有访问地址；不推断整库永久不可读。
- `NOT_PDF_NO_DOWNLOAD` / `NOT_SELECTED`：选定条目非PDF或没有标题匹配；不自动换条目。
- `CHECK_FAILED`：保留失败阶段、HTTP或业务码，不能当空库、没有研报或成功取文。
- `PDF_MACHINE_READABLE`：实际PDF解析、前3页有文字、首张渲染；**没有语义阅读全文、内容质量或研究接受证明**。可渲染但无文字另报 `PDF_RENDERABLE_TEXT_UNAVAILABLE`，不偷偷OCR。

原v1搜索回执保持可读；单篇模式增加可选 `body_check`，source_calls计入尝试次数，失败步骤不声称成功下载。原两次失败与两库成功搜索记录不回写。取得原件可用性证据后，才决定是否需要受鉴权的私有研究交付；这一步不自动建立新存储、不触发模型或改变原公共公告/新闻/研报通道。替换/退出时同时处理本入口、专属helper/tests、workflow选项与说明，原回执及共享搜索保留。
