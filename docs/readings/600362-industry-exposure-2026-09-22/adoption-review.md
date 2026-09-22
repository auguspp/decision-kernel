# P1-4 采用检查：声明支持不等于日常执行已经接通

固定代码 b16a87084034d6205f73f16e452c5b38a740dc48。本记录是检查结果和待落地范围，不是新的执行权限或并行框架。

1. reviewed_question_input.py 已支持 INDUSTRY_VARIABLE_OBSERVATION；prepare仍要求精确来源、先声明后预检、R绑定、必要资料与已有研究关系，并不获取正文或运行模型。
2. stock_question_host.py 有显式问题模式，但须真实问题材料、原件、精确许可和公开材料批准；不能把本底稿直接当成启动令牌。
3. stock_daily_question.bind 从 state.lanes.stock.last_qualified_result 读取已保存Stock批次，再执行 selected=observations[packet.case_id] 与Stock资格检查。当前R的六只候选不含600362.SH。
4. 原#297/comment5748820065及其冻结policy明确只涵盖合格Stock批次。通用声明新增Industry标签没有同时扩展这个日常执行范围。

因此本样本不能靠添加Stock候选、伪造价格资格、换question/execution key或改写旧许可来进入日常调用。这是产品接线/执行范围缺口，不是公司不值得研究。P1的工程授权不等于旧Stock专属许可文本已经变化。

## 复用优先的接续方案

在现有宿主中为已批准P1 Industry范围增加明确的原生批次绑定：行业原run/独立任务/原件、完整声明的观察范围、逐项处置、选定公司的经济暴露依据。不得假借Stock验证器或将Industry来源混入881/884分类。

复用原资料保管、声明式必要来源、启动时准入和同一work ref/日/问题消费机制。非Stock入口如启用，应与原10日/每市场日最多1次政策共享上限，不能每增加一种Radar就新建一套配额；原已消费日期和失败也不能重置。来源目标日不能单靠抓取日期推断。

对冻结的付费执行许可，显式核定是否纳入Industry来源及必要更新类；未落实前不开启新的自动/模型调用。当前只是提出这一窄范围接续，并未修改policy、生成许可hash或声称它已获独立批准。

## 本轮停点

已保存具体经济问题及必要补证，不创建假的 input/preflight/custody/launch/funnel。通用输入准备未运行，正式日常调用未运行，自动日常Industry采用仍未完成。未重建provider、Question registry、scheduler或数据库。

来源：同M src/decision_kernel/runtime/reviewed_question_input.py、stock_daily_question.py；docs/reviewed-question-input-v0.md、stock-question-host-v0.md；#297/comment5748820065。后者的scope原文由本轮重新读取，不以聊天记忆替代。
