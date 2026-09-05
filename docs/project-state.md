# Decision Kernel — Current Project State

Status: **MUTABLE CURRENT-STATE INDEX / NOT AUTHORITATIVE OVER FROZEN LINEAGE / NO NEW KERNEL SCHEMA**  
Updated: **2026-09-05**  
Repository: `auguspp/decision-kernel`  
Verified implementation baseline before this state-only sync: `d0c18690f406d2a2d90b32048ede37f643669a93`

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
SECTOR RADAR PURE DAILY COMPOSITION ROOT = MERGED
SECTOR RADAR MANUAL WORKFLOW_DISPATCH PRODUCER = MERGED
SECTOR RADAR LIVE WORKFLOW PROOF = NOT YET EXECUTED
SECTOR RADAR SCHEDULE = NOT PRESENT
SECTOR RADAR PROSPECTIVE CORPUS = NOT YET STARTED
ODDS / CONSTITUTION REDESIGN = FROZEN PENDING OUTCOME-BACKED EVIDENCE
```

Current product objective:

> **后台可以复杂，Human 前门必须稀缺。Human first view should normally show 0–3 genuinely attention-worthy tickers, or explicitly say nothing requires attention.**

Sector Radar remains a separate shadow market-observation surface. The existence of a manual workflow does not create a canonical Human wake, a Research route or investment authority.

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

## 3. Existing Human and disclosure operations

### Ticker-centric Human front door

PR #139 and PR #140 remain authoritative product behavior:

- ticker-first, why-worth-looking-first and drill-down oriented;
- only unresolved `DEEPEN_REQUIRED` Research handoffs surface as Research attention;
- only `HumanResearchSurface.attention_eligible` creates canonical Decision review;
- quiet researched cases remain collapsed.

PR #144 remains the scheduled Attention Inbox composition root. It keeps separate explicit lists:

```text
decision_packages
research_attention_handoffs
```

Current unresolved Research-attention list:

```text
EMPTY
```

The current numerical Decision package set remains curated to Moutai, China Shenhua, GigaDevice and Sanhua. CATL's old generic package remains audit and observation input but does not create a canonical numerical Decision wake.

### Disclosure memory

Quiet CNINFO assessments remain exact, lossy Harness receipts:

```text
cache hit → suppress only the exact reviewed identity
cache loss → reassess
receipt != Research truth
receipt != Human wake
```

Latest frozen 2026-09-04 new-packet result:

```text
DROP_FOR_NOW = 1
WAIT_FOR_TRIGGER = 1
DEEPEN_REQUIRED = 0
```

No disclosure packet currently earns Human Research attention.

### Current workflow directory

Default branch now contains five formal workflows:

```text
apply-disclosure-assessment.yml
ci.yml
decision-inbox.yml
live-dogfood.yml
sector-radar-shadow.yml
```

`sector-radar-shadow.yml` is **manual `workflow_dispatch` only**. It has no `schedule`, is separate from `decision-inbox.yml`, and rejects GitHub job reruns in favour of a fresh dispatch identity.

No successful Sector Radar workflow run or persistent state artifact has yet been produced. Do not infer live activation from the merged workflow file alone.

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

No live-case decision or action changed during the Sector Radar producer work.

---

## 5. Sector Discovery Radar

### 5.1 Accepted discovery design

The Human exposed a real false negative: agriculture, livestock, aquaculture and shipbuilding-related moves had developed for weeks before manual browsing found them. Sector Radar addresses cold-start market discovery that the ticker-scoped Surprise Radar cannot perform.

Selected native HiThink-only observation family:

```text
5 / 20 / 60-session relative strength
+ rank change / acceleration
+ persistence / trend age
+ turnover pulse
+ current constituent breadth for finalists
```

Rejected for v0:

```text
composite opportunity score
LLM ranking authority
RRG or PELT as detector
new scientific-computing dependencies
multi-provider fallback
third canonical Human wake
Recommendation / Action / investment authority
```

### 5.2 Frozen replay evidence

#### 881 broad layer

The 90-member `881*.TI` replay demonstrated early-enough agriculture and livestock discovery and trend-age visibility, but broad-only shipbuilding coverage failed. `881166.TI 军工装备` must not be relabelled as shipbuilding.

#### 884 granular layer

The separate 230-member `884*.TI` replay recovered narrow themes including marine equipment and water-product distinctions, but generated materially more noise and truncation.

```text
881 = primary broad comparison layer
884 = separate bounded granular challenger / decomposition layer
881 + 884 mixed ranking = PROHIBITED
```

#### Current breadth

Current constituent breadth is accepted as a finalist qualifier:

```text
advancers / decliners / unchanged
priced denominator and coverage
mean and median return
turnover and positive-return concentration
leaders / laggards
current membership hash and capture clock
```

Boundaries:

```text
CURRENT CONSTITUENT BREADTH = CURRENT SESSION ONLY
HISTORICAL BREADTH = NOT ESTABLISHED / NOT CLAIMED
EQUAL-WEIGHT PROXY != INDEX CONTRIBUTION
```

Tiny groups must expose denominator and concentration.

### 5.3 Hierarchy and provider contracts

The frozen current hierarchy contains:

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

It is a current-PIT routing hint, not permanent taxonomy. Every surfaced 884 candidate must revalidate the current catalog and exact child containment inside its hinted 881 parent. There is no daily 320-membership fan-out.

Standard Shanghai index provider aliases remain accepted only under the exact requested/returned `thscode` identity contract. A-share constituent and stock snapshot identities require `^\d{6}\.(SH|SZ|BJ)$`.

#### Rolling state and durable bootstrap

The rolling state contract provides:

- exactly 127 completed sessions;
- benchmark plus exact 90/230 identities;
- deterministic content hash;
- exact previous/current replay;
- one-next-session append;
- every provider `prev_price` matching the cached latest close;
- same-session exact idempotence;
- fail-closed revisions, catalog drift, identity drift and missed sessions.

Committed bootstrap files:

```text
radar_inputs/sector-radar-state-bootstrap-2026-09-04.json.gz
radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json
docs/sector-radar-state-bootstrap-2026-09-04.md
```

Canonical bootstrap identity source:

```text
radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json
```

That manifest is the sole canonical source for the bootstrap state hash, byte sizes and hashes, formula, session window, universe shape and source lineage. This mutable index repeats only the compact operational identity:

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

Merged acquisition contracts provide:

- exact `.TI` membership request;
- qualified complete index snapshot;
- normalized A-share trading calendar;
- deterministic paginated all-A-share snapshot;
- every page matching the independently qualified completed session;
- stable declared total and unique identities;
- explicit unpriced rows;
- no fallback or stale substitution.

### 5.4 Pure prospective composition root — merged in PR #187

`runtime/sector_radar_daily.py` now composes one daily run in two pure phases:

```text
market state + current catalog + qualified index snapshot
→ append or exact same-session no-op
→ reconstruct previous/current 881 and 884 snapshots
→ calculate false→true separately
→ create exact enrichment plan

