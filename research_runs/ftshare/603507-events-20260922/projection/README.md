# Offline company-event projection, not a second acquisition

Recorded 2026-09-22. This projection was rebuilt after the original capture, with zero new FTShare, model, PDF or market requests. Its started_at/finished_at and row retrieved_at/available_at values describe the retained original acquisition, not the later rebuilding time.

Original capture commit: `86dccb87f4e1c61dcea23c08d3fadf94a68e5a11`.
Original acquisition producer: `951807b88453e9dc7043d454caffe0f9db44f038`.
Original run/artifact: `35677062431` / `10673871181`.
Source root: `research_runs/ftshare/603507-events-20260922/original/`.

Rebuild code head: `aff174fa04dbd33eb96b35314dfa1b2e228ce67b`.
Company adapter blob: `1f45dd6eab6dda0e970b39918ceba70bd9ca9cc2`.
Existing source-consumer blob: `dc012d37c6b8e65724e77b7ab08db1e65f680f6d`.

The first capture retained IDENTITY_MISMATCH for the documented bare versus observed exact qualified trade_code. That original capture and all response bytes are unchanged. The rebuild accepts only the exact requested qualified identity or exact documented bare identity; wrong exchanges and arbitrary suffixes remain rejected.

Three retained HTTP200/provider200 responses were replayed with the original request parameters, digests and clocks through prepare_company_event_context. Result: four holder-count records, an explicit empty contract return and 148 named-change rows excluded because they precede the publication window. No claim of absence from all issuer disclosures, primary custody, completed company Research or automatic Brief follows.

Paths in projection rows such as holder_counts/page-1.json resolve relative to ../original/, not this projection directory. The complete raw original files and their original capture.json records are located there. The two adjacent projection JSON/Markdown files are outputs of the original source entry under the rebuild code, not overwritten raw source evidence.

The initial and repaired statuses are intentionally separate. Positive nonempty contract/current named-change samples and complete downstream daily adoption remain unverified. Existing research results, budgets, permissions and schedules remain unchanged.
