# Sector Discovery Radar — frozen-PIT replay result — 2026-09-04

Status: **REAL FROZEN-PIT REPLAY / PHASE C PARTIAL PASS / BROAD 881 USEFUL BUT INCOMPLETE / NO PRODUCTION ALERT / NO HUMAN WAKE / NO INVESTMENT AUTHORITY**  
Repository: `auguspp/decision-kernel`  
Formula under test: `sector-rs-5-20-60-persistence126-v0`  
Formula / adapter base: `main@c85b55886a59bc75c9ab84be9bd567aecf61ac64`  
Experiment: PR `#168` — **CLOSED WITHOUT MERGE**

## 0. Executive result

The first full frozen-PIT replay of Sector Discovery Radar v0 produced a **partial pass**, not a general validation.

```text
90-member broad 881 industry universe
+ CSI 300 benchmark
+ exact 5 / 20 / 60-session relative path
+ rank change
+ persistence / trend age
+ turnover pulse
```

was sufficient to surface the broad agriculture and livestock moves before the final September acceleration and to state how old those moves already were.

It was not sufficient to discover every economically narrower theme. The broad `881166.TI 军工装备` parent never produced the same sustained cross-sectional signal, while the bounded granular `884183.TI 航海装备` path was positive and accelerating. A broad-only 881 lane would therefore repeat part of the Human's original failure for shipbuilding-like themes.

The replay also tested one transparent 0–3 compression rule. Its T+20 follow-through was encouraging, but its weak T+5 behavior and retrospective construction do not justify production adoption.

Final disposition:

```text
PHASE C BROAD 881 REPLAY
= PARTIAL PASS

EARLY DISCOVERY
= DEMONSTRATED FOR AGRICULTURE / LIVESTOCK

TREND-AGE VISIBILITY
= DEMONSTRATED

BROAD-ONLY SHIPBUILDING COVERAGE
= FAILED

THREE-SESSION TOP-QUARTILE RULE
= RETROSPECTIVE CHALLENGER ONLY
= NOT A PRODUCTION THRESHOLD

PHASE D PRODUCTION ALERT
= NOT AUTHORIZED

NEXT EVIDENCE NEEDED
= separate 884 cross-sectional challenger
+ current breadth for bounded finalists
+ shadow-only state-change producer

HUMAN ATTENTION AUTHORITY
= NONE

INVESTMENT AUTHORITY
= NONE
```

---

## 1. Fail-closed experiment lineage

The experiment deliberately preserved failures rather than retrying until a favorable result appeared.

### 1.1 Run 1 — transport failure retained

```text
workflow run = 33867245529
completed qualified histories = 61 / 101
failure = upstream connection closed without a response
partial replay result = NOT PUBLISHED
```

There was no HTTP 429, business-code, PIT, calendar, adapter or coverage failure before the connection was closed. The run remained failed.

### 1.2 Run 2 — complete acquisition, analyzer failure retained

```text
workflow run = 33869436890
artifact id = 9936117543
artifact digest
= sha256:58de421f48f5d8d5ddafd1a702e1f676367f450da145948e932b186d6cd78816

qualified histories
= 101 / 101
= CSI 300
+ 90 broad 881*.TI industries
+ 10 bounded 884*.TI pressure controls

sessions per identity
= 164
= 2026-01-05 through 2026-09-04
```

Every history passed the existing HiThink adapter and was atomically retained with its request metadata, provider-envelope hash, checkpoint hash, completed-session identity and authority boundary.

After acquisition completed, the experiment analyzer failed because it treated a `SectorHorizonObservation` dataclass as a dictionary:

```text
TypeError: 'SectorHorizonObservation' object is not subscriptable
```

No partial analytical result was published.

### 1.3 Run 3 — successful analysis from retained inputs

```text
workflow run = 33875813519
new provider calls = 0

analysis artifact id = 9937787999
analysis artifact digest
= sha256:aba89e00ac3a3a64d6481889d2ecece6d788e322af3b3403e335945fcbb3f020

analysis result hash
= fb97046db44c857673a115793cf8f8f1f120e3e08f00ecb23088a47f00389119

full repository CI
= PASS
```

Run 3 downloaded the exact retained Run 2 artifact, re-hashed every checkpoint, revalidated the exact session set and executed only the pure replay analysis. It did not contact HiThink.

PR #168 was then closed without merge. Its workflow and experiment scripts did not enter `main`.

---

## 2. Input integrity

### 2.1 Universe

```text
benchmark
= 000300.SH / 沪深300

broad replay universe
= exact current 90-member 881*.TI industry family

bounded granular controls
= 10 explicit 884*.TI identities

mixed 881 + 884 cross-sectional ranking
= PROHIBITED
```

