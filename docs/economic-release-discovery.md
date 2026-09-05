# Bounded official release discovery

Status: IMPLEMENTATION / REAL DIRECTORY PROOF PENDING / NOT CONTINUOUS COVERAGE / NO AUTOMATIC FACT ACCEPTANCE.

## What changes

The original economic-source capture tool starts from four already-reviewed URLs. This separate command starts from two fixed official directory pages, retains their actual response bodies, extracts dated links, compares against an explicit reviewed baseline and obtains at most four unreviewed article bodies. It never writes an economic observation, market event, candidate ledger, Research handoff or investment decision.

Reviewed baseline: `radar_inputs/economic-node-study-2026-09-05.json`. It is copied into every scan archive and content hashed, not silently updated by discovery. Each publisher must have a reviewed baseline. The baseline cannot contain knowledge acquired after the scan clock.

## Sources and incomplete coverage

The directories checked during source research on 2026-09-05 are:

- MOA monitoring list: https://xmsyj.moa.gov.cn/jcyj/ . Only titles in the livestock/feed weekly-price family are target releases. Slaughter-price publications, animal disease reports and other monitoring items are outside this first discovery family, though qualified visible article rows remain in the directory evidence.
- SPB industry-news first page: https://www.spb.gov.cn/gjyzj/c100015/c100016/common_list.shtml . Only national monthly/first-half postal-industry operating releases are target titles; ordinary news is not an economic release.

The MOA page visibly lists recent feed and slaughter publications with full dates. The SPB page visibly lists a short news window, which can push monthly releases out of view. The SPB statistics landing page https://www.spb.gov.cn/gjyzj/c100275/pubtz.shtml was investigated, but its raw dated-list delivery was not established in this environment; it is not silently substituted into the parser.

**This is a first-page window, not complete release discovery.** Every output records this boundary and the visible oldest/newest dates. A successfully scanned page without target links is not evidence that the publisher has no new release. A blank, script-only, malformed, undated or unreachable page is an explicit INCOMPLETE result, never a quiet scan. A continuous service still needs qualified pagination or dedicated statistics-directory coverage and missed-window handling, especially for SPB. Do not enable a schedule or claim complete monitoring from this slice.

Research page text is not archived original response evidence. The local runtime's DNS/file-download failures did not justify reconstructing originals from web snippets. A separately reviewed networked probe must prove actual directory markup and request behavior.

## Discovery, backlog and review

A list row must bind one same-family HTTPS article link to one explicit valid full date inside the same `li`. Relative same-origin paths may be resolved, but credentialed URLs, alternate hosts, queries, fragments, redirects and arbitrary resources are rejected. Conflicting metadata for a repeated URL is rejected. Script, style, template and noscript content is not used for discovery. This initial link parser accepts UTF-8 only; other encodings are not guessed.

The deterministic plan distinguishes:

```text
KNOWN_URL_NOT_REVALIDATED
  Exact title/date metadata matches reviewed baseline; body is NOT fetched.
  This does not rule out an unseen body-only revision.

KNOWN_METADATA_CHANGED_REVIEW_REQUIRED
  Known URL with changed listed title/date; requires another source review.

OLDER_UNREVIEWED_BACKLOG_NOT_FETCHED
  Unknown URL published before that family's latest reviewed publication date.
  Retained in the directory evidence; not mislabelled as a newly published event.

UNREVIEWED_RELEASE_AT_OR_AFTER_BASELINE
  Unknown URL on or after the latest reviewed publication date.
  Eligible for bounded raw-body acquisition, not automatic acceptance.
```

Publication cutoff is a source-review acquisition policy, not an investment or opportunity threshold. Old releases and revisions may still matter; reviewers can see the backlog, but this first slice does not acquire it automatically. Titles outside target patterns are not silently assigned a metric template. A known URL whose title changes outside the old pattern is still flagged for review.

Every selected body's ArticleTitle and date-only PubDate must corroborate the directory identity. Matching only this metadata cannot confirm the contents, units, period, revisions, authenticity, profitability or economic meaning. The packet remains `PENDING_HUMAN_SOURCE_REVIEW`; no metric parser is applied to unreviewed facts. Disagreement or acquisition failure remains `SOURCE_IDENTITY_OR_TRANSPORT_REVIEW_REQUIRED` and makes the overall run INCOMPLETE.

The packet stores separate directory observation and body acquisition clocks. It makes no historical first-vintage claim. Its stable source-packet identity is URL plus raw-body hash; separate scans retain separate provenance. There is no persistent reviewed/seen cache in this version: an unresolved packet remains review-required on another scan, not automatically approved or suppressed. Accepting a new source into the baseline requires a separate explicit review/change.

## Operational budget

Exactly two fixed directory GETs and at most four selected article GETs, each once. Maximum 100 visible dated rows per directory, 2 MiB per file/body, 20 MiB total archive and 20-second per-request timeout. More than four eligible detail candidates retains the complete plan, fetches none of them and exits INCOMPLETE. It never silently selects a top-four subset. One directory's failure remains visible even if the independent other source can be inspected.

No credentials, cookies, environment proxies, redirect following, retries, browser execution, linked-resource fetching or fallback providers. HTTPError handling retains only a safe numeric code and class; it closes without reading or saving unsafe error payloads. No project dependency or existing capture/workflow/state schema is changed.

## Archive and offline verification

```text
python -m decision_kernel.runtime.economic_release_discovery scan \
  radar_inputs/economic-node-study-2026-09-05.json --output /new/path/discovery

python -m decision_kernel.runtime.economic_release_discovery verify /path/discovery
```

Output must be a new directory outside `decision-state`; existing archives are never overwritten. It contains the exact reviewed baseline, numbered request records, received original bodies/response metadata, a complete result and readable summary, and a content-hashed inventory with implementation hashes. A fatal filesystem/budget/clock error may prevent sealing; an unsealed archive is not accepted as complete.

Verification uses the recorded implementation and performs zero network requests. It checks inventory, file/content hashes, authority, clocks and HTTP metadata; re-extracts the directory rows and exact request plan; rechecks article identity; reconstructs every result and summary byte. Tampering with a result is not legitimized by merely recomputing an outer file hash. Replaying retained errors verifies their recorded evidence, not the original remote failure. Hashes and HTTP records are not independent publisher authentication.

`COMPLETE_BOUNDED_SCAN` means the limited scan and its planned acquisitions completed, not that all publisher releases were found or that pending packets were reviewed. `INCOMPLETE` remains nonzero even if the retained archive is internally consistent. No source success is inferred from a green unit-test run.

SHADOW OBSERVATION ONLY. FUNDAMENTAL STATE AUTHORITY = NONE. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
