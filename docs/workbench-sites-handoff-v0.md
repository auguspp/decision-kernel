# Sites 施工通知｜Decision Kernel 只读工作台 v0.1

2026-09-26。归属 #351；代码沿 Draft PR #585，分支 `feat/workbench-readonly-20260926`。
用户已经授权本轮继续，并明确 Sites 由其在支持 Sites 的会话中手动操作。
本文件是界面接合/预览验收通知，不是 A1 全部完成、上线或投资权限。

## 可直接交给 Sites 会话的指令

请使用 ChatGPT Sites 创建 **Decision Kernel 只读工作台**。不是从头设计另一个投资平台。
先读取随附交接包的 `HANDOFF-MANIFEST.json`，取得精确源码 commit 与文件 SHA-256；
或从 `auguspp/decision-kernel` 的 PR #585 恢复明确指定的源码 commit，不能混用 main 或移动分支。
无附件时，先解析 #585 当前 head 一次并记录，再固定该 commit 读取下列文件；不要猜不存在的主干文件。

要移入同一站点目录的运行文件：
- `workbench/index.html`
- `workbench/app.mjs`
- `workbench/reading.mjs`
- `workbench/presentation.mjs`

保留相对导入，按 Sites 当前支持的方式提供静态文件和正确的 JavaScript MIME 类型。
需要宿主外壳时只作薄适配。不要重写研究方法、固定读取逻辑和数据源定义；不新建数据库、抓取器或调度器。
先跑 `node --test workbench/reading.test.mjs`（交接包附测试）并检查导入及语法；
Node 不可用则如实报告，不冒称测试通过。实际界面仍须在 Sites 预览中检查。

### 数据与权限

1. 正式后端仍是 `auguspp/decision-kernel`。每次显式刷新先从 GitHub 解析
   `read-model/current-state` 为精确 R，再固定同 R 读取 `current-state.json`、目录和原件。
   源码 commit、读取 R、包内 code_commit 是不同身份，不必相等。
2. Quick 来自 #575，健康来自 #581；它们的修改/读取时点独立于 R。
   非标准标题的补充、更正和工程记录另列，不丢弃，也不自动升级为研究结论。
3. 公司入口复用 `details/research/asset-reentry.json` 的已登记关联。
   先核目录字节/hash，再允许同 R 的嵌套文件；保留用途、前驱与原接受边界。
4. 此版只使用公开 GitHub 的 GET，不放令牌，不写 GitHub，不调用模型或行情服务，
   不自动研究、Full、重算 Odds、启用 Watch 或交易。不将静态测试样本写成实时数据。
5. 仓库公开不等于本站必须公开。首先保存版本并保持原默认受限预览，
   让用户检查后决定是否部署及访问范围。不要自动改成 Anyone on the Internet。
6. 浏览器跨域、网络或权限失败时显示 GAP，记录实际错误。
   不用任意代理、关闭安全策略、嵌入个人 Token 或转存虚构数据掩盖失败。
   若 Sites 标准外壳需要 CSP 适配，明确记录最小差异，不整体取消保护。

### 页面要求

保持注意力、研究、Odds/Watch、市场观察、系统健康五个入口，可改布局、间距、配色和中文表达。
注意力展示原已保存 Quick 与复核事实；不是新生成的全球总结。
公司目录应支持名称/证券代码/用途搜索，点击后可读真实原件并复制接续请求。
复制接续请求只是复制，不显示“已接受”“已委托Full”或“已保存回应”。
五个 Watch 中若一个无价格，应显示五个启用、四个完成判断、一个未知，而不是全部未触界。
尚未完成的持仓、完整待办、日历、全球行情和持续学习，不要画出假数据或假完成状态。
页面呈现可插拔，但不做插件市场；关闭可选视图不得删除正式资料。

### 必须实际检查

