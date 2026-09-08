# Radar：让已识别变化保持可发现

行为合同：`qualified-market-change-must-remain-human-discoverable`。

**Radar may detect before it understands. Price can create a Question. Price cannot create a Belief.**

**0–3 是 Attention Budget，不是 Reality Budget。** 目标是回答“市场到底发生了什么”，不是保证出现某只股票、预测涨幅或新增投资建议。

## 使用入口

正常后续 Sector 运行仍通过既有 Actions 结果页的 `Sector Discovery Radar` 摘要阅读：页首给出全部合格变化组数、首页摘要数及其他变化数。首页仅保留原 composition 的 0–3 组；“其他变化”按原次序逐组显示变化、位置、幅度、breadth 和 leader，可展开证据、未知项和下一问题。也可下载该运行附件阅读 `summary.md`（需要支持 Markdown/HTML details 的阅读器）。不新建网站或工作流。

**现在就读保存结果：[2026-09-07 的全部 12 组变化](readings/sector-discovery-2026-09-07.md)。** 这是新呈现代码对已保存 `result.json` 的历史投影，不是新的行情运行、原始 summary 或捕获版本重放证书。页面固定日期，不自动检查今天是否有更新；私有仓库链接需要访问权限。

## 精确真实 provenance 与修正后的失败定位

基线为 `9976b666de0cbd13415ac6097f6cf489a1ab9d19`。读取当前 project-state 及其指定的最新 handoff 后，直接下载并检查：

