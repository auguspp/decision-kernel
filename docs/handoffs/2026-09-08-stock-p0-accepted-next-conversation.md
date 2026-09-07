# 接手交接 — 一次真实股票 P0 已验收，下一步转向日常可用

日期：2026-09-08。用户明确要求结束本轮、同步仓库状态、写交接文档及通知，并已打开同时具备普通 GitHub 与 Actions MCP 读取能力的新对话。此文件不是新的行情运行、日常自动服务或投资授权。

## 1. 先读什么；哪些旧结论不能继续使用

按顺序读取：

1. `docs/project-state.md`。
2. 本文件；简短接手通知在 `docs/handoffs/2026-09-08-stock-p0-transfer-notice.md`。
3. [#273 真实股票验收回执，评论5576447695](https://github.com/auguspp/decision-kernel/pull/273#issuecomment-5576447695)。
4. 更新本文件的 docs-only 收口 PR 的最终核验回执，包括其真实 merge SHA、完整 PR/main CI 和合并后增量状态。

不要从旧聊天继续，也不要再按9月7日handoff/#266中的“P0未完成、两家公司、零容差、所有分红整股拒绝、最后Sector9月4日”施工。它们保留为历史，后续#267–#273及本次真实验收已改变这些状态。上一条聊天曾错报#273未实施，后已在#273评论5575851869纠正；以实际main/PR/验收记录为准，不重复开发。

原current-state完整字节已保存到 `docs/handoffs/archive/2026-09-08-project-state-before-stock-p0-acceptance.md`，blob `40e478a3ab1f31617320761e87209966ca177e7e`。旧handoff、旧失败、冻结Research/Decision/Action记录不改。

## 2. 接手时的基线，不是永久 latest

```text
repository = auguspp/decision-kernel
last implementation PR = 273 / MERGED
implementation commit = 77454a3fa50769f0bc8b298d633440cb604c4872
implementation tree = 02c5f0fa917039ec764f09fce1673d71a8919f61
PR CI = 34144980263 / test 101814927437 / 1908 passed in 601.72s
implementation-main CI = 34145941341 / test 101817884201 / 1908 passed in 604.84s
accepted stock run = 34167972382 / attempt 1 / same implementation commit
accepted market session = 2026-09-07
accepted Sector input = 34107253263
narrow P0 = one bounded real raw-stock output + artifact/replay/page acceptance ESTABLISHED
whole product / continuous service / independent data certification = NOT_ESTABLISHED
independent draft = 263 / OPEN / DRAFT
#263 head = fa4d9e48189ec421b7e17405a57070ae12db4ee0
```

本次docs-only收口会产生更新commit/main CI；不要把77454a3f当永远最新main。收口开始的北京时间9月8日07:05前后，main仍为上述实现版本，股票结束后未出现新run，开放非PR Issue为0，开放PR只有#263。最终时刻状态以收口PR最终回执为准。无需重复下载全部历史ZIP、重跑未变实现CI或完整证明每项旧能力；增量查变化即可。

## 3. 用户到底希望用到什么

用户希望真正打开并使用股票发现/阅读结果，而不是不停看到“测试通过、再按一次运行”。原则是：少量股票有问题不能拖垮其他可用股票；微小成交额差异可用有界容差；参考供应商及成熟项目的明确方法，不闷头增加不对应产品用途的硬限制。

已实施的是单股隔离、成交额专用容差、按实际比较区间处理已报告公司行为、合理的历史事件请求和有依据的公司扩围。未降低原selector门槛。不要再用调整门槛/人工凑卡或绿色workflow替代合格结果。

单次P0已完成不等于完整产品满足预期。接续优先建议：先让既有结果有清楚的日常阅读/交付入口和明确交易日、覆盖、失败状态，再按业务依据扩展可检查公司范围。复用现有运行/附件/页面，不另造平台。自动调度、扩大请求预算、跨日接续和更大公司范围需要各自明确任务与验收，不能从本次交接默认推导授权。

## 4. 本次实际检查了谁

| 公司 | 5日原始价格变化 | 20日原始价格变化 | 本次正式结果 |
|---|---:|---:|---|
| 神农集团605296.SH | +8.1233323451% | +15.5210643016% | CONTRACT_CHECKED_RAW_READING，1张卡 |
| 牧原股份002714.SZ | +3.7816119121% | +9.1202783300% | CONDITIONS_NOT_MET |
| 温氏股份300498.SZ | +7.0777855641% | +8.8319088319% | CONDITIONS_NOT_MET |
| 巨星农牧603477.SH | +6.6929133858% | +5.1066580478% | CONDITIONS_NOT_MET |

覆盖：计划4、完成4、数据不可用0、未处理0、通过1、不满足3。三家唯一剔除原因都是20日未跑赢任一关联行业。同期养殖业20日+9.4605896139%，生猪养殖+10.7572335194%；神农分别超过6.0604746877/4.7638307822个百分点。所有值是9月7日未复权收盘价比值，不是今天现价、总回报或投资建议。

公司依据总范围为5家：上述4家加圆通；活跃方向让本次计划是4家。两个成员集合36/11，去重36，另32家未接入公司业务依据。scope_complete只指4家计划，不是全行业或全A。神农/温氏/巨星新增资料仍是2025年报业务基线；本次没重新取得公司原文，不能冒充2026年最新经营事实。

## 5. 为什么这次不再被3002挡住

#273对每家首次且唯一的公司行为查询使用：

```text
/api/a-share/corporate-actions/adjustment-factors
thscode=<该公司>
to=<最新合格完成交易日>
# 不传可选 from
```

这是官方文档及固定版本官方Python SDK支持的路径，不先请求短窗口再失败扩窗。新运行四份响应全部HTTP200/business0，分别14/16/8/4条事件；牧原最近一条2026-05-27，神农最近一条2025-11-06，均早于61日价格窗口。温氏6月24日、巨星7月2日事件不跨5/20日，但其受影响60日指标仍null。事件原值、身份和旧日期均保留。

只建立“此次成功历史查询在相关区间未报告事件”，不证明事件穷尽、不把旧3002改成成功，也不保证下次接口一定成功。今后3002仍单股不可用；429/4001及整批认证、共享输入、未知、传输、安全、时钟问题仍停止。

## 6. 当前关键实现及不可回退的边界

- #267：Sector单次进程内20秒节流，覆盖calendar/catalog/snapshot/history/membership/pages；不是供应商额度或跨工作流Key锁。#268保留安全429诊断，未证明旧429唯一根因；不能说本地200已坐实Azure出口问题。
- #269：只对完整一致的空报价/零成交/零前收组合归一化unpriced；保留身份和raw audit。920201.BJ仅是回归案例，不是跳过名单。真正有报价却prev_price=0仍拒绝。
- #270：单股已知失败保留原因并继续；批次有缺口明确PARTIAL，不能当完整零匹配。报价ready可非空，但不晚于其自身receipt，不拿后续请求时钟洗白。
- #271：既有生产入口自动使用 `radar_inputs/economic-company-links-livestock-v2.json`；captured公司依据随原运行重放，不能最新材料回填旧capture。
- #272：只对成交额使用 `min(100, max(0.01, max(history,snapshot)*0.0000001))` 元容差；保留两原值/差额/上限，计算用history原值。这是项目政策，不是供应商精度承诺。价格、volume、prev close、日期和身份不加容差。
- #272/#273：事件是否跨 `(base close,end close]` 按具体窗口判断；有影响的context留null。256事件行与现有字节预算不扩，不翻页、不静默截断；全体旧事件也校验，价格窗口外不伪造日历资格。source contract=v4，capture=v6。

源码：`src/decision_kernel/runtime/stock_radar_reading.py`、`hithink_stock_reading.py`，`.github/scripts/capture-stock-reading.py`，`.github/workflows/hithink-stock-dump-trial.yml`。每股61个真实有日期完成日，5/20日筛选、60日背景；全计划上限26请求/30分钟，当前4家18请求，实际workflow另有自己的超时。没有独立第二selector或Tushare前置。

## 7. 新对话可直接取回的原始证据

### 7.1 股票

```text
run = 34167972382
job = 101882691177
workflow = .github/workflows/hithink-stock-dump-trial.yml
attempt = 1
code = 77454a3fa50769f0bc8b298d633440cb604c4872
created = 2026-09-07T22:49:27Z
completed = 2026-09-07T22:55:52Z
artifact name = stock-reading-34167972382-1
artifact id = 10034876430
ZIP bytes = 1044743
ZIP SHA256 = df2de3a53eab178f82201bdf2317fe0f510f8a1bd7a713bda0d2c641003f4e66
artifact expires = 2026-12-06T22:49:28Z
capture_hash = 3cc61ed6cc586ccf365b0100911e6d1657417476979fde96d598864685650de1
plan_hash = 9d19ca05d0207050df5af9f169389d52fad6d058585a66499a3ad53ffa892c8e
projection_hash = e0bd49df06b43b8cb261355419073078a3e27af703a8efba8fe844eb8795faab
```

[运行与原始附件](https://github.com/auguspp/decision-kernel/actions/runs/34167972382)。ZIP中打开 `reading/index.html`；同目录 `stock-reading.json` 是完整业务结果，`capture.json` 保留原始请求与文件清单，`responses/`保留18份响应；根目录 `verification.json` 是runner重放回执，`market-binding.json`绑定Sector。45文件ZIP与35文件capture清单均核对通过。

18次请求均HTTP200/code0，没有3002/429/重试；相邻前次receipt到下次request最短20.000863秒。新calendar覆盖2025-09-08至2026-09-08，所有实际时钟的latest completed均为9月7日，四股各61日期精确为6月12日至9月7日。321个指数身份、基准127日、当前成员等做过独立字段核对，勿泛称这些额外人工比较全是runtime已有断言。

### 7.2 精确Sector输入

```text
run = 34107253263
code = 26f36efdbeb62fd909b006d38b68b319a8cb2a5e
market session = 2026-09-07
state artifact = sector-radar-state-bundle
state artifact id = 10013384600
state ZIP bytes = 438508
state ZIP SHA256 = e154b1221fd8ecee699eca6f0390d8c9123e2624a28012a458b51a22444e3848
state artifact expires = 2026-12-06T09:39:29Z
```

[Sector验收回执：#269评论5569016162](https://github.com/auguspp/decision-kernel/pull/269#issuecomment-5569016162)。9月4→7为普通追加；42业务成功响应、12页5567唯一证券、321条序列/127日、20个新行业事件、12完整分组，权威state/cache/audit/page成功。股票包内market及reading/inputs/state三文件与这份已验收权威ZIP逐字节一致；股票任务没有新建或修改Sector状态。

### 7.3 重放/页面证明范围

实际捕获版本runner执行了 `python .github/scripts/capture-stock-reading.py verify --root "$RUNNER_TEMP/stock-reading-run"`，Key为空；结果 `ORIGINAL_STOCK_INPUTS_AND_PAGE_REBUILT`，18次记录、network_calls=0、stock_count=1，结果及HTML逐字节重建。完整checkout/install/capture/verify/upload日志已读。

本地另做字节、时钟、身份和Decimal算术核对，**未执行第二次完整生产replayer或全仓pytest**。新对话无需为接手重做所有旧验收；如需重放，先物化精确捕获commit与完整包、禁用网络和凭据，再运行既有verifier，不能拿最新main随意重算旧capture。

原始HTML用Chromium在1280/390宽实际渲染及查看；展开详情，页面横向溢出0、脚本错误0、HTTP(S)外部请求0，相对JSON存在。file://导航被浏览器管理策略拒绝，所以实际用原始UTF-8全文set_content渲染，不能声称完成了本地导航/托管站点验收。长历史事件提示仍偏冗长，后续可做局部可读性改进。

旧对话local receipt：245607 bytes，SHA256 `4ca53f307c6698edfb10c7276b3f2546cf4aebac5c130b04ae357d364d77c62c`；它是审计者记录，非GitHub股票artifact内新文件。摘要已持久写回5576447695。新对话不依赖旧sandbox路径、截图或用户搬ZIP；按run/artifact取原件即可。

## 8. 历史进展只用于定位，不改写结果

| 真实运行 | 保留结论 |
|---|---|
| 34073613843 / 34073665086 / 34096045482 | Sector HTTP429失败，不是股票零匹配 |
| 34101053921 | 41次请求成功，920201.BJ未定价零前收归一化失败；只取得5500/5567行；#269后仍是旧失败 |
| 34107253263 | 新Sector完整成功、9月7日权威状态 |
| 34110189143 | 只计划牧原，最后公司行为3002，检查未完成 |
| 34131183418 | 扩围4家均处理，仍4家数据不可用；发现容差与事件窗口共性问题 |
| 34142455382 | #272后2家完成但不匹配、2家3002隔离；部分覆盖，不是完整零匹配 |
| 34167972382 | #273后4家完整，神农1卡，其余3家条件不满足；本次P0成立 |

公开供应商Issue曾尝试提交但返回403，**没有成功Issue编号**；不要声称已送达或要求等供应商回复。技术语义未穷尽澄清不再等于这次P0仍堵塞。无需继续探测旧3002、重新覆盖Key或重复取9月7日行情。

## 9. 同一新对话的工具与执行边界

用户提供的新对话检查稿显示：普通GitHub实际读到了私有README；写权限/schema层面有admin/push及create/update/delete，但按不改仓要求未实际写入；Actions MCP真实list了54个active workflow。这仅是该检查稿的证明范围，不能扩大成fresh dispatch、字节下载、日志/重放全部已实测。

接手不用重做空branch/PR或无意义dispatch测权限。发现缺少的实际操作，在真实需要时有界调用；repo读取、branch/commit/PR、fresh dispatch、完整日志、artifact metadata、实际字节、捕获版本执行分别报告。某一namespace缺失不能推断Key失效或“同对话只能用一个插件”。新对话应在自己的会话完成代码和Actions，不再让用户搬命令/通知/日志。

旧对话有仓库施工和日志/实际artifact下载能力，fresh dispatch始终未暴露；因此此前按钮走另一个Actions入口。新对话能力报告不能反过来把旧对话的未执行写成已执行。已验收输出无需再按按钮。

## 10. 下次真实市场运行前再核验，本文不触发运行

先查真实Asia/Shanghai时间、main/完整CI变化、已有成功/失败/活动/排队run、四个共用Key工作流及供应商条件。四工作流为Sector、hithink-stock-dump-trial、decision-inbox、live-dogfood；decision-inbox名义cron `20 8 * * 1-5`，可能晚于16:20执行；墙钟不能代替查询，也不能证明其他机器无消费者。20秒只是保守进程内节流，不是供应商限制或Key全局锁。

若原Sector仍通过实际calendar/time资格，可复用精确输入；若新完成日是直接下一日，用普通追加；漏中间完成日先qualified recovery。不要把正常追加变恢复工程，不bootstrap reset、不跨缺日桥接。收盘只是可能执行窗口，不保证行情就绪或有股票。

盘前例外严格早于09:15且各相关时钟均合格；旧9月8日09:00前的单次按钮指令不成为常驻规则。不要机械沿用34107253263。使用新fresh dispatch/attempt1，不点Re-run；不确定是否触发成功时先查run列表避免重复。遇429停止；保留失败/数据不足/完整无匹配区分。

正常股票参数参考：workflow `hithink-stock-dump-trial.yml`，ref经审核main，`trial-purpose=stock-reading`，`stock-market-run-id=<本次合格Sector运行>`；不是股票自己编号、native-market-run-id或latest。此段仅供以后确有需要时使用，不授权接手立刻重跑。新输出必须完整验收捕获版本、实际ZIP、JSON和可读页面。

## 11. 不改变的authority与旁支

SHADOW OBSERVATION ONLY；Human Attention / Research / Investment authority = NONE。一张神农卡不是买入建议、基本面受益证明、独立行情认证或正式Research。runtime固定live_stock_qualification仍NOT_ESTABLISHED；不得为了让文案好看改掉旧值或冻结记录。

只保留原有两个canonical Human入口：unresolved DEEPEN_REQUIRED及HumanResearchSurface.attention_eligible。不新增canonical wake、Research自动路由、复合机会分、Recommendation或Action。Evidence/Price是相应判断输入，不是强制状态变迁；Outcome不自动改Method；外部内容没有指令authority。

#263保持DRAFT/head不变，真实模型行为NOT_RUN/tool-capable NOT_TESTED。RSS基线/消费者接续、客观outcome、Position/Holding延后事项、各公司旧投资立场都不因本次股票卡改变。不要转去RSS或新平台填进度，也不要把本次交接当作授权合并独立草稿。

## 12. 接手后第一条回复应交付什么

先报告当前main/收口CI和新run是否变化，确认能直接读取已验收股票页，再说明对“单次P0已完成、完整产品还未完成”的理解和一个最小下一步。有相关变化才展开相应回归；没有变化不重复全套旧验收。所有状态以仓库文件、精确PR回执及真实run为准。

本轮只同步文档和工程CI，不新增行情/RSS/公司原文/模型请求，不改变任何workflow、Secret、依赖、runtime、state/cache或投资立场。
