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
upgrade or a bypass. Other FTShare families use their own documented auth contract.

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

## Financial input through the same source-preparation entry

`stock_research_sources.prepare_financial_context` consumes the five fixed
families in `ftshare_financial`: balance, income, cashflow, forecast and express.
It produces inspectable `financial-context.json` and `financial-context.md`, plus
all bounded raw returns and capture records. This is operator-invoked secondary
Question/Research context, NOT an automatically enabled daily request, primary
custody, a Research result or a new egress permission. Required original issuer
materials and the existing admission/budget/continuation rules remain required.

```sh
python -m decision_kernel.runtime.stock_research_sources \
  --mode financial --ticker 603507.SH --year 2026 --report-type q2 \
  --output run-output/603507-financial
```

Use the already configured `FTSHARE_API_KEY` through the runner environment;
never put the value in commands, files or messages. Only the fixed official
FTShare host and exact financial route/parameter set receive the credential.
No redirects, retry, alternate host, subscription upgrade or all-market query.
A reflected credential is rejected before retaining the response. Authentication,
entitlement and rate-limit stops prevent later family requests in that attempt.
An independent family's transport failure remains visible without discarding
other valid families. No network or environment access occurs on import.

The provider's stock_code mode returns one issuer's periods. The adapter does
not pretend that year/report_type filters this server mode: it retains up to
four complete 200-row pages per family, then explicitly selects year/period/form.
The per-response limit is 2MiB; original whole-context limit stays 448KiB. Failed
pagination cannot qualify a partial family, and oversized context is not clipped.
Amounts use decimal strings; null remains UNKNOWN. Balance is period-end stock,
while income/cashflow are year-to-date, not isolated quarterly observations.
Adjusted/unadjusted consolidated forms stay distinct. Multiple matching versions
require review instead of silently picking one. Provider publish dates keep DAY
precision and UNKNOWN timezone; historical availability is not inferred from
these dates or from today's retrieval. Forecast and express remain respectively
forecast and preliminary data, not final actuals; uncertain units/attribution
remain unmapped original fields, not inputs to forecast-versus-actual arithmetic.

Reuse evidence for this slice: existing FTShare discovery strict JSON, no-redirect,
clock and error primitives; original source entry and byte bounds. Actual official
SDK implementation inspected: `src/ftshare/base.py` blob
abc230cb1a3ab40ac36cfec15e0bbb573671deb8 and `src/ftshare/apis/stock.py` blob
e1133fabaef87ed1b216e71bbe66770ac74016c8. Its fixed header and stock-code semantics
are reused without adding the SDK's pandas dependency to core. Official Skill
income/balance/cashflow field contracts were checked, not treated as infallible.

### Real partial acceptance anchor, not a synthetic all-green sample

Run35674021253 used code9d2b4dd7a861c9e40e92cda762e0a9ace553e243 for
603507.SH /2026q2. Five requests, no retries: balance had TRANSPORT_FAILURE;
income and cashflow each returned43 rows with an eligible target-period row;
forecast returned14 rows including the target; express returned one2022annual
row, so target2026q2 is NOT RETURNED. It is not proof the issuer never disclosed
an express report. No PDF/model/market call was made. The original raw ZIP is
artifact10672795706,4740529bytes,SHA256
3785dcef6293304f52abad8d5c275f703b1e846cf674bc382e2012935a60062a.
Later offline consumer replay must keep these actual response bytes/clocks and
failure, and must not be described as another live request or a repaired balance.

Twelve selected monetary fields reconcile to retained issuer calculations at
6eacd1fe5963514948cbcf0a516a13098286fe14,
`docs/readings/603507-profit-hedging-cash-2026-09-21/calculations.json`, blob
c5022a9d1c533033fc7fa31b3b518a63fb5c1b37. This scoped comparison reuses already
reviewed issuer material; it is not a full financial-statement audit.
The Skill labels parcomp_n_profit as ex-item parent profit, but this real return
149833033.7100 matches retained parent net, NOT ex-item parent97005857.01.
Therefore the adapter retains this field unmapped. One example does not authorize
a global field redefinition or alteration of the provider's original response.
Balance still requires a real successful sample; the whole financial family is
not accepted as fully complete merely because other inputs or tests succeeded.

## Remaining staged consumers

| Family | Existing consumer / state | Remaining acceptance |
|---|---|---|
| Financial | Source-preparation context implemented; real partial anchor above | Successful balance and complete intended use; no automatic Research admission |
| Company Event | Not implemented; existing event/question inputs next | Contracts and holder changes with source/time/scope; not a new event ontology |
| Market Expression | Not implemented; existing Stock price/flow observation | Same security/session/adjustment/units comparison before any default-provider replacement |
| Sector/Concept | Not implemented; existing Sector/Concept Radar | Actual constituents/date/provider identity through existing semantics |
| Industry/Futures | Not implemented; existing Industry variable input | LC/CU/RB first; contract/units/warehouse/roll/PIT explicit |

NewsNow/feed, Institutional Radar and original issuer-PDF acquisition stay in
place where this account's FTShare scope does not cover them. No paid tier,
trading, automatic Deep, attention-authority change or extra notification task.
Each family's status is accepted only after its real consumer works; one client
or successful HTTP request is not staged full integration completion.
