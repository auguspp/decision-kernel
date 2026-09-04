# Sector Discovery Radar — prior-art review and v0 decision — 2026-09-04

Status: **RESEARCH / DESIGN DECISION ONLY / NO RUNTIME ADOPTION / NO NEW KERNEL SCHEMA / NO INVESTMENT AUTHORITY**  
Repository: `auguspp/decision-kernel`  
Reviewed from `main`: `51ac311db510009ce582188e7082c617e9bbd190`  
Decision date: **2026-09-04**

## 0. Executive decision

The Human observed that several A-share groups — including shipbuilding, aquaculture, livestock and agriculture — had already produced meaningful multi-week moves before the current system surfaced them. This is a real product failure:

```text
Human manually browses the market
→ discovers an established sector trend
→ only then tells Decision Kernel
```

The desired order is:

```text
broad market reality
→ Sector Discovery Radar
→ a very small Human attention surface
→ Human / Research triage
→ existing Research Funnel
→ Full Research only when earned
```

The project will therefore move **Sector Discovery Radar** to the highest implementation priority.

However, the first production slice will **not** copy an external stock-selection platform, create a composite opportunity score, promote a change-point model, or add a third canonical Human wake gate.

Selected v0 direction:

```text
UNIVERSE
= formal HiThink industry indices first

DISCOVERY SIGNALS
= multi-horizon relative strength
+ rank change / acceleration
+ persistence
+ turnover pulse
+ current constituent breadth for finalists

OUTPUT
= descriptive, auditable sector observations
= normally 0–3 Human-facing sectors
= full universe retained in a machine-readable artifact

ROUTING
= Human / Research triage
→ existing Research Funnel

AUTHORITY
= attention acquisition only
= no Fundamental Belief change
= no Recommendation
= no Action
= Investment Authority NONE
```

No runtime code is authorized by this document alone. Implementation must follow the staged acceptance plan below.

---

## 1. Problem statement

The current Surprise Radar is intentionally narrow. It accepts exact reviewed A-share Research packages, binds each price path to an existing `ResearchSnapshot`, and emits short-lived `SHADOW_OBSERVATION_ONLY` artifacts.

That makes it suitable for:

```text
already-researched ticker
→ later unusual price path
→ possible renewed attention
```

It cannot answer:

```text
which industry or theme has quietly become strong?
which group has stayed strong for several weeks?
which group is newly accelerating versus merely extending an old move?
which strong group has broad constituent participation rather than one leader?
which move is losing participation or turnover confirmation?
```

This limitation is structural, not a bug in the existing ticker Surprise Radar.

The missing product is **cold-start sector discovery**. It is distinct from:

- official-disclosure discovery;
- Commitment Radar;
- post-Research ticker Surprise Radar;
- canonical Decision-review wake;
- market-regime context.

The new lane must acquire attention without acquiring investment authority.

---

## 2. Existing repository doctrine that remains binding

### 2.1 Decision Kernel is not a stock-picking system

The established flow remains:

```text
Reality
→ Evidence / Claims
→ Discovery / Radar
→ Research Funnel
→ Attention Inbox
→ Research
→ frozen ResearchSnapshot
→ Observed Market
→ Odds
→ Decision Rehearsal
→ Human Surface
→ Human decides
```

Sector Radar belongs before Research. It cannot write Fundamental Belief, probability, Odds, Human Decision or Action.

### 2.2 Do not create another Radar routing model

The existing Research Funnel already owns:

```text
DROP_FOR_NOW
WAIT_FOR_TRIGGER
DEEPEN_REQUIRED
```

Sector Radar may create a bounded discovery observation or handoff input. It must not invent competing terminal states such as `BUY_SECTOR`, `STRONG_BUY`, `PROMOTE`, or another investment-decision route.

### 2.3 The Human front door remains scarce

The current product objective remains:

> Human should normally see only 0–3 genuinely attention-worthy items, or an explicit quiet state.

A broad sector table may exist as an artifact for audit and drill-down. It must not become the default Human surface.

### 2.4 Existing wake authority remains unchanged

