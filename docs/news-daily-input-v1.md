# Native NewsNow windows in the daily reading

Original scope: P1-3 under RM-20260922-r2, #297/5771409745 and
preconstruction5772065650. The 2026-10-01 Human-approved successor is implemented
in [PR #689](https://github.com/auguspp/decision-kernel/pull/689): ten-minute
acquisition, rolling overnight history and low-frequency publication. This is
source/reading wiring, not verified economic events, Research or investment authority.

## Cadence and existing owners

`radar-newsnow-daily` retains its owned Sector-completion and native manual entries
and adds `3/10 * * * *` (144 scheduled opportunities/day). News therefore no longer
requires an A-share Sector run to get an overnight acquisition opportunity. The
schedule is best effort, not a ten-minute delivery SLA; GitHub may delay or omit
scheduled work. Native concurrency does not cancel an active capture; no retry,
external scheduler, polling Agent or new ChatGPT task is introduced.

Every path still requires owned main, attempt 1 and successful independent main CI
for the actual executing code before source calls. Source permissions remain
contents/actions read. Exact Site request/code/next-run-number checks remain;
updating the backend workflow fingerprint is not deployment of the Site handler.
The original Site and its pause/deployment/permission checks are separate.

The original `current-state-read-entry` publisher excludes high-frequency scheduled
News events. It retains existing event/manual publication and adds two read-only
publication opportunities, 07:50 and 19:10 Asia/Shanghai (`50 23 * * *` and
`10 11 * * *` UTC). These schedules also require successful exact-code main CI.
No producer is dispatched by this publisher. Publication/start delays remain visible;
the Human's weekday 08:00 morning task and evening/Quick schedules are not changed.

## Source acquisition and custody

One ephemeral container supplies the existing seven windows: cls, wallstreetcn,
fastbull, jin10, mktnews, gelonghui and thepaper. The image remains pinned:
`ghcr.io/ourongxing/newsnow@sha256:98b62bd971d308040937fdfde5263a00715b357894936e88b3ce3c0d8adbf55a`.
It receives no repository, market or model credentials, mounts no repository or
Docker socket and exposes only a loopback port. Exact source-commit equivalence
to this image has not been independently established; no upstream upgrade is implied.

The finite batch still makes at most seven local-service GETs, without proxy,
redirects or retries: 1 MiB per response, at most 30 items per source and a 12 MiB
expanded bundle. Service startup checks are separate. NewsNow's actual upstream
request count remains UNKNOWN, not asserted to be seven. The job cap is 12 minutes.
Requested/received times, original bodies or typed absence, image/run identity and
create-only manifests remain retained. Partial acquisition does not certify seven
healthy sources or complete news coverage. Scheduled artifacts retain three days;
manual and original event-driven artifacts keep thirty days.

## Bounded rolling history and honest gaps

Reuse `external_radar_observations.news/news_context` for source/URL identity,
publication claims and article versions. The native `news_rolling` consumer retains
an 18-hour derived index, capped at 2,000 observations, 120 capture summaries and
2 MiB; the original 12 MiB total capture limit is not enlarged.

The original `version_id` deduplicates identical captures. Revisions remain separate
versions; title similarity does not certify common economic-event identity.
`first_seen_at` is the earliest fetch retained in this chain, not original publication
time or a global first-ever observation. The original observation and its publication
claims remain unchanged when repeated; last-seen time/run/count are separate.
Eviction or a broken chain limits any first-seen interpretation.

Before starting the source container, `news_history_recovery` uses the existing
GitHub transport, artifact selection and native ZIP/digest/identity verifier. It
inspects at most twenty run records and one selected successful predecessor archive,
within five GitHub calls. Current/latest-prior attempt, selected predecessor,
newer unsuccessful attempts, artifact identity and recovery failure remain explicit.
If that selected archive is corrupt/expired/unavailable, it does not search older
archives until one passes. A legacy capture can bootstrap one saved window.

Each new archive binds the exact preceding `history-input.json` and
`history-recovery.json` into its manifest and writes the derived `history.json`
under `native-newsnow-rolling-v2`. The reader replays current raw HTTP and the last
history transition. Earlier entries are inherited native-producer index data;
this is not a claim to have re-read every historical HTTP response this round.

Invalid history, missing/empty/oversized optional files and malformed recovery
input yield an explicit predecessor gap without preventing the current seven-source
attempt. Optional reads remain bounded; arbitrary exception text is not published.
Fresh raw windows and their normalized result are retained before writing history.
Actual output/identity/source-bound failures remain failures, not retry permission.

Observation/capture truncation and recovery losses persist while they can affect
the rolling window. A later successful capture does not erase them. Drop counts
mean retained loss operations, not distinct articles. The mathematical target start,
actual chain start, source-gap captures and maximum acquisition interval are separate;
bootstrap is not a completed 18-hour window. None of these fields asserts exhaustive
upstream coverage, and an empty latest window never means no news.

## Normal reading and morning/evening consumption

The normal source remains `research.daily_news`, with same-R
`details/radar/news-daily.json` and `.md` plus the original native ZIP copy. A failed
or unfinished latest attempt stays visible; the newest earlier successful run in
the bounded page may supply retained history, selected once before byte verification.
Failure of the selected archive remains a local News gap; it is not permission to
hunt for a different green archive or erase unrelated lanes.

Capture age is exposed in seconds, with a thirty-minute stale threshold replacing
the original daily reader's thirty-six-hour threshold. Neither this label nor a new
R certifies upstream publication freshness. Company-name association remains scoped
to the current capture, not advertised as whole-history economic mapping.

Morning consumption compares the actual prior Brief body/cutoff and source dates;
Quick cutoff or task scheduled time does not replace that evidence. Late-obtained
old material is a supplement, not a new overnight event. Known Research validation
windows and missing results remain responsibilities of the Research/agenda/Brief
consumer, not an automatic News-to-Research scheduler. No company filing text,
single-stock post-earnings quote or complete US-market coverage is created merely
by raising the NewsNow frequency.

## Reuse, acceptance and exit

Reuse Decision: **REUSE + THIN_ADAPTER**. Internal reuse is the existing NewsNow
normalizers, native GitHub transport/ZIP/custody and current-state publisher. Official
GitHub Actions supplies cadence and concurrency. Retained external review starts at
#508/5773538785 (NewsNow supplier), #508/5773258951 (cadence versus interruption)
and #511/5854823445 (reuse retrieval order); no new supplier, database, crawler,
provider framework, model or paid API is installed.

The unchanged supplier's historical code-level review is retained artifact10597975192
and `newsnext/newsnow@0f95b2c998dffbfd2ddbc51b47b5809887dc6b97`, README and
`server/api/s/index.ts` (MIT), together with Python urllib and official GitHub
workflow/artifact contracts. This is not a claim of a new source/image equivalence
or a fresh audit of an upstream branch that could not be recovered.

Offline regressions cover lost-window retention, version deduplication and revisions,
persistent truncation, recovery byte/clock/identity failures, optional input isolation,
legacy versus missing-declared-history distinction and actual workflow admission.
Formal full CI, exact main qualification, browser contract checks, normal publication,
natural ten-minute capture/inheritance and real next-Brief consumption are separate
acceptances in PR #689/#297. Do not turn synthetic cases into natural delivery proof.

If this cadence is retired, remove the two new scheduling seams and their dedicated
contracts through a normal change, retaining historical source bytes and compatible
readers. No force-push, erased failures, inferred Human acceptance, automatic Full,
Odds recalculation, Watch activation or investment action is part of this change.
