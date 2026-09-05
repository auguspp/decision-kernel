# Decision Kernel — Current Project State

Status: **MUTABLE CURRENT-STATE INDEX / NOT AUTHORITATIVE OVER FROZEN LINEAGE / NO NEW KERNEL SCHEMA**  
Updated: **2026-09-05**  
Repository: `auguspp/decision-kernel`  
Verified clean baseline before this state-only sync: `e3d8611b40d7b59694d1d86a4d85c8342de1cd39`

## Operating rule

This file is the default cross-conversation entry point. Frozen Research, Human Decision, Action and Outcome artifacts remain authoritative over this mutable index.

```text
New conversation: read this file and the latest handoff, then verify current main.
End of conversation: sync only real state deltas.
```

Do not trust a chat summary over repository state, frozen lineage, CI results or real workflow artifacts.

---

## 1. Current phase

```text
TRUSTWORTHY COGNITION CORE = STABLE / DO NOT EXPAND WITHOUT REAL FAILURE
ATTENTION ACQUISITION = ACTIVE HIGHEST PRIORITY
HUMAN ATTENTION SURFACE = ACCEPTED / MERGED / ACTIVE
SECTOR DISCOVERY RADAR = SHADOW CONTRACTS + DURABLE BOOTSTRAP READY
SECTOR DISCOVERY RADAR DAILY PRODUCER = NOT YET MERGED
SECTOR DISCOVERY RADAR PROSPECTIVE CORPUS = NOT YET STARTED
ODDS / CONSTITUTION REDESIGN = FROZEN PENDING OUTCOME-BACKED EVIDENCE
```

Current product objective:

> **后台可以复杂，Human 前门必须稀缺。Human first view should normally show 0–3 genuinely attention-worthy tickers, or explicitly say nothing requires attention.**

Sector Radar is currently a separate market-observation surface. It has no canonical Human-wake authority and must not be inserted into the ticker-centric Attention Inbox before prospective shadow evidence is reviewed.

---

## 2. Architecture and authority

Decision Kernel remains a **Decision Hygiene layer, not a Truth Machine**.

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

The accepted Human-attention lanes remain exactly two:

```text
Research Funnel
→ DEEPEN_REQUIRED
→ Research-attention card

Decision Spine
→ HumanResearchSurface.attention_eligible == true
→ canonical Decision-review card
```

Sector Radar is not a third lane:

```text
Sector Radar shadow observation
!= DEEPEN_REQUIRED
!= canonical Decision wake
!= Recommendation
!= Action
```

Core doctrine:

```text
Evidence changes Belief.
Price changes Odds.

Research complete != Probability established != Odds ready.
Human owns the investment decision.
Investment Authority = NONE.
Frozen lineage is authoritative.
```

Not authorized:

```text
CONSTITUTION CHANGE
NEW KERNEL SCHEMA
NEW PROBABILITY STATE MACHINE
THIRD CANONICAL HUMAN WAKE
LIVE ODDS POLICY REPLACEMENT
COMPOSITE OPPORTUNITY SCORE AS AUTHORITY
```

---

## 3. Existing Attention Inbox and disclosure operations

### Ticker-centric Human front door

PR #139 and PR #140 remain authoritative product behavior:

- ticker-first, why-worth-looking-first and drill-down oriented;
- only unresolved `DEEPEN_REQUIRED` Research handoffs surface as Research attention;
- only `HumanResearchSurface.attention_eligible` creates canonical Decision review;
- quiet researched cases remain collapsed.

PR #144 remains the scheduled composition root. The weekday `decision-inbox` workflow keeps separate explicit lists:

```text
decision_packages
research_attention_handoffs
```

Current unresolved Research-attention list:

```text
EMPTY
```

The current numerical Decision package set remains curated to Moutai, China Shenhua, GigaDevice and Sanhua. CATL's old generic package is retained for audit, disclosures and non-authoritative observation but no longer creates a canonical numerical Decision wake.

### Disclosure memory

Quiet CNINFO assessments remain exact, lossy Harness receipts:

```text
cache hit → suppress only the exact reviewed identity
cache loss → reassess
receipt != Research truth
receipt != Human wake
```

