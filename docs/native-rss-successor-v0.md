# Native RSS: explicit successor qualification

Status: IMPLEMENTATION AND REVIEWED RUN REQUEST / REAL SUCCESSOR RESULT MUST BE CHECKED SEPARATELY.

## What this slice does

Reuse `radar_feed_intake` unchanged, its feedparser 6.0.14 parser, original-byte verifier, exact version registry and the existing `economic-release-discovery` workflow. The new workflow-only helper binds the selected predecessor to GitHub's run/artifact metadata and the downloaded original capture before either public feed request. No new feed parser, queue, Kernel model, source acceptance or market execution is introduced.

The existing runtime-file push trigger formerly initialized a separate baseline on every implementation change. It is removed. A push now acts only on `radar_inputs/native-rss-successor-request.json`, an explicit reviewed continuation request containing the exact predecessor run, commit, artifact ID/ZIP digest and source capture/registry hashes. It cannot request initialization. Changing runtime, scripts, workflow or documentation alone does not make public-source calls. Manual source-kind, explicit bootstrap and explicit previous-run-id remain available; manual inputs do not silently inherit the committed request. No schedule, latest-success lookup, cache, permanent pointer or auto-acknowledgment exists.

The request is operational intent recorded in Git, not a source or signal ledger. Reusing a predecessor creates an explicitly selected branch of observations, not proof of continuous monitoring. Operators must select the intended last qualified successor for the next operation; the file does not automatically advance. Registry dedup makes an unchanged window quiet, but does not claim exactly-once transport or natural new content. No current/initial state is overwritten.

## Exact preflight and retained identity

1. Require the canonical repository/workflow/main, numeric run IDs, exact commit SHA and fresh attempt. Resolve manual input or the whole committed request; no incomplete implicit baseline.
2. Reuse GitHub CLI GET for that run and its artifact listing. Require completed success, same repository/workflow/main/attempt, one exact artifact, unexpired identity and a server SHA-256. Verify declared pins, where supplied. No substitute or most-recent artifact selection.
3. Reuse official `actions/download-artifact@v8` with exact artifact ID/run and `digest-mismatch: error`.
4. Run the unchanged full feed-capture verifier. Bind capture workflow, commit, run, LIVE provenance and capture/registry hashes to the predecessor metadata/request. Require predecessor finished before this invocation; check this BEFORE public requests, not only in the later registry transition.
5. Only then call the original capture CLI with `--previous`, followed by the original offline verifier. Unchanged RSS is valid `NO_NEW_FEED_VERSIONS`; any new/changed representation remains subject to existing pending/date/text constraints.

`preflight.json`, `predecessor-run.json`, `predecessor-artifacts.json`, `predecessor-binding.json` and `predecessor-verification.json` sit outside the sealed child `capture/`. They bind the invocation, not Human review or delivery acceptance. The child retains the prior registry and parent capture hash using the old schema; it does not embed every ancestor's raw XML. Source policy and old bundle byte identities remain unchanged. Full-chain archival still requires preserving original artifacts and code before their 90-day expiration; a hash cannot recover expired content.

The initial request explicitly pins baseline run 34010252507, artifact 9982240741, code f33cde26c7228740b70b95f8299d4399a095512b. Its merge intentionally requests ONE real two-feed successor, not a repeat initialization. No linked articles, company PDFs, old MOA/SPB directories or HiThink requests are part of this operation. The outcome is not assumed before inspecting the run.

## Publication-time review — still unresolved

Checked on 2026-09-06:
- Publisher RSS subscription: https://www.stats.gov.cn/wzgl/rss/202302/t20230217_1912859.html
- Official 2026 release calendar: https://www.stats.gov.cn/sj/fbrc/bnxxfb/
- Bounded searches of official `stats.gov.cn` pages for RSS publication time/timezone and Beijing-time conventions.

The subscription page establishes the two feed addresses, not a timezone contract for `pubDate`. The release calendar lists planned dates/times and expressly allows adjustment; it is not proof of the actual publication instant or a universal RSS-field timezone. The checked material does not provide enough evidence to assign +08:00 or UTC to the unzoned RSS strings. This is a limited negative finding, not proof that no such specification exists anywhere.

Do not transfer timezone statements about procurement deadlines, census reference times, a browser locale, HTTP Date/Last-Modified, country convention, or another endpoint into this RSS field. No automatic timezone default, inferred midnight, first-received-as-publication or change to EvidenceArtifact is made. Original strings and source first-received clocks stay distinct. A successful restored successor can prove exact continuity/dedup even while publication-time Evidence export remains unqualified. It cannot demonstrate natural new-source arrival unless the saved originals actually change.

## Acceptance and remaining work

Synthetic tests run actual feedparser, baseline capture, remote-binding checks, successor capture and original reconstruction with only the transport replaced. They require unchanged baseline versions/first clocks, explicit parent linkage and no source rows; reject wrong run/commit/artifact/digest, expiration, incomplete artifact listing, changed original bytes, synthetic-to-live restoration and future predecessor clocks. They test manual versus push intent and failure before new requests. None is a real cloud restore or a natural-source proof.

This helper adds no automatic consumer acknowledgment, source-to-theme forwarding, broad news coverage, forecast independence, economic fact acceptance, portfolio/action or third canonical wake. Sector direct-next-session append and joint-page production acceptance remain independent milestones. Human / Research / Investment / signal-transition authority remains NONE.
