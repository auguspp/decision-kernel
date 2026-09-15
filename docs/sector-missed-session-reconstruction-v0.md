# Missed-session reconstruction v0: retained Sector prefix

Scope: #375-A, Human start recorded in #375 comment 5675606163.
Reuse Decision: **THIN_ADAPTER**. This is an offline historical reading tool,
not a natural production run, a general backtester, or a production restore path.

## What this first slice does

A failed run can retain useful inputs even when it produces no final result.
`decision_kernel.runtime.sector_missed_session` accepts an independently bound,
sealed, rejected Sector audit containing exactly these four successful responses:
calendar, industry catalog, index snapshot, and benchmark history. It reuses the
existing index normalizers, original pre-opening snapshot qualification and
`prepare_sector_radar_daily_run` to reconstruct the next completed session.
It does not change ranks, gates, limits, price rules or the ordinary producer.

The original audit and failure stay byte-identical. Original implementation
identity and later reconstruction implementation identity are both retained.
The ordinary audit validator/replay still requires exact producing code; its
shared integrity-only reader is not source truth or restore authority.

The output is explicitly `PARTIAL_RECONSTRUCTED_SECTOR_PREFIX_ONLY`:
- historical index state and un-enriched state-entry observations;
- exact missing enrichment plan;
- original event-ledger bytes, unchanged;
- source cutoff, market session, actual later execution time and implementation;
- `stock.candidate_codes = null`, not an empty successful Stock screen;
- no natural acceptance, current-live qualification or production restore authority.

It does not call a provider, emit ledger events, run Research, install a cache,
change refs, dispatch a workflow or write an investment decision. There is no
new workflow or scheduled task. Output requires a new directory separate from
original inputs; a failed write is not complete delivery and must not be retried
by overwriting existing output.

## Three clocks, not one fake historical time

`market_session` identifies the bars. `source_cutoff` is the last actual receipt
in the original capture, not a newly invented publication/availability time.
`reconstructed_at` is the actual later calculation time.

The motivating 9/14 capture actually arrived on **9/15 around 00:22–00:23 +08**.
Its latest completed market session is 9/14. The existing pre-opening contract
can qualify those saved prices against saved history, but this does **not** prove
the exact bytes were available at 9/14 15:00 or 18:13. Therefore the result is
PIT to the original capture window, not a certified close-time backtest.
The original 09:15 carry expiry is retained, not extended by later calculation.
Neither current membership nor later stock performance can enter the result.

## Use after exact original-artifact and code binding

First read run/attempt/head, download the original archive, and verify archive
SHA256, inventory and the expected audit hash. The local CLI does not authenticate
GitHub metadata or prove that a caller-supplied SHA belongs to the executing tree.
The execution carrier must bind the actual code/tree and source ZIP separately.

```sh
python -m decision_kernel.runtime.sector_missed_session \
  --audit-root /path/to/verified/input-audit \
  --expected-audit-hash <independently-bound-audit-hash> \
  --origin-run-id <original-run-id> \
  --origin-commit <original-head-sha> \
  --market-session YYYY-MM-DD \
  --reconstruction-commit <actual-executing-commit> \
  --output /path/to/new-historical-reading
```

No credentials or live URLs are accepted. A requested date different from the
captured completed session, future/unreceived bars, identity mismatch, malformed
inventory, invalid clocks, or multiple missing intermediate sessions is rejected.
This is not arbitrary date range recovery.

## Exact 9/14 source / reusable acceptance case

- Original run: `34868170673`, attempt 1; head
  `2021f8a0999ce3eae299cea83800c803e23a44c7`.
- Artifact: `10358420687`, `sector-radar-run-34868170673`, 505956 bytes.
- ZIP SHA256: `00d0a785466e64de97541c47124f9540f1b0c522b724a1b0a7f8415ec5c7d3cd`.
- Audit hash: `788b8b89edd543026a6c0608ee61bfcc97c151257e44c115efe46ad30f971e69`.
- Original final receipt: `2026-09-14T16:23:34.646808+00:00`.
- Parent market session: 9/11; 321 index series; no membership/Stock responses.
- Initial offline experiment: 2 broad + 12 granular state entries; original
  enrichment plan needs 23 distinct memberships plus the all-market stock snapshot.

These are not 14 stock picks. The stored initial experiment is not full current
main CI, remote publication, an adopted checkpoint, or a natural schedule success.
Exact implemented-code acceptance belongs in the subsequent #375/#297 receipt.

## Why Stock cannot be invented

HiThink's official `docs/api/endpoints-index.md` (read 2026-09-15,
blob `d86f528634e73b75a4c8bb6d21f136d725ad6c43`) explicitly says
`constituents/ths-stock-list` returns current members and no historical changes.
Its `docs/api/endpoints-market-dumps.md` (blob
`07e93d98ec02e33e6db6c1661c1d280a38a5fcb6`) supplies historical bars and
corporate actions, not historical memberships. Daily bars do not by themselves
recreate the missed selection universe. Do not invent a historical date parameter,
carry 9/11 members forward without evidence, or use 9/15 members as 9/14.

## Remaining Part A work, not silently completed here

Full historical Stock delivery requires qualified historical membership and the
necessary stock fields, or contemporaneous retained inputs. Preventing the same
loss on future days additionally needs an approved bounded capture/retention
contract; an offline consumer cannot retroactively create unreceived inputs.

Production continuity is another separate gate. The ordinary producer rejects
more than one completed session after its restored state. A historical reading
must not silently install itself as the new production parent. Any subsequent
checkpoint adoption must use the existing explicit persistence/adoption lineage,
preserve old ledger history and be separately verified. Waiting for the next
close alone does not fix a previously missed day.

Part B outcome study, trading simulation, new source/provider frameworks,
automatic Research/Odds/Action and retrospective natural-success labels remain
outside this slice. Old failure and original source evidence remain retained.
