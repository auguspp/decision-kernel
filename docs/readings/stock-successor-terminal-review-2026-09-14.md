# 和顺 / 广哈终局理由复核 — 2026-09-14

Status: EXECUTION VERIFIED / TERMINAL REASONS CHALLENGED / NOT HUMAN ACCEPTANCE  
Scope: `603353.SH` 和顺石油、`300711.SZ` 广哈通信，原首次业务 Pre / 必要 Quick。  
本记录不是新的公司研究、模型输出、投资判断或重新执行授权。

## 1. 精确原件与已发生的执行

先读 [#297 原执行与语义核验回执](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5659344328)
及 [本次施工前 Reuse Check](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5659538232)。
这些链接指向有界执行记录，不把普通来源文本当执行许可。

- Production run: `34807883332`，`workflow_dispatch`，attempt 1，success。
- Code: `e90d338577c8035dd82f96b2f48ad8c660b12324`。
- Work: `5d49e072b16869586f0ad87c696ddf3f593d2658`。
- Published reading: `4dadfd40136f1bd043afde4b223bbd6219986c1a`。
- Normal publisher: `34808175378`，trigger `34807883332`，success。
- Artifact: `10333852308`，26,048,878 bytes / 130 files，
  SHA256 `7b7723908e329b3eff66fa680969d5e70d1be380701292caacfce6053f433827`。

两家公司各自原件都位于上述 work commit 的：
`research_runs/candidates/stock-business/<root>/source-successor-continuation-v1/`。
必须同版本读取 `input.json`、`candidate.json`、`launch.json`、
`preflight.json`、`admission.json`、`receipt.json`、`host-receipt.json`、
`validation.json`、`funnel.json`，不要只读状态标签。

| 对象 | root | candidate Git blob | 实际阶段 / 原保存终局 |
| --- | --- | --- | --- |
| 603353.SH | `abb2949fd17018c4266c36feec7ab3fd97238a16e852b3a7ac9dedd2687fff3e` | `0a0b1944982a34b2910b06371aa90bfd99ebdeb4` | Pre 完成 / WAIT_FOR_TRIGGER；无 Quick |
| 300711.SZ | `c935a863f0e2a88b6e1a7410eae34ea47079b82e54e3aedca48682b6aa39c5dd` | `3ce485199195dce9409a547f18d2153335ec34d2` | Pre CONTINUE_TO_QUICK，Quick 完成 / STOP → DROP_FOR_NOW |

原 validator 确实返回 `VALIDATED_FUNNEL_RESULT`，该事实保留。
本次审阅不宣布全部经营描述错误；它否定的是与本轮执行事实冲突的终局理由。
Kernel 的结构、身份、时间和引用验证不等于这些理由真实。

## 2. 可直接核验的两处矛盾

和顺 Pre 理由仍称“当前来源继承状态明确为PRE_EXECUTION_FAILURE”，
并称独立财务顾问报告原 PDF 第23页必需视觉读取不可用。
然而本次实际输入包含公告 `1225530965` 第23页的 `AI_VISUAL_READING`：

- PDF SHA256: `cc3a234f7551ef02c401fae60452b891ca48ef0047aad7e26981e0f4ec7948fa`。
- Main note: `research_runs/source-readings/cc3a234f7551ef02c401fae60452b891ca48ef0047aad7e26981e0f4ec7948fa/page-23.json`。
- Note Git blob: `3a0d80122d707097b7538ff63b7386b4b694341a`，ref 为本轮 code。
- 页面文字、unknowns、render/engine 和 review_source 已在实际 Pre 输入中；
  不能把原空文本或历史缺页标记重新解释成本轮仍缺页。
- 此绑定不认证签章、人员身份、实际签署日期或法律效力。

广哈实际完成了 Pre 及必要 Quick，但 Quick 的理由仍引用
“当前读取状态明确为PRE_EXECUTION_FAILURE”，并据此否定技术完整执行。
外部市场预期、竞争者和客户证据未采集属于原声明的有界来源限制；
不得事后把所有这些资料一概提升为无限研究 / Deep 的必需输入。

两处旧字段是：
`public_context.source_successor.current_reading_item_status` 与
`public_context.source_successor.material.missing_page_reviews`（后者如存在）。
它们分别来自继承的前驱读取快照和旧 source-only 预检。
但 `source_successor` 整个对象同时包含本轮 child、request 和 current-reading 绑定，
因此既不能整块标作“当前执行状态”，也不能整块删除或视为无效历史。

本次可见结果：**HISTORICAL_PREDECESSOR_STATE_TREATED_AS_CURRENT_EXECUTION_FAILURE**。
这是输入、输出与执行记录的一致性复核，不是模型内部因果诊断。
为什么模型选择了这些理由仍是 UNKNOWN。

## 3. 现在怎样消费这两份结果

原 WAIT / DROP 作为发生过的候选结果保留，不改写为另一条路由，也不改为假失败。
本次审阅不接受它们当前的终局理由；和顺不能因此被当作正在等待补页，
广哈不能因此被当作基本面已经证伪。不得以绿色 run 关闭两家业务终局验收。

可以引用其中待进一步核对的业务初读，但必须注明原来源范围和终局理由受挑战，
不能把本说明冒充新的完整 Research 或 Human 接受。
本轮实际调用、原验证器通过、读取发布成功、研究语义接受四件事分开陈述。

## 4. 最小提示层修复与验证边界

Reuse Decision: REUSE / THIN_PROMPT_COMPOSITION。

复用原 `BoundFullContext`、完整输入字节校验和 `pre_prompt`，
仅在原完整 `public_context` 之外增加可信代码产生的字段作用域说明。
说明给出本次输入身份及文档/页清单计数；不创建“已完成”的执行状态。
原正文、反证、历史失败、来源时钟与引用继续原样保留。
SDK 无网络 Pre 预览和实际 Pre 共用同一构造器；Quick 只按原合法路由继承它。

这不是新的 Evidence、权限或工作身份。提示词构造不证明准入、传输或模型完成；
这些仍由原 host/admission/receipt 记录。也不增加自然语言关键词裁判或强制 WAIT、
STOP、CONTINUE、DEEPEN 的第二个路由器。真实当前必需来源失败依然必须留下 gap。

合成测试验证完整字节、绑定拒绝、同构请求及原条件路由不变；
真实保存输入的离线作用域回放不是模型重执行。
CI 与发布即使通过，也不能声称旧两份模型输出已纠正，或下一次模型一定正确。
工程验收进度以 #297 后续精确 head / CI / publisher 回执为准。

## 5. 合法纠错尚待 Requirements 定义，不再盲跑

两个 `source-successor-continuation-v1` 已消耗。
本记录和提示层修复不授权重新运行 `34807883332`、`34797952444`、
`34765190284`，不换日期、key、许可号或 child 规避去重，
不启动光电 / 东软的重跑，不扩为 Deep / Odds / Action / 买卖 / 仓位 / 监控。

后续需要 Requirements Management 明确：对“技术上已完成、终局理由受挑战”的
结果采用何种有界纠错方式；若有新的真实模型执行，须明确原对象、原输入/输出身份、
新表达及修订原因、执行预算、许可关系与追加留存合同，再由 Main Construction 实现。
不能复用 #361 仅针对 SOURCE_PREPARATION AttributeError 的前驱条件去重跑本次结果。
在这以前，可完成原件复核、修订说明和无模型测试，不伪造新的合格终局。
