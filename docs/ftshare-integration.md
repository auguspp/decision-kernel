# FTShare integration — existing consumers, staged acceptance

Requirement: #490; resumed by Human on 2026-09-22. Reuse Decision: THIN_ADAPTER.
The user has requested the already-recorded staged full integration, not a new
provider framework or all catalog endpoints. #297 delivery/response work and its
historical results remain intact. Implementation/CI/live use are separate facts.

## First connection: report discovery

`stock_research_sources.prepare_report_discovery` is an explicit source-only
entry in the existing source module. It calls the bounded
`ftshare_discovery.discover`, then reuses the original CNINFO identity lookup,
pagination, normalized announcement ID/title/time and official locator.
The legacy `capture`, `choose`, page checks, PDF transport and research admission
are unchanged. Nothing runs automatically on import.

Inputs are a security, one announcement date, a report period and issuer name.
The existing `report_match` separates full annual/half-year reports from
summaries and unrelated announcements. More than one matching report is an
explicit ambiguity, not an invented latest version. The report period must end
before its announcement date. The official CNINFO row must match the selected
FTShare ID/title and requested security/date. No guessed PDF URL is generated.

Example (operator action, not a daily schedule or an instruction in source data):

```sh
python -m decision_kernel.runtime.stock_research_sources \
  --ticker 603507 --announcement-date 2026-08-26 --period 2026H1 \
  --issuer-name 振江股份 --output run-output/603507-discovery
```

Output directories are create-only. Each bounded complete FTShare response is
retained byte-for-byte, with request parameters, endpoint/version, HTTP/provider
status, retrieval time and SHA256. Up to four 200-row pages / 2MiB per response;
changed totals, duplicate IDs, missing pages or over-budget results are not a
complete inventory. Failure after an earlier page keeps its raw evidence but
publishes no qualified partial lead list. Empty, entitlement denial, 404,
transport failure, provider rejection, malformed data and identity/time errors
remain separate. No retries, redirects, fallback hosts or arbitrary endpoints.
The public list handler uses no API key; this connection does not inspect,
print or persist any environment credential. A 403 stops, not a subscription
upgrade or a bypass. Other FTShare families have their own future auth contracts.

`announcement_time` remains raw provider text with timezone UNKNOWN. It is not
silently equated with CNINFO's aware timestamp, nor used to backdate availability.
A one-day index does not prove complete disclosure history, current market data
or absence of later corrections. The official discovery query responses are
retained separately as decoded JSON, not falsely labelled wire bytes.

The terminal success is `OFFICIAL_REPORT_LOCATED_NOT_ACQUIRED`: an official
locator for the existing downstream acquisition function, NOT PDF custody,
page verification, Research admission, a completed Research result or Evidence
truth. No model, PDF, market or investment action is executed by this entry.
The production daily request and scheduler are not changed by this slice.

## Reuse evidence

Internal: existing stock_research_sources.report_match, cninfo_http query/org
normalization, saved-research serialization, existing PDF and preparation paths.
Official/public prior art: FTShare-Lab/FTShare-skill,
`ftshare-market-data/sub-skills/report-announcement-list/scripts/handler.py`,
blob 5888b6c353d3809c452e23913f4cc0e76fd0d8ee, inspected at construction.
Its standard-library GET and page contract are reused; the repository-specific
bounds, retained provenance and no-authority meaning are the thin adaptation.
Prior #490 SDK v1.0.8 review (MIT, requests and pandas) is retained; pandas is not
added to core just to obtain JSON. No generated handler catalog is copied.
MIT source availability does not itself grant data redistribution rights.

The two small test index fixtures come from the already retained public
discovery run35603062208 / artifact10641000153 and are historical test inputs,
not fresh production observations:
- 000920-20260821.json: 5158 bytes, SHA256
  8e6b41ea91d7e3840ab03982087ca19833576703370c6ed574a1337c198f3d85.
- 603507-20260826.json: 3177 bytes, SHA256
  8d5561012481755c48c38e2aabd0d736cf9099d1a80c0e2fbb1d74c7895dcb5b.

Offline tests use these real FTShare bytes and simulated CNINFO responses
through the original normalizer. Live provider/official-directory acceptance
must be recorded separately in #490; CI alone does not satisfy it.

## Remaining staged consumers (not implemented by this first slice)

| Family | Next existing consumer | Required acceptance |
|---|---|---|
| Financial | Question/Research structured context | Same issuer/report period/publish clock; original-report cross-check; units/unknowns explicit |
| Company Event | Existing event/question inputs | Contracts and holder changes with source/time/scope; not a new event ontology |
| Market Expression | Existing Stock price/flow observation | Same security/session/adjustment/units comparison before any default-provider replacement |
| Sector/Concept | Existing Sector/Concept Radar | Actual constituents/date/provider identity through existing semantics |
| Industry/Futures | Existing Industry variable input | LC/CU/RB first; contract/units/warehouse/roll/PIT explicit |

NewsNow/feed, Institutional Radar and original issuer-PDF acquisition stay in
place where this account's FTShare scope does not cover them. No paid tier,
trading, automatic Deep, attention-authority change or extra notification task.
Each family's status is accepted only after its real consumer works; one client
or successful HTTP request is not staged full integration completion.
