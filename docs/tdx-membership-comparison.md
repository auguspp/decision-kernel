# C2：比较两次成员观察，不把当前名单回填为历史

**2026-10-02范围后继：** [Human采纳](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5950122271)后，完整历史成员角色回放为可选增强，现时发现/合格多周期比较仍必交；[当前验收与固定补采退役](c2-five-session-inputs.md)持有准确边界。下方两端成员观察的事实、时间资格与UNKNOWN不改，已有比较器和#711/#712继续复用。当前名单可用于明确标注的历史价格回看，不再要求先补齐每日成员才开展该用途；但不能把子集/端点比较当全成员历史排名、真实生效日期或因果领先。旧成果不重新签收。

2026-10-01。原 C2/P2-6 的只读消费者；[本批范围](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5930312673)。承接 #701 的历史成员缺口，不重复 K3、行业新起点或 Concept 长历史重算。AI Investment Authority = NONE。

## 能力与边界

`decision_kernel.runtime.tdx_membership_comparison` 显式比较两份已发布的 TDX 成员观察。输入是两个固定读取 R 各自的 `current-state.json` 与其声明的完整 `membership.json`，并分别提供从可信读取取得的 R 和 `reading_hash`。调用者须先通过原生 GitHub 确认这些定位；从待检查文件自己抄一个新 hash，不构成独立来源证明。本消费者不执行 Git 网络取数，也不认证调用者捏造的 ref。

每一端单独执行原 `validate_read_package`、外部 hash pin、成员文件 SHA256/bytes/Git blob、原投影与源观察绑定，再检查完整目录、完整证券代码、唯一关系和原时间/权限语义。不同日期的两个 R 是显式比较对象，不是把不同 R 的字段拼成同一次市场观察。只有原 `tdx-concept-membership-v1` 语义可以进入；不同分类、解析器版本和倒置时间不可偷偷混用。

输出保留全部目录分母、两端均出现的关系数、观察新增/移除、名称变化和目录消失。源文件顺序不作排名，概念名称不作证券或跨来源身份。一个空成员概念与该端目录根本没有概念不同。

**两端变化只证明两次保存观察不同。** `effective_change_date` 始终为空；成员实际纳入/剔除日期、观察之间是否反复变化、历史 PIT 知识和 5/20/60 日个股角色均未因此成立。同一源原件再次发布返回 `SAME_SAVED_OBSERVATION`；不同观察但相同名单也不证明整个间隔恒定。相同捕获/观察时钟下出现矛盾内容会被拒绝，而非当作新变化。

这是显式离线读能力，没有常驻状态、成员数据库、定时器、来源重试、收益重算、自动 Research/Watch 或投资排名。现有 TDX 采集、成员解析、生产读取包和 Sites 均不改。当前供货商的业务真值仍归其原来源合同；本检查不重新执行原 provider 资格化。

## 使用原件与命令

先从两个精确 R 各取 `current-state.json`，再按该根声明取同 R 的 `details/radar/tdx-concept/membership.json`。本次真实输入：

| 端点 | 精确 R | 根 reading_hash | 成员 SHA256 / bytes |
|---|---|---|---|
| 9/29 | `bc519f1c81d0eb053a18051c5bd1918bf343c456` | `69d48a900e1d39cfa648ed681145f8941e4855059b497438b26b6100b7f3de71` | `8551e298e3cbfef0dc9a6f5207b7079d06c2eeac73144927b87617010d18f360` / 903660 |
| 9/30 | `f5dd2954c5e29dea77d875c013d399e78dc7270f` | `982f79e8f21f8bfa776df7015cad795caf063dbc448e4d3557d23318dd0b5c26` | `40705d9cba1c33401b3b66112d9ee6de6deb15291b0bb58c5d3af2cd4375956b` / 903923 |

原准备代码 M=`c8521eee3e596d788ed51db1b5c45e1b0dae6f95`。9/29 R 从 #645/5889846158 恢复；9/30 数据从本轮独立固定普通 ref 得到的后一 R 恢复，读取根生成日为10/1，不改成9/30已使用。两端成员源观察时钟分别为 `2026-09-29T10:24:25.283863+00:00` 与 `2026-09-30T10:23:58.946293+00:00`。

使用包含本消费者的获准代码环境，输入文件名可自行设置，输出目录必须不存在：

```sh
python -m decision_kernel.runtime.tdx_membership_comparison \
  --before-reading before/current-state.json \
  --before-membership before/membership.json \
  --before-ref bc519f1c81d0eb053a18051c5bd1918bf343c456 \
  --before-hash 69d48a900e1d39cfa648ed681145f8941e4855059b497438b26b6100b7f3de71 \
  --after-reading after/current-state.json \
  --after-membership after/membership.json \
  --after-ref f5dd2954c5e29dea77d875c013d399e78dc7270f \
  --after-hash 982f79e8f21f8bfa776df7015cad795caf063dbc448e4d3557d23318dd0b5c26 \
  --output new-comparison
```

