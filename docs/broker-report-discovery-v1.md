# 券商研报发现：行业、策略、宏观、晨报

Owner / scope: #297 的 Human-approved broker-report discovery increment
[5946621550](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5946621550)。
这是手动、来源资料层的轻适配；不是第二个研究平台。

## 用途与普通入口

从根 AGENTS 的 Broker report discovery 行进入本页；研究解释仍先读
[RESEARCH-ENTRY](RESEARCH-ENTRY.md)。把明确的报告类型、日期窗口和可选的
东方财富原生行业代码交给 `decision_kernel.runtime.broker_report_discovery`。
先得到候选目录，再在已保存目录中按标题、券商、行业做关键词子串过滤。
`PCB` 与 `AI服务器` 可以分别过滤同一份目录，不为换关键词重新访问来源。
这是已取有限页的目录搜索，不是PDF全文搜索、全网语义检索或市场穷尽。

个股研报继续用 [institutional-context](institutional-context.md) 与
[Smart Money](smart-money-radar.md)；不改 `report/list qType=0` 的旧合同。
取得目录不等于取得PDF：已有 AP report ID 的正文定位沿
`smart_money_documents.pdf_spec` 和现有正文取得/保管路径处理。
只有 `encodeUrl` 时保留详情页定位与 `UNFETCHED_LOCATOR`，不把加密定位当AP编号、
不编造PDF、不自动打开详情页或下载正文。原PDF/页码、阅读、保存、登记和研究准入
继续分别成立；这次不扩正文下载范围。

## 手动使用

使用仓库已有 `feeds` extra；无新增依赖、凭据或安装 report-cli 整套软件。
下面日期仅为命令示例，不表示已查过该窗口。真正操作必须服从该次任务的
来源范围和既有失败/停止记录；没有获得批准的重试不因新目录名而获准。

```sh
python -m pip install -e '.[feeds]'

# 只打印有限请求计划：无来源请求、无文件写入
python -m decision_kernel.runtime.broker_report_discovery plan \
  --kind industry --begin 2026-09-01 --end 2026-09-30 --pages 2

# 在实际授权的新来源任务中执行；输出目录必须不存在
python -m decision_kernel.runtime.broker_report_discovery capture \
  --kind industry --begin 2026-09-01 --end 2026-09-30 --pages 2 \
  --output run-output/reports-202609

# HASH 使用捕获结果、精确Git档案或获准任务回执中记录的 capture_hash
python -m decision_kernel.runtime.broker_report_discovery replay \
  --output run-output/reports-202609 --expected-hash "$HASH"
python -m decision_kernel.runtime.broker_report_discovery search \
  --output run-output/reports-202609 --expected-hash "$HASH" --keyword PCB
```

`--kind` 另可取 `strategy`、`macro`、`morning`。一次只查一种类型，默认一页，
最多四页、每页50条；日期端点差最多92天。`--industry-code` 仅接受行业类型下
调用者已核对的原生数字代码，不新建/猜测行业映射或更新全市场行业缓存。

`capture` 的成功退出只表示已保存结果与失败，不保证来源取得成功。
检查 `coverage`、`failure_detail`、`provider_total` 和实际 `records`；失败的空数组
不代表没有研报。`search` 同时保留原目录覆盖统计和单独的 `matched_versions`。
类别冲突的原行仍在目录与原件中，但不进入关键词结果；缺栏目时明确只是请求类型，
不是独立核实的类别。评级原字段保留，不组成推荐、共识或预测修订。

## 身份、分页、失败与保管

- 行业沿上游 `report/list qType=1`；策略/宏观/晨报沿 `report/jg qType=2/3/4`。
  请求主机和参数固定；没有任意URL入口、重定向、代理凭据、备用主机或自动重试。
  复用现有隔离 Requests session，显式 connect/read timeout 和512KiB响应上限。
- 来源 `hits / TotalPage / pageNo` 必须自洽，页长与页码、分母变化都被检查。
  不把上游含混的 `total` 猜成总页数。未见过的响应形状保留原页为
  `RETAINED_PAGE_UNQUALIFIED`，不能由营销说明或合成测试补签真实来源资格。
- 记录发布时间原字符串/日期、UNKNOWN时区、真实请求/取得时间、原页SHA256和行号。
  不把取得年份解释成预测目标年；原报告可得时间没有建立就继续保留缺口。
  `infoCode` 与 `encodeUrl` 不混为同一种身份。JSON数值与字符串版本区分，
  完全重复保留全部原行定位；同ID修订保留多个版本，不自动挑新值计算。
- HTTP失败、认证/限流/重定向、业务错误、未合格页均停止本次分页。
  已成功取得的早页保留；没有为晚页失败覆盖旧结果。写盘失败是保管失败，
  不吞成网络错误重试。每页完成后在本次新目录内原子保存检查点；进程中断时
  `final=false` 与原页仍可核读，不宣称捕获完整，也不自动续抓。
  突然终止时检查点之后是否曾发起请求可能UNKNOWN，不能据此重放来源。

目录含 `capture.json`、`page-N.body`、`catalog.json` 和 `summary.md`。
重放重新验证请求、时钟、原字节、外部提供的capture hash、分类/去重和派生正文；
重放/关键词查询没有网络请求。完整校验是自洽与身份核对，不认证供应商经济真理。
本地目录、代码合并或Actions附件都不是自动永久Git保管/登记/发布。
需要研究消费时，沿既有 [Research archive](research-archive-v0.md) 的实际来源资格、
许可和文件预算登记原件；超限保留缺口，不拆分绕限、不发布未获准正文。

## Reuse decision、验证与退出

**Reuse Decision: THIN_ADAPTER.** 内部恢复 institutional_context、smart_money_sources、
smart_money_documents、既有隔离session、canonical identity及原archive入口。
#511 已保留本次候选评估；#508/#511的其他框架/交易/PIT候选不解决这四类东方财富目录，
不在本次安装或重审那些框架。实际审阅的外部实现：
[manymore13/report-cli@0d98dde87a6b295359ae68152ca2693428baef83](https://github.com/manymore13/report-cli/tree/0d98dde87a6b295359ae68152ca2693428baef83)，
`src/eastmoney/report_client.py`、README、pyproject及LICENSE。
采用其类型/请求/详情页映射；未采用宽窗口可变行业缓存、curl -L批量下载、
静默None错误和未经约束的文件名。直接CLI/整包会额外引入lxml和上述不适用副作用；
只取这些映射并用既有Kernel边界包装，无需再造provider框架。
官方交叉参考：[Requests advanced usage](https://requests.readthedocs.io/en/latest/user/advanced/)、
[AKShare股票文档](https://akshare.akfamily.xyz/data/stock/stock.html)的个股研报接口。
AKShare个股接口不是这四类/jg当日可用的实证，也不替代现有个股通道。

工程验收采用原pytest与正常PR/full/main合同，无新CI工作流、registry或定时器。
合成分页/类型/停止/中断/篡改/URL与Markdown转义反例只验证工程行为。
**四类真实响应、来源持续可用、原件永久保管、真实Hosted Quick消费尚需各自实际回执；
没有这些回执不标为已验。** 本文不部署Sites，不解除C1/C2受阻操作，不启动D，
不新增费用、来源Secret、Full/Odds/Watch或投资权限。

退出时一起移除这个手动调用入口、专属测试与AGENTS导航；保留已取得历史原件、
其精确读取代码与仍被使用的原archive reader。没有永久外部服务或后台进程要迁移。

## Upstream MIT notice

MIT License

Copyright (c) manymore13

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

This licence covers the reused code, not redistribution rights for broker reports.
