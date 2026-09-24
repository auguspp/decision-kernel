# 行业市场表达与期指持仓上下文

状态：READ&#95;OK&#95;WITH&#95;SOURCE&#95;GAPS

资金流不是公司 Evidence；期指会员排名不是市场方向或买卖指令。
腾讯/东方财富分类独立；f24不作为20日，缺失字段不填零；抓取时间不是交易/发布时间。
榜单第一页不是全市场；中信(代客)缺失侧为UNKNOWN，四品种手数不合为风险敞口。

原工作流结论：success；本节单独核对public-context任务。

本批目标日期：2026-09-24（检查目标，不是已认证的最新完成交易日）。

## tencent-industry

状态：MARKET&#95;CONTEXT

原响应行数：124；这里展示前10行，全部原字段和缺口见JSON。

| 原代码/名称 | 1日 | 5日 | 20日 | 主力净流入原值 |
|---|---|---|---|---|---|
| pt01801131/纺织制造 | 1.54 | 2.66 | -0.49 | UNKNOWN |
| pt01801952/焦炭Ⅱ | 1.48 | -1.00 | -3.20 | UNKNOWN |
| pt01801736/风电设备 | 1.25 | -0.57 | 0.54 | UNKNOWN |
| pt01801994/教育 | 0.84 | 4.14 | 11.06 | UNKNOWN |
| pt01801784/城商行Ⅱ | 0.81 | 0.22 | 2.53 | UNKNOWN |
| pt01801782/国有大型银行Ⅱ | 0.64 | -0.01 | 4.62 | UNKNOWN |
| pt01801951/煤炭开采 | 0.57 | 1.60 | -4.31 | UNKNOWN |
| pt01801769/出版 | 0.49 | 3.96 | 9.81 | UNKNOWN |
| pt01801981/个护用品 | 0.34 | 5.25 | 7.68 | UNKNOWN |
| pt01801962/油服工程 | 0.34 | 0.94 | -4.96 | UNKNOWN |

## eastmoney-industry

状态：SOURCE&#95;UNAVAILABLE

来源未取得或合同未通过；原尝试保留，不用旧成功替代。

## eastmoney-theme

状态：SOURCE&#95;UNAVAILABLE

来源未取得或合同未通过；原尝试保留，不用旧成功替代。

## eastmoney-stock

状态：SOURCE&#95;UNAVAILABLE

来源未取得或合同未通过；原尝试保留，不用旧成功替代。

## cffex-IF

状态：SOURCE&#95;UNAVAILABLE

来源未取得或合同未通过；原尝试保留，不用旧成功替代。

## cffex-IH

状态：SOURCE&#95;UNAVAILABLE

来源未取得或合同未通过；原尝试保留，不用旧成功替代。

## cffex-IC

状态：SOURCE&#95;UNAVAILABLE

来源未取得或合同未通过；原尝试保留，不用旧成功替代。

## cffex-IM

状态：SOURCE&#95;UNAVAILABLE

来源未取得或合同未通过；原尝试保留，不用旧成功替代。

[全部原字段、可用性、原件和任务身份](easy-stock-context.json)

未执行经济问题审阅、Pre/Quick、Odds重算或Human提醒。
