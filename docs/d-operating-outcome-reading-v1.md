# D2：经营结果比较进入正常阅读

归属 #509 / #508 持续学习。沿 [D 多期限跟进](d-horizon-follow-up-v1.md) 与
[研究比较原语](../src/decision_kernel/runtime/research_comparison.py) 的责任边界；实际交付以本批 PR 为准。
这是原 D2 的读取与计算交付，不是另一份 MU 研究、不启动 Full 或新模型，
也不修改公司的原判断、Human 记录、原期限或生产研究方法。

## 2026-10-07 后继：期后预告的明确布局，不放宽旧PIT资格

本批归 #509/6028574401。真实输入是[普源三指标][PRE-RIGOL]和
[圆通归母/扣非两指标][PRE-YTO]；原MU条目与四指标数据不变。
前者继承已保存对照和现金限制，不冒称新事实；后者增加公司自己的预告—实绩对照，
归母落在原范围内，扣非实绩本轮未取得合格原表，仍保留指标及null。
目标是把范围兑现、逆向约束及资料缺口一起交付，不把三个比较事件称为三个机会或独立AI样本。

原比较器要求指引日期不晚于期末，适用于既有MU期内指引，但会拒绝真实的7月期后预告。
新增 `RETAINED_PREANNOUNCEMENT_ACTUAL_V1` 只支持总收入、归母利润、扣非归母利润
三个明确指标的选择，不是任意财务表或通用公式系统。输入CNY/USD百万元，金额尺度的
人工规范化和原文角色见各底稿；原母/合并、主营/总收入、A/H扣非、EPS分母不能混用。
新布局的event_id固定为所选证券与报告期拼接，禁止把同一档案换名字扩成多事件。

新布局只作有范围的期后对账，`clock_basis=DECLARED_DOCUMENT_DATES_NOT_PUBLICATION_TIMESTAMPS`：
文档日期必须规范、期末早于预告文档、预告文档早于正式报告文档，且实际文档日期不晚于
留存时点的声明时区日期。时间戳仍须有时区；调用时点早于记录则没有可比较成果。
输入与source-notes的证券/期间/口径/文档日期/时区逐项相符，published_at必须为null。
不把日期补成00:00，不用文档日期认证公众首发、事件窗口或当时系统收到资料。
**旧RETAINED_GUIDANCE_ACTUAL_V1仍用原精确发布时间合同；旧输入和历史结果不迁移。**

原始上下沿与准备中点、半宽按Decimal勾稽，再复用原compare_pair，不另写盈利评分。
中点只是范围中心，实际减中点不等于市场预期差；范围端点含等号。缺实际值保留VALUE_NOT_RETAINED，
事件层为RETAINED_REVIEW_WITH_COMPARISON_GAPS，不能因其他指标成功签整项成功。
选择、完整可比、部分缺口和指标分母分别呈现；独立样本量、Brier、胜率、机会概率继续null。

仍复用原三文件读取、Decision Book NAVIGATION_ONLY、hash/blob精确绑定、局部回滚及总预算。
无新collector、源请求、运行工作流、依赖、权限、日程、通知或Watch；D联合读取自动保留现有items。
新正文显示文档时间限制、原范围、结果位置和现金/月份反例；全部材料不读取时不能代签研究采用。

