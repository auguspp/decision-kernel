# 股票读取回到现有 HiThink 路径 — 2026-09-06

本次纠正“必须新增 Tushare 连接才可继续”的执行前提，不更换用户已配置的 HiThink，不索取明文密钥。`HITHINK_FINANCE_API_KEY` 仍只在既有 GitHub Actions 采集步骤注入。Tushare 检查器是前次未接线的候选研究，不是当前股票输出依赖；其历史记录保留。

## 本次数据合同与上一版的区别

上一版 v1 把 B 的逐日独立前收参考价窗口作为所有股票卡片的先决条件；真实采集却不提供该输入，因而恒定卡在数据不足。这不证明 HiThink 失效，也不是用户必须购入第二家数据源的依据。

v2 仍只计算自身原始收盘价比值 `close[t] / close[t-n] - 1`，n=5/20/60。它不计算含分红收益、复权回报或执行盈亏。61个逐日原始收盘价是比值的必要输入；61个独立逐日前收字段不是该算式的输入。两种校验合同明确分开，不把“未做历史参考价核验”伪装成“已通过”。

HiThink 官方合同已重读，文件 `skills/hithink-finance/references/api/endpoints-prices.md`，Git blob `c8d9cc7d636dbb944404328f0e254387afb80585`：
https://github.com/HiThink-Tech/Financial-API/blob/main/skills/hithink-finance/references/api/endpoints-prices.md

- 每只股票显式请求 `historical`，`interval=1d`、`adjust=none`、完整起止时刻。默认 forward 不采用。历史响应未保证回显 thscode/interval/adjust，身份绑定到明确请求；若实际有回显且冲突，拒绝，不覆盖字段。
- 严格要求与已核验 Sector/calendar 窗口相同的61个完成交易日，明确午夜日期键、OHLC合理性、正成交、无重复/缺日/额外日及有限数值。日历仍由现有流程验证，不生成工作日日历，不跨缺日。
- `data.timestamp` 只保留为上游就绪时刻；真正行情日取个股 K 线的 `date_ms`。周末就绪时刻不能改写行情日，未来就绪时刻拒绝。
- 再请求同一代码的最新快照，必须精确匹配最新日线 OHLC、成交量、成交额，且实际快照 `prev_price` 等于上一日原始收盘。不填字段、不添加经验容差。显式快照的 timestamp=null 保持原样；它没有逐股交易日期，不虚构独立日期认证。
- 同一来源、同一代码、同一窗口请求公司行为事件。返回身份、事件日期和字段必须合法；窗口内有任何已报告事件即停止该完整尝试的股票展示，不自行计算复权因子。空列表只称“本接口未报告”，不是所有公司行为已被独立排除。未报告事件及历史参考价未核验的限制在卡片可见。

B 的独立参考价检查与反例继续保留在显式 SYNTHETIC_TEST_ONLY 路径；真实 capture 仍拒绝这些规范化测试输入。只有一个 selector，观察门槛、节点轮询排序、60日背景用途、881/884分开比较均保持不变。没有修改旧 dump 资格或冻结的公司行为来源证明。

## 实际接线，不是新增一个未使用的检查器

`stock_radar_reading._observe` 在无测试 reference_inputs 的正常路径实际请求历史、当前快照、公司行为，再计算同一股票观察结果。既有 `capture-stock-reading.py` 的实际 CLI 已连接此路径，原输入复制、状态绑定、请求/接收时钟、负面页、原始输入离线重建及附件工作流继续使用。

计划在首次调用前为每家计划公司预留3次请求，总上限仍26：`4 + directions + 3 * issuers`。超限失败，不先拿前三只。当前公司依据仍为牧原/圆通两个已接入案例，实际计划由活跃方向及公司 builder 产生，不能人工点名。取数失败/资格不符时不发布部分名单，其余计划项明确未完成，不冒充已扫描。

网络步骤复用现有 dump transport 的 session 与响应长度检查：固定 HiThink HTTPS 域、禁跳转、禁环境代理/netrc凭据、有限字节及超时、无自动重试。股票专用解码保留十进制字面量为字符串，并拒绝重复 JSON 键及非有限数值。附件明确保存解码后响应，不声称原始 wire bytes。

## 验证与真实验收边界

本地只运行新纯输入检查的专项测试与语法检查；完整集成与全部仓库测试必须以本次新 head 的实际 CI 日志为准。旧全仓结果不借给新提交。B 的安全反例未删除，三项原来断言“没有独立参考价就永远失败”的用例改为直接测试独立参考价合同／真实快照缺件，保留原来的缺件、禁补字段和可重建失败页保证。新增真实 builder、capture、replay 的 HiThink 形状集成测试，行情仍为合成且网络禁止。

完整 CI 和精确 diff 通过后才合并；然后进行一次有界真实输入和实际下载附件验收。无实际认证请求就不宣称密钥失效；没有真实运行不宣称自动筛选已证明。仅需现有 GitHub HiThink secret，不要求 Tushare。会话工具缺少 workflow_dispatch 是执行入口限制，不是行情供应商失效；不得以修改 push 触发器或 Re-run jobs 绕过它。

股票读取不运行 Sector producer。普通 Sector 下一交易日追加、同日幂等、RSS时间资格、消费者历史云端接续仍分别取得真实证明；漏过中间完成交易日先 qualified recovery，不桥接。SHADOW OBSERVATION ONLY；HUMAN ATTENTION / RESEARCH / INVESTMENT AUTHORITY = NONE。无新增 canonical wake、Research、Recommendation、Action 或公司判断改写。
