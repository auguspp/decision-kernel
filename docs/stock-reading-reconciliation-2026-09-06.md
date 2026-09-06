# 股票优先阅读收敛 — 2026-09-06

状态：单一实现收敛；完整 CI 和真实运行以 PR #259 的精确 head / Actions 为准。
**真实个股参考价来源资格仍为 NOT_ESTABLISHED；实现与合成测试不等于真实股票名单。**

## 基线和两份材料

本轮独立核验 main 为 `9e558c292878ee7406391d367dd0b10f76866e81`，#259 仍为 open draft，head `966ff79e39ba310705922b2cd3fd186df62efb69`。保留这七次提交，不重置或 force push；将 #260 的三个原始文档 blob 原样带入整合提交，以当前 main 作为另一父提交。

附件 B：`stock-attention-projection-v0-local.zip`，536888 bytes，SHA-256 `91aeb6f3ec637262cbb49b6b95d4611e3d5221fc4d71c8eb586a12af3937f21f`；patch SHA-256 `214df5d87c578a4af194d1b1f63f6f1382134ace148b913ee3533702dafd071a`。本轮已打开实际 ZIP、CRC 校验并读取五个 overlay 文件。没有 git apply，没有把 B 的两个模块整个加入仓库。

## 一套规则，不叠加两套 selector

保留 A 的 `stock_radar_reading.py`、原有公司 builder / Sector context / HiThink adapter / 手动采集与原始输入重建。保留当前强势方向入口；最新原始账本及市场复现支持的事件才标“已记录新进入行业事件”，其他为“仍强势阅读，非新事件”。零事件不是零强势方向。

保留 A 已声明的试行价格门槛：个股5日原始变化、5日市场超额、20日市场超额及至少一个相关行业20日超额为正；60日仅背景。保留节点轮询、20日市场超额／5日市场超额／代码的字典序展示，不采用 B 的另一套成交额筛选或成交额排序，不根据首次样本调参。最多3个不同代码，全部结果及省略项仍保留；881与884分别比较。

从 B 迁入严格的独立参考价窗口、当前报价一致性、无成交日期缺口、日期／身份／接收时钟反例以及可读失败页。B 的 bridge 不独立引入；真实公司来源与 Sector state 的连接继续走 A 已调用的原始 builder，不能把 B 原来模拟 serializer/source-builder 的12项测试称为完整集成。

## 已确认的真实来源缺口，禁止隐式补字段

本轮读取 HiThink 官方 `skills/hithink-finance/references/api/endpoints-prices.md`，Git blob `c8d9cc7d636dbb944404328f0e254387afb80585`：

https://github.com/HiThink-Tech/Financial-API/blob/main/skills/hithink-finance/references/api/endpoints-prices.md

该合同的历史 K 线字段为 date_ms、OHLC、volume、turnover，没有逐日 prev_price。当前 snapshot 有 prev_price，但不是61天历史；显式 thscodes 批量的 timestamp 为 null，不能变造逐股最后交易日。公司行为事件流也不是独立逐日前收参考价，更不是已经计算的每日复权因子。

所以：**能下载61个收盘价，不代表 B 的独立参考价条件已经有真实来源。** 不从昨日 close 生成 prev_price，不接受未定义额外字段为新合同，不用行业收益、旧10日dump、推算除息或任意容差代替。当前实际采集无真实 reference 输入，走到该条件时输出 `DATA_INSUFFICIENT / QUALIFIED_DAILY_REFERENCE_HISTORY_UNAVAILABLE`，不输出股价收益卡片或成功空扫描。

核心中的 `reference_inputs` 只接受显式 `SYNTHETIC_TEST_ONLY` 规范化测试窗口，用于原门槛、页面及 B 反例的回归。真实 capture 明确拒绝该参数；CLI 不提供传入合成参考价的入口。合成参考价文件、哈希和标签随测试重建保留，不能重标为 LIVE_HITHINK。真实来源需要后续独立资格审查与最小适配，不在本次发明另一套价格引擎或历史数据库。

## 首屏与失败行为

股票卡片呈现方向来源状态、自身5/20/60日表现、为什么通过条件、公司业务范围、暴露及证据保留限制、下一核查问题。所有证据位置与机制放展开层；PARTIAL 不提升。现有证据范围明确列出牧原／圆通，不把这两家公司直接当成候选，也不声称全A盲筛。

零卡片分开：无活跃方向、活跃方向无业务覆盖、资料完整但条件不匹配。失败尝试另有可读 `reading/index.html`，显示数据不足、资格不通过或请求失败；不会包含 `stock-reading.json` 成功结果，也不会留下部分股票卡片。完整原计划中的公司均列出；未完成项不称已扫描或条件不满足。响应无安全保留的原文不声称离线重新认证其原因。

原始响应、实际请求和接收时刻、输入 cutoff、来源身份及运行绑定继续保留。完整数据缺口可以从保留输入重复产生同一失败类别和同一负面页面；网络失败只能重放记录的失败，不证明远端错误原因。重哈希的伪造公司名、结果或失败页仍须由输入重建拒绝。

## 预算、安全和验收

最多16个计划公司、6个成员目录、26次 HiThink 请求，计划先冻结、每次调用核算、没有自动重试。26次不包含 GitHub 元数据或附件传输。凭据仍仅用于采集步骤，offline verify 不得收到凭据；所有时钟、身份、来源、目录安全与预算保护保留。既有两个失败的 workflow 回归只改精确 job 边界和选项列表，新增单独股票 job 的秘密、触发与只读权限断言，不删除安全要求。

本地语法检查不是完整仓库测试。本轮完整测试须由精确整合 head 的 PR CI 取得，不能相加 main 的1511、旧A的1569或B原来的78。合并需审阅完整 diff 和完整 CI；实际主干 CI 另核验。

真实验收为明确有界的独立运行和实际下载附件。可以如实取得资料不足或请求失败的负面证明，但它不等于真实合格股票输出已完成。当前来源缺口意味着合成 ready 页面不能证明这一项。普通 Sector 下一交易日追加、同日幂等、RSS 时间资格及消费者历史云端接续继续分别记账；缺中间交易日必须 qualified recovery，不桥接。

SHADOW OBSERVATION ONLY
HUMAN ATTENTION AUTHORITY = NONE
RESEARCH AUTHORITY = NONE
INVESTMENT AUTHORITY = NONE

不自动进入 Research，不新增第三条 canonical Human wake，不生成 Recommendation／Action，不改写任何既有公司判断。不增加 schedule、通用采集平台、队列、数据库或前端框架。
