# Reviewed Question 技术接续 v0

2026-09-20。承接 #456/#457、run35476493146、DeepSeek 兼容性验收 #297/5746790291，以及施工前 Reuse Check #297/5746815465。

状态：**THIN_ADAPTER / DEFAULT DISABLED / NO EXECUTION AUTHORITY**。

## 目的

只解决一种已经发生的真实情况：

1. 一个 reviewed Radar question 已完成原输入准备和原 admission；
2. 已写入稳定 question root，正式 Research 时钟已经开始；
3. Pre provider 调用发生技术失败；
4. 没有得到 Pre 结果、没有 Quick、没有业务终局、没有 Human 语义接受；
5. 原 root 因 create-only / no-retry 规则已经永久消费，不能删除或重开；
6. Human 明确要求在新的、已验收 provider 上做一次有界技术接续。

它不是自动 retry，也不是把旧失败改称“没运行”。

## Reuse Decision

**THIN_ADAPTER**。

复用：

- `stock_question_host._question_inputs`：同一 question/context/reading/source scope；
- `reviewed_question_input.prepare`：原问题声明与 source binding；
- `external_research_admission`：原 preflight/input/readback/admission；
- `saved_research_once.research`：原 Pre → 条件 Quick → validator；
- `Retainer`：原 create-only Git 留存；
- `stock_source_successor_continuation` 的 predecessor/child/no-auto-retry 模式；
- 已验收的官方 DeepSeek exact binding。

不引入 Temporal、Argo、Dagster、Prefect、第二 Funnel、provider router、fallback、scheduler 或 Agent/DAG。

GitHub Actions 官方 re-run 仍不是合法路径：它复用原 run 的 `GITHUB_SHA/GITHUB_REF`，不能建立新的 provider egress、fresh preflight 或 Human permission。

## 稳定身份

父 question root 仍由：

`canonical_hash({security_id, question_id})`

唯一决定，永远不变。

技术接续只能写入固定 child：

`<parent-root>/technical-continuation-v1/`

execution id：

`<parent-execution-id>-technical-continuation-v1`

revision、run、provider 或 execution rename 均不能生成第二个 child。

child 任何文件已经存在时，不再调用模型，只返回：

`EXISTING_QUESTION_CONTINUATION_REUSED_NO_EXECUTION`

该状态只证明已有结果或部分尝试，不证明完成。

## 前序失败门禁

continuation request 必须绑定：

- 原 failed workflow run identity；
- 原 Actions artifact identity；
- 原 work commit；
- 原 parent execution/root；
- parent 下的：
  - `host-receipt.json`
  - `candidate.json`
  - `receipt.json`
  - `validation.json`
  - `launch.json`
  - `input.json`
  - `admission.json`

runner 从最新 work tree 重新确认这些路径的 Git blob 未变，同时读回固定 predecessor commit 的原字节。

仅接受这种 predecessor 语义：

- `EXECUTION_GAP`
- `INCOMPLETE_TECHNICAL_FAILURE`
- formal Research 已开始；
- mutation_uncertain=false；
- automatic_retry=false；
- Pre 单次调用失败；
- 无 Pre result；
- 无 Quick；
- 无 funnel result；
- 原 admission 为 `RESEARCH_EXECUTION_ALLOWED`；
- 原 parent 没有 `pre.json` / `funnel.json`；
- no semantic acceptance。

当前实现还要求历史失败与 run35476493146 的事实类型一致：旧 provider `gpt-6-astra`、Pre `PermissionDeniedError`、无返回文本。

这些检查只认证“这个 child 是哪个技术失败的接续”，不证明 provider WHY。

## Source / preflight

question 和 MODEL_CONTEXT 仍必须是原精确保存字节。

continuation 不重新获取公告，不自动查询最新披露。

新的 preflight 可以基于重新读取的 retained original artifact，但必须明确：

- STATIC source classes；
- 实际 recheck 时间；
- retained artifact / file identity；
- 原 PDF SHA；
- 新的有限 `valid_until`。

这只证明冻结原件在本轮重新读取时仍完整可用；不是源站当前可达、最新公告穷尽或当前资金余额认证。

原 `stock_research_sources.recheck` 继续在每次 egress 前验证保存 page representation。

## DeepSeek egress

continuation 只允许当前已验收 exact provider tuple：

- provider: `DEEPSEEK_OFFICIAL`
- base_url: `https://api.deepseek.com`
- model: `deepseek-flash`
- credential: `DEEPSEEK_API_KEY`
- reasoning: `{"effort":"none"}`

egress digest 绑定：

- normalized Pre prompt；
- 全部 source refs，包括 predecessor lineage；
- budget；
- system hash；
- provider / endpoint / model / credential binding；
- max output/input limits；
- Pre/Quick schema hash；
- DeepSeek 实际 wire text.format hash；
- conditional Quick 规则。

Quick 仍只能在原 Pre validator 确认 `CONTINUE_TO_QUICK` 后执行，实际 Pre 与 canonical hash 在 runtime 加入 prompt。

## Provider identity retention

`saved_research_once.research` 增加两个可选 label 参数：

- `provider_event_prefix`
- `model_or_executor`

默认值仍是历史 Sub2API / gpt-6-astra，所有旧调用保持原语义。

continuation 显式写：

- `DEEPSEEK_RESPONSES:PRE/QUICK`
- `trusted Python + DeepSeek Responses / deepseek-flash`

这只是正确记录实际 provider 身份，不是多-provider framework。

## 唯一手动入口

仍复用：

`.github/workflows/stock-business-research.yml`

新增显式 boolean：

`reviewed-question-continuation=true`

同时必须：

- workflow_dispatch；
- main；
- attempt1；
- exact code-sha；
- reviewed-question=false；
- deepseek-compat=false；
- source-stock-run-id 为空；
- recovery/prepare/source-successor flags 全 false。

自动 workflow_run 不选择 continuation。

## 激活与执行分离

当前 `research_runs/stock-question-continuation-request.json` 默认 disabled。

真实激活必须另行 reviewed main 物化：

1. fresh retained-artifact preflight；
2. exact question/context refs；
3. exact predecessor refs；
4. DeepSeek-specific egress hash；
5. new Human permission。

实现 CI、synthetic tests、旧 #457 permission、DeepSeek compatibility success 均不能替代这五项。

真实执行后仍只有 candidate/validator 结果；Human acceptance、Brief/current-state registration、Odds/Action/Watch 都是后续独立步骤。

AI Investment Authority = NONE。
