# Sector Discovery Radar — HiThink acquisition proof — 2026-09-04

Status: **REAL OPERATIONS PROOF / HARNESS DATA DECISION / NO DETECTOR / NO HUMAN WAKE / NO INVESTMENT AUTHORITY**  
Repository: `auguspp/decision-kernel`  
Parent design: `docs/sector-discovery-radar-prior-art-and-v0-decision-2026-09-04.md`  
Calculation contract: `src/decision_kernel/runtime/sector_radar.py`

## 0. Executive result

Two bounded same-repository probes established the minimum live data facts needed before implementing the Sector Discovery Radar provider adapter.

```text
HiThink tag=industry catalog identities = 320
broad 881*.TI industries = 90
granular 884*.TI sub-industries = 230

one explicit snapshot request
= CSI 300 + all 320 industry identities
= 321 requested / 321 returned

three history controls
= CSI 300 / 航海装备 / 养殖业
= all reached completed 2026-09-04 session
= snapshot last_price exactly matched latest history close
```

The resulting production acquisition decision is:

```text
BROAD CROSS-SECTIONAL DISCOVERY UNIVERSE
= exact 90-member 881*.TI family

GRANULAR DECOMPOSITION
= 884*.TI only for bounded drill-down after a broad industry is shortlisted

ONGOING DAILY ACQUISITION HYPOTHESIS
= one explicit 91-code snapshot
  (CSI 300 + 90 broad industries)

HISTORY
= separate bootstrap / qualification path
= no unbounded daily 90-history fan-out

SOURCE
= HiThink only
= no market-provider fallback
```

This proof authorizes a native adapter implementation. It does **not** authorize a detector, candidate threshold, lifecycle label, Human alert, Research route, Recommendation, Action or investment authority.

---

## 1. Probe lineage

### Probe A — catalog, full batch snapshot and history coherence

```text
PR = #165 / CLOSED WITHOUT MERGE
workflow run = 33864210050
workflow job = 100995236819
artifact = hithink-sector-acquisition-budget-2026-09-04
artifact id = 9933331611
artifact digest = sha256:ae7c2ebda58e6d6fa0b82f679e52352bd7fd969a1bb33a2c9d7b6213c4e8c28e
```

The workflow existed only on the temporary branch. It was never merged to `main`.

### Probe B — catalog layer partition

```text
PR = #165 / CLOSED WITHOUT MERGE
workflow run = 33864452822
workflow job = 100995996870
artifact = hithink-industry-catalog-layers-2026-09-04
artifact id = 9933388883
artifact digest = sha256:1b42f112ccb44087e22354c5df9766f8e4cda5c53a0dd611a85d4845935ba86b
```

Catalog canonicalization:

```text
item ordering = thscode ascending
canonical JSON = UTF-8 / sorted keys / compact separators
catalog SHA-256 = 367d64660f5ef1f715ae0ef1d832a180d075ec7d6fc0a915797cbfafbd33f360
```

These are Harness operations artifacts, not Research truth or investment Evidence.

---

## 2. Catalog result

Endpoint:

```text
GET /api/a-share-index/catalog/ths-index-list?tag=industry
```

Real result:

```text
business code = 0
qualified .TI identities = 320
data timestamp = 1788518341745
request duration ≈ 1.573 seconds
```

The exact catalog split was:

```text
881 prefix = 90 identities
884 prefix = 230 identities
```

### 2.1 881 family

The `881*.TI` family contains broad, non-overlapping-enough industry groups suitable for the first cross-sectional comparison layer, including:

```text
881101.TI 种植业与林业
881102.TI 养殖业
881103.TI 农产品加工
881105.TI 煤炭开采加工
881121.TI 半导体
881145.TI 电力
881155.TI 银行
881166.TI 军工装备
881281.TI 电池
```

Count:

```text
90
```

This is selected as the production v0 broad discovery universe.

### 2.2 884 family

The `884*.TI` family is substantially more granular and includes child / sub-industry decompositions such as:

```text
884002.TI 粮食种植
884005.TI 海洋捕捞
884006.TI 水产养殖
884183.TI 航海装备
884275.TI 生猪养殖
884276.TI 肉鸡养殖
884279.TI 水产饲料
884309.TI 锂电池
```

Count:

```text
230
```

Using both 881 and 884 identities in one rank would mix parent and child industries, duplicate economic exposures and distort cross-sectional percentiles. The 884 family is therefore excluded from the broad rank and retained only for bounded drill-down.

### 2.3 Human-example mapping

The Human's observed themes map without inventing new taxonomies:

| Human observation | Broad discovery identity | Granular drill-down identities |
| --- | --- | --- |
| 农业 / 种植 | `881101.TI 种植业与林业` | `884002 粮食种植`, `884003 其他种植业`, `884004 林业` |
| 猪肉 / 鸡肉 / 养殖 | `881102.TI 养殖业` | `884275 生猪养殖`, `884276 肉鸡养殖`, `884277 其他养殖` |
| 水产 | `881102.TI 养殖业` as broad parent | `884005 海洋捕捞`, `884006 水产养殖`, `884279 水产饲料` |
| 造船 | `881166.TI 军工装备` is a broad contextual parent, not an exact economic synonym | `884183.TI 航海装备` for bounded decomposition |

The last row is deliberately cautious: `军工装备` is broader than shipbuilding. A later Radar card must show the broad group and granular driver separately rather than relabel the parent as “造船”.

---

## 3. Full industry snapshot result

Endpoint:

```text
GET /api/a-share-index/prices/snapshot
```

Explicit request set:

```text
000300.SH
+ all 320 tag=industry identities
= 321 thscodes
```

Real result:

```text
business code = 0
requested = 321
returned = 321
data total = 321
data timestamp = 1788518347000
request duration ≈ 1.243 seconds
```

Snapshot fields observed:

```text
thscode
ticker
last_price
prev_price
price_change
price_change_ratio_pct
open_price
high_price
low_price
volume
turnover
```

This proves that a single explicit batch can cover the complete formal industry catalog plus the benchmark at this PIT.

It does **not** prove that every future 321-code request will always succeed or that the provider guarantees the same maximum indefinitely. Production must validate exact requested-versus-returned identity and fail closed on partial, duplicate, malformed or stale output.

---

## 4. History coherence controls

Endpoint:

```text
GET /api/a-share-index/prices/historical
```

The probe fetched three exact histories from 2026-01-01 through the latest completed session, with 20-second inter-request pacing.

| Identity | Rows | Latest session | Latest close | Snapshot last price | Match |
| --- | ---: | --- | ---: | ---: | --- |
| `000300.SH 沪深300` | 164 | 2026-09-04 | 4548.05 | 4548.05 | YES |
| `884183.TI 航海装备` | 164 | 2026-09-04 | 3490.77 | 3490.77 | YES |
| `881102.TI 养殖业` | 164 | 2026-09-04 | 3043.893 | 3043.893 | YES |

All three histories returned:

```text
business code = 0
history timestamp = 1788451200000
adjust = null
latest completed session = 2026-09-04
```

Request durations were approximately:

```text
CSI 300 = 0.949 seconds
航海装备 = 0.969 seconds
养殖业 = 1.692 seconds
```

The exact equality between snapshot last price and latest historical close supports a qualification seam in which one completed benchmark history anchors the snapshot batch to a completed market session.

The evidence is still bounded:

- only three identities were cross-checked;
- equality at this PIT is not a provider-wide contractual guarantee;
- production normalization must keep the qualification method explicit;
- a snapshot timestamp alone is not accepted as a completed-session proof.

---

## 5. Acquisition-budget conclusion

### 5.1 Daily full-industry snapshot is practical

One catalog plus one complete explicit snapshot required two quick successful calls.

Therefore daily broad observation does not require 90 separate history requests if a trusted historical state already exists.

Likely daily shape:

```text
restore prior qualified 126-session state
→ fetch current exact 90-member catalog
→ verify catalog identity / hash policy
→ fetch one 91-code snapshot
→ fetch one benchmark history control
→ qualify snapshot against completed benchmark close and previous close
→ append exactly one new completed session
→ run pure calculation contract
```