```text
Research Funnel DEEPEN_REQUIRED
= Research-budget attention
!= canonical Decision wake

HumanResearchSurface.attention_eligible
= sole canonical Decision-review wake
```

Sector discovery is neither of those until it has passed the existing Research Funnel or joined an already-authoritative output. The first v0 surface should therefore remain separate from the canonical Attention Inbox while signal quality is being evaluated.

### 2.5 Price-path evidence does not become Fundamental Evidence

A strong sector price path can justify investigation. It does not establish:

- an industry earnings upcycle;
- a supply shortage;
- company revenue or profit growth;
- owner cash;
- cheapness;
- a buy decision.

Required semantic chain remains:

```text
sector price / breadth change
→ discovery question
→ causal / fundamental evidence search
→ listed-company mapping
→ Research Funnel
```

---

## 3. Prior-art review

The goal of prior-art review is not to find a system to copy. It is to identify proven commodity patterns, documented failure modes, and architecture that should be rejected.

### 3.1 HiThink Financial API — closest native data fit

Repository: `HiThink-Tech/Financial-API`  
Role: **PRIMARY COMMODITY DATA CONTRACT / IMPLEMENT NATIVELY AGAINST OFFICIAL ENDPOINTS**

Relevant official endpoints:

```text
GET /api/a-share-index/catalog/ths-index-list?tag=industry
GET /api/a-share-index/catalog/ths-index-list?tag=cn_concept
GET /api/a-share-index/prices/historical
GET /api/a-share-index/prices/snapshot
GET /api/a-share-index/constituents/ths-stock-list
GET /api/a-share/prices/snapshot
```

The official `industry-strength-rotation` inspiration already proposes the right observation family:

```text
5 / 20 / 60-day relative strength
+ turnover pulse
+ rank change
+ market breadth
+ industry-to-constituent drill-down
```

Its most important data boundary is also compatible with Decision Kernel:

```text
current constituents
= current cross-sectional evidence only
!= historical constituents
!= historical index contribution
```

What to borrow:

- one authoritative A-share market source already used by this project;
- explicit industry catalog identity;
- index history and current constituent drill-down;
- 5/20/60-session strength, acceleration, turnover and breadth vocabulary;
- clear distinction between an industry index and a directly investable asset.

What not to borrow blindly:

- demonstration UI as product authority;
- simulated labels as production thresholds;
- a large all-sector history fan-out without an acquisition-budget test.

Decision:

> **HiThink remains the sole qualified market source for Sector Discovery Radar v0.**

### 3.2 `xang1234/stock-screener`

Status at review: active 2026 project, Apache-2.0, multi-market scanner with group rankings, breadth, RRG, theme discovery and validation.  
Role: **BORROW DATA-CONTRACT AND EVALUATION PRINCIPLES / DO NOT ADOPT PLATFORM**

Most useful design properties:

1. Relative strength is calculated once per market/date from an explicit universe.
2. The formula has an explicit version.
3. Market-session anchors are exact rather than arbitrary row counts.
4. Coverage, benchmark identity and universe identity are published.
5. Incomplete or failed runs cannot replace the latest completed run.
6. Historical formula versions are not mixed silently.
7. Group rank history is retained so changes can be evaluated prospectively.
8. Theme / scan alerts have a later validation surface using forward returns and MFE / MAE.

Its balanced RS implementation also exposes a useful anti-domination idea:

```text
per-horizon returns
→ cross-sectional percentile normalization
→ combine bounded horizon information
```

This prevents one extreme long-horizon return from completely hiding recent deterioration.

What to reject:

- full FastAPI / PostgreSQL / Redis / Celery / React platform;
- composite stock-selection scores;
- position-sizing and portfolio policy;
- proprietary-style IBD rank imitation as Decision authority;
- a dashboard-first implementation.

Decision:

> Borrow versioned daily snapshots, exact universe/session identity, deterministic ties, explicit failure coverage, and forward evaluation. Do not copy the platform or its investment methodology.

### 3.3 `ZhuLinsen/alphasift`

