# Radar Stock discovery pool v1

Status: IMPLEMENTATION SLICE / SAVED-SOURCE PROJECTION / NOT FULL RADAR CLOSEOUT.

Human engineering approval and pre-construction reuse review: #297 comment5722798725, following RM-20260918-Radar-r3 comment5722603668 and #351 comment5722608370. The wider current product still includes concepts, Smart Money, ongoing direction coverage and independent company discovery.

## What this slice changes

`runtime/radar_stock_candidates.py` reuses `sector_radar_discovery._validate_projection`, its exact primary/driver breadth pairs, issuer normalization and canonical hashes to collect **all retained leaders from all qualified groups**, including omitted homepage groups and granular drivers. It merges an exact security only, preserves every original direction and raw leader record, and rejects conflicting names, duplicate within-direction rows and invalid numbers/identities.

The existing Sector Markdown renderer now includes this company-first pool. Existing 0–3 homepage groups, detector predicates, ranks, group identity, prices, frozen state/event ledger, Stock qualification, Research admission and investment authority do not change. The output is a derived read projection, not a second canonical registry or a new continuous source.

This is not all-member or all-A-share coverage. Ongoing directions without new qualified events, concepts and Smart Money remain explicit false coverage flags. An ST-labelled source row is retained, not declared eligible. Appearing in this pool does not mean a Stock price test or Research was performed; existing Stock/Research results must be read separately.

## A complete pool and a bounded batch are different

`plan_stock_discovery_batch(result, pool_hash=..., offset=...)` prepares one explicit page under the existing Stock constants, imported rather than raised: at most16 issuers,6 directions,26 requests. Cost is the existing `4 + direction_count + 3 * stock_count` formula; an empty batch costs0. All exact candidate origins count towards direction cost. A single issuer that cannot fit all its origins fails explicitly.

Read/planning order is round-robin over original direction order and retained leader position, not a mixed industry rank, composite score or investment priority. Every plan preserves prior-page, selected and deferred codes; none are silently discarded. The required hash binds every offset to one exact pool. It cannot be carried to a revised source or another date. Prior pages are NOT asserted executed; the next offset is not permission to auto-dispatch.

**The new planner is NOT connected to the live Stock executor in this slice.** The legacy live route still has its existing small-batch contract. This slice delivers broader visibility and the bounded next planning seam, not broader completed price acquisition or completed Pre/Quick. Wiring approved batches to the existing executor, current-session validation and execution receipt is still required; do not use this planner output as an existing Stock plan schema.

## Reuse evidence

Reuse Decision: REUSE + THIN_COMPOSITION. Native exact-result/partition validation, canonical identity, A-share normalization, retained breadth leaders, Markdown escaping and the original delivery are reused. No scheduler, provider, queue service, database, generic discovery framework, new dependency or score.

External prior art already inspected at `jundizhou/easy-stock@707a5338564a4b2b74fee89f0252c3db385cfcab`: `backend/internal/sector/radar.go`, `radar_fusion.go`, `trend.go`. Adopt direction-to-member drill-down and visible scope as product principles; do not import fusion scores, runtime, original code or change the prior license boundary.

## Real saved-input component check — 2026-09-18

Input is the unchanged 2026-09-17 Sector result for run35209312183, pinned R `ac23c61446d7a7001c3ceb82d345d30a31fa5c84`, Git blob `338896d623f46642bef68e9ef03a269772a054ed`. Actual input was recovered from the already-retained Stock archive35210443356 and its Git blob matched R. This is a historical saved-input component check, not a fresh market run, original-code canonical replay or whole reading_hash certification.

Computed output:

-10 qualified groups;11 qualified directions including the driver;3 original homepage groups unchanged.
-55 retained leader-origin records;53 distinct securities;38 securities have only non-homepage origins.
-The original Stock plan contains6 securities;47 pool securities are outside that exact plan. This is not47 new discoveries in the market or47 completed research recommendations.
-Pool hash `5481549e393c2b07063cb6d4b1d0ea2af07784e60c3e9d6a3ded34d857f89b37`.
-First offline proposed page: `002199.SZ,601579.SH,000980.SZ,920087.BJ,300010.SZ`,5 directions,maximum24 requests; execution NOT_EXECUTED. The ST source name for300010 is preserved. This is not a nominated investment shortlist; Stock gates still need to decide any later price-reading qualification.

The chat delivers the full historical pool JSON, original result, proposed first page and Markdown reading. Artifact attachment existence is not a Git blob retention claim for those derived bytes; this document and source code are retained in Git and the exact original stays at R.

Local checks:19 component tests ran using the previously retrieved source subset plus the two edited modules; the reused discovery module's pre-edit blob was verified against current main. This is NOT a full current-main checkout or full-repo local CI. Full exact-head GitHub CI, merge, independent main CI, normal publisher and future natural output remain separate gates with their actual receipts.

## Regression intent and outstanding integration

Tests preserve every group/driver, duplicate origins, fixed pool identity, entire paged universe, no network/write/Research claims, names escaping, empty coverage, invalid numbers and bad authority/session bindings. Existing producer/audit/source/state/Stock tests remain in the full suite; do not delete them to obtain green CI.

The saved pool records input consistency, not provider truth or investment relevance. An informative research question still needs actual evidence work. Next: connect this explicit full pool to approved bounded Stock batches and retain their dispositions; qualify concept and Smart Money inputs as independent discovery paths, not filters that all require prior price strength. These remaining requirements are not closed by this PR.
