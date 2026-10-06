# D公开叙事输入：复用新闻窗口，先分清重复曝光

2026-10-06，归属#509。依据[伴随功能接续授权](https://github.com/auguspp/decision-kernel/issues/509#issuecomment-5974700368)及其原公开叙事需求。本批只补现役News reader的同标题复现上下文，不宣称完整社区舆情或D整体验收。

## 真实用途与范围

固定R `c5df30e8b3bc0cc865b1d75e5697bb55a94c89f8` 所用News run37424390105／artifact11394570639已取回：303139bytes，SHA256 `bae6929f9a77abfda20f7bb17cdd01a1522e04c24395503b672c999d09b4b716`。ZIP CRC、25项manifest原件字节和两份projection自哈希已核。对其保存历史作独立字典统计，再以本helper计算：470版本、467来源文章、439个仅空白归一的不同标题、27个同标题多版本组，其中26组跨渠道；保存版本累计出现723次。历史保留4次采集、一次来源缺口，最大采集间隔22420秒。这些不是723条独立新闻或26个已核实共识。

该样本含同一文章、同一标题的多个版本，也有完全同标题出现在不同新闻渠道的记录。原reader已按version_id去掉同版本复抓，却未把上述分母同时呈现；直接数标题出现次数会混淆轮询、版本与渠道。这是本批补充的实际用途，不改变旧新闻身份或内容。

## 最小实现与数据归属

`news_daily_reading.read`在原`source.replay_history`核验后，调用私有纯helper；将`headline_repetition`加到已有news-daily.json的projection中，原封口自动包含它。原news-daily.md新增同标题段，正常README仍引用同一文件。没有第五个发布器、附加来源、单独registry、状态库或新的文件树。

分组只折叠空白，不折叠数字、标点、大小写或肯定/否定。完全同标题也不是同一个经济事件的证明；不同标题也可能讲同一事件。组中保留全部version_id、来源文章数、渠道名和原最早/末次抓取时间；正文最多展示按末次抓取排序的10组，JSON保留所有重复组与同文章多版本关系，原索引一条不删。

抓取次数不是作者或独立消息数，渠道名不是底层独立消息源。重复发布、发布时间声明变化与真正文本修订不自动推断原因。抓取跨度不当观点持续时长，旧失链/截断和陈旧状态不因新视图消失。作者数、互动、语义分歧及拥挤评分保持null；公司暴露未评价，semantic_review仍NOT_PERFORMED，四authority仍NONE。

## 复用、官方能力与外部合同

REUSE / THIN_ADAPTER：复用现役NewsNow七窗口、external_radar_observations的article/version身份、news_rolling原重放/上限/缺口、同R发布、_text和原容量预算。官方GitHub继续提供原artifact与Git字节；Python原生字符串split及字典足够精确空白分组，无新包或API。

已恢复[原供应商与living prior-art记录](https://github.com/auguspp/decision-kernel/issues/508#issuecomment-5773538785)，并读取两候选的实际当前默认分支及最近提交：

- EasyStock `c7488138ca03d6c204a1e9cc8b951c66ba6d2c44`，最近为休市主题强度修复。实际读`backend/internal/review/daily_summary.go`前185行，blob `a52d31b1f606a0e061087636296a8420dbe03b9a`：按作者/文章组织观点、分歧、触发与反证，依赖正文/作者和其Agent流程。可借分开作者与文章的责任；当前七新闻窗口没有作者样本，不能调用其共识能力或继承AutoApprove。
- OpenStock `e109f188480b7e5f4a8349dde582aeea45875071`，最近为watchlist布局修复。实际读完整`lib/actions/adanos.helpers.ts`，blob `44713de1e4083753600c68a3a36063cb173a991c`：从独立输入的buzz、mentions/trades、bullish_pct计算混合指标/一致性。当前没有这些输入，不移植均值/阈值，也不从标题数量伪造字段。

两者对当前输入均不直接适配；本次未复制外部代码、安装框架或调用Adanos/外部Agent，也未声称完整许可/安全审计。未来真实需要社区作者或互动样本时，再核具体能力、许可、数据接收者和授权。没有以本批开通雪球/股吧/小红书、Cookie、账号或订阅。

## 验证、失败与退出

局部实际运行10项私有helper检查与上面真实保存索引分组；本地AST切片使用等价的primitive JSON哈希/时钟/文本转义和原公开authority字段，不是完整checkout、原来源重放或完整依赖环境。另两项原Collector/ZIP/normalizer集成检查提交到现役CI，要求原4次读取不增加、原状态不变、篡改派生值拒绝、旧无该字段的读取继续可显示。正式full/main/正常publisher/固定R内容验收分别以PR回执成立。

无采集权限变化、无新增费用/任务、无自动提研究或通知。容量不足沿原News/publication失败边界，不放宽限额；原来源失败不被本功能降为quiet。退出只删除本reader私有helper及其两个消费接点、专属测试和说明，原索引与所有历史原件继续可读。
