# 招行公告增量 Pre：等待可区分证据，不追加 Quick

## 给阅读者的结论

本次确实读完了已保存的一页管理人员离任公告，不是因正文缺失而等待。该历史公告称行长助理因工作原因辞任、与董事会无不同意见并已完成交接；它没有提供足以把此次变动连接到净息差、信用成本、存款或ROAE变化的证据。因而本次 Pre 为 **WAIT_FOR_TRIGGER**，没有必要启动 Quick，更没有自动 Deep。

这不是“高管离任没有风险”，也不是对当前招行经营状况或现任高管的判断。超出披露的具体原因、分管职责、继任安排及其经济后果仍为 UNKNOWN。公司称无分歧不等于独立证明无风险。后续官方治理/风控/业务安排的实质变化，或原经营监控中的新证据，才构成重新评估的线索；股价本身不能补出原因。

## 精确执行与资料范围

执行 `p0-4b-cmb-20260910-aa9ea8d2-v1`；问题 key `aa9ea8d22fab770546fcc4b010f71be65dd353bed2fd69693424278640c81199`。已冻结 input 在 `9c7d1d6d88de87f77fc159e6ff4cd1bdc9dc447a`，blob `492df7254696f0a19bdd0ce8a51bc4f4ac765cb1`，canonical input hash `feae350cdbd3f5e5ffab51ae4bb696ad53efebf1f6173f3cf5d44daed8ac140e`，未重新命名或改写。

原 packet 在 `2bb33fdcc1771a3723bf70f41bc355971fa9c388`，blob `eed0b91cd916f215b7521834c58497ecd6c28912`，SHA256 `562abdcc134b820aab76bfdb190660a9dbea43fa9214b1e4c016f038d99697d5`。公告编号1225552023、扫描保存披露日2026-09-08；正文签署日与所述生效日2026-09-07。内部Git保存日2026-09-10不是公告发生日。事实只用完整可读叙述，不用抽取表格的布局推断；未重新下载或渲染原PDF。

`research_context` 是旧AI研究的待检验问题，不是本次新确认的基本面优势或市场共识。没有读取当前行情，没有概率或估值更新。

## 过程和原验证器

事前 execution-plan 在 `90cba999693c32e6cd1ea585703ec99bf9d24f4f` 已写入、读回。实际调用 unchanged `execute_after_admission()` 后进入正式读取；不是只填写一个PASS。`admission.json` 原样保留，里面 NOT_EXECUTED 是该函数的准入检查状态，不替代后续实际 launch；`research_execution_allowed=true` 后回调实际执行。

正式时段UTC 00:53:52.918885–00:55:13.327538，向上计2分钟；两次本地工具调用全部在candidate receipt中：一次完整来源读取，一次读入与定稿/原validator/Funnel。成功读工具数2不等于两份来源，实际原始来源一份。零搜索、零技术重试、零公司源站请求。最后一次调用的确定性验证及本地读回在00:55:13.332823结束，仍属于已计数的第二次调用。后续Git发布和CI不冒充正式研究调用。

原验证器结果 `VALIDATED_FUNNEL_RESULT`；原Funnel终止阶段 `PRE_RESEARCH`，结果 `WAIT_FOR_TRIGGER`。candidate canonical hash `e3e5134d070a79df729889302f3e86a2232c7dc20b6590a426b6013f783ab296`；Funnel canonical hash `beed8a79fe6a114434ea6feebfb35a9970f71e9e6b19c031e0823edac2df0f29`。本地Pydantic2.13.4与仓库一致；所用原准入/identity/研究模型/Funnel模块与当前main一致，已核对原blob及381f4d1f→25679a21的完整文件差异。没有修改这些模块。

## 证明范围与语义复核

准入使用连接器实际读回的精确Git文件、哈希和commit日期投影。main在启动前重新读回，回调使用这份小于60秒的观测；它不是连续实时HTTP回调、跨账户原子锁或平台原生追踪。事件是实际本地调用摘要和时钟，不记录私有思维链。输入恢复阶段曾有一次本地DNS失败和一次下载工具路由拒绝，随后通过已连接GitHub读取并校验字节；它们发生于正式研究前，不是假装零失败的全会话trace。

执行后的AI语义复核认为：对“此保存公告本身是否值得立即追加研究”的限定问题，正文已覆盖，事实/推断/未知分开，未将公司模板表述升级为无风险，WAIT的理由不来自缺核心来源，未为验收硬塞Quick。此复核不冒充独立人类研究审计或Human投资采纳。外部CI与远端读取另行登记。

## 不能由本案例推出什么

这是一条 **Disclosure origin** 的有限端到端研究候选，不能替代 Sector/Market-State origin。也不单独收口#296的完整Quick案例，不证明每日无人值守研究、原生Scheduled、Human回应/续作或5–10个交易日使用。旧兆易和CATL失败均保留。当前工作key已有处理，不自动重复研究；后续新增来源或明确续作另走原边界。

Human Attention / Research / Investment authority = NONE。没有变更生产Research登记、Belief、Odds、Human决定或Action。
