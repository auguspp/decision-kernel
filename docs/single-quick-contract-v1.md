# Single Quick：版本合同与共享执行（R4-1）

`runtime/single_quick_contract.py`提供纯数据、机械验证、历史分派、只读投影及非执行Full交接；`saved_research_once.py`的原循环及`reviewed_full_input.py`的原完整输入/SDK检查已增加显式单Quick能力。遵循[成果边界](research-outcome-contract-v1.md)；不是第二研究引擎，也不是R4-1整体完成或生产启用。

## 版本与责任

输入复用ExternalResearchInputPacket schema 1，显式绑定`method_version=single-quick-v1`和`prompt_version=single-quick-outcomes-v1`。新候选schema 2；旧research-funnel-v1候选schema 1仍由原模型/验证器解释。raw读取检查明确版本组合；未知/混合版本、重复JSON key拒绝，不尝试另一parser。不修改任何旧字段、哈希、预算或消费台账。原共享执行器另保留已存在的`RESEARCH_METHOD_V1`旧公告方法标识，不因新入口迁移将原合法任务拒绝，也不把未知新方法自动降级。

QuickAssessment是模型内容，不含模型自算hash/cutoff/许可。主解释覆盖why-now、公司联系/重要性、既有研究关系等责任，形式自由；结构化claims继续复用ResearchClaim。反证检查说明、未知、业务route/理由和必要的下一步分开，不将Pre和Quick原字段全集拼接。

Full候选须有来源支持的观察和明确调查委托（问题、重要性理由、当前可做的工作、可改变/推翻判断的检验）。不强制预期差或相反FACT；诚实INFERENCE可保留。WAIT须有未来触发；UNKNOWN可以为空，数量不用于质量打分。代码仅验证结构与一致性，不证明经济联系、重要性、反证充分性或研究价值。

SingleQuickCandidate由宿主生成，复用Discovery、Receipt、Evidence及已有身份/预算/工具/来源处置校验；完整结果要求assessment而非Pre，缺口不能携带正式业务route。原始非法输出由原model_call先保存；本纯合同模块本身不保存文件或运行模型。

## 共享执行与完整输入

`initial_prompt`复用原问题/观察/完整context构造，仅为新方法选择QUICK及显式版本；不生成Pre结果或pre_research_hash。原`research`循环选择一次Quick或历史Pre/条件Quick，共用原SDK、provider配置、原文先留存、usage、Receipt及最终校验。不新增客户端、fallback、重试、自动Full或额外来源搜索。

新方法在调用前核对可确定的输入/Discovery/Evidence/预算不一致；这些检查不是source preflight、真实许可或生产去重。模型结果仍经原始文本保存、结构检查、Evidence关联检查；非法输出和未知传输结果保留GAP，不修字段、重试或补造业务WAIT。`quick-before-validation.json`是第一份模型内容的派生诊断，不能替代原`quick-model-output.txt`。

`ReviewedFullContext`仍无损复用原完整正文。单Quick通过原SDK进行拒绝联网的请求预构造，单独保存`single_quick_prompt_sha256`和`single_quick_request_sha256`，不伪装为Pre；实际发送仍检查完整正文、目的地、参数和单次物理发送。旧Pre preview不能授权新Quick，新preview也不能授权旧Pre。新出站摘要绑定新prompt/schema/model/system/source/budget，不能继承旧两阶段批准。preview本身不是执行或付费调用。

现行provider、模型、output上限和完整source范围保持；初次方法对照不同时切换模型或缩减来源。原`stock_question_host`现在能按明确的新方法请求接入同一个执行器；当前仓库生产请求仍保持原样，未启用新方法。方法支持不是新任务/新预算授权，已消费旧问题不得再次运行。

## 读取与交接

`read_saved_result`返回原版本的候选和校验；`reading_view`是无权限公共展示数据，不是虚拟ResearchFunnelResult。v2的`pre_state=NOT_APPLICABLE`，旧有Pre/缺口如实保留。STOP、WAIT和Full候选都可读；读取不等于登记、提醒或新研究。展示消费者仍需HTML/Markdown安全渲染。

`build_full_handoff`绑定调用者提供的已保存input/candidate精确Git blob/SHA256及原目录，引用原输入来源、cutoff和未知；只对合格Full候选生成委托，`execution_authority=NONE`。读取其持久化结果后应调用`verify_full_handoff`从原件重建比对，不仅相信模型字段或hash标签。调用者仍负责实际远端读回/commit时钟/前驱/权限核验；这个纯API不声称完成那些I/O。

机器起源始终为QUICK_RESEARCH_CANDIDATE，不变成HUMAN_ORIGIN_DIRECT_DEEP；不生成Full结果或ResearchCommitPackage、不建立新Evidence、不执行其中任何文字。

### r4.1：共用 FullResearchCommission，起源证明分开

