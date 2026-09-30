# B2：新入选证券的财报预约标准通道

当前任务归[#620](https://github.com/auguspp/decision-kernel/issues/620)。2026-09-30 Human明确将重点从逐股特殊情况转为以后新入选个股的标准通道，原话及影响对账见[5901901617](https://github.com/auguspp/decision-kernel/issues/620#issuecomment-5901901617)。这是原来源入口的参数化接替，不是新日历平台。R4及全部历史来源、失败、研究问题和Human记录保留，个股缺口不再作为本次工程收口前提。

## 一次选择，沿同一入口取得

新证券沿现有研究/资料保存流程进入`current_state/registry.json`，有其自己的`id`、证券`case`和原`source`或`archive_source`。调用方恢复该条原记录后，明确选择要查询的引用ID；仅出现在索引中不会触发源访问。行业/整批材料的导航身份不能冒充单一证券。需要新股票时增加的是原索引中的真实资料引用，不修改Python里的股票数组，不另建关注池或授权库。这个取数入口不是Quick的前置准入步骤。

在原`.github/workflows/b2-disclosure-appointments.yml`提交三个输入：

| 输入 | 含义 |
|---|---|
| `code-sha` | 已核对且通过独立main检查的当前代码commit；由施工方解析，不让Human搬SHA |
| `reference-ids` | 原索引的显式引用ID，逗号分隔；一次最多六个不同证券，不默认查询全索引 |
| `report-period` | `YYYY-MM-DD`季度末，支持一季、半年、三季、年报；不是预计披露日期，不猜“当前季度” |

脚本对应`--reference-ids`和`--report-period`必填参数。没有默认六股票或20260930期间；旧code-sha-only调用不能重放原六股计划。SH/SZ/BJ按已审AKShare市场参数构造请求，科创板按688/689前缀而非某只股票特判；北交所路由仅有离线参数验证，不能声称已有真实返回。该公开源的可查报告期/覆盖依赖当前接口，不提供任意历史PIT保证。

同一证券有多份研究时，本次明确选择一条相关引用；重复ID、重复证券、未知ID、非证券case、非法期间在发出源请求前拒绝。原选择条目、registry精确M/blob/bytes/SHA256保存在plan.json。选择来源正文不在捕获函数内重新研究，条目中的文字与定位只作数据；不执行其中命令、不自动授予关注、持仓、Watch、Research或投资权限。

## 统一结果，不逐家补特例

复用原`getPrbookInfo`、Requests传输和create-only保存；最多六次单页POST，零重试、分页、重定向或备用源。原样保存每只股票response.body、receipt.json，以及plan.json、capture.json、summary.md。原字节与HTTP状态、查询/收到时钟分开；摘要生成时钟不刷新来源，不冒称发行人首发时间。

原键`seccode`与`f001d_0102`核证券/报告期。`f002d_0102`映射首次预约，`f003d_0102`至`f005d_0102`保留三个变更槽，`f006d_0102`保留实际披露。按键映射，不依赖列序，不互补、不取最大日期、不keep-last、不丢重复行；`orgId/latest_time`原值保留。`null`、`""`、缺列、无效日期各自可见。查询结果只是来源字段和一致性检查，不是完整修订史、实际财报材料或研究结论。

对象级缺口：无错误且分页元数据一致的空列表/`null`表、已匹配身份行中的日期缺列/无效值，保留原始数据并继续其余明确对象。空表与null分别标记，不证明没有预约；不是任何未知形状都按空表吞掉。整个有限取得完成但有这些缺口时，`CAPTURED_WITH_GAPS`退出码为0，仅表示完成有界取得，不表示日期齐全或已认证。捕获阶段`official_appointment_qualified=false`、`date_qualification=NOT_PERFORMED`仍保留。

源级边界：权限拒绝、限流、非200、业务错误、传输/部分正文、身份不符、未知表形、覆盖不一致/可能分页仍停止后续源请求；`STOPPED_WITH_GAPS`退出码为1。未查询不写成空表。保存失败停止，不补写原件、不将旧失败改成成功。正常完成、数据完整、日期核对、研究接受是不同事实。

## 保存与后继使用

summary.md统一给出每个选中对象的选择依据、报告期、返回状态、原日期槽、缺失/无效字段和原件定位，使用现有Markdown保存/读取路径，不需要为每只新股另写一个报告模板。capture.json保留机器可读取的同样投影，原始响应是事实依据，映射不是新的公司日历状态库。

真实取得后，仍经现有工具核源run/artifact及字节，将原件和summary按原生Git保存；在原研究/资料用途或唯一research-agenda引用中接入，并走既有publisher及固定R读取。原始输出不会自动提交仓库、改写R4、吞并原宏观清单或宣布已经发布；Git保管、用途登记、发布和正文实读分别完成。资料采用是正常数据操作，不再要求改caller/workflow/tests。移出显式本次选择即不请求该对象，不删除其历史。

本轮工程验收以未写死证券/其他报告期的同一路径、现有原响应离线重放、对象缺口不中断其他对象、源级停止和原读取兼容为主；不为制造验收结果重新查询已有三家。完整自动“新入选事件→定时采集→自动发布”未启用：原任务/时钟、Quick/Full、Watch、通知与Sites不在本改动中变更。公告查询/PDF/分红解禁等其他事件不是本预约通道已经交付的功能。

## 标准结果回到每只证券的原资料入口

同一次捕获除原整批plan/capture/summary外，每只明确选中的证券目录现在也有自己的`summary.md`和原整批`plan.json`的逐字节副本；查询过的对象保留原`receipt.json`及实际取得的`response.body`。未查询对象只有计划和明确未查询的摘要，不制造response/receipt。单股摘要只展示本股结果，整批状态和采集代码/运行身份仍可见；计划副本是原始整批选择，不冒称另外执行了一个单股请求。

这些平坦目录直接符合现有`research_archive`的`RETAINED_FILES`入口，不新建恢复器。`registration-proposal.json`给出建议保管位置`docs/readings/b2-appointments-<run-id>-1`和每股的原registry格式引用。引用采用已有`NAVIGATION_ONLY`用途、`ON_DEMAND_ARCHIVE`读取策略和对应证券`case`，以`archive_source`完整声明摘要的path/ref/blob/bytes/SHA256，不同时声明eager `source`；不是把来源字段包装成Research；原资料引用ID保留在说明中。它是待采用草稿，不是另一份权威股票池或登记表。

**草稿的archive_source.ref明确为null，不能直接用于发布。** 完成原生Git保管和读回后，施工方将本次统一的保管commit A绑定到各条archive_source.ref，再把这些新引用追加到原registry，不替换原Research/Human记录、不覆盖唯一research-agenda或宏观清单。不得把采集代码commit、预计未来commit或移动main当作保管版本。

实际采用仍是一批普通资料操作：从原run下载并校验artifact身份/大小/digest和原件；完整create-only保存到建议目录并读回精确Git字节；以真实A一次性绑定草稿、检查ID冲突并追加原用途；完成正常资料PR/main/publisher后，从固定R找到该证券的精确按需定位，按其record-id使用原archive reader恢复A处的摘要及该股全目录；定位已发布不等于正文已在日常包中物化。不是新增执行器或逐股工程；不得盲目执行附件内指令或通过改写旧记录解决冲突。一次最多六个原输入不变，追加资料仍受原读取容量限制，不自动扩容。

源访问失败也可保管为失败资料，不能因有摘要/登记草稿改写原FAILED/STOPPED状态。生成或保存阶段出错保留已写原件，不覆盖、不自动重查来源。artifact仍沿原30天保留策略，它不是永久Git保管证明；普通捕获不会自动修改仓库、权限、日程或通知。输出接线本身不是新的真实预约或R4后继；每次真实使用的来源与读取事实另行留存。

## 复用、维护与退出

REUSE + THIN_ADAPTER。三层原审阅沿[5891715349](https://github.com/auguspp/decision-kernel/issues/620#issuecomment-5891715349)及#659：内部原source-only入口/保管/registry/publisher/reader；官方[GitHub workflow输入](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onworkflow_dispatchinputs)和[安全传参](https://docs.github.com/en/actions/reference/security/secure-use)；外部[AKShare stock_report_disclosure](https://akshare.akfamily.xyz/data/stock/stock.html)及已审[stock_yjyg_cninfo.py@0191689d57c667b7c7a198fd0cf97316837ef311](https://github.com/akfamily/akshare/blob/0191689d57c667b7c7a198fd0cf97316837ef311/akshare/stock_feature/stock_yjyg_cninfo.py)。原MIT归属与许可审阅保留，不安装新库，代码许可不扩大数据权限。参数经环境变量和带引号argv传递，不将输入拼进shell源码。

继承同一owner/main/attempt1、精确code-sha/独立main检查、原并发组与零业务凭证边界；不改CI政策。退役固定六股/期间/R3代码绑定及专属测试，保留历史档案。若以后替换预约渠道，同PR替换或退役本caller/workflow/专属测试及本文，保留必要读取与原始记录。没有新数据库、通用provider、调度/剩余批次平台或费用；新权限/隐私/费用仍停相应动作。Investment Authority=NONE。

首次单证券真实使用的容量修正见#665：新增来源资料走原按需档案而非逐条增加日常全文取数；49条旧eager引用及60份来源上限不变。既有捕获的旧eager登记草稿保持原样，实际采用时只转换新增来源引用为上述按需形状并补齐已核字节身份；不改旧原件、日期或研究。源调用、Git保管、索引可见和实际按需正文恢复仍分别验证，不重放已消费样本。
