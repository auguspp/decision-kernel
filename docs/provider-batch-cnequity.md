# Unified FTShare + CNEquity input batch

Human changed #490 delivery granularity on 2026-09-22: complete the remaining relevant families in one batch, and reuse rootSunc/CNEquity. This page supersedes the earlier interface-by-interface construction order, not Research/Market/Human rules. Reuse Decision: THIN_ADAPTER + REUSE. No investment authority.

## One existing entry

```sh
python -m pip install -e '.[cnequity]'
python -m decision_kernel.runtime.stock_research_sources --mode batch \
  --config provider_requests/ftshare-batch-example.json --output run-output/provider-inputs
```

The example is explicitly a historical 2026-09-21 session, not an automatic latest-session selector. The operator owns company/board/contract selection; raw source text cannot select endpoints or execute instructions. The optional `company` section reuses the existing five financial and three company-event preparation functions. Existing report-discovery remains available through the same source module; no repeat download is required. `FTSHARE_API_KEY` is supplied by the existing runner environment, never by config or URLs.

One result covers stock daily fields/flow, SW membership and metrics, Eastmoney concept membership and typed price input, and fixed LC/CU/RB contracts and warehouses. Each capture retains exact responses, request identity, HTTP/provider status and real retrieval clocks. Every route has finite fixed parameters, 2 MiB response limits and bounded pagination. Auth, entitlement and rate-limit stops prevent later attempts. No automatic retries, redirect, paid-tier upgrade or default-provider replacement.

`provider-batch.json` and `.md` expose every requested family's result. A complete program run can still produce `PARTIAL_BATCH_CONTEXT`: this is data coverage/quality, not a claim that every source returned acceptable data. Invalid OHLC cannot become qualified prices; valid contract identity/warehouse records remain inspectable. Company inputs retain their original partial status. Raw files are not primary issuer PDFs, Research admission, independent economic truth, or Human exposure.

## Native consumers and identity

Concept prices use the original `SectorPriceSeries` / `SectorPricePoint` and its validator. An Eastmoney BK code is not rewritten into a HiThink TI code. One-day data cannot satisfy the existing 5/20/60-session ranking and cross-section requirements. SW interval membership retains source level rows; duplicate appearances at different industry levels with identical requested membership intervals are grouped without double-counting or dropping provenance. Conflicting intervals fail.

Stock comparison binds ticker, session, currency, volume units and a separately retained reference identity; it reports residuals without approving a replacement. Float-serialization artifacts remain visible. `cum_adjust_factor` is documented unusable and is not adopted as a verified corporate-action adjustment. Source-defined order flow does not become issuer cashflow or Fundamental Belief.

Industry output reuses the original `INDUSTRY_VARIABLE_OBSERVATION` kind, canonical sealing and no-authority fields, with an explicit fixed-contract variant. Exact contracts such as LC2610.GFE are not main-continuous symbols. Trade date, quote currency/unit, multiplier and warehouse unit remain separate. LC warehouse lots are not silently converted to tonnes; no cross-unit totals, basis, beneficiary or inflection is invented. The original HiThink Industry collector/renderer is unchanged.

## CNEquity: use its implementation, not another home-grown lake

Inspected upstream: rootSunc/CNEquity commit `1650e384a3fd1f67a70144a489acc91432f1df27`, version 0.11.0, Apache-2.0 and upstream NOTICE. Its own vendored components retain their own notices. Using the package is not a grant to redistribute third-party data. No upstream implementation is copied into Kernel.

Reused actual APIs: `cnequity.query.load`, `domain.schemas`, `storage.parquet.StagingWriter` and `compact_dataset`. Its Parquet/query/revision/PIT/adjustment algorithms remain upstream. The dependency is optional for Kernel core and explicitly present in dev so CI executes real integration tests rather than skipping them. Core dependencies remain only Pydantic.

`cnequity_bridge.read_lake` can read selected bars, factors, corporate actions, financial items, counts, constituents, instruments and status data. Supply a bounded existing local lake and explicit dates/symbols. Strict PIT and strict adjustment are always used; unknown historical availability or absent factors do not become exact facts or factor=1. A revisioned adjusted read must pin bars and factors independently. Reads verify the bounded lake identity before and after, retain row sources, and never run acquisition/backfill/scheduling.

Optional batch config example:

```json
{"lake":{"data_root":"data/retained-lake","dataset":"daily_bars","start":"2026-09-01","end":"2026-09-21","symbols":["603507.SH"]}}
```

This section is added beside `market` and optional `company`, not used alone. `as_of`, `adjust` and per-dataset `revision_map` may be explicitly supplied. No lake is bundled with the upstream package. Missing deployment data remain unavailable. `retain_bars` can import explicitly sourced unadjusted share-volume bars into a NEW isolated native lake, retaining exact original JSON alongside Float64 Parquet. It never overwrites an existing lake or relabels old HiThink/FTShare data as an independent CNEquity source.

## Actual evidence and remaining data limitations

Initial multi-family run 35682717289 retained raw responses and failures. Corrected explicit contracts were subsequently captured through the new adapter in run 35683374665: exact SW industry, compact board dates, and exchange-qualified futures symbols. Documented board items pagination differed from actual records pagination; the observed envelope is handled explicitly. Original failures stay unchanged.

A real LC2610 row for 2026-09-18 reported open=135900 above high=133760. The input remains invalid for OHLC comparison, not repaired by changing numbers. SW raw rows describe both levels of the same memberships; all source rows are retained. These are bounded provider-contract findings, not deeper company research.

Full-suite CI, native CNEquity execution, final real batch capture/replay and archive/readback must be recorded with actual run evidence in #490/associated PR; this document does not preclaim those future runs. Financial balance and nonempty current company-event samples retain prior known limitations until an actual later run changes their state. Automatic daily Research/Brief is not enabled by a source-only batch. The earlier blocked STATIC/semantic-supplement writes are not part of this work.