依据[#297/5793148239](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5793148239)，`runtime/full_research_commission.py`把Quick候选与Human Direct Full归入同一个非执行委托。共同字段是对象/问题/范围、why-now、输入cutoff、来源及seed Evidence、旧研究关系和局限；研究者不必复现上游思考步骤。

Quick适配复用#527的精确`FullResearchHandoff`证明，并实际绑定原Question声明与问题根；它不自动生成Full执行ID、批准或预算。Human适配读取既有`direct_deep.Request`与明确permission原件，不造Discovery/Pre/Quick；原请求ID和预算可追溯，`max_passes`不被提升为共享研究者算法。Human旧请求没有单独经济问题ID时，保留其请求ID作为起源标识，**不声称这解决跨起源语义重复或建立新消费资格**。

两种起源都有同一`outcome_contract`和NONE执行/投资权限。`verify`从精确原件整体重建，不相信改写的委托字段。它证明委托与输入相符，不替代真实远端commit时钟、Human语义授权、执行准入或跨来源去重。输入材料时点不是未来Full研究的永久时点：后续获准Full如使用新增证据，必须声明自己的研究时点/版本和前驱，不能回填旧Quick或改写本提案。

共享委托不是Hosted worker，也不是自动Research Commit。未来合格成果复用原Research Outcome Contract、ResearchCommitPackage/进度留存与GitHub读回；不复制结果合同或把机器起源改成Human接受。R4-2.5可选择任一合格起源做一次真实验证；无人值守队列、调度、自动Odds仍不进入本切片。

## 原共享宿主、留存和正常阅读

新请求在原`stock_question_host`使用`research_method=single-quick-v1`和原authorizer可核对的`method_permission`，保留原来源范围permission；`approved_egress_hash`明确绑定新方法的完整prompt/schema/provider/source/budget。旧daily的动态摘要或旧两阶段批准不能直接变成新方法批准。这些字段只在新方法显式选择时要求，旧请求序列化不改；本仓实际配置仍没有开启新方法。未来日常激活必须同时确认材料/方法/外发/次数/费用范围，不从单个hash推断同意。

同一Question仍由原security_id/question_id生成消费根；原day/slot/launch与日常POLICY保持。旧部分结果/失败标记也阻止再次消费；新方法退回旧方法不返还额度。完整来源、同PDF解释和准入仍走原source-custody与调用前重查，不因取消Pre而取消。

原Retainer增加有限输出文件的精确本地复用后create-only远端保存：第一份公开模型原文、output format、usage与派生候选诊断，均保留原字节，不重新生成模型回复。超大完整model-input仍在原Actions附件，原source/input另有已保存的精确绑定；不声称全部SDK输入副本新增到Git。若保存不确定，立即停止写入并留本地失败回执，下一次不自动重试模型。候选有效但缺最终交付回执/原文/usage时，新reader明确显示读取/交付缺口。

成功结果保存`research-attention.json`，Full候选另外保存共同`full-commission.json`；这些是可读产物，不自动登记当前Human事项。原identity/promotion与registry支持显式v2绑定，拒绝无执行证明或改写的handoff；没有第二状态库或新的自动注册服务。

原`reviewed_question_reading`、正常publisher和已有Daily Brief读取入口可消费新旧并存结果。新方法显示“该方法不设Pre”，先说明为什么值得看、反证/已知未知、处置和下一步。首页沿用最多3条可读解释，全部结果和省略数量留在同R详情；STOP/WAIT可读，不强制转主动提醒。原Attention Inbox的Markdown/HTML同样读取新wrapper且安全转义，不构造假Funnel。当前Stock批次关联仍只声明同批Stock审阅；Industry问题保持独立来路，不因不在Stock批次中而隐去，也不冒称本次读取重验全产业覆盖。

## 验收层次与当前停止条件

本批针对上述原宿主→SDK→Git留存→版本化读取→正常publisher/Brief消费以及双起源委托进行工程验证；工程完成必须有完整PR/main CI及正常发布/读回，不由本文件预填成功。测试使用合成Git/模型边界，不表示真的有一条新日常研究送达。

当前新生产请求未启用；A/B质量实验、首个真实Quick日常发现/用户交付/反馈、Hosted Full实际读取/调查/写回均未运行。R4-2须一次有界材料/外发/调用数/费用批准；S0仅实验变体，20次不是目标。新方法正式切换、真实日常问题的选择/批次消费与正常Brief送达分别留证，不能以手选问题的单次smoke签P1。R4-2.5继续排在首条真实Quick闭环之后，真实能力缺口明确留账，不为probe另造通用worker。

#525继续暂存，不带入其旧checkpoint/恢复/激活配置。新默认方法稳定后不常态双跑；回退保留新reader、原文和所有消费记录，不自动fallback到Pre。R4-3及之后按r4.1顺序推进，真正P1退出仍由值得看的板块/公司、原因/局限、实际交付和Human反馈决定。

## 验证与复用

合同测试使用#523保留的历史失败原件和明确synthetic的新候选。共享执行测试复用现有fixture与实际SDK构造/模拟HTTP流，禁止网络；检查三种route一次Quick、缺口零/一次调用、完整材料不截断、原文先保存、旧preview/新schema隔离、错误目的地/参数/第二次发送、旧结果兼容。合成Full候选不作为公司纠正结果；模拟usage不作为真实费用证据。

复用原`_validate_candidate_identity`的公共字段检查；不复制预算/Receipt/工具/来源处置校验。该私有接点的依赖由回归保护，后续改共享接口时须同时覆盖v1/v2。外部复用Pydantic当前明确分派/验证和既有依赖；[官方版本分派说明](https://docs.pydantic.dev/latest/concepts/unions/)、[模型复制与验证](https://docs.pydantic.dev/latest/concepts/models/)，以及#523/5789661998已审SDK实现。不增加框架或依赖，不向provider发送联合类型或擅自假定真实模型质量等价。

本地仅定向诊断：当前Python/SDK安装与固定CI不同；临时schema转换替身仅存在于工作目录之外，不进入仓库或CI。完整CI必须安装原固定SDK并运行新增的真实SDK＋模拟HTTP/SSE原宿主用例，不能skip；它仍不证明真实模型质量或费用。每次PR/main实际结果和正常publisher逐次记录，失败保留。
