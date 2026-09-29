# B2：六个既有对象的三季报预约原始取得

归属 [#620](https://github.com/auguspp/decision-kernel/issues/620)，承接该事项的复用审阅5891715349与接手回执5892128445。当前范围/实际结果仍从原事项恢复；本文不是第二进度表。

## 可用接点与边界

`.github/workflows/b2-disclosure-appointments.yml` 是有限、手动、source-only入口，不是新日历底座或通用接口执行器。只允许owner在精确已审main及其最新独立main CI成功后，调用原 `tushare_relay.py` 的 `disclosure_date`。原客户端blob必须保持 `d2ee02a81648eafe7204a47e7f8e41b56c3c48fd`；不改HTTP、域名、凭证、TLS、超时或原单次30秒排队重试。

对象由[已保存R2清单](readings/2026-09-29-research-agenda-r2.md)的明确范围固定：天智航688277.SH为FOLLOWED；恒瑞600276.SH、兴业002674.SZ、北大荒600598.SH、三花002050.SZ、兆易603986.SH为原ODDS_WATCH。保存其精确来源commit/blob，均不推持仓或新增关注。

报告期固定 `end_date=20260930`，逐证券显式请求 `ts_code,ann_date,end_date,pre_date,actual_date,modify_date`，请求limit=100，不分页、不扩证券或报告期；六个逻辑调用最多12次HTTP，原每响应4MiB上限继续。`modify_date`是原修正记录，不解释成唯一修改时间。预计/实际/公告日期不互相补齐，空值保留。原表多行不自动去重或keep-last，不从到期推实际披露。

入口只有code-sha输入，密钥仅使用既有Actions secret。不提取或转移明文Key，不新增费用、日程或Sites权限；沿原Relay并发组，不声称与所有其他Relay消费者形成全局锁。实际调用前检查原任务是否在途，不取消它们。没有从publisher自动触发本入口。

## 取得与资格分开

脚本只检查响应业务状态、表头唯一性、证券/报告期与缺字段/可能截断，**不认证日期或官方预约**。全部原始响应字节、原请求、HTTP/业务状态、可见安全响应头、原客户端请求/取得时钟及逐件bytes/SHA256保留；来源的provider/source声明仍在原JSON，不能因使用另一个库就当第二独立证据。

输出目录create-only，逐文件读回。原客户端没有返回receipt的异常只记录异常类别与缺口，外层调用时钟不冒充HTTP取得时间；部分I/O失败不补成完整capture。服务拒绝、限流、其他客户端失败或字段/覆盖异常停止本批剩余调用，后五项可为未查询，而不是零条预约。成功空表可以完成捕获，但不证明不存在预约。

`plan.json`为固定请求/实际运行身份；每证券目录保留`attempt-N.body`和`receipt.json`；`capture.json`与`summary.md`只汇总实际取得状态，不是公司日历、Research或Human待办。Actions保管30天，不等于永久归档；正常退出代码也不证明真实日期已经验证。

完整交付仍须下载原artifact、核外部运行/摘要与每件原字节，审六对象的计划/实际/修正值和日期资格；真实记录才进入另存的research-agenda后继，沿唯一用途和原publisher/固定R读取。重要条目使用已审AKShare巨潮预约/公告定位与官方原件作独立核对，而非拒绝后偷偷换源冒充同一次成功。原R2、BLS、Human/Watch和历史不改。该source-only任务本身不发布、不更新registry、不执行Research/Odds/通知或投资。

## 复用决定与退出

**REUSE + THIN_ADAPTER**。内部已审原Relay、全球市场source-only工作流与capture、Smart Money的响应保留/字段反例、既有calendar/agenda和Collector。原全球市场只支持indices/shibor，Smart Money有自己的固定请求，不能以重跑它们取得任意预约。复用其GitHub原生执行/上传和原Relay，而非重建HTTP客户端或扩大它们的业务范围。

官方核对 [Tushare财报披露计划](https://tushare.pro/document/2?doc_id=162)：字段含modify_date且默认不返回，单次最大6000不外推为Relay实际权限/覆盖。外部复用沿 #620/5891715349 已保存的AKShare两函数、CNEquity0.11.0模块和catalyst-calendar具体审阅；没有证据需要重新引入这些框架或为本次捕获安装新库。

这里只新增这个有限caller、手动入口和其低层合成测试，沿现役CI合同正常验证，不修改CI策略。取得所需原件后可用普通PR移除本专属caller/工作流/测试与本文；保留原始数据及读取档案，原Relay和B1/Smart Money不受影响。重复/不确定dispatch先对账，不重放旧探针，不以重新运行换绿。
