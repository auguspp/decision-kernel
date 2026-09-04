# Sector Discovery Radar — full current hierarchy result — 2026-09-05

Status: **CURRENT-PIT HIERARCHY ESTABLISHED / FROZEN PARENT HINTS / CANDIDATE-TIME REVALIDATION REQUIRED / NO HISTORICAL TAXONOMY / NO HUMAN WAKE / NO INVESTMENT AUTHORITY**  
Repository: `auguspp/decision-kernel`  
Experiment: PR `#178` — **CLOSED WITHOUT MERGE**

## Executive result

The full current formal-industry catalog produced a complete and unambiguous containment hierarchy:

```text
881 broad industries = 90
884 granular industries = 230
unique 884 -> 881 full-containment mappings = 230 / 230
ambiguous mappings = 0
unmapped granular industries = 0
exact duplicate granular member sets = 0
overlap between distinct broad 881 member sets = 0
```

This establishes a mechanically viable **current parent hint** for hierarchical Radar composition. It does not establish a permanent or historical taxonomy.

## Operations lineage

```text
workflow run = 33894305778
artifact = 9945768475
artifact digest = sha256:f6471d240ce303b44cda6f1d9558e95c38e50aaf450eca86b2c1fe31dbe35cb4
result hash = 084ff551a5df98c4750c2b3d1e95c7f94dde8b6fa6205c6348eeae69515b506a
parent-hint mapping hash = 0b0b73e17da9019e4ce15af263394f0aafc5c49442c99babefbf43d15b6c6f38
catalog hash = 367d64660f5ef1f715ae0ef1d832a180d075ec7d6fc0a915797cbfafbd33f360
qualified current membership checkpoints = 320 / 320
membership capture window = 2026-09-05T00:17:53.247000+08:00 through 2026-09-05T00:36:28.849000+08:00
transient transport retries = 2
HTTP / business-code / adapter / semantic retries = 0
```

Every checkpoint hash and the final result hash were revalidated before the frozen hint file was generated.

## Pressure-case mapping

| Granular child | Broad parent | Members at capture |
| --- | --- | ---: |
| 种子生产 `884001.TI` | 种植业与林业 `881101.TI` | 10 |
| 海洋捕捞 `884005.TI` | 养殖业 `881102.TI` | 2 |
| 水产养殖 `884006.TI` | 养殖业 `881102.TI` | 3 |
| 地面兵装 `884182.TI` | 军工装备 `881166.TI` | 12 |
| 航海装备 `884183.TI` | 军工装备 `881166.TI` | 10 |
| 生猪养殖 `884275.TI` | 养殖业 `881102.TI` | 11 |
| 肉鸡养殖 `884276.TI` | 养殖业 `881102.TI` | 7 |
| 其他养殖 `884277.TI` | 养殖业 `881102.TI` | 3 |

## Parent distribution

`63` of the 90 broad industries currently have one or more granular children; `27` have none in the formal 884 catalog.

| Broad parent | Granular children |
| --- | ---: |
| 化学制品 `881109.TI` | 8 |
| 半导体 `881121.TI` | 7 |
| 专用设备 `881118.TI` | 6 |
| 通用设备 `881117.TI` | 6 |
| 化学原料 `881108.TI` | 6 |
| 农产品加工 `881103.TI` | 6 |
| 养殖业 `881102.TI` | 6 |
| 光伏设备 `881279.TI` | 5 |
| 农化制品 `881263.TI` | 5 |
| 旅游及酒店 `881160.TI` | 5 |

## Production use rule

The committed mapping is a lookup hint, not taxonomy authority:

```text
restore frozen child -> parent hint
→ check the current formal-industry catalog explicitly
→ only for a surfaced 884 candidate, fetch that child and hinted 881 parent
→ normalize both exact current memberships
→ require current child members to be fully contained in the hinted parent
→ build the existing current parent link
→ group only after revalidation
```

If catalog identity or current containment changes, automatic grouping fails visibly. The system must not silently search for a convenient replacement parent or perform a daily 320-membership fan-out.

## Authority boundary

```text
current parent hint = Harness routing metadata
historical taxonomy authority = NONE
Fundamental Belief change = NO
Research route = NO
canonical Human wake = NO
Recommendation = NO
Action = NO
Investment Authority = NONE
```

Central conclusion:

> **At the current PIT, the formal 884 universe is a clean child partition of the 881 universe. That is strong enough to support deterministic parent-child deduplication, but only when the frozen hint is checked against current candidate memberships before use.**
