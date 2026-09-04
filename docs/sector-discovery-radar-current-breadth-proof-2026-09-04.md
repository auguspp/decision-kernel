# Sector Discovery Radar — current constituent breadth proof — 2026-09-04

Status: **REAL OPERATIONS PROOF / CURRENT-BREADTH VALUE ESTABLISHED / HISTORICAL BREADTH NOT CLAIMED / PROVIDER INDEX-ALIAS GAP FOUND / NO PRODUCTION ALERT / NO HUMAN WAKE / NO INVESTMENT AUTHORITY**  
Repository: `auguspp/decision-kernel`  
Parent decisions:

- `docs/sector-discovery-radar-frozen-pit-replay-result-2026-09-04.md`
- `docs/sector-discovery-radar-884-replay-result-2026-09-04.md`

Experiment: PR `#172` — **CLOSED WITHOUT MERGE**

## 0. Executive result

A bounded current-session proof acquired exact current constituent sets for 15 declared industry finalists and controls, then joined them to one fully paginated A-share market snapshot.

The proof establishes that current constituent breadth is useful because it distinguishes:

```text
broad participation
from
index direction dominated by a few active / high-return members
```

It also proves that current 881 parents and 884 children materially overlap. Therefore a Human-facing Sector Radar cannot independently surface both layers without hierarchical deduplication.

Final disposition:

```text
CURRENT CONSTITUENT BREADTH
= USEFUL FINALIST QUALIFIER

HISTORICAL BREADTH
= NOT ESTABLISHED / NOT CLAIMED

PARENT-CHILD OVERLAP RISK
= ESTABLISHED

PRIMARY DISCOVERY LAYER
= 90-member 881 broad universe

GRANULAR 884 LAYER
= separate challenger / decomposition

HUMAN PRESENTATION
= one economic move, with parent context and granular driver
  rather than duplicate parent and child cards

STANDARD SHANGHAI INDEX TICKER ALIAS CONTRACT GAP
= ESTABLISHED

NEXT ENGINEERING
= correct production index adapter identity semantics
+ add pure current-breadth observation contract
+ add hierarchical candidate deduplication tests
+ begin prospective shadow state-change capture only after those pass

PRODUCTION ALERT
= NOT AUTHORIZED

ATTENTION INBOX INSERTION
= NOT AUTHORIZED

HUMAN ATTENTION AUTHORITY
= NONE

INVESTMENT AUTHORITY
= NONE
```

---

## 1. Operations lineage

```text
workflow run
= 33890792134

artifact id
= 9943794625

artifact digest
= sha256:b2f7f8cf6dde0bf4fdf39c6515155341a69a0ddd261504148faa1904597e7912

result hash
= 5335a22bf2cfe8a0e9a4c509d1d2ae871e2317f4633fdcc937fe7dae2a257691

experiment head
= 40dd46e2cfa985869876b33da3d43f20e9fc696a

full repository CI
= PASS

focused experiment tests
= 5 passed
```

Acquisition result:

```text
target / qualified market session
= 2026-09-04

bounded finalists and controls
= 15

current membership responses
= 15 / 15

full-market stock snapshot
= 5,567 / 5,567 unique rows

priced rows
= 5,548

unpriced or invalid rows
= 19

snapshot pages
= 12

all page provider dates
= 2026-09-04

transport retries
= 0

constituent coverage for every tested industry
= 100%
```

The result hash was independently recomputed after download and matched the artifact claim.

The experiment workflow and its compatibility seam were not merged to `main`.

---

## 2. Data and authority boundary

### 2.1 Current membership only

The constituent endpoint returns the membership visible at capture time.

Therefore this proof may state:

```text
which companies the provider currently places in one industry
how many of those companies advanced, declined or were unchanged on 2026-09-04
current equal-weight return mean and median
current turnover and positive-return concentration
current parent-child membership overlap
```

It may not state:

```text
what the membership was on an earlier date
which stocks caused an earlier index move
historical breadth or historical index contribution
```

Required semantics remain:

```text
CURRENT_CONSTITUENT_EQUAL_WEIGHT_PROXY_ONLY
!= historical breadth
!= index contribution
!= company-level Fundamental Evidence
```

### 2.2 No research or investment authority

A broad or narrow market move may justify a causal Research question. It does not establish:

- industry earnings improvement;
- supply shortage;
- listed-company profit growth;
- owner cash;
- cheapness;
- Recommendation;
- Action.

All proof outputs retain:

```text
Research authority = NONE
Human attention authority = NONE
Investment authority = NONE
```

