# Official economic directories — first bounded discovery proof — 2026-09-05

Status: TWO ORIGINAL DIRECTORY WINDOWS CAPTURED AND RECONSTRUCTED / ZERO ELIGIBLE DETAIL REQUESTS / NO NEW RELEASE ACCEPTED / NOT COMPLETE PUBLISHER COVERAGE.

## Exact implementation and run

PR #204 added the isolated directory-discovery command and synthetic tests; PR #205 added its independent compatibility workflow. No existing source fixture, market state, candidate ledger, economic observation schema, gate or authority changed.

```text
PR #204 base = 0a155c8eb52ad91781ffd8fbe53b36dd0d34cadc
PR #204 head = b210d79eb321cb9028f490ed742669960aa539d8
PR #204 merge = 007b6dd36a2a3beeabe5850b5bc7b569e4adbe1b
PR #204 CI = 33951993802 / success / 565 passed in 8.92s
PR #204 main CI = 33952078229 / success

PR #205 base = 007b6dd36a2a3beeabe5850b5bc7b569e4adbe1b
PR #205 head = 4cb6077d176493e93a5f12b8db637ce81b40935c
PR #205 merge = 26769c4bdf5254b9eace867395157dcb28c9848e
PR #205 CI = 33952178639 / success / 569 passed in 9.84s
PR #205 main kernel CI = 33952315586 / success

live workflow = .github/workflows/economic-release-discovery.yml
run = 33952315592 / workflow #1 / attempt 1
event = push / branch = main
implementation = 26769c4bdf5254b9eace867395157dcb28c9848e
workflow conclusion = success
scan result = COMPLETE_BOUNDED_SCAN
actual directory GETs = 2
actual detail GETs = 0
pending new source packets = 0
new economic observations / market events = 0 / 0
```

This was one controlled post-merge scan, not a rerun-until-favourable experiment. The existing four-page source-capture workflow and Sector Radar were not invoked. All test fixtures are explicitly synthetic and do not count as live releases.

## What the original directory bodies establish

| Directory | HTTP | Body bytes | Visible dated articles | Target-family articles | Visible publication window |
| --- | --- | --- | --- | --- | --- |
| MOA livestock monitoring first page | 200 | 55553 | 20 | 10 livestock/feed weekly releases | 2026-07-01 to 2026-09-04 |
| SPB industry-news first page | 200 | 30726 | 10 | 0 monthly operating releases | 2026-09-03 to 2026-09-04 |

MOA request began at `2026-09-05T07:21:28.463782+00:00` and completed at `2026-09-05T07:21:30.287543+00:00`. SPB began at `2026-09-05T07:21:30.288060+00:00` and completed at `2026-09-05T07:21:31.840706+00:00`.

The ten MOA target articles split into:

```text
KNOWN_URL_NOT_REVALIDATED = 2
OLDER_UNREVIEWED_BACKLOG_NOT_FETCHED = 8
UNREVIEWED_RELEASE_AT_OR_AFTER_BASELINE = 0
KNOWN_METADATA_CHANGED_REVIEW_REQUIRED = 0
```

The two known feed releases are the reviewed August week 3 and week 4 records, published August 25 and September 1 respectively. The latest dated MOA page item is a slaughter-price release outside this initial livestock/feed target family. The eight older feed entries remain visible as backlog; they were not fetched, accepted or relabelled as newly published events.

The SPB news window contains no matching monthly operating release. This is **not** evidence that SPB has no newer monthly release. Its visible window does not even reach the reviewed August 14 publication boundary. A qualified statistics directory or bounded pagination with missed-window handling remains necessary before continuous monthly-release coverage can be claimed.

## Artifact identity

```text
artifact = economic-release-discovery-33952315592-1
artifact id = 9965217757
ZIP bytes = 25654
ZIP SHA-256 = 238cdebd4b208f3576d7d95642b249a624ee1d4ad748744d1a2563ca11a7bc1b
archive hash = 0ca0623b6375ef677478e354750dd38b8b35f8314a33d275b3bb3dcade3c060c
workflow provenance hash = 7d5f1d64c46ed8aca1589e69d1d530be64ce0aab675b60f666af86f64d4e0cee
expires_at = 2026-12-04T07:21:16Z
```

The sealed scan contains nine inventoried files plus its manifest: exact reviewed baseline; two request records, response metadata and raw bodies; full result and summary. Workflow provenance and verification output remain outside that inventory. No article detail file exists because the exact acquisition plan is empty.

Original body hashes:

```text
MOA = bd750d6c4226f84118a226c796585ec131920af4cada37a6fa30ba21d8a1e904
SPB = b4ed98612b7218111ded50105a4f2b4f324cb22f44a41a74bb4c50758bb530a1
result.json = f7c506f656021d2c76e11df867a1355de9323cc113d73741647c56d90ab1d190
```

## Verification and what was not verified

The workflow executed the project verifier offline, reconstructed the directory rows and empty detail plan from the original inputs, compared result and summary bytes and reported:

```text
archive_integrity = VERIFIED
status = COMPLETE_BOUNDED_SCAN
review_packet_count = 0
network_calls = 0
production_state_writes = 0
```

After download, independent local checks reconciled the ZIP digest, exact file inventory and all file hashes, archive/provenance hashes, source SHA against the local implementation, HTTP metadata, request clocks, and unchanged baseline records against the previous four-page capture. A separate BeautifulSoup HTML traversal checked each recorded link/title/date against its own list row, all 30 anchor line/column positions and target-title counts. The ten plan dispositions were independently checked against the original reviewed baseline.

This independent check was hash/HTML/clock/plan reconciliation, not a second execution of the entire project verifier. HTTP evidence and content hashes are not independent publisher authentication. Raw HTML is archived data and should not be executed.

No newly eligible article body was acquired by this live run. The natural new-release detail capture and `PENDING_HUMAN_SOURCE_REVIEW` path remain synthetically tested only. The already-reviewed article captures from prior runs do not substitute for that proof. No baseline was weakened or artificially backdated to force a candidate.

Known URLs are not body-refetched in this discovery policy, so a body-only revision is not ruled out. There is no persistent seen/review queue: separate scans keep separate evidence, not an automatic approval state. Publication dates remain date-only; actual system knowledge begins at acquisition, not a guessed original publication instant.

## Next useful work and unchanged market state

Do not repeat the same scan merely for another green result. Qualify SPB statistics-directory or pagination coverage before claiming monthly monitoring; then validate a naturally eligible release and explicit source review without auto-accepting metrics. Coverage gaps and old backlog must remain visible.

The latest real Sector Radar proof remains run #4 / `33939414197`, implementation `5f8f635d191dd8559844d1b74af0dca0cf4c02df`, state ending 2026-09-04 with an empty prospective event ledger. New-session append, input-audit replay and context publication still need the next real Sector run. The public discovery workflow has no access to its state or credentials.

No Sector or economic clock schedule was added. No real stock dump, multi-day breadth, company exposure mapping, objective outcome or long-term checkpoint was established. Artifacts retain the declared 90-day lifecycle.

SHADOW OBSERVATION ONLY. FUNDAMENTAL STATE AUTHORITY = NONE. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
