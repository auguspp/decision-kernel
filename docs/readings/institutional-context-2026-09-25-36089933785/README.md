# 兴森科技机构活动 / 研报列表原件｜2026-09-25

资格：RETAINED_FILES / SECONDARY_CONTEXT_NOT_EVIDENCE。不是完成的Quick/Full研究，不是调研次数认证或可比预测修订。

## 本次范围和实际结果

证券002436.SZ；请求的披露日期窗口2026-08-11至2026-09-24；两个固定接口各一次GET，每个最多50行。没有全市场扫描、分页追加、重试、模型调用、PDF正文获取、交易或自动提醒。

研报接口HTTP200，来源报告hits=2、TotalPage=1，实际返回两条：
- 浦银国际证券，2026-08-27，AP202608271828545222。
- 开源证券，2026-08-24，AP202608241828363256。

这是来源返回范围的2/2，不是独立认证所有券商研究均已获取；报告原PDF未获取。完整原始行与EPS相对槽位在reports.body。不同券商不能当作同一预测的上修/下修；目标期、货币和股本口径未确认，预测可比性NOT_ESTABLISHED。

机构调研接口HTTP200，但JSON为success=false/result=null/code=9201/message=返回数据为空。失败原件activity.body保留。事件数、独立机构数和人数均UNKNOWN；这不证明窗口内没有调研，也不能推断是接口故障、筛选字段问题或公司确无披露。

取得窗口：2026-09-25T03:20:21.213258+00:00至2026-09-25T03:20:22.992120+00:00。供应商的披露/事件日期与本次取得时钟分开；未建立历史available_at，未把本次取得日期写回报告日期。

## 执行与保管身份

- Repository: auguspp/decision-kernel
- Workflow: .github/workflows/institutional-context.yml
- Source code: a6a1d5f0c652d3012a0b408a97c491a76d1f18bc
- Run: 36089933785 / attempt1 / workflow_dispatch / completed success
- Artifact: 10844239864 / institutional-context-36089933785-1
- Artifact ZIP: 6109 bytes; SHA256 3e92953c544437ab198df8a23a0bf6bc2f59876e500c1578b5a05e3bff37ab35
- Capture hash: 0c4f029cd802f30921546de8c51100e8a22248a8a1a6b3360143c6b97902ebfb

工作流绿色只表示capture/replay/留档按合同完成。下面五个文件从上述ZIP逐字节复制，README是本次追加的归档说明，不冒充源站响应。原JSON/时钟/失败不更正或重跑。context.json/summary.md是当时代码的派生产物，不是源站原件。

| 文件 | 字节数 | SHA256 |
|---|---:|---|
| activity.body | 89 | ea6528a2204b61a7ee34683a73ca00f8afdc86aadf3f765d4dae39bbfb19dbe7 |
| capture.json | 2325 | 3053312f88be4696511fb58969ea58744d821eea5cfaf20fc560897ab9dd9ad4 |
| context.json | 6835 | 6b756d6978e41f9cd07f0535a9d81b5e271d7e9fae65ad23e067052d18d4e32c |
| reports.body | 2888 | dab8ad13b138601ee5c53622b75a3a9110f47e73f23c8fd5d8781dcf693c6276 |
| summary.md | 778 | 68122743632bcf4ec2ee894373a811582cafce8c6d74fcd44687329390965f51 |

## 供后续研究使用

Hosted Quick可按两份报告标识寻找原文、核对目标期与预测口径，再解释是否值得继续；这不是自动续作授权。机构活动缺口继续开放，不因研报接口成功而签成调研模块成功。未执行数值预测修订、Research接受、Odds、Watch或任何资本决定。

此档案只需在已有purpose registry按需登记；登记不等于正文已读或研究已接受。来源稳定性与日常自动交付仍未建立，#504/P1不由本次有限样本整体签收。
