# P0 Stock source artifact byte audit — 2026-09-14 Beijing

This is a source-reading and input-capacity record, not Research, Human
acceptance, a successor permission, or an instruction to dispatch.
Authority remains #297 comment5652950925. Pre-construction readback/reuse:
#297 comment5654388807. Do not repeat #352/#353 or source-recovery-v1.

## Fixed starting point

- main: `121ffe5dd8d1e4ffc6e9278b4be8f1c20d15a814`
- read-model/current-state: `bf2c7d715cb228b830ef87ff11afa2f6d5f67d22`
- research-work/stock-business-v0: `dc75bd59a06fa7b6da30c855fe232348270db089`
- latest Stock invocation/source preparation: `34765190284`, attempt1
- latest Research execution: `34751517820`; no later Stock run at this read

## Actual artifact bytes

The original GitHub artifact downloader supplied artifact `10320565453`,
`stock-source-preparation-34765190284-1.zip`. The ZIP was actually read and
extracted, rather than inferred from logs: 12,563,240 bytes,
SHA256 `25cda8a1d4afb4783432320239cd6271fe193cfdc5ed6dc2095a5deb833dce9c`.
All 91 members passed CRC, with no duplicate names, absolute/traversal paths,
symlinks or encrypted entries. Uncompressed total: 17,331,131 bytes.

Both issuer inventories match their preparation hashes and selected IDs.
Every saved query return matches its journal SHA256. All 33 issuer PDFs match
their filename/journal hashes and lengths; extraction records match PDF and
source-locator identities and have complete numbered page sequences.
Completed-read/body-event IDs match each checked-body list. This checks
retained byte consistency, not financial truth or fresh source-site availability.

603353.SH still has the original 20 selected / 19 checked preparation record;
300711.SZ has 13/13. The original ZIP and those failure records are not rewritten.

## Actual Heshun page23 reading

From the audited ZIP: announcement `1225530965`, PDF SHA256
`cc3a234f7551ef02c401fae60452b891ca48ef0047aad7e26981e0f4ec7948fa`, 23 pages.
Original extracted page23 text is empty. The whole page was rendered and
visually inspected before the note was written. Using pypdfium2 5.8.0 /
PDFium149.0.7825.0 and the original full-page render parameters gives RGB
1180x1678, scale2, rotation0, crop[0,0,0,0], draw_annots=true and pixels SHA256
`196d9e941525f37577039e27b81fed72354caa0f1afb2844f856940ef6177059`.

The page describes itself as the independent financial adviser report's
signature/seal page. Visible institution text, a red circular seal image and
printed date are recorded only as page contents. No signatory identity,
authenticity, actual signing date or legal effect is certified.

The added original-contract note is
`research_runs/source-readings/cc3a234f7551ef02c401fae60452b891ca48ef0047aad7e26981e0f4ec7948fa/page-23.json`:
1,778 bytes, SHA256
`6c50058e86954f71f0e97692a1b5b55fe692e32a8d34e6b29041e6b1912dbe49`.
It is new same-PDF reading material, not independent new Evidence or permission.
A narrow regression calls the existing `checked_visual`; the existing generic
binding, tampering, loader-clock and no-review tests remain unchanged.

## Guangha: storage success is not egress success

The actual complete `300711.SZ/sources/prepared-context.json` is 636,462 bytes,
SHA256 `4cb6c5a18a18ef6ed8b011f315c7bac000a3ecaaf4b21b6cd72b476a3344cbf0`.
Its inventory and all 13 document/page sets match the saved extraction/reading
records: 286 original PDF pages. Nothing was clipped or summarized.

Local, nonproduction probes on those exact bytes:

- zlib level9: 165,870 bytes; base64: 221,160 bytes. Decoding returns the exact
  original 636,462 bytes and SHA256. This does not implement checked-source storage.
- Lossless JSON whitespace removal still needs 605,252 bytes, above 512KiB.
- Using the current sorted, indented serialization, the minimal object containing
  only `public_context` needs 642,620 bytes, SHA256
  `bb8a980a24da47ac2de69426940a54a298ee0d45f9d3b1e5e9973f730cba4a52`.
  This is a LOWER BOUND, not a measured final Pre or Quick request. The real
  request adds binding, question, unknowns, discovery, Evidence IDs, SYSTEM,
  strict output format and, for conditional Quick, the validated Pre result.

Current code has distinct checks: sources context448KiB, Retainer file512KiB,
checked-source512KiB, and Stock model request512KiB. `model_call` also rejects an
opt-in above512KiB. `research` requires the supplied context hash to match the
MODEL_CONTEXT source. Saving compressed bytes alone therefore does not satisfy
source identity or the decoded egress contract. No limit is changed here.

The production lossless storage/checked-source/decode/final-egress adapter and
real final request measurement remain NOT IMPLEMENTED / NOT ACCEPTED.
Do not send a compressed string to the model or drop bodies, metadata needed
for identity, risk evidence or required material to fit a limit.

## New Heshun capacity finding after the page reading

Fixing page23 does NOT make Heshun ready for model execution. A local size-only
probe over the same 20 selected PDFs counts 372 pages and 622,943 UTF-8 bytes
of required readable page text alone, before JSON/source metadata or any model
request envelope. This already exceeds both448KiB and512KiB.

The probe uses the artifact's original extraction for18 documents, its saved
same-PDF reading for1225530957, and the same pinned PDFium text method for the
22 nonempty pages of1225530965 plus the actual new page23 note. It does not
invent a production context or re-date a source acquisition. No selected page
was omitted. This is a page-text LOWER BOUND, not the final serialized context,
not a new source-preparation run, and not production20/20 acceptance.

Thus BOTH issuers now have a confirmed full-input capacity blocker. Heshun's
new reading must pass the original trusted-main/CI path, and both issuers still
need the bounded lossless storage/checked-source/decode/final-egress bridge.
The old artifact still truthfully records Heshun20selected/19checked.
Do not spend a successor merely because the visual gap has been filled.

## Continuation boundary

This change does not create a successor, work key, launch or Research result;
it does not recapture sources or rerun anything. Local clone/archive access did
not yield an executable current-main checkout. Local byte/render checks are
not full repository CI. Exact-head PR CI, review, main CI and normal publication
remain separate acceptance steps.

Next: finish and test the bounded lossless input bridge on these real bytes,
including source/decoded identity and actual final Pre/conditional Quick request
size. Only then bind legal successor work to old parent failures, consumed
source-recovery-v1, run34765190284, the newly current fixed reading and existing
Human permission5652950925. Preserve the old failures. Reuse 光电600184.SH and
东软300183.SZ without rerun. No Deep/Odds/Action/trading/position/monitoring authority.
