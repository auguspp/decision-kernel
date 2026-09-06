# Cross-industry theme probe v0

Status: INDEPENDENT OFFLINE SHADOW PROBE / NOT A GLOBAL THEME SCANNER / NO INVESTMENT AUTHORITY.

## Delivered slice

`runtime/theme_radar_probe.py` reads a strict existing Sector market-state original plus an explicitly supplied, bounded collection of HiThink concept records. Select one to three exact concept identities and zero to six broad 881 industries. Output: each concept's 5/20/60-session index/benchmark/excess path, five-session change in 20-day excess, positive-excess duration with left censoring, turnover pulse, current constituent intersections with the selected industries, and pairwise concept overlap. No concept receives a cross-sectional rank or rating from this small selected sample. A positive trend is not a new false-to-true event or the system's first discovery.

A concept label is not itself proof of cross-industry reach. `OBSERVED_ACROSS_PROBED_INDUSTRIES` requires members exclusively observed in at least two supplied 881 sets. Unmatched members remain unmatched IN THE PROBED SET, not industry-less. Members present in several broad sets stay explicitly ambiguous; the tool does not pick the largest overlap or silently divide them. 884 probes are rejected to avoid parent/child double-counting. Raw overlaps, exclusive members, ambiguous members and unassigned members retain the full concept denominator.

Concept pairs reuse the existing current-membership overlap calculation (intersection, union, Jaccard, containment). Exact-equal cohorts are visible but their distinct index identities are never merged. Sum of membership counts and unique-member count are separate; neither is a count of independent forecasts. No overlap threshold, graph clustering, composite score, automatic beneficiary list, recommendation, Action, Research route, or canonical Human wake exists here. Stock price breadth, causal company exposure, historical constituents and index weights remain explicitly unestablished.

## Reuse before import

The original `docs/sector-discovery-radar-prior-art-and-v0-decision-2026-09-04.md` deliberately left full concept scanning out of the 881/884 producer because of overlapping narratives and request volume. This separately approved exploratory probe does NOT change that production universe or relax that decision. It may be explicitly selected without an industry signal, but cannot generate a canonical attention route.

Primary upstream contract rechecked on 2026-09-06: `HiThink-Tech/Financial-API`, commit `765513c2616030803ad80915ed65b205f425a942`, `docs/api/endpoints-index.md`. It already supplies full, non-paginated `cn_concept` and `industry` catalogs, explicit index snapshots, single-index daily history and CURRENT constituent sets. History has no adjustment parameter. Nothing requires another data vendor, full-market stock download or novel taxonomy.

Implementation reuses the project's strict index history/snapshot/identity normalization, exact market-state parser, current-membership normalization and overlap function, and existing return/average/persistence primitives. The existing catalog parser is used ONLY as a .TI identity/name/timestamp/hash parser; its industry-family classification never becomes theme semantics. State/catalog equality and concept/industry disjointness are checked separately. The existing two industry rankings, candidate producer, event ledger and policy remain unchanged. The tested formula window is the existing last 126 observations within the supplied exact 127-session state; no third ranking universe is inserted.

`xang1234/stock-screener` remains prior art for distinct theme lifecycles and overlap, not a library dependency: its news/LLM extraction and application stack do not replace the existing commodity functions or satisfy this narrow contract. No graph library, crawler, new frontend framework, provider SDK or additional dependency is introduced. Native HTML disclosure and existing Beautiful Soup tests suffice.

References:
- https://github.com/HiThink-Tech/Financial-API/blob/765513c2616030803ad80915ed65b205f425a942/docs/api/endpoints-index.md
- https://github.com/xang1234/stock-screener
- `docs/radar-reuse-decision-2026-09-05.md`

## Two phases and input contract

1. Obtain the two exact catalog captures. `make_theme_plan(state, concept_catalog, industry_catalog, themes=..., industries=..., planned_at=...)` validates a declared selection AFTER those responses. Each selection has exact `thscode`, `name`, and an explicit `reason`. It returns exact requested endpoint/parameter slots, catalog-capture identity, state identity, window, and a content hash. It performs ZERO requests.
2. Supply EVERY planned response. `build_theme_probe` recomputes the plan, checks the exact capture set, then validates all responses before returning any successful view. No top-three truncation, silently excluded theme, missing-to-zero conversion or partial-rank output is allowed. An unavailable requested source prevents the successful probe; keep collection failures in the external acquisition audit.

