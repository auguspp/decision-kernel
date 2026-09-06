# Decision Kernel — Current Project State

Status: **MUTABLE CURRENT-STATE INDEX / NOT AUTHORITATIVE OVER FROZEN LINEAGE / NO NEW KERNEL SCHEMA**  
Updated: **2026-09-05**  
Repository: `auguspp/decision-kernel`  
Last independently verified live Sector Radar implementation: `5f8f635d191dd8559844d1b74af0dca0cf4c02df`

## Operating rule

This file is the default cross-conversation entry point. Frozen Research, Human Decision, Action and Outcome artifacts remain authoritative over this mutable index.

```text
New conversation: read this file and the latest handoff, then verify current main.
End of conversation: sync only real state deltas.
```

Do not trust a chat summary over repository state, frozen lineage, CI results or real workflow artifacts.

Latest implementation handoff: `docs/handoffs/2026-09-05-stock-primary-sources-next.md`. Prior handoffs and failed probes are retained for lineage. Completing a row comparison or acquiring original sources does not establish production qualification; a bounded directory scan is not complete publisher coverage or accepted economic evidence.

Human implementation preference: **reuse mature wheels before building generic infrastructure**. Prefer exact official structured data/feeds, maintained source adapters and mature libraries. Bespoke code is for missing project-specific identity, time/version, review and authority contracts, not another parser/crawler/queue. See `docs/radar-reuse-decision-2026-09-05.md`.

---

## 1. Current phase

