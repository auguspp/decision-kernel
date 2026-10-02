# C1固定取报入口已退役｜保留离线历史核验

2026-10-02。Authority：[Human采纳个人投资者范围](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5948305322)。
当前产品边界由[研究成果合同](research-outcome-contract-v1.md#c1个人投资者范围可用证据优先完整券商原件为可选增强2026-10-02)持有。

## 当前处置

#715/#716的固定光迅两日期取报及原生字段后继不再是施工队列或C必交样本。
`.github/workflows/c1-report-locators.yml`已从当前树删除；脚本不再包含联网capture函数或capture命令。
只保留`plan`、`identity`、`inspect`、`rebuild`与verify CLI，用于解释旧输入/原件，不执行计划。
原生模式是旧manifest的历史标记，不是新的采集许可。旧authorization和剩余预算不复活。

共享`research_comparison`、`reviewed_forecasts`、Relay、Smart Money、#717发现层及相关历史不退役。
“不再强制取得原报告”不等于允许比较不合格数字；光迅旧NOT_COMPARABLE/null继续，格力候选不替换它。
不要求Human搬运固定PDF，也不为验收再换一组报告。缺可选原文时，独立研究可继续，相关模型结论保持未知。
C2受阻源操作、Brief自然接续、Sites暂停及D边界与本次无关，未被解除或签收。

## 必要历史与准确恢复定位

最后含完整旧执行器的代码：`5cf2bf3f4558d7e41667ecf32111b36c42a4cd4d`。
[旧运行说明](https://github.com/auguspp/decision-kernel/blob/5cf2bf3f4558d7e41667ecf32111b36c42a4cd4d/docs/c1-report-locators.md)、
[首次来源回执](https://github.com/auguspp/decision-kernel/pull/715#issuecomment-5946188058)、
[最终交付和平台拒绝](https://github.com/auguspp/decision-kernel/pull/716#issuecomment-5946361983)继续保留。
恢复旧版本用于读取不授予重新执行权限。

实际首run `36968934918` / attempt `1`，代码
`c31a62bc08d543a2d5cd6e6c3a377e65f0b5b25f`，artifact `11210703148`，
ZIP 2184 bytes，SHA256 `e2f951b99cdd529acd3feba3fb8d736259f2bf654d84dc1e1c88efbd3031d764`。
仅4月目标一笔逻辑/两次HTTP：先504，再200但114行×10列全空；9月目标未执行。
原生字段后继被平台安全拒绝，未观察到新run。目录成功退出不是目标报告已取得。
该Actions原件原定于`2026-11-01T05:27:34Z`到期；Git保留此定位不延长附件寿命，也不证明当前仍可下载。

取得并核对这份已保存ZIP身份、哈希、大小和CRC后，使用合格代码/既有依赖环境，离线读取其原文件：

```sh
GITHUB_REPOSITORY=auguspp/decision-kernel \
GITHUB_SHA=c31a62bc08d543a2d5cd6e6c3a377e65f0b5b25f \
GITHUB_RUN_ID=36968934918 GITHUB_RUN_ATTEMPT=1 \
GITHUB_REF=refs/heads/main GITHUB_EVENT_NAME=workflow_dispatch \
PYTHONPATH=/path/to/qualified-checkout/src python \
  /path/to/qualified-checkout/.github/scripts/c1-report-locators.py \
  verify --root /path/to/retained-original-files
```

上述环境是原件身份，不是假装当前执行发生在过去。verify不需要来源凭据，不联网、不写文件；
重新生成的summary必须与原文件逐字节一致，拒绝篡改、额外文件及错误原执行身份。
原件已过期或不在可恢复范围时如实说明，不用派生摘要再造原响应。

## 重新接入与退出成本

将来有成熟开源轮子或已获准服务的新能力，沿Reuse First审阅实际源码/合同与旧失败，
在具体研究需要下有界验证跨日期/对象的取得、合法保存、后继读取与个人维护成本，再接可选增强。
不设自动找轮子任务、不自建完整资料库，不因一次成功或新封装复位旧拒绝/预算。
新费用或权限另行决定；没有这些变化时继续现有可用证据研究，不反复索要PDF。
恢复工具不自动恢复“完整模型为必交”的旧承诺。

本次退役同步收缩执行器专属测试，保留旧原件解释/回放和拒绝错误输入的检查。
代码、CI、正常发布、真实使用和Human接受仍分别记录；不新增provider、数据库或采集流程。