The latest frozen 2026-09-04 new-packet result remains:

```text
DROP_FOR_NOW = 1
WAIT_FOR_TRIGGER = 1
DEEPEN_REQUIRED = 0
```

No disclosure packet currently earns Human Research attention.

### Current production workflows

After PR #184 cleanup, default branch contains only:

```text
apply-disclosure-assessment.yml
ci.yml
decision-inbox.yml
live-dogfood.yml
```

There is **no scheduled Sector Discovery Radar workflow yet**. Do not infer production activation from merged pure contracts, bootstrap data, closed experiment PRs or previous chat wording.

---

## 4. Current live cases

### CATL / 宁德时代 / 300750.SZ

```text
BUSINESS QUALITY = HIGH / ESTABLISHED
GLOBAL SHARE LEADERSHIP = ESTABLISHED
CHEAPNESS AT CNY351 = NOT ESTABLISHED
CARDINAL PROBABILITY = NOT ESTABLISHED
NUMERICAL ODDS = WITHHELD
HUMAN DECISION = NONE
ACTION = NONE
FOLLOWED = YES
PRICE TRIGGER = NONE
```

Reopen only on discriminating margin, owner-cash, supplier-finance, capex/utilisation, overseas-ROIC, capital-allocation or new-business owner-economics evidence.

### GigaDevice / 603986.SH

```text
HUMAN DECISION = CONDITIONAL BUY
~CNY350 = RE-UNDERWRITE
CNY320–335 = FIRST-ENTRY BAND ONLY IF THESIS SURVIVES
ACTION = NOT EXECUTED
```

### Sanhua / 002050.SZ

```text
RESEARCH = STOP / REOPEN
HUMAN DECISION = CONDITIONAL BUY AROUND CNY30
ACTION = NOT EXECUTED
ROBOT OPTIONALITY = NOT INDEPENDENTLY ESTABLISHED
```

### Tinavi / 688277.SH

```text
DECISION = WATCH / CONTINUE FOLLOWING
ACTION = NO_ACTION
RESEARCH = STOP CURRENT PUBLIC-DILIGENCE LOOP
```

Reopen only on payment implementation, procedure monetisation, owner-cash conversion, transaction economics or Reference-Frame evidence.

### Micron / MU

```text
DECISION = WAIT / DO NOT BUY FOR NOW
ACTION = NO_ACTION
NEXT NATURAL HINGE = 2026-09-30 FY2026/FQ4 EARNINGS
```

### Other existing cases

- YTO: Research complete enough to stop; cardinal probability not established; no Human decision.
- Midea: mature high-ROE global consumer-industrial franchise; no Human decision.
- Xiamen Tungsten: historical Reference-Frame failure negative control; no current action.

No live-case decision or action changed during the Sector Radar work.

---

## 5. Radar state

### 5.1 Sector Discovery Radar — accepted current state

The Human exposed a real false negative: agriculture, livestock, aquaculture and shipbuilding-related moves had developed for weeks before manual browsing found them. The old Surprise Radar could not discover them because it was limited to already-researched tickers.

PR #163 selected a native HiThink-only Harness design after prior-art and repository review:

```text
5 / 20 / 60-session relative strength
+ rank change / acceleration
+ persistence / trend age
+ turnover pulse
+ current constituent breadth for finalists
```

Rejected for v0:

```text
copying an external platform
composite opportunity score
LLM ranking authority
RRG or PELT as detector
new scientific-computing dependencies
multi-provider fallback
third canonical Human wake
Recommendation / Action / investment authority
```

PR #164 added the pure frozen-PIT calculation contract in `runtime/sector_radar.py`.

#### 881 broad-universe replay

PR #169 froze the experiment result:

```text
90 exact 881*.TI broad industries
+ CSI 300 benchmark
+ 104 frozen-PIT replay dates

EARLY DISCOVERY FOR AGRICULTURE / LIVESTOCK = DEMONSTRATED
TREND-AGE VISIBILITY = DEMONSTRATED
BROAD-ONLY SHIPBUILDING COVERAGE = FAILED
PRODUCTION THRESHOLD = NOT EARNED
```

