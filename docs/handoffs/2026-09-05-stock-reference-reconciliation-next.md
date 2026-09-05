# Handoff and proof — stock rows decoded, differences retained

Evidence date: 2026-09-05. Repository: `auguspp/decision-kernel`.
Status: COMPLETE PAGINATED COMPARISON REFERENCES / REAL PARQUET ROW INSPECTION EXECUTED / DIFFERENCES_REQUIRE_REVIEW / NO PRODUCTION STOCK PANEL.

## Read first

Read `docs/project-state.md`, `docs/hithink-stock-snapshot-reference-window.md` and this record, then verify current main and actual CI/workflow artifacts. The prior handoff `docs/handoffs/2026-09-05-stock-dump-trial-next.md` remains the record of four earlier failed probes, including the first downloaded file. Their results are not rewritten by this later inspection.

Reuse-first remains required. This slice reuses Requests, Apache PyArrow, the existing calendar/benchmark adapter, stock pager and exact row inspector. No new dependencies, workflow definitions, parsers, retry framework or calendar feed were added.

## Exact implementation lineage

```text
PR = #215
base = 24c5eb4a27191e68750caaa1c8d165b1fa24cae6
head = 188863e78a0c1a55eb011b59d3639842e520269b
merge / executed implementation = 74509398a1a9afa226e83ef878c418fbe114586b
PR kernel CI = 33959105550 / success / 680 passed in 8.72s
main kernel CI = 33959190993 / completed / success
new test cases = 41; prior 639 cases retained
```

Exact files, 440 additions / 15 deletions:

```text
src/decision_kernel/runtime/hithink_sector_breadth_http.py
src/decision_kernel/runtime/hithink_dump_trial.py
tests/test_hithink_stock_reference_window.py
tests/test_hithink_dump_trial.py
docs/hithink-stock-snapshot-reference-window.md
```

The code adds an explicit isolated-study reference context, not a silent migration of production stock freshness. The existing Sector producer still calls the original date-equality default. Only the dump trial opts into the closed capture window: same completed session at/after 15:30, or Friday's directly following Saturday/Sunday. A later missing weekday is not inferred to be a holiday. Every original page clock is bounded by the completed capture boundary and actual receipt; backwards, future and date-crossing clocks fail. The page clock never proves each stock's last-trade session.

Source semantics and review rationale are in `docs/hithink-stock-snapshot-reference-window.md`. Original market values, exact comparisons, null handling and all pagination/identity checks remain intact. Production qualification remains NOT_ESTABLISHED even if all checked fields agree.

## One actual changed-code trial

```text
workflow = hithink-stock-dump-trial #5
run = 33959190974
attempt = 1
event = push, narrowly filtered existing workflow
branch = main
executed SHA = 74509398a1a9afa226e83ef878c418fbe114586b
started_at = 2026-09-05T09:53:52.353872+00:00
download_started_at = 2026-09-05T09:53:53.690364+00:00
download_completed_at = 2026-09-05T09:53:59.059412+00:00
completed_at = 2026-09-05T09:54:16.991013+00:00
reference observation = 2026-09-05T09:54:01.299341+00:00
comparison session = 2026-09-04
status = DIFFERENCES_REQUIRE_REVIEW
stage = INSPECTED_NOT_ADOPTED
workflow conclusion = failure
production_qualification = NOT_ESTABLISHED
```

Exactly one signing request, one object GET and 15 reference JSON requests occurred: calendar, CSI300 snapshot/history and 12 stock pages. Stock page offsets were 0 through 5500 in steps of 500; eleven pages had 500 rows and the last had 67. Declared total stayed 5,567, all 5,567 identities were unique, and all original page timestamps/quoted numeric values were preserved. Page ready times ranged from 2026-09-05 17:54:01 through 17:54:15 Shanghai, within recorded response-receipt bounds. The calendar and qualified benchmark hashes bind the reference window.

The original Parquet is byte-identical to the file downloaded in run #4. Both captures observed the same bytes on the same calendar day. This is **not** two independently published market vintages, proof of no revisions, or a history of prospective availability.

## Actual row-level result

PyArrow iterated all 55,467 rows; the existing strict inspector completed its structural and date-window checks. The rows contained 5,556 unique stock identities across ten completed sessions. There were no missing whole sessions, no off-current-provider-universe dump identities, and no zero-volume rows. This is stronger than #4's footer-only inspection, but not independent exchange-wide completeness.

| Checked item | Actual count/result |
| --- | --- |
| Provider snapshot identities | 5,567, 12 complete pages |
| Fully priced latest references with matching latest dump bars | 5,548 |
| Latest close exact matches | 5,548 / 5,548 |
| Turnover exact matches | 894 / 5,548 |
| Turnover differences | 4,654 |
| Previous raw close exact matches | 5,532 / 5,548 |
| Previous raw close differences | 15 |
| Missing previous bar | 1, identity `920289.BJ` |
| Unpriced reference identities | 19 |
| Current reference identities missing latest dump bar | the same 19 identities, not an additional disjoint set |
| All field/previous-bar diagnostic entries | 4,670 |