Status at review: active 2026 project, Apache-2.0, A-share full-market discovery and hotspot workflow.  
Role: **BORROW PROVENANCE / HISTORY / EVALUATION PATTERNS / REJECT RANKING AUTHORITY**

Useful patterns:

- broad discovery is separate from later analysis;
- generated-at timestamp and provider metadata are explicit;
- cache / history sidecars preserve what the system saw at the time;
- source errors, stale state and fallback use are exposed rather than hidden;
- later evaluation distinguishes follow-through from failed breakouts;
- MFE / MAE and failure samples are retained.

Especially useful provenance fields include the equivalent of:

```text
source
source_confidence
stale
fallback_used
source_errors
```

What to reject:

- deterministic factors converted into investment conviction;
- LLM ranking as candidate authority;
- broad multi-provider fallback stacks;
- composite opportunity scores;
- stock-selection output flowing directly into portfolio risk buckets.

Decision:

> Borrow explicit source health, last-good visibility, append-only discovery history and T+N evaluation. In v0, a HiThink failure should remain visible and should not trigger a competing market-data fallback.

### 3.4 `simonlin1212/a-stock-data`

Status at review: highly used, actively updated A-share data toolkit, Apache-2.0.  
Role: **ACQUISITION PRIOR ART ONLY**

Relevant capabilities include:

- industry board ranking;
- industry up/down constituent counts;
- sector fund flow over current / 5d / 10d windows;
- leader stock and topic attribution;
- source-specific throttling and failure handling.

What to borrow:

- current board ranking and breadth as useful commodity observations;
- bounded source-specific adapters;
- explicit throttling when upstream reality demands it;
- treating current constituent breadth separately from historical index performance.

What to reject:

- 19-source fallback architecture;
- Eastmoney or other wrapper data promoted to the project's authoritative market boundary;
- fund-flow labels treated as economic truth;
- embedding a large Markdown skill or data platform into Decision Kernel.

Decision:

> Use as evidence that breadth and board rank are practical and useful. Do not import its provider architecture.

### 3.5 RRG projects

Reviewed examples:

- `BennyThadikaran/RRG-Lite`;
- `marketcalls/sector-rotation-map`;
- RRG implementation inside `xang1234/stock-screener`.

RRG's useful conceptual split is:

```text
relative strength level
× relative-strength momentum
→ Leading / Weakening / Lagging / Improving visualization
```

But open-source evidence also exposes a real warning: RRG-Lite explicitly states that its current implementation is overly sensitive to short-term movement and noise and is paused pending better smoothing.

RRG also tends to be:

- a lagging visualization;
- parameter-sensitive;
- easy to over-interpret as a four-state investment machine;
- dependent on sufficiently long, clean and consistently versioned history.

Decision:

> **RRG is not the v0 detector.** It may be added later as a drill-down visualization after the underlying relative-strength history and signal evaluation are trusted.

### 3.6 Change-point and online anomaly libraries

Reviewed:

- `deepcharles/ruptures` — mature BSD-2 change-point library;
- `online-ml/river` — mature BSD-3 online learning / drift library.

The libraries themselves are credible. The project-specific evidence is not yet sufficient.

The repository's prior PELT experiment on coal, planting/forestry and CRO found:

```text
some transitions were prospectively detectable
but confirmation lag was roughly 12–29 trading sessions
and several latest breaks were penalty-unstable
```

The same experiment also hit HiThink HTTP 429 under fan-out; only a bounded four-history-request run with 20-second pacing succeeded.

Decision:

> Do not add `numpy`, `scipy`, `ruptures`, `river` or a general anomaly stack to v0. Revisit only after simple descriptive observations produce a real labeled failure corpus.

### 3.7 Qlib and Alphalens

Reviewed:

- `microsoft/qlib` — mature AI-oriented quant platform;
- `quantopian/alphalens` — factor forward-return evaluation library.

Useful ideas:

- strict point-in-time separation;
- immutable run identity;
- cross-sectional factor evaluation;
- forward-return and quantile diagnostics;
- separation of signal creation time from later outcome windows.

What to reject:

- adopting a broad quant platform;
- turning Sector Radar into a backtest / portfolio / ML framework;
- requiring heavy dependencies before the observation contract is stable.

