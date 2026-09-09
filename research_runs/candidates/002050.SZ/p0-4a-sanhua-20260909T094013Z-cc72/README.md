# 三花 cc72：已有监控问题的真实 Pre / Quick

**候选阅读入口；不是正式 Research 登记、当日买卖建议或 Human 决定。**

这次已经形成有来源绑定的 Pre 与 Quick，并实际调用未改动的原安装模型及 Funnel 校验。结论为 `Pre CONTINUE_TO_QUICK → Quick WAIT_FOR_TRIGGER`。这里的 COMPLETE 只指冻结问题范围内的研究内容和阶段完成；**早期六次读取日志丢失，过程证明 PARTIAL；P0-4A 整体验收、独立正常/恶意来源对照仍未完成。** 不因候选 JSON 或 CI 通过而登记、合并或刷新投资状态。

## 先看结论

在已读六份官方原件中，核心经营仍有盈利和现金流支撑，发行人也确实披露了液冷供货、机器人批量交付与产线爬坡。但这些措辞尚未建立新业务独立可重复收入、毛利或资本回报。核心增长与压力并存：扣非归母增长，归母利润下降；汽零收入增长而毛利率下降。

因此本轮完成一个有界的研究等待：等待可量化的新业务经济性、后续核心现金转化或权威口径澄清。不是把“没有取得必需正文”伪装成 WAIT，也不是证明其他资料不存在。未读取的当前市场价格、卖方预期、历史概率不参与本轮结论。

### 两处原文差异保留，不自行修正

| 来源 | 读到的差异 | 本轮处置 |
|---|---|---|
| H1 p13 与 p7/p60/p114 | OCF 2,492,168,439.73 元与 2,499,553,386.38 元；相差 7,384,946.65 元 | 关键原页已渲染核对，未取得权威解释；并列保留，不猜重分类或错误原因 |
| 募集资金专项报告与现金管理公告 | 调整后募集投入 29,572.79 万元与拟使用募集投入 30,688.49 万元；差额 1,115.70 万元 | 标签/口径分别保留，不假设二者本应相等，不自行桥接 |

未来产业中心为基建类项目，原文称效益无法单独核算；建设可使用目标由 2026年6月延至12月。不能把整座中心资金视为机器人独占资本，也不能把建设延期直接解释成客户订单失败。

## 详细入口与精确身份

请先将本候选分支解析为一个精确 commit R，再在同一 R 下读这些相对文件。

- [input.json](input.json)：已冻结的 cc72 输入；原提交 `05c67a2636d10e445f5ee533549792f464cb3ebe`，blob `50eb2bce246f9572ae53692c923dab45b1255b50`。
- [candidate.json](candidate.json)：完整 Discovery、Pre、Quick、六份 Evidence 和执行回执；不是另写一份摘要来代替研究。
- [funnel.json](funnel.json)：原 `validate_external_research_candidate()` 内实际调用原 Funnel 后得到的完整输出；与现有候选扫描测试逐值比较。
- [validation-summary.json](validation-summary.json)：原模型规范化 hash、阶段、预算、证明边界。
- [admission.json](admission.json)：原 #291 的实际准入输出。`status=NOT_EXECUTED` 是检查本身的字段；`reason=RESEARCH_EXECUTION_ALLOWED` 不是完整研究回执。
- [execution-context.md](execution-context.md)：早期日志缺失与预算计入方式，不重置旧预算、不倒造平台日志。
- [原已提交预检](../p0-4a-sanhua-20260909T084245Z-6d91/preflight.json)：五类来源与所有有界目录线索的处置；不是全部互联网或9月9日全天披露覆盖。

```text
execution_id: p0-4a-sanhua-20260909T094013Z-cc72
code_commit: 381f4d1f826a6d98844d27d626129211218ca332
research_cutoff: 2026-09-09T09:40:13.921747Z
canonical_input_hash: bfee6fe264dd4322e9b67b4ddb05aa9ce5bb499b51e599aa00d81e6bdafab695
candidate_hash: 39ea0846711c1dcc1bfc7621a63c977b1b4000e50e71e7c27da378aea6e3ce4d
funnel_hash: 5a8d608336eeb0c69ffe8a4f74a34860000eb4aa0e609e29649ddf602eb8ed91
```

## 原件，不是搜索摘要

| 来源 | 已保存位置 | 内容范围 |
|---|---|---|
| H1 1225514004 | run 34316364031 / artifact 10090204888 / capture/003.pdf | 当期财务、分产品、现金流及附注 |
| IR 1225523008 | run 34322709839 / artifact 10092493073 / capture/003.pdf | 8月27日电话会议；液冷、机器人、汇率问答 |
| 专项报告 1225514006 | run 34328835353 / artifact 10095294054 / 003.pdf | 募集资金投入、项目进度、独立效益限制 |
| 现金管理 1225514001 | 同一补充 artifact / 004.pdf | 授权额度和募集资金拟投入口径 |
| 进展公告 1225514010 | 同一补充 artifact / 005.pdf | 公司行动进展、研发、商业化及分配预案 |
| 回购进展 1225541228 | 同一补充 artifact / 006.pdf | 截至8月31日累计回购及现金使用 |

源文件 SHA256、官方原 URL、发表/可得/读取时间分别在 Evidence 中。FULL replayability 指保留原件字节可回放，不承诺源站观点为真或永久存储。旧 fulltext 包仍是 SOURCE_CAPTURE_INCOMPLETE；没有因后来取得 IR 改写旧包。

## 执行与验收分层

原准入在 10:17:49.033728Z 完成后调用读取器。随后本地新目录/早期 journal 不再可见；具体原因 UNKNOWN。后续在同一 cc72、同一预算内重读原件并完成研究，未重开第二次研究来洗掉失败。回执起点采用准入完成的保守下界；内容结束于 10:28:32.207835Z。

22 个预算记账事件包含 16 个后续读/渲染/计算事件及 6 个明确标记的早期读取回溯记账摘要；后六个 observed_at 是摘要记录时间，不是原读取时间。独立来源正文只有6份。没有新增源站请求、搜索或技术重试。预算全是 SOFT_EXECUTOR，不宣称硬权限沙箱。

| 层次 | 状态 |
|---|---|
| 六份原件与已声明来源范围 | 已取得并阅读；目录范围限制保留 |
| 原 #291 准入 | 实际执行通过 |
| Pre / Quick 有界内容、原 Funnel 本地确定性验证 | 已完成 / VALIDATED_FUNNEL_RESULT |
| 此候选 exact-head 全仓 CI | 另查本 PR 的实际 run，不从本地通过推导 |
| 原执行过程完整认证 | **未通过：早期 journal 丢失，PARTIAL** |
| 独立正常/恶意对照 | **NOT_RUN** |
| P0-4A 整体完成、正式 Research/待办登记 | **NOT_ESTABLISHED / NOT_REGISTERED** |

这是已有研究问题的接续复核，不是新 Radar 发现、盲测或独立审计。Human / Investment authority 为 NONE；不修改旧 Human 决定、概率、Odds、Deep 或生产 registry。不要为了取得绿灯重写候选或放松已有校验器。
