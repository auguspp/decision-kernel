# 已声明 Radar 问题 → 原 Research 输入准备 v0

2026-09-19；承接 #452 与 Human「好，继续」。施工前 Reuse Check：#297/5741531267。
Reuse Decision: **THIN_ADAPTER**。实现 `runtime/reviewed_question_input.py` 的显式 `prepare()`，复用原输入模型、来源引用、时间/身份检查与 `external_research_admission.prepare_input`。

## 已落地的最小缺口

#452 已证明 origin kind/原资格依据有保存位置，不需要再加 radar_kind 或统一 Price Gate。原 ExternalResearchInputPacket 也能存研究问题和来源，但尚不检查：一份**在来源预检之前已保存**的问题声明，是否与实际问题、必要来源类、更新查询范围、已有研究关系和前驱一致。

本模块只补这一段绑定，不选择公司，不生成/评判问题，不获取发行人资料，不接受 executor，不产生新 Pre/Quick 或自动路由。它不改变任何旧入口；调用方须显式选择本函数。当前普通 Stock `FIRST_BUSINESS_BASELINE`、稳定 key、launch、旧失败、lineage、监听及全部正文合同均不变。

这是新增的宿主 sidecar 格式 `reviewed-radar-question-v0`，**不是 Kernel 或 ExternalResearchInputPacket 的 schema 升级**。不能把增加了一份结构化声明说成完全没有新合同；它的必要性仅是把已批准的九项内容绑定到既有输入。原 packet 的 `source_refs` 用 purpose=`REVIEWED_RADAR_QUESTION` 引用其精确 Git 原件，`source_lane` 显式使用同名标签；声明字节因而进入原 canonical input identity。不创建 Question registry 或新的全局ID体系。

## 声明文件的字段

完整且仅允许以下字段；未知字段如 composite_score/route/authority 拒绝，而非被采用。以下是文件合同，不是自动创建真实公司问题的命令。

| 字段 | 内容与绑定 |
|---|---|
| format | `reviewed-radar-question-v0` |
| case_id / ticker / security_id | 与原 packet 三字段逐项相等；不据六位代码猜交易所，不认证发行人真相 |
| question_id / revision / predecessor | 研究者沿用的经济问题ID；正整数版本；首版无前驱，其后用原 ResearchInputSourceRef 引用精确直接前驱。不是新 execution_id，不认证自然语言问题等价 |
| declared_at | 问题及必要范围的声明时间。要求声明≤该Git commit时间≤preflight.started_at；先下载失败再改计划不能冒充原计划 |
| reading_source | 原 ResearchInputSourceRef，绑定 packet.current_state_commit 的 `current-state.json`；按原 reading verifier及reading_hash检查；超过原recheck_after需另行恢复，不回退main/latest |
| question / why_now / falsification_test | 具体问题、此时研究的理由、可以推翻/区分的检验。question必须与原packet.research_question相同。非空仅证明有声明，不认证可回答性或因果关系 |
| required_classes | 原class id/mode，加该类预先声明的planned_queries。STATIC为空列表；LATEST_INVENTORY须与实际preflight的planned_queries精确相等。原preflight继续检查成功查询与相关主来源正文 |
| known_counterevidence / known_unknowns | 非空文本列表，允许明确UNKNOWN；unknowns不得在packet中丢失。反证正文是否必要仍由原preflight的实际相关性声明及研究者负责，不能靠文字齐全替代读取 |
| next_discriminating_search | 与原packet同名字段一致，不由适配器补造 |
| origins | 每项保留kind、原source ref、observed_at、qualification、qualification_reason。kind目前仅支持已有SECTOR_LEADER / CONCEPT_CURRENT_MEMBER / INSTITUTIONAL_WINDOWS；未来Industry Inflection尚未接入 |
| existing_research_relation | kind、note、source_refs；所有引用都须列入原packet并按原字节检查。v0仅准备NEW_DISTINCT_QUESTION；CONTINUE_ANALYSIS / CHECK_TRIGGER / METHOD_REVIEW明确拒绝，要求原宿主处理，不能换key重启旧基线 |

origin的qualification允许 `QUALIFIED_FOR_DECLARED_SCOPE` / `CONTEXT_ONLY` / `UNKNOWN`，至少一条声明为前者并给出理由。**这些是研究者/可信collector可追责的声明，不是本模块重新执行源资格或业务判断。** 哈希正确不能证明QUALIFIED是真的，多个来源不能加分。没有Price Gate调用，也不把机构净流入改为投资结论。observed_at是已保存观察的实际时钟，不能拿市场日冒充；要求不晚于原件Git保存时间。

