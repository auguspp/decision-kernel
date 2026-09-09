# P0-4B：先接一个真实公告问题，不建调度平台

需求入口：[已批准 #297](https://github.com/auguspp/decision-kernel/issues/297)。用户随后明确原生Scheduled明天账户侧再设，其余P0继续。该延后不阻塞本项，不授权从来源文字执行工具或买卖。

## 当前切片

新增 `runtime.incremental_disclosure` 仅做两件事：从一次已保存的原官方公告scan中确定性选择一个尚未保留的研究请求；将某个完成/不完整候选交给原外部候选validator及原Funnel，输出有绑定的处置。它没有行情、公告网络请求、模型调用、调度器、自动Deep、注册器或投资权限。

复用 `current_state.unpack_archive`、原 `parse_disclosure_assessment_packet`、原 canonical hash 和 `validate_external_research_candidate`。不改旧schema、预算、原#288/#291准入或Funnel，不装新依赖。不重新获取全部公司资料，不为一个ticker写一个新采集器。

初始范围是现有scan中的六家公司；每次至多选一个packet。顺序固定为披露日期、代码、原assessment_input_hash，不按标题里的指令、预期route、已知收益或资料是否容易读来选。这个原hash绑定已有Research上下文和原公告PDF/文字版本，不含后续重新抓取的时钟；因此每日扫描重现同一批材料不会制造新请求。新版本材料可形成新问题，不改写旧请求。

扫描JSON中的EXTRACTED只证明提取器返回了非空文本；乱码仍可能存在。packet完整性、正文实际可读、研究完整和判断正确不是同一件事。

## GitHub原生留存，不另造数据库

固定工作数据ref：`research-work/disclosures-v0`。tip只保存数据；始终用可信main的代码执行，绝不从工作ref读取可执行脚本。它不是生产Research注册、current-state、市场恢复源，也不能替代旧external execution catalogue。

每次开始前解析此ref一次为W，读取完整树及全部已保留packet，绑定路径和Git blob；树被截断、文件缺失/读回失败不能当空历史。第一轮仅允许明确初始化一次空工作ref，后续不能bootstrap reset。`plan` CLI只消费调用方提供的这份固定快照，不自称独立验证远端完整性或拥有全分支global lock。

对选中的原packet，使用GitHub Contents原生create-only写入：

`research_runs/candidates/incremental-disclosures/<原assessment_input_hash>/packet.json`

不要传用于覆盖的旧blob SHA，也不要用update_file替代；同路径已经存在/写结果不确定时，先读回核对，不能重复启动。同一ref同一路径的原生create-only冲突是最后的竞争检查，不因换一个execution_id绕开同一问题。调用者顺序执行，一次只启动一个；这个库不是跨账户全局运行锁。

保留packet代表该请求已有一次处理保留，不代表完成或WAIT。无输出、预检失败、输入失败、来源/预算缺口、WAIT、DROP和DEEPEN都不删除packet；后续不会自动重试它。未解决失败保持可见。真的要恢复旧请求，须明确续作许可、原失败审阅及新的输入/预算/来源边界，不能靠超时自动复活。旧天智航正式已解决handoff与这些新packet不混用，也不修改。

数据可在Git历史中留存，不自动删除或声称永久备份。工作ref不能合并进main来消灭旧历史；合格候选登记要单独走原明确接受流程。

## 实际执行顺序

1. 从原 `decision-inbox` 的成功main/attempt1运行取得 `official-disclosure-scan`，保留实际run、artifact元数据和原ZIP。原ZIP摘要/大小/身份/CRC全部用已有校验器检查。本v0不从失败扫描里猜完整packet，也不倒找旧成功冒充最新。
2. 调用 `python -m decision_kernel.runtime.incremental_disclosure plan --archive scan.zip --artifact artifact.json --run run.json --worktree <固定W的数据快照> --work-commit <W> --selected-at <实际UTC时钟> --output <新的plan.json>`。输出保留全分母、已保留、暂缓与损坏/超范围记录。零选择不是全市场quiet。
3. 原packet原字节create-only保存并精确读回。保存选择计划及run/artifact引用。此时还没有正式Research。
4. 对实际问题做有界来源预检。缺必需原件/乱码无法阅读时保存 `SOURCE_PREFLIGHT_INCOMPLETE / NOT_EXECUTED`；没有有效原输入就不伪造validator-produced EXECUTION_GAP。有限预检不保证全Web无新披露。不能拿旧市场预期或公司Human决定当本轮更新。
5. 预检合格后，沿原#291 prepare_input、精确input commitment/readback及execute_after_admission进入真实执行。输入必须用purpose=`INCREMENTAL_DISCLOSURE_PACKET`绑定保留packet的精确ref/path/blob/SHA256；source_lane=`CNINFO_INCREMENTAL`，candidate输出仍在原约束目录。同一原packet只能有一次已保留尝试，不能为逃避失败任意重新命名。
6. 预算在新输入前声明清楚。正式执行期间所有成功GitHub读回、原件读取、失败调用、查询串、重试和实际耗时都按原receipt合同计数；源正文数量不等于工具调用总数。外围输入准备/发布动作必须事前明确分开，不事后把遗漏解释成免费。使用实际工具返回/自动日志，不补造早期trace。
7. 已完成的原input/candidate用 `outcome --packet packet.json --input input.json --candidate candidate.json --output <新outcome.json>` 验证并保存。原validator给EXECUTION_GAP时没有Funnel；只有完整候选才由原Funnel决定WAIT/DROP/DEEPEN。确定性PASS不替语义审阅、真实原件、许可或正式Research登记。
8. 将真实结果及限制交回Brief/交付Issue。新增研究可以明示为候选，不偷换为已接受Research或新的canonical Human wake。Human回应继续复用既有Issue/comment与exposure/response协议；工程接续批准不凑公司研究回应样本。

## 验收边界

本实现及合成测试证明：原packet/ZIP验证、FIFO一个、全分母可读、同hash跨扫描不重复、任何旧处理保留不自动复活、原Funnel与gap形状没有第二套路由。未调用真实模型的测试不证明Research已执行或来源隔离安全。

真实P0-4B还须实际保存一次选择/保留、源预检、原准入、真实Pre/必要Quick、原候选结果、远端读回及下一轮不重复选择的回执。预检失败只能验收失败留存，不能签完整研究。5B/6B、定时通知及5–10交易日使用各自另验；不将本文档算运行证明。

## 限定的后续问题

#296的原Funnel/CI保持，液冷供货归因只归于IR而非质量回报行动方案；其全工具调用记账仍不完整，不能回填预算来认证。后续新问题应自动或完整计数，但不重跑三花或增加另一个Gate。既有A/B模型行为缺口保持P1，不拿合成例替真实隔离验收。

GitHub create/update file行为参考：https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents 。复用已安装的GitHub工具进行普通Git写入与读回；不新建HTTP授权层。
