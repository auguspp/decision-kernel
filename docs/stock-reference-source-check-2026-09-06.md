> 当前执行方向已纠正：Tushare 不是股票读取的必要依赖，不要求用户新增账户或连接。以下为先前候选来源检查记录；当前 HiThink 端到端路径和合同边界见 `stock-reading-hithink-path-2026-09-06.md`。

# 个股参考价来源核查 — 2026-09-06

状态：找到了明确的逐日前收字段合同，并增加独立的来源响应检查适配器；**尚未接通或资格确认真实来源，股票输出验收未完成**。

## 本轮基线

接手时 #259 head 仍为 `f53a4fbea0cdfdfbc34f1abd34d33b1587d3b518`。main 已由独立 PR #261 前进到 `4cb2762ef67f10c80c5396e2f60f39e7fc7f80e7`。本次保留其两个 voice-pass 文件原始 blob，不覆盖并行改动；完整 CI 以整合后精确 head 为准。

## 直接核对的官方来源

1. HiThink `skills/hithink-finance/references/api/endpoints-prices.md`：仍没有逐日 `prev_price`；当前快照没有逐股历史日期，不能替代61日参考价。原先 NOT_ESTABLISHED 结论不变。
   https://github.com/HiThink-Tech/Financial-API/blob/main/skills/hithink-finance/references/api/endpoints-prices.md
2. Tushare 日线 `daily`：官方明确为未复权行情、停牌期间不提供数据，`trade_date` 为交易日期，`pre_close` 为除权昨收价；`vol` 单位为手，`amount` 单位为千元。可作为下一步真实来源候选，不是已获真实数据或原文真实性证明。
   https://tushare.pro/document/2?doc_id=27
3. 同一日线文档单列 `ah_vol`、`ah_amount`，并说明2026-07-06开始有盘后数据。缺失保持未知，原 vol/amount 与单列盘后字段分开保留。文档未明确 vol/amount 是否已含盘后部分，因此不标为“剔除盘后的常规成交”，不得相加、相减或舍弃后声称和 HiThink 的量额口径已经一致。
4. 官方 REST 示例仍为明文 HTTP，不能从“HTTPS网站”推定“HTTPS REST终点”。官方另有 HTTPS MCP 配置说明，但它是独立的 MCP 路径，不是 REST 终点认证。未向任何猜测地址发送 token，不降级明文、不关闭证书检查。
   https://tushare.pro/document/1?doc_id=130
   https://tushare.pro/document/1?doc_id=463

## 本次小范围实现

新增 `adapters/tushare_stock_reference.py`，只检查已取得的**原始 JSON 响应字节**与明确请求描述：61个已由调用方资格确认的日历交易日、个股完整代码、字段映射、重复键/日、时区与实际接收时刻、业务失败、有限数值、原始前收连续性、成交量精确乘100和成交额精确乘1000。无价格填充、无复权推导、无量额容差；盘后字段独立保留，null不变成0。

输入截止与请求寿命检查沿用股票读取的有界原则。这里的捕获时间由调用方提交，**不能认证来源身份，也不能证明历史发布PIT**。调用方不能把任意61个工作日冒充交易所日历。

返回结果始终包含：

```text
semantics = TUSHARE_DAILY_CONTRACT_CHECK_NOT_LIVE_QUALIFICATION
origin_authenticated = false
latest_quote_independently_matched = false
cross_provider_amount_scope_established = false
qualified_for_stock_reading = false
```

结果不是原股票 reader 可接纳的 reference_inputs 形状；不能通过换标签或重算哈希升级成 LIVE。未修改原 reader、捕获工作流、凭据范围或筛选门槛，不新增第二套 selector。不安装新网络 SDK、不新建数据平台。新增测试全为源合同反例与合成表格，不是股票市场证明。

## 尚缺的可执行条件

Tushare 官方 HTTPS MCP 是已找到的安全候选接入方式。仍需实际授权连接、读取该服务当前工具 schema，并取得按冻结计划执行的真实响应；不猜 MCP 工具名或把 REST schema当作 MCP工具schema。随后才能把该源接到现有 capture/replay，核对 HiThink 量额及当前报价，并在完整 CI 通过后进行有界真实附件验收。

本轮运行环境未配置 Tushare 凭据，未取得该 MCP 连接；插件检索没有返回可直接调用的连接。GitHub 工具仍未提供 workflow_dispatch 动作。本轮无股票行情/RSS/公司原文数据请求、无新股票附件上传或真实选股；读取官方接口文档不算行情采集。不要索取明文 token 到聊天，也不要改触发器来绕过手动边界。

源字段存在不等于源接入完成；源接入完成不等于当前样本能通过完整61日与量额检查。#259 保持草稿，主干不因文档/测试绿色而发布此未资格确认的功能。

SHADOW OBSERVATION ONLY
HUMAN ATTENTION AUTHORITY = NONE
RESEARCH AUTHORITY = NONE
INVESTMENT AUTHORITY = NONE

不自动进入 Research、不新增 canonical Human wake、不生成 Recommendation/Action、不改写公司判断。Sector新日/同日幂等、RSS时间资格、消费者云端接续各自仍需真实证明；漏过中间交易日先 qualified recovery。
