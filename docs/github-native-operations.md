# GitHub 原生能力：施工与维护入口

授权与本批实际采用/未验回执归 [#619](https://github.com/auguspp/decision-kernel/issues/619)，原则仍归 AGENTS。这里是操作说明，不是永久权限矩阵或第二个项目状态库。

## 事项导航：归属、执行顺序和证据分开

产品事项从 [#351](https://github.com/auguspp/decision-kernel/issues/351) 的原生子事项读取：B2 为 #620；六族 Markets 原站采用为 #621。两者恢复原 #297 批准范围，不是新建第二份路线图，也不因建立 Issue 宣称已开工/部署。

架构与工程能力从 [#508](https://github.com/auguspp/decision-kernel/issues/508) 的子事项读取：既有 Reuse Radar #511、本批 #619。#511 的既有 Phase 0 与后续授权不因关联改变。#297 仍只持有当前执行顺序；#601 是追加请求/结果记录，#581 是运行健康记录，不当作必须关闭的开发任务。

原生父子关系只表示归属，**不是 blocking，不是 Research/投资接受，父项进度百分比不是产品完成率**。仅对确有前置关系的事项设置 dependency；不能把 B2 和既有 Markets 采用人为互锁。新事项先查现有归属；不为每个观察拆工单，不批量迁移/关闭历史。发现状态不一致时恢复原件和最新回执，由 RM 解释。

## 先发现能力，不猜权限

按 AGENTS 的四层 preflight，只检查本任务相关目标，不在每次会话重跑所有安全/管理接口。优先发现 GitHub MCP All 的直接动作，原有 connector 也可服务其获准范围；工具缺失与真实拒绝分开。读取成功不证明写入已授权；未知写结果先对账。

特别更正旧权限探查：Issue/评论的 `performed_via_github_app` 描述**该记录由哪个 App 写入**，不能据旧记录断言当前 MCP 请求身份、token scope 或安装权限。`get_me` 的账号、工具面、当前操作结果各自举证。错误由 disabled 变成 403 也不独立证明所有仓库安全开关已开。旧结论保留在历史回执，不继续作为当前权限证明。

本批已用原生子事项真实写/读回；Projects、Dependabot 告警接口的403详见 #619。受限动作停在其权限边界，不新造 workflow/token/代理导出被拒绝的管理数据或历史告警。新扫描/签名工作流使用本次授权的最小 GITHUB_TOKEN 权限执行自己的新任务，不给 Sites PAT 增权。

## Dependabot：少量更新提案，不自动升级

`.github/dependabot.yml` 使用 GitHub 自带配置。根 `pyproject.toml` 的 pip 依赖与 GitHub Actions 分生态每周检查、每生态成一个普通版本更新组、最多保留1个普通版本更新 PR。安全更新不声称受这个上限约束；配置文件也不代替仓库的 security-updates 开关。

不自动合并，不跳过完整 CI，不把告警消失当安全证明。依赖 PR 按实际改动核兼容、当前包版本和原来源/方法义务；不能为机器人 PR 弱化 owner/full/evidence 条件，无法满足精确复用就按原完整验证处理。源码/脚本里的任意硬编码版本不属于“全部已覆盖”的承诺。优先同步一个更新组的相关约束，不为每个包开新治理项目。

自然检查运行、提案创建、CI兼容、合并、修复漏洞是不同结果。本说明不预先声称机器人已经产生 PR。

## CodeQL：独立维护，不加重每次施工门禁

`repository-security.yml` 只在明确 main 手动调用或每周三03:23 UTC扫描；不监听普通 PR/push，也不成为 kernel-tests 的 needs 或 required check。两个有界 job 分别分析 Python 与 JavaScript/TypeScript，使用原生 CodeQL、build-mode none，无项目安装/构建或来源/模型运行。每job最长20分钟、最多2个并行。

只给 contents/actions read 与该扫描所需 security-events write。原 SARIF 作为独立附件保存30天，即使上传失败也尽量留存；上传失败仍是真实失败。没有扫描结果/没有完成的job不能当无告警；CodeQL运行成功也不等于零问题、全仓安全或误报已裁定。只处理实际相关发现，不自动dismiss，不产生投资Attention。

旧 MCP 对历史告警的读取限制与新扫描的运行/上传分别报告。复核本次扫描可消费它自己保存的 SARIF；不是获得全历史告警读取权的替代通道。停用时删除/停用本专属workflow及无消费者测试；不修改原业务CI。

## 工作台源代码包：实际生成、签名、消费前验签

`workbench-source-bundle.yml` 仅显式 main / attempt1，输入 `code-sha` 是当前已审代码的40位SHA。生成前核当前main仍相同、该SHA最新独立main kernel-tests attempt1成功、checkout一致。只导出 `workbench/` 与本说明；原生 `git archive` 使用Git对象，不使用未提交的工作区。无来源请求或项目代码执行。

包内外的交付文件为：`workbench-source.tar`、`SHA256SUMS`、`source-manifest.json`、GitHub `attestation.jsonl`、`verification.json`，成功时另有 `verification-status.txt`。manifest是辅助定位，不代替签名证书/原run。`actions/attest` 对真实tar生成原生provenance；同任务用 `gh attestation verify` 核签名、仓库、signer workflow、main ref与精确SHA，并确认改坏的副本不能通过。

消费端还应自己验签；不能只相信别人给的 PASS 文本。示例（`M`取原请求/原run的精确代码版本，不从tar自报值接受任意来源）：

```sh
sha256sum -c SHA256SUMS
gh attestation verify workbench-source.tar \
  --bundle attestation.jsonl --repo auguspp/decision-kernel \
  --signer-workflow auguspp/decision-kernel/.github/workflows/workbench-source-bundle.yml \
  --source-ref refs/heads/main --source-digest "$M" \
  --deny-self-hosted-runners --format json
```

### 受限采用环境：可选官方离线工具，不要求管理员安装

#621 的实际采用环境曾缺少 `gh`，且 apt 的身份切换系统调用不可用；这表示原生命令没有执行，不是签名无效。不能省略验签、信任包内PASS、提升容器权限或反复安装来换绿。

同一显式源码导出可以选择 `offline-verifier=true`，在现有获准联网runner准备 `offline-verifier/`：固定官方 `cli/cli` 2.101.0 Linux amd64发布压缩包（SHA256 `9bca2d1c16825f109907a23307628a2f0698fbf99662b73a5cf0b020293072b8`，来自官方Release asset565857134）、原生TUF取得的当前 `trusted_root.jsonl`、取得时点与辅助摘要。工具包在源码tar外；不成为站点运行依赖，不安装到系统路径，不改原项目/Secret。输入默认false，原导出/签名/权限/日程不变。

生产端另用该未修改CLI、全新HOME、无token和不可用HTTP代理，执行原生离线配置并拒绝改坏字节。该配置测试不是隔离网络空间证明，更不是采用端已经验签。任一步失败保留实际失败；缺少材料或成功标记不得称工具已就绪。

采用者通过获准GitHub连接独立核原run、artifact外层bytes/digest，并核官方CLI发布校验值；可信根必须经受信传输取得并固定其来源/哈希/取得时点，不能仅凭与待验包一起出现的自报SHA256SUMS建立根信任。联网准备端的原生TUF校验和采用端的签名验证分别记录；较早取得的根不证明后续未撤销。CLI/根能用于此前已固定的原源包，**M仍取那个原源包的获准版本，不能改为工具包生成时的main**。

在允许执行官方用户态工具的Linux amd64采用环境，将已核CLI解到临时目录即可；无须apt、sudo、登录GitHub或提取PAT。保留上方仓库/workflow/ref/digest/runner约束，只给原命令增加 `--custom-trusted-root /已核路径/trusted_root.jsonl`，并用解出的 `bin/gh` 替代系统 `gh`。采用端必须实际返回成功并保留输出，再检查应用差异/页面与发布；明确禁执行或不允许传入工具时仍停止，不绕过策略。不把生产端输出替代采用端结果。

官方依据：[离线验签](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/verify-attestations-offline)、[原生可信根导出](https://cli.github.com/manual/gh_attestation_trusted-root)、[官方预编译发行包](https://github.com/cli/cli/blob/trunk/docs/install_linux.md#precompiled-binaries)。REUSE原导出与官方CLI，不自建密码学验证器/服务。停用时移除可选input/step与本段，原源码导出、签名及历史原件保留；不新增持续任务或费用。

**这是可验来历的源代码包，不是 Sites 部署包或替换整站的授权。** 原站采用仍按 #621 核真实host adapter、差异、owner-only/CSP、同源入口、Secret、回退和手机页面。签名不能证明研究正确、来源时间正确、漏洞不存在、代码被Human接受或线上已部署；Kernel原领域验证不删除。30天附件不是永久档案；需要长期保管时按现有正式归档保存原字节与签名，不只存一个会过期的URL。

## 暂不引入与退出

Projects暂不部署替代看板；没有经实际权限验证的管理写不启用Ruleset/Environment，也不为测权创建假规则。Immutable Release等真正有版本发布需求时再用，不给当前原件补造过去的生产签名。所有调用不重设现有任务、源日程或Sites PAT；本批新增的只是上面明确的工程维护安排。

回滚用正常PR移除对应配置、专属helper和失去消费者的测试，保留历史Issue/PR/run/原件；无第二canonical状态、权限服务、自动学习或交易能力。

## 复用依据

已恢复 #508/5854935905、5855392009 与 #511/5854938235：保留原生状态、按需能力检索、可审阅小改动与可退出维护义务，不安装对应治理/Agent框架。本批直接复用官方实现，未复制第三方签名/扫描引擎。

- [Dependabot 配置合同](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)
- [原生产物证明](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
- [gh attestation verify](https://cli.github.com/manual/gh_attestation_verify)
- [attest已审输入](https://github.com/actions/attest/blob/1e69f48acb82d1966a394da916b4c1698aa569d6/action.yml)
- [CodeQL init已审合同](https://github.com/github/codeql-action/blob/2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2/init/action.yml)及同commit的analyze/action.yml

实际首次运行、失败、读回与后继自然维护证据留在 #619/关联PR，不把本说明更新日作为持续运行保证。
