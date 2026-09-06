# Source-grounded theme lead entry v0

Status: OFFLINE RETAINED-TEXT LEAD DISCOVERY AND EXISTING PROBE PLAN / NOT AUTOMATIC NEWS INGESTION OR A MARKET SIGNAL.

## What changed

`runtime/theme_source_discovery.py` derives themes from the explicitly supplied source text and the complete supplied HiThink concept catalog, rather than a preselected list of theme names. It retains the source EvidenceArtifact, field, exact UTF-8 text hash, Unicode character offsets, surrounding text and exact catalog identities. It passes ALL unambiguous leads within the budget to the existing `make_theme_plan`; the existing probe then owns historical prices, current memberships and overlap. No alternative price formula, ranking, taxonomy or signal ledger is introduced.

This is a deliberately narrow discovery entry: full-label, case-sensitive literal matching, no LLM, synonyms, fuzzy matching, suffix removal, stemming or semantic translation. It cannot discover a theme absent from the catalog or an unlabeled causal relationship. A reference to robots need not match the exact label 机器人概念. Unmatched text remains available with `NO_LITERAL_CATALOG_MENTION`; this never means no theme or no investment opportunity. English/ASCII labels have ASCII word-edge checks (AI must not match inside RAIL); Chinese substring matches are not word-sense disambiguation. Nested labels are both retained, not silently resolved by longest match.

A mention in a denial, quoted opinion, warning, stale source or prompt-like sentence remains a neutral lead, not a bullish/bearish interpretation. A mapping is a retrieval hypothesis, not economic relevance or fact acceptance. A paragraph can produce a lead for a topic the issuer explicitly denies benefiting from. Full retained text must be read before interpreting the topic. No role, source label, hash or mention frequency certifies truth.

## Reuse instead of another extraction platform

Reuse existing EvidenceArtifact/Pydantic time and retention validation, canonical identity, HiThink catalog normalization, request-record/window checks, bounded theme planner, exact-input file guards and native HTML disclosure. Literal lookup uses Python's standard string search and a small ASCII-edge check, not a home-built NLP engine, feed service or vector database. Existing Beautiful Soup is used in tests. No dependency, workflow, data provider, Kernel schema or authority change.

Prior-art rechecked: `xang1234/stock-screener` official README and LIVE_APP_GUIDE describe source-fed extraction, dedup/merge review, mention velocity and lifecycle. Borrow source lineage and review separation, not its LLM fallback stack, embedding merge, count-as-momentum scoring or stock basket semantics. A catalog-literal v0 is much less capable than narrative extraction; it is not claimed equivalent. If broader ingestion is later required, first qualify an official feed or maintained feedparser/RSSHub adapter rather than grow this into a crawler.

References: https://github.com/xang1234/stock-screener/blob/main/docs/LIVE_APP_GUIDE.md ; `docs/radar-reuse-decision-2026-09-05.md`; `docs/theme-radar-probe-v0.md`.

## Explicit inputs, no new evidence authority

Input fields are exactly `schema_version: 1`, `provenance`, `source_scope`, `concept_catalog`, `industry_catalog`, `industries` and `sources`. Provenance uses the existing `SUPPLIED_HITHINK_RECORDS_NOT_LIVE_CERTIFIED` or `SYNTHETIC_TEST_ONLY` labels; it is not evidence that source text was actually fetched. Catalogs are the existing `{path, params, requested_at, received_at, response}` captures. Industry probes are existing exact `{thscode, name, reason}` selections; `[]` requests no industry members. The module does NOT infer industries from an issuer or theme name.

Each source is `{recorded_at, evidence, text_fields}`. `evidence` is an existing full EvidenceArtifact record; it is not a ResearchSnapshot or Human Judgment. `text_fields` selects `['permitted_excerpt']` and/or `['extracted_structured_values', '<exact-key>']`. Only these explicitly selected string values are scanned. Identifiers, titles/URLs, license notes, raw-storage references, dictionary keys, unselected values and generated Research text are not automatically scanned. Raw-storage paths and URLs are never dereferenced. Numeric/missing/empty fields are rejected; an empty field list is an explicit coverage gap. This interface can read existing retained excerpts or management-statement fields without changing their role or PARTIAL retention. A structured paraphrase is not upgraded to an original-source quotation.