Reuse：施工前重读原D2内部实现与下方已保存外部审阅，并主动检查
[Nixtla/utilsforecast的losses.py](https://github.com/Nixtla/utilsforecast/blob/main/utilsforecast/losses.py)
的cutoff/id分组、区间coverage与MAPE。此次是其当次主分支可见实现检查，不冒称固定新运行依赖或完整上游审计。
本用途不需要跨事件均值、DataFrame或预测评分，因此沿已有原子比较器加薄布局；未复制外部代码。
文档日期与精确时刻分离使用Python标准库[date/datetime](https://docs.python.org/3.12/library/datetime.html)
与[ZoneInfo](https://docs.python.org/3.12/library/zoneinfo.html)，未新增时区库。

检查包含真实保存输入、后置预告、假首发时间、乱序/不规范日期、声明时区边界、跨证券/指标/期间、
错误单位/角色/来源、虚构中点与半宽、缺值和两项局部失败，以及三事件同一原reader的装配。
旧单事件测试fixture显式选择原MU，不把生产新增条目静默变成老fixture的隐式输入。
本地局部导入对shared root/预算等依赖有明确替身，不能代替完整仓库集成；正式full/main和正常发布后
必须核同R新三文件与实际行。真实自然Quick/Brief、成熟前向期限与整条D验收仍独立。

退出通过正常PR移除两项选择及本新增布局和专属反例；原MU、共享比较器、旧来源、历史失败与底稿保留。
下面是#760原布局的依据，除本节明确扩展的选择外继续生效，不据原“仅四指标”描述重复退回新布局。

[PRE-RIGOL]: https://github.com/auguspp/decision-kernel/blob/e1a124f10d77b6e20a0cba550ad9d4bdd11fa20d/docs/readings/d2-rigol-preannouncement-2026-10-07/README.md
[PRE-YTO]: https://github.com/auguspp/decision-kernel/blob/e1a124f10d77b6e20a0cba550ad9d4bdd11fa20d/docs/readings/d2-yto-preannouncement-2026-10-07/README.md

---

## 原#760布局的实际用途

已有美光 FQ4 2026 事件审阅已在 Decision Book 的 NAVIGATION_ONLY 入口保留，
但正常读取只给链接，经营指引、实绩、误差和限制没有共同进入可恢复正文。
本批在原 Collector 增加一个可停用的薄消费者，按明确选择取回该审阅的
inputs / source-notes / README 三文件，再用原比较原语核验数值与身份。
没有复制研究档案，也不执行档案中的 calculate.py；三文件不是完整档案恢复。

首个实际输入固定在 `4d9c706d4662a30be7c72ef3b1194a29c94ef37a` 的
`docs/readings/d2-micron-fq4-validation-2026-10-05/`。
来源仍是手工保存的发行人索引表提取，未取得原 HTML/PDF、审计年报或完整电话会。
机器比较不提高这个资格。这里只重新呈现保存资料的四项差异，
不声称本次发现新的财报事实或改变原 Human WAIT / NO_ACTION。

## 比较责任：同一期间、角色、口径和时间

`operating_outcomes.compare_pair` 仅对明确的公司指引与已报告实绩计算。
证券/事件/指标/期间/会计口径/币种/单位/每股口径逐项一致才比较；
不把公司指引当券商一致预期或 AI 预测，不把收入与费用仅因单位相同相减。
原#760适配仅支持现有 RETAINED_GUIDANCE_ACTUAL_V1 四指标布局，
不是任意报表解析器或所有股票/行业的通用财务模型。

披露时间必须有时区，指引早于实绩，目标报告期结束不晚于实际披露，
实际披露不晚于该审阅留存。未成熟、未披露、未在该截止留存、缺值和
口径冲突分别输出状态及 null；不是零误差或零分。新的来源取得不能倒灌历史。
整个已保存审阅在其留存之前不进入正常阅读，避免连表格都提前泄漏后见值。

使用已有严格 Decimal 字符串和固定局部精度。输出实际减指引、绝对差异，
另给差异除以指引绝对值；后一项明确不是 MAPE，也不是以实际值为分母的误差率。
零指引时比例为 null，不塞 epsilon 或填零。负指引分母取绝对值，
不因分母符号倒转增减方向。范围端点含等号；above/within/below 不是概率覆盖率。
毛利率原字段明确 fraction 与 percent，仅此处 x100，结果单位为百分点。
报告 diluted EPS 分别比较，不将不同稀释股数当同一常量分母。
精细小数不表示原近似指引取得了更高精度。

## 可读结果与不能升级的结论

首个原事件有四项可比值：收入实际减原中点 4,229 百万美元、
毛利率约 +1 个百分点、经营费用 +918 百万美元、稀释 EPS +2.42 美元。
这四个指标属于同一个公司指引事件，不是四个独立预测样本。
原审阅中的费用抵消、周期底部/下行合同保护/增量资本回报尚未证明，
以及“算术残差不是价格/销量/产品组合因果归因”的原句一同进入正文。
正常输出不只摘取正向结果，不赋予“超预期=研究正确”的标签。

AI 预测误差、Brier、胜率、方法有效性和独立样本量均保持未建立。
没有原数字概率、可比独立样本、原方法接受与后续采用证据时，不生成这些评分。
本批计算可复查不等于经济假设已经证实，更不自动改提示、规则或风险偏好。

## 原发布、权限和失败边界

选择配置 `decision_inputs/d-operating-outcomes.json` 只有消费者选择权，
不是第二份 canonical 研究/决定登记库。每项必须绑定已有正常阅读中的
NAVIGATION_ONLY 记录，且其已核字节含精确历史审阅链接；随后才允许取回三文件。
三个文件的 ref、目录、字节数、SHA256 与 Git blob 均须匹配，不拼接不同档案版本。
配置重复同事件被拒绝，不能换 record-id 把同一事件扩成多个独立样本。

复用 Collector.source、calendar/horizon 的临时局部 source-cache 范围、
共享 publication reserve、原 root assembler 和正常 publisher。
仍使用原 API/字节上限，不提高 source 注册数、不清旧缓存、不自动重试，
也不转查其他 ref、供应商或私有服务。没有新的权限、依赖、工作流、时钟或通知。
在原 `include_reviewed_questions` 之内装配，与价格输入开关分开；
价格局部失败不能自动否定一个独立合格的经营结果审阅。

输出为 `details/research/operating-outcomes.json`，原根增加一个描述符，
README 增加可读比较与原限制。选定三文件在同 R 保存，研究/Human 原件不改。
重复读取保留原审阅时钟，只有读取时钟前移；不制造新事件、提醒或新研究。
单项失败回滚该项新文件并显示缺口，不删除其他正常阅读。
总容量不足时保持原整体读取；不会删除别的材料来让本模块勉强成功。

## 复用依据、验证与退出

内部复用：`research_comparison` 的严格数值、精确选段和重复键拒绝，
`current_state` 的根/来源身份、原 publisher 装配；既有比较器的股票主体及
forecast-to-forecast 合同保持，未把 MU 改名为 A 股或放宽旧合同。
现有一次性 MU 工作底稿作为已保存数据用途保留，不长期执行旧脚本。

官方/外部对照：scikit-learn 的 MAE/MAPE 定义用于核对绝对差异与零分母边界；
Nixtla/utilsforecast 精确 `b30fe6ab6574540fa3e858737fdba7b1d8d43450`
（v0.2.17）的 `utilsforecast/losses.py` 前150行展示 id/cutoff 分组及均值聚合。
本批借鉴角色/截止分开，不采用默认跨事件平均或引入 DataFrame 依赖。
没有复制外部代码、安装运行时依赖或声称完整算法/许可证审计。
本地已有 sklearn 1.8.0 的 MAE 对四个规范化值逐项算术交叉核验，
不是运行新第三方研究系统或证明来源真实性。

局部检查覆盖真实保存值、异币种/期间/指标/口径、范围边界、零与负指引、
未来/晚留存、缺失、篡改、跨档案拼接、权限与原文限制。
原根/预算集成检查使用真实仓库实现和显式合成 Git I/O，另验价格隔离、
source-cache 不污染、重复读取和低预算/容量回滚。
本地 import-slice 的替身不冒充完整仓库；正式 full/main、正常发布与固定 R
实际正文/来源读回仍独立验收。自然 Quick/Brief采用及长期效果不由单测代签。

停用可在正常 PR 中清空选择（明确未配置，不报告零分），
或移除薄装配、两个模块与失去消费者的专属测试/配置。
原研究、Decision Book、Git 历史、失败及其它共享比较保护继续保留。
Investment Authority=NONE。
