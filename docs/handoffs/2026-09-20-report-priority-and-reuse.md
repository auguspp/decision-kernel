# Kernel 财报研究接手：历史能力复用核对

核对日期：2026-09-20。代码基线固定为 `auguspp/decision-kernel@728de4ead5094a74c835304c9a6e7fc385c48e6f`。这是有界的能力与历史验收核对，不是全仓架构整理、所有历史重新验收或新的研究执行许可。

当前范围按 [Human 更正 #297 / 5750493197](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5750493197) 向前调整：先复用仓库已有能力，以财报推进沃顿研究；其他公告采集及全窗口补齐暂缓。若某个必要结果确实离不开某份公告，才说明具体缺口与受影响结论。局部 UNKNOWN 不成为整个项目停工的理由。旧 7/1–9/20 范围、失败及执行合同保留原貌，不回填为已完成。

## 结论

项目已有实际运行过的 PDF 获取、原件留存、全文解析、同 PDF 阅读补充、完整输入无损保存、原准入与 Pre/必要 Quick、分层研究进度、Research-only COMMIT、Git 档案恢复、正常 publisher、Brief 和精确版本 Human 回应。当前工作应先组合这些已存在的能力，不能因一份旧文档的阶段性“尚未实现”或一个源站失败，重新从“缺一套财报系统”出发。

本轮必要半年报已取得：[实际成功回执 #297 / 5750454664](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5750454664)。新浪原 PDF 1,262,185 bytes、133 页，SHA256 `27c74e31c8aaf5a38d27b688f0841d81797816420b591647bfb6763e485b7728`；现有解析器的完整逐页 JSON 271,234 bytes、纯文本 258,940 bytes。DataSinking 的 H1 与 2025 年报正文也已取得。不得再把这份 H1 PDF 的搬运列为 Human 待办。

## 10 项现有能力与复用决定

| # | 能力 | 已有事实 | 当前复用决定与边界 |
|---|---|---|---|
| 1 | 公共财报 PDF 获取；原件先存后解析 | 苏垦新浪完整 192 页 PDF、Stock 多家公司完整 CNINFO PDF 均有真实运行；本轮沃顿新浪普通 GET 再次成功 | REUSE 一次公共 HTTP、原字节/hash/时钟保存；不重跑苏垦旧执行入口，不新建下载框架 |
| 2 | 原 PDF 全文解析与同 PDF 备用阅读表示 | 原 `pypdf`；损坏/缺字页已有 PDFium/整页视觉 note 绑定；DataSinking 有真实财报 Markdown 先例与本轮成功 | REUSE 原 parser；需要时复用同源阅读补充。DataSinking 保持第三方转换表示，不冒充原 PDF 或独立第二份 Evidence |
| 3 | 保存 source artifact 恢复，避免重新获取 | 同一 33 份 PDF、658 页来源包被后续准备和实际研究复用；本轮原 artifact metadata 仍未过期 | REUSE 原下载/解包/hash/库存-journal-PDF-extraction 关系；旧 source-only 请求限定两家公司，不能改股票复活 |
| 4 | 完整输入无损封装和实际 SDK 发送前检查 | 两份 873,576 / 658,453-byte context 已无损保存并进入 3 个真实模型阶段 | REUSE 已实现 codec/bridge 思路；当前代码只限原两家公司。沃顿 H1 全文自身在现有限额内，暂无重建大包接口必要 |
| 5 | 已声明问题、旧研究关系、真实输入准备和原准入 | #455 已以完整真实原件完成 `reviewed_question_input.prepare` 正向验收；#456 现役执行接线；#474 有界日常组合 | REUSE 原 question/prepare/admission；保留稳定问题 ID 和旧根，用户范围变更不能伪造 NEW_DISTINCT |
| 6 | 原 Pre → 必要 Quick、原验证和创建式留存 | 苏垦、东软、光电及和顺/广哈都有真实阶段记录，后者另有语义挑战 | REUSE 原 `research()`、SDK、validator/Funnel、Retainer；执行成功与研究结论正确分别判断 |
| 7 | 未完成研究的进度保存与恢复 | #403 真实 typed progress 远端往返，旧底稿 blob 不改写 | REUSE `save-progress` / `read-progress`；不必等行情、估值、全部资料或 COMMIT 才保存成果 |
| 8 | Research-only COMMIT、Git 档案与同 R 恢复 | #412 真实 Research-only commit → archive → registry → fixed R；#321 后续正式收口 | REUSE 原 commit/retention/archive；不新建状态库，任意 Markdown 不直接升为 COMMITTED |
| 9 | 正常 current-state 发布与 Brief 消费 | 真实自然 Stock → Research stop → publisher；#475 正常发布与 7 文件原 reader 恢复；Brief v1.3 已实际更新 | REUSE 原 publisher/registry/同 R/原任务；新研究的自然 Brief 交付尚待真实验收，不再创建第二日报系统 |
| 10 | Human 回应绑定所见精确版本 | 600598 真实回应 checkpoint 指向准确 Odds 与冻结 Research；现有通用记录协议 | REUSE 原 comment/checkpoint；历史接受不转移给沃顿，“继续”无需重复 magic word，研究/投资/Action 不混同 |

## 1. 公共 PDF 与原件先留存：不是未建设能力

现役实现：

- [`saved_research_once.py::acquire`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/saved_research_once.py)：普通 `requests.get(timeout=(15,60), stream=True, allow_redirects=False)`，保存 `source.pdf`，再调用原 extractor。
- [`disclosure_pdf_capture.py::DisclosurePdfCapture`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/disclosure_pdf_capture.py)：包装原 fetcher，按 SHA 保存返回 bytes、manifest、完成记录；原 extractor 收到同一 bytes，部分失败已得原件不丢失。
- [`stock_research_sources.py::capture`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/stock_research_sources.py)：先保存 PDF，再保存原解析结果；journal 区分已取得、格式身份已核对、未取得及表示缺口。

历史实证：

- 苏垦 [run 34548590855](https://github.com/auguspp/decision-kernel/actions/runs/34548590855)，code `ad41ff8aa13db77c0dcc5e36c4795277696e01f4`，artifact `10180018843`，ZIP 1,207,866 bytes，SHA256 `fbb79d2cc45a71c93c154672d32a6a7662f65bcdaa749a017f4bf12c3b21a907`。PDF SHA256 `37963782aa53690018b1dac50a4aa928b73712b3a365a86150bcb58c5b5b5f69`，192 页完整原件；模型只取 9 页。原 [source.json](https://github.com/auguspp/decision-kernel/blob/30874a41ea97a6fd41118fca45f9d578cb905c88/research_runs/candidates/601952.SH/p0-suken-api-20260910-v2/source.json) 与 [preflight.json](https://github.com/auguspp/decision-kernel/blob/30874a41ea97a6fd41118fca45f9d578cb905c88/research_runs/candidates/601952.SH/p0-suken-api-20260910-v2/preflight.json) 已实际读取；[验收 5627850421](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5627850421) 记录 ZIP/CRC/原图/模型与留存核验。本轮重读 artifact metadata 仍 `expired=false`。
- [#302 验收 5609792467](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5609792467) 证明原件留存薄适配已合并，原六份三花 PDF 1,845,537 bytes 离线逐字节复制核验；该回执当时明确尚未发生自然 scan 验收，不能独自夸大成 live source 成功。
- 后续 [Stock 原件验收 5652012258](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5652012258) 实际核验 13 份已捕获 PDF；[恢复运行 5652913153](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5652913153) 核验 24 份 PDF，其中光电 10/10、广哈 13/13 共 286 页，具有更强真实采集证据。

现役区别：`saved_research_once.checked_request()` 固定苏垦、报告 URL、192 页和已消费执行；能复用 HTTP/原件/解析机制，不把旧 `run()` 或一次性许可改成沃顿重跑。新浪镜像在历史 preflight 中有 PRIMARY issuer-report 记录及诚实 mirror 限定，不是项目全局禁止来源。

## 2. 解析与可读表示：原件不等于某一次抽取结果

现役 [`adapters/pdf_text.py::extract_pdf_text`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/adapters/pdf_text.py) 纯处理 bytes，无获取/模型；核对 PDF 结构、页树、加密/资源限制，逐页抽取并保留 PDF/text 哈希。本轮沃顿已直接使用原实现完成 133 页解析，全部页有文本、0 个 U+FFFD。

现役 [`disclosure_source_reading.py`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/disclosure_source_reading.py) 的 `represent/checked_visual/validate` 复用 pypdfium2；保留原 pypdf 结果和原 PDF 身份，逐页绑定 PDFium 文本或整页视觉 note 的 engine/render/pixel hash。主干 review 来源需要真实图像观察；不是 OCR、另一个原始来源或真理校验。

实际依据：[source artifact audit](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/docs/readings/stock-source-artifact-audit-2026-09-14.md) 记录和顺 `1225530965` 的第 23 页原抽取为空、实际全页渲染以及新 note。PDF SHA256 `cc3a234f7551ef02c401fae60452b891ca48ef0047aad7e26981e0f4ec7948fa`；像素 SHA256 `196d9e941525f37577039e27b81fed72354caa0f1afb2844f856940ef6177059`；后续 [34807883332 验收](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5659344328) 证明该 note 真实进入当前完整输入，不能继续要求 Human 补同一页。

外部可复用事实：[DataSinking 5657559667](https://github.com/auguspp/decision-kernel/issues/354#issuecomment-5657559667) 的两个半年报 Markdown 为约 375,994 / 364,519 UTF-8 bytes，0 replacement characters；公告覆盖分别 1/20、1/13。财报成功与临时公告低覆盖须分开。本轮 DataSinking 公开预览已取得沃顿 H1/年报，见 [5750454664](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5750454664)。现主干未找到其客户端集成/凭证配置；历史 probe 回执不证明后台 parser 公开或全部表格正确。当前 H1 有新浪原 PDF，优先用原 PDF 对关键表格核验，不为本案再造 OCR 或转换服务。

## 3. source-only 与原 artifact 恢复：不再重复取同一报告

现役 [`stock_source_preparation.py`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/stock_source_preparation.py) 把来源准备与付费研究分开；`preparation_only=True` 保存完整 context 的真实大小及缺页信息，不把准备结果当执行准入。原 `bind()` 明确只允许和顺/广哈的已记录修复，不是任意公司 source runner。

现役 [`stock_source_successor.py::_saved_document`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/stock_source_successor.py) 将库存行、journal body event、PDF bytes 与 extraction 的 locator/hash/length 互相核对；`_represent()` 复用同一保存 PDF，避免重新从源站取得。

强证据为 [source-only run 34765190284](https://github.com/auguspp/decision-kernel/actions/runs/34765190284) 的 artifact `10320565453`：ZIP 12,563,240 bytes，SHA256 `25cda8a1d4afb4783432320239cd6271fe193cfdc5ed6dc2095a5deb833dce9c`，91 文件、33 份 PDF、解压 17,331,131 bytes；和顺 20 份/372 页，广哈 13 份/286 页。原件字节与完整页序列在 [5654388807](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5654388807) / 上述 audit 中核对；[后续真实执行 5659344328](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5659344328) 的嵌套 `source-successor-origin.zip` 与原 source-only ZIP 逐字节一致，实际复用了这批文件。

本次重读原 run 的 GitHub artifact metadata：`expired=false`，digest/size/head 与原记录一致，expires_at `2026-10-13T15:19:28Z`。这是 metadata 再确认，不冒称本次重下载或逐页重审全部 33 份 PDF。原件 artifact 有保留期限，不是永久备份。

## 4. 完整输入无损保存与真实发送：后续已激活，早期文档不可倒退引用

现役 [`stock_full_input.py`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/stock_full_input.py) 与 [`stock_full_input_bridge.py`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/stock_full_input_bridge.py) 使用标准 zlib/base64、原 checked-source、BoundFullContext 与原 SDK hook；保留完整 bytes、原来源/正文/时钟，不把压缩串当模型正文。

演进顺序：#357 的独立 codec → #358 原 host 接线 → #359 测试时钟修复 → #360/#361 正常 successor/技术接续 → #362 修正保存完整 context 仍误入旧 512 KiB JSON decoder。当前 `stock_source_successor.py` 的最后相关修正 commit 是 `e90d338577c8035dd82f96b2f48ad8c660b12324`；[5659189421](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5659189421) 记录 #362 的完整 PR/main CI 与正常发布，代码只改原 decoder 接点及回归。

最终事实由 [34807883332 实际运行回执](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5659344328) 支撑：

- 和顺完整明文 873,576 bytes，存储封装 288,129 bytes；广哈完整明文 658,453 bytes，封装 225,221 bytes。
- 33 份 PDF/extraction 及原 captured_at 不变；3 个实际阶段 prompt 的 public_context 等于完整解码明文。
- 实际 SDK 请求 bytes 分别 916,421 / 692,759 / 704,382，均有 pre-send hash 和 completed provider response；不是假 transport 测试。
- 原 artifact `10333852308` 的 ZIP 26,048,878 bytes，SHA256 `7b7723908e329b3eff66fa680969d5e70d1be380701292caacfce6053f433827`；本次 metadata 再读取仍未过期，expires_at `2026-10-14T05:02:24Z`。

当前限制仍有 `TICKERS={603353,300711}`、512 KiB 存储、1.5 MiB 解码、2 MiB 请求，仅原明确修复范围。模块 docstring/早期 docs 中“尚未激活”描述的是该历史切片，不应覆盖后续实际调用证据。也不能借此把沃顿的原授权预算自动扩至 2 MiB。沃顿本轮 H1 完整逐页 JSON 为 271,234 bytes（约 265 KiB），先测实际必要输入，不为了用旧 codec 而扩建。

## 5. 问题声明与原准入：真实 prepare 正向已经完成

现役 [`reviewed_question_input.py::prepare`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/reviewed_question_input.py) 读取精确 question、同 R、先存来源、旧研究关系和必要类，再调用原 `prepare_input`。现役 [`external_research_admission.py`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/external_research_admission.py) 已区分 STATIC / LATEST_INVENTORY，准备和启动准入分开；无需另造 gate/schema。

[#455 完整正向验收 5742478124](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5742478124)：真实 `prepare` 调用发生于 `2026-09-19T13:27:05.576063Z`，结果 `QUESTION_INPUT_PREPARED_NOT_EXECUTED`；canonical input `54f606c5217a3a12cd55865d595bc15bedb03029b47f6150d3661537d456736e`。原档案 `20fd886cfe570e2af184cd62a9e04580b38c4769/docs/readings/300711-question-input-positive-2026-09-19/`；question commit `27cb769d2ef54e3fa0231cfeffb40c84e14a17d4`、preflight commit `9295e6af038851a9fd67cdb931af0eb0fd004a9d`，先声明→实际原件检查→prepare 顺序成立。#455 PR/main CI 4385 passed；这不是重复 mock 原 prepare 得到 PASS。

[#456 5743173577](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5743173577) 已把 [`stock_question_host.py`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/stock_question_host.py) 接入原 Stock workflow/job/concurrency/Retainer；稳定根只依 security+question_id，revision/run 改名不能重复消费。#474 在其上追加有界 daily 组合，完整验收见 [5749800329](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5749800329)，4658 项 PR/main CI，未另建 executor。

当前问题宿主实际仍只接受 `NEW_DISTINCT_QUESTION`，CONTINUE_ANALYSIS 等关系要求原接续路径。沃顿已保存草稿与旧基线关系不能靠改标题避开。用户本轮财报范围变更应留下 old→new 和适用边界，不改旧失败、不重用过期输入 token。daily v1 的 CNINFO artifact、单 PDF 512 KiB、ORIGINAL_PYPDF、STATIC 是该专用入口的限制，不是财报阅读、progress 留存或所有 Research 的全局限制。

## 6. 原 Pre/Quick 与 Retainer：真实执行很多次，但技术成功不替代语义审阅

现役 [`saved_research_once.py::research`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/saved_research_once.py) 使用原 Pre/Quick 类型和 `validate_pre_research_transition`；只有合法 Pre `CONTINUE_TO_QUICK` 才构造 Quick，原 `validate_external_research_candidate` 生成验证/Funnel。模型输出与 usage 先保存；无工具、无技术重试、失败不修造路由。`Retainer` 使用原 Git create-only、精确读回，写入未知后停止进一步写入。

实际已运行案例支撑不同组件：

- 苏垦 34548590855：真实 Pre 和 Quick，原 validator/Funnel 完整离线重现，原 source/input/candidate/receipt 已保留。
- 东软 34744840053：完整来源→Pre/Quick→原验证→工作 ref→固定 R 已验；光电 34751517820：10 份正文完整取得，真实两阶段、保存 validation/Funnel 全 JSON 重现。见 [5652012258](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5652012258)、[5652913153](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5652913153)。
- 和顺/广哈 34807883332：和顺 Pre 一次，广哈 Pre/Quick 两次，actual output/usage/完整 inputs 留存；原 WAIT/DROP 理由误用旧失败状态，被独立追加审阅挑战。不能说没有运行，也不能说结论因 validator 绿灯已接受。

[#363 5659976885](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5659976885) 已修正后续 prompt 对当前输入与历史来源状态的区分；原输出不改写。[追加业务审阅](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/docs/readings/stock-business-review-addendum-2026-09-14.md) 在不新增模型/来源的情况下继续形成有据的有限业务阅读，说明“历史状态不齐”不应抹掉已有真实内容。

## 7. 中途 progress 保存：不等估值或全部资料

现役 [`research_commit_only.py`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/research_commit_only.py) 的 `save_research_progress/read_research_progress`，CLI `save-progress/read-progress`，保存原 workpaper bytes 与独立 progress.json，绑定 subject/question_id/revision/predecessor digest、独占创建和写后读回。reader 不执行保存正文的下一步。

[#403 / #321 5695692687](https://github.com/auguspp/decision-kernel/issues/321#issuecomment-5695692687) 有真实远端 roundtrip：typed progress 档案 commit `1f11d4853d11ba204760a5b620d80edcdf40026f`，恰好两文件：progress.json 519 bytes / blob `74e3e76113f642a71e583777625615f9c848b6ac`；workpaper.md 7,269 bytes / blob `fda17f439ddb03323de60b6a77dac1bd8974dd02`，原底稿 blob 直接复用。PR/main CI 3546 passed；正常 [publisher 35082341885](https://github.com/auguspp/decision-kernel/actions/runs/35082341885)，main `18f659d8232268019756896504ac4c9b2838d79f`，R `747ac8618c237895ce27d7fc4822efe82500e9ac`，经同 R registry→原 commit/tree/blob 恢复。

对当前工作：已得到的财报阅读、财务矛盾、有限结论、UNKNOWN 和接续问题可以先保存；它不是一次新 COMMIT、自动调用、Human 接受或完整 Full Research 认证。

## 8. Research-only COMMIT 与档案：#321 已有正式收口

现役 [`research_commit.py::commit_research_package`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/research_commit.py)、`research_commit_only.py::commit_research_file/read_retained_commit` 复用原模型与 deterministic commit；v2 Research-only 不要求虚构 Market、期限、概率或 Odds。任意 Markdown 不因此成为合格 package。

[#412 / #321 5706547278](https://github.com/auguspp/decision-kernel/issues/321#issuecomment-5706547278) 真实北大荒 Research-only commit→archive→registry→fixed R：main `0ef823035a8567943930dc7438149d2b4e6c4609`；main CI `35165707884`，3728 passed；正常 [publisher 35166046150](https://github.com/auguspp/decision-kernel/actions/runs/35166046150)；R `046290b34d38a117fcef16c7fa150bae9bc049f0`；registry `600598-research-commit-20260917`；原四文件档案 `b116981dde58efe3132cdcd477ec93ed0066ddae`。包保留 `NOT_ESTABLISHED` 模型风险、`EXTRACTED_VALUES/PARTIAL`，Market NOT_REQUESTED、Odds NOT_COMPUTED。

现役 [`research_archive.py`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/research_archive.py) 与 [`research_archive_index.py`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/research_archive_index.py) 已负责精确 Git 档案恢复，不需要另建存储或恢复器。普通 reader 每档案最多 16 件、每件 512 KiB；本轮沃顿 1.26 MB PDF 要使用真实大原件保存路径，不截短塞入普通 reader。

[#418 / #321 final closeout 5714722473](https://github.com/auguspp/decision-kernel/issues/321#issuecomment-5714722473) 已正式收口该需求，A3/A4 独立 Research 留存/COMMIT 为 PASS。早期 docs 的 OPEN/未来时态不能覆盖后续验收；#297 日常新研究全闭环仍是另一层验收。

## 9. 正常 publisher 与原 Brief：现役交付机制，不等于新链已完成

现役 [current-state-read-entry.yml](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/.github/workflows/current-state-read-entry.yml) 监听生产、Research 与 main CI，调用 [`current_state_delivery_with_odds_watch.py`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/current_state_delivery_with_odds_watch.py)，已有 `--include-reviewed-questions`。底层 [`current_state_delivery.py::publish`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/src/decision_kernel/runtime/current_state_delivery.py) 基于已有 tree 创建新 commit、先读回候选 current-state，再非 force 更新 ref。

已有自然链实证：[5680533525](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5680533525) 的 Stock `34969200369`→自然 Research `34970111538`→正常 publisher `34970187887`→R `ebde16aff905f6792a84124cf0265d0d75303cfd`。该 Research 在真实 source failure 后停止，model=0；证明自然事件与失败可见性，不是研究成功。

最新档案发布 [#475 / 5750264017](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5750264017)：当前 main PR/main CI 4658 passed，正常 [publisher 35514946801](https://github.com/auguspp/decision-kernel/actions/runs/35514946801)，R `d121e57cbcad08064fcc41e4f54139b86ddc0ffa`；原 `recover_archive` 在实际 connector 响应快照上恢复 7 文件、11 次 logical reads，状态 `RECOVERED_ON_DEMAND_AFTER_REGISTERED_ONLY`。

Brief [5749800329](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5749800329) / [固定 retention-receipt](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/docs/readings/p0-takeover-2026-09-20/retention-receipt.json)：原任务 `6aa28013b7348191a647f2f8e75d6017`，v1.3、enabled、每日 19:15 Asia/Shanghai，实际 prompt 更新逐字读回，SHA256 `32186417529dcea15e8f374557b4cd48906a800c044727925d38dbc03c8fa10c`；无第二任务或 Run now。本轮核对采用已保存回执，未新改任务。v1.3 下一自然交付及首例新研究→Brief→Human 响应仍须真实验收，不能用配置/CI替代。

## 10. Human 精确版本回应：已有真实保存先例

现役协议 [`human-exposure-and-response-capture-v0.md`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/docs/human-exposure-and-response-capture-v0.md) 与 [`p0-daily-brief-and-response-v0.md`](https://github.com/auguspp/decision-kernel/blob/728de4ead5094a74c835304c9a6e7fc385c48e6f/docs/p0-daily-brief-and-response-v0.md) 复用现有 Issue/comment/checkpoint，先定位已见版本、查重，区分原话与解释，再保存并实际读回；无新 Human-response schema 或数据库需求。

实际读取的 [600598 checkpoint](https://github.com/auguspp/decision-kernel/blob/e8f51d75111a29bbe62dc7eb160725e722542145/docs/decisions/600598-beidahuang-human-odds-acceptance-2026-09-16.md) 保存 Human“嗯，我现在同意了 odds”：commit `e8f51d75111a29bbe62dc7eb160725e722542145`，blob `f25f25cadd7018563f0a6394cbe7958337428765`；绑定 BA2 ref `daf25acbda3a764c73ffad1a5de89bc365e6d924` 下的 `docs/readings/600598-beidahuang-odds-revision-2026-09-16/provisional-odds-revision.json`、blob `d35934f5f4ef27a225c7d7928e5ee7634dab3878`，冻结 Research `fefff5b49ecfbe4f5cfb4aa62cf29f6f9f26aa03`。当前 registry 仍有 `odds-beidahuang-human / HUMAN_DECISION_CHECKPOINT`。

该先例证明精确“哪一版、哪一层”的回应能保存；不把北大荒接受转给沃顿，不推断买入、Action、Watch，也不是 v1.3 新 Brief 的送达/接受证据。

## 已知过时表述与不应重做的工作

1. `stock_research_sources.choose()` 现役 legacy baseline 会选最新完整报告及其后全部声明正文；源码和 `research-source-scope-v0.md` 均明确它属于 FIRST_BUSINESS_BASELINE。该特定合同不能变成所有研究的前置要求，更不能覆盖 Human 本轮财报优先范围。
2. 当前 `research-source-scope-v0.md` 的“新的按问题 Stock 接续尚未实现”是早期状态；#453/#455/#456/#474 已交付明确问题准备与手动有界宿主。自动问题生成、自然日常研究和真实 P0 全闭环仍未因此完成，应写清现在的具体边界。
3. full-input 早期“未激活”文字被后续实际 host/successor 执行所超越；不要重做 codec、page23 或 #362 decoder 修复。
4. #321 既定工程需求已由 #418 正式收口；不能重新制造 Research-only 保存/COMMIT 缺口。
5. 原两家公司 WAIT/DROP 语义挑战保留，但实际模型、输入、保存、发布已经发生；未知原结论不等于没有基础设施或没有任何可继续的研究内容。
6. #470 旧 checkout 导出诊断草稿已由 #474 替代关闭；不能继续视为主线功能欠账。
7. 当前无需为财报获取新增 provider/scanner/OCR/调度框架，也无需重跑旧公司已消费 key。后续只修已经被真实沃顿输入证明的最小接点。

## 实际核对范围与本轮未做的验证

- 当前代码与文档固定在 M，不切换分支、不改仓库。实际读取 AGENTS、RESEARCH-ENTRY，精确搜索并阅读上述来源获取/原件留存/解析/准备/完整输入/问题/执行模块及相关 workflow；子任务实际核对 progress、commit、archive、publisher、Brief/回应模块、协议与固定 checkpoint。
- 使用已恢复的 #297 362 条评论清单，按组件关键词定位并阅读本文引用的验收/失败/后续更正段落；#354 DataSinking 两条相关评论；子任务读取 #321 相关真实 progress/commit/final-closeout 回执。不是全文通读全部 362 评论，也没有声称读完所有 Issues/PR/history。
- 只沿已知原件/来源索引/fixed refs 和少量 `git log -1 -- path` 判断演进；没有重扫 529 refs 全部文件。当前 main 精确 DataSinking 文本搜索及所有 commit message 的有界精确词搜索未找到 probe 配置，不代表其他会话或外部机器从未配置。
- 本轮重新通过 GitHub run/artifacts metadata 核对苏垦 `10180018843`、source-only `10320565453`、Stock 恢复 `10315717092`、实际完整输入 `10333852308`：digest/size/head 对应，均未过期。子任务重读三个正常 publisher 的 run metadata，均 workflow_run / attempt1 / completed-success。历史“下载并逐字节核验”来自原固定验收，本轮没有重复下载这些大 ZIP 或重跑其 parser/model。
- 本轮新取得的沃顿 Sina PDF 与解析文件另有真实获取/字节回执；本份历史核对任务没有新增财报/公告获取、模型调用、workflow dispatch、GitHub 写入、库/预算修改或新测试执行。
- 可优先关注的 docs 字面测试：`tests/test_disclosure_on_demand.py::test_research_entry_links_source_scope_without_weakening_legacy_stock_contract` 硬断言 source-scope 含“尚未实现”。修正过时状态应调整该定位断言以核对真实边界，同时保留 required report/update 缺失负对照、旧 baseline 范围与 RESEARCH-ENTRY 的源计划纪律。`test_radar_question_contract.py` 还要求 source-scope 的 contract 链接；`test_odds_book_navigation.py` 要求入口保留 Odds Book v0。

本轮读取出的直接施工方向是：使用已保存的沃顿财报完成财报内的业务/利润/现金桥并保存可接续进度，同时修正接手入口对历史能力的过时描述。是否需要更大原件 custody 接口或显式同问题执行薄接线，应由实际将进入原宿主的材料证明；不是先开展全仓 consolidation。

## 本轮已经产生的财报接续

沿上述既有能力，已实际保存[沃顿财报内利润到经营现金底稿](https://github.com/auguspp/decision-kernel/blob/7e992b3ce83993897930076f64da0eb9cf2035f6/docs/readings/000920-reports-only-progress-2026-09-20/workpaper.md)，commit `7e992b3ce83993897930076f64da0eb9cf2035f6`。原问题根保持 `stock-business-66446c4257a92cd4576ee87ff1bd4ead51ca61a4292befc55cbde3d514b5542c`；旧档案是RETAINED_FILES，本次revision1仅表示第一次使用typed progress保存该旧根，没有新建独立研究问题。

第104页12项实际金额经Decimal逐项重算，两期均精确勾稽至经营现金；同比经营现金增加19,164,293.37元，分解为合并净利润增加5,507,828.90元、其他调节项增加1,492,513.92元、营运项目负向影响减少12,163,950.55元。采用合并净利润，未混用归母利润。第16页的膜产品/工程收入、成本和毛利也已有明确页表与算术；量价/组合/单位成本的定量归因及按业务分配集团现金仍未完成。

本次使用原save-progress/read-progress保存恰好两个文件，并将远端tree/blob/大小/原字节逐项读回；`progress.json` SHA256为`0124c5dac5d2bc9c9e20a6b9de9b7b7bcbe532e589e15fe27ee08884f14372c6`。用途索引只追加`p0-000920-reports-only-profit-cash-20260920`的ON_DEMAND_ARCHIVE定位；登记不等于正文已进入每次日常读取。待正常publisher产生R后，另行执行原archive reader从该R恢复，保持RETAINED_PROGRESS_NOT_COMMITTED；本文件不预填该步骤已完成。原PDF及DataSinking全文不是这两件progress文件的一部分。

下一步直接复用已保存财报与本底稿，继续报告内管理层讨论、收入成本及营运资本附注的明确缺口。若以后要执行正式同题Pre/必要Quick，再在既有root接续与原预算内做必要来源消费接线；本次没有改runtime、重新开旧launch或调模型。当前daily的来源/旧题绑定尚未适配这份沃顿材料，并不妨碍有限财报研究与进度留存。