Decision:

> Borrow evaluation discipline only. Keep implementation native and small.

---

## 4. Selected product boundary

### 4.1 Name and purpose

Working product name:

```text
Sector Discovery Radar v0
```

Purpose:

> Detect persistent or newly accelerating sector-level market attention early enough to allocate Research attention, while making trend age and confirmation visible so the Human can distinguish an emerging move from a late-stage acceleration.

It is not:

- a sector allocation model;
- a sector ETF strategy;
- an industry earnings model;
- a market-timing engine;
- a recommendation system;
- a third canonical Decision wake.

### 4.2 Initial universe

Production v0 begins with:

```text
HiThink formal industry index catalog only
```

Reasons:

- industries are a smaller, less overlapping universe;
- index identity is explicit and stable enough for a first observation layer;
- broad concept catalogs contain heavy overlap and duplicate narratives;
- broad concept-history fan-out would amplify rate-limit and attention-noise risk;
- Human examples such as shipbuilding, aquaculture and agriculture should already map to formal industries or be recoverable through later constituent / concept drill-down.

Concept indices may be used only after an industry candidate is selected, for bounded decomposition such as:

```text
livestock industry
→ pork / chicken concept context

marine equipment industry
→ shipbuilding / central-shipbuilding concept context
```

Concepts do not enter the first full cross-sectional ranking universe.

### 4.3 Benchmark

The benchmark must be explicit in every run.

Initial candidate:

```text
000300.SH / CSI 300
```

Rationale:

- broader investable-market quality than a price-weighted Shanghai-only comparison;
- compatible with the official HiThink sector-strength example;
- reduces distortion when Shenzhen / ChiNext-heavy industries are compared with `000001.SH`.

Before production activation, a frozen-PIT sensitivity check must compare at least:

```text
000300.SH / CSI 300
000985.CSI or another broad all-A benchmark if HiThink identity is qualified
000001.SH / Shanghai Composite as a context control
```

The benchmark selection is a Harness formula decision, not a Fundamental Belief.

---

## 5. v0 observation contract

No single composite opportunity score is authorized.

Each sector observation should expose the following raw / derived fields.

### 5.1 Identity and PIT

```text
run_id
captured_at
market_session
source
catalog_tag
catalog_hash
industry_thscode
industry_name
benchmark_thscode
formula_version
history_window_start
history_window_end
```

### 5.2 Multi-horizon path

Exact market-session horizons:

```text
5 sessions
20 sessions
60 sessions
```

For each horizon:

```text
sector_return
benchmark_return
excess_return
cross-sectional percentile or rank
```

The initial implementation should publish both raw return and percentile. Percentile is useful for comparison; raw return prevents a rank from hiding whether the whole market is falling.

### 5.3 Acceleration / rank change

Expose, do not hide:

```text
current 5d / 20d / 60d rank
rank change versus 5 sessions earlier
change in 20d excess return versus 5 sessions earlier
```

This distinguishes:

```text
already strong and still strong
newly improving
accelerating from an established base
strong but losing momentum
```

### 5.4 Persistence

Persistence is essential because the Human's failure mode was discovering themes only after they had already run for weeks.

Candidate fields:

```text
consecutive sessions with positive 20d excess
consecutive sessions in top quartile by 20d excess
first session the current top-quartile run began
first session the current positive-excess run began
```

These are descriptive age fields, not buy / sell timing rules.

### 5.5 Turnover pulse

For each industry index:

```text
recent 5-session average turnover
prior 20-session average turnover
turnover pulse ratio
```

Turnover is confirmation context only. It must not be interpreted as institutional buying, owner economics, or durable capital inflow without stronger evidence.

### 5.6 Current breadth — finalists only

For only a bounded set of candidate industries, retrieve current constituents and latest stock snapshots.

Expose:

```text
current constituent count
valid snapshot count
up / flat / down counts
advance ratio
median constituent daily return
equal-weight current daily return proxy
share of constituents above their own 20-session average, if bounded history is available later
```

Critical boundary:

