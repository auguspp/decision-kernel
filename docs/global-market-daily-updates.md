# 全球市场日终数据持续更新

2026-09-30 Asia/Shanghai，原 Sites 对话 Human 明确要求“以后都要用实时数据，网页里还有一些别的地方也是旧的”。#621 记录完整前提对账。旧“仅手动有限采集”在六族已接入数据的每日更新范围内由此指令取代；不授权 Quick/Full/Odds/交易。

原六族接口只提供有日期的日终行，不是盘中报价。复用两个原 workflow、原 Relay/公开来源和原 publisher，不新建 Site、调度服务或数据源。每天 UTC 00:17 indices、00:37 shibor、00:57 treasury、01:17 fx、01:37 commodities、01:57 crypto（北京时间 08:17–09:57）。每族每天一批，默认截止昨日 UTC；并发组、请求/超时/重试/失败/部分结果保留约束不变。GitHub schedule 可延迟，不能保证准点或每次成功。

计划事件固定为实际 `schedule`，不伪造 workflow_dispatch；既有手动身份与历史原件仍可读。scheduled 分支只用当次 github.sha，仍要求 checkout=GITHUB_SHA=当时main 和精确独立main CI成功；手动仍需 code-sha。保留 contents/actions read、原secret范围、artifact每族命名、30天原件、attempt1与原main-only门禁。publisher已经允许schedule，无需新增写权限。

回退：正常PR移除这六个cron停止新采集；保留schedule历史reader，旧原件不删除。部署或CI通过不是自然日程运行、实时行情、来源完整或研究验收。

复用：原 radar-smart-money 原生schedule、global两族workflow/client/replay/reader/publisher；GitHub官方events schedule合同（default branch/真实事件/UTC与延迟）；外部采集的已有 #610/#614 候选、原官方 Actions checkout/setup-python/upload-artifact 实现保持，不引入另一个调度/采集依赖。Reuse Decision: REUSE 原采集与GitHub scheduler，THIN_ADAPTER 真实schedule身份。
