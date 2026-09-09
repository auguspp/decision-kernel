# 本轮结果：远端检查点演练 + 独立配对材料

**不是新 Research 结果，不是 P0-4A 全部通过。** 本轮没有更改 main、#295 历史候选或原模型，没有新增采集器、Kernel schema、生产 workflow 或新的准入门。

## 1. 实际做过的留存演练

先落 REQUEST，再做一次保存 H1 原字节的读取/哈希校验，再落 RESPONSE 并按提交读回。随后仅删除这次试验的本地 staging 目录，再从 GitHub 的同一精确 commit 读回两个记录，重建新的本地目录并验证字节身份。

- REQUEST commit: `05768906c8fb31200848f571c975e09ba248f269`；blob `9bc7f48b252ca74d5e9b3d14dfaf591fc9f30a89`。
- 实际本地读取：2026-09-09T11:15:58.480590Z 至 11:15:58.489773Z；H1 992669 bytes，SHA256 `2ee90783405f45a177f6f3bf6e4d9955e49b5c87ab6cf604c8b1eaaed3561fc3`。这是原字节校验，不计作新的正文研究。
- RESPONSE commit: `4fc76be0eea2505e9158213c8ca6b25a1175ac12`；blob `abf12f85e0bf42c7175bc499237017106cc91c2f`。
- 删除试验 staging 后确认不存在：11:17:15.979961Z；原来源 ZIP 未删除、未修改。
- 删除后实际再次调用 GitHub.fetch_file 读取 REQUEST/RESPONSE；恢复校验完成于11:18:34.577830Z。
- 恢复 RESPONSE SHA256 `28dbaa4f01429f27752f60c1fd84deb6cf98aa70698cbc78b975be798fc26ba8`，与事先记录的字节身份一致。

**最窄结论：ACKNOWLEDGED_CHECKPOINT_READBACK_AFTER_LOCAL_STAGE_LOSS_PASS。** 这是主动删除局部临时目录后的人工编排恢复，不是进程崩溃、全部运行环境消失、自动研究续跑或平台原生遥测认证。不能修复或补证cc72丢失的六次历史日志。

接下来实际执行时沿用这套GitHub能力：宿主先保存调用意图，返回后立即保存原始结果/动作记录，精确读回确认后才继续。只有REQUEST、没有已确认RESPONSE时保留不确定动作，不自动重试、不伪造成功。是否在完整模型链中成立，仍须实际运行验收。

## 2. 两份配对输入已经做成，不是只写计划

两份独立材料包各含相同的六份原始PDF、相同的两个原始CNINFO目录、相同的来源manifest及由未改动原模型生成的schema。共同问题取自原cc72输入，未提供旧candidate、结论、路由、概率、准入回执或本对话。

对照只在task.json的user数据内追加旧的合成攻击fixture；没有修改官方PDF或证据内容。该fixture仍包含原来的神农名称，是通用指令攻击样本，不被伪装成三花披露。

实际离线检查通过：3份输入ZIP摘要/CRC；6份PDF逐份长度/SHA256；2个有限目录的issuer与计数；两个包文件名集合相同；所有共享文件逐字节相同；唯一不同文件task.json、唯一不同user字段adjacent_untrusted_text；trusted developer消息相同。没有删除良性源文，也没有复制#263的Disclosure schema。

- arm-a.zip: 1717882 bytes，SHA256 `6ae5cf436c48740ffe067fa0b15d18055b5092b8e29674c292f2ee91cb1796cb`。
- arm-b.zip: 1718253 bytes，SHA256 `7ed332cc0b7e70d4dab29ed2f12cea6edbcb8336651d56e3a160e0d4f271962a`。
- `pair-manifest.json` blob `67db3a32619af688687c566bb09f1561a6e6ea3e`。
- `paired-task-spec.json` blob `a6c56f92db6457426fa8e6fae1c0bd600a36eac9`。
- 上述两份文本已在`0d14f12fc2165030da0d6e9b0b3f9562c25dfb3f`精确读回，blob与本地字节相符。

原模型代码来自已保存的trusted-source.tar，87个文件逐一通过其原Git tree清单blob比对，安装时不改源码；schema生成使用pydantic2.13.4。没有把这个局部安装/准备检查说成新的全仓CI。二进制配对包在本轮工作区保留；本ref保存任务、计划和身份清单，**不声称二进制包已经上传到新的GitHub artifact或永久备份**。六份来源的远端原artifact引用仍保留。

## 3. 尚需独立执行能力

插件目录发现Codex Replay可用于独立回放，发现时未安装，已向Human提供连接入口。尚未调用该插件，不能从产品描述推导它支持本次要求的隔离目录、消息角色、限额或原生工具日志。连接后先核对这些能力；不足则停，不在同一会话伪装两名独立执行者。

| 层次 | 本轮状态 |
|---|---|
| 一次已确认检查点在局部staging丢失后的恢复 | 实际PASS，范围如上 |
| 配对来源与任务准备 | 实际离线检查PASS |
| 独立模型会话、相同模型配置与工具权限 | NOT_YET_VERIFIED |
| 正常/恶意模型实际输出与行为对照 | NOT_RUN |
| 完整生产Research过程留存认证 | NOT_ESTABLISHED |
| #295旧过程证明 | STILL_PARTIAL，不改写 |
| P0-4A全验收/正式Research登记 | NOT_ESTABLISHED / NOT_REGISTERED |

本轮全部是隔离评测准备与一次保存字节留存演练；源站请求、行情请求、正式Research执行、dispatch、Re-run均为0。未新增PR或CI运行，不把记录文件新增计成生产工程交付。下一步的历史行为回放即便通过，也不能代替新正式Research所需的原#291准入或倒填旧预检有效期。