---

## 3. Provider standard-index ticker contract finding

The live HiThink index snapshot returned exact requested `thscode` identities, but the redundant `ticker` metadata was not uniformly the first six characters of `thscode`.

Observed safe identity fields:

| Requested `thscode` | Returned provider `ticker` |
| --- | --- |
| `000001.SH` | `1A0001` |
| `000300.SH` | `1B0300` |
| `399001.SZ` | `399001` |
| `399006.SZ` | `399006` |
| `881101.TI` | `881101` |

The existing production adapter rejects `000300.SH` because it currently assumes:

```text
returned ticker == thscode[:6]
```

That assumption is false for the observed Shanghai standard indices.

The experiment did not silently weaken the adapter. It used an explicit, evidence-producing compatibility seam with this rule:

```text
exact requested / returned thscode
= identity authority

provider ticker
= preserved metadata alias

compatibility seam
= experiment only
```

A production fix must retain exact `thscode` set validation and malformed-alias rejection while treating standard-index `ticker` as provider metadata rather than canonical identity.

---

## 4. Breadth findings

### 4.1 Broad agriculture and livestock moves were genuinely broad

| Industry | Members | Advancers | Median return | Top-3 turnover share | Top-3 positive-return mass |
| --- | ---: | ---: | ---: | ---: | ---: |
| `881101.TI 种植业与林业` | 30 | 86.7% | +1.71% | 34.3% | 37.4% |
| `881102.TI 养殖业` | 36 | 91.7% | +4.37% | 49.6% | 18.7% |

The broad-parent index moves were not produced by one or two isolated names.

For agriculture, 26 of 30 current constituents advanced. For livestock, 33 of 36 advanced, and the median constituent rose more than 4%.

This supports the descriptive statement:

```text
2026-09-04 agriculture / livestock move
= broad current participation
```

It does not establish the durability or fundamental cause of that move.

### 4.2 Shipbuilding had broad direction but concentrated leadership

```text
884183.TI 航海装备
members = 10
advancers = 10 / 10
median return = +2.31%
top-three turnover share = 84.3%
top-three positive-return mass = 64.0%
```

The direction was broad — every current member advanced — but market activity and return contribution proxy were concentrated around the leaders, including 中国船舶 and 江龙船艇.

This is more informative than either of these incomplete statements:

```text
“造船只是中国船舶一只股票带动”
“造船十只股票全涨，所以完全不拥挤”
```

The observed reality was:

```text
broad direction
+ concentrated trading leadership
```

### 4.3 Pork and chicken showed strong breadth with concentrated turnover

| Granular industry | Members | Advancers | Median return | Top-3 turnover share |
| --- | ---: | ---: | ---: | ---: |
| `884275.TI 生猪养殖` | 11 | 90.9% | +6.27% | 71.7% |
| `884276.TI 肉鸡养殖` | 7 | 100.0% | +4.37% | 75.1% |

This supports the Human observation that pork and chicken were not merely defensive proxies on one day. They were active, broad current moves within already-established multi-week paths.

Again, price breadth does not prove product-price duration, margin improvement or owner cash.

### 4.4 Tiny granular industries require denominator visibility

```text
884005.TI 海洋捕捞
members = 2
advancers = 2 / 2

884006.TI 水产养殖
members = 3
advancers = 3 / 3

884277.TI 其他养殖
members = 3
advancers = 3 / 3
```

A displayed `100% advancers` value is misleading without the denominator and concentration fields. For these tiny groups, the top-three concentration measures are mechanically 100%.

Therefore every granular breadth observation must show:

```text
member count
priced member count
coverage ratio
advancer numerator / denominator
concentration
```

It must not publish a context-free “100% breadth” badge.

### 4.5 Fading control behaved correctly

```text
881169.TI 贵金属
members = 14
advancers = 2
median return = -1.84%
index return = -1.78%
```

The earlier frozen-PIT replay had already identified 贵金属 as a long-horizon leader with sharply weakening five-day strength. Current breadth confirmed broad weakness rather than hiding behind the older trend label.

---

## 5. Parent-child overlap result

Every tested granular child was fully contained in its current broad parent:

```text
884001 种子生产
⊂ 881101 种植业与林业

884275 生猪养殖
884276 肉鸡养殖
884277 其他养殖
884006 水产养殖
884005 海洋捕捞
⊂ 881102 养殖业

884183 航海装备
884182 地面兵装
⊂ 881166 军工装备
```

Selected overlap measures:

