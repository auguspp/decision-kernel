# Quick → Brief：防重复执行和跨日漏读的有界接续

2026-10-02。Human要求同步修复Quick进入不了Brief，范围见[#297/5953022959](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5953022959)。接续#351/5952334647的真实遗漏及5952419966的HANDOFF-LOOKUP-20261002-v1配置。只有现役任务实际更新回执才代表采用本后继；本文件不是新的任务、存储服务或执行授权。

## 旧问题与本批改变

原#575保存失败不表示Quick没有做完，语义搜索没命中不证明获准目录没有文件。rev1已采用目录精确定位和最多一次最终核对；仍须避免只在Quick结束时查重，和Brief只找当天文件而丢掉前晚未取得/晚到的Quick。

KEEP：#575为canonical；固定两个Library目录为非canonical交接，真实file_id读取、全文/元数据、create-only/冲突不覆盖、已有安全拒绝不重试、读取失败不变无成果。日程18:50工作日Quick/19:15每日Brief、通知、来源/研究职责与投资权限不变。CHANGE仅是开始时查重和跨日采用核对，不建立通用Memory或逐事件数据库。

## Quick开始及保存

开始研究前先核#575当日精确标题，同时通过`/Decision Kernel/Hosted Quick Handoff/`单层目录，以实际执行日精确名称取得真实file_id并完整读取已有handoff。不能用路径代替file_id，不能把语义检索无命中当不存在。目录未解析、列表不完整、正文截断或身份冲突时，只报告查重缺口，不发起可能重复的研究/写入；其他独立获准事项不因此停止。

若已存在同日自洽完整Quick handoff，即使#575缺失，也只读恢复并报告HANDOFF_ALREADY_PRESENT，不重新研究，不尝试补写其被拒或状态未知的canonical mutation。存在canonical时仍以canonical为主并对照差异；同日冲突保留两种真实身份，不能合并、覆盖或另取文件名。

没有既有成果且查重完整，才按原Quick职责执行。写前检查和成功后读回使用同目录真实身份；保留文件自述时间、Library创建/修改时间和实际读回时间的区别。只在成功响应并实际读回一致后对外声称保存完成，不能在预写正文中自签未来读回。原pre-mutation schema例外、明确拒绝停止及不确定写只读对账规则不变。

## Brief跨日接续

当天查找及rev1最多一次最终核对继续。同时在原获准`/Decision Kernel/Brief Handoff/`恢复最近实际Brief的完整正文、cutoff和实际Quick定位；这个读取只为对照晚报采用，不能把Quick正文或任务时间冒充Brief基线。

同获准Quick目录查看最近7个日历日内最多3份实际Quick正文，先当天，再最近既往文件；仅纳入上一Brief明确未取得的对象、在其cutoff之后形成/修订的材料，或核对两份正文后有证据的有用遗漏。文件名只是定位索引，原执行日/cutoff/M/R/保存状态保持。跨周末没有当天Quick不等于可以跳过周五未取得的成果。此前是否采用不明时保持UNKNOWN，不猜“从未读过”。超过有界范围的已知未完成项保持具体定位，不以滚动窗口删除；不无限遍历或另建待办库。

每份选取的Quick要在当前Brief已有消费摘要/交接元数据中简短记录：精确定位、原cutoff/保存状态，以及本次采用的有用增量或明确省略理由。未采用可因已在实际前次Brief讲过且未变、与本次无关或证据不足；不能仅因没有新增Full而删掉有效研究。没有正文证据不能自签全部采用。

恢复出的旧增量标为原日期的后到补充/遗漏补充，不当今日新事件；不覆盖旧Brief，不重新跑旧任务，不把#575被拒正文换目的地补存。当前Brief仍只综合已有研究和保存观察，不另开研究/归因/Full/Odds。

## 新独立读取面

同R若有`research.independent_stock_observations`描述符，Quick/Brief沿其实际read_path核SHA256/bytes/git_blob取得正文。#730之后若`preferred_current_input=daily_market_inputs`，先核该对象的status、latest_attempt、market_session，再沿其file描述符在同R取得`details/stock/daily-market-inputs.json`。按columns解释完整rows，核cohort_denominator、qualified_windows、status_codes及source_row_coverage；不能只读摘要上下端样本，也不能继续把旧16名表当作本次全市场输入。

分析按用途使用：查询证券的实际末日close；用各期限COMPARABLE值进行5/20/60区间与横向比较；保留短历史、错日、重复、截断和缺因子所影响的具体范围。缺60日不阻断合格5/20日；末日daily失败导致分母未建立时明确说明不可计算，不解释为零变化，不补0或假设因子1。不要求跨供应商逐字段一致或全部中间日完整才使用合格端点。来源口径、市场日与实际取得时钟保持，区间表现不升级成因果领先、完整走势、总回报或投资结论。

现有`observations/price_comparison`继续按historical_sample_status和原日期读作历史观察；只有不存在当前支路时，才按旧入口核status/summary/gaps、observations.coverage、selected_observations并按价值读inventory，仍不冒充今天。当前输入失败不能通过旧样本替代掩盖。具体字段和来源职责见[独立读取说明](independent-stock-daily-reading.md)。

价格结果为已有分析增加可核输入，业务解释仍用现有合格公司/产业材料；不用Sector入选、已有研究或某个其他来源部署作候选前提，也不因价格局部缺口整体否定有效公司证据。这里只消费保存结果，不授权Quick/Brief发起K3、补采、重复研究或扩大原Brief职责；自然任务实际采用仍须由其正文举证。

## 验收和退出

配置更新、交互端真实文件恢复与内容对照、下一次独立自然Brief使用及五日C2可用性分别验收。Oct2旧遗漏保留，不把本会话恢复写成当时已消费；根因若未恢复仍UNKNOWN，不凭当前可见文件推断当时可见性或搜索参数。

本规则只有Quick/Brief两个现役任务的上述交接消费者，无新增常驻组件。后续原平台提供可靠同语义交接时，有界核验身份、重复、晚到、冲突及拒绝传播后再替换；保留旧正文、失败与Human记录。晨报继续其原Brief只读范围，不自动获准一般Quick目录。
