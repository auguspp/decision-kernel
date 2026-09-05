# 产业证据 × 行业状态 — v0

Status: READ-ONLY HARNESS ASSOCIATION / SHADOW OBSERVATION / NOT CAUSAL CONFIRMATION.

## Delivered module

`runtime/economic_market_context.py` combines the existing saved Sector context with existing source-derived economic observations, producing Chinese `index.html` and `association.json`. It is independently callable and does not require a price candidate before displaying a supplied economic release. It never creates a new signal, Research route, Human wake, investment Judgment or Action.

The purpose is to answer: what does the saved industry price path show, which reported economic quantities changed, what period/version was actually supplied, and which transmission questions remain unresolved? It does NOT answer whether corporate fundamentals are improved or the market has failed to price information.

## Company-business evidence reading — PR #234

Read `docs/economic-company-context-v0.md`. The independent `economic_company_context` command reuses this shared-input reading and appends explicit company EvidenceArtifact fields, source roles, transmission hypotheses and missing evidence. The first curated case is retained YTO H1/IR evidence; livestock and capacity coverage gaps remain explicit. `association.json` and `input-set.json` remain unchanged, while `company-links.json` binds the added reading to the exact association. No member/rank-based company inference, current-original verification, exposure magnitude, net-benefit conclusion or new authority is created.

## Shared input directory — PR #233

Read `docs/economic-release-input-assembly.md`. `economic_release_inputs context` now expands one frozen seed plus one directory of existing accepted bundles into this unchanged CLI. The same resolver supplies the next bounded directory scan and records exact input identities/cutoffs. The default `radar_inputs/economic-reviewed-releases/` is empty; no natural source acceptance is invented. Registered bundles require explicit preservation, and every child is reverified rather than selected by filename or modification time.

The existing discovery workflow uses this resolver and its offline check; it retains original scan output plus an explicit original-seed-window gap report. Advancing a known-publication cutoff cannot quietly hide an in-window unreviewed row. Known-URL bodies remain unverified for revisions, same-URL metadata conflicts require review, and economic versions remain separate in this page. Refer to PR #233 for exact CI and real workflow evidence; tests alone do not prove natural new-release acceptance. No market, Kernel, threshold or authority semantics change.

## Explicit discovered-source review ingress — PR #232

Read `docs/economic-release-review-v0.md`. The existing association CLI now accepts repeatable `--reviewed-release <acceptance-directory>` inputs alongside explicitly pre-reviewed legacy `--observation` inputs. Each new input is rebuilt from its original discovery archive and explicit source-review declaration, using the existing verifier, binder and economic parser. A loose discovery packet or whole acceptance JSON cannot masquerade as an old observation.

New source capture, declared review and first recorded acceptance are separate clocks. Consumption is not permitted before the acceptance was recorded, even when its original source was acquired earlier. The original observation's capture time/hash is not rewritten; HTML and JSON retain the separate review receipt and its later eligibility. This is source review, not Human investment judgment, authenticated reading, automatic fundamental confirmation or a new event. Empty drafts and unresolved source templates remain unaccepted. Exact duplicate reviews do not create new economic periods; different selected source versions still require version review.

The existing local acceptance helper stages, verifies and publishes a new immutable bundle containing a copy of the original discovery archive. It does not operate an approval platform, update the discovery baseline, auto-select a latest source or provide remote retention. The original discovery runtime/implementation must remain compatible for revalidation. Combined old observations and accepted bundles remain limited to 64 supplied inputs. With no new review inputs, the original projection behavior remains unchanged. This implementation is exercised by synthetic end-to-end tests, not a claim that a natural new public release has been accepted or published live.

## Explicit reading links, not a new taxonomy

`radar_inputs/economic-market-links-v0.json` is an implementer-curated display association, not a Human investment/exposure record or Kernel object. The reviewed clock records preparation of this mapping, not a historically known taxonomy. It is tied to the exact catalog hash and verified code/name/family of the saved state:

- National live-hog/corn/fattening-feed releases beside 881102.TI 养殖业 and 884275.TI 生猪养殖. The broad industry contains other activities; these are separate 881/884 ranks, not a combined universe or a newly revalidated parent relation.
- National express volume/revenue/mix-proxy releases beside 881152.TI 物流. Logistics is broader than express, NOT a pure express index. The frozen catalog has no selected 884 express identity; none is invented or substituted.

These names and codes were checked in the previously saved 2026-09-04 market state and are tested against the committed durable bootstrap. A new catalog identity requires explicit mapping review; no name-based, keyword or proxy remapping happens. Mapping bytes plus hash demonstrate what was selected, not that a causal relation or company beneficiary has been established. Review questions are display prompts only, never automatic Research requests.

## Independent axes, not an opportunity score

The market side reuses `build_sector_radar_context`, including exact current/previous calculations, current gate predicates, 5/20/60-session raw/benchmark/excess returns and homogeneous-family ranks. Existing recorded event identities remain visible. A gate currently being active is not a newly recorded false-to-true event, and a gate being inactive does not prove information is unpriced.

The economic side revalidates each complete observation with the existing `economic_node_study` source-derived validator and uses its comparison function. Values, units, source URL/title, period, date-only publication clock, capture time, excerpt and original hashes are retained. All metrics keep descriptive UP/DOWN/UNCHANGED directions, NOT favorable/unfavorable economics labels. Pig price increases do not establish farm profits; revenue per parcel remains the rounded aggregate mix proxy, not a like-for-like price or company margin.

