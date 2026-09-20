# 保存新闻与行业观察：正常读取入口 v1

本切片把 #466 的纯适配器接入原 current-state publisher。它交付已保存样本的阅读入口，不开启每日新闻或行业数据采集，不把重建当作新信号、研究准入或投资判断。

Reuse Check：#297/5747710808。复用原 `Collector.artifacts/archive/retain`、`current_state.unpack_archive`、publication reserve 和 `external_radar_observations.news_context/industry`。原件只作为数据，不执行 artifact 中的 Python、脚本或说明。没有新增依赖、工作流、外部采集 client、provider、registry 或 scheduler。

## 读取方式

先把 `read-model/current-state` 固定为 R；`current-state.json` 中 `research.external_radar` 给出本模块状态和同 R 的 HTML/JSON/config 引用。根 README 有“保存的新闻与行业观察”链接：

- `details/radar/external/index.html`：带原取得日期的新闻、公司名称命中、行业变量及缺口；
- `details/radar/external/observations.json`：原适配器重建结果、来源 ZIP 引用和精确哈希；
- `details/radar/external/source-config.json`：本次明确读取的 run/artifact 及时间窗；
- 原始 ZIP 由既有 Collector 保存到同 R 的 `sources/artifacts/`，不是 production restore。

旧 `company-reading.json`、Stock/Sector/Inbox 及 Research 记录保持原字节/语义；新内容是 sidecar，不改写旧公司投影或加入来源计数确认。公司名称匹配使用同 R 已校验的公司阅读，保存其投影身份和研究上下文，不能冒称独立证券识别或经济暴露。

## 当前显式样本

`decision_inputs/external-radar-reading-v1.json` 是小型来源配置，不是自动发现器。初始只绑定：

| 范围 | run | artifact | 捕获性质 |
|---|---|---|---|
| NewsNow | 35486102537 | 10597975192 | 2026-09-20 保存的七个窗口；不是以后每次发布的新新闻 |
| HiThink | 35486156318 | 10597645925 | 主连历史至 2026-09-18；价格从 2026-04-01，近期基差/仓单从 2026-08-01 |

run ID、workflow、branch、head SHA、attempt1、终态、archive ID/name/size/digest 均逐项绑定；不搜索 latest，不向旧成功回退。这里允许读取明确绑定的历史 push 探针，**不放宽原生产 lane 的 main/workflow_dispatch/schedule 资格**。

正常发布只读取 GitHub 已有原件，不启动 Docker、新闻抓取、HiThink、AKShare、ruptures 或模型。每源原件经原 ZIP 路径/大小/CRC 校验，再交原 #466 适配器。外部托管运行时的源码commit与镜像digest关联仍不是由本阅读器认证。

## 失败与日期

来源读取失败、过期、hash不一致或转换拒绝，分别保留该板块的 `UNAVAILABLE_OR_REJECTED`；另一板块及旧阅读不受影响。不得把缺口写成0条新闻、无变化或业务WAIT。当前 archive 原件在2026-10-20到期；沿用原 archive 资格检查，届时未取得新的合法读取来源就明确 unavailable，不自动重采或恢复。

原取得区间、来源发布时间声明和本次重建时间分开。重读同一数据不会更改 article version，也不会创建新的事件或Human待办。所有新闻标题、待核对组和公司命中仍为 CONTEXT_ONLY；没有语义分流、自动Pre或独立证据确认。

行业端保留主连、默认spot历史未确认、仓单单位UNKNOWN、日历完整性/历史PIT/公司实质性未建立。基差变化显示百分点，收益显示百分比；原始值、重算值和两条已知LC勾稽差异都保存在JSON，不为了页面更好看改源值或扩大容差。

## 接线与验收

原入口新增显式 `--include-external-radar`，要求 `--include-radar-discovery`；默认调用行为不变。现有 `current-state-read-entry.yml` 只添加这个读取flag，触发器、权限、业务凭据和生产调度不变。

仍受原 publication API/byte reserve；预算不够先报阅读缺口，不增加预算、丢弃旧产物或重复外部调用。替换根摘要时保留既有公司、概念和档案导航。新增回归复用原合成公司/行业输入和真实 native ZIP checker，完整CI不抽样、不减旧测试。

完成以 exact-head CI、正常merge、独立main CI和正常publisher中的实际同R文件读回为准。未来每日capture、行业到公司经济暴露与问题形成，仍是独立的下一产品工作；本页面不是两个Radar全链路生产上线。

AI Investment Authority = NONE。
