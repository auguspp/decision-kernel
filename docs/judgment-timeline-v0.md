# Judgment Timeline v0 — frozen-record reading surface

Status: READ-ONLY HUMAN SURFACE / NOT A SECOND JUDGMENT STORE / NO AUTOMATION.

## What is delivered

A self-contained HTML page and a JSON projection of four existing frozen checkpoints, grouped into CATL, Sanhua and Micron for navigation. It answers: what the checkpoint said, what the Human said, what remained unexecuted, and what the record declared for later review. The Sanhua 07:04 decision and 07:22 horizon supplement remain separate; the latter does not rewrite the former.

This is a selected historical record view, not a current-state dashboard. All four source files are pinned to commit `7c9bd59c46d752c1a9d95c292ed9a5cb5e270d41` and exact Git blob identities. Their full source bytes remain unchanged. It does not scan for later records, so absence of an Outcome in the view means not included, not that no later information exists.

`ui_inputs/judgment-timeline-v0.json` is reviewed display configuration: explicit file selections, source line ranges, navigation order, labels and Chinese reading notes. It has no Kernel model, market state, investment judgment, execution, episode or evaluation authority. Changing it requires review; hash matching verifies bytes, not the truth or adequacy of a navigation note. No LLM or regex interprets investment decisions from prose.

## Run

From a checkout with the existing package installed:

```bash
python -m decision_kernel.runtime.judgment_timeline \
  --source-root . \
  --output ../judgment-timeline-view
```

Use a NEW output directory outside the source root. Open `index.html` with its sibling `projection.json` retained. The HTML includes its source excerpts and needs no server, JavaScript, stylesheet download, credentials or market data. Clicking an original-source link explicitly opens the private GitHub source and may require repository access. No tracking or implicit HTTP request is added.

Source files can be supplied from a minimal local copy rather than a complete checkout, provided the selected bytes match the manifest. A changed or missing source must be restored from the pinned version or reviewed in a distinct future view; the tool will not refresh a pin or silently use current content. The manifest's source-commit/file association was checked against the repository when selected; the offline reader verifies those curated blob identities, not GitHub history or historic Human exposure itself.

Output files:

```text
index.html
projection.json
```

The projection reuses `identity.canonical_hash`. Its identity includes the exact view-manifest hash, selected source hashes, line ranges and extracted text. `generated_at` is separate and is only the current page-generation clock; rebuilding later must not change the source clocks or settle a pending judgment. The renderer checks the projection hash and no-authority boundary. This output is not an input to commit, Odds, Inbox, cache restoration or the Sector producer.

## Semantics kept visible

- CATL: acceptance of a research posture, not BUY/SELL/HOLD; Odds withheld. CNY351 is the source's research context, not a newly acquired live observation.
- Sanhua: a conditional first entry around CNY30, not an executed trade or price target. The original lack of a personal horizon remains visible; the later approximately 3–6 month window begins after actual execution, not the note's date. No automatic calendar due date is computed.
- Micron: an explicit WAIT/NO_ACTION with a Human market-allocation constraint, not bearish Fundamental Belief. September 30 is the original record's validation window, not a newly verified schedule or compelled investment decision. U.S. production ObservedMarket and numerical Odds remain unavailable/withheld in the selected record.
- Research context in this page is what each Human checkpoint references or records. The reader does not reload all underlying research packages, recompute Odds, reconstruct system prompts, or claim that a historical Git file was exactly what the Human saw.
- Occurrence and recording clocks are not inferred from file names, Git timestamps, or generation time. Original timestamp lines are presented verbatim with original precision. A date-only Micron record does not acquire midnight or an invented timezone.
- Unknown presentation/reading evidence remains unknown. No old exposure or independent Human forecast is backfilled. Security grouping is not DecisionEpisode inference, and record counts are not statistical samples.
- No Outcome/Attribution records have been selected; no price chart, actual PnL, hit rate, win/loss label, barrier settlement or method learning is computed. Missing qualified historical prices are not filled with source target/condition/reference prices.

## Reuse decision

Reuse the existing `canonical_hash`, Python `html.escape` and the project's self-contained HTML approach. Native browser `details`/`summary` supplies disclosure interaction; no frontend state framework, graph library, Markdown parser, telemetry stack or new dependency is introduced. Beautiful Soup, already in the dev dependencies, checks the generated DOM in tests. Do not reuse `build_human_surface` as a view constructor: that function owns an attention gate and expects exact Odds/Rehearsal, not these probability-withheld checkpoint excerpts.

Native disclosure documentation consulted: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/details . ARTi remains Human-reported product prior art, not imported code or backend settlement semantics. No external code body is copied.

## Acceptance and limits

`tests/test_judgment_timeline.py` contains 26 cases using selected source copies, existing canonical identity and Beautiful Soup. Socket access is blocked. They verify exact source/hash/line bindings, three distinct Human meanings, explicit supplement linkage, generation-clock isolation, no inferred midnight/settlement/authority, HTML escaping, no forms/scripts/network resources, duplicate/invalid manifest rejection, path/symlink rejection, source drift rejection before output, new-output-only writes and cleanup of a failed display write. The tests do not prove that the original Human statements were logged by this new UI.

Local validation used a minimal source copy whose four Markdown files and the reused `identity.py` / `primitives.py` matched their Git blob identities. All 26 targeted cases passed. The exact generated HTML was loaded into Chromium using Playwright `set_content`, at 1280px and 390px widths: no horizontal overflow or page-initiated network requests, and native details opened. Screenshots were inspected. This checks layout/interaction, not deployment, full Safari support or production file-URL delivery. The local browser policy blocked direct file-URL navigation; it was not bypassed. No full local repository-suite claim is made; full regression belongs to CI.

This version is an independently invoked, downloadable local reading surface. No workflow attachment publishing, live web deployment, canonical Inbox integration, Human response input form, automatic source discovery, governance service or Kernel Judgment/Episode/Outcome schema is added. A new genuine Human response still uses `docs/human-exposure-and-response-capture-v0.md`; this page does not manufacture such a response.

Sector's next completed-session append/replay/publication acceptance remains a separate pending milestone. No provider acquisition, policy threshold, real state/cache/event, original company stance or Human/Research/Investment authority is changed by this work.
