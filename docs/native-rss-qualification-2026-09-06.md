# Native NBS RSS qualification — 2026-09-06

Status: REAL TWO-FEED BASELINE RETAINED AND REBUILT / NO NATURAL NEW-SOURCE OR CLOUD SUCCESSOR PROOF.

The publisher advertises `https://www.stats.gov.cn/sj/zxfb/rss.xml` and `https://www.stats.gov.cn/sj/sjjd/rss.xml`. Its subscription page verifies source addresses, not our initial size/window assumptions. Implementation reuses feedparser 6.0.14, not a handwritten XML parser, RSSHub proxy or substitute source. `docs/native-rss-source-intake-v0.md` defines the unchanged seen-versus-accepted/delivered boundary.

## Exact implementation and retained attempts

| PR | Head | Merge | Full PR CI | Tests |
| --- | --- | --- | --- | --- |
| #245 | d1782685f9e654f7ab3a1219022d9cbd429f4c24 | f7c3019538a077719e64e68fc637054e735cb035 | 34008765031 / 101420704996 | 1261 / 40.86s |
| #246 | 14c95e1d3e28d9dbaab9cd7fba80942d5e0cd548 | 085910a72e3b18557eec6ed17630e6ccd18b0cbc | 34009031265 / 101421443051 | 1266 / 53.29s |
| #247 | c40940624fe584594d4c12885fe14bf3b62a3426 | 94a7b59256f7aea14fe59021257e711026035fd9 | 34009366055 / 101422349866 | 1269 / 44.77s |
| #248 | 9a78c7ccf7c931a7e53102d7413e1734fbe03978 | 3214853661150a1c5c5f834d6ac4a21162e072db | 34009766970 / 101423424872 | 1274 / 42.72s |
| #249 | d94faf04884b01248f149dd197ecadd5975d3cb6 | f33cde26c7228740b70b95f8299d4399a095512b | 34010170369 / 101424477737 | 1276 / 45.45s |

All five first PR CIs passed; 57 tests were added over the starting 1219. Full tests and production-library reconstruction ran in Actions. Local syntax/identity checks and independent downloaded-file/XML/DOM inspection are not a full local repository execution or browser acceptance. PR #249 main CI 34010252506 test 101424695333 and the unrelated existing Timeline job 101424804771 completed successfully. See the documentation PR for its later exact head/merge/full CI; documentation does not trigger another source call.

| Source run / attempt | Code PR | Artifact | ZIP bytes | ZIP SHA-256 | Result |
| --- | --- | --- | --- | --- | --- |
| 34008846022 / 1 | #245 | 9981816666 | 1681 | 83216a92014fe4a76d931dfd6e5c422cd4d08b9b0622aed4c8102c17995615c9 | one attempt, no raw XML or registry |
| 34009113645 / 1 | #246 | 9981901578 | 1679 | bcaacdded98427f8ab862df17933a90d2b52473007fb59005c51a8dfb8a9c812 | one attempt, no raw XML or registry |
| 34009539824 / 1 | #247 | 9982025063 | 1899 | 21b01f73da28346255f8d932f95574f080834bbc90d63b54e44bbfd363b59993 | one attempt, explicit declared-size refusal |
| 34009868992 / 1 | #248 | 9982131423 | 2416913 | fa3765069f8d2f7e520f193dfe3aea28fe1f7dc48b825f52994f3b775877760a | two complete XML bodies, no qualified registry |
| 34010252507 / 1 | #249 | 9982240741 | 3086278 | 029e72aaa55dea0f0c720aae50ed96e72a3893745da5076729408a4745daabff | two complete XML bodies and initial baseline |

Each run used the explicitly reviewed runtime-change compatibility trigger, one attempt per feed and no Re-run jobs, fallback or alternate source. Total seven request attempts. The first two have unknown HTTP status; do not call all seven HTTP200. None fetched linked articles, MOA/SPB directories, company PDFs or market data. The old directory job was skipped throughout.

## Failures remain failures, not provider faults

The first two attempts recorded plain ValueError before a PublicResponse returned. HTTP status, headers and body were unavailable. They do not independently establish HTTP403, invalid XML or an outage. Initial diagnostics were insufficient and caused avoidable additional trials; this is an implementation shortcoming, not an upstream economic-data fault.

The third retained HTTP200, Content-Type text/xml, declared Content-Length 4207576, and `DECLARED_BODY_BYTE_BUDGET_EXCEEDED`. Request 03:39:37.065223Z, refusal 03:39:40.850478Z; program origin was fetch_feed's declared-length guard. Body was NOT read, hashed or parsed. Server Date/Last-Modified are server claims, not publication/freshness proof. These three failed four-file artifacts and their retained-byte verification/nonzero status remain unchanged.