```text
current constituent breadth
= latest cross-section
!= historical breadth
!= historical membership
!= index contribution
```

The v0 must not backfill today's constituents into the past.

---

## 6. Descriptive lifecycle labels

Lifecycle labels may be useful for Human readability, but they remain Harness presentation labels, not Kernel enums and not investment states.

Candidate vocabulary:

```text
EMERGING
= relative strength recently improved; persistence still short

ESTABLISHED
= relative strength is high and persistence is material

ACCELERATING
= established or improving strength with positive short-horizon rank / excess change

FADING
= still historically strong but recent rank / breadth / turnover confirmation is weakening
```

Before production, every label must be reducible to visible fields and versioned rules. No opaque score may decide the label.

The first implementation may omit labels entirely and publish only fields until replay evidence supports stable wording.

---

## 7. Human surface

### 7.1 Separate shadow surface first

Initial rollout:

```text
Sector Discovery Radar shadow
→ its own summary.md / index.html / JSON artifact
→ no canonical Attention Inbox insertion
```

Reason:

- discovery quality has not yet been prospectively validated;
- a broad sector detector can easily become a noise generator;
- inserting unqualified sector observations into the current Inbox would create a de facto third attention authority.

### 7.2 Human-facing compression

The summary should normally contain no more than three sectors.

Each card should answer:

```text
what changed?
how long has it persisted?
is it emerging, established, accelerating or fading?
does current turnover / breadth confirm it?
what Research question should be asked next?
```

Example presentation shape:

```text
造船 / 航海装备
- 20d excess rank: top decile
- current strong run began: N sessions ago
- 5d rank change: improving / weakening
- turnover pulse: 1.x
- current breadth: x/y constituents up
- interpretation: established trend / latest acceleration
- next Research question: order cycle, pricing, delivery, margin and owner-cash mapping
```

It must not say:

```text
recommended sector
best opportunity
high conviction
buy now
```

### 7.3 Full audit artifact

The full industry universe remains available as JSON with:

- all metrics;
- exclusions and reasons;
- data freshness;
- source / benchmark / formula identity;
- candidate-selection trace;
- current breadth only where fetched.

---

## 8. Candidate-selection rule — no composite opportunity score

The Human summary needs compression, but compression does not require a conviction score.

Preferred v0 structure:

1. Apply transparent eligibility gates.
2. Partition observations into descriptive buckets.
3. Sort within a bucket by one declared primary field with deterministic ties.
4. Show at most three, while retaining all eligible rows in the artifact.

Illustrative gates to test, not yet authorize:

```text
minimum history coverage
+ latest completed session reached
+ 20d excess rank in a high cross-sectional band
+ either meaningful persistence or positive recent acceleration
+ no missing benchmark / catalog identity
```

Potential priority order:

```text
EMERGING / ACCELERATING candidates first
then ESTABLISHED candidates not previously surfaced
then material FADING transitions for an already-followed sector
```

A sector should not recur every day merely because it remains strong. The system must distinguish:

```text
new state change
!= unchanged daily persistence
```

---

## 9. Acquisition and operations decision

### 9.1 Known constraint

HiThink index history is one index per request. The prior repository experiment hit HTTP 429 under broad fan-out; four requests with explicit 20-second pacing succeeded.

Therefore, production design cannot assume that fetching the full historical industry universe after every close is acceptable.

### 9.2 Required acquisition-budget probe

Before implementation chooses storage or cadence, run a bounded, non-product probe that measures:

```text
industry catalog size
index snapshot explicit-batch limits
response freshness / completeness
history request rate limit
whether catalog / snapshot timestamps can anchor the latest completed session
```

The probe must be designed after this document and must not itself define a detector.

### 9.3 Preferred operating pattern if supported

Likely efficient shape:

```text
one-time / infrequent industry-history bootstrap
+ daily explicit-batch industry snapshot
+ append one completed session locally
+ bounded constituent snapshot only for finalists
```

This is only a hypothesis until the API budget is verified.

### 9.4 Failure behavior

```text
stale or incomplete source
→ visible run failure / unavailable status
→ do not publish a new completed observation
→ do not silently reuse stale values as current
→ do not fall back to another market provider
```