planned memberships + one same-session all-A snapshot
→ candidate-time parent revalidation
→ breadth for every candidate
→ hierarchical composition
→ complete artifact
→ 0–3 shadow projection
```

The acquisition safety cap is:

```text
32 distinct membership requests per run
```

It is an operations guard only. If exceeded, the full candidate/request plan remains auditable and finalization fails; the system never silently enriches only the top three.

`runtime/sector_radar_events.py` provides a content-hashed append-only candidate event ledger:

```text
previous/current market state = sole false→true authority
candidate event ledger = immutable audit / idempotence / later outcome anchor only
signal-transition authority = NONE
```

### 5.5 Manual prospective producer — merged in PR #188

`runtime/sector_radar_producer.py`, `runtime/sector_radar_persistence.py` and `.github/workflows/sector-radar-shadow.yml` now provide a manual operational shell.

Persistence discipline:

```text
newest prior successful workflow state artifact = restore authority
Actions cache = byte-identical acceleration copy only
cache/artifact disagreement = fail closed
latest artifact missing or expired = explicit qualified recovery required
older artifact fallback = prohibited
committed bootstrap = first successful run only
artifact retention = 90 days
automatic long-term checkpoint = not implemented
```

Completed-session discipline:

```text
latest completed == cached session
→ exact validation only
→ no membership fetch
→ no retrospective event append

exactly one completed session follows cached state
→ require direct calendar continuity
→ append exactly once
→ prospective composition

more than one completed session follows cached state
→ fail closed
→ no bridge
```

Workflow output remains a separate GitHub Summary and audit artifact. The workflow has no schedule and no canonical Inbox insertion.

### 5.6 What still has not happened

Despite the merged code and manual workflow:

```text
SUCCESSFUL SECTOR RADAR WORKFLOW RUN = NONE
PERSISTENT LIVE STATE ARTIFACT = NONE
PERSISTENT LIVE CACHE = NONE
SAME-SESSION PROVIDER VALIDATION PROOF = NOT EXECUTED
2026-09-07 DIRECT APPEND PROOF = NOT EXECUTED
PROSPECTIVE SHADOW CANDIDATE CORPUS = EMPTY
OBJECTIVE T+5 / T+20 EVALUATION = NOT STARTED
HUMAN REVIEW ANNOTATION = NOT STARTED
SCHEDULED SECTOR RADAR WORKFLOW = NOT PRESENT
CANONICAL ATTENTION INBOX INSERTION = NOT AUTHORIZED
```

Merged prerequisites are not evidence that the producer has successfully contacted HiThink or persisted a prospective state.

---

## 6. Next work

### P0 — first fresh manual validation dispatch

Run a new `workflow_dispatch` from `main`, not a GitHub job rerun.

On 2026-09-05, the expected qualified completed session is still 2026-09-04. Therefore the first proof should be:

```text
verified committed bootstrap
→ current catalog
→ exact same-session qualified 321-series snapshot
→ market-state equality validation
→ no membership acquisition
→ no retrospective candidate event
→ new 90-day state artifact
```

Any state, turnover, catalog or provider identity disagreement remains a real proof failure and must not be weakened silently.

### P0 — fresh same-session idempotence dispatch

After the first successful run, start a second fresh `workflow_dispatch`:

```text
restore latest successful artifact
+ restore cache acceleration copy
→ require exact agreement
→ validate same completed session
→ market-state hash unchanged
→ event-ledger hash unchanged
→ zero prospective events
```

Do not use “rerun jobs,” because it reuses a run identity.

### P0 — first direct completed-session append

The bootstrap's direct next A-share session is:

```text
2026-09-07
```

A first real append may occur only against that completed session. If ordinary production first sees 2026-09-08 or later while restored state still ends at 2026-09-04, it must fail closed and use a separate qualified recovery procedure.

### P1 — objective outcomes and Human review

After the first real prospective false→true event, keep three layers separate:

```text
SignalEvent
→ immutable signal-time path, breadth and hierarchy

