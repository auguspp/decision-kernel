# B2：六个既有对象的三季报预约原始取得

当前接点归[#620](https://github.com/auguspp/decision-kernel/issues/620)。本轮沿[5900793113](https://github.com/auguspp/decision-kernel/issues/620#issuecomment-5900793113)，复用既有手动入口进行一次有限巨潮核对，不继续扩写已消费的Relay剩余批次。

## 当前一次性核对

证券固定为兆易创新、天智航、恒瑞医药、兴业科技、北大荒、三花智控，原身份仍为天智航FOLLOWED、其余ODDS_WATCH，不推持仓。请求前核已发布R3的精确原字节；兆易先查只是补缺顺序，不增加研究优先级或权限。报告期20260930，每家stockCode、market、sectionTime明确，单页100，最多六次POST，零重试、零分页、零重定向、没有备用主机。任一传输、HTTP、原JSON表形或覆盖缺口停止其后请求。

复用AKShare `stock_report_disclosure` 的 `getPrbookInfo` 请求形状，固定上游[0191689d57c667b7c7a198fd0cf97316837ef311](https://github.com/akfamily/akshare/blob/0191689d57c667b7c7a198fd0cf97316837ef311/akshare/stock_feature/stock_yjyg_cninfo.py)，blob4a7bbe49a8902d1d4bd7c6bd4e271ebf8d2953a3。采用该公共端点的HTTPS和逐证券有限请求；不用其按位置重命名、日期强转或宽全市场表。原库MIT许可与完整内/官方/外部审阅见[5891715349](https://github.com/auguspp/decision-kernel/issues/620#issuecomment-5891715349)。不安装新库，不宣称代码许可授予额外数据权利。REUSE + THIN_ADAPTER。

同一 `.github/workflows/b2-disclosure-appointments.yml` 仍仅owner/main/attempt1手动执行，精确code-sha与独立main CI前置不变，原并发组不取消在途任务，15分钟上限。源步骤不再注入Relay或GitHub凭证。Requests每次新Session、trust_env=False，不读netrc、环境代理凭证或共享cookie；TLS验证不关闭。原JSON/clock helpers继续复用不变Relay模块，但不调用Relay网络。没有新workflow、schedule、数据库、provider或通用恢复平台。

## 原始来源与读取资格

原响应在解析前create-only保存，保留HTTP状态、安全响应头、完整或部分字节、字节数及SHA256；捕获异常只记类别，不留异常URL。received_at为请求/读流/异常处理结束时钟，不冒称服务器首发或网络层微秒延迟。拒绝非identity编码，不把透明解压后的结果冒充原字节；超限或读流失败只保存有界前缀并明确不完整。

`prbookinfos`只检查为少于100项的对象列表，不重命名或填值。HTTP200与表形合格不认证证券/报告期、首次/后继改期或实际披露；`official_appointment_qualified=false`、`date_qualification=NOT_PERFORMED`在捕获阶段保持。实际取得后必须人工核每行身份、期间、源字段和覆盖，才能在后继清单说明哪些日期来自官方。空表不证明没有预约。不同源取得与时间分开，不以本次成功覆盖旧Relay失败，不因源名不同增加独立证据数。

已有plan、逐证券response.body/receipt、capture和summary保管继续使用；30天artifact不是永久档案。实际交付沿原件下载核对→原生Git→原唯一research-agenda后继→正常publisher→固定R实际读取。原R3/BLS/研究问题/Human/Watch/历史时钟不改；日历不自动研究、提醒或交易。

## 原执行器退出与后继边界

#654–#657的三次Relay执行及全部原件、字段缺失/空值/空表/容量失败和R3均保留。原四对象执行计划已消费，原source caller专属执行段与测试随本次替换退出，历史从Git及原PR恢复；共享Relay、公共reader与历史原件不删。当前入口没有Relay分支，不得重放旧批次。

本有限巨潮计划也只执行一次；下一次是否需要获取须按#620真实结果明确，不靠rerun换绿。它不是后台采集服务。完成后可普通PR移除专属caller/workflow/tests/本文，保留原始档案与共享读取。发生新权限、费用、隐私或范围边界停对应动作；Source失败不阻塞其他已批准工作。Sites、Brief/Quick/Watch、#658市场日常更新及通知均不由本次改变。Investment Authority=NONE。
