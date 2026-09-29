# B2 四对象接续 · 原始响应与取得范围

本目录保管source run36591598716/1的全部十个原始文件。run为workflow_dispatch/main/attempt1，代码7c806b4e9edfd2572e92ea60cebad57cfc522735，2026-09-29T15:37:19Z开始，15:38:34Z结束，原结论FAILURE不改。原计划来自第二次失败后仍未查询的四家，不是重查天智航或恒瑞。

兴业科技002674.SZ：HTTP200/code0，六列齐备，items=[]/count0，表示本次空返回而不是无预约。北大荒600598.SH：HTTP200/code0/count1，ann_date20260924、end_date20260930、pre_date20261029、actual_date=null、modify_date=null。三花002050.SZ：两次HTTP503/upstream_pool_exhausted，中间仅原客户端30秒一次重试；未取得预约行。兆易603986.SH：其后停止，NOT_QUERIED_AFTER_STOP。

北大荒的修正列存在且值为null，与首轮天智航修正列缺失不同；两者都不证明没有改期。日期仅第三方Relay声明，没有巨潮／交易所独立核对、实际披露材料或完整修订历史。没有研究／Odds／Human投资接受、持仓或执行推断。

来源固定为既有pcd.mobcvb.cn/tushare/pro/disclosure_date；原客户端blob d2ee02a81648eafe7204a47e7f8e41b56c3c48fd不变。请求报告期20260930、每对象limit100、显式六字段含modify_date、不分页；实际三次逻辑调用、四次HTTP。JSON request_id与HTTP X-Request-ID分别保存；正文detail里的省略号是来源返回的原值，不是本次截断或补写。未见可核的具体内部provider身份，不冒称官方Tushare。

原artifact11044091840为5809bytes，SHA25662ed37dd4d35405f7f76088873a46def2643880ad80b54bf0604e9409f7a97d3；通过GitHub原生下载，外ZIP大小/digest/CRC及十个成员已核。本目录保存完整成员字节，不是重新序列化的响应，也不宣称保留了ZIP封装本身。README为本次说明，不属于源artifact。

每个receipt绑定原请求、每次响应body的字节数/SHA256、安全响应头与原时钟；计划、capture及summary也原样保留。证券/报告期/返回值和可提供日期的格式已人工检查，不回写原date_qualification=NOT_PERFORMED，也不以格式合格证明源站真值。原捕获截止2026-09-29T15:38:29.820125+00:00；归档时刻不是来源时刻。

| 原文件 | bytes | SHA256 |
|---|---:|---|
| 002050.SZ/attempt-1.body | 46 | d02cd52a88b58c8ba349ed8fe4a4ed20a7e1b84eec3ba2e153564daa6af3e18f |
| 002050.SZ/receipt.json | 1915 | 9895a36d13c19a6cc1a6c899d837c11845be96bb376c0ae0229f2096ef7a5b05 |
| 002050.SZ/attempt-2.body | 46 | d02cd52a88b58c8ba349ed8fe4a4ed20a7e1b84eec3ba2e153564daa6af3e18f |
| 002674.SZ/attempt-1.body | 227 | ce3458ebfe3d553b22c1eebe92f553b69dd56a6993b1aa2394711c001cc11795 |
| 002674.SZ/receipt.json | 1684 | 52cbd03f8b4c3a123d2cceb2bde14f47cee169b9c1685f7007060b199d7950b3 |
| 600598.SH/attempt-1.body | 283 | 83f617db8f7393c8b2ca312636e6298fcdbc820c793f0060bebfcedba4e80f36 |
| 600598.SH/receipt.json | 1908 | a696f999bc7544b9a121270297864ae8ddf92263aa1624e79b69ba10105cd3f5 |
| capture.json | 1320 | 1de44992b409eccb3bb3e6eac28e0cbc1723e77aaa30cfbb4747c93218968e5f |
| plan.json | 2472 | f38520a3c31aeab3b388081e30b532a36c2343f57f0cbef203d493bc22e725ec |
| summary.md | 472 | 0c56325ce2b6955b5b80907754c6d7d6d077fb599ddbf25522a6bb7d44f8b7ab |

明确前驱为[第二次原始捕获](../2026-09-29-b2-relay-36587228220/README.md)，该capture.json的SHA25640f406ef7fcceabc14c09b5a74c3f300d8867d3e80ef4e9bc9f1053638b5d909；其更早天智航捕获仍保留。三次原失败不合并成成功批次，不生成第四次请求或后台重试。后继不能重放本次四家计划：只有兆易仍未查询；其他未取得项各自属于已发生的失败或空返回。

可读清单沿唯一research-agenda另存R3；本目录的保存、main采用、用途登记、自然发布和固定R实际读取分开验收，当前结果读#620后继回执。原R2、BLS、Human、Watch与Sites均不因本原件归档改动。原artifact30天保留不等于永久备份；Git保管不保证防删除或平台永久可达。Investment Authority=NONE。
