# Industry observation to company-business evidence — v0

Status: READ-ONLY HARNESS / RETAINED SOURCE INPUTS / NO BENEFICIARY SELECTION.

## What is implemented

`runtime/economic_company_context.py` composes the existing shared economic inputs and saved Sector reading with explicitly selected company EvidenceArtifacts. The same command reads the seed and accepted-release directory; it does not require manually repeating every observation flag. The result keeps the original economic/market `association.json` and `input-set.json` unchanged, adds `company-links.json`, and places the company-business section in the existing HTML page.

This answers: which retained company fields are relevant to a proposed transmission mechanism; which business scope and period do they describe; what still needs evidence? It does not answer which stock will benefit or whether a current investment thesis is true. The independent 881/884 rankings and existing market events are not modified. No ranking, member list, ticker keyword or generic supply-chain graph creates a company link.

## First bounded example: YTO, not a new company research conclusion

The manifest `radar_inputs/economic-company-links-v0.json` explicitly selects the existing `research_cases/600233-yto-deep-research-v2.json`, local Git blob `ae9bfce4dd3cfbedddb4be84075238d867f58529`, available at source reference `f0a667a4e569584b511bf16f151772a38492e700`.

- Express node: YTO's retained H1 volume, unit revenue/cost, transport/center costs, operating cash flow and cash capex. Seven numeric fields remain exactly as retained; no new conversion or arithmetic is applied.
- A separate investor-relations EvidenceArtifact retains two management statements about franchise fees and cost composition. It remains PRIMARY_STATEMENT / ATTRIBUTED_STATEMENT, not realized franchise profitability.
- Revenue, cost and cash/reinvestment channels are HYPOTHESIS_WITH_RETAINED_INPUTS. Their fields are available inputs, not proof that the mechanism has occurred.
- Capacity/utilization is EVIDENCE_GAP. Parcel count and capex do not establish capacity, utilization, investment return or maintenance/growth allocation.
- Exposure size, elasticity and net-benefit direction remain null. In particular, dividing express profit by group parent profit does not produce an audited segment revenue share.
- Livestock has NO_COMPANY_EVIDENCE_SUPPLIED. This is missing supplied coverage, not evidence that no company is exposed. Do not fill it with industry members to make the page look complete.

These are existing retained records, not new 2026 company disclosures acquired this turn. Their source locations include mirrors; both selected artifacts have EXTRACTED_VALUES / PARTIAL retention. The original PDF and exact original page numbers were not reverified. The display keeps the original source locator, location description, period and available/retrieved clocks and explicitly shows these limits. There is no fabricated page citation, raw-PDF hash, direct-original acquisition, FULL replay or current-business freshness claim.

## Reuse and layer discipline

The implementation reuses EvidenceArtifact validation and `source_policy_v2` role/admissibility functions. Company-source facts are not parsed out of Research prose; only explicitly selected retained fields are read. The source Research package is not committed, recalculated or promoted to a fresh recommendation.

File reading uses the existing bounded, canonical-relative-path/symlink-safe Timeline helper. Identity uses existing canonical hashing. The UI uses the existing economic page and native HTML disclosure; tests use the already-installed Beautiful Soup. The shared-input and market-bundle CLI is executed rather than replaced. No new graph library, parser, data downloader, approval platform, database or Kernel schema is introduced. The prior-art refresh already defers NetworkX until an actual graph algorithm is needed; this bounded mapping does not need one.

Mechanisms, units and business-scope labels are implementer-curated declarations, not additional issuer quotations. Hashes and type checks prove correspondence to retained bytes, not economic correctness, source authenticity, issuer authorization or Human reading. The source commit is a declared immutable navigation reference; this reader verifies local blob bytes, not Git ancestry. A full publication proof must separately bind its checkout/source revision.

## Identity, time and failures

Company ticker/exchange/name must equal the selected source container identity. Exact Evidence ID and source identifier must match; unknown fields, duplicate IDs/bases, orphan evidence, unrecognized roles, metadata-only sources and unsafe source URLs are refused. Investor-relations statements cannot be upgraded to realized facts, and sell-side forecasts cannot substitute for the selected company evidence.

Company source bytes are pinned. Changed bytes require explicit new mapping review even when JSON values look identical. A validly rehashed file still has to pass EvidenceArtifact and source-use semantics; a hash is not sufficient acceptance.

Source publication, availability, actual retrieval, mapping preparation, economic reporting periods, market session and page generation stay separate. Selected evidence must have been acquired by mapping preparation, and mapping preparation must be no later than the requested input cutoff. Current-business freshness and temporal alignment remain NOT_ESTABLISHED/NOT_REVALIDATED. H1 company fields beside a later national monthly release are not same-period confirmation, and assembling the page never backfills a historical market event.

Limits: eight economic nodes, eight companies per node, sixteen company-node entries total, eight evidence bases per company, sixteen selected fields per base and four transmission channels. Source JSON files and manifest reuse the existing 256 KiB reader bound; the existing association reader retains its own 4 MiB bound. Over-budget inputs fail, not truncate to a top-N list. A node without a company still needs an explicit coverage record.

The combined command stages all files outside input roots. Invalid input or interrupted publication does not leave a partial output or replace a prior report. Inputs are rechecked before final publication. This is a single-writer local reading operation, not a concurrent database or remote state commit.

## Run

Use the existing package and discovery extra (needed for any accepted economic source bundles), an already verified saved Sector bundle, and the existing seed/review directory:

```bash
CUTOFF=$(python -c 'from datetime import datetime, timezone; print(datetime.now(timezone.utc).isoformat())')
python -m decision_kernel.runtime.economic_company_context \
  --seed radar_inputs/economic-node-study-2026-09-05.json \
  --reviews-dir radar_inputs/economic-reviewed-releases \
  --bundle ../saved-sector-state \
  --parent-hints radar_inputs/sector-parent-hints-2026-09-05.json \
  --links radar_inputs/economic-market-links-v0.json \
  --source-root . \
  --company-links radar_inputs/economic-company-links-v0.json \
  --as-of "$CUTOFF" \
  --output ../economic-company-reading
```

The output directory must be new and outside source/market input roots. Open `index.html` with `association.json`, `input-set.json` and `company-links.json` retained. There is no hosted site, remote asset, auto-fetch or telemetry. Clicking an explicit source link can open its original recorded locator. Reproduction requires the exact original source files and economic/market inputs, not only the derived report hashes. No workflow attachment or remote long-term retention was added.

## Acceptance and remaining work

Tests use the actual committed YTO source and economic excerpts, and the existing audited synthetic Sector producer for full shared-input CLI execution. They cover missing coverage, source roles, exact bytes, rehashed invalid fields, issuer/ID mismatches, PIT boundaries, HTML escaping, nonmutation and interrupted output. Synthetic candidate events are not a real prospective corpus. Full run/test results belong to the implementing PR, not an invented live proof.

A natural current-company application still needs original filing/page verification, period-aligned operating observations, explicit segment magnitude where reported, and relevant counterevidence. None of those gaps is solved by this projection. No automatic Research route, opportunity score, equity ranking, Human Decision, Action, schedule or market/cache/event-ledger write is authorized. Sector's real next-session append and later T+5/T+20 maturity remain separate pending milestones.
