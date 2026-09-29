# B2：六个既有对象的三季报预约原始取得

归属[#620](https://github.com/auguspp/decision-kernel/issues/620)，承接5891715349复用审阅、5892128445接手、5893063479实际停点及5893265058继续施工。实际结果与执行许可从原事项恢复；本文不是第二进度表。#654/#655的实现和当时范围保留在Git历史。

## 当前有界接续：只查尚未查询的四家

首轮run36585190686/1取得天智航的部分记录；第二次run36587228220/1尝试恒瑞后容量/超时失败。两次FAILURE及原始字节均保留：[首轮](readings/2026-09-29-b2-relay-36585190686/README.md)、[第二次](readings/2026-09-29-b2-relay-36587228220/README.md)。不重新查询这两家，也不重放已消耗的五家范围。

脚本在源调用前核第二次精确capture.json字节和五项实际处置，当前仅请求002674.SZ/600598.SH/002050.SZ/603986.SH。报告期仍为20260930，仍显式请求六字段含modify_date，limit100且不分页，最多四次原client逻辑调用/八次HTTP。没有新证券、报告期或任意API入口。

仅modify_date单独缺失时，保留逐项FIELD_GAP并继续其他对象，最终CAPTURED_WITH_FIELD_GAPS仍返回非零；不冒称完整取得或官方日期认证。证券/报告期/预计/实际等其他列缺失、身份/覆盖/业务异常以及拒绝/限流照旧停止。缺修正历史限制的是改期完整性和正式资格，不把其他对象仍未查询偷换成零数据。这是一次明确前驱的剩余范围接续，不是通用恢复器、按latest挑成功或rerun-to-green。

## 共同运行边界

`.github/workflows/b2-disclosure-appointments.yml`仅手动、owner/main/attempt1；唯一输入code-sha。调用前核精确current main、最新独立main CI成功及原客户端blob `d2ee02a81648eafe7204a47e7f8e41b56c3c48fd`。原`tushare_relay.py`、域名/HTTP/凭证/TLS/超时和单次30秒临时排队重试不改。

原六对象范围仍绑定R2的精确commit/blob：天智航FOLLOWED，后五家ODDS_WATCH，均不推持仓。新接续不更新Watch、公司关注、Research、Odds、Human待办或通知。Key仅为既有Actions secret，不转移本地或浏览器；GitHub contents/actions只读。原Relay并发组不取消在途任务，也不冒称协调所有Relay消费者。15分钟上限，无新日程、订阅或依赖；没有从publisher自动触发此入口。

## 原始取得不等于日期认证

全部原始响应字节、原请求、HTTP/业务状态、安全响应头和原client时钟保留，输出目录create-only、逐文件读回、记录bytes/SHA256。provider/source声明在原JSON中，不补造内部上游。无原receipt异常只留类别，外层调用时钟不冒充HTTP取得时间；部分I/O失败不报告完整捕获，凭证反射拒绝保管。

原表按列名读取且拒重复；多个行不keep-last，预计/实际/公告字段不互补，缺列不当null，修改字符串不当唯一修改时间。日期资格仍NOT_PERFORMED，不从日期到来推实际披露。空返回不证明没有预约，未查询不等于无记录。安全失败不自动换源。

`plan.json`绑定范围/前驱和实际运行身份；证券目录保存`attempt-N.body`与`receipt.json`；`capture.json`/`summary.md`仅汇总取得状态。Actions上传30天不等于永久归档。实际完整交付须下载核原artifact与每件字节、审证券/报告期/日期/来源、另存agenda并切原唯一用途，再走正常publisher和固定R读取；重要条目沿巨潮/交易所核原件，不能由Relay替代。原R2/BLS/Human/历史保留。

## 复用与退出

REUSE+THIN_ADAPTER。内部原Relay、全球市场source-only运行/上传和原保存/读取直接复用；全球市场只支持indices/shibor，Smart Money不是任意接口执行器，不重跑无关采集。官方Tushare162确认modify_date默认不返回，但不外推Relay权限/内部来源；真实首轮证明请求该字段仍未返回，原因UNKNOWN。外部沿5891715349已审AKShare预约/公告定位、CNEquity0.11.0及catalyst-calendar，不安装新库或框架。

不建设公司日历schema、数据库、provider、爬虫或恢复平台。适用普通CI不削弱；沿用原低层缺字段继续/精确未查询范围反例，不增加永久测试数量。原件取得后可普通PR移除专属caller/workflow/tests/本文，历史数据/失败/原Relay和公共reader保留。新执行前查原任务/实际调用状态，不重跑已消耗的批次；发生新权限、费用或范围变更停止对应动作。
