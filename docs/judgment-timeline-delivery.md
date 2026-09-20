# 判断时间线的按需 Actions 附件交付

Status: READ-ONLY DELIVERY / EXPLICIT MANUAL DISPATCH / NO NEW JUDGMENT OR EXPOSURE RECORD.

## 用户入口

普通 `kernel-tests` 的 PR / main push **不再自动生成 Judgment Timeline 附件**。需要查看这份选定历史记录时，在仓库 Actions 中打开独立的 `judgment-timeline` workflow，选择 **Run workflow**，并在 `main` 上显式运行。成功后从 **Judgment timeline attachment** job 的 Summary 进入“下载本次时间线附件”；GitHub 自身的 Artifacts 区也显示同名附件。

附件名为 `judgment-timeline-<run_id>-<attempt>`。解压后打开 `index.html`。它仍是 `docs/judgment-timeline-v0.md` 定义的四份选定历史记录，不代表今日公司状态，没有自动扫描后续档案或新的市场数据。手动生成也没有扩大选定案例、回填 Human exposure 或制造新的 Judgment。

```text
index.html
projection.json
README.txt
build.json
sources/
  ui_inputs/judgment-timeline-v0.json
  docs/decisions/<四份明确选定的原文>
```

文件来自当前私有仓库，原文 GitHub 链接及附件下载需要相应访问权限。没有启用 Pages、公开站点、外部存储、通知或隐藏遥测。生成、上传、下载都不自动成为 Human 已阅读／同意的记录。

## 为什么从普通 CI 拆出

这份 Timeline 是固定历史记录的只读阅读面，不是每次代码变更都需要重新发布的 CI 结果。此前把它绑定到每个 main push，会重复生成语义相同的历史附件，并在普通 CI Summary / artifact 中制造不必要噪音。

现在普通 `kernel-tests` 只负责完整 blocking test 与 CI 诊断；Timeline 的远端附件交付改为专用 `workflow_dispatch`。这样保留原产品能力，同时把“何时生成一份阅读附件”恢复成显式 Human 操作。它没有 schedule，也不会因为 PR、main push、Radar、Research 或行情变化自动运行。

## 复用而不新建发布平台

专用 workflow 仍只复用现有 Timeline 生成器和 Python 标准库；压缩、上传、附件 ID/URL/SHA-256 交给 GitHub 官方 `actions/upload-artifact@v7`。没有新增发布服务、快照数据库、归档引擎或业务依赖。

workflow 只有 `contents: read`，不使用行情或其他业务 secrets，不保存 cache；checkout 不保留凭据。完整 Git history 只在这次显式生成的 job 中取得，用于核验固定历史原文关联；本地 Git 读取禁用 lazy fetch，缺失就失败。workflow 和构建脚本都要求仓库为 `auguspp/decision-kernel`、ref 为 `refs/heads/main`，并绑定本次精确 `GITHUB_SHA`。从其他 branch dispatch 会被 job 门禁跳过，不能冒充 main 生成。

参考的官方功能说明：
- https://github.com/actions/upload-artifact/tree/v7
- https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts
- https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch

## 三种身份不得合并

1. `build_commit` 是这次实际 checkout 和生成代码版本，并与 GITHUB_SHA 一致。
2. `source_commit` 是展示清单明确引用的历史原文版本，可以早于生成版本。
3. `generated_at` 只是页面生成时间，不是行情、Research 或 Human 判断时间。

薄的交付脚本 `.github/scripts/build-judgment-timeline.py` 调用现有生成器，并增加两项交付检查：生成器／清单／相关代码与本次 Git commit 的字节一致；所选原文确实存在于清单声明的 source commit，且与被选中的字节相同。不以重新计算内容哈希替代 Git commit 与文件的关联核验。

它把四份原文和展示清单复制到附件的 sources/ 后，再用现有生成器从复制品重建结果，与待上传的 projection 和 HTML 对照。失败时不上传局部页面，不覆盖旧附件；旧 artifact 不作为当前构建的 fallback。输出只写新建的 runner 临时目录，原始仓库和记录不变。

build.json 的精确文件清单覆盖 HTML、投影、说明和源文件，不包括它自身；build_hash 使用现有 canonical_hash 对去掉 build_hash 的对象计算，完整 ZIP 另由 GitHub artifact-digest 覆盖。它只证明声明的构建关联，**不是数字签名、来源真伪审查、远端上传成功证明或 Human 暴露证据**。校验时必须将 run_id、attempt、build_commit 和摘要与真实 GitHub 运行及附件元数据对应。

Summary 只有在本次生成和上传均成功、且 action 返回真实 URL/digest 后提供链接。若构建或上传失败，job/workflow 保持失败，Summary 明确不可用，不把旧页面链接作为替代。普通 CI 成功与手动 Timeline 发布成功是两个独立事实。

## 保存期限和重建

这些是可重建的阅读附件，不是永久权威状态，保留期为30天。到期不重置任何账本；从生成 commit 恢复代码和展示清单，并按固定 source commit 恢复四份原文。Git 原始记录及其版本仍为来源，附件数和生成次数没有认知语义。

安装记录中的精确代码版本后，普通现有 CLI 可以对解压后的 sources/ 再生成页面：

```bash
python -m decision_kernel.runtime.judgment_timeline \
  --source-root ./sources --output ../rebuilt-timeline
```

此命令使用新的生成时间，因此 HTML/JSON 文件字节可能变化；原文时钟和 projection_hash 不应因此改变。需要逐字节复核时，用 build.json 的 generated_at 调用现有 `build_judgment_timeline` 和 `render_judgment_timeline`，并对照 JSON、HTML 及所有文件 SHA-256。无需行情接口或浏览器网络请求。浏览器内核／字体差异仍可能改变像素布局，文件一致不等于所有浏览器视觉已验收。

## 验证边界

测试复用 `test_judgment_timeline` 的真实来源副本，在 pytest 临时目录里创建真正的本地 Git histories；不伪造生产历史，不调用源站。覆盖错误 event/branch/repository/workflow、脏代码或清单、不存在的 source commit、存在但不包含相应原文的 commit、页面写入后篡改、receipt 写入失败和旧输出不可删除。相同来源在更晚时间或新 attempt 生成只改变交付记录，不新建 Judgment 或 Outcome。

结构化测试同时确认普通 `kernel-tests` 已不含 Timeline job，专用 workflow 只有显式 `workflow_dispatch`、main 门禁、只读权限和真实 upload 成功门禁。静态 wiring 与 PR CI 仍不能替代一次真实手动 dispatch 的远端附件验收。

没有新增 Kernel entity、Episode 计数、evaluation lifecycle、Human 输入表单、自动学习、系统投资权限或第三条 canonical wake。Sector / Radar / Research 的生产验收仍独立，不能用本附件的成功替代。