```text
TRUSTWORTHY COGNITION CORE = STABLE / DO NOT EXPAND WITHOUT REAL FAILURE
ATTENTION ACQUISITION = ACTIVE HIGHEST PRIORITY
HUMAN ATTENTION SURFACE = ACCEPTED / MERGED / ACTIVE
SECTOR RADAR PURE DAILY COMPOSITION ROOT = MERGED
SECTOR RADAR MANUAL WORKFLOW_DISPATCH PRODUCER = MERGED
SECTOR RADAR LIVE SAME-SESSION VALIDATION = PROVEN
SECTOR RADAR LIVE ARTIFACT/CACHE RESTORE = PROVEN
SECTOR RADAR INPUT AUDIT / OFFLINE REPLAY = IMPLEMENTED / SYNTHETICALLY TESTED
SECTOR RADAR READ-ONLY CONTEXT = WORKFLOW ARTIFACT WIRING MERGED / LIVE PUBLICATION PENDING
HITHINK STOCK DUMP = REAL ROW INSPECTION COMPLETED / DIFFERENCES_REQUIRE_REVIEW / NO PRODUCTION ADOPTION
STOCK FIELD SOURCE STUDY = 15 EVENT RECORDS + TWO ISSUER ORIGINALS OBTAINED / NO AUTOMATIC ADJUSTMENT
ECONOMIC NODES = TWO BOUNDED PUBLIC-EXCERPT PILOTS / NO AUTOMATED FEED
ECONOMIC RAW CAPTURE = FOUR REVIEWED PAGES MATCHED / PRIOR INCOMPLETE PROOF RETAINED / NO CONTINUOUS FEED
ECONOMIC RELEASE DISCOVERY = BEAUTIFUL SOUP REUSED / DIRECT SPB STATISTICS WINDOW PROVEN / ZERO LIVE NEW DETAIL PACKETS
SECTOR RADAR NEW COMPLETED-SESSION APPEND = NOT YET PROVEN LIVE
SECTOR RADAR SCHEDULE = NOT PRESENT
SECTOR RADAR PROSPECTIVE CORPUS = EMPTY
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

Default branch now contains nine formal workflows:

```text
apply-disclosure-assessment.yml
ci.yml
decision-inbox.yml
economic-release-discovery.yml
economic-source-capture.yml
hithink-stock-dump-trial.yml
live-dogfood.yml
sector-radar-shadow.yml
stock-field-source-study.yml
```

`sector-radar-shadow.yml` is **manual `workflow_dispatch` only**. It has no `schedule`, is separate from `decision-inbox.yml`, and rejects GitHub job reruns in favour of a fresh dispatch identity.

`economic-source-capture.yml` is an independent public-only compatibility probe: manual dispatch or tightly path-filtered main pushes, at most four reviewed pages, no credentials, market cache or state access, and no schedule. Its first real run `33947395994` is **failure / INCOMPLETE**, not green: two SPB pages matched and two MOA requests failed with HTTPError. Its uploaded artifact preserves both outcomes. Kernel tests on that same commit succeeded; unit-test success does not override the source failure.

A later controlled diagnostic run `33949122077` on `386f12112e56089d2c76822ed342c4f084ff3b85` returned HTTP 200 and matched all four reviewed pages. It is a separate success / COMPLETE proof, not a rewrite of the first failure or continuous monitoring. The earlier HTTP codes and cause remain unknown because that rejection did not recur. See section 5.12.

`economic-release-discovery.yml` separately checks two fixed official directory windows, with at most four planned article requests and no automatic fact acceptance. It runs manually on main or for narrowly scoped main code/workflow changes, without secrets, market cache or a schedule. First live run `33952315592` succeeded as a bounded scan with two directory requests and zero eligible detail requests; this is not complete publisher coverage. See section 5.13. It now installs optional `.[discovery]` and uses Beautiful Soup; the current direct-statistics proof and retained script-stub failure are in section 5.14.

`hithink-stock-dump-trial.yml` is an isolated compatibility study, not a Sector state producer. It uses optional Requests/PyArrow and the existing HiThink secret only during acquisition, has fresh-main/manual or narrow main-path triggers, and has no schedule or market cache/state access. Run `33957604949` first retained a Parquet file but stopped at reference-date qualification. The later run `33959190974` completed all stock pages and full row inspection, retaining DIFFERENCES_REQUIRE_REVIEW rather than adopting data. See sections 5.15–5.16; both workflows remain failure evidence for their respective scopes.

`stock-field-source-study.yml` restores the fixed prior comparison artifact, verifies its hashes and collects only identified event/history/issuer-notice evidence. It is a retained isolated manual/narrow-main-path study with read-only permissions, no schedule, market cache or state access. Run `33963949084` obtained 21 source bodies; collection success does not change price acceptance. See section 5.17.

Runs `33938625934` and `33939414197` succeeded. They proved live bootstrap validation and subsequent artifact/cache restoration at the same completed session, 2026-09-04. They did not append a new market session or create prospective candidates. Full evidence is frozen in `docs/sector-radar-live-bootstrap-restore-proof-2026-09-05.md`.

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

PR #190 removed the unnecessary requirement for a future calendar row during same-session validation. PR #191 qualified index snapshots using their documented data-ready timestamp semantics, completed benchmark prices and the normalized calendar. Neither repair introduced a fallback provider or relaxed exact market-state equality.

Workflow output remains a separate GitHub Summary and audit artifact. The workflow has no schedule and no canonical Inbox insertion.

### 5.6 Live validation and recovery — proven on 2026-09-05

```text
FIRST SUCCESSFUL LIVE VALIDATION = run 33938625934 / workflow #3 / attempt 1
SAME-SESSION RESTORE PROOF = run 33939414197 / workflow #4 / attempt 1
EXECUTED IMPLEMENTATION = 5f8f635d191dd8559844d1b74af0dca0cf4c02df
LATEST VERIFIED RESTORE SOURCE = LATEST_SUCCESS_ARTIFACT
LATEST STATE ARTIFACT = 9961284050
LATEST RUN AUDIT ARTIFACT = 9961283551
LATEST SAVED CACHE KEY = sector-radar-state-33939414197-1
STATE SESSION = 2026-09-04
MARKET STATE AND EVENT LEDGER BETWEEN RUNS = BYTE-FOR-BYTE UNCHANGED
PROSPECTIVE EVENTS = 0
```

Run #4 restored run #3's artifact and cache, passed their consistency checks, validated the same completed session and published the next provenance wrapper. Its market state and candidate-ledger file bytes remained identical to run #3. The per-run bundle manifest and ZIP hashes changed normally with run identity and update time.

Artifact digests, content-hash reconciliation, cache-log evidence and review limitations are frozen in `docs/sector-radar-live-bootstrap-restore-proof-2026-09-05.md`. The two earlier failed runs remain failure evidence; they did not publish a successful state bundle.

### 5.7 What still has not happened

```text
2026-09-07 DIRECT APPEND PROOF = NOT EXECUTED
LIVE CANDIDATE-TIME HIERARCHY/BREADTH IN THIS PRODUCER = NOT EXERCISED
LIVE REPLAYABLE INPUT AUDIT PROOF = NOT EXECUTED
LIVE SECTOR CONTEXT ARTIFACT PUBLICATION = NOT EXECUTED
PROSPECTIVE SHADOW CANDIDATE CORPUS = EMPTY
OBJECTIVE T+5 / T+20 EVALUATION = NOT STARTED
HUMAN REVIEW ANNOTATION = NOT STARTED
SCHEDULED SECTOR RADAR WORKFLOW = NOT PRESENT
CANONICAL ATTENTION INBOX INSERTION = NOT AUTHORIZED
```

The successful same-session runs are not a new-session screen showing no market opportunities. They deliberately perform validation only and create no retrospective candidate events.

### 5.8 Replayable input audit and full-path offline tests — PR #193

`runtime/sector_radar_audit.py` now records bounded decoded provider JSON, exact input states, parent hints, request identities and clocks, implementation hashes and expected calculation outputs. The live CLI stages state, seals and validates the audit, then publishes using the existing transactional bundle writer. No credential headers or environment snapshots are retained.

New-session `observations.json` retains complete previous/current 881 and 884 snapshots separately, plus diagnostics from the existing gate predicates. Offline replay checks the sealed input inventory, source-manifest relationships, request order, clocks and every regenerated output byte; it has no network or production-state output path.

Synthetic integration tests execute real adapters, relative strength, false-to-true gates, hierarchy, breadth, event append, artifact/cache resolution and same-session idempotence. They also cover interrupted acquisition, tampered inputs and failure before or during state publication. These are implementation tests, not live HiThink evidence or prospective events.

The audit contract, replay command, operational budgets and limits are documented in `docs/sector-radar-input-audit-and-offline-replay.md`. Existing run #3/#4 artifacts cannot be retroactively upgraded to this input format. The workflow definition, schedule, signal policy, live state and investment authority are unchanged.

### 5.9 Fuller Radar — first isolated slices, PR #194–#196

The approved expansion preserves the market detector while adding better state reading, independently qualified stock-data research and economic-source observations. The first slices are additive; they do not establish a complete continuous multi-channel Radar.

**PR #194 — saved-state context.** `runtime/sector_radar_context.py` produces an on-demand HTML/JSON report from a validated state bundle. It shows active, weakening/exited and full industry paths separately for 881 and 884, including raw sector/benchmark/excess returns and censor-aware trend age. It distinguishes trend start, unavailable system-first-observed time and recorded prospective-event time. Presentation labels do not change gates or create events. No breadth is carried forward. It was initially a standalone CLI; PR #198 added workflow artifact wiring described below, not public hosting.

**PR #195 — stock-dump integrity study.** `runtime/hithink_dump_inspection.py` checks local recent-ten-session rows against an explicit calendar, stock universe and snapshot. It exposes missing/unpriced rows, unit/schema discrepancies and raw-previous-close differences requiring corporate-action review. That slice tested pure Python rows only; it did not establish a real download, physical Parquet decoding, overlapping-vintage revisions or production qualification. PyArrow was then optional but not installed by the project. Later optional-library tests and actual partial delivery evidence are recorded in section 5.15; no stock panel or multi-day breadth is activated.

**PR #196 — two economic-source pilots.** `runtime/economic_node_study.py` parses four reviewed official MOA/SPB excerpts saved in `radar_inputs/economic-node-study-2026-09-05.json`: two livestock/feed weeks and two express-business months. It separates period, date-only publication and actual capture, preserves immutable versions and descriptive comparisons, and does not backdate system-PIT availability. Express revenue per parcel is a rounded mix proxy, not like-for-like price or profit. These are manually reviewed public-source studies, not full HTTP capture, automated feeds, historical first-vintage proof, company mapping, fundamental-state confirmation or market candidate events. Later raw captures retain new, separate capture-time records; they do not rewrite these original studies.

The implementation baseline after these three PRs is `f7f5aa9e7433a4d1d75fb6e05fb3e8aadb16c2e9`; full CI contains 463 passing tests. Its test success does not replace the older, explicitly identified live operational proof. No workflow definition, schedule, signal threshold, live market state, candidate ledger or company decision changed in these slices.

### 5.10 Read-context artifact delivery — PR #198

The existing manual Sector workflow renders `context/index.html` and `context/context.json` after successful producer calculation and includes them in its complete run artifact. The summary links the actual uploaded artifact only after successful rendering and upload. This is a downloadable self-contained page, not a hosted dashboard or a new alert surface.

Rendering reads the exact saved bundle with no HiThink credential or network request. It does not modify market state, ledger or the sealed calculation audit. A rendering failure remains visible and blocks remote state-artifact/cache publication; a calculated local bundle or retained page alone is not proof that the whole workflow succeeded. Tests cover quiet/candidate bundle rendering, local packaging and byte preservation. A new live Sector dispatch has not yet exercised this delivery path.

### 5.11 Official raw-source capture — PR #199–#200

`runtime/economic_source_capture.py` archives original bounded response-body bytes for explicitly reviewed MOA/SPB URLs, safe headers and actual request/capture clocks. It binds selected reviewed text to those bodies and reconstructs accepted/rejected bindings offline. No redirects, credentials, cookies, automatic retries, fallback or linked resources are used. Budgets are four sources, 2 MiB/body and 20 MiB/archive; source changes remain visible rather than silently replacing reviewed facts.

The first real compatibility run `33947395994` on `1c19360e5b400933339f452ba159117d5a8408e2` produced:

```text
SPB raw pages + reviewed bindings = 2 / 2 matched
MOA raw pages = 0 / 2 obtained; HTTPError
aggregate = INCOMPLETE
workflow = failure
proof artifact = 9963755766
capture archive integrity = VERIFIED, still INCOMPLETE
market state / candidate event writes = 0
```

The proof artifact was downloaded and its ZIP, inventory, file/content hashes, original-body text and binding offsets checked independently. The recorded workflow verifier reconstructed observations from raw inputs. Detailed hashes and limits are in `docs/economic-source-raw-capture-proof-2026-09-05.md`.

That first version did not retain numeric HTTP status for the MOA errors, so their exact HTTP cause is unknown. The two failures must not be reclassified as successful source capture, a permanent outage or evidence of source revision. At that proof stage there was no directory-discovery implementation. Historical first-vintage proof and continuous industry monitoring remain unestablished; the older reviewed snippets and live Sector state are unchanged.

### 5.12 Safe HTTP diagnostics and four-page proof — PR #202

Capture schema 2 records exact numeric HTTP status or explicit null, without retaining HTTPError bodies, server messages, credentials or redirect targets. It verifies status against response metadata and reconstructs the diagnostic summary. Older archives require their exact recorded implementation; no old HTTP status is inferred or backfilled. Full PR CI `33949060448` passed 532 tests; main kernel CI `33949122096` succeeded.

One controlled post-merge public compatibility run `33949122077` on `386f12112e56089d2c76822ed342c4f084ff3b85` returned HTTP 200 for all four original reviewed URLs and matched all four excerpts. The workflow completed successfully; archive status is COMPLETE and offline integrity is VERIFIED. Artifact `9964235933` retains all four raw bodies. After download, independent checks reconciled its ZIP digest, 25 file entries, hashes, raw text, fragment offsets, capture clocks and descriptive metric arithmetic. The two SPB raw bodies equal the prior capture byte for byte; the MOA bodies have no earlier retained body for comparison.

This new success does not explain the old failure: the earlier rejection did not recur and request headers/URLs were unchanged. Its old codes and cause remain unknown, and the original INCOMPLETE proof is retained. No retry or access-control bypass was introduced. The successful four-page proof is not continuous economic coverage, new-release discovery, a market event or a company-profit conclusion. Detailed lineage and limits: `docs/economic-source-four-page-capture-proof-2026-09-05.md`.

### 5.13 Bounded official-directory discovery — PR #204–#205

`runtime/economic_release_discovery.py` starts from two fixed MOA/SPB directory first pages rather than only preselected article URLs. It preserves original directory bytes, row-local title/date/link evidence, the exact reviewed baseline and an explicit acquisition plan. Known URLs, changed metadata, older unreviewed backlog and eligible unreviewed releases are distinguished. At most four detail bodies may be fetched; an over-budget plan retains all candidates and fetches no top-N subset. Acquired details must corroborate title/date identity but remain pending source review, never automatically accepted economic observations or market events. There is no persistent seen/review queue and known URL body-only revisions are not checked.

The first live compatibility run `33952315592` on `26769c4bdf5254b9eace867395157dcb28c9848e` returned HTTP 200 for both directories and completed as `COMPLETE_BOUNDED_SCAN`. MOA had 20 dated entries, including 10 target feed-price releases: two known and eight older backlog entries. The SPB news first page had 10 ordinary news entries dated September 3–4 and no target monthly report. Exactly two directory requests and zero article requests occurred; no new review packet, economic observation or market event was created.

Artifact `9965217757` retained the original bodies and nine-file sealed inventory. Workflow verification reconstructed the scan offline; independent local hash/HTML/clock/plan checks reconciled the downloaded artifact and unchanged baseline. Detailed lineage: `docs/economic-release-directory-proof-2026-09-05.md`.

This proved those two visible windows, not complete publisher coverage or natural new-release body acquisition. The original SPB news window did not reach the reviewed August 14 boundary. Full implementation CI at that stage contained 569 tests; this did not replace the unchanged live Sector proof. The later direct statistics-window result is below.

### 5.14 Reuse-first parser and official statistics entry — PR #207–#208

PR #207 removed both custom discovery HTMLParser subclasses, reusing optional pinned Beautiful Soup 4.14.3 and its explicit html.parser builder. The production module shrank by 30 lines; base Kernel dependencies stayed unchanged. Only the existing discovery workflow's install line changed. Parser/runtime versions and code hashes are recorded for replay; prior archives use their recorded implementation. Source/date/review/authority checks remain project contracts. No crawler framework or homemade pagination was added.

Its controlled run `33954522717` remained INCOMPLETE: MOA parsed successfully, but the SPB landing URL returned HTTP 200 with only a 137-byte script navigation stub. Artifact `9965907259` preserves this failure. The script was not executed. PR #208 changed exactly one source URL to the separately reviewed direct official statistics list `/gjyzj/c100276/common_list.shtml`, leaving parser/transport logic and article identities unchanged.

The resulting run `33954898834` on `aa7f9f4f03e529604c164e164c99e04471aa465d` completed successfully with two directory requests and zero article requests. MOA retained 20 qualified rows / 10 target releases; SPB had 9 qualified rows / 6 target titles, including both reviewed monthly reports. Its visible dates ran from 2025-11-18 through 2026-08-14, reaching the current reviewed boundary. Artifact `9966022845` and its nine-file inventory were downloaded and reconciled independently; the workflow rebuilt the scan offline. The original baseline and MOA raw body remained byte-identical to prior evidence.

This is improved current-window coverage, not complete history, continuous discovery, new-detail acquisition or source acceptance. No pending new packet, economic observation or market event was created. Full implementation CI at that stage contained 587 passing tests; no HiThink call, live Sector change, schedule or authority change occurred in that slice. Exact PR/run/hash evidence, failure lineage and next-step constraints are in `docs/handoffs/2026-09-05-reuse-first-statistics-proof-next.md`.

### 5.15 First real stock dump, incomplete reference qualification — PR #210–#213

`runtime/hithink_dump_trial.py` composes mature Requests/PyArrow with the existing row inspector and strict market reference adapters. Libraries are isolated in `.[dump-study]` and CI `.[dev]`; Kernel base dependencies remain unchanged. Physical synthetic Parquet tests now run in CI. Its separate main-only workflow has bounded one-signing/one-download acquisition and at most 32 reference requests, no market cache/state writer or schedule, and never retains usable presigned URLs or credentials. Every outcome keeps production qualification NOT_ESTABLISHED.

Three initial real signing attempts returned code 0 but stopped before object/reference acquisition because of our AWS-only or example-directory assumptions. Safe diagnostics isolated the remaining prefix mismatch. The official signing service selects object paths, so PR #213 removed the unsupported fixed-directory assumption on the exact reviewed CDN origin, without adding arbitrary hosts, redirects, ambiguous paths or price tolerance. The upstream downloader exists and was reviewed; the trial reuses Requests/PyArrow rather than its mutable cache/resume behavior. All earlier failed runs remain unchanged.

Run `33957604949` on `bde9bad7ef725fbca54f5c7a567227e6b9b7dd56` retained the first real 1,077,266-byte recent-stock Parquet, artifact `9966871869`. PyArrow read the exact 11-column footer, reporting 55,467 rows and one row group. Calendar and benchmark checks qualified 2026-09-04; then stock page 0 had a 2026-09-05 data timestamp. The unchanged all-stock adapter rejected the date before further pagination. The overall workflow remains failure / FAILED_CLOSED at QUALIFIED_REFERENCE, not successful data qualification. Full row inspection did not execute (`inspection=null`), and no complete stock-universe reference, multi-day breadth or stock panel was produced.

Original Parquet, four raw decoded reference JSON responses, normalized calendar tail and qualified benchmark are retained. Independent download checks reconciled all seven input files, ZIP/report/provenance hashes, clocks, the benchmark close pair and stock timestamp. Full local Parquet decoding and full local project tests are not claimed. Full code CI at that stage had 639 passing tests. Exact PRs, failed stages, artifact digests and interpretation limits remain in `docs/handoffs/2026-09-05-stock-dump-trial-next.md`.

### 5.16 Stock reference-window correction and real row comparison — PR #215

`HithinkStockSnapshotReference` explicitly separates stock page data-ready clocks from the independently anchored comparison session. Only the isolated dump trial opts in; the Sector producer default is unchanged. It supports the same session after 15:30 or Friday's directly following weekend, checks each timestamp against actual receipt, and rejects missing weekday/holiday assumptions. Returned reference semantics deny per-security-session proof. No dependencies, workflow definitions, price tolerances, null filling or production callers were changed. Full PR CI `33959105550` passed 680 tests; main kernel CI `33959190993` succeeded.

One changed-code live run `33959190974` on `74509398a1a9afa226e83ef878c418fbe114586b` fetched all 12 stock pages with 5,567 unique identities and physically inspected all 55,467 Parquet rows. All 5,548 fully priced latest closes matched exactly. The unchanged inspector retained 4,654 turnover differences, 15 raw-previous-close differences and one missing previous bar. Nineteen unpriced references were exactly the nineteen current identities without a latest dump bar, not two disjoint groups. No causes such as rounding, dividends, suspensions or IPO status were asserted without evidence. Status is DIFFERENCES_REQUIRE_REVIEW, stage INSPECTED_NOT_ADOPTED and workflow failure; production qualification remains NOT_ESTABLISHED.

Artifact `9967375391` preserves 21 input files plus report/summary/offline inspection/workflow identity. The workflow's second actual offline Parquet inspection wrote the same inspection object and returned nonzero for differences; the following shell equality assertion was skipped. Equality, all inventory/file/content hashes, page clocks/counts/identities, original-to-normalized values and diagnostic categories were independently checked after download. Local full Parquet execution is not claimed. The Parquet was byte-identical to the prior same-day download, not a naturally later vintage or revision proof. Detailed evidence and next steps: `docs/handoffs/2026-09-05-stock-reference-reconciliation-next.md`.

### 5.17 Frozen-field diagnosis and actual primary-source evidence — PR #217–#218

PR #217 added a read-only diagnostic projection without changing acceptance. It separated a material 920371.BJ turnover difference from the small differences; its full CI passed 697 tests. PR #218 reused existing Requests/identity/audit helpers and a maintained adapter's CNINFO query contract to collect only the identified evidence. No new dependency, adjustment engine, whole-market download or signal rule was introduced. Full PR CI `33963783988` passed 722 tests; main CI `33963949069` succeeded.

One actual source-study run `33963949084` on `9b062cd5b7024ddd9ecc74129e0a36767f5e4f10` made 21 once-only successful requests and retained 15 exact-date event records, one targeted raw history, a public organization directory, two notice queries and two original issuer PDFs. Its 26-file artifact `9968826124` passed offline plan/inventory/hash checks and independent local review, including pypdf extraction and rendered-page review. Collection status is CAPTURE_COMPLETE_REVIEW_REQUIRED, not production qualification.

The 15 events all refer to September 4; twelve gross-cash subtractions match the frozen displayed prev_price and three leave explicit residuals. This is not a universal price rule. The original 000408 notice prescribes a treasury-share-adjusted deduction of 0.9967967 rather than gross cash 1; the 001316 notice supports a cash-only example with 27.79 - 0.35 = 27.44. The original wordings and actual capture clocks are retained. For 920371, targeted REST raw amount agrees with the frozen Parquet, while snapshot differs by 10,312,354.49 CNY and 1,983,145 shares; the original BSE transaction details and provider scope/precision remain pending.

The old stock comparison still has DIFFERENCES_REQUIRE_REVIEW and production qualification NOT_ESTABLISHED. No price rewrite, tolerance, missing-stock exclusion, historical availability backfill or live Sector change occurred. Exact source/PDF hashes, arithmetic, interpretation limits and remaining work are in `docs/stock-field-primary-source-proof-2026-09-05.md`.

---

## 6. Next work

### Completed — initial live validation and same-session recovery

Runs `33938625934` and `33939414197` completed these proofs. No additional same-session dispatch is required merely to repeat them. The latest operational evidence supersedes the pre-live expectations in `docs/handoffs/2026-09-05-sector-radar-manual-producer-next.md`.

### P0 — first direct completed-session append

The next validation target is a fresh `main` dispatch after the 2026-09-07 close. The actual latest completed session must still be established by the provider calendar and qualified snapshot, not hardcoded.

```text
restore newest successful artifact, currently ending 2026-09-04
+ verify any restored cache agrees
→ require exactly one subsequent completed session
→ require every provider prev_price to match the cached latest close
→ append only 2026-09-07
→ calculate prospective entries from market snapshots only
→ retain complete audit and persist market state and event ledger
```

Zero candidates is a valid quiet outcome; do not force a candidate. If ordinary production first sees 2026-09-08 or later while restored state still ends at 2026-09-04, it must fail closed and use a separate qualified recovery procedure.

Review the real new-session append before adding a schedule. Continue to use a new `workflow_dispatch`, not “rerun jobs.” Any state, turnover, catalog or provider identity disagreement remains a real proof failure and must not be weakened silently.

For the next audited run, also download its complete run artifact and verify `input-audit/` with the recorded implementation. Confirm `context/index.html` and `context/context.json` match that exact state/ledger and were actually uploaded. Successful offline reproduction supplements, but does not replace, the workflow's artifact publication and cache checks.

### P1 — expansion qualification and usable reading

Reuse mature components before building more generic infrastructure. Read-context delivery, raw capture and bounded discovery are implemented; the direct SPB statistics window now reaches the current reviewed monthly boundary. Natural new-detail acquisition, continuous coverage, known-body revisions and live Sector view publication remain unproven. Use the existing explicit source-review process rather than invent another approval engine. Do not repeat unchanged scans or rewrite the baseline to force a candidate. Earlier failures and their limits remain evidence.

The stock trial now has complete comparison references and a real full-row inspection, but field agreement and production qualification remain incomplete. Work from retained inputs to establish turnover precision/units, corporate-action evidence for the fifteen previous-close differences, and the nineteen missing/unpriced identities plus one missing previous bar. Do not invent a numerical tolerance, dividend or suspension classification. Reuse official tooling before adding calculations. A naturally later overlapping vintage and longer stock history remain necessary before stock-panel or multi-day breadth adoption. Do not repeat failed probes blindly, ask for secrets in chat, install a competing provider or use stock dumps to bridge missing industry sessions.

Section 5.17 now supplies the fifteen effective-date event records and two original issuer examples. Next reconcile the remaining distinctions, not merely acquire these same sources again: gross cash versus ex-reference deduction, final quotation rounding, BSE transaction types/provider scope, and the unresolved listing/trading gaps. Current event APIs and a later PDF capture do not establish earlier system availability.

The original benchmark-sensitivity acceptance item still needs an explicit evidence result. Keep its effect on excess sign, persistence and transition dates separate from within-universe ranks. Concept expansion, company-economic mapping and new trigger challengers remain later scoped work, not implied by the new read labels or two source pilots.

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
- `docs/handoffs/2026-09-05-stock-primary-sources-next.md` — latest targeted source evidence, original issuer distinctions and remaining adoption gates.
- `docs/handoffs/2026-09-05-stock-reference-reconciliation-next.md` — prior complete stock-row inspection, unresolved differences and reference-window limits.
- `docs/handoffs/2026-09-05-stock-dump-trial-next.md` — prior real stock delivery, rejected reference contract and failed probes.
- `docs/handoffs/2026-09-05-reuse-first-statistics-proof-next.md` — prior reuse decision, direct-statistics proof and retained failed probe.
- `docs/handoffs/2026-09-05-bounded-release-discovery-next.md` — prior directory-discovery handoff and coverage limits.
- `docs/handoffs/2026-09-05-http-diagnostics-and-four-page-proof-next.md` — prior diagnostic/capture handoff, retained for lineage.
- `docs/handoffs/2026-09-05-context-and-public-capture-next.md` — prior delivery and partial-capture handoff, retained for lineage.
- `docs/handoffs/2026-09-05-radar-expansion-next.md` — prior expansion handoff, retained for lineage.
- `docs/sector-radar-live-bootstrap-restore-proof-2026-09-05.md` — latest live Sector evidence and next-step constraints.
- `docs/economic-source-raw-capture-proof-2026-09-05.md` — partial raw public-source proof and retained failures.
- `docs/economic-source-four-page-capture-proof-2026-09-05.md` — subsequent four-page capture, without a claimed cause for prior failure.
- `docs/economic-release-directory-proof-2026-09-05.md` — two-window discovery proof, zero new detail packets and explicit coverage gaps.
- `docs/handoffs/2026-09-05-sector-radar-manual-producer-next.md` — pre-live handoff retained for lineage; live-execution status is superseded by the proof above.
- `docs/handoffs/2026-09-05-sector-radar-next-conversation.md` — prior prerequisite handoff retained for lineage.

### Sector Radar decisions and evidence

- `docs/sector-discovery-radar-prior-art-and-v0-decision-2026-09-04.md`
- `docs/sector-discovery-radar-frozen-pit-replay-result-2026-09-04.md`
- `docs/sector-discovery-radar-884-replay-result-2026-09-04.md`
- `docs/sector-discovery-radar-current-breadth-proof-2026-09-04.md`
- `docs/sector-discovery-radar-full-current-hierarchy-result-2026-09-05.md`
- `docs/sector-radar-state-bootstrap-2026-09-04.md`
- `docs/sector-radar-prospective-producer-operations.md`
- `docs/sector-radar-input-audit-and-offline-replay.md`
- `docs/sector-radar-read-only-context.md`
- `docs/hithink-dump-qualification-study.md`
- `docs/hithink-stock-dump-trial.md`
- `docs/hithink-stock-snapshot-reference-window.md`
- `docs/hithink-stock-field-diagnostics-2026-09-05.md`
- `docs/stock-field-source-study.md`
- `docs/stock-field-primary-source-proof-2026-09-05.md`
- `docs/economic-node-public-source-pilots-2026-09-05.md`
- `docs/economic-source-raw-capture.md`
- `docs/economic-source-compatibility-operations.md`
- `docs/economic-source-http-diagnostics.md`
- `docs/economic-release-discovery.md`
- `docs/economic-release-discovery-operations.md`
- `docs/radar-reuse-decision-2026-09-05.md`

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
- `src/decision_kernel/runtime/sector_radar_audit.py`
- `src/decision_kernel/runtime/sector_radar_context.py`
- `src/decision_kernel/runtime/hithink_dump_inspection.py`
- `src/decision_kernel/runtime/hithink_dump_trial.py`
- `src/decision_kernel/runtime/hithink_dump_diagnostics.py`
- `src/decision_kernel/runtime/stock_field_source_study.py`
- `src/decision_kernel/runtime/economic_node_study.py`
- `src/decision_kernel/runtime/economic_source_capture.py`
- `src/decision_kernel/runtime/economic_release_discovery.py`
- `src/decision_kernel/runtime/hithink_index_http.py`
- `src/decision_kernel/runtime/hithink_sector_breadth_http.py`
- `.github/workflows/sector-radar-shadow.yml`
- `.github/workflows/hithink-stock-dump-trial.yml`
- `.github/workflows/stock-field-source-study.yml`
- `.github/workflows/economic-source-capture.yml`
- `.github/workflows/economic-release-discovery.yml`
- `radar_inputs/sector-parent-hints-2026-09-05.json`
- `radar_inputs/sector-radar-state-bootstrap-2026-09-04.json.gz`
- `radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json`
- `radar_inputs/economic-node-study-2026-09-05.json`

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
- **PR #190:** repaired the same-session calendar-boundary failure exposed by run `33936773283` without requiring a future calendar row.
- **PR #191:** repaired index snapshot data-ready timestamp interpretation exposed by run `33937883228`, preserving benchmark-price and calendar qualification.
- **PR #193:** added bounded replayable input audit, full separate-universe diagnostics, staged publication and synthetic full-path integration/rollback coverage; no new live proof is claimed.
- **PR #194:** added a standalone read-only context CLI; full state visibility is not a new alert.
- **PR #195:** added isolated stock-dump integrity tooling; actual download, entitlement, reader execution and production qualification remain unproven.
- **PR #196:** added two public-source economic pilots using four reviewed excerpts; no automated feed, industry-wide coverage or fundamental-state migration is claimed.
- **PR #198:** wired context rendering and an actual artifact link into the manual Sector workflow; live delivery remains pending.
- **PR #199:** added original public-response capture and accepted/rejected excerpt reconstruction; no market state or event writer.
- **PR #200:** added the separate bounded public-source compatibility workflow. First live run `33947395994` remained INCOMPLETE: SPB 2/2 matched, MOA 0/2 obtained. Artifact `9963755766` and failure evidence retained.
- **PR #202:** added safe numeric HTTP diagnostics and schema-2 status/summary reconciliation. New public run `33949122077` matched all four pages, artifact `9964235933`; old HTTP failure codes/cause remain unknown. No continuous feed or market event is implied.
- **PR #204–#205:** added bounded directory discovery into unreviewed source packets and its independent compatibility workflow. Live run `33952315592` captured two directory windows, with zero eligible detail requests; artifact `9965217757` preserves scope and backlog evidence. Complete publisher coverage and natural new-release detail acquisition remain unproven.
- **PR #207–#208:** replaced custom discovery parsers with optional Beautiful Soup, retained the script-only landing-page failure and corrected one explicit SPB statistics-list URL. Live run `33954898834` captured the direct statistics window including reviewed monthly records; no new article, observation or market event was created.
- **PR #210–#213:** added the isolated Requests/PyArrow stock trial, corrected our unsupported signing destination/path assumptions and retained all failed probes. Run `33957604949` downloaded actual Parquet and read its footer but stopped at stock-reference date qualification. No full row validation, stock-panel adoption or market/event write occurred.
- **PR #215:** separated stock data-ready clocks from isolated comparison-session evidence without switching the Sector producer default. Run `33959190974` completed 12-page acquisition and real row inspection; latest closes matched for 5,548 priced references, while turnover, previous-close and coverage differences remain unresolved. Artifact `9967375391` and matching offline inspection are retained; workflow failure is not promoted to production acceptance.
- **PR #217–#218:** diagnosed the frozen field discrepancies and collected 15 effective-date event records, targeted raw history and two original issuer notices in run `33963949084`. Treasury-share/ex-reference distinctions remain explicit; raw prices and the original non-acceptance are unchanged. Source artifact `9968826124` is evidence, not a production stock panel.
- **VERIFIED LIVE SECTOR IMPLEMENTATION:** `5f8f635d191dd8559844d1b74af0dca0cf4c02df`; successful runs `33938625934` and `33939414197`.
- **PROVEN LIVE SECTOR:** committed-bootstrap validation, state-artifact publication, cache publication, authoritative artifact recovery, cache agreement and same-session market/event idempotence.
- **NOT YET PROVEN LIVE SECTOR:** future market-state append, candidate enrichment, the new replayable input audit or context delivery on real provider data. Prospective corpus remains empty; T+5/T+20 outcomes and schedule have not started; canonical Inbox insertion remains unauthorized.
- **UNCHANGED AUTHORITY:** no Research route, Recommendation, Action or investment authority.