原有严格 JSON、安全路径与原子 create-only 双文件写入被复用。成员输入沿现有 1 MiB 上限；根沿 192 KiB，输出沿原报告每文件 512 KiB。没有扩大档案/发布上限，没有隐式选 latest、扫历史或执行保存的脚本。

## 真实结果与用途

[完整比较](readings/c2-membership-observations-2026-10-01/comparison.md)、[机器结果](readings/c2-membership-observations-2026-10-01/comparison.json)、[本地验证记录](readings/c2-membership-observations-2026-10-01/validation.json)。

269 个概念都保留；关系数 46615→46632。两端均出现 46613 条关系，观察新增19条、移除2条，涉及15个概念；另254个概念的端点目录名及成员集合相同。目录没有新增或消失。`880524 含可转债` 两端均为明确空列表，仍在269分母中，不因只按关系 groupby 而消失。

例如 ST 板块本轮观察增加 `600363.SH`，移除 `300527.SZ`、`301139.SZ`；这不是对交易所实施/撤销风险警示日期的独立认证，不能自动修正 Stock 准入。PCB 概念增加 `301389.SZ` 也不自动建立业务净受益。完整21条关系变化全部保留，不挑成功或高收益样本。

**实际用于 P2-6 的处置：** 后一名单不是前一日观察名单的无变化延长，不能把当前全成员5/20/60日收益直接称为历史成员角色。在本两端资料上，可靠交付是观察变化和明确时间资格，而非虚造生效区间。旧 #701 横截面、原 Concept 长路径和原来源失败不改。本报告不构成全成员多周期领先、完整 C 或 Human 接受。

## Reuse 与历史来源选择

- 内部：`current_state`、`identity`、`research_commit_only` 原读取/字节/写入合同；已有成员投影提供完整代码和时间资格。集合交/差复用 Python 原生集合，不自建连接算法或时序数据库。
- 开源实查：本次读取 [AKShare index_cni.py@fac1e50e](https://github.com/akfamily/akshare/blob/fac1e50ebf9b907960d6aab4c3df658559689f39/akshare/index/index_cni.py) 的 `index_detail_hist_cni` 与 `index_detail_hist_adjust_cni`，它们从国证原历史样本/调样下载读 Excel；不是 TDX 880 概念历史。没有复制其代码、调用来源或据此添加 AKShare 依赖。日期列、原始发布日期与实际采用资格仍须分别核验，不能仅凭函数名签历史 PIT。
- 官方合同：[HiThink a-share-index.md@3bca7805](https://github.com/HiThink-Tech/Financial-API/blob/3bca7805a4127ece8d81961917e740d2effac6ec/docs/api/index/a-share-index.md) 明确成分接口返回当前清单，只有指数标识参数，不能私加日期假装回溯。[Tushare index_member_all](https://tushare.pro/document/2?doc_id=335) 有纳入/剔除日期字段，但属于申万分类；不能不经实际来源资格核查就替换本 TDX/HiThink 历史。未来按对应分类的问题单独评估，而不是否定成熟轮子本身。新凭据、费用、数据权限与实际返回可靠性在本次未建立，不启动调用。
- 独立数值/分母交叉核验直接使用本机 pandas 2.2.3，沿 #701 已实读的 [merge.py](https://github.com/pandas-dev/pandas/blob/v2.2.3/pandas/core/reshape/merge.py) 与 BSD-3-Clause 许可记录。对完整目录及完整 `(concept,security)` 关系作 `outer merge / validate=one_to_one`，不是用它认证来源生效日期。未加运行依赖或第三方代码副本。

Reuse Decision: **REUSE + THIN_ADAPTER**。当前差分不需要再采购数据或自建历史成员系统；历史生效证据的缺口不能靠扩大本比较器解决，也不因当前只支持端点比较就宣称外部无可用方案。

## 验证与退出

本地新消费者26项聚焦测试通过；无网络/子进程，覆盖外部pin、错R成员、原件篡改、重复身份、空目录分母、倒置时钟、同源矛盾、不同解析器、Markdown安全、可复现与create-only。独立 pandas 首轮校验脚本错误地假定每个概念都有关系行；发现空880524后改用独立目录外连接，生产比较器原本已保留该组，并追加回归样本。该本地校验失败/修正保留，不称首轮全通过。

真实完整关系检查与两次显式命令输出逐字节一致。Python3.13.5/Pydantic2.13.4 的部分源码环境不是正式 Actions 全量环境。正式 PR、独立 main 和普通发布各按实际后继回执记录。

本三文件示例是工程结果，随代码在 Git 留存并通过 #297/本说明找回；**不是新的 Research 用途登记，不自动进入综合读取包，不宣称自然 Brief 已消费。** 原两个读取版本继续提供输入原件；本结果不复制全部原成员字节，也不替代原来源保管。退役时同步移除本消费者、专属测试、说明与示例链接；原成员/源历史及已有消费者保留。
