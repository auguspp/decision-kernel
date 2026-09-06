# Livestock company evidence — Muyuan original-page case, 2026-09-06

Status: ORIGINAL ACQUIRED / SELECTED PAGES REVIEWED / READ-ONLY RADAR CASE / NOT INVESTMENT RESEARCH OR CONFIRMED BENEFICIARY.

## What was actually obtained

PR #235 reused the existing CNINFO Requests transport, issuer resolution and announcement parser. The existing source-study workflow ran once: **33999968354 / attempt 1**, job **101396950653**, at merge **f69dbfcd5c6f8b40eb5a2c3e31382231ab34f336**. Its livestock job acquired the original, reconstructed its selection and checked all saved bytes, uploaded the artifact and published its access link successfully. The old remaining-listings job was correctly skipped, not silently repeated.

Three requests, each once, all HTTP 200: issuer directory, a fixed 2026-08-01 through 2026-09-06 announcement query, and one uniquely matching full report. No HiThink, stock-price download, retry, redirect, substituted issuer, summary-as-full-report, or automatic extraction acceptance occurred.

- Issuer directory mapped 002714 to CNINFO organization **9900022995**.
- Selected full-report ID **1225485220**, title `2026年半年度报告`.
- Official original: https://static.cninfo.com.cn/finalpage/2026-08-21/1225485220.PDF
- Provider publication metadata: **2026-08-21T00:00:00+08:00**. Midnight metadata is not independently proved intraday first availability.
- Original download started **2026-09-05T23:56:46.679676+00:00** and completed **2026-09-05T23:56:48.407690+00:00**.
- Original: **3,954,283 bytes / 196 PDF pages**; SHA256 **06f3f6284318122399c6cf1156f5a142c9b9abd8157c669ccd37bdb298002c53**.
- Artifact **9979191964**, `muyuan-original-33999968354-1`: **2,882,921 bytes / six files**, ZIP SHA256 **2a16701a1fdc00a8d499bbe774e2a667b8a3cc01ef7cc82216d54fd52b65c792**. Retention **90 days**, expiry **2026-12-04T23:56:21Z**.
- Capture hash **77a4c26eb655547fcf12f7976049bbbfa7a16fa4acab5417a5930b69bfb99505**.

Downloaded ZIP, inventory, three response sizes/hashes, workflow/capture canonical hashes and saved verification equality were independently checked locally. The existing capture/selection verifier ran in Actions. pypdf extracted the original text; PyMuPDF rendered pages 6, 11, 12, 19, 20, 25, 26, 66 and 67 for direct visual review. No OCR. Only the selected pages/fields were substantively reviewed, not an audit of the complete report or its truth. This is an implementer source review, not authenticated Human reading or investment approval.

## Issuer and business identity

**PDF page 6 / printed page 6** identifies 牧原股份, A-share **002714**, Shenzhen Stock Exchange, legal entity 牧原食品集团股份有限公司. It also lists an H-share code; this view does not substitute that other instrument. **Page 12** describes pig farming/sales and slaughter with an integrated feed-processing, breeding, farming and meat chain. Business existence is relevant context, not a verified causal sensitivity.

## Reported financial fields and their limits

All below are retained strings from the 2026 H1 column; currency amounts are **CNY**, not 100 million CNY. Percentage fields use percent, not fractional weights. Page numbers are one-based PDF and printed page numbers, equal in this original.

| Original page | Field | Reported value | Scope |
|---|---|---:|---|
| 19 | Consolidated revenue | 59,410,306,384.59 | H1 group revenue |
| 19 | Farming revenue | 52,430,296,318.87 | Includes interbusiness sales |
| 19 | Slaughter/meat revenue | 22,061,248,684.20 | Read alongside elimination |
| 19 | Trade revenue | 4,319,430,543.58 | Feed-material product revenue is not feed purchase cost |
| 19 | Other revenue | 1,639,750,264.40 | Kept in the revenue bridge |
| 19 | Interbusiness sales elimination | -21,040,419,426.46 | Keep its original sign; not another business loss |
| 19 | Reported farming/slaughter revenue proportions | 88.25% / 37.13% | Not disjoint external revenue weights |
| 20 | Farming/slaughter gross margins | -4.51% / 4.24% | Gross, not net margins |
| 19 and 66–67 | Consolidated operating cash flow | -2,223,668,382.68 | Consolidated, not parent-only cash flow |
| 67 | Cash paid for fixed/intangible/other long-lived assets | 6,520,966,515.39 | Not all investing cash flow or identified maintenance capex |

