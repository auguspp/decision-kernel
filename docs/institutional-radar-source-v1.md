# Independent institutional leaderboard source v1

Status: BOUNDED IMPLEMENTATION; LIVE SOURCE ACCEPTANCE NOT YET ESTABLISHED.

This implements one Smart Money dimension under #297 Radar-r3 and #351 HOME-14. It is not full Smart Money, concepts, the Stock multi-page executor, automatic research or a new investment rule.

## Reuse decision and source boundary

Reuse Decision: THIN_ADAPTER. Reuse the existing HiThink fixed host and credential, Requests `_session`/`_check_response`, explicit-calendar normalization, security normalization, safety checks, canonical hashes and native GitHub Actions/artifacts. Do not extend the Sector audited route allowlist or couple independent discovery to Sector health/price strength. A small manual-only source workflow isolates these two requests; it is not a replacement scheduler, provider registry, agent, queue or market-data platform. No new dependency or extra is introduced; the existing feeds extra supplies pinned Requests.

Exact upstream contract reviewed: HiThink-Tech/Financial-API@0a629aba2b3977a419f7c4330972d2047c8612da, `docs/api/a-share/special-data-dragon-tiger-list.md`, blob5904d1b0de226b7d0a501525e46d1aca2c3a8a4c. Prior diligence is retained in #351/5723002863. It documents `board_type=org`, explicit date, no pagination, source `count` versus `stock_count`, and1/3-day windows. A documented endpoint is not proof of entitlement, live shape or exchange completeness. Existing EasyStock prior-art remains a product reference, not imported code or a licensed dependency.

## One source observation, not a signal

A fresh explicit main workflow attempt obtains exactly one calendar and one institutional leaderboard for an explicit completed session. The code checks actual board/date, midnight date key, ticker/exchange/name, row windows, duplicate security-window pairs, optional numeric fields and distinct stock count. Missing institutional values remain null, not zero. The supplier's upstream record count and returned window-row count are reported separately; differences do not invite a guessed aggregation formula. The caller cannot select a favorable subset of rows.

Each security retains all distinct1/3-day records and each exact raw source row. No cross-window or cross-day sums, flows into concepts, current holdings, continuous buying, trader intention, corporate benefit or probabilities are inferred. Source concept/reason labels remain unverified data. Negative and missing institutional net values remain visible. Order is original first appearance, not research priority or investment rank.

No existing Sector/Stock qualification or prior ResearchSnapshot is required to observe a company. Every row explicitly says Stock/Research were not executed by this path; this does not assert that the repository has never researched the company. The next-question text is an orientation prompt, not completed Pre/Quick or an economic explanation.

## Clocks and retained failures

Target session is not publication time. Actual requests and receipts may occur later; the midnight source timestamp is only a market-date key. First-vintage/historical PIT availability and source publication time remain unestablished. Calendar consistency does not establish comprehensive exchange data coverage.

No redirects, retries, cookies reused between requests, environment proxies, alternate providers or new credentials. Two requests maximum with the existing20-second pause; each body8MiB, retained capture32MiB, row bound2048. HTTP200 still requires business-code success. Safe original response bytes are retained unchanged before normalization. Unsafe/malformed bodies are not stored; a safe stage/reason survives, not a guessed remote cause. A failure is not a successful empty leaderboard. Interrupted/unsealed artifacts are not accepted.

`verify` performs zero network calls, checks the code/input inventory and exact request/clock identity, rebuilds successful readings from the original bytes, and compares all derived JSON/HTML. Failed transport/unsafe attempts retain only their verifiable subset and are labelled retained failures, not independently re-proven remote failure causes. Pure render/hash checks do not authenticate the provider or certify economics.

## Runtime and delivery

The `radar-institutional-source` workflow accepts an explicit session and exact reviewed main SHA, rejects reruns/branch execution, has read-only repository permissions and no schedule/workflow-run activation. Only the acquisition step receives the existing provider secret; replay does not. It uploads payload, replay receipt and one bounded native `git archive`/tree of that exact code for executable offline reproduction. The code archive is diagnostic/replay input, not production restore/canonical state. Artifacts expire after30days; Git code and this scope remain the canonical process entry.

A fresh run is separately authorized/reconciled in #297. No automatic next run, retry, Research, Odds, Watch or Action is implied by merge. Standalone attachment delivery does not mean current-state/Brief daily integration is complete.

Tests use clearly synthetic dates/companies/leaderboard activity and include opposite overlapping windows, unknown values, bad clocks/identities, source-label escaping, raw-byte capture/rebuild, rehashed-output tampering, failure retention, create-only I/O and manual-workflow boundaries. Local subset checks, full exact-head CI, independent main CI/publication and live source/Human-use acceptance remain distinct.

## Still required

Stock discovery-pool batches still need live-executor integration and dispositions; the existing historical Stock reading mismatch remains separate. Concept selection and persistent observations are not replaced by source concept labels. Other Smart Money dimensions—research visits, forecast revisions, disclosed ownership, actual insider/buyback execution and locked capital—remain in the approved Radar-r3 track. This one-day leaderboard is only the first independent input.