The broad parent `881166.TI 军工装备` diluted the narrower `884183.TI 航海装备` move. It must not be relabelled as “shipbuilding.”

#### Separate 884 granular replay

PR #171 froze a separate 230-member `884*.TI` cross-sectional replay:

```text
NARROW-THEME COVERAGE = IMPROVED
884 AS PRIMARY HUMAN-FACING UNIVERSE = REJECTED
881 + 884 MIXED RANKING = PROHIBITED
884 = SEPARATE BOUNDED / SECONDARY CHALLENGER
```

The granular universe generated substantially more events and truncation than 881. It is useful for decomposition and narrow-theme recovery, not as an unfiltered replacement.

#### Current breadth proof

PR #173 established current constituent breadth as a useful finalist qualifier:

- advancers / decliners / unchanged;
- equal-weight mean and median return;
- current denominator and missing rows;
- turnover and positive-return concentration;
- leaders / laggards;
- current membership overlap and containment.

Boundaries:

```text
CURRENT CONSTITUENT BREADTH = CURRENT SESSION ONLY
HISTORICAL BREADTH = NOT ESTABLISHED / NOT CLAIMED
EQUAL-WEIGHT PROXY != INDEX CONTRIBUTION
```

Tiny groups such as two- or three-stock water-product industries must always expose denominator and concentration.

#### Provider identity contract

The live proof showed standard Shanghai indices may return provider ticker aliases:

```text
000001.SH -> 1A0001
000300.SH -> 1B0300
```

PR #175 accepts valid standard-index ticker aliases while preserving exact requested/returned `thscode` as canonical identity. Formal `.TI` industries still require ticker metadata to match their six-digit code.

#### Pure breadth and hierarchical composition

PR #176 added `runtime/sector_breadth.py`, a provider-agnostic, content-hashed current-breadth contract.

PR #177 added `runtime/sector_radar_shadow.py`:

- 881 and 884 remain separate homogeneous universes;
- only false-to-true state entries are emitted;
- unchanged strong sectors remain quiet;
- parent/child and sibling candidates may be grouped only with exact same-session membership evidence;
- full auditable groups are retained while the shadow display is capped at three;
- no canonical Attention Inbox insertion.

Current replay challengers remain descriptive, not promoted detector law:

```text
PERSISTENT TOP-DECILE ENTRY
ACCELERATING ENTRY
```

Do not retune or promote them before prospective evidence.

#### Current 881→884 hierarchy and parent hints

PR #179 froze the full current hierarchy:

```text
broad identities = 90
granular identities = 230
unique fully-contained child→parent mappings = 230
ambiguous children = 0
unmapped children = 0
```

Committed lookup:

```text
radar_inputs/sector-parent-hints-2026-09-05.json
```

This is a **current-PIT routing hint, not permanent taxonomy**.

PR #180 added candidate-time validation. Before grouping a surfaced 884 child:

```text
validate current catalog identity
→ load the exact frozen hint
→ fetch current child and hinted-parent memberships
→ revalidate full containment
→ group only if containment still holds
```

Do not perform a daily 320-membership fan-out. Catalog or containment drift must remain visible and block automatic grouping.

#### Rolling state and durable bootstrap

PR #181 added `runtime/sector_radar_state.py`:

- exactly 127 completed sessions;
- benchmark + exact 90/230 identities;
- deterministic content hash;
- exact previous/current replay;
- next-session-only append;
- every provider `prev_price` must match cached latest close;
- same-session identical rerun is idempotent;
- missed sessions, revisions, catalog drift or identity drift fail closed.

PR #182 committed the durable bootstrap:

```text
radar_inputs/sector-radar-state-bootstrap-2026-09-04.json.gz
radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json
docs/sector-radar-state-bootstrap-2026-09-04.md
```

Canonical bootstrap identity source:

```text
radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json
```

That manifest is the sole canonical source for the bootstrap state hash, byte sizes and hashes, formula, session window, universe shape and source lineage. This mutable index repeats only the compact operational identity below:

```text
latest completed session = 2026-09-04
rolling sessions = 127
series = 321
benchmark = 1
broad = 90
granular = 230
catalog hash = 367d64660f5ef1f715ae0ef1d832a180d075ec7d6fc0a915797cbfafbd33f360
state hash = 2963d7fa62757a56e7296b3d9855a7d6d067d59816738078361f86c51d1f41d7
```