The ten granular controls were:

```text
884002.TI 粮食种植
884003.TI 其他种植业
884004.TI 林业
884005.TI 海洋捕捞
884006.TI 水产养殖
884279.TI 水产饲料
884183.TI 航海装备
884275.TI 生猪养殖
884276.TI 肉鸡养殖
884277.TI 其他养殖
```

They were used only as bounded path controls. They were not mixed into the 90-member broad rank, and they do not substitute for a full 884 cross-sectional replay.

### 2.2 Catalog and checkpoint identity

```text
catalog SHA-256
= 367d64660f5ef1f715ae0ef1d832a180d075ec7d6fc0a915797cbfafbd33f360

checkpoint-set hash
= 417d6b3b0395d8ad15ab23e9d315675dcffa5b7aecec1899255ae79368de80f7

all checkpoint hashes verified
= YES

all histories exactly session-aligned
= YES

history count
= 101

session count per identity
= 164
```

Every broad replay date required all 90 industries. There was no partial-universe percentile or silent exclusion.

### 2.3 PIT and authority

Only bars at or before each frozen market session were available to that replay. Later outcomes were calculated separately after the signal record.

No current constituent list was applied backward. No breadth or historical contribution claim was made.

All replay outputs remained:

```text
PRICE_PATH_DISCOVERY_OBSERVATION_ONLY
Research authority = NONE
Fundamental Belief authority = NONE
Human attention authority = NONE
Recommendation = NONE
Action = NONE
Investment authority = NONE
```

---

## 3. Replay method

The pure calculation contract was executed for each eligible completed session from `2026-04-08` through `2026-09-04`, producing 104 frozen PIT snapshots.

Each broad observation exposed:

```text
5 / 20 / 60-session sector return
5 / 20 / 60-session CSI 300 return
5 / 20 / 60-session excess return
cross-sectional strongest-first rank
bounded 1–99 cross-sectional rating
20-day rank change versus five sessions earlier
20-day excess acceleration versus five sessions earlier
positive 20-day excess persistence and run start
top-quartile 20-day persistence and run start
five-session turnover average / prior twenty-session average
```

For pressure-case comparison, the replay recorded several descriptive milestones:

```text
first positive 20-day excess
first top-quartile 20-day rating
first positive top-quartile run lasting three sessions
first top-decile 20-day rating
latest observation
```

The three-session milestone was used to inspect timeliness and compression. It was not selected through prospective evidence and is not authorized as a detector.

---

## 4. Human pressure cases

### 4.1 Broad-industry result

| Human observation | Broad identity | First positive 20d excess | First positive top-quartile run lasting 3 sessions | Latest 20d excess | Latest positive-excess age |
| --- | --- | --- | --- | ---: | ---: |
| 农业 / 种植 | `881101.TI 种植业与林业` | 2026-07-17 | 2026-08-05 — rank 17, rating 81, 20d excess +8.71% | +25.46% | 32 sessions |
| 养殖 / 猪肉 / 鸡肉 | `881102.TI 养殖业` | 2026-04-21 | 2026-07-07 — rank 11, rating 88, 20d excess +0.24% | +14.30% | 41 sessions |
| 水产 | `881102.TI 养殖业` as broad parent | 2026-04-21 | 2026-07-07 — rank 11, rating 88, 20d excess +0.24% | +14.30% | 41 sessions |
| 造船 / 航海装备 | `881166.TI 军工装备` as contextual parent | 2026-04-20 | **not observed** | +6.73% | 20 sessions |

### 4.2 Agriculture

`种植业与林业` first became positive on 2026-07-17, entered the top quartile on 2026-08-03 and completed a three-session top-quartile run on 2026-08-05.

At that 2026-08-05 PIT:

```text
20d excess return = +8.71%
20d rank = 17 / 90
20d rating = 81
positive-excess age = 10 sessions
top-quartile age = 3 sessions
turnover pulse = 1.10x
```

By 2026-09-04:

```text
20d excess return = +25.46%
20d rank = 1 / 90
positive-excess age = 32 sessions
top-quartile age = 14 sessions
turnover pulse = 1.93x
```

The broad observation layer therefore could have told the Human both that agriculture was becoming cross-sectionally unusual and, by September, that it was no longer a fresh one-day event.

### 4.3 Livestock and aquaculture

`养殖业` completed the same descriptive three-session milestone on 2026-07-07.

At that PIT:

```text
20d excess return = +0.24%
20d rank = 11 / 90
20d rating = 88
5d excess return = +11.46%
5d rank = 1 / 90
positive-excess age = 4 sessions
top-quartile age = 3 sessions
turnover pulse = 1.63x
```

