# Handoff and proof — reuse first, official statistics entry

Date: 2026-09-05. Repository: `auguspp/decision-kernel`.
Status: GENERIC PARSERS REPLACED BY BEAUTIFUL SOUP / OFFICIAL SPB STATISTICS WINDOW CAPTURED / NOT CONTINUOUS MONITORING.

## User direction and implementation rule

The Human explicitly requires mature wheels instead of bespoke infrastructure. Prefer exact official structured sources/feeds, maintained source adapters, and mature libraries with thin domain configuration. Do not grow the Radar into its own HTML parser, browser, crawler queue, scheduler or Parquet engine. Retain project-specific identity, source/time/version lineage, review disposition, budgets and authority contracts. See `docs/radar-reuse-decision-2026-09-05.md` for the primary-source review and explicit non-adoption reasons; mentioning RSSHub, AKShare or Scrapy does not mean they were deployed.

PR #207 deleted the two discovery HTMLParser subclasses and adopted optional `beautifulsoup4==4.14.3` with the explicit `html.parser` builder. The production module shrank by 30 lines. Base Kernel dependencies did not change; discovery/dev extras include the pin, and the existing workflow changes only its install line. The pin is tested, not claimed newest. The archive records exact Beautiful Soup/builder/Python runtime and code hashes. Prior archives require their recorded implementation, not silent migration. General markup repair is the library's behavior; row-local evidence ambiguity still fails. The separate legacy raw-capture text normalizer was not refactored in this slice.

An independent offline DOM comparison using 4.14.3 matched all 30 anchors/title/date/source-position records in the prior real directory artifact, without network or altering old bytes. This comparison was not full project replay or proof of the new statistics endpoint.

## Exact code PRs and CI

| PR | Base | Head | Merge | Full PR CI |
| --- | --- | --- | --- | --- |
| #207 | 07ae2b90b39a5eaca8236f33eb8915b248224cf8 | cbb1ce72209acc68bfdf1ab868093043440aa0bb | 194a733e1db87bab1f7700f55cabfe29de0332f8 | 33954381179 / success / 585 passed |
| #208 | 194a733e1db87bab1f7700f55cabfe29de0332f8 | 22b58e36e986ecef813266c41cf65ea45216be64 | aa7f9f4f03e529604c164e164c99e04471aa465d | 33954811760 / success / 587 passed |

Main kernel CI after #207: `33954522731` success. After #208: `33954898833` success. Full tests ran in CI; no full local repository test run is claimed.

Exact #207 files: `pyproject.toml`, `.github/workflows/economic-release-discovery.yml`, `src/decision_kernel/runtime/economic_release_discovery.py`, `tests/test_economic_discovery_reuse.py`, `docs/radar-reuse-decision-2026-09-05.md`.

Exact #208 files: `src/decision_kernel/runtime/economic_release_discovery.py`, `tests/test_economic_discovery_reuse.py`. Its production diff is ONE fixed directory URL; parser, transport and budgets did not change. Two added cases prove script-only same-origin/external navigation is never executed or followed.

## Retained failure: landing page is not a directory

Existing path-filtered workflow run `33954522717`, discovery #2 / attempt 1 / push main, used #207's merge. Both requests returned HTTP 200. MOA's unchanged 55,553-byte body parsed normally. The SPB landing page `/gjyzj/c100275/pubtz.shtml` returned only a 137-byte script with `window.location.href="/gjyzj/c100276/common_list.shtml"`. No dated list rows existed, so scan and workflow remained INCOMPLETE / failure. Offline verification reconstructed INCOMPLETE with archive_integrity VERIFIED; its nonzero exit was not an integrity mismatch. No script was executed.

```text
artifact id = 9965907259
ZIP SHA256 = a83f77ed233e479a758f41f00448573186b32d89eca0a59b15898069e93b4c27
archive hash = 59fd358190d29d715de34c66170f4729115e4ec6a7cd348dcf9c0f7e24e15776
SPB stub SHA256 = 3a20ab81a1837c1aeeeadef637083498d700bb828a10b89479f3cd3088395946
expires_at = 2026-12-04T08:10:09Z
```