- [Sector run `34107253263`](https://github.com/auguspp/decision-kernel/actions/runs/34107253263)，captured code `26f36efdbeb62fd909b006d38b68b319a8cb2a5e`。
- artifact `10013384121` / `sector-radar-run-34107253263`，ZIP **2192995 bytes**，SHA-256 `b536adec74877527d196b48e2b1eef59a6434770a3de5f2fb8579046b4e4f0f9`。
- `result.json` SHA-256 `870833f0a71ce9c5944fc699f477cfb1e97248b594a9df52e24bc2b202ccf7a0`；其 `result_hash` 为 `271686e9171d20202dc9bd606402de8a7e76b28f7bf1a8c644a9e0f2e0995879`。
- `preparation.json` 记录 2026-09-04 → 2026-09-07，`APPENDED_NEW_COMPLETED_SESSION`，不是 bootstrap 或合成运行。结果包含20个 false→true候选事件、12个变化组（3首页+9其他）。

第4组 `group_key=881101.TI` 的主要候选为 **其他种植业 `884003.TI` / ACCELERATING_ENTRY**，另有农业综合 `884012.TI`；父行业“种植业与林业”只是已核对的当期分组上下文，不能把它也算成一个新 detector 候选。

其他种植业当日指数变化约 **+4.3515%**，成员10/10已定价、9上涨1下跌，等权中位数约+3.4713%；原 breadth 的首位 leader 是 **亚盛集团 `600108.SH`，当日原始价格变化约+10.0917%**。这不是多日个股路径、连板或交易可执行性认证。该组在 `all_groups[3]` 和 `omitted_groups[0]`，没有进入原首页3组。

**失败应准确表述，不能夸大旧系统完全没有行业阅读入口：** 原 `summary.md` 仅展示首页3组，剩余9组只提示“存在完整审计附件”，并且连首页组也没有列出 breadth leaders。旧 `context/index.html` 能查到该行业的完整状态行，但没有亚盛/600108和这些 leader 信息；`economic-company/index.html` 也没有补出这条发现路径。故缺口是“合格变化＋广度＋突出成员”未形成可直接阅读的完整变化入口，而不是底层 detector 未看到，或所有行业字段都从人类页面消失。

Stock Reader 的第二个限制是独立的：生产v2只检查已有公司业务依据且关联节点活跃的公司，亚盛不在该范围。它**不是先取 Sector 的 top3 再选股票**；两条路径分别压缩和限制覆盖，不能写成一个并不存在的串行调用链。本修复不改 Stock Reader，不凭 breadth 为亚盛补业务解释或个股条件检查。

## 最小实现与语义

只替换 `render_sector_radar_daily_summary` 的呈现实现，调用纯格式化模块 `sector_radar_discovery.py`。生产入口先用原 `serialize_sector_radar_daily_result` 验证原结果，再显示其既有字段。检测、分组、排序、0–3数量和机器结果 JSON 均不改变。

每个 primary 和 granular driver 都保留 WHAT / WHERE / WHEN、已有幅度、当前 breadth、全部已保存 leaders（不是全体成员排名）、KNOWN、UNKNOWN 和 NEXT QUESTION。未知原因固定为 `WHY = UNKNOWN`，业务联系为 `BUSINESS LINK = NOT ESTABLISHED`。公司资料在**本视图**没有接入，显示 UNREVIEWED；这不谎称其他仓库路径一定没有资料。下一问题只提示按观察时点查身份、公告、政策或共同变化，没有 LLM 填空或自动 Research。

呈现校验只保护原候选集合、primary/driver/breadth绑定和首页/其他的无损分区，不重算或放宽 detector。只有通过原流程的结果才具有原资格；拿任意 JSON 调格式化函数不构成新市场认证。

现有 workflow 已将 `sector-radar-run/summary.md` 写到 `GITHUB_STEP_SUMMARY`，并包含在原运行审计中。因此正常后续运行直接使用新呈现；不修改 workflow、触发器、文件清单、state/cache/restore/publication语义或任何预算。未来摘要字节会改变；旧 artifact及其摘要字节不改写，旧捕获版本重放仍必须使用原代码。

## 行为合同与 negative controls

`tests/test_sector_radar_discovery.py` 用合成行情输入调用**原 state-entry detector、原 breadth 和原 composer**，验证0/1/3/4/8/12组完整呈现、0组首页预算仍可发现、同组子方向leaders不丢失。没有公司输入也能展示市场事实，但不会有公司解释。

旧呈现函数原文固定在 `tests/fixtures/sector_discovery/legacy_summary_renderer.py.txt`，取自上述基线 `sector_radar_daily.py`（blob `1c80628592cb072448bcb164b3b37defe2bce8a5`）的 `_percent` 至文件末尾。旧/新比较只针对呈现，旧函数的外部结果验证器在该单元测试中被隔离；不是模拟市场资格通过。8组合成场景证明旧摘要漏列5组和全部leaders，新摘要保留8组；另一个现有daily入口集成回归使用原序列化校验并检查结果字节不变。

negative controls覆盖普通上涨未过原门槛、原强势状态不重复发新事件、遗漏/重复或增加非候选分组、扩大首页到4、错配breadth日期、权限升级、来源HTML/Markdown注入，以及未经依据的WHY文本不被采用。所有测试禁用网络；没有“涨得多就自动推送”的新逻辑。

真实历史校验另用原 `result.json`：旧冻结呈现函数重建的摘要字节与原 `summary.md` 一致；新呈现保留全部12组及20个primary/driver候选对应的leaders，原ZIP及结果字节未变。这是格式化/呈现验收，不冒充重跑原生产采集/全套审计replayer。完整PR/main CI、页面渲染和最终提交身份另在本PR回执记录，不在此预填成功。

## 边界与后续

本轮没有新的 Sector/stock-reading dispatch、HiThink/行情请求、重试、预算提高、公司原文获取、ticker特判、排序门槛修改或新 Human wake。股票单次P0和#275阅读入口、#276两家公司证据准备、独立草稿#263均不因本项改变。

`MULTI_DAY_MARKET_WIDE_STOCK_SURPRISE = NOT_ESTABLISHED`。P1仅保留问题，不实现逐股61日请求、新provider、调度平台或另一套通知系统。

**SHADOW / DISCOVERY OBSERVATION ≠ RESEARCH ≠ BELIEF ≠ INVESTMENT DECISION。Human Attention / Research / Investment authority = NONE。**

产品验收问题：如果原 detector 明天识别8个合格变化组，首页仍只保留原0–3组，其余每组能否直接读到“发生了什么、在哪里、广度和突出对象、还不知道什么”？本合同要求答案为是，不要求特定ticker入选或被推送。
