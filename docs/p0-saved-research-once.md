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

新入口 `saved-research-once` 手动运行一次，无参数。首先读回main与最新运行防重复。检查实际input/准入、两阶段模型调用和预算、原Funnel、真实来源与候选分支读回。仅有job绿灯不够，结果还需内容语义审阅。

本次仅生成候选/回执和artifact；**不会直接把未审阅结果写进current-state，也没有接通每日触发**。接续对话完成语义审阅后，按既有阅读引用发布到Brief。23:10只读任务不改。

官方接口依据：OpenAI structured outputs指南及openai/openai-python v3.11.0。复用现成SDK和既有source/admission/Funnel，没有新增通用agent、DAG、provider框架或真理Gate。
