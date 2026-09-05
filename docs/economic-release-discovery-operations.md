# Official directory discovery compatibility operations

Status: REUSED PARSER AND DIRECT STATISTICS WINDOW VERIFIED / EACH REAL RESULT MUST BE REVIEWED / NO CONTINUOUS FEED.

`economic-release-discovery.yml` is a maintained independent compatibility probe for `runtime/economic_release_discovery.py`. It runs by manual main dispatch or only main pushes changing that module or the workflow. It does not run on pull requests, arbitrary branches, a schedule, ordinary documentation changes, or every existing source-capture change. It does not self-modify.

The merge adding this workflow intentionally caused one real public scan: two fixed directory GETs, plus at most four exact discovered article GETs according to the explicit reviewed baseline and budget. Subsequent parser/source changes require separately reviewed compatibility evidence. There is one attempt per URL, no automatic retries and no retry-until-success. The original four-page compatibility workflow is unchanged and is not triggered by these files.

Permissions are contents-read only. No repository secrets, provider keys, cookies or market state/cache/ledger are used. The run is separate from kernel-tests, sector-radar-shadow and the canonical Attention Inbox. No source review is auto-accepted and no economic metric/market event is published.

The workflow installs `.[discovery]`, containing pinned Beautiful Soup; no crawler/browser service was added. Schema 2 records the exact Beautiful Soup/builder/Python runtime as well as implementation hashes. Reproduction must use that environment. An old-schema archive is not upgraded or accepted by changing its metadata.

Artifacts, retained for 90 days, contain:

```text
workflow.json       # exact repository/run/attempt/SHA/event and hash
verification.json   # recorded zero-network reconstruction, when possible
scan/
  baseline.json
  00.request.json   # directory one
  00.response.json  # only when a bounded body was acquired
  00.body.bin
  01.*              # directory two
  02.* ... 05.*     # only planned detail acquisitions
  result.json
  summary.md
  manifest.json
```

Workflow provenance and verification output remain outside the sealed scan inventory. Acquisition rejection remains nonzero. Verification, upload and summary execute on failure when evidence exists, without masking that failure. A partial/unsealed archive or uploaded artifact is not proof of successful discovery. The artifact is not a long-term checkpoint.

Download a trusted artifact, check its exact run/SHA/digest, and use the recorded implementation and parser environment:

```bash
python -m pip install -e '.[discovery]'
python -m decision_kernel.runtime.economic_release_discovery verify /path/to/scan
```

Review both per-source records and aggregate disposition. A complete scan may find no eligible unreviewed release in the visible window. It must never be described as proof that the publisher has not released anything. The original SPB news-window proof remains historical evidence. Run `33954522717` correctly rejected the script-only statistics landing page; run `33954898834` then verified its explicitly reviewed direct statistics list, reaching the existing monthly baseline. There is still no complete history or future missed-window guarantee. Evidence and limits are in `docs/handoffs/2026-09-05-reuse-first-statistics-proof-next.md`; current source/review contracts are in `docs/economic-release-discovery.md`.

Real success does not demonstrate new-release body acquisition when the actual plan contains zero detail requests. That path remains only synthetically exercised until a naturally eligible release appears. No artificial baseline rewrite, invented release, old-page relabelling or repeated live scan is warranted just to force a candidate.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
