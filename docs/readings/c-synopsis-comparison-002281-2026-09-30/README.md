# C：同机构公开研报摘要的有界比较验收

2026-09-30。目的仅为验证已有来源、版本、算术与恢复后端能保留一组真实比较及其资格边界，不发起新的Full、估值、Odds或投资判断。

## 从已有记录接续

在固定R `502036708fc1e9d28a700dcf681f3bc894d0f95e` 的普通Research记录找到 `002281-accelink-full-research-20260917-v1`，沿其精确A `6b45ddeb6db51cb16933f2885a9daee7c3228541` 恢复README、sources.md和accelink-calculations.json中的既有长江证券比较。原来源完整字节重放为PARTIAL，原Full未建立Human接受或canonical Odds；本次不改原档案或扩大其资格。

只核读原sources.md已列的两条公开摘要定位：[早期](https://stock.finance.sina.com.cn/stock/go.php/vReport_Show/kind/search/rptid/830894481499/index.phtml)、[后期](https://stock.finance.sina.com.cn/stock/go.php/vReport_Show/kind/search/rptid/842411263451/index.phtml)。本次web工具返回的标题区和预测段均可读；没有下载原券商PDF/模型，不保管整篇受版权保护正文。evidence.json是少量字段的研究者提取，不是原HTTP/完整HTML。2026-09-30核读不补造4月、9月首次可得时钟。

## 取得的比较与不能推论的内容

两页均归属光迅科技002281、长江证券，显示日期分别为2026-04-30和2026-09-10，目标年都是2026/2027/2028。所列归母预测依次为14.71/19.89/27.03与17.35/33.86/45.41，单位标为亿元。作者组合不同，故不是同分析师连续性证明。

比较只回答“这两个公开摘要所归属的同机构、同目标年、同名总利润数字相差多少”：差额2.64/13.97/18.38，名义变化约17.95%/70.24%/68.00%。公式和未舍入Decimal结果见comparison.json，与旧档案算术在浮点误差内一致。原生产institutional_context的NOT_COMPARABLE限制不改变。

币种代码未在选取预测句中独立列明；同名归母指标不证明全部调整、并表边界或模型一致。股本分母未恢复，因此不作EPS、每股价值或价格倍数比较。原PDF、完整模型、正式修订声明、同ID前后正文变化和历史available_at均未验证。**严格完整模型可比修订仍NOT_ESTABLISHED**；只接受上述有明确来源资格的名义总额比较，不据此改Belief、判断新公司事件或回填旧研究的证据完整性。

## 复用和后继验收

内部：原institutional_context保留机构ID、原行、版本、真实时钟及缺失/零；RESEARCH-ENTRY的市场预期对照；原RETAINED_FILES/用途索引/发布和读回。官方：原生Git精确版本与Python标准库Decimal。

外部：先消费#508/#511既有审阅。当前EasyStock相关研报/type/许可与旧版本相同，缺失值转0不采用；AKShare研报文件相同，currentYear给历史槽标年、丢身份及全页取数不采用；Anthropic相关方法可复用但不是比较数据库；Wilson定位/引用反例可复用，不继承未知事件时钟回退公告日。详细核查回执归#504/#508；没有把候选框架或新依赖装入项目。

Reuse Decision: REUSE。没有真实证据要求新增comparator、provider、schema或任务。保存/登记/发布、另一上下文恢复与来源经济真实性分别成立。本目录没有执行来源调用器、旧研究脚本或模型，不改#504两条异机构样本，也不把本次核读当全池覆盖。后继独立恢复应能找回两端定位/日期/机构/年/数量级、计算以及全部资格限制。