The small 20-day excess and very strong five-day acceleration are both visible. The observation did not need a composite score to show that this was an emerging rather than mature move.

Bounded granular paths later confirmed that the broad parent contained materially different drivers:

| Granular control | First 3-session positive-excess run | Latest 20d excess | Latest positive-excess age | Latest turnover pulse |
| --- | --- | ---: | ---: | ---: |
| `884275.TI 生猪养殖` | 2026-07-03 | +15.58% | 15 | 1.20x |
| `884276.TI 肉鸡养殖` | 2026-04-23 | +13.91% | 39 | 1.10x |
| `884277.TI 其他养殖` | 2026-07-20 | +36.25% | 20 | 1.51x |
| `884005.TI 海洋捕捞` | 2026-07-20 | +22.32% | 33 | 2.30x |
| `884006.TI 水产养殖` | 2026-07-17 | +15.76% | 33 | 1.58x |
| `884279.TI 水产饲料` | 2026-04-23 | +12.58% | 20 | 1.39x |

These granular controls are descriptive decomposition only. Their early isolated positive runs also show why path persistence without a proper 884 cross-sectional comparison is insufficient for production discovery.

### 4.4 Shipbuilding coverage failure

The broad `军工装备` identity briefly entered the top quartile on 2026-04-20, but its run lasted only one session. It never completed the three-session broad milestone and never reached the 20-day top decile during the replay.

At 2026-09-04:

```text
军工装备
20d excess return = +6.73%
20d rank = 36 / 90
20d rating = 60
positive-excess age = 20 sessions
top-quartile age = 0
turnover pulse = 1.32x
```

The bounded granular path showed a different picture:

```text
航海装备
first positive 20d excess = 2026-04-20
first 3-session positive-excess run = 2026-04-22

2026-09-04:
20d excess return = +7.91%
5d excess return = +6.03%
20d excess acceleration versus five sessions earlier = +4.90 percentage points
positive-excess age = 20 sessions
turnover pulse = 1.54x
```

Because `军工装备` is broader than shipbuilding, relabeling it “造船” would be semantically false. The replay therefore establishes a real product gap:

```text
881 broad rank
= useful first comparison layer

881 broad rank alone
!= complete cold-start sector discovery

narrow economic theme inside a broad parent
= may be diluted below the broad cross-sectional surface
```

---

## 5. Negative controls

### 5.1 One-day spike that failed to persist

`881174.TI 厨卫电器` on 2026-08-19:

```text
one-session sector return = +4.57%
one-session CSI 300 return = -2.90%
one-session excess return = +7.47%

20d rank = 3 / 90
20d rating = 97
turnover pulse = 1.45x
```

Five sessions later, its forward excess return was `-3.29%`, and its 20-day rating had fallen from `97` to `68`.

A one-day price shock, even with turnover and a high current rank, is not enough. Persistence and later state change must remain visible.

### 5.2 Relative strength caused mainly by benchmark weakness

`881155.TI 银行` on 2026-04-09:

```text
20d sector return = -0.52%
20d CSI 300 return = -2.94%
20d excess return = +2.42%
20d rank = 4 / 90
20d rating = 96
turnover pulse = 0.82x
```

The high relative rank did not mean the industry itself had produced a positive 20-day return. Publishing raw sector and benchmark returns alongside excess is therefore mandatory.

### 5.3 Established long-horizon leader whose short horizon was fading

`881169.TI 贵金属` on 2026-09-04:

```text
60d rank / rating = 1 / 99
20d rank / rating = 12 / 87
5d rank / rating = 84 / 8

20d rank change versus five sessions earlier = -11 places
20d excess acceleration versus five sessions earlier
= -17.79 percentage points

turnover pulse = 0.88x
```

A long-horizon leader can be materially weakening now. A single “strong sector” label or one composite score would hide this transition.

### 5.4 Narrow one-or-two-constituent move

This control was **not evaluated**.

The available endpoint exposes current constituents, not historical membership. Using the 2026-09-04 list to infer breadth or concentration at an earlier PIT would create look-ahead and membership backfill.

Required future treatment:

```text
current constituent list
→ current cross-sectional breadth only

historical breadth / concentration
→ unavailable unless same-PIT membership was actually retained
```

---

## 6. Transparent 0–3 compression challenger

The replay tested this illustrative rule:

```text
20d excess return > 0
+ 20d cross-sectional rating >= 75
+ current top-quartile run reaches exactly 3 sessions
→ eligible state-change observation

sort:
1. strongest 20d rank
2. larger five-session rank improvement
3. thscode deterministic tie

surface:
at most 3
```

Result:

```text
replay days = 104
quiet days = 38
active days = 66

eligible state-change events = 129
events retained by 0–3 cap = 123
days requiring truncation = 5
maximum same-day eligible events = 5
```

