# Odds 结果留存与同版本 Research 恢复 v0

Scope: #321-B；接续 #405。Reuse Decision: THIN_ADAPTER。
这不是新的研究、计算器、归档服务、行情源或 publisher。既有公司资格退出、
Human 接受记录及 Watch 配置均不因保存/恢复而改变。

## 保存：原字节先落地，原验证器再复核

`runtime.odds_retention` 只接收 #405 已生成的两种对象：
`FrozenProvisionalOdds`（PROVISIONAL）与 `SameResearchOddsComparison`
（SAME_RESEARCH_COMPARISON）。不解析任意研报、不新增情景、不重新取价。

调用前通过原 #321-A 入口恢复并复核 Research。`expected-research-hash` 来自
已核过的 Research/登记，而不是从待验证结果里抄一个自报 hash。

```sh
python -m decision_kernel.runtime.odds_retention retain \
  --input original-result.json --kind PROVISIONAL \
  --research-directory recovered-research/bundle \
  --expected-research-hash '<已固定的完整ResearchSnapshot hash>' \
  --output new-result-directory

python -m decision_kernel.runtime.odds_retention verify \
  --research-directory recovered-research/bundle \
  --expected-research-hash '<同一完整ResearchSnapshot hash>' \
  --output new-result-directory
```

新目录严格只有 `result.json` 与 `retention.json`。前者是原输入字节，不是
重新序列化的替代品；后者区分原结果时点与实际留存时点，绑定结果字节/语义 hash、
snapshot 全文 hash、package hash 和 information-bundle hash。

Research 使用原 `read_retained_commit()` 复验；结果使用 #405 的确定性重建
验证器。只校验 JSON 形状或自报 hash 不够。没有数值世界的 schema-v2 结果
可保留 `NO_CALCULATION / ORDINAL_NOT_ESTABLISHED`，这不是成功算出零赔率。

沿用原 512 KiB 文件上限、独占写入、symlink 拒绝和读回检查。验证失败保留
`result.json` 和能够写出的 `rejection.json`；磁盘故障可能只留下前缀。
已有/半写目录绝不覆盖或自动重试。命令失败返回2且不回显来源正文/异常私密内容。

## 原生 Git 登记：一个结果、一个明确研究依赖

原 [Research archive](research-archive-v0.md) 的 Git 保存/登记/正常发布程序不变。
结果目录和研究目录各自平面保存；不要把结果文件塞进原 Research commit 的
严格清单，也不要复制/修改 Research 来适配新结果。仍然使用普通 reviewed PR。

结果的原 purpose reference 追加以下 `archive` 元数据：

```json
{
  "format": "ODDS_RESULT",
  "result_kind": "PROVISIONAL",
  "research_record_id": "已登记的精确Research记录id",
  "research_snapshot_hash": "已固定的64位小写SHA256"
}
```

`source.path/ref/git_blob` 指向该结果目录的入口及不可变 Git commit/blob。
依赖记录必须是同一 pinned R 中可见且显式登记的 `RESEARCH_COMMIT`；两个
记录的导航 case 必须一致，实际证券/研究身份继续由原包与结果验证器检查。
不按股票代码猜最新版本、不允许循环、不依赖另一个 Odds/Progress/raw 档案。
比较结果使用 `result_kind=SAME_RESEARCH_COMPARISON`，不能把 provisional
改标签当 canonical。

## 恢复：同一个 R，两个原件，再重建验证

仍调用原命令，不新增远端读取器：

```sh
python -m decision_kernel.runtime.research_archive \
  --reading-commit '<固定R>' --record-id '<结果用途记录id>' \
  --output new-recovery-directory
```

原读取器检查结果的 source/tree/blob，再用同一固定 R 恢复唯一的 Research
依赖。依赖只能是最多5文件的原 `RESEARCH_COMMIT`，不能继续递归；结果目录
只能有前述2文件，原24次 API预算不放宽。读取与 registry 字节也必须完全相同。

输出 `bundle/` 是结果原件，`research/bundle/` 是原研究；两层都保留原来
的 reading/registry/Git 元数据和读回回执。研究依赖失败时已经取得的结果前缀
不丢失，根目录不会产生成功 readback。依赖成功不代表整个结果恢复成功。

成功资格是 `ODDS_RESULT_REVALIDATED_NOT_CURRENT_QUALIFICATION`。
`SAVED_RESULT_REBUILT_FOR_VERIFICATION_NOT_NEW_PRICE_ANALYSIS` 明确指原时点、
原价格的算术核验，不是今天重算 Odds。恢复不会刷新来源或行情资格，不建立
概率校准、Human 接受、投资决定、Watch 或 Action。型别中的 canonical 分支
也不能独自证明实际行情源资格；原 ingress 的来源/证券绑定仍须独立成立。

## 验收边界

合成测试验证原字节、严格目录、同R依赖、篡改/重哈希、循环拒绝、失败前缀和
真实离线 CLI。它们不是实际公司 provisional→canonical 接受，也不是新的自然
生产样本。现有人工/ordinal公司报告不会自动转换；需要合格原始 typed Research
及真实已声明的价格输入，不能为闭环捏造概率、时间或 Human 原话。

普通 publisher 不变：它仍发布原用途入口及同R registry；完整档案仅在显式恢复
时取回。代码发布、实际数据登记/远端往返、公司数值资格与投资判断分别验收。
