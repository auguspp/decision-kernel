# 股票手动运行未开始：34043329828

本次核验的是2026-09-06T15:45:57Z发起、attempt 1、main `81ce648e140acdd35cc8249d796aecd842edde5b` 的真实手动运行；不是合成运行或后续重算。

- Run: https://github.com/auguspp/decision-kernel/actions/runs/34043329828
- Stock job: `101513884011`
- 日志明确记录 `TRIAL_PURPOSE=stock-reading`，`STOCK_MARKET_RUN_ID` 为空。
- 安装成功；`Record explicit stock reading intent` 拒绝空编号后退出2。
- 状态绑定、下载和HiThink采集全部skipped。没有HiThink请求，不能据此判断密钥有效或失效，也不能称真实数据资格失败/零匹配。
- 旧工作流随后仍执行verify，因没有request.json而失败；再执行upload，因输出目录不存在而失败。实际artifact列表为空，不能给这次运行编造附件或重建证明。

## 修复范围

保留精确Sector run要求，不设置历史run默认值，不自动搜索latest，不回退bootstrap。共享表单上标明stock-reading时必填；其他trial用途不被强制填写此字段。

空值、格式非法、自引用编号分别返回固定原因。只有原有仓库/main/工作流/attempt1身份检查通过后，才在新目录保存preflight.json、README.txt和可读index.html。无原始非法参数回显，无环境变量或密钥转存。成功init仍只创建精确request.json；语法有效不是远端来源资格已通过，后续绑定、日历/时间/身份/行情资格原样保留。

已留档才发布artifact_ready输出；工作流据此上传原有90日附件。采集skipped时不尝试股票重建；采集失败时仍保留原有离线重建尝试。init失败仍使整个run失败，不使用continue-on-error把它变绿。summary分开表示未开始、输入检查失败和上传结果，不能把诊断附件称为选股结果。

新增测试通过实际main入口、独立Python进程和原工作流summary重现空输入；正向编号、非法字符串不泄漏、原身份/重跑/目录保护及步骤条件分别覆盖。完整仓库CI以修复PR精确提交为准。

## 下一次真实验收

修复合并且主干CI通过后，从Actions的hithink-stock-dump-trial发起新的Run workflow，选main和stock-reading，明确填写已成功、仍被当前日历和时限接受的sector-radar-shadow运行编号。不是这次股票run编号，不用Re-run jobs。曾验证的33939414197只代表2026-09-04旧市场，不把它写成永不过期默认值；漏过中间完成日须qualified recovery，不桥接。

代码/测试、失败诊断留档和后续真实股票输入/附件验收分别记录。SHADOW OBSERVATION ONLY；HUMAN ATTENTION / RESEARCH / INVESTMENT AUTHORITY = NONE。无Research自动路由、第三条canonical wake、Recommendation、Action、公司判断或市场状态变更。
