# 神农 P0-4A 候选阅读入口（未接收入正式 Research）

请先固定本候选分支的精确 commit，再在同一 commit 读取下列相对路径。
本目录属于 #285 独立 DRAFT；不是 current-state 正式待办，也不是投资建议。

## 时间和来源

- 原观察交易日：2026-09-07；Stock run `34167972382`、artifact `10034876430`。
- 采用的已验收读取包：`e7ad9591a3139b568708a8d927494027d45da924`。
- 固定研究代码：`30a28c0763d56b74d82c06ac544b724fe265f41d`。
- 研究 cutoff：2026-09-08T12:17:30Z（北京时间20:17:30）。
- 原回执记录的执行区间：12:20:16Z—12:23:20Z；不是新的市场采集。

## 先读哪个文件

| 文件 | 用途 |
|---|---|
| `binding-repair-01/input.json` | 原冻结输入的逐字节副本；没有改 cutoff、来源或预算 |
| `binding-repair-01/candidate.json` | 修正输入哈希及未证实模型身份标签后的待验证候选；Discovery/Pre/Quick正文及Evidence原样保留 |
| `binding-repair-01/funnel.json` | 与候选比较的原 Funnel 预期结果；是否通过须看该版本实际CI，不是模型填写的通过标志 |
| `binding-repair-01/correction.json` | 本次修正的四个字段、失败来源和字节身份 |
| `review.md` | 本轮来源复核、语义限制及未完成验收项 |
| `input.json`、`candidate.rejected.json`、`funnel.unvalidated.json` | 原失败版本保留，不作为已验证研究结果 |

原候选 CI `34226817088` / job `102062846947` 的实际结果为
**1 failed, 2068 passed in 627.43s**；原校验拒绝 `input_hash` 不匹配。
失败及原文件均保留。修正版等待新提交触发的普通 PR CI，不 Re-run 原 run。

## 候选实际表达与限制

原文提出 Pre `CONTINUE_TO_QUICK`，Quick `WAIT_FOR_TRIGGER`，没有自动 Deep。
成功读取计数4含两次GitHub输入/攻击样本读取，实际外部业务来源为2份。
4月经营公告与7月半年度业绩预告说明的是各自所属时期；没有取得后续成本、现金流、
行业供给及市场预期证据，不能据此证明9月基本面状态或解释9月股价。

候选原句“Quick falsifies ... already-improving realized earnings”措辞过强：早期压力
并不排除后期改善。该原文保留给需求侧审阅，本轮没有偷偷替换成已验收结论。
WAIT仅是原候选的研究路由；不表示证据完整、市场quiet或请求已获得正式登记。

预算是 SOFT_EXECUTOR；没有实际路径级权限沙箱。原回执中的精确模型标签缺乏平台
证明，修正版设为未知。一次读入攻击样本不是独立正常/恶意配对测试，也不是#263验收。

阶段状态由最终CI与需求侧语义回执分别确定。无行情/公告新增采集任务、无新Research
待办登记、无Human wake；Investment authority=NONE。
