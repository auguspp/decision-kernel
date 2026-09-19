# CNINFO PDF failures: finite diagnostics through the existing Stock path

Radar-r3 / #297 pre-implementation receipt5738933263, 2026-09-19.
Reuse Decision: REUSE existing Requests session, response guard, exception types,
source journal and Stock host retention. No new provider, retry system or workflow.

## The observed gap, not an inferred remote cause

Saved Stock business run35335061635 (code542cd178f12e904d26f89d7b85f3806825485cda)
stopped before formal Research for000920.SZ and603268.SH. Their first PDF bodies,
announcements1225486756 and1225497616, remained INCOMPLETE with zero retained PDF
bytes. The saved finite exception name was CninfoPdfHttpError; neither the saved
journal nor host failure identified the HTTP status. The earlier status remains
UNKNOWN. A later code fix, successful fetch or new failure cannot reconstruct it.

The existing shared _check_response already rejects non200 statuses, unexpected
content encoding and invalid Content-Length with finite codes. cninfo_http was
wrapping those exceptions without preserving the existing code/status. This change
retains that diagnostic distinction without changing whether a body is accepted.

## Scope and safety

CninfoPdfHttpError and CninfoPdfTransportError keep their one-message construction
compatible. The bounded PDF request attaches the observed status and a finite
reason. pdf_failure_diagnostic, in the same module, emits only reason_code and
http_status for exact known PDF exception types. It does not inspect arbitrary
causes, response/request objects, headers, URLs or free-text exception messages.
Unknown exception types receive no invented PDF diagnosis. Invalid metadata is
quarantined; bool/string/out-of-range statuses are not admitted. Legacy failures
without an observed status retain null, never zero or an invented403/429.

HTTP_REJECTED preserves a valid non200 status without following redirects or
reading the rejected body. Transport failures distinguish response encoding,
Content-Length format, received-length mismatch, Requests Timeout, ConnectionError
and other RequestException. A200 in a transport diagnosis means the response
headers were received, not that its PDF body was accepted. Requests' actual
exception category is retained; it is not proof of the deeper network cause.
Source destination, byte-limit and container errors have finite categories and
unknown HTTP status where the existing exception carries no status.

The existing stock_research_sources.capture body event gains finished_at when
fetch_pdf raises. Only a finite PDF diagnostic is attached. Source-preparation-only
output also retains that diagnostic, without becoming Research admission. The
original stock_research_host copies it only while formal Research has not started
and its phase is SOURCE_PREPARATION, then uses the same failure/host-receipt saves.
Other legacy standalone capture hosts are not claimed to be integrated by this
slice. Previously saved journals, roots, launches and failures are not rewritten.

Source host, headers, timeout, source/byte limits, no-redirect/no-retry behavior,
identity/period checks, successful bytes and success journal contracts stay as
before. This does not acquire any new PDF, refresh Eastsoft trigger evidence,
complete Fibocom financial research, run Pre/Quick, or authorize a new invocation.
No WAIT/DROP, Human acceptance, monitoring, Odds or investment decision is created.

## Verification

New synthetic tests execute the original response guard and streaming transport,
then the original Stock source capture and host failure retention. They distinguish
403/404/429/redirect/server statuses, malformed status/header/length, pre-header and
body-stream exceptions, legacy errors and untrusted metadata. External networking
is explicitly forbidden. Original source identity and failure clocks are checked;
repeating the same research root must not fetch again or call a model. Existing
positive transport/source/host tests remain unchanged.

Local focused tests use the verified native8abe source archive plus current touched
modules; this is not a complete current-main checkout or the runner environment.
The ordinary exact-head full PR CI, independent main CI, normal publisher and
pinned-reading readback remain separate required gates. No test is skipped or
removed and no source budget is increased to obtain success.

Primary reuse references checked2026-09-19: Requests official API
https://requests.readthedocs.io/en/latest/api/ and upstream exception definitions
https://github.com/psf/requests/blob/main/src/requests/exceptions.py . No dependency
or version change is required. Actual publication/CI results belong in a later
receipt, not prefilled in this implementation note.
