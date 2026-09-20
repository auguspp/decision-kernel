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


## 首次真实兼容性 probe 结果与 wire 修正（2026-09-20）

run `35480185939` 在 exact main `ea15091529c42e8e439a4b883fc738c8e422ec9d` 上实际执行一次合成调用。artifact `10595691407` 已下载并核验：

- ZIP 1937 bytes，SHA256 `72496d2ebef94f1ccd3d9d7787f5ff41104950e8531d3c2950d8d8297e8c748a`；
- 仅 `pre-model-input.json`、`probe.json` 两个文件；
- provider/model/base-url 均为 `DEEPSEEK_OFFICIAL / deepseek-flash / https://api.deepseek.com`；
- 请求进入 SDK 后收到 `BadRequestError`，有限诊断为 **HTTP 400**；
- 无 parsed output、response_id 或 token usage。

该结果证明 Secret 存在且请求到达 HTTP API 边界，但不证明 WHY。

锁定的 OpenAI SDK 3.11.0 对 Pydantic Responses structured output 自动生成：

`text.format = {type: json_schema, strict: true, name, schema}`

而 DeepSeek 当前 Responses 文档的 `text.format=json_schema` 请求结构定义为 `type/name/schema`。因此下一薄修只对 **DeepSeek 精确 binding** 移除 SDK 自动添加的 `strict` 字段，保留 schema 本身、reasoning=none、工具禁用、无重试及其它原约束；历史 Sub2API wire 不变。

同时，SDK 3.11.0 在创建 `BadRequestError` 等状态异常时，会将 HTTP body 中的 `error` 对象解包为 `exc.body`。有限诊断因此同时支持解包后的顶层 `code/type`，仍不保存任意 message/body。

以上只是针对真实 400 的最小兼容修正，不创建 Chat Completions 第二执行器、不切换到 beta endpoint、不降低应用层 Pydantic 校验，也不授权公司 Research。
