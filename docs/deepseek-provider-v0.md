# DeepSeek V4.1 官方 API 兼容性接入 v0

2026-09-20。承接 #297/5746328226、5746356483。

状态：**THIN_ADAPTER / COMPATIBILITY ONLY**。本页只定义官方 DeepSeek Responses 接入与兼容性探针，不授权任何公司 Research，不改变旧广哈失败记录，不建立多 provider 路由器或自动 fallback。

## 精确 provider 身份

官方 OpenAI-compatible base URL：

`https://api.deepseek.com`

当前 DeepSeek V4.1 Flash 的 API 模型名：

`deepseek-flash`

不要填写 `deepseek-v4.1`、`deepseek-4.1` 等不存在的别名。

新凭证仅使用 GitHub Actions Secret：

`DEEPSEEK_API_KEY`

不得覆盖旧 `SUB2API_API_KEY`，也不得将 DeepSeek key 发往原 `ai.6600600.xyz` 中转地址。

## Reuse Decision

复用：

- 锁定的 `openai==3.11.0` SDK；
- 原 Responses 流式调用；
- 原严格 JSON schema 生成；
- 原 Evidence ID allowlist；
- 原 Pre/Quick Pydantic models；
- 原工具禁用、无自动 retry、无 redirect；
- 原脱敏留存原则。

`saved_research_once.model_call` 只新增显式的 provider/model/base-url/credential 参数。所有参数都有旧默认值，因此历史 `gpt-6-astra` / Sub2API 路线的调用语义不因本切片自动改变。

新增错误留存只允许有限字段：

- HTTP status（若 SDK 暴露）；
- 安全字符范围内的 request_id；
- 安全字符范围内的 provider error code/type。

不保存任意 error message/body、Authorization、cookie、key 或私有推理。

## 兼容性探针

唯一入口仍复用：

`.github/workflows/stock-business-research.yml`

手动输入：

- `deepseek-compat=true`
- `code-sha=<exact reviewed main>`
- `reviewed-question=false`
- `source-stock-run-id=""`
- 其余 recovery/prepare/successor 开关全部 false。

该 job：

- contents 只读；
- 不获得 GitHub contents write；
- 不读取公司资料；
- 不访问 Research work ref；
- 不创建 launch/input/admission/candidate；
- 只调用一次 `deepseek-flash`；
- 合成公开文本；
- `reasoning.effort=none`；
- 复用原 Pre schema 检验 Responses + strict structured output；
- 无 retry、fallback、Quick、Deep、Odds、Action。

探针成功只表示当前 SDK + DeepSeek 官方 endpoint/model/credential 在这一合成请求上兼容，不证明公司研究质量、长期稳定性、成本、Full Research 能力或任何投资结论。

## 与广哈通信失败的关系

run `35476493146` 已真实产生 launch 与稳定消费根，并以 Sub2API / `gpt-6-astra` 在 Pre 响应阶段失败。该记录保持不变。

DeepSeek 兼容性通过后，也**不能直接重跑同一个问题**。真实公司技术接续必须另行：

1. 明确引用原技术失败；
2. 重做当前必要来源/preflight有效性检查；
3. 为 DeepSeek endpoint/model 重新计算并审阅 public egress；
4. 取得新的、有界执行许可；
5. 使用原稳定根语义处理 continuation，不换 question_id 逃避消费历史。

本页不创建该 continuation，也不自动登记 current-state/Brief。

AI Investment Authority = NONE。
