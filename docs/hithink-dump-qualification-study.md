# HiThink daily-k dump: isolated qualification study

Status: OFFLINE INSPECTOR IMPLEMENTED / NO REAL DUMP DOWNLOADED / ENTITLEMENT AND PRODUCTION QUALIFICATION NOT ESTABLISHED.

## Reviewed primary contracts, 2026-09-05

- https://github.com/HiThink-Tech/Financial-API/blob/main/skills/hithink-finance/references/api/endpoints-market-dumps.md
- https://github.com/HiThink-Tech/Financial-API/blob/main/skills/hithink-finance/references/api/endpoints-index.md
- https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetFile.html

HiThink documents a recent-ten-session unadjusted A-share daily-k dump, a longer historical dump and a separate corporate-action event dump. Signing endpoints return short-lived URLs, not the dataset. The index endpoints and stock dumps are different contracts: stock daily-k cannot replace the 881/884 index state or bridge its gaps.

The current implementation session has no usable HiThink credential in its local runtime; connector discovery did not expose a suitable HiThink data action. Existing GitHub secrets were not retrieved or copied. No signed download was attempted, no credential was requested in chat, and no alternative market provider was used. Public documentation proves advertised capability only, not account access, actual row count, completeness or price consistency.

## First deliverable

`runtime/hithink_dump_inspection.py` is an offline, quarantined inspector of an already obtained trusted local `daily-k-10d` file. It scans the exact documented columns, checks exact stock identity, Shanghai-midnight session, CNY/unadjusted/day convention, finite values, OHLC ranges, unique identity/session keys and explicit expected sessions. It reports latest identity gaps, off-current-universe history, zero-volume rows and exact comparisons with a separately qualified same-session snapshot.

Raw previous close mismatches remain visible and require corporate-action or price-convention review. They are not automatically called split events or anomalies. No returns, adjusted price series, moving-average breadth or investable rankings are computed here.

A partial/unpriced reference set cannot report a full match. Missing stock bars are not filled with zero or prior prices. Unexpected historical identities are retained in coverage diagnostics rather than removed just because they are absent from today's universe. A local hash is not provider authentication.

## Inputs and command

Use an isolated, reviewed research environment with PyArrow available. PyArrow is loaded only inside the optional reader; this PR does not install it, add it to project dependencies, or import it from the production producer. The core row tests require no PyArrow.

```bash
python -m decision_kernel.runtime.hithink_dump_inspection \
  --parquet /research/daily-k-10d.parquet \
  --sessions /research/qualified-ten-sessions.json \
  --universe /research/current-a-share-identities.json \
  --snapshot /research/qualified-snapshot.json \
  --output /research/new-inspection.json
```

Session input: exactly ten ISO date strings in ascending order, established independently from the qualified provider calendar. Universe input: unique exact A-share thscodes. Snapshot input: `market_session` plus `points` containing `thscode`, `last_price`, `prev_price`, `turnover`; unavailable values remain null and make reference coverage incomplete.

The output binds before/after SHA-256 identities of the four input files. Inputs cannot be replaced, silently revised, UPSERTed or overwritten. Output must be new. No network endpoint, presigned URL, API-key field or live-state directory is accepted by this command.

The initial scope is ten-session data with operations limits of 1,000,000 rows and 256 MiB file bytes, metadata files at most 4 MiB. It deliberately is not a full-history warehouse. These limits are resource protection, not investment thresholds. Actual resource use and trusted Parquet-reader installation still need a real-data trial.

## Required evidence before any adoption

1. Verify account entitlement and one bounded signed download. Preserve download time, official endpoint, byte hash and expiry handling, never the usable signed URL or authorization header in an artifact.
2. Independently validate the latest completed session and exact reference identities. Reconcile schema, units, latest prices, turnover and explicit missing/suspended/newly-listed records.
3. Acquire two overlapping immutable vintages and inspect revisions. Do not silently overwrite previously observed values. Establish listing/delisting/suspension coverage rather than assuming today's universe represents the past.
4. Qualify corporate-action data, effective time and publication/revision limitations before constructing adjusted stock paths. A declared ex-date alone does not establish full PIT availability.
5. Only then design a separate stock-panel state and current-basket historical-path breadth. Historical industry membership is not supplied by this dump and remains unavailable.

The inspector always writes `production_qualification = NOT_ESTABLISHED`, including when checked fields match. A zero CLI exit code means only that the supplied fields matched; it does not authorize integration or investment use. A difference or incomplete reference returns nonzero with visible diagnostics. Malformed structural inputs stop without a partial success report.

The actual Parquet reader and real file download are not claimed as validated by row fixtures. No new workflow, schedule, source fallback, sector-state migration, prospective candidate or Human/Research/Investment authority is added.
