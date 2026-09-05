# Economic source compatibility operations

Status: WORKFLOW IMPLEMENTATION / REAL CAPTURE RESULT MUST BE REVIEWED SEPARATELY / NO CONTINUOUS MONITORING.

## Why a maintained compatibility workflow

The capture implementation in #199 has offline tests, but a synthetic page cannot prove current official server reachability, body delivery or markup compatibility. The local development runtime could not retrieve original bytes. This independent workflow provides an appropriately networked, inspectable public-source probe without using provider credentials or changing market production.

`economic-source-capture.yml` runs manually or after a main-branch change to exactly the capture implementation, economic-study parser, reviewed source list or workflow itself. It is not a temporary self-modifying workflow and does not run on arbitrary branches, pull requests, ordinary documentation changes or a clock schedule. It remains useful when the source contract is revised. A matching main push explicitly incurs at most four public-page GET attempts. There is no automatic retry or retry-until-success behavior.

The first merge that adds this workflow will trigger its first real source probe. That is a real external read, not a unit test. Main `kernel-tests` and Sector Radar production remain separate workflows; a source outage is not represented as a core unit-test failure or a market-state update.

## Data and permissions

Only the four exact records in `radar_inputs/economic-node-study-2026-09-05.json` are selected initially. The runtime preflights source domains, paths, excerpt/date/unit contracts and request/byte limits. No key, password, cookie or repository secret is read. Checkout credentials are not persisted. Workflow permissions are `contents: read`; there is no market cache, state restoration, ticker Inbox integration or git write.

The command attempts each independently selected URL once. A missing or revised statement is an explicit rejected binding, not an invented new observation. See `docs/economic-source-raw-capture.md` for the raw-response and time semantics.

## Artifact and verification

The run publishes one private-repository artifact:

```text
economic-source-capture-<run_id>-<attempt>
├── workflow.json            # repository/run/attempt/code/event and content hash
├── verification.json        # offline verification result, when available
└── capture/
    ├── manifest.json
    ├── summary.md
    └── 0000/ ... 0003/      # raw response, metadata and binding evidence
```

The `capture/` inventory is sealed independently. Workflow identity and verification output stay outside it, so adding operational metadata does not invalidate its fixed inventory. The artifact is retained for 90 days, matching the current research-proof lifecycle. It is not a permanent raw-source archive or a long-term checkpoint.

Verification runs even after acquisition rejection if an archive exists. Its command remains nonzero for `INCOMPLETE`, even when the retained bytes are internally consistent. Upload and summary steps run regardless, without `continue-on-error` or `|| true` masking the source failure. An uploaded artifact does not imply that all selected sources were obtained or accepted.

To inspect an extracted trusted artifact at the recorded implementation:

```bash
python -m decision_kernel.runtime.economic_source_capture verify /path/to/artifact/capture
```

Check both the workflow conclusion and structured per-source records. For accepted pages, verify raw bytes, exact source URL, HTTP status, capture clock, binding offsets and reconstructed observations. For failures, distinguish transport unavailability from fetched-but-rejected content. Do not replace either with another provider or browser-extracted text and claim original acquisition.

## What success does not mean

Even four matched pages only prove that these reviewed excerpts reconciled with these captured bodies at these times. It does not discover a newer release, prove an unchanged whole-page narrative, establish historical first-vintage knowledge, create a market event, confirm an industry cycle or infer company profits.

There is still no automatic economic release discovery or continuous monitoring. Candidate gate selection, market states, append-only event ledgers, current members, objective outcomes and Human annotations are unchanged. A future broader feed must be separately designed and qualified.

HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
