# Inbox calendar timeout recovery v1 — #513

Authority/reuse: #513 comment5776996907; Human explicitly requested the registered
HiThink error be fixed while continuing P1. P0 reliability takes precedence.

Run35704259853/job106669287497 failed at calendar TLS establishment with
URLError(reason=TimeoutError), elapsed_ms12842. Why TLS timed out is UNKNOWN.
No historical run is re-executed or relabelled by this change.

Only attention_inbox_with_odds_watch.main enters the standard-library recovery
scope. One identical calendar GET can be retried once after a typed timeout;
1-second backoff, per-operation timeout at most10seconds, 30-second retry-start
budget (not an operating-system hard wall-clock guarantee). Terminal failure
is retained for the batch; nested callers cannot reset it. Other callers,
custom request_json paths, price-history requests and Sector pacing are unchanged.
HTTP/auth/429/certificate/decoding/calendar-validation failures never retry.
Every successful response still passes the original calendar and price validators.

HITHINK_CALENDAR_ATTEMPT JSON records in original run/job logs retain locally
constructed source, sequence, request/finish clocks, result, retry/backoff and
normalized session-list digest. No key or raw error text is logged. The date-key
is not a source publication clock; NORMALIZED_DATE_LIST_NOT_RAW_HTTP_BYTES is
not raw custody. Same-day process cache hits make no new retrieval claim; new
Shanghai dates use distinct cache keys. Logs are diagnostics, not canonical state.

Reuse: existing urllib transport/calendar LRU/adapter/Inbox/Watch; Python3.12
urllib.error/request and ContextVar/contextmanager; urllib3 Retry reviewed, not
installed or substituted. External candidates examined: AKShare trade_date_hist
blobc3f8baeffe3c1bbea0b54b47c26b707eb87a9a7d (Sina+JS decoder), and
exchange_calendars@bbda29fed902374bdb75acab008f421fbd567823 XSHG
blob7a91411a7b542391a79ee34db86f0ed4bdfafdc5 (precomputed through2026).
Independent fallback is DEFERRED, not rejected: current-source coverage,
retrieval/qualification clocks and compatible market semantics need real-source
verification before adoption. No calendar dependency/code was copied here.
Do not wrap a different source in a fake HiThink envelope.

Fault-injection tests retain original urllib wrapping, calendar/price adapters,
research-package execution, Inbox rendering and typed Watch validation. They
verify success after one TLS timeout and honest failure after two; no live API
or historical reconstruction is implied. Full exact-head/main CI and normal
publisher/readback are separately recorded in the PR. Existing failed state
remains until a new actual Inbox run succeeds. No scheduler/authority expansion.
Rollback uses a reviewed PR, retaining historical failures and diagnostics.
