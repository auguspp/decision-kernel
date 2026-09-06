# Source-derived theme capture — v0

Status: IMPLEMENTED CONNECTOR / REAL EXECUTION MUST BE VERIFIED SEPARATELY / SHADOW ONLY.

This extends the existing `.github/scripts/capture-theme-probe.py`, rather than creating a second HTTP loop, planner, theme model or workflow. It connects `theme_source_discovery` to the same raw-response collector and unchanged `theme_radar_probe`. Source matching proposes a bounded acquisition plan, not an accepted fact, signal, beneficiary or Research route.

## Declared input scope before provider requests

`radar_inputs/theme-source-sample-v0.json` is a version-2 selection: exact evidence-only company files, Git blob identities, EvidenceArtifact IDs and text-field paths, plus explicit broad-industry overlap probes. It contains no preselected theme labels. Paths are restricted to bounded JSON files under `radar_inputs/company-evidence`; no arbitrary path, URL fetch, metadata mining or raw-PDF parsing is added. Eight-file / 32-record bounds protect operations, not opportunity selection.

The initial sample selects both existing Muyuan operating/feed-risk evidence records and all their five narrative fields. The full unchanged source file is retained, including unscanned numeric finance and capture metadata. Only the declared fields are matched. This is a previously reviewed, implementer-selected engineering sample, not a natural new release, blind discovery or market-wide source scan. These fields are PARTIAL retained paraphrases, not original quotations. Their old evidence IDs, retrieval/recording clocks and content hashes are not updated by a later read. They do not create another Human acceptance or alter the existing company view.

The existing source concerns procurement and cost risk. Any matched commodity concept is a literal retrieval lead; being an input purchaser cannot be turned into a price-rise beneficiary. The parser does not infer direction, business exposure, thesis quality or company membership. No particular successful match is required for acceptance: no match, ambiguity and excess budget have defined outcomes.

## Execution and storage

1. Check the frozen comparison state and exact source bytes. Validate selected EvidenceArtifact fields and retrieved <= recorded <= trial start before any provider call. Missing, changed, future or malformed source inputs prevent all provider requests.
2. Save unchanged source files as `sources/01.json`, etc., together with the selection and comparison state. Acquire the complete concept and industry catalogs once each.
3. Invoke existing source discovery with an actual post-catalog cutoff/planning clock. Save `source-input.json`, `source-discovery.json` and `source-discovery.html` before requesting any price, history or member set.
4. If eligible, write the exact source-derived `plan.json`, then execute only its existing slots once with 20-second pacing. No top-three truncation, fallback, history correction or changed ranking.
5. Invoke unchanged theme calculation and write `theme-probe.json` / `index.html` only when every required input passes. Persist the capture manifest including partial failure evidence.

More than three themes, ambiguous names or incomplete retained text leaves the whole source report visible but fails capture without a detail request. No literal match produces `COMPLETE_SOURCE_SCAN_NO_THEME_CAPTURE`, exactly two catalog requests and no market page/plan. It is not 'no market opportunity'. A transport or validation failure remains `INCOMPLETE_THEME_CAPTURE`, even when preserved-byte or source-scan reconstruction succeeds. Named v1 inputs and their old artifacts remain supported.

Offline verification reads only copied original source files and raw responses. It repeats pinned-file selection, source clock/retention checks, complete-catalog matching, exact plans, then existing market JSON/HTML reconstruction. Rehashing an edited source-derived sidecar cannot bypass rebuilding. Successful source capture reports `ORIGINAL_SOURCES_SCAN_PLAN_AND_PAGE_REBUILT`; source-only no-match reports `ORIGINAL_SOURCES_CATALOGS_SCAN_REBUILT_NO_DETAIL_REQUESTS`. Neither result is source authentication, independent market truth, prospective discovery time or producer-state recovery.

## Existing workflow and deliberate live-call scope

`hithink-stock-dump-trial` gains explicit `theme-source`. Main pushes touching the capture script or source sample execute this mode once. The former fixed-name sample is now manual-only via `theme-probe`; full stock dump remains manual-only and is still the manual default. No source-file changes or documentation changes automatically trigger provider calls. This scope supersedes the older fixed-name push trigger described in the original capture guide.

Only acquisition receives the existing secret. Source files are pinned before use, original response size/credential/encoding checks and no-redirect Requests transport are reused. Offline verification has no secret. Existing upload retains the whole attempt for 90 days; Summary distinguishes failures, source-only no-match and an actually generated market page. Open `capture/source-discovery.html` first, then `capture/index.html` only if present. No public hosting or permanent retention is implied. The copied company JSON is not the original report PDF; preservation of that earlier PDF remains the separate source artifact's responsibility.

The exact September 4 bootstrap is ONLY an isolated comparison, not producer restoration. The existing same-completed-day/adjacent-weekend guard remains; later weekdays require a separately qualified current state, not a gap bridge. No normal Sector dispatch, market/cache/event writes, schedule, threshold or 881/884 changes. All Human/Research/Investment/signal-transition authorities remain NONE.

## Tests and evidence limits

Tests reuse existing synthetic source/market fixtures and execute the original complete theme calculation, raw capture loop, refusal handling and offline reconstruction. They cover real committed source-byte pins without treating that test as a new acquisition. Full tests and one eventual real source-derived run must be reported separately. A successful run proves previously retained source-to-market integration, not an automatically arriving news feed, prospective candidate corpus, daily theme state, active-trading eligibility or stock-price breadth.

## Native source intake, separately qualified

See `docs/native-rss-source-intake-v0.md` and `docs/native-rss-qualification-2026-09-06.md` for the reused feedparser intake and real NBS two-feed baseline. It stores 1000 initial feed versions, forwards none as new sources, and keeps unzoned publication strings unqualified. Its successor dedup is tested, not yet proven with a live restored predecessor or natural new release. The retained-company capture above is unchanged; no RSS-to-market automatic execution or new accepted economic record is implied.
