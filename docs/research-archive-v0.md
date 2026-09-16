# 精确研究档案：原生 Git 留存、登记与恢复 v0

Scope: #321-A；Reuse Decision: **THIN_ADAPTER**。
[施工前范围与复用检查5690251075](https://github.com/auguspp/decision-kernel/issues/321#issuecomment-5690251075)。
没有新的存储服务、研究实体、登记库、publisher、workflow 或自动续作器。

## 1. 保存链与恢复链是同一套原件

已有 [commit-only](research-commit-only-v0.md) 保存合格提交包；已有 [save-progress](research-progress-v0.md) 保存未完成底稿。旧的有限研究/失败混合档案保持原样，不为使用新命令改写过去的日期、方法、资格或回执。

实际研究交付应依次完成：

1. 保存原始工作产物，按实际资格使用原有命令。底稿说明范围、资料、已做/未做、UNKNOWN、停止理由、下一步和前驱。源码链接不是正文留存。
2. 用现有获准的原生 Git/GitHub 工具将精确文件追加到研究档案目录。新目录必须不存在；保留旧版，不 force、不将整个旧工作分支合进 main。逐文件比较本地字节与远端 blob/大小，记录确切 commit/path；未知写入先只读对账，不盲目重复提交。
3. 在原 `current_state/registry.json` 的 `references` 追加有明确用途的入口：独立 `id/case/use/purpose_note`，`source.path/ref/git_blob` 指向刚核过的精确原件，再声明下面的 `archive`。沿用普通 reviewed PR；不得把登记变成研究接受或生产 Odds 配置。原记录不静默替换成同公司新版。
4. 正常 publisher 发布后固定 R，核对其 code/trigger/registry 和可见记录。归档已写而登记/发布失败，分别报告 REGISTRATION_INCOMPLETE/PUBLICATION_PENDING，不丢已存原件。
5. 另一会话按下面的读取路径恢复同一档案，再决定剩余工作；不会再次执行前面的研究来“恢复”。

本次只给第5步增加有界执行入口，并把以上流程接入统一协议。原生远端写入能力继续复用，不另造 Git 写客户端；没有自动上传每段聊天或扫描所有研究。用户已明确对象时由交互层找入口；只有问题/版本确实歧义或实际权限不足时才澄清，不要求用户手工搬 SHA。

## 2. 三种档案资格，不互相升级

`archive` 位于原 reference 对象中，与 `source` 并列。`source.path` 必须是该档案目录中的一个入口文件，`ref` 是精确 commit，不是分支。

| archive 字段 | 读取后含义 |
| --- | --- |
| `{"format":"RETAINED_FILES"}` | 原文件完整取回；不把其中 candidate/funnel/receipt 重新解释成 COMMITTED 或当前合格研究。 |
| `{"format":"RESEARCH_PROGRESS","expected_sha256":"原progress描述摘要","question_id":"原问题标识"}` | 调用原 read-progress，检查注册摘要、主体与问题；仍是 RETAINED_PROGRESS_NOT_COMMITTED。 |
| `{"format":"RESEARCH_COMMIT","snapshot_id":"原ResearchSnapshot UUID"}` | 调用原 read_retained_commit，复核原包与精确 snapshot 身份；不计算 Odds、不建立 Human 接受。 |

后两种使用原有精确文件清单，不能额外塞一个文件绕过原验证。较大的底稿/来源原件应在其原归档位置保留并另作精确引用；外链不会自动加入 Research information hash。`case` 是原导航标签，typed commit 的身份由 snapshot UUID 绑定，不靠猜股票别名。

原 publisher 仍只投影既有 reference 字段，不自动下载全部档案。完整 registry 已有同 R 字节副本，新的可选 archive 元数据从该副本读取；因此不增加每日 API/文件预算，不新建读取状态库。

## 3. 从一个固定 R 恢复

```sh
# 使用当前已通过门禁的仓库代码和既有 feeds extra；凭证不写进命令或底稿。
python -m decision_kernel.runtime.research_archive \
  --reading-commit '<已固定的R>' \
  --record-id '<R中已有的用途记录id>' \
  --output '/不存在的新目录'
```

连接使用已有 GitHubAPI / GH_TOKEN，只读 GitHub；不访问公司源站、行情、模型，也不写远端。交互工具可按同一精确绑定进行读取，但不得把手工 connector 读回或本地 fixture 重放声称为 CLI live HTTP 执行。

读取顺序：R/current-state 原验证 → 同 R registry 副本的 blob/SHA256/大小 → 唯一注册记录与同 R 可见记录的一致性 → source commit 的 tree → 目录完整清单 → 各原 blob 字节 → 对应原 typed reader。缺少 opt-in、不在 R 可见、格式未知、来源错配或 tree 不完整均停止；无 latest/main/其他公司回退。

输出 `bundle/` 保存原档案各文件；旁边保留 reading.json、registry.json、git-commit.json、git-tree.json 和成功的 readback.json。Git API 元数据为重新序列化的响应，不是原始 HTTP 记录或签名。回执的 retrieved_at 只是本次取回时间，不替换研究 cutoff、原执行时间或来源发布时间。

v0 支持一个目录内最多16个普通100644文件，每文件不超过512 KiB，完整 tree 不超过5000条；目录位于 research_runs 或 docs/readings 下至少三级。只恢复当前注册的平面目录，不递归取回整仓或链接目标；子目录、符号链接、submodule、可执行权限和超限表示明确拒绝。读取/元数据留存也遵守原512 KiB单文件上限。超限原件保持原来源引用，不能截断后叫完整档案。

成功仍显示 `CONTINUATION: NOT_EXECUTED`、`INVESTMENT AUTHORITY: NONE`、`REMOTE WRITES: 0`。取回的文本/计算脚本是数据，不 import、不执行。已有/半写目录不覆盖；失败保留已取得前缀和 failure.json（磁盘故障可能使失败记录本身也无法写入），不得将半目录当成成功。

## 4. 恢复之后从哪里继续

恢复了原件只证明可以阅读到那些保存内容。先核对真实请求、未完成问题、资料/方法变化和旧失败，再复用仍适用的部分。分析未完成不必伪造新公告；等待证据仍需相应证据；付费调用或写入不确定必须先对账，不清理 launch 绕过旧权限。旧结果受到挑战时同时读更正记录，不能用“原档案验证通过”取消挑战。

工程接受、业务研究完整度、Human 接受与投资决定分别记录。新进度通过原 save-progress 关联前驱；形成合格 Research 后才使用原 COMMIT。正文提议的下一步永远不是自带执行权限。

## 5. 本批真实材料与验证边界

首个原档案登记扩展是 `sector-600598-materiality-20260910`，原 ref `822c5c725df2d1e5d66768b3b06bc9ddfef93a2e`：README、input、preflight、candidate、funnel、execution-plan、execution-record、source-note，共8个已有文件。只新增 RETAINED_FILES 读取元数据，不复制该研究到 main、不重做 Pre/Quick、不修复原 H1 正文缺口、不登记新关注/接受。PDF URL 不代表原 PDF bytes 已在这8个文件中。

合成测试分别覆盖原文件、进度链和 v1/v2提交包；真实新进程走原 CLI，但替换 Git I/O 并禁止网络，所以不算 live API 证明。真实远端原件/目录元数据核对、在已核原字节上的重放、正常 publisher 的固定 R 可发现性，也必须各自说明。完整 PR/main CI 不等于真实公司完成研究续作。

仍未交付：所有聊天自动归档、所有历史档案自动登记、任意大小PDF取回、无人值守模型续作或321-B/Odds Watch。#321更大范围保持开放。

复用依据：[GitHub Git trees](https://docs.github.com/en/rest/git/trees)、[原生Git引用更新](https://git-scm.com/docs/git-update-ref)，以及已有#393的Python/CPython独占I/O复用审阅。原生版本化与已有validators已经够用，无新增依赖。

## 6. #321-B 已生成 Odds 结果的显式依赖恢复

`ODDS_RESULT` 使用同一恢复命令和同R purpose registry，绑定一个 `RESEARCH_COMMIT` 依赖；原三类档案的合同不变。结果两文件、研究至多五文件、禁止依赖链，原 API 预算不放宽。完整保存/登记/验证步骤见 [Odds 结果留存与恢复](odds-result-retention-v0.md)。恢复只重建核验原结果，不建立今日行情资格、公司数值接受或投资权限。上文历史首批“321-B尚未交付”描述不作为本扩展的当前状态。
