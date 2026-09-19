# 问题式 Research：既有 Stock 工作流的显式手动模式 v0

2026-09-19；承接 #455 与 #297/5742593738。
Reuse Decision: **THIN_ADAPTER INTO EXISTING HOST**。本批只接执行路径，默认关闭；不是自动 Radar→Research 闭环，也不授权实际公司调用。

## 已补的缺口与复用

#453/#455 证明已声明的问题能进入原输入准备；准备回执不能作为执行令牌。此模式在原 Stock workflow/job/concurrency 中选择 `stock_question_host` 配套入口，调用已验收的 `reviewed_question_input.prepare`、原 `assess_admission/execute_after_admission`、原 `saved_research_once.research` 与 create-only `Retainer`。原 executor 继续决定 Pre→必要 Quick、验证候选和记录预算，不建立另一套 Funnel。

为避免改动旧基线，原 `stock_research_host.py` 字节不变。新模式源码单独放在 `runtime/stock_question_host.py`，只负责已有能力的组合与调用前检查；没有新的 provider、SDK、scheduler、Agent/DAG、资料客户端或依赖。

仍使用 `research-work/stock-business-v0`。输出为 `research_runs/candidates/stock-questions/<hash>/`，hash仅取证券身份和既有 question_id。它与旧 `stock-business/` 平级，避免旧读取器把新目录误判为基线损坏。revision、run和execution重命名不能创建新消费根；任何已存在的该根文件，包括部分失败或未知文件，都禁止再次调用。缺失/截断工作树不是空历史；不自动删除、续跑或重试。

## 单问题请求，默认关闭

主干 `research_runs/stock-question-request.json` 只允许八个字段：

- `schema_version=1`、`enabled`、`mode=REVIEWED_RADAR_QUESTION`；
- `permission`：原 #297 comment_id/body_sha256/created_at 合同；
- `question_source`、`context_source`、`preflight_source`：原精确 Git SourceRef；
- `approved_egress_hash`：独立审阅后保存的公开材料摘要。

初始 enabled=false，其他绑定为null。启用须另经正常 reviewed PR；不能从来源正文、网页提示、合成测试许可或本页复制“授权”。在当前main反复检查原权限comment的原始body/hash/date；GitHub用户名本身不建立投资权限。不从dispatch接收任意公司、prompt、API地址、目录或execution_id。

旧source-stock-run-id在workflow表单变为条件必需：旧模式仍必须提供，新问题模式必须留空。这样机构来路不被迫伪装成通过Stock价格门槛的来路；观察资格仍是研究者可追责的声明，不由此模式重新认证。

## 真实输入，而不是复用旧的准备令牌

问题声明、必要材料范围、预检及公开正文均需先以精确Git原件保存；调用方负责沿用问题ID、保留相关旧研究与反证。此模式只支持原#453的NEW_DISTINCT_QUESTION，旧续作/触发/方法复核回原宿主。

context复用既有 `issuer_documents/pages` 表示，完整保留每份所需原件的announcement_id/title/source_locator/pdf_sha256/published_at/retrieved_at/page_count/pages/reading_method/page_reading；同原preflight的成功PRIMARY BODY逐项相配。页码完整连续、正文可读；全部成功PRIMARY BODY不得悄悄遗漏。BOUND_SAME_PDF_READING继续调用原 `stock_research_sources.recheck`。context包含 `source_limitations`，不把仅有索引、标题、市场seed或哈希当作财务正文。

本模式不重新获取或解析PDF。以上检查绑定的是可信预检记录和保存表示，并不认证抄录准确性、原文经济真相、签章或问题质量。原PDF须在其获准归档位置保留，不能只靠伪造BODY记录获得事实资格。每个source的原512KiB上限、context原大小上限和Stock prompt的512KiB上限保留；禁止截断。

宿主构造一份新的ExternalResearchInputPacket：actual main、实际选择/cutoff、固定R及其hash、预先保存的全部来源。唯一seed绑定实际MODEL_CONTEXT的字节和Git发布时间，不把#455市场seed样本直接升格成可执行证据包。UNKNOWN、必要类marker、反证、证伪测试和旧研究关系说明进入原prompt；原研究输入和旧失败不改写。

