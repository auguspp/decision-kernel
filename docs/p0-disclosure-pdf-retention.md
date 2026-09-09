# P0 source reuse: retain PDFs at the existing scan boundary

Requirements and authorization: Issue #297. This is a small acquisition-retention change for the existing six-company scan, not a new P0 gate or a research execution.

## Why this change exists

The saved scan `34354228621` / artifact `10105040865` contains five original assessment packets. Some page text is garbled, and one document is `NO_TEXT`. Those packets contain hashes and extracted pages, not their original PDFs. Fetching the same documents again in a research conversation introduces unnecessary requests and another failure opportunity.

`scan-disclosures --packet-dir ... --raw-pdf-dir ...` now wraps the ORIGINAL PDF fetcher. Each normal return is stored before the ORIGINAL extractor receives the same bytes. There are no additional requests, retries, provider changes, parser changes or OCR. Omitting the new flag preserves the original CLI behavior. Packet serialization, assessment hashes, Evidence retention labels and Funnel remain unchanged.

## Saved files and failure meaning

The capture directory must be new and separate from the packet directory. It contains:

- `objects/<sha256>.pdf`: exact returned bytes, one local copy for identical bodies; never executed. This is not a network cache: each original fetch still occurs as before.
- `manifest.jsonl`: source locator, body hash, byte count, path, retention time and successful retention sequence. Retention time is NOT publication/availability time. This is not a complete HTTP or Research tool-call journal; failed transport calls remain failures in the existing CLI/job log.
- `capture-summary.json`: written only after all assessment packets have been written successfully; binds the manifest hash and counts. No completion file means completeness is not established, even if some PDFs exist. A zero-body completed capture is not a full-market quiet statement.

If parsing, a later request, packet writing or local retention fails, the original error propagates; already saved bodies remain available. No exception becomes WAIT or successful Research. Local exclusive writes and a closed-file manifest do not claim platform-wide crash recovery or a hard permission sandbox.

The existing `decision-inbox` workflow adds just the flag and a separately named `official-disclosure-primary-bodies` artifact, uploaded with `always()` and the existing 14-day retention period. The original successful `official-disclosure-scan` artifact remains unchanged in layout and success requirement. A failed scan can therefore expose partial raw material without becoming an eligible complete scan. Schedule, concurrency, account credentials, HiThink calls and the six-company scope are unchanged.

## Consumer and real acceptance

Read the artifact through the same producing run/attempt/head identity and original archive checks; compare the selected packet's `source_locator` and `pdf_sha256` with the manifest and recomputed body SHA256. Existing reader size/safety limits still apply; an oversized or incomplete artifact is a visible gap, not permission to relax those limits. Read or render the actual PDF when text is unreadable. Never infer that bytes retained means the document is understood, true or semantically accepted.

Do not rewrite historical packet Evidence from REFERENCE_ONLY to FULL_ARTIFACT. A subsequent admitted execution may create its own accurately retained Evidence referencing the actual artifact, while the original packet and request identity stay frozen. No new field in Kernel/packet/Research schema is introduced.

The first 603986 request remains reserved and failed on its original URL-safety refusal. This change is NOT an alternate transport for retrying that blocked request; no new invocation of it is authorized here. No production dispatch or Re-run is needed for this engineering acceptance. The next already-authorized natural scan can demonstrate raw retention under its own actual run, after which exact artifact/readback and original-PDF inspection are separate acceptance evidence. Tests and CI do not pre-sign that future run, P0-4A/4B, native Scheduled, Human response or live-use days.

Reuse references: existing `cninfo_http.fetch_cninfo_pdf_bytes`, `prepare_disclosure_assessment_packet`, `pypdf`, Python pathlib/hashlib/json, and `actions/upload-artifact` (https://github.com/actions/upload-artifact). The pypdf extraction documentation explains that extracted text is not equivalent to visible PDF content (https://pypdf.readthedocs.io/en/6.12.0/user/extract-text.html). No new dependency is installed by this change.