ObjectiveOutcomeRecord
→ T+5 / T+20 sector, benchmark and excess return
→ MFE / MAE
→ rank and gate persistence

HumanReviewAnnotation
→ whether Human had already noticed the move
→ whether it formed a useful Research question
→ reviewer, review time and rationale
```

Human annotation must not overwrite the signal event or enter the objective outcome hash. Do not tune thresholds until a meaningful prospective corpus exists.

---

## 7. Do not do

```text
no new probability enum
no third canonical Human wake
no Sector Radar → automatic Research route
no Sector Radar → Recommendation / Action
no composite opportunity score
no mixed 881 / 884 percentile ranking
no current membership backfilled into history
no parent hint treated as permanent taxonomy
no daily 320-membership fan-out
no silent top-three-only breadth enrichment
no fallback provider or stale-price substitution
no missed-session bridge
no silent state reset after cache loss
no older-artifact fallback after latest-artifact loss
no GitHub rerun of a state-producing run
no threshold tuning to retrospective examples
no price → Fundamental Belief shortcut
no forced cardinal probabilities
no broker / portfolio ledger inside Kernel
```

A strong sector remains only a discovery fact. It does not prove every constituent has equal exposure, company revenue or profit, owner cash, cheapness, probability or Odds.

---

## 8. Authoritative entry pointers

### Cross-conversation

- `docs/project-state.md` — mutable current-state index.
- `docs/handoffs/2026-09-05-sector-radar-manual-producer-next.md` — latest next-conversation instructions.
- `docs/handoffs/2026-09-05-sector-radar-next-conversation.md` — prior prerequisite handoff retained for lineage.

### Sector Radar decisions and evidence

- `docs/sector-discovery-radar-prior-art-and-v0-decision-2026-09-04.md`
- `docs/sector-discovery-radar-frozen-pit-replay-result-2026-09-04.md`
- `docs/sector-discovery-radar-884-replay-result-2026-09-04.md`
- `docs/sector-discovery-radar-current-breadth-proof-2026-09-04.md`
- `docs/sector-discovery-radar-full-current-hierarchy-result-2026-09-05.md`
- `docs/sector-radar-state-bootstrap-2026-09-04.md`
- `docs/sector-radar-prospective-producer-operations.md`

### Sector Radar runtime and data

- `src/decision_kernel/runtime/sector_radar.py`
- `src/decision_kernel/runtime/sector_breadth.py`
- `src/decision_kernel/runtime/sector_radar_shadow.py`
- `src/decision_kernel/runtime/sector_parent_hints.py`
- `src/decision_kernel/runtime/sector_radar_state.py`
- `src/decision_kernel/runtime/sector_radar_events.py`
- `src/decision_kernel/runtime/sector_radar_daily.py`
- `src/decision_kernel/runtime/sector_radar_persistence.py`
- `src/decision_kernel/runtime/sector_radar_producer.py`
- `src/decision_kernel/runtime/hithink_index_http.py`
- `src/decision_kernel/runtime/hithink_sector_breadth_http.py`
- `.github/workflows/sector-radar-shadow.yml`
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

- **PR #184:** repaired strict A-share identity validation, retained regression coverage and removed the leaked one-time workflow.
- **PR #185:** synchronized the prerequisite-era state and handoff.
- **PR #186:** made the committed bootstrap manifest the sole canonical bootstrap identity source and added dynamic documentation consistency coverage.
- **PR #187:** merged the pure two-phase daily composition root, exact acquisition plan, deterministic full artifact/summary and append-only event ledger.
- **PR #188:** merged the manual `workflow_dispatch` producer, artifact-authoritative persistence, exact cache conflict checks, 90-day retention, direct-session discipline and separate shadow output.
- **VERIFIED IMPLEMENTATION BASELINE:** `d0c18690f406d2a2d90b32048ede37f643669a93`, main CI run `33934306867`, `374 passed`.
- **NOT YET PROVEN LIVE:** no Sector Radar workflow run, state artifact, future market-state append, prospective candidate, T+5/T+20 outcome or canonical Inbox insertion.
- **UNCHANGED AUTHORITY:** no Research route, Recommendation, Action or investment authority.
