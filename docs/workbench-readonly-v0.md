# Workbench read-only v0.1 — one 0a/0b → A1 development slice

2026-09-26. Product owner #351; architecture owner #508. The current construction
plan remains [NEXT-PHASE-CONSTRUCTION](NEXT-PHASE-CONSTRUCTION.md).
Authorization: [#297/5836374143](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5836374143).
The user now explicitly assigns Sites interaction to their own Sites-enabled session.
Use the [Sites handoff](workbench-sites-handoff-v0.md) for that bounded task.
This document supersedes the initial development description, not its retained history.

## Adopted choices and scope

Keep the public single repository now; credentials and content without publication
rights remain excluded. Sites is the preferred replaceable host. GitHub remains
the formal backend. No added recurring spend; existing authorizations are preserved.
Weekday 08:00 Beijing morning delivery and existing evening delivery remain as
previously accepted; this consumer does not create or alter tasks.
H5 is approved: same main integration line, capability-sized PRs, normal CI and
rollback. No long-lived v2, direct/force push to main, or premature activation.
R5 natural observation and new feature verification are separate.

## Ownership / reuse

- KEEP existing current_state validators, publishers, archives, purpose registry,
  Research/corrections, explicit Human records and saved Watch. The browser is not
  a producer, truth validator or second canonical store.
- REUSE the retained asset-reentry company projection rather than matching stock
  names or inventing holdings. Preserve its original notes and acceptance boundary.
- THIN_ADAPTER: browser-native ES modules, Fetch, Web Crypto, Node built-in tests.
  No package, server, database, scheduler, dynamic plugin or market/model call.
- Independent Quick #575 and health #581 keep their own modification/read clocks.
  Finding a link, reading bytes, accepting Research and making a decision differ.
- Existing Luna recovery@6e3a281 and gptme portable-apps@2d94902 review supplies exact
  state/ownership, thin runtime wrappers and upgrade-preservation principles.
  No upstream runtime/code installation; no new blanket prior-art audit claimed.
- Current official Sites preview/deploy/access and GitHub comment API review,
  precise internal source observations and successor acceptance are in the handoff.

## Read contract

Each explicit refresh resolves `read-model/current-state` once, then uses only
that exact R for package and source reads. Current-state has its original 192 KiB
bound. Root shape/authority checks do not recompute canonical reading_hash or
prove the complete manifest. Selected UTF-8 text is bounded to 512 KiB and checked
against its declared length and SHA-256 before display. Files render as text,
never remote HTML/scripts; ZIPs remain links, not executable or extracted content.

Repeated source locators retain all category locations. Research cannot disappear
merely because the same file was first encountered under another lane.
`readAssets()` loads only the registered `details/research/asset-reentry.json`,
checks its bytes and actual company envelope, and checks all nested descriptors
before expanding the same-R read allowlist. No arbitrary caller-supplied endpoint
or partial failed expansion. Its promise is shared within that one reading.
The projection's base_reading_hash is historical metadata, not required to equal
the final package reading_hash after other attachments; neither is certified here.

Quick reads at most two recent pages. Main-result headings and nonmatching records
remain separate; the latter can contain late supplements, corrections or engineering
notes, without being automatically classified as new Research. All returned rows
need correct IDs, URLs and explicit-zone ordered times; duplicate IDs fail. Records
are ordered by modification time, which is NOT economic event time or proof of
supersession. Bounded pages cannot establish all-history or today's completeness.

Watch counts distinguish enabled, actually evaluated in the saved result, triggered,
unknown and inactive. Missing prices, condition results or clocks cannot become
"not triggered". No price-distance arithmetic or configurable entry thresholds.
Company search uses explicit thscode, any retained Watch name and asset purpose.
The catalogue is not a portfolio and does not select a final accepted version.

Views have independent display toggles and isolated read errors. Refresh replaces
memory-only state; slow old detail/catalogue responses cannot replace a new reading.
No automatic polling, localStorage, IndexedDB, credentials or writes. Copying a
resume request does not execute it, save a response or commission Full.
Learning is still existing retention/reentry, not L1 measured later improvement.

## Verification / remaining work

From repository root:

```sh
node --test workbench/reading.test.mjs
python -m pytest tests/test_workbench_web.py
python -m http.server 8765 --bind 127.0.0.1
# In a permitted browser environment: http://127.0.0.1:8765/workbench/
```

Node >=20 is a declared test prerequisite; missing Node fails, not skips. One
existing pytest wrapper runs all JS contracts and app/reading syntax checks in
normal CI. Presentation is imported by the tested code. No new workflow or gate.
Tests are synthetic transport except one explicitly retained exact-byte archive
fixture; even that test's package envelope is synthetic. It is not whole-R replay.
Exact local/remote test counts and run identity belong to the current PR receipt.

This session has no native Sites tool. The earlier browser administrative denial
remains a historical limitation; it was not retried or bypassed here. Container
source download again failed DNS, while the authorized GitHub connector worked.
No browser screenshot, live HTTP/CORS, site preview, deployment, hosted refresh or
hosted identity result is claimed. The user performs permitted Sites checks using
the handoff. Code/read tests, host acceptance, full merge CI and main publication
are separate deliverables. Keep PR Draft pending the actual host checks and full CI.
A1 curated Attention/complete object navigation, A2 actual response and personal
context, L1 natural adoption, and B global/calendar coverage are not complete.

## Exit

Remove the optional workbench directory, its dedicated pytest wrapper/JS tests
and handoff together when no longer consumed. Existing shared tests, producers,
Research, Odds and Human history are untouched. Host adaptations return as a diff
for this PR, not an untracked business-state fork. Use normal PR rollback and keep
historical failures/observations. No unrelated R5 observation reset.
