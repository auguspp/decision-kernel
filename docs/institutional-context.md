# Bounded institutional activity / report-version context

Authority: #504 (including R5 clarification 5805821503), #297 current next, and
Human continuation on 2026-09-25. Reuse Check: #504/5825988588.

## What this slice delivers

A source-only CLI and manual-only workflow obtain one explicitly bounded
issuer/publication window. The initial trial is **002436.SZ, 2026-08-11 through
2026-09-24**. Each of two reviewed public endpoints receives exactly one request,
page 1 / at most 50 returned rows. No pagination sweep, host fallback, proxy,
retry, model, PDF, schedule, recommendation or investment authority is added.
The workflow's eight-minute job limit is an outer failure boundary, not a claim
that a timed-out capture is complete. Requests use the existing isolated
Requests session, fixed destinations, no redirects or ambient credentials,
10/20-second connection/read timeouts and a 512 KiB response limit.

The first scope is intentionally a **bounded sample**, not all disclosures or
all institutional visits. `provider_total`, `provider_pages` and the actual row
count travel with the result. Missing totals or additional pages do not become
complete coverage. Empty returns are not proof of no activity. HTTP failure
bodies, when safely received within the transport boundary, remain byte-for-byte
in `.body` files with SHA256, status, request identity and retrieval clocks.
401/403/429 stop the remaining provider request; other source failures remain
visible while the other fixed endpoint may receive its single request.

## Meaning and comparison limits

Activity uses `RPT_ORG_SURVEY` (participant-level detail), not the existing
exchange-seat Institutional Radar. `NOTICE_DATE` selects the disclosure-date
window; `RECEIVE_START_DATE` remains a different event-date claim. An event may
precede the requested disclosure window. Neither date proves historical public
availability. Missing event identities, independent institution identities or
participant identities leave event/institution/person counts **UNKNOWN**.
Exact source-row duplicates are collapsed with all original row locators kept;
raw institution/person text is not split into invented independent entities.

Reports preserve `infoCode`, institution code/name, publication date, complete
provider row and a content-version hash. Same-ID changed variants remain
separate versions. Relative EPS slots (`predictThisYearEps` and following slots)
are **not** assigned calendar years from the retrieval clock or publication year.
Without independently established target period, currency and share basis,
`forecast_revision=NOT_COMPARABLE`; no numeric revision, consensus, probability
or investment signal is produced. Zero, missing and invalid source strings are
preserved distinctly. Hosted Quick may interpret these observations and seek
missing evidence; this source does not accept Research or generate Questions.

`context.json` is a deterministic projection, not a raw response. `capture.json`
binds both planned source receipts to the exact main code/run/attempt and
SHA256 of each raw body. `replay` validates that binding and recomputes the
projection and summary without source calls. It does not certify the provider's
economic truth. Original source bodies are untrusted data, never instructions.

## Reuse rather than replacement

Internal: existing `easy_stock_context` JSON/Decimal/clock/seal/authority helpers,
`hithink_dump_trial._session`, canonical JSON/hash, ordinary CI, Actions artifacts
and native Git archives. Existing FTShare company inputs handle contracts,
shareholder counts and holding changes, not visits or analyst versions; their
schemas/executors remain untouched. The EasyStock eight-request capture's
historical workflow binding is not weakened to accommodate this new sample.

Official: Requests/standard CLI and GitHub Actions artifact primitives;
[AKShare official interface description](https://akshare.akfamily.xyz/data/stock/stock.html)
for `stock_jgdy_detail_em`. Its unrestricted all-history DataFrame helper is not
installed or invoked. The issuer/disclosure-date filter below is a scoped
adaptation, requiring live acceptance rather than a claimed official SLA.

External exact implementations read:

- [Vibe-Research 7f3a08b...](https://github.com/simonlin1212/Vibe-Research/blob/7f3a08b85451b54c762898789e2dcaa5d7d2ec98/.agents/skills/data-access/scripts/sources/eastmoney.py):
  `eastmoney_reports`, reportapi `/report/list`, exact issuer and report fields;
  MIT. Its broad historical window, automatic host/proxy behaviors and model
  application are not imported.
- [AKShare 0191689...](https://github.com/akfamily/akshare/blob/0191689d57c667b7c7a198fd0cf97316837ef311/akshare/stock_feature/stock_jgdy_em.py):
  `stock_jgdy_detail_em`, datacenter-web `/api/data/v1/get`, `RPT_ORG_SURVEY`
  columns/order/source contract; MIT. Replaced all-market/event-date sweep with
  one exact issuer and publication-date window, no duplicate first-page fetch.
- [EasyStock 0470c34...](https://github.com/jundizhou/easy-stock/blob/0470c34b2d77a18c8389c6e9e0bcf324611c2b3a/backend/internal/providers/eastmoney/market_overview.go):
  `MarketReports` field comparison, source meta and publication handling. Design
  reference only here, no new direct code copy; its PolyForm Noncommercial
  obligation still applies to existing EasyStock-derived repository modules.

**Reuse Decision: REUSE + THIN_ADAPTER.** Two finite protocol requests do not
justify installing another platform or building a generic provider framework.
These are different endpoints from Concept push2, not independent vendors or a
promise of better reliability. Concept v1/v2/v3 runs remain unchanged.

## Execution, retention and remaining acceptance

Normal exact-head PR full CI, normal merge and applicable main CI/publication
precede one fresh manual source trial. The workflow checks its dispatch SHA
against `code-sha` and successful attempt-1 main CI before any source call.
A green workflow means the capture/replay/retention contract ran; inspect the
per-family statuses before claiming any acquired data. Never rerun a historical
source attempt to replace its outcome. A later authorized window is new data.

After the live result, retain exact files/run/artifact in native Git and the
existing purpose index; do not rely on expiring Actions artifacts as permanent
memory. Registration, ordinary entry discoverability and actual Hosted Quick
consumption are separate checks. This slice does not add a normal-reading
consumer or automatically enable a daily schedule. #504 remains open until its
scoped real-source/retention/reading acceptance is recorded. #364 gaps and P1
multi-day discovery/continuity acceptance remain open.

Exit responsibility: if retired, retire this manual caller and source-specific
tests together, preserving recorded source/Research history and any still-used
reader. No per-test registry or permanent source monitor is added.

## MIT notices for adapted endpoint protocols

Copyright (c) 2026 simonlin1212

Copyright (c) 2019-2026 Albert King

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