A capture is `{path, params, requested_at, received_at, response}`. `response` is the original HiThink JSON object, not a text summary or manually normalized list. Request credentials/headers are not fields. The root input is `{schema_version:1, provenance, plan, concept_catalog, industry_catalog, captures}`; captures is keyed by the plan's request IDs. Parse decimal JSON values as Decimal before canonical hashing, not binary float.

Permitted provenance labels: `SUPPLIED_HITHINK_RECORDS_NOT_LIVE_CERTIFIED` and `SYNTHETIC_TEST_ONLY`. Neither is proof of real HTTP execution or a genuine prospective signal. A hash binds the supplied claims, not website authenticity or historical availability. There is no way to mark this result as certified live production merely by giving it a source-like name.

Request budget, if the plan is later executed: two catalogs, one theme-plus-CSI300 snapshot, at most three theme histories, at most nine member requests = at most FIFTEEN calls. No stock snapshot, per-company history, 320-sector membership fan-out, retries, provider fallback or automatic acquisition is implemented. The CLI bounds each supplied file at 8 MiB, catalogs at 4096 identities and each membership at 10000 entries. These are operational limits, not opportunity thresholds. The complete selection fails rather than being truncated.

## Session and PIT discipline

The state uses the exact existing CSI300 benchmark. Snapshot last and previous benchmark prices must match that state; each theme's dated history must contain ALL AND ONLY the same 127 completed sessions, with exact latest/previous prices, volume and turnover agreeing with its current snapshot. Latest NaN, latest missing, initial/middle missing, adjusted history, off-calendar/future bars and changed identity fail. Do not clean away the final row and use the prior row as current.

For this first probe, the reading must occur after the saved session's 15:00 close on that day or its directly following Saturday/Sunday. A later weekday or an unproven holiday gap is refused. This is a conservative acquisition guard, not a new exchange calendar or proof of per-security freshness. The selected state must already exist before planning; both catalogs precede planning; all later requests lie between planning and the cutoff (at most 30 minutes); generation cannot precede cutoff. Snapshot/member ready clocks must be at least the represented close and no later than receipt. Ready time is retained separately from actual requested/received time and is not historical membership effective time.

Current members are NEVER used to reconstruct historical index returns. Those returns come only from the provider's exact index bars. Current set evidence answers current overlap questions, not historical taxonomy, index contribution, actual stock-price participation or business sensitivity. New generation time leaves fixed-input projection identity unchanged. A late receipt cannot enter an earlier cutoff. A trend start computed from bars is not the first time any person or system noticed it.

## Run and reconstruction

Use an existing exact market-state file and separately collected capture input; this command cannot fetch them:

```bash
python -m decision_kernel.runtime.theme_radar_probe \
  --state /path/to/verified-sector-bundle/market-state.json \
  --input /path/to/theme-captures/input.json \
  --as-of '<actual supplied capture cutoff, timezone-aware>' \
  --output /path/outside-input-directories/new-theme-probe
```

Open `index.html`; `theme-probe.json` preserves all selected identities, denominators, unmatched/ambiguous members, raw overlap values and source hashes. `supplied-input.json` and `saved-market-state.json` are exact input byte copies. `files.json` records local checksums only, not remote publication, signatures or an authoritative restore source. Rebuilding at the original generation time can reproduce the JSON and HTML. Existing output is never overwritten; writes are staged and removed on interruption. This is a single-writer offline command, not a concurrent service.

## Acceptance and what remains

Tests reuse the real existing parsers/math and a genuinely parsed committed bootstrap for the maximum request-plan test; THEME CATALOGS, BARS AND MEMBERSHIPS IN TESTS ARE SYNTHETIC. Tests compare descriptive math with the existing calculation, cover duplicate/ambiguous memberships and exact union counts, missing/future input rejection, generation-time independence, budget enforcement, escaping, input-byte preservation and full CLI reconstruction. No synthetic record enters a production artifact or event ledger.

No real concept capture, prospective theme corpus, natural acquisition throughput proof, daily theme state/cache, global scanning, live breadth, workflow dispatch/schedule, automatic delivery, target-company economic validation, or new false-to-true trigger was earned by this code. The next qualifying experiment must collect exact catalogs first, freeze a reasoned small selection, execute the bounded plan under the existing source/audit discipline, and preserve failures. Do not dispatch the normal Sector producer just to demonstrate this independent probe. Its real next-session acceptance remains separately pending.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
