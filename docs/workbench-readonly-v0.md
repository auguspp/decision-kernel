# Workbench read-only v0 — 0a/0b → A1 development slice

2026-09-26. Engineering scope, not Research acceptance or production deployment.
Authority: [#297/5836374143](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5836374143).
Plan: [NEXT-PHASE-CONSTRUCTION](NEXT-PHASE-CONSTRUCTION.md). Product owner #351; architecture owner #508.

## Accepted execution choices

H1: retain the existing public single repository now; no private-repository split as a prerequisite. Credentials and content not authorized for publication remain excluded. Future privacy migration is a later decision, not a claim that public copies can be recalled.
H2: Sites is the preferred host to validate, not already provisioned or deployed. GitHub remains the canonical research/decision backend.
H3: zero additional recurring spend; prior authorizations are not revoked.
H4: weekday 08:00 Beijing morning delivery, existing evening delivery retained; the morning input/consumption acceptance condition remains. This slice neither creates nor modifies tasks.
H5: Human expressly approved starting work. Continue against the existing main line with normal PR/CI. Batch around a useful capability and common rollback boundary, not one menu/file/line-count per PR. No long-lived parallel v2, no direct push/force-push to main, no premature production activation. R5 observation continues independently.

## Ownership and reuse decisions

| Boundary | Owner / actual source | Decision |
|---|---|---|
| Saved observation identity, qualifiers and reading hash | `runtime/current_state.py`, existing publisher and `read-model/current-state` | KEEP. Do not reconstruct or weaken producer validators in the browser. |
| Research originals, corrections, accepted scope | Existing purpose registry/archives; hosted comments at #575 | KEEP. The page locates existing bodies, it does not generate new Research or choose a canonical conclusion. |
| Saved price conditions | Existing Inbox `last_qualified_result.odds_watch.report.watch` | REUSE as historical display, no recalculation, inferred holdings, new Watch or trading. |
| Independent delivery-health observation | #581 current body plus its own updated/observed time | REUSE; never pretend the issue is included in R. |
| Web presentation and transport | `workbench/reading.mjs`, `app.mjs`, `index.html` | THIN_ADAPTER over existing public endpoints; browser-native modules and read-only controls. No new backend/DB/provider/scheduler/framework. |
| Private data, writes and hosted publishing | Not owned by this browser preview | DEFER to an explicit actual host/auth validation. Current public repo choice does not authorize anonymous writes. |
| Learning | Existing methods, correction trail and referenced case assets | KEEP. Resume text returns to the current Research entry/corrections. Not L1 real adoption or learning-effect acceptance. |

Internal inspection at M `c847b4ad6fefa4b5d3c02536b4d02866a7c92258`: AGENTS, versioned construction plan, CI-MAINLINE retained contract, #297, current_state.py native read/ref/hash/path contract, and saved R `3c4818dc9ad7a068febb6889f53bf2546dccfeea` current-state structure. No full-repository architecture audit claimed. Reuse the existing #584 and R5 proofs; do not rerun business research to demonstrate the UI.

Official ecosystem: GitHub [GET reference](https://docs.github.com/en/rest/git/refs#get-a-reference) resolves one R, then same-R raw file URLs. Independent issue GETs have independent times. [Sites guide](https://learn.chatgpt.com/docs/sites) and [Sites help](https://help.openai.com/en/articles/20001339-creating-and-managing-chatgpt-sites) distinguish saved code, preview, deployment and audience. Web runtime permissions are not inherited from a chat connector.

External prior art actually re-read:
- [Luna recovery at 6e3a281](https://github.com/Osteoporosis/luna-chat-coder/blob/6e3a281b0a25d7b2208e7abb05a429f7ee73b10f/.agents/skills/luna-chat-coder/references/recovery.md): reuse exact-state precedence, drift/ownership and preserving unfamiliar history. Existing Kernel discipline already covers most of it; no Luna runtime or automatic retry installed.
- [gptme portable apps at 2d94902](https://github.com/gptme/gptme-agent-template/blob/2d94902b13200ae438850389ffaf94f9b4d9dcea/knowledge/portable-agent-apps.md): one procedure owner and thin runtime wrappers; replace system/UI files without erasing user state. No gptme daemon, copied knowledge tree or plugin marketplace. This is mechanism/contract reference, not copied upstream source or a new dependency. Upstream licenses were not re-audited for installation because no upstream code is imported; a future adoption requires that check.

## Exact behavior and limits

`openReading()` resolves R once. A reading object cannot change in place. An explicit refresh opens a new reading; selected files remain bound to the old object's R. `current-state.json` retains the existing 192 KiB limit. Unsupported schema, semantics or authority values are a reading GAP. Root shape/transport checks do **not** recompute canonical `reading_hash` or validate its entire manifest; the UI says so.

Only registered source descriptors can be read through `readFile()`. Selected text is bounded to 512 KiB, checked against declared length/SHA-256, decoded as UTF-8, and rendered as text. No ZIP execution/extraction, remote HTML, dynamic source scripts, Markdown HTML or caller-supplied endpoint. Other/larger attachments stay accessible through the exact GitHub locator rather than being silently truncated.

Quick reads at most the last two #575 comment pages and accepts only a leading `## DAILY HOSTED QUICK YYYY-MM-DD` result heading. This is bounded history, not proof that today's result exists or the last complete research universe. Comment identity and created/updated/observed times remain visible. Mutable-page duplicates fail explicitly. #581 is independently read; title/closed state is not a health verdict.

Attention combines saved Watch facts with original Quick text. It does not claim to be a new Quick attention summary or the complete Human-response queue. Research views expose source locators; clicking retrieves the body. Copying a resume request is not executing it, saving a response, accepting Research, commissioning Full or changing Odds. No holdings are inferred.

Modules are ordinary local renderers. Optional view toggles affect display only, not the producer's schedule or retained state. Failed health/Quick reads do not suppress independently available readings. An unavailable fixed reading does not suppress successfully fetched independent comments. All view state is memory-only. Explicit refresh only; no automatic polling, localStorage, IndexedDB, tokens, GitHub writes, model or market API calls.

## Local development and verification

Run from repository root:

```sh
python -m http.server 8765 --bind 127.0.0.1
# Open http://127.0.0.1:8765/workbench/
node --test workbench/reading.test.mjs
python -m pytest tests/test_workbench_web.py
```

Browser ES modules, Fetch and Web Crypto are required. The optional web module's test toolchain requires Node >=20; `node:test` is native, with no npm packages. One pytest integration invokes the JS cases and syntax checks within the existing full CI collection. No new workflow/matrix/registry or bypass is added. Existing hosted image capability is a candidate, not permanent proof: the actual PR run must establish the tool is present. Missing Node fails, not skips. Tests use synthetic transport, never real holdings or fabricated acceptance.

This session's native Sites namespace/creation/deploy tools were not exposed. Container clone separately failed DNS resolution; authorized GitHub connector reads worked. A local Chromium UI-check attempt was explicitly blocked with `ERR_BLOCKED_BY_ADMINISTRATOR` before loading the localhost page; that browser action stopped, without alternative routing or bypass. No screenshot or browser/CORS pass is claimed. The portable code can be reviewed and handed to a Sites-enabled environment, but is **not** proof of live GitHub CORS, account runtime access, deployed Site creation, refresh behavior in Sites, or hosted authentication. These remain explicit acceptance items. No alternate hosting is commissioned.

## Exit and remaining acceptance

This development slice is ready for review when native tests and existing CI pass, the actual diff is reviewed and exact commit is recovered. Do not label A1 complete until the real hosting/read path is exercised. Remaining A1: Sites execution, real response shape/selected-file integration, full object navigation, quality-reviewed Attention, refresh/failure behavior in the actual host. A2: actual authorized response round-trip, personal context and a natural L1 successor remain NOT RUN.

Disable/remove this optional `workbench/` consumer without changing any original archive, producer or task. Its dedicated pytest wrapper and JS tests retire with it; shared Kernel checks and historical readers remain. Rollback goes through a normal PR; do not delete original Research, comments, errors or Human words. An implementation change is not a reason to reset unaffected R5 natural observations.