The target was reviewed separately as the publisher's statistics list, including its dated monthly links and unchanged article URL family. #208 configured this exact URL directly: `https://www.spb.gov.cn/gjyzj/c100276/common_list.shtml`. No automatic JS/HTTP redirect support, browser, fallback or custom pagination was added. The failed run is retained, not overwritten or retried unchanged.

## New real statistics-window proof

After the one-line source correction, the existing workflow ran once:

```text
run = 33954898834 / economic-release-discovery #3 / attempt 1
implementation = aa7f9f4f03e529604c164e164c99e04471aa465d
event = push / branch = main
actual requests = 2 directories / 0 articles
both HTTP statuses = 200
scan = COMPLETE_BOUNDED_SCAN / workflow = success
new pending packets / economic observations / market events = 0 / 0 / 0
```

| Source | Bytes | Qualified dated rows | Target titles | Reviewed / older backlog | Visible dates |
| --- | --- | --- | --- | --- | --- |
| MOA feed monitoring | 55553 | 20 | 10 | 2 / 8 | 2026-07-01 through 2026-09-04 |
| SPB statistics list | 29953 | 9 | 6 | 2 / 4 | 2025-11-18 through 2026-08-14 |

MOA completed at `2026-09-05T08:18:37.810423+00:00`; SPB at `2026-09-05T08:18:39.476014+00:00`. The SPB page now includes both reviewed monthly report identities and reaches past the August 14 baseline boundary. Unlike the earlier news window, those monthly reports are visible. Counts apply to the existing allowed article/title families, not every link or all forms of monthly/annual publication. No full-history, future missed-window or body-revision coverage is claimed.

```text
artifact id = 9966022845
artifact name = economic-release-discovery-33954898834-1
ZIP bytes = 25007
ZIP SHA256 = 42d0b2a68f03583a5914538bfbf980f5f006c1df3809d1988e4e8f3693423d82
archive hash = 413be97ec18d31c3fb7c1de23ea1495f7a8d14f8e50323dc4fb0afafd1d68599
workflow provenance hash = b830dcf387ef212b7f324330de6ede8d54121f05e0109e971143c3929965ff6c
SPB body SHA256 = e5df0138e6a93b591befcaa50e0eedc70062845ac77a816f3dbd9e8f8f5022b0
MOA body SHA256 = bd750d6c4226f84118a226c796585ec131920af4cada37a6fa30ba21d8a1e904
expires_at = 2026-12-04T08:18:25Z
```

The workflow verifier rebuilt the scan without network. Both new ZIPs were downloaded and independently reconciled against artifact digests, the exact nine-file inventories and all file/content hashes, HTTP metadata, clocks and baseline equality. For the final scan, a separate DOM check matched all 29 recorded allowed anchors/title/date/positions and verified the 16 target dispositions against the original reviewed sources. The MOA body and baseline match prior artifacts byte for byte. Independent local checks were hash/DOM/date/plan reconciliation, not a second full project-verifier run. HTTP/content hashes are not independent publisher authentication. Original HTML is evidence, not content to execute.

## Remaining gates and next priorities

Do not repeat these scans just to obtain another green status. Natural new-detail acquisition and source-review completion remain unproven: zero article requests cannot validate that path. No persistent seen/review queue, automatic economic acceptance or continuous feed has been introduced. Known URL body-only revisions are still not checked. Artifacts still expire after 90 days; no long-term checkpoint was created.

Before further generic infrastructure, follow the reuse decision. For new releases use the existing source-review process, not a new bespoke approval engine. For actual stock dumps validate the existing PyArrow/DuckDB reader options and entitlement in isolation; do not write a Parquet decoder. For broader crawling assess maintained adapters/RSSHub/Scrapy before adding orchestration. A maintained external feed is a discovery source, not a substitute for qualified original evidence.

Latest real Sector proof is still #4 / `33939414197` on `5f8f635d191dd8559844d1b74af0dca0cf4c02df`, ending 2026-09-04 with zero prospective events. Next actual single-session append, live input-audit replay and context artifact publication remain pending. No HiThink request, market/event update, schedule, signal-threshold change, company-posture change or canonical Human wake occurred here. Do not request another same-session run simply to repeat it. Read current main and CI rather than assuming this handoff's implementation remains latest.

SHADOW OBSERVATION ONLY. FUNDAMENTAL STATE AUTHORITY = NONE. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
