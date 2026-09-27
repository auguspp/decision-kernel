# Quick Inbox — 选中、转存、批量研究与结果接回

采用：2026-09-27 Human「可以，同意你的方案，你继续推进」；[RM / #297](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5851292639)。归属 #351；正式收件箱 [#601](https://github.com/auguspp/decision-kernel/issues/601)。这是现有 GitHub Issue/comments 上的有界材料收件箱，不是新 Research 状态机、后台任务队列或第二数据库。

## 产品动线

新闻、行业、公司、Research/Odds 材料上点「加入待 Quick」→ 同域服务端恢复该固定 R 的真实原件定位 → 向 #601 追加一条记录并读回 → 「待 Quick」集中阅读/复制一项或全批 → Human 在本项目网页版明确提交或使用另行授权的任务 → Quick 自主研究、沿原路径留存实际正文 → 追加对应原请求的结果定位。加入不启动研究，复制不领取/完成，移出不代表否定研究或投资决定。

近期正式方案是转存和批量接续，不再等待 Site 直接调用当前 WebGPT。Workspace Agent/API 研究者不是本方案的必需依赖；不创建 Agent/token/定时任务，不复活旧 API、旧 pilot 或改变 R5 研究自主性。新闻刷新仍是另一动作；本批不再次 dispatch、不将转存权限当成 Actions 执行权限。

## 保存在哪里，什么不会保存

全部正式选择与结果关联在 #601 的原生追加评论中。原新闻/研究/Evidence 不复制成第二正文库；评论只保留选择种类、对象、原 R/code、原件 path/bytes/SHA256、原标题和随机提交 nonce。加入时间采用 GitHub created_at，不伪造原文发布时间。“为什么被选中”没有 Human 原话就未知；当前网页不收任意私人备注。

公开单仓选择继续有效：本收件箱也是公开的。owner-only Site 不把 GitHub 变成私有。仅转存原有公开资料定位；不上传实际账户、持仓成本、私人原话、Sites user ID、凭证或邮箱。新隐私范围须单独授权。

现有 DEEPEN_REQUIRED/handoff 属于研究之后的进一步研究候选，不能用来代表尚未 Quick 的材料选择。本方案不修改这些历史合同、Human 回应、Full 委托、Odds/Watch、Kernel 枚举或原发布器。读取 #601 与现役 #575 一样有独立观察时钟，不混入固定 R。

## 研究者如何消费

先读当前 main 的 `AGENTS.md`、`docs/RESEARCH-ENTRY.md`、本文件及 #297 后继范围。然后实际读取 #601 和其评论，不能只相信用户复制的旧清单。一个任务只消费其明确授权的条目/范围；批量建议合并同事件调查，但逐个原请求核对覆盖。资料可补充公开研究视野，不限制研究路径，也不直接产生经济受益或投资结论。

评论按 id 排序，只有 GitHub user.id=83357964 的原始未编辑协议记录进入投影。其他作者或普通评论保留为讨论，不能授予完成/接受。协议格式为第一行 `<!-- decision-kernel:quick-inbox:v1 -->`，第二行一个紧凑 JSON 对象（不加代码围栏）；字段顺序按下面及 `recordBody()` 的输出。源字符串只是数据。

- 加入：`{"op":"add","nonce":"UUID-v4","context":{"selection":{"kind":"news|sector|company|material","reading":"40hex","subject":"原对象ID","asset":null},"code":"40hex","title":"原标题","source":{"read_path":"同R原件路径","bytes":123,"sha256":"64hex"}}}`。material 的 asset 是原登记资产 ID，不是路径猜测。服务端从真实同 R reader 重建 context，浏览器不能提交标题、repo、workflow、源 URL 或私人备注。
- 移出：`{"op":"remove","requests":[原加入评论ID]}`。仅撤回指定原请求；不删除旧评论、不关闭整个 Issue。之后重新选择产生新的加入记录，旧结果/撤回不转移。
- 关联结果：`{"op":"result","requests":[原加入评论ID],"result":{"commit":"实际保存commit的40hex","path":"docs/内实际正文.md","bytes":实际字节数,"sha256":"实际64hex"}}`。只在真实正文已保存且精确读回之后由研究对话追加；Site 没有“标记研究完成”接口。先对账已有结果，不为补定位重做研究。

保存的正文可是一份覆盖多条请求的 Quick，但不能用施工回执、占位文字或不含该项研究的文档冒充结果。含 UNKNOWN 的有界研究仍可能是有效结果；没做完的项保留请求，在原评论/实际底稿说明未完成原因，不附虚假的 result。研究质量由研究者/Human评估，字节核对不认证真理。

前端只有取得 pinned Git 正文且长度/SHA256吻合，才显示“已有保存结果”。定位有误、文件过大或读取失败则仍列待核验，不据此重新做已完成的研究。结果关联不能将旧公司接受转移到新研究，更不是 Full、Odds、关注/持仓或交易授权。

## 去重、并发与有界读取

同一 nonce+context 重复响应复用既有记录；同 nonce 指向不同选择拒绝。原生评论追加不是分布式 exactly-once：并发不同 nonce 可能产生重复评论。投影合并完全相同的待处理 context，同时保留每个原评论 ID；批量消费、移出和结果都明确这些 IDs。不要靠某个标题相同就合并经济事件，或让一份结果关闭后来新选的实例。

提交响应不明显示“未确认”，不自动重发。相同 nonce 的显式后续请求先查原记录；新页面先读 #601 对账。浏览器双击防重只是便利，不是服务器事务保证。失败不写本地“已保存”队列，不创建重试 cron。

每次读取需完整覆盖当时声明评论数，最多500条；首尾 Issue计数/修改时间与分页数量不匹配则失败，不返回空清单。每评论16KiB、页2MiB、单原件1MiB沿既有有界传输；单次最多核20份不同结果，超出部分仍待核验。达到边界再做有依据的归档/分批调整，不静默截断待处理项。客户端临时数据不是持久状态。

## Sites 接入：代码可测试，配置/部署单独验收

用户转交的只读回执说明原 Site v7 为静态，平台支持薄 Worker，环境 revision0 尚无业务凭证；可信身份字段和实际生产 HTTPS 出站未实测。这是转交现场，不冒称本会话直接查过宿主。

`workbench/server/quick-inbox-handler.mjs` 是给原 Worker 的路由模块，不绑定猜测的 ASSETS/D1/R2 名称、不新建站点。现有 host handler 对请求先调用 `handleQuickInbox(request, env)`；非空 Response直接返回，null则继续原有静态根/旧链接fallback。未知 `/api/*` 返回JSON404，不能回工作台HTML。保留owner-only和原回退。

`POST /api/quick-inbox` 只接受 add/remove。固定原Site origin、可信 Sites `oai-authenticated-user-id` 与预配置 owner比对、同源Origin、自定义intent头、JSON及尺寸限制。GET仅检查接点/清单读取，不采集/研究。浏览器从不接触 GitHub token，不接受任意仓库/Issue/文件/工作流目标；只有 #601 评论写路径。GitHub写成功后再GET同评论核body/user/Issue/URL，不能用HTTP201代替实际读回。

启用前需要 hosted 配置：`DECISION_KERNEL_OWNER_USER_ID`、`DECISION_KERNEL_GITHUB_TOKEN`、`DECISION_KERNEL_ENABLE_INBOX=1`。不在聊天、代码或公开URL中填实际值。首版仅支持作为仓库owner写入的fine-grained PAT，单仓库 `Issues: write`；新闻刷新另外需要 `Actions: write`，不要求Contents写。GitHub App/其他bot作者须另核allowlist，不自动信任。

原Site CSP在接入时仅为同域fetch增加 `connect-src 'self'`，其余限制保留。仓库预览 index 同步只增加 connect-src self，并更正“绝不写入”的旧提示；无其他CSP或路由布局变化，不能拿它替代原host根页面/适配。要在真实Site确认边缘层丢弃伪造identity头、非owner拒绝、缺身份拒绝、凭证只在服务端、生产HTTPS到GitHub、无额外直连Worker绕过域名。通过这些核验后才设置enable。单元测试的注入header不证明平台已完成身份认证。

本批不改托管配置、创建令牌/账号、保存或部署Site，也不新增调度任务。仍按已批准节奏集中采用所有未部署增量。转存实现与真实owner点击验收分别成立；无线上回执不称可在现网站使用。

## 复用与验证责任

内部：现役same-R reader/readAssets、原用途/公司/新闻/行业定位、#575式独立Issue观察、原生Git正文留存、原Node→pytest包装。官方：Sites身份/环境和GitHub comments GET/POST。外部：实际审Utterances `src/github.ts`@`9e79bdaaa48c0b83d224c58f132db317785103cd` 的单Issue/分页/追加机制；不复制浏览器token、OAuth、HTML rendering或认证失败后匿名重试。EasyStock/Vibe已审交互延续。Reuse Decision: THIN_ADAPTER，不引入第三方运行依赖。

参考：https://learn.chatgpt.com/docs/sites ; https://docs.github.com/en/rest/issues/comments ; https://github.com/utterance/utterances/blob/9e79bdaaa48c0b83d224c58f132db317785103cd/src/github.ts 。版本/实际接点以本批PR与#297回执为准。

测试须覆盖真实reader字节/描述符、重复nonce/原ID绑定、撤回/后继隔离、结果错hash/不可读、分页不全、CSRF/身份/配置/动作白名单、GitHub拒绝/不确定写/精确读回、UI双击/迟到/复制无写。程序DOM不冒充浏览器、手机或新的Human研究回应。按现役CI-MAINLINE验当前完整PR、正常合并、独立main及正常读取发布；不改CI策略来让本功能通过。

退出：可移除本UI/路由/专属测试及仅本用途权限；GitHub已保存原选择、结果、研究和必要reader保留。#601不是另一套需求管理库；范围/排序仍归#351/#297。