These diagnostic counts are not disjoint stock counts: one stock can have both a turnover and previous-close difference. Nineteen missing/unpriced cases were preserved, not filled or removed from the provider reference universe. No cause such as suspension, not-yet-listed status or delisting was inferred without evidence.

Example retained turnover difference: `000001.SZ`, dump `969948436.21` versus snapshot `969948440`. A precision/representation difference is a hypothesis, not an established contract; no rounding rule or numerical tolerance was introduced. Fifteen raw-previous-close differences require corporate-action/price-convention evidence; e.g. `000408.SZ` was `76.86` versus `75.86`. That numerical pattern alone is not proof of a dividend. The missing prior bar for `920289.BJ` is not automatically classified as an IPO.

Per-session row counts: August 24: 5545; 25: 5546; 26: 5547; 27: 5547; 28: 5547; 31: 5545; September 1: 5546; 2: 5547; 3: 5549; 4: 5548. They sum to 55,467. Full identity-level diagnostics remain in the original report.

## Offline reproduction and independent review

The workflow executed the existing offline inspector a second time from the frozen Parquet, sessions, universe and snapshot. It wrote `offline-inspection.json` and correctly returned exit 2 for the same differences. Because the shell uses fail-fast execution, the subsequent in-step equality assertion did not run. After downloading the artifact, an independent comparison verified that both `inspection` objects are exactly equal, including hashes and all diagnostics. Do not claim that skipped workflow assertion executed.

Independent local review verified the ZIP digest, exact 25-file inventory, all 21 inventoried input sizes/hashes, report/inspection/offline/provenance hashes, normalized reference prices against all raw pages, all page counts/totals/offsets/times, calendar/benchmark evidence hashes, the difference categorization above, and equality with the earlier Parquet bytes. The local environment still had no PyArrow; this review did not physically decode the file locally or run the full repository suite. The two actual Parquet scans and full tests ran in GitHub Actions. Same-provider agreement is not an independent market source.

```text
artifact = hithink-stock-dump-trial-33959190974-1
artifact id = 9967375391
ZIP bytes = 1587630
ZIP SHA256 = ee7f5c1bdc955b0d4c86c898a2d035e632a93ba6429ab2bdcb2d75fb4273b812
expires_at = 2026-12-04T09:53:35Z
Parquet bytes = 1077266
Parquet SHA256 = f333ddc55a614cc14872639e4831a60bcdf20590953bf9a1545764adc4ce2d6a
report hash = 926b088c431599f121e596278fbdb86514f4c553d77041d1c913d846d7219d4a
inspection hash = 823beb55ca45044a16e7e52172901a5bb60fd358c27030a85a6fb866326e523c
offline report hash = 668073931733d725abecb39a579495ebaad18a21b91f9b558be6a32fb366d5ce
workflow provenance hash = d72a7d14abc0543c6800aa1605715bbe52b5b996d2b969ccfd1d4e1020c6a917
```

Original artifact includes 15 raw reference JSON files, Parquet, normalized calendar tail, benchmark, reference-window evidence, universe and snapshot (21 inputs), plus report, summary, offline inspection and workflow provenance. No signing response, usable download URL or secret was retained. Retention is 90 days, not permanent.

## Next work: reconcile the observed differences, not more blind retries

1. Work from these frozen inputs. Establish documented turnover units and precision on both endpoints before any quantization proposal. Classify diagnostics by field rather than making the entire file silently pass with an arbitrary epsilon. Do not assume that an approximate turnover check establishes exact prices or per-security freshness.
2. Review the existing official adjustment-factor/corporate-action tooling before writing custom calculations. Obtain explicit event/effective-date evidence for the 15 raw-previous-close discrepancies; preserve source and actual availability clocks. Do not silently turn raw history into adjusted prices.
3. Establish the 19 missing/unpriced cases and missing prior-bar case from qualified listing/trading-status evidence. Preserve denominators and explicit gaps; do not erase inconvenient identities.
4. Only a naturally later overlapping vintage can test revisions over time. The same-day identical file does not satisfy this gate. Twenty/sixty-session history, corporate-action PIT and current-basket/history semantics remain unestablished before multi-day breadth adoption.

No further live probe was needed merely to make this comparison green. No workflow/dependency, market-state/cache/ledger, signal threshold, company posture, Research route or Human/Research/Investment authority changed. The isolated study did not create a prospective signal.

The actual Sector operational proof remains run #4 / `33939414197` at implementation `5f8f635d191dd8559844d1b74af0dca0cf4c02df`, ending 2026-09-04 with zero prospective events. Its next direct completed-session append, real sealed input-audit replay and context publication remain pending. Do not enable schedule before that proof or use stock files to bridge an industry-index gap.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
