# 巨潮三季报预约：本次原件与核对范围

本目录原样保存source run36648293469/1的11个原始文件。运行于2026-09-30T00:02:23Z—00:02:57Z（新加坡08:02），代码0d63bab1e2b95301b764b21bbbbfb2f60b88d0fd，原结论FAILURE保留。真实取得四次HTTP200；不是四条有效预约，也不是网络／权限失败。没有重试、分页、重定向或更换来源。

## 实际结果与逐字段核对

| 证券 | 本次巨潮记录 | 首次预约 | 变更／实际披露 | 取得时钟（UTC） |
|---|---|---|---|---|
| 603986.SH 兆易创新 | 一行，证券与报告期匹配 | 2026-10-30 | 三个变更字段与实际披露字段均为空字符串 | 00:02:46.396272—00:02:49.039041 |
| 688277.SH 天智航 | 一行，证券与报告期匹配 | 2026-10-29 | 同上；不是原Relay缺失修正整列 | 00:02:49.040289—00:02:50.568262 |
| 600276.SH 恒瑞医药 | 一行，证券与报告期匹配 | 2026-10-28 | 同上；不覆盖此前Relay容量／超时失败 | 00:02:50.569569—00:02:51.680705 |
| 002674.SZ 兴业科技 | prbookinfos=null，totalRows=0、totalPages=0 | 未取得 | 原捕获按表形缺口停止；不是没有预约的证明 | 00:02:51.681968—00:02:52.661260 |
| 600598.SH 北大荒 | 本次未查询 | 不补填 | 原Relay10月29日仍仅第三方预计 | 无 |
| 002050.SZ 三花智控 | 本次未查询 | 不补填 | 原Relay两次503保留 | 无 |

原字段seccode／secname绑定证券及简称，f001d_0102为2026-09-30报告期。首次预约f002d_0102、三次变更f003d_0102／f004d_0102／f005d_0102、实际披露f006d_0102的语义沿已审AKShare stock_report_disclosure对应，本次按原键与完整行核对，未使用DataFrame位置重命名、日期补值、keep-last或排序推断。原实现：[stock_yjyg_cninfo.py@0191689d57c667b7c7a198fd0cf97316837ef311](https://github.com/akfamily/akshare/blob/0191689d57c667b7c7a198fd0cf97316837ef311/akshare/stock_feature/stock_yjyg_cninfo.py)，blob4a7bbe49a8902d1d4bd7c6bd4e271ebf8d2953a3；完整复用审阅仍在#620/5891715349，不因本次出现真实行重做选型。

三条有效行均为totalRows=1、totalPages=1、hasNextPage=false。原orgId分别为9900026561、gfbj0834360、gssh0600276，原值保留；本轮未另取组织映射表。latest_time=null，变更和实际日期为空字符串，不能改写成null、零值、没有改期或已经披露。首次预约不是永久不变的最终日期；日期只有DAY粒度，不补披露时刻、首次公布时刻或实际发布时间。查询是当前状态取得，不补历史PIT。

本次可以支持“巨潮官方预约接口返回这三条首次预约记录，证券／报告期／字段已核对”。天智航首次预约与此前Relay预计日相同，但两来源是否内部共用上游UNKNOWN，不累计独立证据数。未取得公告PDF、修订通知或完整修订历史，没有交易所第二份独立核对；不扩大为六家公司全部官方确认。原capture/receipt的date_qualification=NOT_PERFORMED、official_appointment_qualified=false是捕获阶段原值，保持不变；本节是后续人工核对，不伪改原回执。

## 原件来历与保管

来源是https://www.cninfo.com.cn/new/information/getPrbookInfo，经原有限入口逐证券HTTPS POST取得，不是Relay或其他网站镜像。请求参数、身份、scope_source精确R3、每次请求／结束时钟、安全响应头、全部返回字节分别保留。未保存可复用cookie或凭证。HTTP Date为源响应头，received_at为本客户端操作结束，不互换为发行人首发。

原GitHub artifact11069682127：6278bytes，SHA256 e6ebbc89716489ee7e306f9b28a8ea32466cbbd36d28d4f21df6e062e9309e3a。经原生下载并核外ZIP大小／digest／CRC／路径、原identity与每份response的bytes／SHA256。下列成员逐字节保留；本README不属于原artifact。Git保管原成员，不声称本目录保存ZIP封装本身；30天artifact不等于永久备份。

| 原成员 | bytes | SHA256 |
|---|---:|---|
| 002674.SZ/receipt.json | 1042 | 610e99e960866a701729117910bc3785d8d9f96010aca853b6106997f5d559c1 |
| 002674.SZ/response.body | 93 | 9df96d4a14dd4e841028b1ce9571742a85af950b573dca78339bafa4a017a32e |
| 600276.SH/receipt.json | 1067 | 3884a4675d2ea5c5b6a083c0578af274a0f5eae93adbbb4eb9b45e6291132783 |
| 600276.SH/response.body | 293 | d812f2fac08dfc92b9c37005e57619771ef7afd31fd3682f51d6b3919855f44a |
| 603986.SH/receipt.json | 1067 | 50a033264918d0fad70ed2536966a3292f8bd243d147ce4aad5901e197c685d9 |
| 603986.SH/response.body | 292 | eb23ae768a74caf7ff9e2a1ed026a3b1b5f0892af6538e920d0aef7ce816f290 |
| 688277.SH/receipt.json | 1065 | 27d1e2d9f07aede17dc785a112d9576cd71911434a37de825531d2d47939e44a |
| 688277.SH/response.body | 290 | abac69b5b08942d0f3523d221ee827c4233d848869b187c05983e498e246f5c4 |
| capture.json | 1424 | 666204fcd65cfacd374d53a036124a9214e06f70a84cfcc7141b36e894201308 |
| plan.json | 3301 | 73783fdeb1bcc5d78e3ca7d2696e8c22c920942f49f81540a0cd19bf6229da79 |
| summary.md | 540 | 578bff835ba7949660edcc430ff65828dc345eae52ec7e4d61ca00aa3f5d1e14 |

## 使用与停止边界

本次有限六对象计划已经消费，不再dispatch或rerun。兴业null表导致北大荒、三花未查询的实际停止保留；后继先评估源端null语义与这两项未查询缺口，不重新查询已经取得的三家，不建设“余下批次”管理平台。旧三次Relay失败、R3、原Human用途及来源时钟不改。

另存R4并切原唯一research-agenda，正常PR／main／publisher／固定R实际正文读取分别验收，详情归#620。仅保存有来源的预约和研究复核入口，不新增持仓、Human接受、Research、Odds、提醒或交易。Sites与#658市场日常更新独立，权限、既有调度和通知不变。Investment Authority=NONE。
