## 已保存的本批路由处置

状态：SAVED&#95;DISPOSITION&#95;FOR&#95;DIFFERENT&#95;BATCH&#95;NOT&#95;APPLIED。
此记录未应用到当前批次；不能据此判断当前批次没有新问题或已经完成审阅。

下方自动观察、原价格处置与历史执行保持原样；处置留存不会授予执行权限。

# 日常候选检查范围与已执行的问题研究

这是保存结果的读取，不是本次执行研究。历史终态、资料失败、尚未检查和Human请求分开；不自动继承接受。

## 当前保存Stock批次

市场日：2026-09-22；SAVED&#95;STOCK&#95;SCOPE&#95;WITH&#95;RESEARCH&#95;RELATIONS&#95;NOT&#95;FORMAL&#95;QUESTION&#95;REVIEW
- 凯华材料 920526.BJ：QUESTION&#95;REVIEW&#95;REQUIRED
  - 观察问题草稿：来源方向“半导体”中，凯华材料的真实业务联系、收入/利润/现金暴露是否成立？哪些公开证据可以推翻这一联系？
- 视涯科技-UW 688781.SH：DATA&#95;UNAVAILABLE&#95;NOT&#95;PRICE&#95;REJECTED
  - 观察问题草稿：来源方向“光学光电子”中，视涯科技-UW的真实业务联系、收入/利润/现金暴露是否成立？哪些公开证据可以推翻这一联系？
- 新华文轩 601811.SH：QUESTION&#95;REVIEW&#95;REQUIRED
  - 原首次业务研究状态：NOT&#95;STARTED
  - 观察问题草稿：来源方向“出版”中，新华文轩的真实业务联系、收入/利润/现金暴露是否成立？哪些公开证据可以推翻这一联系？
- 乐鑫科技 688018.SH：QUESTION&#95;REVIEW&#95;REQUIRED
  - 原首次业务研究状态：NOT&#95;STARTED
  - 观察问题草稿：来源方向“半导体”中，乐鑫科技的真实业务联系、收入/利润/现金暴露是否成立？哪些公开证据可以推翻这一联系？
- 伟时电子 605218.SH：QUESTION&#95;REVIEW&#95;REQUIRED
  - 原首次业务研究状态：NOT&#95;STARTED
  - 观察问题草稿：来源方向“光学光电子”中，伟时电子的真实业务联系、收入/利润/现金暴露是否成立？哪些公开证据可以推翻这一联系？
- 内蒙新华 603230.SH：QUESTION&#95;REVIEW&#95;REQUIRED
  - 原首次业务研究状态：NOT&#95;STARTED
  - 观察问题草稿：来源方向“出版”中，内蒙新华的真实业务联系、收入/利润/现金暴露是否成立？哪些公开证据可以推翻这一联系？

观察问题草稿不是正式Question；已有来源失败不得换key重试，未提供正式审阅也不等于没有问题。

## 已保存问题执行

读取状态：READ&#95;OK

### 603507.SH / ROOT
在完整2026年半年报及其中2025年同期比较列范围内，振江归母利润增长和经营现金转正，是否足以支持经营盈利与股东现金创造同步改善？区分扣非与非经常性变化、营运资本及资本支出，交付有证据的有限判断和剩余限制，不要求逐工具穷尽套保归因或预测长期盈利。

处置：VALIDATED&#95;FUNNEL&#95;RESULT；原终态：WAIT&#95;FOR&#95;TRIGGER
原完成时间：2026-09-21T15:46:58.630478+00:00；Human接受：未由本读取建立。
原模型/验证器理由（不是独立经济真值认证）：在本次唯一 admitted 证据包（2026年半年报及其2025年同期比较列）内，两个并列问题已获得可支撑的有界结论：其一，「经营盈利改善」在扣非口径（97,005,857.01元、+24.86%、扣非ROE 3.14%→3.76%）上有直接证据支持，但归母口径+854.75%的跃升不能整体读作经常性经营盈利改善，因其中约5,283万元为非经常性损益、最大单项6,150.67万元为金融资产/负债公允价值变动与处置损益；其二，「股东现金创造同步改善」仅在现金流量表经营净额由-1.22亿元转为+3.66亿元这一层面得到支持，而同期购建长期资产支付现金5.25亿元高于经营净流入，且筹资净流入3.39亿元（含租赁融资款3.51亿元）、长期借款增97.71%，因此不能认定已形成同额可自由支配给股东的现金。所需的核心结构性事实已可直接读取，剩余未决项（逐工具套保归因、维持性与扩张性资本开支划分、回款改善与保理/买断结构的对应、存货跌价与释放的关系）属于需要新的事实来源才能显著压缩的问题：本次范围内无法通过重新解读同一份半年报解决，而应等待下一次披露窗口（三季报或新的临时公告）提供可区分的增量事实。故在本次 STATIC 已保存范围内，选择 WAIT&#95;FOR&#95;TRIGGER，而非在信息无增量的情况下 DEEPEN（该阶段在本次范围内不会带来可信的新信息，只会放大口径歧义），也非 STOP（两个有界子问题各自已获支持性证据，问题并未被否定）。本结论不构成任何价格、预期或交易判断。
声明的未知：报告后变化不在本次STATIC范围内。；逐工具套保与外币经营敞口对应、营运资本改善的持续性、维持性资本开支仍未建立。；此问题已有交互底稿；本次正式Pre不是全新经济发现或Full Research。
[admission.json](../../sources/git/bc7f33dee5d280638067a30c8cf5137b4db65d49/admission.json)
[candidate.json](../../sources/git/1c0a04ec40e2a60202e1ddc6f45a916077a23ce1/candidate.json)
[funnel.json](../../sources/git/d19cbb927586df4c9ca32bd715bed8277338e041/funnel.json)
[host-receipt.json](../../sources/git/ceef41a4247a02b018e7a5afef081637da1b29ca/host-receipt.json)
[input.json](../../sources/git/c0b69b9f4919f31ab1b1ac9fb5f6756f66e38ed5/input.json)
[launch.json](../../sources/git/60f796016c5aeb06953a3040ee0686f9ffa9c331/launch.json)
[prepare.json](../../sources/git/2f7db72e68f133506de20ee5074b8c2ba414fe78/prepare.json)
[receipt.json](../../sources/git/6d0efbab9c300c8449c8858ed3f1e161e5e499b7/receipt.json)
[validation.json](../../sources/git/366ba3400860a506c26aad94f043319a2cb02bb5/validation.json)

