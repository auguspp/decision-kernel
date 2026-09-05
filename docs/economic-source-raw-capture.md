# Official economic-source raw capture

Status: BOUNDED CAPTURE IMPLEMENTATION / NOT CONTINUOUS ECONOMIC COVERAGE / NO MARKET EVENT OR INVESTMENT AUTHORITY.

## Purpose and scope

PR #196 retained four manually reviewed official excerpts, not original HTML. This slice adds a credential-free archival transport and reproducible binding of those reviewed statements to the captured page. The existing economic-study calculation and all market producer/gate/state contracts are unchanged.

This is deliberately not a general crawler or an automatic release interpreter. The operator supplies 1–4 exact, already-reviewed source records. Each must pass the existing MOA/SPB URL, title, date, period, unit and excerpt parser before any network call. The committed four-record study list is the initial bounded probe. New releases still need review before being added to this input; no claim of latest-release discovery is made.

## Commands

```bash
python -m decision_kernel.runtime.economic_source_capture capture \
  radar_inputs/economic-node-study-2026-09-05.json \
  --output /path/to/new-capture-directory

python -m decision_kernel.runtime.economic_source_capture verify \
  /path/to/new-capture-directory
```

Capture performs one HTTPS GET per selected page, with a 20-second timeout and a 2 MiB response-body limit. Total retained files are limited to 20 MiB. Only exact MOA livestock and SPB national monthly-release paths are allowed. No redirects, proxy credentials, cookies, JavaScript, secondary page resources, provider key, retry or fallback are used. Challenges, unsupported encodings, content types, changed phrases and malformed pages remain explicit failures.

The output directory must be new, cannot have symlink ancestors and cannot be under `decision-state`. There is no market-state, Radar event, Research route or Human-wake writer.

## Inventory

```text
manifest.json
summary.md
0000/ ... 0003/
  source.json       # original reviewed input and its original capture clock
  response.bin      # exact bounded response-body bytes, when received
  response.json     # exact URL, HTTP status and allowlisted noncredential headers
  page.txt          # text projection, only if binding succeeded
  binding.json      # phrase locations, response/text/source hashes and new clock
  observation.json  # same study semantics, now bound to this actual capture time
```

Raw HTML is intentionally stored as `.bin`; do not execute or open it as trusted application code. HTTP framing/TLS bytes are not recorded. Response-body bytes are not reconstructed from a browser's text view or manually authored fixtures. Headers such as Set-Cookie and Authorization are not retained.

The manifest covers byte sizes/hashes, ordered request identities and clocks, statuses, fixed file inventory and the relevant implementation-file hashes. An interrupted run remains `RECORDING` and cannot pass complete verification. Each later capture uses a separate directory; no earlier body, record or observation is overwritten. The initial committed excerpts remain unchanged.

## What binding proves

The existing excerpt parser first validates the reviewed record. Then a deterministic HTML text projection excludes script/style/noscript/template content, normalizes whitespace and finds each reviewed fact in the captured text. The declared title and publication-date text must precede the selected fact statements. The binding retains exact normalized offsets.

This is substring reconciliation of the specifically reviewed excerpt, not a browser visibility claim, exhaustive semantic reading or authentication of the publisher. It does not prove that unselected surrounding claims are unchanged. The complete captured body is available for that review; future overlapping captures can expose a changed body hash even when selected phrases still match.

A changed value is not silently accepted as a revision. Its raw response is retained, binding is rejected, and a new explicitly reviewed record is needed. A new observation uses the actual new capture clock, never the old record's timestamp or the reporting period as system knowledge time. Source publication remains DATE_ONLY. Historical first-vintage proof, next-release due date and continuous coverage remain unestablished.

## Failure and replay

A source transport failure retains its class and an operations reason, not arbitrary exception payloads. Other selected independent pages can still be attempted once. Any rejected or unavailable source makes the aggregate `INCOMPLETE`, and the capture command exits nonzero. Complete success cannot be inferred from one working node.

Offline verification checks file inventory and hashes, provenance and implementation compatibility. Successful bindings are recomputed from source records and original response bodies; changed observations cannot be legitimized merely by changing their file hashes. Network failures have integrity evidence only; verification does not recreate remote outages or fetch missing responses. It makes zero network calls and writes no production state. An incomplete archive does not turn into a complete acquisition because its retained bytes pass integrity checks.

Injecting a test transport requires explicit `SYNTHETIC_TEST_ONLY` provenance, carried into the rebound observations. Unit-test HTML is generated from the reviewed excerpts and is not described as captured official HTML. Full-suite tests are offline. A separate real compatibility probe is required to establish actual server reachability, markup, encoding and response-body capture.

## Operational delivery

A separate maintained public-source compatibility workflow may invoke these commands on relevant main-branch implementation changes and by manual dispatch. It must use no secrets, no market cache, no Research/Inbox integration and no schedule. Its artifact and status are separate from `sector-radar-shadow` and `kernel-tests`. A main push may trigger four bounded public GETs, but does not activate continuous industry monitoring.

At this implementation stage there is no successful raw capture proof yet. The local development runtime failed DNS resolution and its file-download tool could not retrieve the public page bytes. A web tool can read some page text, but that is not a substitute for original response-body archival. Do not fabricate originals from the existing snippets.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