Coverage states are separate from price state:

| State | Behavior |
|---|---|
| NO_OBSERVATIONS | The mapped node remains visible; absence is not deterioration or confirmation. |
| ONE_PERIOD_ONLY | Keep the single period; no invented direction. |
| VERSION_REVIEW_REQUIRED | A selected period has differing source versions; retain them and require review instead of selecting the latest. |
| NONADJACENT_PERIODS | Missing intervening weekly/monthly periods are not turned into ordinary sequential comparisons. |
| CAPTURE_ORDER_REVIEW_REQUIRED | Period order and capture/publication order disagree; no automatic reordering. |
| TWO_PERIOD_DESCRIPTIVE_COMPARISON | Compare the latest two distinct periods IN THE PROVIDED INPUT SET, not a claim about the publisher's actual latest release. |

An exact observation repeated in input collapses to one observation. The same source record re-captured at another time remains one release period, not a new release, revision or evidence of first-public vintage. Different supplied versions in either selected period block comparison; older records stay in the audit even when not selected. No observations are silently truncated to fit a candidate budget. v0 accepts at most 64 observation files, at most 4 MiB per bounded JSON file.

## Time and provenance

Explicit `as_of` is the input knowledge boundary. Economic captures, mapping review, saved state and ledger must not be later than it, and it cannot follow page generation. Merely old publication dates cannot legitimize later-captured records at an earlier system cutoff. Future supplied records are rejected, not silently used or re-dated.

The saved price session, economic reporting/collection period, date-only official publication, actual source capture, mapping preparation, input boundary and page-generation clock remain separate. The module records whether each provided capture came after the saved market close and whether its economic period extends beyond that price date. Neither relation proves what all market participants knew. A September 5 capture beside September 4 prices is a later reading context; it is not injected into the September 4 signal.

Natural-day distance is labeled as such, not missing trading days or publication lateness. No publisher schedule is qualified by this module, so it cannot say there were no updates, a release is overdue, or an unchanged old value reconfirms a thesis. Saved market freshness is explicitly NOT revalidated.

`fundamental_confirmation` stays NOT_ESTABLISHED. Company exposure, membership, prospects, forecasting independence and thesis validation are outside this module. Human annotations are not an input. No automatic causal support/opposition score is generated. Source-derived validation and hashes do not independently authenticate a website or a claimed review; preserve the original capture/source-audit chain separately. Synthetic inputs do not become real prospective records when joined to a price view.

Generation time is outside projection identity. Rebuilding the same input boundary with the same inputs does not create a new event or rewrite the economic observations. The existing content hash and deterministic Decimal arithmetic are reused.

## Run against saved inputs

Install the existing package; no new dependency is required. Unpack the desired verified Sector state bundle and previously verified economic capture. Pass explicit `observation.json` files, NOT arbitrary free-text claims or discovery packets awaiting review:

```bash
python -m decision_kernel.runtime.economic_market_context \
  --bundle ./saved-sector-state \
  --parent-hints ./radar_inputs/sector-parent-hints-2026-09-05.json \
  --links ./radar_inputs/economic-market-links-v0.json \
  --observation ./saved-capture/0000/observation.json \
  --observation ./saved-capture/0001/observation.json \
  --observation ./saved-capture/0002/observation.json \
  --observation ./saved-capture/0003/observation.json \
  --as-of 2026-09-06T12:00:00+00:00 \
  --output ../economic-market-reading
```

The cutoff shown is an example, not a claim that a live run occurred at that time. Use an actual applicable input cutoff no later than generation. The bundle loader verifies its existing repository/workflow/parent-hint identity. The module then reads the saved state; it does not fetch or restore producer state. The output must be a fresh directory outside all input directories. Failures do not overwrite prior reports; interrupted new output is removed. Missing economic coverage still produces an honest readable report, while malformed, future or conflicting identities fail before publishing one.

Open `index.html` with `association.json` retained. No server, JavaScript, remote assets, telemetry or input form is added. Explicit original-source links can open their official websites. JSON includes all supplied unique observations, selected periods, comparison hashes, independent market rows and the reviewed link configuration. It is a reading projection, not a second state ledger.

## Reuse and acceptance

Reuse existing economic qualification/comparison, saved-state/context generation, bundle/hint validation, canonical identity, standard HTML escaping and native disclosure. Beautiful Soup is already a dev dependency for DOM assertions. No new parser, data fetcher, factor library, state service, workflow, schedule or Kernel entity is introduced. This task is project-specific association semantics, not a reason to import another backtest or multi-agent platform.

Tests exercise the exact committed bootstrap and existing reviewed-source fixtures, plus the real synthetic audited producer for actual calculated event identities. They cover missing/single/repeated/revised/gapped releases, ordering, late captures, rehashed source-value tampering, mapping drift, separated ranks, immutable input bytes, generation/Decimal stability, HTML safety and the full existing bundle-load CLI. The tests are not a new LIVE_HITHINK run, a new economic-source acquisition or a new prospective corpus.

Explicit local review ingestion and shared directory input assembly are implemented as described above. Natural new-release application, durable original-archive retention, association-page workflow publication, current company-original/segment qualification and genuinely forward co-observation remain future work; unattended review acceptance is not authorized. The separate Sector direct-next-completed-session append, sealed input replay and publication acceptance are still required. This module's offline functionality does not satisfy those milestones or unlock schedule, thresholds or canonical Inbox integration.