It is only an initial state. It cannot bridge a missed completed session.

#### HiThink sector-breadth acquisition

PR #183 added strict current-membership and paginated all-A-share snapshot acquisition:

- exact `.TI` membership request;
- deterministic full-market pagination;
- every page must match the independently qualified completed session;
- stable declared total and unique identities;
- unpriced rows remain explicit;
- no fallback or stale substitution.

Its first post-merge main run exposed one omitted fail-closed check: a fake `ABCDEF.XY` row passed because only ticker-prefix equality was checked. PR #184 repaired this by requiring `^\d{6}\.(SH|SZ|BJ)$`, retained the regression and removed the accidentally retained one-time repair workflow.

Verified baseline after PR #184:

```text
main = e3d8611b40d7b59694d1d86a4d85c8342de1cd39
kernel-tests run = 33930589341
result = 342 passed
one-time repair workflow on main = ABSENT
```

### 5.2 What is not built yet

Despite the merged contracts and bootstrap:

```text
DAILY SECTOR RADAR PRODUCER = NOT MERGED
SCHEDULED SECTOR RADAR WORKFLOW = NOT PRESENT
PERSISTED FUTURE LIVE STATE = NOT YET CREATED
PROSPECTIVE SHADOW CANDIDATE CORPUS = EMPTY
T+5 / T+20 PROSPECTIVE EVALUATION = NOT STARTED
CANONICAL ATTENTION INBOX INSERTION = NOT AUTHORIZED
```

Closed experiment PRs and their artifacts are evidence lineage, not product runtime.

### 5.3 Existing Surprise Radar

The old ticker-scoped Surprise Radar remains a separate product for already-researched cases.

Accepted reviewed baseline remains:

```text
eligible post-Research daily observations = 10
securities = 6
largest absolute eligible daily move = 2.74% / CATL / 2026-09-02
qualified anomaly label = NOT YET EARNED
detector = NOT PROMOTED
```

Do not turn 2.74% into a threshold.

### 5.4 Commitment Radar

Commitment Radar remains an attention allocator for frozen commitments that can now be resolved or falsified. It does not create a second attention authority.

---

## 6. Next work

### P0 — independent prospective Sector Radar shadow producer

Build from clean, green `main`; keep it separate from `decision-inbox`.

Required flow:

```text
durable 2026-09-04 bootstrap or later exact persisted state
→ current formal-industry catalog
→ independently qualified completed-session index snapshot
→ direct continuity check against cached last closes
→ append exactly one new completed session
→ reconstruct previous/current 881 and 884 snapshots
→ detect false→true shadow entries
→ 881 primary + bounded 884 secondary
→ revalidate parent hints only for surfaced granular candidates
→ hierarchical deduplication
→ current breadth only for finalists
→ retain full audit artifact
→ render normally 0–3 shadow groups
```

Operational requirements:

1. No missed-session bridging. A stale bootstrap after more than one completed session must fail closed and require an explicit recovery procedure.
2. Same-session reruns must be exactly idempotent; changed values must fail.
3. Catalog hash or identity drift must be visible.
4. Market-state persistence and candidate-state persistence must be content hashed and source identified.
5. State restoration failure must never silently reset the Radar.
6. Current breadth fetches only finalists; do not fan out memberships for all 320 industries daily.
7. All output must prominently retain:
   ```text
   SHADOW OBSERVATION ONLY
   HUMAN ATTENTION AUTHORITY = NONE
   INVESTMENT AUTHORITY = NONE
   ```
8. Keep a separate GitHub Summary/artifact. Do not insert Sector Radar directly into the canonical ticker Inbox.

### P1 — prospective evaluation after real candidates exist

For each first prospective candidate, freeze signal-time identity and later calculate objective T+5/T+20 path outcomes without relabelling the original observation.

Do not tune thresholds until a real prospective corpus exists. False positives, false negatives, repeated-state suppression and 0–3 compression all need prospective review.

### P1 — existing operations

