# Real bounded theme capture — v0

Status: ISOLATED SOURCE TRIAL / NOT DAILY THEME PRODUCTION. Actual results must be documented separately after inspecting the run and downloaded artifact.

## Selection before returns

`radar_inputs/theme-probe-sample-v0.json` predeclares exact-name criteria for 机器人概念 and 人形机器人, plus three exact 881 identities (通用设备, 自动化设备, 汽车零部件) from the retained industry catalog. The first label is the official HiThink concept example; the second is an adjacent narrative chosen to test membership overlap, not price performance. There is no assumed concept code. Both must resolve uniquely in the actually acquired cn_concept catalog. Missing/ambiguous names stop before prices; there are no aliases, proxies, ranking, substituted themes or largest-intersection assignments.

The collector first retains the two whole catalogs, then invokes the existing `make_theme_plan` to bind exact names/codes, reasons, catalog captures and saved state. `plan.json` is written before requesting snapshots, histories or members. This is a deterministic implementer-declared sample, not a Human judgment, an automatic global scan or a retrospectively selected winner. The current sample needs ten calls: two catalogs, one snapshot, two histories, five member sets. Existing maximum remains fifteen; never truncate the plan.

## Reuse and execution

`.github/scripts/capture-theme-probe.py` wraps the existing offline probe. Requests supplies HTTPS, sessions and streaming; the existing isolated transport supplies fresh sessions, no ambient proxy/netrc credentials, status/content policy and no redirects. The only thin network addition retains bounded original JSON bytes, which the existing decoded-only helper cannot provide. Existing endpoint checks, credential safety, catalog/member/history adapters, bootstrap validation and all theme calculations remain in use. No new package, provider, graph system, Kernel object or market convention.

Each request is attempted once, sequentially, with a twenty-second pause before the next. Per response maximum 8 MiB, total retained files 32 MiB. JSON decimals are decoded directly with `Decimal` and existing duplicate-key/finite checks; raw JSON bytes are kept separately from canonical normalized number strings. This avoids binary-float loss without changing the provider's number or creating a tolerance. HTTP/encoding/size errors stop; no fallback/retry. Rejected HTTP bodies are not read, malformed or credential-like JSON is not retained, and the attempt keeps a bounded typed failure/status instead. No tokens or response cookies are archived.

The workflow shell reads the manifest-validated committed 2026-09-04 bootstrap strictly as this experiment's fixed comparison state, NOT as the producer's recovery source. No production cache or candidate ledger is opened or written. The probe only permits that day or its immediately adjacent weekend. It will refuse a later weekday; this experiment is not an excuse to bridge an unfinished/missing day or claim bootstrap is the latest successful producer state.

## Existing workflow, explicit scope change

Use existing `hithink-stock-dump-trial` with `trial-purpose=theme-probe`. Its existing `stock-dump` mode remains the manual default with the same implementation and evidence handling. Stock dump acquisition is now **manual only**: changing this workflow must not redownload all-stock data. Main push compatibility triggers are limited to the theme capture script and exact sample file; a code/docs/workflow change elsewhere does not collect themes. A merge touching those two files deliberately causes one bounded theme trial. No schedule, additional workflow file, Actions write permission or production-state lane is added.

Only each mode's acquisition step receives the existing HiThink secret. Theme verification runs without it. The ordinary Sector workflow is not invoked or changed, and its previous-success restoration search cannot encounter this trial. Base credentials, script identity, run/attempt/commit and actual acquisition clocks are recorded; a run is not claimed successful from a local hash alone.

## Artifact and offline validation

The existing Actions uploader retains `theme-probe-trial-<run>-<attempt>` for 90 days. It contains operation and verification output, and `capture/` with selection, comparison market state, raw responses, request log/file hashes (`capture.json`), frozen plan, and — only when all checks pass — supplied inputs, theme JSON and HTML. Download, verify the actual workflow/commit/artifact metadata, then open `capture/index.html`. No successful page is promised for an incomplete capture.

```
python .github/scripts/capture-theme-probe.py verify --output <artifact>/capture
```

Verification of a successful capture re-resolves selection, rebuilds the exact request plan, reconstructs normalized input from retained original bytes, executes the existing full probe and compares its JSON and HTML. Failure verification checks retained file identity only and explicitly reports `RETAINED_BYTES_ONLY_INCOMPLETE_CAPTURE`; it does not certify the cause or manufacture a successful probe. An error in collection still makes the workflow fail even if its retained bytes verify. Both paths upload available evidence and truthful Summary.

The unchanged probe HTML intentionally retains its supplied-input provenance wording. The separate live capture receipt and workflow evidence establish acquisition; the standalone renderer does not authenticate HTTP execution. File hashes are not signatures, long-term storage, exchange truth, historical membership effective dates, breadth qualification or independent forecasts. After artifact expiry, preserving exact bytes is necessary; hashes and refetched URLs cannot reproduce missing originals.

## Remaining gates

Actual raw response semantics, historical continuity, snapshot/history values and current industry overlaps must be reviewed after the first run. Same-source consistency is not independent economic evidence. A successful selected probe does not establish all-theme coverage, current-stock breadth, daily theme state, prospective candidates/outcomes, economic benefit or Research eligibility. The normal Sector next-session append and joint-page remote delivery remain separate pending milestones. All Human/Research/Investment and signal-transition authorities remain NONE.

Primary provider references inspected: `HiThink-Tech/Financial-API` index endpoint specification and its official concept example, https://fuyao.aicubes.cn/best-practices/03-index-constituents/example.html . No upstream SDK code was imported; this reuses the project's already-adopted transport and parser contracts.