## 公开材料批准与启动身份分开

`question_egress_hash(packet, discovery, context)` **只计算摘要，不批准自身输出**。操作者须先独立审阅将发往既有provider的全部公开材料和政策，再把该摘要连同原权限记录提交到主干请求。许可范围须涵盖原Pre及其通过后最多一次Quick；不许可自动Deep。

摘要绑定原pre_prompt的全部公开文字、问题、Evidence IDs、source_refs、预算、system prompt摘要、原模型/endpoint、输出token/输入字节界限、原Pre/Quick schema与明确的conditional Quick追加规则。只有pre_prompt.binding.as_of规范化为HOST_ASSIGNED_RESEARCH_CUTOFF。实际main/cutoff属于启动时创建的packet，另受原准入与input readback绑定；这避免请求文件必须提前知道自身未来合并SHA/时刻的自指问题。

这不是exact provider wire-byte hash，也不是可到处重用的准入token。代码或实际正文改变、原prompt/schema/policy改变会影响相应校验。Quick只能在原validator确认CONTINUE_TO_QUICK后追加实际Pre和其hash；每次外发重新构造允许的完整prompt并逐项比较，不接受任意追加文本。原 `model_request` 在任何远端写入前做实际SDK/schema/大小预检查。

## 执行与失败

按顺序：原授权→完整问题prepare/原件/egress检查→检查稳定根历史→create-only prepare→保存source和新input并精确读回→原启动准入→create-only launch→再检查→原execute_after_admission→原Pre/必要Quick→原candidate/validation/receipt及README留存。

每次Pre/Quick外发前，再检查权限main、预检时限、固定R窗口、原件摘要、原launch和原admission。模型无工具，不访问公司站点。预算沿用6个tool calls、0搜索、4个source reads、0technical retry、15分钟及原SOFT_EXECUTOR语义；不是新的硬沙箱或消费SLA。原单次模型/Quick时间边界不放宽。

正文/权限/读取不齐时不写launch、不调用模型。已保存的稳定prepare也表示这次根被消费，不因后来失败自动重开。写入不确定后只留本地诊断，不补写、不重试、不清理marker；恢复要先对账原件并按原权限处理。技术失败是EXECUTION_GAP/NOT_EXECUTED等实际状态，不能包装成业务WAIT/DROP。

## 手动入口与交付边界

唯一入口仍为 `.github/workflows/stock-business-research.yml`：仅workflow_dispatch、main、attempt1，显式reviewed-question=true及code-sha=实际reviewed main。source-stock-run-id留空，所有旧恢复/prepare/successor开关为false。同一job及 `stock-business-first-v0` 并发组保留；workflow_run/schedule不选择新模式。CLI独立复核同样身份。错误组合先失败，不自动回退旧模式。

结果留在同一work ref与原Actions artifact。没有自动登记execution catalog/current-state registry、当前Human handoff或publisher研究条目；旧reader仍只处理原基线。真实成功后须按原研究留存/语义审阅/登记协议另作精确接续。技术validator绿灯、Human接受和投资决定各自独立。

本批合成测试只替换Git I/O和模型返回边界，实际调用原prepare/admission/research/Retainer、SDK request builder。覆盖合法分支、必要正文缺失、权限撤销、截止窗口、篡改、已消费revision、并发/不确定写入、原读取器隔离和手动入口。它们不是实际公司Pre或live source验收。

本地开发环境无法安装原锁定SDK，临时格式化stand-in仅在仓库外运行，未进入提交或CI。局部开发PASS不代替完整native exact-head CI；最终原SDK、原4385项测试集合保留、新回归、独立main CI及正常publisher均须真实验收。

已落地目标是默认关闭的显式执行接线。自动问题生成/选择、真实启用请求、模型实跑、自然日常运行及Radar→Research自动闭环尚未交付。公告按需收敛不变，不接Tushare/Jev/MinerU或重开下载工程。AI Investment Authority=NONE。
