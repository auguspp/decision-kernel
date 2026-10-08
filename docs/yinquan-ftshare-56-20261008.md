# YinQuan — new, isolated 56-call FTShare study (2026-10-08)

Human explicitly approved a new separate one-shot with **at most 56 FTShare
source requests**. The previous Tushare task (run 37718496941) was already
consumed and failed with date_range_too_large; its PR794 comment 6051016633
and raw failure archive are immutable and **not retried**.

Freeze the fourteen existing user-DAT symbols and four dated windows per symbol:
full 2023, full 2024, full 2025, and 2026-01-01 through 2026-09-30.
Each is shorter than the official 12-calendar-month stock-candlesticks limit.
All requests use Shanghai-millisecond bounds, interval_unit=day,
adjust_kind=none, no limit truncation, single FTShare fixed endpoint.

Reuse Decision: **REUSE + THIN_ADAPTER**. The existing fixed FTShare transport
owns credentials, no-redirect and credential-reflection protection and strict
response budget. Only the finite new source route is added. Existing three-stock
comparison, C2 pilot and all normal providers/schedules remain byte-preserved.
Official contract pinned in FTShare-Lab/FTShare-skill at commit
d31ee34c86d68569a486feedec5dd8d5cc29db31.
Historical turnover_rate is vendor percentage points; correspondence to the
original Tongdaxin HSL is NOT ESTABLISHED.

Normal Ready PR/full CI and separately successful exact-main CI are required
before the new manual workflow may use its source key. It checks main, exact
SHA and a unique single workflow run *before* source credential exposure.
No retries, no fallback, no new scheduler, database, generic provider, signal
route, Quick/Brief/Watch/Sites effect or trade authority. Every attempted HTTP
request is checkpointed before transport; first error ends the batch.

Original source bytes, identities, clocks, SHA256, per-symbol coverage and
normalized OHLC/volume/turnover/turnover_rate CSV are saved in one isolated
30-day Actions artifact. Offline exact replay performs zero market requests.
HSL gaps remain UNKNOWN, not zero. Source vintage is retrospective, not PIT.
Price series here are unadjusted, not qualified corporate-action total returns.

After a complete validated run, the ChatGPT research workspace downloads that
exact artifact by run ID and checksum; it joins data with user-provided 14 DAT
files **without uploading proprietary DAT to GitHub**. Rebuild the original
nested 89-day brightness formulas and inspect 5/10/20-day event outcomes and
false positives, preserving missing prices and future-vintage limitations.
No claim of a tradable or predictive strategy follows from historic data alone.

Retire the one-shot executor by a normal PR when finished, retaining the
historical source and validation receipts.
