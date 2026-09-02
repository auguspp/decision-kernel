# Radar prior-art refresh — 2026-09

Status: **RESEARCH ONLY / NO RUNTIME ADOPTION AUTHORIZED BY THIS NOTE**

This note refreshes prior-art work from `decision-os`. The old external-reference map is useful history, not current approval. Every adoption still requires exact-source, license, maintenance, coupling, and live-fit checks at implementation time.

## Boundary

Reuse commodity engineering aggressively. Do not outsource Decision Kernel or Radar semantics:

- PIT / anti-hindsight
- `NEW_EVIDENCE` vs `PRICE_PATH_EVIDENCE` vs inference
- fundamental-state migration authority
- `DEEPEN_NOW / WAIT_FOR_TRIGGER / DROP_FOR_NOW`
- Human attention and investment authority

For A-share market price, HiThink remains the qualified authoritative commodity source. A reused project must not introduce a competing market-provider framework or fallback chain into Decision Kernel.

## Historical references consulted

From `decision-os`:

- `docs/architecture/external-reference-map.md`
- `docs/architecture/radar-external-reality-v0.md`
- old Radar / Market Slow / Attention / Research handoff code
- Web `产业拐点扫描`, `每日研究分配`, and `Radar Attribution Review` methodology

The old map explicitly required re-checking latest upstream state before adoption. This refresh follows that rule.

## Fresh 2026 scan

### 1. simonlin1212/a-stock-data

**Current judgment: BORROW SMALL ACQUISITION PARTS / HIGH PRIORITY DILIGENCE**

- Apache-2.0.
- Actively repaired through 2026; changelog documents broken-endpoint replacement, CNINFO `orgId` correction, board pagination fixes, throttling, and source-specific failure modes.
- Useful Radar-adjacent capabilities: CNINFO filings, industry reports, sector/concept membership, industry ranking/fund flow, THS hotspot reason tags, public-data retrieval patterns.
- Particularly relevant proven details: dynamic CNINFO issuer mapping; explicit throttling for Eastmoney; source-specific normalization rather than pretending wrappers are stable.

**Do not inherit:** its full 15-source fallback stack, market-data authority, valuation workflows, or all-in-one Skill architecture. For Decision Kernel market prices, keep HiThink only.

**Best fit:** inspect and adapt the smallest exact acquisition helpers when Radar needs CNINFO / industry / sector reality that Web search alone cannot provide deterministically.

Upstream: https://github.com/simonlin1212/a-stock-data

### 2. ZhuLinsen/alphasift

**Current judgment: LEARN + POSSIBLY EXTRACT SMALL HOTSPOT/HEALTH PATTERNS**

- Apache-2.0.
- Now materially more developed than the old map captured: full-market snapshots, deterministic screening, hotspot discovery, source-health metadata, stale/fallback marking, history sidecars, and T+N saved-run evaluation.
- Good patterns for Radar: normalized hotspot payloads, explicit source confidence, stale/fallback metadata, data-source health summaries, later evaluation records.

**Do not inherit:** factor score as conviction, LLM ranking authority, composite opportunity ranking, multi-provider market fallback, or strategy framework.

**Best fit:** reference implementation for commodity hotspot normalization and failure-visible source metadata, not a stock-selection engine inside Radar.

Upstream: https://github.com/ZhuLinsen/alphasift

### 3. HKUDS/Vibe-Trading

**Current judgment: REFERENCE ONLY**

- MIT; large and active.
- 2026 A-share fixes expose valuable real-world data-quality lessons: unit mismatches across fallback sources, ticker-routing errors, stale/fallback provenance, and correctness hardening.

**Do not inherit:** trading-agent architecture, broker/execution capabilities, provider registry/fallback architecture, factor zoo, or backtest platform.

**Best fit:** mine regression-test ideas for units, identity, provenance, and fallback honesty when building Harness adapters.

Upstream: https://github.com/HKUDS/Vibe-Trading

### 4. deepcharles/ruptures

**Current judgment: DEPENDENCY CANDIDATE FOR SHADOW EXPERIMENTS**

- BSD-2-Clause; lightweight dependency surface (`numpy`, `scipy`).
- Focused change-point detection library; active 2026 development continues.

**Potential Radar use:** detect regime/level changes in already-qualified economic-node time series (price, inventory, utilization, orders, etc.).

**Boundary:** a detected change point is an observation trigger only. It cannot migrate fundamental state or create Research authority by itself.

**Adoption rule:** first run as shadow evidence on frozen historical series; do not make it a production attention gate until attribution proves incremental value.

Upstream: https://github.com/deepcharles/ruptures

### 5. online-ml/river

**Current judgment: LATER DEPENDENCY CANDIDATE**

- BSD-3-Clause; active, with dedicated streaming anomaly and drift detection including ADWIN.
- Strong fit for online change detection if Radar eventually maintains continuously updated economic-node streams.

**Why not first:** broader package and compiled Rust/Cython path than `ruptures`; current Radar does not yet need a general online-ML layer.

Upstream: https://github.com/online-ml/river

### 6. yzhao062/pyod

**Current judgment: REFERENCE / OPTIONAL EXPERIMENT ONLY**

