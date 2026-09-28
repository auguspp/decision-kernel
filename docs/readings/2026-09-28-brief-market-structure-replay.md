# 9月28日市场结构：Brief呈现回放

这是对同一份真实保存数据的**市场结构部分回放**，不是重新采集、当天第二次Quick、完整晚间Brief或新的研究结论。未在本回放核查独立#575研究正文和#581健康记录，因此不判断今晚有无Human待办、不宣称完整研究/健康消费完成。其目的，是让#645的呈现修改可以直接与原件对照，而不是只增加一条抽象写作要求。

## 默认层样稿

**医疗方向有中期改善，但不是题材普遍转强。** 通达信所存269个概念条目中，当日上涨4个，近5日上涨24个；该来源的短期广度仍弱，不能用少数方向概括全市场。

**持续强化｜医疗服务。** 近20日上涨6.33%，原有持续与加速观察条件都还成立。这不是今天才出现的新热点。当前事件型公司目录没有给出这个持续方向的成员与逐股结果，不能补列“龙头”，也尚不能据此判断哪些公司业务受益。

**新进入｜生物制品。** 相比前一保存时点9月24日，新满足了持续与加速观察条件。已关联的康希诺通过原价格观察；赛伦生物因窗口内公司行动的数据资格问题，无法完成价格判断——不是被条件否决。这里只建立了市场表达，业务受益仍未由该目录中的研究材料证实。

**强中分歧｜互联网电商；另看细分行业印制电路板。** 电商近20日仍涨5.30%，但近5日回落1.10%；印制电路板近20日仍涨14.91%，近5日回落5.40%。两者原持续观察条件仍成立，但相对加速度与各自同层名次已回落，不再包装成“今日新热点”，也不直接写成整个方向退出。

**尚缺什么：** 通达信当前只有1/5/10日观察，20/60日、长期阶段、成员重叠和完整概念→公司下钻尚未建立。这是数据/产品覆盖缺口，不靠阶段词补齐。以上都是已保存的市场表达，不是投资或Full委托。

