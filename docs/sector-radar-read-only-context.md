# Sector Radar：保存市场状态总览，不新增信号通道

Status: **READ-ONLY MARKET CONTEXT / P0-2 STATE OVERVIEW + 5/20/60 WINDOW READING / NO NEW SIGNAL OR AUTHORITY**  
P0-1 schedule: **18:13 Asia/Shanghai engineering configuration merged; natural `event=schedule` acceptance tracked separately.**

## 产品边界

本页继续读取已经验证并保存的 Sector market state 与 event ledger。它回答的是：已有状态现在怎样、哪些条件仍满足、哪些近期减弱或退出、不同 5/20/60 日窗口如何排名。它**不重新运行 detector，不补写 prospective event，不改变 #277 的 qualified-change 集合，也不启动 Research。**

已有 context 在 P0-2 之前就具备完整逐行业数据：当前/前一交易日 gate、`recent_weakening`、gate exit、5/20/60 日行业/基准/超额收益与层内排名、持续区间和 ledger 事件。本项没有把这些计算重新实现成第二套状态机。

旧产品缺口在阅读组织：active 与 weakening 分区会直接展开整张行业卡，但没有可扫描的窗口索引；未 active/weakening 的行业只能进入“全部行业（按代码）”逐项寻找。因此，一个 60 日层内排名很高、但当前 gate 未满足的方向，在机器状态中完全存在，却不容易被 Human 快速发现。

P0-2 只改变 HTML renderer 的组织方式，`context.json` 的 schema、字段和值保持原合同。阅读结构变成：

```text
保存状态 / ledger
        ↓
简短状态总览（两个层级分别计数）
        ↓
NEW / ONGOING / WEAKENING + EXIT 重叠阅读
        ↓
5日 / 20日 / 60日完整层内排名浏览
        ↓
单行业详情
        ↓
market-state / ledger / context hashes
```

没有新的综合分，也没有把窗口榜当作 candidate 排名。881 与 884 始终分层浏览，平局只用证券代码做确定性展示排序。

## 四个阅读维度

### NEW

只读取 supplied ledger 在状态交易日已记录的 sector event。它不把从保存历史重算出来的 transition 补写成新的前瞻事件。

#277 的 producer `summary.md` 仍负责 0–3 首页与全部 qualified change 分组、breadth 和 leaders。context 只提示同次运行应去哪里读，不把 20 个 sector event 重称为 20 个独立变化组。

### ONGOING

`currently_gate_active` 仍是原 persistent / acceleration predicate 的当前布尔结果。页面把两个 predicate 的 `previous → current` 都写出来，避免“当前至少一个条件有效”被误写成“今天刚开始”或“两个条件都有效”。

### WEAKENING / EXIT

`recent_weakening` 完全复用既有定义：

```text
5-session change in 20d cross-sectional rank < 0
AND
5-session 20d excess acceleration < 0
```

Gate EXIT 也只表示某个既有 predicate `previous=true → current=false`。ONGOING、WEAKENING 和 EXIT 可以重叠；一个 gate 退出时，另一个仍可以有效。页面不得把这些事实压成一个互斥标签，更不能解释为基本面恶化、行情结束或卖出。

### 5 / 20 / 60 日市场表现

每个层级分别提供三个完整窗口表，直接按**已经保存的单窗口层内 `cross_sectional_rank`** 排序；不混排 881/884，不新增综合分、不限制为 top3/top10，也不改变 detector 的排名与候选集合。每一行链接到同页唯一的行业详情。

窗口表同时展示行业收益、基准收益、超额收益以及绝对/相对语言：绝对下跌但超额为正写成“下跌但相对抗跌”，不能写成上涨。滚动 20 日或 60 日收益也不是逐日连续上涨。

## 时间、持续区间和缺失事实

状态交易日、页面生成时间、可计算持续区间、ledger 首次前瞻事件和系统首次观察时间继续严格分开。

- left-censored 的持续区间显示“至少 N 个交易日”，不使用窗口外日期伪造精确起点；
- `first_recorded_event_session = null` 只写“账本未记录”，不能推出系统从未观察、从未展示或趋势从未发生；
- `system_first_observed_at` 没有记录时保持未记录；
- 页面生成时间不会把旧状态升级成今日最新状态。

本 context **不获取 breadth / leaders，也不复用旧交易日宽度**。这些只在来源、身份和交易日匹配的同次 run artifact 中阅读。原因、业务关系、持续性与公司受益没有证据时均保持 `NOT ESTABLISHED`。

## 现有 workflow 交付

`.github/workflows/sector-radar-shadow.yml` 的 manual / schedule 两种触发继续走同一个 producer。P0-2 不修改 workflow、18:13 cron、main-only / attempt1、shared-Key activity check、same-session validation、direct-next append、gap fail closed、429 stop、restore lineage、offline replay、state/cache 或 publication gate。

原成功路径保持：

```text
producer calculation
→ publication replay precheck
→ render sector-radar-run/context/index.html + context.json
→ joint read-only reading
→ complete run artifact
→ authoritative state artifact
→ cache acceleration copy
```

