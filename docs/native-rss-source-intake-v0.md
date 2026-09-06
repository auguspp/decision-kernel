# Native NBS RSS intake and seen-version succession — v0

Status: SOURCE WINDOW INTAKE / NOT ECONOMIC FACT ACCEPTANCE / NOT A NEWS-WIDE OR MARKET PRODUCER.

Actual first baseline: `docs/native-rss-qualification-2026-09-06.md`. Run 34010252507 retained both full 500-entry feeds and rebuilt its initial registry/page. Four preceding incomplete attempts and the explicit resource reviews remain documented. All 1000 baseline publication strings lack timezone: no source Evidence or prospective events were exported. Cloud successor restoration and natural arrival remain unproven.

## Native source and reuse decision

The National Bureau of Statistics itself advertises two HTTPS feeds on its RSS subscription page:
- https://www.stats.gov.cn/wzgl/rss/202302/t20230217_1912859.html
- latest releases: https://www.stats.gov.cn/sj/zxfb/rss.xml
- interpretations: https://www.stats.gov.cn/sj/sjjd/rss.xml

These exact two sources are the entire v0 profile. Selecting a publisher/channel precedes seeing its entries; no company, theme, keyword or success sample is preselected. This is not representative of all Chinese news or official statistics. The subscription announcement verifies the addresses, not live transport, actual XML format, article coverage or future reliability. Real capture results are documented separately after inspection.

Use feedparser **6.0.14**, the maintained BSD-2-Clause parser, in the optional `feeds` extra and development environment, not Kernel base requirements. Feedparser owns XML/RSS/Atom parsing and namespaces. Existing Beautiful Soup handles a feed's HTML description when preparing plain text; it is not a new article scraper. Python's existing standard-library public HTTP policy, source clock/header/file guards, EvidenceArtifact and canonical identity are reused. RSSHub's maintained MIIT adapters were inspected as prior art; no RSSHub instance, TypeScript scraper, proxy service or AGPL code is needed where a native official feed exists.

Primary references: https://pypi.org/project/feedparser/ ; https://feedparser.readthedocs.io/en/latest/bozo/ ; https://feedparser.readthedocs.io/en/latest/date-parsing/ . The parser is deliberately invoked on an in-memory byte stream, never a URL or path string. No parser-driven HTTP, image, entity, enclosure or article fetch is permitted. Reject malformed/bozo XML rather than accepting its loose-parser recovery. Reject DTD/entities and unknown formats; all original feed bytes remain separate from parsed strings. The profile reads title/description/publication/update fields only, not every optional feed field or content:encoded full text. Library normalization, including description outer-whitespace removal observed in the real baseline, is not an original-byte quotation claim.

## Observation identity, not truth or independence

A document key binds the publisher and exact article URL. A version binds that key plus the parsed title, description, content types and raw date strings. Do not guess canonical URLs, remove query parameters, merge equal headlines, normalize proxy instruments or fetch linked pages. Current supported NBS article paths are explicit. A GUID is scoped to the feed; rebinding it to a different link fails. A new GUID for an identical link/version does not create a new version.

Identical link/version appearances across both feeds deduplicate while preserving both appearances. Different descriptions for one link remain separate feed representations, not a verified article revision. Conflicting simultaneous representations block downstream preparation. Different links, GUIDs, titles, versions or feed categories never establish independent sources. There is no mention velocity, confidence score, beneficiary classification, Research gate or investment authority.

Initial capture is **INITIAL_BASELINE_ONLY** and exports no prospective source rows. The source registry then preserves old versions and their first received/recorded clocks. A newly observed older publication is retained rather than discarded by a publication-date high-water mark. A disappeared entry is not deleted or presumed withdrawn: RSS is a rolling window. Changes are FIRST_SEEN_LINK or CHANGED_FEED_REPRESENTATION, not newly published facts. NO_NEW_FEED_VERSIONS is about these windows, not the publisher or market.

The registry records seen versions, NOT acceptance/delivery acknowledgments. Non-baseline versions remain a visible pending source inventory, with stable Evidence IDs when usable; preparation does not acknowledge consumption. Blocked descriptions must not disappear merely because the next window is unchanged. No consumer automatically executes these rows or advances a market signal. A later bounded consumer/explicit review must define its own receipt without turning this registry into a second signal authority.

## Time and downstream source records

