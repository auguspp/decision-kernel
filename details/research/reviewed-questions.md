# 日常候选检查范围与已执行的问题研究

这是保存结果的读取，不是本次执行研究。历史终态、资料失败、尚未检查和Human请求分开；不自动继承接受。

## 当前保存Stock批次

市场日：2026-09-18；SAVED&#95;STOCK&#95;SCOPE&#95;NOT&#95;A&#95;COMPLETED&#95;RESEARCH&#95;REVIEW
- 道明光学 002632.SZ：ORIGINAL&#95;PRICE&#95;DISPOSITION&#95;ONLY
- 金健米业 600127.SH：DATA&#95;UNAVAILABLE&#95;NOT&#95;PRICE&#95;REJECTED
- &#42;ST航图 688066.SH：ORIGINAL&#95;PRICE&#95;DISPOSITION&#95;ONLY
- 沃顿科技 000920.SZ：QUESTION&#95;NOT&#95;YET&#95;REVIEWED
- 深粮控股 000019.SZ：ORIGINAL&#95;PRICE&#95;DISPOSITION&#95;ONLY
- 松发股份 603268.SH：QUESTION&#95;NOT&#95;YET&#95;REVIEWED

未提供问题审阅回执的对象仍是未检查，不得由未执行Pre反推没有问题。

## 已保存问题执行

读取状态：READ&#95;OK

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