所有相关source都复用原ResearchInputSourceRef、`_checked_source`和精确commit；source必须已在packet.source_refs，且在声明之前保存。声明本身不能被充当新的seed Evidence。原资料链接存在不证明正文已读，也不代表拿到了原PDF。

## 调用与结果

```python
from decision_kernel.runtime.reviewed_question_input import prepare

# 各参数沿用原有可信宿主的精确输入和只读I/O；本示例不创建凭证或发起调用。
receipt = prepare(
    question_source=question_ref,
    input_raw=saved_input_bytes,
    preflight_raw=saved_preflight_bytes,
    catalog_source=pinned_existing_catalog,
    load=existing_bounded_git_reader,
    commit=existing_commit_metadata_reader,
    checked_at=actual_check_time,
    current_code=actual_main_reader,
)
```

输出是 `QUESTION_INPUT_PREPARED_NOT_EXECUTED`，保留question source/id/revision、原execution_key、原input/preflight/catalog摘要及R身份；`research_execution_allowed=false`、正式研究预算消耗0、Funnel未调用、投资权限NONE。本函数不写输入/归档/registry，不输出假执行记录。资料读取仍受调用方原预算约束；没有新API配额或网络客户端。异常保留有限错误代码，不回显来源或凭证。

实际逻辑：声明与原件绑定→必要范围一致→调用**原prepare_input**→检查同一显式catalog内是否已有同证券/同question_id的另一个输入。已有同问题的其他execution直接拒绝并回原宿主；更换execution_id或仅改revision不能绕过。相同execution/key的准备复验仍可进行，复验不运行Research。

这个去重范围只是原catalog，不是全仓锁、全历史穷尽、语义相似度模型或Human接受认证。没有登记的历史不会凭空被找到；恶意或误将同一问题换名，仍须原宿主及研究者审阅，不能用本函数的成功取消旧权限/失败。已知相关旧研究不可在声明中故意省略。

**准备成功不是可复用执行令牌。** 以后真实宿主接线时必须重新恢复精确声明/前驱及原输入，调用本准备检查，并继续原launch-time `assess_admission/execute_after_admission`、预算与one-shot合同。本轮不接线那个执行动作，不调用它来证明测试成功。旧入口不自动获得此新检查；也不能绕过本准备函数却宣称采用了它。

## 原件范围、版本与留存

沿用原512KiB每source、MAX_ITEMS及MAX_INPUTS；不提高publisher/archives预算。数百公司组成的大company-reading JSON可能超限，**v0不自动切片、不静默截断、不重新制造来源**。调用方只能提供已由现有可信宿主保存、可核验的有界来源引用；全900公司视图→具体问题的生产者及传递仍未实现。

直接前驱检查只证实同对象/问题、相邻revision及时间顺序，不递归认证全部历史。已经登记过执行的同问题不能靠一个新前驱版本获得重跑授权。尚未形成正式输入的计划修订保留old→new与前驱；必要范围改变需重新形成计划与预检，不能改旧结果。

声明、底稿和失败按原RETAINED_FILES或原progress路径留存；本函数不代替save-progress，不创建COMMITTED。登记、正常发布和正文按需恢复仍是独立步骤。历史事实、当前候选资格、Human研究接受和资本决定分别保留。

## 本批验收与未实施项

Synthetic回归使用原admission fixtures、原prepare_input、真实输入模型和reading verifier，禁止socket；验证先声明后预检、必要/可选缺口、相关反证、前驱、同问题更换execution、code/scope冲突、source字节及unknown保留。技术回归不是公司研究或问题质量验收。没有真实公司输入/执行、模型调用、price/Market刷新或dispatch。

已实现的是**显式问题声明的输入准备薄适配**。自动问题形成/质量审阅/全局语义去重/少量选择、company-first生产接线、问题式Stock执行及真实Pre仍未实施。Industry Inflection继续P2定义。公告按需收敛不变，不接Tushare/Jev/MinerU、不继续CNINFO/SZSE/SSE实验。

外部复用：Pydantic官方Models及pytest monkeypatch（2026-09-19读取）；沿用已有版本，不增加依赖。结构验证不认证输入经济真相；没有需要引入Agent/DAG/router框架的缺口。
