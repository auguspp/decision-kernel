# Native NewsNow windows in the daily reading

Scope: P1-3 under RM-20260922-r2, #297/5771409745 and preconstruction5772065650.
Reuse Decision: REUSE + THIN_ADAPTER. This is acquisition/reading wiring; it does
not certify economic-event identity, reviewed questions or complete P1 delivery.

## What is connected

`radar-newsnow-daily` keeps the existing owned Sector-completion and native manual
entries and adds a GitHub-native ten-minute schedule (`3/10 * * * *`). This is a
bounded source cadence, not a five/ten-minute delivery SLA: GitHub may delay scheduled
runs, concurrency does not cancel an in-progress capture, and there is no automatic
retry. All paths still require current main, attempt 1 and successful independent main
CI for the actual executing SHA before source acquisition. The schedule changes source
freshness only; it does not create Research, Human attention or investment authority.

Each qualified capture tries to recover the immediately prior successful News artifact
and, when its rolling-history contract is present and valid, carries forward a bounded
18-hour derived index. Articles are deduplicated by the existing `version_id`; the
index records capture `first_seen_at` / `last_seen_at`, not publisher-certified
publication time. It is capped at 2,000 observations, 120 capture summaries and 2 MiB;
older observations may be explicitly dropped rather than silently expanding the
existing 12 MiB capture bundle. Missing/invalid predecessor history starts a new chain
and is not rewritten as a quiet-news claim. The original per-run raw source attempt is
still retained separately.

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
`news_daily_reading` binds an exact run/artifact, uses native ZIP verification,
replays the current raw inputs with trusted installed code and validates the derived
rolling index. A failed latest high-frequency attempt stays visible; within the bounded
20-run query the reader may retain the newest prior qualified rolling capture instead
of erasing the whole overnight window. This is an explicit last-qualified source state,
not a claim that the failed run succeeded or that no news occurred.

High-frequency scheduled News runs do **not** each publish `read-model/current-state`.
The existing publisher keeps manual/owned event-driven behavior, while two low-frequency
read-only publication schedules (07:50 and 19:10 Asia/Shanghai) consume the latest
qualified rolling capture for the morning/evening delivery seams. A36-hour source-age
label still exposes stale saved windows without deleting original dates; neither a new
read-model commit nor the rolling first-seen clock certifies publisher publication time.
Scheduled high-frequency artifacts use a shorter three-day retention; manual and
existing event-driven captures retain the prior 30-day setting. Source request/body and
12 MiB per-capture bundle budgets remain unchanged.

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
unchanged article versions, rolling first/last-seen dedupe, predecessor corruption,
bounded truncation, existing native Collector/ZIP composition, company-context gaps,
stale/latest-failure handling and preserved old lanes. Workflow-contract tests pin the
ten-minute source schedule and the two low-frequency publication times. Tests and
normal publication do not establish a fresh live source run, continuous upstream
coverage or natural Brief arrival. Those real receipts belong in #297 after they occur.
Economic question review, relevant full sources and any actual Research consumption
remain separate acceptance; no new model, paid API, Odds, Watch or investment authority.

Prior art actually inspected: retained artifact10597975192; NewsNow
`newsnext/newsnow@0f95b2c998dffbfd2ddbc51b47b5809887dc6b97`, README and
`server/api/s/index.ts` (MIT); Python urllib.request/ProxyHandler and the existing
_NoRedirect; official GitHub workflow_run/default-branch security and artifacts.
The old probe's permissive clock guesses and fuzzy-title rules are not adopted.

## 2026-10-01 Reuse / premise reconciliation

Human identified a real morning-delivery miss: material overnight news could fall outside the last 30-item window, and a pre-registered Micron earnings validation window was not surfaced. The adopted product premise is now morning-as-delta from the prior evening delivery, not a replay of the prior Brief. Affected consumers are the News capture/reader and the read-model publication cadence; Research validation-window checking remains in the morning-delivery instructions and is not converted into a News source responsibility.

Reuse Check: internal existing NewsNow adapter, original normalizers, artifact verifier, GitHub Actions and current-state publisher are reused; official GitHub Actions supports a minimum five-minute scheduled interval but does not guarantee exact start time; retained #508 registers NewsNow as the specialized News supplier and #511 adds no better overlapping acquisition primitive. Current upstream NewsNow remains MIT and continues to expose source-oriented real-time windows; no external code or new dependency is copied. **Reuse Decision: REUSE + THIN_ADAPTER.**
