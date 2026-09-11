# P0 下一真实案例：苏垦农发的业务映射，不再重跑宿主 smoke

需求入口 #297；市场来源为 #310 已保存的2026-09-09两成员比较。苏垦601952的近期价格领先与北大荒的主要成交载体用途不同；本次解释前者的业务暴露，不重复北大荒Quick，不消费或改排公告FIFO。

## 运行范围

`research_runs/api-once-request.json` 固定唯一对象、问题、公开半年报镜像URL、9个一基页码与原市场阅读文件blob。没有运行时任意公司、URL、代码、模型或预算输入。

流程为：只创建launch标记 → 取得该公开PDF并用既有解析器处理 → 保存允许外发的公共context和原预检 → 冻结并远端保存input → **原execute_after_admission** → 一次Pre → **原validate_pre_research_transition** → 仅CONTINUE时一次Quick → **原validate_external_research_candidate/Funnel** → 固定候选分支逐文件只创建、读回 → 同run原件/日志artifact。没有模型输出代码执行或模型可调用工具。

为了让准入、分阶段预算和校验留在可信Python中，本切片复用官方`openai==3.11.0`的Responses streaming/structured output，而不是让Codex shell获得私库工作区。沿用已实测的网关和模型，但**Codex smoke不证明这个直接SDK接口的结构化/流式兼容性**；只有新案例的真实运行能证明，失败不切换URL/模型、不改输出迎合校验。

## 权限与预算

- 模型收到公开issuer页文本、精简公共市场观察、Evidence IDs和原模型字段要求；不收到Human原话、账户、持仓、整个私库或GitHub凭据。模型无shell/Web/MCP/GitHub tools。可信程序持有GitHub写凭据，仅写请求中固定候选分支和allowlist文件，绝不main/registry。此处不是声称整个runner进程没有GitHub权限。
- 一次公开PDF GET，无重试/重定向fallback；最大16MiB/200页，所选192页文档的身份不符就停。摘要/表格解析成功不认证事实真伪；不声称整份报告都研究过或后续公告完整。
- 原正式Research预算：最多6个记录动作，4个成功读取（包括保守计入的模型返回读取），零搜索、零技术重试，15分钟。来源准备、GitHub保存/读回和验证另由host receipt记录，不冒充全程6次调用。
- SDK最多两次请求：Pre一次，必要Quick一次；客户端max_retries=0，每次max_output_tokens=6000，prompt/context/schema初步字节界限64KiB；请求方界限不是对网关服务端行为和账单的独立证明。15分钟总闹钟、20分钟job timeout，不是人民币硬上限。只授权这次试用，不自动启用每日API。
- 请求ID和create-only launch不随run id变化。失败、中断或不确定的写入不会自动再跑；原失败和原始输出保留。不要Re-run，不能删标记刷成功。
- 只保存模型对外结构化回答和usage，不保存reasoning items/private chain of thought。缺口与合法WAIT分开；DEEPEN不自动启动Deep；全部投资authority NONE。

## 验收

入口 `saved-research-once` 沿用手动运行、main、无参数；当前只允许下文明确授权的v2后继首次执行，不重跑已终止v1。首先读回main与最新运行防重复。检查实际input/准入、两阶段模型调用和预算、原Funnel、真实来源与候选分支读回。仅有job绿灯不够，结果还需内容语义审阅。

本次仅生成候选/回执和artifact；**不会直接把未审阅结果写进current-state，也没有接通每日触发**。接续对话完成语义审阅后，按既有阅读引用发布到Brief。23:10只读任务不改。

官方接口依据：OpenAI structured outputs指南及openai/openai-python v3.11.0。复用现成SDK和既有source/admission/Funnel，没有新增通用agent、DAG、provider框架或真理Gate。

## 首次失败后的局部修复：提交时序与原诊断

**v1请求已在 run34490271156 失败并留下 launch，不能再次执行。修复不会解除此标记；只允许下文已授权、明确关联该失败的独立v2尝试，不删历史、不偷偷换ID或Re-run。**