Keep the source's date strings verbatim, actual request/receive times and registry-recording time separate. Feedparser accepts incomplete or impossible dates by normalizing them; that behavior is NOT inherited as PIT authority. Only a complete valid RFC3339 or qualified RFC822 numeric/GMT/UTC timestamp can supply Evidence.published_at. Date-only, timezone-less, ambiguous abbreviation, invalid or future dates remain visible and block the whole proposed source batch; do not invent midnight or reinterpret retrieval as publication. The parser's date tuple is not an authenticated publication clock. The real unzoned NBS strings therefore remain unqualified for that export; the baseline does not resolve this gap.

Usable descriptions become existing EXTRACTED_VALUES/PARTIAL EvidenceArtifact source rows with conservative available_at == first_received_at, original first retrieval/record time and exact retained feed-version identity. Only descriptions are selected for the existing theme-source matcher; titles remain visible metadata, not automatically scanned source evidence. HTML descriptions are library-projected text, not certified article quotations. Missing descriptions remain explicit gaps. More than the existing 32-source or text budget blocks the full export, never a hidden first-N subset. The downstream theme budget remains unchanged at three; this module performs zero market requests.

## Execution, failure and restoration

```
python -m decision_kernel.runtime.radar_feed_intake capture --bootstrap --output /new/baseline
python -m decision_kernel.runtime.radar_feed_intake capture --previous /exact/prior/capture --output /new/successor
python -m decision_kernel.runtime.radar_feed_intake verify --output /saved/capture
```

Every run needs an explicit separate baseline OR an exact previous successful capture. No implicit empty fallback. Both RSS windows must pass before publishing a successor registry; a partial HTTP/XML failure retains attempted-source evidence but publishes no registry or success page. Each source is tried once; no redirect, cookie jar, proxy credentials, retry, fallback, conditional-304 shortcut or linked-resource fan-out. Reviewed bounds are two requests, **8 MiB per response and 512 entries per feed**, 4096 stored versions and 6 MiB registry bytes; exhaustion requires explicit checkpoint/migration, not pruning or resets. The initial 2 MiB/128-entry assumptions were replaced only after inspecting actual source metadata/raw XML. Both resource limits are now bound in the policy identity; original failed receipts keep their original implementation. Existing economic HTML bounds and downstream semantic budgets did not change.

The existing `economic-release-discovery` workflow adds `nbs-native-rss`. Its previous MOA/SPB directory mode remains the manual default with unchanged calculations and preserved failure evidence. Push compatibility is now limited to this new runtime file and deliberately creates an independently named **baseline-only** trial, not a daily successor or reset of a latest-state pointer. Old source files, workflow-only and docs changes no longer auto-repeat the two HTML-directory requests. No schedule or new workflow file is introduced.

Manual RSS successor execution requires an exact previous run ID. GitHub CLI checks the same repository/workflow/main/fresh attempt and completed-success status; official download-artifact restores the exact named artifact with digest mismatch treated as error. The intake verifies original prior feed reconstruction, source policy, run identity, LIVE versus synthetic and clocks before any new public request. No automatic latest-success search is implemented. All GitHub credentials are confined to metadata/download steps, not RSS fetching. Missing/expired/wrong artifacts fail; never silently bootstrap. An explicit new baseline is a separate chain and cannot claim continuity. The first successful real baseline did not exercise these restoration steps.

Archive contains capture.json, two original XML bodies, registry.json, delta.json, source-rows.json and index.html; successors also retain previous-registry.json and its parent capture hash. Verification reconstructs the current transition and page from original RSS and the preserved parent registry, not from a self-asserted derived hash. The initial previous bundle is fully verified when opened; embedding a parent registry is not embedding every ancestor's raw XML. Hashes are not signatures or permanent recovery. Git/source policy changes need explicit migration or original implementation replay, not transparent reinterpretation.

Artifacts retain **90 days**, with no cache and no automatic long-term checkpoint. Preserve original bundles and exact code/parser versions outside expiring Actions storage before expiry to retain the full chain. The latest successful artifact can continue seen-version state only when explicitly identified and verified. An archive expiring does not authorize a blank reset. Restored cloud-success and new natural-source succession require separate live evidence; synthetic same-input tests and a single real baseline do not establish either.

No production Sector state/ledger/rank/threshold/company judgment changes. Human / Research / Investment / signal-transition authority remains NONE. This is an upstream source observation surface, not a new canonical attention lane, economic-release acceptance or Judgment lifecycle.
