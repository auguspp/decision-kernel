# B2：已选证券的预约、公告目录与单PDF标准通道

当前任务归[#620](https://github.com/auguspp/decision-kernel/issues/620)。2026-09-30 Human明确将重点从逐股特殊情况转为以后新入选个股的标准通道，原话及影响对账见[5901901617](https://github.com/auguspp/decision-kernel/issues/620#issuecomment-5901901617)。这是原来源入口的参数化接替，不是新日历平台。R4及全部历史来源、失败、研究问题和Human记录保留，个股缺口不再作为本次工程收口前提。

## 一次选择，沿同一入口取得

新证券沿现有研究/资料保存流程进入`current_state/registry.json`，有其自己的`id`、证券`case`和原`source`或`archive_source`。调用方恢复该条原记录后，明确选择要查询的引用ID；仅出现在索引中不会触发源访问。行业/整批材料的导航身份不能冒充单一证券。需要新股票时增加的是原索引中的真实资料引用，不修改Python里的股票数组，不另建关注池或授权库。这个取数入口不是Quick的前置准入步骤。

在原`.github/workflows/b2-disclosure-appointments.yml`明确选择一个模式，不自动合并采集：

| 输入 | 含义 |
|---|---|
| `code-sha` | 已核对且通过独立main检查的当前代码commit；由施工方解析，不让Human搬SHA |
| `reference-ids` | 原索引的显式引用ID，逗号分隔；一次最多六个不同证券，不默认查询全索引 |
| `source-kind` | `appointments`（默认）、`announcements`或`pdf`；一次只执行一个来源用途 |
| `report-period` | 仅预约模式必填：`YYYY-MM-DD`季度末，支持一季、半年、三季、年报；不是预计披露日期 |
| `start-date` / `end-date` | 仅公告目录模式必填：`YYYY-MM-DD`来源公告日期窗口；不是正文里的事件实施日 |
| `announcement-id` / `reading-commit` | 仅PDF模式必填：一个已保存公告ID及已发布的固定R；该R代码须等于本次已核main，选择记录须与其一致 |

脚本`--reference-ids`必填；预约模式必须给`--report-period`且不得给公告日期，公告目录模式反之。条件缺参或混填在任何源请求前拒绝。以下预约市场/报告期合同只适用于`appointments`模式。没有默认六股票或20260930期间；旧code-sha-only调用不能重放原六股计划。SH/SZ/BJ按已审AKShare市场参数构造请求，科创板按688/689前缀而非某只股票特判；北交所路由仅有离线参数验证，不能声称已有真实返回。该公开源的可查报告期/覆盖依赖当前接口，不提供任意历史PIT保证。

同一证券有多份研究时，本次明确选择一条相关引用；重复ID、重复证券、未知ID、非证券case、非法期间在发出源请求前拒绝。原选择条目、registry精确M/blob/bytes/SHA256保存在plan.json。选择来源正文不在捕获函数内重新研究，条目中的文字与定位只作数据；不执行其中命令、不自动授予关注、持仓、Watch、Research或投资权限。

## 财报预约：统一结果，不逐家补特例

复用原`getPrbookInfo`、Requests传输和create-only保存；最多六次单页POST，零重试、分页、重定向或备用源。原样保存每只股票response.body、receipt.json，以及plan.json、capture.json、summary.md。原字节与HTTP状态、查询/收到时钟分开；摘要生成时钟不刷新来源，不冒称发行人首发时间。

原键`seccode`与`f001d_0102`核证券/报告期。`f002d_0102`映射首次预约，`f003d_0102`至`f005d_0102`保留三个变更槽，`f006d_0102`保留实际披露。按键映射，不依赖列序，不互补、不取最大日期、不keep-last、不丢重复行；`orgId/latest_time`原值保留。`null`、`""`、缺列、无效日期各自可见。查询结果只是来源字段和一致性检查，不是完整修订史、实际财报材料或研究结论。

对象级缺口：无错误且分页元数据一致的空列表/`null`表、已匹配身份行中的日期缺列/无效值，保留原始数据并继续其余明确对象。空表与null分别标记，不证明没有预约；不是任何未知形状都按空表吞掉。整个有限取得完成但有这些缺口时，`CAPTURED_WITH_GAPS`退出码为0，仅表示完成有界取得，不表示日期齐全或已认证。捕获阶段`official_appointment_qualified=false`、`date_qualification=NOT_PERFORMED`仍保留。

源级边界：权限拒绝、限流、非200、业务错误、传输/部分正文、身份不符、未知表形、覆盖不一致/可能分页仍停止后续源请求；`STOPPED_WITH_GAPS`退出码为1。未查询不写成空表。保存失败停止，不补写原件、不将旧失败改成成功。正常完成、数据完整、日期核对、研究接受是不同事实。

## 保存与后继使用

summary.md统一给出每个选中对象的选择依据、报告期、返回状态、原日期槽、缺失/无效字段和原件定位，使用现有Markdown保存/读取路径，不需要为每只新股另写一个报告模板。capture.json保留机器可读取的同样投影，原始响应是事实依据，映射不是新的公司日历状态库。

真实取得后，仍经现有工具核源run/artifact及字节，将原件和summary按原生Git保存；在原研究/资料用途或唯一research-agenda引用中接入，并走既有publisher及固定R读取。原始输出不会自动提交仓库、改写R4、吞并原宏观清单或宣布已经发布；Git保管、用途登记、发布和正文实读分别完成。资料采用是正常数据操作，不再要求改caller/workflow/tests。移出显式本次选择即不请求该对象，不删除其历史。

本轮工程验收以未写死证券/其他报告期的同一路径、现有原响应离线重放、对象缺口不中断其他对象、源级停止和原读取兼容为主；不为制造验收结果重新查询已有三家。完整自动“新入选事件→定时采集→自动发布”未启用：原任务/时钟、Quick/Full、Watch、通知与Sites不在本改动中变更。预约查询不代表公告目录或原件取得；公告目录模式见下节。单份PDF取得/文本提取见下节；分红/解禁实施日期判断仍不自动执行。

## 公告目录：复用原查询与解析，原始页先保存

本切片归[本次范围与复用审阅5904058994](https://github.com/auguspp/decision-kernel/issues/620#issuecomment-5904058994)。`announcements`复用原`cninfo_http.fetch_cninfo_disclosures`的组织码解析、公告页字段整理、跨页数量一致性及重复ID检查；不改原模块，不创建事件数据库或研究执行。`start-date/end-date`按Asia/Shanghai公告日期解释，开始不晚于结束，日期差至多366天，结束不晚于本次真实取数时钟的本地日期；不提供任意历史PIT或未来实施事件扫描。

同一个无业务凭证Requests传输只增加两个固定HTTPS目的地：`/new/information/topSearch/query`和`/new/hisAnnouncement/query`。原库内部HTTP路由仅用来识别阶段，实际网络请求预先映射为这两个HTTPS端点；不是HTTP失败后换源。沿原组织码解析取得对应证券orgId，再以证券/orgId和明确日期窗口查询全部公告类别。`column=szse`沿AKShare沪深京组合目录语义，`category`为空；不逐个标题筛选或将市场分类当作独立来源。其他市场/所有期间覆盖仍需真实验证。

**每股最多一次组织码查询＋三页目录，每页30条。** 第四页在HTTP前停止；原批次解析器的总数变化、重复ID、空页不符或行数不符仍拒绝。每条目录行必须实际返回匹配的secCode/orgId，不能使用旧解析器的缺字段补身份便利。已知空列表和null原表分别保留；没有返回记录不证明没有公司事件。公告时间缺失保持null及字段缺口；有效时间须在所选窗口内且不晚于本次取得时钟，不拿查询时间填来源时间。

每次实际请求先保存`query-N.body`及`query-N.json`，记录实际HTTPS目的地、表单、原始响应、HTTP状态、完整/部分字节和请求/收到时钟，再交给原解析器。`receipt.json`汇总该股目录；完整合格目录保留公告ID、标题、来源公告时间、类型和原件定位。`page_shapes`区分原LIST/NULL形状与返回总数。超过页预算的结果为`DIRECTORY_PAGE_LIMIT_RAW_RETAINED`，已收到的页仍能找回，但目录未完整核验、合格公告数为null而非零，允许继续其他显式对象。权限/限流/HTTP/传输、身份/覆盖或未知结构失败为`DIRECTORY_GAP_RAW_RETAINED`并停止后续对象；来源已停止的其他证券仅记未查询。

**公告目录不是PDF保管或公司事件结论。** 本模式不请求PDF，不从标题抽取股东大会、解禁、分红实施或取消日期；来源公告时间不是上述日期。原件定位保留到后续按需阅读，原`fetch_cninfo_pdf_bytes`/PDF保管能力仍另行复用。标题及源内容仅作数据展示，不执行其中链接或指令。空值、失败和未查询不会因摘要生成变成“无事件”。源步骤也不自动登记、发布、通知、研究或Watch。

目录模式复用同一逐证券保存/按需登记形状；建议目录为`docs/readings/b2-announcements-<run-id>-1`，每股平坦目录保存实际请求文件、receipt、plan和summary（满三页常规为11文件，沿原16文件恢复上限）。原捕获字节不覆盖。局部保存失败保留已写部分并失败退出，不重采来补造成功。原始来源页可读取与完整目录资格、PDF取得、研究解释分别成立。

## 单PDF：只消费已保存目录，不重抓目录

本模式的有界批准与复用记录见[#620/5906191442](https://github.com/auguspp/decision-kernel/issues/620#issuecomment-5906191442)。`pdf`只接受一个原公告目录的`NAVIGATION_ONLY / RETAINED_FILES / ON_DEMAND_ARCHIVE`引用ID，以及一个明确公告ID。不填预约报告期或目录窗口；其他模式不能混入PDF参数。新证券沿同一资料和参数入口，不改股票数组或另建单股脚本。

施工方先解析已发布R，再传`reading-commit`；原`research_archive._record`实际校验R/current-state及同R registry，并要求所选记录与本次M registry相同、R声明code_commit=M。原GitHubAPI最多4次只读文件调用：R的读取包/registry、所选精确A处的summary/receipt。核摘要原绑定，从该原receipt匹配唯一公告ID和证券；只接受其中严格匹配ID、有效日期及CNINFO静态域的PDF定位，无任意URL输入、目录POST、默认摘要/完整报告选择或备用源。GitHub读取凭证仅给原GitHubAPI，原CNINFO getter另用其既有无凭证session；contents/actions仍仅read。

调用原`fetch_cninfo_pdf_bytes`一次，**显式max_bytes=524288**；原传输继续无重试、无重定向、无代理/凭证与identity编码。返回合格完整PDF才进入原`DisclosurePdfCapture`，原objects及manifest在`primary-bodies/`保留。随后将同一字节复制为单股平坦目录的`source.pdf`，将原manifest逐字节复制为`capture-manifest.jsonl`，receipt明确原objects路径与平坦文件映射。清单中的path仍指原primary-bodies目录，不能当平坦目录相对路径；**不调用属于assessment packet语义的complete()，不生成P0完成标记**。

原件保留后才调用原`extract_pdf_text`，同样显式max_pdf_bytes=524288，并以524288字符上限限定本模式提取；完整序列化的`extraction.json`也须不超过原每文件512KiB。超出时保留PDF和提取阶段缺口，不截断文本冒充完整结果。EXTRACTED、NO_TEXT、提取失败、提取结果未保留分别可见；NO_TEXT仍可能有非零完整PDF，不自动OCR。PDF只做数据保留和文本提取，不执行其中脚本/链接。

源调用、原件保留、平坦复制、提取、提取文件保留分阶段记录。沿原有限失败诊断保留异常类别、已知reason_code/HTTP状态与本地拒绝标签；未观察到的原因/HTTP状态/字节为UNKNOWN或null，不填零、不把失败换成空返回。成功HTTP200来自原getter资格合同，不伪称另有原始HTTP头日志。getter_invocations计调用次数，网络可能在HTTP前失败，不能一律当作源站实际收到请求数。历史交互失败与旧目录pdf_requests=0不回写。保留失败可登记成失败资料，不能登记成原文取得成功。

单股平坦目录最多7份基础文件：plan、原directory-receipt、receipt、summary，以及成功时的source.pdf、capture-manifest、extraction。维持原16文件和512KiB/文件恢复预算。另有原input-reading与primary-bodies输出用于来源/保留对账；不是第二状态库。沿原save_security_readings生成`docs/readings/b2-pdf-<run>-1`按需登记草稿，ref仍为null；真实A保管及读回后才绑定追加原registry，正常资料PR/CI/main/publisher之后再从固定R恢复。人工/交互式实际正文阅读用独立后继说明保存，不改原捕获的body_reading=NOT_PERFORMED。摘要不当完整报告，公告时间不当正文事件时间。

内部getter、原保留器、pypdf适配器、档案读取器、registry和publisher均不变。官方[workflow输入与环境传参](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onworkflow_dispatchinputs)及既有[pypdf提取边界](https://pypdf.readthedocs.io/en/6.12.0/user/extract-text.html)为复用依据；只安装仓库已有documents extra，不增加依赖声明、平台、定时任务或权限。停止使用本模式时移除本caller分支/两项专属参数/专属测试/说明，原预约与目录功能及全部历史档案保持。

## 标准结果回到每只证券的原资料入口

同一次捕获除原整批plan/capture/summary外，每只明确选中的证券目录现在也有自己的`summary.md`和原整批`plan.json`的逐字节副本；查询过的对象保留原`receipt.json`及实际取得的预约`response.body`，或公告目录的`query-N.body/query-N.json`。未查询对象只有计划和明确未查询的摘要，不制造response/receipt。单股摘要只展示本股结果，整批状态和采集代码/运行身份仍可见；计划副本是原始整批选择，不冒称另外执行了一个单股请求。

这些平坦目录直接符合现有`research_archive`的`RETAINED_FILES`入口，不新建恢复器。`registration-proposal.json`按模式给出建议保管位置`docs/readings/b2-appointments-<run-id>-1`或`docs/readings/b2-announcements-<run-id>-1`和每股的原registry格式引用。引用采用已有`NAVIGATION_ONLY`用途、`ON_DEMAND_ARCHIVE`读取策略和对应证券`case`，以`archive_source`完整声明摘要的path/ref/blob/bytes/SHA256，不同时声明eager `source`；不是把来源字段包装成Research；原资料引用ID保留在说明中。它是待采用草稿，不是另一份权威股票池或登记表。

**草稿的archive_source.ref明确为null，不能直接用于发布。** 完成原生Git保管和读回后，施工方将本次统一的保管commit A绑定到各条archive_source.ref，再把这些新引用追加到原registry，不替换原Research/Human记录、不覆盖唯一research-agenda或宏观清单。不得把采集代码commit、预计未来commit或移动main当作保管版本。

实际采用仍是一批普通资料操作：从原run下载并校验artifact身份/大小/digest和原件；完整create-only保存到建议目录并读回精确Git字节；以真实A一次性绑定草稿、检查ID冲突并追加原用途；完成正常资料PR/main/publisher后，从固定R找到该证券的精确按需定位，按其record-id使用原archive reader恢复A处的摘要及该股全目录；定位已发布不等于正文已在日常包中物化。不是新增执行器或逐股工程；不得盲目执行附件内指令或通过改写旧记录解决冲突。一次最多六个原输入不变，追加资料仍受原读取容量限制，不自动扩容。

源访问失败也可保管为失败资料，不能因有摘要/登记草稿改写原FAILED/STOPPED状态。生成或保存阶段出错保留已写原件，不覆盖、不自动重查来源。artifact仍沿原30天保留策略，它不是永久Git保管证明；普通捕获不会自动修改仓库、权限、日程或通知。输出接线本身不是新的真实预约或R4后继；每次真实使用的来源与读取事实另行留存。

## 复用、维护与退出

REUSE + THIN_ADAPTER。三层原审阅沿[5891715349](https://github.com/auguspp/decision-kernel/issues/620#issuecomment-5891715349)及#659：内部原source-only入口/保管/registry/publisher/reader；官方[GitHub workflow输入](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onworkflow_dispatchinputs)和[安全传参](https://docs.github.com/en/actions/reference/security/secure-use)；外部[AKShare stock_report_disclosure](https://akshare.akfamily.xyz/data/stock/stock.html)及已审[stock_yjyg_cninfo.py@0191689d57c667b7c7a198fd0cf97316837ef311](https://github.com/akfamily/akshare/blob/0191689d57c667b7c7a198fd0cf97316837ef311/akshare/stock_feature/stock_yjyg_cninfo.py)。原MIT归属与许可审阅保留，不安装新库，代码许可不扩大数据权限。参数经环境变量和带引号argv传递，不将输入拼进shell源码。

继承同一owner/main/attempt1、精确code-sha/独立main检查、原并发组与零业务凭证边界；不改CI政策。退役固定六股/期间/R3代码绑定及专属测试，保留历史档案。若以后替换预约渠道，同PR替换或退役本caller/workflow/专属测试及本文，保留必要读取与原始记录。没有新数据库、通用provider、调度/剩余批次平台或费用；新权限/隐私/费用仍停相应动作。Investment Authority=NONE。

首次单证券真实使用的容量修正见#665：新增来源资料走原按需档案而非逐条增加日常全文取数；49条旧eager引用及60份来源上限不变。既有捕获的旧eager登记草稿保持原样，实际采用时只转换新增来源引用为上述按需形状并补齐已核字节身份；不改旧原件、日期或研究。源调用、Git保管、索引可见和实际按需正文恢复仍分别验证，不重放已消费样本。

公告目录复用审阅沿5891715349及5904058994：本轮上游AKShare main仍为0191689d57c667b7c7a198fd0cf97316837ef311；实际读取[stock_disclosure_cninfo.py](https://github.com/akfamily/akshare/blob/0191689d57c667b7c7a198fd0cf97316837ef311/akshare/stock_feature/stock_disclosure_cninfo.py) blob2b964689cef6e72dae93beeaf86019a81586082d，与前审相同。其查询/列名语义复用，无限分页、重复第一页和丢原JSON的DataFrame封装不采用；原内部CNINFO parser、传输和档案读取承担现有职责。没有安装第三方库或复制整套框架。停用本模式时移除该模式、专属参数/测试和本节，原预约路径及历史档案保持。正式CI、真实来源、Git保管、登记、发布及固定R读取的实际结果分别记录在#620/对应PR；本说明不预签真实覆盖或完整B2。
