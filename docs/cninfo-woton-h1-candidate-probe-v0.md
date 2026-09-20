# 沃顿 2026H1 巨潮报告候选验证

这是固定财报来源实验，不是生产来源接入。Human 在审阅
[候选比较](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5750741381)
后要求“那你继续吧”，
[本次范围](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5750797689)
据此允许这一次有界适配及实际验证。其他公告暂缓；旧失败、原问题身份和已消费执行保持原历史。

## 复用决定

**Reuse Decision: THIN_ADAPTER。** 基线 main 为
`7bb5a2617681882ea65faa50c59c0fcd57673a22`。

| 层次 | 实际检查及复用 | 不匹配之处 |
| --- | --- | --- |
| 仓库内部 | 现役 CNINFO 只读探针工作流；`cninfo_pdf_transport_probe.native_identity`；原 Requests session/响应守卫、create-only 留存和 PDF parser | 原目录入口先做 ORG_SEARCH；四个旧探针模式均不包含本次公司、报告期及查询契约。 |
| 官方生态 | 已审现役 GitHub Actions checkout、精确 main、首次 attempt、官方 artifact；巨潮实际目录与静态附件端点 | 工作流成功、目录成功、PDF 获取和正文身份正确需要分别验收。 |
| 公共 GitHub | `youhaozhao/cninfo-mcp` 的 `python/spider.py`、测试、MIT 许可证和近期真实 Actions 日志；其余用户提供项目及补充候选见上述比较回执 | 上游高层入口默认全历史、多市场、重试；近期 Actions 部分证券 403，绿灯也不证明 PDF 全部成功。 |

采用
[cninfo-mcp@f0108154966b50fe94d5d31e5c381a586b8c53d6](https://github.com/youhaozhao/cninfo-mcp/tree/f0108154966b50fe94d5d31e5c381a586b8c53d6)
的报告查询形状：`stock=""`、`searchkey=000920`、半年报 category，
直接查询深圳市场，避免把 ORG_SEARCH 作为第一步。源码片段的固定 Git blob 是
`522f958ccaab8045b0a2e738d689ecf5311702d7`。这是经边界适配的路径实测，
不能称为未修改的第三方程序原样验收。软件归属和完整 MIT 条款保留在
[NOTICE](../third_party/cninfo-mcp-NOTICE.txt)。

## 实际范围

现役 `.github/workflows/cninfo-announcement-source-probe.yml` 新增固定
`woton-h1-cninfo-candidate` 选项，继续在同一只读 job 运行。
只有合并后的精确 main、首次 `workflow_dispatch` 可发请求。
只为该模式安装仓库已有的 `documents` extra；没有新增第三方包。

- 公司：沃顿科技 `000920`；报告：`2026H1 / semiannual`。
- 市场：`szse / sz`；查询区间：`2026-07-01~2026-09-20`。
- 最多两页目录 POST，每页 30 条；最多三次 PDF GET，总计最多五次来源请求。
- 不重试，目录和 PDF 均不跟随跳转；3xx 原样记录为失败，不增加隐藏请求。
- 每个目录响应最多 512 KiB，每个 PDF 最多 4 MiB，总响应最多 12 MiB。
- 来源获取在每次请求发起和流式读取时检查 180 秒预算，并设置有限网络超时；这不是解析与重验的硬截止。外层沿用五分钟 job，覆盖安装、获取、解析和重验。实际返回、预算耗尽及未尝试项如实保存。

仅从真实返回行选择本公司、本报告期的全文。更正、修订及补充线索保留；
不能把摘要、别家公司或别的报告期当成所需正文。附件只来自实际返回的
巨潮静态域定位，不能用已知旧 PDF URL 替代目录成功。

PDF 原始字节与 SHA256 先写入本次独立目录，再交原 parser；
解析失败也保留已取得原件。目录、附件传输和正文身份分别给出结果。
`--verify-only` 只检查留存结果，不发来源请求。

已有新浪 2026H1 原件为 133 页、1,262,185 bytes，
SHA256 `27c74e31c8aaf5a38d27b688f0841d81797816420b591647bfb6763e485b7728`。
只有本次字节哈希相同，才能称为两端同字节；不同则保留差异，不覆盖原件。

## 结果解释

实验始终是 source-only：模型调用 0、Research work 写入 0。
PDF 获取成功不等于正式研究完成、证据资格通过或生产接入。
旧问题根
`stock-business-66446c4257a92cd4576ee87ff1bd4ead51ca61a4292befc55cbde3d514b5542c`
保持连续；本次实验不派发 daily 或修改旧 request。

代码验收按现役完整 PR CI、独立 main CI、正常 publisher/readback 执行。
真实源验证结果另以该次 workflow artifact 与 #297 回执留存；本文不预填成功。
即使候选失败，已取得的新浪财报仍可供后续财务研究使用。
