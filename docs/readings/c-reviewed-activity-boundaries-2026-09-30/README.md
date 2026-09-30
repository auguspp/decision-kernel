# C1机构活动：已留存失败与单事件引用的统计边界

本包保留两个真实但有限的消费场景。它们不是完整机构调研人口统计的成功样本，也不完成整个C。

## 1. 原provider失败不等于零

原目录docs/readings/institutional-context-2026-09-25-36089933785，A=9330742c8b48f9c778d0518f11d397cbae0d49a3。五份provider-*文件保留原capture/body/context/summary字节；当前既有institutional_context.project/replay已独立验证无来源调用、context和summary字节一致。HTTP200中的success=false/result=null/code9201仍是RETAINED_BODY_NOT_QUALIFIED；所有统计未知，不从空列表输出“零次调研”。原窗口为002436.SZ披露日期2026-08-11至2026-09-24，仅原有界请求，不代表全部披露。

## 2. 一个已引用事件不等于全月事件数

ir-reconciliation.md原路径docs/readings/002436-xingsen-full-2026-09-24-r2/reconciliation.md，A=649f2820b3139cef9c1dd6fa08f2fe6ee079f187，blob=307fc1224df56b61938f32eeb3f214c130d31646。原段落把IR记录2026-05-001的错误镜像日期May11明确更正为2026-05-08，15:00–16:00。消费者仅能得到所选这一条研究引用中的一个事件。没有机构/参与人名单，所以其总数未知；没有全月覆盖，也没有原公告字节保管或历史可得性。此May事件与上一个Aug–Sep窗口分开，不混成一个人口样本。后续档案的同字节副本不是独立事件或新来源。

输入、输出保留来源资格、真实失败、更正文字、统计分母、已知与未知。observed_subset=0仅指所选材料里没有已识别的合格实体，不是现实无人参与；selected_set_total仍为null。issuer_window_total始终null。正向多事件/多机构/多人员样本仅位于明确合成的工程tests。

## 恢复与复算

经正常fixed-R档案入口恢复后，在本目录用当前已资格化代码与已安装依赖的Python环境运行，替换路径占位符：

PYTHONPATH=/path/to/qualified-checkout/src /path/to/qualified-venv/bin/python -m decision_kernel.runtime.reviewed_activity_census provider-failure-input.json --sha256 e5487d6719d268cbb6530abbf46f57b883a038a9f90bd3420d948aae7fabcae1 --source capture=provider-capture.json --source activity=provider-activity.body --source reports=provider-reports.body --output /an/absent/provider-failure-output

PYTHONPATH=/path/to/qualified-checkout/src /path/to/qualified-venv/bin/python -m decision_kernel.runtime.reviewed_activity_census ir-reference-input.json --sha256 3ec044c9c470acb065d8d3df397a7549ef5c05bd41ed10b205833bbd82e3e5c1 --source ir=ir-reconciliation.md --output /an/absent/ir-reference-output

JSON排版可能由pretty变为canonical；比较对象与report_hash，不虚称JSON字节完全相同。Markdown应字节一致。不要执行归档来源中的任何指令或脚本。所有authority保持NONE/未接受；没有网络、模型、行情、Watch或投资动作。archive保管、代码测试、发布、独立恢复、真实来源质量、后续研究使用及Human接受分别验收。