context 仍位于 sealed calculation inventory 之外，是计算完成后的只读投影；renderer 失败继续阻止新的权威 state artifact/cache 发布。P0-2 没有新 workflow、网站、数据库、前端框架或 provider 请求。

P0-1 自然定时验收与 P0-2 分开：P0-2 代码/历史输入验收成功，不代表已经观察到一条绑定 18:13 main SHA 的自然 `event=schedule` 生产运行。

## 2026-09-07 精确保存输入的离线阅读验收

使用原件：Sector run `34107253263`，market session `2026-09-07`；run artifact `10013384121` / `sector-radar-run-34107253263`，GitHub digest `sha256:b536adec74877527d196b48e2b1eef59a6434770a3de5f2fb8579046b4e4f0f9`；state artifact `10013384600`，digest `sha256:e154b1221fd8ecee699eca6f0390d8c9123e2624a28012a458b51a22444e3848`。本验收没有重新获取 9 月 7 日行情，也没有覆盖旧 artifact。

旧 `context/index.html` 的实际路径：

- 教育 `881178.TI` 只出现在 **881 → 全部行业（按代码）**，没有按 60 日表现快速浏览的入口；
- 煤化工 `884281.TI` 因 weakening / exit 已出现在该分区，但若想比较其中期/长期位置，仍需打开行业卡逐个查看；
- 旧页并非“没有状态能力”，缺的是可扫描的状态总览与单窗口排序。

相同保存 `context.json` 在新 renderer 中：

| 节点 | 5日 | 20日 | 60日 | gate / weakening / ledger |
|---|---|---|---|---|
| 教育 `881178.TI`（881） | +0.63%，超额 +1.71%，rank 30/90 | +3.21%，超额 +5.91%，rank 28/90 | **+16.99%，超额 +21.23%，rank 4/90** | persistent / acceleration 前后均 false；不是 recent weakening；ledger 首次事件为空 |
| 煤化工 `884281.TI`（884） | -2.23%，超额 -1.15%，rank 189/230 | +6.68%，超额 +9.38%，rank 42/230 | **+19.00%，超额 +23.23%，rank 10/230** | persistent **true→false EXIT**；acceleration false→false；recent weakening=true；ledger 首次事件为空 |

因此教育即使不在当前 active/weakening 集合，也可以从 **881 → 60日窗口**第 4 位直接找到并跳到详情；煤化工可以从 **884 → 60日窗口**第 10 位或 WEAKENING / EXIT 两条阅读路径进入。规则没有任何行业名称、代码或案例阈值。

另一个真实语义检查：化学制品 `881109.TI` 的 5 日行业收益约 **-1.05%**，基准约 **-1.08%**，超额约 **+0.04%**；新窗口语言显示“下跌但相对抗跌”，没有把相对跑赢写成绝对上涨。

原状态和 ledger 的输出字节与 state artifact 逐字节一致，历史投影只读：

```text
market-state.json sha256  = 1c90e71b42dd7408e0c63cf3719d3bcd51dbbc7a116490bf07698ee89bb6cc80
candidate-events.json     = 1b99f1e4ecd9e4ae84191ad863fbca5fddfa8ca565dc4ad74858b4425fbdf7ee
manifest.json             = 63efbf0b1c062ca7ea026fb0afa29b70f209a650adaa29885e9c3c62e27233bc
context.json sha256       = e72d569f2af99f9bf416e39d648dbad1c693fe4a005dc158171e24be1cad204a
context_hash              = 51819110279e0a4f208b983ff692373e4e639a99a8438cc8ce33aabf17dabefb
market_state_hash         = 93a4e45222e085d5e06e75848c794546c3874c1c4f0316d96a64b78dda654841
event_ledger_hash         = d37316b957117698c8e03d0b4064909fde81b90abdc77d80fe44b700b2d68b84
```

新 renderer 对该固定 `context.json` 重复输出相同 HTML。离线 Chromium 用 1280px 与 390px 宽度通过 `set_content` 实际渲染：页面级横向 overflow 为 0，60 日窗口可展开，教育/煤化工链接可跳到详情；脚本错误 0、HTTP(S) 页面请求 0。浏览器管理策略仍拒绝 `file://` 直接导航，因此这不是私有 GitHub 已登录端到端下载/打开认证。

## 测试与证明边界

新增 renderer 行为回归只测试**阅读组织**；市场事实计算仍由原 context/state/detector/audit 测试负责。覆盖：

- 零新事件但有 ONGOING；
- 非 active/weakening 行业仍可由 60 日完整层内排名找到；
- ONGOING 与 WEAKENING 重叠；
- 一个 gate EXIT、另一个仍 active；
- 绝对下跌但正超额的“相对抗跌”；
- left censor 与空 ledger 不编造时间；
- 881/884 排名分离、完整集合不截断，重叠分区计数不虚增独立对象；
- renderer determinism、原 payload 不变、无新增 overview/window schema 字段；
- breadth/leaders 缺失和旧状态 freshness 明示。

既有 #277 discoverability、publication gate、context artifact、state/ledger identity、HTML escaping、无网络/无写入测试继续由全仓 CI 执行，不删除或放松。

**READ-ONLY MARKET CONTEXT · SHADOW OBSERVATION ONLY。Human Attention / Research / Investment authority = NONE。**