Reuse Decision: THIN_ADAPTER。施工前证据在 [#297 comment5620693226](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5620693226)。直接复用现有 `Retainer.save/native`、GitHubAPI、原 admission 和原 full-host 测试，只有一个现有 runtime 的局部修改，没有新组件、依赖或 workflow。

实际预检结束于 `2026-09-10T14:37:59.261214+00:00`，其提交 `72ecf07a0bc34d88674bc411326f27a478b6d44c` 记录为 `14:37:59Z`。Git 内部提交时间以秒表示，ISO 小数秒会忽略；这不能独立证明实际事件倒序。原 `preflight.finished_at <= commit.date` 的必要条件仍失败。来源：[Git 官方日期说明](https://git-scm.com/docs/git-commit-tree)、[GitHub commit API](https://docs.github.com/en/rest/git/commits)。

修复仅在 `preflight.json` 和 `input.json` 的现有写入前，保留原完整事件时间与字节，计算不早于该事件的整秒；尚未到达时用标准库 `time.sleep` 等待一次，参数小于一秒，复查本地时钟后再写。已过边界不等；时钟倒退、不带时区或等待未推进则停止。原远端提交时钟与 admission 条件不改，服务器时钟偏差仍可能被原检查拒绝，不自动重试或回填日期。实际睡眠可能因调度变长，由原15分钟总预算限制；不是一个新的时钟同步服务或长期 Kernel 规则。

准备前把拟提交 input 原字节保存到同run附件的 `input-preparation.json`；这是诊断草稿，不冒充正式 `input.json` 或准入通过。原 `assess_admission` 返回值通过既有保存器保留为 `prepare.json`，即便拒绝也保留原原因码。成功时正式 input 与上述草稿字节一致；后续正式准入仍独立执行。没有补造失败 run 当时丢失的 input 或 prepare 报告。

回归使用实际两种精度的失败时间对，覆盖预检/正式input两处提交、时区/整秒/已过边界、时钟异常、整秒模拟Git下的原准入与Funnel、服务器倒序仍拒绝、拒绝不调用模型、旧launch继续拒绝。模拟来源/模型/写入不是新的公司 Research 或真实网关通过证明。

## 明确授权的v2纠错后继

[Human单次许可](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5621532088)与[施工前复用检查](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5627258617)分别保留。Reuse Decision: THIN_ADAPTER。仅修改既有请求、worker固定身份/前驱绑定、原测试与本文档，不新增runtime、writer、workflow、依赖或恢复框架。

当前唯一后继为 `p0-suken-api-20260910-v2`；同一 `research-candidate/p0-suken-api-20260910` 分支写入独立v2前缀。标识中的日期是案例身份，不是回填实际执行日期；选定、预检、cutoff和执行时钟仍记录真实发生时间。v1原run、文件与launch不变，v2重复启动也由原create-only阻止，不自动产生v3。

原 `identity._checked_source` 读取前驱commit `2722e676e0a7c273fd60b6c388a2941f5c1fc284` 的v1 `host-receipt.json`，核对原blob/SHA256及 `NOT_EXECUTED / INPUT_PREPARATION / formal_research_started=false / mutation_uncertain=false`。缺失、损坏或状态不符时，停止在新尝试的前驱检查阶段，不取得报告、不调用模型。前驱/许可绑定保留于现有launch和host；冻结input同时引用该确切前驱文件，但它不是研究Evidence，也不向模型发送。

对象、问题、公开报告URL/页码、市场观察、模型、权限和预算与v1相同。本后继不消费公告FIFO，不补取新行情，不证明今日公司全景，不借技术纠错修改研究路由。CI只执行无真实外部I/O的测试，不启动付费研究；合并后的一次真实运行和语义验收分别记录。现有23:10 Brief不因本配置自动修改，未审阅结果也不会自动进入读取包。
