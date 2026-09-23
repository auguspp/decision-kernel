# Complete Industry question input through the original host

Scope: #297/5786165647, continuing Human approval5778160521 and P1-4.
Reuse Decision: REUSE + THIN_ADAPTER. Original main a1a42eb44cf462bb7890d078817699582fa9eae8.

The existing full-input codec, SDK request hook, native artifact reader, PDF
parser, same-PDF reading and question host already own the required mechanisms.
This change connects them without borrowing old Stock identities or permissions.
The existing 603353/300711 wrappers retain their original policy and ticker
checks. Shared private pack/unpack helpers use the same bounded zlib/base64
implementation; no new dependency, storage service or provider framework.

A reviewed Industry request may opt into REVIEWED_INDUSTRY_FULL_INPUT_ZLIB_V1.
The stored MODEL_CONTEXT remains at most512KiB; its exact decoded canonical JSON
is bounded at1.5MiB. All issuer documents, consecutive pages, source clocks,
visual notes and limitations survive losslessly. The provider receives complete
PLAIN text, never compressed/base64 source text. The actual SDK request is
bounded at2MiB. These byte limits do not certify token-window/provider acceptance.
Unknown, malformed, truncated, concatenated, over-limit or changed envelopes fail.

The original question host constructs its original Pre, source admission and
shared day/question reservations. A full bound context is checked at every
re-entry and passed through the ORIGINAL research function; the original raw
context hash check remains for the default small path. The final SDK hook binds
DeepSeek destination/model/reasoning/format, exact complete input and one send.
An actual SDK preview is built before reservation with a transport that cannot
send. Quick still requires the original validated Pre transition and is checked
only if executed. No automatic Deep, retries or investment authority is added.

The original source-import registry gains one explicit declared-report profile
for run35754054446/artifact10706728112. Native run/event/main/attempt, ZIP digest,
all12 original members, original capture plan and Git source manifest are checked.
The event remains issues, not a fabricated workflow_dispatch. Original PDF and
extraction bytes bind to exact Git files; no fake legacy inventory or journal is
created. The old Zhenjiang capture adapter reuses the same extracted native
artifact-check helper and retains its own format contract.

For the declared CNINFO reports, original PYPDF pages are re-extracted and checked.
The bound same-PDF alternative is rebuilt from the exact PDF and frozen notes.
Current trusted main must contain byte-identical visual notes, while their
original source commit and review clock remain unchanged. A new implementation
commit must not cause the original review to be silently retimed. Other capture
formats or mirror semantics require their own reviewed mapping; they are not
accepted by changing a provenance string.

Publication dates keep DAY_NOT_AVAILABILITY_TIMESTAMP. Their normalized midnight
field is not proof of first availability. Retrieval, Git custody, page review and
research cutoff are distinct. Failed or absent latest-update inventory remains a
failure under the original LATEST_INVENTORY admission; no STATIC downgrade occurs.
The ten-day/day-question consumption ledger is unchanged, not reset for Industry.
DeepSeek costs are managed by the Human account, not a new project monetary gate.

Tests reuse original Industry/Stock host fixtures, real PDF parsing/representation,
original admission/conditional Funnel/Retainer and real SDK-built request bytes.
Only Git/HTTP/model boundaries are synthetic. They do not prove live report
qualification, a current correction inventory, real model execution or delivery.
All5705 original test identities remain required in complete PR and independent
main CI; no skipped tests or path-filtered acceptance. Normal publisher/readback
and real company activation remain separate facts, not prefilled by this file.

Reuse evidence: original stock_full_input and stock_full_input_bridge, prior
external audit5656635695 and docs/readings/stock-full-input-adapter-2026-09-14.md;
Python zlib.decompress(max_length/eof/unused_data/unconsumed_tail), HTTPX request
hooks and the repository-pinned existing SDK/DeepSeek format contract. No new
codec implementation, model loop, scheduler or canonical database was selected.