Forward path diagnostics:

| Horizon | Evaluable events | Median forward excess | Positive share |
| --- | ---: | ---: | ---: |
| T+5 sessions | 118 | -0.40% | 46.61% |
| T+20 sessions | 82 | +4.39% | 71.95% |

Interpretation:

- the state-change rule can compress a 90-industry universe into a small surface on most days;
- it sometimes still exceeds the Human budget;
- it did not show reliable immediate five-session follow-through;
- its stronger T+20 result is consistent with a Research-attention horizon, not proof of a trading edge;
- the rule was inspected retrospectively on the same corpus that motivated the product.

Therefore:

```text
challenger rule
= useful replay probe
!= accepted detector
!= recommendation
!= timing rule
!= production Human alert authority
```

---

## 7. Acceptance criteria disposition

| Criterion | Result | Evidence |
| --- | --- | --- |
| PIT correctness | PASS | Exact frozen session slices; later outcomes recorded separately |
| Coverage honesty | PASS | Every broad PIT required all 90 identities; failures published no result |
| Early-enough discovery | PARTIAL PASS | Agriculture and livestock surfaced before final acceleration; shipbuilding did not |
| Trend-age visibility | PASS | Positive-excess and top-quartile run starts are explicit |
| Noise restraint | CHALLENGER ONLY | 38/104 quiet days; 5 days still exceeded the 3-item cap |
| No daily repetition | CHALLENGER ONLY | The tested rule emitted only on the third top-quartile session, but is not prospectively accepted |
| No authority leak | PASS | No Research, Recommendation, Action or investment authority |
| Source integrity | PASS | HiThink only; exact checkpoint and source-envelope hashes |
| Current-breadth honesty | PASS BY OMISSION | No current constituents were backfilled into historical PITs |
| Forward evaluability | PASS | T+5 and T+20 outcomes preserved for eligible events |
| Complete thematic coverage | FAIL | Broad-only 881 missed the shipbuilding-like granular move |

This is why the overall result is **partial pass** rather than pass.

---

## 8. Product decision

### 8.1 What is now supported

The evidence supports retaining the current simple observation family:

```text
5 / 20 / 60-session relative strength
+ raw sector and benchmark returns
+ rank / rating
+ rank change
+ excess acceleration
+ persistence / trend age
+ turnover pulse
```

It also supports using the 90-member 881 family as the first, low-overlap broad comparison layer.

### 8.2 What is not supported

The replay does not authorize:

```text
no production threshold
no EMERGING / ESTABLISHED / ACCELERATING / FADING Kernel state
no composite opportunity score
no 881-only claim of complete market discovery
no full 884 + 881 mixed rank
no current-constituent historical breadth
no automatic Research Funnel route
no Attention Inbox insertion
no canonical Human wake
no Recommendation
no portfolio allocation
no Action
no investment authority
```

### 8.3 Next authorized work

The next evidence-building slice is:

1. run a **separate** cross-sectional replay over the exact 230-member `884*.TI` family;
2. compare its incremental discoveries and noise against the broad 881 lane;
3. fetch current constituents and stock snapshots only for bounded current finalists;
4. expose current breadth without historical backfill;
5. then build a separate shadow-only state-change producer with full JSON and a 0–3 summary;
6. collect prospective T+5 / T+20 outcomes before considering any alert gate.

The 881 and 884 lanes should remain distinct:

```text
881
= broad industry discovery
= lower overlap
= first comparison layer

884
= granular challenger / decomposition
= higher overlap and duplicate-exposure risk
= separate rank and stricter Human compression

881 + 884 in one percentile universe
= prohibited
```

---

## 9. Central conclusion

> **The broad Sector Radar can catch real multi-week agriculture and livestock moves early enough to improve Research allocation, and it can state when those moves are already mature. It cannot, by itself, guarantee discovery of narrower themes hidden inside broad parents. The correct next move is a separate granular challenger and current breadth—not a production alert, score, or trading rule.**

## Source pointers

Repository:

- `docs/sector-discovery-radar-prior-art-and-v0-decision-2026-09-04.md`
- `docs/sector-discovery-radar-hithink-acquisition-proof-2026-09-04.md`
- `src/decision_kernel/runtime/sector_radar.py`
- `src/decision_kernel/adapters/hithink_index.py`
- `src/decision_kernel/runtime/hithink_index_http.py`
- PR `#168` — closed without merge

Frozen operations lineage:

- Run `33867245529` — retained partial-acquisition transport failure
- Run `33869436890` / artifact `9936117543` — complete qualified acquisition, retained analyzer failure
- Run `33875813519` / artifact `9937787999` — successful analysis from retained inputs, zero new provider calls