- 首次打开能显示真实 Quick/Watch 或明确缺口；原日期不被换成今天。
- 研究页能加载真实公司目录；搜索一个目录中的公司，打开一份原文，确认原文/日期/接受状态。
- 点刷新：记录刷新前后 R。没有新发布时 R 不变是正常现象，不宣称因此验证了跨版本更新。
- 同一 R 继续阅读不混入 main；补充评论仍有独立时间和出处。
- 模拟一个可选源失败、坏 hash、目录缺失：显示对应 GAP，其他独立内容仍能读。
- 关闭/打开视图、换页后快速点击不同原件：较晚返回的旧请求不得覆盖当前选择。
- 在桌面和窄屏检查导航、搜索、长中文、长路径、原文滚动、键盘焦点及复制接续。
- 来源含 HTML/script 的测试内容只能显示为文字，不执行脚本。
- 看网络请求：没有写入、付费请求、自动轮询或暴露令牌。

先完成预览和测试，未经用户查看不自动发布。每个部署 URL 都应按实际生产入口对待。
不能创建预览或某项没测到，就写明断点；不要报告为PASS。

### 交回主施工

给出 Site/预览定位、保存版本（及部署版本若实际发布）、所用源码 commit、
实际读取 R 与时点、上述检查的PASS/GAP、两张实际桌面/窄屏截图和必要错误。
若改了代码，交回修改文件或 diff，注明哪些是宿主适配；不要只在 Sites 留一个无法恢复的分叉。
不在 Sites 会话修改 GitHub主干/PR、生产任务、研究成果或此项目权限。
用户把结果带回后，主施工对账并继续 #585 的正式CI/合并/发布验收。

## 本轮工程增量与验证边界

本次继续同一PR，没有新建长期v2分支。修复原件去重丢分类、严格Quick标题吞掉补充记录的问题；
公司关联来自现有asset-reentry，而非手写映射或自动推断持仓。
Watch计数按保存的状态分开呈现；没价格、没条件结果或时点不明均不当未触界。
公司目录失败不影响独立Quick、Watch和健康；嵌套描述符在完整检查后才扩入同R允许读取集合。

测试含原15例及新增边界/回归；保留一个真实783-byte存档原件的固定SHA-256校验。
该单文件样本来自 R `3c4818dc9ad7a068febb6889f53bf2546dccfeea` 的
`sources/git/a3147841eeacb65c8cb4d4827bb7082e95bb6f63/commit.json`。
根读取包/目录测试外壳明确为合成输入，不宣称整包历史回放、真实HTTP/CORS、Sites或浏览器验收。
确切测试计数与GitHub运行身份以 #585/#297 本次执行回执为准。

没有新增依赖包、workflow、数据库或业务任务。沿用原pytest接点调用Node内置测试。
仍不重算canonical reading_hash、不认证经济真理、不自动转移Human接受。
代码检查就绪、Sites预览验收、正式CI与主干合并是独立状态；本通知不提前签收任何一个未执行步骤。

## 复用与退出

内部：同精确main的AGENTS、NEXT-PHASE-CONSTRUCTION、CI-MAINLINE，#297后继，
现有asset-reentry目录及其真实源描述符；原有档案、读取发布与Watch不重建。
外部：复用首批已保存的Luna精确恢复和gptme薄宿主/共享所有权审阅，本次不导入其源代码或守护进程。
官方增量核查（2026-09-26）：
- https://help.openai.com/en/articles/20001339-creating-and-managing-chatgpt-sites
- https://learn.chatgpt.com/docs/sites
- https://docs.github.com/en/rest/issues/comments#list-issue-comments

结论仍是THIN_ADAPTER：现有正式目录+浏览器原生模块+用户在Sites完成宿主验证。
没有证据要求另搭托管、解析器或通用插件平台。失败时回到GitHub原件/ChatGPT现有入口，不隐藏缺口。
移除workbench运行文件及专属测试即可退役此消费端；不删除任何Research/Odds/回应和历史。
Sites中得到的适配差异应交回本PR，不在站点形成第二份正式业务状态。
