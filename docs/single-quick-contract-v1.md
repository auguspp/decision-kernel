# Single Quick：版本合同与共享执行（R4-1）

`runtime/single_quick_contract.py`提供纯数据、机械验证、历史分派、只读投影及非执行Full交接；`saved_research_once.py`的原循环及`reviewed_full_input.py`的原完整输入/SDK检查已增加显式单Quick能力。遵循[成果边界](research-outcome-contract-v1.md)；不是第二研究引擎，也不是R4-1整体完成或生产启用。

## 版本与责任

输入复用ExternalResearchInputPacket schema 1，显式绑定`method_version=single-quick-v1`和`prompt_version=single-quick-outcomes-v1`。新候选schema 2；旧research-funnel-v1候选schema 1仍由原模型/验证器解释。raw读取检查明确版本组合；未知/混合版本、重复JSON key拒绝，不尝试另一parser。不修改任何旧字段、哈希、预算或消费台账。

QuickAssessment是模型内容，不含模型自算hash/cutoff/许可。主解释覆盖why-now、公司联系/重要性、既有研究关系等责任，形式自由；结构化claims继续复用ResearchClaim。反证检查说明、未知、业务route/理由和必要的下一步分开，不将Pre和Quick原字段全集拼接。

Full候选须有来源支持的观察和明确调查委托（问题、重要性理由、当前可做的工作、可改变/推翻判断的检验）。不强制预期差或相反FACT；诚实INFERENCE可保留。WAIT须有未来触发；UNKNOWN可以为空，数量不用于质量打分。代码仅验证结构与一致性，不证明经济联系、重要性、反证充分性或研究价值。

SingleQuickCandidate由宿主生成，复用Discovery、Receipt、Evidence及已有身份/预算/工具/来源处置校验；完整结果要求assessment而非Pre，缺口不能携带正式业务route。原始非法输出由原model_call先保存；本纯合同模块本身不保存文件或运行模型。

## 共享执行与完整输入

`initial_prompt`复用原问题/观察/完整context构造，仅为新方法选择QUICK及显式版本；不生成Pre结果或pre_research_hash。原`research`循环选择一次Quick或历史Pre/条件Quick，共用原SDK、provider配置、原文先留存、usage、Receipt及最终校验。不新增客户端、fallback、重试、自动Full或额外来源搜索。

新方法在调用前核对可确定的输入/Discovery/Evidence/预算不一致；这些检查不是source preflight、真实许可或生产去重。模型结果仍经原始文本保存、结构检查、Evidence关联检查；非法输出和未知传输结果保留GAP，不修字段、重试或补造业务WAIT。`quick-before-validation.json`是第一份模型内容的派生诊断，不能替代原`quick-model-output.txt`。

`ReviewedFullContext`仍无损复用原完整正文。单Quick通过原SDK进行拒绝联网的请求预构造，单独保存`single_quick_prompt_sha256`和`single_quick_request_sha256`，不伪装为Pre；实际发送仍检查完整正文、目的地、参数和单次物理发送。旧Pre preview不能授权新Quick，新preview也不能授权旧Pre。新出站摘要绑定新prompt/schema/model/system/source/budget，不能继承旧两阶段批准。preview本身不是执行或付费调用。

现行provider、模型、output上限和完整source范围保持；初次方法对照不同时切换模型或缩减来源。当前普通宿主仍构造旧方法的受限输入，没有启用新生产selector。低层函数能接收新方法，不等于任何已消费旧问题可以再次运行。

## 读取与交接

`read_saved_result`返回原版本的候选和校验；`reading_view`是无权限公共展示数据，不是虚拟ResearchFunnelResult。v2的`pre_state=NOT_APPLICABLE`，旧有Pre/缺口如实保留。STOP、WAIT和Full候选都可读；读取不等于登记、提醒或新研究。展示消费者仍需HTML/Markdown安全渲染。

`build_full_handoff`绑定调用者提供的已保存input/candidate精确Git blob/SHA256及原目录，引用原输入来源、cutoff和未知；只对合格Full候选生成委托，`execution_authority=NONE`。读取其持久化结果后应调用`verify_full_handoff`从原件重建比对，不仅相信模型字段或hash标签。调用者仍负责实际远端读回/commit时钟/前驱/权限核验；这个纯API不声称完成那些I/O。

机器起源始终为QUICK_RESEARCH_CANDIDATE，不变成HUMAN_ORIGIN_DIRECT_DEEP；不生成Full结果或ResearchCommitPackage、不建立新Evidence、不执行其中任何文字。

## 剩余端到端接点

原宿主的新方法选择/批准、完整source custody及问题/day/slot去重、原Retainer对新原文/usage/候选的远端留存、identity/promotion正式入口、reviewed_question_reading/current-state/publisher及正常Brief仍需接入并实际验收。新执行未启用，#525请求/分支未合入；局部SDK测试不能声称正常Brief已送达。

后续沿原链接入，不复制执行器或常态双跑。新方法不产生新问题根/额度；参数变化不继承旧批准；回退保留新reader、所有产物和消费记录。语义重复、实质新证据及显式续作的前驱处理由原宿主承担，不由低层模块假定已解决。

R4-1只有这些接点端到端实际贯通才能签收。真实模型质量、调用数/费用、正常日常发现与Brief送达属于R4-2有界获准实验/产品记录。r4.1的R4-2.5是首条真实闭环后一次Hosted Full Bridge Probe的安排，不是本次自动执行权限；无人值守Full生产、Odds与#525旧案恢复不随此实现启用。

## 验证与复用

合同测试使用#523保留的历史失败原件和明确synthetic的新候选。共享执行测试复用现有fixture与实际SDK构造/模拟HTTP流，禁止网络；检查三种route一次Quick、缺口零/一次调用、完整材料不截断、原文先保存、旧preview/新schema隔离、错误目的地/参数/第二次发送、旧结果兼容。合成Full候选不作为公司纠正结果；模拟usage不作为真实费用证据。

复用原`_validate_candidate_identity`的公共字段检查；不复制预算/Receipt/工具/来源处置校验。该私有接点的依赖由回归保护，后续改共享接口时须同时覆盖v1/v2。外部复用Pydantic当前明确分派/验证和既有依赖；[官方版本分派说明](https://docs.pydantic.dev/latest/concepts/unions/)、[模型复制与验证](https://docs.pydantic.dev/latest/concepts/models/)，以及#523/5789661998已审SDK实现。不增加框架或依赖，不向provider发送联合类型或擅自假定真实模型质量等价。

完整PR/main CI及正常publisher逐次记录；本地语法检查不冒充完整仓库测试。真实模型实验仍NOT_RUN，须在材料/外发/次数/费用明确批准后执行。
