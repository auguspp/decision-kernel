# Radar reuse decision — 2026-09-05

Status: REUSE EXISTING LIBRARIES AND OFFICIAL ENTRY POINTS / NOT A NEW CRAWLER FRAMEWORK.

The Human explicitly prefers mature components to additional bespoke infrastructure. The previous discovery slice implemented two HTMLParser subclasses for list traversal and article metadata. That is generic tree-navigation work; this change deletes those classes and uses Beautiful Soup instead. Source identity, time/version lineage, acquisition bounds, review disposition and authority remain application contracts, not features to delegate to a library or an LLM.

## Selected implementation

- `beautifulsoup4==4.14.3`, MIT licensed, in optional `.[discovery]` and CI `.[dev]`, not base Kernel dependencies. The explicit `html.parser` builder is supported by Beautiful Soup; no parser auto-selection or encoding guessing.
- This pin is a reproducible tested version, not a claim to use the newest release. PyPI lists 4.15.0 as the latest release on the review date. Upgrading the pin requires compatibility tests and new parser-runtime lineage.
- Beautiful Soup supplies DOM construction, tree traversal, text/entity handling and source line/column positions. Its documented duplicate-attribute callback rejects ambiguity. No replacement HTML tokenizer, crawler scheduler, cache, browser renderer, retry manager or feed database is added.
- Existing bounded standard-library HTTP acquisition remains; changing it merely to add another HTTP wrapper would not solve the current coverage problem.
- Schema 2 records the library version, explicit builder and exact Python version, and verifies that environment before replay. Old schema-1 archives must use the old recorded implementation; they are not migrated or re-labelled.

Malformed outer HTML may be repaired by the mature parser. This is not a claim of identical syntax acceptance to the deleted event parser. Evidence checks still require one allowed URL, one explicit full date from the same list row, no nested/ambiguous article links, unique metadata, and exact directory/detail identity. Scripts, styles, templates and noscript content cannot supply evidence. A base element is rejected. Data-quality failures remain failures.

## Upstream review: use what matches, do not confuse names with contracts

| Component | Evidence inspected | Decision for this slice |
| --- | --- | --- |
| Beautiful Soup | Official traversal, source-location, parser-selection and duplicate-attribute APIs | Adopt; remove custom parser classes rather than wrap them in another framework. |
| RSSHub | Repository and MOA routes; exact-host searches for `xmsyj.moa.gov.cn` and `spb.gov.cn` returned no match in this review | Retain as first candidate for future multi-feed discovery. No exact route was confirmed; this is not a claim none can ever exist. A transformed RSS item would be discovery input, not original official HTTP evidence. Do not deploy a service or hand-write a feed platform for two pages. |
| AKShare | `macro_china_postal_telecommunicational` in `akshare/economic/macro_china.py`, inspected commit `8e95744b79ae22326308ccd2b4e62650c5b53c55` | Existing postal-series interface uses Sina macro data, not these exact SPB release bodies or first-vintage records. Keep it as a separately qualified research candidate, not a silent substitute for original source evidence. |
| Scrapy | Official overview: selectors, crawling, pipelines and feed export | Appropriate when a multi-site crawl actually needs those features. Not deployed for the current maximum two-directory/four-detail sequential pass. Reassess before writing queues, pagination orchestration, rate-control or crawl persistence ourselves. |
| Official SPB statistics page | `https://www.spb.gov.cn/gjyzj/c100275/pubtz.shtml`, indexed as statistics and containing monthly report links | Replace the crowded news homepage with this explicit statistics-window qualification target. Do not add a home-built news pagination engine. Original bytes, row metadata and the reviewed boundary must be checked in the controlled probe before calling coverage improved. |

The new SPB directory is from the same official publisher and still routes to the exact existing article family. It is not fallback. No old reviewed URL/date or baseline is changed to force a new item. No result from search indexing is substituted for raw HTTP bytes. If the statistics page lacks qualified rows, retain INCOMPLETE; do not invent dates or fall back to the old news page.

## Boundaries and next gate

Existing request budgets, one-attempt rule, no redirects/credentials/cookies, pending-only review packets, lack of complete-publisher coverage, no baseline acceptance and no market/event/Research write remain. The existing discovery workflow installs the extra; its triggers and budgets are unchanged. No new workflow or schedule is added.

The implementation merge intentionally causes one controlled compatibility scan of MOA monitoring and the new SPB statistics page. A new live source proof is not inferred from CI. If the result is quiet, it does not establish natural new-detail acquisition. If the result is incomplete, inspect original evidence before changing anything; do not repeat until green.

Future work should follow this order: exact official structured data or feed; maintained source-specific adapter; mature generic library with thin source configuration; bespoke code only for a documented missing application contract. In particular, Parquet reading should reuse PyArrow/DuckDB, RSS/Atom parsing should reuse feedparser or a maintained feed service, and broader crawling should reuse a crawler rather than extending this module into one. Each requires its own need/version/license/source review; none is installed merely by being listed here.

## Primary references reviewed

- https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- https://pypi.org/project/beautifulsoup4/
- https://github.com/DIYgod/RSSHub/tree/master/lib/routes/gov/moa
- https://github.com/akfamily/akshare/blob/8e95744b79ae22326308ccd2b4e62650c5b53c55/akshare/economic/macro_china.py
- https://docs.scrapy.org/en/latest/intro/overview.html
- https://www.spb.gov.cn/gjyzj/c100275/pubtz.shtml

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