[行业路径与持续状态](https://github.com/auguspp/decision-kernel/blob/5119b25825d2a35761d594120289d7ea06e6b823/details/sector/36408369162/context/context.json) · [通达信全部概念观察](https://github.com/auguspp/decision-kernel/blob/5119b25825d2a35761d594120289d7ea06e6b823/details/radar/tdx-concept/summary.md) · [已保存的方向与公司定位](https://github.com/auguspp/decision-kernel/blob/5119b25825d2a35761d594120289d7ea06e6b823/details/radar/company-reading.json)

## 对照依据与未验范围

这四个方向是呈现对照，不是完整机会排序或新的投资优先级。选择依据是同一保存数据中明确的新进入、持续强化和强中分歧，用来检验不同语义有没有被混写；不是后来收益筛选。第一段通达信广度用全269行计算，没有只读Top-N；行业context读取全部90个881与230个884，各自仍保留来源分类，不把两层加成320个独立机会。

<details>
<summary>原字段、计算口径与公司边界</summary>

| 原行业身份 | 近5日 | 近20日 | 近60日 | 原持续/加速条件（前→现） | 表述依据 |
|---|---:|---:|---:|---|---|
| 医疗服务 881175.TI | 2.98% | 6.33% | 21.37% | true/true → true/true | 原条件仍成立、相对加速度为正、recent_weakening=false；不是当日新事件 |
| 生物制品 881142.TI | 4.89% | 2.99% | 7.09% | false/false → true/true | 相对于明确previous_session=2026-09-24新进入；不声称此前从未出现或9/25没有变化 |
| 互联网电商 881177.TI | -1.10% | 5.30% | 5.29% | true/false → true/false | recent_weakening=true；持续条件仍真，不改成已退出 |
| 印制电路板 884092.TI | -5.40% | 14.91% | 1.21% | true/false → true/false | recent_weakening=true；884是细分族，不能与881名次混比 |

Sector的sector_return是小数，乘100后用Decimal四舍五入显示两位；不是重新跑来源/selector。短期与中期涨跌是不同窗口，不能把20日正收益写成今天上涨。既有recent_weakening的依据是相对20日超额收益加速度与同层20日名次变化同时为负，不是任意一项下降就宣判趋势失败。原连续超额收益为正的天数不被改名为整个Concept的生命周期年龄。

TDX的change_percent已经是百分数：today为4正/265负，5d为24正/245负，10d为115正/154负，均269行、无零值。每个条目现有15根历史（9/7至9/28），只提供today/5d/10d。这里统计已保存字段，不计算不存在的20/60日，也不把多个高度重叠概念当成独立机会计分。

公司定位按同R的原origins中精确行业代码和2026-09-28日期核对，不靠名称相似。生物制品→康希诺688185.SH对应CONTRACT_CHECKED_RAW_READING/OBSERVED；→赛伦生物688163.SH对应DATA_QUALIFICATION_FAILED及REPORTED_CORPORATE_ACTION_IN_WINDOW_REQUIRES_REVIEW；→泰诺麦博-U688806.SH等原保留成员没有当次Stock结果，不能与前两种状态混为一类。

另一个真实反例：体外诊断884243.TI→新产业300832.SZ已保存CONDITIONS_NOT_MET，原因是20日路径不胜原路由行业；这是条件不满足，不是缺数据。它不被挪到生物制品或某个TDX概念下。全Stock范围为6只、实际检查价格路径5只、3只通过、2只不满足、1只不可判断；不等于全市场覆盖。

本公司目录对这些案例的Research为UNKNOWN_WITHIN_READ_SCOPE，未含可读研究正文，不是“从未研究”或对#575/其他独立研究的否定。行业对应公司不等于Concept成员关系；本回放尚未证明#645要求的完整Concept→Stock下钻。旧HiThink Concept/成员详情在本R有PAYLOAD_REPLAY/PRIMARY_BINDING缺口，而独立TDX269行可读；二者不能互相冒名补齐。

</details>

<details>
<summary>固定来源、实际校验与回放边界</summary>

- 工程阅读M：`d8fedb169eaeaf825b45afb3602fe0c4d4390aa4`。
- 原数据固定R：`5119b25825d2a35761d594120289d7ea06e6b823`，根绑定同M。根检查窗口为2026-09-28T12:00:35.490152+00:00至12:02:07.730273+00:00；这是读取检查窗口，不是采集或交易时间。
- 行业市场日9/28、原previous_session9/24。TDX市场日9/28，公司Stock保存日9/28；其他来源各自日期不强行同步。

| 已实际下载的原件 | bytes | SHA256 |
|---|---:|---|
| 根current-state.json | 157600 | 58e985048785c69b68cd014880424a32856c1306f61ebe8ba2b8d61990e6b1c0 |
| details/sector/36408369162/context/context.json | 814586 | d6587e7cc3cb44fdea9bdd91dba36d19c8864bfddc4a9ed36cad733cb16114ff |
| details/radar/tdx-concept/observation.json | 108468 | 61c2ca2e3d8e293dfb5df7cd8ac3c1f8c9023ae0b8f0e1dd1e247b2b90bd190e |
| details/radar/company-reading.json | 323389 | 7202ac935d7209e6f84786002bf45503e46562eec0581f8afb9e4fb9ac69da2e |

在本地实际下载文件上使用原identity.canonical_hash核根`reading_hash=36bd7b471cdd3123df9d961657c71061a3d3bf66b4a4a8086c941727e2264870`；三份详情均与根登记的bytes/SHA256/Git blob相符，并分别重算自身context_hash/projection_hash。没有重放全部供应商原ZIP或声称全R所有详情已读。原始行情正确性、公司业务受益和源站真值不由这些hash认证。

本地环境是已下载文件的有界副本，不是完整Git checkout。本地新旧Instructions中的读取、增量、Watch、输出权限与9/25健康补充段落已逐字比较；实际原生任务采用另验；新旧完整prompt各自保存，可按原任务回退。没有新增Python/JS生产模块、自动化测试框架、数据采集、模型调用或模拟Human回应。

本回放为同一助手按真实原件做的呈现检查，不叫独立评审、自然Brief运行或Human可用性签收。原工作台未在此修改/部署；自然下一份Brief、持续使用、完整Concept v2、20/60日与成员重叠继续在#645验收，不以本页登记替代。

</details>