The four business revenues PLUS the signed elimination exactly reconcile to consolidated revenue using Decimal. That is arithmetic consistency, not independent validation of accounting. The two quoted revenue proportions exceed 100% in combination because they are not mutually exclusive external-revenue shares. Do not normalize them into economic exposure weights or infer net pig-price benefit. No FCF, earnings sensitivity or share-price implication is computed.

## Operating statements: actual period, approximation and target must not collapse

**Pages 11–12** report H1 commercial-pig sales **3,861.5 ten-thousand head**, explicitly including sales to the group's slaughter/meat business, and slaughter volume **1,723.4 ten-thousand head**. Neither is installed capacity or capacity utilization; they cannot be added as independent pig sales.

**Page 11** describes June 2026 full farming cost at approximately **11.7 CNY/kg**, separately from the aspiration to reach a full-year average **11.5 CNY/kg**. The first is a single-month approximate company statement; the second is a target, not achieved annual cost. The stored target remains attributed TEXT. Do not subtract either from an August national weekly pig quote to manufacture current company profit.

**Page 25** attributes roughly **55%–65%** of operating cost in past years to wheat, corn, soybean meal and other principal raw materials together. This is not an exact 2026 H1 share, not corn-only, and not a justified 60% model coefficient. **Page 26** describes flexible ingredient substitution and purchasing responses; it does not quantify actual mix, inventory-cost lag or successful hedging. Both remain PRIMARY_STATEMENT / ATTRIBUTED_STATEMENT, not a current realized cost bridge.

## Reading integration, not another research state

`radar_inputs/company-evidence/002714-muyuan-h1-2026-09-06.json` stores existing EvidenceArtifacts inside a small **evidence-only** container. It has a company identity and first local recording time, no ResearchSnapshot, thesis, Odds, decision, confidence or trading instruction. Acquisition must precede recording; recording must precede mapping preparation and input cutoff. The new path does not manufacture a research snapshot merely to satisfy the former reader's file layout.

`radar_inputs/economic-company-links-livestock-v1.json` is an explicit opt-in manifest for the existing `economic_company_context` command. It adds Muyuan beside the livestock node, preserving the previous YTO company fields and mechanisms. The old default v0 manifest remains unchanged for exact old-input reproduction.

Financial table inputs use PRIMARY_REALIZED / REALIZED_OUTCOME as the existing source-use policy permits. Operating discussion, cost targets, the past-years raw-material range and management responses are attributed company statements. Three EvidenceArtifact subsets are three selections of ONE report, not three independent sources. Hashes/role labels do not prove truth, issuer authorization, semantic extraction correctness or Human acceptance. Text fields are reviewed paraphrases, not purported verbatim quotations.

Evidence remains **EXTRACTED_VALUES / PARTIAL**. `content_hash` binds source URL, raw-PDF hash, page-location description and the retained fields. The raw PDF is separately retained in the finite-lived source artifact, not embedded in the JSON or guaranteed forever. Conservative `available_at` equals actual PDF acquisition; the original declared publication metadata is preserved separately. The renderer reads the frozen fields and does not reopen the PDF, so `original_page_verified_this_run` correctly remains false.

Revenue, cost and cash-flow mechanisms remain hypotheses with evidence inputs; capacity/utilization remains an evidence gap. Exposure size, elasticity, net-benefit direction, current-business freshness and period alignment are not established. H1 financials, a June company cost statement and late-August national weekly prices describe different periods and scopes. No industry members/rank generate company exposure, no new market event or automatic Research route is created.

## Use and acceptance

Run the existing command described in `docs/economic-company-context-v0.md`, replacing its `--company-links` argument with `radar_inputs/economic-company-links-livestock-v1.json`. Use a real input cutoff after this manifest's preparation, a verified saved Sector state and the existing economic inputs. The result keeps original association/input receipts and adds the company section; no workflow publication or hosted site is claimed.

Tests read the committed reviewed fields, existing source policy and actual audited synthetic Sector producer/shared-input CLI. They check the financial bridge, signs/units, target and range qualifiers, source/container identities, late clocks, old v0/YTO compatibility and unchanged candidate identities. Full CI is recorded in the implementing PR; tests are not fresh issuer observations or an independently audited report. New extraction transport/parser/graph/Kernel schemas are unnecessary and not introduced.

To revalidate the raw original, preserve the exact downloaded artifact before expiry. A later re-download must be a new capture and compared by hash; the URL alone cannot reconstruct the old version. Remaining work is same-period follow-through, fresh operating evidence, actual capacity denominators and causal/magnitude testing, not automatic acceptance of a beneficiary conclusion. Independent Sector next-session live acceptance is still pending.
