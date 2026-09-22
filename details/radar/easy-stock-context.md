# 行业市场表达与期指持仓上下文

状态：READ&#95;OK&#95;WITH&#95;SOURCE&#95;GAPS

资金流不是公司 Evidence；期指会员排名不是市场方向或买卖指令。
腾讯/东方财富分类独立；f24不作为20日，缺失字段不填零；抓取时间不是交易/发布时间。
榜单第一页不是全市场；中信(代客)缺失侧为UNKNOWN，四品种手数不合为风险敞口。

原工作流结论：success；本节单独核对public-context任务。

本批目标日期：2026-09-22（检查目标，不是已认证的最新完成交易日）。

## tencent-industry

状态：MARKET&#95;CONTEXT

原响应行数：124；这里展示前10行，全部原字段和缺口见JSON。

| 原代码/名称 | 1日 | 5日 | 20日 | 主力净流入原值 |
|---|---|---|---|---|---|
| pt01801765/广告营销 | 3.58 | 6.99 | 4.69 | UNKNOWN |
| pt01801183/房地产服务 | 3.40 | 17.19 | 17.81 | UNKNOWN |
| pt01801769/出版 | 3.39 | 7.49 | 9.58 | UNKNOWN |
| pt01801096/商用车 | 2.83 | 1.04 | -4.62 | UNKNOWN |
| pt01801145/文娱用品 | 1.74 | 8.28 | 3.72 | UNKNOWN |
| pt01801767/数字媒体 | 1.71 | 8.06 | 14.65 | UNKNOWN |
| pt01801111/白色家电 | 1.55 | -3.97 | -5.48 | UNKNOWN |
| pt01801995/电视广播Ⅱ | 1.54 | 5.23 | 4.59 | UNKNOWN |
| pt01801104/软件开发 | 1.54 | 5.09 | 2.74 | UNKNOWN |
| pt01801223/通信服务 | 1.41 | 2.60 | -0.25 | UNKNOWN |

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

状态：RETAINED&#95;BODY&#95;CONTRACT&#95;REJECTED

来源未取得或合同未通过；原尝试保留，不用旧成功替代。

## cffex-IH

状态：RETAINED&#95;BODY&#95;CONTRACT&#95;REJECTED

来源未取得或合同未通过；原尝试保留，不用旧成功替代。

## cffex-IC

状态：RETAINED&#95;BODY&#95;CONTRACT&#95;REJECTED

来源未取得或合同未通过；原尝试保留，不用旧成功替代。

## cffex-IM

状态：RETAINED&#95;BODY&#95;CONTRACT&#95;REJECTED

来源未取得或合同未通过；原尝试保留，不用旧成功替代。

[全部原字段、可用性、原件和任务身份](easy-stock-context.json)

未执行经济问题审阅、Pre/Quick、Odds重算或Human提醒。
