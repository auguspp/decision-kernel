# Economic sources — first raw-page capture proof — 2026-09-05

Status: REAL PUBLIC CAPTURE / TWO SPB PAGES MATCHED / TWO MOA HTTP FAILURES / OVERALL INCOMPLETE / NO CONTINUOUS FEED / NO MARKET EVENT / NO INVESTMENT AUTHORITY.

## Exact operational lineage

```text
repository = auguspp/decision-kernel
workflow = .github/workflows/economic-source-capture.yml
run = 33947395994
run number = 1
attempt = 1
event = push
branch = main
implementation = 1c19360e5b400933339f452ba159117d5a8408e2
workflow conclusion = failure
capture status = INCOMPLETE
matched reviewed excerpts = 2 / 4
```

The merge of PR #200 triggered this maintained compatibility check. Each exact selected public URL was attempted once. There was no automatic retry, fallback source, HiThink credential or market-state access. The two failures remain part of the proof; this is not a four-source success.

Independent kernel-tests on the same implementation completed successfully: run `33947395988`, with the 506-test suite. A green unit-test result does not override the failed public compatibility run.

## Per-source result

| Ordinal | Reviewed source | Actual result | Completed capture/request time (UTC) |
| --- | --- | --- | --- |
| 0000 | MOA, August week 3; published 2026-08-25 | SOURCE_UNAVAILABLE / HTTPError / no body retained | 2026-09-05T05:30:53.004672+00:00 |
| 0001 | MOA, August week 4; published 2026-09-01 | SOURCE_UNAVAILABLE / HTTPError / no body retained | 2026-09-05T05:30:53.195756+00:00 |
| 0002 | SPB, June / first-half release; published 2026-07-17 | MATCHED_REVIEWED_EXCERPT / HTTP 200 | 2026-09-05T05:30:57.855791+00:00 |
| 0003 | SPB, July / January–July release; published 2026-08-14 | MATCHED_REVIEWED_EXCERPT / HTTP 200 | 2026-09-05T05:30:59.062111+00:00 |

The original four reviewed record identities remain in `radar_inputs/economic-node-study-2026-09-05.json`. That file was not altered. The capture archive retains an exact copy of each selected source record.

**Diagnostic limit:** this first capture implementation retained the MOA exception class but not the numeric HTTP status. The evidence does not distinguish 403, 404, 5xx or another HTTP rejection. Do not infer permanent unavailability, a bad source URL, source-data revision or a specific access-control cause from `HTTPError` alone. Improving safe numeric HTTP diagnostics is a next bounded task; replacing originals with browser-extracted snippets is not a repair.

## Raw bodies and selected-statement binding

For SPB June, the retained HTML body is 40,024 bytes:

```text
raw body SHA-256
e74f6020e5768e314c58098f3af6e72b9f0e4fab26f939dcb9ed49e2ac7606a8
binding hash
5b1ecaf130a5138ee56c8652c05a9d6e57ceeff8e27cdd292a2237f72364f4d3
observation hash
f4451a292177e2c4f04b38deed2d6757ea3fa2bab36a9cc057eac89a4fa8a73f
```

For SPB July, the retained body is 36,628 bytes:

```text
raw body SHA-256
b4f724c0f6b58180795a56aa734ea9867600e6a5a2d800711a9171542bb8a386
binding hash
a33501c25096b64a661a40a9f4eea245e465fd368ade9af9d13be0b1ded401b2
observation hash
8b9b70d002eb84e374b1753f4b8c59901d5cef8e22525991d97a7095bfff7100
```

Both exact URLs returned HTTP 200 and HTML. The raw bodies, safe response metadata and deterministic text are retained. The original reviewed title, publication date and selected sentences matched the captured text; numeric study observations were reconstructed by the existing parser. June express revenue/volume remained 1360.4 CNY100m / 175.1 100m parcels, and July remained 1303.7 / 170.8 under the original scope and units.

The new observations use the actual capture times above. They do not assert that this system had those exact versions at the July/August publication date. `historical_first_vintage_proven` remains false. The prior manually reviewed observations are neither overwritten nor relabelled as original HTTP captures.

A matching excerpt does not prove every unselected page claim is unchanged, and a raw body hash is not independent publisher authentication. No company-profit, like-for-like pricing or industry-cycle conclusion was created.

## Artifact and independent checks

```text
artifact name = economic-source-capture-33947395994-1
artifact id = 9963755766
ZIP bytes = 30186
ZIP SHA-256 = 1e3185318dc41364eba325abdcf3bd7deea71921a7133794a9e96e481aa1c094
capture hash = 365ddb7f9a7750b6dcaa8828115056be6ed5432ed6792d67789c727c8660da0c
workflow provenance hash = 44058a50e16f3db08fa9f986e3fbef1050b8b4b4ce109ffe87d14e1ec2328d7b
expires_at = 2026-12-04T05:30:40Z
```

The workflow's offline verification reconstructed bindings and returned:

```text
archive_integrity = VERIFIED
matched_excerpts = 2
attempted_sources = 4
status = INCOMPLETE
network_calls = 0
production_state_writes = 0
```

Its exit code stayed nonzero because source acquisition was incomplete. Upload and summary succeeded; neither made the workflow green.

The artifact was then downloaded through the connected GitHub action and checked independently in the local runtime. Checks covered:

- ZIP bytes against the GitHub artifact digest;
- exact capture inventory and all 15 retained file size/SHA-256 entries;
- capture manifest and workflow-provenance content hashes and exact run/SHA;
- both accepted observation/binding hashes;
- an independent HTMLParser text extraction against the retained page text;
- every selected fragment's recorded offset against the captured normalized text;
- observation capture times against request completion, and absence of success files for MOA failures.

This local check was independent hash/text/binding reconciliation, not a second execution of the full project parser. The full parser reconstruction was performed by the recorded workflow verifier. No missing MOA body was synthesized, downloaded from another source or declared verified.

## Unchanged market and product state

The latest real Sector Radar workflow remains #4 / `33939414197` on `5f8f635d191dd8559844d1b74af0dca0cf4c02df`, ending at 2026-09-04 with an empty prospective event ledger. This economic compatibility run wrote neither market state nor candidate events.

PR #198 wired the separate read-only context into future Sector run artifacts, but this economic workflow did not exercise that wiring. Real new-session append, the new market input-audit replay and context artifact publication remain pending. Stock dump download/entitlement/Parquet qualification and multi-day breadth are unchanged and unproven.

There is no Sector schedule or continuous economic monitoring. This artifact expires under its declared retention policy; it is not a durable long-term checkpoint.

HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
