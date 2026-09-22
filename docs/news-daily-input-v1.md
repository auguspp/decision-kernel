# Native NewsNow windows in the daily reading

Scope: P1-3 under RM-20260922-r2, #297/5771409745 and preconstruction5772065650.
Reuse Decision: REUSE + THIN_ADAPTER. This is acquisition/reading wiring; it does
not certify economic-event identity, reviewed questions or complete P1 delivery.

## What is connected

`radar-newsnow-daily` uses the existing owned Sector completion event as a clock,
not a price qualification or successful-Sector requirement. It also has a native
manual entry. Both require main and first attempts; no push launcher, new cron,
external scheduler migration or ChatGPT task is introduced. Automatic invocations
can follow an owned main attempt-1 Sector workflow_dispatch even when it failed.
The source job checks successful independent main CI for its actual executing SHA
before acquiring anything. Duplicate/manual calls still require their existing
execution authority; there is no automatic retry.

One ephemeral NewsNow container supplies seven explicitly selected windows:
cls, wallstreetcn, fastbull, jin10, mktnews, gelonghui and thepaper. The image is
pinned to the digest recovered from the accepted September20 probe:
`ghcr.io/ourongxing/newsnow@sha256:98b62bd971d308040937fdfde5263a00715b357894936e88b3ce3c0d8adbf55a`.
It receives no repository, market or model credentials, mounts no repository or
Docker socket, and publishes only a loopback port. Exact source-commit equivalence
to the image has not been independently established.

The capture makes at most seven local-service GETs, no redirects/proxy/retries,
1MiB per body, at most30 items per source, and a12MiB expanded bundle. Service
startup checks are separate from the seven data requests. NewsNow's internal
upstream request count is UNKNOWN, not asserted to be seven. The whole job has a
12-minute cap. Requested/received times, raw bodies or typed absence, image/run
identity and a create-only manifest are retained. Partial acquisition is a
completed finite batch with explicit gaps, not a claim of seven healthy sources.

## Existing owners are reused

`external_radar_observations.news/news_context` still own normalization, domains,
source/id aliases, publication claims, exact-title candidates and company-name
matching. Article versions exclude fetch time; repeated capture does not itself
make a new article/event. Old historical sample configuration and source bytes
are untouched. No article body or a full news archive is promised by a30-item
service window; an empty window is not proof of no news.

The original current-state publisher opts in through `--include-daily-news`.
`news_daily_reading` selects the newest main invocation, binds exact run/artifact,
uses native ZIP verification, replays raw inputs with trusted installed code and
compares the saved projection. It never executes artifact code or searches older
successes after a failure. A36-hour source-age label exposes stale saved windows
without deleting their original dates; it is not publication-time certification.
GitHub/archive/API/output budgets are unchanged.

The same-R company context is associated at reading time, not retroactively at
capture time. Name matches are CONTEXT_ONLY/NOT_FORMED and remain separate from
security/economic verification. Existing company/re-entry paths locate prior
research; title matching cannot launch Pre or amend Belief.

## Reading and acceptance

The new source is `research.daily_news`; details are
`details/radar/news-daily.json` and `.md`, with the original source ZIP retained by
the existing collector. Absent/failed/expired/invalid input is not a quiet result.
Current source windows, historical #467 examples and actual Research are distinct.

Offline regression covers all seven sources, empty/error/invalid windows, clocks,
run/image identity, tampering, source budgets, no redirects, no network in tests,
unchanged article versions, existing native Collector/ZIP composition, company
context gaps, stale/latest-failure handling and preserved old lanes. Tests and
normal publication do not establish a fresh live source run or natural Brief
arrival. Those real receipts belong in #297 after they occur. Economic question
review, relevant full sources and any actual original-Funnel consumption remain
separate acceptance; no new model, paid API, Odds, Watch or investment authority.

Prior art actually inspected: retained artifact10597975192; NewsNow
`newsnext/newsnow@0f95b2c998dffbfd2ddbc51b47b5809887dc6b97`, README and
`server/api/s/index.ts` (MIT); Python urllib.request/ProxyHandler and the existing
_NoRedirect; official GitHub workflow_run/default-branch security and artifacts.
The old probe's permissive clock guesses and fuzzy-title rules are not adopted.
