# 下一阶段施工方案 v3｜按需刷新、待 Quick 收件箱与网页版研究

2026-09-27 · Requirements Management / Main Construction。

采用依据：[Human明确确认与RM回执](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5851292639)。Human同意「Site不直接调用当前WebGPT；一键转存待Quick，集中后在网页版操作」，并要求继续推进。本文是原方案的后继，不是全部重设计或功能已上线声明。

## 保留基线，不重做已交付

[完整v2](https://github.com/auguspp/decision-kernel/blob/372cbee049215057f8476069de91924d2de786b2/docs/NEXT-PHASE-CONSTRUCTION.md)与其链接的v1保留在精确Git。除本页明确改动外，v2的0→A→B→C→D、横向L、P01–P10、H1–H5、全站人类问题、信息层次、Reuse First、CI和退出责任继续适用。后继恢复须阅读有关基线，不把下面的施工摘要当完整方法。

已交付#596事项/原版本/更正/历史回应接续，#598核心账本与原文阅读，#599新闻/市场阅读，#600原生更新/查询与复制接续全部保留，不反复装修、不重跑采集证明同一结论。源码/完整CI/main/正常读取发布不等于Sites采用、手机可读或Human接受。精确当前M/R、分支/PR和真正进展始终查#297。

## 前提变化及处置

原近期目标把「Site→合格Hosted Quick执行入口」放在主路径。新的Human选择是：**刷新直接执行；研究先转存，再由网页版ChatGPT/另行授权任务消费**。直接调用当前聊天并非接一个GitHub dispatch；不为这个目标继续造bridge、Agent/token、邮件/PR或轮询触发器。Published Agent/API研究执行仅为以后有真实净收益时的独立增强，不能再阻塞近期收口。

用户转交原Site只读核验：现部署v7是静态；平台支持Worker/hosted环境/身份header，当前没有服务端动作和GitHub写凭证。管理角色不是运行时身份；生产header可用性/防伪造和HTTPS出站未验。这修订旧“现场完全未知”，但不升级成已授权/已配置/已部署。现仍暂不交Sites、不发零散包。

## 当前优先级

| 顺序 | 交付目标 | 实际边界 |
|---|---|---|
| 当前主批次 A2-Quick Inbox | 新闻/行业/公司/Research/Odds材料加入待Quick；一个GitHub收件箱、原定位保存/读回、批量接续与结果关联。 | 不启动研究、不修改旧DEEPEN_REQUIRED、不建新数据库或后台队列。先做同域路由与安全测试；Site身份/凭证和真实点击单独验。 |
| A2-Refresh | 原Site owner点击→仅现役新闻刷新白名单→实际run→原publisher→同次资料读回；之后按批准范围复用其他刷新。 | 不重跑历史probe/backfill，不将前端读取改名为采集。凭证/owner/Origin、在途和提交不明须处理；刷新不隐式Quick。 |
| 集中Sites采用 | 根据真实v7及宿主适配，合入所有未采用的阅读/收件箱/受控动作增量。 | 保留root/旧链接、owner-only、CSP（同域fetch只增self）、当前回退。非API走原fallback，API不能返回HTML。无需等所有全球来源/日历/长期需求完成。 |
| A2连续性 + B1/B2 | 真实原话/原版本/再次恢复可穿插；明确关注/持有；全球来源族和有限研究日历逐步交付。 | 不制造Human回复/持仓/财报日期，不把局部入口受阻扩大成全局停工。 |
| C→D，L贯穿 | 原跨期证据/预测比较、盲点驱动发现、多期限机会、成熟校准和后继真实采用。 | 保留原范围与反例，不另造学习/Agent/调度框架，不以清空backlog为目标。 |

一次一个主工程功能批次。故障仅按真实依赖阻塞；严重误导、身份/权限或真实交付失败可抢占，普通想法回原台账。自然R5.1/R5-5日常链及既有资源/任务继续；不新增定时任务、不改变Brief时钟、不追加原P1验收前置。

## 待 Quick 的责任与共享记录

正式入口[#601](https://github.com/auguspp/decision-kernel/issues/601)，合同和用法见[quick-inbox](quick-inbox.md)。它只保存Human选中的公开材料定位和后继结果关系；未知选中原因不编造。原正文留在原路径，客户端临时视图不成为第二事实库。

GitHub原生Issue/comments提供保存、时间和原评论身份；薄投影区分未有结果、已关联且字节可读的结果、移出。复制/浏览不清空，不伪造“运行中”。相同原上下文可合并待处理展示，但所有原请求ID保留；旧回应/旧结果不关闭后来新选版本。提交不确定先查原记录，不机械重试，不宣称原生comments是exactly-once。

消费从当前RESEARCH-ENTRY恢复，优先使用原材料/旧研究/更正并可自主查公开资料。可合并相关事项调查，但原请求逐项有实际去向；先保存Quick正文并读回，后追加原请求的结果定位。没有材料或没做完保留原因/UNKNOWN，不编报告或完成事件。Quick只建议Full，Human拥有委托、接受和资本决定。

## 权限与验收

先前Actions:write仅能支持刷新；收件箱写评论另需单仓库Issues:write。当前只实现代码与受控离线测试，不因方案批准就创建令牌、改环境或外发私人数据。代码不要求Contents写。实际owner ID/token只在原Sites hosted配置，无需发到聊天。缺配置/身份直接拒绝，浏览器不持凭证、不能指定其他repo/Issue/workflow/ref。

现阶段first-party Site能力依据用户转交核验＋官方资料；必须在实际handler验证可信身份、防伪造、非owner拒绝和生产出站后才激活写入口。任何新费用/账号/权限或隐私范围仍另行成立。全站保持Human-first：有用内容与时点/限制优先，精确机器信息下钻。

工程仍依[CI-MAINLINE](CI-MAINLINE.md)：真实PR/head、正式full原件、正常merge、独立main复用/实跑smoke、正常publisher与固定读取分别验。不得弱化完整性、回头补造旧测试或把DOM测试当浏览器截图。一个空收件箱不是一次真实Human选择或Quick消费验收。

普通源码更新可继续；Sites最后集中采用，不逐PR/逐按钮交接。退出模块时一并处置专属UI/handler/tests/config权限，保留历史原件、必要reader、研究/回应与共享保护。没有自动投资系统或第二研究引擎。

当前执行与历史：#297；产品范围：#351；旧Odds合同：#349；旧研究/pilot/失败：#524原记录保持，不因新收件箱复活。v2及#596/#598/#599/#600的原文件、失败、授权和交付回执均保留于Git/原评论。更新当前导航，不重写历史。