A last-good artifact may remain available for reference only if its stale status and exact age are explicit. It cannot masquerade as today's result.

---

## 10. Prospective evaluation

Sector Radar cannot be judged merely because a chart looks reasonable.

Every surfaced observation must preserve its PIT and later receive an outcome record.

Minimum evaluation horizons:

```text
T+5 completed sessions
T+20 completed sessions
```

For each surfaced sector, record:

```text
forward sector return
forward excess return versus the same benchmark
maximum favorable excursion
maximum adverse excursion
rank persistence
whether the sector remained top quartile
whether the Human / Research Funnel found a decision-relevant causal question
whether a later fundamental event confirmed or contradicted the initial market signal
```

Primary product questions:

1. Did Radar surface an emerging / accelerating group before the Human would ordinarily discover it manually?
2. Did it distinguish a newly forming trend from a move already mature and extended?
3. How often did apparently strong paths fail immediately?
4. Which important groups were missed despite later obvious persistence?
5. Did the output improve Research allocation rather than merely describe past winners?

No detector is promoted until these questions have a real prospective corpus.

---

## 11. Frozen-PIT acceptance cases

The first replay corpus should include the Human's real missed examples plus controls.

### Positive / pressure cases

```text
shipbuilding / marine equipment
pork / livestock
chicken / livestock
fishery / aquaculture
planting / forestry / agriculture
```

The replay question is not “did the system rank them first today?” It is:

> At what earliest frozen PIT did the observable path become meaningfully different from ordinary cross-sectional noise, and did the output clearly state how old the trend already was?

### Negative / control cases

Include at least:

- a one-day sector spike that did not persist;
- a low-turnover relative move caused mostly by benchmark weakness;
- a narrow move driven by one or two constituents;
- an established leader whose short-horizon strength was fading;
- a sector that later became fundamentally important without an early strong price path, as a false-negative candidate.

### Acceptance criteria for a shadow v0

A candidate implementation must demonstrate:

1. **PIT correctness** — no future bar, current constituent list or later outcome leaks into an earlier run.
2. **Coverage honesty** — missing histories / catalog / benchmark produce explicit exclusions.
3. **Early-enough discovery** — at least some real pressure cases surface before the final acceleration day.
4. **Trend-age visibility** — Human can tell whether a move began recently or weeks ago.
5. **Noise restraint** — summary remains 0–3 sectors under ordinary days.
6. **No daily repetition** — unchanged established leaders do not recur as new alerts.
7. **No authority leak** — no Recommendation, Action, portfolio allocation or Fundamental Belief mutation.
8. **Source integrity** — HiThink only for qualified market values; no hidden fallback.
9. **Current-breadth honesty** — today's constituents are never used to claim historical breadth or contribution.
10. **Forward evaluability** — every surfaced item can be replayed and evaluated at T+5 / T+20.

---

## 12. Implementation sequence

Only this sequence is authorized.

### Phase A — native calculation contract

- pure standard-library calculations;
- exact market-session anchors;
- returns, excess, ranks, percentiles, persistence, rank change and turnover pulse;
- deterministic ties;
- fixtures and PIT tests;
- no live provider call;
- no Human alert.

### Phase B — HiThink index adapter and acquisition-budget proof

- catalog normalization;
- index history normalization;
- explicit-batch snapshot normalization;
- completed-session and stale-response discipline;
- exact request-count / rate-limit evidence;
- no fallback.

### Phase C — frozen-PIT replay

- shipbuilding, livestock / pork / chicken, aquaculture and planting / agriculture;
- negative controls;
- compare simple transparent fields before considering any model;
- document earliest detection and lag.

### Phase D — shadow daily producer

- independent non-fatal workflow;
- full JSON artifact plus compressed summary;
- 0–3 sectors;
- no Attention Inbox insertion;
- state-change deduplication;
- source-health visibility.

### Phase E — prospective T+5 / T+20 evaluation

- append outcome records;
- inspect false positives and false negatives;
- compare Human discovery timing;
- only then decide whether a simple alert gate is justified.