- add only exact unresolved `DEEPEN_REQUIRED` handoffs to the scheduled Research-attention list;
- remove them when Full Research or Human disposition resolves the request;
- continue current disclosure receipt discipline;
- maintain Tinavi, CATL, Sanhua, GigaDevice and Micron only on their stated reopen evidence;
- freeze real Human Decision / Action / Outcome lineage promptly.

---

## 7. Do not do

```text
no new probability enum
no EconomicSpecies schema / router
no third canonical Human wake
no Sector Radar → automatic Research route
no Sector Radar → Recommendation / Action
no composite opportunity score
no mixed 881 / 884 percentile ranking
no current membership backfilled into history
no parent hint treated as permanent taxonomy
no daily 320-membership fan-out
no retry-until-favourable experiment
no fallback provider or stale-price substitution
no missed-session bridge
no silent state reset after cache loss
no threshold tuning to one retrospective replay
no price → Fundamental Belief shortcut
no forced cardinal probabilities
no broker / portfolio ledger inside Kernel
```

Also do not treat a strong sector as proof that every constituent has the same economic exposure. Sector discovery must eventually pass through company mapping and the existing Research Funnel before any Research budget is allocated.

---

## 8. Authoritative entry pointers

### Cross-conversation

- `docs/project-state.md` — mutable current-state index.
- `docs/handoffs/2026-09-05-sector-radar-next-conversation.md` — next-conversation instructions.

### Sector Radar decisions and evidence

- `docs/sector-discovery-radar-prior-art-and-v0-decision-2026-09-04.md`
- `docs/sector-discovery-radar-hithink-acquisition-proof-2026-09-04.md`
- `docs/sector-discovery-radar-frozen-pit-replay-result-2026-09-04.md`
- `docs/sector-discovery-radar-884-replay-result-2026-09-04.md`
- `docs/sector-discovery-radar-current-breadth-proof-2026-09-04.md`
- `docs/sector-discovery-radar-full-current-hierarchy-result-2026-09-05.md`
- `docs/sector-radar-state-bootstrap-2026-09-04.md`

### Sector Radar runtime and data

- `src/decision_kernel/runtime/sector_radar.py`
- `src/decision_kernel/runtime/sector_breadth.py`
- `src/decision_kernel/runtime/sector_radar_shadow.py`
- `src/decision_kernel/runtime/sector_parent_hints.py`
- `src/decision_kernel/runtime/sector_radar_state.py`
- `src/decision_kernel/adapters/hithink_index.py`
- `src/decision_kernel/runtime/hithink_index_http.py`
- `src/decision_kernel/runtime/hithink_sector_breadth_http.py`
- `radar_inputs/sector-parent-hints-2026-09-05.json`
- `radar_inputs/sector-radar-state-bootstrap-2026-09-04.json.gz`
- `radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json`

### Existing Human system

- `docs/decision-inbox.md`
- `src/decision_kernel/runtime/attention_inbox.py`
- `.github/workflows/decision-inbox.yml`
- `docs/live-decision-book.md`

---

## 9. Recent state delta

- **PR #163–#164:** prior-art decision and pure Sector Radar calculation contract merged.
- **PR #169:** broad 881 replay frozen as a partial pass; agriculture/livestock early discovery demonstrated, broad-only shipbuilding coverage rejected.
- **PR #171:** separate 884 replay frozen; narrow-theme coverage improved, but 884 rejected as the primary unfiltered universe.
- **PR #173:** current breadth value and parent-child overlap risk established; historical breadth remains unclaimed.
- **PR #175–#177:** provider alias fix, pure breadth contract and hierarchical shadow composition merged.
- **PR #179–#180:** full current 881→884 hierarchy and candidate-time parent-hint validation merged.
- **PR #181–#182:** content-hashed rolling market state and durable 2026-09-04 bootstrap merged.
- **PR #183:** strict HiThink sector membership / all-market snapshot acquisition merged.
- **PR #184:** repaired the post-merge A-share identity gap, retained the regression, removed the leaked one-time workflow and restored `main` to `342 passed`.
- **UNCHANGED:** no scheduled Sector Radar producer, no prospective candidate corpus, no canonical Inbox insertion, no Research route, no Recommendation, no Action, no investment authority.
