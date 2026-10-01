# Independent Stock observations from retained full-market pages

This is a bounded original C2 / P2-4 consumer, not completion of C2 or independent
live acquisition. It reads existing decoded provider envelopes offline, preserves
the complete source denominator and freezes a small sample before checking which
stock histories happen to be available. No Sector trigger, membership, company
link or previous Research admits a candidate.

Authority remains the [original P2-4 scope](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5835074681)
and [C completeness correction](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5909499946).
AI Investment Authority = NONE. The retained-audit consumer itself makes no source
requests or production admission. The later manual K3 capture described below is
a distinct mode in the existing owner, without live Stock current-state admission,
scheduling, new provider/dependency, automatic Research or Watch changes.
A passive `NAVIGATION_ONLY / ON_DEMAND_ARCHIVE` locator for the derived report may
use the existing archive index. It does not admit a live Stock reading, eagerly
materialize a source, or claim custody of the original large archive.

## Reuse decision: REUSE + THIN_ADAPTER

- Internal: `sector_radar_audit.validate_sector_radar_input_audit_integrity` binds
  the original inventory; the existing full-market parser owns pagination,
  duplicate/total/null/zero/clock checks. The recorded calendar, benchmark snapshot
  and benchmark history qualify a comparison session without reading a Sector
  result. `hithink_stock_reading.qualify` retains 26 required recent own-stock bars,
  61-calendar-session context, exact request identity, receipt clocks, price,
  volume/turnover and corporate-action checks
- Arithmetic: `stock_radar_reading._stock_path` remains a backward-compatible
  state-facing wrapper around its unchanged sessions-only body. No `_observe`
  policy, v7/v8/v9 selection, issuer isolation or serialization rule changes