### Phase F — optional later work

Only after evidence:

- concept-universe expansion;
- RRG drill-down visualization;
- change-point or online-drift challenger;
- joining qualified sector discovery to the existing Research Funnel producer;
- possible Human Inbox composition, without creating a third authority.

---

## 13. Explicit non-goals

```text
no external project copied wholesale
no new Kernel schema
no SectorState enum in Kernel
no composite opportunity score
no LLM ranking authority
no sector buy / sell signal
no portfolio allocation
no automatic order
no broker integration
no second / third canonical wake gate
no price path changing Fundamental Belief
no current constituents backfilled into history
no RRG as v0 detector
no ruptures / river / PyOD in v0
no numpy / scipy production dependency in v0
no multi-provider fallback
no broad dashboard as the default Human surface
no threshold tuned only to shipbuilding / pork / agriculture examples
```

---

## 14. Prior-art disposition summary

| Source | Borrow | Reject / defer |
| --- | --- | --- |
| HiThink official industry-strength example | industry catalog, 5/20/60 RS, acceleration, turnover, current breadth, explicit endpoint contracts | simulated thresholds / UI as authority; unbounded fan-out |
| `xang1234/stock-screener` | versioned daily RS, exact universe/session, atomic publish, formula isolation, forward evaluation | full platform, composite scores, position sizing |
| `ZhuLinsen/alphasift` | source-health metadata, append-only history, stale/fallback visibility, T+N evaluation | LLM ranking, conviction score, provider fallback stack |
| `simonlin1212/a-stock-data` | board rank, breadth, fund-flow context as low-authority observation, throttling lessons | 19-source architecture, wrapper data as truth |
| RRG projects | relative strength vs momentum vocabulary; later visualization | v0 detector; four-quadrant investment state machine |
| `ruptures` / `river` | later challenger candidates | production dependency before labels and failure corpus |
| Qlib / Alphalens | PIT and forward-evaluation discipline | platform / factor framework adoption |

---

## 15. Decision

```text
PROJECT PRIORITY
= Sector Discovery Radar v0

FIRST IMPLEMENTATION
= native, explainable, HiThink-only industry observation layer

PRIMARY SIGNAL FAMILY
= 5/20/60 relative strength
+ rank change
+ persistence / trend age
+ turnover pulse
+ current breadth for finalists

FIRST HUMAN SURFACE
= separate shadow summary
= normally 0–3 sectors

ROUTING
= Human / Research triage
→ existing Research Funnel

DETECTOR / SCORE / RRG / ML
= NOT AUTHORIZED FOR V0

FUNDAMENTAL BELIEF CHANGE
= NO

RECOMMENDATION / ACTION
= NO

INVESTMENT AUTHORITY
= NONE
```

Central discipline:

> **The Radar succeeds when it helps the Human notice an emerging or persistent sector early enough to ask the right Research question — while also saying when the move is already mature — not when it produces the most impressive ranking table.**

## Source pointers

Project:

- `docs/project-state.md`
- `docs/decision-inbox.md`
- `docs/handoffs/2026-09-03-radar-phase-next-conversation-handoff.md`
- `docs/dogfood/surprise-radar-v0-first-post-research-baseline-2026-09-04.md`
- `docs/dogfood/surprise-radar-v0-human-alert-policy-2026-09-04.md`
- `docs/radar-prior-art-refresh-2026-09.md`
- `src/decision_kernel/runtime/market_history_shadow.py`
- `src/decision_kernel/runtime/hithink_http.py`
- `src/decision_kernel/adapters/hithink.py`

External prior art:

- `https://github.com/HiThink-Tech/Financial-API`
- `https://github.com/xang1234/stock-screener`
- `https://github.com/ZhuLinsen/alphasift`
- `https://github.com/simonlin1212/a-stock-data`
- `https://github.com/BennyThadikaran/RRG-Lite`
- `https://github.com/marketcalls/sector-rotation-map`
- `https://github.com/deepcharles/ruptures`
- `https://github.com/online-ml/river`
- `https://github.com/microsoft/qlib`
- `https://github.com/quantopian/alphalens`
