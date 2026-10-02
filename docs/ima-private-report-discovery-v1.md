# IMA 私有研报库：只读发现入口

Owner / scope: #297 的 Human-approved optional mature-wheel enhancement。用户已加入一个 IMA 共享/订阅研报知识库，并配置 IMA OpenAPI 凭证。这个入口只验证和使用 **私有搜索能力**；不会把付费/受限研报库复制进公开仓库。

## 边界

Decision Kernel 仓库是公开仓库。IMA 订阅库可能包含来源权利不明或不允许再分发的券商材料，因此本入口默认把 IMA 当作 `PRIVATE_SECONDARY_LIBRARY / PROVENANCE_NOT_VERIFIED`：可用于发现“有什么值得读”，不能仅凭 IMA 条目声称官方原件、公开授权、完整模型或研究接受。

第一版只做两次以内的手动 probe：

1. `search_knowledge_base`：按明确名称片段定位共享/订阅知识库；
2. 可选 `search_knowledge`：在唯一定位的知识库中做一次首屏关键词搜索。

公开留存只含状态、首屏命中数量、分页布尔、HTTP/字节/hash/时钟及查询本身的哈希。**不留存**知识库名称/ID、标题、摘要、media_id、URL、原始 JSON、PDF 或凭据；因此也明确 `source_replay=NOT_AVAILABLE_WITHOUT_PRIVATE_BYTES`。这不是原件保管链。

## 凭据与执行

凭据从 GitHub Actions Secrets 注入：优先 `IMA_OPENAPI_CLIENTID` / `IMA_OPENAPI_APIKEY`，并兼容 IMA 社区实现常用的 `IMA_CLIENT_ID` / `IMA_API_KEY` 别名；同一语义只取首个非空值。不要把值写进 workflow input、Issue、PR、代码、artifact 或聊天。固定服务为 `https://ima.qq.com/openapi/wiki/v1/`，只允许 IMA 官方搜索端点；POST JSON、禁重定向、禁代理凭据、显式 timeout、512KiB 单响应上限、无自动重试/备用主机。

`.github/workflows/ima-private-probe.yml` 仅 `workflow_dispatch`，要求精确 main SHA 和该 main 的独立 CI success。它不是 schedule，也不接 Research/Full/Odds/Watch。workflow inputs 本身属于公开仓库运行元数据，所以只放非敏感搜索词，不放账号、凭据、私密公司判断或原文。

## Reuse

Reuse Decision: **THIN_ADAPTER**。

- 内部：KEEP #717 的公开研报发现与既有正文/Research通道；IMA 不替换它。
- 外部：复用 `xuewolai/ima-mcp-server@2eb49e017a5158fc4b6521005e9917d61250b503` 已核的 IMA OpenAPI endpoint/header/schema 映射，MIT；不安装其 Node/MCP runtime。
- IMA API/数据权利与开源代码许可分开。能读订阅知识库不等于获得批量再分发券商 PDF 的权利。

## 后继

probe 成功只证明：当前 Secrets 有效、目标订阅库可通过 OpenAPI 定位、给定关键词可执行搜索。它不证明全部历史覆盖，也不把搜索结果送入模型。

若后续要让 Hosted Quick/Full 消费 IMA 正文，需要单独裁定**私有内容如何在不公开泄漏的情况下进入 Research**；不得因为本 probe 成功就把标题/摘要/PDF 上传到公开 GitHub artifact。优先做按需、小批量、可撤销的私有消费，不做全库同步、批量下载器或数据库。
