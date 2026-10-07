# 招商轮船 Full / 条件 Odds：原附件的英文文件名恢复入口

本目录是已交付研究的同字节恢复副本，不是新的研究、模型修订或投资接受。原文件名和原字节永久保留于 `a3f905d41146e29106f8ff4de71fbafbc0c081d8` 的 `docs/readings/cmes-full-odds-2026-10-07-original/`；先读该目录的 `ARCHIVE-DELIVERY.md` 了解版本与保管边界。

## 为什么有这个入口

PR #782 的 run37599437213/1 正确拒绝中文入口名：现役 `research_archive_index.project` 和 `research_archive._tree_files` 要求平面英文文件名。该失败保留。本目录只复用相同 Git blob，在原 16 文件上限内提供 12 个正文副本和这份映射，不改读取器、测试或预算，不把只改入口名而仍无法恢复整个目录当成解决。

## 一一对应的文件名

| 本目录文件 | 原附件文件 |
|---|---|
| README-original.md | README.md |
| build_report.py | build_report.py |
| calculate.py | calculate.py |
| inputs.json | inputs.json |
| manifest.json | manifest.json |
| results.json | results.json |
| source_ledger.json | source_ledger.json |
| verification.json | verification.json |
| delivery-original.md | 交付回执.md |
| price-requirements.csv | 价格反推表.csv |
| conditional-odds.csv | 条件Odds表.csv |
| report.md | 研究报告.md |

每一对是同一 Git blob，内容没有改写；这份 README 不在原 manifest 内。原 manifest 的路径仍是原文件名，在单独新目录按本表恢复文件名后才能逐项核原 manifest。`calculate.py --check` 读取的 inputs/results/verification 名字未变，可在副本上离线验证算术；这不是允许来源正文执行代码或新建自动研究任务。不要运行 build_report.py 覆盖已经留存的报告。

原 ZIP 容器为 42499 bytes，SHA256 `7104070f574958965c6ddd01d77c24b9b8136e453d3b21a0fa84516209353702`；Git 保存的是解压后的内容，不声称保存了 ZIP 容器。原报告 21220 bytes，SHA256 `3c8f52ee96e3397b8f53ea04ce9a57b603c2ac08d1b0ede7f9185951c3be2ea4`，blob `92857484cd6d197e35e45c905e762d8ebac4847f`。

## 两种条件模型不得混用

本副本对应用户所见的原模型：50艘等效VLCC、350日、85%转换、三年归母分红加退出PE，36项原算术检查。PR #782 既有 `docs/readings/cmes-full-odds-2026-10-07/` 的两文件则是345日现金等价/更新准备/项目价值模型。两者分别保留，不因保存顺序宣布经济替代，不拼接结果或验证回执，也不是两个独立研究者。

原文件中的 NOT_SAVED / TOOL_NOT_EXPOSED 是当时记录；本轮已实际获得 GitHub/MCP 写入，后继交付状态以 PR #782 精确回执为准。原件、用途登记、CI、main、publisher 和固定 R 回读分别验收。登记为 RETAINED_FILES；公司原始 PDF、全部租约、NAV、概率、Human接受、typed COMMITTED、canonical Odds、Watch 和投资权限未由归档补齐。

本次不重做 Full，不重抓行情或公告，不启动 CONS-07 开发，不改变 D/C、来源、费用、日程或通知。Investment Authority = NONE。
