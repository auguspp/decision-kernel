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


## Saved Concept members in the existing reading and Workbench

Under [Brief / Concept #645](https://github.com/auguspp/decision-kernel/issues/645),
the normal reader optionally derives `tdx-concept-membership-v1` from the same
successfully replayed source ZIP. The original capture module, policy, 15-bar
observations, implementation fingerprints and historical files remain unchanged.
This is a disposable read projection, not a second source or state owner.

`tdx_concept_membership` uses the already adopted `eltdx==3.2.2` pure-file
`BoardService._members_for` and `_infoharbor_headers` seams against an explicit
temporary source directory. It never calls preparation, quote methods, a client,
or current machine caches. Those private seams are version-bound and covered by
installed-package no-network tests. The SDK owns member parsing/order; Kernel
binds its result to the full observed Concept catalog, checks every declared
member count, exact `(market, code)` security identity, retained file hashes and
source-preparation clock. Missing security-list entries remain visible with an
unknown name; they do not establish delisting or remove source members.

The shared reader first performs its original strict archive replay, then
retains one bounded `details/radar/tdx-concept/membership.json` at the same R.
The original 1 MiB Workbench file limit and publication/API budget remain in
force. Absent SDK, incompatible files, rejected membership or insufficient
optional retention budget produce a member gap without discarding the valid
short-horizon Concept observation. The source ZIP remains available; a member
projection is not a claim of raw-wire custody or historical effective membership.

The optional `concept` install extra is used by the existing publisher; `dev`
installs the same pinned SDK for real parser tests. Base Kernel dependencies,
existing source capture, provider access, token scope, trigger and all task
schedules do not change. The personal non-commercial license boundary above
continues; no upstream source code is copied.

Workbench's market page reads the full observation and optional member projection
through existing `Reading.readFile`, including native byte/SHA verification.
It searches/pages the complete saved catalog, shows all source members in their
original order, and links an exact security to the existing company reader.
Existing Stock dispositions are joined only by exact security and keep their
own market date: qualified price observation, conditions not met, unavailable,
and outside the saved check scope are separate. No member/price state establishes
business benefit, new Research, a holding, a watch or an investment action.

Overlap is ordinary set intersection of the same saved membership. Each relation
shows actual shared members and both denominators (`shared / selected members`,
`shared / other members`); displaying by shared count is not an opportunity score.
The two Concept identities are not merged. No shared members within this table
is not a claim of economic independence. Search and page changes never fetch
new source data; an old-R response cannot overwrite a newly selected reading.

Reuse starts from the retained source audit above and
[the existing direction-to-company prior-art record](radar-stock-discovery-pool-v1.md).
The eltdx upstream inspected for this increment remains
`d19ac86f2bae7565660a89baf94a3fcc531fac93`; the actual `boards.py` parser and
`protocol/unit.py` market IDs were read. Python/JavaScript native sets and the
existing text-only DOM/isolated Playwright harness supply relationship display
and verification. This is REUSE + THIN_ADAPTER, not a replacement parser,
provider framework or EasyStock fusion engine.

**Still missing:** 20/60-day Concept paths and a qualified relative benchmark,
long-horizon lifecycle, historical membership, leading-member ranking, and
cross-taxonomy corroboration. A 15-bar archive cannot supply those paths, and
Sector members cannot stand in for Concept members. Actual fixed-R adoption,
browser results, Sites/phone use and overall #645 acceptance are recorded in
that issue, not inferred from this documentation or from CI alone.

To retire this extension, remove the optional reader/projection, its Workbench
panel/import, dedicated tests/scenes and the no-longer-consumed install extra in
one normal change. Keep original capture/replay, old archives, shared Stock and
company readers, and historical receipts. No persistent state requires migration.


## Optional same-source 5/20/60 paths — Concept #645

The same existing daily capture now packages the unchanged nine-file v1 tree
under `snapshot/` and an optional `trend/` sibling. Old flat archives remain
readable without a fake long-history result. No original capture fingerprint,
1/5/10 calculation, member parser, clock owner, schedule or notification changes.
No manual source dispatch is performed merely to obtain an acceptance sample.

After the original snapshot is qualified, `tdx_concept_trend` connects once to
that snapshot's already-selected adopted TDX host, with the same installed wheel,
no fresh host probe/preparation and no source retry. The existing SDK's public
`bars.get` requests one page of at most126 daily bars for every original Concept
and `sh000300` (沪深300), with explicit `kind=index`, `adjust=None`, `all_pages=False`.
This is one SDK batch, **not one network request**: it adds one history request
per Concept plus the benchmark; concurrency is capped by the existing four
connections. It does not introduce a second source workflow or data provider.

The actual inspected upstream remains eltdx3.2.2 at
`d19ac86f2bae7565660a89baf94a3fcc531fac93`: `api/bars.py`, `models/kline.py` and
`docs/methods/7709-K线周期线.md`. SDK period and adjustment identities are checked;
the extension retains the actual returned aware times and integer milli-closes,
not reconstructed float prices. **Custody is explicitly extracted SDK fields,
not full Kline models or raw7709 frames.** The original source models/files stay
intact in `snapshot/`. This is a thin consumer of the already-adopted SDK, not a
new protocol parser. The personal noncommercial license boundary above remains.

The canonical source file binds actual acquisition clocks, installed wheel,
selected host, request parameters and complete requested identities. Each usable
Concept must match the same returned benchmark-session suffix, end on the source
session, and match *every* date/close retained by its original short snapshot.
There is no filling, calendar-day substitution, taxonomy fusion, stale-success
fallback, or joining disparate histories. Returned benchmark dates establish the
observed comparison grid, not independent exchange-calendar certification.
Malformed benchmark/identity makes the optional projection unavailable; a bad
Concept path stays visible with a local gap. A young Concept can retain available
5/20-day paths without inventing60-day history or a long phase.

Existing `sector_radar._return_over` and `_persistence` supply arithmetic:
index return and benchmark return are separate fractions; excess is their
difference.20-day excess acceleration is current20-day excess minus its value
five observed sessions earlier. The positive20-day excess run and left-censor
flag are retained; this is not the true age of a theme or an economic judgment.
All historical comparisons are made from this acquisition's current catalogue,
not a claim that the catalogue or a signal was known at the earlier date.

### Explicit descriptive phases, not an investment score

A phase requires a comparable60-day path, prior-session20-day excess and the
five-session change of20-day excess. Otherwise it is UNKNOWN. With those inputs:

- `EMERGING`:20-day excess has crossed from nonpositive to positive since the
  preceding returned session. The label names this condition, not first discovery.
- `STRENGTHENING`:20-day excess was already positive;5-day excess and20-day excess
  acceleration are positive. It can still have a negative absolute return.
- `MATURE_OR_DIVERGING`:20-day excess remains positive, but5-day excess is
  nonpositive or20-day acceleration is negative. The displayed term is
  强中分歧, **not proof of economic maturity**.
- `PERSISTENT`:20-day excess remains positive without further acceleration under
  the above partition.
- `WEAKENING_OR_EXIT`: either20-day excess crossed out of positive territory, or
  nonpositive20-day excess is still weakening. Separate reason codes and wording
  distinguish an actual observed exit from continued weakness.
- `NOT_POSITIVE`: no positive20-day state and no observed weakening under those
  conditions. A short rebound is not called a long-term reversal.

No opaque total, percentile rank, sector threshold or business benefit is added.
Every original Concept remains available, including negative and unknown paths.
This implements descriptive relative-price phases within #645; it neither changes
Research Method nor creates a new admission, Watch or investment condition.

### Retention, reading and failure

The original8-minute job timeout,8MiB per-file,16MiB combined capture and1MiB
per-Workbench-file limits remain. The source reserves room for derived files
before retaining the optional history; exceeding the bound is an explicit gap.
`INCOMPLETE_LONG_HISTORY` is a retained source failure with a reason and available
inputs, **not a successful long path**, while the original snapshot may remain
qualified. No `continue-on-error`, retry loop or fallback producer is added.

Normal publisher supports both archive layouts and independently replays the
original tree, member projection and optional history. Exact source identity,
implementation and inventory hashes, run clocks and derived bytes must agree.
Long-history tampering or optional retention failure leaves original quotes and
members readable. The sameR carries compact `trend/trend.json`, `summary.md` and
`capture.json`; the full extracted history stays in the exact source ZIP. A failed
capture may retain only its receipt in the compact reading. No failed receipt is
promoted into a phase; an old flat archive explicitly has no captured long path.

Workbench reads the optional file using existing `Reading.readFile`/Web Crypto,
shows phase and run-length wording, and expands index/benchmark/excess5/20/60-day
values on demand. Source and comparison dates remain visible; oldR responses
cannot overwrite a new reading. Members, overlaps and company research use the
existing panel. Brief can follow the same fixedR README and detail references;
native task adoption, actual source delivery and natural Brief use are separate
facts, not inferred from this code or a synthetic browser run.

Reuse/decision and current acceptance remain in #645, starting at
[5881010177](https://github.com/auguspp/decision-kernel/issues/645#issuecomment-5881010177).
Retiring this extension removes only the same-workflow history step, trend module,
optional reader/renderer and dedicated tests/scenes together; preserve v1 replay,
membership, original source/Research history and the legacy archive reader.
