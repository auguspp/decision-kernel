# 下一会话通知｜Decision Kernel #297 P0

继续 `auguspp/decision-kernel` 的已批准P0。目标是实现并真实验收P0，只有确需Human权限、范围裁定或真实使用反馈时才提出；不在“已提交PR/CI在跑”假称完成，不承诺会话外后台工作。

## 先恢复

先解析当前main为M，在同一M完整读取：

- `docs/HANDOVER-2026-09-14-P0-DELIVERY.md`
- `docs/NEXT-CHAT-NOTICE-2026-09-14-P0-DELIVERY.md`
- `AGENTS.md`；涉及公司研究/Odds时另读 `docs/RESEARCH-ENTRY.md`。

再直接读取 #297 最新回执，以及当前 `read-model/current-state`、`research-work/stock-business-v0`、`research-work/disclosures-v0`。固定R后只在同一R消费README/current-state/相关read_path，不以旧聊天代替GitHub。

正式顺序：RM-20260914-r1 / #297 comment `5660297398`。
Human实施批准：`5660584568`。
最近综合P0验收：`5665615573`；Brief：#299 `5665630891`；Odds Book：#349 `5665638453`。
完整需求导航：#297 `5665559201`；其未改变RM顺序。

归档前基线（不是永久当前值；归档本身会推进main）：
```text
main = 446bbb82206d8dec46b3d88e975012f828cdd17e
read-model/current-state = fb110c73faf2773beb28c3d868889e73931160ab
research-work/stock-business-v0 = 5d49e072b16869586f0ad87c696ddf3f593d2658
research-work/disclosures-v0 = 70f06cdc2181dd96b92146c5a85e50d678042ca7
```

## 从这里继续，不重新施工

#365/P0-A、#366/P0-B已完成工程/正常发布/同R读回。六家公司具体处置、系统owner、Sector完整/ongoing入口、两家追加业务审阅和十家公司Odds Book已可读。旧终局理由仍CHALLENGED，原输出/失败保留；无新canonical Funnel/Human接受，不补造和顺Quick。Book不是Watch或全历史穷尽。

#367/P0-C显式请求入口已真实执行run `34842900705`（push、attempt1），7/7 ALREADY_RESERVED，合法NOOP、无新模型调用。独立CI `34842900729`：3226 passed，无pytest skip；正常publisher `34842934852`已验。不要重发旧scan请求或把该NOOP当自然新问题研究完成。

下一步优先核验真实新自然run → 原Research/有据停止 → 保存/publisher → Brief → Human回应的链路，以及v1.2可读性和5–10个真实合格交易日。无新问题允许NOOP，未来日期/真人反馈不能补造；已有反馈不清零。发现别人已做了新的PR/run/work写入，先验现场，不重复操作。

既有Daily Brief id `6aa28013b7348191a647f2f8e75d6017`，v1.2，每天23:10 Asia/Shanghai，不重建任务。归档准备时last_run仍早于v1.2更新；通知与邮件字段均false，Human已被告知账户侧开启通知，未确认完成。先核验届时配置/交付和已有回应，不重复要求设置。

## 读写和启动能力

先发现并实际使用本会话GitHub工具。新会话是否有读写/native dispatch取决于实际连接和动作，不能预先保证，也不能照搬旧会话“只能Actions/不能写”的结论。

有native workflow_dispatch且原流程合法时优先用；没有时，已验收的 `saved-disclosure-research` 支持显式first-addition请求，不必仅因工具拆分让Human搬run/SHA。但它仅覆盖原公告研究workflow，不是所有Actions的通用启动器。

任何新请求先读当前 `.github/workflows/saved-disclosure-research.yml`、`src/decision_kernel/runtime/saved_disclosure_invocation.py`及原host/续作合同；绑定精确approved parent、其正常发布R、当前work、source和时效。单一request-only提交，不混改代码；先查请求历史/active/queued/已消耗身份。重复或不确定先读现场，不盲重试。本通知本身不要求立刻发起任何run。

## 不越界

不重做#352–363/#365–367；不Re-run34765190284/34797952444/34807883332/34842900705；不重发scan-34601025149.json或旧Stock recovery/successor/continuation；不重跑光电/东软，不删必需正文或反证。

P1的#321运行闭合、#349-C真实Watch、新Radar及全仓重构未因本交接自动获准施工。可按现有RM做有限只读准备，开始下一生产切片前由需求管理明确范围。不要把“准备P1设计”解释成已经授权实现。

Evidence changes Belief；Price changes Odds。Data != Evidence != Judgment != Decision。AI无Investment Authority；不自动Deep/Odds/Action/交易/仓位/监控。

继续时交付用户价值与真实剩余边界，必要写回#297/#299并精确读回；不要求Human搬技术编号，不用新工程替代自然验收。