Source timestamps must satisfy the existing published <= available <= retrieved relation, followed by retrieved <= recorded <= input cutoff <= generation. A historical report period or rehashed object cannot bypass a later retrieval/record time. These are supplied clock claims, not authenticated historical execution or Human reading proof. The original bytes are retained separately from normalized EvidenceArtifact values. Source content_hash keeps its original meaning; text_sha256 binds only the selected retained string and does not certify the underlying PDF/site.

The concept/industry catalogs must remain disjoint and industry catalog identity must match the exact saved market state. One code has one exact identity. If a catalog label maps to several codes, keep all identities and block automatic planning; do not guess. Entire supplied input scope is validated before any plan, even when nothing matches.

## Budget and duplicate discipline

At most 32 supplied source records, 16 text fields per record, 16,384 characters per field, 131,072 total retained characters, 4,096 catalog identities, 128 characters per label, 2,048 literal occurrences, and 64 MiB of label-count × text-length scan work. Malformed or excessive input fails without truncation. These are operational limits, not opportunity thresholds.

Exact duplicate source records are processed once, with duplicate count visible. Reusing an Evidence ID or idempotency key for different content/time/selection fails. Explicit different versions remain side by side; no newest-only, majority-vote or favorable-version selection. Different IDs, URLs, versions, excerpts or multiple matching labels do not establish independent sources or forecasts. No confidence score or mention-count ranking exists.

At most three distinct unambiguous themes may enter the existing probe. More than three yields `ACQUISITION_BUDGET_EXCEEDED`: retain the complete lead list and produce NO partial plan. Ambiguous identities or unscannable source records likewise block planning, even if other sources have valid matches. Empty input is `NO_SOURCE_RECORDS`, not quiet success. `NO_LITERAL_CATALOG_MENTIONS` describes the supplied text only.

For a valid bounded scope, the existing planner supplies exact requests, state and catalog hashes and the unchanged total maximum of fifteen, including two already supplied catalog requests. Every planned theme carries its lead ID and discovery projection hash in its reason. The module performs ZERO requests. The plan time is the actual generation/planning time, not the older source cutoff. A new render cannot backdate selection before later price calls. Outside the existing saved-session/adjacent-weekend window, preserve the source projection but block a NEW plan with `PLAN_REQUIRES_CURRENT_SAVED_MARKET_STATE`. Do not use this as qualified recovery or a way to bridge a missing market day.

## Run, inspect, and hand off

Use the existing package and its `discovery` extra, an exact saved market-state file and a supplied source-input file:

```bash
python -m decision_kernel.runtime.theme_source_discovery \
  --state /inputs/market-state.json --input /inputs/source-input.json \
  --as-of '<actual source cutoff with timezone>' --output /reports/new-source-discovery
```

Output: `index.html`, `source-discovery.json`, exact `supplied-input.json` and `saved-market-state.json` copies, `files.json`, and `probe-plan.json` ONLY when a complete plan is allowed. A blocked scan saves its full readable report and returns 2; malformed input returns 2 without a success directory. A valid no-literal-match report returns 0 without a plan. Rejected output must not replace a previous success. Existing output is not overwritten; owned staging is cleaned after interruption, and input bytes are rechecked.

The returned plan is compatible with the existing probe input's `plan` field. Original catalog captures plus every later exact response must then pass `build_theme_probe`; no invented empty captures or successful validation marker substitutes for execution. Unit tests actually run that entire downstream builder using original synthetic price/member fixtures and verify unchanged calculations. The fixed-name live capture script/workflow has NOT been switched to consume this plan: no source collector, dispatch, remote publication, daily dedup state, accepted source registry update or natural new-source run is claimed in this slice. Integrating execution must bind and retain this source input/projection before the first request, respect the same plan/response clocks and preserve failures.

The projection hash excludes report-generation time; a newly created request plan has its own clock and hash. Lead IDs bind exact source records/mentions and catalog identity, not first-ever discovery. Later generation creates neither a signal event nor an independent sample. Rebuild the original result with the original recorded generation clock via the pure function; this is offline reconstruction, not authorization to execute an old plan. Copies/checksums are not signatures, long-term source storage, production state recovery or a new append-only event ledger.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE. No changes to Sector ranks, gates, company positions, candidate ledger, canonical Inbox or deferred Position/Holding loop.
