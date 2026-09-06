# Native NBS RSS qualification — 2026-09-06

Status: REAL SOURCE QUALIFICATION IN PROGRESS / NO SUCCESSFUL BASELINE OR NATURAL ARRIVAL YET.

The publisher's subscription page advertises `https://www.stats.gov.cn/sj/zxfb/rss.xml` and `https://www.stats.gov.cn/sj/sjjd/rss.xml`. It does not certify that the entire feeds fit our initial assumptions. Implementation uses maintained feedparser6.0.14, not a handwritten XML parser, RSSHub proxy or replacement source. `docs/native-rss-source-intake-v0.md` explains the source/version/seen-versus-delivered contracts.

## Preserved real attempts

| Code PR | Commit | Actual run / attempt | Downloaded artifact | ZIP bytes / SHA-256 |
| --- | --- | --- | --- | --- |
| #245 | f7c3019538a077719e64e68fc637054e735cb035 | 34008846022 / 1 | 9981816666 | 1681 / 83216a92014fe4a76d931dfd6e5c422cd4d08b9b0622aed4c8102c17995615c9 |
| #246 | 085910a72e3b18557eec6ed17630e6ccd18b0cbc | 34009113645 / 1 | 9981901578 | 1679 / bcaacdded98427f8ab862df17933a90d2b52473007fb59005c51a8dfb8a9c812 |
| #247 | 94a7b59256f7aea14fe59021257e711026035fd9 | 34009539824 / 1 | 9982025063 | 1899 / 21b01f73da28346255f8d932f95574f080834bbc90d63b54e44bbfd363b59993 |

Each attempted only the first source, nbs-interpretations, once. The first two recorded plain ValueError before returning a PublicResponse: HTTP status, headers and body were unavailable. They do not independently establish HTTP403, invalid XML or an outage. The initial diagnostics were insufficient, causing two additional implementation trials; do not present that as an upstream data fault or as successful capture. Raw feed bodies, registry and success page were absent in all three attempts.

The third attempt finally retained the exact pre-body refusal: HTTP200, Content-Type text/xml, Content-Length **4207576**, rejection `DECLARED_BODY_BYTE_BUDGET_EXCEEDED`. Source header date was Sun,06Sep2026 03:39:39GMT; Last-Modified was Mon,31Aug2026 01:30:09GMT. These are server claims, not a verified feed-publication or freshness clock. Request 03:39:37.065223Z, refusal receipt03:39:40.850478Z. Program origin is fetch_feed's declared-length guard. The body was NOT read, hashed or parsed; declared length is not a verified downloaded-byte count.

All three failed runs retained four-file artifacts and truthful failed status. Offline verification checked preserved receipt/files and returned `RETAINED_BYTES_ONLY_INCOMPLETE_INTAKE`; nonzero workflow result remains correct. Every downloaded ZIP digest, inventory, run/commit identity, receipt hash and request clock was independently checked locally. No local full-repository replay or browser check is claimed.

## Reviewed RSS-only capacity

The initial 2MiB bound was too small for the observed declared4,207,576-byte publisher window. The RSS source profile now explicitly permits **8MiB per response, at most two requests /16MiB of raw feed bodies**. This is a disclosed operational capacity change, not 'unchanged budgets' or a semantic pass. A small RSS-specific byte/Content-Length check keeps the existing economic-HTML helper and its2MiB default entirely unchanged. The RSS policy hash now includes the body bound. Prior receipts remain replayable under their original code; changing the policy does not migrate/reset a successful source chain. No live baseline existed to migrate.

Do not raise other limits based on speculation. The128-item, individual/aggregate text,4096-version,6MiB registry,32-source handoff and three-theme limits remain. The next run can retain complete bounded XML and still fail parsing/scope/semantic checks; raw acquisition success must not be conflated with a qualified feed window. No truncating items, dropping old entries, date normalization to fabricated midnight, accepting bozo XML, ignored GUID conflicts, fallback, retry or accepted-article claim.

Five additional tests verify a synthetic complete XML document padded to the observed size, original-byte retention/rebuild, unchanged HTML limit, empty/truncated/over8MiB rejection, and a distinct capacity-policy identity. Padding is not a claim about the unseen publisher XML. Complete project tests occur in Actions; local work checks syntax and file identity only.

A merge touching the existing RSS runtime deliberately permits one further bounded implementation qualification run. It is not a Re-run jobs attempt and does not repeat the old HTML directory or market acquisitions. Record the real result separately after inspecting raw output; do not claim a baseline from this document or synthetic tests. No schedule, new workflow, dependencies, company stance, market state/cache/event ledger, canonical wake, Research route or Human/Research/Investment authority changes.