- BSD-2-Clause; production-stable and actively released in 2026.
- Very broad anomaly-detection toolkit with many detectors.

**Why not first:** too many model choices before Radar has a stable feature matrix; contamination/threshold/model selection can silently become a second policy system. Use only for bounded comparative experiments if simple change detection proves insufficient.

Upstream: https://github.com/yzhao062/pyod

### 7. adbar/trafilatura

**Current judgment: DIRECT DEPENDENCY CANDIDATE WHEN DETERMINISTIC WEB INGESTION IS NEEDED**

- Apache-2.0 for current releases; actively maintained in 2026.
- Focused web text/metadata extraction with deduplication support.

**Potential Radar use:** deterministic Harness ingestion of public article/industry pages before evidence qualification.

**Why not immediately:** current Web GPT can already perform broad discovery. Add local extraction only when repeated ingestion, replayability, or content hashing creates a real need.

Upstream: https://github.com/adbar/trafilatura

### 8. kurtmckee/feedparser

**Current judgment: DIRECT DEPENDENCY CANDIDATE IF RSS/ATOM BECOMES A REAL CHANNEL**

- BSD-2-Clause; production/stable.
- Small, mature RSS/Atom/JSON feed parser.

**Boundary:** parsing is commodity plumbing; source authority and Evidence qualification remain ours.

Upstream: https://github.com/kurtmckee/feedparser

### 9. docling-project/docling

**Current judgment: LATER DEPENDENCY CANDIDATE FOR DOCUMENT EXTRACTION**

- MIT codebase; very active and widely used.
- Strong PDF/document/table conversion capabilities.

**Why not immediately:** large dependency/model surface. Web GPT already handles many documents; add Docling only if deterministic local extraction/replay becomes a bottleneck. Check model licenses separately before enabling model-backed components.

Upstream: https://github.com/docling-project/docling

### 10. akfamily/akshare

**Current judgment: EXPLORATORY / LOW-AUTHORITY DATA SOURCE, NOT A TRUTH BOUNDARY**

- MIT; very active and broad Chinese financial-data coverage.
- Useful coverage includes industry/concept boards, macro, futures/inventory, forecasts, and announcements.
- 2025–2026 issues show that wrapper-backed Eastmoney board endpoints can break, truncate, cache unexpectedly, or disconnect when upstream changes.

**Best fit:** rapid exploration or shadow acquisition for commodity/industry data where provenance is explicit. Prefer official sources or a separately qualified direct acquisition path for authoritative Evidence.

Upstream: https://github.com/akfamily/akshare

### 11. microsoft/qlib

**Current judgment: REFERENCE ONLY**

- MIT; mature quantitative research platform with explicit PIT concepts.
- Useful patterns: observation-time vs period-time, PIT storage and data-expression conventions.

**Why not dependency:** very large dependency/platform surface (MLflow, Redis, Mongo, LightGBM, CVXPY, etc.) and much broader goals than Radar needs.

Upstream: https://github.com/microsoft/qlib

### 12. OpenBB-finance/OpenBB

**Current judgment: DO NOT ADOPT AS A DEPENDENCY**

- Current main platform repository is AGPLv3.
- Broad financial-data platform with provider extensions, but both licensing and architecture are mismatched with the small private Harness we want.

**Use:** public conceptual reference only if an API/provider pattern is worth studying. Do not copy or embed platform code without a separate license decision.

Upstream: https://github.com/OpenBB-finance/OpenBB

### 13. NetworkX

**Current judgment: MATURE WHEEL, BUT NO CURRENT NEED**

- BSD-3-Clause and extremely mature.
- Could model economic-node → company → supply-chain exposure graphs later.

**Why not now:** current mappings are small enough for typed records/dicts; adding graph infrastructure before graph algorithms are actually needed would be architecture for architecture's sake.

Upstream: https://github.com/networkx/networkx

## Current shortlist

If implementation started today, investigate in this order:

1. **`a-stock-data`** — extract only the exact CNINFO / industry / sector acquisition pieces we actually need; do not adopt its market-provider stack.
2. **`ruptures`** — cheap shadow experiment for economic-node change detection.
3. **AlphaSift** — reuse patterns for hotspot normalization, source-health, stale/fallback visibility, and later attribution records.
4. **Trafilatura / feedparser** — add only when deterministic repeated web/feed ingestion becomes a real Harness requirement.
5. **Docling** — add only when local PDF/table extraction becomes a repeated bottleneck.

`River` and `PyOD` remain experiment candidates after simple detectors have real failure cases. `Qlib`, `Vibe-Trading`, `TradingAgents`, and `OpenBB` are architecture/reference mines, not runtime foundations.

## Next diligence before code

For the first Radar slice, do not add dependencies yet. Select one real missing capability and perform exact-source diligence:

- exact upstream file/API to reuse;
- latest commit/tag and license;
- live smoke against current sources;
- failure/provenance behavior;
- smallest adapter shape;
- evidence that reuse is cheaper than 20–50 lines of native glue.

A wheel is adopted only if it removes recurring commodity work without importing a second investment methodology or runtime architecture.