The exact catalog-change policy remains to be implemented and tested. A catalog change must be visible; it cannot silently rewrite historical cross-sectional ranks.

### 5.2 Initial history bootstrap remains separate

The previous project PELT experiment already established that broad index-history fan-out can encounter HTTP 429, while a bounded four-request run with 20-second pacing succeeded.

This probe did not attempt 90 histories. It deliberately confirmed only three controls.

Therefore:

```text
history bootstrap
= manual / bounded / paced / all-or-nothing operation
!= ordinary daily scheduled path
```

A future bootstrap job must record every requested identity, failure, duration, history range and hash. Partial history cannot masquerade as a complete cross-section.

### 5.3 No fallback

If the catalog, snapshot, benchmark control or state fails qualification:

```text
new completed Sector Radar snapshot = NOT PUBLISHED
failure / stale status = VISIBLE
last-good artifact = reference only, explicitly stale
alternate market provider = NOT USED
```

---

## 6. Formal v0 universe decision

```text
UNIVERSE FAMILY = 881*.TI
EXPECTED CURRENT SIZE = 90
CATALOG SOURCE = HiThink tag=industry
BENCHMARK CANDIDATE = 000300.SH
GRANULAR DRILL-DOWN FAMILY = 884*.TI
MIXED 881+884 CROSS-SECTION = PROHIBITED
```

The expected size 90 is a current operations fact, not a permanent hard-coded truth. Production must read the catalog, classify it, record the exact identity set and fail visibly if the expected shape changes before a migration decision is made.

The catalog hash above is the frozen proof identity for this PIT. It must not be used to suppress a later genuine catalog change.

---

## 7. Adapter requirements authorized by this proof

The next implementation may add native Harness adapters for:

### Catalog

- validate business success and data object;
- require unique `.TI` identity and non-empty name;
- preserve source timestamp;
- compute canonical catalog hash;
- partition 881 and 884 families explicitly;
- expose unexpected prefixes rather than ignoring them.

### Snapshot

- require exact requested identity set;
- reject missing, extra and duplicate rows;
- require finite positive prices and non-negative volume / turnover;
- preserve source timestamp;
- do not infer completed session from timestamp alone;
- qualify the batch against an exact completed benchmark-history control.

### History

- require one explicit `.TI`, `.SH` or `.SZ` identity;
- require daily interval and `adjust = null` for index histories;
- validate unique ascending calendar sessions;
- reject off-calendar, future and unfinished bars;
- require response timestamp to agree with latest bar;
- require history to reach the latest completed session when used for live qualification.

### Authority

All outputs remain:

```text
Harness market observations
!= Research
!= Fundamental Belief
!= Odds
!= Recommendation
!= Action
```

---

## 8. What this proof does not authorize

```text
no candidate threshold
no EMERGING / ESTABLISHED / ACCELERATING / FADING production label
no composite opportunity score
no LLM ranking authority
no RRG production detector
no PELT / ruptures / River detector
no concept-wide 884 cross-sectional rank
no current-constituent backfill into history
no automatic Research Funnel route
no canonical Human wake
no Recommendation
no portfolio allocation
no Action
no investment authority
```

---

## 9. Disposition

```text
PR #165 = CLOSED WITHOUT MERGE
TEMPORARY WORKFLOW = NOT IN MAIN
REAL OPERATIONS EVIDENCE = PRESERVED

PHASE A PURE CALCULATION = MERGED VIA PR #164
PHASE B NATIVE HITHINK INDEX ADAPTER = AUTHORIZED NEXT
FULL HISTORY BOOTSTRAP = NOT YET EXECUTED
FROZEN-PIT SECTOR REPLAY = NOT YET EXECUTED
SHADOW DAILY PRODUCER = NOT YET AUTHORIZED
```

Central conclusion:

> **The data source can support a broad daily sector radar efficiently. The correct first comparison layer is the 90-member 881 industry family; the 230-member 884 family belongs in bounded causal drill-down, not in the same rank.**
