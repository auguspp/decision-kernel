# Single Quick：版本合同基础（R4-1）

本切片实现`runtime/single_quick_contract.py`的纯数据、机械验证、历史分派、只读投影及非执行Full交接。遵循[成果边界](research-outcome-contract-v1.md)；不是新的研究引擎，也不是R4-1整体完成或生产启用。

## 版本与责任

输入复用ExternalResearchInputPacket schema 1，显式绑定`method_version=single-quick-v1`和`prompt_version=single-quick-outcomes-v1`。新候选schema 2；旧research-funnel-v1候选schema 1仍由原模型/验证器解释。raw读取检查明确版本组合；未知/混合版本、重复JSON key拒绝，不尝试另一parser。不修改任何旧字段、哈希、预算或消费台账。

QuickAssessment是模型内容，不含模型自算hash/cutoff/许可。主解释覆盖why-now、公司联系/重要性、既有研究关系等责任，形式自由；结构化claims继续复用ResearchClaim。反证检查说明、未知、业务route/理由和必要的下一步分开，不将Pre和Quick原字段全集拼接。

Full候选须有来源支持的观察和明确调查委托（问题、重要性理由、当前可做的工作、可改变/推翻判断的检验）。不强制预期差或相反FACT；诚实INFERENCE可保留。WAIT须有未来触发；UNKNOWN可以为空，数量不用于质量打分。代码仅验证结构与一致性，不证明经济联系、重要性、反证充分性或研究价值。

SingleQuickCandidate由宿主生成，复用Discovery、Receipt、Evidence及已有身份/预算/工具/来源处置校验；完整结果要求assessment而非Pre，缺口不能携带正式业务route。原始非法输出应由原executor先保存，不能为了构造candidate丢弃；本纯模块本身不保存文件或运行模型。

## 读取与交接

`read_saved_result`返回原版本的候选和校验；`reading_view`是无权限公共展示数据，不是虚拟ResearchFunnelResult。v2的`pre_state=NOT_APPLICABLE`，旧有Pre/缺口如实保留。STOP、WAIT和Full候选都可读；读取不等于登记、提醒或新研究。展示消费者仍需HTML/Markdown安全渲染。

`build_full_handoff`绑定调用者提供的已保存input/candidate精确Git blob/SHA256及原目录，引用原输入来源、cutoff和未知；只对合格Full候选生成委托，`execution_authority=NONE`。读取其持久化结果后应调用`verify_full_handoff`从原件重建比对，不仅相信模型字段或hash标签。调用者仍负责实际远端读回/commit时钟/前驱/权限核验；这个纯API不声称完成那些I/O。

机器起源始终为QUICK_RESEARCH_CANDIDATE，不变成HUMAN_ORIGIN_DIRECT_DEEP；不生成Full结果或ResearchCommitPackage、不建立新Evidence、不执行其中任何文字。

## 本切片之外仍必须完成

原宿主的方法选择与出站批准、SDK新schema的真实无网络构造/发送保护、完整来源和同PDF解释实际读取、问题/day/slot去重、原文/usage/候选的原Retainer留存、identity/promotion正式入口、reviewed_question_reading/current-state/publisher及正常Brief尚未接入此模块。没有production caller导入它；新执行仍未启用，#525请求/分支未合入。

后续沿原链接入，不复制执行器或常态双跑。新方法不产生新问题根/额度；参数变化不继承旧批准；回退保留新reader、所有产物和消费记录。语义重复、实质新证据及显式续作的前驱处理由原宿主承担，不由本模块假定已解决。

R4-1只有这些接点端到端实际贯通才能签收。真实模型质量、调用数/费用、正常日常发现与Brief送达属于R4-2有界获准实验/产品记录，本切片无相应运行。

## 验证与复用

新增测试使用#523保留的历史失败原件和明确synthetic的新候选，所有网络连接禁止。覆盖旧Pre/hash与失败保持、新方法无Pre、三种业务route、真实未知/推断的允许边界、来源/时点/对象/预算、混合版本、结果资格与handoff篡改。合成Full候选不作为公司纠正结果。

复用原`_validate_candidate_identity`的公共字段检查；不复制预算/Receipt/工具/来源处置校验。该私有接点的依赖由回归保护，后续改共享接口时须同时覆盖v1/v2。外部复用Pydantic当前明确分派/验证和既有依赖；[官方版本分派说明](https://docs.pydantic.dev/latest/concepts/unions/)、[模型复制与验证](https://docs.pydantic.dev/latest/concepts/models/)，以及#523/5789661998已审SDK实现。不增加框架或依赖，不向provider发送联合类型或擅自假定新wire兼容。

完整PR/main CI及正常publisher逐次记录；本地语法检查不冒充完整仓库测试。
