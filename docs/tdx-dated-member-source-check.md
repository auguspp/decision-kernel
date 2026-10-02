# C2：有界验证 TDX 日期成员，不再新建排名器

2026-10-02。范围与单次执行授权见 [#297/5943570283](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5943570283)，前置复用调查见 [#511/5943375601](https://github.com/auguspp/decision-kernel/issues/511#issuecomment-5943375601)。本说明不代表接口已成功、已启用生产或整个 C 已验收；实际 PR、主干、一次来源运行及回读分别记录在原事项。

## 复用与新增范围

保留 #310 的当期两成员 5/20/60 比较及 #702 的两个保存观察比较。它们不是历史各日成员数据库，但也不是尚未交付的功能。本切片只验证此前缺少的日期成员来源。

`runtime/tushare_relay.py` 仅增加 `tdx_index`、`tdx_member` 两项准入。原 blob `d2ee02a81648eafe7204a47e7f8e41b56c3c48fd` 是保留的前驱，新增接口后的 blob 为 `3f1f6eb33903de1fd77bbb9dae6e2c9470244b73`；全部函数、主机、Header 凭据、TLS、代理/重定向、30秒单次临时排队重试与4MiB响应上限不变。B2工作流的当前客户端指纹同步更新，旧研究/来源档案不改。此前文档的“保持原客户端”仍适用于传输和失败合同，不应拿前驱 blob 阻止本次明确授权的两项准入，也不构成未来任意扩接口许可。

新消费者复用 `global_market_context.validate_attempt` 的原始响应/HTTP/时钟校验，以及 `tdx_membership_comparison._snapshot` 的原读取包和成员身份核验。日期/身份/截断与目录人数的薄适配是本次新增；没有引入 Qlib、AKShare 或其他运行依赖，没有另造 HTTP 客户端、历史执行平台或排名器。

成熟实现与接口依据：此前实读 Qlib `cn_index/collector.py@be725493` 的实际调样公告方法；它是 CSI 对象，不能移植为 TDX 历史真值。官方 [TDX目录376](https://tushare.pro/document/2?doc_id=376) 与 [成员377](https://tushare.pro/document/2?doc_id=377) 本轮再次核读，支持明确交易日期；用户已购 Relay 手册列有对应接口。Relay 的兼容池是供应商声明，返回成功不升级成官方独立来源。无需另购账户或提交明文密钥。

## 固定试验，不是全量采集

`c2-tdx-members-20261002` 只包含2026-09-29、2026-09-30，以及880550.TDX（PCB概念）、880706.TDX（分散染料）。这是有目的的合同检查，不是发现质量盲样。

每日期先请求一份 `tdx_index` 概念目录（显式 `idx_type=概念板块`、所需五字段、limit1000），再对两个板块各请求一份 `tdx_member`（显式日期、板块、四字段、limit3000）。总计**2目录+4成员=6逻辑请求，最多12次HTTP**，只有原临时排队合同允许第二次尝试。没有额外能力/日历/报价/复权请求，不分页、不换源/分类或样本凑成功。

原 #702 两个固定 R 和 reading_hash 直接在模块 `NATIVE` 中保留；先分别恢复其完整根与成员原件，并运行原 `_snapshot`，再允许读取来源凭据。四次 GitHub 原件读取与金融API分母分开。不能用后来根替换一个历史根，也不能只拿当前成员作为历史对照。

每页核 code、api_name（若返回）、列唯一性、完整必要列、行形状、精确日期/板块/证券、唯一成员与截断边界。空页不是零成员；达到请求/官方上限或count不符不签完整页。目录须包括两个精确 TDX 代码、原名称及概念类型，成员数量另与相同日期目录核对；差异保留完整证券集合，不做相似名称模糊映射。

返回字段全部留在原始响应；输出只投影必要字段并列出额外列，保留可见源声明而不认证其独立性。来源错误或表格不合格停止后续请求；跨响应/跨来源差异进入明确 GAP，不自动启用生产。401/403/429及明确不可用不重试，不访问备用主机。

## 执行、留存与核验

原生 `tdx-member-source-check.yml` 仅接受手动调用，无schedule/push/source触发，复用原Relay并发组，不宣称跨所有工作流建立原子锁。精确当前main、对应独立main CI成功、owner及attempt1均须成立。`authorization=c2-tdx-members-20261002` 只允许一次调用；运行列表按该固定名称查重，第一次调用即占用，失败不能再点Run或Re-run。回执不确定先核原run，不重复调度。

业务密钥只注入capture一步；前置GitHub读取、无凭据重算、CI与报告读取不取得业务密钥。CI通过或合并不触发该金融请求。capture的来源GAP会以非零退出显示，原件和summary仍通过always附件保留；突然中断可能只有部分原件/进行中回执，不冒充完整结果。

输出包含四份原native输入、原raw响应、capture.json（独立请求时钟、HTTP状态、摘要和执行身份）、summary.json/md及成功重放时的verification.json。临时capture检查点只在该次新建目录更新，不覆盖任何历史档案。原生artifact保管90日不是永久原件备份，后继需沿确切artifact/run保存/读取，不自动登记为Research。

离线核验（不发请求）：

```sh
python -m decision_kernel.runtime.tdx_member_source_check verify \
  --root /path/to/original-artifact \
  --code-commit <actual-capture-code-sha> --run-id <actual-run-id>
```

必须先独立绑定原run、attempt、head和ZIP身份；从待验JSON自己抄hash不证明来源。重复写verification被拒，另取原始副本核验，不能改旧文件凑结果。

## 通过什么，不通过什么

只有四组的日期/身份、人数和逐证券集合都合格并匹配原native观察，才报告 `FOUR_DATED_GROUPS_MATCH_NATIVE`。其他结果报告 `SOURCE_QUALIFICATION_GAP`，不是无成员/无机会。PCB两端已知变化可用于检查回溯是否重放同一当前名单，但即便吻合，也不认证上游是否保有不可变历史版本。

两个日期不建立整段连续有效成员；后来取得的历史日期行不等于本项目当时已知。5/20/60价格路径、公司行动、经济因果/角色、自然发现价值和Brief使用均没有由本试验取得。AI Investment Authority=NONE，Sites暂停，D不启动。没有新的定时器、模型调用、Full/Odds/Watch或一般采集许可。

退出：首次真实资格核查结束后，消费其原件，不反复重跑同一pilot。保留仍被使用的离线读取器；一次性执行入口是否退出，按原owner处置，不以此默认增加长期生产义务。来源不合格时停止扩历史窗口，保留原C缺口，而非把GAP当成C通过。
