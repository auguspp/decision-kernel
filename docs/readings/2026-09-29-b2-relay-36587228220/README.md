# 六对象三季报预约 · 实际取得与剩余缺口

截至原第二次捕获结束2026-09-29T15:04:12.835249Z。本页合读两次明确范围的真实来源尝试，不是第三次查询，不是官方预约认证或完整B2交付。报告期均为20260930。

## 已取得什么

**天智航688277.SH：第三方Relay记录预计2026年10月29日披露，实际披露日期为空，修正历史字段缺失。** 该行来自[原首轮捕获](../2026-09-29-b2-relay-36585190686/README.md)，HTTP200/code0/count1，ann_date20260924。请求明确包含modify_date，响应没有此列。缺失不当null或无改期；没有披露时刻、没有本次官方预约表或三季报原文核验，不能升级为官方已确认日程。

**恒瑞医药600276.SH：已尝试，但没有取得预约记录。** 首次HTTP503，原46bytes正文为upstream_pool_exhausted。原客户端按既有规则等待30秒后仅再试一次，随后TRANSPORT_TIMEOUT，没有第二份响应体或HTTP状态。最终TEMPORARY_QUEUE，源run失败，不是没有预约、授权拒绝或字段缺失。

**兴业科技002674.SZ、北大荒600598.SH、三花智控002050.SZ、兆易创新603986.SH：两次范围接续后仍未查询。** 第二次因恒瑞容量/超时失败停止后四项，全部保留NOT_QUERIED_AFTER_STOP，不记作空表或零条预约。

天智航原FOLLOWED和后五家ODDS_WATCH用途不改；没有推断持仓、接受、研究触发或交易。旧R2里的官方日期未知不由这些第三方/失败数据抹去。

## 本目录保管哪些原件

五文件是源artifact11041474065的完整成员字节：600276.SH/attempt-1.body、600276.SH/receipt.json、capture.json、plan.json、summary.md。README是本次人可读说明，不是源API输出。原ZIP经GitHub原生下载，3229bytes，SHA256dc2357e2ea8fc7294fa802abc126833870b12a3a0957ebbe2f771986e90aea0a及CRC已核；这里保存成员而非ZIP封装。

原source run：https://github.com/auguspp/decision-kernel/actions/runs/36587228220 ，workflow_dispatch/main/attempt1，M=140cafb02912b05b38b6d053b874260d92933617，起止2026-09-29T15:03:13—15:04:17Z，结论FAILURE。前驱run36585190686/1没有重跑，天智航没有重复请求。

首个实际HTTP时钟15:03:30.033020—15:03:32.389027Z；第二次超时回执中的requested_at/received_at由原客户端在异常处理时记录，不能当第二次网络请求的精确起止或微秒延迟证明。原值原样保留，不回填新时钟。具体内部上游没有返回，来源身份仍是第三方Relay，不冒称官方Tushare/交易所。

| 原件 | bytes | SHA256 |
|---|---:|---|
| 600276.SH/attempt-1.body | 46 | d02cd52a88b58c8ba349ed8fe4a4ed20a7e1b84eec3ba2e153564daa6af3e18f |
| 600276.SH/receipt.json | 1764 | aeeccd5de74145d0e648847588315a84fde53553ee9df6464cf7843ee20791d1 |
| capture.json | 1358 | 40f406ef7fcceabc14c09b5a74c3f300d8867d3e80ef4e9bc9f1053638b5d909 |
| plan.json | 2803 | 434fcd0f53364269cd5239a847334c90fdbb09a0edc32a29879fa7abe5c1606d |
| summary.md | 485 | ab4fa3330d93074804695495f630518e1305b443196dfa653ce0917c1cee4056 |

## 官方核对与接续边界

独立巨潮核对沿已审AKShare getPrbookInfo请求逻辑，收窄为688277/2026-09-30/科创板/单页100；本地一次HTTPS POST在2026-09-29T14:57:05.134441—.136170Z遇ConnectionError，没有HTTP状态和响应正文，不是源站403或没有预约。没有安装AKShare、增加凭据或切换主机。此失败不否定已保存的第三方行，也不为它建立官方资格。

本轮源请求到此停止，没有后台重试、无限等待或换源冒充本次成功。两次原失败保留。后继从#620的实际许可及这两份原件恢复，不能直接重放“余下五家”的旧范围：恒瑞已真实尝试，后四家仍未查询。需要新的有界来源处理计划；不新购服务、不索取明文Key、不改原Relay、既有任务、Sites或通知。

该目录是原生Git历史档案，保存/精确读回与main合并、用途登记、发布R读取分别成立。本次没有改唯一research-agenda引用，正常近期清单仍指R2；六对象官方预约、真实改期链、完成版新清单与其发布验收仍未完成。原BLS、Human及Watch记录保留。Investment Authority=NONE。
