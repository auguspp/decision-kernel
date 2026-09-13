# Stock full-input representation / pre-send adapter — 2026-09-14

Continues #297 Human permission5652950925 and pre-construction Reuse Check
5656635695, after #356's actual page23 reading and artifact audit. This is a
THIN_ADAPTER under the original source/Research boundary, not a new executor.

## Implemented in this change

`stock_full_input.py` has no network, source capture, persistence, model loop,
permission, work key, launch or workflow. It composes standard-library zlib and
base64 with the original `external_research_identity._checked_source` gate and
an SDK-compatible request hook. Neither helper authorizes execution.

The stored envelope remains at most512KiB. Its original JSON bytes, size and
SHA256 are bound and restored, including all source bodies, metadata, repeated
text and source clocks. Decoding is bounded before allocation; damaged,
truncated, concatenated or trailing streams and duplicate/nonfinite JSON are
rejected. Decoded issuer/document/page inventories must agree. These are
identity/shape checks, not independent source/readability/truth certification.
The original source preparation and trusted-page checks are still mandatory.

The pre-send hook compares the actual SDK-built HTTP method, destination and
entire JSON body with the exact trusted host parameters: complete PLAIN
public_context, instructions, strict output format, model, stream, no tools,
no storage and output bound. It measures the actual request bytes/hash, refuses
a second send and records no credentials. A successful pre-send check is NOT
proof of transport delivery, provider token-window acceptance or Research.

This isolated adapter has finite decoded1.5MiB/request2MiB bounds and is limited
to603353/300711. These are NOT activated production limits. Original capture448KiB,
Retainer512KiB, checked-source512KiB and model_call's Stock512KiB/default128KiB
limits are UNCHANGED. The integration test explicitly verifies that the original
model_call still rejects a2MiB opt-in. No production host/workflow imports or
calls this adapter in this change.

## Real saved-input check, not a synthetic source or final model request

The mounted original artifact10320565453 ZIP was re-hashed to
`25cda8a1d4afb4783432320239cd6271fe193cfdc5ed6dc2095a5deb833dce9c` and CRC checked.
The existing Guangha prepared context was read directly from its ZIP member:

- original:636,462 bytes, SHA256
  `4cb6c5a18a18ef6ed8b011f315c7bac000a3ecaaf4b21b6cd72b476a3344cbf0`;
- this module's stored envelope:221,497 bytes, SHA256
  `2bfaa5b10cc701c449a4510248058183547b1d7363f3dec674e08d1672fb1571`;
- unpacked bytes equal the original byte-for-byte; all13 documents/286 pages,
  counterevidence and original timestamps remain unchanged.

This real-input local result does NOT establish GitHub production storage
readback, source admission, actual SDK final Pre/Quick bytes or delivery. The
original context/artifact/failures were not rewritten. Heshun's original372-page
text lower bound and remaining production full-context check are not promoted
by a synthetic two-issuer byte test.

## Tests and environment boundary

35 pure new-module tests passed locally with pytest9.0.2. No current-main
executable checkout or pinned SDK was available locally; this is not a full
repository pytest run. No old repository was manually reconstructed.

The separate integration tests use the ORIGINAL checked-source/serialization,
original admitted-ID output models, and the pinned original SDK strict format.
For PRE and QUICK byte fixtures the SDK constructs the real HTTP request, but
a fake transport stops before any network/model call. The request hook must
run before that fake transport. Socket calls fail the test; no SDK-absence skip,
new model provider or altered original tests. These are synthetic transport
fixtures, not actual Research stages, valid company candidates or route acceptance.
Complete original exact-head PR CI and review remain required.

## Still not complete / not activated

The production host must still compose capture, stored MODEL_CONTEXT identity,
decoded/plain prompt identity, the original SDK call and its final request
hook before this is a usable full-input path. It must check actual complete Pre
request size before launching and actual Quick bytes only when original Funnel
routing requires Quick. Never fabricate a future Quick result or use a dummy
request measurement as proof that the real packet fits. Model token-window /
provider acceptance is a separate property, not inferred from byte limits.

A legal successor must separately bind original failures, consumed source-recovery-v1,
source-only run34765190284, the then-current fixed reading and original permission.
No successor, launch, model invocation, source recapture or Research-work write
is made here. No Re-run34765190284, recover-sources=true, rerun of600184/300183,
automatic Deep/Odds/Action/trading/positions/monitoring authority.
