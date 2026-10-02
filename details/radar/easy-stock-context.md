# 行业市场表达与期指持仓上下文

状态：READ&#95;OK&#95;WITH&#95;SOURCE&#95;GAPS

资金流不是公司 Evidence；期指会员排名不是市场方向或买卖指令。
腾讯/东方财富分类独立；f24不作为20日，缺失字段不填零；抓取时间不是交易/发布时间。
榜单第一页不是全市场；中信(代客)缺失侧为UNKNOWN，四品种手数不合为风险敞口。

原工作流结论：success；本节单独核对public-context任务。

本批目标日期：2026-10-02（检查目标，不是已认证的最新完成交易日）。

## tencent-industry

状态：MARKET&#95;CONTEXT

原响应行数：124；这里展示前10行，全部原字段和缺口见JSON。

| 原代码/名称 | 1日 | 5日 | 20日 | 主力净流入原值 |
|---|---|---|---|---|---|
| pt01801152/生物制品 | 4.18 | 3.15 | 6.82 | UNKNOWN |
| pt01801156/医疗服务 | 3.86 | 0.07 | 8.71 | UNKNOWN |
| pt01801016/种植业 | 3.72 | -5.65 | -8.92 | UNKNOWN |
| pt01801151/化学制药 | 2.79 | -0.67 | 0.40 | UNKNOWN |
| pt01801096/商用车 | 2.57 | 8.50 | 2.17 | UNKNOWN |
| pt01801125/白酒Ⅱ | 2.19 | 0.11 | -3.73 | UNKNOWN |
| pt01801126/非白酒 | 2.18 | 1.76 | 7.02 | UNKNOWN |
| pt01801012/农产品加工 | 1.90 | -4.50 | -5.90 | UNKNOWN |
| pt01801113/小家电 | 1.84 | 0.97 | -2.90 | UNKNOWN |
| pt01801053/贵金属 | 1.81 | -8.30 | -16.72 | UNKNOWN |

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
