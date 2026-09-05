# Official directory discovery compatibility operations

Status: OPERATIONAL WIRING / REAL RESULT MUST BE REVIEWED / NO CONTINUOUS FEED.

`economic-release-discovery.yml` is a maintained independent compatibility probe for `runtime/economic_release_discovery.py`. It runs by manual main dispatch or only main pushes changing that module or the workflow. It does not run on pull requests, arbitrary branches, a schedule, ordinary documentation changes, or every existing source-capture change. It does not self-modify.

The merge adding this workflow intentionally causes one real public scan: two fixed directory GETs, plus at most four exact discovered article GETs according to the explicit reviewed baseline and budget. There is one attempt per URL, no automatic retries and no retry-until-success. The original four-page compatibility workflow is unchanged and is not triggered by these files.

Permissions are contents-read only. No repository secrets, provider keys, cookies or market state/cache/ledger are used. The run is separate from kernel-tests, sector-radar-shadow and the canonical Attention Inbox. No source review is auto-accepted and no economic metric/market event is published.

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

Download a trusted artifact, check its exact run/SHA/digest, and use the recorded implementation:

```bash
python -m decision_kernel.runtime.economic_release_discovery verify /path/to/scan
```

Review both per-source records and aggregate disposition. A complete scan may find no eligible unreviewed release in the visible window. It must never be described as proof that the publisher has not released anything. The first-page SPB news window is especially narrow: a separately qualified statistics directory or pagination is still required before continuous coverage. Current source details and review boundaries are in `docs/economic-release-discovery.md`.

Real success does not demonstrate new-release body acquisition when the actual plan contains zero detail requests. That path remains only synthetically exercised until a naturally eligible release appears. No artificial baseline rewrite, invented release, old-page relabelling or repeated live scan is warranted just to force a candidate.

SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