PR #248 disclosed an RSS-only capacity increase from 2 MiB to 8 MiB per body, at most 16 MiB for two feeds. The economic HTML helper's 2 MiB limit was not changed. That run retained both full HTTP200 XML responses, then source qualification still failed. Independent secure lxml inspection of the saved originals found RSS2 and exactly 500 entries per feed, necessarily above the old 128-item bound. It did not run the production feedparser/module locally.

PR #249 separately changed only entry capacity to 512 and bound it in the policy hash. It does NOT take the first 512 of a larger feed. Individual/aggregate text, 4096-version, 6 MiB registry, 32-source handoff and three-theme bounds remain. Both adjustments were explicit resource reviews, not claims of unchanged budgets. Prior receipts require their original implementation; no successful live source registry was silently reset. No dates, MIME/encoding, source identities or semantic rules were relaxed.

## First real baseline — run 34010252507

Exact code f33cde26c7228740b70b95f8299d4399a095512b, source job 101424695475: capture, original-byte rebuild, upload and Summary all succeeded. Previous-run validation/download steps were skipped because this was an explicit baseline; no live cloud restoration claim follows. The old HTML directory job 101424696023 was skipped.

| Feed | Downloaded bytes | SHA-256 | Entries | Claimed first / last publication strings |
| --- | --- | --- | --- | --- |
| interpretations | 4207576 | fe3ae9d0be74205617f64d1e75d5ac8f242e7ec2f94754f91c58feb0b6c9c4fc | 500 | 2026-08-31 09:30:00 / 2023-04-19 10:15:00 |
| latest releases | 4496148 | b15a457fffcba22c65104d35e1c2dfa9021c6c8ec1b47034c153a152c3db12e7 | 500 | 2026-09-04 09:30:00 / 2024-03-18 10:00:06 |

Both bodies are byte-identical to those preserved by #248; this is not evidence of naturally arriving new content or a new XML vintage. All 1000 exact article URLs are distinct and fit the declared profile. There are 1000 stored feed versions, zero duplicate appearances in THIS baseline and no simultaneous variant conflicts. This is not 1000 independent forecasts, a publisher-wide history or a claim of economic novelty.

The complete source registry was first recorded at **2026-09-06T03:57:44.770055+00:00**. Status is `INITIAL_BASELINE_ONLY`; `source-rows.json` is exactly `BASELINE_NOT_FORWARDED` with empty sources/gaps. Baseline does not backfill a prospective corpus.

```
capture_hash = 77f8e2f883a6492df0a33c3becf5575db395b384153942c539ed7dbe77d7177e
registry_hash = 413b40515eed27364adc362b5cff460355f0ae8e2c21b87c85e6485078a4b80b
delta_hash = 2e9a8cb5780784a045038de825dde40332cc2186a3090c8a93c8634afbaff9bb
policy_hash = 168fa769768b8e9f9b873db52fc77daffa4e7b1016aab87face6e0fd30689624
```

**Every one of the 1000 publication strings lacks a timezone.** They are retained literally, not promoted to Evidence.published_at with inferred Beijing time or parser-assigned UTC. If subsequent entries retain this format, the existing Evidence export remains blocked until a separate time contract is qualified. Baseline success is therefore source acquisition/registration proof, not complete publication-PIT or feed-to-theme execution.

Independent local checks verified all 10 ZIP paths, all 6 inventoried body/result files, outer ZIP and capture/registry/delta hashes, exact workflow identity, sequential request/record clocks, Content-Length equality, all 1000 raw URL/title/date-to-registry relationships, and every document/version hash. The parser strips outer whitespace from all 1000 descriptions: each stored description was checked against raw description.strip(), while raw XML remains unchanged. Do not call parsed descriptions byte-identical original quotations. Basic Beautiful Soup DOM checks found all 1000 sections/links and no script; no visual browser, phone or hosted-site test was performed.

Actions returned `ORIGINAL_FEEDS_REGISTRY_AND_PAGE_REBUILT`, with zero network calls in the verifier. It rebuilt from raw RSS, not merely trusted derived hashes. Open `capture/index.html` in the downloaded `radar-feed-intake-34010252507-1` artifact. It retains 90 days, expiring **2026-12-05T03:56:46Z**. Preservation of exact originals/code outside expiring Actions storage remains necessary for long-term recovery.

## Remaining gates and authority

Cross-run dedup, unchanged/late/changed sources and stable pending IDs are implemented and synthetically tested. Exact predecessor artifact download and full reconstruction are wired into manual execution but not proven by this baseline. No auto latest-success lookup, consumer acknowledgment, schedule, naturally arriving new-source observation or qualified timezone-less Evidence export exists. Do not re-run this unchanged baseline to manufacture those proofs. The next task is an explicit successor and a qualified source-time/description handoff, not another generic parser or fixed-source repeated sample.

No Sector market/cache/ledger/rank/threshold/company-judgment changes, Human Decision/Action, Research route or canonical wake were introduced. The new registry is upstream source seen-version state only. Human / Research / Investment / signal-transition authority remains NONE. The normal Sector direct-next-session append and joint reading-page proof remain separate pending milestones.
