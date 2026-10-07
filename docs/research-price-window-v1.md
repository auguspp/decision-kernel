# 有限手动研究日线窗口

归属 [D #509 的具体价格缺口](https://github.com/auguspp/decision-kernel/issues/509#issuecomment-6037742730)。本入口保存显式证券和历史日期的来源响应，不挑股票、不产生机会、不更新当前行情、Research、Human、Watch 或投资状态。它不是新的常驻采集任务；没有 cron、生产成功事件或代码 push 触发。

## 为什么不是重跑日常采集

原 `stock_market_inputs` 给最新完成交易日与5/20/60区间的两端价格/因子，不请求整个中间路径。其缺少9月17日事件价格不是原日常接口错误；把它改为回放过去会破坏原 latest/session 语义。这里使用同一个已批准第三方 Relay 的 `daily`、`adj_factor`、`trade_cal`，另存来源收据，不混入原 daily receipt 或 publisher。#713历史成员补采、#727/K3已消费试点及#745分钟权限拒绝不重放。

## 范围、失败和原件

显式输入1–5个不重复的SH/SZ证券，开始/结束为YYYYMMDD，含首尾最多31自然日，结束必须早于采集时的中国日期。先取所涉及的SSE/SZSE两个市场中的必要日历，再逐证券取日线与因子；最多12个逻辑请求。请求字段固定，不接受API名、主机、任意文件路径、脚本、分钟频率、模糊最新日期或自选策略参数。

复用 `tushare_relay.request` 的固定HTTPS地址、原 `TUSHARE_PROXY_API_KEY`、TLS/禁跳转/禁环境凭据继承、4MiB单体限制和原30秒临时队列重试。最多两次尝试/请求、总16MiB、14分钟请求预算；拒绝、限流、凭据异常或耗尽立即停止余下请求，不換凭据、包装或旧试点补跑。非权限来源/单对象资格失败保留具体范围，不升级为零机会或已检查无变化。

`receipt.json` 保存精确计划及SHA256、原工作流身份、请求/接收时钟、实际尝试、原始文件大小/hash。失败正文不会执行；凭据反射拒绝保存。输出目录必须不存在，原始响应以create-only文件写入；同一次运行的收据仅追加实际过程，不覆盖另一次运行。超时或未形成报告时保留已有收据，不能将其记成完成。Actions附件默认保管90日；到期前有研究留存用途时按原档案合同处理，不宣称下载附件已成为永久Git原件。

`report.json` 用现有严格JSON/日期/正数/表格检查，要求明确证券、区间、唯一日期、OHLC顺序及非截断字段。每个来源日历须覆盖完整自然日区间。逐证券保留缺日价、缺因子、开市日之外行；缺值不前填、不补零，也不从缺行推断停牌或新上市。单表资格失败不抹去其他对象的合格资料。保存原始字节与验证后的值分别保留；提供者复权因子不证明全部公司行动、总回报、历史无修订或可执行成交。

## 使用与读回

只在受审阅的精确main、独立main CI最新对应运行成功、attempt1时，显式调用 `.github/workflows/research-price-window.yml` 的三个输入 `codes/start/end`。工作流仅contents/actions读权限；GitHub token只在前置main/CI检查，来源secret只在capture一步，verify没有来源secret。正常源码PR/CI/发布不自动发起价格请求。

在获准执行环境的实际CLI为：

```sh
python -m decision_kernel.runtime.research_price_window \
  --codes 600276.SH,002674.SZ,600598.SH,002050.SZ,603986.SH \
  --start 20260916 --end 20260930 --output research-price-window
python -m decision_kernel.runtime.research_price_window \
  --verify --output research-price-window
```

离线Python调用 `verify(Path(...), expected_workflow=...)` 可核固定原件，不联网；CLI保留实际工作流身份校验，不用伪环境变量造一次运行。下载后还要用真实artifact metadata核ZIP大小/SHA256/CRC和安全路径，再比较收据的run/attempt/code与显式请求。`verify`重新构造report与summary并逐字节比较。读取与反证、研究采用、Human接受分别验收。

`COMPLETE_PROVIDER_DAILY_WINDOWS`只表示此次提供者开市日资料齐全且通过本合同，不是历史时点信息资格、经济因果或完整投资回报。迟取的9月数据有自己的10月取得时间；原9月知识截点、长期条件和当前前向冻结不可倒写。资料即使齐全也可以得出机会未成立；缺资料则限制对应判断。

## 复用、验证与退出

**Reuse Decision: THIN_ADAPTER。** 内部复用`stock_market_inputs`的JSON/表格/日期/数值与目录安全检查，以及`tushare_relay.request`现有网络/凭据/失败合同。未改这两个模块及任何旧采集/读取结果。

实际检视成熟 [Tushare DataApi.query](https://github.com/waditu/tushare/blob/master/tushare/pro/client.py)（所读blob `d8803117d8182edc209071b20b568fe544bbf055`）：其POST/token/官方默认主机不等于已获准Relay的GET/X-API-Key。官方 [daily](https://tushare.pro/document/2?doc_id=27)、[adj_factor](https://tushare.pro/document/2?doc_id=28)、[trade_cal](https://tushare.pro/document/2?doc_id=26) 已提供证券与日期参数，无需行情数据库、日历引擎或抓取平台；官方字段合同不认证第三方响应。没有安装/复制外部SDK或变更依赖/许可。新建的只有有限请求编排、原件收据和适用验证，不重建网络客户端或价格模型。

`tests/test_research_price_window.py`用显式合成输入覆盖正向留存/重建、越界/重复证券、日期/时区、日历/价格/因子缺口、OHLC错误、截断、篡改/软链/额外文件、拒绝后停止和工作流权限隔离。工程证明不当真实行情或D验收；本地部分导入环境也不替代远端完整CI。实际源码head、CI、合并、发布、首次源运行及真实结果另记原PR/#509，不由本文件预签。

若此手动能力退出，同PR处置该workflow、adapter、专属tests和本入口；已保存原件、对应版本验证代码的Git历史、共享Relay和原日常任务保留。没有另建进度库、评分、自动重试服务、常驻状态或通知。Sites暂停及Investment Authority=NONE。
