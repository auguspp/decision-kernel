# 日常问题输入准备：从三个保存入口组装五组原引用

范围：#297/5757724035。Reuse Decision: **THIN_ADAPTER**。

这是原日常宿主的可选准备工具，不是新的准入门禁、来源采集器、问题生成器、
执行器或调度器。原 `stock_question_host.run_question(daily=True)` 无任何修改。

## 减少的手工步骤

原请求有 question、context、preflight、batch review、source custody 五组 SourceRef。
已保存的全批审阅本来就指向确切 question，custody 本来就指向确切 context。
因此只需提供审阅、custody、preflight 三个 `COMMIT:PATH`；准备工具从原始字节
生成它们的 SourceRef，沿原关系取回另两组，不让操作者重新输入其哈希或改写正文。
所有输入仍须事先真实生成并保存。此命令不填空白的证据、问题、原件或失败记录。

```sh
python -m decision_kernel.runtime.stock_daily_preparation \
  --code-commit "$M" \
  --batch-review "$REVIEW_COMMIT:$REVIEW_PATH" \
  --source-custody "$CUSTODY_COMMIT:$CUSTODY_PATH" \
  --preflight "$PREFLIGHT_COMMIT:$PREFLIGHT_PATH" \
  --output daily-input-draft
```

使用已有 package 的 documents/feeds/research-api extras 和只读 GitHub 访问。
所有 ref 必须为完整40位提交；示例变量须来自真实保存记录，不能把 main/latest
或题目相似的旧沃顿/广哈路径当作新的完整输入。读权限令牌仍由环境提供，不写入文件。

## 原能力的组合

顺序为：原 source_ref / 精确读取 → 原 _question_inputs → 原 daily.bind 的全批、
CNINFO PDF、原采集 artifact、逐页解析/身份检查 → 原 reviewed_question_input.prepare
与来源 recheck → 原稳定问题/容量/日额度检查 → 原 DeepSeek SDK 请求大小/格式预览。
末尾再次核对 main 与工作分支身份，避免将过程中已经变化的状态称作可继续使用。

它不调用 authorize 或 execute_after_admission，不制造 launch，也不替原宿主
执行授权判断。既有政策匹配/时间检查不等于当前授权已被授予。

成功只生成两个本地文件：

- `request.json`：原请求结构，**enabled=false，approved_egress_hash=null**；
- `preparation.json`：原准备回执、检查的精确版本、材料大小、预览摘要和重新检查期限。

失败只留下缺口回执，不输出可误认为已经就绪的请求。全部输出使用原研究保留模块的
create-only 写入。原目录存在就拒绝，不覆盖、不恢复或重试。同样不写远端 Git，
不修改 registry、主干请求、Brief，不占用日/问题 slot、不取模型 Key、不发源站或模型请求。
GitHub 的既有文件/artifact 读取与下载仍会真实发生；不是零 I/O，也不是原件重新获取。

成功名 `DAILY_INPUT_DRAFT_VERIFIED_NOT_EXECUTABLE` 特意保留资格：它不证明经济判断
正确、权限获批或未来可以免检启动。只有经原流程审阅并保存/启用的主干请求，才能在
实际启动时由原宿主重新生成 packet、核对授权、当前版本、预检时限、额度、材料与外发。
不能把这个预览 packet/hash 当成可复用的执行令牌；期限失效后不能回填时间。

## 不改变的边界

原已消费问题、失败、CNINFO/STATIC、512KiB单来源文件、448KiB上下文、512KiB提示、
4文档、原10市场日/每市场日1次、无重试/自动Deep和全部旧 validator 保持。
先前32MiB总PDF限额没有取消每文件较窄的实现限制；本工具不会拆分PDF绕过它。
只支持现有daily合同，不能把新浪沃顿报告自动升级为日常新问题。

源站资料取得、全批经济问题审阅和真正的日常输入仍须完成。当前生产请求缺少原件/
正式问题时，不能拿合成测试、准备命令存在或旧数据的零选择充当P0-A成功。

## 复用证据和测试范围

内部检查基线为6ea967365acc0f041aef1e1abdaf7a3586a54642：原host、daily、问题准备、
source successor 的保存文档接口及原native daily fixture。官方读取合同使用
https://docs.github.com/en/rest/repos/contents 和 Python pathlib/open 的排他创建语义。
公共Git/PyGithub/SDK的同能力三层审查复用 #297/5749609810：没有新依赖、传输、
解析库、第二验证器或权限系统，故无需为这个组合安装另一套框架。

回归调用真实原daily/source/admission/PDF/SDK构造能力，只在Git和模型I/O处合成。
成功草稿经单独的合成主干启用后必须由原宿主执行STOP、WAIT和必要Quick三条路径；
准备过程自身不得产生写入或模型调用。覆盖缺行、续作伪装、缺页、artifact/引用篡改、
旧根/日期已消费、main/work变化、无权限提升及原输出目录不覆盖。
本地无完整当前checkout或锁定SDK时，不将局部语法/selector检查冒称整套通过；
真实exact-head CI、独立main CI、正常发布和固定读取另以实际记录验收。
