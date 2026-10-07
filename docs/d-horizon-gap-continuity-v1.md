# D horizon follow-up: preserve one exact predecessor across interrupted readings

Owner: #509. Successor to [the existing horizon reader](d-horizon-follow-up-v1.md).
This is an engineering continuity fix, not a new opportunity, method, source,
calendar, probability, trading permission or natural-session acceptance.

## Demonstrated gap and reuse

The original reader could preserve a comparable checkpoint while another endpoint
was missing, but an entire failed horizon attachment wrote only a status and a
commit. The next `_previous` ignored that gap because it had no `read_path`.
Consequently repeated failures lost the report descriptor; a later valid input
could no longer restore the saved calendar prefix or first-recorded clock.
The new regression reproduces that behavior on the unchanged predecessor.

REUSE / THIN_ADAPTER: use the one-explicit-locator protocol already implemented in
`d_price_structure_reading._previous_reference` and its exact-byte verification.
The existing native Git reader, shared reserve, horizon calculation and root
assembler continue to own their responsibilities. The original horizon reader's
external Alphalens/DVC/GitHub review still applies; this fix selects no new client,
framework, state backend or dependency. It does not rescan repository history.

## Current behavior

Resolve a previous descriptor before reading today's declaration or price input.
A failed attachment can retain `previous_saved_reading` with one exact commit,
file descriptor and `PREVIOUS_READING_NOT_CURRENT_SUCCESS` meaning. Repeated
failures carry the same original locator, not a chain of failed root packages.
Legacy gaps that already lost the descriptor remain unknown; no reconstruction
from unrelated history or a guessed latest successful run is attempted.

The locator checks the exact report path, immutable Git identities, byte bound,
digest and read-ref rule before I/O. Self-references in failed packages are
rejected. Retrieval performs one existing Git GET, then verifies the exact bytes,
report hash/version and report clock against its containing prior reading. The
same one-read allowance is reserved before the operation, not added to the budget.
No alternate ref, source retry, source query or market/model request is made.

A valid locator with currently unavailable bytes may remain as a locator only.
It is not called a verified current report and cannot supply a result. On a later
successful read, current prices/calendar still independently pass the original
admission and replay; only then can the verified predecessor preserve the original
S0, checkpoints and first-recorded clock. Retained endpoint provenance points to
the actual old report, not to an intervening failed R where that report is absent.

The normal README explicitly marks an interrupted or unavailable predecessor.
An unchanged result after recovery does not establish uninterrupted visibility,
missing-session prices, an economic outcome or new Human acceptance. Declaration,
source and capacity failures keep their actual failure state and isolate the
addition; unrelated reading files, original Research and Human records stay intact.

## Verification and exit

`tests/test_d_horizon_gap_continuity.py` covers invalid locators, self-reference,
exactly one read/no fallback, byte and clock rejection, legacy missing locators,
two failures followed by restoration, failure before declaration, and unavailable
old bytes. Its full-attachment tests reuse the original synthetic Git/registry/
quota seam and native root assembler. Synthetic dates are not observed sessions.

Local import-slice checks do not replace formal full CI, exact-head review,
independent main scope, normal publication and fixed-R consumer readback. Actual
results belong in the original PR/#509 receipts, not an evergreen PASS claim here.
Remove the added resolver/carry fields and dedicated tests to retire this fix;
retained Git reports and failure history remain. No existing case declaration,
freeze, long-horizon deadline, counterevidence, schedule or notification changes.