- Official: [HiThink prices contract at 3bca7805](https://github.com/HiThink-Tech/Financial-API/blob/3bca7805a4127ece8d81961917e740d2effac6ec/docs/api/a-share/prices.md)
  documents full-code-table pages and provider-ready timestamps. A page does not
  provide a per-security trading date or Chinese company name
- External: the retained #508/#511 review and current EasyStock
  `37a8c1bb3e2e9cabeb11f94dbef50a8b955f1948` `radar.go`, tests and license were
  inspected for this increment. Its theme/industry assembly, fallback and strength
  semantics do not solve independent exact-source replay. No code copied or
  dependency adopted; the PolyForm Noncommercial restriction remains relevant to
  any future adoption

The source audit's producing implementation hashes are retained separately from
the consuming implementation hashes. Loading its integrity is deliberately not
ordinary producer replay: the original exact-implementation replay validator is
unchanged and still requires the original code bytes.

## Consumer and output contract

Run `python -m decision_kernel.runtime.independent_stock_observations` with:

```text
--audit-root <retained>/market-context/input-audit
--audit-hash <independently recorded audit_hash>
[--stock-root <retained>/reading --capture-hash <independently recorded capture_hash>]
--sample-size 16
--output <new sibling directory>
```

Use `PYTHONPATH=src` for an uninstalled source checkout. `--verify <directory>`
replaces `--output` to rebuild the JSON from the separately pinned inputs and
verify the exact two-file inventory and rendered README bytes. A pin copied from
an untrusted modified report is not an independent source identity.

Every consumed context, session, page and stock-trace file is read once at its
point of use; those exact bytes must match the length and SHA-256 in the already
pinned audit/capture inventory before they are parsed. An earlier whole-tree
validation does not authorize a later unchecked reread. If a source changes
between inventory validation and consumption, the consumer fails without
publishing a result. Parsing uses the checked buffer, not another filesystem read.

The output pair is `observations.json` and `README.txt`, published through the
existing atomic, create-only report helper. Failed source qualification publishes
no successful empty result. Output cannot be inside an input tree. No network or
saved source script is executed; an absent/unplanned request never falls back to
a provider. Stock response-bearing receipts require exact integer HTTP 200. The
older Sector audit records decoded JSON and `error_type`, not HTTP status; no
missing transport evidence is invented.

The deterministic result does not record a new analysis clock. Its source capture
and receipt clocks remain historical; none is relabeled as the later replay time.

The all-market sample origin is `INDEPENDENT_ALL_MARKET_SNAPSHOT`. The rule is
descending absolute `(last_price / prev_price) - 1`, then exact code, K from 1 to
16, computed using the existing Decimal convention at precision 28. This is an
unvalidated replay display/sample rule. It is not Surprise, investment rank,
economic novelty, liquidity/tradability certification or a production gate. Large
positive and negative moves are retained; unknown name-based risk classification
is not treated as a pass.

The compact derived inventory has explicit columns and one row for every source
identity, ordered by code. Each row joins a page descriptor carrying exact file
SHA-256, bytes, original request parameters and capture clock, then a zero-based
position in that page's original `data.item`. The row retains last/previous price,
the signed difference numerator and an explicit selected/deferred/unpriced
disposition. The ratio denominator is the same previous price. The page hash and
position bind the whole original row, including omitted fields; no standalone
row-hash archive or reconstructed original-envelope claim is made.

Selection is frozen and hashed before reading the history capture. Missing
selected histories remain `UNKNOWN / HISTORY_NOT_SUPPLIED`; available traces
cannot replace them. The complete denominator, selected count, supplied-history
intersection and successfully qualified intersection are separate. Older own-bar
gaps can null 60-day context while a missing recent required bar fails; no gap is
filled and no corporate action is automatically adjusted.

The separate replay-control panel retains the original historically Sector-selected
traces. It is not an independent discovery panel, even if a control also happens
to lie in the independently frozen sample. Provider code 3002 remains a request
failure, never an empty corporate-action history. Per-security session proof,
company name, business benefit and economic interpretation stay UNKNOWN or
NOT_ESTABLISHED where the source does not supply them.

## Real retained replay: 2026-09-30

Source: [run 36702153468](https://github.com/auguspp/decision-kernel/actions/runs/36702153468),
artifact `11091190335`, `stock-reading-36702153468-1`, produced at
`ce22fa79ac841dea11d31541c86e4c4faeb1378b`.

- ZIP SHA-256: `47f4ea4d31f4d575ebb5d16c64269aaaafc280d6ed5e07dc4cce35e6c333fec8`
- Audit hash: `81a3eaeb66b18bf03679756c3d4cdacf339b6b05f7e2e9ba61e8069cba8958f7`
- Stock capture hash: `2aa308ce96a5d020141b086f0b0d26379610bf85dc9afe1b3569d8d09477f446`
- Source pages: `market-context/input-audit/responses/0015.json`–`0026.json`
- The original Actions artifact separately expires on **2026-12-29T10:23:49Z**.
  That expiry does not describe the independently verified Git copy below

The identical original ZIP is already held by the existing read-model source
archive at fixed reading `e2d5074e70acd65277e760ac9c825f51f003d8ec`:
[Git-held original ZIP](https://github.com/auguspp/decision-kernel/blob/e2d5074e70acd65277e760ac9c825f51f003d8ec/sources/artifacts/47f4ea4d31f4d575ebb5d16c64269aaaafc280d6ed5e07dc4cce35e6c333fec8.zip).
Its actual downloaded body is 3,449,794 bytes, Git blob
`7d136bca447b65e9fe08afbadd682049e5214485`, with the same ZIP SHA-256 above.
The Git and Actions bodies are byte-identical; ZIP CRC and the 42 Sector-audit
and 43 Stock-capture inventory entries were independently checked. The reading
binds this copy to run `36702153468` / artifact `11091190335` as
`EXACT_ARCHIVE_READ_COPY_NOT_PRODUCTION_RESTORE`.

At the recorded publisher code, normal publication preserves the previous tree,
parents the new commit to the previous reading and advances the ref without
force. This establishes fixed-reading Git recovery, not an unconditional permanent
archive, main-branch ancestry or production-restore authority; repository/ref
rewrites, deletion or loss of access remain risks. See [current-state custody
boundaries](current-state.md). No new storage owner or archive-limit workaround
is needed. The two-file derived report still does not contain the original ZIP
or source pages; its external-input requirement remains explicit, and hashes
alone cannot recover genuinely missing bytes.

The original Sector audit binds 42 files and the Stock capture binds 43 files.
Their request/response bytes are checked before consumption. The original
`reading/stock-reading.json` is used only as a separate regression comparator,
never as this consumer's input substitute.

Actual result:

- 5,578 unique identities across 12 complete pages; 5,560 usable last/previous
  quote ratios and 18 unpriced identities
- K=16 frozen independently; 5,544 priced rows deferred, all still represented
- Two selected identities have supplied history: `920344.BJ` qualifies;
  `688806.SH` preserves the corporate-action request failure, provider code 3002
- Fourteen selected identities remain `HISTORY_NOT_SUPPLIED`. The single qualified
  intersection is a retained historically selected trace, not evidence of a newly
  discovered, successfully investigated company
- Separate controls: `600072.SH`, `600802.SH`, `300904.SZ`, `920344.BJ` reproduce
  qualified raw paths exactly; `688806.SH` preserves code 3002; `600585.SH`
  preserves `PRICE_REFERENCE_DISCONTINUITY_REQUIRES_SEPARATE_REVIEW`

A separate comparison using the existing `build_stock_discovery_pool` on the
original retained result yields 45 Sector-leader identities, pool hash
`4cc85312306211085fbcbaa0b6b862ca8d556dde96f79e3adf334fde5f0152c4`.
The complete snapshot includes 5,533 identities outside that pool, 5,515 priced.
Eleven of the 16 sampled identities are outside that pool. These are coverage
differences, not counts of valuable discoveries. The comparator is not an input
gate in the independent consumer.

The [retained derived report](readings/c2-independent-stock-observations-2026-09-30/observations.json)
keeps the exact selected identities, source joins, qualifications and failures.
Its [generated summary](readings/c2-independent-stock-observations-2026-09-30/README.txt)
is part of the verified pair. Retention does not claim remote publication,
independent later consumption, Human acceptance or full C2 acceptance.

## Verification and remaining gates

Focused synthetic tests prohibit network and cover absent Sector/Research data,
signed deterministic ordering, the complete denominator, history-independent
selection, null/coherent-zero preservation, missing/extra/truncated/duplicate
pages, inconsistent totals/offsets, future clocks, original request/session pins,
HTTP receipt contradictions, 26-required/61-context behavior, rehashed origin and
source tampering, unchanged inputs and atomic create-only pair verification.
Legacy Stock tests separately exercise the unchanged wrapper and old consumers.

This archive was acquired on an active Sector day. Synthetic no-Sector tests prove
consumer independence, **not quiet-day live acquisition**. New independently
sampled histories, Surprise policy/value, false-positive and lead-time evidence,
attention cost, natural consumption and the original remaining P2-1–6 scope stay
open. No new live acquisition or Research permission is inferred from this replay.


## Manual independent K3 acquisition successor

The explicit `stock-independent-observations` purpose/job in the existing
`hithink-stock-dump-trial.yml` owner captures its own calendar, CSI300 benchmark
snapshot/history, all-market pages and selected own-stock traces. It accepts no
Sector run, discovery page or recovery key, and downloads no Sector artifact.
No Sector audit/run/state/membership/association is synthesized. Legacy
`build(audit_root, ...)`, v7/v8 capture contracts and legacy Stock selection remain
available with their existing semantics. The pure sample and report assembly
are shared; code provenance hashes honestly change when implementation changes.

**Reuse decision: REUSE + THIN_ADAPTER.** This uses the already-inspected
PR #687 internal parsers, exact source-read binding, selection/assembly and raw
price arithmetic; existing `HithinkStockSnapshotReference` from PR #579; the
existing credential-isolated, no-redirect, bounded HTTPS transport and official
HiThink endpoints; and GitHub manual jobs, artifacts and CI identity checks.
The only transport extension admits exact `limit=500`, canonical offsets
`0,500,...,6500` on the existing snapshot endpoint. Individual `thscodes` requests
remain unchanged. Decimal JSON lexemes remain strings, without binary-float loss.
The retained #508/#511 / PR #687 official and EasyStock prior-art assessment above
covers this same source/pagination/assembly capability; no new external code or
dependency is introduced and no new upstream-equivalence review is claimed.

### Attempt cost and stop conditions

- Fixed K=3, 500 rows per complete page, existing ceiling of 26 source attempts
- Three context requests + P complete pages + at most nine own-stock requests;
  P=12 therefore costs at most 24 attempts, not a K16 live batch
- After the first page declares its total, require
  `3 + ceil(total/500) + 3*3 <= 26`; totals above 7,000 reject at attempt four
- No truncation, silent K reduction, available-history intersection, retry,
  fallback provider or automatic next batch. Every failed transport/business
  attempt counts. Known issuer-local gaps retain the frozen selection; shared
  credential/rate-limit/clock failures stop the attempt
- Existing 20-second spacing, bounded response/capture bytes and 30-minute source
  lifetime; workflow has a 20-minute timeout. A process killed before sealing
  is incomplete evidence, never a successful scan

Selection remains the unvalidated absolute signed quote-move sampling rule,
not Surprise, investment priority, company quality, liquidity or tradability.
All source identities remain represented. Company name, name-based risk and
per-security trade-date qualifications remain UNKNOWN where unavailable.

The job requires exact main, successful independent main CI and first manual
attempt. An existing bounded metadata check observes shared-Key peers once;
this is not an atomic lock or provider-quota proof. There are no new credentials,
billing settings, cron, source owner, framework or model calls. GitHub runner
and existing HiThink quota use remain bounded costs of an explicitly dispatched
attempt; monetary provider pricing is not inferred here.

### Truthful capture and replay

`hithink_independent_capture.capture` writes create-only `capture.json`, actual
workflow identity and start/finish/request/receipt clocks, context, decoded safe
provider response bodies, and `selection.json` before any own-history request.
Its inventory binds the exact source bytes and producing implementation. The
capture version is `hithink-independent-stock-capture-v1`, not a legacy Sector or
Stock capture. Decoded envelopes are not original HTTP wire bytes.

A complete capture additionally writes `observations.json` and `README.txt`.
`verify --root <capture> --capture-hash <independently retained capture hash>`
replays the same ordered source plan with no network, checks every consumed byte,
rebuilds selection and qualified paths, and compares exact derived bytes. Failed
attempts only receive an inventory/receipt verification: transport causes and
unsafe discarded bodies are not re-proven offline. A failed shared input does
not publish an empty successful observation file. Artifact custody lasts 90 days;
upload, remote digest/run verification, permanent retention and fixed-R recovery
are separate acceptance facts. No archive index or live Stock admission is added.

The existing `current_state_delivery` selector sees only non-skipped
`stock-reading`, so the distinct independent job cannot become a legacy product.
The `stock-reading-after-sector` title guard excludes this purpose, with an exact
upstream-attempt job check and pure-plan suppression as defense in depth. Failed
independent runs cannot dispatch a missing Sector/Stock stage or overwrite daily
health. Existing separately scheduled daily reconciliation is unchanged; it is
not an independent-capture successor or an extension of this attempt's budget.

### Optional exact October 1 closure

The manual choice `independent-closure-date=2026-10-01` applies only to a real
October 1 Shanghai capture anchored to September 30. The implementation retains
reviewed notice facts from [SSE notice 上证公告〔2026〕22号](https://www.sse.com.cn/disclosure/announcement/general/c/c_20260915_10832273.shtml):
published September 17, October 1–7 closed, October 8 resumes. These bound facts
are copied to the capture inventory as `inputs/closure-evidence.json`; a URL
string alone is insufficient. This is a derived reviewed fact record, not a
claim to original HTML custody or provider calendar completeness.

`closed_dates` is exactly `[2026-10-01]`. The actual provider calendar must omit
that date; CSI300 snapshot/history must qualify September 30. Ready clocks must
be at least September 30 15:30 Shanghai and no later than their own receipts.
Actual October 1 clocks are retained. The prior consumed September backfill pilot
is not reused. Other dates/intervals require separately reviewed evidence; no
holiday inference or generic calendar framework is introduced.

An accepted closure capture demonstrates independent acquisition mechanics only.
It does **not** establish a naturally quiet active-day sample, incremental useful
discovery, Surprise quality/false-positive/attention cost, subsequent Research
use, Human acceptance or completion of original C2/C.

### Acceptance sequence

Local deterministic tests and legacy regressions first; then normal exact-head
formal CI, verified native artifacts, merge/main qualification and ordinary
publication under the existing delivery process. A provider call is a separate
explicitly bounded manual attempt after those prerequisites, not a side effect
of merging or testing. Independently recover and replay its actual artifact,
retaining request counts, failures, gaps and custody limits. Subsequent naturally
quiet-day discovery value and actual research use remain original C2 gates.
