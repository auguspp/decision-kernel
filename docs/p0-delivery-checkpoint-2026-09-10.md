# P0 产品接续：把“做过什么、没做成什么”带回固定读取入口

北京时间2026-09-10凌晨的执行检查点；不是当天交易日结果，也不是新的Research/投资决定。
需求与Human授权：[Issue #297](https://github.com/auguspp/decision-kernel/issues/297)。首份交互Brief：[Issue #299](https://github.com/auguspp/decision-kernel/issues/299)。原生Scheduled由Human稍后在电脑设置，不阻塞其他工作。

## 已交付

- #298 Inbox局部成功读取、失败分离与README表格修复已经合并。完整PR/main CI分别2272 passed673.05s /602.89s；main为537d346f685ccb575762561b53fd599db85ba78d。自动读取发布34371780696成功，读取R1321529876bb4d9ca78bcccd5132f35e6dd6ce1c已实际读回。
- #300 已将原公告scan接到一次一个、按披露日期/代码/原assessment hash排序的工作选择；复用原ZIP/packet/hash/Input/Funnel验证器，无新网络/模型执行器。merge fe3ca58d4bff7d2ee470c0744deecf1464ce16b8，reviewed head e7a5ae3cde793c3e5c80faabd49c63de2c7d2d0f，tree4f177722a2b50b3f8571592f0e0564b2482987d9。完整PR CI34374131808/test102542498475：2303 passed576.76s；main CI34375497803/test102547138668：2303 passed644.48s。两份checkout/install/pytest/cleanup日志已读；main checkout精确为merge，不相加。
- 固定数据ref `research-work/disclosures-v0` 已保存第一次选择及处理记录，不是生产Research registry或市场恢复源。每个原packet hash只保留一次处理；没有结果、预检失败、WAIT或其他结果都不能自动重新启动同一请求。

## 首次真实增量尝试：未进入Research，不是假WAIT

原自然scan34354228621/artifact10105040865，ZIP SHA2568831e7dc5dff5e5aab49c59e23ac36aa1f9de80837b0c9e118d722196ee3e507，包含五个原packet。程序选择最早的兆易603986、9月5日公告1225549295；其他四份保持容量暂缓。不是Human临时挑易通过案例，也不是五家公司都研究完成。

该packet原hash为0b74408c05170420834289e641a8ca0a61fe5524ed74184dd71823beb1c5f6e9。扫描器虽标记EXTRACTED，实际页文是乱码，不能按数字字形猜财务事实。

预检计划先保存在514d89bbceed0d87682c4a1e0013837b93f1eefb。第一次Web打开官方PDF返回非可重试的URL安全/路由拒绝，没有正文。遵守原限制，未重复URL、未换路径绕过、未直接HTTP重试，后续库存检查未执行。状态为 **SOURCE_PREFLIGHT_INCOMPLETE / NOT_EXECUTED / Funnel NOT_REACHED**。没有冻结合法研究input或execution_id，没有原validator产出的EXECUTION_GAP，也没有Pre/Quick/WAIT/DROP/DEEPEN。来源公开可用性、工具内部网络活动和全部其他途径是否可用仍未知，不能将工具拒绝说成发行人未披露。

精确失败记录：`195dcfe710c62c3796fef4d19e68cadd05a8d84d` 下 `research_runs/candidates/incremental-disclosures/0b74408c05170420834289e641a8ca0a61fe5524ed74184dd71823beb1c5f6e9/failure.json`，blob56d4f68dbf92fec23ade24ca6158aed7febf3acc。

预检前发生过一次人工Unicode转存错误：首个create-only提交4d10d678…的blob e1da5d1…不等于原packet78c7f663…，读回未通过。后来用原ZIP字节的base64 blob恢复，错误副本及提交原样保留于83ed8d364bcd7390bfb36af49753428802a14524。此为明确的研究准入前源副本纠正，不是普通create-only成功路径，不能追认首次转存PASS；不是修改已冻结研究input、改变原材料或重新执行研究。详见同目录transfer-correction.md。

在完整固定工作树195dcfe…中确认只有一份保留packet，按原程序重新做只读选择检查，原请求为ALREADY_RESERVED；不会因预检失败复活。核验记录已存c355eea159a1113704b06d19942fe277f56591e2的同目录no-repeat-check.json。程序计算的下个可选packet未保留、未执行；本次没有转挑第二家公司刷成功。

## 给Brief的消费规则

本次只在已有 `current_state/registry.json.references` 添加检查点导航和该次精确失败引用。复用现有Collector的source/ref/blob验证与原件留存，**不是 additional_registered_handoffs，不增加 pending，不新增研究资格或唤醒通道**。读取发布仍由既有生产/CI事件驱动；数据ref一次变化不承诺立即刷新。

消费时沿一次固定的current-state commit R，读取research.records的purpose_note及其同R的source.read_path。报告“有一个来源预检失败、尚未研究的问题”，不能报告“兆易研究完成后建议等待”。正文原始身份及错误副本留在工作ref历史；只读入口留存失败原件和导航，不额外建工作队列数据库、自动订阅器、错误分类服务或模型调用器。

## 尚未完成，不混算

P0-4A的三花#296原Schema/Funnel/CI结果仍保留，审阅评论5604273230限定液冷供货只归于IR，并保留全工具预算记账范围缺口；不签无保留整体PASS，不重跑三花。

P0-4B：工程选择/保留/失败处置/不重复检查已经有真实记录；完整的实际Pre/必要Quick链路仍未通过。下一次获准执行使用合法可用工具，预先冻结范围与预算；不得偷偷重试此失败请求或补造原始过程。

P0-5A：交互Brief已有，原生定时创建与自然交付未验。5B此次只接入真实执行缺口，不能冒充新增研究已交付。6A可使用已明确的Issue/comment与exposure/response协议，但尚无针对这份Brief的实际Human回应；技术“继续施工”不凑公司回应样本。6B的实际授权续作和P0-7的5–10交易日完整使用仍待真实发生。

旧P0-1/P0-2索引与Human提供的已验收记录不一致，是精确回执同步债；不由这次失败或旧pending推翻既有验收，不重新要求同日重跑。投资权限始终NONE。