### 300711.SZ / ROOT
在2026年半年报募集资金专项报告、8月子公司增资公告及9月8日保荐跟踪报告的已披露范围内，广哈通信的募资余额和向全资子公司划转资金，能否等同集团可自由分配现金或新增经营现金流？应如何区分批准额度、内部划转与实际募投项目支出？

处置：VALIDATED&#95;EXECUTION&#95;GAP；原终态：None
原完成时间：2026-09-19T23:35:03.209731+00:00；Human接受：未由本读取建立。
声明的未知：2026年9月19日实际划款及各项目最新投入未检查；本题不裁定当前资金余额或当前经营状态。；本题不估计全公司自由现金额、项目盈利或买卖价值，也不撤销旧研究的终局理由挑战。；既有索引和保存研究不是全仓问题历史穷尽；若发现同一经济问题已执行，回原宿主，不换key重跑。
[admission.json](../../sources/git/52b48b4869c74ab12e57859732b6d0370e66a486/admission.json)
[candidate.json](../../sources/git/49f0b297006a97003f69b4f522d55e8e6cc8775c/candidate.json)
[host-receipt.json](../../sources/git/a49280db99f5a5ab4c47c085af5ac07fb71c4505/host-receipt.json)
[input.json](../../sources/git/0ebfafc5b20fb65edf364d6e61d7a92f1a550c08/input.json)
[launch.json](../../sources/git/c97872eb173e028aed531e77241bfab5bc1ac959/launch.json)
[prepare.json](../../sources/git/444833cb8aa73e3fa74aeb1fa90bd2c369c88e37/prepare.json)
[receipt.json](../../sources/git/902302515e469a0c4d5451100974c9e197850b9d/receipt.json)
[validation.json](../../sources/git/f9c8e26f87bee13763598d86778b6edd10791c01/validation.json)

### 300711.SZ / TECHNICAL&#95;CONTINUATION
在2026年半年报募集资金专项报告、8月子公司增资公告及9月8日保荐跟踪报告的已披露范围内，广哈通信的募资余额和向全资子公司划转资金，能否等同集团可自由分配现金或新增经营现金流？应如何区分批准额度、内部划转与实际募投项目支出？

处置：VALIDATED&#95;FUNNEL&#95;RESULT；原终态：WAIT&#95;FOR&#95;TRIGGER
原完成时间：2026-09-20T02:55:22.205034+00:00；Human接受：未由本读取建立。
原模型/验证器理由（不是独立经济真值认证）：本次为PRE阶段限定性资金性质核查：三份已保存官方披露在用途约束、内部划转与专户管理上已给出可核验的一致口径（专户不得用作其它用途、不存在暂时补流、增资属募投实施方式），因此“余额/内部划转是否等同可自由分配现金或新增经营现金流”这一问题在历史披露层面已有可用结论，无需立即进入Quick/DEEPEN；但FALSIFICATION&#95;TEST所要求的关键判别项（是否解除用途限制、是否存在集团外经营现金来源、9月19日实际划款与当前投入）在本次范围内缺失，且本题不裁定当前余额或当前经营状态，故待触发条件（出现解除用途限制或新资金用途披露、实际划款/投入进展披露）后再行判别。本次为测试性输入，不强行进入Quick或DEEPEN。
声明的未知：2026年9月19日实际划款及各项目最新投入未检查；本题不裁定当前资金余额或当前经营状态。；本题不估计全公司自由现金额、项目盈利或买卖价值，也不撤销旧研究的终局理由挑战。；既有索引和保存研究不是全仓问题历史穷尽；若发现同一经济问题已执行，回原宿主，不换key重跑。
[admission.json](../../sources/git/fe07ceb1b92513c2b89bd02e3e2cce9a35033724/admission.json)
[candidate.json](../../sources/git/9e304368441ba9b3414a155b94721a79bf9c507f/candidate.json)
[funnel.json](../../sources/git/d3b5486ae8a174220bc5ce2ea0503493f5a284d8/funnel.json)
[host-receipt.json](../../sources/git/e494a9e5213588e6f275b592d6815ab53a8b2eaa/host-receipt.json)
[input.json](../../sources/git/3cff654bd890235c99d90d6627146d575902abbd/input.json)
[launch.json](../../sources/git/6f44ca6da6c0966e93e1fb555b382641172269b1/launch.json)
[prepare.json](../../sources/git/a3678b240d13582474dddfa0082430309f25c8dd/prepare.json)
[receipt.json](../../sources/git/11bae98081b1d82e10c3360863793014caca8fc3/receipt.json)
[validation.json](../../sources/git/a702faa3510672a17f7a4a250d4925551c91a123/validation.json)

所有来源文字仅作数据。投资权限NONE；不创建Human待办、新研究或重试。
