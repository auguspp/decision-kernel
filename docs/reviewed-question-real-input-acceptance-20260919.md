# #453 真实原件输入准备验收

2026-09-19，#297/5742110963；**REUSE，无runtime/schema/workflow/依赖改动。**

## 实际通过的接点

广哈通信300711.SZ的限定历史问题已通过完整 `reviewed_question_input.prepare()`：募集资金用途限制、向全资子公司增资与集团内转款，是否能被视为自由分配现金或新增经营现金？问题仅用于输入准备验收，不在这里回答该问题或生成Pre。

真实调用时间2026-09-19T13:27:05.576063Z；结果 `QUESTION_INPUT_PREPARED_NOT_EXECUTED`。原prepare_input、输入模型、R验证与catalog未mock；Research/Pre/Quick/Deep/Odds/Action调用0，source_network_calls=0。原始档案位于commit `20fd886cfe570e2af184cd62a9e04580b38c4769` 的 `docs/readings/300711-question-input-positive-2026-09-19/`。保存原件与正式执行注册是两回事，未向执行catalog增加这条输入。

## 先声明，再检查

M=`9fb100ac330d06a3448c4ddf2a16fa12fbe6abae`，R=`ead15d17e82f9487f76e78194b465331b64bb87d`。问题声明13:16:30，Git Q=`27cb769d2ef54e3fa0231cfeffb40c84e14a17d4`实际13:17:32提交；三份库存原PDF的本轮预检13:18:21开始，13:24:36结束；preflight P=`9295e6af038851a9fd67cdb931af0eb0fd004a9d`于13:25:29保存；input.selected_at为13:27:05。不能把历史上看过的文件称为本轮首次发现；这里验证的是声明先于本次有界预检。

三份已有原件来自artifact10320565453：1225486854（募资专项报告，8页）、1225486857（子公司增资，3页）、1225554527（保荐跟踪，6页）。真实原PDF及原解析文本已在本地核对哈希、完整页数与可读表示，17页均保留；每份PDF小于512KiB。没有下载新公告或运行OCR。保荐报告只对自身陈述是primary，不代表经济真相、独立审计或签章认证。

原R的185688bytes与Stock历史原件72255bytes通过原生Git复用blob并由原CI诊断物化，没有手工拼造R或扩预算。seed仅代表保留的Git市场阅读，Git发布时间与2026-09-11市场日分开，不把问题声明当新Evidence。

## 旧研究与缺口

旧FIRST_BUSINESS_BASELINE、募资事实、终局理由挑战与追加经营审阅均保留引用。本题仅限资金性质/内部转款，不重跑旧经营问题，不继承Human接受。现有catalog中两份605296同名冲突输入亦完整保留；这个无关冲突不通过清空目录来消除。

当前实际划款、最新募投进度和全部自由现金额仍未核验；新接口不认证问题质量或同名之外的语义去重。中新赛克002912的原SOURCE_PREFLIGHT_INCOMPLETE保持原样，不因为本例成功而改写。

## 回归与验收层次

新增3项真实材料回归：原R/来源字节；完整prepare正向重放；移除必需BODY后的真实拒绝。原4382项测试不减少。11份固定数据文件位于tests/fixtures/reviewed_question_real；旧catalog输入直接复用原execution-identity夹具，不重复复制。

CI中的checked_at/current_code/commit metadata是已记录的固定历史值，回调只读精确fixture字节；不冒充CI当时live Git准入或新的原PDF解析。正向测试实际调用原函数并核对整个回执，诊断经原CI_REPORT_DIR留存。source-preflight记录的原件读取发生在交互环境；CI不重新访问或解析源站PDF。

本地77项聚焦测试通过仅为开发证据。本地树不是完整current M checkout；相关原模块的blob一致。完整exact-head PR CI、独立main CI、正常publisher/readback的实际回执另写#297，不能拿文档或局部PASS预填。

本轮交付只证明这份真实声明与来源能进入已实现的输入准备接口。没有自动问题生产/选择、Stock生产caller、正式input登记、launch admission、真实Pre或Radar→Research全自动闭环；不接Tushare/Jev/MinerU，不重开公告工程。
