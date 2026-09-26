# Sites v3 接入回执对账与下一验收点

2026-09-26。归属同一 Draft #585；原开工授权 #297/5836374143，本轮审阅入口 #585/5841677410。范围为返回材料对账、已证明的环境错误修复和原生测试接点，不新增产品后端、权限、费用或调度。

## 返回身份与可核查材料

用户返回 `Decision-Kernel-Sites-acceptance-v3.md` 与同名 ZIP；通过 Files/Library 取得原件，非从另一会话 sandbox 路径推测。ZIP 141692 bytes、17 个成员，SHA256 `924ca7780d07c6695e457f1a2ab4a58fb4ed7d0b0f36992d15d40a3e43f53082`，CRC 通过。原 Markdown SHA256 `7053f5a0270ff013d0d6204fcafcd1f05797407f6403b4860528512e663d67b5`。原材料保留在用户交付文件中；本文是对账，不冒充重新执行 Sites。

- 原 Site：`decision-kernel-progress`；project ID `appgprj_6aae41ff34688191a97e94d4c12f4832`。
- v3 保存 ID：`appgprj_6aae41ff34688191a97e94d4c12f4832~appgver_e9f14a10b49081919be935d2db062b2d`；Sites 源码 `4f6c2650479c0dce3ab8e528a4dcde1c9ae727c0`。
- GitHub 交接 H：`f5b6d15b69de655758bdd135a3c679c30c792965`；返回 R：`3c4818dc9ad7a068febb6889f53bf2546dccfeea`；包内 M：`c847b4ad6fefa4b5d3c02536b4d02866a7c92258`。
- 回执记载 v3 未部署、无新用户预览 URL，原线上 v2 和仅 owner 的访问范围未改。本次没有访问或变更线上站点，不能把这些记录扩大为当前运行状态的重新验证。
- 保存构建包 68 文件/1802240 bytes/SHA256 `8b5bc556e9b48b98fb586cddfd9dacd2cc1f4f68c6d94938a7f39ebeb271cb21` 仅由回执列出；该完整构建包不在此次 ZIP 内，未独立恢复。

本次已读两份 diff、版本/适配清单、原生测试记录、请求记录、离线结果和两张截图。将 `workbench-adaptation.diff` 对固定 H 源码以 fuzz=0 还原，四个运行文件的 bytes/SHA256 均与返回清单一致：app/presentation 未改；index/reading 有差异。index 的返回文件 SHA256 `32fb5344f4558fe5d4afdddc1ada809efa054294f9b9d26951d9b073fbfff1c5`，reading 为 `2a02407aedf1e3f55ede859774d6c7077a3a6dbf5531a978dd7e7d9eb7930b06`。

## 验收裁定

采用原 Sites 会话有范围的执行证据：根读取、独立 Quick/健康、补充记录、保存 Watch、同 R 刷新、入口及视图开关、健康/目录缺失故障隔离、文字不执行、已测桌面/390px 布局。截图审阅不能替代本会话重新点击或网络验证。

以下继续未验：浏览器目录与原件成功核验、公司搜索/原文滚动、复制、坏 hash、慢请求竞态、真实跨 R 更新、生产 MIME/CSP。首次与刷新 R 相同不证明跨版本切换。27 项原生测试重复跑两次仍是同一集合，不是54项。

原回执的 Node 离线结果记载29个公司关联与一份4295-byte原件核验成功，属于该次结果。`qa/replay.mjs` 所引用的 current-state.json、asset-reentry.json、provisional-odds.json 没有随 ZIP 提供，因此本次未独立重跑那条真实资料回放，不用摘出的结果对象重造原始字节。

## 同批采用的修复与保留

1. 采用 Sites 明确缺少 Web Crypto 的失败语义，公共 reading.mjs 检查 digest 是否可调用，保留 SHA256/长度/同 R/先校验再登记的边界。不加入纯 JS 替代算法，不放宽 CSP，不使用代理或忽略证书。
2. 复用原 pytest 接点，显式 `--test-reporter=tap`，检查全部30项且失败/取消/跳过/todo均为0；添加 presentation 语法检查。旧 Sites 临时 `NODE_OPTIONS=--test-reporter=tap` 不再需要。若残留报告器覆盖则明确拒绝并提示清理该临时设置，不静默修改调用者环境。
3. 新增3项原生环境回归：缺 crypto/subtle/digest、目录失败不扩大可读范围且不吞独立结果、digest调用失败。仅测试进程模拟能力缺失，不更改真实浏览器安全设置。
4. Sites 布局、返回工程首页和原 Site 外壳仍由其宿主代码拥有，原 diff/哈希作为适配记录保留。本次不覆盖已保存 v3 的 index，不把整个 Sites 工程复制进 Kernel；本批 app/presentation/index 无改动。未来更新共享读取模块时保留这些已验证宿主差异。

本地 Node22.16.0/Python3.13.5：旧接点在显式 spec 报告模式复现失败；新环境回归在旧读取代码中2失败/1通过，修复后全部30项通过；pytest包装1通过（内含同30项），无隐藏跳过。临时 NODE_OPTIONS 与命令行报告器重复的中间失败保留，现为明确配置错误。不是本次原生Node24运行、真实浏览器、全仓CI或main合并证明。精确提交和远端检查另记 #585，不在文件内自引。

## 最佳实践依据和下一步

内部：原读取及pytest接点、实际用户回执。外部机制：沿用本批 Luna/gptme 的精确恢复、职责单一与薄适配；不因一个环境限制引入框架。官方本轮核查：
- https://www.w3.org/TR/webcrypto/ ：Crypto.subtle标注SecureContext。
- https://w3c.github.io/webappsec-secure-contexts/ ：顶层/祖先上下文影响安全状态；不能仅看内层URL或把所有HTTP一概判断为不可信。
- https://nodejs.org/download/release/v24.19.0/docs/api/test.html ：Node23起非TTY默认改为spec，原生支持显式TAP。
- https://help.openai.com/en/articles/20001339-creating-and-managing-chatgpt-sites ：保存与部署分开，每个部署URL是生产URL。

首选在 Sites 支持且不改变线上版本的安全预览里记录 `location.protocol`、`isSecureContext`、`typeof crypto?.subtle?.digest`，再测真实目录/原件/复制。不绕过此前浏览器管理员拒绝，不猜测预览地址或假设iframe内HTTPS必然安全。

如果该宿主只有HTTP内部预览，不继续重复无效操作；向Human一次说明：需要将核定后继版本更新到原仅本人可访问的站点，保留v2回退、不扩大访问范围，才能做实际HTTPS验收。这是建议，用户返回“已保存未部署”本身不是部署许可。未经同意不部署，不把v2链接冒充新预览。

源码接合、保存版本、部署、生效访问控制、真实浏览器检查、正式PR全量CI/main发布分别记账。本次不宣布A1完成，不推进Full/Odds/交易或修改任何自动任务。后继受限部署成功也只是只读试用，不代表整个工作台或长期学习完成。
