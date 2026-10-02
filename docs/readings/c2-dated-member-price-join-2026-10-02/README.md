# C2：日期成员 × 共同价格窗口，先把可用范围接实

2026-10-02。接续 [#711 实测回执](https://github.com/auguspp/decision-kernel/pull/711#issuecomment-5943925576) 与 [#297 接点](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5943930370)。本批只消费已保存输入；没有重用已消费的 pilot、查询金融接口、重新选股或升级整条 C 的验收。

## 实际结果与用途

复用两日原成员核验和已保存 K3 价格来源，在同一 2026-09-30 截止下作完整截止日成员左连接。PCB 的 238 名成员在本价格输入中没有已检查路径；分散染料 20 名成员中，善水科技一名有可复现的 5/20 日原始价格路径，60 日仍跨 7 月 14 日已报告公司行动而不可比。其余成员仅有报价，不能填成收益为零或直接删除后排名。

[可读结果](join.md) 与 [完整 JSON 的无损 gzip 存档](join.json.gz) 保留两板块、三个窗口共 **774 条成员—窗口记录**。同一证券跨窗口不是独立发现。源集合中两项原请求失败也保留在 price_source，不因未属于本截止日板块而隐去来源范围。PCB 新观察成员 301389.SZ 在 9 月 29 日名单中未出现，和其他日期没有成员观察是两种不同状态；这不是纳入生效日期判定。

5/20/60 日收益分别要求 6/21/61 个共同收盘日。本批只具备其中两天的成员观察，缺口分别为 4/19/59 天。即使该证券两端都在名单里，也不能把中间填成持续成员。终点前出现但终点已不在的成员另列为 observed_nonterminal_members，不冒充已研究完整动态组合。完整价格范围与完整日期成员范围分别报告，均成立才标“日期标签与原始路径齐全”，也仍不授予历史当时可得、实际生效成员或经济角色资格。

## 复用与边界

**Reuse Decision: REUSE + THIN_ADAPTER。** 不改 #310 原比较、#702 原成员读取或 #711 请求/重放。复用 current_state.unpack_archive/inventory/sealed、tdx_member_source_check.replay/native_inputs、hithink_stock_reading.qualify 及 sector_radar._return_over；输出沿原 create-only 两文件写入。原日历和样本资格从精确已保存消费者继承，不把本轮称为重新获取或全 K3 执行重放。可用价格路径重新核原 history/quote/actions 字节、请求、时钟与 5/20/60 比值；原不可用路径不重试或换源。

实现前核查 pandas 官方 merge 文档及 pandas-dev/pandas 的 merge 实现：精确 left join、many_to_one 唯一性与 indicator 能直接支撑交叉检查，merge_asof/forward-fill 不适合填造缺失成员。实际另用已安装 pandas 2.2.3（BSD-3-Clause）的 _validate_validate_kwd/merge 检查 774 行，771 行仅左表、3 行精确匹配；未向 Kernel 增加 pandas 依赖或复制外部代码。运行接合只是原生集合/字典的薄连接，无新排名、成员数据库、采集器或资格平台。来源/日期/公司行动含义仍由已有消费者承担，不由 pandas 认证。

参考：<https://pandas.pydata.org/docs/reference/api/pandas.merge.html>；<https://github.com/pandas-dev/pandas/blob/v2.2.3/pandas/core/reshape/merge.py>。本地核读的 _validate_validate_kwd 源码 SHA256 为 f0b9cb3f4b72134dcbaf90a453df977f6d21ea73a08b6a4b235476dd96d9fb0a。#511/5943375601 对 Qlib 日期成员的前置评估仍适用；不引入 CSI 分类或交易框架。

## 原件、执行与验证

[input-pins.json](input-pins.json) 从独立读取的 GitHub run/artifact 元数据和原回执绑定，不从候选 ZIP 自取摘要来消除差异：成员 run36951061047/artifact11203384879；价格 run36815556951/artifact11141865519。实际获取时钟分别在 10 月 2 日、10 月 1 日，不是 9 月 30 日当时执行。两份源档案依原 Actions 留存至 2026-12-31、2026-12-30；此派生结果不是其永久原件备份，也不是 R 已登记数据。

本批最小交付是离线可执行接合入口、反例与真实输出。不改 registry、生产工作流、依赖、日程、通知、Brief、Watch 或资本权限。运行以下命令需已由正常工具恢复两份精确原 ZIP，并在项目已有依赖环境执行；命令自身不访问网络：

```sh
python -m decision_kernel.runtime.tdx_member_price_join \
  --member-zip /path/to/tdx-member-check-36951061047-1.zip \
  --price-zip /path/to/stock-independent-observations-36815556951-1.zip \
  --pins docs/readings/c2-dated-member-price-join-2026-10-02/input-pins.json \
  --pins-sha256 0d2bc18dd624a4aa500c53190107a5ff0a17b772f8545038d1e0f14c828b0cf3 \
  --output /path/to/new-absent-directory
```

完整 join.json 为 168550 bytes，SHA256 a43dac31ab97520de28f7b707d84d8bc3cd1d47f1e6ce35790aab31970962fa7，report_hash 676c4199ae9173140eead943d58cb05c81d035ae2bde3907519a160ede4269ec。gzip 仅压缩重复的派生表格；不是拆分原件绕过输入限制，解压内容与 CLI 输出逐字节相同。join.md SHA256 18b74a6e5079b43dffd879dec14485778b4fcc9e1b010a8f5a75d8faca997887。本轮断网重放、独立连接和局部反例与正式 PR/full/main/发布分别记账，实际后继回执位于本批 PR/#297，不由此文预签。

## 下一证据与退出

离线接合不能补造缺失的 59 个历史成员观察或其他成员价格。后继沿已验证 TDX 日期接口，先限定一个共同窗口、声明成员完整分母、公司行动/价格口径和请求预算，再取得缺失数据；旧六请求 pilot 不重跑。未具备这些输入前，不追加角色阈值或继续扩写同类算表，不把 NOT_ESTABLISHED 当作原必需项 PASS。

此入口在后继正式日期成员/价格消费者能够承担同一职责时合并或退役；保留原件定位、读取兼容和本真实输出，不形成第二份长期状态库。C1 原模型、自然 Quick→Brief→晨报使用、C2 自然发现效果与整体 C 仍分别待验。Sites 暂停，D 不提前启动。Investment Authority = NONE。
