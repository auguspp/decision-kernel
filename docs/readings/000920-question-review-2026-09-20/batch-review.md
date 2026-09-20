# 2026-09-18 保存 Stock 批次的接手审阅

本记录编制于 2026-09-20，读取版本固定为 `e7127c414731ebbb9aed49dd2f2ac10975a73a61`，代码版本 `73b994bf9cc42270e0a401ed978dc1b546e23352`。Stock 批次 `a5f7fb0222fc80fa377dc4ea923637750785e8859f57b493eb0bafa887b9f518` 来自正常保存运行 [35334355692](https://github.com/auguspp/decision-kernel/actions/runs/35334355692)。这是已保存六行范围的交互审阅，不是全 A 股覆盖，也不是新一次市场获取或 runtime admission。

| 保存对象 | 已保存市场/输入资格 | 本次处理及理由 |
| --- | --- | --- |
| 002632.SZ 道明光学 | CONDITIONS_NOT_MET；五日原始价格路径或相对市场表现未满足条件 | 本轮没有由该市场表达形成新问题；不表示公司基本面差。 |
| 600127.SH 金健米业 | DATA_QUALIFICATION_FAILED；CURRENT_QUOTE_HISTORY_MISMATCH | 输入不合格，保留数据缺口；不能归类为条件不满足或业务 DROP。 |
| 688066.SH *ST航图 | CONDITIONS_NOT_MET；RISK_OR_NEW_LISTING_NAME_LABEL | 保留原资格退出，本轮没有新问题；不由名称标签推导经济判断。 |
| 000920.SZ 沃顿科技 | CONTRACT_CHECKED_RAW_READING；膜材料市场表达已观察，业务受益未建立 | 按保存顺序选首个价格合格对象开展本目录来源审阅。新方向仍为草稿；必要半年报原件、更新覆盖和问题去重尚未闭合，没有正式问题或 Pre。 |
| 000019.SZ 深粮控股 | CONDITIONS_NOT_MET；五日原始价格路径或相对市场表现未满足条件 | 本轮没有由该市场表达形成新问题；不表示公司基本面差。 |
| 603268.SH 松发股份 | CONTRACT_CHECKED_RAW_READING；市场表达已观察，业务受益未建立 | 已查看该行与旧 FIRST_BUSINESS_BASELINE 来源准备失败的关系；本次来源预算用于保存顺序更早的沃顿，尚未展开其新经济问题审阅，不标为业务 WAIT/DROP，也不重跑旧 key。 |

全部六行均有处置；本轮正式新问题为 **0**。0–3 项注意力预算不要求凑出研究结果。原保存范围仍为 `BOUNDED_SURFACED_SECTOR_BREADTH_LEADERS_NOT_ALL_A_SHARES`，`scope_complete=false`，不声称其余行业成员已经被逐一研究。

同一 R 的 `research.reviewed_question_work` 保留两次广哈通信执行：原问题根与固定技术接续是同一经济问题的技术关系，不作为两个新增日常问题。`research.stock_business_work` 中沃顿和松发的旧 baseline 均在来源准备阶段失败。本地精确 main 的用途 registry、已保存 docs/readings、research_runs、research_cases 中对 `000920`、`沃顿`、`vontron`、`woton` 的检索没有发现另外已登记研究正文；这只描述当前 main 与该 R 所列范围，不宣称穷尽所有未登记分支。沃顿的 `NEW_DISTINCT_QUESTION` 资格继续为 NOT_ASSIGNED。

来源范围沿 [事前声明 5749522521](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5749522521)：7/1–9/20 的必要更新保持必要，不能为了适配首版 STATIC 日常执行政策而删除。取得既有资料与补齐去重之后再沿原 reviewed-question preparation/admission 路径处理。此记录不是可执行的 `batch_review_source`，没有模型授权、Human 研究接受或投资决定。
