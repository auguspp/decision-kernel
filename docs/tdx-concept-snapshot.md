# TDX / eltdx concept snapshot — primary current cross-section source

Status: PRIMARY SOURCE / LIVE MAIN / PINNED READ-MODEL RETENTION ACCEPTED; DAILY HANDOFF USES EXISTING SECTOR CLOCK.
Authority: Human 2026-09-25 “那就做吧，东财退二线去”; Reconcile #364
comments 5826719708 and 5826769197. This changes the current supplemental
Concept cross-section source, not the existing HiThink `radar-concept-source`
contract, Industry Radar, Research authority or historical source identity.

## Source decision

The required current Concept cross-section path is now TDX/eltdx. Eastmoney/Vibe
is retained as SECONDARY / BEST-EFFORT and for historical evidence only; it is
not an implicit fallback and is not required for a TDX result to qualify.

This is deliberately source-native. TDX board codes/names are not translated to
Eastmoney BK or HiThink TI identities. The 2026-09-25 comparison proved the
taxonomies are materially different: the retained Eastmoney/Vibe snapshot had
504 BK names, while eltdx returned 269 strict `category="概念"` boards and 427
all-board rows. Simple light name normalization found partial overlap only and
also exposed obvious synonym/taxonomy differences. No alias table or fake
one-to-one mapping is introduced.

## Reuse evidence

Reuse Decision: **REUSE + THIN_ADAPTER**.

External implementation actually inspected:
- `electkismet/eltdx`, package pinned to `eltdx==3.2.2`;
- inspected upstream main `d19ac86f2bae7565660a89baf94a3fcc531fac93`;
- `src/eltdx/helpers/boards.py` for board definition/member preparation;
- `docs/helpers/板块行情.md`, `docs/helpers/板块成分股行情.md`;
- `docs/METHOD_REFERENCE.md` for `TdxClient` and batched `bars.get`.

Internal reuse remains the existing exact-main/main-CI admission, canonical hash,
create-only output, native GitHub artifact retention, explicit UNKNOWN and
Human-authority boundaries. This slice does not add a provider framework,
database, scheduler, taxonomy service, model call or investment scoring layer.

### Actual GitHub-hosted probes

The decision is based on live GitHub-hosted runs, not README capability:

- `36090750436/attempt1`: Ubuntu runner installed `eltdx==3.2.2`, 42/43
  packaged 7709 hosts accepted TCP, explicit host handshake succeeded, 269/269
  strict Concept boards had quotes and one 88-member board returned 88/88.
- `36091451870/attempt1`: three independent runners in centralus/westus/
  westcentralus all succeeded with default 5s connection, 269/269 board quotes,
  stable catalog/member/topic hashes and identical board-file hashes.
- `36094464175/attempt1`: one bounded batch call retrieved 15 daily bars for
  all 269 strict Concept boards in about 14 seconds; 269/269 histories were
  present and every last history close matched the board snapshot (0 mismatch).

The earlier 3-second default-connect timeout `36090670418` remains historical
evidence. Its cause is UNKNOWN; it is not erased by later success.

## Completed-session contract

`.github/workflows/tdx-concept-snapshot.yml` remains a `workflow_dispatch` capture contract, so it keeps the same manual fallback and never owns a second clock. Routine daily invocation is handed from the existing `stock-reading-after-sector.yml` `workflow_run` successor after one successful result-bearing `sector-radar-shadow` production. The successor reuses the exact Sector run/job classifier and retained audit, takes `market-session` from the sealed Sector `operations.json.latest_completed_session`, and uses the already-existing `DAILY_CHAIN_DISPATCH_TOKEN` to request the TDX workflow once. Recovery/adoption and same-session no-op Sector runs do not create a TDX dispatch.

The capture workflow still requires:
- exact `main` / attempt1 / `code-sha`;
- a successful independent main `ci.yml` push run for that exact SHA;
- an explicit completed A-share `market-session`.

The daily successor itself makes no TDX/Eastmoney call, does not infer a trade date from wall clock, and adds no `schedule:`. If main advances after the successor starts, it stops before dispatch rather than binding an ambiguous code SHA. The TDX capture then independently rechecks exact main/CI and source-session equality.

The source probes the packaged TDX host list with a 1.5s TCP bound, then permits
at most three distinct protocol connection attempts and uses the first successful
7709 handshake. There is no provider key and no Eastmoney request.

The source then asks eltdx for the complete strict `category="概念"` board
table and 15 daily bars for every returned board. Qualification requires:
- board `prepared_date == requested market-session`;
- at least two retained bars per board;
- the last retained bar date equals the requested market-session;
- snapshot last / previous close exactly match the last two retained daily closes;
- complete current board quote coverage.