| Parent | Child | Intersection | Jaccard | Child contained in parent |
| --- | --- | ---: | ---: | ---: |
| 种植业与林业 | 种子生产 | 10 | 33.3% | 100% |
| 养殖业 | 生猪养殖 | 11 | 30.6% | 100% |
| 养殖业 | 肉鸡养殖 | 7 | 19.4% | 100% |
| 军工装备 | 航海装备 | 10 | 12.2% | 100% |

This proves a concrete Human-surface failure mode:

```text
881 broad candidate
+ one or more 884 child candidates
→ duplicate cards for one economic move
```

Required presentation rule:

```text
one parent economic context
→ show relevant granular drivers underneath
→ do not consume separate Human-attention slots for fully contained children
```

A granular child may become the primary label when the broad parent dilutes the economically relevant move — as with 航海装备 versus 军工装备 — but the relationship and current overlap must remain visible.

---

## 6. Industry-index versus equal-weight proxy observation

For all 15 tested industries on this exact session, the reported industry-index one-day return matched the current-constituent equal-weight mean within approximately `2.2e-7`.

This is a real current-PIT observation. It is not promoted into a permanent provider methodology claim because no authoritative index-construction document was established.

The result has two implications:

1. `index return - equal-weight mean` did not add useful discrimination on this date.
2. Breadth remains useful because advancer share, median return, denominator, turnover concentration and positive-return concentration expose structure that the average return hides.

The project should retain the gap as an auditable field, but should not treat it as a mandatory production signal until more sessions establish how the provider constructs and updates these indices.

---

## 7. Pure current-breadth contract authorized next

A reusable Harness contract may now be implemented with no live provider call inside the pure calculation layer.

Minimum inputs:

```text
one exact sector identity
one current constituent set and capture timestamp
one exact completed-session sector return
one same-session stock snapshot map
```

Minimum outputs:

```text
member_count
priced_member_count
coverage_ratio
advancers / decliners / unchanged
advancer_share / decliner_share
equal_weight_mean_return
equal_weight_median_return
top_three_turnover_share
top_three_positive_return_mass_share
leaders / laggards
visible missing-or-unpriced members
current constituent-set hash
```

Required fail-closed behavior:

- duplicate or malformed constituent identity fails;
- duplicate snapshot identity fails;
- zero priced members fails;
- non-finite values fail;
- session mismatch fails;
- membership capture later than the observation capture fails;
- coverage remains explicit rather than silently dropping members;
- no historical breadth field exists;
- no Recommendation or Action field exists.

This is a Harness observation contract, not a new Kernel schema.

---

## 8. Hierarchical candidate composition authorized next

The next pure composition test should accept:

```text
broad 881 state-entry candidates
separate 884 state-entry candidates
current constituent overlap observations
```

It should produce:

```text
full auditable candidate set
+ a deterministic 0–3 shadow summary
```

Without a composite opportunity score.

Required hierarchy rules:

1. never compare or merge 881 and 884 cross-sectional percentile values;
2. fully contained child candidates do not automatically consume additional Human slots;
3. retain a child as a visible driver under the parent;
4. allow a child to become the primary label when the broad parent is not itself strong enough and the granular move is independently qualified;
5. expose denominator, breadth and concentration;
6. preserve every omitted candidate and the reason for summary compression;
7. unchanged active states do not recur as new events.

This composition remains shadow-only until prospectively evaluated.

---

## 9. Remaining blockers before a daily shadow producer

```text
production index adapter alias correction
+ pure current-breadth contract and tests
+ hierarchical parent-child composition and tests
+ exact daily state persistence / bootstrap policy
+ catalog-change policy
+ source-health / stale-last-good presentation
+ prospective T+5 / T+20 outcome capture
```

The completed proof does not authorize adding Sector Radar to the canonical Attention Inbox.

---

## 10. Final authority

```text
CURRENT BREADTH VALUE
= ESTABLISHED FOR FINALIST QUALIFICATION

HISTORICAL BREADTH
= NOT ESTABLISHED

INDEX CONTRIBUTION
= NOT ESTABLISHED

FUNDAMENTAL BELIEF CHANGE
= NO

RESEARCH ROUTE
= NO

CANONICAL HUMAN WAKE
= NO

RECOMMENDATION
= NO

ACTION
= NO

INVESTMENT AUTHORITY
= NONE
```

Central conclusion:

> **The Radar should not merely say that an industry index rose. It should show whether the current move is broad or concentrated, how many companies the claim rests on, and whether a granular child is duplicating its broad parent. That information is useful for allocating Research attention, but it still carries no investment authority.**