For each board Kernel computes close-to-close:
- `today`: last close / prior close - 1;
- `5d`: last close / close five trading intervals earlier - 1;
- `10d`: last close / close ten trading intervals earlier - 1.

A new board with insufficient longer history remains visible with a 5d/10d
UNKNOWN; it is not dropped or filled with zero. This is a completed-session
mechanical Market Expression observation, not business Evidence, Research,
Odds or a Decision.

The midday 2026-09-25 probes returned `prepared_date=2026-09-24` and daily
histories ending 2026-09-24 even though the handshake clock was 2026-09-25.
That is why the workflow binds source identity to the explicit completed market
session instead of equating retrieval date with trade date.

## Custody and replay boundary

The capture retains:
- exact package version and runtime wheel SHA256;
- chosen host, bounded host probes and protocol attempts;
- handshake fields;
- source-native board snapshot and K-line model fields;
- `infoharbor_block.dat`, `tdxhy.cfg`, `security_list.json` and the eltdx
  board cache metadata with byte size/SHA256;
- derived observation and summary.

Replay is network-free and recomputes 1/5/10-day observations from retained
source-native models while checking the retained board-file hashes and exact
capture/implementation identity.

A material limitation stays explicit: the public eltdx board helper does not
expose the complete raw 7709 protocol frames for the board snapshot. Therefore
the artifact records `raw_protocol_frames=NOT_EXPOSED_BY_ELTDX_BOARD_HELPER`;
normalized source models plus source board files are retained instead. This is
not silently upgraded to raw-wire custody or historical membership PIT.

## Relationship to existing sources

- **HiThink `radar-concept-source`**: unchanged. It remains a separate
  source-native Concept Radar path with bounded detail/member/history semantics.
- **TDX/eltdx**: primary current cross-section source for completed-session
  1/5/10-day Concept market expression.
- **Vibe/Eastmoney**: SECONDARY / BEST-EFFORT / historical evidence. v1/v2/v3
  failures and partial success remain immutable; no v4 retry/backoff work.
- **FTShare Eastmoney concept routes**: existing historical/reference capability
  remains unchanged and is not silently promoted or deleted.

No source membership establishes company economic exposure. Quick remains free
to interpret multiple source observations and public evidence; Radar does not
gain Investment Authority.

## License/use boundary

eltdx is provided under its Research-Only License for personal learning,
protocol research and non-commercial study, and disallows commercial/paid/
production-service and automated-trading-service uses. The current Human use is
personal non-commercial research. This adoption does not grant or assume a
future commercial/production-service right; such a use change requires a fresh
license/source decision.

No eltdx source code is copied into Decision Kernel by this adapter. The
workflow installs the pinned wheel and Kernel only owns its thin source
identity/time/retention semantics.


## Normal read-model retention

The source workflow's local replay happens before artifact upload. GitHub's
`actions/upload-artifact` excludes hidden files by default, while this contract
binds `source-files/.eltdx_board_cache.json`. Therefore the normal artifact path
explicitly sets `include-hidden-files: true`; without that file, later replay
must fail closed even if the original source job was locally successful.

The existing `current-state-read-entry` publisher listens to completed main
`tdx-concept-snapshot` attempts. It selects only the newest attempt, never
searches backwards for an older green run, downloads the exact artifact, and
replays it with trusted installed Kernel code. The pinned read-model retains the
exact source ZIP plus compact `observation.json`, `summary.md`, capture receipt
and run metadata. It does not duplicate the large source model/file payload
outside that exact ZIP.

This reading seam performs zero TDX/Eastmoney calls and creates no new source,
Research, Odds, Decision, Action or investment authority. A missing, failed,
expired or unreplayable newest artifact is an explicit reading gap, not zero
Concept activity.


## Daily handoff boundary

The nominal daily clock remains the already-adopted Sector trigger path (currently the Human-managed workday 18:13 Asia/Shanghai external dispatch). TDX does not gain its own cron. One successful result-bearing Sector production may hand the same completed session to both the existing Stock successor and TDX, but the two jobs are independent: Stock shared-key activity cannot suppress TDX and a TDX failure cannot relabel Sector/Stock success.

The handoff is event plumbing, not a source success claim. If Sector fails, performs a recovery/adoption, or validates an already-current same session, no new TDX run is fabricated. If the TDX child fails its exact-main/main-CI/source-date contract, the existing publisher exposes the gap rather than searching an older green child. R5-5 must measure those actual missing days instead of repairing them with same-day manual duplicates.
